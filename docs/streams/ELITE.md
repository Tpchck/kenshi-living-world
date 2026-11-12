# Поток ELITE - элитные гвардии

Данные: `tools/streams/elite.py` + `rules/streams/elite.json` -> `KMM_Elite.mod` (только новые записи: 6 CHARACTER, 2 SQUAD_TEMPLATE) и `build/KMM_Elite/scripts/kmm_elite_data.lua`.
Lua: `build/KMM_Elite/scripts/init/kmm_elite.lua` (ленивый старт, тик charsUpdate через guarded).

Подразделения:
- **Tenka Gusoku Guard** (United Cities): сверхтяжёлая самурайская броня гусоку (Samurai Armor - Superheavy, шлемы Taisho/Shosa, плащ императора), нодати (Greater Nodachi, Sugoi Nagai Katana).
- **Phoenix Seraphs** (The Holy Nation): латы Феникса (Phoenix Plate/Helmet/Cuisses/Greaves, плащ Holy Lord), Pilgrim's Nodachi, Paladin's Heavy Cross, Great Sabre.

Состав отряда: 1 Captain (combat 86) + 2-3 Guard (66) + 1-2 Veteran (76). Вещи не WH, не из catalog_excluded (проверяется при сборке).

Условия спавна: >= 2 года (720 дней), фракция жива, wealth >= 1.5 x wealth0, know >= 1.5 (если поля нет - только богатство), город фракции в 6000 от игрока,
кулдаун фракции 20 дней, не более 1 живого элитного отряда. Событие `elite_seen {a, town_name}` для слухов.

Проверки: `python -I -X utf8 tools/streams/elite.py --check [--write]`; `python -I -X utf8 build/KMM_Elite/_dev/test_elite.py`; `tools/build/lua_lint.py`.
