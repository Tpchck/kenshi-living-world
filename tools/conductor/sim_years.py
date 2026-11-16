"""Офлайн-прогон дирижёра на LuaJIT из KenshiLua (lua51.dll) без игры: N лет, срезы по годам, проверка критериев живости.
python -I -X utf8 tools/conductor/sim_years.py [years=15] [seed=2026] [--stub|--no-stock]
Склады: если есть build/KMM_Stock/scripts/kmm_stock_model.lua (контракт STOCK: return M; M.init(stock, cstate, cfg),
M.day(stock, cstate, day, emit); stock = cstate.stock), модель вызывается раз в игровой день; иначе (или --stub) —
заглушка tools/conductor/stock_stub_model.lua. Необязательно в модели: M.view(stock, cstate) → {[sid] = {[cat] = qty}},
M.bounds(stock, cstate, sid, cat) → lo, hi (дефицит/переполнение); без них — goods-таблицы и 0.2×/3× стартового запаса.
Пути C:/KenshiModMap/logs/ перенаправлены во временную папку (реальная хроника не трогается).
Синтетическая база игрока ставится в центр карты на 1-м году (проверка мотивированных рейдов)."""
import ctypes
import json
import os
import sys
import tempfile

ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
YEARS = int(ARGS[0]) if len(ARGS) > 0 else 15
SEED = int(ARGS[1]) if len(ARGS) > 1 else 2026
STOCK_MODEL = r"C:\KenshiModMap\build\KMM_Stock\scripts\kmm_stock_model.lua"
STOCK_STUB = r"C:\KenshiModMap\tools\conductor\stock_stub_model.lua"
if "--no-stock" in sys.argv:
    MODEL = None
elif "--stub" in sys.argv or not os.path.exists(STOCK_MODEL):
    MODEL = STOCK_STUB
else:
    MODEL = STOCK_MODEL
