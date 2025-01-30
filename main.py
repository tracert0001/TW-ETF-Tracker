# main.py
import logging
import argparse
import pandas as pd
import schedule
import time

from config.config_loader import load_config
from modules.data_fetcher import ETFDataFetcher
from modules.storage import CSVStorage
from modules.reporter import ReportGenerator

def init_historical_data(config):
    """一次性抓取多檔ETF的歷史數據"""
    fetcher = ETFDataFetcher(config)
    storage = CSVStorage(config.get('data_dir', 'data'))
    reporter = ReportGenerator(storage)

    for etf in config['etf_list']:
        etf_code = etf['code']
        start_date = etf['start_date']
        print(f"[初始化] 抓取 {etf_code} 從 {start_date} 起的歷史資料...")

        df = fetcher.fetch_daily_data(etf_code, start_date)
        if not df.empty:
            storage.save_data(etf_code, df)
            report = reporter.generate_etf_report(etf_code)
            print(report)  # 簡單印出報表資訊
        else:
            logging.warning(f"{etf_code} 歷史資料抓取失敗")

def update_daily_data(config):
    """每日更新資料"""
    fetcher = ETFDataFetcher(config)
    storage = CSVStorage(config.get('data_dir', 'data'))

    today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
    for etf in config['etf_list']:
        etf_code = etf['code']
        print(f"[更新] 抓取 {etf_code} {today_str} 當日資料...")
        df = fetcher.fetch_daily_data(etf_code, start_date=today_str)
        if not df.empty:
            storage.save_data(etf_code, df)
        else:
            logging.warning(f"{etf_code} 當日資料抓取失敗")

def schedule_tasks(config):
    """排程每日固定時間執行更新"""
    update_time = config.get('update_time', '18:00')  # 預設下午六點
    schedule.every().day.at(update_time).do(update_daily_data, config)
    logging.info(f"已排程每日 {update_time} 執行更新")

    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分鐘檢查一次

def main():
    config = load_config()

    # 設定全域日誌 (可依需求改成 logging.config)
    logging.basicConfig(
        level=getattr(logging, config.get('log_level', 'INFO')),
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s"
    )

    parser = argparse.ArgumentParser(description="ETF Tracker")
    parser.add_argument("--init", action="store_true", help="初始化歷史資料")
    parser.add_argument("--update", action="store_true", help="更新當日資料")
    parser.add_argument("--schedule", action="store_true", help="啟動每日排程")

    args = parser.parse_args()

    # 根據參數執行
    if args.init:
        init_historical_data(config)
    if args.update:
        update_daily_data(config)
    if args.schedule:
        schedule_tasks(config)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("程式已手動停止")
