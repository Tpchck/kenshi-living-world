@echo off
call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.cmd" /x64 /Release >nul 2>&1
cd /d C:\KenshiModMap\tools\cpp\lib
lib /nologo /def:KenshiLib.def /machine:x64 /out:KenshiLib.lib
echo rc=%ERRORLEVEL%
