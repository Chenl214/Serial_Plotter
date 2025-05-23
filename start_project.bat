@echo off
:: Simple startup script (ANSI encoded)
:: Avoids all non-ASCII characters

echo === Script Start ===
echo Current dir: %cd%
echo Script path: %~f0
echo.

:: Step 1 - Check Python
echo [1] Checking Python...
python --version
if errorlevel 1 (
    echo ERROR: Python not found
    pause
    exit /b 1
)
echo.

:: Step 2 - Set codepage
echo [2] Setting console codepage...
chcp 936 > nul
echo Current codepage:
chcp
echo.

:: Step 3 - Check dependencies
echo [3] Checking required Python packages...
echo Checking installed packages...
python -m pip list
echo.
echo Verifying required packages...
python -c "try: import numpy, pandas; print('SUCCESS: Required packages are installed'); exit(0)\
except ImportError as e: print(f'ERROR: Missing package: {e.name}'); exit(1)"
if errorlevel 1 (
    echo.
    echo WARNING: Some required packages are missing
    echo Installing required packages automatically...
    python -m pip install numpy pandas
    if errorlevel 1 (
        echo ERROR: Failed to install packages
        pause
        exit /b 1
    )
    echo Packages installed successfully
    echo.
)

:run_app
:: Step 4 - Run application
echo [3] Starting main.py...
echo Executing: python main.py
echo ========================
python main.py
set exit_code=%errorlevel%
echo ========================
if %exit_code% equ 0 (
    echo SUCCESS - Plotter window was closed normally
) else (
    echo FAILED - Program exited abnormally (code %exit_code%)
)
pause