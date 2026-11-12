@echo off
chcp 65001 >nul
cd /d C:\KenshiModMap
python tools\release.py safe
pause
