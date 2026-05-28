@echo off
chcp 65001 >nul 2>&1
REM HighRateSowing Hyperopt Script
REM Usage: run_hyperopt.bat [timerange] [epochs] [spaces] [min_trades]
REM Example: run_hyperopt.bat 20260322-20260522 15000 "buy sell roi stoploss" 100

setlocal EnableDelayedExpansion

REM Config - use current project path
set "CONFIG=%~dp0config.json"
set "STRATEGY=HighRateSowing"
set "DATADIR=%~dp0..\data\binance"
set "LOGDIR=%~dp0logs"
set "FREQTRADE_DIR=%~dp0..\.."

REM Get timestamp
for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value 2^>nul') do set "datetime=%%I"
set "TIMESTAMP=!datetime:~0,8!_!datetime:~8,6!"

REM Parameters
if "%~1"=="" (set "TIMERANGE=20260322-20260522") else (set "TIMERANGE=%~1")
if "%~2"=="" (set "EPOCHS=15000") else (set "EPOCHS=%~2")
if "%~3"=="" (set "SPACES=buy sell roi stoploss") else (set "SPACES=%~3")
if "%~4"=="" (set "MIN_TRADES=100") else (set "MIN_TRADES=%~4")

REM Create log directory
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ========================================
echo HighRateSowing Hyperopt
echo Timerange: %TIMERANGE%
echo Epochs: %EPOCHS%
echo Spaces: %SPACES%
echo Min trades: %MIN_TRADES%
echo Start time: %date% %time%
echo ========================================

REM Run hyperopt
cd /d "%FREQTRADE_DIR%"
python ./freqtrade/main.py hyperopt --config "%CONFIG%" --strategy %STRATEGY% --datadir "%DATADIR%" --timerange=%TIMERANGE% --epochs %EPOCHS% --spaces %SPACES% --hyperopt-loss SharpeHyperOptLoss --min-trades %MIN_TRADES% --random-state 42 --cache none --job-workers 1

echo.
echo Hyperopt completed: %date% %time%
pause
