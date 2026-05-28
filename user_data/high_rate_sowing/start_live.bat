@echo off
chcp 65001 >nul 2>&1
REM HighRateSowing Live Trading Script

setlocal EnableDelayedExpansion

REM Config - use current project path
set "STRATEGY_NAME=HighRateSowing"
set "STRATEGY_DIR=%~dp0"
set "STRATEGY_FILE=%STRATEGY_DIR%%STRATEGY_NAME%.py"
set "CONFIG_FILE=%STRATEGY_DIR%config.json"
set "STRATEGIES_DIR=%~dp0..\strategies"
set "FREQTRADE_DIR=%~dp0..\.."
set "LOG_DIR=%STRATEGY_DIR%logs"

REM Create log directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

REM Get date
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "datetime=%%I"
set "DATE_STR=!datetime:~0,8!"

REM Log file
set "LOG_FILE=%LOG_DIR%\trading_%DATE_STR%.log"

echo === HighRateSowing Start Script ===
echo Time: %date% %time%
echo.

REM 1. Copy strategy file to strategies directory
echo [Step 1] Copying strategy file...
if not exist "%STRATEGIES_DIR%" mkdir "%STRATEGIES_DIR%"
copy /Y "%STRATEGY_FILE%" "%STRATEGIES_DIR%\%STRATEGY_NAME%.py" >nul
echo   Copied: %STRATEGY_FILE% -^> %STRATEGIES_DIR%\%STRATEGY_NAME%.py
echo.

REM 2. Change to freqtrade directory
cd /d "%FREQTRADE_DIR%"

REM 3. Start trading bot
echo [Step 2] Starting trading bot...
echo   Config: %CONFIG_FILE%
echo   Strategy: %STRATEGY_NAME%
echo   Log file: %LOG_FILE%
echo.

python ./freqtrade/main.py trade --config "%CONFIG_FILE%" --strategy "%STRATEGY_NAME%" --logfile "%LOG_FILE%" %*
pause
