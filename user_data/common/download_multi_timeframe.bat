@echo off
echo ========================================
echo 下载多时间周期数据（最大历史范围）
echo ========================================
echo 配置文件: freq.json
echo 时间周期: 1m, 5m, 15m, 1h, 4h, 1d
echo 时间范围: 根据不同周期优化
echo.
echo 数据范围说明:
echo - 1分钟:  365天 (约1年) - API限制，数据量巨大
echo - 5分钟:  500天 (约1.4年) - API限制
echo - 15分钟: 730天 (约2年)
echo - 1小时:  1095天 (约3年)
echo - 4小时:  1825天 (约5年)
echo - 日线:   2500天 (约7年)
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

echo [1/6] 下载1分钟数据（365天 = 1年）...
echo 警告: 1分钟数据量极大，单币种约52万根K线，9个币种约470万根K线
echo 建议: 如不需要超高频策略，可跳过此步骤（按Ctrl+C中断）
echo 等待5秒后开始下载...
timeout /t 5 /nobreak
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1m ^
  --days 365 ^
  --trading-mode futures

echo.
echo [2/6] 下载5分钟数据（500天）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 5m ^
  --days 500 ^
  --trading-mode futures

echo.
echo [3/6] 下载15分钟数据（730天 = 2年）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 15m ^
  --days 730 ^
  --trading-mode futures

echo.
echo [4/6] 下载1小时数据（1095天 = 3年）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1h ^
  --days 1095 ^
  --trading-mode futures

echo.
echo [5/6] 下载4小时数据（1825天 = 5年）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 4h ^
  --days 1825 ^
  --trading-mode futures

echo.
echo [6/6] 下载日线数据（2500天 = 约7年）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1d ^
  --days 2500 ^
  --trading-mode futures

echo.
echo ========================================
echo 所有数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/futures/
echo.
echo 已下载时间周期（最大历史范围）:
echo - 1分钟:  365天 (约1年) - 约470万根K线
echo - 5分钟:  500天 (约1.4年) - 约130万根K线
echo - 15分钟: 730天 (约2年) - 约32万根K线
echo - 1小时:  1095天 (约3年) - 约24万根K线
echo - 4小时:  1825天 (约5年) - 约10万根K线
echo - 日线:   2500天 (约7年) - 约2.3万根K线
echo.
echo 数据量估算（9个币种）:
echo - 1分钟: 约470万根K线（数据量极大！）
echo - 5分钟: 约130万根K线
echo - 总存储空间: 约2-4GB
echo.
echo 下载时间估算:
echo - 1分钟数据: 60-120分钟
echo - 5分钟数据: 30-60分钟
echo - 其他周期: 20-30分钟
echo - 总计: 约2-3小时
echo.
pause

