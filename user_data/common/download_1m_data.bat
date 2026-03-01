@echo off
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
echo 是否继续? 将在10秒后自动开始...
timeout /t 10 /nobreak

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 下载1分钟K线数据（最大范围）
echo.
echo 开始下载1分钟数据（365天）...
python freqtrade/main.py download-data ^
  -c user_data/panicIndex/freq.json ^
  --timeframe 1m ^
  --days 365 ^
  --trading-mode futures

echo.
echo ========================================
echo 数据下载完成！
echo ========================================
echo 数据保存位置: user_data/data/binance/futures/
echo.
echo 已下载币种（1分钟，365天数据）:
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
echo 数据统计:
echo - K线数量: 约470万根（9个币种）
echo - 数据周期: 1分钟
echo - 历史时长: 365天（1年）
echo.
echo 使用建议:
echo - 超高频策略（秒级、分钟级决策）
echo - 市场微观结构分析
echo - 回测速度会较慢，建议使用缓存
echo.
pause

