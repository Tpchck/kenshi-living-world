"""Офлайн-тесты KMM_Stock на LuaJIT из KenshiLua (lua51.dll): синтаксис, модель, рантайм на заглушках API. Без игры, < 10 с.
python -I -X utf8 build/KMM_Stock/_dev/test_stock.py
Пути C:/KenshiModMap/logs/ перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPTS = "C:/KenshiModMap/build/KMM_Stock/scripts"
RUNTIME = SCRIPTS + "/init/kmm_stock.lua"
MODEL = SCRIPTS + "/kmm_stock_model.lua"
ITEMS = SCRIPTS + "/kmm_stock_items.lua"

L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.luaL_loadfile.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
L.lua_close.argtypes = [ctypes.c_void_p]

# синтетический мир дирижёра: 2 фракции, 3 города, ферма; руда; события; договоры
WORLD = r"""
function mkworld()
  local cfg = {
    player_faction = "PF",
    town_info = { A = { kind = "city", type = 2, name = "Alpha", x = 0, z = 0 }, B = { kind = "city", type = 2, name = "Beta", x = 1000, z = 0 },
                  C = { kind = "city", type = 7, name = "Gamma", x = 9000, z = 0 }, H = { kind = "holding", type = 3, name = "Farm", x = 500, z = 0 } },
    factions = { f1 = { name = "One", capital = "A" }, f2 = { name = "Two", capital = "C" }, PF = { name = "Nameless" } },
    roles = { drugs = { "f2" }, drug_ban = {}, technopriests = {} },
  }
  local cs = { F = { f1 = { alive = true, towns = { A = true, B = true, H = true }, wealth = 500, wealth0 = 500, strength = 50, strength0 = 50, stress = 0.6 },
                     f2 = { alive = true, towns = { C = true }, wealth = 600, wealth0 = 600, strength = 60, strength0 = 60, stress = 0.6 },
                     PF = { alive = true, towns = {}, wealth = 0, wealth0 = 1, strength = 0, player = true } },
               ore = { A = { R = 4000, R0 = 4000 }, B = { R = 3000, R0 = 3000 }, C = { R = 5000, R0 = 5000 }, H = { R = 2000, R0 = 2000, mine = true, flow = 40 } },
               treaties = {}, events = {}, next_id = 1, metal_price = 1 }
  return cs, cfg
