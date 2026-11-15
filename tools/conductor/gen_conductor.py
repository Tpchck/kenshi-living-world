"""CONDUCTOR v1 — данные дирижёра → rules/conductor.json (+ копия build/KMM_Conductor/conductor.json, её читает Lua).

Фракции: все с базовыми городами (LORE_MAP) + реликтовые WH-фракции + игрок. Для каждой: города, центр (по координатам
городов из leveldata.level ванили и модов), отношения, соседи по расстоянию, стартовые богатство/сила, амбиция, реликтовая цель.
Пары «город — лидер» (смерть/плен лидера → ванильный world state меняет владельца) — как в v0.
Параметры симуляции — секция "params" (правится руками; генератор её сохраняет, если она уже есть).
python -I -X utf8 tools/conductor/gen_conductor.py [--prune-params]   (--prune-params: только убрать DEAD_PARAMS из готового json)
"""
import collections
import glob
import json
import math
import os
import sys

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
import ctx as _ctx  # noqa: E402
import kmod  # noqa: E402

OUT = os.path.join(ROOT, "rules", "conductor.json")
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
DATA = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"

EXTRA_TOWN_MODS = ["The Shoddy Firearm Mod.mod", "BlackPowder.mod"]
CITY_TYPES = {2, 5, 6, 7}   # TownType: 2 город, 5 крупный комплекс (Rebirth, Port North), 6 крепость, 7 столица/убежище; остальное — владения
RELIC = {  # реликтовые фракции: узкая цель, focused/mobilized (DESIGN.md)
    "Imperial Expedition Remnants": "hunt_chaos", "Astartes survivors": "hunt_chaos", "The Lost Black Sanctuary": "hunt_xenos",
    "Death Watch": "hunt_xenos", "Grey Knight": "hunt_chaos", "Space Necromancer - Sora Dynasty": "guard_tomb",
    "Lost Chaos Space Marines": "spread_chaos", "World Devourer War Gang": "spread_chaos", "Midnight Lord": "spread_chaos"}
AMBITION = {  # амбиции по лору (LORE_MAP); остальные — по типу фракции
    "United Cities": "enrichment", "The Holy Nation": "faith", "Shek Kingdom": "survival", "Tech Hunters": "enrichment",
    "Traders Guild": "enrichment", "Slave Traders": "enrichment", "Western Hive": "survival", "Southern Hive": "expansion",
    "Cannibals": "expansion", "Fogmen": "expansion", "Flotsam Ninjas": "revenge", "Anti-Slavers": "revenge",
    "Holy Nation Outlaws": "revenge", "Greenskins": "expansion", "Skin Bandits": "revenge", "Nomads": "survival",
    "Deadcat": "survival", "Swampers": "enrichment", "Shinobi Thieves": "enrichment", "Empire Peasants": "survival"}
BY_TYPE = {8: "enrichment", 4: "survival", 2: "expansion", 3: "enrichment", 9: "survival", 1: "faith", 7: "enrichment"}


def _astartes():   # A1 (docs/core/ASTARTES.md): ордена космодесанта из rules/streams/relics.json astartes_chapters (единый источник)
    try:
        A = json.load(open(os.path.join(ROOT, "rules", "streams", "relics.json"), encoding="utf-8")).get("astartes_chapters") or {}
    except Exception:
        return {}, set()
    if not A.get("enabled"):
        return {}, set()
    return {c["faction"]: c for c in A.get("chapters", [])}, {sid for sid, _ in A.get("remove_camps", [])}


CHAPTERS, CHAPTER_GONE = _astartes()
RELIC.update({n: c["relic"] for n, c in CHAPTERS.items()})   # ордена — реликтовые фракции: узкая цель (охота на хаос/ксеносов), архетип imperium
# ключи params без читателя в Lua/тестах (DEADCODE.md A2-A5, W1 2026-11-15): генератор вычищает их из сохранённого params
DEAD_PARAMS = [("attacker_weight", "town_strength"), ("attacker_weight", "min_strength"), ("economy", "income_per_town"),
               ("relic", "mobilize_triggers"), ("materialize", "apply_to_player_characters"), ("materialize", "relation_write_min_delta"),
               ("materialize", "gear_enabled"), ("materialize", "gear_swaps_per_day"), ("materialize", "gear_elite_slowdown"),
               ("player_base", "join_raid_min_rel"), ("traces", "column_size"), ("roads", "ambient"), ("roads", "ambient_seconds")]


def prune_params(params):   # ключи без читателя (DEADCODE A2-A5): убираем и из сохранённых ручных params
    n = 0
    for sec, key in DEAD_PARAMS:
        if isinstance(params.get(sec), dict) and key in params[sec]:
            del params[sec][key]
            n += 1
    return n


def prune_only():   # --prune-params: только вычистить DEAD_PARAMS в готовом conductor.json, без перегенерации фракций/городов
    out = json.load(open(OUT, encoding="utf-8"))
    n = prune_params(out["params"])
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(out, open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), "w", encoding="utf-8"), ensure_ascii=False)
    print("pruned params:", n)


