@echo off
chcp 65001 >nul
cd /d "%~dp0"
where pyw >nul 2>nul && (start "" pyw -3 briefing_app.py & exit /b 0)
where pythonw >nul 2>nul && (start "" pythonw briefing_app.py & exit /b 0)
echo Python 3 is required. Install it from https://www.python.org/downloads/
echo (Python 3 설치가 필요합니다. 설치 시 "Add python.exe to PATH" 를 체크하세요.)
pause
