import pandas as pd
import numpy as np

print("=== 1. 載入多場賽事的歷史大表 ===")
# 模擬一個累積了多個賽事日、多場比賽的歷史數據庫
# 注意：這裡的資料必須依照「日期」由舊到新排序，AI 才能正確計算歷史走勢
history_data = pd.DataFrame({
    '賽事日期': ['2023/12/01', '2023/12/01', '2023/12/15', '2023/12/15', '2024/01/01', '2024/01/01'],
    '場次': [1, 1, 3, 3, 1, 1],
    '馬名': ['光年八十', '快狠準', '光年八十', '快狠準', '光年八十', '快狠準'],
    '檔位': [5, 12, 3, 8, 1, 6],
    '名次': [4, 8, 2, 5, 1, 2],              # 真實名次
    'finish_seconds': [71.20, 72.50, 70.50, 71.10, 69.80, 70.02] # 清洗後的完賽秒數
})
print(history_data)

print("\n" + "="*50 + "\n")
print("=== 2. 開始計算每匹馬的滾動歷史特徵 ===")

# 為了確保計算正確，先按馬名和日期排序
df = history_data.sort_values(by=['馬名', '賽事日期']).reset_index(drop=True)

# 【核心邏輯】
# groupby('馬名'): 把每一匹馬分組
# shift(1): 關鍵！將數據下移一行。因為在預測今天這場比賽時，我們只能知道牠「過去」的成績，絕對不能包含今天的成績！
# rolling(window=2, min_periods=1): 設定計算過去最多2場的滾動視窗（這裡因為模擬數據少，用2場示範；真實實戰通常用3-5場）
# mean(): 計算平均值

df['過去_avg_名次'] = df.groupby('馬名')['名次'].transform(lambda x: x.shift(1).rolling(window=2, min_periods=1).mean())
df['過去_avg_秒數'] = df.groupby('馬名')['finish_seconds'].transform(lambda x: x.shift(1).rolling(window=2, min_periods=1).mean())

# 再把排序梳理回原本按日期排列的樣子方便檢視
df = df.sort_values(by=['賽事日期', '場次']).reset_index(drop=True)

print(df)