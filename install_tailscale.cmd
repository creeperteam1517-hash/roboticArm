@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\install_tailscale.ps1" %*
