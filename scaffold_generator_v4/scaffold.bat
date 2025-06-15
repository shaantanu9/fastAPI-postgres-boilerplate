@echo off
REM Scaffold v4 Global Command Script for Windows
REM This script allows running scaffold from anywhere

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"

REM Change to scaffold directory and run main.py
cd /d "%SCRIPT_DIR%" && python main.py %* 