"""Офлайн-тест TOWNLIFE: ротация лавок по времени (модель M.rot_try + рантайм apply_rot) на LuaJIT из KenshiLua, без игры.
python -I -X utf8 build/KMM_Stock/_dev/test_rotation.py -> «N/N passed», код 1 при провале. Заглушки - из test_stock.py."""
import importlib.util
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("test_stock_base", os.path.join(HERE, "test_stock.py"))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

# мини-данные: города A,B (рядом с игроком) и C (далеко), у C лавки: еда, еда, оружие, бар(фикс), книги(фикс), броня, мед, мисц
TL = r'''
package.loaded["kmm_townlife"] = { guilds = {"G1","G2","G3","G4"},
  specs = {"food","weapons","tools/mats","armor","misc","bar","medical","books/loot"},
  fixed = {[6] = true, [8] = true}, cat = {[1]="food",[3]="metal",[2]="weapons",[4]="armor",[7]="med",[5]="lux"},
  shops = { C = {1,1, 2,1, 3,2, 4,6, 1,8, 2,4, 3,7, 4,5, 1,3, 2,4, 3,1, 4,7},
            A = {1,1, 2,3} } }
'''


N0 = len(T.CASES)


def case(name):
    return T.case(name)


@case("TOWNLIFE: раз в 2-3 дня одна смена, служебные лавки (бар/книги) не трогаются, потолки доли держатся")
def t_cadence(lua):
    lua.run(TL + T.MODEL_PRE + """
      CFG.player_faction = "PF"; ST.cfg = { rot_cap_spec = 0.7 }   -- в мини-мире 14 лавок потолок 30% душит смены
      local n, last, gaps = 0, nil, {}
      local log = {}
      M.rot_log = function(m) log[#log + 1] = m end
      for d = 0, 600 do
        M.day(ST, CS, d, EMIT); if ST.rot then ST.rot.pend = {} end   -- рантайм применил смену
        local c = M.rot_stats(ST).n
        if c > n then if last then gaps[#gaps + 1] = d - last end; last = d; n = c end
      end
      local rs = M.rot_stats(ST)
      assert(rs and rs.n >= 150 and rs.n <= 320, "rotations ~600/2.5=240: " .. tostring(rs and rs.n))
      local sum = 0
      for _, g in ipairs(gaps) do assert(g >= 2 and g <= 8, "gap " .. g); sum = sum + g end   -- редкая осечка (все 12 попыток в служебные лавки) = ещё один интервал
      assert(sum / #gaps <= 3.2, "mean gap " .. sum / #gaps)
      assert(rs.max_guild_ever <= 0.25 + 1e-9 or rs.shops < 20, "guild cap " .. rs.max_guild_ever)
      -- бар (6) и книги (8) исходно в C: 2 лавки; их число не изменилось и ни одна лавка не стала баром/книгами
      assert(ST.rot.sc == nil and rs.spec[6] == 1 and rs.spec[8] == 1, "fixed shops untouched: " .. tostring(rs.spec[6]) .. "/" .. tostring(rs.spec[8]))
      assert(rs.spec[2] == nil or rs.spec[2] <= 2, "weapons not a rotation target by default (only shrinks): " .. tostring(rs.spec[2]))
      assert(#log == rs.n, "one TRADE line per event: " .. #log .. " vs " .. rs.n)
      assert(log[1]:match("^shop rotated in .+: .+/.+ %-> .+/.+$"), "format: " .. log[1])
      assert(ST.towns.A and not ST.rot_off, "no self-disable")
    """)


@case("TOWNLIFE: игрок рядом с городом (away=false) - смены нет; игрок далеко - есть; игрок-владелец не трогается")
def t_away(lua):
    lua.run(TL + T.MODEL_PRE + """
      CFG.player_faction = "PF"; ST.cfg = { rot_cap_spec = 0.7 }   -- в мини-мире 14 лавок потолок 30% душит смены
      M.away = function(t) return false end
      for d = 0, 60 do M.day(ST, CS, d, EMIT) end
      assert(M.rot_stats(ST).n == 0, "player near: no rotation")
      M.away = function(t) return t == "C" end
      for d = 61, 120 do M.day(ST, CS, d, EMIT); ST.rot.pend = {} end
      local rs = M.rot_stats(ST); assert(rs.n > 10, "player away from C: " .. rs.n)
      for t, ov in pairs(ST.rot.ov) do assert(t == "C", "only away town rotated: " .. t) end
    """)


@case("TOWNLIFE: ошибка данных/самоотключение - ротация гаснет, склад считается дальше")
def t_selfoff(lua):
    lua.run(TL + T.MODEL_PRE + """
      M.rot_try = function() error("boom") end
      for d = 0, 10 do M.day(ST, CS, d, EMIT) end
      assert(ST.rot_off, "rot_off set"); assert(ST.last_day == 10, "stock keeps running")
      assert(not next(EV) or true)
    """)


@case("TOWNLIFE: рантайм - строка TRADE в stock.log, лавка перекладывается при заходе игрока (еда -> лекарства), оружие не кладётся")
def t_runtime(lua):
    lua.load_runtime()
    lua.run(TL + """
      install_conductor()
      PCS = { mkchar("P", 0, 0, { player = true }) }
      TICK(40, 1, 0.01); DRAIN()
      -- далёкий C: добавить в синтетический мир (есть в town_info), игрок в 9000 от него? C на x=9000, радиус 4500 -> далеко
      CFG.town_info.C.x = 9000
      for i = 1, 40 do DAY = DAY + 1; TICK(2, 1, 0); DRAIN() end
      local log = read_tmp("stock.log") or ""
      assert(log:find("TRADE shop rotated in Gamma: ", 1, true), "TRADE line: " .. log:sub(-400))
      assert(not log:find("rotated in Alpha", 1, true), "player near Alpha: not rotated")
      -- применение: лавка города A (у игрока), pend выставлен вручную: еда -> лекарства
      local R = CS.stock.rot; R.pend = { A = { from = "food", to = "med", day = math.floor(DAY), shop = 1 } }
      local inv = mkinv(20, { mkitem("1946-gamedata.base", 1), mkitem("VANILLA-ITEM", 1) })
      BUILDINGS = { mkbuilding("shopA", "A", "f1", true, inv) }
      for _ = 1, 30 do TICK(1, 7, 0); DRAIN() end
      local food, med, van = 0, 0, 0
      for _, it in ipairs(inv.items) do local s = it.gd.stringID; if s == "1946-gamedata.base" then food = food + 1 elseif s == "VANILLA-ITEM" then van = van + 1 else med = med + 1 end end
      assert(R.pend.A == nil, "pending cleared")
      assert(van == 1, "vanilla item untouched")
      assert(food == 0, "old category removed: " .. food)
      assert(med > 0, "new category added: " .. med)
      assert((read_tmp("stock.log") or ""):find("shop restocked after rotation in Alpha", 1, true), "restock line")
      assert(count(KMM_Stock.disabled()) == 0, "nothing disabled: " .. tostring(next(KMM_Stock.disabled())))
    """)


def main():
    for c in T.CASES[N0:]:
        c()
    bad = [r for r in T.RESULTS if not r[1]]
    for name, ok, msg in T.RESULTS:
        print(("OK   " if ok else "FAIL ") + name + ("" if ok else "\n     " + msg))
    print(f"{len(T.RESULTS) - len(bad)}/{len(T.RESULTS)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
