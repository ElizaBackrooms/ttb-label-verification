@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo First-time setup required. Running setup.bat...
    call "%~dp0setup.bat"
)

call ".venv\Scripts\activate.bat"

echo.
echo Starting TTB Label Verification Assistant...
echo Your browser should open to http://localhost:8501
echo Press Ctrl+C in this window to stop the app.
echo.

python -m streamlit run app.py --server.headless false

if errorlevel 1 (
    echo.
    echo Something went wrong. Try running setup.bat first.
    pause
)
