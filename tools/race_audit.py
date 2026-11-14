r"""Аудит рас (2026-11-14, плейтест: «связка рас модовых с ванильными, без дублей, все со всеми»). Только чтение.
python -I -X utf8 tools\race_audit.py  -> печать + data\race_audit.json

Для каждой расы в игре: мод, основа (ванильная раса с тем же телом: меш/анимации/лимиты редактора), дубли (одинаковые поля и ссылки).
Родные списки движка, где участвуют расы: условия диалогов (my race / my subrace / target race / no target race), запреты вещей
(races / races exclude), бонус урона (race damage), группы рас (RACE_GROUP races), фракции (races). Для модовой расы с ванильной
основой считаем «пропуски»: список содержит основу, но не её. Это кандидаты для потока связки (ничего не пишет)."""
import collections
import json
import os
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmm_build  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

BODY_KEYS = ("male mesh", "female mesh", "editor limits")
LIST_CATS = {"DIALOGUE": ("my race", "my subrace", "target race", "no target race"),
             "DIALOGUE_LINE": ("my race", "my subrace", "target race", "no target race"),
             "ARMOUR": ("races", "races exclude"), "WEAPON": ("race damage",), "CROSSBOW": ("race damage",),
             "ITEM": ("races", "races exclude"), "RACE_GROUP": ("races",), "FACTION": ("races",)}


def norm(v):
    return str(v or "").strip().lower().replace("/", "\\")


def main():
    ctx = kmm_build.Ctx()
    M = ctx.M
    van = {n for n, _, _ in ctx.van}
    races = ctx.all("RACE")
    is_van = {r.sid: ctx.origin.get(r.sid) in van for r in races}
    body = {}
    for r in races:
        anims = tuple(sorted(x.target for x in r.refs.get("animation files", [])))
        body[r.sid] = (norm(r.values.get("male mesh")), norm(r.values.get("editor limits")), anims)
    # основа: ванильная раса с тем же мужским мешем (иначе — те же лимиты редактора; иначе — те же анимации)
    van_by = collections.defaultdict(list)
    for r in races:
        if is_van[r.sid]:
            van_by[("m", body[r.sid][0])].append(r)
            van_by[("e", body[r.sid][1])].append(r)
            van_by[("a", body[r.sid][2])].append(r)
    base = {}
    for r in races:
        if is_van[r.sid]:
            continue
        for k, idx in (("m", 0), ("e", 1), ("a", 2)):
            key = body[r.sid][idx]
            if key and van_by.get((k, key)):
                cands = van_by[(k, key)]
                # из нескольких — та, чьё имя ближе (общий первый токен)
                tok = (r.name or "").split(" ")[0].lower()
                best = next((c for c in cands if (c.name or "").split(" ")[0].lower() == tok), cands[0])
                base[r.sid] = (best.sid, k)
                break
    # дубли: одинаковые значения и ссылки (без имени)
    sig = collections.defaultdict(list)
    for r in races:
        vals = tuple(sorted((k, norm(v)) for k, v in r.values.items() if k not in ("name",)))
        refs = tuple(sorted((c, tuple(sorted((x.target, x.v0, x.v1, x.v2) for x in xs))) for c, xs in r.refs.items()))
        sig[(vals, refs)].append(r)
    dupes = [[(r.sid, r.name, ctx.origin.get(r.sid)) for r in g] for g in sig.values() if len(g) > 1]
    # родные списки, где участвуют расы
    usage = collections.defaultdict(collections.Counter)   # race sid -> {type.cat: n}
    lists = []   # (item, cat, set targets)
    for it in M.values():
        cats = LIST_CATS.get(it.type_name)
        if not cats or not ctx.in_game(it.sid):
            continue
        for c in cats:
            xs = it.refs.get(c)
            if xs:
                tg = {x.target for x in xs}
                lists.append((it, c, tg))
                for t in tg:
                    usage[t][it.type_name + "." + c] += 1
    gaps = collections.Counter()
    gap_by_race = collections.defaultdict(collections.Counter)
    for it, c, tg in lists:
        for rs, (bs, _) in base.items():
            if bs in tg and rs not in tg:
                gaps[it.type_name + "." + c] += 1
                gap_by_race[rs][it.type_name + "." + c] += 1
    rows = []
    for r in sorted(races, key=lambda r: (not is_van[r.sid], r.name or "")):
        b = base.get(r.sid)
        rows.append({"sid": r.sid, "name": r.name, "mod": ctx.origin.get(r.sid), "vanilla": is_van[r.sid],
                     "base": M[b[0]].name if b else None, "base_sid": b[0] if b else None, "base_by": b[1] if b else None,
                     "playable": bool(r.values.get("playable", True)), "robot": bool(r.values.get("is robot", False)),
                     "used_in": dict(usage.get(r.sid, {})), "gaps": dict(gap_by_race.get(r.sid, {}))})
    out = {"_doc": __doc__, "races": len(races), "vanilla": sum(is_van.values()), "mod": len(races) - sum(is_van.values()),
           "mod_with_base": len(base), "dupes": dupes, "gaps_total": dict(gaps), "rows": rows}
    json.dump(out, open(r"C:\KenshiModMap\data\race_audit.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"рас в игре {len(races)}: ваниль {out['vanilla']}, моды {out['mod']}, с ванильной основой {len(base)}")
    print("дубли:", len(dupes))
    for g in dupes[:15]:
        print("   ", g)
    print("пропуски в родных списках (модовая подраса не вписана рядом с основой):", dict(gaps))
    print("модовые расы без основы:")
    for x in rows:
        if not x["vanilla"] and not x["base"]:
            print(f"    {x['name']!s:40} {x['mod']!s:45} used {sum(x['used_in'].values())}")
    print("модовые с основой (топ по пропускам):")
    for x in sorted((x for x in rows if x["gaps"]), key=lambda x: -sum(x["gaps"].values()))[:40]:
        print(f"    {x['name']!s:38} <- {x['base']!s:26} ({x['base_by']}) пропусков {sum(x['gaps'].values()):4d} {x['gaps']}")


if __name__ == "__main__":
    main()
