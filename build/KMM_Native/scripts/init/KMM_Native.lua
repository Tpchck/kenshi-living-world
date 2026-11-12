-- KMM_Native: thin Lua adapter over the native plugin (KMM_Native.dll, Lua module "kmm_native").
-- Nothing runs at load time except defining the table. The native module is looked up lazily on first use;
-- if it is missing (plugin disabled, wrong game version, no RE_Kenshi) every call is a harmless no-op.
--
--   KMM_Native.available              -> field (evaluated lazily on access): true if the native module is loaded and the world-state hook is installed
--   KMM_Native.ws_set(sid, true|false)-> true if the override was stored
--   KMM_Native.ws_clear(sid)          -> true if an override existed
--   KMM_Native.ws_clear_all()         -> number of overrides removed
--   KMM_Native.ws_get(sid)            -> true / false / nil (nil = no override)
--   KMM_Native.stats()                -> table {hooked, get_hook, queries_mapped, overrides, hits, unmapped_calls} or nil
--   KMM_Native.version()              -> string or nil
-- v2 (NATIVE2):
--   KMM_Native.getFactionForce(fid)   -> {squads, chars, active_squads, active_chars, unloaded_squads, unloaded_chars,
--                                         dead_squads, imprisoned_squads} or nil (read only, includes unloaded platoons; no tier data)
--   KMM_Native.unique_set(npc_sid, state) -> false (state 0 dead / 1 alive / 2 imprisoned). NOT implemented natively: no verified
--                                         registry write exists (docs\PLUGIN.md, NATIVE2 p.1); becomes live only if the module gets unique_set
--   KMM_Native.unique_get(npc_sid)    -> nil (same reason; 0/1/2 once the module provides it)
--   KMM_Native.orderSquad(...)        -> false (research only, docs\PLUGIN.md NATIVE2 p.3)
-- v2.3 (P4, B2): long-term character memory through the plugin (only the LongTerm overload, RVA 0x6732A0 / 0x6745F0):
--   KMM_Native.has_memory()           -> true if the DLL exports remember_lt (older DLL -> false)
--   KMM_Native.remember_lt(npc, who, tag) -> true | false, reason   (tag = CharacterPerceptionTags_LongTerm number 1..10)
--   KMM_Native.memory_lt(npc, who, tag)   -> true | false | nil, reason
-- Overrides live in memory only (not in the save): the caller re-applies them after loading.
local M = {}
local state = { tried = false, mod = nil, dead = false }

local function try_load()
  if state.tried then return state.mod end
  state.tried = true
  local ok, mod = pcall(require, "kmm_native")
  if ok and type(mod) == "table" then
    state.mod = mod
    return mod
  end
  -- KenshiLua may not have been ready when the plugin started: open the module straight from the loaded DLL
  local okp, loader = pcall(function()
    return package and package.loadlib and package.loadlib("KMM_Native.dll", "luaopen_kmm_native")
  end)
  if okp and type(loader) == "function" then
    local okc, m2 = pcall(loader)
    if okc and type(m2) == "table" then
      state.mod = m2
      return m2
    end
  end
  return nil
end

-- calls fn(mod) under pcall; the first error disables the adapter (and only the adapter)
local function call(fn, default)
  if state.dead then return default end
  local mod = try_load()
  if not mod then return default end
  local ok, a = pcall(fn, mod)
  if not ok then
    state.dead = true
    return default
  end
  if a == nil then return default end
  return a
end

function M.is_available()
  return call(function(m) return m.ws_hook_active() == true end, false)
end

function M.ws_set(sid, value)
  if type(sid) ~= "string" or type(value) ~= "boolean" then return false end
  return call(function(m) return m.ws_set(sid, value) == true end, false)
end

function M.ws_clear(sid)
  if type(sid) ~= "string" then return false end
  return call(function(m) return m.ws_clear(sid) == true end, false)
end

