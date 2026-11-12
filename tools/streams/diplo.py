"""Поток DIPLO: дипломатия игрока через диалоги у лидеров, дипломатов и главарей фракций (rules/streams/diplo.json).

Новые записи (существующие не трогаем, кроме ОДНОЙ категории ссылок):
- DIALOGUE «KMM Diplomacy» (PLAYER_TALK_TO_ME) — доступен, только если у говорящего персонажа игрока есть «Envoy's Seal»
  (условие «target has item»), поэтому ванильные разговоры лидеров не перекрываются;
- дерево DIALOGUE_LINE: приветствие → 4 реплики игрока (подменю «договоры» / подменю «дань» / разрыв договора / прощание); предложения: 6 (ненападение, торговля, союз, присяга игрока = игрок-вассал,
  требование покорности = игрок-сюзерен, требование дани) + выплата/сбор дани вассалитета + разрыв договора;
  ответы фракции: согласие / встречное требование дани (2 яруса) / отказ — по жетонам-предметам, которые выдаёт Lua
  (условие «target has item»); запасной ответ без жетона — «изложите условия письменно» + письмо-предмет (give item);
- DIALOG_ACTION: условия (DC_PLAYERMONEY) и действия (DA_TAKE_MONEY / DA_GIVE_MONEY) — суммы в данных;
- ITEM: печать посланника, 7 жетонов, 6 писем (клоны ванильного письма);
- LUA_SCRIPT (тип 322 KenshiLua): «run lua script» на репликах → scripts/dialogue/kmm_diplo_line.lua (мост диалогов).
Существующие CHARACTER: только категория ссылок «dialogue» (доп. PLAYER_TALK_TO_ME) — её не меняет ни один поток.
S4 (условия мира, rules/streams/diplo.json «world»): одно зарезервированное условие DC_FACTION_VARIABLE «KMM_WORLD» = base+код,
на него отвечает перехват Dialogue::_checkCondition в kmm_diplo.lua (O(1) по таблице флагов). Им:
- ответы посланника продублированы «близнецами» без жетона (условие вместо «target has item»; при живом перехвате Lua жетоны не выдаёт);
- реплики-монологи торговцев/барменов/стражи (EV_I_SEE_NEUTRAL_SQUAD) по состоянию города, где стоит игрок: голод, изобилие, осада,
  беспорядки, опустение, хозяин враждебен/сменился, прозвище игрока, соперник рядом; награда игрока — ванильным DC_BOUNTY_AMOUNT_ACTUAL;
  существующие DIALOGUE_PACKAGE: только доп. ссылки «dialogs»;
- угрозы соперника (DIALOGUE для addConversation в рантайме, EV_I_SEE_ENEMY_PLAYER / EV_I_SEE_NEUTRAL_SQUAD).
X3 (вызов на поединок, rules «duel»): DIALOGUE для addConversation в рантайме лидерам отрядов-конкурентов (EV_PLAYER_TALK_TO_ME), условие
duel_open; вызов игрока → ответ лидера по условию duel_accept / duel_refuse (решает Lua); принятие — ванильные эффекты нападения
DA_FLAG_TEMP_ENEMY + DA_ATTACK_CHASE_FOREVER (как ванильное «Beat him down. Strip his stuff.»); без перехвата — запасной отказ.
Карта реплик/жетонов/посланников для Lua → build/KMM_Diplo/scripts/kmm_diplo_data.lua."""
import collections
import json
import os
import re

import kmod
from kmod import F32, FilePath, Ref

ROOT = r"C:\KenshiModMap"
OUT_DIR = os.path.join(ROOT, "build", "KMM_Diplo", "scripts")
LUA_SCRIPT_TYPE = 322          # itemType.LUA_SCRIPT (KenshiLua fcs.def)
SCRIPT_FILE = "dialogue/kmm_diplo_line.lua"
T_ME, T_TARGET = 0, 1          # TalkerEnum
DC_PLAYERMONEY, CE_EQUALS, CE_MORE_THAN = 2, 0, 2
DC_TARGET_IN_TALKING_RANGE, DC_IN_MY_BUILDING, DC_IS_ENEMY, DC_IS_PLAYER, DC_BOUNTY_AMOUNT_ACTUAL = 16, 17, 25, 36, 47   # DialogConditionEnum
DA_TAKE_MONEY, DA_GIVE_MONEY = 8, 9
DA_ATTACK_CHASE_FOREVER, DA_FLAG_TEMP_ENEMY = 6, 21   # DialogActionEnum (X3: вызов на поединок)

KINDS = ["nonaggression", "trade", "alliance", "fealty", "submission", "tribute"]
COUNTER_KINDS = {"nonaggression", "trade", "alliance", "fealty"}
TOKENS = ["accept", "refuse", "counter_s", "counter_l", "liege_due", "vassal_due", "has_pact"]