DEFAULT_PARAMS = {
    "_doc": "Параметры CONDUCTOR v1. День = игровые сутки.",
    "tick_days": 5,
    "interval": {"_doc": "крупное событие (захват/атака на город по парам «город — лидер») раз в base ± jitter дней", "base_days": 30, "jitter_days": 10},
    "first_event_after_days": 10,
    "attacker_weight": {"exponent": 1.0},
    "outcome": {"base_success": 0.35, "strength_exponent": 1.0, "min_success": 0.05, "max_success": 0.75, "capture_share": 0.4},
    "economy": {"upkeep_per_strength": 0.08, "strength_regen": 0.03, "strength_per_wealth": 0.6,
                "mobilized_upkeep_mult": 3.0, "relic_income": 10, "min_wealth": 0, "collapse_strength": 5, "collapse_wealth": 25, "collapse_share": 0.35,
                "income_city": 8, "income_holding": 2, "city_upkeep_base": 2, "city_upkeep_scale": 0.08, "dist_upkeep": 3, "relic_floor": 0.5},
    "unrest": {"base": 0.04, "decay": 0.02, "garrison_ref": 150, "city_capture_mult": 0.7},
    "test_mode": False,
    "utility": {"act_chance": 0.15, "weights": {
        "raid": {"expansion": 1.2, "enrichment": 1.0, "survival": 0.3, "revenge": 1.4, "faith": 0.8},
        "trade": {"expansion": 0.5, "enrichment": 1.4, "survival": 0.8, "revenge": 0.4, "faith": 0.6},
        "alliance": {"expansion": 0.7, "enrichment": 0.9, "survival": 1.3, "revenge": 1.0, "faith": 0.7},
        "recruit": {"expansion": 1.0, "enrichment": 0.6, "survival": 0.9, "revenge": 1.0, "faith": 1.0},
        "hide": {"expansion": 0.2, "enrichment": 0.4, "survival": 1.5, "revenge": 0.3, "faith": 0.5},
        "capture": {"expansion": 1.5, "enrichment": 0.6, "survival": 0.1, "revenge": 1.2, "faith": 1.1}},
        "raid_gain": 0.12, "raid_loss": 0.15, "capture_min_ratio": 1.25, "raid_weight_mult": 0.6, "capture_weight_mult": 1.5, "betrayal_chance": 0.03, "war_cooldown_days": 20, "recruit_cost": 20, "recruit_gain": 6, "trade_gain": 12},
    "bus": {"_doc": "событие расходится к соседям: дальность и вес по отношениям", "radius": 120000,
            "fear_strength_cost": 0.02, "opportunism_days": 20, "common_enemy_rel": 6, "weak_ratio": 0.6},
    "relic": {"trigger_memory_days": 30,
              "demobilize_after_days": 60, "mobilized_strength_mult": 1.6, "retaliation_days": 30, "focused_act_chance": 0.05},
    "treaties": {"_doc": "типы: nonaggression, trade, defense, military, vassal", "propose_chance": 0.4, "min_trust": -20,
                 "term_days": {"nonaggression": 360, "trade": 240, "defense": 360, "military": 180, "vassal": 720},
                 "trust_betrayal": -60, "trust_unfulfilled": -25, "trust_fulfilled": 10, "trust_decay_per_tick": 0.5,
                 "tribute_share": 0.08, "help_cooldown_days": 30, "vassal_power_ratio": 2.5, "help_cost": 0.1, "break_rel": -30,
                 "relation_on_sign": {"nonaggression": 10, "trade": 15, "defense": 25, "military": 40, "vassal": 20},
                 "relation_on_betrayal": -60},
    "materialize": {"_doc": "материализация в игре (KenshiLua); всё под pcall, флаги отключают", "window_seconds": 15, "min_distance": 1500,
                    "use_on_screen": True, "use_line_of_sight": True, "los_max_distance": 4000,
                    "relations_enabled": True,
                    "dispatch_enabled": True, "dispatch_max_per_day": 1, "dispatch_squad_size": 6},
    "chronicle_path": "C:/KenshiModMap/logs/chronicle.log",
    # --- шаг 1 офлайн-билда (2026-11-12) ---
    "seed": {"_doc": "семя мира: случайное лорное стартовое состояние каждой новой игры (WORLD_FLOW §1)",
             "strength_jitter": 0.25, "wealth_jitter": 0.3, "rel_jitter": 12, "rel_lock": 50, "ambition_shuffle": 0.15,
             "ore_city": [2500, 6000], "ore_holding": [1200, 4000], "ore_mine": [3000, 8000], "mine_flow": [25, 60], "ruin_scrap": [2000, 6000]},
    "ore": {"_doc": "Пик руды (LATE_GAME.md): жилы конечны (yield ∝ (R/R0)^k), рудники — поток с содержанием, переплавка из войны",
            "k": 1.5, "base_yield": 0.035, "demand_per_strength": 0.55, "mine_upkeep": 3, "mine_decay_unpaid": 0.15, "scrap_per_loss": 0.6,
            "smelt_share": 0.5, "stress_wealth_cost": 2.5, "stress_strength_cost": 0.01, "comp_wear_focused": 0.04, "comp_wear_mobilized": 0.3, "metal_price_base": 1.0,
            "crisis_reserve_share": 0.55, "crisis_stress": 1.05, "player_drain_mult": 1.0, "ruin_raid_gain": 120},
    "flows": {"_doc": "потоки WORLD_FLOW §3: наркотики, рабы, краденое, еда; влияют на богатство, цены и слухи",
              "drugs_income": 5, "slaves_income": 6, "stolen_take": 0.03, "fence_cut": 0.3, "food_per_village": 3, "food_per_city": 2,
              "famine_unrest": 0.25, "famine_level": 0.45, "city_self_food": 1, "food_per_holding": 1.2, "bust_chance": 0.08, "slave_raid_chance": 0.1, "theft_chance": 0.25},
    "succession": {"_doc": "смерть/плен лидера → кризис преемственности, а не мгновенное переключение (DESIGN.md World states)",
                   "days": [45, 120], "strength_cost": 0.15, "act_mult": 0.4, "split_chance": 0.05, "split_share": 0.3},
    "shards": {"_doc": "спящие фракции-осколки активирует дирижёр (расколы, варлорды, остатки армий)", "warlord_chance": 0.03,
               "warlord_min_strength": 120, "start_rel": -50, "sleepers_max_active": 6},
    "chaos": {"_doc": "Хаос растёт на нестабильности: культы и прорывы там, где дирижёр фиксирует кризис",
              "crisis_threshold": 2.5, "cooldown_days": 120, "incursion_extra": 0.5, "rift_chance": 0.5, "incursion_chance": 0.25, "cult_wealth_drain": 8, "foothold_strength": 30},
    "player_base": {"_doc": "мотивированные рейды на базу игрока (нужда, месть, богатство); союзники защищают и присоединяются",
                    "min_value": 30, "raid_weight": 0.8, "revenge_rel": -40, "need_stress": 1.2, "greed_ratio": 1.4,
                    "raid_cooldown_days": 60},
    "traces": {"_doc": "видимые следы событий рядом с игроком (KMM_Traces.lua)", "enabled": True, "radius": 70000, "spawn_min": 1800,
               "spawn_max": 3200, "min_gap_seconds": 75, "max_per_day": 8, "max_queue": 12, "first_hour_traces": 4,
               "first_hour_gap_seconds": 420, "tier_squad_size": 5, "refugee_size": 4, "caravan_dead": 3,
               "price_enabled": True, "price_radius": 9000, "price_min": 0.8, "price_max": 1.45, "dead_scan_seconds": 4},
    "self": {"_doc": "самосохранение NPC (KMM_Self.lua)", "enabled": True, "scan_seconds": 3, "radius": 6000, "flee_loss_share": 0.5,
             "weak_tier_gap": 1.5, "surrender_loss_share": 0.75, "surrender_mode": "flee", "surrender_factions_ftype": [8], "cooldown_seconds": 60},
    "goals": {"_doc": "ЦЕЛИ фракций и роль оплотов (GOALS, 2026-11-13). Цель живёт goal_ttl дней; progress растёт от реальных действий (act) и собственных шагов; "
                      "оплот = безопасность + рынок + убежище: danger вокруг оплота -> беженцы/караваны тянутся к нему, владелец нанимает охрану; бандиты обходят сильные оплоты.",
              "enabled": True, "chunk": 14, "act_chunk": 10, "goal_ttl": 100, "goal_gap": 6, "own_step_chance": 0.5, "city_bias_mult": 0.5, "camp_income": 3, "camp_floor": 0.4, "wealth_cap": 320,
              "reward_wealth": 14, "reward_strength": 4, "found_cost": 40, "found_max": 3, "found_income": 1.5, "pilgrim_cost": 3, "route_share": 0.35,
              "danger": {"decay": 0.8, "raid": 1.0, "waylay": 0.6, "chaos_cult": 1.2, "chaos_incursion": 2.0, "slave_raid": 1.0, "attack_repelled": 0.3, "famine": 0.5,
                         "radius": 60000, "feeder_radius": 40000, "refuge_at": 1.2, "refuge_share": 0.05, "refuge_cooldown": 40,
                         "hire_at": 1.8, "hire_cost": 12, "hire_gain": 8, "hire_cooldown": 40, "act_base": {"night": 0.4, "twilight": 0.2, "famine": 0.3}},
              "shield": {"per_stronghold": 0.35, "weak_ratio": 0.6, "weak_boost": 1.3},
              "bias": {"_doc": "цель -> множители utility действий (для держав с городами смягчаются city_bias_mult)",
                       "loot_roads": {"waylay": 2.0, "raid_surplus": 1.4}, "racket": {"raid": 1.5, "waylay": 1.3}, "seize_camp": {"capture_free": 3.0, "expedition": 2.0, "capture": 1.3},
                       "hunt_travelers": {"waylay": 2.2}, "defend_lands": {"hide": 1.4, "recruit": 1.4, "raid": 1.2},
                       "trade_route": {"trade": 2.0, "trade_for": 1.8, "alliance": 1.3}, "pilgrimage": {"alliance": 1.4, "trade": 1.2}, "crusade": {"raid": 1.8, "capture": 1.5},
                       "convert": {"alliance": 1.8, "trade": 1.3}, "found": {"capture_free": 2.5, "recruit": 1.3, "expedition": 1.3}, "grow": {"recruit": 1.6, "trade": 1.4},
                       "patrol": {"raid": 1.2, "recruit": 1.4, "alliance": 1.2}, "scavenge": {"expedition": 3.0, "raid_surplus": 1.2}, "hunt": {"raid": 1.8, "capture": 1.4},
                       "spread": {"raid": 1.6, "capture": 1.5, "waylay": 1.3}, "survive": {"hide": 1.8, "recruit": 1.4, "alliance": 1.4}, "revenge": {"raid": 1.8, "waylay": 1.5, "capture": 1.3}}},
    "guard": {"_doc": "безотказность: каждая рантайм-функция в pcall, при первой ошибке отключается до конца сессии",
              "debug_log": "C:/KenshiModMap/logs/debug.log"},
}

