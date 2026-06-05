import sqlite3
import pandas as pd
import numpy as np
import requests
import os
import time
import re
import io  # 修正讀取字串必備

print("=== 🗄️ 1. 初始化 SQLite 資料庫 ===")
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'racing_platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS race_results (
        race_date TEXT,
        race_no INTEGER,
        actual_rank INTEGER,
        horse_name TEXT,
        draw INTEGER,
        weight INTEGER,
        finish_seconds REAL,
        past_avg_seconds REAL,
        PRIMARY KEY (race_date, race_no, horse_name)
    )
''')
conn.commit()
print("資料庫結構就緒！")

print("\n" + "="*50 + "\n")
print("=== 🌐 2. 開始從香港賽馬會網頁爬取賽果數據 ===")

target_date = "2026-06-07" 
formatted_date_db = target_date.replace("-", "/")

all_real_races = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://racing.hkjc.com/'
}

for race_no in range(1, 12):
    print(f"正在下載 {target_date} 第 {race_no} 場賽果...", end="")
    
    # 這是賽果網址
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={target_date}&RaceNo={race_no}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(" ❌ 伺服器拒絕連線或無此場次。")
            continue
            
        if "沒有有關賽事紀錄" in response.text or "未有排位資料" in response.text:
            print(" ⚠️ 馬會尚未釋出該場資料或當天無比賽。")
            continue
            
        # 💡 【核心修正】使用 io.StringIO 包裹 HTML 字串，防止 Pandas 誤認為是檔案路徑
        tables = pd.read_html(io.StringIO(response.text))
        
        race_table = None
        for t in tables:
            # 馬會賽果表格通常包含「名次」或「馬名」
            # 這裡把欄位名稱全部轉成字串來比對
            cols_str = "".join([str(c) for c in t.columns.get_level_values(0)])
            if '馬名' in cols_str and ('名次' in cols_str or '檔位' in cols_str):
                race_table = t
                break
                
        if race_table is None:
            print(" ❌ 找不到相符的賽果表格欄位。")
            continue
            
        # 如果表格欄位是 MultiIndex (多層欄位)，將其扁平化成一般字串
        if isinstance(race_table.columns, pd.MultiIndex):
            race_table.columns = ['_'.join(col).strip() for col in race_table.columns]
        else:
            race_table.columns = [str(col).strip() for col in race_table.columns]

        # 動態偵測欄位名稱所在的位置
        cols = race_table.columns
        rank_col = [c for c in cols if '名次' in c]
        name_col = [c for c in cols if '馬名' in c]
        draw_col = [c for c in cols if '檔位' in c]
        weight_col = [c for c in cols if '實際負磅' in c or '負磅' in c]
        time_col = [c for c in cols if '完成時間' in c]

        if not name_col:
            print(" ❌ 無法定位馬名欄位。")
            continue

        # 逐行解析數據
        for idx, row in race_table.iterrows():
            try:
                # 提取馬名並清洗
                horse_name = str(row[name_col[0]]).strip()
                if horse_name == '' or 'NaN' in horse_name or '馬名' in horse_name:
                    continue
                horse_name = re.sub(r'\(.*?\)', '', horse_name).strip() # 去除 (C123) 這種馬匹編號
                
                # 提取檔位
                draw_val = str(row[draw_col[0]]) if draw_col else "1"
                draw = int(float(draw_val)) if draw_val.replace('.0','').isdigit() else 1
                
                # 提取實際負磅
                weight_val = str(row[weight_col[0]]) if weight_col else "120"
                weight = int(float(weight_val)) if weight_val.replace('.0','').isdigit() else 120
                
                # 提取名次 (賽果已有真實名次)
                rank_val = str(row[rank_col[0]]).strip() if rank_col else "99"
                if rank_val.isdigit():
                    actual_rank = int(rank_val)
                elif '平頭' in rank_val: # 處理平頭馬情況，例如 "1 平頭"
                    actual_rank = int(re.search(r'\d+', rank_val).group())
                else:
                    actual_rank = np.nan # 可能是 跌倒、退出 等非數字狀況
                
                # 提取完賽時間並轉換為總秒數 (例如 1:21.40 -> 81.40 秒)
                finish_seconds = 0.0
                if time_col:
                    time_str = str(row[time_col[0]]).strip()
                    time_match = re.match(r'(\d+):(\d+\.\d+)', time_str)
                    if time_match:
                        minutes = int(time_match.group(1))
                        seconds = float(time_match.group(2))
                        finish_seconds = minutes * 60 + seconds
                    elif re.match(r'\d+\.\d+', time_str):
                        finish_seconds = float(time_str)

                # 基準歷史平均秒數 (可依你原本邏輯保留或稍後自行計算填入)
                past_avg_seconds = 107.50
                
                # 只要名次不是 NaN（代表有順利完賽跑出時間）就寫入
                if not pd.isna(actual_rank):
                    all_real_races.append({
                        'race_date': formatted_date_db,
                        'race_no': race_no,
                        'actual_rank': int(actual_rank),
                        'horse_name': horse_name,
                        'draw': draw,
                        'weight': weight,
                        'finish_seconds': finish_seconds,
                        'past_avg_seconds': past_avg_seconds
                    })
            except Exception as row_err:
                # print(f"列解析跳過: {row_err}")
                continue
                
        print(f" ✅ 成功解碼該場馬匹數據！")
        time.sleep(1.5) # 禮貌延時
        
    except Exception as e:
        print(f" ❌ 發生錯誤: {e}")

if all_real_races:
    today_scraped_data = pd.DataFrame(all_real_races)
    # 確保寫入資料庫前，將原本是 numpy/float 的欄位轉回 Python 原生型態
    today_scraped_data['actual_rank'] = today_scraped_data['actual_rank'].astype(int)
    
    print(f"\n🎉 真實全日數據爬取完畢！共 {len(today_scraped_data)} 筆馬匹數據。")
    
    print("\n" + "="*50 + "\n")
    print("=== 📥 3. 自動寫入 SQLite 資料庫 ===")
    
    insert_sql = '''
        INSERT OR REPLACE INTO race_results (
            race_date, race_no, actual_rank, horse_name, draw, weight, finish_seconds, past_avg_seconds
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    '''
    
    # 轉換成 tuple 列表準備寫入
    data_tuples = [tuple(x) for x in today_scraped_data.to_numpy()]
    
    try:
        cursor.executemany(insert_sql, data_tuples)
        conn.commit()
        print("🎉 成功將馬會【網頁版真實數據】同步至資料庫！")
    except Exception as e:
        print(f"❌ 寫入資料庫失敗: {e}")
else:
    print("\n❌ 未能成功解析網頁。")

conn.close()