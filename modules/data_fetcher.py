# modules/data_fetcher.py
import logging
import requests
import pandas as pd
import time
from datetime import datetime
from functools import lru_cache

logger = logging.getLogger(__name__)

class DataFetchError(Exception):
    pass

class ETFDataFetcher:
    def __init__(self, config):
        # 預設資料來源改為 'twse'（可在 settings.yaml 設定）
        # 若想保留 Yahoo Finance 作為fallback，也可在此判斷 data_source
        self.data_source = config.get('data_source', {}).get('primary', 'twse')

    @lru_cache(maxsize=32)
    def fetch_daily_data(self, etf_code, start_date):
        """
        從TWSE官網抓取指定ETF自 start_date (YYYY-MM-DD) 之後的所有日線資料。
        若想配合官方API做多月合併，請注意TWSE一次只能抓一個月的資料。
        """
        if self.data_source == 'twse':
            try:
                return self._fetch_from_twse(etf_code, start_date)
            except DataFetchError as e:
                logger.error(f"TWSE資料抓取失敗: {e}")
                # 如果想要fallback到 Yahoo Finance，可自行呼叫 fallback函式:
                # return self._fetch_from_yahoo(etf_code, start_date)
                return pd.DataFrame(columns=['Date','Close','Volume'])
        else:
            # 其他來源 (例如 yahoo_finance)
            return self._fetch_from_yahoo(etf_code, start_date)

    def _fetch_from_twse(self, etf_code, start_date):
        """
        使用台灣證交所官方日成交資訊，逐月抓取並合併成一個DataFrame。
        :param etf_code: ETF代號，如 '0050'
        :param start_date: 'YYYY-MM-DD' 格式的起始日期
        :return: DataFrame(columns=['Date','Close','Volume'])
        """
        # 1. 解析日期，將其拆成 (YYYY, MM, DD)
        start_dt = pd.to_datetime(start_date)
        end_dt = pd.Timestamp.now()  # 抓到今天
        
        # 2. 建立 month list，例如從 2012-01 到 2025-01
        all_months = []
        current = pd.Timestamp(start_dt.year, start_dt.month, 1)
        while current <= end_dt:
            all_months.append(current)
            # 下個月
            next_month = current.month + 1 if current.month < 12 else 1
            next_year = current.year + 1 if current.month == 12 else current.year
            current = pd.Timestamp(next_year, next_month, 1)

        all_df = []
        for month_start in all_months:
            yyyymmdd = month_start.strftime("%Y%m01")  # e.g. '20120101'
            logger.info(f"抓取 {etf_code} {month_start.strftime('%Y-%m')} 月份資料...")
            try:
                df_month = self._fetch_twse_one_month(etf_code, yyyymmdd)
                all_df.append(df_month)
                time.sleep(0.5)  # 禮貌性延遲，避免對官方站點造成壓力
            except Exception as e:
                logger.warning(f"{etf_code} {month_start} 資料抓取失敗: {e}")

        if not all_df:
            raise DataFetchError(f"{etf_code} 自 {start_date} 起無可用資料")

        final_df = pd.concat(all_df, ignore_index=True)
        # 篩掉 start_date 之前的資料
        final_df = final_df[final_df['Date'] >= start_dt]
        final_df = final_df.sort_values('Date').drop_duplicates('Date')
        return final_df

    def _fetch_twse_one_month(self, etf_code, yyyymmdd, max_retries=3, retry_delay=2):
        """
        抓取「特定年月」的成交資訊，並解析成DataFrame
        :param etf_code: '0050'
        :param yyyymmdd: '20250101' (只會回傳該月資料)
        :param max_retries: 最大重試次數 (預設 3 次)
        :param retry_delay: 每次重試前等待秒數 (預設 2 秒)
        :return: DataFrame(columns=['Date','Close','Volume'])
        """
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=csv&date={yyyymmdd}&stockNo={etf_code}"
        
        for attempt in range(1, max_retries + 1):  # 重試最多 max_retries 次
            try:
                resp = requests.get(url, timeout=10)  # 設定 timeout 避免請求卡住
                resp.encoding = 'big5'  # TWSE CSV 通常是 big5

                if resp.status_code != 200:
                    raise DataFetchError(f"HTTP 狀態碼非 200: {resp.status_code}")

                lines = resp.text.split('\n')

                # 過濾掉非資料行 (通常前幾行或最後幾行是標題或空行)
                raw_data = [line.strip() for line in lines if len(line.split('","')) >= 9]

                if not raw_data:
                    logging.warning(f"[{etf_code} {yyyymmdd}] 該月份無資料，直接返回空 DataFrame")
                    return pd.DataFrame(columns=['Date','Close','Volume'])

                # 解析 CSV
                df = pd.DataFrame([r.split('","') for r in raw_data])
                df.columns = df.iloc[0].str.replace('"', '')
                df = df.iloc[1:].copy()  # 去除表頭那一列

                # 取需要的欄位: 日期(0), 收盤價(6), 成交股數(1)
                df['日期'] = df['日期'].str.replace('"','')
                df['日期'] = df['日期'].apply(self._transform_date)
                df['收盤價'] = df['收盤價'].str.replace(',','').astype(float)
                df['成交股數'] = df['成交股數'].str.replace(',','').astype(float)

                output = df[['日期','收盤價','成交股數']].copy()
                output.columns = ['Date','Close','Volume']

                return output  # 成功抓取資料時直接回傳

            except (requests.RequestException, DataFetchError) as e:
                logging.warning(f"[{etf_code} {yyyymmdd}] 抓取失敗 (第 {attempt} 次): {e}")

            except Exception as e:
                logging.error(f"[{etf_code} {yyyymmdd}] 未知錯誤: {e}")

            if attempt < max_retries:
                logging.info(f"[{etf_code} {yyyymmdd}] 等待 {retry_delay} 秒後重試 ({attempt}/{max_retries}) ...")
                time.sleep(retry_delay)

        logging.error(f"[{etf_code} {yyyymmdd}] 多次重試失敗，返回空 DataFrame")
        return pd.DataFrame(columns=['Date','Close','Volume'])  # 多次重試失敗則回傳空 DataFrame

    def _transform_date(self, tw_date_str):
        """
        把 TWSE 的日期(民國年) 轉成西元datetime
        e.g. '112/01/05' -> 2023-01-05
        """
        parts = tw_date_str.split('/')
        year = int(parts[0]) + 1911
        month = int(parts[1])
        day = int(parts[2])
        return pd.Timestamp(year, month, day)

    def _fetch_from_yahoo(self, etf_code, start_date):
        """
        (若保留) 從 Yahoo Finance 抓取資料
        """
        import yfinance as yf
        from requests.exceptions import RequestException

        try:
            ticker = yf.Ticker(f"{etf_code}.TW")
            hist = ticker.history(start=start_date)
            if hist.empty:
                raise DataFetchError(f"{etf_code} 無有效Yahoo Finance資料")
            return hist.reset_index()[['Date', 'Close', 'Volume']]
        except RequestException as e:
            logger.error(f"Yahoo API請求失敗: {e}")
            return pd.DataFrame(columns=['Date','Close','Volume'])
        except Exception as e:
            logger.error(f"未知錯誤: {e}")
            return pd.DataFrame(columns=['Date','Close','Volume'])
