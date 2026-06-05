import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random

# 設定你要抓取的日期和預計的場次（例如 1 到 11 場）
target_date = "2024/01/01"
total_races = 11

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

all_race_data = [] # 用來存放今天所有場次的總大表

for race_no in range(1, total_races + 1):
    url = f"https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate={target_date}&RaceNo={race_no}"
    print(f"🚀 正在抓取：第 {race_no} 場次... ", end="")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        
        if response.status_code != 200:
            print(f"❌ 失敗 (狀態碼: {response.status_code})")
            continue
            
        soup = BeautifulSoup(response.text, 'html.parser')
        tables = soup.find_all('table', class_='table_bd')
        results_table = None
        
        for t in tables:
            if '名次' in t.text or '馬名' in t.text:
                results_table = t
                break
                
        if not results_table:
            print("❌ 找不到賽果表格 (可能這場沒開跑)")
            continue
            
        # 開始解析該場次的馬匹
        rows = results_table.find_all('tr')
        horse_count_in_race = 0
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 10:
                try:
                    rank = cols[0].text.strip()
                    if rank.isdigit() or rank in ['WX', 'WX-A', 'A', 'DISQ', 'D']:
                        all_race_data.append({
                            '賽事日期': target_date,
                            '場次': race_no,
                            '名次': rank,
                            '馬號': cols[1].text.strip(),
                            '馬名': cols[2].text.strip().split('(')[0],
                            '騎師': cols[3].text.strip(),
                            '練馬師': cols[4].text.strip(),
                            '實際負磅': cols[5].text.strip(),
                            '檔位': cols[7].text.strip(),
                            '完賽時間': cols[10].text.strip()
                        })
                        horse_count_in_race += 1
                except:
                    continue
                    
        print(f"✅ 成功！抓到 {horse_count_in_race} 匹馬")
        
        # 🛡️ 關鍵安全機制：隨機休息 2 ~ 4 秒，模仿人類行為
        sleep_time = random.uniform(2, 4)
        time.sleep(sleep_time)
        
    except Exception as e:
        print(f"💥 發生網路錯誤: {e}")
        time.sleep(5)

# 全部抓完後，打包存檔
if all_race_data:
    df = pd.DataFrame(all_race_data)
    filename = f"race_results_{target_date.replace('/', '')}.csv"
    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n🎉 任務完成！已將今天共 {len(df)} 筆馬匹賽果，儲存至 {filename}")
else:
    print("\n😢 很遺憾，今天沒有抓到任何數據。")