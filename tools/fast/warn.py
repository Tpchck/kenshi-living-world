import sys, collections, re
sys.path.insert(0, r"C:\KenshiModMap\tools"); sys.path.insert(0, r"C:\KenshiModMap\tools\fast")
import kmod, fcsdef, pickle, ctx
M = pickle.load(open(ctx.OUT + "/merged.pkl", "rb"))
g = kmod.read(r"C:\KenshiModMap\build\KMM_Glue\KMM_Glue.mod")
sch = fcsdef.load(r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi")
c = collections.Counter()
for it in g.items:   # проверяем ТОЛЬКО ключи/категории, которые пишем мы
    fd = sch.for_type(it.type_name)
    for k in it.values:
        if k not in fd: c[("value", it.type_name, k)] += 1
    for k in it.refs:
        if k not in fd: c[("refcat", it.type_name, k)] += 1
print(c.most_common(30))
