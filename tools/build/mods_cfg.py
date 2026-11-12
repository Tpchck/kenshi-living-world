"""Генератор Kenshi/data/mods.cfg + автопроверка перед сборкой (владелец — интегратор).

Порядок: основа (официальный LO, tools/fast/lo.py) → WH-слой → EXTRA → наши KMM_* (rules/load_order.json).
Проверки (любая ошибка останавливает сборку):
  1) каждый мод есть на диске (Workshop, Kenshi/mods или build/ для своих);
  2) у каждого есть все зависимости — из заголовка .mod и rules/excluded_mods.json → required_items — и они стоят раньше;
  3) нет модов, исключённых по аудиту (rules/excluded_mods.json → mods);
  4) никто, кроме владельцев (Community Part Map и её фикс), не поставляет файлы тела основы (маски, скелеты) — Ogre ищет по имени;
  5) реестр лаунчера (data/__mods.list) знает все моды на диске — иначе лаунчер сам допишет новые подписки в конец mods.cfg
     (так вернулся Deathstroke и попали Crafting Redux / RobolimbNPCs 2026-11-12); при записи недостающие имена дописываются в реестр.
python -I -X utf8 tools/build/mods_cfg.py check        # проверить сгенерированный список и живой mods.cfg (ничего не пишет)
python -I -X utf8 tools/build/mods_cfg.py write        # проверить и записать mods.cfg (+ бэкап, + реестр лаунчера)
"""
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
CFG = os.path.join(GAME, "data", "mods.cfg")
REG = os.path.join(GAME, "data", "__mods.list")
VANILLA = {"gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"}
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
import kmod  # noqa: E402


def rules():
    ex = json.load(open(os.path.join(ROOT, "rules", "excluded_mods.json"), encoding="utf-8"))
    lo = json.load(open(os.path.join(ROOT, "rules", "load_order.json"), encoding="utf-8"))
    return ex, lo


def mod_paths():
    """имя .mod → путь: Workshop, затем Kenshi/mods, затем build/ (свои, ещё не установленные)."""
    p = {}
    for d in os.listdir(W):
        for f in glob.glob(os.path.join(W, d, "*.mod")):
            p.setdefault(os.path.basename(f), f)
    for f in glob.glob(os.path.join(GAME, "mods", "*", "*.mod")):
        p[os.path.basename(f)] = f
    for f in glob.glob(os.path.join(ROOT, "build", "KMM_*", "KMM_*.mod")):
        p[os.path.basename(f)] = f   # свои — из build/ (то, что будет установлено)
    return p


def merge_state(lines, paths=None):
    """KMM_Merged (rules/merge.json + rules/merged_manifest.json): → dict(active, ok, stale, errors, warns).
    ok — исходники с совпавшим md5 (выключаются), stale — изменились/пропали (остаются в mods.cfg отдельными модами)."""
    st = {"active": False, "ok": [], "stale": [], "errors": [], "warns": []}
    fl = os.path.join(ROOT, "rules", "merge.json")
    try:
        if not json.load(open(fl, encoding="utf-8")).get("enabled"):
            return st
    except (OSError, ValueError):
        return st
    mp = os.path.join(ROOT, "rules", "merged_manifest.json")
    mf = os.path.join(ROOT, "build", "KMM_Merged", "KMM_Merged.mod")
    if not os.path.exists(mp) or not os.path.exists(mf):
        st["warns"].append("слияние включено, но KMM_Merged не собран (tools/build/merge_mods.py --write): моды остаются отдельно")
        return st
    man = json.load(open(mp, encoding="utf-8"))
    if _md5(mf) != man["merged_md5"]:
        st["errors"].append("build/KMM_Merged/KMM_Merged.mod не совпадает с rules/merged_manifest.json (пересоберите merge_mods.py --write)")
        return st
    paths = paths or mod_paths()
    for s in man["sources"]:
        n = s["name"]
        p = paths.get(n) or s["path"]
        if not os.path.exists(p) or _md5(p) != s["md5"]:
            st["stale"].append(n)
        else:
            st["ok"].append(n)
    if st["stale"]:
        st["warns"].append(f"исходники KMM_Merged изменились (Steam обновил?) — возвращены в mods.cfg отдельными модами, KMM_Merged устарел до "
                           f"merge_mods.py --write: {st['stale']}")
    anchors = [man.get("insert_after"), man.get("insert_before")]
    if not (anchors[0] is None or anchors[0] in lines or anchors[1] in lines):
        st["errors"].append(f"слияние: якорь позиции KMM_Merged не найден в списке ({anchors})")
        return st
    st["active"] = True
    st["man"] = man
    return st


