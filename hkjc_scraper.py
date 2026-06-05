import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 使用 2024年1月1日 第一場作為測試
url = "https://racing.hkjc.com/racing/information/Chinese/Racing/LocalResults.aspx?RaceDate=2024/01/01&RaceNo=1"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

print(f"正在重新請求網頁: {url}")

try:
    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = 'utf-8'
    
    if response.status_code == 200:
        print("網頁下載成功！開始進階解析...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 【修正點】馬會的賽果主表格通常帶有 'table_bd' 這個 class
        # 我們直接尋找所有包含 'table_bd' 的表格
        tables = soup.find_all('table', class_='table_bd')
        
        results_table = None
        for t in tables:
            # 檢查這個表格的第一行是不是包含「名次」或「馬名」，確認它是我們要的賽果表
            if '名次' in t.text or '馬名' in t.text:
                results_table = t
                break
                
        if results_table:
            rows = results_table.find_all('tr')
            all_horses = []
            
            for row in rows:
                cols = row.find_all('td')
                # 馬會標準賽果表格一行通常有 12 個欄位以上
                if len(cols) >= 10: 
                    try:
                        rank = cols[0].text.strip()        # 名次
                        horse_no = cols[1].text.strip()    # 馬號
                        horse_name = cols[2].text.strip()  # 馬名/微調去除英文字母
                        jockey = cols[3].text.strip()      # 騎師
                        trainer = cols[4].text.strip()     # 練馬師
                        weight = cols[5].text.strip()      # 實際負磅
                        draw = cols[7].text.strip()        # 檔位
                        finish_time = cols[10].text.strip()# 完賽時間
                        
                        # 過濾掉表頭文字行（確保名次是數字，或是特殊狀況如 DISQ/DH）
                        if rank.isdigit() or rank in ['WX', 'WX-A', 'A', 'DISQ', 'D']:
                            all_horses.append({
                                '名次': rank,
                                '馬號': horse_no,
                                '馬名': horse_name.split('(')[0], # 只拿中文名
                                '騎師': jockey,
                                '練馬師': trainer,
                                '實際負磅': weight,
                                '檔位': draw,
                                '完賽時間': finish_time
                            })
                    except Exception as e:
                        continue # 個別行數解析出錯就跳過
            
            if all_horses:
                df = pd.DataFrame(all_horses)
                print("\n🎉 成功攻破馬會網頁！抓取到以下數據：")
                print(df.to_string()) # 完整印出表格
                
                # 儲存
                df.to_csv('race_result_sample.csv', index=False, encoding='utf-8-sig')
                print("\n檔案已更新儲存至 race_result_sample.csv")
            else:
                print("❌ 找到了表格，但無法解析出馬匹資料列。")
        else:
            print("❌ 依舊找不到目標賽果表格。")
            
except Exception as e:
    print(f"❌ 發生錯誤: {e}")