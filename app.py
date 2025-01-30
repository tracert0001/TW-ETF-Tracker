# app.py (Streamlit UI)
import streamlit as st
import pandas as pd
import logging

from config.config_loader import load_config
from modules.data_fetcher import ETFDataFetcher
from modules.storage import CSVStorage
from modules.reporter import ReportGenerator
from modules.data_processor import ETFComparator
from modules.plotter import ETFVisualizer
from main import init_historical_data, update_daily_data, schedule_tasks

# 如果需要日誌顯示在 Streamlit console:
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s - %(message)s")

# 輔助函式：用於依期間過濾資料 (2w/1m/3m/1y/3y)
def filter_by_period(df, period='1m'):
    # 簡易示範
    period_map = {
        '2w': 14,
        '1m': 30,
        '3m': 90,
        '6m': 180,
        '1y': 365,
        '2y': 365*2,
        '3y': 365*3
    }
    days = period_map.get(period, 30)
    if df.empty:
        return df
    end_date = df['Date'].max()
    start_date = end_date - pd.Timedelta(days=days)
    return df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

def color_performance(val):
    try:
        numeric_val = float(val)
    except ValueError:
        return ''  # 非數值或空白就不改顏色

    if numeric_val > 0:
        return 'color: red'
    elif numeric_val < 0:
        return 'color: green'
    else:
        return ''
    
