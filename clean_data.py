import pandas as pd
import numpy as np

# 1. 定義一個自訂函式：將 "分:秒" 轉換為 "純秒數"
def convert_time_to_seconds(time_str):
    # 如果數據缺失 (NaN) 或是空白，直接回傳 NaN
    if pd.isna(time_str) or str(time_str).strip() == '' or time_str == '---':
        return np.nan
    
    try:
        time_str = str(time_str).strip()
        
        # 狀況 A：格式為 "1:09.80" (有分鐘)
        if ':' in time_str:
            parts = time_str.split(':')
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        
        # 狀況 B：格式為 "69.80" (本來就只有秒數)
        else:
            return float(time_str)
            
    except Exception as e:
        # 如果遇到特殊文字（例如：退出 WX, 取消資格 DISQ），無法轉成時間，回傳 NaN
        return np.nan

# 2. 模擬我們從爬蟲抓到的原始數據 (包含各種髒數據與特殊狀況)
raw_data = pd.DataFrame({
    '馬名': ['光年八十', '快狠準', '閃電俠', '幸運兒'],
    '檔位': ['1', '6', '---', '12'],            # 有些檔位可能是髒數據
    '實際負磅': ['125', '120', '133', '128'],
    '完賽時間': ['1:09.80', '1:10.02', 'WX', '1:08.45'] # WX 代表退出賽事
})

print("=== 🧼 清洗前的原始數據 ===")
print(raw_data)
print(raw_data.dtypes) # 查看目前資料型態，全部都是 object (文字)

print("\n" + "="*40 + "\n")

# 3. 開始執行數據清洗
processed_data = raw_data.copy()

# 應用時間轉換函式，創造新欄位 'finish_seconds'
processed_data['finish_seconds'] = processed_data['完賽時間'].apply(convert_time_to_seconds)

# 將其他本來就應該是數字的欄位（檔位、負磅），強制轉成數字，不行的變 NaN
processed_data['檔位'] = pd.to_numeric(processed_data['檔位'], errors='coerce')
processed_data['實際負磅'] = pd.to_numeric(processed_data['實際負磅'], errors='coerce')

print("=== ✨ 清洗後的 AI 專用數據 ===")
print(processed_data)
print(processed_data.dtypes) # 檢查型態，已經成功變成 float64 和 int64 了！

# 4. 剔除無法訓練的髒數據（例如退出的馬匹沒有完賽時間，AI 無法學習）
# dropna() 會把包含 NaN 的那一列直接刪除
final_train_data = processed_data.dropna(subset=['finish_seconds', '檔位'])

print("\n" + "="*40 + "\n")
print("=== 🚀 最終餵給 AI 訓練的乾淨數據 ===")
print(final_train_data)