"""Офлайн-проверки KMM_Diplo на LuaJIT из KenshiLua (lua51.dll), без игры. ≤ нескольких секунд.
1) синтаксис: kmm_diplo.lua, мост dialogue/kmm_diplo_line.lua, сгенерированный kmm_diplo_data.lua, дирижёр с патчем _dev/conductor_patch.lua;
2) оценка интереса на сценариях (чистая функция evaluate);
3) рантайм на заглушках: «нет персонажей» → ничего; полный разговор (жетоны → очередь → договор у дирижёра); письмо (запасной
   канал); дань вассала; измена игрока; «ошибка API» → отключается только функция, причина в debug.log; путь через патч дирижёра.
python -I -X utf8 build/KMM_Diplo/_dev/test_diplo.py"""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build"
MAIN = B + r"\KMM_Diplo\scripts\init\kmm_diplo.lua"
LINE = B + r"\KMM_Diplo\scripts\dialogue\kmm_diplo_line.lua"
DATA = B + r"\KMM_Diplo\scripts\kmm_diplo_data.lua"
COND = B + r"\KMM_Conductor\scripts\init\KMM_Conductor.lua"
PATCH = B + r"\KMM_Diplo\_dev\conductor_patch.lua"
TMP = tempfile.mkdtemp(prefix="kmm_diplo_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("lua_settop", [ctypes.c_void_p, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p


def new_state():
    st = L.luaL_newstate()
    L.luaL_openlibs(st)
    return st


def compile_only(st, code, name):
    if L.luaL_loadstring(st, code.encode("utf-8")):
        msg = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
        L.lua_settop(st, 0)
        return name + ": " + msg
    L.lua_settop(st, 0)
    return None


def run(st, code, name, ret=False):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 1 if ret else 0, 0):
        msg = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
        L.lua_settop(st, 0)
        raise RuntimeError(name + ": " + msg)
    if ret:
        v = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, 0)
        return v.decode("utf-8", "replace") if v else ""


read = lambda p: open(p, encoding="utf-8").read()  # noqa: E731
FAILS, PASSES = [], []

# ---- 1. синтаксис ---------------------------------------------------------------------------------------------
st = new_state()
cond_src = read(COND)
patch = read(PATCH)
body = patch.split("-- >>> BEGIN KMM_Diplo patch", 1)[1].split("-- <<< END KMM_Diplo patch", 1)[0]
anchor = "KMM_Conductor = {"
assert anchor in cond_src, "anchor not found in conductor"
i = cond_src.index(anchor)
j = cond_src.index("\n", i) + 1
patched = cond_src[:j] + body + cond_src[j:] + "\n_G.KMM_Conductor = KMM_Conductor\n"
for name, src in [("kmm_diplo.lua", read(MAIN)), ("kmm_diplo_line.lua", read(LINE)), ("kmm_diplo_data.lua", read(DATA)),
                  ("KMM_Conductor.lua + patch", patched)]:
    e = compile_only(st, src, name)
    (FAILS if e else PASSES).append(e or f"syntax {name}")
print("patch lines:", len([x for x in body.splitlines() if x.strip()]))

# ---- 2–3. заглушки и сценарии -----------------------------------------------------------------------------------
STUBS = r'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "TMPDIR/"):gsub("^C:/KenshiModMap/state/", "TMPDIR/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "TMPDIR/"); return __rr(p) end
package.path = "C:/KenshiModMap/build/KMM_Diplo/scripts/?.lua;" .. package.path
KenshiLua = { log = function(s) LOGS = (LOGS or "") .. s .. "\n" end }
Events = { h = {} }
function Events.on(n, f) Events.h[n] = Events.h[n] or {}; table.insert(Events.h[n], f) end
function FIRE(n, ...) for _, f in ipairs(Events.h[n] or {}) do f(...) end end
CLOCK = 0; os.clock = function() return CLOCK end
MSGS, PCS, LOADED, MONEY = {}, {}, {}, 3000
FAIL_GETDATA, FAIL_INV = false, false
function CH(id, fid, x, z, player)
  local ch = { id = id, fid = fid, x = x, z = z, items = {}, player = player }
  local inv = {
    getItem = function(_, gd) if (ch.items[gd.sid] or 0) > 0 then return { sid = gd.sid } end end,
    addItem = function(_, item, n) ch.items[item.sid] = (ch.items[item.sid] or 0) + (n or 1); return true end,
    removeItemAutoDestroy = function(_, it, n) ch.items[it.sid] = (ch.items[it.sid] or 0) - (n or 1); return true end,
  }
  ch.getInventory = function() if FAIL_INV then error("getInventory exploded") end; return inv end
  ch.isPlayerCharacter = function() return player end
  ch.getFaction = function() return { getData = function() return { stringID = fid } end } end
  ch.getGameData = function() return { stringID = id } end
  ch.getPosition = function() return { x = ch.x, y = 0, z = ch.z } end
  return ch
