"""Отчёт после игровой сессии (только чтение, игру не запускает): одна команда вместо ручного разбора.
python tools\\session_report.py   -> печать + logs\\session_last.txt
Разделы: health (логи, краши, отключения модулей); активность модулей по debug.log/chronicle за последнюю сессию;
память (logs\\mem.csv); одежда NPC по свежему сейву (save_report)."""
import collections
import datetime
import glob
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
    tags, disabled = collections.Counter(), []
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
            if "disabled until restart" in l:
                disabled.append(l.strip()[:200])
    out.append("debug.log за сессию: " + (", ".join(f"{k} x{v}" for k, v in tags.most_common(14)) or "пусто"))
    out += ["  ОТКЛЮЧЕНО: " + d for d in disabled]
    p = os.path.join(LOGS, "chronicle.log")
    if os.path.exists(p):
        kinds = collections.Counter(l.split("\t")[2] for l in open(p, encoding="utf-8", errors="replace") if l.count("\t") >= 3)
        out.append("хроника мира (типы событий): " + ", ".join(f"{k} {v}" for k, v in kinds.most_common(12)))
    lua = open(LUALOG, encoding="utf-8", errors="replace").read() if os.path.exists(LUALOG) else ""
    out.append(f"KenshiLua: реплик диалогового моста {lua.count('DialogueScriptBridge: Triggered')}, решений дипломатии {lua.count('[KMM_Diplo] decision')}, "
               f"ошибок {len(re.findall(r'(?i)error|attempt to|bad argument', lua))}")
    return out


STATE = os.path.join(ROOT, "state")
# что должно появиться в логах, если модуль реально работает в игре (файл, подстрока, смысл)
MARKERS = [
    ("debug.log", "override registered at load", "побеждённый лежит: перехват ядра зарегистрирован при загрузке"),
    ("debug.log", "override calls=", "побеждённый лежит: сколько раз ядро спросило (calls>0 и asks>0 — окно работает)"),
    ("debug.log", "dropped:", "след Traces отменён: игрок ушёл от места планирования"),
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
    ("debug.log", "KO hold:", "окно после нокаута: побеждённый не встаёт (связать/обыскать/добить)"),
    ("debug.log", "KO release:", "окно после нокаута: отпущен (asks= — частота override ядра)"),
    ("debug.log", "DUEL offer added", "поединок: лидерам-конкурентам добавлена реплика вызова"),
    ("debug.log", "DUEL start", "поединок: вызов принят, бой до нокаута"),
    ("debug.log", "DUEL end", "поединок: исход (победа/поражение/убийство/таймаут)"),
    ("debug.log", "DUEL clear", "поединок: временная вражда снята"),
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
    ("debug.log", "DIPLO_RIVAL world changed", "диалоги: смена мира, отряды прошлого мира не вызываются"),
    ("debug.log", "[KMM_Gov] summary:", "нагрузка: сводка снимка NPC (сборки/с, стоимость, переиспользование)"),
    ("debug.log", "[KMM_Gov] modules:", "нагрузка по модулям: средняя/пик мс и доля троттлинга"),
    ("debug.log", "set:has unavailable", "нагрузка: проверка снимка недоступна — правило одного кадра"),
    ("debug.log", "DIPLO_COND hook live", "диалоги: перехват условий ядра работает (реплики по состоянию мира)"),
    ("debug.log", "DIPLO_COND fallback", "диалоги: перехват не работает — Diplo вернулся к жетонам"),
    ("debug.log", "DIPLO_WORLD town=", "диалоги: флаги мира для города игрока (голод/осада/беспорядки/соперник)"),
    ("debug.log", "DIPLO_RIVAL threat talk added", "диалоги: соперник получил ванильный разговор-угрозу"),
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
    ("tempo.log", "TILL town", "касса: богатство города посчитано (pop/беспорядки/еда/осада/процветание)"),
    ("tempo.log", "TILL poor", "касса: торговец бедного города обеднел — игроку искать другой рынок"),
    ("tempo.log", "TILL probe", "касса: ванильное процветание фракции прочитано"),
    ("tempo.log", "DISABLED till", "ВНИМАНИЕ: касса торговцев выключилась ошибкой — смотреть tempo.log"),
    ("predators.log", "smell:", "запах: бой/смерть оставили ванильный запах в зоне (хищники ядра)"),
    ("predators.log", "smell api unavailable", "ВНИМАНИЕ: addSmell недоступен — только фолбэк-спавны"),
    ("predators.log", "addSmell DISABLED", "ВНИМАНИЕ: крэш-сторож выключил addSmell навсегда (state/probe_addSmell.off)"),
    ("herds.log", "smell took:", "запах сработал: хищники ядра пришли на след стада без нашего спавна"),
    ("herds.log", "smell fallback spawn", "запах не дал эффекта — наш фолбэк-спавн хищника"),
    ("debug.log", "world state loaded via", "дирижёр загрузил состояние мира"),
    ("debug.log", "no v1 state", "дирижёр НЕ нашёл состояние (первый запуск — норма)"),
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
    ("chronicle.log", "	black_market	", "сделки чёрных рынков (вассалы/рынки 14.11)"),
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
    ("outlaws.log", "probe", "крэш-сторож нативных вызовов (награда, память ядра)"),
    ("KenshiLua.log", "world state loaded via", "дирижёр загрузил мир (KenshiLua.log)"),
]


