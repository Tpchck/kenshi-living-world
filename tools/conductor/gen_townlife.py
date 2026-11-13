"""TOWNLIFE: генератор build/KMM_Stock/scripts/kmm_townlife.lua - абстрактная карта неуникальных лавок по городам (для ротации по времени).
python -I -X utf8 tools/conductor/gen_townlife.py
Источники: build/KMM_Conductor/conductor.json (town_info), data/atlas_report.json ключ townlife.shops (доли гильдий/специализаций после сборки).
Лавка = (гильдия, специализация). Гильдия не меняется (физически владельца/здание сменить нельзя), меняется специализация.
Детерминированно (seed фиксирован)."""
import json
import os
import random
import re

ROOT = r"C:\KenshiModMap"
OUT = os.path.join(ROOT, "build", "KMM_Stock", "scripts", "kmm_townlife.lua")
ci = json.load(open(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), encoding="utf-8"))["town_info"]
sh = json.load(open(os.path.join(ROOT, "data", "atlas_report.json"), encoding="utf-8"))["townlife"]["shops"]
gshare = dict(sh["guild_share_pct_after"])
rest = max(0.0, 100.0 - sum(gshare.values()))
for i in range(1, 7):   # хвост «прочие гильдии» - шесть мелких, чтобы не было искусственной монополии
    gshare["Other-%d" % i] = rest / 6
guilds = list(gshare)
specs = list(sh["spec_share_pct_after"])
# служебные специализации ротацией не трогаются (бар, книги/лут), остальные - ротация
FIXED = {"bar", "books/loot"}
CAT = {"food": "food", "tools/mats": "metal", "weapons": "weapons", "armor": "armor", "medical": "med", "misc": "lux"}
PROTECT = re.compile(r"hub|shem|admag|mourn|ruin|prison|fort |cage|slave|bad teeth|world.?s end", re.I)   # узловые/квестовые: лавок в таблице нет
rng = random.Random(20261113)
N = int(sh.get("nonunique_shops_est", 582))
towns = [(sid, i) for sid, i in sorted(ci.items()) if not PROTECT.search(i.get("name", ""))]
w = [(6.0 if i["kind"] == "city" else 0.9) * (0.6 + rng.random() * 0.8) for _, i in towns]
tot = sum(w)
cnt = [max(0, round(N * x / tot)) for x in w]
shops = {}
gw = [gshare[g] for g in guilds]
sw = [sh["spec_share_pct_after"][s] for s in specs]
for (sid, i), n in zip(towns, cnt):
    if n <= 0:
        continue
    row = []
    for _ in range(n):
        row += [guilds.index(rng.choices(guilds, gw)[0]) + 1, specs.index(rng.choices(specs, sw)[0]) + 1]
    shops[sid] = row
lines = ["-- СГЕНЕРИРОВАНО tools/conductor/gen_townlife.py - не править руками. Карта неуникальных лавок (гильдия, специализация) по городам.",
         "return {"]
lines.append(" guilds = {%s}," % ", ".join(json.dumps(g, ensure_ascii=False) for g in guilds))
lines.append(" specs = {%s}," % ", ".join(json.dumps(s) for s in specs))
lines.append(" fixed = {%s}," % ", ".join("[%d] = true" % (specs.index(s) + 1) for s in FIXED if s in specs))
lines.append(" cat = {%s}," % ", ".join("[%d] = %s" % (specs.index(s) + 1, json.dumps(c)) for s, c in CAT.items() if s in specs))
lines.append(" shops = {")
for sid, row in shops.items():
    lines.append("  [%s] = {%s}," % (json.dumps(sid, ensure_ascii=False), ",".join(map(str, row))))
lines += [" },", "}"]
open(OUT, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("towns", len(shops), "shops", sum(len(r) // 2 for r in shops.values()), "->", OUT)