def apply_merge(lines, paths=None):
    st = merge_state(lines, paths)
    if not st["active"]:
        return lines
    man, drop = st["man"], set(st["ok"])
    rest = [l for l in lines if l not in drop]
    a, b = man.get("insert_after"), man.get("insert_before")
    if a is None:
        i = 0
    elif a in rest:
        i = rest.index(a) + 1
    else:
        i = rest.index(b)   # якорь «после» пропал — встаём перед следующим
    return rest[:i] + ["KMM_Merged.mod"] + rest[i:]


def generate(merge=True):
    import lo as _lo
    r = _lo.build()
    ex, lorder = rules()
    lines = [b["file"] for b in r["base"]] + [w["file"] for w in r["wh"]] + [x["file"] for x in r["extra"]]
    for m in lorder["kmm"]:
        if m in lorder.get("disabled", {}):
            continue
        if lorder.get("new_game", {}).get(m) is False:   # только для новой игры, сейчас выключен
            continue
        if os.path.exists(os.path.join(ROOT, "build", m, m + ".mod")):
            lines.append(m + ".mod")
    return apply_merge(lines) if merge else lines


def check(lines, paths=None, live=None):
    ex, lorder = rules()
    paths = paths or mod_paths()
    errors, warns = [], []
    if len(lines) != len(set(lines)):
        errors.append("дубли в списке: " + str(sorted({x for x in lines if lines.count(x) > 1})))
    seen = set(VANILLA)
    pos = {l: i for i, l in enumerate(lines)}
    ms = merge_state(lines, paths)
    errors += ms["errors"]
    warns += ms["warns"]
    merged_src = set(ms["ok"]) if ms["active"] else set()
    for l in sorted(merged_src & set(lines)):
        errors.append(f"{l}: слит в KMM_Merged и при этом стоит в списке (двойное применение)")
    if ms["active"] and "KMM_Merged.mod" not in lines:
        errors.append("слияние активно, но KMM_Merged.mod нет в списке")
    for l in lines:
        if l in ex["mods"]:
            errors.append(f"исключён по аудиту: {l} — {ex['mods'][l]}")
        if l not in paths:
            errors.append(f"нет на диске: {l}")
            seen.add(l)
            continue
        try:
            h = kmod.read(paths[l]).header
            deps = [d for d in (h.dependencies or []) if d]
        except Exception as e:  # noqa: BLE001
            errors.append(f"не читается {l}: {type(e).__name__}: {e}"[:200])
            deps = []
        deps += [d for d in ex.get("required_items", {}).get(l, [])]
        for d in deps:
            if d in VANILLA:
                continue
            if d in merged_src:   # зависимость на слитый мод = на KMM_Merged (он стоит на их месте)
                d = "KMM_Merged.mod"
            if d not in pos:
                errors.append(f"{l}: нет зависимости {d}" + (" (на диске есть, но не в mods.cfg)" if d in paths else " (нет на диске)"))
            elif d not in seen:
                errors.append(f"{l}: зависимость {d} стоит позже")
        seen.add(l)
    # 3б) «не брать» по названию из Workshop (.info)
    import re as _re
    brx = [_re.compile(x) for x in ex.get("blocked_titles", {}).get("rx", [])]
    for l in lines:
        if l in paths and brx:
            info = glob.glob(os.path.join(os.path.dirname(paths[l]), "_*.info"))
            t = _re.search(r"<title>([^<]*)</title>", open(info[0], encoding="utf-8", errors="replace").read()) if info else None
            if t and any(r.search(t.group(1).strip()) for r in brx):
                errors.append(f"«не брать» по принятым решениям: {l} ({t.group(1).strip()})")
    # 4) файлы тела основы: побеждает последний поставщик файла с этим именем; он должен совпадать с версией владельца
    for e in body_resources(lines, paths, ex)[1]:
        errors.append(e)
    # 5) реестр лаунчера
    reg = set(open(REG, "rb").read().decode("utf-8", "replace").replace("\r", "").split("\n")) if os.path.exists(REG) else set()
    unknown = sorted(n for n in paths if n.endswith(".mod") and n[:-4] not in reg and not paths[n].startswith(os.path.join(ROOT, "build")))
    if unknown:
        warns.append(f"лаунчер не знает {len(unknown)} модов на диске (при запуске допишет их в mods.cfg): {unknown[:8]} — write дописывает их в реестр")
    # 6) Dust: наш пресет и тени без подмены атласа (иначе вылет при включении теней в настройках, DECISIONS 2026-11-12)
    dust = os.path.join(W, "3703458265")
    if os.path.isdir(dust):
        ini = open(os.path.join(dust, "Dust.ini"), encoding="utf-8", errors="replace").read()
        sh = open(os.path.join(dust, "effects", "Shadows.ini"), encoding="utf-8", errors="replace").read()
        if "LastPreset=laptop" not in ini:
            errors.append("Dust.ini: нет LastPreset=laptop — Dust грузит dust_high (атлас теней 6144, RTGI/SSIL)")
        if "Resolution=0" not in sh or "PCSS=0" not in sh:
            errors.append("Dust effects/Shadows.ini: Resolution/PCSS не 0 — подмена атласа теней даёт вылет при включении теней")
        for fx in ("Letterbox",):   # владелец 2026-11-12: без чёрной полосы (рисовка — наполовину, по желанию владельца)
            fp = os.path.join(dust, "effects", fx + ".ini")
            if os.path.exists(fp) and "Enabled=0" not in open(fp, encoding="utf-8", errors="replace").read():
                errors.append(f"Dust effects/{fx}.ini включён — чёрная полоса (владелец просил убрать)")
    if live is not None:
        stray = [l for l in live if l not in set(lines)]
        missing = [l for l in lines if l not in set(live)]
        if stray:
            errors.append(f"в живом mods.cfg лишние (не из генератора): {stray}")
        if missing:
            warns.append(f"в живом mods.cfg нет: {missing[:10]}{' …' if len(missing) > 10 else ''}")
    return errors, warns, unknown


