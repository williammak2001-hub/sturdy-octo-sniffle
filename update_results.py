import sqlite3
import pandas as pd
import requests
import io
import re
import time

db_path = 'racing_platform.db'
target_date = "2026-06-07" 
formatted_date_db = target_date.replace("-", "/")

print(f"=== 🏆 開始同步 {target_date} 賽後真實結果 ===")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

for race_no in range(1, 12):
    print(f"正在下載第 {race_no} 場真實賽果...", end="")
    # 賽後改看 LocalResults.aspx
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={target_date}&RaceNo={race_no}"
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200 or "沒有有關賽事紀錄" in response.text:
            print(" ⚠️ 賽果尚未公佈或無此場次。")
            continue
            
        tables = pd.read_html(io.StringIO(response.text))
        race_table = None
        for t in tables:
            cols_str = "".join([str(c) for c in t.columns.get_level_values(0)])
            if '馬名' in cols_str and ('名次' in cols_str or '實際負磅' in cols_str):
                race_table = t
                break
                
        if race_table is None:
            print(" ❌ 找不到賽果表格。")
            continue
            
        if isinstance(race_table.columns, pd.MultiIndex):
            race_table.columns = ['_'.join(col).strip() for col in race_table.columns]
        else:
            race_table.columns = [str(col).strip() for col in race_table.columns]

        cols = race_table.columns
        rank_col = [c for c in cols if '名次' in c]
        name_col = [c for c in cols if '馬名' in c]
        time_col = [c for c in cols if '完成時間' in c]

        update_count = 0
        for idx, row in race_table.iterrows():
            horse_name = str(row[name_col[0]]).strip()
            if horse_name == '' or 'NaN' in horse_name or '馬名' in horse_name:
                continue
            horse_name = re.sub(r'\(.*?\)', '', horse_name).strip()
            
            # 提取名次
            rank_val = str(row[rank_col[0]]).strip() if rank_col else "99"
            actual_rank = int(re.search(r'\d+', rank_val).group()) if re.search(r'\d+', rank_val) else None
            
            # 提取完賽秒數
            finish_seconds = 0.0
            if time_col:
                time_str = str(row[time_col[0]]).strip()
                time_match = re.match(r'(\d+):(\d+\.\d+)', time_str)
                if time_match:
                    finish_seconds = int(time_match.group(1)) * 60 + float(time_match.group(2))
                elif re.match(r'\d+\.\d+', time_str):
                    finish_seconds = float(time_str)

            if actual_rank is not None:
                # 💡 只更新真實名次和完賽時間，不破壞原本排位表抓到的檔位、負磅
                cursor.execute('''
                    UPDATE race_results 
                    SET actual_rank = ?, finish_seconds = ?
                    WHERE race_date = ? AND race_no = ? AND horse_name = ?
                ''', (actual_rank, finish_seconds, formatted_date_db, race_no, horse_name))
                update_count += 1
                
        print(f" ✅ 成功更新 {update_count} 匹馬的真實賽果！")
        conn.commit()
        time.sleep(1.0)
    except Exception as e:
        print(f" ❌ 錯誤: {e}")

conn.close()
print("=== 🏁 全日賽果同步完畢！ ===")