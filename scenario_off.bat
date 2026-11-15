@echo off
chcp 65001 >nul
if exist C:\KenshiModMap\state\scenario.txt del /q C:\KenshiModMap\state\scenario.txt
echo KMM: тестовые сценарии выключены (state\scenario.txt удалён). Для чистого прохождения начните НОВУЮ игру.
pause