TXT = {
    "greet": ["You carry an envoy's seal. Speak, then. What do the Nameless want of us?",
              "An envoy? Hm. Say your piece, and say it quickly.",
              "So the Nameless send words instead of blades. I'm listening."],
    "propose": {
        "nonaggression": ["Let there be no blood between us. A pact of non-aggression."],
        "trade": ["Open your markets to us, and ours to you. A trade agreement."],
        "alliance": ["We share enemies. Stand with us: an alliance."],
        "fealty": ["We would swear fealty to you. Take the Nameless as your vassals."],
        "submission": ["Bend the knee. Become our vassals and we will shield you."],
        "tribute": ["Pay us tribute, and we'll leave you in peace."],
    },
    "accept": {
        "nonaggression": ["Agreed. Our blades stay sheathed, so long as yours do.", "Very well. No war between us. Do not make me regret it."],
        "trade": ["Agreed. Your caravans will find our gates open.", "Trade, then. Profit makes better friends than blood."],
        "alliance": ["Then we stand together. Your enemies are ours.", "An alliance it is. Call, and we will answer, if we can."],
        "fealty": ["Kneel, then. You serve us now. Pay your dues and we will guard your back.",
                   "Accepted. The Nameless are ours. Do not forget your tribute."],
        "submission": ["...We have no choice. We are yours. Spare our people.", "So be it. We bend the knee. Our tribute will be ready."],
        "tribute": ["Take it, and be gone.", "Here. May it choke you."],
    },
    "refuse": {
        "nonaggression": ["No. We do not bargain with the likes of you.", "Peace with you? Not today."],
        "trade": ["We have no use for your trade.", "Our markets are closed to you."],
        "alliance": ["An alliance? You are not worth the risk.", "We do not bind ourselves to strangers."],
        "fealty": ["We have no need of vassals like you.", "Serve someone else."],
        "submission": ["Never. Come and take it, if you can.", "You mistake us for cowards."],
        "tribute": ["Tribute? Come and collect it with a sword.", "Not a single cat. Get out."],
    },
    "counter": ["Words are cheap. {n} cats, and you have your pact.", "It can be done, for {n} cats."],
    "pay": "Done. ({n} cats)",
    "decline": "Too steep. Forget it.",
    "paid_ack": ["Then it is agreed.", "Good. We have a pact."],
    "declined_ack": ["Then we have nothing more to discuss.", "Your loss."],
    "consider": ["I cannot answer that today. Leave your terms in writing, and you will hear from us.",
                 "Put it in writing. Our answer will reach you."],
    "pay_tribute": "Our tribute, as agreed. ({n} cats)",
    "pay_tribute_ack": ["Your loyalty is noted.", "Good. You keep your word."],
    "collect": "I've come for the tribute you owe us.",
    "collect_ack": ["Here. Count it if you must.", "Take it. As agreed."],
    "renounce": "Our pact is over.",
    "renounce_ack": ["So be it. Remember that we remember.", "Then go. We will not forget this."],
    "menu_treaty": "Let us talk about treaties.",
    "menu_tribute": "Let us talk about tribute.",
    "sub_treaty": ["What manner of pact do you have in mind?", "Treaties, then. Name your terms."],
    "sub_tribute": ["Tribute. Go on.", "Ah, the matter of dues. Speak."],
    "nevermind": "Never mind.",
    "anything_else": ["As you wish. Is there anything else?", "Very well. Anything more?"],
    "bye": "Farewell.",
    "bye_ack": ["Go, then.", "Safe roads."],
}

# S4: реплики мира. Ключ — код условия (rules «world».codes) или "bounty" (ванильное условие награды игрока); (score, тексты).
TXT_WORLD = {
    "trade": {
        "town_siege": (30, ["Gates shut, roads cut. Prices only go one way now.", "You came in through that? Brave or stupid. Buy something either way.",
                            "Nothing comes in, nothing goes out. What's on the shelf is all there is."]),
        "owner_captured": (25, ["New masters, new taxes. Same empty bellies.", "Different flag over the gate. The prices noticed before we did."]),
        "town_hungry": (20, ["Food's dear. Half this town eats once a day.", "No grain worth the name left. Buy it or don't, but don't haggle.",
                             "Hungry folk get desperate. Keep your pack close in here."]),
        "town_emptied": (18, ["Used to be busy here. Then the raids came. Now it's me and the flies.",
                              "Half the houses stand empty. Nobody's coming back for them."]),
        "town_unrest": (16, ["Keep your voice down. The streets are angry and the guards are jumpy.",
                             "Trouble brewing out there. Spend your cats and get off the street."]),
        "owner_hostile": (15, ["Your kind isn't welcome here. Your cats are. Be quick.", "I'll trade. The guards won't be so friendly. Don't linger."]),
        "rival_here": (14, ["Someone was in here asking after you. Didn't leave a name. Left a look.",
                            "A hard type's been around, asking where you drink. I said I didn't know."]),
        "bounty": (12, ["There's paper on your head. Pay, drink, leave. I never saw you.", "Bounty hunters shop here too, you know. Be quick."]),
        "player_title": (10, ["I know that face. They talk about you from here to the Hub.", "You're the one from the stories. Thought you'd be taller."]),
        "town_plenty": (8, ["Shelves are full for once. Enjoy it. It never lasts.", "Good season. Prices are down, for now."]),
        "rival_alive": (4, ["Word is somebody's hunting you. Not my business. Pay first."]),
    },
    "guard": {
        "town_siege": (30, ["Move along. Everyone on the walls has a job. Find one or get out of the way.",
                            "Stay off the gate. If they break through, you're on your own."]),
        "owner_captured": (25, ["This town has new masters. Their law now. Learn it fast.",
                                "Old banners came down. Don't ask who put up the new ones."]),
        "town_unrest": (20, ["Trouble in the streets. Step wrong and you'll be part of it.", "Riots last night. Give me a reason. Any reason."]),
        "town_hungry": (18, ["Hungry folk steal. Thieves get the cage. Don't be hungry here.",
                             "Food's short. Anyone caught with a stolen sack hangs. Remember that."]),
        "owner_hostile": (15, ["I'm watching you, outsider. One wrong move.", "Your people and mine are no friends. Keep your hands where I can see them."]),
        "rival_here": (12, ["Somebody's been asking at the gate about you. Settle it outside the walls."]),
        "player_title": (10, ["I've heard of you. Don't make me prove the stories wrong.", "So you're the famous one. Keep the fame outside the walls."]),
    },
    "rival": {
        "player_title": (20, ["So you're the one they tell stories about. Let's see how this one ends.", "Big name. Small grave."]),
        "bounty": (10, ["Your head's worth more than mine now. Funny how that goes.", "Every hunter in the land wants you. I just want you first."]),
        None: (0, ["There you are. I've been walking your tracks for days.", "You should have finished it when you had the chance.",
                   "Stand still. This won't take long."]),
    },
}

