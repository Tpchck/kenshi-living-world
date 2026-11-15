@echo off
chcp 65001 >nul
if not exist C:\KenshiModMap\state mkdir C:\KenshiModMap\state
>C:\KenshiModMap\state\scenario.txt echo bar
echo KMM: сценарий bar включён (state\scenario.txt). Начните НОВУЮ игру; шаги пишутся в logs\scenario.log
echo Выключить: scenario_off.bat
pause
