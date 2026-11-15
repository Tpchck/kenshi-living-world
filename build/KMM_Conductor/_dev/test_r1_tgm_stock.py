"""Offline test R1: склад города (KMM_Stock) -> родные цены товара Town.tradeGoodsMults (KMM_Traces TGM.apply).
A) KMM_Stock.price_x / cat_items на рантайме склада (заглушки test_stock.py): дефицит дороже, избыток дешевле, осада дорожит оружие, пределы.
B) KMM_Traces: запись только после «TGM probe OK» и проверки первой записи («TGM write OK/FAIL»), пределы 0.6..1.8, шаг раз в игровой час,
   событие склада — сразу («TGM town ... stock changed»), без двойного счёта (priceMultWhenITrade исходный), фолбэк на общий множитель,
   родной множитель вещи не накапливается («TGM persist»).
python -I -X utf8 build/KMM_Conductor/_dev/test_r1_tgm_stock.py -> OK"""
import ctypes, importlib.util, re, sys, tempfile

FAILS = []

# ---------------------------------------------------------------- A: KMM_Stock API
spec = importlib.util.spec_from_file_location("kmm_test_stock", r"C:\KenshiModMap\build\KMM_Stock\_dev\test_stock.py")
TS = importlib.util.module_from_spec(spec)
spec.loader.exec_module(TS)
lua = TS.Lua(tempfile.mkdtemp(prefix="kmm_r1_stock_").replace("\\", "/"))
try:
    lua.load_runtime()
    lua.run(r'''
      assert(KMM_Stock.price_x("A") == nil and KMM_Stock.cat_items("A", "food") == nil, "API safe before start")
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      TICK(30, 1, 0.01); DRAIN()
      assert(KMM_Stock._rt.ready and CS.stock and CS.stock.towns.A, "stock ready")
      local st = CS.stock
      local p = KMM_Stock.price_x("A")
      assert(p and p.x and type(p.sig) == "string", "price_x shape")
      for c, v in pairs(p.x) do assert(v >= 0.6 and v <= 1.8, "limits " .. c .. "=" .. v) end
      local T = st.towns.A
      T.q.food = 0
      p = KMM_Stock.price_x("A")
      assert(math.abs(p.x.food - 1.6) < 1e-6 and p.sig:find("food" .. "d"), "empty food -> 1.6, deficit bucket: " .. p.x.food .. " " .. p.sig)
      T.q.food = 1e9; KMM_Stock.add("A", "food", 1e9)
      p = KMM_Stock.price_x("A")
      assert(p.x.food < 0.8 and p.sig:find("foodg"), "glut food cheaper: " .. p.x.food .. " " .. p.sig)
      local w0 = p.x.weapons
      T.siege = (st.last_day or 0) + 3
      p = KMM_Stock.price_x("A")
      assert(p.siege and p.sig:find("|S", 1, true) and p.x.weapons > w0 and p.x.weapons <= 1.8, "siege: weapons dearer " .. w0 .. " -> " .. p.x.weapons)
      T.q.weapons = 0
      p = KMM_Stock.price_x("A")
      assert(p.x.weapons == 1.8, "siege + empty armoury capped at 1.8: " .. p.x.weapons)
      local f = KMM_Stock.cat_items("A", "food")
      assert(f and #f > 0 and f[1][2] == 4, "food items with ITEM type")
      local wl = KMM_Stock.cat_items("A", "weapons")
      local seen = {}
      for _, it in ipairs(wl) do assert(not seen[it[1]] and it[2] == 2, "weapons unique, WEAPON type"); seen[it[1]] = true end
      assert(#wl > 0 and #wl <= 40, "weapons capped: " .. #wl)
      assert(KMM_Stock.cat_items("nope", "food") == nil and KMM_Stock.price_x("nope") == nil, "unknown town -> nil")
      assert(count(KMM_Stock.disabled()) == 0, "nothing disabled")
    ''', "stock api")
    print("A ok")
except AssertionError as e:
    FAILS.append("A: " + str(e))
finally:
    lua.close()

# ---------------------------------------------------------------- B: KMM_Traces TGM.apply
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
B = r"C:\KenshiModMap\build\KMM_Conductor\scripts\init"
TMP = tempfile.mkdtemp(prefix="kmm_r1_tgm_").replace("\\", "/")
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code, name="chunk"):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(f"{name}: {msg.decode('utf-8', 'replace') if msg else '?'}")