RAWP = ("pairs = ORIG_PAIRS" + chr(10)) if "--rawpairs" in sys.argv else ""   # только замер времени: без сортировки pairs (быстрее, недетерминированно)
NOGOALS = ("KMM_Conductor.cfg().params.goals.enabled = false" + chr(10)) if "--nogoals" in sys.argv else ""
MODEL_LUA = "nil" if MODEL is None else '"' + MODEL.replace("\\", "/") + '"'
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
OUT = r"C:\KenshiModMap\tools\conductor\out"
os.makedirs(OUT, exist_ok=True)
TMP = tempfile.mkdtemp(prefix="kmm_sim_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        raise RuntimeError(name + ": " + L.lua_tolstring(st, -1, None).decode("utf-8", "replace"))


run(f'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"); return real_open(p, m) end
-- детерминизм: порядок pairs в LuaJIT зависит от хеш-сида строк -> в симуляции обходим ключи в отсортированном порядке
ORIG_PAIRS = pairs
do
  local rawpairs, rank = pairs, {{ number = 1, string = 2, boolean = 3 }}
  local function lt(a, b)
    local ta, tb = type(a), type(b)
    if ta ~= tb then return (rank[ta] or 9) < (rank[tb] or 9) end
    if ta == "number" or ta == "string" then return a < b end
    return tostring(a) < tostring(b)
  end
  function pairs(t)
    local ks, n = {{}}, 0
    for k in rawpairs(t) do n = n + 1; ks[n] = k end
    table.sort(ks, lt)
    local i = 0
    return function() i = i + 1; local k = ks[i]; if k ~= nil then return k, t[k] end end, t, nil
  end
end
{RAWP}KenshiLua = {{ log = function(s) end }}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f; return n end
function getGameWorld() error("no game") end
function getPlayerInterface() error("no game") end
''', "stubs")
WS_STUB = """
KMM_Native = { available = true, held = {}, calls = 0 }
function KMM_Native.ws_set(sid, v) KMM_Native.calls = KMM_Native.calls + 1; KMM_Native.held[sid] = v; return true end
function KMM_Native.ws_clear(sid) local h = KMM_Native.held[sid] ~= nil; KMM_Native.held[sid] = nil; return h end
function KMM_Native.ws_clear_all() KMM_Native.held = {}; return 0 end
"""
if "--ws" in sys.argv:   # LINKN: фейковый KMM_Native (всегда доступен), в итог попадает KMM_Conductor.ws_stats()
    run(WS_STUB, "ws_stub")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
local function q(s) return '"' .. tostring(s):gsub('\\', '\\\\'):gsub('"', '\\"') .. '"' end
function JSON(v)
  local t = type(v)
  if t == "table" then
    local parts, isarr = {}, (#v > 0)
    if isarr then for _, x in ipairs(v) do parts[#parts + 1] = JSON(x) end; return "[" .. table.concat(parts, ",") .. "]" end
    for k, x in pairs(v) do if type(x) ~= "function" then parts[#parts + 1] = q(k) .. ":" .. JSON(x) end end
    return "{" .. table.concat(parts, ",") .. "}"
  elseif t == "number" then if v ~= v or v == math.huge or v == -math.huge then return "0" end; return string.format("%.4g", v)
  elseif t == "boolean" then return tostring(v)
  elseif t == "nil" then return "null" end
  return q(v)
end
''', "json")
run('''
local ffi = require("ffi")
ffi.cdef[[int QueryPerformanceCounter(int64_t*); int QueryPerformanceFrequency(int64_t*);]]
local fq, tmp = ffi.new("int64_t[1]"), ffi.new("int64_t[1]")
ffi.C.QueryPerformanceFrequency(fq)
local FQ = tonumber(fq[0])
function HRT() ffi.C.QueryPerformanceCounter(tmp); return tonumber(tmp[0]) / FQ end   -- мкс-таймер (os.clock в Windows - 15 мс)
''', "hrt")
run(f'''
math.randomseed({SEED})
KMM_Conductor.reset()
{NOGOALS}local S = KMM_Conductor.state()
local cx, cz, n = 0, 0, 0
for fid, f in pairs(S.F) do local x, z = KMM_Conductor.fpos(fid); if x and f.alive then cx, cz, n = cx + x, cz + z, n + 1 end end
SNAP = {{}}
local function snap(year)
  local fac = {{}}
  for fid, f in pairs(S.F) do
    local t = 0; for _ in pairs(f.towns) do t = t + 1 end
    fac[fid] = {{ alive = f.alive, towns = t, s = f.strength, w = f.wealth, stress = f.stress or 0, hunger = f.hunger or 0, mode = f.mode,
                 relic = f.relic, comp = f.components, know = f.know or 0, shard = f.shard_active and true or false, gear = (f.gear_shift or 0) < 0, sleeper = f.sleeper and true or false, arch = f.arch, tl = f.townless and true or false, gd = f.goals_done or 0, gf = f.goals_failed or 0, goal = f.goal and f.goal.k or nil, cities = KMM_Conductor.fcities and KMM_Conductor.fcities(fid) or 0 }}
  end
  local nt = 0; for _, tr in pairs(S.treaties) do if tr.active then nt = nt + 1 end end
  local nf = 0; for _ in pairs(S.free or {{}}) do nf = nf + 1 end
  local stats = {{}}; for k, v in pairs(S.stats) do if type(v) == "number" then stats[k] = v end end
  local pn, ps, pmin, pmax, pn0 = 0, 0, 1e9, 0, 0
  for sid, tw in pairs(S.town) do
    if type(tw) == "table" and tw.pop and tw.pop0 then pn = pn + 1; ps = ps + tw.pop / tw.pop0; pn0 = pn0 + tw.pop; pmin = math.min(pmin, tw.pop / tw.pop0); pmax = math.max(pmax, tw.pop / tw.pop0) end
  end
  SNAP[#SNAP + 1] = {{ year = year, pop_rel = pn > 0 and ps / pn or 0, pop_min = pn > 0 and pmin or 0, pop_max = pmax, pop_total = pn0, cities = KMM_Conductor.cities(), fac = fac, treaties_active = nt, free = nf, stats = stats,
                      ore_share = S.ore_share or 1, ore_stress = S.ore_stress or 0, metal_price = S.metal_price or 1,
                      ore_crisis = S.ore_crisis and S.ore_crisis.phase or "none", sm = S.story and S.story.m, sact = S.story and S.story.act }}
end
-- склады: модель STOCK (или заглушка), раз в игровой день; ошибка модели = guard (отключение до конца прогона)
local MP = {MODEL_LUA}
local M, MERR, STOCKSNAP, METAL = nil, nil, {{}}, {{}}
local CFG = KMM_Conductor.cfg()
local emitf = function(ev) return KMM_Conductor.emit(ev) end
if MP then
  local dir = MP:match("^(.*)/[^/]+$")
  package.path = dir .. "/?.lua;" .. package.path
  local ok, m = pcall(dofile, MP)
  if ok and type(m) == "table" and m.init and m.day then
    M = m
    local ok2, e2 = pcall(M.init, S.stock, S, CFG)
    if not ok2 then MERR = "init: " .. tostring(e2); M = nil end
  else MERR = "load: " .. tostring(m) end
end
local function view()
  if M.view then return M.view(S.stock, S) end
  local out, src = {{}}, S.stock.towns or S.stock
  for sid, t in pairs(src) do
    if type(t) == "table" then
      local g = t.q or t.goods or t.stock or t.items or t
      local row, any = {{}}, false
      for k, v in pairs(g) do if type(v) == "number" then row[k] = v; any = true end end
      if any then out[sid] = row end
    end
  end
  return out
end
local INIT
local function stock_snap(year)
  local V = view()
  local owner = {{}}
  for fid, f in pairs(S.F) do if f.alive then for t in pairs(f.towns) do owner[t] = fid end end end
  local tot, def, ovf, base, town_tot, fac_tot, all = {{}}, {{}}, {{}}, {{}}, {{}}, {{}}, 0
  for sid, row in pairs(V) do
    local tt = 0
    for c, q in pairs(row) do
      tot[c] = (tot[c] or 0) + q; tt = tt + q
      local lo, hi
      if M.bounds then lo, hi = M.bounds(S.stock, S, sid, c)
      elseif M.T and M.DEFAULTS and S.stock.towns and S.stock.towns[sid] then   -- норма T города и пороги модели STOCK
        local T, sc = M.T(S.stock, S.stock.towns[sid]), S.stock.cfg or {{}}
        lo, hi = (sc.deficit or M.DEFAULTS.deficit or 0.2) * T, (sc.overflow or M.DEFAULTS.overflow or 3) * T
      else local i0 = INIT[sid] and INIT[sid][c] or 0; if i0 > 0 then lo, hi = 0.2 * i0, 3 * i0 end end
      if lo then
        base[c] = (base[c] or 0) + 1
        if q < lo then def[c] = (def[c] or 0) + 1 end
        if hi and q > hi then ovf[c] = (ovf[c] or 0) + 1 end
      end
    end
    town_tot[sid] = tt; all = all + tt
    local o = owner[sid] or "free"
    fac_tot[o] = (fac_tot[o] or 0) + tt
  end
  local dshare, oshare = {{}}, {{}}
  for c, n in pairs(base) do dshare[c] = (def[c] or 0) / n; oshare[c] = (ovf[c] or 0) / n end
  local tops = {{}}
  for sid, v in pairs(town_tot) do tops[#tops + 1] = {{ sid, v }} end
  table.sort(tops, function(p, q) return p[2] > q[2] end)
  local top5 = {{}}
  for i = 1, math.min(5, #tops) do top5[i] = {{ sid = tops[i][1], share = all > 0 and tops[i][2] / all or 0, owner = owner[tops[i][1]] or "free" }} end
  local ftops = {{}}
  for fid, v in pairs(fac_tot) do ftops[#ftops + 1] = {{ fid, v }} end
  table.sort(ftops, function(p, q) return p[2] > q[2] end)
  local ftop3 = {{}}
  for i = 1, math.min(3, #ftops) do ftop3[i] = {{ fid = ftops[i][1], share = all > 0 and ftops[i][2] / all or 0 }} end
  STOCKSNAP[#STOCKSNAP + 1] = {{ year = year, total = tot, all = all, deficit = dshare, overflow = oshare, top_towns = top5, top_owners = ftop3, towns = #tops }}
end
KMM_Conductor.phase_timer(HRT)
TM = {{ n = 0, adv = 0, drain = 0, adv_max = 0, drain_max = 0, tick_n = 0, tick = 0, tick_max = 0, pump_max = 0 }}
for d = 0, 365 * {YEARS} do
  local t0 = HRT()
  KMM_Conductor.advance(d)
  local t1 = HRT()
  while KMM_Conductor.goals_pending() > 0 do   -- порции очереди целей, как в игре (по одной на вызов advance); замер самой тяжёлой
    local p0 = HRT(); KMM_Conductor.goals_pump(); local pd = HRT() - p0
    if pd > TM.pump_max then TM.pump_max = pd end
  end
  local t2 = HRT()
  TM.n = TM.n + 1; TM.adv = TM.adv + (t1 - t0); TM.drain = TM.drain + (t2 - t1)
  if t1 - t0 > TM.adv_max then TM.adv_max = t1 - t0 end
  if t2 - t1 > TM.drain_max then TM.drain_max = t2 - t1 end
  if d % 5 == 0 then TM.tick_n = TM.tick_n + 1; TM.tick = TM.tick + (t1 - t0); if t1 - t0 > TM.tick_max then TM.tick_max = t1 - t0 end end
  if d == 365 * 4 then KMM_Conductor.emit({{ type = "player_relic_forge", item = "sim" }}) end
  if d == 365 then KMM_Conductor.set_base(cx / n, cz / n, 140, 25) end
  if M then
    local ok, e = pcall(M.day, S.stock, S, d, emitf)
    if not ok then MERR = string.format("day %d: %s", d, tostring(e)); M = nil end
    if M and d == 0 then INIT = view() end
    if M and d % 30 == 0 then local V, m = view(), 0; for _, row in pairs(V) do m = m + (row.metal or 0) end; METAL[#METAL + 1] = {{ d, m }} end
  end
  if d > 0 and d % 365 == 0 then snap(d / 365); if M then stock_snap(d / 365) end end
end
local fh = io.open("C:/KenshiModMap/logs/sim_snap.json", "w")
fh:write(JSON({{ rot = (M and M.rot_stats) and M.rot_stats(S.stock) or nil, snaps = SNAP, stock = STOCKSNAP, metal = METAL, tm = TM, wst = KMM_Conductor.phase_stats(), model = MP or "none", model_error = MERR or "", ws = KMM_Conductor.ws_stats(), story = S.story and {{ hist = S.story.hist, k = S.story.k, ck = S.story.ck, hk = S.story.hk, act = S.story.act, m = S.story.m, cycles = S.story.cycles, cur = S.story.cur }} or nil }})); fh:close()
''', "simulation")

RAW = json.load(open(os.path.join(TMP, "sim_snap.json"), encoding="utf-8"))
snaps = RAW["snaps"]
cfg = json.load(open(r"C:\KenshiModMap\rules\conductor.json", encoding="utf-8"))
nm = lambda fid: cfg["factions"].get(fid, {}).get("name", fid)  # noqa: E731
total_cities = sum(1 for v in cfg["town_info"].values() if v["kind"] == "city")
chron = open(os.path.join(TMP, "chronicle.log"), encoding="utf-8").read().splitlines()
types = {}
per_year = {}
for line in chron:
    c = line.split("\t")
    types[c[2]] = types.get(c[2], 0) + 1
    y = int(float(c[0]) // 365) + 1
    per_year.setdefault(y, {}).setdefault(c[2], 0)
    per_year[y][c[2]] += 1
by_year = {}
for sn in snaps:
    top = sorted(sn["cities"].items(), key=lambda x: -x[1])[:5]
    alive = sum(1 for f in sn["fac"].values() if f["alive"])
    by_year[sn["year"]] = {"top5": [(nm(f), n) for f, n in top], "max_share": round(top[0][1] / total_cities, 3) if top else 0,
                           "alive": alive, "free": sn["free"], "treaties_active": sn["treaties_active"], "ore_share": round(sn["ore_share"], 3),
                           "ore_stress": round(sn["ore_stress"], 2), "metal_price": round(sn["metal_price"], 2), "ore_crisis": sn["ore_crisis"],
                           "stats": sn["stats"]}
last = snaps[-1]
relic = {nm(fid): ("alive " + str(f.get("mode")) + f" s={f['s']:.0f} comp={f.get("comp") or 0:.0f}") if f["alive"] else "fell"
         for fid, f in last["fac"].items() if f.get("relic")}
caps = [(y, v["stats"].get("captures", 0)) for y, v in by_year.items()]
cap_last5 = caps[-1][1] - (caps[-6][1] if len(caps) >= 6 else 0)
st = last["stats"]
POP = {y: {"avg_rel": round(sn["pop_rel"], 3), "min_rel": round(sn["pop_min"], 2), "max_rel": round(sn["pop_max"], 2), "total": round(sn["pop_total"])}
       for y, sn in ((x["year"], x) for x in snaps)}
relic_state = {nm(fid): {"alive": f["alive"], "parts": round(f.get("comp") or 0, 1), "know": round(f.get("know") or 0, 2), "strength": round(f["s"]), "towns": f["towns"]}
               for fid, f in last["fac"].items() if f.get("relic")}
crit = {
    "max_share_le_25": max(v["max_share"] for v in by_year.values()) <= 0.25,
    "not_frozen_last5y_captures": cap_last5,
    "not_dead_alive_end": by_year[YEARS]["alive"],
    "relics_all_alive": all(v != "fell" for v in relic.values()),
    "splits": st.get("splits", 0), "warlords": st.get("warlords", 0), "treaties_signed": st.get("signed", 0), "revolts": st.get("revolts", 0),
    "ore_crisis": last["ore_crisis"] != "none", "ore_crisis_day": st.get("ore_crisis_day"),
}
# --- ЦЕЛИ (GOALS): безгородские фракции (нет городов в данных) — доля, выполнившая хотя бы одну цель; бандиты живы; нагрузка ---
_gl = {fid: f for fid, f in last["fac"].items() if not f.get("sleeper") and f.get("arch")}
_nocity = {fid: f for fid, f in _gl.items() if not cfg["factions"].get(fid, {}).get("cities") and not cfg["factions"].get(fid, {}).get("player")}
_done = [fid for fid, f in _nocity.items() if f.get("gd", 0) >= 1]
_all_done = [fid for fid, f in _gl.items() if f.get("gd", 0) >= 1]
_ban = [f for f in _gl.values() if f.get("arch") == "bandit"]
_tm = RAW.get("tm") or {}
crit["goals"] = {"nocity_factions": len(_nocity), "nocity_share_of_all": round(len(_nocity) / max(1, len(_gl)), 2),
                 "nocity_done_share": round(len(_done) / max(1, len(_nocity)), 2), "all_done_share": round(len(_all_done) / max(1, len(_gl)), 2),
                 "nocity_not_done": sorted(nm(f) for f in _nocity if f not in _done)[:12],
                 "bandits_alive": sum(1 for f in _ban if f["alive"]), "bandits_total": len(_ban),
                 "goals_done": st.get("goals_done", 0), "goals_failed": st.get("goals_failed", 0), "goals_done_townless": st.get("goals_done_townless", 0),
                 "by_arch": {k[11:]: v for k, v in st.items() if k.startswith("goals_done_") and k not in ("goals_done_townless",)},
                 "routes": st.get("routes", 0), "founded": st.get("founded", 0), "pilgrimages": st.get("pilgrimages", 0), "patrols": st.get("patrols", 0),
                 "refuge_pulls": st.get("refuge_pulls", 0), "hires": st.get("hires", 0), "refugees": st.get("refugees", 0),
                 "ms_per_day": round(_tm.get("adv", 0) / max(1, _tm.get("n", 1)) * 1000, 3), "ms_tick_day_avg": round(_tm.get("tick", 0) / max(1, _tm.get("tick_n", 1)) * 1000, 3),
                 "ms_tick_day_max": round(_tm.get("tick_max", 0) * 1000, 2), "ms_goals_pump_max": round(_tm.get("pump_max", 0) * 1000, 2),
                 "phase_ms_max": {k: round(v * 1000, 2) for k, v in sorted((RAW.get("wst") or {}).get("tmax", {}).items(), key=lambda x: -x[1])[:6]},
                 "ms_drain_per_day": round(_tm.get("drain", 0) / max(1, _tm.get("n", 1)) * 1000, 3)}
_raid = {y: sum(v for k, v in d.items() if k in ("raid", "attack_repelled", "town_captured", "waylay")) for y, d in per_year.items()}
_f5 = sum(_raid.get(y, 0) for y in range(1, 6)); _l5 = sum(_raid.get(y, 0) for y in range(YEARS - 4, YEARS + 1))
crit["goals"]["war_last5_vs_first5"] = round(_l5 / max(1, _f5), 2)   # вечная война: рост насилия к концу > 2x = тревога
crit["goals"]["treaties_active_end"] = last["treaties_active"]
crit["goals"]["no_eternal_war"] = crit["goals"]["war_last5_vs_first5"] <= 2.0 and last["treaties_active"] > 0
crit["goals"]["ok"] = crit["goals"]["nocity_done_share"] >= 0.7 and crit["goals"]["bandits_alive"] >= 1 and crit["goals"]["no_eternal_war"]
_rot = RAW.get("rot")   # TOWNLIFE: ротация лавок раз в 2-3 дня; потолки доли гильдии и специализации среди неуникальных лавок
if _rot:
    crit["townlife"] = {"rotations": _rot["n"], "per_year": round(_rot["n"] / YEARS, 1), "shops": _rot["shops"],
                        "max_guild_share": round(_rot["max_guild_ever"], 3), "max_spec_share": round(_rot["max_spec_ever"], 3),
                        "max_guild_share_ok": _rot["max_guild_ever"] <= 0.25, "max_spec_share_ok": _rot["max_spec_ever"] <= 0.35}
crit["pop_ok"] = all(0.3 <= v["avg_rel"] <= 1.4 for v in POP.values())
crit["contra"] = {"smuggle_run": types.get("smuggle_run", 0), "gear_worn": types.get("gear_worn", 0),
                  "per_year_max": max([v.get("smuggle_run", 0) for v in per_year.values()] or [0])}
_gs = {}
for sn in snaps:
    al = [f for f in sn["fac"].values() if f["alive"] and not f.get("sleeper")]
    _gs[sn["year"]] = round(sum(1 for f in al if f.get("gear")) / max(1, len(al)), 3)
crit["gear_shift_share_by_year"] = _gs
crit["loop_events"] = {k: types.get(k, 0) for k in ("trade_for", "raid_surplus", "refugees", "relic_salvage", "relic_forge_known")}
_rob = {k: st.get(k, 0) for k in ("waylay", "waylay_try", "waylay_need", "waylay_greed", "waylay_revenge", "loot_sold", "loot_sold_own", "loot_sold_ally",
                                  "loot_sold_neutral", "loot_sold_contra", "loot_melted", "gear_loot")}
_rob["waylay_per_year"] = round(types.get("waylay", 0) / YEARS, 1)
_rob["loot_sold_per_year"] = round(types.get("loot_sold", 0) / YEARS, 1)
_ext = _rob["loot_sold_ally"] + _rob["loot_sold_neutral"]
_rob["neutral_share_of_external"] = round(_rob["loot_sold_neutral"] / max(1, _ext), 2)
_bw = [round(f["w"]) for f in last["fac"].values() if f["alive"] and not f.get("sleeper") and f["towns"] == 0]
_rob["townless_wealth_max"] = max(_bw or [0]); _rob["townless_wealth_n"] = len(_bw)
_rob["wealth_max_all"] = round(max([f["w"] for f in last["fac"].values() if f["alive"]] or [0]))
_rob["townless_wealth_max_by_year"] = {sn["year"]: round(max([f["w"] for f in sn["fac"].values() if f["alive"] and not f.get("sleeper") and f["towns"] == 0] or [0])) for sn in snaps}
crit["robbery"] = _rob
summary = {"pop_by_year": POP, "relic_state": relic_state, "years": YEARS, "seed": SEED, "total_cities": total_cities, "events_total": len(chron), "criteria": crit,
           "events_by_type": dict(sorted(types.items(), key=lambda x: -x[1])), "relic_fate": relic,
           "by_year": {y: {k: v for k, v in by_year[y].items() if k != "stats"} for y in by_year if y in (1, 3, 5, 10, 15) or y == YEARS},
           "stats_end": st}
crit["max_share"] = max(v["max_share"] for v in by_year.values())
summary["reference"] = {"max_share_le_21": crit["max_share"] <= 0.215}   # справочная метрика (не критерий дизайна; критерий — max_share_le_25)


OWN_TYPES = {"town_captured", "town_rejoined"}   # события самого дирижёра с префиксом town_ — не склад и не город за работой


def is_st(k):
    return k.startswith(("stock_", "town_")) and k not in OWN_TYPES


def stock_summary(raw, crisis_day):
    """Склады: запасы по категориям, доли дефицита/переполнения, накопители, металл вокруг рудного кризиса, поток событий."""
    out = {"model": raw.get("model"), "model_error": raw.get("model_error") or None}
    ss = raw.get("stock") or []
    if not ss:
        return out
    r2 = lambda x: round(x, 2)  # noqa: E731
    tname = lambda sid: cfg["town_info"].get(sid, {}).get("name", sid)  # noqa: E731
    out["by_year"] = {s["year"]: {"total": {c: round(v) for c, v in sorted(s["total"].items())},
                                  "deficit": {c: r2(v) for c, v in sorted(s["deficit"].items()) if v > 0},
                                  "overflow": {c: r2(v) for c, v in sorted(s["overflow"].items()) if v > 0},
                                  "top_towns": [(tname(t["sid"]), nm(t["owner"]), r2(t["share"])) for t in s["top_towns"][:3]],
                                  "top_owners": [(nm(t["fid"]), r2(t["share"])) for t in s["top_owners"]]} for s in ss}
    first, lastss = ss[0], ss[-1]
    # снежный ком: доля мирового запаса у топ-1 города и топ-1 владельца — в начале и в конце; рост общего запаса
    out["snowball"] = {"top_town_share_y1": r2(first["top_towns"][0]["share"]), "top_town_share_end": r2(lastss["top_towns"][0]["share"]),
                       "top_owner_share_y1": r2(first["top_owners"][0]["share"]), "top_owner_share_end": r2(lastss["top_owners"][0]["share"]),
                       "world_total_ratio_end_vs_y1": r2(lastss["all"] / first["all"]) if first["all"] else None,
                       "cat_ratio_end_vs_y1": {c: r2(lastss["total"].get(c, 0) / v) for c, v in first["total"].items() if v}}
    # вечный дефицит/изобилие: категории с долей ≥ 50 % городов в дефиците/переполнении в каждом из последних 5 лет
    tail = ss[-5:]
    out["chronic_deficit"] = sorted(c for c in lastss["deficit"] if all(s["deficit"].get(c, 0) >= 0.5 for s in tail))
    out["chronic_overflow"] = sorted(c for c in lastss["overflow"] if all(s["overflow"].get(c, 0) >= 0.5 for s in tail))
    metal = raw.get("metal") or []
    if crisis_day and metal:
        before = [m for d, m in metal if crisis_day - 120 <= d < crisis_day]
        after1 = [m for d, m in metal if crisis_day + 60 <= d < crisis_day + 240]
        after2 = [m for d, m in metal if crisis_day + 365 <= d < crisis_day + 730]
        avg = lambda xs: sum(xs) / len(xs) if xs else None  # noqa: E731
        b = avg(before)
        out["metal_vs_ore_crisis"] = {"crisis_year": r2(crisis_day / 365), "metal_before": round(b) if b else None,
                                      "ratio_2_8_months_after": r2(avg(after1) / b) if b and after1 else None,
                                      "ratio_1_2_years_after": r2(avg(after2) / b) if b and after2 else None}
    out["stock_town_events_per_year"] = {y: sum(v for k, v in d.items() if is_st(k)) for y, d in per_year.items()}
    st_types = {}
    for k, v in types.items():
        if is_st(k):
            st_types[k] = v
    out["stock_town_event_types"] = st_types
    tail300 = chron[-300:]   # журнал S.events (слухи) — кольцо 300: какую долю занимают склад/город
    out["share_of_last300_journal"] = r2(sum(1 for x in tail300 if is_st(x.split("\t")[2])) / max(1, len(tail300)))
    return out


summary["stock"] = stock_summary(RAW, st.get("ore_crisis_day"))
if "--ws" in sys.argv:
    summary["ws"] = RAW.get("ws")
summary["story"] = RAW.get("story")
if summary["story"]:
    summary["story"]["by_year"] = {sn["year"]: [sn.get("sact"), sn.get("sm")] for sn in snaps}
    # обороты: hist режется на обороты по входу в стартовую фазу; годы входа в фазы и длина оборота (годы = день / 365)
    _start = cfg["params"]["story"].get("start", "quiet")
    _cyc = []
    for _act, _day in summary["story"].get("hist") or []:
        if _act == _start or not _cyc:
            _cyc.append({"start_year": round(_day / 365, 2), "phases": []})
        _cyc[-1]["phases"].append(f"{_act} {_day / 365:.2f}")
    for _i, _c in enumerate(_cyc):
        _nxt = _cyc[_i + 1]["start_year"] if _i + 1 < len(_cyc) else None
        _c["len_years"] = round(_nxt - _c["start_year"], 2) if _nxt is not None else None   # None: оборот не закончен к концу прогона
    summary["story"]["cycles_by_hist"] = _cyc
    _cr = set(cfg["params"]["story"].get("cycle", {}).get("crises", []))
    summary["story"]["crises_by_cycle"] = [[p.split()[0] for p in c["phases"] if p.split()[0] in _cr] for c in _cyc]
SUFFIX = ("_raw" if "--rawpairs" in sys.argv else "") + ("_nogoals" if "--nogoals" in sys.argv else "") + ("_nostock" if MODEL is None else ("_stub" if MODEL == STOCK_STUB else ""))
if "--ws" in sys.argv:
    SUFFIX += "_ws"
json.dump(summary, open(os.path.join(OUT, f"sim_{YEARS}y_{SEED}{SUFFIX}.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
open(os.path.join(OUT, f"chronicle_sim_{YEARS}y_{SEED}{SUFFIX}.log"), "w", encoding="utf-8").write("\n".join(chron))
print(json.dumps(summary, ensure_ascii=False, indent=1))
_dbg = os.path.join(TMP, "debug.log")
if os.path.exists(_dbg):
    print("DEBUG.LOG:", open(_dbg, encoding="utf-8").read()[-1500:])
