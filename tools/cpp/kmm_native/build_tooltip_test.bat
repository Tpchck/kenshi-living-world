@echo off
rem Offline unit test of src\tooltip_compact.h (no game, no KenshiLib). Same toolchain / CRT as the plugin.
call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.cmd" /x64 /Release >nul 2>&1
set HERE=%~dp0
if not exist "%HERE%out" mkdir "%HERE%out"
cl /nologo /W3 /O2 /MD /EHsc /DNDEBUG /I"C:\KenshiModMap\tools\cpp\compat" /I"%HERE%src" /Fo"%HERE%out\test_tooltip.obj" /Fe"%HERE%out\test_tooltip.exe" "%HERE%src\test_tooltip.cpp" /link /MACHINE:X64
if errorlevel 1 exit /b 1
"%HERE%out\test_tooltip.exe"
exit /b %errorlevel%
