import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
import re

def safe_float(value):
    try:
        return float(value)
    except:
        return None

# === 監測站 → 18 區中文 ===
STATION_TO_DISTRICT = {
    'Central/Western': '中西區',
    'Southern': '南區',
    'Eastern': '東區',
    'Kwun Tong': '觀塘區',
    'Sham Shui Po': '深水埗區',
    'Kwai Chung': '葵青區',
    'Tsuen Wan': '荃灣區',
    'Tseung Kwan O': '西貢區',
    'Yuen Long': '元朗區',
    'Tuen Mun': '屯門區',
    'Tung Chung': '離島區',
    'Tai Po': '大埔區',
    'Sha Tin': '沙田區',
    'North': '北區',
    'Tap Mun': '大埔區',  # Tap Mun 歸入大埔
    # 注意：黃大仙、九龍城、灣仔、油尖旺、南區已有
    # 灣仔需用 Causeway Bay？但它是路邊站 → 暫不處理
}

def get_aqhi_from_rss():
    try:
        url = "https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = 'utf-8'
        
        root = ET.fromstring(r.content)
        namespaces = {'ns': 'http://www.w3.org/2005/Atom'}
        
        aqhi_dict = {}
        
        for entry in root.findall('ns:entry', namespaces):
            title_elem = entry.find('ns:title', namespaces)
            content_elem = entry.find('ns:content', namespaces)
            
            if title_elem is None or content_elem is None:
                continue
                
            station_name = title_elem.text.strip()
            content_text = content_elem.text.strip()
            
            # 跳過路邊站
            if 'Roadside Stations' in content_text:
                continue
                
            # 從內容提取數字，例如 "5 Moderate"
            # 使用正則表達式找開頭的數字
            match = re.search(r':\s*(\d+)', content_text)
            if match:
                aqhi = safe_float(match.group(1))
                if aqhi is not None:
                    district = STATION_TO_DISTRICT.get(station_name, station_name)
                    aqhi_dict[district] = aqhi
            else:
                print(f"⚠️ 無法解析 AQHI: {content_text}")
                
        return aqhi_dict
    except Exception as e:
        print(f"❌ RSS 抓取錯誤: {e}")
        return {}

# === 溫度（保持不變）===
def get_hko_temperature():
    try:
        df = pd.read_csv(
            "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature_uc.csv",
            timeout=10
        )
        temps = []
        for col in df.columns:
            if 'Temperature' in col:
                for val in df[col]:
                    if pd.notna(val):
                        try:
                            temps.append(float(val))
                        except:
                            pass
                break
        return sum(temps) / len(temps) if temps else None
    except Exception as e:
        print(f"⚠️ 溫度錯誤: {e}")
        return None

# === 主程式 ===
if __name__ == "__main__":
    print("🚀 開始執行健康風險評估...")
    
    aqhi_data = get_aqhi_from_rss()
    if not aqhi_data:
        print("❌ 無法取得 AQHI 數據")
        sys.exit(1)
    print(f"✅ 成功取得 {len(aqhi_data)} 個區域的 AQHI")
    print("數據預覽:", list(aqhi_data.items())[:3])
    
    current_temp = get_hko_temperature()
    print(f"🌡️ 全港即時溫度: {current_temp}°C")
    
    results = []
    for district, aqhi in aqhi_data.items():
        risk = aqhi * 0.7
        if current_temp is not None and current_temp < 16:
            risk += (16 - current_temp) * 0.3
        risk = min(risk, 10.0)
        results.append({
            'district': district,
            'aqhi': round(aqhi, 1),
            'temperature': round(current_temp, 1) if current_temp else None,
            'risk_score': round(risk, 2),
            'risk_level': '高' if risk > 7 else '中' if risk > 4 else '低',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    
    df = pd.DataFrame(results)
    df.to_csv('risk_map.csv', index=False, encoding='utf-8')
    print(f"✅ risk_map.csv 已生成（{len(df)} 區）")
    print(df[['district', 'risk_level']].to_string(index=False))