# лорные осколки (LORE_MAP): родитель → кандидаты; плюс общий пул варлордов и остатков разбитых армий
SHARDS = {"The Holy Nation": ["Holy Nation Outlaws", "Flotsam Ninjas"], "United Cities": ["Rebel Swordsmen", "Yabuta Outlaws", "Rebel Farmers"],
          "Shek Kingdom": ["Kral's Chosen"], "Slave Traders": ["Slave Hunters", "Hounds"], "Traders Guild": ["Free Traders", "Trade Ninjas"],
          "Tech Hunters": ["Iron Company"], "Western Hive": ["Red Hive"], "Southern Hive": ["Red Hive"]}
WARLORDS = ["Iron Company", "Twinblades", "Reavers", "Red Sabres", "Dust Bandits", "Starving Bandits", "Bloodraiders"]
FLOW_ROLES = {"drugs": ["Swampers", "Swamp Ninjas", "Trade Ninjas"], "drug_ban": ["The Holy Nation"],
              "slavers": ["Slave Traders", "Hounds", "Manhunters"], "slave_markets": ["United Cities", "The Holy Nation"],
              "anti_slavers": ["Anti-Slavers"], "thieves": ["Shinobi Thieves", "Dust Bandits", "Starving Bandits"],
              "fences": ["Shinobi Thieves", "Trade Ninjas"], "technopriests": ["Tech Hunters", "Imperial Expedition Remnants"]}
