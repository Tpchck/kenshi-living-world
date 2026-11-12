"""Офлайн-калибровка KMM_Stock: дирижёр + модель складов на LuaJIT из KenshiLua (lua51.dll), N лет × сиды. Без игры, < 2 мин.
python -I -X utf8 build/KMM_Stock/_dev/sim_stock.py [years=15] [seed ...]
Критерии: нет снежного кома (доля склада города/фракции ограничена), доли дней в дефиците/переполнении по категориям
в разумных пределах, металл падает в рудный кризис. Пути C:/KenshiModMap/logs/ → временная папка."""
import ctypes
import json
import os
import sys
import tempfile

YEARS = int(sys.argv[1]) if len(sys.argv) > 1 else 15
SEEDS = [int(x) for x in sys.argv[2:]] or [2026, 7, 4242]
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
COND = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init\KMM_Conductor.lua"
MODEL = "C:/KenshiModMap/build/KMM_Stock/scripts/kmm_stock_model.lua"

LIM = {  # доля город-дней (города) — допустимые пределы
    "def": {"food": 0.15, "metal": 0.30, "weapons": 0.30, "armor": 0.30, "med": 0.25, "drugs": 0.35, "lux": 0.30, "scrap": 1.0},
    "over": {"food": 0.15, "metal": 0.15, "weapons": 0.10, "armor": 0.10, "med": 0.10, "drugs": 0.3, "lux": 0.10, "scrap": 0.5},
}


def one(seed, all_towns):
    tmp = tempfile.mkdtemp(prefix="kmm_stock_").replace("\\", "/")
    L = ctypes.CDLL(DLL)
    L.luaL_newstate.restype = ctypes.c_void_p
    for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                   ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]), ("lua_close", [ctypes.c_void_p])]:
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
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", "{tmp}/"); return real_open(p, m) end
KenshiLua = {{ log = function(s) end }}
Events = {{ h = {{}} }}
function Events.on(n, f) Events.h[n] = f; return n end
function getGameWorld() error("no game") end
function getPlayerInterface() error("no game") end
''', "stubs")
    for _f in sorted(__import__("glob").glob(COND.replace("KMM_Conductor.lua", "KMM_Conductor*.lua"))): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
    ALL = 'true' if all_towns else 'false'
    run(f'''
