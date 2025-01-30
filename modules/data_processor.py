# modules/data_processor.py
import pandas as pd
from .storage import CSVStorage

class ETFComparator:
    def __init__(self, storage: CSVStorage):
        """
        :param storage: CSVStorage的實例，用於讀取ETF資料
        """
        self.storage = storage

    def compare_performance(self, etf_codes, period='1m'):
        """
        比較多支ETF在指定區間的表現，返回合併後的DataFrame
        :param etf_codes: ETF代碼列表 (ex: ['0050','0056','006208'])
        :param period: '2w'、'1m'、'3m'、'1y'、'3y'等
        """
        combined_list = []
        for code in etf_codes:
            df = self.storage.load_data(code)
            if df.empty:
                continue
            filtered = self._filter_period(df, period)
            # 在合併前先加一欄 ETF_Code 以便後續繪圖或分析
            filtered['ETF_Code'] = code
            combined_list.append(filtered)

        if combined_list:
            return pd.concat(combined_list, ignore_index=True)
        else:
            return pd.DataFrame(columns=['Date','Close','Volume','ETF_Code'])

    def _filter_period(self, df, period):
        """
        依 period 來過濾最近 n 天 / 月 / 年
        這裡提供一種簡易示範：先把 df 排序，再利用日期篩選
        """
        df = df.sort_values('Date')
        if df.empty:
            return df

        end_date = df['Date'].max()
        
        # 可自訂更多區間對應
        days_map = {
            '2w': 14,
            '1m': 30,
            '3m': 90,
            '6m': 180,
            '1y': 365,
            '2y': 365*2,
            '3y': 365*3
        }
        delta_days = days_map.get(period, 30)  # 若period無法對應，就預設30天
        start_date = end_date - pd.Timedelta(days=delta_days)

        return df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
