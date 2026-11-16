"""Отчёт после игровой сессии (только чтение, игру не запускает): одна команда вместо ручного разбора.
python tools\\session_report.py   -> печать + logs\\session_last.txt
Разделы: health (логи, краши, отключения модулей); самопроверка (KMM_Probe: fail/absent, итог, сравнение с прошлой сессией); активность модулей по debug.log/chronicle за последнюю сессию;
память (logs\\mem.csv); одежда NPC по свежему сейву (save_report).
Маркеры: [+] подтверждено, [!] СЛОМАНО (явный отказ в логе), [0] строки есть, но значение везде 0, [ ] строк нет; ≈ — лог без меток
времени посчитан целиком. Логи без меток (predators, chronicle) режутся по размеру на момент прошлого отчёта (logs/session_offsets.json).
Всплески >= 5 одинаковых строк в секунду (офлайн-тесты) в счёт не идут. Маркеры сверяет с исходниками tools/test/test_session_report.py.
  --no-offsets   не записывать размеры логов (повторный разбор той же сессии)"""
import collections
import datetime
import glob
import json
import os
import re
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"C:\KenshiModMap"
LOGS = os.path.join(ROOT, "logs")
LUALOG = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\logs\KenshiLua.log"
PY = [sys.executable, "-I", "-X", "utf8"]


