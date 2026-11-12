"""KMM_Merged: слияние малых чистых data-модов в один .mod (DEDUP.md п.4, журнал docs/journal/MERGE.md).

Отбор (каждый раз заново по генератору mods.cfg без слияния): мод не KMM_ и не ядро; в папке только .mod/.info/.img и превью
(.png/.jpg/.txt) в корне — ни ресурсов, ни dll/json/lua, ни подпапок; 1..499 записей; нет удалений записей (DELETED);
на мод никто не ссылается (dependencies/references всех модов списка, required_items); заголовок без неразобранного хвоста.
Слияние: записи по порядку загрузки, записи про один sid складываются в одну дельту (значения — последний побеждает,
ссылки/инстансы — последовательно, как kmod.apply), change-флаг первого.
Эквивалентность: для каждого sid из исходников цепочка «ваниль + все моды по порядку» с исходниками и с KMM_Merged на их месте
обязана дать одно и то же состояние (kmod.apply, strict для модов, как в игре). Позицию выбираем (последний/первый исходник),
исходники, ломающие эквивалентность (между ними мод, правящий те же sid), исключаем из слияния; зависимости исходника
должны стоять раньше позиции.
Выход: build/KMM_Merged/KMM_Merged.mod, rules/merged_manifest.json, секция «merged» в rules/excluded_mods.json.
python -I -X utf8 tools/build/merge_mods.py            # посчитать и проверить, ничего не писать
python -I -X utf8 tools/build/merge_mods.py --write    # записать мод, манифест, секцию merged
"""
import collections
import hashlib
import json
import os
import sys
import time

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
sys.path.insert(0, os.path.join(ROOT, "tools"))
sys.path.insert(0, os.path.join(ROOT, "tools", "fast"))
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
import kmod  # noqa: E402

MERGED = "KMM_Merged"
MAX_RECORDS = 500
VANILLA_ORDER = ["gamedata.base", "rebirth.mod", "Newwworld.mod", "Dialogue.mod"]
OK_EXT = {".mod", ".info", ".img", ".png", ".jpg", ".jpeg", ".txt", ".md", ".url"}
MANIFEST = os.path.join(ROOT, "rules", "merged_manifest.json")
FLAG = os.path.join(ROOT, "rules", "merge.json")
OUT_DIR = os.path.join(ROOT, "build", MERGED)


def md5(p):
    return hashlib.md5(open(p, "rb").read()).hexdigest()


def enabled():
    try:
        return bool(json.load(open(FLAG, encoding="utf-8")).get("enabled"))
    except (OSError, ValueError):
        return False


# --- складывание дельт ----------------------------------------------------------------------------
class _M:
    def __init__(self, it):
        self.items = [it]


def _compose_ops(cur, new, key, is_del):
    """Складывает последовательность операций (set/del по ключу) так, чтобы применение одной дельты = применение двух."""
    for x in new:
        j = next((n for n in range(len(cur) - 1, -1, -1) if key(cur[n]) == key(x)), None)
        if j is None:
            cur.append(x)
        elif not is_del(cur[j]):
            cur[j] = x          # set после set / del после set — на месте
        elif not is_del(x):
            cur.append(x)       # set после del: del остаётся (убрать из базы), set добавляется в конец
        # del после del — ничего


def compose(items):
    """items одного sid в порядке загрузки → одна запись."""
    res = kmod._copy(items[0])
    for it in items[1:]:
        if res.change == kmod.CHANGE_NEW:
            kmod.apply({res.sid: res}, _M(it))
            continue
        res.name = it.name
        res.values.update(it.values)
        res.save_data |= (it.save_data & kmod.CHANGE_RENAMED) if it.change != kmod.CHANGE_NEW else 0
        for cat, refs in it.refs.items():
            lst = res.refs.setdefault(cat, [])
            _compose_ops(lst, [kmod.Ref(r.target, r.v0, r.v1, r.v2) for r in refs], lambda r: r.target,
                         lambda r: (r.v0, r.v1, r.v2) == kmod.DELETED_REF)
        _compose_ops(res.instances, [i for i in it.instances], lambda i: i.id, lambda i: not i.target)
    return res


