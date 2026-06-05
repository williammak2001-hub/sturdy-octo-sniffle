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

# A. 建立基礎資料表（如果是全新資料庫會直接用這結構）
cursor.execute('''
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT,
        race_no INTEGER,
        horse_name TEXT,
        draw INTEGER,
        weight INTEGER,
        finish_seconds REAL,
        PRIMARY KEY (race_date, race_no, horse_name)
    )
''')
conn.commit()

# 💡 B. 【核心安全升級】：檢查並手動為「舊資料庫」追加新欄位
# 1. 獲取目前資料庫內現有的所有欄位名稱
cursor.execute("PRAGMA table_info(race_results)")
existing_columns = [column[1] for column in cursor.fetchall()]

# 2. 安全檢查：如果缺少 `actual_rank`，就手動追加
if 'actual_rank' not in existing_columns:
    print("⚠️ 偵測到舊版資料庫缺少 actual_rank 欄位，正在進行動態升級...")
    cursor.execute("ALTER TABLE race_results ADD COLUMN actual_rank INTEGER;")
    conn.commit()
    print("✅ actual_rank 欄位已成功追加！")

# 3. 安全檢查：如果缺少 `past_avg_seconds`，也手動追加
if 'past_avg_seconds' not in existing_columns:
    print("⚠️ 偵測到舊版資料庫缺少 past_avg_seconds 欄位，正在進行動態升級...")
    cursor.execute("ALTER TABLE race_results ADD COLUMN past_avg_seconds REAL;")
    conn.commit()
    print("✅ past_avg_seconds 欄位已成功追加！")

print("資料庫結構檢查完畢，已是最新狀態！")

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
print("=== 📥 4. 自動寫入資料庫 (如有重複自動覆蓋) ===")

# 💡 【核心修改】：棄用 pandas.to_sql()，改用原生 SQL 的 INSERT OR REPLACE
# 這樣就算重複執行，它也會自動用最新數據覆蓋舊數據，不會再報錯！

insert_sql = '''
    INSERT OR REPLACE INTO race_results (
        race_date, race_no, actual_rank, horse_name, draw, weight, finish_seconds, past_avg_seconds
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
'''

# 將 Pandas DataFrame 轉換成 Python 的 List 格式方便寫入
data_tuples = final_db_data.to_records(index=False).tolist()

try:
    # cursor.executemany 可以一次過快速寫入多條數據
    cursor.executemany(insert_sql, data_tuples)
    conn.commit()
    print("🎉 成功將今日賽果自動寫入資料庫！（重複數據已自動覆蓋更新）")
except Exception as e:
    print(f"❌ 寫入資料庫失敗: {e}")

conn.close()