def main():
    st.title("Taiwan ETF Tracker Dashboard")

    # 載入config，初始化物件
    config = load_config()
    storage = CSVStorage(config.get('data_dir', 'data'))
    fetcher = ETFDataFetcher(config)
    reporter = ReportGenerator(storage)
    comparator = ETFComparator(storage)

    # 區塊1: 功能按鈕 (初始化、更新、排程)
    st.subheader("系統操作")
    col1, col2, col3 = st.columns(3)
    if col1.button("初始化資料 (init)"):
        with st.spinner("正在初始化所有ETF歷史數據..."):
            init_historical_data(config)
        st.success("初始化完成！")

    if col2.button("更新當日資料 (update)"):
        with st.spinner("正在更新今日資料..."):
            update_daily_data(config)
        st.success("更新完成！")

    if col3.button("啟動每日排程 (schedule)"):
        st.warning("目前的程式架構下，schedule 會進入 while True。建議在終端機執行 main.py --schedule。")

    st.write("---")

    # 使用 session_state 來記錄是否顯示「各ETF最後資料日期」
    if "show_etf_dates" not in st.session_state:
        st.session_state["show_etf_dates"] = False

    st.subheader("各ETF最後更新日期")

    # 這個按鈕會切換 show_etf_dates 狀態
    if st.button("顯示/收起"):
        st.session_state["show_etf_dates"] = not st.session_state["show_etf_dates"]

    # 根據 session_state 決定是否顯示
    if st.session_state["show_etf_dates"]:
        etf_data = []
        for etf in config['etf_list']:
            etf_code = etf['code']
            df = storage.load_data(etf_code)
            if df.empty:
                etf_data.append({"ETF 代號": etf_code, "最後資料更新日期": "尚未有資料"})
            else:
                last_date = df['Date'].max().strftime('%Y-%m-%d')
                etf_data.append({"ETF 代號": etf_code, "最後資料更新日期": last_date})
        
        etf_df = pd.DataFrame(etf_data)
        st.dataframe(etf_df)
        st.info("以上是目前系統中各ETF的最後更新日期。")

    st.write("---")

    # 區塊2: 查詢比較
    st.subheader("ETF 查詢與比較")

    # 1) 讓使用者選擇一個或多個 ETF
    etf_codes = [etf['code'] for etf in config['etf_list']]
    selected_etfs = st.multiselect("選擇要比較的ETF代號", etf_codes, default=etf_codes[:1])

    # 2) 選擇時間範圍
    period_options = ["2w", "1m", "3m", "6m", "1y", "2y", "3y"]
    selected_period = st.selectbox("選擇資料區間", period_options)

    if st.button("查詢並顯示圖表"):
        if not selected_etfs:
            st.error("請至少選擇一檔ETF!")
        else:
            st.success([f"({etf.get('code')}) {etf.get('name')}" for etf in config['etf_list'] if etf.get("code") in selected_etfs])
            # 讀取並合併
            combined_df = comparator.compare_performance(selected_etfs, period=selected_period)  # 先抓3年全量
            # 再依使用者選的區間做進一步過濾
            filtered_df = filter_by_period(combined_df, selected_period)
            
            if filtered_df.empty:
                st.warning("選擇的期間內沒有資料，請嘗試更長期間或檢查資料是否已初始化。")
            else:
                # 顯示表格
                st.dataframe(filtered_df)

                # 排序功能 (範例: 以Close降序)
                st.markdown("#### 按收盤價排序 (示範)")
                sorted_df = filtered_df.sort_values(by="Close", ascending=False)
                st.dataframe(sorted_df.head(10))

                # 繪圖
                st.markdown("#### 趨勢圖")
                # 您可直接用 plotly.express 在此畫圖，也可用 plotter.py
                # 若要用 modules.plotter.ETFVisualizer:
                fig = ETFVisualizer.plot_comparison(filtered_df)
                if fig is None:
                    st.warning("無資料可顯示")
                else:
                    # 由於plot_comparison可直接 fig.show() 在普通Python中，但在Streamlit中:
                    st.plotly_chart(fig, use_container_width=True)

    
    # 區塊3: ETF 績效表現 (自訂開始/結束日期)
    st.write("---")
    st.subheader("ETF 績效表現 (自訂區間)")

    # 輸入自訂的開始/結束日期
    col_start, col_end = st.columns(2)
    with col_start:
        user_start_date = st.date_input("開始日期", value=pd.Timestamp.now() - pd.Timedelta(days=30))
    with col_end:
        user_end_date = st.date_input("結束日期", value=pd.Timestamp.now())

    # 新按鈕 => 顯示績效表
    if st.button("績效表現"):
        # 確認使用者是否有選ETF (複用 selected_etfs)
        if not selected_etfs:
            st.error("請先在上方選擇要比較的ETF!")
        else:
            selected_full_etfs = [(etf.get("code"), etf.get("name")) for etf in config['etf_list'] if etf.get("code") in selected_etfs]
            # 用來儲存成果
            performance_data = []
            
            for code, name in selected_full_etfs:
                # 讀取CSV / DataFrame
                df_etf = storage.load_data(code)
                if df_etf.empty:
                    # 若沒有資料就略過或標註
                    import math
                    performance_data.append({
                        "ETF代號": code,
                        "ETF名稱": name,
                        "累積漲幅(%)": math.nan,
                        "年化報酬率(%)": math.nan
                    })
                    continue

                # 過濾指定區間
                mask = (df_etf['Date'] >= pd.to_datetime(user_start_date)) & \
                       (df_etf['Date'] <= pd.to_datetime(user_end_date))
                df_period = df_etf[mask].sort_values('Date')

                if df_period.empty:
                    # 該ETF在此區間無資料
                    import math
                    performance_data.append({
                        "ETF代號": code,
                        "ETF名稱": name,
                        "累積漲幅(%)": math.nan,
                        "年化報酬率(%)": math.nan
                    })
                    continue
                
                # 取得第一筆收盤價, 最後一筆收盤價
                start_close = df_period.iloc[0]['Close']
                end_close   = df_period.iloc[-1]['Close']

                # 累積漲幅
                cum_return = (end_close - start_close) / start_close  # e.g. 0.05 => 5%
                
                # 計算天數
                num_days = (df_period.iloc[-1]['Date'] - df_period.iloc[0]['Date']).days
                if num_days <= 0:
                    # 交易日太少或同一天
                    annual_return = 0
                else:
                    # 年化報酬率 (單純以天數計算)
                    annual_return = (1 + cum_return)**(365/num_days) - 1

                performance_data.append({
                    "ETF代號": code,
                    "ETF名稱": name,
                    # 直接儲存浮點數 => 例如 10.5 代表 +10.5%
                    "累積漲幅(%)": cum_return * 100,  
                    "年化報酬率(%)": annual_return * 100
                })
            
            # 產出表格
            perf_df = pd.DataFrame(performance_data)

            perf_df_styled = perf_df.style.format(
                subset=["累積漲幅(%)", "年化報酬率(%)"],
                formatter="{:.2f}%"
            )
            perf_df_styled = perf_df_styled.applymap(color_performance,
                subset=["累積漲幅(%)", "年化報酬率(%)"]
            )
            st.dataframe(perf_df_styled)



def run_streamlit():
    """執行 streamlit app"""
    # python -m streamlit run app.py
    main()

if __name__ == "__main__":
    main()