# X3: вызов на поединок (лидер отряда-конкурента, разговор добавляется в рантайме)
TXT_DUEL = {
    "greet": ["What do you want?", "You're in my way. Talk.", "Hm. You again, or someone like you. Speak."],
    "challenge": "I challenge you. You and me, until one of us is in the dirt. No blood feud after.",
    "accept": ["Ha! Finally, someone with a spine. Come on, then.", "Done. When you wake up, your purse will be lighter.",
               "One on one? Gladly. Try to stay standing."],
    "refuse": ["Not worth my time. Come back some other day.", "No. Not today, not with you.", "Find someone else to lose to."],
    "busy": ["Not today."],
    "never": "Never mind.",
    "never_ack": ["Then get out of my way.", "Thought so."],
}


def lua_lit(v, ind=""):
    """Python → литерал Lua (dict/list/str/num/bool)."""
    if v is None:
        return "nil"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    if isinstance(v, str):
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
    if isinstance(v, list):
        return "{ " + ", ".join(lua_lit(x, ind) for x in v) + " }"
    if isinstance(v, dict):
        inner = ind + " "
        parts = [f"{inner}[{lua_lit(str(k))}] = {lua_lit(x, inner)}" for k, x in v.items()]
        return "{\n" + ",\n".join(parts) + "\n" + ind + "}"
    raise TypeError(v)


LORE_FILE = os.path.join(ROOT, "rules", "lore", "diplo_lore.json")


def lore_build(ctx, s, M, T_ME, T_TARGET, line, child, trader_why, extra_dlg):
    """Ветка «What is the word on the world?» у уникальных (хроника «Сумерки реликтов»): отдельный DIALOGUE на персонажа, доп. запись в «dialogue»
    (PLAYER_TALK_TO_ME), без печати посланника, без перекрытия торговых разговоров; ванильные ссылки не трогаем."""
    if not os.path.exists(LORE_FILE):
        return
    L = json.load(open(LORE_FILE, encoding="utf-8"))
    by_name = collections.defaultdict(list)
    for ch in ctx.all("CHARACTER"):
        if ch.values.get("unique") and not ch.values.get("dumb") and not ch.values.get("slave"):
            by_name[ch.name].append(ch)
    linked, skipped, missing = [], [], []
    for i, e in enumerate(L["entries"]):
        hits = [c for c in by_name.get(e["name"], []) if not e.get("mod") or ctx.origin.get(c.sid) == e["mod"]]
        if not hits:
            missing.append(e["name"])
            continue
        dl = s.new("DIALOGUE", "KMM Lore: " + e["name"], values={
            "for enemies": False, "locked": False, "monologue": False, "one at a time": False,
            "chance permanent": F32(L["chance"]), "chance temporary": F32(100.0), "repetition limit": 0,
            "score bonus": 0, "target is type": 0, "tag": "KMM_Lore"})
        hook = child(dl, line(T_ME, e["hook"]))
        q1 = child(hook, line(T_TARGET, L["q_world"]))
        a1 = child(q1, line(T_ME, e["world"]))
        q2 = child(a1, line(T_TARGET, L["q_relics"]))
        a2 = child(q2, line(T_ME, e["relics"]))
        q3 = child(a2, line(T_TARGET, L["q_thanks"]))
        child(q3, line(T_ME, L["close"][i % len(L["close"])]))
        qb = child(hook, line(T_TARGET, L["q_bye"]))
        child(qb, line(T_ME, L["bye_ack"]))
        for ch in hits:
            if trader_why(ch):
                skipped.append(ch.name)
                continue
            extra_dlg[ch.sid].append(Ref(dl.sid, 0, 0, 0))
            linked.append(ch.sid)
    s.report["lore_dialogues"] = len(L["entries"]) - len(missing)
    s.report["lore_characters"] = len(linked)
    ctx.lore_linked = linked
    ctx.lore_missing = missing
    ctx.lore_skipped = skipped


