-- KMM_Ore: рудные шаблоны итоговой цепочки модов. Сгенерировано build/KMM_Ore/_dev/gen_ore_templates.py — не править руками.
-- templates[stringID] = { класс, ресурс, auto }; funcs[stringID функциональности] = ресурс (запасная классификация в игре).
return {
  templates = {
    ["14521-rebirth.mod"] = { "surface", "iron", false },   -- Iron Rock
    ["2056-gamedata.base"] = { "mine", "iron", false },   -- Ore Mine
    ["2094-gamedata.base"] = { "mine", "iron", false },   -- Ore Mine II
    ["2095-gamedata.base"] = { "mine", "iron", false },   -- Ore Mine III
    ["2096-gamedata.base"] = { "mine", "iron", false },   -- Ore Drill
    ["2097-gamedata.base"] = { "mine", "iron", false },   -- Ore Drill II
    ["2098-gamedata.base"] = { "mine", "iron", true },   -- Ore Drill III (Automated)
    ["42248-gamedata.base"] = { "surface", "iron", false },   -- Iron Resource
    ["42249-gamedata.base"] = { "surface", "copper", false },   -- Copper Resource
    ["5008195-Soulbody.mod"] = { "mine", "iron", false },   -- SC Iron Ore Drill red
    ["5008196-Soulbody.mod"] = { "mine", "iron", false },   -- SC Iron Ore Drill green
    ["5008197-Soulbody.mod"] = { "mine", "iron", false },   -- SC Iron Ore Drill cyan
    ["5008198-Soulbody.mod"] = { "mine", "iron", false },   -- SC Iron Ore Drill purple
    ["5008199-Soulbody.mod"] = { "mine", "iron", true },   -- SC Auto Iron Ore Drill red
    ["5008200-Soulbody.mod"] = { "mine", "iron", true },   -- SC Auto Iron Ore Drill green
    ["5008201-Soulbody.mod"] = { "mine", "iron", true },   -- SC Auto Iron Ore Drill cyan
    ["5008202-Soulbody.mod"] = { "mine", "iron", true },   -- SC Auto Iron Ore Drill purple
    ["5008204-Soulbody.mod"] = { "mine", "copper", false },   -- SC Copper Ore Drill red
    ["5008205-Soulbody.mod"] = { "mine", "copper", false },   -- SC Copper Ore Drill green
    ["5008206-Soulbody.mod"] = { "mine", "copper", false },   -- SC Copper Ore Drill cyan
    ["5008207-Soulbody.mod"] = { "mine", "copper", false },   -- SC Copper Ore Drill purple
    ["5008208-Soulbody.mod"] = { "mine", "copper", true },   -- SC Auto Copper Ore Drill red
    ["5008209-Soulbody.mod"] = { "mine", "copper", true },   -- SC Auto Copper Ore Drill green
    ["5008210-Soulbody.mod"] = { "mine", "copper", true },   -- SC Auto Copper Ore Drill cyan
    ["5008211-Soulbody.mod"] = { "mine", "copper", true },   -- SC Auto Copper Ore Drill purple
    ["56977-Copper drill.mod"] = { "mine", "copper", false },   -- Copper Ore Drill
    ["56978-Copper drill.mod"] = { "mine", "copper", false },   -- Copper Ore Drill II
    ["56979-Copper drill.mod"] = { "mine", "copper", false },   -- Copper Ore Drill III
    ["99106-Boneyard Wolf.mod"] = { "surface", "copper", false },   -- Small Copper Resource
    ["99107-Boneyard Wolf.mod"] = { "surface", "iron", false },   -- Small Iron Resource
  },
  funcs = {
    ["1535160-AnimationOverhaul.mod"] = "iron",
    ["1869-gamedata.base"] = "iron",
    ["42251-gamedata.base"] = "copper",
    ["5008203-Soulbody.mod"] = "copper",
  },
}
