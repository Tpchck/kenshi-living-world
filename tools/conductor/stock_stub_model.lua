-- Заглушка модели складов для офлайн-харнесса sim_years.py (пока нет build/KMM_Stock/scripts/kmm_stock_model.lua).
-- Контракт тот же: M.init(stock, cstate, cfg), M.day(stock, cstate, day, emit); stock = cstate.stock.
-- Не баланс — только чтобы харнесс и метрики работали: город производит/ест, металл идёт от руды дирижёра.
local M = {}
local CATS = { "food", "metal", "weapons", "armor", "medicine", "drugs", "luxury", "scrap" }
M.CATS = CATS

function M.init(stock, cstate, cfg)
  stock.towns = stock.towns or {}
  for sid, i in pairs(cfg.town_info or {}) do
    local big = (i.kind == "city") and 1 or 0.3
    stock.towns[sid] = { goods = { food = 100 * big, metal = 40 * big + (i.mine and 30 or 0), weapons = 20 * big, armor = 15 * big,
                                   medicine = 10 * big, drugs = 5 * big, luxury = 10 * big, scrap = 10 * big } }
  end
end

function M.day(stock, cstate, day, emit)
  local ore = cstate.ore_share or 1
  for sid, t in pairs(stock.towns) do
    local g = t.goods
    g.food = math.max(0, g.food + 1.0 - 0.9 - (math.random() < 0.02 and 10 or 0))
    g.metal = math.max(0, g.metal + 0.5 * ore - 0.3)
    local make = math.min(g.metal, 0.2)
    g.metal = g.metal - make; g.weapons = g.weapons + make * 0.6 - 0.05; g.armor = g.armor + make * 0.4 - 0.04
    g.scrap = g.scrap + 0.02
    for _, c in ipairs(CATS) do if g[c] < 0 then g[c] = 0 end end
    if g.food <= 0 and not t.hungry then
      t.hungry = true
      emit({ type = "stock_shortage", town_sid = sid, text = "food ran out (stub)" })
    elseif g.food > 20 then t.hungry = nil end
  end
end

return M
