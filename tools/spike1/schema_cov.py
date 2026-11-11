import sys, pickle, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod, fcsdef
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
ctx = kmod.load_chain([K + f for f in ["gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"]])
sch = fcsdef.load(r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi")
print("types in schema:", len(sch.fields), "fields:", sum(len(v) for v in sch.fields.values()))
E, W = [], []
for it in ctx.values():
    e, w = fcsdef.validate(it, sch, resolve=ctx.get); E += e; W += w
print("vanilla items", len(ctx), "errors", len(E), "warnings", len(W))
kinds = collections.Counter(x.split(": ",1)[1].split(" ")[0] if "не найдено" not in x else "missing-target" for x in E)
for x in E[:12]: print("  E", x)
c = collections.Counter()
for x in E:
    if "не найдено" in x: c["битая ссылка"] += 1
    elif "тип" in x and "ждали" in x: c["тип цели"] += 1
    else: c["тип значения"] += 1
print(c)
print([x for x in E if "ожидается" in x])
print(collections.Counter(x.split("нет в схеме ")[-1] for x in W).most_common(8))
