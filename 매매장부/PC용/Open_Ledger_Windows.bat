@echo off
rem Opens the ledger (the .html file next to this script) in Chrome or Edge.
cd /d "%~dp0"
set "FILE="
for %%f in (*.html) do if not defined FILE set "FILE=%%~ff"
if not defined FILE (
  echo No .html file was found next to this script.
  pause
  exit /b 1
)
set "BROWSER="
call :try "%ProgramFiles%\Google\Chrome\Application\chrome.exe"
call :try "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
call :try "%LocalAppData%\Google\Chrome\Application\chrome.exe"
call :try "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
call :try "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"
if defined BROWSER (
  start "" "%BROWSER%" "%FILE%"
) else (
  start "" "%FILE%"
)
exit /b 0
:try
if not defined BROWSER if exist %1 set "BROWSER=%~1"
exit /b 0
