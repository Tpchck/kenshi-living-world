-- KMM_Diplo: мост диалога KenshiLua («run lua script» на репликах KMM Diplomacy) → scripts/init/kmm_diplo.lua.
-- Скрипт выполняется в своей песочнице: модуль виден только через общий _G. Вся работа и обработка ошибок — в KMM_Diplo.on_line.
local D = _G and _G.KMM_Diplo
if D and D.on_line and currentDialogue and currentDialogueLine then
  D.on_line(currentDialogue, currentDialogueLine)
end
