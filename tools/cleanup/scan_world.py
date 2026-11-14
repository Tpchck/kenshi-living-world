"""Разведка для чистки карты (ТОЛЬКО ЧТЕНИЕ): Ctx + зоны -> кэш scratch pickle.
python -I -X utf8 tools/cleanup/scan_world.py <out.pkl>
Сохраняет: towns (sid,name,mod,pos,owner,REMOVED,squads по видам), zone-инстансы по слоям, фракции."""
import os, sys, pickle, collections
ROOT = r"C:\KenshiModMap"
for _p in ("", "build", "fast"):
    sys.path.insert(0, os.path.join(ROOT, "tools", _p))
import kmod, zone_fix, kmm_build as kb  # noqa: E402

def main(out):
    ctx = kb.Ctx()
    M = ctx.M
    towns = {}
    for t in M.values():
        if t.type_name == "TOWN":
            towns[t.sid] = dict(name=t.name, values={k: v for k, v in t.values.items() if k in ("REMOVED", "type", "is public", "public")},
                                refs={c: [(r.target, r.v0, r.v1, r.v2) for r in rs] for c, rs in t.refs.items()}, origin=ctx.origin.get(t.sid))
    facs = {t.sid: t.name for t in M.values() if t.type_name == "FACTION"}
    sq = {t.sid: dict(name=t.name, type=t.type_name, refs={c: [(r.target, r.v0, r.v1) for r in rs] for c, rs in t.refs.items() if c in ("faction", "leader", "squad", "squad2", "pets", "members")}) for t in M.values() if t.type_name in ("SQUAD_TEMPLATE", "UNIQUE_SQUAD_TEMPLATE")}
    bld = {t.sid: t.name for t in M.values() if t.type_name == "BUILDING"}
    # позиции TOWN из leveldata.level (по слоям)
    import glob, mods_cfg
    game = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\newland"
    levels = [os.path.join(game, "leveldata.level")] + sorted(glob.glob(os.path.join(game, "leveldata", "*", "leveldata.level")))
    levels += [os.path.join(os.path.dirname(p), "leveldata", "leveldata.level") for n, p in mods_cfg.mod_paths().items()]
    pos = {}
    for lf in levels:
        if os.path.isfile(lf):
            try:
                for it in kmod.read(lf).items:
                    if it.type_name == "GAMESTATE_TOWN_INSTANCE_LIST":
                        for ins in it.instances:
                            if ins.target:
                                pos[ins.target] = (ins.pos[0], ins.pos[2], lf)
            except Exception:
                pass
    zones = []   # (layer, zone, id, target, x, z)
    for name, zs in zone_fix.layers():
        for z, f in zs.items():
            try:
                m = kmod.read(f)
            except Exception:
                continue
            for it in m.items:
                if it.type_name == "INSTANCE_COLLECTION":
                    for ins in it.instances:
                        zones.append((name, z, ins.id, ins.target, ins.pos[0], ins.pos[1], ins.pos[2]))
    pickle.dump(dict(towns=towns, facs=facs, sq=sq, bld=bld, pos=pos, zones=zones, rej=set(ctx.rejected)), open(out, "wb"))
    print("ok", len(towns), len(zones))

main(sys.argv[1])
