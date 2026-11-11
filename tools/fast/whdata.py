import sys, collections, pickle, json
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, ctx
M = pickle.load(open(ctx.OUT + "/merged.pkl", "rb"))
lo, van, base, wh = ctx.load()
whnew = {}
for n, m, _ in wh:
    for it in m.items:
        if it.change == 0: whnew[it.sid] = n
refby = collections.defaultdict(list)
for it in M.values():
    for cat, rs in it.refs.items():
        for r in rs: refby[r.target].append((it.type_name, cat, it.name))
nm = lambda s: M[s].name if s in M else "?"
for n in ["wh40k_imperial_forces.mod", "Death Korps of Krieg.mod", "Steel Legion Armor Mod.mod", "OrcRaceReview.mod", "40K Necrons.mod", "TEXT TEXTURE.mod"]:
    sq = [M[s] for s, f in whnew.items() if f == n and s in M and M[s].type_name == "SQUAD_TEMPLATE"]
    print(f"== {n}: squads {len(sq)}")
    for s in sq[:12]:
        users = collections.Counter((t, c) for t, c, _ in refby[s.sid])
        print(f"   {s.name[:40]:<40} fac={[nm(r.target)[:20] for r in s.refs.get('faction', [])]} used_by={dict(users)}")
    fac = [M[s] for s, f in whnew.items() if f == n and s in M and M[s].type_name == "FACTION"]
    for f in fac[:30]:
        print(f"   FACTION {f.name[:30]:<30} type={f.values.get('fundamental type')} squads={len(f.refs.get('squads',[]))} rel={len(f.refs.get('relations',[]))} coex={len(f.refs.get('coexistence',[]))} used_by={len(refby[f.sid])}")
