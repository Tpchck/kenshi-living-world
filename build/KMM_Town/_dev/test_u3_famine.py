"""Офлайн-тест U3 KMM_Town: голод города в его постройках (ванильный PRODUCTION_STARVED), плавность, откат, самоотключение.
python -I -X utf8 build/KMM_Town/_dev/test_u3_famine.py
Заглушки — из test_town.py (LuaJIT KenshiLua, без игры); логи во временной папке."""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("kmm_test_town", os.path.join(HERE, "test_town.py"))
tt = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tt)

BLD_STUBS = r"""
lektor = { new = function(ty) local l = {}; function l:clear() for i = #self, 1, -1 do self[i] = nil end end; return l end }
BLD, BREAK_SPHERE = {}, false
API.sphere = 0
getGameWorld().getObjectsWithinSphere = function(self, buf, pos, r, ty, maxn, skip)
  API.sphere = API.sphere + 1
  if BREAK_SPHERE then error("getObjectsWithinSphere: binding changed") end
  assert(ty == 0, "тип объектов не BUILDING")
  for _, b in ipairs(BLD) do if #buf >= maxn then break end; if not b.unloaded then buf[#buf + 1] = b.ro end end
end
KMM_Conductor.cfg = function() return { player_faction = "PF" } end
LV = {}
function install_lv() KMM_Stock.level = function(t, c) return LV[c] or 0.5 end end
for sid, m in pairs(DATA.machines) do if m.cat == "food" and not FOODM then FOODM = sid end end
local NB = 0
function mkbld(o)
  NB = NB + 1
  local town = P:getCurrentTownLocation()
  local b = { sid = o.sid or FOODM, x = o.x or (NB * 40), z = o.z or 0, productionMult = 1, unloaded = false }
  local pb = { productionState = 2, consumptionItems = {} }
  for i, a in ipairs(o.inputs or {}) do pb.consumptionItems[i] = { amount = a, maxCapacity = o.cap or 100 } end
  if o.copies then   -- элемент lektor отдаётся копией: запись не доходит до движка
    local real = pb.consumptionItems
    pb.real = real
    pb.consumptionItems = setmetatable({}, { __len = function() return #real end,
      __index = function(_, i) local c = real[i]; return c and { amount = c.amount, maxCapacity = c.maxCapacity } or nil end })
  end
  b.pb = (o.noprod ~= true) and pb or nil
  local key = "b" .. NB
  local h = { isValid = function() return not b.unloaded end, getBuilding = function() if b.unloaded then return nil end; return b end,
              toString = function() return key end }
  function b:getHandle() return h end
  function b:getProductionBuilding() return self.pb end
  function b:isThePlayer() return o.player or false end
  function b:getFaction() return { data = { stringID = o.fid or "npcfac" } } end
  function b:getSpecialFunction() return o.mine and 1 or 10 end
  function b:getGameData() return { stringID = self.sid } end
  function b:getBuildingClass() return o.farm and 13 or 4 end
  function b:getPosition() return { x = self.x, y = 0, z = self.z } end
  function b:getTown() if o.intown == false then return nil end; return town end
  function b:getCurrentTownLocation() if o.intown == false then return nil end; return town end
  b.ro = { getHandle = function() return h end }
  table.insert(BLD, b)
  return b
end
function starved_count() local n = 0; for _, b in ipairs(BLD) do if b.pb and b.pb.productionState == 0 then n = n + 1 end end; return n end
function store() return (TSTATE[TOWN] or {}).u3 or {} end
function nstore() local n = 0; for _ in pairs(store()) do n = n + 1 end; return n end
function CYCLE(k, dday) TICK(12 * (k or 1), 2.5, dday) end
"""

SETUP = tt.SETUP_TOWN + """
install_lv()
"""

