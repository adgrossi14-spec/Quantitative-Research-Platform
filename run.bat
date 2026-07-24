@echo off
REM Launch the Stock Forecaster dashboard in your browser.
cd /d "%~dp0"
".venv\Scripts\python.exe" -m streamlit run app.py
pause