def _md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def body_resources(lines, paths, ex):
    """→ ({имя файла: путь эталона}, ошибки). Эталон — файл последнего владельца в порядке загрузки (иначе ваниль).
    Скелет чужого мода допустим, если порядок ванильных костей совпадает (анимационные паки)."""
    import mesh_skel
    pr = ex["protected_resources"]
    owners = set(pr["owners"])
    van = {}
    for d in pr["dirs"]:
        for dp, _, fs in os.walk(os.path.join(GAME, "data", *d.split("/"))):
            for f in fs:
                van[f.lower()] = os.path.join(dp, f)
    providers = {}   # имя → [(мод, путь)] в порядке загрузки
    ref = dict(van)
    for l in lines:
        if l not in paths:
            continue
        root = os.path.dirname(paths[l])
        for dp, _, fs in os.walk(root):
            for f in fs:
                k = f.lower()
                if l in owners and any(os.path.normcase(os.path.join(root, *d.split("/"))) == os.path.normcase(dp) for d in pr["dirs"]):
                    ref[k] = os.path.join(dp, f)
                    providers.setdefault(k, []).append((l, os.path.join(dp, f)))
                elif k in van or (l not in owners and k.endswith(".png") and "mask" in k and "skins" in dp.lower()):
                    providers.setdefault(k, []).append((l, os.path.join(dp, f)))
    errors = []
    for k, pv in providers.items():
        if k not in ref:
            continue
        win_mod, win = pv[-1]
        if win_mod in owners or _md5(win) == _md5(ref[k]):
            continue
        if k.endswith(".mesh") and mesh_skel.check_mesh(win, [os.path.dirname(win)]) is None:
            continue   # тело анимационного пака на скелете с ванильным порядком костей
        if k.endswith(".skeleton"):
            a, b = mesh_skel.skeleton_bones(win), mesh_skel.skeleton_bones(ref[k])
            if all(a.get(i) == n for i, n in b.items()):
                continue
            errors.append(f"{win_mod}: скелет {k} меняет порядок костей основы")
            continue
        errors.append(f"{win_mod} перезаписывает файл тела основы {k} (последним в порядке загрузки; эталон — "
                      f"{next((m for m, _ in reversed(pv) if m in owners), 'ваниль')}); нужен повтор эталона в KMM_Fix")
    return ref, errors


