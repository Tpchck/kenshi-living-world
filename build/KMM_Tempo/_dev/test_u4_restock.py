"""U4 офлайн-тест KMM_Tempo: темп пополнения лавки (Platoon.traderInventoryRefreshTime) следует за богатством города.
python -I -X utf8 build/KMM_Tempo/_dev/test_u4_restock.py
Заглушки и загрузчик — из test_tempo.py (та же папка); реальные логи не трогаются."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_tempo as tt  # noqa: E402

RESULTS = tt.RESULTS
case = tt.case

PRE = tt.TILL_PRE + """
  -- платун торговца: метка пополнения TimeOfDay; o.copy — поле отдаётся копией (sol2 по значению), o.ro — запись игнорируется,
  -- o.days — метка не в часах мира (getTotalHours даёт в 24 раза меньше)
  function mkpl(t, o)
    o = o or {}
    local pl = { _t = t, speedOverride = 2, isResidentSquad = o.res, myBaseHomeTownData = o.home and { stringID = o.home } or nil }
    local k = o.days and 24 or 1
    local function tod(v) return { time = v, isUnset = function(self) return o.unset or false end,
      getTotalHours = function(self) return self.time / k end, addHours = function(self, h) self.time = self.time + h * k end } end
    if o.copy or o.ro then
      setmetatable(pl, { __index = function(self, key) if key == "traderInventoryRefreshTime" then return tod(rawget(self, "_t")) end end,
        __newindex = function(self, key, v) if key == "traderInventoryRefreshTime" then if not o.ro then rawset(self, "_t", v.time) end else rawset(self, key, v) end end })
    else pl.traderInventoryRefreshTime = tod(t) end
    return pl
  end
  function stamp(pl) return pl.traderInventoryRefreshTime.time end
  function restamp(pl, v) if rawget(pl, "traderInventoryRefreshTime") then pl.traderInventoryRefreshTime.time = v else rawset(pl, "_t", v) end end
  function ARM() TICK(10, 3, 0.01) end   -- проба единиц: >= 3 правдоподобных чтения на разных тактах; первая встреча без записи
  function trader(name, town, pl, f)
    f = f or {}; f.trader = true; f.town = town
    local ch = mkhuman(name, { money = 4000 })
    local rec = snap_char(ch, f)
    rec.pl, rec.pkey = pl, "pk_" .. name
    SNAP.by_pkey[rec.pkey] = { rec }
    return rec
  end
  POOR_T2 = function() MOOD.T2 = { pop = 40, pop0 = 100, unrest = 0.8, food = 0.05 }; STK.T2.siege = true end
"""


@case("U4 полки: осаждённый голодный город — пополнение всё реже (плавно, до ~64 ч); проба и первая встреча без записи; сдвиг раз на обновление")
def t_poor(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2()
      local pl = mkpl(HOURS, { home = "T2" }); trader("POOR", "T2", pl)
      local t0 = HOURS
      ARM()
      assert(stamp(pl) == t0, "first sight / probe: no write")
      assert(KMM_Tempo._restock.armed, "armed after plausible reads")
      local tv = HOURS; restamp(pl, tv); TICK(3, 3, 0.01)
      local d1 = stamp(pl) - tv
      assert(d1 > 5 and d1 < 15, "first step half-way (m 1 -> 0.625): " .. d1)
      TICK(20, 3, 0.01); DAY(2)
      assert(math.abs(stamp(pl) - tv - d1) < 1e-6, "one shift per vanilla refresh: " .. (stamp(pl) - tv))
      local last
      for _ = 1, 7 do DAY(1); local tw = HOURS; restamp(pl, tw); TICK(3, 3, 0.01); last = stamp(pl) - tw end
      assert(last > 46 and last <= 48.01, "settles at m=0.25 -> +48 h (cycle 64 h): " .. last)
      local lg = read_tmp("tempo.log")
      assert(lg:find("RESTOCK armed: 3 plausible reads"), "armed marker")
      assert(lg:find("RESTOCK shift Town Two: m=0%.%d+ %+"), "shift marker")
      assert(lg:find("RESTOCK day %d+: platoons=%d+ delayed=%d+ hastened=0 restamped=[1-9]%d* implausible=0 armed=true"), "day marker")
      assert(lg:find("RESTOCK probe Town Two: resident=true home=T2"), "probe marker")
      assert(lg:find("RESTOCK armed") < lg:find("RESTOCK shift"), "probe before first write")
      assert(not next(KMM_Tempo.status().disabled), "nothing disabled")
    """)


