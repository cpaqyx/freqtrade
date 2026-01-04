@echo off
chcp 65001 >nul
echo ========================================
echo 下载1小时K线数据（最大历史范围）
echo ========================================
echo 配置文件: spot.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近1095天（约3年）
echo K线周期: 1小时
echo 说明: 1小时数据适合高频策略开发，1095天约为API支持的最大范围
echo.
echo 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
echo.

REM 切换到freqtrade根目录
cd /d "C:\work\freqtrade\freqtrade"

echo 开始下载1小时数据（1095天）...
python freqtrade/main.py download-data ^
  -c user_data/common/spot.json ^
  --timeframe 1h ^
  --days 1095 ^
  --trading-mode spot ^
  --erase


REM echo 开始下载1小时数据（1095天）...
REM python freqtrade/main.py download-data ^
REM   -c user_data/common/futures.json ^
REM   --timeframe 1h ^
REM   --days 1095 ^
REM   --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================

echo.
pause

