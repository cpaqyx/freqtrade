import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict
logger = logging.getLogger(__name__)
from datetime import datetime, timedelta, timezone
import requests
import time


# https://alternative.me/crypto/fear-and-greed-index/
class FGIDataProvider:
    def __init__(self, config: dict, historical_file: str = "panicIndex\\fgi_historical.json"):
        self.historical_file = os.path.join("user_data", historical_file)
        self.historical_data = self._load_historical_data()
        self.is_backtest = True  # 强制回测模式

    def _load_historical_data(self) -> Dict[str, float]:
        historical = {}
        try:
            if os.path.exists(self.historical_file):
                with open(self.historical_file, 'r') as f:
                    data = json.load(f)
                    for item in data.get('data', []):
                        try:
                            ts = int(item['timestamp'])
                            date_str = datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
                            fgi = float(item['value'])
                            if 0 <= fgi <= 100:
                                historical[date_str] = fgi
                        except:
                            continue
                    logger.info(f"FGI Loaded: {len(historical)} days")
            else:
                logger.error("FGI file not found!")
        except Exception as e:
            logger.error(f"FGI Load Error: {e}")
        return historical

    def get_fgi_for_date(self, target_date: datetime) -> float:
        """仅精确取目标日期的前一天 FGI；若不存在则抛出异常。"""
        if not isinstance(target_date, datetime):
            raise TypeError(f"target_date must be datetime, got {type(target_date)}")

        prev_date_str = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
        if prev_date_str in self.historical_data:
            return self.historical_data[prev_date_str]

        # 未找到严格前一日的数据，直接报错
        raise KeyError(f"FGI not found for previous day: {prev_date_str}")

    def get_current_fgi(self) -> float:
        if self.is_backtest:
            return 50.0
        current_time = time.time()
        for ts_str, data in self.cache.items():
            if current_time - data.get('fetch_time', 0) < 86400:
                return data['value']
        if current_time - self._last_api_call < self._api_rate_limit:
            return 50.0
        try:
            url = "https://api.alternative.me/fng/?limit=1"
            response = requests.get(url, timeout=self.api_timeout)
            response.raise_for_status()
            data = response.json()
            if data.get('data') and len(data['data']) > 0:
                fgi_value = float(data['data'][0]['value'])
                if 0 <= fgi_value <= 100:
                    timestamp = data['data'][0]['timestamp']
                    self.cache[timestamp] = {
                        'value': fgi_value,
                        'timestamp': timestamp,
                        'fetch_time': current_time
                    }
                    self._save_cache()
                    self._last_api_call = current_time
                    return fgi_value
        except:
            pass
        return 50.0