@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-Host.ps1"
set "hostExit=%ERRORLEVEL%"
pause
exit /b %hostExit%
