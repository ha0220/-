@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo === Stock price helper ===
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 fetch_prices.py %*
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    python fetch_prices.py %*
  ) else (
    echo Python is not installed. Install it from https://www.python.org/downloads/ and check "Add python.exe to PATH".
  )
)
echo.
pause
