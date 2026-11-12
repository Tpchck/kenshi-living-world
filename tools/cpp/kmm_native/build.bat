@echo off
rem KMM_Native build (Windows SDK 7.1 + VC++ 2010 SP1 x64).
rem kmm_native.cpp: no Boost, src\kenshi_decl.h declares only what it uses.
rem salvage.cpp (2.4): full KenshiLib + MyGUI + Ogre headers (needs Boost 1.60 headers, like build_verify.bat); links MyGUIEngine_x64 / OgreMain_x64 import libs.
call "C:\Program Files\Microsoft SDKs\Windows\v7.1\Bin\SetEnv.cmd" /x64 /Release >nul 2>&1
set HERE=%~dp0
set OUT=%HERE%out
set KL=C:\KenshiModMap\tools\ref\KenshiLib
if not exist "%OUT%" mkdir "%OUT%"
cl /nologo /c /W3 /O2 /MD /EHsc /D_WIN32_WINNT=0x0601 /DNDEBUG /I"C:\KenshiModMap\tools\cpp\compat" /I"%HERE%third_party" /I"%HERE%src" /Fo"%OUT%\kmm_native.obj" "%HERE%src\kmm_native.cpp"
if errorlevel 1 exit /b 1
cl /nologo /c /W3 /O2 /MD /EHsc /D_WIN32_WINNT=0x0601 /DNDEBUG /DBOOST_ALL_NO_LIB /DBOOST_ERROR_CODE_HEADER_ONLY /DBOOST_SYSTEM_NO_DEPRECATED /DUNICODE /D_UNICODE /I"C:\KenshiModMap\tools\cpp\compat" /I"C:\KenshiModMap\tools\cpp\deps\boost_1_60_0" /I"%KL%\Include" /I"%HERE%src" /Fo"%OUT%\salvage.obj" "%HERE%src\salvage.cpp"
if errorlevel 1 exit /b 1
link /nologo /DLL /MACHINE:X64 /OUT:"%OUT%\KMM_Native.dll" /IMPLIB:"%OUT%\KMM_Native.lib" /PDB:"%OUT%\KMM_Native.pdb" /OPT:REF /OPT:ICF "%OUT%\kmm_native.obj" "%OUT%\salvage.obj" "C:\KenshiModMap\tools\cpp\lib\KenshiLib.lib" "%KL%\Libraries\mygui\MyGUIEngine_x64.lib" "%KL%\Libraries\ogre\OgreMain_x64.lib" kernel32.lib user32.lib
if errorlevel 1 exit /b 1
if exist "C:\KenshiModMap\build\KMM_Native" copy /y "%OUT%\KMM_Native.dll" "C:\KenshiModMap\build\KMM_Native\KMM_Native.dll" >nul
echo BUILD OK
