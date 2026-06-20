@echo off
setlocal
cd /d "%~dp0"

echo.
echo TTB Label Verification - First-time setup
echo ==========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed.
    echo Install Python 3.11+ from https://www.python.org/downloads/
    echo Check "Add Python to PATH" during install, then run this file again.
    pause
    exit /b 1
)

echo [1/3] Creating virtual environment...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
)

echo [2/3] Installing Python packages...
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Checking Tesseract OCR...
where tesseract >nul 2>&1
if errorlevel 1 (
    if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
        echo Tesseract found in Program Files.
    ) else (
        echo.
        echo Tesseract is NOT installed yet. Install it with:
        echo   winget install UB-Mannheim.TesseractOCR
        echo.
        echo Or download from:
        echo   https://github.com/UB-Mannheim/tesseract/wiki
        echo.
    )
) else (
    tesseract --version
)

echo.
echo Setup complete.
echo Next: double-click run.bat to open the app in your browser.
echo.
pause
