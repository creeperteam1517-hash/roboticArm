@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\remote_token.ps1" %*
