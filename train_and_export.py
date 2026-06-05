import pandas as pd
import xgboost as xgb
import numpy as np

print("=== 📦 1. 載入並準備歷史數據 (升級特徵工程) ===")
# 模擬包含「場次 (race_id)」與「真實名次 (rank)」的完整歷史數據
# 實戰中用：history_df = pd.read_sql_query("SELECT * FROM race_results ORDER BY race_id", conn)
history_df = pd.DataFrame({
    'race_id': [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],                             # 新增：場次 ID
    'horse_name': ['馬A', '馬B', '馬C', '馬D', '馬E', '馬F', '馬G', '馬H', '馬I', '馬J'],
    'draw': [3, 12, 5, 1, 8, 2, 11, 4, 9, 6],                             
    'weight': [120, 133, 115, 122, 128, 120, 133, 115, 122, 128],                       
    'past_avg_seconds': [107.2, 109.5, 106.8, 108.1, 108.9, 107.0, 109.1, 106.5, 108.0, 108.5],               
    'finish_seconds': [107.10, 109.45, 106.90, 108.05, 108.95, 107.15, 109.30, 106.40, 108.15, 108.40],
    'actual_rank': [2, 5, 1, 3, 4, 2, 5, 1, 3, 4]                          # 新增：真實完賽名次 (Ranker 用)
})

# 💡 【核心修改】特徵工程：計算相對於「同場對手」的優勢
# 使用 groupby 計算每場比賽的平均值
race_means = history_df.groupby('race_id')[['weight', 'past_avg_seconds']].transform('mean')

# 衍生新特徵：負磅比同場平均輕多少？歷史秒數比同場平均快多少？
history_df['weight_vs_average'] = history_df['weight'] - race_means['weight']
history_df['speed_vs_average'] = history_df['past_avg_seconds'] - race_means['past_avg_seconds']

# 確保數據按 race_id 排序（XGBRanker 的嚴格要求）
history_df = history_df.sort_values(by='race_id').reset_index(drop=True)

# 定義特徵群 (X)
# 我們淘汰了絕對數值，改用「檔位」以及「相對優勢特徵」
feature_names = ['draw', 'weight_vs_average', 'speed_vs_average']
X = history_df[feature_names]

# 定義標籤 (y)
# XGBRanker 的標籤通常是「越小越好」的名次，或者「越大越好」的得分。
# 這裡直接用真實名次 (1, 2, 3...)。注意：名次越小代表越好，XGBRanker 預測分數越低代表排名越前。
y = history_df['actual_rank']

# 💡 【核心修改】計算群組大小 (Groups)
# XGBRanker 需要知道每場比賽有多少匹馬參與
# 例如：第一場 5 匹馬，第二場 5 匹馬 -> groups = [5, 5]
groups = history_df.groupby('race_id').size().to_list()

print("=== 🤖 2. 訓練強化的 XGBoost 排序模型 (XGBRanker) ===")
# 建立 XGBRanker 模型（專門用來做賽馬排序）
model = xgb.XGBRanker(
    objective="rank:pairwise",  # 配對排序演算法，學習「馬 A 是否比馬 B 強」
    n_estimators=100, 
    learning_rate=0.05, 
    max_depth=5, 
    random_state=42
)

# 訓練模型，必須傳入 group 參數
model.fit(X, y, group=groups)
print("模型訓練完成！")

print("=== 💾 3. 匯出模型檔案 ===")
model.save_model("xgb_racing_model.json")
print("🎉 成功導出新型排序模型檔案：xgb_racing_model.json")