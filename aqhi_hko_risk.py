import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import sys

def safe_float(value):
    try:
        return float(value)
    except:
        return None

# === 從香港政府 RSS 抓取 18 區 AQHI ===
def get_aqhi_from_rss():
    try:
        url = "https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = 'utf-8'
        
        # 解析 XML
        root = ET.fromstring(r.content)
        namespaces = {'ns': 'http://www.w3.org/2005/Atom'}
        
        aqhi_dict = {}
        
        # 找出所有 <entry>（每個 entry 是一個區域）
        for entry in root.findall('ns:entry', namespaces):
            title = entry.find('ns:title', namespaces)
            content = entry.find('ns:content', namespaces)
            
            if title is not None and content is not None:
                # title 格式: "Central and Western: 3"
                title_text = title.text.strip()
                if ':' in title_text:
                    eng_district, aqhi_str = title_text.split(':', 1)
                    eng_district = eng_district.strip()
                    aqhi = safe_float(aqhi_str.strip())
                    if aqhi is not None:
                        aqhi_dict[eng_district] = aqhi
        return aqhi_dict
    except Exception as e:
        print(f"❌ RSS 解析錯誤: {e}")
        return {}

# === 從 HKO 抓取溫度（全港平均）===
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
        print(f"⚠️ 溫度數據可選性錯誤: {e}")
        return None

# === 英文區 → 中文區 ===
ENG_TO_CHI = {
    'Central and Western': '中西區',
    'Wan Chai': '灣仔區',
    'Eastern': '東區',
    'Kowloon City': '九龍城區',
    'Kwun Tong': '觀塘區',
    'Sham Shui Po': '深水埗區',
    'Yau Tsim Mong': '油尖旺區',
    'Wong Tai Sin': '黃大仙區',
    'Kwai Tsing': '葵青區',
    'Tsuen Wan': '荃灣區',
    'Tuen Mun': '屯門區',
    'North': '北區',
    'Yuen Long': '元朗區',
    'Tai Po': '大埔區',
    'Sha Tin': '沙田區',
    'Sai Kung': '西貢區',
    'Islands': '離島區',
    'Southern': '南區',
}

# === 主程式 ===
if __name__ == "__main__":
    print("🚀 開始執行健康風險評估...")
    
    # 1. 抓 AQHI
    aqhi_data = get_aqhi_from_rss()
    if not aqhi_
        print("❌ 無法從 RSS 取得 AQHI 數據")
        sys.exit(1)
    print(f"✅ 成功取得 {len(aqhi_data)} 個區的 AQHI")
    
    # 2. 抓溫度
    current_temp = get_hko_temperature()
    print(f"🌡️ 全港即時溫度: {current_temp}°C")
    
    # 3. 計算風險
    results = []
    for eng_district, aqhi in aqhi_data.items():
        chi_district = ENG_TO_CHI.get(eng_district, eng_district)
        
        risk = aqhi * 0.7
        if current_temp is not None and current_temp < 16:
            risk += (16 - current_temp) * 0.3
        risk = min(risk, 10.0)
        
        results.append({
            'district': chi_district,
            'aqhi': round(aqhi, 1),
            'temperature': round(current_temp, 1) if current_temp else None,
            'risk_score': round(risk, 2),
            'risk_level': '高' if risk > 7 else '中' if risk > 4 else '低',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    
    # 4. 輸出 CSV
    df = pd.DataFrame(results)
    df.to_csv('risk_map.csv', index=False, encoding='utf-8')
    print(f"✅ risk_map.csv 已生成（{len(df)} 區）")
    print(df[['district', 'risk_level']].to_string(index=False))