def _tv(v):
    k = kmod._kind(v)
    return (k, tuple(v) if isinstance(v, tuple) else (round(float(v), 6) if k == 1 else v))


def sig(it):
    if it is None:
        return None
    return (it.name, tuple(sorted((k, _tv(v)) for k, v in it.values.items())),
            tuple(sorted((c, tuple((r.target, r.v0, r.v1, r.v2) for r in rs)) for c, rs in it.refs.items() if rs)),
            tuple((i.id, i.target, tuple(i.pos), tuple(i.rot), tuple(i.states)) for i in it.instances))


def run_seq(sid, seq):
    d = {}
    for idx, it in seq:
        kmod.apply(d, _M(it), strict=idx >= 4)
    return d.get(sid)


def nfields(it):
    return 0 if it is None else len(it.values) + sum(len(r) for r in it.refs.values()) + len(it.instances)


# --- загрузка и отбор -------------------------------------------------------------------------------
def load_layers(lines, paths):
    layers, bad = [], []
    for v in VANILLA_ORDER:
        layers.append((v, kmod.read(os.path.join(GAME, "data", v)), None))
    for l in lines:
        p = paths.get(l)
        try:
            layers.append((l, kmod.read(p), p))
        except Exception as e:  # noqa: BLE001
            layers.append((l, None, p))
            bad.append((l, f"{type(e).__name__}: {e}"[:120]))
    return layers, bad


def candidates(layers, ex):
    """→ ({имя: причина отказа} , [имена кандидатов в порядке загрузки])."""
    refd = collections.Counter()
    for n, m, p in layers:
        if m is not None and m.header:
            for x in (m.header.dependencies or []) + (m.header.references or []):
                refd[x] += 1
    for deps in ex.get("required_items", {}).values():
        for x in deps:
            refd[x] += 1
    why, cand = {}, []
    for i, (n, m, p) in enumerate(layers):
        if i < 4 or p is None:
            continue
        if m is None:
            why[n] = "не читается"
        elif n.startswith("KMM_"):
            continue
        elif not (1 <= len(m.items) < MAX_RECORDS):
            why[n] = "записей %d" % len(m.items)
        elif refd[n]:
            why[n] = "на мод ссылаются"
        elif m.header.tail or m.header.delete_requests:
            why[n] = "нестандартный заголовок"
        elif any(it.values.get("DELETED") is True for it in m.items):
            why[n] = "удаление записей"
        else:
            bad = False
            for dp, dn, fs in os.walk(os.path.dirname(p)):
                if dn or (os.path.normcase(dp) != os.path.normcase(os.path.dirname(p))) or any(os.path.splitext(f)[1].lower() not in OK_EXT for f in fs):
                    bad = True
                    break
            if bad:
                why[n] = "ресурсы/подпапки/dll/json/lua"
            else:
                cand.append(n)
    return why, cand


def select(layers, cand):
    """→ (набор исходников, позиция-слой, режим, отказы {имя: причина}). Фикс-пойнт по эквивалентности и зависимостям."""
    idx = {n: i for i, (n, m, p) in enumerate(layers)}
    by_src = {n: {it.sid for it in layers[idx[n]][1].items} for n in cand}
    T = set().union(*by_src.values()) if by_src else set()
    seq = collections.defaultdict(list)
    for i, (n, m, p) in enumerate(layers):
        if m is not None:
            for it in m.items:
                if it.sid in T:
                    seq[it.sid].append((i, it))
    rej = {}
    best = None
    for mode in ("last", "first"):
        S = set(cand) - set(rej)
        drop = {}
        while S:
            P = (max if mode == "last" else min)(idx[n] for n in S)
            rem = {}
            for n in S:   # зависимости должны стоять раньше позиции
                for d in layers[idx[n]][1].header.dependencies:
                    if d and (d not in idx or idx[d] >= P):
                        rem[n] = f"зависимость {d} не раньше позиции слияния"
            for sid in sorted({s for n in S for s in by_src[n]}):
                full = seq[sid]
                src_idx = [i for i, it in full if layers[i][0] in S]
                if not src_idx:
                    continue
                outs = [i for i, it in full if layers[i][0] not in S]
                comp = compose([it for i, it in full if layers[i][0] in S])
                mer = sorted([(i, it) for i, it in full if layers[i][0] not in S] + [(P, comp)], key=lambda x: x[0])
                if sig(run_seq(sid, full)) == sig(run_seq(sid, mer)):
                    continue
                crossed = [s for s in src_idx if any(min(s, P) < o < max(s, P) for o in outs)]
                for s in (crossed or src_idx):
                    rem.setdefault(layers[s][0], f"перекрытие записей: между ним и позицией слияния мод правит sid {sid}")
            if not rem:
                break
            S -= set(rem)
            drop.update(rem)
        if best is None or len(S) > len(best[0]):
            best = (set(S), P if S else None, mode, drop)
    return best


