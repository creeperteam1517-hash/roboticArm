@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\setup_ssh.ps1" %*
