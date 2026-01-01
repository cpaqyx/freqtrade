@echo off
chcp 65001
echo 正在启动UI和WebServer...
echo.

REM 获取当前批处理文件所在目录
set SCRIPT_DIR=%~dp0

REM 在新窗口中启动UI
start "FreqUI - 前端界面" cmd /k "cd /d %SCRIPT_DIR% && call back_00_UI.bat"

REM 等待2秒，让UI先启动
timeout /t 2 /nobreak >nul

REM 在新窗口中启动WebServer
start "FreqTrade WebServer - 后端服务" cmd /k "cd /d %SCRIPT_DIR% && call back_03_show_webserver.bat"

echo.
echo ✅ 已启动两个服务窗口：
echo    1. FreqUI - 前端界面
echo    2. FreqTrade WebServer - 后端服务
echo.
echo 请在各自的窗口中查看运行状态
echo.
echo 主窗口即将自动关闭...
timeout /t 2 /nobreak >nul

