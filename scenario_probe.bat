@echo off
chcp 65001 >nul
if not exist C:\KenshiModMap\state mkdir C:\KenshiModMap\state
>C:\KenshiModMap\state\scenario.txt echo probe
echo KMM: сценарий probe включён (state\scenario.txt). Начните НОВУЮ игру; шаги пишутся в logs\scenario.log
echo Выключить: scenario_off.bat
pause
