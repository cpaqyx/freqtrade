@echo off
chcp 65001 > nul
echo ========================================
echo 5分钟高频策略参数优化 - 全部币种
echo ========================================
echo 策略: HighFreq5mStrategy
echo 配置: freq.json
echo 币种: BTC, ETH, SOL, XRP, ADA, DOGE, SUI, TRX, ENA (9个)
echo 时间框架: 5分钟
echo 优化范围: 2024-01-01 至 2025-10-24
echo 迭代次数: 10000
echo 优化目标: SharpeHyperOptLoss (夏普比率)
echo 优化空间: buy, sell, roi, stoploss
echo ========================================
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 运行Hyperopt
echo 开始参数优化... (预计运行时间: 数小时)
python freqtrade/main.py hyperopt ^
  -c user_data/freq/freq.json ^
  --strategy HighFreq5mStrategy ^
  --strategy-path user_data/freq ^
  --timeframe 5m ^
  --timerange=20240101-20251024 ^
  --hyperopt-loss SharpeHyperOptLoss ^
  --epochs 10000 ^
  --spaces buy sell roi stoploss ^
  --random-state 42 ^
  --min-trades 30 ^
  -j -1

echo.
echo ========================================
echo 参数优化完成！
echo ========================================
echo.
echo 最优参数已保存，请查看输出结果
echo.
pause

