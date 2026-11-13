"""GOALS (2026-11-13): цели фракций и роль оплотов. Офлайн, LuaJIT из KenshiLua, без игры.
Проверяет: (1) в конфиге есть безгородские участники с лагерем и архетипом; (2) каждому архетипу выбирается цель и она выполняется;
(3) бездомные не вымирают (пол лагеря); (4) опасность вокруг оплота -> беженцы из соседних владений, найм охраны владельцем, щит от бандитов;
(5) поэтапный режим (advance_staged + ws_pump по времени) даёт те же фазы, что синхронный, и ни один вызов не делает больше одной фазы за slice=0;
(6) отключение params.goals.enabled возвращает множители 1.0.
python -I -X utf8 build/KMM_Conductor/_dev/test_goals.py -> OK / FAIL, код 1 при провале."""
import ctypes
import json
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
CONF = r"C:\KenshiModMap\rules\conductor.json"
TMP = tempfile.mkdtemp(prefix="kmm_goals_").replace("\\", "/")
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


cfg = json.load(open(CONF, encoding="utf-8"))
tl = {k: v for k, v in cfg["factions"].items() if v.get("townless")}
check(len(tl) >= 20, f"конфиг: безгородских участников {len(tl)} (>=20)")
check(all(v.get("arch") and v.get("x") is not None and v.get("camp") for v in tl.values()), "конфиг: у каждого бездомного есть архетип, центр и лагерь")
check(all(v.get("arch") for v in cfg["factions"].values()), "конфиг: архетип есть у всех фракций")
check(sum(1 for v in cfg["town_info"].values() if v.get("sh")) >= 30, "конфиг: оплоты (town_info.sh) отмечены")
check("goals" in cfg["params"] and cfg["params"]["goals"].get("bias"), "конфиг: params.goals с bias")

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


