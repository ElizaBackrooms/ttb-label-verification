@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo.
    echo First-time setup is required.
    echo.
    call "%~dp0setup.bat"
)

call ".venv\Scripts\activate.bat"

echo.
echo ============================================================
echo   TTB Label Verification Assistant is starting...
echo.
echo   Your browser should open automatically.
echo   If it does not, go to:  http://localhost:8501
echo.
echo   LEAVE THIS WINDOW OPEN while you use the app.
echo   To quit: close this window or press Ctrl+C
echo ============================================================
echo.

python -m streamlit run app.py --server.headless false

if errorlevel 1 (
    echo.
    echo Something went wrong.
    echo Try double-clicking setup.bat first, then run.bat again.
    echo.
    pause
)
