import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import sys

# === 監測站 → 18 區對應表 ===
station_to_district = {
    'Central': '中西區',
    'Wan Chai': '灣仔區',
    'Causeway Bay': '灣仔區',
    'Eastern': '東區',
    'North Point': '東區',
    'Kwun Tong': '觀塘區',
    'Sham Shui Po': '深水埗區',
    'Kwai Chung': '葵青區',
    'Tsuen Wan': '荃灣區',
    'Tuen Mun': '屯門區',
    'Tung Chung': '離島區',
    'Tai Po': '大埔區',
    'Sha Tin': '沙田區',
    'Yuen Long': '元朗區',
    'Hong Kong Observatory': '油尖旺區',
    'King\'s Park': '九龍城區',
    'Wong Chuk Hang': '南區',
    'Sai Kung': '西貢區',
    'Tseung Kwan O': '西貢區',
    'Cheung Chau': '離島區',
    'Lau Fau Shan': '元朗區',
    'Tai Mei Tuk': '大埔區',
}

def safe_float(value):
    try:
        return float(value)
    except:
        return None

# === 抓 AQHI ===
def get_aqhi():
    try:
        r = requests.get("https://aqhi.gov.hk/en/aqhi/past-24-hours.xml", timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.content)
        aqhi_dict = {}
        for station in root.findall('.//station'):
            name_elem = station.find('name')
            aqhi_elem = station.find('aqhi')
            if name_elem is not None and aqhi_elem is not None:
                name = name_elem.text.strip()
                val = safe_float(aqhi_elem.text)
                if val is not None:
                    aqhi_dict[name] = val
        return aqhi_dict
    except Exception as e:
        print(f"AQHI error: {e}")
        return {}

# === 抓溫度 ===
def get_temp():
    try:
        df = pd.read_csv(
            "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature_uc.csv",
            timeout=10
        )
        temp_dict = {}
        for _, row in df.iterrows():
            name = row.get('Automatic Weather Station', 'Unknown')
            temp = safe_float(row.get('Air Temperature (°C)', None))
            if temp is not None:
                temp_dict[name] = temp
        return temp_dict
    except Exception as e:
        print(f"Temperature error: {e}")
        return {}

# === 主程式 ===
if __name__ == "__main__":
    print("開始抓取 AQHI 與溫度...")
    aqhi_data = get_aqhi()
    temp_data = get_temp()
    
    if not aqhi_data and not temp_data:
        print("❌ 無法取得任何數據，終止執行。")
        sys.exit(1)
    
    results = []
    all_stations = set(list(aqhi_data.keys()) + list(temp_data.keys()))
    
    for station in all_stations:
        district = station_to_district.get(station, '其他')
        aqhi = aqhi_data.get(station, None)
        temp = temp_data.get(station, None)
        
        risk = 0
        if aqhi is not None:
            risk += aqhi * 0.6
        if temp is not None and temp < 16:
            risk += (16 - temp) * 0.4
        risk = min(risk, 10)
        
        results.append({
            'district': district,
            'risk_score': round(risk, 2),
            'risk_level': '高' if risk > 7 else '中' if risk > 4 else '低',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    
    df = pd.DataFrame(results)
    if df.empty:
        print("❌ 無有效數據，不生成 CSV。")
        sys.exit(1)
    
    df_agg = df.sort_values('risk_score', ascending=False).drop_duplicates('district')
    df_agg.to_csv('risk_map.csv', index=False, encoding='utf-8')
    print(f"✅ 成功生成 risk_map.csv（共 {len(df_agg)} 區）")