def astartes_build(ctx, s, M, T_ME, T_TARGET, line, child, extra_dlg, A):
    """A1 (2026-11-15, docs/core/ASTARTES.md): разговор с орденом космодесанта — отдельный DIALOGUE «KMM Order: <фракция>» на орден,
    доп. запись в CHARACTER «dialogue» (PLAYER_TALK_TO_ME, как lore_build) у членов отрядов ордена (leader/squad/squad2; отряды и ранги
    создаёт поток relics, astartes_chapters); условие «my faction» = орден — приданные уники мода говорят так только в отряде ордена.
    Цепочка без циклов: приветствие → кто вы → чего хотите → враги веры → прощание (и короткое прощание сразу)."""
    if not A or not A.get("enabled"):
        return
    facs = {}
    for f in ctx.all("FACTION"):
        facs.setdefault(f.name, f)
    for e in A["orders"]:
        f = facs.get(e["faction"])
        if f is None:
            s.report["astartes_order_missing:" + e["faction"]] = 1
            continue
        mem = sorted({r.target for q in ctx.all("SQUAD_TEMPLATE") if q.refs.get("faction") and q.refs["faction"][0].target == f.sid
                      for c in ("leader", "squad", "squad2") for r in q.refs.get(c, []) if r.target in M and M[r.target].type_name == "CHARACTER"})
        dl = s.new("DIALOGUE", "KMM Order: " + e["faction"], values={
            "for enemies": False, "locked": False, "monologue": False, "one at a time": False,
            "chance permanent": F32(A["chance"]), "chance temporary": F32(100.0), "repetition limit": 0,
            "score bonus": 0, "target is type": 0, "tag": "KMM_Order"})
        dl.refs["my faction"] = [Ref(f.sid, 0, 0, 0)]
        hook = child(dl, line(T_ME, e["hook"]))
        q1 = child(hook, line(T_TARGET, A["q_who"]))
        a1 = child(q1, line(T_ME, e["who"]))
        q2 = child(a1, line(T_TARGET, A["q_goal"]))
        a2 = child(q2, line(T_ME, e["goal"]))
        q3 = child(a2, line(T_TARGET, A["q_foe"]))
        a3 = child(q3, line(T_ME, e["foe"]))
        q4 = child(a3, line(T_TARGET, A["q_bye"]))
        child(q4, line(T_ME, e["bye"]))
        qb = child(hook, line(T_TARGET, A["q_bye"]))
        child(qb, line(T_ME, e["bye"]))
        for sid in mem:
            extra_dlg[sid].append(Ref(dl.sid, 0, 0, 0))
        s.report["astartes_order_dialogues"] += 1
        s.report["astartes_order_speakers"] += len(mem)
        s.report[f"astartes_order:{e['faction']}"] = len(mem)


