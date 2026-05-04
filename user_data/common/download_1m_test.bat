@echo off
echo ========================================
echo 下载1分钟K线数据（测试版）
echo ========================================
echo 配置文件: freq.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 最近90天（约3个月）
echo K线周期: 1分钟
echo 说明: 快速测试版，适合策略初步验证
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 下载1分钟K线数据（90天测试）
echo 开始下载1分钟数据（90天）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1m ^
  --days 90 ^
  --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/futures/
echo.
echo 已下载币种（1分钟，90天数据）:
echo - 9个币种，每币种约13万根K线
echo - 总计约117万根K线
echo - 数据量适中，适合快速测试
echo.
echo 如需更长历史数据，请运行:
echo   .\user_data\panicIndex\download_1m_data.bat
echo.
pause