TESTS = {
    "starve_smooth_limits_and_owners": SETUP + """
LV.food = 0.0
local W = {}
for i = 1, 4 do W[i] = mkbld({ inputs = { 50, 20 } }) end
for i = 1, 4 do W[#W + 1] = mkbld({ sid = "farm_sid", farm = true }) end
PLY = mkbld({ inputs = { 30 }, player = true }); PF = mkbld({ inputs = { 30 }, fid = "PF" })
MINE = mkbld({ inputs = { 30 }, mine = true }); FAR = mkbld({ inputs = { 30 }, intown = false })
UNK = mkbld({ sid = "unknown_workshop", inputs = { 30 } }); NOP = mkbld({ noprod = true })
dofile(SCRIPT_PATH)
TICK(14, 2.5); TICK(8, 2.5)   -- старт + стадии первого цикла
local s1 = starved_count()
assert(s1 >= 1 and s1 <= 2, "за первый цикл больше лимита изменений или ноль: " .. s1)
CYCLE(1); assert(starved_count() <= s1 + 2, "плавность: больше 2 за цикл")
CYCLE(6)
assert_eq(starved_count(), 8, "при пустой полке остановлены все 8 построек города")
for i = 1, 4 do
  local ci = W[i].pb.consumptionItems
  assert_eq(ci[1].amount, 0, "вход 1 не изъят"); assert_eq(ci[2].amount, 0, "вход 2 не изъят")
end
for i = 5, 8 do assert_eq(W[i].productionMult, 1, "productionMult тронут"); assert_eq(W[i].pb.productionState, 0, "ферма не STARVED") end
for _, b in ipairs({ PLY, PF, MINE, FAR, UNK }) do
  assert_eq(b.pb.productionState, 2, "тронута чужая постройка " .. b.sid); assert_eq(b.pb.consumptionItems[1].amount, 30, "изъят вход у чужой")
end
assert_eq(nstore(), 8, "изъятое не в слоте дирижёра S.town[tsid].u3")
assert(KMM_Town.u3().inputs_ok == true, "проверка записи входов")
local log = read_tmp("stock.log")
assert(log:find("U3 starve town=", 1, true), "нет маркера U3 starve")
assert(log:find("U3 check inputs_write=1", 1, true), "нет маркера проверки записи")
assert(log:find("U3 pop lever: none", 1, true), "нет маркера о рычаге жителей")
assert(log:find("starved=8/8", 1, true), "нет итоговой строки по категории")
assert(next(KMM_Town.disabled()) == nil or not KMM_Town.disabled().famine, "famine отключился")
""",
    "partial_famine_half": SETUP + """
LV.food = 0.2
for i = 1, 6 do mkbld({ inputs = { 10 } }) end
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(8)
assert_eq(starved_count(), 3, "полка посередине (0.2 из 0.1..0.3): половина построек")
""",
    "abundance_restores_after_hold": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 50, 20 } }); local B = mkbld({ sid = "farm_sid", farm = true })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(3)
