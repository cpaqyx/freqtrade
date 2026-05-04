@echo off
echo ========================================
echo 下载5分钟K线数据（最大历史范围）
echo ========================================
echo 配置文件: freq.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近500天（约1.4年）
echo K线周期: 5分钟
echo 说明: 5分钟数据量大，500天约为API支持的最大范围
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 下载5分钟K线数据（最大范围）
echo 开始下载5分钟数据（500天）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 5m ^
  --days 500 ^
  --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/futures/
echo.
echo 已下载币种（5分钟，500天数据）:
echo - BTC/USDT:USDT
echo - ETH/USDT:USDT
echo - SOL/USDT:USDT
echo - XRP/USDT:USDT
echo - ADA/USDT:USDT
echo - DOGE/USDT:USDT
echo - SUI/USDT:USDT
echo - TRX/USDT:USDT
echo - ENA/USDT:USDT
echo.
echo 警告:
echo - 5分钟数据量非常大（500天 = 约144,000根K线/币种）
echo - 9个币种总数据量约130万根K线
echo - 下载时间较长，请耐心等待
echo - 如果下载失败，可能是API限制，尝试减少天数
echo.
pause

