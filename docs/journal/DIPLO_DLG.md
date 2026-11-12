# DIPLO_DLG — посланники без торговцев и дерево диалога в два подменю (2026-11-12)

Баг из игры: у Бармена в Хабе в диалоге семь веток дипломатии и нет торговли.

## Причина
Поток diplo вешал ссылку CHARACTER "dialogue" -> DIALOGUE "KMM Diplomacy" (score bonus 100, условие «target has item = Envoy's Seal») на 142 персонажей,
среди них генерик-торговцы (Barman 1187, Swamper/Mourn/Crab Barman, Slave Trader 5288, UC Construction Trader, Fish and Drugs Seller...).
Родной разговор торговца (пакет shopkeep -> DIALOGUE trader1, v0=1, в нём DIALOG_ACTION «action name»=1 = DA_TRADE) проигрывал по score.
Как именно движок выбирает среди нескольких PLAYER_TALK_TO_ME, в docs/ проекта не описано; предположение (не проверено в игре): побеждает больший score bonus среди подходящих по условиям.

## Что сделано
1. Отбор посланников (tools/streams/diplo.py, rules/streams/diplo.json, секция envoys):
   - исключаются имена по `exclude_name_regex` (barman|bartender|barkeep|trader|seller|merchant|shopkeep|vendor|dealer|innkeeper|peddler|smuggler|caravan);
   - исключаются персонажи, у которых в «dialogue package» (рекурсивно по inheritsFrom) или в собственных «dialogue» есть разговор с v0=1 (PLAYER_TALK_TO_ME), в чьём дереве реплик есть эффект DA_TRADE (`exclude_trade_dialog`);
   - если у фракции посланников не осталось — остаётся без них; торговцев взамен не назначаем. Данные для Lua (kmm_diplo_data.lua) генерятся тем же потоком.
2. Родной разговор оставшихся посланников: вставить в наше дерево ссылку на родные DIALOGUE_LINE нельзя без привязки к каждому персонажу (у каждого пакета свои реплики, условия и speaker; одна общая реплика-выход на «их обычные дела» невозможна). Оставлены уникальные лидеры/знать/главари без торговли (её у них и не было). Выход к родному разговору: убрать «Envoy's Seal» (описание предмета говорит об этом) или «Прощай». Остальные родные v0=1 диалоги у оставшихся — реакции/рекрутинг/«shoo», без торговли.
3. Дерево KMM Diplomacy: корень (приветствие NPC) -> 4 реплики игрока:
   «Let us talk about treaties.» (подменю: non-aggression, trade agreement, alliance, fealty, «Never mind»),
   «Let us talk about tribute.» (подменю: demand vassal, demand tribute, pay tribute [жетон liege_due, деньги], collect tribute [жетон vassal_due], «Never mind»),
   «Our pact is over.» (жетон has_pact), «Farewell.»
   «Never mind» -> NPC «Is there anything else?» -> «Farewell.» (role close). Циклов в дереве нет (возврата в меню нет — осознанно).
   Условия, эффекты, run lua script, тексты ответов не менялись.
4. Lua: kmm_diplo_line.lua / kmm_diplo.lua не менялись. Мост ищет реплику по id (D.lines[sid]) и роли open/propose/commit/close, позиция в дереве не используется. on_open срабатывает на приветствии (до подменю), жетоны живут token_ttl_seconds=90.

## Бэкапы
tools/streams/_bak/diplo.py_pre_dlg, rules/streams/diplo.json_pre_dlg, build/KMM_Diplo/_dev/KMM_Diplo.mod.pre_dlg, build/KMM_Diplo/_dev/kmm_diplo_data.lua.pre_dlg.txt.

## Проверки
- kmm_build.py --write diplo: 0 ошибок; tools/streams/_diplo_check.py: 0 ошибок fcsdef, 0 конфликтов.
- tools/streams/_diplo_dlg_check.py: OK (нет посланника с торговым пакетом/торговым именем, корень 4 реплики, id в data.lua есть в моде).
- build/KMM_Diplo/_dev/test_diplo.py: 36 passed, 0 failed. tools/build/lua_lint.py: 0 нарушений.
- Посланников 142 -> 125; фракций с данными 52 -> 49 (без посланника: Shinobi Thieves, Skin Bandits, Trade Ninjas).
