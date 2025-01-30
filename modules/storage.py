# modules/storage.py
import pandas as pd
import numpy as np
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, Union
# from functools import lru_cache  # 若想對 load_data 做快取可開啟

logger = logging.getLogger(__name__)

class CSVStorage:
    """ETF數據存儲管理器，包含數據驗證、修復和版本控制功能"""
    
    REQUIRED_COLUMNS = ['Date', 'Close', 'Volume']
    NUMERIC_COLS = ['Close', 'Volume']
    
    def __init__(self, data_dir: str = 'data', max_backups: int = 30):
        """
        初始化存儲管理器
        :param data_dir: 數據存儲目錄
        :param max_backups: 最大保留備份版本數
        """
        self.data_dir = Path(data_dir)
        self.backup_dir = self.data_dir / 'backups'
        self.max_backups = max_backups
        self._setup_directories()
        
    def _setup_directories(self) -> None:
        """建立必要的存儲目錄"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def save_data(self, etf_code: str, new_data: pd.DataFrame) -> bool:
        """
        保存ETF數據，包含完整處理流程：
        1. 數據驗證 2. 自動修復 3. 合併數據 4. 建立版本 5. 寫入主檔案
        :return: 是否成功保存
        """
        try:
            if not self._validate_basic(new_data):
                logger.error(f"{etf_code} 數據驗證失敗")
                return False

            processed_data = self._preprocess_data(new_data)
            combined_data = self._merge_with_existing(etf_code, processed_data)
            
            if self._needs_repair(combined_data):
                combined_data = self.auto_repair_data(combined_data)
            
            self._clean_backups(etf_code)
            self.save_versioned_data(etf_code, combined_data)
            self._save_to_main_file(etf_code, combined_data)
            
            return True
            
        except Exception as e:
            logger.exception(f"保存 {etf_code} 數據時發生錯誤: {str(e)}")
            return False
    
    # @lru_cache(maxsize=10)  # 可選，如果確定檔案不會頻繁更新，可開啟此快取
    def load_data(self, etf_code: str) -> pd.DataFrame:
        """載入ETF歷史數據，並作後續基本處理"""
        file_path = self.data_dir / f"{etf_code}.csv"
        
        if not file_path.exists():
            logger.warning(f"{etf_code} 數據檔案不存在，回傳空DataFrame")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
        
        try:
            df = pd.read_csv(file_path, parse_dates=['Date'])
            df = self._postprocess_data(df)
            return df
        except Exception as e:
            logger.error(f"載入 {etf_code} 數據失敗: {str(e)}")
            return pd.DataFrame(columns=self.REQUIRED_COLUMNS)
    
    def check_data_integrity(self, df: pd.DataFrame) -> Dict[str, Union[pd.DataFrame, int]]:
        """執行深度數據完整性檢查，回傳各種可疑數據"""
        results = {}
        if df.empty:
            # 如果是空的，就直接回傳空結果
            results['date_gaps'] = pd.Series([], dtype='int')
            results['outliers'] = pd.DataFrame(columns=df.columns)
            results['zero_volume'] = pd.DataFrame(columns=df.columns)
            results['missing_values'] = {col: 0 for col in self.NUMERIC_COLS}
            return results
        
        # 排序日期，計算日期差
        df = df.sort_values('Date')
        date_diff = df['Date'].diff().dt.days.dropna()
        gaps = date_diff[date_diff > 1]
        results['date_gaps'] = gaps
        
        # 數值異常值檢查
        close_stats = df['Close'].describe()
        iqr = close_stats['75%'] - close_stats['25%']
        outliers = df[
            (df['Close'] < (close_stats['25%'] - 3 * iqr)) | 
            (df['Close'] > (close_stats['75%'] + 3 * iqr))
        ]
        results['outliers'] = outliers
        
        # 零成交量
        zero_volume = df[df['Volume'] == 0]
        results['zero_volume'] = zero_volume
        
        # 缺失值
        missing_values = df[self.NUMERIC_COLS].isnull().sum().to_dict()
        results['missing_values'] = missing_values
        
        return results
    
    def auto_repair_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """簡單的自動修復邏輯：插值填補、移動平均修復極端值、以及零成交量處理"""
        if df.empty:
            return df

        # 確保日期已排序
        df = df.sort_values('Date')

        # 先把 'Date' 設為 DatetimeIndex
        df = df.set_index('Date')

        # 填充缺失值 (time-based)
        df[self.NUMERIC_COLS] = df[self.NUMERIC_COLS].interpolate(method='time')

        # 移動平均修復極端值
        close_stats = df['Close'].describe()
        iqr = close_stats['75%'] - close_stats['25%']
        upper_bound = close_stats['75%'] + 3 * iqr
        lower_bound = close_stats['25%'] - 3 * iqr

        df['Close'] = df['Close'].mask(
            df['Close'] > upper_bound,
            df['Close'].rolling(5, min_periods=1).mean()
        )
        df['Close'] = df['Close'].mask(
            df['Close'] < lower_bound,
            df['Close'].rolling(5, min_periods=1).mean()
        )

        # 交易量若為 0 則用前值填補
        df['Volume'] = df['Volume'].replace(0, pd.NA).ffill()

        # 復原 index 為原本的欄位
        df = df.reset_index()

        return df
    
    def save_versioned_data(self, etf_code: str, data: pd.DataFrame) -> None:
        """建立備份版本"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"{etf_code}_{timestamp}.csv"
        data.to_csv(backup_path, index=False)
        logger.info(f"[{etf_code}] 已建立版本快照: {backup_path.name}")
    
    def _validate_basic(self, data: pd.DataFrame) -> bool:
        """基礎驗證"""
        if data.empty:
            logger.error("接收的DataFrame為空，無法驗證")
            return False
        
        # 檢查欄位是否齊全
        if not all(col in data.columns for col in self.REQUIRED_COLUMNS):
            missing = set(self.REQUIRED_COLUMNS) - set(data.columns)
            logger.error(f"缺少必要欄位: {missing}")
            return False
        
        # 檢查日期是否重複
        if data['Date'].duplicated().any():
            logger.error("DataFrame中存在重複的Date")
            return False
        
        return True
    
    def _preprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """將資料做基礎整理（轉型別、排序、去重等）"""
        df = df.copy()
        df['Date'] = pd.to_datetime(df['Date'])
        df[self.NUMERIC_COLS] = df[self.NUMERIC_COLS].apply(pd.to_numeric, errors='coerce')
        df = df.drop_duplicates(subset='Date')
        df = df.sort_values('Date')
        return df
    
    def _postprocess_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """讀檔後的後處理"""
        df = df.sort_values('Date')
        df[self.NUMERIC_COLS] = df[self.NUMERIC_COLS].fillna(method='ffill').fillna(method='bfill')
        return df
    
    def _merge_with_existing(self, etf_code: str, new_data: pd.DataFrame) -> pd.DataFrame:
        """將新數據合併至舊數據"""
        existing = self.load_data(etf_code)
        if existing.empty:
            return new_data
        
        combined = pd.concat([existing, new_data], ignore_index=True)
        combined = combined.drop_duplicates(subset='Date')
        combined = combined.sort_values('Date')
        return combined
    
    def _needs_repair(self, data: pd.DataFrame) -> bool:
        """判斷是否需要進行自動修復"""
        checks = self.check_data_integrity(data)
        if data.empty:
            return False
        
        return any([
            not checks['date_gaps'].empty,
            not checks['outliers'].empty,
            any(val > 0 for val in checks['missing_values'].values())
        ])
    
    def _clean_backups(self, etf_code: str) -> None:
        """刪除過舊的備份檔"""
        backups = sorted(self.backup_dir.glob(f"{etf_code}_*.csv"))
        if len(backups) > self.max_backups:
            to_remove = backups[:-self.max_backups]
            for backup in to_remove:
                backup.unlink()
                logger.debug(f"已移除過期備份: {backup.name}")
    
    def _save_to_main_file(self, etf_code: str, data: pd.DataFrame) -> None:
        """最終儲存至主檔案"""
        file_path = self.data_dir / f"{etf_code}.csv"
        data.to_csv(file_path, index=False, date_format='%Y-%m-%d')
        logger.info(f"[{etf_code}] 成功寫入主檔案，共 {len(data)} 筆記錄")
