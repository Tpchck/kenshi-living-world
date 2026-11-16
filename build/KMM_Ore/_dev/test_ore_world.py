"""Офлайн-тест ORE3 в модели дирижёра (KMM_Conductor_World.lua: ore_regen, ore_claim, PLAYER_MINED) на LuaJIT KenshiLua.
cd build/KMM_Ore/_dev && python -I -X utf8 ../../../tools/test/log_sandbox.py test_ore_world.py   → «OK n checks», код 1 при провале.
Без игры. Не зависит от порядка обхода таблиц: жилы выбираются по имени, проверяются суммы и конкретные записи."""
import ctypes
import glob
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
TMP = tempfile.mkdtemp(prefix="kmm_oreworld_").replace("\\", "/")

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        L.lua_settop(st, 0)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


run(f'''
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return real_open(p, m) end
KenshiLua = {{ log = function(s) end }}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f end
function getGameWorld() error("no game") end
function getPlayerInterface() error("no game") end
''', "stubs")
for _f in sorted(glob.glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))):
    run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
N, FAILS = 0, {}
local function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C, KC = KMM_Conductor, KMM_C_INT
math.randomseed(5)
C.reset()
local S = C.state()
local CFG = C.cfg()
local pf = CFG.player_faction
check(type(KC.ore_regen) == "function" and type(KC.ore_claim) == "function", "ORE3 functions present")
-- владение: первая по имени жила, у которой есть живой владелец-не игрок и координаты
local names = {}
for t in pairs(S.ore) do names[#names + 1] = t end
table.sort(names)
local vt, owner
for _, t in ipairs(names) do
  local I = CFG.town_info[t]
  local o = KC.owner_of(t)
  if I and I.x and o and o ~= pf then vt, owner = t, o; break end
end
check(vt ~= nil, "found owned vein")
local I = CFG.town_info[vt]
local n = S.ore[vt]
KC.DAY = 100

-- 1) восстановление: нетронутая жила растёт на rg*R0*tick/365, черпанная и копаемая игроком — нет, потолок R0
local O = { vein_regen_per_year = 0.365, regen_told_share = 0.25 }
local td = KC.P.tick_days or 5
n.R, n.told, n.pm_day = 0.2 * n.R0, true, nil
local other
for _, t in ipairs(names) do if t ~= vt then other = t; break end end
local m = S.ore[other]
m.R = 0.5 * m.R0
KC.ore_regen({ [other] = true }, O)
check(math.abs(n.R - (0.2 + 0.365 * td / 365) * n.R0) < 1e-6, "idle vein regenerates")
check(math.abs(m.R - 0.5 * m.R0) < 1e-9, "drawn vein does not regenerate")
check(n.told == true, "told kept below regen_told_share")
n.R = 0.3 * n.R0; KC.ore_regen({}, O)
check(n.told == nil, "recovered vein can be told exhausted again")
n.R = n.R0 - 1e-6; KC.ore_regen({}, O)
check(n.R <= n.R0 + 1e-9, "capped at R0")
n.R, n.pm_day = 0.5 * n.R0, KC.DAY - 1
KC.ore_regen({}, O)
check(math.abs(n.R - 0.5 * n.R0) < 1e-9, "vein worked by player does not regenerate")
KC.ore_regen({}, { vein_regen_per_year = 0 })
check(math.abs(n.R - 0.5 * n.R0) < 1e-9, "regen 0 = off")

-- 2) добыча игрока: ближайшая жила, учёт pm, претензия владельца после share*R0, кулдаун, пол отношений, договор
KC.P.ore.claim = { enabled = true, share = 0.03, cooldown_days = 20, rel = 1.5, rel_floor = -30 }
KC.set_rel(owner, pf, 10)
for _, tr in pairs(S.treaties) do if (tr.a == owner and tr.b == pf) or (tr.b == owner and tr.a == pf) then tr.active = false end end
local ev0 = #S.events
local R1, need = n.R, 0.03 * n.R0
C.player_mined(need * 0.5, I.x + 1, I.z + 1)
check(math.abs(n.R - (R1 - need * 0.5)) < 1e-6, "player drains nearest vein")
check(math.abs((n.pm or 0) - need * 0.5) < 1e-6 and n.pm_day == KC.DAY, "player take recorded on vein")
check(KC.rel(owner, pf) == 10, "no claim below threshold")
C.player_mined(need * 0.6, I.x + 1, I.z + 1)
local r1 = KC.rel(owner, pf)
check(r1 < 10 and r1 >= 10 - 1.5 * 3 - 1, "claim lowers owner relation: " .. tostring(r1))
local claimed = false
for i = ev0 + 1, #S.events do if S.events[i].type == "ore_claim" and S.events[i].a == owner and S.events[i].town_sid == vt then claimed = true end end
check(claimed, "ore_claim event emitted")
C.player_mined(need * 2, I.x + 1, I.z + 1)
check(KC.rel(owner, pf) == r1, "cooldown holds")
KC.DAY = KC.DAY + 25
KC.set_rel(owner, pf, -29)
C.player_mined(need * 2, I.x + 1, I.z + 1)
check(KC.rel(owner, pf) >= -30, "rel_floor respected: " .. tostring(KC.rel(owner, pf)))
KC.DAY = KC.DAY + 25
KC.set_rel(owner, pf, 0)
S.treaties[#S.treaties + 1] = { a = owner, b = pf, type = "trade", active = true, day = KC.DAY }
local c0 = S.stats.ore_claim_pact or 0
C.player_mined(need * 2, I.x + 1, I.z + 1)
check(KC.rel(owner, pf) == 0 and (S.stats.ore_claim_pact or 0) == c0 + 1, "treaty = licence, no claim")
KC.P.ore.claim.enabled = false
KC.DAY = KC.DAY + 25
S.treaties[#S.treaties] = nil
C.player_mined(need * 2, I.x + 1, I.z + 1)
check(KC.rel(owner, pf) == 0, "claim disabled")
C.player_mined(0, I.x, I.z); C.player_mined(-5, I.x, I.z); C.player_mined(1, nil, nil)
check(true, "bad input ignored without error")

-- 3) сериализация: новые поля жилы переживают сейв (только числа)
local s2 = KC.deserialize(KC.serialize(S))
check(s2 and s2.ore[vt].pm and s2.ore[vt].claim_day, "ORE3 vein fields survive serialize")
-- 4) метрики дирижёра на месте после тика
local d0 = math.floor(KC.DAY); for dd = d0, d0 + td * 3 do C.advance(dd) end
check(type(S.ore_stress) == "number" and type(S.ore_share) == "number", "ore_stress/ore_share computed")
RESULT = (#FAILS == 0) and ("OK " .. N .. " checks") or ("FAIL " .. #FAILS .. "/" .. N .. ": " .. table.concat(FAILS, "; "))
''', "checks")
L.luaL_loadstring(st, b"return RESULT")
L.lua_pcall(st, 0, 1, 0)
res = L.lua_tolstring(st, -1, None).decode("utf-8", "replace")
print(res)
sys.exit(0 if res.startswith("OK") else 1)
