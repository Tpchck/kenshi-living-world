"""Офлайн-аудит зон мира (только чтение игры/модов/сейвов): итоговое состояние зон = ваниль + mods.cfg + KMM_Fix.
Проверки: (1) битые ссылки инстансов; (2) states, которых нет в файле-источнике; (3) наложения крупных зданий
разных модов-авторов (OBB SAT в XZ, проникновение > 2 м); (4) «снимковые откаты», не покрытые zone_fix.
python -I -X utf8 tools/zone_audit.py [--strict] [--pen 2.0] [--cache файл.pkl]  → data/zone_audit.json
--strict: код 1, если (1) или (4) > 0. --cache: кэш габаритов зданий (ускоряет повторные прогоны; Ctx грузится минуты)."""
import collections
import glob
import json
import math
import os
import pickle
import re
import struct
import sys
import time

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
WORKSHOP = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
for _p in ("", "build", "fast"):
    _d = os.path.join(ROOT, "tools", _p)
    if _d not in sys.path:
        sys.path.insert(0, _d)
import kmod  # noqa: E402
import zone_fix  # noqa: E402

FIX_DIR = os.path.join(ROOT, "build", "KMM_Fix", "leveldata")
FURN = re.compile(r"bed|table|chair|bench|lamp|light|torch|crate|barrel|shelf|rack|sign|banner|flag|stool|\bbox|cabinet|chest|cage|"
                  r"decor|rug|plant|tree|rock|bush|grass|campfire|fire|statue|pot\b|pots|sack|bucket|stove|oven|workbench|"
                  r"anvil|forge|bookcase|desk|counter|sofa|couch|pillow|mat\b|carpet|lantern|candle|crystal|skull|bones|"
                  r"corpse|cart|wagon|tent|hay|pile|junk|rubble|debris|puddle|fountain|well\b|post\b|pole|chain|rope", re.I)
WALL = re.compile(r"pipe|ramp|wall|fence|gate|barrier|rampart|palisade|railing|stair|ramp|bridge|tunnel|pillar|column|arch", re.I)
U = 1.0  # масштаб ед. мира не подтверждён (дом ~500 ед.), поэтому все пороги и вывод в единицах мира, не в метрах
MIN_DIM, MIN_AREA = 200.0, 30000.0  # "крупное": длинная сторона >= 200 ед. и площадь >= 30000


def author(layer):
    return "vanilla" if layer.startswith("vanilla:") else layer


# ---------- габариты ----------
def mesh_index():
    idx = {}
    for root in (WORKSHOP, os.path.join(GAME, "mods"), os.path.join(GAME, "data", "buildings")):
        for dp, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".mesh"):
                    idx.setdefault(f.lower(), os.path.join(dp, f))
    return idx


def mesh_bounds(path):
    try:
        with open(path, "rb") as fh:
            d = fh.read(1 << 20)
        i = d.find(struct.pack("<HI", 0x9000, 34))
        if i < 0:
            return None
        v = struct.unpack("<6f", d[i + 6:i + 30])
        if not all(math.isfinite(x) and abs(x) < 1e5 for x in v):
            return None
        return v
    except OSError:
        return None


def _mesh_of(it):
    for k, v in it.values.items():
        if isinstance(v, str) and v.lower().endswith(".mesh"):
            return str(v)
    return None


class Boxes:
    """Габарит (minx,minz,maxx,maxz) здания: distant mesh, иначе объединение частей. Записи берём из файла зоны, затем из ctx.M."""

    def __init__(self, ctx):
        self.ctx, self.mi, self.mb, self.bx = ctx, mesh_index(), {}, {}

    def _bounds(self, rel):
        if rel not in self.mb:
            cand = os.path.join(GAME, rel.replace("/", os.sep))
            p = cand if os.path.isfile(cand) else self.mi.get(os.path.basename(rel.replace("\\", "/")).lower())
            self.mb[rel] = mesh_bounds(p) if p else None
        return self.mb[rel]

    def box(self, it):
        dm = it.values.get("distant mesh")
        rels = []
        if isinstance(dm, str) and dm.lower().endswith(".mesh"):
            rels.append([str(dm)])
        rels.append([m for m in (_mesh_of(self.ctx.M[r.target]) for r in it.refs.get("parts", []) if r.target in self.ctx.M) if m])
        key = tuple(tuple(x) for x in rels)
        if key in self.bx:
            return self.bx[key]
        out = None
        for group in rels:
            bs = [bb for bb in (self._bounds(m) for m in group) if bb]
            if bs:
                b = (min(x[0] for x in bs), min(x[2] for x in bs), max(x[3] for x in bs), max(x[5] for x in bs))
                if b[2] - b[0] >= 0.5 or b[3] - b[1] >= 0.5:
                    out = b
                    break
        self.bx[key] = out
        return out