assert_eq(starved_count(), 2, "не остановлены")
LV.food = 0.9
CYCLE(2, 0.0001)
assert_eq(starved_count(), 2, "откат раньше famine_hold_hours (мигание)")
CYCLE(3, 0.05)
assert_eq(starved_count(), 0, "изобилие: постройки не заработали")
assert_eq(A.pb.consumptionItems[1].amount, 50, "вход 1 не возвращён"); assert_eq(A.pb.consumptionItems[2].amount, 20, "вход 2 не возвращён")
assert_eq(A.pb.productionState, 2, "состояние не NORMAL"); assert_eq(B.pb.productionState, 2, "ферма не NORMAL")
assert_eq(nstore(), 0, "слот u3 не очищен")
assert(read_tmp("stock.log"):find("reason=stock", 1, true), "нет маркера U3 restore")
""",
    "reassert_vanilla_refill_and_flip": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 50 }, cap = 60 })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(A.pb.productionState, 0, "не STARVED")
A.pb.consumptionItems[1].amount = 30; A.pb.productionState = 2   -- ваниль подвезла и пересчитала
CYCLE(1)
assert_eq(A.pb.consumptionItems[1].amount, 20, "изъято сверх того, что влезет обратно (50 + 10 = cap 60)"); assert_eq(A.pb.productionState, 0, "состояние не удержано")
assert(KMM_Town.u3().flipped >= 1 and KMM_Town.u3().reassert >= 1, "счётчики flipped/reassert")
local rec = select(2, next(store()))
assert_eq(rec.a[1], 60, "изъятое не ограничено maxCapacity")
A.pb.consumptionItems[1].amount = 25; CYCLE(1)
assert_eq(A.pb.consumptionItems[1].amount, 25, "на потолке изъятого вход обнулён (подвоз уничтожен)")
A.pb.consumptionItems[1].amount = 0
LV.food = 0.9; CYCLE(4, 0.05)
assert_eq(A.pb.consumptionItems[1].amount, 60, "возврат не до maxCapacity")
""",
    "leave_town_rolls_back": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 40 } }); local B = mkbld({ inputs = { 7 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(starved_count(), 2, "не остановлены")
P.intown = false
CYCLE(1)
assert_eq(starved_count(), 0, "уход игрока: нет отката"); assert_eq(A.pb.consumptionItems[1].amount, 40, "вход не возвращён")
assert_eq(nstore(), 0, "слот не очищен")
assert(read_tmp("stock.log"):find("restore_all reason=leave n=2", 1, true), "нет маркера restore_all leave")
""",
    "unloaded_kept_and_adopted": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 40 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(A.pb.productionState, 0, "не STARVED")
A.unloaded = true; P.intown = false; CYCLE(1)
assert_eq(nstore(), 1, "выгруженная постройка потеряла запись изъятого")
A.unloaded = false; P.intown = true; LV.food = 0.0
CYCLE(2)
assert(KMM_Town.u3().adopted >= 1, "запись не подхвачена при возвращении")
LV.food = 0.9; CYCLE(4, 0.05)
assert_eq(A.pb.consumptionItems[1].amount, 40, "после возвращения вход не возвращён")
""",
    "copy_semantics_fallback": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 40 }, copies = true }); local B = mkbld({ inputs = { 40 }, copies = true })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(3)
assert(KMM_Town.u3().inputs_ok == false, "копия не распознана")
assert(read_tmp("stock.log"):find("inputs_write=0", 1, true), "нет маркера inputs_write=0")
for _, b in ipairs({ A, B }) do
  assert_eq(b.pb.productionState, 0, "состояние не STARVED"); assert_eq(b.productionMult, 1, "productionMult тронут")
  assert_eq(b.pb.real[1].amount, 40, "вход испорчен")
