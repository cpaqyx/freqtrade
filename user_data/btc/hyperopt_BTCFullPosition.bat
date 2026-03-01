@echo off
chcp 65001 >nul
echo ========================================
echo BTC全仓策略参数优化
echo ========================================
echo 策略: BTCFullPosition
echo 配置文件: config.json
echo 损失函数: MultiMetricHyperOptLoss
echo 优化空间: buy + sell
echo 迭代次数: 10000
echo 币种: BTC/USDT
echo 时间范围: 2020-2025 (约5年)
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 同步策略文件到 strategies 目录
echo 正在同步策略文件...
if not exist user_data\strategies mkdir user_data\strategies
copy /Y user_data\btc\BTCFullPosition.py user_data\strategies\BTCFullPosition.py >nul
echo ✓ 策略文件已同步
echo.

REM 设置优化时间范围
set START_DATE=20200101
set END_DATE=20251103

REM 标记为优化模式，供策略识别
set IS_HYPEROPT=true

echo 优化时间范围: %START_DATE%-%END_DATE%
echo.
echo 优化参数列表:
echo   【建仓参数】
echo   - max_drop_from_high      : 15%%-45%%  (默认 25%%)
echo   - day_rise_threshold      : 1%%-5%%    (默认 2%%)
echo   - continuous_rise_threshold : 2%%-6%%  (默认 3%%)
echo   - pattern_drop_threshold  : 5%%-20%%   (默认 10%%)
echo   - double_top_threshold    : 3%%-10%%   (默认 5%%)
echo.
echo   【平仓参数】
echo   - day_drop_threshold           : 1%%-5%%  (默认 2%%)
echo   - continuous_drop_threshold    : 2%%-6%%  (默认 3%%)
echo   - double_top_higher_threshold  : 1%%-6%%  (默认 3%%)
echo   - double_top_lower_threshold   : 3%%-10%% (默认 5%%)
echo   - last_down_threshold          : 3%%-10%% (默认 5%%)
echo.
echo ⚠️  注意事项:
echo   - 优化过程需要较长时间 (预计 2-12 小时)
echo   - 建议使用性能较好的计算机
echo   - 可以随时按 Ctrl+C 中断，已完成的结果会保存
echo   - 优化结果保存在: user_data/hyperopt_results/
echo.

REM 执行 Hyperopt 优化命令
python freqtrade/main.py hyperopt ^
  -c user_data/btc/config.json ^
  --strategy BTCFullPosition ^
  --strategy-path user_data/btc ^
  --hyperopt-loss MultiMetricHyperOptLoss ^
  --spaces buy sell ^
  --epochs 10000 ^
  --timerange=%START_DATE%-%END_DATE% ^
  --min-trades 10 ^
  -j -1

echo.
echo ========================================
echo 参数优化完成！
echo ========================================
echo 结果保存在: user_data/hyperopt_results/
echo.
echo 💡 应用最优参数的方法:
echo.
echo 方法一: 修改策略文件中的 default 值
echo   max_drop_from_high = DecimalParameter(
echo       0.15, 0.45, default=0.22,  # 修改这里为最优值
echo       ...
echo   )
echo.
echo 方法二: 在配置文件中添加 strategy_params
echo   "strategy_params": {
echo       "max_drop_from_high": 0.22,
echo       "day_rise_threshold": 0.025,
echo       ...
echo   }
echo.
echo 📊 查看优化结果:
echo   python -m freqtrade hyperopt-list --best 10
echo   python -m freqtrade hyperopt-show -n 1
echo.
echo 提示: 
echo - 建议在不同时间段验证最优参数的稳定性
echo - 如需进一步优化，可调整参数范围后重新运行
echo - 查看详细说明，请阅读 Hyperopt使用说明.md
echo.
pause
