# NATIVE2 (2026-11-12)
- Итог: KMM_Native 2.0.0: добавлен faction_force (чтение, SEH, флаг faction_force=true), unique_set не реализован (флаг false, только лог), orderSquad только исследование. Подробности в docs\PLUGIN.md (NATIVE2).
- Файлы: tools\cpp\kmm_native\src\kmm_native.cpp, kenshi_decl.h, verify_headers.cpp (статические проверки смещений), build_verify.bat, test_adapter.py; build\KMM_Native (DLL, kmm_native.json, KMM_Native.lua).
- Сборка: build.bat BUILD OK без предупреждений; build_verify.bat без ошибок и предупреждений; test_adapter.py 5/5.
- Игру не запускали; запрещённые файлы не менялись.
