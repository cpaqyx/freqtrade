@echo off
chcp 65001 >nul
echo ========================================
echo 下载日线K线数据（最大历史范围）
echo ========================================
echo 配置文件: spot.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近2500天（约7年）
echo K线周期: 日线
echo 说明: 日线数据量小，2500天约为API支持的最大范围
echo.
echo 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
echo.

REM 切换到freqtrade根目录
cd /d "C:\work\freqtrade\freqtrade"

echo 下载日线数据（2500天 = 约7年）...
python freqtrade/main.py download-data ^
  -c user_data/common/spot.json ^
  --timeframe 1d ^
  --days 2500 ^
  --trading-mode spot ^
  --erase


REM REM 下载5分钟K线数据（最大范围）
REM echo 下载日线数据（2500天 = 约7年）...
REM python freqtrade/main.py download-data ^
REM   -c user_data/common/futures.json ^
REM   --timeframe 1d ^
REM   --days 2500 ^
REM   --trading-mode futures

echo ========================================
echo 数据下载完成！
echo ========================================
echo.
pause