end
function push(cs, ev) ev.id = cs.next_id; cs.next_id = cs.next_id + 1; cs.events[#cs.events + 1] = ev end
function run_days(M, st, cs, d0, n, emit) for d = d0, d0 + n - 1 do M.day(st, cs, d, emit) end end
function copy(t) if type(t) ~= "table" then return t end; local o = {}; for k, v in pairs(t) do o[k] = copy(v) end; return o end
function anynan(st) for t, s in pairs(st.towns) do for c, v in pairs(s.q) do if v ~= v or v < 0 then return t .. "." .. c end end end end
"""

STUBS = r"""
TMP = "%(tmp)s"
OPEN_LOG, LOGS, REG, EMITTED = {}, {}, {}, {}
API_CALLS, BREAK, CREATED = 0, false, 0
local real_open = io.open
io.open = function(p, m)
  OPEN_LOG[#OPEN_LOG + 1] = tostring(p) .. "|" .. tostring(m)
  p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/")
  return real_open(p, m)
end
function read_tmp(name) local f = real_open(TMP .. "/" .. name, "r"); if not f then return nil end; local s = f:read("*a"); f:close(); return s end
CLOCK, DAY = 100, 10.0
os.clock = function() return CLOCK end
package.path = "%(scripts)s/?.lua;" .. package.path
KenshiLua = { log = function(s) LOGS[#LOGS + 1] = s end }
Events = { h = {}, n = 0 }
function Events.on(name, f) Events.n = Events.n + 1; Events.h[name] = f; REG[#REG + 1] = name; return Events.n end
function Events.off(id) end
lektor = { new = function() local t = {}; function t:clear() for i = #self, 1, -1 do self[i] = nil end end; return t end }
-- инвентарь-заглушка: вместимость cap вещей
function mkinv(cap, items)
  local inv = { cap = cap, items = items or {} }
  function inv:getAllItems() if BREAK then error("getAllItems: binding changed") end; return self.items end
  function inv:hasRoomForItem(gd) local n = 0; for _, it in ipairs(self.items) do n = n + (it.quantity or 1) end; return n < self.cap end
  function inv:addItem(item, q, drop, destroy) if not self:hasRoomForItem(item.gd) then return false end; self.items[#self.items + 1] = item; return true end
  function inv:removeItemAutoDestroy(it, n)
    for i, x in ipairs(self.items) do if x == it then x.quantity = (x.quantity or 1) - n; if x.quantity <= 0 then table.remove(self.items, i) end; return true end end
  end
  function inv:isAContainer() return true end
  function inv:getNumItems() return #self.items end
  return inv
end
function mkitem(sid, q) local gd = { stringID = sid }; return { gd = gd, quantity = q or 1, isEquipped = false, getGameData = function(self) return self.gd end } end
function mktown(sid) return { getGameData = function() return { stringID = sid } end } end
function mkfaction(sid) return { getData = function() return { stringID = sid } end } end
function mkbuilding(name, tsid, fid, shop, inv)
  local b = { name = name, tsid = tsid, fid = fid, shop = shop, inv = inv }
  function b:getHandle() local s, me = self.name, self; return { toString = function() return s end, getBuilding = function() return me end } end
  function b:getTown() return mktown(self.tsid) end
  function b:hasFaction() return self.fid ~= nil end
  function b:getFaction() return mkfaction(self.fid) end
  function b:isAShop() return self.shop end
  function b:getPosition() return { x = 1500, y = 0, z = 0 } end
  function b:getInventory() return self.inv end
  return b
end
function mkchar(name, x, z, opts)
  opts = opts or {}
  local c = { name = name, x = x, z = z, player = opts.player, trader = opts.trader, tsid = opts.tsid, fid = opts.fid, inv = opts.inv or mkinv(20) }
  function c:getHandle() local s = self.name; return { toString = function() return s end } end
  function c:getPosition() return { x = self.x, y = 0, z = self.z } end
  function c:isPlayerCharacter() return self.player end
  function c:isDead() return false end
  function c:isUnique() return false end
  function c:getPlatoon() local tr = self.trader; return { getIsTrader = function() return tr end } end
  function c:getCurrentTownLocation() return self.tsid and mktown(self.tsid) or nil end
  function c:getFaction() return mkfaction(self.fid) end
  function c:getInventory() return self.inv end
  return c
end
BUILDINGS, NPCS, PCS = {}, {}, {}
local ts = { getTotalDays = function() return DAY end }
local factory = { createItem = function(self, gd) CREATED = CREATED + 1; return { gd = gd, quantity = 1, isEquipped = false, getGameData = function(s) return s.gd end } end }
local gw = { getTimeStamp_inGameHours = function() return ts end, theFactory = factory,
  gamedata = { getData = function(self, sid, ty) return { stringID = sid, ty = ty } end } }
function gw:getObjectsWithinSphere(buf, pos, r, ty, max, skip)   -- как в игре: RootObject без методов Building, приведение через handle
  for _, b in ipairs(BUILDINGS) do local bb = b; buf[#buf + 1] = { getHandle = function() return bb:getHandle() end } end
end
function gw:getCharacterUpdateList() local s = {}; for _, c in ipairs(NPCS) do s[c] = true end; for _, c in ipairs(PCS) do s[c] = true end; return s end
function getGameWorld() API_CALLS = API_CALLS + 1; return gw end
local pi = { getAllPlayerCharacters = function() return PCS end }
function getPlayerInterface() API_CALLS = API_CALLS + 1; return pi end
-- дирижёр-заглушка поверх синтетического мира
function install_conductor()
  CS, CFG = mkworld()
  KMM_Conductor = { state = function() return CS end, cfg = function() return CFG end,
    emit = function(ev) assert(type(ev.type) == "string"); EMITTED[#EMITTED + 1] = ev; push(CS, ev); return ev end,
    tier_shift = function(fid) return 0 end }
  _G.KMM_Conductor = KMM_Conductor
end
function TICK(n, dclock, dday)
  for _ = 1, n do
    CLOCK = CLOCK + (dclock or 1); DAY = DAY + (dday or 0.01)
    Events.h["GameWorld::charsUpdate"]({})
  end
end
function DRAIN() local n = 0; while (KMM_Stock._rt.dctx or KMM_Stock._rt.jobs[1]) and n < 300 do n = n + 1; Events.h["GameWorld::charsUpdate"]({}) end; return n end
function count(t) local k = 0; for _ in pairs(t) do k = k + 1 end; return k end
""" + WORLD


class Lua:
    def __init__(self, tmp):
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)
        self.run(STUBS % {"tmp": tmp, "scripts": SCRIPTS}, "stubs")

    def run(self, code, name="chunk"):
        rc = L.luaL_loadstring(self.st, code.encode("utf-8")) or L.lua_pcall(self.st, 0, 0, 0)
        if rc:
            msg = L.lua_tolstring(self.st, -1, None)
            L.lua_settop(self.st, 0)
            raise AssertionError(f"{name}: {msg.decode('utf-8', 'replace') if msg else rc}")

    def load_runtime(self):
        self.run(f'dofile("{RUNTIME}")', "load kmm_stock.lua")

    def close(self):
        L.lua_close(self.st)


def compile_only(path):
    st = L.luaL_newstate()
    rc = L.luaL_loadfile(st, path.encode("utf-8"))
    msg = L.lua_tolstring(st, -1, None) if rc else None
    L.lua_close(st)
    if rc:
        raise AssertionError(f"syntax {path}: {msg.decode('utf-8', 'replace')}")


RESULTS, CASES = [], []


def case(name):
    def deco(fn):
        def wrapped():
            tmp = tempfile.mkdtemp(prefix="kmm_stock_").replace("\\", "/")
            lua = Lua(tmp)
            try:
                fn(lua)
                RESULTS.append((name, True, ""))
            except AssertionError as e:
                RESULTS.append((name, False, str(e)))
            finally:
                lua.close()
        CASES.append(wrapped)
        return wrapped
    return deco


MODEL_PRE = f'M = dofile("{MODEL}"); math.randomseed(5); CS, CFG = mkworld(); ST = {{}}; M.init(ST, CS, CFG); EV = {{}}; EMIT = function(ev) EV[#EV + 1] = ev end\n'


@case("syntax: модель, рантайм, списки вещей компилируются (LuaJIT KenshiLua)")
def t_syntax(lua):
    for p in (MODEL, RUNTIME, ITEMS):
        compile_only(p)


@case("модель: контракт M.init/M.day, 8 категорий, без NaN, уровни в 0..3, ничего «божественного»")
def t_model_basic(lua):
    lua.run(MODEL_PRE + """
      assert(type(M.init) == "function" and type(M.day) == "function" and M.view and M.bounds and M.level and M.take and M.add)
      local want = { food = 1, metal = 1, weapons = 1, armor = 1, med = 1, drugs = 1, lux = 1, scrap = 1 }
      assert(#M.CATS == 8); for _, c in ipairs(M.CATS) do assert(want[c], c) end
      assert(count(ST.towns) == 4, "stores for all towns")
      for _, s in pairs(ST.towns) do for c in pairs(s.q) do assert(want[c], "unknown category " .. c) end end
      run_days(M, ST, CS, 0, 200, EMIT)
      assert(not anynan(ST), "nan " .. tostring((anynan(ST))))
      for t in pairs(ST.towns) do for _, c in ipairs(M.CATS) do local l = M.level(ST, t, c); assert(l >= 0 and l <= 3.0001, t .. c .. l) end end
      for _, ev in ipairs(EV) do assert(ev.type:sub(1, 6) == "stock_", "event prefix " .. ev.type) end
      local d = ST.last_day; M.day(ST, CS, d, EMIT); assert(ST.last_day == d, "same day twice is no-op")
      CS.F.f1.wealth = -300; run_days(M, ST, CS, 200, 30, EMIT); assert(not anynan(ST), "negative wealth -> nan")
    """)


@case("LINK2: видимое изделие (M.made) = +1 на склад и не дублируется мастерской модели в тот же день; приток металла ускоряет ковку")
def t_link2(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 20, EMIT)
      local s = ST.towns.A
      -- 1) модельный день без видимого производства
      s.q.metal = 2 * M.T(ST, s, "metal"); s.q.armor = 0.1; s.q.weapons = 0.1
      local snap = copy(ST); local cs2 = copy(CS)
      local s1 = ST.towns.A
      M.day(ST, CS, 20, EMIT)
      local base = (s1.q.armor - 0.1) + (s1.q.weapons - 0.1)
      assert(base > 0, "модель не ковала")
      -- 2) то же, но видимая цепочка сделала часть: made() даёт +1 и модель вычитает
      local sv = ST.towns.A; local ST2 = snap; local s2 = ST2.towns.A
      local m0 = s2.q.metal
      local got = M.made(ST2, "A", "armor", 0.05)
      assert(math.abs(got - 0.05) < 1e-9 and s2.vis_made.armor, "made -> склад +")
      M.day(ST2, cs2, 20, EMIT)
      local total = (s2.q.armor - 0.1) + (s2.q.weapons - 0.1)
      assert(math.abs(total - base) < 0.01, "двойной счёт: " .. total .. " vs " .. base)
      assert(s2.vis_made == nil, "дневной зачёт не сброшен")
      -- 3) бонус металла: больше запаса -> быстрее
      local function rate(q) local S2, c3 = copy(snap), copy(cs2); local x = S2.towns.A; x.q.metal = q * M.T(S2, x, "metal"); x.q.armor = 0.1; x.q.weapons = 0.1; M.day(S2, c3, 21, EMIT); return x.ws_rate, x.ws end
      assert(rate(2.5) > 1.3 * rate(0.5), "темп мастерской не растёт с металлом: " .. table.concat({rate(2.5)}, "/") .. " vs " .. table.concat({rate(0.5)}, "/"))
    """)


@case("модель: смена владельца (захват) — разграбление, новый хозяин, добыча у столицы захватчика, событие stock_sacked")
def t_capture(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 30, EMIT)
      local before = 0; for _, v in pairs(ST.towns.B.q) do before = before + v end
      local c_lux = ST.towns.C.q.lux
      CS.F.f1.towns.B = nil; CS.F.f2.towns.B = true
      push(CS, { type = "town_captured", a = "f2", b = "f1", town_sid = "B" })
      M.day(ST, CS, 30, EMIT)
      local after = 0; for _, v in pairs(ST.towns.B.q) do after = after + v end
      assert(after < 0.65 * before, string.format("plundered %.0f -> %.0f", before, after))
      assert(ST.towns.B.owner == "f2", "owner")
      assert(ST.towns.C.q.lux > c_lux - 1, "loot carried to captor hub")
      local seen = false; for _, ev in ipairs(EV) do if ev.type == "stock_sacked" and ev.town_sid == "B" then seen = true end end
      assert(seen, "stock_sacked emitted")
      local n = #EV; M.day(ST, CS, 31, EMIT)
      for i = n + 1, #EV do assert(EV[i].type ~= "stock_sacked", "event processed twice") end
    """)


@case("модель: смена владельца без события (бунт/распад) — потери, новый владелец; свободный город живёт")
def t_owner_silent(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 20, EMIT)
      CS.F.f1.towns.B = nil
      M.day(ST, CS, 20, EMIT)
      assert(ST.towns.B.owner == nil, "free town")
      run_days(M, ST, CS, 21, 60, EMIT)
      assert(not anynan(ST) and M.level(ST, "B", "food") > 0, "free town keeps living")
    """)


@case("модель: торговый договор подвозит товар, блокада (осада) закрывает ворота")
def t_trade_blockade(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 10, EMIT)
      ST.towns.A.q.drugs = 250; ST.towns.C.q.drugs = 5   -- обмен идёт и в обратную сторону; проверяем металл
      ST.towns.A.q.metal = 280; ST.towns.C.q.metal = 10
      local S2, C2 = copy(ST), copy(CS)
      CS.treaties[1] = { active = true, type = "trade", a = "f1", b = "f2" }
      run_days(M, ST, CS, 10, 5, EMIT)
      run_days(M, S2, C2, 10, 5, nil)
      assert(ST.towns.C.q.metal > S2.towns.C.q.metal + 5, string.format("trade delivers metal %.1f vs %.1f", ST.towns.C.q.metal, S2.towns.C.q.metal))
      -- блокада: отбитый штурм города C = осада, договор не возит, рынок закрыт
      local S3, C3 = copy(ST), copy(CS)
      push(C3, { type = "attack_repelled", a = "f1", b = "f2", town_sid = "C" })
      S3.towns.C.q.metal = 10; ST.towns.C.q.metal = 10; ST.towns.A.q.metal = 280; S3.towns.A.q.metal = 280
      run_days(M, S3, C3, 15, 3, nil)
      run_days(M, ST, CS, 15, 3, nil)
      assert(S3.towns.C.siege >= 17, "siege set")
      assert(S3.towns.C.q.metal < ST.towns.C.q.metal - 3, string.format("blockade cuts supply %.1f vs %.1f", S3.towns.C.q.metal, ST.towns.C.q.metal))
    """)


@case("модель: война режет караваны (потери в пути), рейд уносит товар")
def t_war_raid(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 10, EMIT)
      CS.F.f1.last_war = 10
      ST.towns.A.q.food = 280; ST.towns.B.q.food = 5
      run_days(M, ST, CS, 10, 3, EMIT)
      assert((ST.metrics.caravan_lost or 0) > 0, "caravan losses in war")
      local lux = ST.towns.A.q.lux
      push(CS, { type = "raid", a = "f2", b = "f1" })
      M.day(ST, CS, 13, EMIT)
      assert(ST.towns.A.q.lux < lux, "raid takes goods from victim hub")
    """)


@case("модель: рудный кризис — металл и затем оружие падают, переплавка частично выручает")
def t_ore_crisis(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 60, EMIT)
      local S2, C2 = copy(ST), copy(CS)
      for _, n in pairs(C2.ore) do n.R = n.R0 * 0.15; n.flow = 0; n.mine = false end
      C2.metal_price = 2.2; C2.ore_crisis = { since = 60, phase = "deficit" }
      for _, f in pairs(C2.F) do f.stress = 1.6 end
      run_days(M, ST, CS, 60, 240, nil)
      run_days(M, S2, C2, 60, 240, nil)
      local m1, m2, w1, w2 = 0, 0, 0, 0
      for _, t in ipairs({ "A", "B", "C" }) do m1 = m1 + ST.towns[t].q.metal; m2 = m2 + S2.towns[t].q.metal; w1 = w1 + ST.towns[t].q.weapons; w2 = w2 + S2.towns[t].q.weapons end
      assert(m2 < 0.7 * m1, string.format("metal falls %.0f vs %.0f", m2, m1))
      assert(w2 < w1, string.format("weapons fall %.0f vs %.0f", w2, w1))
      local ws = M.level(S2, "A", "weapons"); assert(ws > 0.05, "weapons not wiped out: " .. ws)
    """)


@case("модель: потолок склада — ничего не копится бесконечно")
def t_cap(lua):
    lua.run(MODEL_PRE + """
      for _, s in pairs(ST.towns) do for c in pairs(s.q) do s.q[c] = 1e6 end end
      M.day(ST, CS, 0, EMIT)
      for t in pairs(ST.towns) do for _, c in ipairs(M.CATS) do assert(M.level(ST, t, c) <= 3.0001, "cap " .. t .. c) end end
      assert(M.add(ST, "A", "food", 1e9) >= 0 and M.level(ST, "A", "food") <= 3.0001, "add capped")
      assert(M.take(ST, "A", "food", 1e9) > 0 and ST.towns.A.q.food == 0, "take to zero")
      assert(M.take(ST, "nope", "food", 5) == 0 and M.level(ST, "nope", "food") == nil and M.level(ST, "A", "relic") == nil, "unknown -> 0/nil")
    """)


@case("рантайм: загрузка — только charsUpdate (под guard), ни I/O, ни API игры, _G.KMM_Stock опубликован")
def t_load(lua):
    lua.load_runtime()
    lua.run("""
      assert(#REG == 1 and REG[1] == "GameWorld::charsUpdate", "registered: " .. table.concat(REG, ","))
      assert(#OPEN_LOG == 0 and API_CALLS == 0, "no IO/API at load")
      assert(_G.KMM_Stock and KMM_Stock.level and KMM_Stock.take and KMM_Stock.add and KMM_Stock.workshop and KMM_Stock.put_item)
      assert(package.loaded.kmm_stock_model == nil, "model not loaded at start")
      assert(KMM_Stock.level("A", "food") == nil and KMM_Stock.take("A", "food", 1) == 0, "API safe before start")
    """)


@case("рантайм: дирижёра нет / персонажей нет — ничего не происходит")
def t_no_chars(lua):
    lua.load_runtime()
    lua.run("""
      TICK(50, 1, 0.01)                         -- дирижёра нет
      assert(API_CALLS == 0, "no API without conductor")
      install_conductor()
      PCS = {}
      TICK(300, 1, 0.01)
      assert(CS.stock == nil, "no stock created without player chars")
      assert(not KMM_Stock._rt.ready and count(KMM_Stock.disabled()) == 0 and CREATED == 0, "idle")
    """)


@case("рантайм: ленивый старт, раз в день M.day, склад в состоянии дирижёра, догон порциями, события на шину")
def t_happy(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      TICK(5, 1, 0.01)
      assert(CS.stock == nil, "nothing before delay")
      TICK(20, 1, 0.01)
      assert(KMM_Stock._rt.ready and CS.stock and CS.stock.towns.A, "stock inside conductor state")
      DRAIN()
      local d0 = CS.stock.last_day
      DAY = DAY + 10; DRAIN(); TICK(1, 1, 0); DRAIN()
      assert(CS.stock.last_day == d0 + 1, "TRADE: one day per poll, split over frames: " .. CS.stock.last_day - d0)
      for _ = 1, 12 do TICK(1, 1, 0); DRAIN() end
      assert(CS.stock.last_day == math.floor(DAY), "caught up")
      assert(KMM_Stock.level("A", "food") > 0, "API level")
      local got = KMM_Stock.take("A", "food", 3); assert(got == 3, "take " .. tostring(got))
      assert(KMM_Stock.add("A", "food", 2) == 2, "add")
      local w = KMM_Stock.workshop("A"); assert(w and w.making and w.rate, "workshop")
      -- новое состояние дирижёра (загрузка другого сейва): склад пересоздаётся внутри него
      local old = CS; CS = mkworld(); TICK(3, 1, 0.01)
      assert(CS.stock and CS.stock ~= old.stock, "re-init on new conductor state")
      assert(count(KMM_Stock.disabled()) == 0, "nothing disabled")
    """)


@case("TRADE: день порциями (day_begin/day_step/day_end) дает тот же склад, что M.day; один кадр не считает весь мир")
def t_phased(lua):
    lua.run(MODEL_PRE + """
      run_days(M, ST, CS, 0, 12, EMIT)
      local ST2, CS2 = copy(ST), copy(CS)
      M.day(ST, CS, 12, EMIT)
      local ctx = M.day_begin(ST2, CS2, 12, EMIT)
      assert(ctx and ctx.n >= 3, "ctx")
      local steps = 0
      while not M.day_step(ctx, 1) do steps = steps + 1; assert(steps < 100) end
      assert(steps >= 2, "по одному городу за кадр: " .. steps)
      for i = 1, 3 do M.day_end_part(ctx, i) end
      for t, s in pairs(ST.towns) do
        for c, v in pairs(s.q) do assert(math.abs(v - ST2.towns[t].q[c]) < 1e-9, "расхождение " .. t .. "/" .. c) end
      end
      assert(ST2.last_day == 12 and M.day_begin(ST2, CS2, 12, EMIT) == nil, "тот же день повторно не считается")
    """)


@case("TRADE: рантайм — день не в одном кадре, строки TRADE в stock.log (day computed), лавка/покупки логируются, очередь по одному")
def t_trade_log(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      TICK(40, 1, 0.01); DRAIN()
      local rt = KMM_Stock._rt
      assert(rt.ready and CS.stock.last_day, "ready")
      DRAIN(); DAY = DAY + 2
      local frames = 0
      -- опрос запускает день; дальше кванты по кадрам без нового опроса (dclock=0)
      CLOCK = CLOCK + 2; Events.h["GameWorld::charsUpdate"]({})
      assert(rt.dctx ~= nil, "day started")
      while rt.dctx and frames < 200 do frames = frames + 1; Events.h["GameWorld::charsUpdate"]({}) end
      assert(frames < 200 and not rt.dctx, "day finished by frames: " .. frames)
      for _ = 1, 6 do TICK(2, 1, 0); DRAIN() end
      assert(CS.stock.last_day == math.floor(DAY), "last_day " .. CS.stock.last_day .. " vs " .. DAY)
      local log = read_tmp("stock.log") or ""
      assert(log:find("TRADE stock day %d+ computed"), "day line in stock.log: " .. log)
      assert(log:find("source=new"), "source line")
    """)


@case("рантайм: лавка и склад рядом наполняются по складу города, списание, лимит операций, без переполнения")
def t_materialize(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      local shop_inv = mkinv(4, { mkitem("1946-gamedata.base", 1) })        -- лавка торгует едой, места на 4 вещи
      local box_inv = mkinv(100)
      local own_inv = mkinv(100)
      TICK(30, 1, 0.01)
      assert(KMM_Stock._rt.ready, "ready")
      local food0 = CS.stock.towns.A.q.food
      BUILDINGS = { mkbuilding("shop", "A", "f1", true, shop_inv), mkbuilding("box", "A", "f1", false, box_inv),
                    mkbuilding("mine", "A", "PF", false, own_inv), mkbuilding("wild", nil, nil, false, mkinv(100)) }
      TICK(10, 1, 0.001)
      assert(#shop_inv.items <= 4, "no overflow: " .. #shop_inv.items)
      assert(#shop_inv.items > 1, "shop restocked from stock: " .. #shop_inv.items)
      for _, it in ipairs(shop_inv.items) do assert(it.gd.ty == nil or it.gd.ty == 4, "shop got only its own category (ITEM)") end
      assert(#box_inv.items > 0 and #box_inv.items <= 12, "storage filled within ops limit: " .. #box_inv.items)
      assert(#own_inv.items == 0, "player building untouched")
      assert(CS.stock.towns.A.q.food < food0, "stock debited")
      local n = CREATED; TICK(10, 1, 0.001)
      assert(CREATED == n, "same day: no revisit")
      -- нехватка: полки пустеют (только наши вещи)
      local inv2 = mkinv(50); for i = 1, 8 do inv2.items[i] = mkitem("1946-gamedata.base", 1) end
      inv2.items[9] = mkitem("SOME-QUEST-ITEM", 1)
      BUILDINGS = { mkbuilding("shop2", "B", "f1", true, inv2) }
      CS.stock.towns.B.q.food = 1
      TICK(10, 1, 0.001)
      assert(#inv2.items < 9, "removed when short: " .. #inv2.items)
      local quest = false; for _, it in ipairs(inv2.items) do if it.gd.stringID == "SOME-QUEST-ITEM" then quest = true end end
      assert(quest, "foreign item kept")
      assert(count(KMM_Stock.disabled()) == 0, "nothing disabled")
    """)


@case("рантайм: торговец рядом и покупки жителей — по складу, без переполнения инвентаря")
def t_traders(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      local tinv = mkinv(6, { mkitem("209-gamedata.base", 1) })
      local full = mkinv(30); for i = 1, 20 do full.items[i] = mkitem("x" .. i) end
      NPCS = { mkchar("T", 10, 10, { trader = true, tsid = "A", fid = "f1", inv = tinv }),
               mkchar("N", 20, 20, { tsid = "A", fid = "f1", inv = full }) }
      math.randomseed(1)
      TICK(800, 1, 0.001)   -- покупка жителя: шанс 0.25 раз в 20 с → ~40 попыток
      assert(#tinv.items > 1 and #tinv.items <= 6, "trader restocked within room: " .. #tinv.items)
      assert(#full.items == 20, "full NPC inventory untouched: " .. #full.items)
      assert(KMM_Stock.stats().buys > 0, "npc buys happen")
    """)


@case("рантайм: ошибка API — отключается только функция, причина в debug.log, исключение наружу не выходит")
def t_api_error(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      BUILDINGS = { mkbuilding("shop", "A", "f1", true, mkinv(10, { mkitem("1946-gamedata.base") })) }
      TICK(30, 1, 0.01)
      BREAK = true
      TICK(20, 1, 0.1)
      local d = KMM_Stock.disabled()
      assert(d.materialize and not d.model and not d.tick, "only materialize disabled")
      local log = read_tmp("debug.log"); assert(log and log:find("%[KMM_Stock%] materialize disabled until restart"), "debug.log: " .. tostring(log))
      local day = CS.stock.last_day; TICK(30, 1, 0.1)
      assert(CS.stock.last_day > day, "model keeps running")
      -- ошибка модели: отключается модель, тик молчит, наружу ничего
      CS.F = nil; CS.stock.towns = nil
      CS.F = setmetatable({}, { __index = function() error("boom") end, __pairs = function() error("boom") end })
      CS.F = { f1 = setmetatable({}, { __index = function() error("state broken") end }) }
      DAY = DAY + 3; TICK(5, 1, 0.1)
      assert(KMM_Stock.disabled().model, "model disabled")
      -- API от TOWN с мусором не бросает
      assert(KMM_Stock.level(nil, nil) == nil and KMM_Stock.take({}, 5, "x") == 0, "API robust")
    """)


@case("рантайм: getPlayerInterface/getGameWorld бросают (главное меню) — ждём, без исключения")
def t_world_missing(lua):
    lua.load_runtime()
    lua.run("""
      install_conductor()
      getPlayerInterface = function() error("no interface in main menu") end
      TICK(50, 1, 0.01)
      assert(not KMM_Stock._rt.ready and count(KMM_Stock.disabled()) == 0, "waiting, nothing disabled")
    """)


@case("CONTRA: законность — незаконное идёт контрабандой (smuggle_run с кулдауном), не лавина; M.illegal/price")
def t_contra(lua):
    lua.run(MODEL_PRE + """
      CFG.params = { contra = { legal = { { pat = "One", drugs = false }, { pat = "Two", lux = 0.5 } }, inflow = 0.3, demand = 0.5, confiscate = 0.012,
                               trig = 0.25, delivery = 0.5, cooldown = 45, gap = 4, price = 1.5 } }
      M.init(ST, CS, CFG)
      assert(M.illegal(ST, "f1", "drugs") == true and M.illegal(ST, "f1", "food") == false and M.illegal(ST, "f2", "drugs") == false)
      assert(M.price(ST, "A", "drugs") == 1.5 and M.price(ST, "C", "drugs") == 1)
      run_days(M, ST, CS, 0, 360, EMIT)
      local n, per = 0, {}
      for _, ev in ipairs(EV) do if ev.type == "smuggle_run" then
        n = n + 1; assert(ev.cat == "drugs" and ev.town_sid and ev.town_name and ev.a, "fields"); per[ev.town_sid] = (per[ev.town_sid] or 0) + 1 end end
      assert(n > 0 and n <= 16, "runs " .. n)
      for t, k in pairs(per) do assert(k <= 360 / 45 + 1, t .. k) end
      assert(M.level(ST, "A", "drugs") > 0.02, "contraband keeps trickling")
    """)


def main():
    if not os.path.exists(DLL):
        print("SKIP: lua51.dll KenshiLua не найден")
        return 1
    for c in CASES:
        c()
    bad = [r for r in RESULTS if not r[1]]
    for name, ok, msg in RESULTS:
        print(("OK   " if ok else "FAIL ") + name + ("" if ok else "\n     " + msg))
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
