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
    'Tap Mun': '大埔區',
}

def get_aqhi_from_rss():
    try:
        url = "https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = 'utf-8'
        
        # 移除命名空間干擾
        xml_text = r.text.replace('xmlns=', 'ns=')
        root = ET.fromstring(xml_text)
        
        aqhi_dict = {}
        entries = root.findall('.//entry')
        
        for entry in entries:
            title = entry.find('title')
            content = entry.find('content')
            if title is None or content is None:
                continue
                
            station_name = title.text.strip()
            content_text = content.text.strip()
            
            if 'Roadside Stations' in content_text:
                continue
                
            parts = content_text.split(':', 1)
            if len(parts) == 2:
                value_part = parts[1].strip()
                num_str = ""
                for char in value_part:
                    if char.isdigit():
                        num_str += char
                    else:
                        break
                if num_str:
                    aqhi = safe_float(num_str)
                    if aqhi is not None:
                        district = STATION_TO_DISTRICT.get(station_name, station_name)
                        aqhi_dict[district] = aqhi
        print(f"🔍 解析到 {len(aqhi_dict)} 個區域: {list(aqhi_dict.keys())}")
        return aqhi_dict
    except Exception as e:
        print(f"❌ RSS 錯誤: {e}")
        return {}

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

if __name__ == "__main__":
    print("🚀 開始執行健康風險評估...")
    aqhi_data = get_aqhi_from_rss()
    if not aqhi_
        print("❌ 無法取得 AQHI 數據")
        sys.exit(1)
    print(f"✅ 成功取得 {len(aqhi_data)} 個區域的 AQHI")
    
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