local M = dofile("{MODEL}")
math.randomseed({seed})
KMM_Conductor.reset()
local S = KMM_Conductor.state()
local CFG = KMM_Conductor.cfg()
S.stock = S.stock or {{}}
M.init(S.stock, S, CFG)
local EV = {{}}
local function emit(ev) EV[ev.type] = (EV[ev.type] or 0) + 1; return KMM_Conductor.emit(ev) end
local Y = {{}}
local cats = M.CATS
local acc
local function reset_acc() acc = {{ n = 0, sum = {{}}, def = {{}}, over = {{}}, fmax = 0, tmax = 0 }} end
reset_acc()
local crisis_day
MET = {{}}
ALLTOWNS = {ALL}
for d = 0, 365 * {YEARS} do
  KMM_Conductor.advance(d)
  M.day(S.stock, S, d, emit)
  if S.ore_crisis and not crisis_day then crisis_day = d end
  -- выборка по дням: средние доли нормы по категориям (города), дефицит/переполнение, ком (максимум по городу/фракции)
  local fsum = {{}}
  local mtot = 0
  for t, s in pairs(S.stock.towns) do
    mtot = mtot + s.q.metal
    if ALLTOWNS or s.city then
      acc.n = acc.n + 1
      local tot = 0
      for _, c in ipairs(cats) do
        local r = s.q[c] / M.T(S.stock, s, c)
        acc.sum[c] = (acc.sum[c] or 0) + r
        if r < 0.2 then acc.def[c] = (acc.def[c] or 0) + 1 end
        if r > 2.5 then acc.over[c] = (acc.over[c] or 0) + 1 end
        tot = tot + r
      end
      if tot / #cats > acc.tmax then acc.tmax = tot / #cats end
      if s.owner then fsum[s.owner] = (fsum[s.owner] or 0) + tot / #cats * M.T(S.stock, s) end
    end
  end
  if d % 30 == 0 then MET[#MET + 1] = {{ d, mtot }} end
  for _, v in pairs(fsum) do if v > acc.fmax then acc.fmax = v end end
  if d > 0 and d % 365 == 0 then
    local y = {{ year = d / 365, mean = {{}}, def = {{}}, over = {{}}, town_max = acc.tmax, fac_max = acc.fmax,
                ore_share = S.ore_share or 1, metal_price = S.metal_price or 1, crisis = S.ore_crisis and S.ore_crisis.phase or "none" }}
    for _, c in ipairs(cats) do
      y.mean[c] = (acc.sum[c] or 0) / acc.n; y.def[c] = (acc.def[c] or 0) / acc.n; y.over[c] = (acc.over[c] or 0) / acc.n
    end
    Y[#Y + 1] = y
    reset_acc()
  end
end
OUT = {{ years = Y, ev = EV, crisis_day = crisis_day, metrics = S.stock.metrics, metal = MET }}
local q = function(s) return '"' .. tostring(s):gsub('\\\\', '\\\\\\\\'):gsub('"', '\\\\"') .. '"' end
local function J(v)
  local t = type(v)
  if t == "table" then
    local parts = {{}}
    if #v > 0 then for _, x in ipairs(v) do parts[#parts + 1] = J(x) end; return "[" .. table.concat(parts, ",") .. "]" end
    for k, x in pairs(v) do if type(x) ~= "function" then parts[#parts + 1] = q(k) .. ":" .. J(x) end end
    return "{{" .. table.concat(parts, ",") .. "}}"
  elseif t == "number" then if v ~= v or v == math.huge or v == -math.huge then return "0" end; return string.format("%.4g", v)
  elseif t == "boolean" then return tostring(v) elseif t == "nil" then return "null" end
  return q(v)
end
local fh = io.open("C:/KenshiModMap/logs/stock_out.json", "w"); fh:write(J(OUT)); fh:close()
''', "sim")
    L.lua_close(st)
    return json.load(open(os.path.join(tmp, "stock_out.json"), encoding="utf-8"))


def main():
    cats = ["food", "metal", "weapons", "armor", "med", "drugs", "lux", "scrap"]
    ok_all = True
    for seed in SEEDS:
      for all_towns in (False, True):
        print("== " + ("ALL towns" if all_towns else "cities"))
        r = one(seed, all_towns)
        Y = r["years"]
        tot_def = {c: sum(y["def"][c] for y in Y) / len(Y) for c in cats}
        tot_over = {c: sum(y["over"][c] for y in Y) / len(Y) for c in cats}
        cd = r.get("crisis_day")
        cy = int(cd // 365) + 1 if cd else None
        m_pre = sum(y["mean"]["metal"] for y in Y[:3]) / 3
        m_post = sum(y["mean"]["metal"] for y in Y if cy and y["year"] >= cy + 1) / max(1, sum(1 for y in Y if cy and y["year"] >= cy + 1))
        w_pre = sum(y["mean"]["weapons"] for y in Y[:3]) / 3
        w_post = sum(y["mean"]["weapons"] for y in Y if cy and y["year"] >= cy + 1) / max(1, sum(1 for y in Y if cy and y["year"] >= cy + 1))
        snow = max(y["town_max"] for y in Y)
        fac_growth = Y[-1]["fac_max"] / max(1, Y[0]["fac_max"])
        crit = {
            "def_ok": all(tot_def[c] <= LIM["def"][c] for c in cats),
            "over_ok": all(tot_over[c] <= LIM["over"][c] for c in cats),
            "no_snowball_town": snow <= 2.6,
            "no_snowball_faction": fac_growth <= 2.0,
            "metal_reacts": bool(cy) and m_post < 0.8 * m_pre,
            "no_chronic_last5": all(max(y["def"][c] for y in Y[-5:]) < 0.5 for c in cats if c != "scrap"),
        }
        ok_all = ok_all and all(crit.values())
        print(f"seed {seed}: crisis year {cy}  metal {m_pre:.2f}->{m_post:.2f}  weapons {w_pre:.2f}->{w_post:.2f}  town_max {snow:.2f}  fac_growth {fac_growth:.2f}")
        print("  def  " + " ".join(f"{c}={tot_def[c]:.3f}" for c in cats))
        print("  def max last5 " + " ".join(f"{c}={max(y['def'][c] for y in Y[-5:]):.2f}" for c in cats))
        print("  over " + " ".join(f"{c}={tot_over[c]:.3f}" for c in cats))
        print("  mean y1/5/10/15 " + " | ".join(" ".join(f"{c[:3]}={Y[i]['mean'][c]:.2f}" for c in cats) for i in (0, 4, 9, len(Y) - 1) if i < len(Y)))
        print("  metal by year " + " ".join(f"{y['mean']['metal']:.2f}" for y in Y))
        met = r["metal"]
        if cd:
            pre = [m for d, m in met if cd - 120 <= d < cd]
            post = [m for d, m in met if cd + 60 <= d <= cd + 240]
            late = [m for d, m in met if cd + 700 <= d <= cd + 1100]
            pre_v = sum(pre) / max(1, len(pre))
            print(f"  metal around crisis: pre {pre_v:.0f}  +2..8mo {sum(post) / max(1, len(post)) / pre_v:.2f}  +2..3y {sum(late) / max(1, len(late)) / pre_v:.2f}")
        print("  events", r["ev"], "  crit", crit)
    print("ALL_OK" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
