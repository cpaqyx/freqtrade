@echo off
chcp 65001 >nul
echo ========================================
echo 下载5分钟K线数据（最大历史范围）
echo ========================================
echo 配置文件: spot.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近500天（约1.4年）
echo K线周期: 5分钟
echo 说明: 5分钟数据量大，500天约为API支持的最大范围
echo.
echo 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
echo.

REM 切换到freqtrade根目录
cd /d "C:\work\freqtrade\freqtrade"

echo 下载5分钟数据（500天）...
python freqtrade/main.py download-data ^
  -c user_data/common/spot.json ^
  --timeframe 5m ^
  --days 500 ^
  --trading-mode spot ^
  --erase

REM echo 下载5分钟数据（500天）...
REM python freqtrade/main.py download-data ^
REM   -c user_data/common/spot.json ^
REM   --timeframe 5m ^
REM   --days 500 ^
REM   --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================
echo.
pause

