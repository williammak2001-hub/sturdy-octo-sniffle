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
    model = xgb.XGBRanker() # 確保讀取的是新型排序模型
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
    conn = sqlite3.connect('racing_platform.db')
    available_dates = pd.read_sql_query("SELECT DISTINCT race_date FROM race_results ORDER BY race_date DESC", conn)
    
    if not available_dates.empty:
        selected_date = st.sidebar.selectbox("選擇賽事日期", available_dates['race_date'].tolist())
    else:
        selected_date = st.sidebar.selectbox("選擇賽事日期", ["2026/06/07"])
        
    selected_race = st.sidebar.slider("選擇場次", min_value=1, max_value=11, value=1)
    conn.close()
except Exception as e:
    st.sidebar.warning(f"資料庫讀取異常，切換至模擬模式: {e}")
    selected_date = "2026/06/07"
    selected_race = 1

# 💡 輔助函式：將「6次近績」轉化為「近三場平均名次」
def calculate_recent_rank_mean(form_str):
    if not form_str or pd.isna(form_str) or form_str in ['---', '']:
        return 6.0  # 沒近績的馬給予中間偏下的預設名次
    ranks = [int(s) for s in form_str.split('/') if s.isdigit()]
    if not ranks:
        return 6.0
    return float(np.mean(ranks[:3])) # 取最近三場的平均名次

# 4. 【核心】從資料庫動態撈取當天數據，並現場做特徵工程
@st.cache_data
def get_live_predictions(date, race_no):
    try:
        conn = sqlite3.connect('racing_platform.db')
        query = f"SELECT * FROM race_results WHERE race_date = '{date}' AND race_no = {race_no}"
        current_race = pd.read_sql_query(query, conn)
        
        if not current_race.empty:
            # 根據馬名去重
            current_race = current_race.drop_duplicates(subset=['horse_name'])
            
            # 1️⃣ 計算相對特徵
            mean_weight = current_race['weight'].mean()
            mean_speed = current_race['past_avg_seconds'].mean()
            current_race['weight_vs_average'] = current_race['weight'] - mean_weight
            current_race['speed_vs_average'] = current_race['past_avg_seconds'] - mean_speed
            
            # 2️⃣ 現場轉化「近三場平均名次」
            current_race['recent_avg_rank'] = current_race['recent_form'].apply(calculate_recent_rank_mean)
            
            # 3️⃣ 現場撈取並計算 騎師 / 練馬師 的歷史勝率 (Target Encoding)
            # 如果是全新的資料庫，沒有 actual_rank 歷史數據，會自動填入預設勝率 0.08
            try:
                jockey_stats = pd.read_sql_query("""
                    SELECT jockey, AVG(CASE WHEN actual_rank = 1 THEN 1.0 ELSE 0.0 END) as jockey_win_rate
                    FROM race_results WHERE actual_rank IS NOT NULL GROUP BY jockey
                """, conn)
                current_race = current_race.merge(jockey_stats, on='jockey', how='left')
            except:
                current_race['jockey_win_rate'] = 0.08
                
            try:
                trainer_stats = pd.read_sql_query("""
                    SELECT trainer, AVG(CASE WHEN actual_rank = 1 THEN 1.0 ELSE 0.0 END) as trainer_win_rate
                    FROM race_results WHERE actual_rank IS NOT NULL GROUP BY trainer
                """, conn)
                current_race = current_race.merge(trainer_stats, on='trainer', how='left')
            except:
                current_race['trainer_win_rate'] = 0.08
                
            # 補齊可能缺失的勝率值
            current_race['jockey_win_rate'] = current_race['jockey_win_rate'].fillna(0.08)
            current_race['trainer_win_rate'] = current_race['trainer_win_rate'].fillna(0.08)
            
        conn.close()
        return current_race
    except Exception as e:
        return pd.DataFrame()
    
# 執行資料讀取
race_df = get_live_predictions(selected_date, selected_race)

# 5. 判斷是否有資料並進行預測
if not race_df.empty:
    if real_model is None:
        st.error("🧠 AI 預測大腦尚未就緒（模型檔案載入失敗）。")
        st.stop()
        
    st.subheader(f"📊 正在檢視：{selected_date} ── 第 {selected_race} 場 賽事預測")
    
    # 💡 升級後的超強預測特徵矩陣！欄位順序必須與你重新訓練模型時完全一致！
    feature_cols = [
        'draw', 
        'weight_vs_average', 
        'speed_vs_average',
        'rating_change',
        'body_weight',
        'recent_avg_rank',
        'jockey_win_rate',
        'trainer_win_rate'
    ]

    features = race_df[feature_cols]
    
    # 讓 AI Ranker 大腦預測這場比賽的分數
    race_df['AI_Score'] = real_model.predict(features)
    
    # XGBRanker 分數越低，排名越前
    predict_result = race_df.sort_values(by='AI_Score').reset_index(drop=True)
    predict_result.insert(0, 'AI 推薦名次', range(1, len(predict_result) + 1))
    
    # 欄位中文化展示，方便用戶閱讀
    predict_result = predict_result.rename(columns={
        'horse_name': '馬名',
        'draw': '檔位',
        'weight': '實際負磅',
        'jockey': '騎師',
        'trainer': '練馬師',
        'body_weight': '排位體重',
        'rating_change': '評分+/-',
        'recent_form': '6次近績'
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
        
    # 💡 在 DataFrame 中加上新抓的實用資訊，讓表格更豐富 scannable
    show_cols = ['AI 推薦名次', '馬名', '檔位', '實際負磅', '騎師', '練馬師', '排位體重', '評分+/-', '6次近績', 'AI_Score']
    st.dataframe(predict_result[show_cols].style.map(highlight_top3, subset=['AI 推薦名次']), width='stretch')

else:
    st.warning(f"😢 資料庫中目前沒有 {selected_date} 第 {selected_race} 場的歷史賽果數據。")
    st.info("💡 建議：請先執行新版 `auto_pipeline.py` 將當天完整數據寫入資料庫，網頁平台就會立刻更新顯現！")