end
GW = {
  gamedata = { getData = function(_, sid, t) if FAIL_GETDATA then error("getData exploded") end; return { sid = sid } end },
  theFactory = { createItem = function(_, gd) return { sid = gd.sid } end },
  getCharacterUpdateList = function() local s = {}; for _, c in ipairs(LOADED) do s[c] = true end; return s end,
  showPlayerAMessage_withLog = function(_, t) MSGS[#MSGS + 1] = t end,
}
function getGameWorld() return GW end
function getPlayerInterface() return { getAllPlayerCharacters = function() return PCS end,
  getOwnerships = function() return { getMoney = function() return MONEY end } end } end
-- состояние и конфиг дирижёра (как в KMM_Conductor: S.F/rel/treaties/events, CFG.params.treaties/bus/relic)
function FRESH()
  local F = function(str, w, amb, extra) local f = { alive = true, strength = str, strength0 = str, wealth = w, wealth0 = w, ambition = amb,
    towns = { t1 = true }, trust = {}, opp = {} }; for k, v in pairs(extra or {}) do f[k] = v end; return f end
  S = { last_day = 100, next_id = 1, next_tid = 1, events = {}, treaties = {}, dirty_rel = {}, stats = { signed = 0 }, rel = {},
        F = { P = F(40, 300, "survival", { player = true }), WEAK = F(12, 200, "survival"), BIG = F(400, 900, "expansion", { towns = { a = true, b = true, c = true, d = true } }),
              FRIEND = F(120, 400, "survival"), POOR = F(80, 300, "enrichment", { wealth = 60, hunger = 0.6, stress = 1.5 }),
              ENEMY = F(300, 500, "expansion"), RICH = F(100, 300, "faith", { wealth = 600 }) } }
  for a in pairs(S.F) do S.rel[a] = {} end
  local function R(a, b, v) S.rel[a][b] = v; S.rel[b][a] = v end
  R("WEAK", "P", 0); R("WEAK", "ENEMY", -60); R("BIG", "P", -70); R("FRIEND", "P", 50); R("FRIEND", "ENEMY", -70); R("P", "ENEMY", -80)
  R("POOR", "P", 10); R("RICH", "P", 0)
  S.F.FRIEND.trust.P = 30
  CFG = { player_faction = "P", params = { bus = { radius = 120000 }, relic = { mobilized_strength_mult = 1.6 }, chronicle_path = "TMPDIR/chronicle.log",
          treaties = { term_days = { nonaggression = 360, trade = 240, defense = 360, military = 180, vassal = 720 }, relation_on_sign = { nonaggression = 10, trade = 15, defense = 25, military = 40, vassal = 20 },
                       min_trust = -20, trust_betrayal = -60, relation_on_betrayal = -60 } },
          factions = { WEAK = { name = "Weaklings", near = { { "ENEMY", 50000 } } }, BIG = { name = "Big Empire", near = {} }, FRIEND = { name = "Friends", near = { { "ENEMY", 60000 } } },
                       POOR = { name = "Poor Folk", near = {} }, ENEMY = { name = "Enemy", near = {} }, RICH = { name = "Rich Monks", near = {} }, P = { name = "Nameless", player = true } } }
end
FRESH()
SIGNED = {}
KMM_Conductor = { state = function() return S end, cfg = function() return CFG end }
-- API дирижёра (как в KMM_Conductor.lua: emit/add_rel/add_trust_one/player_sign/player_break) — заглушка пишет в S, как ядро
do
  local K = KMM_Conductor
  local function cl(x) return math.max(-100, math.min(100, x)) end
  local function nm(f) return (CFG.factions[f] or {}).name or tostring(f) end
  local function today() return S.last_day or 0 end
  function K.emit(ev)
    ev.id = S.next_id; S.next_id = S.next_id + 1; ev.day = ev.day or today()
    S.events[#S.events + 1] = ev
    return ev
  end
  function K.add_rel(a, b, dv)
    local v = cl(math.floor(((S.rel[a] or {})[b] or 0) + dv + 0.5))
    S.rel[a] = S.rel[a] or {}; S.rel[b] = S.rel[b] or {}
    if S.rel[a][b] ~= v or S.rel[b][a] ~= v then S.rel[a][b], S.rel[b][a] = v, v; S.dirty_rel[a .. "|" .. b] = true end
  end
  function K.add_trust_one(a, b, dv) local f = S.F[a]; if f then f.trust = f.trust or {}; f.trust[b] = cl((f.trust[b] or 0) + dv) end end
  function K.player_sign(fid, ttype, why, ps)
    local pf, T = CFG.player_faction, CFG.params.treaties
    for _, t in pairs(S.treaties) do
      if t.active and t.type == ttype and ((t.a == fid and t.b == pf) or (t.a == pf and t.b == fid)) then t.term = today() + (T.term_days[ttype] or 360); return t end
    end
    local a, b = fid, pf
    if ttype == "vassal" and ps then a, b = pf, fid end
    local t = { id = S.next_tid, type = ttype, a = a, b = b, since = today(), term = today() + (T.term_days[ttype] or 360), active = true, why = why }
    S.next_tid = S.next_tid + 1; S.treaties[t.id] = t
    K.add_rel(a, b, T.relation_on_sign[ttype] or 10)
    S.stats.signed = (S.stats.signed or 0) + 1
    K.emit({ type = "treaty_signed", a = a, b = b, treaty = ttype, text = nm(a) .. " and " .. nm(b) .. " sealed a " .. ttype .. " pact" })
    return t
  end
  function K.player_break(fid, why, by_player)
    local pf, T, n = CFG.player_faction, CFG.params.treaties, 0
    for _, t in pairs(S.treaties) do
      if t.active and ((t.a == fid and t.b == pf) or (t.a == pf and t.b == fid)) then
        t.active = false; n = n + 1
        if by_player then K.add_trust_one(fid, pf, T.trust_betrayal or -60); K.add_rel(fid, pf, T.relation_on_betrayal or -60) end
        K.emit({ type = by_player and "betrayal" or "treaty_broken", a = t.a, b = t.b, treaty = t.type, text = why })
      end
    end
    return n
  end
end
'''.replace("TMPDIR", TMP)

TESTS = r'''
local R = {}
local function OK(name, cond, info) R[#R + 1] = (cond and "PASS " or "FAIL ") .. name .. (info and (" | " .. tostring(info)) or "") end
local Dm = KMM_Diplo
local data = require("kmm_diplo_data")
local function line_of(role, kind, outcome)
  for sid, m in pairs(data.lines) do if m.role == role and (not kind or m.kind == kind) and (not outcome or m.outcome == outcome) then return sid end end
end
local function ev(fid, kind, extra)
  local ctx = { pf = "P", nchars = 3, money = 3000, day = 100, asked = 0, jitter = 0 }
  for k, v in pairs(extra or {}) do ctx[k] = v end
  return Dm.evaluate(S, CFG, data.params, fid, kind, ctx)
end
-- без API дирижёра модуль не стартует (прямой записи в обход дирижёра больше нет)
do
  local K = KMM_Conductor; local ps = K.player_sign; K.player_sign = nil
  local pc0 = CH("pc0", "P", 0, 0, true); PCS = { pc0 }; LOADED = { pc0 }
  Dm._set_data({ params = {}, counter_kinds = {} })
  for i = 1, 10 do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end
  OK("no conductor API: module idle", not Dm.ready() and next(Dm.disabled()) == nil, tostring(Dm.ready()))
  K.player_sign = ps; PCS, LOADED = {}, {}
end
-- 0. «нет персонажей» → ничего (до данных и без ошибок)
Dm._set_data({ params = {}, counter_kinds = {} })
for i = 1, 20 do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end
OK("no player chars: idle", not Dm.ready() and #Dm.queue() == 0 and next(Dm.disabled()) == nil, tostring(Dm.ready()))
Dm._set_data(data)
-- 2. оценка интереса
local o, U, why, tt = ev("WEAK", "nonaggression"); OK("weak+threatened accepts non-aggression", o == "accept", string.format("%s U=%.2f %s", o, U, why))
o, U, why = ev("WEAK", "tribute"); OK("weak pays tribute to stronger player", o == "accept", string.format("%s U=%.2f %s", o, U, why))
o, U, why = ev("BIG", "nonaggression"); OK("big hostile expansionist refuses peace", o == "refuse", string.format("%s U=%.2f %s", o, U, why))
o, U, why = ev("BIG", "submission"); OK("big power never submits", o == "refuse", string.format("%s U=%.2f %s", o, U, why))
o, U, why = ev("BIG", "tribute"); OK("big power refuses tribute", o == "refuse", string.format("%s U=%.2f %s", o, U, why))
o, U, why, tt = ev("FRIEND", "alliance"); OK("friend with common enemy → military alliance", o == "accept" and tt == "military", string.format("%s %s U=%.2f %s", o, tostring(tt), U, why))
o, U, why = ev("ENEMY", "alliance"); OK("enemy refuses alliance", o == "refuse", string.format("%s U=%.2f %s", o, U, why))
o, U, why = ev("POOR", "trade", { money = 30000 }); OK("poor hungry faction + rich player → trade", o == "accept", string.format("%s U=%.2f %s", o, U, why))
local o2, U2 = ev("RICH", "trade", { money = 0 }); OK("rich faith faction, poor player → no free trade", o2 ~= "accept", string.format("%s U=%.2f", o2, U2))
OK("counter is a priced middle ground", (function() for _, f in ipairs({ "RICH", "POOR", "FRIEND", "WEAK" }) do for _, k in ipairs({ "trade", "nonaggression", "fealty" }) do
  local x = ev(f, k, { money = 0 }); if x == "counter_s" or x == "counter_l" then return true end end end end)())
local _, Ua = ev("WEAK", "nonaggression"); local _, Ub = ev("WEAK", "nonaggression", { asked = 2 }); OK("pestering lowers interest", Ub < Ua, string.format("%.2f → %.2f", Ua, Ub))
o, U, why = ev("BIG", "fealty"); OK("big expansionist takes the player as vassal (or prices it)", o ~= "refuse" or U > 0, string.format("%s U=%.2f %s", o, U, why))
S.treaties[99] = { id = 99, type = "trade", a = "RICH", b = "P", active = true, since = 90, term = 400 }
o, U, why = ev("RICH", "trade"); OK("existing treaty → confirmed", o == "accept" and why == "already bound", why); S.treaties[99] = nil
o = ev("GHOST", "trade"); OK("unknown faction → refuse", o == "refuse")
-- 3. рантайм: появились персонажи → ленивый старт
local pc = CH("pc1", "P", 0, 0, true); PCS = { pc }
local npc = CH("envoy1", "WEAK", 100, 0, false); LOADED = { npc, pc }
for i = 1, 10 do CLOCK = CLOCK + 1; FIRE("GameWorld::charsUpdate") end
OK("lazy start after chars appear", Dm.ready())
OK("seal given once", (pc.items[data.items.seal] or 0) == 1)
local DLG = { me = npc, getSpeaker = function(_, who, line, w) return pc end }
local function LINE(sid) return { getStringID = function() return sid end } end
Dm.on_line(DLG, LINE(line_of("open")))
Dm.on_line(DLG, LINE(line_of("propose", "nonaggression")))
OK("propose → accept token", (pc.items[data.items.accept] or 0) == 1)
Dm.on_line(DLG, LINE(line_of("commit", "nonaggression", "accept")))
OK("commit removes token, queues", (pc.items[data.items.accept] or 0) == 0 and #Dm.queue() == 1)
CLOCK = CLOCK + 2; FIRE("GameWorld::charsUpdate")
local t; for _, x in pairs(S.treaties) do if x.type == "nonaggression" and x.a == "WEAK" and x.b == "P" then t = x end end
OK("treaty signed via conductor API", t ~= nil and #S.events > 0 and S.rel.WEAK.P == 10, S.rel.WEAK.P)
-- противник: отказ + требование дани → отношения падают
local big = CH("envoy2", "BIG", 50, 0, false); LOADED = { npc, big, pc }
local DLG2 = { me = big, getSpeaker = function() return pc end }
Dm.on_line(DLG2, LINE(line_of("open"))); Dm.on_line(DLG2, LINE(line_of("propose", "tribute")))
OK("big → refuse token", (pc.items[data.items.refuse] or 0) == 1)
Dm.on_line(DLG2, LINE(line_of("commit", "tribute", "refuse"))); CLOCK = CLOCK + 2; FIRE("GameWorld::charsUpdate")
OK("refused demand hurts relations", S.rel.BIG.P == -80, S.rel.BIG.P)
-- вассалитет: игрок присягает BIG (если не принято — подписываем напрямую через commit paid)
Dm.on_line(DLG2, LINE(line_of("open"))); Dm.on_line(DLG2, LINE(line_of("commit", "fealty", "paid")))
CLOCK = CLOCK + 2; FIRE("GameWorld::charsUpdate")
local vt; for _, x in pairs(S.treaties) do if x.type == "vassal" and x.a == "BIG" and x.b == "P" then vt = x end end
OK("paid counter → player becomes vassal", vt ~= nil)
S.last_day = 100 + 31; Dm.on_line(DLG2, LINE(line_of("open")))
OK("tribute due → liege_due token", (pc.items[data.items.liege_due] or 0) == 1 and (pc.items[data.items.has_pact] or 0) == 1)
S.last_day = 100 + 31 + 25; CLOCK = CLOCK + 6; FIRE("GameWorld::charsUpdate")
OK("missed tribute → relations/trust down", (S.F.BIG.trust.P or 0) <= -20, S.F.BIG.trust.P)
-- письмо (запасной канал): мост не сработал, у игрока письмо «торговля»
pc.items[data.letters.trade] = 1; MONEY = 30000
local poor = CH("x", "POOR", 300, 0, false); LOADED = { poor, pc }
CLOCK = CLOCK + 4; FIRE("GameWorld::charsUpdate")
local tt2; for _, x in pairs(S.treaties) do if x.type == "trade" and x.a == "POOR" then tt2 = x end end
OK("letter → decision → trade treaty + message", (pc.items[data.letters.trade] or 0) == 0 and tt2 ~= nil and #MSGS > 0, MSGS[#MSGS])
-- измена: игрок напал на партнёра (событие дирижёра player_raid)
S.events[#S.events + 1] = { id = S.next_id, type = "player_raid", a = "P", b = "POOR" }; S.next_id = S.next_id + 1
CLOCK = CLOCK + 6; FIRE("GameWorld::charsUpdate")
OK("player raid on partner → pact broken as betrayal", tt2 and not tt2.active, tt2 and tostring(tt2.active))
-- ошибка API → отключается только диалог, причина в debug.log, такт продолжает работу
FAIL_INV = true
Dm.on_line(DLG, LINE(line_of("open")))
OK("API error disables only 'dialogue'", Dm.disabled().dialogue == true and not Dm.disabled().apply and not Dm.disabled().tick)
FAIL_INV = false
CLOCK = CLOCK + 6; FIRE("GameWorld::charsUpdate")
OK("tick keeps running after dialogue failure", not Dm.disabled().tick and not Dm.disabled().letters)
local f = io.open("C:/KenshiModMap/logs/debug.log", "r"); local dl = f and f:read("*a") or ""; if f then f:close() end
OK("reason in debug.log", dl:find("dialogue disabled until restart: .-getInventory exploded") ~= nil)
-- вызов дирижёра подменён: kmm_diplo не пишет договор сам, а зовёт player_sign/emit
KMM_Conductor.player_sign = function(fid, ttype, why, ps) SIGNED[#SIGNED + 1] = fid .. ":" .. ttype .. ":" .. tostring(ps); return { id = 500 } end
KMM_Conductor.emit = function(ev) return ev end
Dm.queue()[#Dm.queue() + 1] = { fid = "WEAK", kind = "submission", outcome = "accept" }
CLOCK = CLOCK + 2; FIRE("GameWorld::charsUpdate")
OK("patched conductor: player_sign(vassal, player suzerain)", SIGNED[1] == "WEAK:vassal:true", SIGNED[1])
local st = Dm.stats()
R[#R + 1] = string.format("INFO decisions=%d applied=%d letters=%d tokens=%d", st.decisions, st.applied, st.letters, st.tokens)
return table.concat(R, "\n")
'''

# реальный конфиг дирижёра (стартовый мир rules/conductor.json): распределение ответов по видам — не «всегда да/нет»
import json  # noqa: E402
import re  # noqa: E402
sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\streams")
from diplo import lua_lit  # noqa: E402
cj = json.load(open(r"C:\KenshiModMap\rules\conductor.json", encoding="utf-8"))
RF = {fid: {"alive": not f.get("sleeper"), "strength": f.get("strength") or 0, "strength0": f.get("strength") or 0, "wealth": f.get("wealth") or 0,
            "wealth0": max(1, f.get("wealth") or 1), "ambition": f.get("ambition"), "relic": f.get("relic"), "towns": {t: True for t in f.get("towns") or []},
            "trust": {}, "player": bool(f.get("player"))} for fid, f in cj["factions"].items()}
RREL = {fid: dict(f.get("rel") or {}) for fid, f in cj["factions"].items()}
for a, d in list(RREL.items()):
    for b, v in d.items():
        RREL.setdefault(b, {})[a] = v
RCFG = {"player_faction": cj["player_faction"], "params": {k: cj["params"][k] for k in ("bus", "relic", "treaties")},
        "factions": {fid: {"name": f["name"], "near": f.get("near") or []} for fid, f in cj["factions"].items()}}
NL = chr(10)
REAL = "RS = { last_day = 0, treaties = {}, events = {}, F = " + lua_lit(RF) + ", rel = " + lua_lit(RREL) + " }" + NL + "RCFG = " + lua_lit(RCFG) + NL + r'''
local data = require("kmm_diplo_data")
KMM_Diplo._set_data(data)
local cnt, kinds = {}, { "nonaggression", "trade", "alliance", "fealty", "submission", "tribute" }
for _, k in ipairs(kinds) do cnt[k] = { accept = 0, counter_s = 0, counter_l = 0, refuse = 0 } end
for fid, f in pairs(RS.F) do
  if f.alive and not f.player then
    for _, k in ipairs(kinds) do local o = KMM_Diplo.evaluate(RS, RCFG, data.params, fid, k, { pf = RCFG.player_faction, nchars = 4, money = 2000, day = 0, asked = 0, jitter = 0 }); cnt[k][o] = cnt[k][o] + 1 end
  end
end
local out = {}
for _, k in ipairs(kinds) do local c = cnt[k]; out[#out + 1] = string.format("%s: accept %d, counter %d/%d, refuse %d", k, c.accept, c.counter_s, c.counter_l, c.refuse) end
return table.concat(out, ";")
'''

st = new_state()
try:
    run(st, STUBS, "stubs")
    run(st, read(MAIN), "kmm_diplo.lua")
    out = run(st, TESTS, "tests", ret=True)
    real = run(st, REAL, "real config", ret=True).split(";")
    print("start-of-world answers to a 4-character player band (all factions):")
    for ln in real:
        print("  ", ln)
    nums = {ln.split(":")[0]: [int(x) for x in re.findall(r"\d+", ln)] for ln in real}
    vary = 0 < nums["nonaggression"][0] < sum(nums["nonaggression"]) and nums["submission"][0] < sum(nums["submission"]) // 3
    out += NL + ("PASS" if vary else "FAIL") + " real config: answers vary by faction (not a fixed script)"
except RuntimeError as e:
    out = "FAIL runtime: " + str(e)
for ln in out.splitlines():
    (FAILS if ln.startswith("FAIL") else PASSES).append(ln)
for p in PASSES:
    print("PASS" if not p.startswith(("PASS", "INFO")) else "", p)
for f_ in FAILS:
    print("FAIL", f_)
print(f"\n{len([p for p in PASSES if not p.startswith('INFO')])} passed, {len(FAILS)} failed; logs in {TMP}")
sys.exit(1 if FAILS else 0)