def run(script):
    r = subprocess.run(PY + [os.path.join(ROOT, "tools", script)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def session_start():
    """Начало последней сессии = время первой строки KenshiLua.log (лог пишется заново при каждом запуске)."""
    try:
        first = open(LUALOG, encoding="utf-8", errors="replace").readline()
        return datetime.datetime.strptime(first[:19], "%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def activity(t0):
    out = []
    p = os.path.join(LOGS, "debug.log")
    tags = collections.Counter()
    if os.path.exists(p):
        for l in open(p, encoding="utf-8", errors="replace"):
            try:
                t = datetime.datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if t0 and t < t0:
                continue
            m = re.match(r".{19} \[(\w+)\] (\w+)", l)
            if m:
                tags[m.group(1) + " " + m.group(2)] += 1
    out.append("debug.log за сессию: " + (", ".join(f"{k} x{v}" for k, v in tags.most_common(14)) or "пусто"))
    out += health_registry(t0)
    p = os.path.join(LOGS, "chronicle.log")
    if os.path.exists(p):
        kinds = collections.Counter(l.split("\t")[2] for l in open(p, encoding="utf-8", errors="replace") if l.count("\t") >= 3)
        out.append("хроника мира (типы событий): " + ", ".join(f"{k} {v}" for k, v in kinds.most_common(12)))
    lua = "\n".join(session_lines("KenshiLua.log", t0)[0])
    out.append(f"KenshiLua: реплик диалогового моста {lua.count('DialogueScriptBridge: Triggered')}, решений дипломатии {lua.count('[KMM_Diplo] decision')}, "
               f"ошибок {len(re.findall(r'(?i)error|attempt to|bad argument', lua))}")
    return out


STATE = os.path.join(ROOT, "state")
# что должно появиться в логах, если модуль реально работает в игре (файл, подстрока, смысл)
MARKERS = [
    ("debug.log", ": OFF (", "ВНИМАНИЕ: реестр здоровья выключил механику навсегда (noapi/crash) — смотреть строку"),
    ("debug.log", "-> pause", "ПАУЗА: реестр здоровья — отказ механики, пауза и повтор (не навсегда)"),
    ("tempo.log", "PAUSED", "ПАУЗА: темп лавок — отказ шага, пауза реестра"),
    ("debug.log", "recovered after", "реестр здоровья: механика восстановилась после паузы"),
    ("debug.log", "health: ok", "реестр здоровья: сводка KMM_Gov (есть механики не в ok)"),
    ("probe.log", "PROBE summary", "самопроверка: проход завершён (итог ok/fail/absent — раздел «Самопроверка»)"),
    ("probe.log", "PROBE internal fail", "ВНИМАНИЕ: модуль самопроверки выключился ошибкой"),
    ("debug.log", "override registered at load", "побеждённый лежит: перехват ядра зарегистрирован при загрузке"),
    ("debug.log", "override calls=", "побеждённый лежит: сколько раз ядро спросило (calls>0 и asks>0 — окно работает)", r"override calls=(\d+)"),
    ("debug.log", "dropped:", "след Traces отменён: игрок ушёл от места планирования"),
    ("debug.log", "herald said:", "глашатай: житель сказал игроку о событии мира (ok=)"),
    ("debug.log", "PACE: player squad down", "темп: отряд игрока лёг — враждебные встречи ждут"),
    ("predators.log", "smell skipped (attack_on_player)", "запах: удар по игроку не оставил запаха (причина в строке)"),
    ("nemesis.log", "beaten:", "побеждённый: персонаж игрока лёг — кто победил (соперник из этого или нет)"),
    ("nemesis.log", "-> contempt", "соперник презрел слабый отряд игрока без добычи (ушёл, не напал)"),
    ("predators.log", "smell api ok", "запах крови/трупов работает"),
    ("predators.log", "soul echo: death", "эхо павших: смерти копятся у места бойни"),
    ("predators.log", "soul echo", "эхо павших: Soulbodies пришли к месту бойни ночью (spawned/request)"),
    ("scenario.log", "done: ok=", "тест-сценарий: итог шагов ok/fail/skip"),
    ("scenario.log", "FAIL ", "тест-сценарий: шаг не прошёл — смотреть строку"),
    ("scenario.log", ": OFF", "ВНИМАНИЕ: модуль выключен (сводка probe)"),
    ("debug.log", "PROSPERITY disabled forever", "ВНИМАНИЕ: вызов процветания уронил игру в прошлый раз — выключен навсегда"),
    ("relicrace.log", "ruinloot probe", "руины: проба переноса/удаления лута из ящиков ok/FAIL"),
    ("relicrace.log", "ruinloot moved", "руины: искатели вынесли лут — он у лидера (убей и забери)"),
    ("relicrace.log", "ruinloot removed", "руины: экспедиция вскрыла руины — ящики беднеют"),
    ("relicrace.log", "DISABLED forever", "ВНИМАНИЕ: разбор руин выключен навсегда"),
    ("relicrace.log", "free containers", "руины: ящиков без хозяина у места (0 при owned>0 — разбор руин пуст)", r"free containers (\d+)"),
    ("debug.log", "KO hold:", "окно после нокаута: побеждённый не встаёт (связать/обыскать/добить)"),
    ("debug.log", "KO release:", "окно после нокаута: отпущен (asks= — частота override ядра)", r"asks=(\d+)"),
    ("KenshiLua.log", "DUEL offer added", "поединок: лидерам-конкурентам добавлена реплика вызова"),
    ("KenshiLua.log", "DUEL start", "поединок: вызов принят, бой до нокаута"),
    ("KenshiLua.log", "DUEL end", "поединок: исход (победа/поражение/убийство/таймаут)"),
    ("KenshiLua.log", "DUEL clear", "поединок: временная вражда снята"),
    ("debug.log", "PROSPERITY probe", "процветание: проба notifySquadDefeated ok/FAIL"),
    ("debug.log", "PROSPERITY defeated:", "процветание: разгром отряда снизил процветание фракции в ядре"),
    ("debug.log", "PROSPERITY no effect", "процветание: вызов ядра без эффекта — вызовы прекращены"),
    ("deeds.log", "notifyCrimeWitnessed hook registered", "свидетели: колбэк ядра подключён"),
    ("deeds.log", "crime seen:", "свидетели: ядро засекло преступление игрока"),
    ("deeds.log", "witness:", "свидетели: дело игрока seen/unseen (без свидетеля — нет слуха и памяти)"),
    ("nemesis.log", "appraise: app=", "соперник оценил видимую силу отряда игрока -> attack/parley/withdraw"),
    ("nemesis.log", "appraise: off until restart", "ВНИМАНИЕ: оценка силы соперником выключена"),
    ("predators.log", "squadjob ok", "засада: отряд держит участок дороги нарядом ядра (addSquadJob, подтверждено через час игры)"),
    ("predators.log", "squadjob drift", "засада: отряд ушёл с участка — наряд не держит, возврат addOrder"),
    ("predators.log", "squadjob release", "засада: срок вышел, отряд вернулся к своему пакету"),
    ("predators.log", "squadjob FAIL", "засада: наряд не встал — старый addOrder"),
    ("recruitrace.log", "merc hired", "перекупка наёмников: конкурент нанял охрану (setContractJob)"),
    ("recruitrace.log", "contract FAIL", "перекупка наёмников: контракт не встал"),
    ("recruitrace.log", "slave bought", "невольничий рынок: конкурент забрал сильного раба (changeSlaveOwner)"),
    ("recruitrace.log", "slave freed by player", "невольничий рынок: игрок освободил купленного раба"),
    ("recruitrace.log", "disabled", "ВНИМАНИЕ: рычаг гонки за людьми выключен"),
    ("outlaws.log", "captive scan:", "перехват пленника: читается ли isCarryingSomething (сколько NPC проверено)"),
    ("outlaws.log", "captive carried", "перехват пленника: охотник несёт разыскиваемого — слух"),
    ("outlaws.log", "captive taken", "перехват пленника: игрок отбил пленника у охотника"),
    ("outlaws.log", "captive watch disabled", "ВНИМАНИЕ: перехват пленника выключился ошибкой"),
    ("recruitrace.log", "race start", "гонка за рекрутом: конкурент положил глаз на лучшего рекрута бара"),
    ("recruitrace.log", "recruit taken", "гонка за рекрутом: конкурент увёл рекрута (setFaction)"),
    ("recruitrace.log", "recruit cancel by player", "гонка за рекрутом: игрок нанял первым"),
    ("recruitrace.log", "setFaction FAIL", "ВНИМАНИЕ: setFaction не сработал — гонка выключена (state/recruitrace.off)"),
    ("debug.log", ": pkg ok", "отряды Traces: ванильный пакет ИИ поставлен (ядро ведёт к цели)"),
    ("debug.log", "engine keeps the squad off-screen", "отряды Traces: караван/беженцы стали постоянными (живут вне видимости)"),
    ("debug.log", "native error:", "ВНИМАНИЕ: ошибка в ведении отрядов Traces ядром"),
    ("debug.log", "campaign: base outcome", "рейд на базу: исход кампании (repelled/sacked/unattended)"),
    ("debug.log", "-> Traces raid", "рейд на базу: кампания не пошла — старый спавн"),
    ("stock.log", "U3 starve", "голод города: производственная постройка остановлена (ванильный STARVED)"),
    ("stock.log", "U3 restore", "голод города: постройка снова работает (изобилие/уход игрока)"),
    ("stock.log", "kept=", "голод города: держит ли движок записанное состояние (kept/flipped)"),
    ("stock.log", "U3 off", "ВНИМАНИЕ: голод построек выключился ошибкой"),
    ("tempo.log", "RESTOCK shift", "лавки: пополнение ускорено/замедлено по богатству города"),
    ("tempo.log", "RESTOCK day", "лавки: сводка за день (restamped>0 — ваниль переставляет таймер)"),
    ("tempo.log", "DISABLED restock", "ВНИМАНИЕ: управление пополнением лавок выключилось ошибкой"),
    ("outlaws.log", "persistent orphan", "постоянный отряд-сирота отпущен/забыт"),
    ("outlaws.log", "world changed", "смена мира: живые отряды и таймеры подхвата сброшены"),
    ("fates.log", "world changed", "судьбы: смена мира, живые отряды сброшены"),
    ("KenshiLua.log", "DIPLO_RIVAL world changed", "диалоги: смена мира, отряды прошлого мира не вызываются"),
    ("debug.log", "[KMM_Gov] summary:", "нагрузка: сводка снимка NPC (сборки/с, стоимость, переиспользование)"),
    ("debug.log", "[KMM_Gov] modules:", "нагрузка по модулям: средняя/пик мс и доля троттлинга"),
    ("debug.log", "set:has unavailable", "нагрузка: проверка снимка недоступна — правило одного кадра"),
    ("debug.log", "DIPLO_COND hook live", "диалоги: перехват условий ядра работает (реплики по состоянию мира)"),
    ("debug.log", "DIPLO_COND fallback", "диалоги: перехват не работает — Diplo вернулся к жетонам"),
    ("debug.log", "DIPLO_WORLD town=", "диалоги: флаги мира для города игрока (голод/осада/беспорядки/соперник)"),
    ("debug.log", "DIPLO_COND stats:", "диалоги: счётчики перехвата условий (calls/cond6/reserved)", r"DIPLO_COND stats: calls=(\d+)"),
    ("debug.log", "DIPLO_COND asked", "диалоги: ядро спросило зарезервированный код условия мира"),
    ("KenshiLua.log", "DIPLO_RIVAL threat talk added", "диалоги: соперник получил ванильный разговор-угрозу"),
    ("outlaws.log", "persistent ok", "банда стала постоянным отрядом движка (живёт вне видимости)"),
    ("outlaws.log", "persistent FAIL", "банда осталась временным отрядом — setPersistentSquad не сработал"),
    ("outlaws.log", "package ok", "банде задан ванильный пакет ИИ (рэкет/бродяги/охота)"),
    ("outlaws.log", "package FAIL", "ванильный пакет ИИ банде не задан — смотреть причину"),
    ("nemesis.log", "persistent ok", "соперник стал постоянным отрядом движка"),
    ("nemesis.log", "package ok", "соперник получил ванильный пакет охоты на игрока"),
    ("fates.log", "deed bounty +", "судьбы: дело конкурента подняло его награду"),
    ("fates.log", "justice:", "судьбы: конкурент пойман, награда закрыта"),
    ("fates.log", "memory LT_", "судьбы: конкурент запомнил игрока при повторной встрече"),
    ("fates.log", "link idle", "ВНИМАНИЕ: связка судеб с Outlaws/Nemesis не активна"),
    ("debug.log", "CORESYNC steps=", "модель мира сверяется с ядром: сила/процветание/владельцы городов"),
    ("debug.log", "CORESYNC town owner differs", "расхождение владельца города: модель дирижёра vs ядро"),
    ("debug.log", "CORESYNC disabled until restart", "ВНИМАНИЕ: сверка с ядром выключилась ошибкой — модель живёт сама"),
    ("debug.log", "TGM write OK", "цены города: запись в родную таблицу tradeGoodsMults сработала"),
    ("debug.log", "TGM write FAIL", "цены города: запись не прошла — работает старый множитель торговца"),
    ("debug.log", "TGM town", "цены города изменились от склада (дефицит/избыток/осада)"),
    ("debug.log", "TGM persist", "цены города: сохраняет ли движок их в сейве"),
    ("rumors.log", "map place ok", "слух-наводка: место открыто на ванильной карте"),
    ("rumors.log", "map squad ok", "слух-наводка: отряд разыскиваемого показан на карте"),
    ("rumors.log", "map place miss", "слух-наводка: место не найдено (no_xz/no_town) — смотреть причину"),
    ("rumors.log", "map disabled until restart", "ВНИМАНИЕ: метки карты выключились ошибкой — смотреть rumors.log"),
    ("rumors.log", "VISIBILITY day=", "заметность слухов: доля событий мира, дошедших до игрока (последняя строка ниже)", r"VISIBILITY day=\d+ events=\d+ shown=(\d+)"),
    ("rumors.log", "journal: addMessage ok", "слухи: услышанное записано в журнал сообщений окна управления"),
    ("rumors.log", "smalltalk town=", "слухи: мелочь города при входе (житель сказал о месте)"),
    ("rumors.log", "merge kind=", "слухи: шум однотипных событий слит в один слух"),
    ("tempo.log", "TILL town", "касса: богатство города посчитано (pop/беспорядки/еда/осада/процветание)"),
    ("tempo.log", "TILL poor", "касса: торговец бедного города обеднел — игроку искать другой рынок"),
    ("tempo.log", "TILL probe", "касса: ванильное процветание фракции прочитано"),
    ("tempo.log", "DISABLED till", "ВНИМАНИЕ: касса торговцев выключилась ошибкой — смотреть tempo.log"),
    ("predators.log", "smell:", "запах: бой/смерть оставили ванильный запах в зоне (хищники ядра)"),
    ("predators.log", "smell api unavailable", "ВНИМАНИЕ: addSmell недоступен — только фолбэк-спавны"),
    ("predators.log", "addSmell DISABLED", "ВНИМАНИЕ: крэш-сторож выключил addSmell навсегда (state/probe_addSmell.off)"),
    ("herds.log", "smell took:", "запах сработал: хищники ядра пришли на след стада без нашего спавна"),
    ("herds.log", "smell fallback spawn", "запах не дал эффекта — наш фолбэк-спавн хищника"),
    ("KenshiLua.log", "world state loaded via", "дирижёр загрузил состояние мира из сейва (KC.log -> KenshiLua.log)"),
    ("KenshiLua.log", "no v1 state", "дирижёр НЕ нашёл состояние в сейве (первый запуск — норма)"),
    ("debug.log", "TGM probe", "чтение родной таблицы цен города"),
    ("debug.log", "arrival ", "приходящие в город"),
    ("debug.log", "campaign: triggerCampaign ok", "родная кампания фракции запущена (FactionWarMgr:triggerCampaign)"),
    ("debug.log", "campaign: triggerCampaign FAIL", "ВНИМАНИЕ: запуск родной кампании отклонён ошибкой"),
    ("debug.log", "RELSYNC steps=", "отношения: сверка модели дирижёра с ядром (merged — дельты от дел влиты, diverged — расхождение)"),
    ("debug.log", "RELSYNC first merge", "отношения: первая ванильная дельта (дело игрока/NPC) влита в модель, а не затёрта"),
    ("debug.log", "RELSYNC write mismatch", "ВНИМАНИЕ: ядро держит не то, что записали (диапазон/обрезка relation)"),
    ("debug.log", "relsync disabled", "ВНИМАНИЕ: сверка отношений с ядром выключена ошибкой — запись абсолютная, как до Q5"),
    ("siege.log", "campaign fired", "осада: запущена родная кампания (Q4, FactionWarMgr:triggerCampaign)"),
    ("siege.log", "campaign bound", "осада: найден CampaignInstance в activeCampaigns (Q4)"),
    ("siege.log", "outcome from campaign", "осада: исход из фазы кампании VICTORY/RETREATING (Q4)"),
    ("siege.log", "campaign not started", "ВНИМАНИЕ: кампания осады не появилась в activeCampaigns (очередь/world state)"),
    ("siege.log", "fallback roll", "осада: исход броском (кампания недоступна; причина в строке)"),
    ("outlaws.log", "spawned near player", "банда разыскиваемого у игрока"),
    ("outlaws.log", "native bounty ok", "родная награда на главаре: ядро приняло (getTotalBounty вырос)"),
    ("outlaws.log", "native bounty FAIL", "ВНИМАНИЕ: родная награда не легла (вызов упал/нет фракции/сумма не выросла)"),
    ("outlaws.log", "native bounty unverified", "родная награда: вызов прошёл, сумму ядра не прочитать"),
    ("outlaws.log", "deed bus subscribed", "награды по делам: подписка на шину дел принята"),
    ("outlaws.log", "deed bounty +", "награды по делам: дело банды подняло награду главаря (native ok/FAIL/later)"),
    ("outlaws.log", "deed bounty disabled", "ВНИМАНИЕ: связка дел -> награда выключена ошибкой"),
    ("outlaws.log", "hunt goal HUNT_BOUNTIES ok", "охота: патрулю облавы дана ванильная цель HUNT_BOUNTIES"),
    ("outlaws.log", "hunt goal HUNT_BOUNTIES FAIL", "ВНИМАНИЕ: addGoal(HUNT_BOUNTIES) не принят"),
    ("outlaws.log", "outlaw_epithet", "заслуженное прозвище"),
    ("outlaws.log", "DISABLED forever", "нативный вызов отключён после краша"),
    ("debug.log", "brawl:", "драки NPC против NPC (кто кого бил, у какого города)"),
    ("chronicle.log", "\tblack_market\t", "сделки чёрных рынков (вассалы/рынки 14.11)"),
    ("nemesis.log", "nemesis_born", "немезис: родился соперник игрока (избит и оставлен жить / сбежал / мститель)"),
    ("nemesis.log", "said:", "немезис: главарь сказал игроку реплику при встрече"),
    ("nemesis.log", "nemesis_dead", "немезис: соперник погиб"),
    ("nemesis.log", "debt hooks registered", "должники: колбэки первой помощи/взлома/оков приняты ядром"),
    ("nemesis.log", "debt_made", "должники: игрок вылечил или освободил NPC — долг записан"),
    ("nemesis.log", "debt_repaid", "должники: должник пришёл на помощь в бою"),
    ("nemesis.log", "debt_word", "должники: долг вернули доброй молвой (отношение фракции)"),
    ("nemesis.log", "nemesis_hunter:", "охотники: именной охотник вышел на след игрока"),
    ("nemesis.log", "nemesis_hunter_beaten", "охотники: игрок уложил охотника и оставил жить"),
    ("nemesis.log", "nemesis_hunter_dead", "охотники: охотник убит, ордер у преемника"),
    ("nemesis.log", "leader_fell:", "лидеры: игрок убил/заковал лидера города — кризис наследования в модели мира"),
    ("nemesis.log", "banter:", "отряд: свой персонаж отозвался о деле игрока"),
    ("nemesis.log", "ambient_", "отряд: реплика о месте боя / голоде / пустых прилавках / осаде"),
    ("nemesis.log", "ambient disabled", "ВНИМАНИЕ: реплики отряда о мире выключены ошибкой"),
    ("nemesis.log", "chronicle:", "хроника: крупное событие мира записано в журнал сообщений (окно управления)"),
    ("nemesis.log", "ambient_scar:", "шрамы: свой вспомнил место, где лежал без сознания"),
    ("nemesis.log", "scars disabled", "ВНИМАНИЕ: шрамы отряда выключены ошибкой"),
    ("nemesis.log", "chronicle disabled", "ВНИМАНИЕ: хроника в журнале выключена (addMessage не сработал)"),
    ("nemesis.log", "town_greet:", "город встречает: житель хозяина сказал о положении дел / отношении к игроку"),
    ("nemesis.log", "shop_talk:", "торговец сказал о рынке (осада, дефицит, цены) при открытии торговли"),
    ("nemesis.log", "greet disabled", "ВНИМАНИЕ: «город встречает» выключен ошибкой"),
    ("nemesis.log", "hook trade disabled", "ВНИМАНИЕ: хук окна торговли выключен ошибкой"),
    ("nemesis.log", "captive:", "пленники: игрок заковал NPC (колбэк оков сработал)"),
    ("nemesis.log", "town_talk:", "город помнит: горожанин заговорил с игроком о его деле рядом"),
    ("nemesis.log", "nemesis_rescue", "за своими приходят: фракция пленника выслала отряд к игроку"),
    ("nemesis.log", "nemesis_title", "прозвище: мир стал звать игрока по его делам"),
    ("nemesis.log", "nemesis_warlord:", "варлорд: трижды пощажённый соперник поднял спящую фракцию"),
    ("nemesis.log", "nemesis_company", "наёмники-соперники: компания появилась / перехватила награду"),
    ("nemesis.log", "disabled until restart", "ВНИМАНИЕ: модуль/колбэк немезиса выключился из-за ошибки — смотреть строку в nemesis.log"),
    ("nemesis.log", "remember: no native", "ВНИМАНИЕ: память соперника выключена — плагин KMM_Native без remember_lt"),
    ("nemesis.log", "remember: LT_", "память ядра: соперник запомнил игрока (LT-тег через плагин; failed — смотреть причину)"),
    ("nemesis.log", "chronicle: addMessage ok", "хроника: строка дошла до вкладки сообщений окна управления"),
    ("nemesis.log", "deeds: subscribed", "дела ядра: немезис подписан на шину deed (KMM_Deeds)"),
    ("nemesis.log", "deed_owed:", "дела ядра: фракция помогла игроку — игрок должен (память помощника LT_FRIENDLY_AQUAINTANCE)"),
    ("nemesis.log", "aid_said:", "дела ядра: помощник сказал игроку реплику о долге"),
    ("nemesis.log", "deed_town:", "город помнит: дело игрока против/за хозяина города записано (скажут greet/town_talk)"),
    ("nemesis.log", "deed_ingrate:", "дела ядра: игрок ударил фракцию, которой был должен — неблагодарность"),
    ("nemesis.log", "said_ev:", "ванильная реплика: sendDialogEvent сработал вместо нашей строки"),
    ("nemesis.log", "not answered by dialogue package", "ванильная реплика: у пакета NPC нет строки на повод — сказана наша"),
    ("nemesis.log", "vanilla_ev failed", "ВНИМАНИЕ: sendDialogEvent падает — реплики идут нашими строками"),
    ("nemesis.log", "deeds disabled", "ВНИМАНИЕ: потребитель дел ядра в немезисе выключен ошибкой"),
    ("deeds.log", "affectRelations hook registered", "дела: колбэк FactionRelations::affectRelations принят ядром"),
    ("deeds.log", "first callback:", "дела: ядро вызвало колбэк (строка: код события, кто > кому — проверить направление a/b)"),
    ("deeds.log", "deed:", "дела: событие deed ушло в шину дирижёра (кто кого убил/пленил/спас)"),
    ("deeds.log", "disabled until restart", "ВНИМАНИЕ: шина дел (или её колбэк) выключилась ошибкой — смотреть deeds.log"),
]


TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")
OFFSETS = os.path.join(LOGS, "session_offsets.json")   # размеры логов на момент прошлых отчётов: начало сессии для логов без меток
SPIKE = 5    # >= 5 одинаковых строк в одну секунду (тесты давали пачки по 5 и 26) — всплеск офлайн-теста (B3 И9), в счёт не идёт
FAIL_RX = re.compile(r"disabled until restart|DISABLED|unavailable|off until restart|FAIL\b|: OFF \(|failed, retry in|PAUSED\b")
# реестр здоровья KMM_Gov (2026-11-16): отказ -> пауза и повтор вместо «disabled until restart»; навсегда — только OFF (noapi/crash).
# СЛОМАНО: старое «disabled until restart» (модуль без Gov) и «[KMM_Gov] health <ключ>: OFF (<reason>)».
# ПАУЗА: «<имя> failed, retry in N s: <err>» (модули), «[KMM_Gov] health <ключ>: fail #n -> pause N s», «PAUSED <имя> N s» (tempo.log).
# ВОССТАНОВЛЕНО: «[KMM_Gov] health <ключ>: recovered after n fails».
REG_OFF = re.compile(r"disabled until restart|\bhealth (\S+): OFF \(")
REG_PAUSE = re.compile(r"\bhealth (\S+): fail #\d+ -> pause|(?:\] |^)([^\]]*?) failed, retry in \d+|\bPAUSED (\S+) \d+ s")
REG_RECOVER = re.compile(r"\bhealth (\S+): recovered after (\d+) fails")
REG_SUMMARY = "[KMM_Gov] health: "
_CACHE = {}


def log_path(name):
    """KenshiLua.log лежит в папке KenshiLua (3817000612/logs), остальные — в C:\\KenshiModMap\\logs."""
    return LUALOG if name == "KenshiLua.log" else os.path.join(LOGS, name)


def _ts(l):
    try:
        return datetime.datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _offsets():
    try:
        return json.load(open(OFFSETS, encoding="utf-8"))
    except Exception:
        return {}


def session_lines(name, t0):
    """(строки сессии, режим). Режимы: ts — по меткам времени; offset — лог без меток, с размера на момент прошлого отчёта (до t0);
    approx — лог без меток, изменён в сессии, точного начала нет: весь файл (счёт с «≈»); old — не менялся с начала сессии; none — нет файла.
    Всплески (>= SPIKE одинаковых строк в одну секунду) выбрасываются, их число — в _CACHE[(name, 'spikes')]."""
    key = (name, t0)
    if key in _CACHE:
        return _CACHE[key]
    path = log_path(name)
    try:
        raw = open(path, "rb").read()
        mtime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    except OSError:
        _CACHE[key] = ([], "none")
        return _CACHE[key]
    text = raw.decode("utf-8", "replace")
    lines = text.splitlines()
    stamped = sum(1 for l in lines[:400] if TS.match(l))
    if stamped * 2 >= min(len(lines), 400) and stamped:
        out, cur = [], None
        for l in lines:
            t = _ts(l) if TS.match(l) else None
            if t:
                cur = t
            if cur and (not t0 or cur >= t0):   # строки без метки (продолжения) идут с последней меткой
                out.append(l.rstrip())
        groups = collections.Counter(l[:19] + "|" + l[19:].strip() for l in out if TS.match(l))
        spikes = {k for k, v in groups.items() if v >= SPIKE} if name != "KenshiLua.log" else set()   # KenshiLua.log тесты не пишут
        if spikes:
            out = [l for l in out if not (TS.match(l) and l[:19] + "|" + l[19:].strip() in spikes)]
        _CACHE[(name, "spikes")] = sum(groups[k] for k in spikes)
        _CACHE[key] = (out, "ts")
        return _CACHE[key]
    if t0 and mtime < t0:
        _CACHE[key] = ([], "old")
        return _CACHE[key]
    hist = _offsets().get(name, [])
    best = None
    for when, size in hist:
        try:
            w = datetime.datetime.strptime(when, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if t0 and w < t0 and size <= len(raw) and (best is None or w > best[0]):
            best = (w, size)
    if best:
        _CACHE[key] = ([l.rstrip() for l in raw[best[1]:].decode("utf-8", "replace").splitlines()], "offset")
    else:
        _CACHE[key] = ([l.rstrip() for l in lines], "approx")
    return _CACHE[key]


def since(path, t0):
    """Совместимость: строки сессии лога по пути."""
    return session_lines(os.path.basename(path) if os.path.dirname(path) != os.path.dirname(LUALOG) else "KenshiLua.log", t0)[0]


def save_offsets():
    """Запомнить размеры логов без меток (берутся следующим отчётом как начало новой сессии); хранится 6 последних записей."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data = _offsets()
    for f in sorted(os.listdir(LOGS)):
        if f.endswith(".log") and not f.startswith(("_", "verify_fail_", "install")):
            try:
                data.setdefault(f, []).append([now, os.path.getsize(os.path.join(LOGS, f))])
                data[f] = data[f][-6:]
            except OSError:
                pass
    try:
        json.dump(data, open(OFFSETS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    except OSError:
        pass


def marker_status(m, t0):
    """(значок, счёт, пояснение). [+] подтверждено, [!] СЛОМАНО (явный отказ в логе), [0] строки есть, но значение везде 0,
    [ ] строк нет. ≈ — лог без меток времени: посчитан весь файл."""
    f, sub, what = m[:3]
    val = m[3] if len(m) > 3 else None
    ls, mode = session_lines(f, t0)
    hits = [l for l in ls if sub in l]
    n = len(hits)
    approx = "≈" if mode == "approx" else ""
    fail = "ВНИМАНИЕ" in what or bool(FAIL_RX.search(sub))
    if not n:
        return " ", f"{approx}0", ""
    if what.startswith("ПАУЗА"):   # отказ с повтором (реестр KMM_Gov): не СЛОМАНО, а отдельно
        return "~", f"{approx}{n}", " (отказ -> пауза и повтор: " + hits[-1][-140:].strip() + ")"
    if fail:
        return "!", f"{approx}{n}", " СЛОМАНО: " + hits[-1][-160:].strip()
    if val:
        vals = [int(x) for l in hits for x in re.findall(val, l) if x.isdigit()]
        if vals and max(vals) == 0:
            return "0", f"{approx}{n}", " (везде 0 — повод был, эффекта нет)"
    return "+", f"{approx}{n}", ""


def _reg_key(m):
    return re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} ", "", next((g for g in m.groups() if g), "?")).strip()[-60:]


def health_registry(t0):
    """Отказы механик за сессию по всем логам KMM: СЛОМАНО (OFF / до перезапуска), ПАУЗА (отказ с повтором), ВОССТАНОВЛЕНО."""
    names = sorted(f for f in os.listdir(LOGS) if f.endswith(".log") and not f.startswith(("_", "verify_fail_", "install")))
    off, pause, rec, summ = [], {}, {}, None
    for f in names:
        for l in session_lines(f, t0)[0]:
            if REG_SUMMARY in l:
                summ = l.strip()
                continue
            if REG_OFF.search(l):
                off.append(f"{f}: {l.strip()[:200]}")
                continue
            m = REG_RECOVER.search(l)
            if m:
                k = _reg_key(m)
                rec[k] = (rec.get(k, (0, ""))[0] + 1, l.strip())
                continue
            m = REG_PAUSE.search(l)
            if m:
                k = f"{f}:{_reg_key(m)}"
                pause[k] = (pause.get(k, (0, ""))[0] + 1, l.strip())
    out = [f"реестр здоровья: СЛОМАНО {len(off)}, на паузе {len(pause)} механик (отказов {sum(v[0] for v in pause.values())}), "
           f"восстановлений {sum(v[0] for v in rec.values())}"]
    out += ["  СЛОМАНО: " + x for x in off[:12]]
    out += [f"  ПАУЗА {k} x{n}: {l[-170:]}" for k, (n, l) in sorted(pause.items())[:15]]
    out += [f"  ВОССТАНОВЛЕНО {k} x{n}" for k, (n, _) in sorted(rec.items())]
    if summ:
        out.append("  последняя сводка реестра: " + summ[:220])
    return out


def modules(t0):
    """По каждому логу KMM: строк за сессию, самоотключения, ошибки, последняя строка; маркеры работы; крэш-сторож state/."""
    out = []
    names = sorted(f for f in os.listdir(LOGS) if f.endswith(".log") and not f.startswith(("_", "verify_fail_", "install")))
    silent, spikes = [], []
    for f in names:
        ls, mode = session_lines(f, t0)
        if _CACHE.get((f, "spikes")):
            spikes.append(f"{f} {_CACHE[(f, 'spikes')]}")
        if not ls:
            silent.append(f + (" (без меток, не менялся с начала сессии)" if mode == "old" else ""))
            continue
        cut = 20 if mode == "ts" else 0
        off = [l for l in ls if FAIL_RX.search(l) and not re.search(r"\bok\b", l)]
        err = [l for l in ls if re.search(r"(?i)\berror\b|traceback|attempt to", l)]
        tag = {"ts": "", "offset": " (без меток: с прошлого отчёта)", "approx": " (без меток времени: ≈ весь файл, начала сессии не знаем)"}[mode]
        out.append(f"{f}: {len(ls)} строк{tag}" + (f", ОТКАЗОВ/ОТКЛЮЧЕНИЙ {len(off)}" if off else "") + (f", ошибок {len(err)}" if err else ""))
        for l in (off + err)[:3]:
            out.append("    ! " + l[cut:cut + 200])
        out.append("    последняя: " + ls[-1][cut:cut + 180])
    if silent:
        out.append("молчали за сессию: " + ", ".join(silent))
    if spikes:
        out.append("отброшены всплески (>= %d одинаковых строк в секунду, похоже на офлайн-тесты): %s" % (SPIKE, ", ".join(spikes)))
    broken = []
    for m in MARKERS:
        st, n, note = marker_status(m, t0)
        out.append(f"  [{st}] {m[2]}: {n}{note}")
        if st in ("!", "0"):
            broken.append(f"  [{st}] {m[0]}: {m[2]}{note}")
    vis = [l for l in session_lines("rumors.log", t0)[0] if "VISIBILITY day=" in l]
    if vis:
        mv = re.search(r"events=(\d+) shown=(\d+) merged=(\d+) pct=([\d.]+).*?types=(\S*)", vis[-1])
        if mv:
            out.append(f"заметность слухов (последняя VISIBILITY): событий {mv.group(1)}, дошло {mv.group(2)} ({mv.group(4)}%), слито {mv.group(3)}; types={mv.group(5)[:200]}")
    if broken:
        out.insert(0, "СЛОМАНО / БЕЗ ЭФФЕКТА (%d):" % len(broken))
        for i, b in enumerate(broken):
            out.insert(1 + i, b)
    offs = sorted(glob.glob(os.path.join(STATE, "probe_*.off")))
    locks = sorted(glob.glob(os.path.join(STATE, "probe_*.lock")))
    out.append("крэш-сторож: " + ("чисто" if not (offs or locks) else ""))
    for p in offs:
        out.append("  ОТКЛЮЧЁН навсегда: " + os.path.basename(p) + " (" + open(p, encoding="utf-8", errors="replace").read()[:80] + ")")
    for p in locks:
        out.append("  ВИСИТ lock (игра упала во время этого вызова?): " + os.path.basename(p))
    return out


PROBE_LINE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) PROBE (\S+) (ok|fail|absent) ?(.*)$")
PROBE_SUMM = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) PROBE summary ok=(\d+) fail=(\d+) absent=(\d+) pass=(\d+)(.*)$")


def probe_passes():
    """logs/probe.log (KMM_Probe) -> проходы по порядку: {t, pass, res: {имя: (статус, значение)}, summ, done}.
    Проход = строки проб до своей строки summary; незавершённый хвост (игра закрыта/упала посреди прохода) — done=False."""
    out, cur = [], {}
    try:
        lines = open(log_path("probe.log"), encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []
    for l in lines:
        ms = PROBE_SUMM.match(l)
        if ms:
            out.append({"t": _ts(ms.group(1)), "pass": int(ms.group(5)), "res": cur, "done": True,
                        "summ": f"ok={ms.group(2)} fail={ms.group(3)} absent={ms.group(4)} pass={ms.group(5)}{ms.group(6)}"})
            cur = {}
            continue
        m = PROBE_LINE.match(l)
        if m:
            cur[m.group(2)] = (m.group(3), m.group(4).strip(), _ts(m.group(1)))
    if cur:
        t = max(v[2] for v in cur.values() if v[2]) if any(v[2] for v in cur.values()) else None
        out.append({"t": t, "pass": 0, "res": cur, "done": False, "summ": "незавершён"})
    return out


def _probe_merge(ps):
    """Последний статус каждой пробы по проходам (проход 2 уточняет проход 1)."""
    res = {}
    for p in ps:
        for k, v in p["res"].items():
            res[k] = v
    return res


def probe_section(t0):
    """Раздел «Самопроверка»: итог по пробам сессии, fail и absent с причиной, сравнение с прошлой сессией."""
    ps = probe_passes()
    if not ps:
        return ["probe.log нет: самопроверка не работала (KMM_Probe не установлен или игра не дошла до мира)"]
    if t0:
        cur = [p for p in ps if p["t"] and p["t"] >= t0]
        before = [p for p in ps if p["t"] and p["t"] < t0]
    else:   # нет KenshiLua.log: текущая сессия — от последнего прохода 1
        starts = [i for i, p in enumerate(ps) if p["pass"] == 1]
        i0 = starts[-1] if starts else 0
        cur, before = ps[i0:], ps[:i0]
    starts = [i for i, p in enumerate(before) if p["pass"] == 1]
    prev = before[starts[-1]:] if starts else before
    if not cur:
        return ["за сессию строк самопроверки нет (сессия короче start_s ~20 с после появления персонажей, или игра упала до прохода)"]
    res = _probe_merge(cur)
    n = {s: sorted(k for k, v in res.items() if v[0] == s) for s in ("ok", "fail", "absent")}
    out = [f"итог: ok={len(n['ok'])} fail={len(n['fail'])} absent={len(n['absent'])} (проб {len(res)}, проходов {len(cur)}: "
           + "; ".join(f"{p['t'].strftime('%H:%M:%S') if p['t'] else '?'} {p['summ']}" for p in cur) + ")"]
    for k in n["fail"]:
        out.append(f"  [!] FAIL {k}: {res[k][1][:200]}")
    for k in n["absent"]:
        out.append(f"  [?] absent {k}: {res[k][1][:160]}")
    if prev:
        pr = _probe_merge(prev)
        broke = sorted(k for k, v in res.items() if k in pr and pr[k][0] == "ok" and v[0] != "ok")
        fixed = sorted(k for k, v in res.items() if k in pr and pr[k][0] != "ok" and v[0] == "ok")
        new = sorted(k for k in res if k not in pr)
        gone = sorted(k for k in pr if k not in res)
        t = prev[0]["t"].strftime("%Y-%m-%d %H:%M") if prev[0]["t"] else "?"
        out.append(f"сравнение с прошлой сессией ({t}): сломалось {len(broke)}, починилось {len(fixed)}, без изменений {len(res) - len(broke) - len(fixed) - len(new)}")
        for k in broke:
            out.append(f"  СЛОМАЛОСЬ {k}: было ok ({pr[k][1][:70]}) -> {res[k][0]} {res[k][1][:110]}")
        for k in fixed:
            out.append(f"  ПОЧИНИЛОСЬ {k}: было {pr[k][0]} ({pr[k][1][:70]}) -> ok {res[k][1][:90]}")
        if new:
            out.append("  новые пробы: " + ", ".join(new))
        if gone:
            out.append("  пропали из лога: " + ", ".join(gone))
    else:
        out.append("сравнение с прошлой сессией: прошлой самопроверки в probe.log нет")
    offs = sorted(glob.glob(os.path.join(STATE, "probe_kmmprobe_*.off")))
    if offs:
        out.append("пробы выключены крэш-сторожем навсегда (удалить файл — включить): " + ", ".join(os.path.basename(p) for p in offs))
    return out


def memory(t0):
    p = os.path.join(LOGS, "mem.csv")
    if not os.path.exists(p):
        return ["память: замера нет"]
    pts = []
    for l in open(p, encoding="utf-8-sig", errors="replace"):
        parts = l.strip().split(",")
        if len(parts) == 2 and parts[1].isdigit():
            try:
                t = datetime.datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if not t0 or t >= t0:
                pts.append((t, int(parts[1])))
    if not pts:
        return ["память: за эту сессию точек нет"]
    mb = [v for _, v in pts]
    return [f"память: {len(pts)} мин, старт {mb[0]} МБ, пик {max(mb)} МБ, конец {mb[-1]} МБ"]


def main():
    t0 = session_start()
    parts = [f"=== отчёт сессии (начало {t0}) ==="]
    parts += ["--- health ---", run("health.py").strip()]
    parts += ["--- самопроверка (logs/probe.log, KMM_Probe) ---"] + probe_section(t0)
    parts += ["--- активность модулей ---"] + activity(t0)
    parts += ["--- модули KMM (логи за сессию, маркеры, крэш-сторож) ---"] + modules(t0)
    parts += ["--- память ---"] + memory(t0)
    parts += ["--- одежда NPC (свежий сейв) ---", run("save_report.py").strip()]
    txt = "\n".join(parts)
    open(os.path.join(LOGS, "session_last.txt"), "w", encoding="utf-8").write(txt)
    if "--no-offsets" not in sys.argv:
        save_offsets()
    print(txt)


if __name__ == "__main__":
    main()
