@echo off
chcp 65001 >nul
echo ========================================
echo 下载1分钟K线数据（最大历史范围）
echo ========================================
echo 配置文件: freq.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近365天（约1年）
echo K线周期: 1分钟
echo 说明: 1分钟数据量极大，365天约为API支持的最大范围
echo.

echo 警告: 1分钟数据量极大！
echo - 单个币种: 约52.5万根K线 (365天 × 1440分钟/天)
echo - 9个币种:  约470万根K线
echo - 下载时间: 60-120分钟
echo - 存储空间: 约1-2GB
echo.
echo 建议: 如非必要，建议使用5分钟或1小时数据
echo 如果只需测试，建议先下载30-90天数据
echo.
echo 注意: 使用 --erase 参数将删除现有数据并重新下载完整数据
echo.
echo 是否继续? 将在10秒后自动开始...
timeout /t 10 /nobreak

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

echo 开始下载1分钟数据（365天）...
python freqtrade/main.py download-data ^
  -c user_data/common/spot.json ^
  --timeframe 1m ^
  --days 365 ^
  --trading-mode spot ^
  --erase

REM REM 下载1分钟K线数据（最大范围）
REM echo 开始下载1分钟数据（365天）...
REM python freqtrade/main.py download-data ^
REM   -c user_data/common/futures.json ^
REM   --timeframe 1m ^
REM   --days 365 ^
REM   --trading-mode futures

echo ========================================
echo 数据下载完成！
echo ========================================
echo.
pause

