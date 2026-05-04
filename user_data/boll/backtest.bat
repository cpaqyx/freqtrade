@echo off
chcp 65001 >nul
echo ========================================
echo 恐慌指数策略回测
echo ========================================
echo.
echo 策略: Boll (纯恐慌指数双向交易)
echo 币种: BTC/USDT, ETH/USDT
echo 时间: 2019-09-08 至 2025-10-23 (约6年)
echo 模式: 永续合约 (支持做多做空)
echo.
echo ========================================
echo.

REM 设置环境
cd /d %~dp0\..\..

REM 同步策略文件到 strategies 目录（供 FreqUI 使用）
echo 正在同步策略文件...
copy /Y user_data\boll\Boll.py user_data\strategies\Boll.py >nul
echo 策略文件已同步
echo.

REM 运行回测
python -m freqtrade backtesting ^
  --config user_data/boll/Boll.json ^
  --strategy Boll ^
  --timerange 20200908-20251023 ^
  --timeframe 4h ^
  --export trades ^
  --breakdown day week month ^
  --cache none

echo.
echo ========================================
echo 回测完成！
echo ========================================
echo.
echo 结果已保存到: user_data/backtest_results/backtest-result-*.json
echo.
pause