# --- сборка ---------------------------------------------------------------------------------------------
def build_mod(layers, S):
    order = [n for n, m, p in layers if n in S]
    idx = {n: i for i, (n, m, p) in enumerate(layers)}
    sids, seq = [], collections.defaultdict(list)
    for n in order:
        for it in layers[idx[n]][1].items:
            if it.sid not in seq:
                sids.append(it.sid)
            seq[it.sid].append(it)
    items = [compose(seq[s]) for s in sids]
    deps, refs = [], []
    for n in order:
        h = layers[idx[n]][1].header
        deps += [d for d in h.dependencies if d and d not in S and d not in deps]
        refs += [r for r in h.references if r and r not in S and r not in refs]
    names = ", ".join(order)
    hdr = kmod.Header(version=1, author="KMM", description=f"KMM_Merged: слияние {len(order)} малых data-модов (rules/merged_manifest.json)",
                      dependencies=deps, references=refs, save_count=1)
    return kmod.ModFile(kmod.FILE_MOD17, hdr, max(layers[idx[n]][1].last_id for n in order), items)


def verify(layers, S, P, data):
    """Round-trip + эквивалентность по прочитанному из байтов KMM_Merged. → dict статистики; бросает AssertionError."""
    back = kmod.read(data)
    assert kmod.write(back) == data, "round-trip KMM_Merged"
    idx = {n: i for i, (n, m, p) in enumerate(layers)}
    mer_items = {it.sid: it for it in back.items}
    srcs = [n for n, m, p in layers if n in S]
    touched = {it.sid for n in srcs for it in layers[idx[n]][1].items}
    assert set(mer_items) == touched, "множество sid слитого мода != объединению исходников"
    # то же, что есть в исходниках: число записей = сумма разных sid; плюс исходные записи читаются обратно (round-trip каждого)
    for n in srcs:
        m = layers[idx[n]][1]
        assert kmod.write(kmod.read(kmod.write(m))) == kmod.write(m), f"round-trip {n}"
    seq = collections.defaultdict(list)
    for i, (n, m, p) in enumerate(layers):
        if m is not None:
            for it in m.items:
                if it.sid in touched:
                    seq[it.sid].append((i, it))
    diffs, fields, writes = [], 0, 0
    for sid, full in seq.items():
        mer = sorted([(i, it) for i, it in full if layers[i][0] not in S] + [(P, mer_items[sid])], key=lambda x: x[0])
        a, b = run_seq(sid, full), run_seq(sid, mer)
        fields += nfields(a)
        writes += sum(len(it.values) + sum(len(r) for r in it.refs.values()) + len(it.instances) for i, it in full if layers[i][0] in S)
        if sig(a) != sig(b):
            diffs.append(sid)
    return {"sids": len(touched), "fields_compared": fields, "source_field_writes": writes, "diffs": diffs,
            "merged_records": len(back.items), "source_records": sum(len(layers[idx[n]][1].items) for n in srcs)}


def plan(lines, paths, ex):
    """Весь расчёт без записи. lines — mods.cfg без слияния."""
    layers, bad = load_layers(lines, paths)
    why, cand = candidates(layers, ex)
    S, P, mode, drop = select(layers, cand)
    why.update(drop)
    return layers, bad, why, cand, S, P, mode


