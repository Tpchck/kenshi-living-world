"""Аудит сборки по родам ошибок теста 2026-11-13 (только чтение). python tools\\audit_classes.py -> печать + data\\audit_classes.json
A. ассеты вещей в пулах KMM: файлы mesh/texture/icon не найдены ни в data, ни в активных модах (чёрная текстура / невидимка)
B. утечка WH-экзотики: персонажи не-WH фракций с imperial/chaos/xenos вещами в одежде после KMM_Wardrobe
C. анимации рас: раса используется персонажами, меш/скелет человеческий, а список animation files заметно короче, чем у Greenlander
D. перекосы спавна: в биоме один шаблон (nests / homeless spawns) с весом > 8x медианы и >= 100
"""
import collections
import glob
import json
import os
import re
import statistics
import sys

sys.path.insert(0, r"C:\KenshiModMap\tools")
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmod  # noqa: E402
import kmm_build  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
G = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
ASSET_EXT = (".mesh", ".dds", ".png", ".tga", ".jpg")


def main():
    ctx = kmm_build.Ctx()
    M = dict(ctx.M)
    for d in sorted(os.listdir(r"C:\KenshiModMap\build")):
        p = os.path.join(r"C:\KenshiModMap\build", d, d + ".mod")
        if d.startswith("KMM_") and os.path.exists(p):
            kmod.apply(M, kmod.read(p))
    out = {}
    # ---- A: индекс имён файлов (Ogre ищет ресурс по имени во всех группах)
    cfg = [l.strip() for l in open(G + r"\data\mods.cfg", encoding="utf-8", errors="replace") if l.strip()]
    dirs = {os.path.basename(p): os.path.dirname(p) for p in glob.glob(W + r"\*\*.mod") + glob.glob(G + r"\mods\*\*.mod")}
    roots = [G + r"\data"] + [dirs[m] for m in cfg if m in dirs]
    names = set()
    for r in set(roots):
        for dp, _, fs in os.walk(r):
            names |= {f.lower() for f in fs}
    cat = json.load(open(r"C:\KenshiModMap\data\catalog.json", encoding="utf-8"))["items"]
    miss = []
    for x in cat:
        it = M.get(x["sid"])
        if it is None:
            continue
        bad = []
        for k, v in it.values.items():
            if isinstance(v, str) and v.strip().lower().endswith(ASSET_EXT):
                n = v.replace("/", "\\").split("\\")[-1].strip().lower()
                if n and n not in names:
                    bad.append(f"{k}={n}")
        if bad:
            miss.append({"sid": x["sid"], "name": x["name"], "mod": x["mod"], "group": x["group"], "missing": bad[:4]})
    out["A_missing_assets"] = miss
    # ---- B: экзотика у не-WH
    wh = json.load(open(r"C:\KenshiModMap\rules\streams\wardrobe.json", encoding="utf-8"))["wh_origin_factions"]
    whn = {n for v in wh.values() for n in v}
    org = {x["sid"]: x["origin"] for x in cat}
    wmod = kmod.read(r"C:\KenshiModMap\build\KMM_Wardrobe\KMM_Wardrobe.mod")
    fac_of, fac_all = {}, {}
    wj = json.load(open("C:/KenshiModMap/rules/streams/wardrobe.json", encoding="utf-8"))
    UR = wj.get("unique_relics", {})
    uniq = [re.compile(e[0], re.I) for e in (UR.get("by_name") or [])]
    ufac = set((UR.get("by_faction") or {}).keys()); uchars = set()   # задуманные реликты уников (Феникс, Валтена, Тенгу...)
    for sq in M.values():
        if sq.type_name in ("SQUAD_TEMPLATE", "UNIQUE_SQUAD_TEMPLATE") and sq.refs.get("faction") and sq.refs["faction"][0].target in M:
            fn = M[sq.refs["faction"][0].target].name
            for c in ("leader", "squad", "squad2"):
                for r in sq.refs.get(c, []):
                    fac_of.setdefault(r.target, fn)
                    fac_all.setdefault(r.target, set()).add(fn)
                    if sq.type_name == "UNIQUE_SQUAD_TEMPLATE" and fn in ufac:
                        uchars.add(r.target)
    leak = collections.Counter()
    for it in wmod.items:
        if it.type_name != "CHARACTER":
            continue
        fn = fac_of.get(it.sid)
        if fn is None or fn in whn or (fac_all.get(it.sid, set()) & whn) or it.sid in uchars or (M.get(it.sid) is not None and M[it.sid].values.get("unique") is True and fn in ufac) or any(u.search(it.name or "") for u in uniq):   # персонаж и WH-отряда (каннибалы Пожирателя) - лор мода
            continue
        for r in it.refs.get("clothing", []):
            # вес <= 5 — задуманный реликт («один на миллион», bandit_relic), не утечка
            if org.get(r.target) in ("imperial", "chaos", "xenos") and r.v0 != 2147483647 and r.v1 > 5:
                leak[fn] += 1
    out["B_exotic_leak"] = leak.most_common()
    # ---- C: анимации рас
    used = collections.Counter(r.target for c in M.values() if c.type_name == "CHARACTER" for r in c.refs.get("race", []))
    gl = next(i for i in M.values() if i.type_name == "RACE" and i.name == "Greenlander")
    gl_af = {r.target for r in gl.refs.get("animation files", [])}
    short = []
    for rc in M.values():
        if rc.type_name != "RACE" or not used.get(rc.sid):
            continue
        mesh = str(rc.values.get("male mesh", "")).lower()
        af = {r.target for r in rc.refs.get("animation files", []) if r.v0 != 2147483647}
        human = "human_male.mesh" in mesh or "human" in mesh
        if (human or af) and len(af) < 0.8 * len(gl_af):
            short.append({"sid": rc.sid, "name": rc.name, "mod": ctx.origin.get(rc.sid, "KMM"), "chars": used[rc.sid], "anim_files": len(af),
                          "mesh": mesh[-60:], "missing_vs_greenlander": len(gl_af - af)})
    out["C_race_anim_short"] = sorted(short, key=lambda e: -e["chars"])
    # ---- D: перекосы спавна
    sk = []
    for bg in M.values():
        if bg.type_name != "BIOME_GROUP":
            continue
        for cat_ in ("nests", "homeless spawns"):
            ws = [(r.v0, r.target) for r in bg.refs.get(cat_, []) if 0 < r.v0 < 2147483647]
            if len(ws) < 4:
                continue
            med = statistics.median(w for w, _ in ws)
            for w, t in ws:
                if w >= 100 and w > 8 * med:
                    sk.append({"biome": bg.name, "cat": cat_, "target": M[t].name if t in M else t, "weight": w, "median": med})
    out["D_spawn_skew"] = sorted(sk, key=lambda e: -e["weight"] / max(1, e["median"]))
    json.dump(out, open(r"C:\KenshiModMap\data\audit_classes.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"A вещи в пулах с ненайденными файлами: {len(miss)}")
    for e in miss[:12]:
        print("   ", e["name"], "|", e["mod"], "|", e["missing"])
    print(f"B утечка экзотики к не-WH: {sum(leak.values())} ссылок, фракций {len(leak)}: {leak.most_common(6)}")
    print(f"C расы с коротким списком анимаций: {len(short)}")
    for e in out["C_race_anim_short"][:12]:
        print("   ", e["name"], "|", e["mod"], "| персонажей", e["chars"], "| файлов", e["anim_files"], "| нет", e["missing_vs_greenlander"], "|", e["mesh"])
    print(f"D перекосы спавна: {len(sk)}")
    for e in out["D_spawn_skew"][:12]:
        print("   ", e["biome"], e["cat"], e["target"], e["weight"], "медиана", e["median"])


if __name__ == "__main__":
    main()
