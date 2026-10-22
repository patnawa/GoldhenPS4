@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Network-Access.ps1" -Remove
pause
