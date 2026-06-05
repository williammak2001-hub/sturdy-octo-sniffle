import sqlite3
import pandas as pd
import numpy as np

# 定義時間清洗函式
def convert_time_to_seconds(time_str):
    if pd.isna(time_str) or str(time_str).strip() in ['', '---', 'WX']:
        return np.nan
    try:
        time_str = str(time_str).strip()
        if ':' in time_str:
            parts = time_str.split(':')
            return float(parts[0]) * 60 + float(parts[1])
        return float(time_str)
    except:
        return np.nan

print("=== 🗄️ 1. 初始化 SQLite 資料庫 ===")
conn = sqlite3.connect('racing_platform.db')
cursor = conn.cursor()

# 💡 【修改 1】：資料表結構新增 `past_avg_seconds` 欄位與 `actual_rank` 欄位
cursor.execute('''
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT,
        race_no INTEGER,
        actual_rank INTEGER,  -- 改為整數型態的名次，方便 Ranker 讀取
        horse_name TEXT,
        draw INTEGER,
        weight INTEGER,
        finish_seconds REAL,
        past_avg_seconds REAL, -- 💡 新增：儲存這匹馬在該場比賽前的歷史平均秒數
        PRIMARY KEY (race_date, race_no, horse_name)
    )
''')
conn.commit()
print("資料庫與資料表 `race_results` 升級準備就緒！")

print("\n" + "="*50 + "\n")
print("=== 🚀 2. 模擬今日爬蟲抓到的新賽果 ===")

# 模擬今天抓下來的排位/賽果數據
today_scraped_data = pd.DataFrame({
    'race_date': ['2026/06/03', '2026/06/03', '2026/06/03'],
    'race_no': [1, 1, 1],
    'rank': [1, 2, 3], # 真實名次
    'horse_name': ['浪漫勇士', '金鎗六十', '加州星球'],
    'draw': ['3', '7', '12'],
    'weight': ['126', '126', '126'],
    '完賽時間': ['1:47.20', '1:47.50', '1:48.10']
})
print(today_scraped_data)

print("\n" + "="*50 + "\n")
print("=== 🧼 3. 自動化數據清洗與計算歷史平均 ===")

today_scraped_data['finish_seconds'] = today_scraped_data['完賽時間'].apply(convert_time_to_seconds)
today_scraped_data['draw'] = pd.to_numeric(today_scraped_data['draw'], errors='coerce')
today_scraped_data['weight'] = pd.to_numeric(today_scraped_data['weight'], errors='coerce')
today_scraped_data['actual_rank'] = pd.to_numeric(today_scraped_data['rank'], errors='coerce')

# 💡 【修改 2】：動態計算或給予這匹馬的「歷史平均秒數」
# 在實戰中，你會去資料庫搜尋這匹馬以前跑過的所有秒數取平均值。
# 這裡做一個防呆：如果找不到過去紀錄，就先用這場的完賽秒數 + 微小隨機值模擬，或是預設一個基準值。
today_scraped_data['past_avg_seconds'] = today_scraped_data['finish_seconds'].fillna(107.50)

# 只保留資料庫需要的 8 個欄位
final_db_data = today_scraped_data[[
    'race_date', 'race_no', 'actual_rank', 'horse_name', 'draw', 'weight', 'finish_seconds', 'past_avg_seconds'
]]

print("\n" + "="*50 + "\n")
print("=== 📥 4. 自動寫入資料庫 (如有重複自動覆蓋/忽略) ===")

# 使用 to_sql 寫入。注意：為了支援 PRIMARY KEY 的重複忽略，實戰可以用 sqlite3 的 INSERT OR IGNORE。
# 這裡簡單起見先用 append。如果遇到重複報錯，可以手動刪除舊的 db 檔案再重新執行。
final_db_data.to_sql('race_results', conn, if_exists='append', index=False, method='multi')
print("🎉 成功將含有「歷史平均秒數」的今日賽果自動寫入資料庫！")

print("\n" + "="*50 + "\n")
print("=== 🔍 5. 從資料庫讀取全部數據驗證 ===")
df_from_db = pd.read_sql_query("SELECT * FROM race_results", conn)
print(df_from_db)

conn.close()