def build(ctx, s, rules):
    M = ctx.M
    cond = json.load(open(os.path.join(ROOT, "rules", "conductor.json"), encoding="utf-8"))
    pf = cond["player_faction"]
    money = rules["money"]
    E = rules["envoys"]
    lines_map = {}

    # ---- записи-помощники -------------------------------------------------------------------------------
    def texts(lst, **fmt):
        lst = [lst] if isinstance(lst, str) else lst
        return {f"text{i}": t.format(**fmt) for i, t in enumerate(lst)}

    def line(speaker, text, score=0, **fmt):
        v = {"chance permanent": F32(100.0), "chance temporary": F32(100.0), "repetition limit": 0, "score bonus": score,
             "speaker": speaker, "target is type": 0}
        v.update(texts(text, **fmt))
        return s.new("DIALOGUE_LINE", "DIALOGUE_LINE", values=v)

    def child(parent, ln):
        parent.refs.setdefault("lines", []).append(Ref(ln.sid, 0, 0, 0))
        return ln

    def cond_money(ln, amount):
        a = s.new("DIALOG_ACTION", "DIALOG_ACTION", values={"compare by": CE_MORE_THAN, "condition name": DC_PLAYERMONEY, "tag": -1,
                                                           "who": 0, "stringvar": ""})
        ln.refs.setdefault("conditions", []).append(Ref(a.sid, amount - 1, 0, 0))

    W = rules["world"]
    WCODE = W["codes"]
    acts = {}

    def dcond(ln, cname, cmp, who, val, stringvar=""):   # одно DIALOG_ACTION на вид условия; значение — в ссылке (v0), как в ванили
        key = (cname, cmp, who, stringvar)
        if key not in acts:
            acts[key] = s.new("DIALOG_ACTION", "DIALOG_ACTION", values={"compare by": cmp, "condition name": cname, "tag": -1,
                                                                       "who": who, "stringvar": stringvar})
        ln.refs.setdefault("conditions", []).append(Ref(acts[key].sid, val, 0, 0))

    def world_cond(ln, code):   # зарезервированное условие мира: ответ даёт перехват _checkCondition в kmm_diplo.lua
        dcond(ln, W["condition"], CE_EQUALS, T_ME, W["base"] + WCODE[code], W["stringvar"])

    def effect(ln, action, value):
        a = s.new("DIALOG_ACTION", "DIALOG_ACTION", values={"action name": action})
        ln.refs.setdefault("effects", []).append(Ref(a.sid, value, 0, 0))

    def needs(ln, token_sid):
        ln.refs.setdefault("target has item", []).append(Ref(token_sid, 0, 0, 0))

    script = kmod.Item(LUA_SCRIPT_TYPE, 0, "KMM Diplo line script", s.mb._sid(), kmod.CHANGE_NEW | (1 << 4),
                       {"file": FilePath(SCRIPT_FILE), "description": "KMM_Diplo: dialogue line -> KMM_Diplo.on_line (scripts/init/kmm_diplo.lua)"})
    s.mb.items[script.sid] = script

    def run(ln, role, **meta):
        ln.refs.setdefault("run lua script", []).append(Ref(script.sid, 0, 0, 0))
        lines_map[ln.sid] = dict(role=role, **meta)
        return ln

    # ---- предметы: печать, жетоны, письма -----------------------------------------------------------------
    tmpl = ctx.find(*rules["template_item"][:2], sid=rules["template_item"][2])

    def item(name, desc):
        return s.new("ITEM", name, template=tmpl.sid, values={"description": desc, "value": 0, "weight kg": F32(0.1), "trade item": False})

    seal = item("Envoy's Seal", "The seal of an envoy of the Nameless. Whoever carries it speaks for the band: lords, envoys and chiefs "
                                "will hear terms of non-aggression, trade, alliance, vassalage or tribute. Put it away to talk as usual.")
    tok = {k: item(f"Envoy's token ({k.replace('_', ' ')})", "A scrap of the talks. It is gone when the talk is over.") for k in TOKENS}
    letters = {k: item(f"Sealed terms: {k}", "Your terms, sealed and left with their envoy. The answer will come by word of mouth.") for k in KINDS}
    s.report["items"] = 1 + len(tok) + len(letters)

    # ---- дерево диалога ----------------------------------------------------------------------------------
    dlg = s.new("DIALOGUE", "KMM Diplomacy", values={"for enemies": True, "locked": False, "monologue": False, "one at a time": False,
                                                   "chance permanent": F32(100.0), "chance temporary": F32(100.0), "repetition limit": 0,
                                                   "score bonus": 100, "target is type": 0, "tag": "KMM_Diplo"})
    needs(dlg, seal.sid)
    greet = run(child(dlg, line(T_ME, TXT["greet"], score=100)), "open")
    # корень: максимум 4 реплики игрока; предложения — в двух подменю (позиция реплики Lua не важна: он ищет по id в D.lines)
    m_treaty = child(greet, line(T_TARGET, TXT["menu_treaty"]))
    m_tribute = child(greet, line(T_TARGET, TXT["menu_tribute"]))
    sub_treaty = child(m_treaty, line(T_ME, TXT["sub_treaty"]))
    sub_tribute = child(m_tribute, line(T_ME, TXT["sub_tribute"]))
    props = {}
    twins = []   # (реплика с жетоном, родитель, код условия) — близнецы создаются после того, как дерево собрано

    def back(sub):   # «Неважно» — без циклов в дереве: NPC спрашивает, нет ли ещё чего, и прощается
        nm = child(sub, line(T_TARGET, TXT["nevermind"]))
        more = child(nm, line(T_ME, TXT["anything_else"]))
        b2 = run(child(more, line(T_TARGET, TXT["bye"])), "close")
        child(b2, line(T_ME, TXT["bye_ack"]))

    for k in KINDS:
        parent = sub_treaty if k in COUNTER_KINDS else sub_tribute
        p = run(child(parent, line(T_TARGET, TXT["propose"][k])), "propose", kind=k)
        acc = run(child(p, line(T_ME, TXT["accept"][k], score=100)), "commit", kind=k, outcome="accept")
        needs(acc, tok["accept"].sid)
        twins.append((acc, p, "dec_accept"))
        if k == "tribute":
            effect(acc, DA_GIVE_MONEY, money["demand_tribute"])
        if k in COUNTER_KINDS:
            for tier, amount in (("counter_s", money["counter_small"]), ("counter_l", money["counter_large"])):
                c = child(p, line(T_ME, TXT["counter"], score=100, n=amount))
                needs(c, tok[tier].sid)
                twins.append((c, p, "dec_" + tier))
                pay = run(child(c, line(T_TARGET, TXT["pay"], n=amount)), "commit", kind=k, outcome="paid", tier=tier, cats=amount)
                cond_money(pay, amount)
                effect(pay, DA_TAKE_MONEY, amount)
                child(pay, line(T_ME, TXT["paid_ack"]))
                dec = run(child(c, line(T_TARGET, TXT["decline"])), "commit", kind=k, outcome="declined", tier=tier)
                child(dec, line(T_ME, TXT["declined_ack"]))
        ref = run(child(p, line(T_ME, TXT["refuse"][k], score=100)), "commit", kind=k, outcome="refuse")
        needs(ref, tok["refuse"].sid)
        twins.append((ref, p, "dec_refuse"))
        cons = child(p, line(T_ME, TXT["consider"], score=0))   # запасной ответ без жетона/условия: мост диалогов не сработал
        cons.refs["give item"] = [Ref(letters[k].sid, 1, 0, 0)]
        run(cons, "deferred", kind=k)   # S4: если прозвучал при ответе по условию — Lua возвращается к жетонам
    pt = run(child(sub_tribute, line(T_TARGET, TXT["pay_tribute"], n=money["liege_tribute"])), "commit", kind="liege_tribute", outcome="paid",
             cats=money["liege_tribute"])
    needs(pt, tok["liege_due"].sid)
    twins.append((pt, sub_tribute, "liege_due"))
    cond_money(pt, money["liege_tribute"])
    effect(pt, DA_TAKE_MONEY, money["liege_tribute"])
    child(pt, line(T_ME, TXT["pay_tribute_ack"]))
    col = child(sub_tribute, line(T_TARGET, TXT["collect"]))
    needs(col, tok["vassal_due"].sid)
    twins.append((col, sub_tribute, "vassal_due"))
    cack = run(child(col, line(T_ME, TXT["collect_ack"])), "commit", kind="vassal_tribute", outcome="collected", cats=money["vassal_tribute"])
    effect(cack, DA_GIVE_MONEY, money["vassal_tribute"])
    back(sub_treaty)
    back(sub_tribute)
    ren = run(child(greet, line(T_TARGET, TXT["renounce"])), "commit", kind="renounce", outcome="renounce")
    needs(ren, tok["has_pact"].sid)
    twins.append((ren, greet, "has_pact"))
    child(ren, line(T_ME, TXT["renounce_ack"]))
    bye = run(child(greet, line(T_TARGET, TXT["bye"])), "close")
    child(bye, line(T_ME, TXT["bye_ack"]))
    s.report["root_player_lines"] = len(greet.refs["lines"])

    # ---- S4: близнецы ответов без жетона (условие мира вместо «target has item»); поддерево копируется, не делится -----------
    def clone(ln):
        t = s.new("DIALOGUE_LINE", "DIALOGUE_LINE", values=dict(ln.values))
        for cat, rs in ln.refs.items():
            if cat == "lines":
                t.refs["lines"] = [Ref(clone(s.mb.items[r.target]).sid, r.v0, r.v1, r.v2) for r in rs]
            else:
                t.refs[cat] = [Ref(r.target, r.v0, r.v1, r.v2) for r in rs]
        if ln.sid in lines_map:
            lines_map[t.sid] = dict(lines_map[ln.sid])
        return t

    for orig, parent, code in twins:
        t = clone(orig)
        t.refs.pop("target has item", None)
        world_cond(t, code)
        lst = parent.refs["lines"]
        lst.insert(next(i for i, r in enumerate(lst) if r.target == orig.sid) + 1, Ref(t.sid, 0, 0, 0))
        lines_map.setdefault(t.sid, {"role": "reply"})["twin"] = True
        s.report["twin_lines"] += 1
    s.report["root_player_lines_visible"] = len([r for r in greet.refs["lines"] if not lines_map.get(r.target, {}).get("twin")])

    # ---- S4: реплики мира у торговцев/барменов/стражи (монологи на EV_I_SEE_NEUTRAL_SQUAD) + угрозы соперника ------------------
    def world_dialogue(role, code, score, txts, monologue=True, enemies=False, chance=100):
        dl = s.new("DIALOGUE", f"KMM World: {role} {code or 'base'}", values={
            "for enemies": enemies, "locked": False, "monologue": monologue, "one at a time": True,
            "chance permanent": F32(100.0), "chance temporary": F32(float(chance)), "repetition limit": W["repetition_limit"],
            "score bonus": score, "target is type": 0, "tag": "KMM_World"})
        dcond(dl, DC_IS_PLAYER, CE_EQUALS, T_TARGET, 1)
        dcond(dl, DC_TARGET_IN_TALKING_RANGE, CE_EQUALS, T_TARGET, 1)
        if not enemies:
            dcond(dl, DC_IS_ENEMY, CE_EQUALS, T_TARGET, 0)
        if role == "trade":
            dcond(dl, DC_IN_MY_BUILDING, CE_EQUALS, T_TARGET, 1)   # как ванильное «shop welcome customer»: игрок у прилавка
        if code == "bounty":
            dcond(dl, DC_BOUNTY_AMOUNT_ACTUAL, CE_MORE_THAN, T_TARGET, W["bounty_cats"][role])
        elif code:
            world_cond(dl, code)
        child(dl, line(T_ME, txts))
        return dl

    world_dlg = collections.defaultdict(list)
    for role in ("trade", "guard"):
        for code, (score, txts) in TXT_WORLD[role].items():
            world_dlg[role].append(world_dialogue(role, code, score, txts, chance=W["chance"][role]))
    pk_ok, pk_bad = [], []
    for role, pks in W["packages"].items():
        for psid, pname in pks.items():
            it = ctx.M.get(psid)
            if it is None or it.type_name != "DIALOGUE_PACKAGE" or it.name != pname:
                pk_bad.append((role, psid, pname))
                continue
            s.add_refs(psid, "dialogs", [Ref(d.sid, W["event"], 0, 0) for d in world_dlg[role]])
            pk_ok.append(psid)
    s.report["world_dialogues"] = sum(len(v) for v in world_dlg.values())
    s.report["world_packages"] = len(pk_ok)
    s.report["world_packages_missing"] = len(pk_bad)
    ctx.diplo_world_missing = pk_bad
    rival = s.new("DIALOGUE", "KMM World: rival threat", values={
        "for enemies": True, "locked": False, "monologue": True, "one at a time": True, "chance permanent": F32(100.0),
        "chance temporary": F32(100.0), "repetition limit": W["repetition_limit"], "score bonus": 50, "target is type": 0, "tag": "KMM_World"})
    dcond(rival, DC_IS_PLAYER, CE_EQUALS, T_TARGET, 1)
    for code, (score, txts) in TXT_WORLD["rival"].items():
        ln = child(rival, line(T_ME, txts, score=score))
        if code == "bounty":
            dcond(ln, DC_BOUNTY_AMOUNT_ACTUAL, CE_MORE_THAN, T_TARGET, W["bounty_cats"]["rival"])
        elif code:
            world_cond(ln, code)
    s.report["dialogue_lines"] = sum(1 for it in s.mb.items.values() if it.type_name == "DIALOGUE_LINE")

    # ---- посланники: кому прикрепить разговор ---------------------------------------------------------------
    F = cond["factions"]
    excl = set(E["exclude_factions"])
    eligible = {fid for fid, f in F.items() if fid != pf and not f.get("player") and f["name"] not in excl and fid in M
                and (f.get("towns") or f.get("relic") or (f.get("strength") or 0) >= E["min_strength"])}
    squad_fac = collections.defaultdict(list)   # персонаж → [(фракция, роль в отряде)]
    for q in ctx.all("SQUAD_TEMPLATE"):
        fr = q.refs.get("faction") or []
        f = fr[0].target if fr else None
        if not f:
            continue
        for cat in ("leader", "squad", "squad2", "squad3"):
            for r in q.refs.get(cat, []):
                squad_fac[r.target].append((f, cat))

    def faction_of(ch):
        fr = ch.refs.get("faction") or []
        if fr and fr[0].target in eligible:
            return fr[0].target
        lead = sorted({f for f, c in squad_fac.get(ch.sid, []) if c == "leader" and f in eligible})
        if lead:
            return lead[0]
        mem = sorted({f for f, c in squad_fac.get(ch.sid, []) if f in eligible})
        return mem[0] if mem else None

    leaders = {p["leader_sid"] for p in cond.get("towns", [])}
    excl_name = re.compile(E["exclude_name_regex"], re.I)
    ACT_TRADE = 1   # DialogActionEnum.DA_TRADE

    def pkg_dialogs(psid, seen):   # диалоги пакета с учётом inheritsFrom
        if psid in seen or psid not in M:
            return []
        seen.add(psid)
        out = []
        for cat, rs in M[psid].refs.items():
            if cat == "dialogs":
                out += [(r.target, r.v0) for r in rs]
            elif cat == "inheritsFrom":
                for r in rs:
                    out += pkg_dialogs(r.target, seen)
        return out

    def has_trade(dsid, seen):   # в дереве реплик есть эффект DA_TRADE
        if dsid in seen or dsid not in M:
            return False
        seen.add(dsid)
        for r in M[dsid].refs.get("effects", []):
            a = M.get(r.target)
            if a is not None and a.values.get("action name") == ACT_TRADE:
                return True
        return any(has_trade(r.target, seen) for r in M[dsid].refs.get("lines", []))

    def trader_why(ch):
        """Почему персонаж — торговец/генерик (его родной разговор нельзя перекрывать); None — можно."""
        if excl_name.search(ch.name):
            return "name"
        if E.get("exclude_trade_dialog"):
            ds = [d for r in ch.refs.get("dialogue package", []) for d, v0 in pkg_dialogs(r.target, set()) if v0 == 1]
            ds += [r.target for r in ch.refs.get("dialogue", []) if r.target in M and M[r.target].name != "KMM Diplomacy"]
            if any(has_trade(d, set()) for d in ds):
                return "trade dialogue"
        return None
    excluded = []
    name_re = re.compile(E["name_regex"], re.I)
    cands = collections.defaultdict(list)   # фракция → [(приоритет, sid)]
    for ch in ctx.all("CHARACTER"):
        v = ch.values
        if v.get("dumb") or v.get("slave"):
            continue
        fid = faction_of(ch) or ""   # "" — фракция задаётся расстановкой в мире (уровни), Lua узнает её через getFaction()
        uniq = bool(v.get("unique"))
        cls = v.get("NPC class")
        is_leader_squad = any(f == fid and c == "leader" for f, c in squad_fac.get(ch.sid, []))
        if ch.sid in leaders:
            pr = 0
        elif name_re.search(ch.name):
            pr = 1
        elif uniq and cls == E["diplomat_class"]:
            pr = 2
        elif uniq and is_leader_squad and cls in E["boss_classes"]:
            pr = 3
        elif not uniq and cls == E["diplomat_class"]:
            pr = 4
        else:
            continue
        if not fid and pr > 2:   # без фракции в данных — только лидеры, посланники по имени и уникальные OT_DIPLOMAT
            continue
        why = trader_why(ch)
        if why:   # торговцы/генерики посланниками не бывают: фракция остаётся без них (в отчёте — список)
            excluded.append((ch.sid, ch.name, fid, pr, why))
            continue
        cands[fid].append((pr, ch.sid))
    envoys = {}
    extra_dlg = collections.defaultdict(list)   # персонаж → доп. разговоры (посланник + «What is the word?»), пишутся одним add_refs
    for fid, lst in sorted(cands.items()):
        lst.sort()
        n_nonuniq = 0
        picked = []
        for pr, sid in lst:
            if len(picked) >= (E["max_per_faction"] if fid else E["max_unknown_faction"]):
                break
            if pr == 4:
                if n_nonuniq >= E["max_nonunique_per_faction"]:
                    continue
                n_nonuniq += 1
            picked.append((pr, sid))
        for pr, sid in picked:
            extra_dlg[sid].append(Ref(dlg.sid, 0, 0, 0))
            envoys[sid] = fid
            s.report[f"envoys_p{pr}"] += 1
    lore_build(ctx, s, M, T_ME, T_TARGET, line, child, trader_why, extra_dlg)
    astartes_build(ctx, s, M, T_ME, T_TARGET, line, child, extra_dlg, rules.get("astartes_orders"))
    for sid, rs in extra_dlg.items():
        s.add_refs(sid, "dialogue", rs)
    s.report["envoys"] = len(envoys)
    s.report["envoys_excluded_traders"] = len(excluded)
    ctx.diplo_excluded = excluded   # для офлайн-проверки (tools/streams/_diplo_check.py)
    s.report["envoy_factions"] = len(set(envoys.values()) - {""})
    s.report["envoys_faction_at_runtime"] = sum(1 for f in envoys.values() if not f)

    # ---- X3: вызов на поединок (addConversation в рантайме лидерам отрядов-конкурентов; в конце: id прежних записей не сдвигаются)
    duel = s.new("DIALOGUE", "KMM Duel: challenge", values={
        "for enemies": False, "locked": False, "monologue": False, "one at a time": False, "chance permanent": F32(100.0),
        "chance temporary": F32(100.0), "repetition limit": 0, "score bonus": 0, "target is type": 0, "tag": "KMM_Duel"})
    # score bonus 0 (ревью batch6 H3): вызов не перекрывает ванильные разговоры найма/торговли, выбирается наравне с ними
    dcond(duel, DC_IS_ENEMY, CE_EQUALS, T_TARGET, 0)
    world_cond(duel, "duel_open")
    dg = child(duel, line(T_ME, TXT_DUEL["greet"], score=100))
    ask = run(child(dg, line(T_TARGET, TXT_DUEL["challenge"])), "duel_ask")
    acc = run(child(ask, line(T_ME, TXT_DUEL["accept"], score=100)), "duel_start")
    world_cond(acc, "duel_accept")
    effect(acc, DA_FLAG_TEMP_ENEMY, 0)
    effect(acc, DA_ATTACK_CHASE_FOREVER, 0)
    rf = run(child(ask, line(T_ME, TXT_DUEL["refuse"], score=100)), "duel_refused")
    world_cond(rf, "duel_refuse")
    run(child(ask, line(T_ME, TXT_DUEL["busy"], score=0)), "duel_refused")   # запасной: перехват не ответил ни на одно условие
    nv = child(dg, line(T_TARGET, TXT_DUEL["never"]))
    child(nv, line(T_ME, TXT_DUEL["never_ack"]))
    s.report["duel_dialogue"] = 1
    # ---- данные для Lua -----------------------------------------------------------------------------------
    data = {
        "version": 1,
        "dialogue": dlg.sid,
        "script": script.sid,
        "items": {"seal": seal.sid, **{k: t.sid for k, t in tok.items()}},
        "letters": {k: t.sid for k, t in letters.items()},
        "counter_kinds": {k: True for k in sorted(COUNTER_KINDS)},
        "money": {k: v for k, v in money.items() if not k.startswith("_")},
        "lines": lines_map,
        "envoys": envoys,
        "params": {k: v for k, v in rules["lua"].items() if not k.startswith("_")},
        "world": {"cond": W["condition"], "base": W["base"], "codes": dict(WCODE), "rival_dialogue": rival.sid,
                  "rival_events": list(W["rival_events"]), "duel_dialogue": duel.sid, "duel_events": list(W["duel_events"])},
        "duel": {"rival_factions": list(rules["duel"]["rival_factions"])},
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "kmm_diplo_data.lua"), "w", encoding="utf-8", newline="\n") as f:
        f.write("-- generated by tools/streams/diplo.py — do not edit (rules/streams/diplo.json)\nreturn " + lua_lit(data) + "\n")