@case("U4 полки: процветающий торговый город — чаще (сдвиг назад, не больше x1.5); обычный город — ваниль")
def t_rich_normal(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      LVL.T1 = FLAT(2.0)
      local rp = mkpl(HOURS); trader("RICH", "T1", rp)
      local np = mkpl(HOURS); trader("NORM", "T3", np)
      ARM()
      local tv = HOURS; restamp(rp, tv); restamp(np, tv); TICK(3, 3, 0.01)
      local d = stamp(rp) - tv
      assert(d < -1 and d > -3, "rich: earlier (m 1 -> 1.15): " .. d)
      assert(stamp(np) == tv, "normal town untouched")
      local last
      for _ = 1, 6 do DAY(1); local tw = HOURS; restamp(rp, tw); TICK(3, 3, 0.01); last = stamp(rp) - tw end
      assert(last < -3.5 and last >= -16 * (1 - 1 / 1.3) - 0.01, "settles at m=1.3: " .. last)
    """)


@case("U4 полки: бродячий торговец, караван из другого города, не житель, отряд игрока, не торговец — не тронуты")
def t_scope(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2()
      local t0 = HOURS
      local a = mkpl(t0); trader("WAND", nil, a)
      local b = mkpl(t0, { home = "T1" }); trader("CARAVAN", "T2", b)
      local c = mkpl(t0, { res = false }); trader("VISIT", "T2", c)
      local d = mkpl(t0, { home = "T2" }); trader("PLAYER", "T2", d, { player = true })
      local e = mkpl(t0, { home = "T2" }); local re = trader("GUARD", "T2", e); re.trader = false
      local f = mkpl(t0, { unset = true }); trader("UNSET", "T2", f)
      local g = mkpl(t0, { res = true }); trader("RES", "T2", g)
      ARM()
      local tv = HOURS
      for _, p in ipairs({ a, b, c, d, e, f, g }) do restamp(p, tv) end
      DAY(3)
      for _, p in ipairs({ a, b, c, d, e, f }) do assert(stamp(p) == tv, "untouched: " .. stamp(p)) end
      assert(stamp(g) > tv, "resident flag without home -> town trader")
    """)


@case("U4 полки: выключили блок или весь модуль — несработавший сдвиг снят (ванильная метка); переставленную ванилью не трогаем")
def t_rollback(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2()
      local a = mkpl(HOURS, { home = "T2" }); trader("A", "T2", a)
      local b = mkpl(HOURS, { home = "T2", copy = true }); trader("B", "T2", b)
      ARM()
      local t0 = HOURS; restamp(a, t0); restamp(b, t0); TICK(3, 3, 0.01)
      assert(stamp(a) > t0 and stamp(b) > t0, "shifted (copy field too): " .. stamp(a) .. " " .. stamp(b))
      restamp(b, t0 + 10)                        -- ваниль успела обновить лавку B
      KMM_Tempo.cfg.restock = false
      TICK(4, 3, 0.01)
      assert(math.abs(stamp(a) - t0) < 1e-6, "A rolled back: " .. stamp(a))
      assert(stamp(b) == t0 + 10, "B vanilla value kept: " .. stamp(b))
      assert(read_tmp("tempo.log"):find("RESTOCK off: shifts rolled back %(1%)"), "off marker")
      KMM_Tempo.cfg.restock = true
      local c = mkpl(HOURS, { home = "T2" }); trader("C", "T2", c)
      TICK(4, 3, 0.01); local tc = HOURS; restamp(c, tc); TICK(3, 3, 0.01)
      assert(stamp(c) > tc, "C shifted")
      KMM_Tempo.cfg.enabled = false
      TICK(4, 3, 0.01)
      assert(math.abs(stamp(c) - tc) < 1e-6, "module off -> C rolled back: " .. stamp(c))
    """)


@case("U4 полки: метка не в часах мира -> restock выключается до первой записи")
def t_units(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2()
      local p = mkpl(HOURS, { home = "T2", days = true }); trader("DAYS", "T2", p)
      ARM(); local tv = HOURS; restamp(p, tv); DAY(2)
      assert(stamp(p) == tv, "no write with implausible units: " .. stamp(p))
      local d = KMM_Tempo.status().disabled
      assert(d.restock and d.restock:find("units implausible"), "restock disabled: " .. tostring(d.restock))
      assert(not d.till and not d.all, "others alive")
    """)


