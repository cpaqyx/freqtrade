@echo off
chcp 65001 > nul
echo ========================================
echo 5分钟高频策略回测 - 全部币种
echo ========================================
echo 策略: HighFreq5mStrategy
echo 配置: freq.json
echo 币种: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA (9个)
echo 时间框架: 5分钟
echo 回测范围: 2024-01-01 至 2025-10-24 (约10个月)
echo ========================================
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 运行回测
echo 开始回测...
python freqtrade/main.py backtesting ^
  -c user_data/freq/freq.json ^
  --strategy HighFreq5mStrategy ^
  --strategy-path user_data/freq ^
  --timeframe 5m ^
  --timerange=20240101-20251024 ^
  --enable-protections ^
  --breakdown month

echo.
echo ========================================
echo 回测完成！
echo ========================================
echo.
echo 查看详细结果请运行:
echo python freqtrade/main.py backtesting-show
echo.
pause

