"""Офлайн-тест KMM_Town на LuaJIT из KenshiLua (lua51.dll) с заглушками API игры, склада и дирижёра. Без игры, без сети, < 5 с.
python -I -X utf8 build/KMM_Town/_dev/test_town.py
Пути C:/KenshiModMap/logs/ перенаправляются во временную папку — реальные логи не трогаются."""
import ctypes
import os
import sys
import tempfile

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
SCRIPT = "C:/KenshiModMap/build/KMM_Town/scripts/init/kmm_town.lua"
SCRIPTS_DIR = "C:/KenshiModMap/build/KMM_Town/scripts"

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

STUBS = r"""
TMP = "%(tmp)s"
EVENTS, LOGS, API, BREAK_SCAN, BREAK_STOCK = {}, {}, { scan = 0, stock = 0, pi = 0 }, false, false
local real_open = io.open
io.open = function(p, m) p = tostring(p):gsub("^C:/KenshiModMap/logs/", TMP .. "/"):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return real_open(p, m) end; local __rr = os.remove; os.remove = function(p) p = tostring(p):gsub("^C:/KenshiModMap/state/", TMP .. "/"); return __rr(p) end
function read_tmp(name) local f = real_open(TMP .. "/" .. name, "r"); if not f then return "" end; local s = f:read("*a"); f:close(); return s end
CLOCK, DAY = 100, 10.0
os.clock = function() return CLOCK end
package.path = "%(scripts)s/?.lua;" .. package.path
KenshiLua = { log = function(s) LOGS[#LOGS + 1] = s end }
Events = { h = {} }
function Events.on(name, f) Events.h[name] = f; return 1 end
function Events.off(id) end
DATA = dofile("%(scripts)s/kmm_town_data.lua")
TOWN = next(DATA.towns)
for sid, m in pairs(DATA.machines) do if m.item then MACHINE = sid; ITEM = m.item; CAT = m.cat; break end end
-- инвентарь
function mkinv(cap)
  local inv = { items = {}, cap = cap or 99 }
  local function n() local k = 0; for _, it in ipairs(inv.items) do k = k + 1 end; return k end
  function inv:tryAddItem(it, q) if n() >= self.cap then return false end; table.insert(self.items, it); return true end
  function inv:addItem(it, q, a, b) table.insert(self.items, it); return true end
  function inv:getItem(gd) for _, it in ipairs(self.items) do if it.gd == gd then return it end end; return nil end
  function inv:removeItemDontDestroy_returnsItem(it, k, c) for i, x in ipairs(self.items) do if x == it then table.remove(self.items, i); return x end end; return nil end
  function inv:count() return n() end
  return inv
end
local GDS = {}
local gw = { theFactory = {}, gamedata = {} }
function gw.gamedata:getData(sid, ty) GDS[sid] = GDS[sid] or { stringID = sid }; return GDS[sid] end
function gw.theFactory:createItem(gd) return { gd = gd } end
local ts = { getTotalDays = function() return DAY end }
function gw:getTimeStamp_inGameHours() return ts end
CHARS = {}
function gw:getCharacterUpdateList()
  API.scan = API.scan + 1
  if BREAK_SCAN then error("getCharacterUpdateList: binding changed") end
  local set = {}; for _, c in ipairs(CHARS) do set[c] = true end; return set
end
function getGameWorld() return gw end
PCS = {}
local pi = { getAllPlayerCharacters = function() return PCS end }
function getPlayerInterface() API.pi = API.pi + 1; return pi end
local townobj = { getGameData = function() return { stringID = TOWN } end }
local nowhere = nil
local NEXT = 0
function mkchar(o)
  NEXT = NEXT + 1
  local c = { x = o.x or 0, z = o.z or 0, pc = o.pc, trader = o.trader, resident = o.resident, work = o.work, intown = (o.intown ~= false),
              inv = mkinv(), key = "h" .. NEXT }
  function c:isPlayerCharacter() return self.pc or false end
  function c:isDead() return false end
  function c:isAnimal() return nil end
  function c:getPosition() return { x = self.x, y = 0, z = self.z } end
  function c:getCurrentTownLocation() return self.intown and townobj or nowhere end
  function c:getHandle() local k = self.key; return { toString = function() return k end, isValid = function() return not c.gone end,
                                                       getCharacter = function() if c.gone then return nil end; return c end } end
  function c:isATrader() return self.trader or false end
  function c:isResident() return self.resident and townobj or nil end
  function c:isInCombatMode() return false end
  function c:getInventory() return self.inv end
  function c:getBody()
    local ch = self
    return { getCurrentAction = function()
      if not ch.work then return nil end
      local b = ch.work
      local h = { isValid = function() return not b.gone end, getBuilding = function() if b.gone then return nil end; return b end }
      return { subject = h, key = function() return DATA.work_tasks.AUTO_LABOURING_MINES end }
    end }
  end
  table.insert(CHARS, c)
  return c
end
function mkmachine(sid, cap)
  local inv = mkinv(cap)
  return { inv = inv, getGameData = function() return { stringID = sid } end, getInventory = function() return inv end }
end
STOCKQ = 50
function install_stock()
  KMM_Stock = {
    level = function(t, c) API.stock = API.stock + 1; if BREAK_STOCK then error("level boom") end; return STOCKQ / 100 end,
    take = function(t, c, v) API.stock = API.stock + 1; if STOCKQ >= v then STOCKQ = STOCKQ - v; return v end; return 0 end,
    add = function(t, c, v) STOCKQ = STOCKQ + v; return v end,
  }
end
TSTATE = {}
KMM_Conductor = { emit = function(ev) EVENTS[#EVENTS + 1] = ev; return ev end, town_state = function() return TSTATE end }
function TICK(n, dclock, dday)
  for _ = 1, n do CLOCK = CLOCK + (dclock or 2.5); DAY = DAY + (dday or 0.002); Events.h["GameWorld::charsUpdate"]({}) end
end
-- смена мира: объект прошлого сейва — любой вызов его метода = обращение к освобождённой памяти (в тесте — ошибка + счётчик)
STALE = 0
function poison(o)
  o.gone = true
  for k, v in pairs(o) do if type(v) == "function" then o[k] = function() STALE = STALE + 1; error("stale object of previous world: " .. k) end end end
end
function count_ev(ty) local k = 0; for _, e in ipairs(EVENTS) do if e.type == ty then k = k + 1 end end; return k end
function assert_eq(a, b, msg) if a ~= b then error(msg .. ": expected " .. tostring(b) .. ", got " .. tostring(a), 2) end end
"""


