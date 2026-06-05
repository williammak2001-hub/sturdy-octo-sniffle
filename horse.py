import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

print("--- 1. 正在初始化模擬數據 ---")
# 【核心】必須先定義 data 變數，給 AI 訓練用的歷史數據
data = pd.DataFrame({
    'horse_id': ['H001', 'H002', 'H003', 'H004', 'H005'],
    'track_condition': ['Good', 'Yielding', 'Good', 'Good', 'Yielding'], 
    'draw': [3, 12, 5, 1, 8],                             
    'weight': [120, 133, 115, 122, 128],                       
    'past_avg_rank': [2.3, 5.1, 1.8, 3.5, 4.2],               
    'finish_time_sec': [82.4, 84.1, 81.9, 83.0, 83.8] # 預測目標：完賽時間
})

print("--- 2. 進行特徵工程轉換 ---")
# 將文字標籤（Good/Yielding）轉換為數字，並創造新特徵
data = pd.get_dummies(data, columns=['track_condition'])
data['weight_efficiency'] = data['past_avg_rank'] / data['weight']

print("--- 3. 準備訓練 AI 模型 (XGBoost) ---")
# 分離特徵 (X) 與 預測目標 (y)
X = data.drop(columns=['horse_id', 'finish_time_sec'])
y = data['finish_time_sec']

# 拆分訓練集與測試集
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# 建立 XGBoost 迴歸模型
model = xgb.XGBRegressor(
    n_estimators=10, 
    learning_rate=0.05, 
    max_depth=3, 
    random_state=42
)

# 訓練模型
model.fit(X_train, y_train)

# 進行預測
predictions = model.predict(X_test)
print("\n🎉 AI 模型訓練並預測成功！")
print(f"測試集的預測完賽時間（秒）: {predictions}")