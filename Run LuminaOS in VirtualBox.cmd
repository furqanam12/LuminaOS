@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run LuminaOS in VirtualBox.ps1" %*
if errorlevel 1 (
  echo.
  pause
)
