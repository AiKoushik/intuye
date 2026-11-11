@echo off
rem Double-click, or run from cmd. Passes arguments through, e.g.:  run-backend.bat -Model local -Test
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run-backend.ps1" %*
if errorlevel 1 pause