function M.ws_clear_all()
  return call(function(m) return m.ws_clear_all() end, 0)
end

function M.ws_get(sid)
  if type(sid) ~= "string" then return nil end
  local v = call(function(m) return m.ws_get(sid) end, nil)
  return v
end

-- NATIVE2. The module is asked only if it really has the function (older DLL / disabled feature -> no-op).
function M.getFactionForce(fid)
  if type(fid) ~= "string" then return nil end
  return call(function(m)
    if type(m.faction_force) ~= "function" then return nil end
    return m.faction_force(fid)
  end, nil)
end

function M.unique_set(npc_sid, state)
  if type(npc_sid) ~= "string" or (state ~= 0 and state ~= 1 and state ~= 2) then return false end
  return call(function(m)
    if type(m.unique_set) ~= "function" then return false end
    return m.unique_set(npc_sid, state) == true
  end, false)
end

function M.unique_get(npc_sid)
  if type(npc_sid) ~= "string" then return nil end
  return call(function(m)
    if type(m.unique_get) ~= "function" then return nil end
    return m.unique_get(npc_sid)
  end, nil)
end

function M.orderSquad(platoon, kind, target)
  return false   -- no verified call template (docs\PLUGIN.md NATIVE2 p.3)
end

function M.has_memory()
  return call(function(m) return type(m.remember_lt) == "function" end, false)
end

-- two results (ok, reason); a raised error disables the adapter like every other call
local function call2(name, a, b, c)
  if state.dead then return nil, "adapter off" end
  local mod = try_load()
  if not mod then return nil, "no module" end
  if type(mod[name]) ~= "function" then return nil, "no native " .. name end
  local ok, r, why = pcall(mod[name], a, b, c)
  if not ok then state.dead = true; return nil, tostring(r) end
  return r, why
end

function M.remember_lt(npc, who, tag)
  if npc == nil or who == nil or type(tag) ~= "number" then return false, "bad args" end
  local r, why = call2("remember_lt", npc, who, tag)
  return r == true, why
end

function M.memory_lt(npc, who, tag)
  if npc == nil or who == nil or type(tag) ~= "number" then return nil, "bad args" end
  return call2("memory_lt", npc, who, tag)
end

function M.stats()
  return call(function(m) return m.ws_stats() end, nil)
end

function M.version()
  return call(function(m) return m.version() end, nil)
end

setmetatable(M, { __index = function(_, k)
  if k == "available" then return M.is_available() end
  return nil
end })

_G.KMM_Native = M

-- Смоук-тест (tools\smoke.py --world): только если smoke.py положил C:/KenshiModMap/logs/smoke_load.txt (имя сейва).
-- В обычной игре файла нет: одна проверка io.open при загрузке скрипта, больше ничего.
do
  local okf, fh = pcall(io.open, "C:/KenshiModMap/logs/smoke_load.txt", "r")
  if okf and fh then
    local name = (fh:read("*l") or ""):gsub("%s+$", ""); fh:close()
    local t0, done = nil, false
    if name ~= "" and Events and Events.on then
      local function guarded(fn) return function(...) if done then return end; local ok = pcall(fn, ...); if not ok then done = true end end end
      Events.on("MyGUI::Gui::eventFrameStart", guarded(function()
        if done then return end
        local ok = pcall(function()
          t0 = t0 or os.clock()
          if os.clock() - t0 < 8 then return end   -- дать меню дорисоваться
          done = true
          local mod = try_load()
          local r = mod and mod.smoke_load and mod.smoke_load(name)
          pcall(os.remove, "C:/KenshiModMap/logs/smoke_load.txt")   -- одноразово: следующий запуск игры обычный
          if KenshiLua and KenshiLua.log then KenshiLua.log("[KMM_Native] smoke_load(" .. name .. ") -> " .. tostring(r)) end
        end)
        if not ok then done = true end
      end))
    end
  end
end
