import pandas as pd
import xgboost as xgb
from sklearn.model_selection import train_test_split

print("=== 📦 1. 載入並準備歷史數據 ===")
# 這裡模擬你從資料庫拉出來的歷史乾淨數據
# 實戰中你會用 pd.read_sql_query("SELECT * FROM race_results", conn)
history_df = pd.DataFrame({
    'draw': [3, 12, 5, 1, 8, 2, 11, 4, 9, 6],                             
    'weight': [120, 133, 115, 122, 128, 120, 133, 115, 122, 128],                       
    'past_avg_seconds': [107.2, 109.5, 106.8, 108.1, 108.9, 107.0, 109.1, 106.5, 108.0, 108.5],               
    'finish_seconds': [107.10, 109.45, 106.90, 108.05, 108.95, 107.15, 109.30, 106.40, 108.15, 108.40] # 預測目標
})

# 分離特徵 (X) 與 標籤 (y)
X = history_df[['draw', 'weight', 'past_avg_seconds']]
y = history_df['finish_seconds']

print("=== 🤖 2. 訓練真實的 XGBoost 模型 ===")
# 建立 XGBoost 迴歸模型
model = xgb.XGBRegressor(
    n_estimators=50, 
    learning_rate=0.1, 
    max_depth=4, 
    random_state=42
)
model.fit(X, y)
print("模型訓練完成！")

print("=== 💾 3. 匯出模型檔案 ===")
# 將模型儲存為 XGBoost 官方推薦的 JSON 格式
model.save_model("xgb_racing_model.json")
print("🎉 成功導出模型檔案：xgb_racing_model.json")