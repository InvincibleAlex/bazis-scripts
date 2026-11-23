@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Configureaza acces baza.ps1"
if errorlevel 1 pause
