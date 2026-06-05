import os
# ✨ 強制設定環境變數，限制 OpenBLAS 與 MKL 只使用單線程運作，防止記憶體分配崩潰
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"

import streamlit as st
import pandas as pd
import sqlite3
import xgboost as xgb
import numpy as np

# 1. 網頁基本配置
st.set_page_config(page_title="AI 賽馬預測平台 (完全體)", page_icon="🏇", layout="wide")
st.title("🏇 AI 智能賽馬預測平台 (真實模型版)")
st.markdown("本網頁已成功串接 **SQLite 歷史資料庫** 與 **XGBoost 預測大腦**，實現全自動特徵增強與即時完賽秒數預測。")
st.divider()

# 2. 安全加載 XGBoost 模型檔案
@st.cache_resource 
def load_xgboost_model():
    # 💡 【核心修改】：這裡必須改成 XGBRanker()，才能成功讀取你的新型模型
    model = xgb.XGBRanker()
    
    import os
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "xgb_racing_model.json")
    model.load_model(model_path)
    return model

# 初始化變數，防止後續報 NameError
real_model = None

try:
    real_model = load_xgboost_model()
    st.sidebar.success("🚀 XGBoost 核心排序模型加載成功！")
except Exception as e:
    st.sidebar.error(f"❌ 模型加載失敗，請先運行 train_and_export.py: {e}")

# 3. 側邊欄：從真實資料庫中讀取可選的日期
st.sidebar.header("📅 賽事動態選擇")

try:
    # 建立資料庫連線
    conn = sqlite3.connect('racing_platform.db')
    
    # 撈取資料庫中所有不重複的日期，讓用戶選擇
    available_dates = pd.read_sql_query("SELECT DISTINCT race_date FROM race_results ORDER BY race_date DESC", conn)
    
    if not available_dates.empty:
        selected_date = st.sidebar.selectbox("選擇賽事日期", available_dates['race_date'].tolist())
    else:
        # 如果資料庫是空的，給予預設值避免崩潰
        selected_date = st.sidebar.selectbox("選擇賽事日期", ["2026/06/03"])
        
    selected_race = st.sidebar.slider("選擇場次", min_value=1, max_value=11, value=1)
except Exception as e:
    st.sidebar.warning(f"資料庫讀取異常，切換至模擬模式: {e}")
    selected_date = "2026/06/03"
    selected_race = 1

# 4. 【核心】從資料庫動態撈取當天數據，並現場做特徵工程
@st.cache_data
def get_live_predictions(date, race_no):
    try:
        conn = sqlite3.connect('racing_platform.db')
        
        # 💡 撈取當天這場比賽的所有馬匹
        query = f"SELECT * FROM race_results WHERE race_date = '{date}' AND race_no = {race_no}"
        current_race = pd.read_sql_query(query, conn)
        
        # 檢查點：確保下面這段 if 區塊，比 try 再向右縮進 4 個空格
        if not current_race.empty:
            # 現場計算這場比賽的相對特徵（新加入的 XGBRanker 特徵）
            mean_weight = current_race['weight'].mean()
            mean_speed = current_race['past_avg_seconds'].mean()
            
            current_race['weight_vs_average'] = current_race['weight'] - mean_weight
            current_race['speed_vs_average'] = current_race['past_avg_seconds'] - mean_speed
            
        conn.close()
        return current_race  # 確保這行在 try 裡面
        
    except Exception as e:
        # 如果出錯，回傳空表避免崩潰
        return pd.DataFrame()

# 執行資料讀取
race_df = get_live_predictions(selected_date, selected_race)

# 5. 判斷是否有資料並進行預測
if not race_df.empty:
    if real_model is None:
        st.error("🧠 AI 預測大腦尚未就緒（模型檔案載入失敗）。")
        st.stop()
        
    st.subheader(f"📊 正在檢視：{selected_date} ── 第 {selected_race} 場 賽事預測")
    
    # 💡 確保特徵欄位與你新版訓練模型完全一致
    # 如果你新版訓練用了相對特徵，請確保這裡有 ['draw', 'weight_vs_average', 'speed_vs_average']
    # 如果你只是先測試，請對齊你 train_and_export.py 的特徵
    feature_cols = ['draw', 'weight_vs_average', 'speed_vs_average']
    
    # 檢查欄位是否存在，如果不存在就現場補算
    if 'weight_vs_average' not in race_df.columns:
        race_df['weight_vs_average'] = race_df['weight'] - race_df['weight'].mean()
    if 'speed_vs_average' not in race_df.columns:
        race_df['speed_vs_average'] = race_df['past_avg_seconds'] - race_df['past_avg_seconds'].mean()

    features = race_df[feature_cols]
    
    # 讓 AI Ranker 大腦預測這場比賽的分數
    race_df['AI_Score'] = real_model.predict(features)
    
    # 💡 排序與美化展示：XGBRanker 分數越低，排名越前
    predict_result = race_df.sort_values(by='AI_Score').reset_index(drop=True)
    predict_result.insert(0, 'AI 推薦名次', range(1, len(predict_result) + 1))
    
    # 欄位中文化展示
    predict_result = predict_result.rename(columns={
        'horse_name': '馬名',
        'draw': '檔位',
        'weight': '實際負磅',
        'past_avg_seconds': '歷史平均秒數'
    })
    
    # 呈現前三名卡片
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(label="🥇 AI 首選獨贏", value=predict_result.loc[0, '馬名'], delta="最具勝出邊緣")
    with col2:
        st.metric(label="🥈 次選位置", value=predict_result.loc[1, '馬名'], delta="威脅力強")
    with col3:
        st.metric(label="🥉 三選位置", value=predict_result.loc[2, '馬名'], delta="可作配腳")
        
    # 顯示高亮數據表格
    st.markdown("### 📋 完整 AI 評分與預測數據表")
    def highlight_top3(val):
        if val == 1: return 'background-color: #FFD700; color: black; font-weight: bold;'
        elif val == 2: return 'background-color: #C0C0C0; color: black; font-weight: bold;'
        elif val == 3: return 'background-color: #CD7F32; color: black; font-weight: bold;'
        return ''
        
    st.dataframe(predict_result[['AI 推薦名次', '馬名', '檔位', '實際負磅', 'AI_Score']].style.map(highlight_top3, subset=['AI 推薦名次']), width='stretch')

else:
    st.warning(f"😢 資料庫中目前沒有 {selected_date} 第 {selected_race} 場的歷史賽果數據。")
    st.info("💡 建議：請先執行 `auto_pipeline.py` 將當天數據寫入資料庫，網頁平台就會立刻更新顯現！")