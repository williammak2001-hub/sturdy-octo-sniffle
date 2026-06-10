import pandas as pd
import xgboost as xgb
import numpy as np

print("=== 📦 1. 載入並準備歷史數據 (完全體 8 特徵大腦升級) ===")

# 💡 在模擬的歷史庫中直接加入這些新特徵，讓新大腦順利擁有 8 個輸入特徵的記憶
history_df = pd.DataFrame({
    'race_id': [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],                             
    'horse_name': ['馬A', '馬B', '馬C', '馬D', '馬E', '馬F', '馬G', '馬H', '馬I', '馬J'],
    'draw': [3, 12, 5, 1, 8, 2, 11, 4, 9, 6],                             
    'weight': [120, 133, 115, 122, 128, 120, 133, 115, 122, 128],                       
    'past_avg_seconds': [107.2, 109.5, 106.8, 108.1, 108.9, 107.0, 109.1, 106.5, 108.0, 108.5],               
    'rating_change': [6, -3, -1, 0, -2, -1, -2, -3, -1, -2],   
    'body_weight': [1096, 1130, 1109, 1152, 1201, 1053, 1064, 1209, 1167, 1125], 
    'recent_avg_rank': [2.3, 11.3, 6.0, 2.3, 8.6, 6.0, 9.6, 10.6, 7.3, 6.3],      
    'jockey_win_rate': [0.12, 0.05, 0.15, 0.11, 0.09, 0.04, 0.06, 0.08, 0.05, 0.10], 
    'trainer_win_rate': [0.14, 0.08, 0.11, 0.07, 0.05, 0.08, 0.06, 0.09, 0.05, 0.12], 
    'actual_rank': [2, 5, 1, 3, 4, 2, 5, 1, 3, 4]                          
})

# 特徵工程：計算相對於「同場對手」的相對優勢
race_means = history_df.groupby('race_id')[['weight', 'past_avg_seconds']].transform('mean')
history_df['weight_vs_average'] = history_df['weight'] - race_means['weight']
history_df['speed_vs_average'] = history_df['past_avg_seconds'] - race_means['past_avg_seconds']

# 確保數據按 race_id 嚴格排序
history_df = history_df.sort_values(by='race_id').reset_index(drop=True)

# 💡 【終極修正】特徵列表和順序，必須與網頁端 app.py 的特徵陣列完美對齊！
feature_names = [
    'draw', 'weight_vs_average', 'speed_vs_average',
    'rating_change', 'body_weight', 'recent_avg_rank', 
    'jockey_win_rate', 'trainer_win_rate'
]

X = history_df[feature_names]
y = history_df['actual_rank']
groups = history_df.groupby('race_id').size().to_list()

print("=== 🤖 2. 訓練強化的 XGBoost 排序模型 (XGBRanker) ===")
model = xgb.XGBRanker(
    objective="rank:pairwise",  
    n_estimators=100, 
    learning_rate=0.05, 
    max_depth=5, 
    random_state=42
)

model.fit(X, y, group=groups)
print("模型訓練完成！")

print("=== 💾 3. 匯出模型檔案 ===")
model.save_model("xgb_racing_model.json")
print("🎉 8維度完全體大腦已成功導出：xgb_racing_model.json")
