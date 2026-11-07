@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\arm.ps1" %*
