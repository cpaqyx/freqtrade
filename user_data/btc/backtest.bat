@echo off
chcp 65001 >nul
echo ========================================
echo BTC全仓策略回测
echo ========================================
echo.
echo 策略: BTCFullPosition (90日图形分析)
echo 币种: BTC/USDT
echo 周期: 1d (日线)
echo 模式: 现货交易 (全仓操作)
echo.
echo 核心逻辑:
echo - 计算最近90日最高/最低价
echo - 分析90日图形趋势
echo - 全仓建仓/平仓
echo.
echo 建仓条件:
echo 1. 从90日最高点跌25%%直接建仓
echo 2. 单日涨2%%或连续涨3%%+图形确认
echo.
echo 平仓条件:
echo 1. 单日跌2%%或连续跌3%%+双顶形态
echo.
echo ========================================
echo.

REM 设置环境
cd /d %~dp0\..\..

REM 同步策略文件到 strategies 目录（供 FreqUI 使用）
echo 正在同步策略文件...
if not exist user_data\strategies mkdir user_data\strategies
copy /Y user_data\btc\BTCFullPosition.py user_data\strategies\BTCFullPosition.py >nul
echo 策略文件已同步
echo.

REM 运行回测
echo 开始回测...
echo.
python -m freqtrade backtesting ^
  --config user_data/btc/config.json ^
  --strategy BTCFullPosition ^
  --timerange 20200101-20251103 ^
  --timeframe 1d ^
  --export trades ^
  --breakdown day week month ^
  --cache none

echo.
echo ========================================
echo 回测完成！
echo ========================================
echo.
echo 结果已保存到: user_data/backtest_results/
echo.
echo 查看详细结果：
echo 1. 打开 FreqUI: http://127.0.0.1:8086
echo 2. 或查看导出的 trades 文件
echo.
pause



