@echo off
chcp 65001 >nul 2>&1
REM Download data for HighRateSowing strategy
REM Usage: download_data.bat [timerange]
REM Example: download_data.bat 20260301-

setlocal EnableDelayedExpansion

set "CONFIG=%~dp0config.json"
set "FREQTRADE_DIR=%~dp0..\.."

REM Parameters
if "%~1"=="" (set "TIMERANGE=20260301-") else (set "TIMERANGE=%~1")

echo ========================================
echo Download data for HighRateSowing
echo Timerange: %TIMERANGE%
echo Start time: %date% %time%
echo ========================================

cd /d "%FREQTRADE_DIR%"
python ./freqtrade/main.py download-data --config "%CONFIG%" --timerange %TIMERANGE% --timeframes 1m 5m 1h

echo.
echo Download completed: %date% %time%
pause