# ---------- геометрия ----------
def obb(ins, box):
    x0, z0, x1, z1 = box
    yaw = 2 * math.atan2(ins.rot[2], ins.rot[0])
    c, s = math.cos(yaw), math.sin(yaw)
    lcx, lcz = (x0 + x1) / 2, (z0 + z1) / 2
    cx = ins.pos[0] + lcx * c + lcz * s
    cz = ins.pos[2] - lcx * s + lcz * c
    hx, hz = (x1 - x0) / 2, (z1 - z0) / 2
    return cx, cz, hx, hz, (c, -s), (s, c)  # оси локальных X и Z в мире


def penetration(a, b):
    ax, az, ahx, ahz, a1, a2 = a
    bx, bz, bhx, bhz, b1, b2 = b
    dx, dz = bx - ax, bz - az
    best = 1e9
    for ux, uz in (a1, a2, b1, b2):
        ra = ahx * abs(a1[0] * ux + a1[1] * uz) + ahz * abs(a2[0] * ux + a2[1] * uz)
        rb = bhx * abs(b1[0] * ux + b1[1] * uz) + bhz * abs(b2[0] * ux + b2[1] * uz)
        ov = ra + rb - abs(dx * ux + dz * uz)
        if ov <= 0:
            return 0.0
        best = min(best, ov)
    return best


# ---------- итоговое состояние зон ----------
def zone_states(L):
    """{зона: [(слой, файл)]}; KMM_Fix последним."""
    by = collections.defaultdict(list)
    for name, zs in L:
        for z, f in zs.items():
            by[z].append((name, f))
    if os.path.isdir(FIX_DIR) and "--no-fix" not in sys.argv:
        for f in glob.glob(os.path.join(FIX_DIR, "*.zone")):
            by[os.path.basename(f)].append(("KMM_Fix", f))
    return by