class Lua:
    def __init__(self, tmp):
        self.st = L.luaL_newstate()
        L.luaL_openlibs(self.st)
        self.run(STUBS % {"tmp": tmp, "scripts": SCRIPTS_DIR}, "stubs")

    def run(self, code, name="chunk"):
        rc = L.luaL_loadstring(self.st, code.encode("utf-8")) or L.lua_pcall(self.st, 0, 0, 0)
        if rc:
            msg = L.lua_tolstring(self.st, -1, None)
            L.lua_settop(self.st, 0)
            raise AssertionError(f"{name}: {msg.decode('utf-8', 'replace') if msg else rc}")

    def close(self):
        L.lua_close(self.st)


def compile_only(path):
    st = L.luaL_newstate()
    rc = L.luaL_loadfile(st, path.encode("utf-8"))
    msg = L.lua_tolstring(st, -1, None) if rc else None
    L.lua_close(st)
    if rc:
        raise AssertionError(f"syntax {path}: {msg.decode('utf-8', 'replace')}")


SETUP_TOWN = """
install_stock()
P = mkchar({ pc = true }); PCS = { P }
M = mkmachine(MACHINE, 99)
"""

TESTS = {
    "load_has_no_side_effects": """
dofile(SCRIPT_PATH)
assert_eq(API.pi, 0, "getPlayerInterface на загрузке"); assert_eq(API.scan, 0, "скан на загрузке"); assert_eq(#EVENTS, 0, "события на загрузке")
assert(Events.h["GameWorld::charsUpdate"], "нет обработчика тика")
""",
    "no_player_chars_nothing": """
install_stock(); M = mkmachine(MACHINE, 99); for i = 1, 5 do mkchar({ work = M }) end
dofile(SCRIPT_PATH)
TICK(200, 2.5)
assert_eq(API.scan, 0, "скан без персонажей"); assert_eq(API.stock, 0, "склад без персонажей"); assert_eq(#EVENTS, 0, "события без персонажей")
assert_eq(KMM_Town._rt.ready, false, "ready без персонажей")
""",
    "lazy_start_then_chain": SETUP_TOWN + """
W = mkchar({ work = M }); C = mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
TICK(3, 2.5)
assert_eq(API.scan, 0, "скан до задержки")
TICK(30, 2.5)
assert(count_ev("town_craft") >= 1, "нет town_craft")
assert(count_ev("town_haul") >= 1, "нет town_haul")
TICK(40, 2.5)
assert(count_ev("town_delivered") >= 1, "нет town_delivered")
assert(S.inv:count() >= 1, "товар не дошёл до лавки")
assert(STOCKQ <= 50, "склад не списан")
assert(TSTATE[TOWN] and TSTATE[TOWN].vis.crafted >= 1, "счётчики не в S.town")
assert(EVENTS[1].type:sub(1, 5) == "town_", "type без префикса town_")
""",
    "worker_limit_per_cycle": SETUP_TOWN + """
for i = 1, 12 do mkchar({ work = mkmachine(MACHINE, 99) }) end
for i = 1, 8 do mkchar({}) end
mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
TICK(14, 2.5)   -- старт
local before = KMM_Town._rt.stats.crafted
local cycles0 = KMM_Town._rt.stats.cycles
TICK(12, 2.5)   -- ровно один цикл (30 с)
local c = KMM_Town._rt.stats.cycles - cycles0
assert(c >= 1, "цикла не было")
local made = KMM_Town._rt.stats.crafted - before
assert(made <= 3 * c, "мастеров за цикл больше лимита: " .. made .. " за " .. c)
local busy = 0; for _ in pairs(KMM_Town._rt.jobs) do busy = busy + 1 end
assert(busy <= 2, "носильщиков больше лимита: " .. busy)
TICK(200, 2.5)
busy = 0; for _ in pairs(KMM_Town._rt.jobs) do busy = busy + 1 end
assert(busy <= 2, "носильщиков больше лимита (долго): " .. busy)
assert(#KMM_Town._rt.crate <= 6, "очередь ящика больше лимита")
""",
    "no_stock_waits_quietly": """
P = mkchar({ pc = true }); PCS = { P }; M = mkmachine(MACHINE, 99); mkchar({ work = M }); mkchar({}); mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
TICK(200, 2.5)
assert_eq(#EVENTS, 0, "события без склада"); assert_eq(API.scan, 0, "скан без склада")
assert(KMM_Town._rt.stats.waits_stock > 0, "не ждал склад")
assert(next(KMM_Town.disabled()) == nil, "что-то отключилось без склада")
install_stock()
TICK(30, 2.5)
assert(count_ev("town_craft") >= 1, "после появления склада не заработал")
""",
    "scan_api_error_disables_only_scan": SETUP_TOWN + """
mkchar({ work = M }); BREAK_SCAN = true
dofile(SCRIPT_PATH)
TICK(60, 2.5)
assert(KMM_Town.disabled().scan, "scan не отключился"); assert(not KMM_Town.disabled().tick, "tick отключился")
assert(read_tmp("debug.log"):find("scan disabled until restart", 1, true), "нет причины в debug.log")
local n = API.scan; TICK(60, 2.5); assert_eq(API.scan, n, "скан продолжает вызываться после отключения")
""",
    "stock_api_error_disables_link": SETUP_TOWN + """
mkchar({ work = M }); mkchar({}); BREAK_STOCK = true
dofile(SCRIPT_PATH)
TICK(60, 2.5)
assert(KMM_Town.disabled().stock_link, "stock_link не отключился"); assert_eq(count_ev("town_craft"), 0, "craft при сломанном складе")
assert(read_tmp("debug.log"):find("stock_link disabled", 1, true), "нет причины в debug.log")
""",
    "outside_town_nothing": """
install_stock(); P = mkchar({ pc = true, intown = false }); PCS = { P }; mkchar({ work = mkmachine(MACHINE, 99) })
dofile(SCRIPT_PATH)
TICK(200, 2.5)
assert_eq(API.scan, 0, "скан вне города"); assert_eq(#EVENTS, 0, "события вне города")
""",
    "shortage_once_with_cooldown": SETUP_TOWN + """
STOCKQ = 5; mkchar({ work = M })
dofile(SCRIPT_PATH)
TICK(100, 2.5, 0.0005)
assert_eq(count_ev("town_shortage"), 1, "town_shortage не один раз")
assert_eq(count_ev("town_craft"), 0, "craft при пустом складе")
""",
    "untracked_town_silent": SETUP_TOWN + """
KMM_Stock.level = function(t, c) return nil end; mkchar({ work = M })
dofile(SCRIPT_PATH)
TICK(100, 2.5)
assert_eq(#EVENTS, 0, "события для города, которого нет в складе")
""",
    "far_npcs_ignored": SETUP_TOWN + """
mkchar({ work = M, x = 99999 })
dofile(SCRIPT_PATH)
TICK(100, 2.5)
assert_eq(count_ev("town_craft"), 0, "дальний NPC работал")
""",
    "delivered_item_credited_to_stock": SETUP_TOWN + """
for sid, m in pairs(DATA.machines) do if m.cat == "armor" then MACHINE = sid; break end end
M = mkmachine(MACHINE, 99)
KMM_Stock.pick_item = function(t, c) return "plate_sid", 3 end
MADE, TAKEN = 0, {}
KMM_Stock.take = function(t, c, v) TAKEN[c] = (TAKEN[c] or 0) + v; return v end
KMM_Stock.made = function(t, c, v) MADE = MADE + v; return v end
W = mkchar({ work = M }); mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
local k = 0
while KMM_Town._rt.stats.crafted == 0 do TICK(1, 2.5); k = k + 1; if k > 200 then error("нет крафта") end end
assert_eq(KMM_Town._rt.stats.delivered, 0, "доставка до носки")
assert((TAKEN.metal or 0) >= 1 and not TAKEN.armor, "куёт не из металла: " .. (function() local r = {}; for k, v in pairs(TAKEN) do r[#r+1] = k .. "=" .. v end; return table.concat(r, ",") .. MACHINE .. tostring(DATA.machines[MACHINE].cat) end)() .. tostring(TAKEN.metal) .. "/" .. tostring(TAKEN.weapons) .. " crafted=" .. KMM_Town._rt.stats.crafted)
assert_eq(MADE, 0, "засчитано до доставки")
TICK(60, 2.5)
local d = KMM_Town._rt.stats.delivered
assert(d >= 1, "нет доставки")
assert_eq(MADE, d, "доставка -> склад +1 за предмет")
assert_eq(TSTATE[TOWN].vis.stocked, d, "счётчик stocked")
""",
    "lost_item_not_credited": SETUP_TOWN + """
for sid, m in pairs(DATA.machines) do if m.cat == "armor" then MACHINE = sid; break end end
M = mkmachine(MACHINE, 99)
KMM_Stock.pick_item = function(t, c) return "plate_sid", 3 end
MADE = 0
KMM_Stock.made = function(t, c, v) MADE = MADE + v; return v end
mkchar({ work = M }); mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
local n0
while true do TICK(1, 2.5); if next(KMM_Town._rt.jobs) then break end; if CLOCK > 5000 then error("нет носильщика") end end
for _, c in ipairs(CHARS) do c.inv.items = {} end   -- предмет пропал/украден по дороге
M.inv.items = {}; KMM_Stock.level = function() return 0 end   -- новых изделий больше нет
TICK(60, 2.5)
assert_eq(KMM_Town._rt.stats.delivered, 0, "доставка пропавшего")
assert_eq(MADE, 0, "пропавший предмет засчитан складу")
""",
    "caravan_delivery": SETUP_TOWN + """
mkchar({ work = M }); mkchar({}); K = mkchar({ trader = true, resident = false })
dofile(SCRIPT_PATH)
TICK(120, 2.5)
assert(count_ev("town_caravan_loaded") >= 1, "нет town_caravan_loaded")
assert(K.inv:count() >= 1, "товар не у каравана")
""",
    "save_switch_mid_cycle_with_load_hook": SETUP_TOWN + """
W = mkchar({ work = M }); C = mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
assert(Events.h["PlayerInterface::loadFromSerialise"], "нет обработчика загрузки сейва")
local k = 0
while not (KMM_Town._rt.stage and KMM_Town._rt.stage >= 1) do TICK(1, 2.5); k = k + 1; if k > 300 then error("цикл не начался") end end
local old = CHARS; CHARS = {}
for _, c in ipairs(old) do poison(c.inv); poison(c) end; poison(M.inv); poison(M)
Events.h["PlayerInterface::loadFromSerialise"]({}, {})
assert_eq(KMM_Town._rt.stage, nil, "стадия цикла пережила загрузку сейва"); assert_eq(#KMM_Town._rt.crate, 0, "ящик пережил загрузку")
P = mkchar({ pc = true }); PCS = { P }; M = mkmachine(MACHINE, 99)
mkchar({ work = M }); mkchar({}); mkchar({ trader = true, resident = true })
TICK(120, 2.5)
assert_eq(STALE, 0, "вызов метода объекта прошлого мира")
assert(next(KMM_Town.disabled()) == nil, "что-то отключилось после загрузки сейва")
assert(count_ev("town_delivered") >= 1, "цепочка не заработала в новом мире")
""",
    "save_switch_mid_cycle_no_hook": SETUP_TOWN + """
W = mkchar({ work = M }); C = mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
for st = 1, 5 do   -- смена мира перед каждой стадией цикла по очереди (новая игра без события загрузки)
  local k = 0
  TICK(40, 2.5)   -- в новом мире успевают появиться ящик и носильщики
  while not (KMM_Town._rt.stage == st and (#KMM_Town._rt.crate > 0 or next(KMM_Town._rt.jobs))) do TICK(1, 2.5); k = k + 1; if k > 400 then error("нет стадии " .. st) end end
  local old = CHARS; CHARS = {}
  for _, c in ipairs(old) do poison(c.inv); poison(c) end; poison(M.inv); poison(M)
  P = mkchar({ pc = true }); PCS = { P }; M = mkmachine(MACHINE, 99)
  mkchar({ work = M }); mkchar({}); mkchar({ trader = true, resident = true })
  TICK(2, 2.5)
  assert_eq(STALE, 0, "стадия " .. st .. ": вызов метода объекта прошлого мира")
end
assert(next(KMM_Town.disabled()) == nil, "что-то отключилось")
""",
    "ore_miners_draw_town_vein": SETUP_TOWN + """
KMM_Ore = { ore_kind = function(s) return (s == "42248-gamedata.base") and "iron" or nil end }
MINED, MINED_TOWN = 0, nil
KMM_Conductor.town_mined = function(t, a) MINED = MINED + a; MINED_TOWN = t; return a end
ORE = mkmachine("42248-gamedata.base", 99)
for i = 1, 3 do mkchar({ work = ORE }) end
mkchar({ work = mkmachine("not-an-ore-node", 99) })
dofile(SCRIPT_PATH)
TICK(120, 2.5, 0.01)
assert(MINED > 0 and MINED_TOWN == TOWN, "town miners did not draw the vein: " .. tostring(MINED))
assert_eq(KMM_Town._rt.stats.miners, 3, "only miners at ore nodes are counted")
local per_cycle_cap = 3 * 2 * 0.25
assert(MINED <= KMM_Town._rt.stats.cycles * per_cycle_cap + 1e-6, "draw capped by mine_max_hours: " .. MINED)
assert(read_tmp("stock.log"):find("ore=%d"), "cycle line carries ore=")
assert(next(KMM_Town.disabled()) == nil, "nothing disabled")
""",
    "trade_log_lines": SETUP_TOWN + """
mkchar({ work = M }); mkchar({}); K = mkchar({ trader = true, resident = false })
dofile(SCRIPT_PATH)
TICK(120, 2.5)
local log = read_tmp("stock.log")
assert(log:find("TRADE player entered"), "нет строки входа в город: " .. log)
assert(log:find("TRADE caravan loaded"), "нет строки каравана: " .. log)
assert(log:find("cycle: crafted="), "нет итога цикла")
local n = 0; for _ in log:gmatch("caravan loaded") do n = n + 1 end
assert(n == KMM_Town._rt.stats.to_caravan, "не больше 1 строки на событие: " .. n)
""",
}


def main():
    res = []
    for p in (SCRIPT, SCRIPTS_DIR + "/kmm_town_data.lua"):
        compile_only(p)
    res.append(("syntax", True, ""))
    for name, code in TESTS.items():
        tmp = tempfile.mkdtemp(prefix="kmm_town_")
        lua = Lua(tmp.replace("\\", "/"))
        try:
            lua.run(f'SCRIPT_PATH = "{SCRIPT}"\n' + code, name)
            res.append((name, True, ""))
        except AssertionError as e:
            res.append((name, False, str(e)))
        finally:
            lua.close()
    ok = sum(1 for r in res if r[1])
    for n, good, msg in res:
        print(("OK   " if good else "FAIL ") + n + ("" if good else "  — " + msg))
    print(f"{ok}/{len(res)}")
    sys.exit(0 if ok == len(res) else 1)


if __name__ == "__main__":
    main()
