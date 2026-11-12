@echo off
call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.cmd" /x64 /Release >nul 2>&1
set HERE=%~dp0
if not exist "%HERE%out" mkdir "%HERE%out"
cl /nologo /c /W3 /O2 /MD /EHsc /DBOOST_ALL_NO_LIB /DUNICODE /D_UNICODE /wd4482 /DKMM_LEKTOR_COUNT_OFF=8 /DKMM_LEKTOR_STUFF_OFF=16 /I"C:\KenshiModMap\tools\cpp\compat" /I"C:\KenshiModMap\tools\cpp\deps\boost_1_60_0" /I"C:\KenshiModMap\tools\ref\KenshiLib\Include" /Fo"%HERE%out\verify.obj" "%HERE%src\verify_headers.cpp"