def since(path, t0):
    out = []
    try:
        for l in open(path, encoding="utf-8", errors="replace"):
            try:
                t = datetime.datetime.strptime(l[:19], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                continue
            if not t0 or t >= t0:
                out.append(l.rstrip())
    except OSError:
        pass
    return out


def modules(t0):
    """По каждому логу KMM: строк за сессию, самоотключения, ошибки, последняя строка; маркеры работы; крэш-сторож state/."""
    out = []
    names = sorted(f for f in os.listdir(LOGS) if f.endswith(".log") and not f.startswith(("_", "verify_fail_", "install")))
    silent = []
    for f in names:
        ls = since(os.path.join(LOGS, f), t0)
        if not ls:
            silent.append(f)
            continue
        off = [l for l in ls if "disabled until restart" in l or "DISABLED" in l]
        err = [l for l in ls if re.search(r"(?i)error|traceback|attempt to", l)]
        out.append(f"{f}: {len(ls)} строк" + (f", ОТКЛЮЧЕНИЙ {len(off)}" if off else "") + (f", ошибок {len(err)}" if err else ""))
        for l in (off + err)[:3]:
            out.append("    ! " + l[20:220])
        out.append("    последняя: " + ls[-1][20:200])
    if silent:
        out.append("молчали за сессию: " + ", ".join(silent))
    for f, sub, what in MARKERS:
        n = sum(1 for l in since(os.path.join(LOGS, f), t0) if sub in l)
        out.append(f"  [{'+' if n else ' '}] {what}: {n}")
    offs = sorted(glob.glob(os.path.join(STATE, "probe_*.off")))
    locks = sorted(glob.glob(os.path.join(STATE, "probe_*.lock")))
    out.append("крэш-сторож: " + ("чисто" if not (offs or locks) else ""))
    for p in offs:
        out.append("  ОТКЛЮЧЁН навсегда: " + os.path.basename(p) + " (" + open(p, encoding="utf-8", errors="replace").read()[:80] + ")")
    for p in locks:
        out.append("  ВИСИТ lock (игра упала во время этого вызова?): " + os.path.basename(p))
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
    parts += ["--- активность модулей ---"] + activity(t0)
    parts += ["--- модули KMM (логи за сессию, маркеры, крэш-сторож) ---"] + modules(t0)
    parts += ["--- память ---"] + memory(t0)
    parts += ["--- одежда NPC (свежий сейв) ---", run("save_report.py").strip()]
    txt = "\n".join(parts)
    open(os.path.join(LOGS, "session_last.txt"), "w", encoding="utf-8").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
