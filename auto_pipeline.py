import sqlite3
import pandas as pd
import numpy as np
import requests
import os
import time
import re
import io

print("=== 🗄️ 1. 初始化 SQLite 資料庫 ===")
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'racing_platform.db')
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# === 🗄️ 1. 初始化 SQLite 資料庫 ===
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
        jockey TEXT,          -- 💡 新增：騎師
        trainer TEXT,         -- 💡 新增：練馬師
        rating_change INTEGER, -- 💡 新增：評分變動 (+/-)
        body_weight INTEGER,   -- 💡 新增：排位體重
        recent_form TEXT,     -- 💡 新增：6次近績 (字串，如 1/5/2/2/5/9)
        PRIMARY KEY (race_date, race_no, horse_name)
    )
''')
conn.commit()

print("資料庫結構就緒！")

print("\n" + "="*50 + "\n")
print("=== 🌐 2. 開始從香港賽馬會網頁爬取【完整排位表】 ===")

target_date = "2026-06-07" 
formatted_date_db = target_date.replace("-", "/") 
url_date = target_date.replace("-", "/")          

all_card_races = []

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
}

# 偵測正確的網址格式 (優先測試標準版)
valid_date_param = None
print("🔍 正在自動探測馬會伺服器的網址日期格式...")

for fmt in [f"{target_date.split('-')[0]}/{target_date.split('-')[1]}/{target_date.split('-')[2]}"]:
    test_url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={fmt}&RaceNo=1"
    try:
        res = requests.get(test_url, headers=headers, timeout=10)
        if res.status_code == 200 and "沒有有關賽事紀錄" not in res.text:
            valid_date_param = fmt
            print(f" 🎯 成功捕獲標準版網址格式！可用參數為: RaceDate={fmt}")
            break
    except:
        continue

if valid_date_param is None:
    print("\n❌ 偵測失敗：未能獲取網頁。請確認排位表是否已釋出。")
    conn.close()
    exit()

# 開始爬取 1 ~ 11 場
for race_no in range(1, 12):
    print(f"正在下載第 {race_no} 場【排位表】...", end="")
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/RaceCard.aspx?RaceDate={valid_date_param}&RaceNo={race_no}"
        
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'utf-8'
        
        if response.status_code != 200 or "沒有有關賽事紀錄" in response.text:
            print(" ⚠️ 無此場次，停止搜尋。")
            break
            
        tables = pd.read_html(io.StringIO(response.text))
        
        potential_rows = []
        
        for t in tables:
            if isinstance(t.columns, pd.MultiIndex):
                t.columns = ['_'.join(col).strip() for col in t.columns]
            else:
                t.columns = [str(col).strip() for col in t.columns]
                
            cols_str = "".join(t.columns)
            
            # 偵測是否為主排位表
            if '馬名' in cols_str or '馬 名' in cols_str:
                cols = list(t.columns)
                name_idx = next((i for i, c in enumerate(cols) if '馬名' in c or '馬 名' in c), None)
                draw_idx = next((i for i, c in enumerate(cols) if '檔位' in c or '檔 位' in c), None)
                weight_idx = next((i for i, c in enumerate(cols) if '負磅' in c or '負 磅' in c), None)
                
                # 💡 動態偵測新欄位索引
                jockey_idx = next((i for i, c in enumerate(cols) if '騎師' in c or '騎 師' in c), None)
                trainer_idx = next((i for i, c in enumerate(cols) if '練馬師' in c or '練馬' in c), None)
                rating_idx = next((i for i, c in enumerate(cols) if '評分+/-' in c or '評分 +/-' in c), None)
                bweight_idx = next((i for i, c in enumerate(cols) if '排位體重' in c or '體重' in c), None)
                form_idx = next((i for i, c in enumerate(cols) if '6次近績' in c or '近績' in c), None)
                
                if name_idx is not None:
                    for _, row in t.iterrows():
                        try:
                            h_name = str(row.iloc[name_idx]).strip()
                            
                            # 【精準過濾】排除空行、標頭、以及後備/退出馬匹的提示字
                            if h_name in ['', 'NaN', 'nan', '馬名', '馬 名'] or '後備' in h_name or '退出' in h_name:
                                continue
                            
                            # 清洗馬名
                            h_name = re.sub(r'^\d+', '', h_name) 
                            h_name = re.sub(r'\(.*?\)', '', h_name).strip() 
                            h_name = re.sub(r'\[.*?\]', '', h_name).strip() 
                            
                            if len(h_name) < 2 or h_name.isdigit(): 
                                continue
                                
                            # 檔位與負磅提取
                            d_val = str(row.iloc[draw_idx]).strip() if draw_idx is not None else ""
                            if d_val in ['', 'NaN', 'nan', '---'] or '後備' in d_val:
                                continue
                            draw = int(float(d_val)) if d_val.replace('.0','').isdigit() else None
                            if draw is None: continue 
                            
                            w_val = str(row.iloc[weight_idx]).strip() if weight_idx is not None else "120"
                            weight = int(float(w_val)) if w_val.replace('.0','').isdigit() else 120
                            
                            # 💡 安全提取新欄位數據（移至變數定義之後）
                            jockey_val = str(row.iloc[jockey_idx]).strip() if jockey_idx is not None else ""
                            jockey_val = re.sub(r'\(.*?\)', '', jockey_val).strip() # 移除減磅標記如 (-10)

                            trainer_val = str(row.iloc[trainer_idx]).strip() if trainer_idx is not None else ""

                            r_change = str(row.iloc[rating_idx]).strip() if rating_idx is not None else "0"
                            rating_change = int(r_change) if r_change.replace('-','').replace('+','').isdigit() else 0

                            b_w = str(row.iloc[bweight_idx]).strip() if bweight_idx is not None else "1100"
                            body_weight = int(b_w) if b_w.isdigit() else 1100

                            form_val = str(row.iloc[form_idx]).strip() if form_idx is not None else ""

                            # 統一打包儲存
                            potential_rows.append({
                                'race_date': formatted_date_db,
                                'race_no': race_no,
                                'actual_rank': np.nan,
                                'horse_name': h_name,
                                'draw': draw,
                                'weight': weight,
                                'finish_seconds': 0.0,
                                'past_avg_seconds': 107.50,
                                'jockey': jockey_val,          
                                'trainer': trainer_val,        
                                'rating_change': rating_change,
                                'body_weight': body_weight,    
                                'recent_form': form_val        
                            })
                        except Exception as row_e:
                            continue
                            
                # 抓完真正的正選排位表後，立刻跳出
                if len(potential_rows) > 0:
                    break

        # 移除重複抓到的馬匹
        seen_horses = set()
        unique_race_rows = []
        for r in potential_rows:
            if r['horse_name'] not in seen_horses:
                seen_horses.add(r['horse_name'])
                unique_race_rows.append(r)
                
        race_count = len(unique_race_rows)
        all_card_races.extend(unique_race_rows)
        
        if race_count > 0:
            print(f" ✅ 成功完整解碼 {race_count} 匹參賽馬！")
        else:
            print(" ❌ 未能撈出任何馬匹。")
            
        time.sleep(1.0)
        
    except Exception as e:
        print(f" ❌ 錯誤: {e}")

if all_card_races:
    today_scraped_data = pd.DataFrame(all_card_races)
    print(f"\n🎉 數據全數爬取完畢！全日共捕獲 {len(today_scraped_data)} 筆不重複馬匹數據。")
    
    print("\n" + "="*50 + "\n")
    print("=== 📥 3. 自動寫入 SQLite 資料庫 ===")
    
    insert_sql = '''
        INSERT OR REPLACE INTO race_results (
            race_date, race_no, actual_rank, horse_name, draw, weight, finish_seconds, past_avg_seconds,
            jockey, trainer, rating_change, body_weight, recent_form
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''

    data_tuples = []
    for _, row in today_scraped_data.iterrows():
        data_tuples.append((
            row['race_date'],
            int(row['race_no']),
            None if pd.isna(row['actual_rank']) else int(row['actual_rank']),
            row['horse_name'],
            int(row['draw']),
            int(row['weight']),
            float(row['finish_seconds']),
            float(row['past_avg_seconds']),
            row['jockey'],
            row['trainer'],
            int(row['rating_change']),
            int(row['body_weight']),
            row['recent_form']
        ))
    
    try:
        cursor.executemany(insert_sql, data_tuples)
        conn.commit()
        print(f"🎉 資料庫完美同步！這次 {len(data_tuples)} 筆馬匹的新欄位數據全部成功進去了！")
    except Exception as e:
        print(f"❌ 寫入失敗: {e}")
else:
    print("\n❌ 最終未成功解碼任何數據。")

conn.close()