import sqlite3
import pandas as pd
import numpy as np

# 定義時間清洗函式（確保存入資料庫前數據是乾淨的）
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
# 連線到資料庫檔案（如果檔案不存在，會自動在同目錄下建立）
conn = sqlite3.connect('racing_platform.db')
cursor = conn.cursor()

# 建立一張用來存賽果的 SQL 資料表（表格結構）
cursor.execute('''
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT,
        race_no INTEGER,
        rank TEXT,
        horse_name TEXT,
        draw INTEGER,
        weight INTEGER,
        finish_seconds REAL,
        PRIMARY KEY (race_date, race_no, horse_name) -- 聯合主鍵：防止同一隻馬在同一場被重複插入
    )
''')
conn.commit()
print("資料庫與資料表 `race_results` 準備就緒！")

print("\n" + "="*50 + "\n")
print("=== 🚀 2. 模擬今日爬蟲抓到的新賽果 ===")

# 假設這是爬蟲今天（2026/06/03）剛抓下來的熱騰騰數據
today_scraped_data = pd.DataFrame({
    'race_date': ['2026/06/03', '2026/06/03', '2026/06/03'],
    'race_no': [1, 1, 1],
    'rank': ['1', '2', '3'],
    'horse_name': ['浪漫勇士', '金鎗六十', '加州星球'],
    'draw': ['3', '7', '12'],
    'weight': ['126', '126', '126'],
    '完賽時間': ['1:47.20', '1:47.50', '1:48.10'] # 尚未清洗的文字時間
})
print(today_scraped_data)

print("\n" + "="*50 + "\n")
print("=== 🧼 3. 自動化數據清洗 ===")

today_scraped_data['finish_seconds'] = today_scraped_data['完賽時間'].apply(convert_time_to_seconds)
today_scraped_data['draw'] = pd.to_numeric(today_scraped_data['draw'], errors='coerce')
today_scraped_data['weight'] = pd.to_numeric(today_scraped_data['weight'], errors='coerce')

# 只保留資料庫需要的欄位
final_db_data = today_scraped_data[['race_date', 'race_no', 'rank', 'horse_name', 'draw', 'weight', 'finish_seconds']]

print("\n" + "="*50 + "\n")
print("=== 📥 4. 自動寫入資料庫 (如有重複自動忽略) ===")

# to_sql 是 Pandas 內建直接塞進資料庫的神器
# if_exists='append': 代表把新數據接在舊數據後面
final_db_data.to_sql('race_results', conn, if_exists='append', index=False, method='multi')
print("🎉 成功將今日賽果自動寫入資料庫！")

print("\n" + "="*50 + "\n")
print("=== 🔍 5. 從資料庫讀取全部數據驗證 ===")
# 以後 AI 訓練時，直接從資料庫拉數據
df_from_db = pd.read_sql_query("SELECT * FROM race_results", conn)
print(df_from_db)

# 關閉資料庫連線
conn.close()