@case("U4 полки: начало игры (дни и часы не различить) — только ждём, ничего не пишем и не выключаемся")
def t_early(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2()
      HOURS = 30
      local p = mkpl(HOURS, { home = "T2" }); trader("EARLY", "T2", p)
      TICK(10, 3, 0.01); local tv = HOURS; restamp(p, tv); TICK(6, 3, 0.01)
      assert(stamp(p) == tv, "early game: no write: " .. stamp(p))
      assert(not KMM_Tempo._restock.armed and not KMM_Tempo.status().disabled.restock, "waiting, not disabled")
    """)


@case("U4 полки: загрузка сейва/новая сессия — сдвинутая метка не сдвигается повторно; запись не применилась -> restock выключается сам")
def t_reload_fail(lua, tmp):
    lua.load_module()
    lua.run(PRE + """
      POOR_T2(); LVL.T1 = FLAT(2.0)
      local p = mkpl(HOURS, { home = "T2" }); trader("P", "T2", p)
      local q = mkpl(HOURS); trader("Q", "T1", q)
      ARM(); local tv = HOURS; restamp(p, tv); restamp(q, tv); TICK(3, 3, 0.01)
      local sp, sq = stamp(p), stamp(q)
      assert(sp > tv and sq < tv, "shifted both ways")
      HOURS = HOURS - 10; TICK(10, 3, 0.01)                 -- загрузка более раннего сейва: метки уже сдвинуты
      assert(stamp(p) == sp and stamp(q) == sq, "load: no re-shift")
      assert(read_tmp("tempo.log"):find("RESTOCK time jump"), "jump marker")
      for _ = 1, 4 do KMM_Tempo._restock.pl = {}; TICK(10, 3, 0.01) end   -- новая сессия Lua: та же метка, пустая память
      assert(stamp(p) == sp and stamp(q) == sq, "new session: no re-shift (no restock on load)")
      local ro = mkpl(HOURS, { home = "T2", ro = true }); trader("RO", "T2", ro)
      TICK(4, 3, 0.01); restamp(ro, HOURS); TICK(6, 3, 0.01)
      local d = KMM_Tempo.status().disabled
      assert(d.restock and d.restock:find("refresh time write not applied"), "restock disabled: " .. tostring(d.restock))
      assert(not d.till and not d.all and not d.npc_hunger, "others alive")
      assert(read_tmp("tempo.log"):find("DISABLED restock"), "logged")
    """)


MINE = {"t_poor", "t_rich_normal", "t_scope", "t_rollback", "t_units", "t_early", "t_reload_fail"}


def main():
    if not os.path.exists(tt.DLL):
        print("SKIP: lua51.dll KenshiLua не найден")
        return 1
    for c in tt.CASES:
        if c.__name__ in MINE:
            c()
    bad = [r for r in RESULTS if not r[1]]
    for name, ok, msg in RESULTS:
        print(("OK   " if ok else "FAIL ") + name + ("" if ok else "\n     " + msg))
    print(f"{len(RESULTS) - len(bad)}/{len(RESULTS)} passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
