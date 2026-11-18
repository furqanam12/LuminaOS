@echo off
title LuminaOS Terminal (Linux)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0LuminaOS Terminal.ps1" %*
if errorlevel 1 (
  echo.
  pause
)
