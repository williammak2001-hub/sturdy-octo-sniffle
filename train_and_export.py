import pandas as pd
import xgboost as xgb
import numpy as np
import sqlite3
import os

print("=== 📦 1. 載入並準備真實歷史數據 (SQLite 連接版) ===")

# 💡 1. 建立與本地 SQLite 資料庫的連接
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'racing_platform.db')
conn = sqlite3.connect(db_path)

# 💡 2. 核心 SQL 革命：只撈取「已經完賽、且有真實名次 (actual_rank)」的優質數據來給 AI 當教科書
# 這裡排除掉還沒開跑、actual_rank 還是空值 (NaN) 的未來排位表
query = """
    SELECT * FROM race_results 
    WHERE actual_rank IS NOT NULL 
    ORDER BY race_date, race_no
"""
history_df = pd.read_sql_query(query, conn)
conn.close()

# 💡 3. 安全檢查：確保資料庫裡已經有足夠的歷史賽果
if len(history_df) < 5:
    print("\n❌ 錯誤：目前資料庫中的真實完賽數據太少（少於 5 筆）！")
    print("💡 請先確保你運行過真實賽果爬蟲，或者資料庫內已有跑完的比賽紀錄。")
    exit()

print(f"📈 成功從 SQLite 載入 {len(history_df)} 筆真實歷史完賽記錄！正在現場進行大數據特徵工程...")

# 💡 4. 為了配合 XGBRanker 的分場訓練，我們將 race_date + race_no 組合成一個唯一的場次編號 (race_id)
history_df['race_id'] = history_df.groupby(['race_date', 'race_no']).ngroup()

# 💡 5. 特徵工程：計算每匹馬相對於「當天同場對手」的相對優勢
race_means = history_df.groupby('race_id')[['weight', 'past_avg_seconds']].transform('mean')
history_df['weight_vs_average'] = history_df['weight'] - race_means['weight']
history_df['speed_vs_average'] = history_df['past_avg_seconds'] - race_means['past_avg_seconds']

# 💡 6. 轉化近績：將字串近績（如 1/2/4/11）轉化為近三場平均名次的純數字
def calculate_recent_rank_mean(form_str):
    if not form_str or pd.isna(form_str) or form_str in ['---', '']:
        return 6.0
    import re
    ranks = [int(s) for s in str(form_str).split('/') if s.isdigit()]
    if not ranks:
        return 6.0
    return float(np.mean(ranks[:3]))

history_df['recent_avg_rank'] = history_df['recent_form'].apply(calculate_recent_rank_mean)

# 💡 7. 騎師與練馬師歷史勝率 (Target Encoding)
# 計算該騎師/練馬師在歷史數據中拿第一名 (actual_rank == 1) 的比例
history_df['jockey_win_rate'] = history_df.groupby('jockey')['actual_rank'].transform(lambda x: (x == 1).mean())
history_df['trainer_win_rate'] = history_df.groupby('trainer')['actual_rank'].transform(lambda x: (x == 1).mean())

# 補齊新馬或歷史資料較少者缺失的勝率預設值（大眾平均勝率約 8%）
history_df['jockey_win_rate'] = history_df['jockey_win_rate'].fillna(0.08)
history_df['trainer_win_rate'] = history_df['trainer_win_rate'].fillna(0.08)

# 💡 8. 確保數據按 race_id 嚴格排序（XGBRanker 的硬性規範）
history_df = history_df.sort_values(by='race_id').reset_index(drop=True)

# 💡 9. 定義 8 維度黃金預測特徵（欄位與順序必須與網頁端 app.py 完美對齊）
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
print("模型實戰優化訓練完成！")

print("=== 💾 3. 匯出實戰模型檔案 ===")
model.save_model("xgb_racing_model.json")
print("🎉 真實歷史大數據模型已成功導出覆蓋：xgb_racing_model.json")
