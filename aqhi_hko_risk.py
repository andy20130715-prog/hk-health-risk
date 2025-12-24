 import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime

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

# === 抓 AQHI ===
def get_aqhi():
    try:
        r = requests.get("https://aqhi.gov.hk/en/aqhi/past-24-hours.xml")
        root = ET.fromstring(r.content)
        aqhi_dict = {}
        for station in root.findall('.//station'):
            name = station.find('name').text
            val = station.find('aqhi').text
            if val and val.replace('.','',1).isdigit():
                aqhi_dict[name] = float(val)
        return aqhi_dict
    except:
        return {}

# === 抓溫度 ===
def get_temp():
    try:
        df = pd.read_csv("https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature_uc.csv")
        temp_dict = {}
        for _, row in df.iterrows():
            name = row['Automatic Weather Station']
            temp = row['Air Temperature (°C)']
            if pd.notna(temp):
                temp_dict[name] = float(temp)
        return temp_dict
    except:
        return {}

# === 主程式 ===
if __name__ == "__main__":
    aqhi_data = get_aqhi()
    temp_data = get_temp()
    
    results = []
    all_stations = set(list(aqhi_data.keys()) + list(temp_data.keys()))
    
    for station in all_stations:
        district = station_to_district.get(station, '其他')
        aqhi = aqhi_data.get(station, None)
        temp = temp_data.get(station, None)
        
        # 風險公式（可調整）
        risk = 0
        if aqhi is not None:
            risk += aqhi * 0.6
        if temp is not None and temp < 16:
            risk += (16 - temp) * 0.4
        
        risk = min(risk, 10)  # 最高 10 分
        
        results.append({
            'district': district,
            'risk_score': round(risk, 2),
            'risk_level': '高' if risk > 7 else '中' if risk > 4 else '低',
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M')
        })
    
    # 按區取最高風險
    df = pd.DataFrame(results)
    df_agg = df.sort_values('risk_score', ascending=False).drop_duplicates('district')
    df_agg.to_csv('risk_map.csv', index=False, encoding='utf-8')
    print("✅ risk_map.csv 已生成")