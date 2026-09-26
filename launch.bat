@echo off
chcp 65001 >nul

:: If the venv folder does not exist, automatically run venv.bat first
if not exist venv (
    echo First-time run detected: Virtual environment not found. Installing automatically...
    call venv.bat
)

echo Starting system...
call venv\Scripts\activate
python app.py
pause