import requests
import pandas as pd
from datetime import datetime
import sys

def safe_float(value):
    try:
        return float(value)
    except:
        return None

# === 從 data.gov.hk 獲取 18 區 AQHI ===
def get_aqhi_district():
    try:
        url = "https://api.data.gov.hk/v2/aggregate/hk-epd-airteam-air-quality-data-air-quality-health-index-district?lang=en"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            print("❌ AQHI 數據為空")
            return {}
        
        latest = data[-1]  # 最新記錄
        aqhi_dict = {}
        for eng_name, record in latest.items():
            if isinstance(record, dict) and 'INDEX' in record:
                aqhi = safe_float(record['INDEX'])
                if aqhi is not None:
                    aqhi_dict[eng_name] = aqhi
        return aqhi_dict
    except Exception as e:
        print(f"❌ AQHI API 錯誤: {e}")
        return {}

# === 從 HKO 獲取溫度（用於降溫風險）===
def get_latest_temperature():
    try:
        df = pd.read_csv(
            "https://data.weather.gov.hk/weatherAPI/hko_data/regional-weather/latest_1min_temperature_uc.csv",
            timeout=10
        )
        # 計算全港平均溫度（簡化）
        temps = []
        for col in df.columns:
            if 'Temperature' in col or 'temperature' in col:
                for temp in df[col]:
                    if pd.notna(temp):
                        temps.append(float(temp))
                break
        if temps:
            return sum(temps) / len(temps)
        return None
    except Exception as e:
        print(f"⚠️ 溫度數據錯誤（可忽略）: {e}")
        return None

# === 英文區名 → 中文區名 ===
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
    print("🚀 開始執行健康風險計算...")
    
    # 1. 抓取 AQHI（18 區）
    aqhi_data = get_aqhi_district()
    if not aqhi_data:
        print("❌ 無法取得 AQHI 數據，終止執行。")
        sys.exit(1)
    print(f"✅ 取得 {len(aqhi_data)} 個區的 AQHI 數據")
    
    # 2. 抓取溫度（用於降溫評估）
    current_temp = get_latest_temperature()
    print(f"🌡️ 全港即時平均溫度: {current_temp}°C")
    
    # 3. 計算風險（範例：只用 AQHI，可加溫度）
    results = []
    for eng_district, aqhi in aqhi_data.items():
        chi_district = ENG_TO_CHI.get(eng_district, eng_district)
        
        # 風險公式（可調整）
        risk = aqhi * 0.8  # AQHI 權重 80%
        if current_temp is not None and current_temp < 16:
            risk += (16 - current_temp) * 0.2  # 冷天加重
        
        risk = min(risk, 10.0)  # 最高 10 分
        
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
    print(f"✅ 成功生成 risk_map.csv（共 {len(df)} 區）")
    print("📄 檔案內容預覽:")
    print(df[['district', 'risk_level']].to_string(index=False))
