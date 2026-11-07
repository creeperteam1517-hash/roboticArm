@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\set_keys.ps1" %*
