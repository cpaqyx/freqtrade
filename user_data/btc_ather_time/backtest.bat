@echo off
chcp 65001 >nul
echo ========================================
echo BTC全仓策略回测
echo ========================================
echo.

REM 设置环境
cd /d %~dp0\..\..

REM 同步策略文件到 strategies 目录（供 FreqUI 使用）
echo 正在同步策略文件...
REM if not exist user_data\strategies mkdir user_data\strategies
copy /Y user_data\btc_ather_time\BTCFullPosition_1h.py user_data\strategies\BTCFullPosition_1h.py >nul
copy /Y user_data\btc_ather_time\BTCFullPosition_1m.py user_data\strategies\BTCFullPosition_1m.py >nul
copy /Y user_data\btc_ather_time\BTCFullPosition_5m.py user_data\strategies\BTCFullPosition_5m.py >nul
copy /Y user_data\btc_ather_time\BTCFullPosition_1m.json user_data\strategies\BTCFullPosition_1m.json >nul
echo 策略文件已同步
echo.

REM 运行回测
echo 开始回测...

REM 下载1小时数据（1095天 = 3年）...
REM python -m freqtrade backtesting ^
REM   --config user_data/btc_ather_time/config_1h.json ^
REM   --strategy BTCFullPosition_1h ^
REM   --timerange 20221101-20251101 ^
REM   --timeframe 1h ^
REM   --export trades ^
REM   --breakdown day week month ^
REM   --cache none

REM REM 下载5分钟数据（500天）...
REM python -m freqtrade backtesting ^
REM   --config user_data/btc_ather_time/config_5m.json ^
REM   --strategy BTCFullPosition_5m ^
REM   --timerange 20240901-20251103 ^
REM   --timeframe 5m ^
REM   --export trades ^
REM   --breakdown day week month ^
REM   --cache none

REM REM 下载1分钟数据（365天 = 1年）...
 python -m freqtrade backtesting ^
  --config user_data/btc_ather_time/config_1m.json ^
  --strategy-path user_data/btc_ather_time ^
  --strategy BTCFullPosition_1m ^
  --timerange 20251001-20251130 ^
  --timeframe 1m ^
  --export trades ^
  --breakdown day week month ^
  --cache none


echo.
echo ========================================
echo 回测完成！
echo ========================================
echo.
pause
