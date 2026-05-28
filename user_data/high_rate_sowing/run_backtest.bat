@echo off
chcp 65001 >nul 2>&1
REM HighRateSowing Backtest Script
REM Usage: run_backtest.bat [timerange] [strategy_params]
REM Example: run_backtest.bat 20260322-20260522

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
set "EXTRA_PARAMS=%~2"

REM Create log directory
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

echo ========================================
echo HighRateSowing Backtest
echo Timerange: %TIMERANGE%
echo Start time: %date% %time%
echo ========================================

REM Run backtest
cd /d "%FREQTRADE_DIR%"
python ./freqtrade/main.py backtesting --config "%CONFIG%" --strategy %STRATEGY% --datadir "%DATADIR%" --timerange=%TIMERANGE% --cache none %EXTRA_PARAMS%

echo.
echo Backtest completed: %date% %time%
pause
