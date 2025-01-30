# modules/reporter.py
import pandas as pd
from .storage import CSVStorage

class ReportGenerator:
    def __init__(self, storage: CSVStorage):
        self.storage = storage

    def generate_etf_report(self, etf_code):
        """
        生成單一ETF報告，包含:
        - 數據期間
        - 總筆數
        - 缺失天數
        - 極端值數量
        - 零成交量天數
        """
        df = self.storage.load_data(etf_code)
        if df.empty:
            return {
                "ETF代碼": etf_code,
                "數據期間": "無",
                "總數據量": 0,
                "缺失天數": 0,
                "極端值數量": 0,
                "零成交量天數": 0
            }

        checks = self.storage.check_data_integrity(df)
        report = {
            "ETF代碼": etf_code,
            "數據期間": f"{df['Date'].min().strftime('%Y-%m-%d')} ~ {df['Date'].max().strftime('%Y-%m-%d')}",
            "總數據量": len(df),
            "缺失天數": len(checks['date_gaps']),
            "極端值數量": len(checks['outliers']),
            "零成交量天數": len(checks['zero_volume'])
        }
        return report

    def generate_comparison_report(self, etf_codes):
        """
        生成多ETF的比較報告，將每檔ETF的報告彙整在同一個DataFrame中。
        """
        all_reports = []
        for code in etf_codes:
            single_report = self.generate_etf_report(code)
            all_reports.append(single_report)

        return pd.DataFrame(all_reports)