def reassert(lines, paths=None):
    """Кладёт эталонные файлы тела (маски Community Part Map) в build/KMM_Fix — он грузится последним и побеждает
    чужие копии (Death Korps of Krieg, Mark-X — их маски = маски Deathstroke). → число файлов."""
    ex, _ = rules()
    paths = paths or mod_paths()
    ref, _ = body_resources([l for l in lines if l != "KMM_Fix.mod"], paths, ex)
    fixed = 0
    for d in ex["protected_resources"]["dirs"]:
        if "masks" not in d:
            continue
        dst = os.path.join(ROOT, "build", "KMM_Fix", *d.split("/"))
        os.makedirs(dst, exist_ok=True)
        for k, src in ref.items():
            if os.path.normcase(os.path.dirname(src)).endswith(os.path.normcase(os.path.join(*d.split("/")))):
                shutil.copy2(src, os.path.join(dst, os.path.basename(src)))
                fixed += 1
    return fixed


def read_live():
    return [l for l in open(CFG, "rb").read().decode("utf-8").split("\r\n") if l]


def write(lines, unknown):
    if "kenshi_x64.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
        sys.exit("Kenshi запущен — закройте игру")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    os.makedirs(os.path.join(ROOT, "backup", "cfg"), exist_ok=True)
    shutil.copy2(CFG, os.path.join(ROOT, "backup", "cfg", f"mods.cfg.{stamp}"))
    open(CFG, "wb").write("".join(l + "\r\n" for l in lines).encode("utf-8"))
    if unknown and os.path.exists(REG):
        shutil.copy2(REG, os.path.join(ROOT, "backup", "cfg", f"__mods.list.{stamp}"))
        raw = open(REG, "rb").read()
        nl = b"\r\n" if b"\r\n" in raw else b"\n"
        if raw and not raw.endswith(nl):
            raw += nl
        raw += b"".join(n[:-4].encode("utf-8") + nl for n in unknown)
        open(REG, "wb").write(raw)
    return stamp


def main(mode):
    lines = generate()
    errors, warns, unknown = check(lines, live=read_live() if mode == "check" else None)
    for w in warns:
        print("ВНИМАНИЕ:", w)
    for e in errors:
        print("ОШИБКА:", e)
    print(f"mods.cfg (генератор): {len(lines)} модов; хвост: {lines[-14:]}")
    gen_errors = [e for e in errors if not e.startswith("в живом mods.cfg")]
    if gen_errors:
        sys.exit(f"ПРОВЕРКА ПЕРЕД СБОРКОЙ НЕ ПРОЙДЕНА: {len(gen_errors)} ошибок")
    if mode == "write":
        stamp = write(lines, unknown)
        print(f"записан {CFG} (бэкап backup/cfg/mods.cfg.{stamp}); реестр лаунчера +{len(unknown)}")
    return lines


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "check")
