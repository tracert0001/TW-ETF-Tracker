# config/config_loader.py
import yaml
from pathlib import Path

def load_config():
    base_path = Path(__file__).parent  # config/ 路徑
    
    try:
        # 載入主設定
        with open(base_path / 'settings.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # 載入ETF清單
        with open(base_path / 'etf_list.yaml', 'r', encoding='utf-8') as f:
            etf_list = yaml.safe_load(f)
        
        config['etf_list'] = etf_list
        return config
    
    except FileNotFoundError as e:
        raise SystemExit(f"設定檔找不到: {e.filename}")
    except yaml.YAMLError as e:
        raise SystemExit(f"設定檔格式錯誤: {e}")
