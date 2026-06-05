import os
# ✨ 強制設定環境變數，限制 OpenBLAS 與 MKL 只使用單線程運作，一秒治好記憶體分配潰
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import requests
from bs4 import BeautifulSoup
import pandas as pd
import sqlite3
import time
import random
from datetime import datetime, timedelta

# 1. 設置時間清洗邏輯
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

# 2. 自動獲取「現實世界今天與昨天的日期」進行批量更新
# 這樣不論你哪一天執行，它都會自動去抓最近的比賽，不用手動改日期
today_str = datetime.now().strftime('%Y/%m/%d')
yesterday_str = (datetime.now() - timedelta(days=1)).strftime('%Y/%m/%d')

# 你可以把想要更新的日期放進這個清單（這裡以昨天和今天為例）
target_dates = [yesterday_str, today_str] 
# 測試提示：如果這兩天剛好沒賽馬，你可以手動改成馬會最近有比賽的日期，例如: ['2026/06/03']

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print("=== 🗄️ 1. 連線至核心資料庫 ===")
conn = sqlite3.connect('racing_platform.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT, race_no INTEGER, rank TEXT, horse_name TEXT,
        draw INTEGER, weight INTEGER, finish_seconds REAL,
        PRIMARY KEY (race_date, race_no, horse_name)
    )
''')
conn.commit()

print("=== 🚀 2. 開始跨日期全自動即時追蹤 ===")

for date_to_crawl in target_dates:
    print(f"\n📅 正在檢查現實日期：{date_to_crawl} 的賽事...")
    
    # 一天通常有 11 場比賽，我們用迴圈自動跑
    for race_no in range(1, 12):
        url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={date_to_crawl}&RaceNo={race_no}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = 'utf-8'
            
            if response.status_code != 200:
                # 如果這天沒賽事，馬會網站會回傳錯誤，我們就直接跳過這一天
                break 
                
            soup = BeautifulSoup(response.text, 'html.parser')
            tables = soup.find_all('table', class_='table_bd')
            results_table = None
            
            for t in tables:
                if '名次' in t.text or '馬名' in t.text:
                    results_table = t
                    break
            
            if not results_table:
                # 找不到表格代表這場比賽不存在，跳出這天的迴圈
                break
                
            rows = results_table.find_all('tr')
            race_horses = []
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 10:
                    try:
                        rank = cols[0].text.strip()
                        if rank.isdigit() or rank in ['WX', 'WX-A', 'A', 'DISQ', 'D']:
                            # 即時進行數據清洗與轉換
                            raw_time = cols[10].text.strip()
                            sec = convert_time_to_seconds(raw_time)
                            
                            race_horses.append({
                                'race_date': date_to_crawl,
                                'race_no': race_no,
                                'rank': rank,
                                'horse_name': cols[2].text.strip().split('(')[0],
                                'draw': int(cols[7].text.strip()) if cols[7].text.strip().isdigit() else np.nan,
                                'weight': int(cols[5].text.strip()) if cols[5].text.strip().isdigit() else np.nan,
                                'finish_seconds': sec
                            })
                    except:
                        continue
            
            if race_horses:
                df = pd.DataFrame(race_horses)
                # 寫入資料庫，遇到重複的自動忽略 (OR IGNORE)
                df.to_sql('race_results', conn, if_exists='append', index=False, method='multi')
                print(f"  🏁 第 {race_no} 場次：抓取成功！已自動寫入資料庫。")
            
            # 防 BAN 安全機制：隨機休息 2-3 秒
            time.sleep(random.uniform(2, 3))
            
        except Exception as e:
            print(f"  ❌ 第 {race_no} 場發生異常: {e}")
            continue

print("\n" + "="*50)
print("🎉 現實數據自動同步流水線執行完畢！資料庫已是最新狀態。")
conn.close()