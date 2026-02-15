@echo off
chcp 65001 >nul
title 王者荣耀皮肤点数管理启动器
cd /d "%~dp0"

echo ==========================================
echo      自动侦测环境与路径...
echo ==========================================

:: ------------------------------------------------
:: 1. 寻找虚拟环境
:: ------------------------------------------------
set "VENV_PATH="

:: 检查当前目录
if exist "venv\Scripts\activate.bat" set "VENV_PATH=venv"
if exist ".venv\Scripts\activate.bat" set "VENV_PATH=.venv"

:: 检查上一级目录
if not defined VENV_PATH (
    if exist "..\venv\Scripts\activate.bat" set "VENV_PATH=..\venv"
    if exist "..\.venv\Scripts\activate.bat" set "VENV_PATH=..\.venv"
)

:: 如果没找到，跳转到错误处理
if not defined VENV_PATH goto ErrorVenv

:: ------------------------------------------------
:: 2. 寻找目标 Python 文件
:: ------------------------------------------------
set "TARGET_FILE=hok_streamlit.py"
set "RUN_FILE="

:: 检查当前目录
if exist "%TARGET_FILE%" set "RUN_FILE=%TARGET_FILE%"

:: 检查子目录 hok-rank
if not defined RUN_FILE (
    if exist "hok-rank\%TARGET_FILE%" set "RUN_FILE=hok-rank\%TARGET_FILE%"
)

:: 如果没找到，跳转到错误处理
if not defined RUN_FILE goto ErrorFile

:: ------------------------------------------------
:: 3. 启动流程
:: ------------------------------------------------
echo [√] 环境路径: %VENV_PATH%
echo [√] 目标文件: %RUN_FILE%
echo.
echo 正在启动...

:: 激活环境
call "%VENV_PATH%\Scripts\activate.bat"

:: 检查 streamlit
where streamlit >nul 2>nul
if %errorlevel% neq 0 goto ErrorStreamlit

:: 运行
streamlit run "%RUN_FILE%"

:: 正常结束
goto End

:: ------------------------------------------------
:: 错误处理模块 (使用 goto 避免路径符号导致闪退)
:: ------------------------------------------------
:ErrorVenv
echo.
echo [错误] 找不到虚拟环境文件夹 (venv 或 .venv)！
echo 请确认项目根目录或上级目录是否存在虚拟环境。
echo.
pause
exit /b

:ErrorFile
echo.
echo [错误] 找不到文件: %TARGET_FILE%
echo 请确认脚本位置是否正确。
echo.
pause
exit /b

:ErrorStreamlit
echo.
echo [严重错误] 激活环境后未找到 streamlit！
echo 请在 PyCharm 终端运行: pip install streamlit
echo.
pause
exit /b

:End
pause