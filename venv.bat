@echo off
chcp 65001 >nul

echo ========================================================
echo   AI Vocal Separation & Multi-Track System - Setup Tool
echo ========================================================

:: 1. Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [Error] Python not found! Please install Python 3.8 or above and check "Add Python to PATH".
    pause
    exit /b
)

:: 2. Create virtual environment
if not exist venv (
    echo [1/3] Creating Python virtual environment (venv)...
    python -m venv venv
) else (
    echo [1/3] 'venv' folder already exists, skipping creation.
)

:: 3. Activate virtual environment and upgrade pip
echo [2/3] Activating virtual environment and upgrading pip...
call venv\Scripts\activate
python -m pip install --upgrade pip

:: 4. Install dependencies from requirements.txt
echo [3/3] Installing required AI packages (this may take a few minutes)...
pip install -r requirements.txt

echo.
echo ========================================================
echo 🎉 Virtual environment and package installation complete!
echo You can now run launch.bat to start the application.
echo ========================================================
pause