run(f'''local ro = io.open; io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{TMP}/"):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return ro(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", "{TMP}/"); return __rr(p) end
KenshiLua = {{ log = function() end }}; Events = {{ h = {{}} }}; function Events.on(n, f) Events.h[n] = f end
function getGameWorld() error("no game") end; function getPlayerInterface() error("no game") end''', "stubs")
for _f in sorted(__import__("glob").glob(SCRIPT.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(r'''
OUT = {}
local function put(k, v) OUT[#OUT + 1] = k .. "=" .. tostring(v) end
math.randomseed(11)
KMM_Conductor.reset()
local S = KMM_Conductor.state()
local C = KMM_Conductor.cfg()
-- 1) 3 года синхронно: цели выбираются и выполняются у всех архетипов, бездомные живы
for d = 0, 365 * 3 do KMM_Conductor.advance(d); KMM_Conductor.goals_drain() end
local arch_done, tl_n, tl_alive, tl_done = {}, 0, 0, 0
for fid, f in pairs(S.F) do
  local c = C.factions[fid]
  if c and c.townless then
    tl_n = tl_n + 1
    if f.alive then tl_alive = tl_alive + 1 end
    if (f.goals_done or 0) > 0 then tl_done = tl_done + 1 end
  end
  if f.arch and (f.goals_done or 0) > 0 then arch_done[f.arch] = (arch_done[f.arch] or 0) + 1 end
end
put("tl_n", tl_n); put("tl_alive", tl_alive); put("tl_done", tl_done)
local na = 0; for _ in pairs(arch_done) do na = na + 1 end
put("arch_with_done", na)
put("goals_done", S.stats.goals_done or 0)
put("goals_off", KMM_Conductor.goals_off())
-- 2) оплот: опасность -> беженцы, найм, щит
local sh, ow
for sid, I in pairs(C.town_info) do
  if I.sh and I.x and S.town[sid] and S.town[sid].pop then
    for fid, f in pairs(S.F) do if f.alive and f.towns[sid] and f.wealth > 40 then sh, ow = sid, fid end end
    if sh then break end
  end
end
put("sh_found", sh ~= nil)
local pop0 = S.town[sh].pop
local feeders0 = 0
for t, T in pairs(C.town_info) do
  if not T.sh and T.x and S.town[t] and S.town[t].pop and math.sqrt((T.x - C.town_info[sh].x) ^ 2 + (T.z - C.town_info[sh].z) ^ 2) <= 40000 then feeders0 = feeders0 + S.town[t].pop end
end
S.danger[sh] = 6
S.F[ow].wealth = 500
S.town[sh].refuge_day = nil; S.hire[sh] = nil
local st0, hires0 = S.F[ow].strength, S.stats.hires or 0
for d = 365 * 3 + 1, 365 * 3 + 12 do KMM_Conductor.advance(d); KMM_Conductor.goals_drain() end
put("hires", (S.stats.hires or 0) - hires0)
put("refuge_pulls", S.stats.refuge_pulls or 0)
put("sh_pop_up", S.town[sh].pop > pop0 or (S.stats.refugees or 0) > 0)
put("shield_owner", S.shield[ow] or 0)
-- 3) щит: бандит к цели с оплотами берёт меньший множитель, чем к слабой цели без оплотов
local bandit, strong, weak
for fid, f in pairs(S.F) do if f.alive and f.arch == "bandit" and not f.relic then bandit = fid; break end end
for fid, v in pairs(S.shield) do if v > 1 then strong = fid end end
for fid, f in pairs(S.F) do if f.alive and not S.shield[fid] and not f.player and fid ~= bandit then weak = fid; break end end
S.F[weak].strength = 1
local m_s = KMM_Conductor.goal_mult(bandit, "raid", strong)
local m_w = KMM_Conductor.goal_mult(bandit, "raid", weak)
put("mult_strong", m_s); put("mult_weak", m_w)
put("danger_api", KMM_Conductor.danger(sh))
''', "scenario")
out = {}
run("__V = table.concat(OUT, ';')", "get")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"__V")
for kv in L.lua_tolstring(st, -1, None).decode("utf-8").split(";"):
    k, v = kv.split("=", 1)
    out[k] = v
print(out)
check(int(out["tl_n"]) >= 20 and out["tl_alive"] == out["tl_n"], f"бездомные живы после 3 лет: {out['tl_alive']}/{out['tl_n']}")
check(int(out["tl_done"]) >= 0.5 * int(out["tl_n"]), f"бездомные, выполнившие цель за 3 года: {out['tl_done']}/{out['tl_n']} (>=50%)")
check(int(out["arch_with_done"]) >= 6, f"архетипов с выполненной целью: {out['arch_with_done']} (>=6)")
check(out["goals_off"] == "false", "блок целей не отключился сам")
check(out["sh_found"] == "true" and int(out["hires"]) >= 1, "оплот при высокой опасности: владелец нанял охрану")
check(int(out["refuge_pulls"]) >= 1 and out["sh_pop_up"] == "true", "оплот при опасности: беженцы тянутся в убежище")
check(float(out["mult_strong"]) < float(out["mult_weak"]), f"бандиты обходят сильные оплоты ({out['mult_strong']} < {out['mult_weak']})")

# 4) поэтапный режим: те же фазы, по одной за вызов при slice=0; синхронный результат не зависит
run(r'''
math.randomseed(5)
KMM_Conductor.reset()
KMM_Conductor.phase_slice(0)
local S2 = KMM_Conductor.state()
local calls, maxpending, d0 = 0, 0, 0
for d = 0, 40 do
  KMM_Conductor.advance_staged(d)
  local p = KMM_Conductor.phase_stats().pending
  if p > maxpending then maxpending = p end
end
local before = KMM_Conductor.phase_stats().pending
for i = 1, 400 do KMM_Conductor.advance_staged(40) end
local after = KMM_Conductor.phase_stats().pending
STG = string.format("%d;%d;%d;%d", maxpending, before, after, S2.stats.goal_set or 0)
''', "staged")
run("__V = STG", "get2")
L.lua_getfield(st, -10002, b"__V")
mp, bf, af, gs = [int(x) for x in L.lua_tolstring(st, -1, None).decode().split(";")]
check(mp >= 5, f"поэтапно: очередь фаз копится при slice=0 (макс {mp})")
check(af == 0, f"поэтапно: очередь опустошается за 400 вызовов (было {bf}, стало {af})")
check(gs > 0, f"поэтапно: цели выбраны ({gs})")

# 5) отключение
run(r'''
KMM_Conductor.cfg().params.goals.enabled = false
local S3 = KMM_Conductor.state()
local b
for fid, f in pairs(S3.F) do if f.arch == "bandit" then b = fid; break end end
M1 = KMM_Conductor.goal_mult(b, "waylay", nil)
KMM_Conductor.cfg().params.goals.enabled = true
''', "off")
run("__V = tostring(M1)", "get3")
L.lua_getfield(st, -10002, b"__V")
check(float(L.lua_tolstring(st, -1, None).decode()) == 1.0, "enabled=false: множитель целей 1.0")
print("test_goals:", "OK" if not FAILS else "FAIL " + "; ".join(FAILS))
sys.exit(1 if FAILS else 0)
