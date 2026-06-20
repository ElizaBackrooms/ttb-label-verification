@echo off
setlocal
cd /d "%~dp0"

echo.
echo ============================================================
echo   TTB Label Verification - FIRST-TIME SETUP
echo   (You only need to do this once.)
echo ============================================================
echo.
echo This installs the tools the app needs on YOUR computer.
echo You do NOT need an API key or internet account to use the app.
echo.
pause

where python >nul 2>&1
if errorlevel 1 (
    echo.
    echo *** PYTHON IS NOT INSTALLED ***
    echo.
    echo 1. Go to https://www.python.org/downloads/
    echo 2. Download and run the installer
    echo 3. CHECK THE BOX: "Add python.exe to PATH"
    echo 4. Run this file again
    echo.
    pause
    exit /b 1
)

echo Step 1 of 3: Preparing the app folder...
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv
    echo   Done - created a private copy of Python for this app.
) else (
    echo   Already set up - skipping.
)

echo.
echo Step 2 of 3: Downloading required components...
echo   (This may take a few minutes the first time.)
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip >nul
pip install -r requirements.txt
echo   Done.

echo.
echo Optional: Enhanced AI mode (Option B - Azure/OpenAI)?
echo   If you have Azure or OpenAI keys, you can install cloud packages now.
echo   Press Y to install, or any other key to skip (local mode still works).
choice /C YN /M "Install Option B packages"
if errorlevel 2 goto skip_option_b
if errorlevel 1 (
    echo   Installing Option B packages...
    pip install -r requirements-option-b.txt
    echo   Done. Copy .env.example to .env and add your keys - see README Option B section.
)
:skip_option_b

echo.
echo Step 3 of 3: Checking the label text reader (Tesseract)...
set TESS_OK=0
where tesseract >nul 2>&1 && set TESS_OK=1
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" set TESS_OK=1

if "%TESS_OK%"=="0" (
    echo.
    echo *** TESSERACT IS NOT INSTALLED YET ***
    echo.
    echo The app cannot read label photos without it.
    echo.
    echo Ask IT to run this command, or open PowerShell yourself:
    echo   winget install UB-Mannheim.TesseractOCR
    echo.
    echo After that, double-click run.bat
    echo.
) else (
    echo   Label reader is installed. Good to go.
)

echo.
echo ============================================================
echo   SETUP COMPLETE
echo.
echo   Next step: double-click  run.bat  to open the app.
echo   Tip: print START_HERE.txt and keep it at your desk.
echo ============================================================
echo.
pause
