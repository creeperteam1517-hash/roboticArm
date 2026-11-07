@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\test_servo.ps1" %*
