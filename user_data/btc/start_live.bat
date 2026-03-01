@echo off
chcp 65001 >nul

echo ========================================
echo BTC全仓策略 - 实盘启动 台湾6
echo ========================================
echo.

REM 切换到项目根目录
cd /d "%~dp0\..\..\"

REM 检查配置文件
if not exist "user_data\btc\config_live.json" (
    echo ❌ 错误：未找到配置文件 user_data\btc\config_live.json
    pause
    exit /b 1
)

REM 检查 API 密钥
findstr /C:"dummy" "user_data\btc\config_live.json" >nul
if %errorlevel%==0 (
    echo.
    echo ⚠️  警告：检测到 dummy API 密钥
    echo 请在 config_live.json 中设置真实的 Binance API Key 和 Secret
    echo （将无法执行真实交易）
    echo.
    echo [Y] 继续启动    [N] 取消退出
    choice /C YN /N
    if errorlevel 2 exit /b 0
)

REM 读取运行模式
findstr /C:"\"dry_run\": false" "user_data\btc\config_live.json" >nul
if %errorlevel%==0 (
    set "MODE=实盘"
    echo ⚠️⚠️⚠️ 实盘模式 - 将执行真实交易 ⚠️⚠️⚠️
) else (
    set "MODE=模拟盘"
    echo ✓ 模拟盘模式 - 不执行真实交易
)

echo.
echo 策略: BTCFullPosition
echo 币种: BTC/USDT
echo 模式: %MODE%
echo 配置: user_data/btc/config_live.json
echo 参数: user_data/btc/BTCFullPosition.json
echo.

if "%MODE%"=="实盘" (
    echo.
    echo ========================================
    echo   警告：即将启动实盘交易模式！
    echo ========================================
    echo.
    echo [Y] 确认启动实盘    [N] 取消退出
    choice /C YN /N
    if errorlevel 2 (
        echo.
        echo 已取消启动
        pause
        exit /b 0
    )
)

REM 同步策略文件
if not exist user_data\strategies mkdir user_data\strategies
copy /Y user_data\btc\BTCFullPosition.py user_data\strategies\BTCFullPosition.py >nul 2>&1

REM 创建日志目录
if not exist user_data\logs mkdir user_data\logs

echo.
echo 正在启动策略...
echo 按 Ctrl+C 可停止运行
echo.

REM 启动交易
python -m freqtrade trade ^
  --config user_data/btc/config_live.json ^
  --strategy BTCFullPosition ^
  --strategy-path user_data/btc ^
  --logfile user_data/logs/btc_live.log

echo.
echo 策略已停止
pause