def step(write=False, quiet=False):
    """Шаг kmm_build: пересчёт KMM_Merged. → dict отчёта (или {'enabled': False})."""
    import mods_cfg
    if not enabled():
        if not quiet:
            print("merge: rules/merge.json enabled=false — слияние выключено")
        return {"enabled": False}
    ex, _ = mods_cfg.rules()
    paths = mods_cfg.mod_paths()
    lines = mods_cfg.generate(merge=False)
    layers, bad, why, cand, S, P, mode = plan(lines, paths, ex)
    srcs = [n for n, m, p in layers if n in S]
    mod = build_mod(layers, S)
    data = kmod.write(mod)
    stat = verify(layers, S, P, data)
    ok = not stat["diffs"] and not bad
    # якорь позиции: последний/первый не-исходник перед слотом
    slot = lines.index(layers[P][0])
    before = next((l for l in reversed(lines[:slot]) if l not in S), None)
    after = next((l for l in lines[slot + 1:] if l not in S), None)
    man = {"_doc": "Манифест KMM_Merged (tools/build/merge_mods.py). md5 исходников: при расхождении генератор возвращает мод в mods.cfg и предупреждает.",
           "built": time.strftime("%Y-%m-%d %H:%M:%S"), "mode": mode, "slot": layers[P][0],
           "insert_after": before, "insert_before": after,
           "merged_file": "build/KMM_Merged/KMM_Merged.mod", "merged_md5": hashlib.md5(data).hexdigest(),
           "merged_records": stat["merged_records"], "source_records": stat["source_records"],
           "verify": {k: stat[k] for k in ("sids", "fields_compared", "source_field_writes")} | {"diffs": len(stat["diffs"])},
           "sources": [{"name": n, "path": layers[[x[0] for x in layers].index(n)][2].replace("\\", "/"),
                        "md5": md5(layers[[x[0] for x in layers].index(n)][2]),
                        "records": len(layers[[x[0] for x in layers].index(n)][1].items)} for n in srcs]}
    summ = {"enabled": True, "ok": ok, "candidates": len(cand), "merged": len(S), "rejected": {n: why[n] for n in cand if n not in S},
            "not_candidates": dict(collections.Counter(why[n].split(" ")[0] + " " + why[n].split(" ")[1] if " " in why[n] else why[n] for n in why if n not in cand)),
            "mode": mode, "slot": layers[P][0] if S else None, "stat": {k: v for k, v in stat.items() if k != "diffs"}, "diffs": stat["diffs"][:10],
            "bad": bad, "lines_before": len(lines), "manifest": man}
    if not quiet:
        print(f"merge: кандидатов {len(cand)}, слито {len(S)}, исключено из слияния {len(cand) - len(S)}; позиция {mode}: после {before}; "
              f"sid {stat['sids']}, полей сверено {stat['fields_compared']}, расхождений {len(stat['diffs'])}")
        for n in cand:
            if n not in S:
                print(f"   исключён из слияния: {n} — {why[n]}")
    if not ok:
        print("merge: ПРОВЕРКА НЕ ПРОЙДЕНА", stat["diffs"][:5], bad[:3])
        return summ
    if write:
        os.makedirs(OUT_DIR, exist_ok=True)
        open(os.path.join(OUT_DIR, MERGED + ".mod"), "wb").write(data)
        json.dump(man, open(MANIFEST, "w", encoding="utf-8", newline=""), ensure_ascii=False, indent=1)
        p = os.path.join(ROOT, "rules", "excluded_mods.json")
        d = json.load(open(p, encoding="utf-8"))
        d["merged"] = {n: "слит в KMM_Merged (rules/merged_manifest.json); отличие от аудита: возвращается в mods.cfg при смене md5" for n in srcs}
        d["_doc_merged"] = "Секция merged — исходники KMM_Merged (tools/build/merge_mods.py); читает только tools/build/mods_cfg.py, в catalog/lo не участвует."
        open(p, "w", encoding="utf-8", newline="").write(json.dumps(d, ensure_ascii=False, indent=1))
        if not quiet:
            print("merge: записано build/KMM_Merged/KMM_Merged.mod, rules/merged_manifest.json, excluded_mods.json[merged]")
    return summ


if __name__ == "__main__":
    t = time.time()
    r = step(write="--write" in sys.argv)
    print(f"{time.time() - t:.1f} с; строк mods.cfg до слияния {r.get('lines_before')}")
