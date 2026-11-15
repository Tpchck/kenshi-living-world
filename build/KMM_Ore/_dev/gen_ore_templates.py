"""Генератор build/KMM_Ore/scripts/ore_templates.lua: все рудные узлы и машины итоговой цепочки модов (железо, медь).
python -I -X utf8 build/KMM_Ore/_dev/gen_ore_templates.py [--check]   (~10 с; только чтение данных игры, пишет один .lua)

Источник: слитый контекст tools/fast/ctx.py (ваниль → основа → WH, порядок final_lo.json). Рудная функциональность —
BUILDING_FUNCTIONALITY с итоговым значением «world resource mining» = 1 (IRON) или 3 (COPPER) (EnumsReference MiningResource).
Здание — BUILDING, у которого в ссылках «functionality» есть такая функциональность.
Класс: surface — природный узел (нет ссылки «construction»: игрок его не строит; Iron Rock, Iron/Copper Resource);
       mine — постройка (шахта, бур). auto — постройка с «Auto»/«Automated» в имени: работает без шахтёра от питания.
--check: не писать, только сравнить с текущим файлом (код возврата 1 при расхождении).
"""
import os
import sys

sys.path[:0] = [r"C:\KenshiModMap\tools", r"C:\KenshiModMap\tools\fast"]
import kmod  # noqa: E402
import ctx  # noqa: E402

OUT = r"C:\KenshiModMap\build\KMM_Ore\scripts\ore_templates.lua"
RES = {1: "iron", 3: "copper"}
TYPES = ("BUILDING", "BUILDING_FUNCTIONALITY")


def collect():
    lo, van, base, wh = ctx.load()
    M = {}
    for _, m, _ in van + base + wh:
        if m is None:
            continue
        m.items = [it for it in m.items if it.type_name in TYPES]
        kmod.apply(M, m)
    funcs = {s: RES[it.values.get("world resource mining")] for s, it in M.items()
             if it.type_name == "BUILDING_FUNCTIONALITY" and it.values.get("world resource mining") in RES}
    rows = []
    for s, it in M.items():
        if it.type_name != "BUILDING":
            continue
        fr = [r.target for r in it.refs.get("functionality", []) if r.target in funcs]
        if not fr:
            continue
        name = it.name or ""
        built = bool(it.refs.get("construction"))
        auto = built and ("auto" in name.lower())
        rows.append((s, "mine" if built or "drill" in name.lower() or "mine" in name.lower() else "surface",
                     funcs[fr[0]], auto, name))
    return funcs, sorted(rows)


def lua_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def render(funcs, rows):
    out = ["-- KMM_Ore: рудные шаблоны итоговой цепочки модов. Сгенерировано build/KMM_Ore/_dev/gen_ore_templates.py — не править руками.",
           "-- templates[stringID] = { класс, ресурс, auto }; funcs[stringID функциональности] = ресурс (запасная классификация в игре).",
           "return {", "  templates = {"]
    for s, cls, res, auto, name in rows:
        out.append(f"    [{lua_str(s)}] = {{ {lua_str(cls)}, {lua_str(res)}, {'true' if auto else 'false'} }},   -- {name}")
    out.append("  },")
    out.append("  funcs = {")
    for s in sorted(funcs):
        out.append(f"    [{lua_str(s)}] = {lua_str(funcs[s])},")
    out.append("  },")
    out.append("}")
    return "\n".join(out) + "\n"


def main():
    funcs, rows = collect()
    text = render(funcs, rows)
    if "--check" in sys.argv:
        cur = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        print("ore_templates.lua", "актуален" if cur == text else "РАСХОДИТСЯ", f"({len(rows)} зданий, {len(funcs)} функциональностей)")
        return 0 if cur == text else 1
    open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(f"{OUT}: {len(rows)} зданий ({sum(1 for r in rows if r[1] == 'surface')} surface, "
          f"{sum(1 for r in rows if r[3])} auto), {len(funcs)} функциональностей")
    return 0


if __name__ == "__main__":
    sys.exit(main())
