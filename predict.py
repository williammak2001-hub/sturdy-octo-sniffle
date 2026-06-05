import pandas as pd
import numpy as np

print("--- 1. 開始測試 Python 程式碼 ---")

# 建立原始資料
data = pd.DataFrame({
    'horse_id': ['H001', 'H002', 'H003'],
    'track_condition': ['Good', 'Yielding', 'Good'], 
    'draw': [3, 12, 5],                             
    'weight': [120, 133, 115],                       
    'past_avg_rank': [2.3, 5.1, 1.8],               
    'finish_time_sec': [82.4, 84.1, 81.9]            
})

# 特徵工程
data = pd.get_dummies(data, columns=['track_condition'])
data['weight_efficiency'] = data['past_avg_rank'] / data['weight']

print("\n--- 2. 資料轉換成功！ ---")
print(data)