@echo off
echo ========================================
echo 下载1小时K线数据（3年历史）
echo ========================================
echo 配置文件: freq.json
echo 交易对: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA
echo 时间范围: 1095天（约3年）
echo K线周期: 1小时
echo 推荐: 高频策略开发的平衡选择
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 下载1小时K线数据
echo 开始下载1小时数据（1095天）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1h ^
  --days 1095 ^
  --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/futures/
echo.
echo 已下载币种（1小时，3年数据）:
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
echo 提示:
echo - 1小时数据适合中高频策略
echo - 3年数据足够覆盖多个市场周期
echo - 数据量适中，回测速度较快
echo.
pause

