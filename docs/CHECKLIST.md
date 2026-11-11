# CHECKLIST — перед любой сборкой/тестом (ввёл после промаха с RE_Kenshi, 2026-11-11)
0. ОБЯЗАТЕЛЬНО: `python -I -X utf8 tools\verify_all.py` (~2 мин): окружение (exe 1.0.65, RE_Kenshi/KenshiLib, KenshiLua), все test_*.py, lua_lint, mods_cfg check, test_conflict (должен остановить сборку), холостой kmm_build. Итог OK/FAIL. `kmm_build.py --install` вызывает его сам и при FAIL не ставит (--no-verify только для отладки). После игры: `python tools\health.py`.
1. Зависимости рантайма: RE_Kenshi, KenshiLib, CTD fix, плагины (Plugins_x64.cfg, RE_Kenshi.json) — установлены ли? Какие моды сборки их требуют?
2. Зависимости модов — ТОЛЬКО офлайн: поля dependencies/references в заголовках .mod через kmod.py (есть ли каждый в mods.cfg и стоит ли выше зависимого). Страницы Workshop не парсить.
3. Версия игры 1.0.68 Steam — совместимость каждого плагина.
4. Отсутствующие строки mods.cfg (мод в списке, но нет на диске).
5. Бэкап: mods.cfg, Plugins_x64.cfg, kenshi.cfg, kenshi_x64.exe — до изменений.
6. Наблюдатель логов запущен до старта игры.
7. Откат описан одной командой.
Правило: проверка ≤ 1–2 минуты. Если пункт требует обхода сети по сотням страниц — пропустить и записать как риск.
Необязательно (≈10 с, офлайн): `python -I -X utf8 tools\dedup_report.py` — клоны предметов, полностью перекрытые моды, остатки пустых разделителей (docs\DEDUP.md).