# --- ЦЕЛИ (2026-11-13): все сознательные фракции — участники; бездомные (без TOWN) получают лагерь ---
ARCH_AMBITION = {"bandit": "enrichment", "savage": "expansion", "trader": "enrichment", "religion": "faith", "settler": "survival",
                 "robot": "survival", "imperium": "faith", "chaos": "expansion", "xeno": "expansion", "state": "survival"}
ARCH_POWER = {"bandit": (34, 60), "savage": (28, 40), "trader": (20, 120), "religion": (26, 50), "settler": (22, 50), "robot": (32, 40),
              "imperium": (40, 60), "chaos": (40, 40), "xeno": (30, 40), "state": (36, 90)}   # (сила, богатство) лагеря
HOME_SITE = {"bandit", "savage", "robot", "chaos", "xeno", "imperium"}   # лагерь в руине/точке интереса; остальные — у города дружественной фракции
ATLAS = os.path.join(ROOT, "rules", "streams", "atlas.json")
AUDIT = os.path.join(ROOT, "data", "world_audit.json")


def _culture():
    """rules/culture.json (B4 И12): явные архетип/амбиция/видимое имя фракции; fix.json rename_auto.dict — видимые имена
    (нелатиница и франшизы переименованы в KMM_Fix, модель и слухи должны называть так же). Нет файла — пусто."""
    try:
        cf = json.load(open(os.path.join(ROOT, "rules", "culture.json"), encoding="utf-8")).get("factions", {})
    except FileNotFoundError:
        cf = {}
    try:
        rd = json.load(open(os.path.join(ROOT, "rules", "streams", "fix.json"), encoding="utf-8"))["junk_unlink"]["rename_auto"]
        rd = {k: v for k, v in rd.get("dict", {}).items() if not k.startswith("_")} if rd.get("enabled") else {}
    except (FileNotFoundError, KeyError):
        rd = {}
    return cf, rd


CULTURE, RENAME = _culture()


def shown(n):
    """Имя, которое видит игрок (culture display > словарь переименований fix > как в данных)."""
    if not isinstance(n, str):
        return n
    return (CULTURE.get(n) or {}).get("display") or RENAME.get(n) or RENAME.get(n.strip()) or n
MINE_WORDS = ("mine", "drill", "quarr", "iron", "copper", "ore ", "mining")


def town_positions(lo):
    """sid города → (x, z) из GAMESTATE_TOWN_INSTANCE_LIST: ваниль (newland/leveldata/*/leveldata.level) + моды."""
    files = glob.glob(os.path.join(DATA, "newland", "leveldata", "*", "leveldata.level")) + [os.path.join(DATA, "newland", "leveldata.level")]
    for b in lo["base"] + lo["wh"] + lo.get("extra", []):
        files += glob.glob(os.path.join(W, b["id"], "leveldata", "leveldata.level"))
    pos = {}
    for f in files:
        try:
            m = kmod.read(f)
        except Exception:
            continue
        for it in m.items:
            if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
                for ins in it.instances:
                    if ins.target:
                        pos[ins.target] = (ins.pos[0], ins.pos[2])
    return pos


