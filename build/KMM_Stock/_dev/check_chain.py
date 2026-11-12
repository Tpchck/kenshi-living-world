"""LINK2: цепочка металл -> мастерские -> armor/weapons склада -> gear_shift фракции (правило дирижёра: gl=(armor+weapons)/2 по уровням,
-1 при gl<0.4, 0 при gl>0.65). Микро-сценарий на реальной модели склада (LuaJIT KenshiLua) + проверка json sim_years (criteria/хронич. дефицит).
python -I -X utf8 build/KMM_Stock/_dev/check_chain.py [json ...]   (по умолчанию tools/conductor/out/sim_15y_{2026,7,99}.json)
Что нужно добавить в sim_years.py для полной метрики: в stock_snap писать по фракциям среднее lvl armor/weapons и f.gear_shift ежедневно (сейчас только раз в год)."""
import json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_stock as T

SCEN = T.MODEL_PRE + """
  run_days(M, ST, CS, 0, 40, EMIT)
  local function lv(S, fid) local f = CS.F[fid]; local a, w, n = 0, 0, 0
    for t in pairs(f.towns) do if S.towns[t] and S.towns[t].city then a = a + M.level(S, t, "armor"); w = w + M.level(S, t, "weapons"); n = n + 1 end end
    return 0.5 * a / n + 0.5 * w / n end
  -- обеднённые арсеналы и мало металла у f1 (A, B — города)
  local function run(inject)
    local S2, C2 = copy(ST), copy(CS)
    for _, t in ipairs({ "A", "B" }) do local s = S2.towns[t]; s.q.armor = 0.15 * M.T(S2, s, "armor"); s.q.weapons = 0.15 * M.T(S2, s, "weapons"); s.q.metal = 0.1 * M.T(S2, s, "metal") end
    local shift, first_up, log = -1, nil, {}
    for d = 40, 40 + 59 do
      if inject and d >= 41 and d < 51 then for _, t in ipairs({ "A", "B" }) do M.add(S2, t, "metal", 0.35 * M.T(S2, S2.towns[t], "metal")) end end   -- игрок сбывает руду/металл
      M.day(S2, C2, d, EMIT)
      local g = lv(S2, "f1")
      if shift < 0 and g > 0.65 then shift = 0; first_up = first_up or (d - 40) end
      if (d - 40) % 10 == 9 then log[#log + 1] = string.format("%d:%.2f", d - 40 + 1, g) end
    end
    return table.concat(log, " ") .. " | gear_shift=" .. shift .. " up_after=" .. tostring(first_up)
  end
  error("RES " .. run(false) .. " || " .. run(true))
"""


def micro():
    lua = T.Lua(tempfile.mkdtemp(prefix="chain_").replace("\\", "/"))
    try:
        lua.run(SCEN)
    except AssertionError as e:
        s = str(e)
        i = s.find("RES ")
        if i < 0:
            raise
        a, b = s[i + 4:].split(" || ")
        return {"without_metal_inflow": a.strip(), "with_player_metal_10d": b.strip()}
    return None


def sims(paths):
    out = {}
    for p in paths:
        if not os.path.exists(p):
            continue
        j = json.load(open(p, encoding="utf-8"))
        c = j.get("criteria", {})
        st = j.get("stock", {})
        gs = c.get("gear_shift_share_by_year", {})
        out[os.path.basename(p)] = {
            "criteria_false": [k for k, v in c.items() if v is False],
            "chronic_deficit": st.get("chronic_deficit"), "chronic_overflow": st.get("chronic_overflow"),
            "gear_shift_share_y5_y15": [gs.get("5"), gs.get("10"), gs.get("15")],
            "model_error": st.get("model_error")}
    return out


if __name__ == "__main__":
    paths = sys.argv[1:] or [f"C:/KenshiModMap/tools/conductor/out/sim_15y_{s}.json" for s in (2026, 7, 99)]
    res = {"micro_gear_shift": micro(), "sim": sims(paths)}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open("C:/KenshiModMap/tools/conductor/out/chain_link2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