rt = open(r"C:\KenshiModMap\tools\test\test_runtime.py", encoding="utf-8").read()
run(re.search(r"STUBS = r'''(.*?)'''", rt, re.S).group(1).replace("TMPDIR", TMP), "stubs")
run("math.randomseed(20261115)", "seed")
for _f in sorted(__import__("glob").glob(B + r"\KMM_Conductor*.lua")): run(open(_f, encoding="utf-8").read(), _f.split("\\")[-1])
run(open(B + r"\KMM_Traces.lua", encoding="utf-8").read(), "KMM_Traces.lua")
run(r'''
N, FAILS = 0, {}
function check(c, what) N = N + 1; if not c then FAILS[#FAILS + 1] = what end end
local C = KMM_Conductor
C.reset()
local TP = C.cfg().params.traces
TP.first_hour_traces = 0; TP.arrive_enabled = false; TP.bounty = { enabled = false }; TP.enabled = true; TP.price_enabled = true
C.price_mult = function() return 1.1 end           -- фракция владельца: война/голод
C.price_mult_town = function() return 1.3 end      -- прежний общий множитель (фолбэк)
local function dbg() local f = io.open("TMPDIR/debug.log", "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
local function cnt(s, pat) local n = 0; for _ in s:gmatch(pat) do n = n + 1 end; return n end

-- город: мап цен (как у биндинга — живой, ключ GameData), isTown() -> себя
local function mktown(sid, map)
  local t = { tradeGoodsMults = map or {} }
  function t:isTown() return self end
  function t:getGameData() return { name = "Town" .. sid, stringID = sid } end
  function t:getLocalTradePriceMult(gd) return self.tradeGoodsMults[gd] or 1 end
  return t
end
TOWN = mktown("A")
-- KMM_Stock-заглушка: цены категорий и вещи
SX, SIG = { food = 1.5, metal = 0.8, weapons = 1.0 }, "foodn,metaln,weaponsn"
ITEMS_ = { food = { { "bread", 4 }, { "meat", 4 } }, metal = { { "iron", 4 } }, weapons = { { "sword", 2 } } }
KMM_Stock = { CATS = { "food", "metal", "weapons" },
  town_of = function(ch) return ch.TSID end,
  price_x = function(t) if t ~= "A" then return nil end; local x = {}; for k, v in pairs(SX) do x[k] = v end; return { x = x, sig = SIG } end,
  cat_items = function(t, c) return ITEMS_[c] end,
  stock = function(t) return { owner = "own" } end }
local TGM = KMM_Traces.tgm
local BREAD = { stringID = "bread" }
TGM.GD["bread#4"] = BREAD
TOWN.tradeGoodsMults[BREAD] = 1.2                   -- родная культура города: хлеб x1.2
local function gd(s, ty) return TGM.GD[s .. "#" .. ty] end

PCS = { MKCH("Nameless", "player", 0, 0, { player = true, platoon = "player_squad" }) }
local tr = MKCH("trader", "own", 200, 100, { platoon = "traders1" })
tr.TSID = "A"; tr.getCurrentTownLocation = function() return TOWN end
CHARS = { PCS[1], tr }
local PL = PLATOONS["traders1"]
DAYV = 500
local function pass(dh) DAYV = DAYV + (dh or 0) / 24; CLOCK = CLOCK + 25; FIRE("GameWorld::charsUpdate", {}) end

-- 1) первый проход: проба OK -> проверка записи OK -> город записан сразу (первый заход), торговцу — исходный множитель
pass(0)
local d = dbg()
check(d:find("TGM probe OK: src=char_here town TownA") ~= nil, "probe OK marker: " .. d)
check(d:find("TGM write OK: town TownA item bread set 1.980 read 1.98") ~= nil, "write OK marker (1.2 x 1.5 x 1.1): " .. d)
check(d:find("TGM town TownA %(A%) first: food=1%.65 metal=0%.88 weapons=1%.10 fac=1%.10 writes=4") ~= nil, "first town marker: " .. d)
check(math.abs(TOWN.tradeGoodsMults[BREAD] - 1.98) < 1e-6, "bread = native 1.2 x 1.65")
check(math.abs(TOWN.tradeGoodsMults[gd("meat", 4)] - 1.65) < 1e-6 and math.abs(TOWN.tradeGoodsMults[gd("iron", 4)] - 0.88) < 1e-6, "meat/iron")
check(math.abs(PL.priceMultWhenITrade - 1.0) < 1e-6, "no double count: trader keeps original mult, got " .. PL.priceMultWhenITrade)
local S = C.state()
check(S.tgm and S.tgm.o.A and S.tgm.o.A.bread == 1.2 and S.tgm.o.A.meat == nil and S.tgm.w.A == true, "native mults remembered (only != 1)")

-- 2) пределы: еда x1.7 x фракция 1.1 = 1.87 -> 1.8; но без смены корзины и до часа — не трогаем
SX.food = 1.7
pass(0.5)
check(math.abs(TOWN.tradeGoodsMults[gd("meat", 4)] - 1.65) < 1e-6, "within an hour, same bucket: no rewrite")
pass(0.6)   -- > 1 игрового часа: шаг 0.5 к цели 1.8
check(math.abs(TOWN.tradeGoodsMults[gd("meat", 4)] - 1.725) < 1e-6, "hourly smoothing step: " .. TOWN.tradeGoodsMults[gd("meat", 4)])
pass(1.1); pass(1.1); pass(1.1)
check(math.abs(TOWN.tradeGoodsMults[gd("meat", 4)] - 1.8) < 1e-6 and math.abs(TOWN.tradeGoodsMults[BREAD] - 2.16) < 1e-6, "capped at 1.8 (bread 1.2 x 1.8)")

-- 3) событие склада (осада: корзина меняется) — сразу к цели, маркер
SX.weapons = 1.6; SIG = "foodn,metaln,weaponsn|S"
pass(0.1)
check(math.abs(TOWN.tradeGoodsMults[gd("sword", 2)] - 1.76) < 1e-6, "siege: sword jumps to 1.6 x 1.1 at once: " .. tostring(TOWN.tradeGoodsMults[gd("sword", 2)]))
check(dbg():find("TGM town TownA %(A%) stock changed: .*weapons=1%.76") ~= nil, "stock changed marker")
check(math.abs(PL.priceMultWhenITrade - 1.0) < 1e-6, "still no double count")

-- 4) новая сессия, движок сохранил наши цены: родной множитель берётся из S.tgm, хлеб не копится; маркер TGM persist kept
TGM.T, TGM.S = {}, nil
pass(0)
check(math.abs(TOWN.tradeGoodsMults[BREAD] - 2.16) < 1e-6, "bread stays 1.2 x 1.8 (no compounding): " .. TOWN.tradeGoodsMults[BREAD])
check(cnt(dbg(), "TGM persist: town TownA engine kept our prices") == 1, "persist marker (kept): " .. dbg())

-- 5) фолбэк: P.tgm_write = false -> общий множитель города
TP.tgm_write = false
pass(0)
check(math.abs(PL.priceMultWhenITrade - 1.3) < 1e-6, "tgm_write=false -> priceMultWhenITrade x1.3, got " .. PL.priceMultWhenITrade)
TP.tgm_write = nil
pass(0)
check(math.abs(PL.priceMultWhenITrade - 1.0) < 1e-6, "back on: original mult")

-- 6) запись не держится (мап-копия без записи) -> TGM write FAIL, фолбэк, город не трогаем больше
local ro = setmetatable({}, { __newindex = function() end })
TOWN.tradeGoodsMults = ro
TGM.T, TGM.S, TGM.wok = {}, nil, nil
pass(0)
check(dbg():find("TGM write FAIL: town TownA item bread") ~= nil and TGM.wok == false, "write FAIL marker: " .. dbg())
check(math.abs(PL.priceMultWhenITrade - 1.3) < 1e-6, "write fail -> fallback x1.3, got " .. PL.priceMultWhenITrade)
check(TGM.set(TOWN, BREAD, 1.0) == false, "no writes after FAIL")

-- 7) проба не прошла -> записи нет вовсе, фолбэк
TGM.wok, TGM.ok = nil, false
TOWN.tradeGoodsMults = {}
pass(0)
check(next(TOWN.tradeGoodsMults) == nil and math.abs(PL.priceMultWhenITrade - 1.3) < 1e-6, "probe not OK: no writes, fallback")
-- 8) торговец вне города склада -> фолбэк
TGM.ok = true; tr.TSID = nil
pass(0)
check(math.abs(PL.priceMultWhenITrade - 1.1) < 1e-6, "no town: faction mult x1.1, got " .. PL.priceMultWhenITrade)
check(next(KMM_Traces.disabled()) == nil, "traces: nothing disabled")
RESULT = #FAILS == 0 and ("OK " .. N) or ("FAIL: " .. table.concat(FAILS, "; "))
'''.replace("TMPDIR", TMP), "test")
L.lua_getfield.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_char_p]
L.lua_getfield(st, -10002, b"RESULT")
r = L.lua_tolstring(st, -1, None).decode()
if not r.startswith("OK"):
    FAILS.append("B: " + r)
print("B", r)
print("OK" if not FAILS else "FAIL\n" + "\n".join(FAILS))
sys.exit(0 if not FAILS else 1)