end
LV.food = 0.9; CYCLE(4, 0.05)
assert_eq(A.pb.productionState, 2, "состояние не возвращено")
""",
    "api_error_self_disables_and_rolls_back": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 40 } })
for sid, m in pairs(DATA.machines) do if m.item and m.cat ~= "food" then M = mkmachine(sid, 99); break end end   -- мастерская не от полки еды
W = mkchar({ work = M }); C = mkchar({}); S = mkchar({ trader = true, resident = true })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(A.pb.productionState, 0, "не STARVED")
BREAK_SPHERE = true; CYCLE(1)
assert(KMM_Town.disabled().famine, "famine не отключился"); assert(not KMM_Town.disabled().tick, "tick отключился")
assert_eq(A.pb.consumptionItems[1].amount, 40, "самоотключение без отката"); assert_eq(A.pb.productionState, 2, "состояние не возвращено")
assert(read_tmp("debug.log"):find("famine disabled until restart", 1, true), "нет причины в debug.log")
assert(read_tmp("stock.log"):find("U3 off", 1, true), "нет маркера U3 off")
local n = API.sphere; local c0 = KMM_Town.stats().cycles; CYCLE(3)
assert_eq(API.sphere, n, "сфера вызывается после отключения"); assert(KMM_Town.stats().cycles > c0, "цепочка встала")
assert(KMM_Town.stats().crafted >= 1, "цепочка мастерских не работает рядом с U3")
""",
    "building_limit_per_pass": SETUP + """
LV.food = 0.0
for i = 1, 200 do mkbld({ inputs = { 5 } }) end
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(30)
local u = KMM_Town.u3()
assert(u.seen <= 24, "разобрано больше famine_max_buildings: " .. u.seen)
assert(starved_count() <= 24, "остановлено больше лимита: " .. starved_count())
local n = 0; for _ in pairs(KMM_Town._rt.fh) do n = n + 1 end; assert(n <= 24, "fh растёт без лимита")
""",
    "no_conductor_slot_state_only": SETUP + """
KMM_Conductor.town_state = nil
LV.food = 0.0
local A = mkbld({ inputs = { 40 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(A.pb.productionState, 0, "без слота: нет STARVED"); assert_eq(A.pb.consumptionItems[1].amount, 40, "без слота дирижёра изъят вход")
LV.food = 0.9; CYCLE(4, 0.05)
assert_eq(A.pb.productionState, 2, "без слота: состояние не возвращено")
""",
    "config_off_unwinds": SETUP + """
CFG = { famine_enabled = true }
package.preload["town_config"] = function() return CFG end
LV.food = 0.0
local A = mkbld({ inputs = { 40 } }); local B = mkbld({ inputs = { 9 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(2)
assert_eq(starved_count(), 2, "не остановлены")
B.unloaded = true
KMM_Town._rt.fh = {}   -- как после перезагрузки: записи только в слоте
package.loaded["town_config"] = nil; CFG = { famine_enabled = false }
dofile(SCRIPT_PATH)   -- перезагрузка скрипта с выключенным флагом (cfg читается заново)
TICK(14, 2.5); CYCLE(1)
assert_eq(A.pb.consumptionItems[1].amount, 40, "выключенный флаг: вход не возвращён"); assert_eq(A.pb.productionState, 2, "состояние не возвращено")
assert_eq(nstore(), 1, "запись выгруженной постройки потеряна")
B.unloaded = false; CYCLE(1)
assert_eq(B.pb.consumptionItems[1].amount, 9, "выгруженная после загрузки не откатилась"); assert_eq(nstore(), 0, "слот не очищен")
assert(read_tmp("stock.log"):find("reason=config_off", 1, true), "нет маркера config_off")
""",
    "stale_anchor_not_used": SETUP + """
LV.food = 0.0
local A = mkbld({ inputs = { 40 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); TICK(3, 2.5)   -- цикл начат, стадии идут
P.getPosition = function() error("stale Character* from previous world") end
P2 = mkchar({ pc = true }); PCS = { P2 }   -- загружен другой сейв посреди цикла
CYCLE(3)
assert(not KMM_Town.disabled().famine, "famine взял старого персонажа")
assert_eq(A.pb.productionState, 0, "после смены персонажа U3 не работает")
""",
    "disabled_by_config": SETUP + """
package.preload["town_config"] = function() return { famine_enabled = false } end
LV.food = 0.0
local A = mkbld({ inputs = { 40 } })
dofile(SCRIPT_PATH)
TICK(14, 2.5); CYCLE(4)
assert_eq(API.sphere, 0, "сфера при famine_enabled=false"); assert_eq(A.pb.productionState, 2, "тронута при выключенном")
""",
}


def main():
    res = []
    for name, code in TESTS.items():
        tmp = tempfile.mkdtemp(prefix="kmm_u3_")
        lua = tt.Lua(tmp.replace("\\", "/"))
        try:
            lua.run(f'SCRIPT_PATH = "{tt.SCRIPT}"\n' + code.replace("install_lv()", BLD_STUBS + "\ninstall_lv()", 1), name)
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