def main():
    lo, van, base, wh = _ctx.load()
    M = {}
    for _, m, _ in van + base + wh:
        kmod.apply(M, m)
    # моды вне основы/WH-слоя, но с обитаемыми городами реальных фракций (ATLAS 2026-11-13: Iron Hearth, Dreg Gunworks — Gunsmiths)
    extra_dirs = []
    for mn in EXTRA_TOWN_MODS:
        hit = glob.glob(os.path.join(W, "*", mn))
        if hit:
            kmod.apply(M, kmod.read(hit[0]))
            extra_dirs.append(os.path.dirname(hit[0]))
    for m in ("KMM_Relics", "KMM_Behavior", "KMM_Atlas"):
        p = os.path.join(ROOT, "build", m, m + ".mod")
        if os.path.exists(p):
            kmod.apply(M, kmod.read(p))
    nm = lambda s: M[s].name if s in M else "?"  # noqa: E731
    fac_of = lambda it: it.refs["faction"][0].target if it.refs.get("faction") and it.refs["faction"][0].target in M else None  # noqa: E731
    pos = town_positions(lo)
    for d in extra_dirs:
        try:
            for it in kmod.read(os.path.join(d, "leveldata", "leveldata.level")).items:
                if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
                    for ins in it.instances:
                        if ins.target:
                            pos.setdefault(ins.target, (ins.pos[0], ins.pos[2]))
        except Exception:
            pass
    towns = [i for i in M.values() if i.type_name == "TOWN"]
    variant = {r.target for t in towns for r in t.refs.get("override town", [])}
    base_towns = [t for t in towns if t.sid not in variant and fac_of(t) and t.sid not in CHAPTER_GONE]   # A1: снятые лагеря космодесанта — не владения
    towns_of = collections.defaultdict(list)
    for t in base_towns:
        towns_of[fac_of(t)].append(t)
    by_name = {}
    for f in M.values():
        if f.type_name == "FACTION":
            by_name.setdefault(f.name, f)
    sel = set(towns_of)
    for n in RELIC:
        if n in by_name:
            sel.add(by_name[n].sid)
    player = next((f.sid for f in M.values() if f.type_name == "FACTION" and f.name == "Nameless"), None)
    squads_of = collections.Counter(fac_of(q) for q in M.values() if q.type_name == "SQUAD_TEMPLATE" and fac_of(q))
    facs = {}
    for sid in sorted(sel):
        f = M[sid]
        if f.values.get("not real"):
            continue
        tw = towns_of.get(sid, [])
        pts = [pos[t.sid] for t in tw if t.sid in pos]
        cx = sum(p[0] for p in pts) / len(pts) if pts else None
        cz = sum(p[1] for p in pts) / len(pts) if pts else None
        relic = RELIC.get(f.name)
        ftype = f.values.get("fundamental type", 4)
        cities = [t.sid for t in tw if t.values.get("type") in CITY_TYPES]
        cap = None
        if cities and cx is not None:
            cp = [c for c in cities if c in pos]
            cap = min(cp, key=lambda c: math.hypot(pos[c][0] - cx, pos[c][1] - cz)) if cp else cities[0]
        elif cities:
            cap = cities[0]
        facs[sid] = {"name": f.name, "relic": relic, "ftype": ftype, "cities": cities, "capital": cap,
                     "ambition": (CULTURE.get(f.name) or {}).get("ambition") or AMBITION.get(f.name) or ("faith" if relic else BY_TYPE.get(ftype, "survival")),
                     "towns": [t.sid for t in tw], "town_names": [t.name for t in tw][:12],
                     "x": round(cx) if cx is not None else None, "z": round(cz) if cz is not None else None,
                     "wealth": 60 + 90 * len(tw) + (200 if relic else 0),
                     "strength": round(15 + 12 * len(tw) + 2 * min(40, squads_of.get(sid, 0)) + (50 if relic else 0)),
                     "rel": {}}
    if player:
        facs[player] = {"name": "Nameless", "relic": None, "ftype": 0, "ambition": "survival", "player": True, "towns": [], "town_names": [],
                        "x": None, "z": None, "wealth": 50, "strength": 10, "rel": {}}
    # ---- ЦЕЛИ: архетипы всех фракций и бездомные участники (бандиты, дикари, культы, странники, роботы, ксено...) ----
    import zlib
    try:
        aud = json.load(open(AUDIT, encoding="utf-8"))["factions_after"]
    except Exception:
        aud = []
    arch_by_name = {}
    for r in aud:
        if r.get("participant") and r.get("archetype"):
            arch_by_name.setdefault(r["name"], r["archetype"])
    for n_, spec_ in CULTURE.items():   # rules/culture.json важнее аудита (B4 Н3: лаборатория роботов-убийц не «поселенцы»)
        if spec_.get("archetype"):
            arch_by_name[n_] = spec_["archetype"]
    FT_ARCH = {8: "bandit", 1: "religion", 3: "trader", 7: "trader", 2: "savage"}
    RELIC_ARCH = {"hunt_chaos": "imperium", "hunt_xenos": "imperium", "guard_tomb": "robot", "spread_chaos": "chaos"}

    def arch_of(fd):
        if fd.get("relic"):
            return arch_by_name.get(fd["name"]) or RELIC_ARCH.get(fd["relic"], "imperium")
        return arch_by_name.get(fd["name"]) or FT_ARCH.get(fd.get("ftype"), "settler" if fd.get("towns") else "bandit")

    hsh = lambda *a: zlib.crc32("|".join(map(str, a)).encode())  # noqa: E731
    site_list = [{"sid": t.sid, "name": t.name, "x": pos[t.sid][0], "z": pos[t.sid][1]} for t in towns
                 if t.sid not in variant and t.sid in pos and t.values.get("type") in (4, 9)]
    city_pts = [pos[c] for fd in facs.values() for c in fd.get("cities", []) if c in pos]
    cap_of = {sid: fd["capital"] for sid, fd in facs.items() if fd.get("capital") in pos}
    skip_names = set(WARLORDS) | {n for v in SHARDS.values() for n in v}
    homeless = {}
    for f in sorted(M.values(), key=lambda i: i.sid):
        if f.type_name != "FACTION" or f.sid in facs or f.name in skip_names or f.name in homeless or f.sid == player:
            continue
        a = arch_by_name.get(f.name)
        if not a or "(test)" in f.name or f.values.get("fundamental type", 4) == 0 or f.name in {x["name"] for x in facs.values()}:
            continue
        homeless[f.name] = f
    used_sites = set()
    for nm_, f in sorted(homeless.items()):
        a = arch_by_name[nm_]
        cx = cz = camp = None
        if a in HOME_SITE and site_list:
            order = sorted(site_list, key=lambda st: hsh(f.sid, st["sid"]))
            far = [st for st in order if st["sid"] not in used_sites and min([math.hypot(st["x"] - px, st["z"] - pz) for px, pz in city_pts] or [1e9]) >= 9000]
            st = (far or [st for st in order if st["sid"] not in used_sites] or order)[0]
            used_sites.add(st["sid"])
            cx, cz, camp = st["x"], st["z"], st["sid"]
        else:   # странники и поселенцы: у города фракции, к которой лучше относятся (иначе по хешу)
            rl = {r.target: r.v0 for r in f.refs.get("relations", [])}
            cand = sorted(cap_of, key=lambda fid2: (-(rl.get(fid2, 0)), hsh(f.sid, fid2)))
            if cand:
                camp = cap_of[cand[0]]
                ang = (hsh(f.sid, "a") % 628) / 100.0
                cx, cz = pos[camp][0] + 6000 * math.cos(ang), pos[camp][1] + 6000 * math.sin(ang)
        if cx is None:
            continue
        pw = ARCH_POWER.get(a, (25, 50))
        facs[f.sid] = {"name": f.name, "relic": RELIC.get(f.name), "ftype": f.values.get("fundamental type", 8), "cities": [], "capital": None,
                       "ambition": ARCH_AMBITION.get(a, "survival"), "towns": [], "town_names": [], "x": round(cx), "z": round(cz),
                       "wealth": pw[1], "strength": pw[0], "rel": {}, "townless": True, "arch": a, "camp": camp,
                       "camp_name": M[camp].name if camp in M else camp}
    # A1: орден без города — лагерь модели в руине/точке интереса своего региона (первый биом spawns), архетип imperium (цели hunt/scavenge/survive)
    if CHAPTERS:
        import areas
        rmap = areas.RegionMap(M)
        biome_at = lambda st: getattr(rmap.at(st["x"], st["z"]), "name", None)  # noqa: E731
        for sid, fd in sorted(facs.items()):
            ch = CHAPTERS.get(fd["name"])
            if not ch or fd.get("x") is not None:
                continue
            home = [b for b, _ in ch["spawns"]]
            free = [st for st in site_list if st["sid"] not in CHAPTER_GONE]
            cand = [st for st in free if biome_at(st) == home[0]] or [st for st in free if biome_at(st) in home]
            if not cand:
                print(f"A1: орден {fd['name']}: нет руины в {home}")
                continue
            st = sorted(cand, key=lambda st: hsh(sid, st["sid"]))[0]
            fd.update({"x": round(st["x"]), "z": round(st["z"]), "townless": True, "arch": "imperium", "camp": st["sid"],
                       "camp_name": st["name"], "region": home})
    for sid, fd in facs.items():
        f = M[sid]
        for r in f.refs.get("relations", []):
            if r.target in facs and r.target != sid:
                fd["rel"][r.target] = r.v0
        if fd.get("townless") and fd["arch"] in ("bandit", "savage"):   # без записи об отношениях — половина «отношения по умолчанию» (бандиты не любят никого)
            dflt = f.values.get("default relation", 0)
            if dflt < 0:
                for b in facs:
                    if b != sid and b not in fd["rel"] and not (sid in facs[b]["rel"]):
                        fd["rel"][b] = max(-60, dflt // 2)
    for a, fa in facs.items():   # симметрия: если у B нет записи об A — берём запись A
        for b, v in list(fa["rel"].items()):
            facs[b]["rel"].setdefault(a, v)
    for a, fa in facs.items():   # соседи по расстоянию
        if fa["x"] is None:
            fa["near"] = []
            continue
        d = []
        for b, fb in facs.items():
            if b != a and fb["x"] is not None:
                d.append((math.hypot(fa["x"] - fb["x"], fa["z"] - fb["z"]), b))
        fa["near"] = [[b, round(dist)] for dist, b in sorted(d)[:10]]
    # пары «город — лидер» из v0 (смерть/плен лидера → ванильный override меняет владельца)
    old = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {}
    pairs = old.get("towns", [])
    params = old.get("params") or DEFAULT_PARAMS
    for k, v in DEFAULT_PARAMS.items():   # новые ключи дополняем, ручные правки сохраняем
        params.setdefault(k, v)
    prune_params(params)
    # KMM_Cleanup включён: убранные лагеря не города ни одной фракции (иначе склад/события/захват шли бы на пустое место)
    _lo0 = json.load(open(os.path.join(ROOT, "rules", "load_order.json"), encoding="utf-8"))
    if _lo0.get("new_game", {}).get("KMM_Cleanup") is True:
        _gone0 = {c["camp"] for c in json.load(open(os.path.join(ROOT, "rules", "cleanup.json"), encoding="utf-8"))["camps"]}
        for fd in facs.values():
            for k in ("towns", "cities"):
                if isinstance(fd.get(k), list):
                    fd[k] = [t for t in fd[k] if t not in _gone0]
    town_info = {}
    import zlib
    for sid, fd in facs.items():
        for t in fd["towns"]:
            typ = M[t].values.get("type")
            nml = M[t].name.lower()
            mine = any(w in nml for w in MINE_WORDS) or (typ in (1, 3) and zlib.crc32(t.encode()) % 100 < 30)
            town_info[t] = {"kind": "city" if t in fd["cities"] else "holding", "name": M[t].name, "type": typ, "mine": mine,
                            "x": round(pos[t][0]) if t in pos else None, "z": round(pos[t][1]) if t in pos else None}
    try:
        _sh = json.load(open(ATLAS, encoding="utf-8"))["stronghold"]
        sh_f = {int(k): v for k, v in _sh["factor"].items()}
        sh_fac = set(_sh.get("factions", {}))
    except Exception:
        sh_f, sh_fac = {2: 1.3, 5: 1.5, 6: 1.75, 7: 2.0}, set(facs)
    for sid, fd in facs.items():
        for t in fd.get("cities", []):
            ti = town_info.get(t)
            if ti and sid in sh_fac and ti["type"] in sh_f:
                ti["sh"] = sh_f[ti["type"]]   # оплот (ATLAS stronghold: города сильных фракций): коэффициент охраны по типу
    # спящие осколки: лорные кандидаты и варлорды, которых нет среди активных фракций
    by_name_real = {f.name: f for f in M.values() if f.type_name == "FACTION" and not f.values.get("not real")}
    name_to_sid = {fd["name"]: s for s, fd in facs.items()}
    shards = {}
    for parent, cands in SHARDS.items():
        if parent not in name_to_sid:
            continue
        lst = []
        for c in cands:
            if c in by_name_real:
                sid = by_name_real[c].sid
                if sid not in facs:
                    facs[sid] = {"name": c, "relic": RELIC.get(c), "ftype": by_name_real[c].values.get("fundamental type", 8), "cities": [], "capital": None,
                                 "ambition": "revenge", "towns": [], "town_names": [], "x": None, "z": None, "wealth": 40, "strength": 25,
                                 "rel": {}, "sleeper": True, "near": []}
                lst.append(sid)
        if lst:
            shards[name_to_sid[parent]] = lst
    warlords = []
    for c in WARLORDS:
        if c in by_name_real:
            sid = by_name_real[c].sid
            if sid not in facs:
                facs[sid] = {"name": c, "relic": RELIC.get(c), "ftype": by_name_real[c].values.get("fundamental type", 8), "cities": [], "capital": None,
                             "ambition": "expansion", "towns": [], "town_names": [], "x": None, "z": None, "wealth": 40, "strength": 25,
                             "rel": {}, "sleeper": True, "near": []}
            warlords.append(sid)
    for sid, fd in facs.items():
        if fd.get("sleeper"):
            for r in M[sid].refs.get("relations", []):
                if r.target in facs and r.target != sid:
                    fd["rel"][r.target] = r.v0
    for fd in facs.values():
        fd.setdefault("arch", arch_of(fd))
    roles = {k: [name_to_sid.get(n) or (by_name_real[n].sid if n in by_name_real and by_name_real[n].sid in facs else None) for n in v] for k, v in FLOW_ROLES.items()}
    roles = {k: [x for x in v if x] for k, v in roles.items()}
    # места: руины и точки интереса (скрап-поля, реликтовые встречи) — все города типа 4/9 с координатами
    sites = []
    # KMM_Cleanup включён (новая игра): убранные лагеря не служат «местами» (иначе события шли бы на пустое место)
    _lo = json.load(open(os.path.join(ROOT, "rules", "load_order.json"), encoding="utf-8"))
    gone = set()
    if _lo.get("new_game", {}).get("KMM_Cleanup") is True:
        gone = {c["camp"] for c in json.load(open(os.path.join(ROOT, "rules", "cleanup.json"), encoding="utf-8"))["camps"]}
    for t in towns:
        if t.sid in variant or t.sid not in pos or t.sid in gone:
            continue
        if t.values.get("type") in (4, 9):
            sites.append({"sid": t.sid, "name": t.name, "kind": "ruins" if t.values.get("type") == 4 else "poi",
                          "x": round(pos[t.sid][0]), "z": round(pos[t.sid][1])})
    # VASSALS (2026-11-14, rules/vassals.json, docs/VASSALS.md): стартовые вассалы и региональные союзы по лору/географии,
    # жёсткие запреты (мятежники не договариваются с государством, против которого восстали, и с его вассалами/союзниками),
    # чёрные рынки — нейтральные хабы, где бандиты сбывают рабов/краденое/дурь, а крупные фракции скупают без договора.
    VS = json.load(open(os.path.join(ROOT, "rules", "vassals.json"), encoding="utf-8"))
    f_of = lambda n: name_to_sid.get(n)  # noqa: E731
    seed, na_pairs, closure = [], set(), []
    def ban(a, b):
        if a and b and a != b:
            na_pairs.add(tuple(sorted((a, b))))
    for r in VS["never_ally"]["rebels"]:
        for ag in r["against"]:
            ban(f_of(r["rebel"]), f_of(ag))
        if r.get("closure") and f_of(r["rebel"]):
            closure.append({"rebel": f_of(r["rebel"]), "against": [f_of(x) for x in r["against"] if f_of(x)]})
    for w in VS["never_ally"]["state_wars"]:
        ban(f_of(w["a"]), f_of(w["b"]))
    for bl in VS["never_ally"].get("blocs", []):
        for m in bl["members"]:
            for o in bl["never_with"]:
                ban(f_of(m), f_of(o))
    for v in VS["vassals"]:
        a, b = f_of(v["overlord"]), f_of(v["vassal"])
        if a and b and tuple(sorted((a, b))) not in na_pairs:
            seed.append({"t": "vassal", "a": a, "b": b, "why": "old allegiance", "sleeper": bool(v.get("sleeper"))})
    for v in VS["regional_allies"]:
        a, b = f_of(v["a"]), f_of(v["b"])
        if a and b and tuple(sorted((a, b))) not in na_pairs:
            seed.append({"t": v.get("type", "defense"), "a": a, "b": b, "why": "regional allies"})
    # закрытие на старте: мятежник не в союзе с вассалом/союзником того, против кого восстал
    for c in closure:
        for s_ in seed:
            for ag in c["against"]:
                if ag in (s_["a"], s_["b"]):
                    ban(c["rebel"], s_["b"] if s_["a"] == ag else s_["a"])
    seed = [s_ for s_ in seed if tuple(sorted((s_["a"], s_["b"]))) not in na_pairs]
    tinfo_by_name = {}
    for tsid, ti in town_info.items():
        tinfo_by_name.setdefault(ti.get("name"), tsid)
    markets = []
    for m in VS["black_markets"]:
        tsid = tinfo_by_name.get(m["hub"])
        if tsid and f_of(m["owner"]):
            markets.append({"town": tsid, "name": m["hub"], "owner": f_of(m["owner"]), "goods": m["goods"]})
    MR = VS["market_rules"]
    mrules = {k: {g: [f_of(n) for n in lst if f_of(n)] for g, lst in MR.get(k, {}).items()} for k in ("sellers", "buyers", "buyer_forbidden")}
    vassals_out = {"seed": seed, "never_ally": sorted(list(p) for p in na_pairs), "closure": closure, "markets": markets, "market": mrules}
    print(f"VASSALS: стартовых договоров {len(seed)} (вассалов {sum(1 for x in seed if x['t'] == 'vassal')}), запретов {len(na_pairs)}, "
          f"мятежников с замыканием {len(closure)}, рынков {len(markets)}/{len(VS['black_markets'])}")
    # COHAB (баг Mongrel 2026-11-14): фракции, живущие в одном городе (хозяин TOWN + фракции residents/bar squads/default resident).
    # Дирижёр не пишет им в движок вражду (нижняя граница 0): модель может их ссорить, стража и лавки — нет.
    cohab = set()
    for t in M.values():
        if t.type_name != "TOWN" or t.values.get("REMOVED"):
            continue
        own = {x.target for x in t.refs.get("faction", [])}
        fs = set(own)
        for cat in ("residents", "bar squads", "default resident"):
            for x in t.refs.get(cat, []):
                sq = M.get(x.target)
                if sq is not None and sq.values.get("is trader"):   # лавки и бармены; пленники и захватчики — не соседи
                    fs.update({y.target for y in sq.refs.get("faction", [])} or own)
        fs = sorted(f for f in fs if f in facs and f != player)
        for i, a_ in enumerate(fs):
            for b_ in fs[i + 1:]:
                # только пары, что по данным уживаются (rel ≥ 0 в обе стороны): пленники в клетках и захваченные варианты городов
                # дают «соседей»-лорных врагов (HN↔Shek, Mongrel↔Fogmen) — их войну не гасим
                if facs[a_]["rel"].get(b_, 0) >= 0 and facs[b_]["rel"].get(a_, 0) >= 0:
                    cohab.add((a_, b_))
    print(f"COHAB: соседей по городу {len(cohab)} пар")
    # видимые имена (B4 Н1/Н2): после всех сопоставлений по имени — как их покажет игра с KMM_Fix
    for fd in facs.values():
        fd["name"] = shown(fd["name"])
        if fd.get("town_names"):
            fd["town_names"] = [shown(x) for x in fd["town_names"]]
        if fd.get("camp_name"):
            fd["camp_name"] = shown(fd["camp_name"])
    for ti in town_info.values():
        ti["name"] = shown(ti.get("name"))
    for st_ in sites:
        st_["name"] = shown(st_.get("name"))
    for m_ in markets:
        m_["name"] = shown(m_.get("name"))
    throes = any("Throes" in b.get("file", "") or b.get("id") == "1762149693" for b in lo.get("extra", []))
    out = {"_doc": "CONDUCTOR v1 (tools/conductor/gen_conductor.py). params — правится руками; factions/towns — генерируются.",
           "version": 1, "params": params, "player_faction": player, "factions": facs, "towns": pairs, "town_info": town_info,
           "shards": shards, "warlords": warlords, "roles": roles, "sites": sites, "throes": throes, "vassals": vassals_out,
           "cohab": sorted(list(p) for p in cohab)}
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dst = os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json")
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"cities {sum(1 for v in town_info.values() if v['kind'] == 'city')}, holdings {sum(1 for v in town_info.values() if v['kind'] == 'holding')}")
    print(f"factions {len(facs)} (relic {sum(1 for f in facs.values() if f['relic'])}, with pos {sum(1 for f in facs.values() if f['x'] is not None)}), "
          f"town positions {len(pos)}, pairs {len(pairs)}, player {player}")
    tl = [f for f in facs.values() if f.get("townless")]
    print(f"townless {len(tl)}: ", collections.Counter(f["arch"] for f in tl).most_common(), "strongholds", sum(1 for v in town_info.values() if v.get("sh")))
    print("ambitions:", collections.Counter(f["ambition"] for f in facs.values()).most_common())


if __name__ == "__main__":
    prune_only() if "--prune-params" in sys.argv else main()
