@echo off
chcp 65001 >nul
echo ========================================
echo BTC全仓策略参数优化 - 快速测试版
echo ========================================
echo 策略: BTCFullPosition
echo 配置文件: config.json
echo 损失函数: MultiMetricHyperOptLoss
echo 优化空间: buy + sell
echo 迭代次数: 50 (快速测试)
echo 币种: BTC/USDT
echo 时间范围: 2023-2025 (约2年，加快测试)
echo.

REM 切换到freqtrade根目录
cd /d "E:\git\freqtrade\freqtrade"

REM 同步策略文件到 strategies 目录
echo 正在同步策略文件...
if not exist user_data\strategies mkdir user_data\strategies
copy /Y user_data\btc\BTCFullPosition.py user_data\strategies\BTCFullPosition.py >nul
echo ✓ 策略文件已同步
echo.

REM 设置优化时间范围（缩短以加快测试）
set START_DATE=20230101
set END_DATE=20251103

REM 标记为优化模式
set IS_HYPEROPT=true

echo 测试时间范围: %START_DATE%-%END_DATE%
echo 预计用时: 5-15分钟（根据硬件配置）
echo.
echo ⚠️  这是快速测试版本，仅用于:
echo   - 验证脚本是否正常运行
echo   - 快速测试参数优化流程
echo   - 估算完整优化所需时间
echo.
echo 💡 正式优化请使用: hyperopt_BTCFullPosition.bat (10000次迭代)
echo.

REM 执行快速 Hyperopt 优化命令
python freqtrade/main.py hyperopt ^
  -c user_data/btc/config.json ^
  --strategy BTCFullPosition ^
  --strategy-path user_data/btc ^
  --timeframe 1d ^
  --hyperopt-loss MultiMetricHyperOptLoss ^
  --spaces buy sell ^
  --epochs 50 ^
  --timerange=%START_DATE%-%END_DATE% ^
  --min-trades 5 ^
  -j -1

echo.
echo ========================================
echo 快速测试完成！
echo ========================================
echo.
echo 📊 测试结果仅供参考，正式优化请使用完整版本
echo.
echo 下一步:
echo 1. 如果脚本运行正常，运行完整版: hyperopt_BTCFullPosition.bat
echo 2. 根据此次测试时间，估算完整优化所需时间 (约为20倍)
echo 3. 查看详细说明: Hyperopt使用说明.md
echo.
pause