def main():
    t0 = time.time()
    strict = "--strict" in sys.argv
    pen_min = float(sys.argv[sys.argv.index("--pen") + 1]) if "--pen" in sys.argv else 100.0  # ед. мира (~1/5 ширины дома)
    cpath = sys.argv[sys.argv.index("--cache") + 1] if "--cache" in sys.argv else None
    import kmm_build
    ctx = kmm_build.Ctx()
    print(f"Ctx: {time.time() - t0:.0f}s", flush=True)
    boxes = Boxes(ctx)

    by = zone_states(zone_fix.layers())
    broken = []          # (зона, мод, id, target, причина)
    bad_states = []
    rollbacks = []
    overlaps = []
    bad_files = []
    stat = collections.Counter()
    nonbuild = collections.Counter()
    for z, chain in sorted(by.items()):
        orig, intended, actual, hist = {}, {}, {}, collections.defaultdict(list)
        sids_of, local, allloc = {}, {}, {}
        for name, f in chain:
            try:
                m = kmod.read(f)
            except Exception as e:
                bad_files.append(f"{name}:{z}:{type(e).__name__}")
                continue
            sids_of[f] = {it.sid for it in m.items}
            local[f] = {it.sid: it for it in m.items}
            allloc.update(local[f])
            for it in m.items:
                if it.type_name != "INSTANCE_COLLECTION":
                    continue
                for ins in it.instances:
                    hist[ins.id].append((name, ins, f))
                    if ins.id not in orig:
                        if ins.target:
                            orig[ins.id] = ins
                    elif not ins.target or not zone_fix._same(ins, orig[ins.id]):
                        intended[ins.id] = (name, ins, f)
                    actual[ins.id] = (name, ins, f)
        stat["zones"] += 1
        live = []
        for k, (name, ins, f) in actual.items():
            if not ins.target:
                continue
            stat["live"] += 1
            # (4) откат: итог — неизменённая копия оригинала, а ранее был намеренный правщик
            if k in intended:
                iname, iins, _ = intended[k]
                if iname != name and k in orig and zone_fix._same(ins, orig[k]):
                    rollbacks.append((z, iname, name, k, "del" if not iins.target else "edit"))
            # (1)
            li = allloc.get(ins.target) or ctx.M.get(ins.target)
            t = li.type_name if li is not None else None
            if t is None:
                broken.append((z, author(name), k, ins.target, "нет в данных"))
            elif t != "BUILDING":
                nonbuild[t] += 1
                if t not in ("INVENTORY_STATE", "GAMESTATE_BUILDING"):
                    broken.append((z, author(name), k, ins.target, "тип " + t))
            # (2)
            for sid in ins.states:
                if sid not in sids_of.get(f, ()):
                    bad_states.append((z, author(name), k, sid, sid in ctx.M))
            # автор: слой, давший это состояние (для KMM_Fix — ближайший слой с тем же состоянием)
            au = name
            if name == "KMM_Fix":
                au = next((n for n, i, _ in reversed(hist[k][:-1]) if i.target and zone_fix._same(i, ins)), name)
            live.append((author(au), ins, f))
        # (3)
        items = []
        for au, ins, f2 in live:
            li = allloc.get(ins.target) or ctx.M.get(ins.target)
            if li is None or li.type_name != "BUILDING":
                continue
            nm, bx = li.name, boxes.box(li)
            if not bx or not nm:
                continue
            w, d = bx[2] - bx[0], bx[3] - bx[1]
            if max(w, d) < MIN_DIM or w * d < MIN_AREA or FURN.search(nm):
                continue
            items.append((au, ins, nm, obb(ins, bx)))
        stat["big"] += len(items)
        cell = collections.defaultdict(list)
        for i, (au, ins, nm, o) in enumerate(items):
            r = math.hypot(o[2], o[3])
            for gx in range(int((o[0] - r) // 6400), int((o[0] + r) // 6400) + 1):
                for gz in range(int((o[1] - r) // 6400), int((o[1] + r) // 6400) + 1):
                    cell[(gx, gz)].append(i)
        seen = set()
        for lst in cell.values():
            for ai in range(len(lst)):
                for bi in range(ai + 1, len(lst)):
                    i, j = lst[ai], lst[bi]
                    if (i, j) in seen:
                        continue
                    seen.add((i, j))
                    A, B = items[i], items[j]
                    if abs(A[1].pos[1] - B[1].pos[1]) > 400:
                        continue
                    if A[0] == B[0] or (WALL.search(A[2]) and WALL.search(B[2])):
                        continue
                    if math.hypot(A[3][0] - B[3][0], A[3][1] - B[3][1]) > math.hypot(A[3][2], A[3][3]) + math.hypot(B[3][2], B[3][3]):
                        continue
                    p = penetration(A[3], B[3]) / U
                    if p > pen_min:
                        overlaps.append({"zone": z, "pen": round(p, 1), "a": A[2], "a_mod": A[0], "a_pos": [round(v) for v in A[1].pos],
                                         "b": B[2], "b_mod": B[0], "b_pos": [round(v) for v in B[1].pos]})
    overlaps.sort(key=lambda o: -o["pen"])
    by_zone = collections.Counter(o["zone"] for o in overlaps)
    by_pair = collections.Counter(" x ".join(sorted((o["a_mod"], o["b_mod"]))) for o in overlaps)
    rb_pair = collections.Counter(f"{r[4]}: {r[1]} <- {r[2]}" for r in rollbacks)
    res = {
        "seconds": round(time.time() - t0), "stat": dict(stat), "bad_files": bad_files,
        "broken_refs": {"count": len(broken), "by_mod": dict(collections.Counter(b[1] for b in broken).most_common(30)),
                        "nonbuilding_types": dict(nonbuild), "sample": [list(b) for b in broken[:40]]},
        "bad_states": {"count": len(bad_states), "missing_everywhere": sum(1 for b in bad_states if not b[4]),
                       "by_mod": dict(collections.Counter(b[1] for b in bad_states).most_common(30)), "sample": [list(b) for b in bad_states[:40]]},
        "overlaps": {"count": len(overlaps), "by_zone": dict(by_zone.most_common(30)), "by_pair": dict(by_pair.most_common(30)),
                     "top": overlaps[:200]},
        "rollbacks_left": {"count": len(rollbacks), "by_pair": dict(rb_pair.most_common()), "sample": [list(r) for r in rollbacks[:40]]},
    }
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "zone_audit.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(f"зон {stat['zones']}, живых инстансов {stat['live']}, крупных {stat['big']}, файлов с ошибкой {len(bad_files)}")
    print(f"(1) битых ссылок: {len(broken)}  {res['broken_refs']['by_mod']}")
    print(f"(2) states вне файла: {len(bad_states)} (нигде нет: {res['bad_states']['missing_everywhere']})")
    print(f"(3) наложений >{pen_min:g} ед.: {len(overlaps)}; зоны {dict(by_zone.most_common(8))}")
    print(f"    пары модов {dict(by_pair.most_common(8))}")
    for o in overlaps[:10]:
        print(f"    {o['zone']} {o['pen']}  {o['a']}[{o['a_mod']}]{o['a_pos']} <> {o['b']}[{o['b_mod']}]{o['b_pos']}")
    print(f"(4) откатов не покрыто: {len(rollbacks)} {dict(rb_pair)}")
    print(f"время {time.time() - t0:.0f}s -> data/zone_audit.json")
    if strict and (broken or rollbacks):
        sys.exit(1)


if __name__ == "__main__":
    main()
