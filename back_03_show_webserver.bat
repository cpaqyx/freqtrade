@echo off
cd C:\work\freqtrade\freqtrade
REM 统一指定UI回测结果目录，便于UI集中显示导入的回测结果
set FREQTRADE__ui__backtest_results_dir=user_data/backtest_results

REM 使用通用配置启动WebServer，支持查看所有策略的回测结果
C:\java\python312\python.exe ./freqtrade/main.py webserver -c ./user_data/webserver_config.json
pause