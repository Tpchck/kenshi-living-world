"""Офлайн-тесты игрока: продажа в лавку, потерянные караваны, реликтовая кузня (lua51.dll KenshiLua, заглушки API).
python -I -X utf8 build/KMM_Stock/_dev/test_player.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_stock as T  # noqa: E402

T.CASES.clear()
T.RESULTS.clear()
TRACES = "C:/KenshiModMap/build/KMM_Conductor/scripts/init/KMM_Traces.lua"
case = T.case

PRE = """
  package.loaded["stock_config"] = { materialize = false, npc_buys = false, traders = false, poll_seconds = 0 }
  local ITEMS = dofile(SCRIPTS_DIR .. "/kmm_stock_items.lua")
  FOOD = ITEMS.goods.food[1][1]
  install_conductor()
  PCS = { mkchar("P", 0, 0, { player = true }) }
  function shop_at(x, z)
    local inv = mkinv(60, { mkitem(FOOD, 3) })
    local b = mkbuilding("S1", "A", "f1", true, inv)
    function b:getPosition() return { x = x, y = 0, z = z } end
    BUILDINGS = { b }
    return inv
  end
  function addfood(inv, n) inv.items[#inv.items + 1] = mkitem(FOOD, n) end
  function sold() local k = 0; for _, e in ipairs(EMITTED) do if e.type == "player_sold" then k = k + 1 end end; return k end
"""


def boot(lua):
    lua.run(f'SCRIPTS_DIR = "{T.SCRIPTS}"')
    lua.load_runtime()
    lua.run(PRE)


@case("продажа игрока: прирост рядом с игроком засчитывается один раз, склад растёт, событие player_sold")
def t_sale(lua):
    boot(lua)
    lua.run("""
      local inv = shop_at(5, 5)
      TICK(40, 1, 0.001)
      assert(KMM_Stock._rt.ready)
      local q0 = CS.stock.towns.A.q.food
      addfood(inv, 6)
      TICK(12, 1, 0.0001)
      assert(sold() == 1, "sold events: " .. sold())
      local e; for _, x in ipairs(EMITTED) do if x.type == "player_sold" then e = x end end
      assert(e.cat == "food" and e.n == 6 and e.town_sid == "A" and e.a == "f1" and e.town_name == "Alpha")
      assert(CS.stock.towns.A.q.food > q0, "stock grew")
      TICK(30, 1, 0.0001)
      assert(sold() == 1, "no double count: " .. sold())
    """)


@case("restock без игрока в радиусе торговли и скачок > лимита — не считаются")
def t_restock(lua):
    boot(lua)
    lua.run("""
      local inv = shop_at(800, 0)   -- игрок далеко от лавки (вне радиуса торговли)
      TICK(40, 1, 0.001)
      local q0 = CS.stock.towns.A.q.food
      addfood(inv, 20)
      TICK(30, 1, 0.0001)
      assert(sold() == 0 and CS.stock.towns.A.q.food == q0, "far restock ignored")
      local inv2 = shop_at(3, 3)
      TICK(40, 1, 0.0001)
      addfood(inv2, 500)   -- ванильный скачок
      TICK(30, 1, 0.0001)
      assert(sold() == 0, "huge jump ignored")
    """)


@case("наше пополнение лавки (put_item) не считается продажей игрока")
def t_own_add(lua):
    boot(lua)
    lua.run("""
      local inv = shop_at(2, 2)
      TICK(40, 1, 0.001)
      KMM_Stock.put_item(inv, "A", "food")
      TICK(30, 1, 0.0001)
      assert(sold() == 0, "own put_item not a sale: " .. sold())
    """)


@case("реликтовая кузня: один раз за мир, флаг в состоянии; «персонажей нет» — ничего")
def t_relic(lua):
    boot(lua)
    lua.run("""
      PCS = {}
      TICK(60, 1, 0.001)
      assert(#EMITTED == 0)
      local p = mkchar("P", 0, 0, { player = true })
      p.inv = mkinv(20, { mkitem("junk", 1) })
      PCS = { p }
      TICK(60, 1, 0.001)
      local function nrel() local k = 0; for _, e in ipairs(EMITTED) do if e.type == "player_relic_forge" then k = k + 1 end end; return k end
      assert(nrel() == 0)
      local core = mkitem("999-KMM_Tech.mod", 1); core.gd.name = "Relic AI Core"
      p.inv.items[#p.inv.items + 1] = core
      TICK(120, 1, 0.001)
      assert(nrel() == 1, "relic once: " .. nrel())
      assert(CS.stock.flags.player_relic_forge, "flag saved in state")
      TICK(120, 1, 0.001)
      assert(nrel() == 1)
    """)


@case("ошибка API в продажах отключает только player_sales")
def t_err(lua):
    boot(lua)
    lua.run("""
      shop_at(2, 2)
      TICK(40, 1, 0.001)
      BREAK = true
      TICK(30, 1, 0.001)
      BREAK = false
      assert(KMM_Stock.disabled().player_sales, "player_sales disabled")
      assert(not KMM_Stock.disabled().model and not KMM_Stock.disabled().tick, "others alive")
      local log = read_tmp("debug.log"); assert(log and log:find("player_sales disabled", 1, true))
    """)


TR_BOOT = """
  KenshiLua = { log = function() end }
  EMITTED, NOW = {}, 100
  os.clock = function() return NOW end
  Events = { on = function(n, f) EV_H = f end }
  CHARS = {}
  local gw = { getCharacterUpdateList = function() local s = {}; for _, c in ipairs(CHARS) do s[c] = true end; return s end }
  function getGameWorld() return gw end
  local CS = { F = {}, events = {}, last_day = 10, next_id = 1 }
  KMM_Conductor = { state = function() return CS end,
    cfg = function() return { player_faction = "PF", params = { traces = { enabled = true, lost_scan_seconds = 0, price_enabled = false },
                              guard = { debug_log = TMP .. "/debug.log" } }, town_info = {} } end,
    read_json = function() return { factions = {}, caravans = {}, dead_caravan_sids = { "DEADTPL" } } end,
    emit = function(ev) EMITTED[#EMITTED + 1] = ev end, name = function(f) return f end, fpos = function() return nil end,
    tier_shift = function() return 0 end, set_base = function() end,
    towns = function() return { { sid = "T1", owner = "f1", x = 500, z = 0 }, { sid = "T2", owner = "f1", x = 9000, z = 0 } } end }
  function mkcar(name, x, z, fid, tpl)
    local c = { name = name, x = x, z = z, dead = false }
    function c:isPlayerCharacter() return false end
    function c:isDead() return self.dead end
    function c:getPosition() return { x = self.x, y = 0, z = self.z } end
    function c:getFaction() return { getData = function() return { stringID = fid } end } end
    function c:getPlatoon() return { me = { getPlatoonStringID = function() return "plat_" .. name:sub(1, 1) end, squadTemplate = { stringID = tpl or "VANILLA" } },
                                     getIsTrader = function() return true end } end
    return c
  end
  local pc = { isPlayerCharacter = function() return true end, getPosition = function() return { x = 0, y = 0, z = 0 } end,
               getPlatoon = function() error("no") end }
  PCS = { pc }
  local pi = { getAllPlayerCharacters = function() return PCS end }
  function getPlayerInterface() return pi end
  dofile("%s")
  function TT() NOW = NOW + 10; KMM_Traces._tick() end
"""


@case("караван потерян: все мертвы — caravan_lost один раз, by по близости игрока, ближайший город владельца, свои трупы не в счёт")
def t_caravan(lua):
    lua.run(TR_BOOT % TRACES, "traces boot")
    lua.run("""
      local a, b = mkcar("a1", 2500, 0, "f1"), mkcar("a2", 2520, 0, "f1")
      CHARS = { a, b }
      TT(); TT()
      assert(#EMITTED == 0, "alive caravan: nothing")
      a.dead = true; TT()
      assert(#EMITTED == 0, "one member alive: nothing")
      b.dead = true; TT(); TT(); TT()
      local n = 0; for _, e in ipairs(EMITTED) do if e.type == "caravan_lost" then n = n + 1 end end
      assert(n == 1, "once: " .. n)
      local e = EMITTED[1]
      assert(e.a == "f1" and e.town_sid == "T1" and e.to_sid == nil, "fields")
      assert(e.by == "other", "2500 away from player: " .. tostring(e.by))
      local c = mkcar("c1", 300, 0, "f1"); CHARS = { c }; TT(); c.dead = true; TT(); TT()
      assert(EMITTED[2] and EMITTED[2].by == "player", "player nearby")
      local d = mkcar("d1", 100, 0, "f1", "DEADTPL"); CHARS = { d }; TT(); d.dead = true; TT(); TT()
      assert(#EMITTED == 2, "our dead caravans ignored: " .. #EMITTED)
      assert(not KMM_Traces.disabled().caravan_lost)
    """)


@case("караваны: персонажей игрока нет — тихо; ошибка API отключает только caravan_lost")
def t_caravan_err(lua):
    lua.run(TR_BOOT % TRACES, "traces boot")
    lua.run("""
      local saved = PCS; PCS = {}
      TT(); TT(); assert(#EMITTED == 0)
      PCS = saved
      getGameWorld = function() error("api changed") end
      TT(); TT()
      assert(KMM_Traces.disabled().caravan_lost, "disabled")
      assert(not KMM_Traces.disabled().events, "others alive")
    """)


@case("CONTRA: игрок сбыл незаконное для владельца — contraband_caught {a, town_sid, town_name, cat}; законное — нет")
def t_contra_caught(lua):
    boot(lua)
    lua.run("""
      CFG.params = { contra = { legal = { { pat = "One", food = false } }, caught = 1.0, inflow = 0.3, demand = 0.5, confiscate = 0.012 } }
      local inv = shop_at(5, 5)
      TICK(40, 1, 0.001)
      addfood(inv, 6)
      TICK(12, 1, 0.0001)
      local e; for _, x in ipairs(EMITTED) do if x.type == "contraband_caught" then e = x end end
      assert(e and e.a == "f1" and e.town_sid == "A" and e.town_name == "Alpha" and e.cat == "food", "caught event")
      assert(sold() == 1, "sale still counted")
      CFG.params.contra.legal = {}
      local n = 0; for _, x in ipairs(EMITTED) do if x.type == "contraband_caught" then n = n + 1 end end
      DAY = DAY + 2; addfood(inv, 6); TICK(12, 1, 0.0001)
      local n2 = 0; for _, x in ipairs(EMITTED) do if x.type == "contraband_caught" then n2 = n2 + 1 end end
      assert(n2 == n, "legal sale is not caught")
    """)


def main():
    if not os.path.exists(T.DLL):
        print("SKIP: lua51.dll не найден")
        return 1
    for c in T.CASES:
        c()
    bad = [r for r in T.RESULTS if not r[1]]
    for name, ok, msg in T.RESULTS:
        print(("OK   " if ok else "FAIL ") + name + ("" if ok else "\n     " + msg))
    print(f"{len(T.RESULTS) - len(bad)}/{len(T.RESULTS)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
