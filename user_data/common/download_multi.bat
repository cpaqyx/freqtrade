@echo off
chcp 65001 >nul
echo ========================================
echo 下载多时间周期数据（最大历史范围）
echo ========================================
echo 配置文件: spot.json
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
echo 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
echo.

REM 切换到freqtrade根目录
cd /d "C:\work\freqtrade\freqtrade"

@REM echo [1/6] 下载1分钟数据（365天 = 1年）...
@REM echo 警告: 1分钟数据量极大，单币种约52万根K线，9个币种约470万根K线
@REM echo 建议: 如不需要超高频策略，可跳过此步骤（按Ctrl+C中断）
@REM echo 等待5秒后开始下载...
@REM timeout /t 5 /nobreak
@REM python freqtrade/main.py download-data ^
@REM   -c user_data/common/spot.json ^
@REM   --timeframe 1m ^
@REM   --days 365 ^
@REM   --trading-mode spot ^
@REM   --erase
@REM
@REM echo.
@REM echo [2/6] 下载5分钟数据（500天）...
@REM python freqtrade/main.py download-data ^
@REM   -c user_data/common/spot.json ^
@REM   --timeframe 5m ^
@REM   --days 500 ^
@REM   --trading-mode spot ^
@REM   --erase
@REM
@REM echo.
@REM echo [3/6] 下载15分钟数据（730天 = 2年）...
@REM python freqtrade/main.py download-data ^
@REM   -c user_data/common/spot.json ^
@REM   --timeframe 15m ^
@REM   --days 730 ^
@REM   --trading-mode spot ^
@REM   --erase
@REM
@REM echo.
@REM echo [4/6] 下载1小时数据（1095天 = 3年）...
@REM python freqtrade/main.py download-data ^
@REM   -c user_data/common/spot.json ^
@REM   --timeframe 1h ^
@REM   --days 1095 ^
@REM   --trading-mode spot ^
@REM   --erase
@REM
@REM echo.
@REM echo [5/6] 下载4小时数据（1825天 = 5年）...
@REM python freqtrade/main.py download-data ^
@REM   -c user_data/common/spot.json ^
@REM   --timeframe 4h ^
@REM   --days 1825 ^
@REM   --trading-mode spot ^
@REM   --erase

echo.
echo [6/6] 下载日线数据（2500天 = 约7年）...
python freqtrade/main.py download-data ^
  -c user_data/common/spot.json ^
  --timeframe 1d ^
  --days 2500 ^
  --trading-mode spot ^
  --erase

echo.
echo ========================================
echo 所有数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/spot/
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

