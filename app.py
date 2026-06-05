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
    model = xgb.XGBRegressor()
    model.load_model("xgb_racing_model.json")
    return model

try:
    real_model = load_xgboost_model()
    st.sidebar.success("🚀 XGBoost 核心模型加載成功！")
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
# ... 撈出 current_race 後 ...
if not current_race.empty:
    # 現場計算這場比賽的相對特徵
    mean_weight = current_race['weight'].mean()
    mean_speed = current_race['past_avg_seconds'].mean()
    
    current_race['weight_vs_average'] = current_race['weight'] - mean_weight
    current_race['speed_vs_average'] = current_race['past_avg_seconds'] - mean_speed
    return current_race

    try:
        conn = sqlite3.connect('racing_platform.db')
        
        # 💡 實戰策略：撈取當天這場比賽的所有馬匹
        query = f"SELECT * FROM race_results WHERE race_date = '{date}' AND race_no = {race_no}"
        current_race = pd.read_sql_query(query, conn)
        
        if current_race.empty:
            # 防呆機制：如果資料庫查無此場，回傳空表
            return pd.DataFrame()
            
        # 💡 特徵工程：現場計算這匹馬在歷史大表裡的平均秒數
        # 在這裡為了示範，如果資料庫剛建立、歷史數據不夠，我們自動填入基準值，實戰中會用前幾次跑的平均
        if 'past_avg_seconds' not in current_race.columns:
            current_race['past_avg_seconds'] = current_race['finish_seconds'].fillna(107.50)
            
        conn.close()
        return current_race
    except:
        return pd.DataFrame()

# 執行資料讀取
race_df = get_live_predictions(selected_date, selected_race)

# 5. 判斷是否有資料並進行預測
if not race_df.empty:
    # 欄位必須跟訓練時完全一致
    features = race_df[['draw', 'weight_vs_average', 'speed_vs_average']]
    
    # XGBRanker 預測出來的是「排序分數」，分數越低（或越小）名次越前
    race_df['AI_Score'] = real_model.predict(features)
    
    # 💡 核心修改：改用 AI_Score 由小到大排序
    predict_result = race_df.sort_values(by='AI_Score').reset_index(drop=True)
    predict_result.insert(0, 'AI 推薦名次', range(1, len(predict_result) + 1))

    st.subheader(f"📊 正在檢視：{selected_date} ── 第 {selected_race} 場 賽事預測")
    
    # 確保特徵欄位名稱與順序和 XGBoost 完全一致
    # 訓練時用的英文：['draw', 'weight', 'past_avg_seconds']
    features = race_df[['draw', 'weight', 'past_avg_seconds']]
    
    # 讓 AI 大腦預測這場比賽
    race_df['AI 預測秒數'] = real_model.predict(features)
    
    # 排序與美化展示
    predict_result = race_df.sort_values(by='AI 預測秒數').reset_index(drop=True)
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
        st.metric(label="🥇 AI 首選獨贏", value=predict_result.loc[0, '馬名'], delta=f"{predict_result.loc[0, 'AI 預測秒數']:.2f} 秒")
    with col2:
        st.metric(label="🥈 次選位置", value=predict_result.loc[1, '馬名'], delta=f"{predict_result.loc[1, 'AI 預測秒數']:.2f} 秒")
    with col3:
        st.metric(label="🥉 三選位置", value=predict_result.loc[2, '馬名'], delta=f"{predict_result.loc[2, 'AI 預測秒數']:.2f} 秒")
        
    # 顯示高亮數據表格
    st.markdown("### 📋 完整 AI 評分與預測數據表")
    def highlight_top3(val):
        if val == 1: return 'background-color: #FFD700; color: black; font-weight: bold;'
        elif val == 2: return 'background-color: #C0C0C0; color: black; font-weight: bold;'
        elif val == 3: return 'background-color: #CD7F32; color: black; font-weight: bold;'
        return ''
        
    st.dataframe(predict_result[['AI 推薦名次', '馬名', '檔位', '實際負磅', 'AI 預測秒數']].style.map(highlight_top3, subset=['AI 推薦名次']), width='stretch')

else:
    st.warning(f"😢 資料庫中目前沒有 {selected_date} 第 {selected_race} 場的歷史賽果數據。")
    st.info("💡 建議：請先執行 `hkjc_auto_pipeline.py` 將當天數據寫入資料庫，網頁平台就會立刻更新顯現！")