import sys, json, struct; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
O = r"C:\KenshiModMap\tools\spike1\out\\"
ocs = {f["file"]: f["items"] for f in json.load(open(O+"ocs_dump.json", encoding="utf-8"))}
def f32(v): return struct.unpack("<f", struct.pack("<f", v))[0] if isinstance(v, float) else v
def sem(m): return [(i.sid, i.type, i.name, i.save_data, {k: f32(v) for k, v in i.values.items()},
                     {c: [(r.target, r.v0, r.v1, r.v2) for r in rs] for c, rs in i.refs.items()},
                     [(x.id, x.target, x.pos, x.rot, x.states) for x in i.instances]) for i in m.items]
for fn in ["KMM_Spike1.mod", "rebirth.mod"]:
    km = kmod.read(O + "ocs\\" + fn)
    oc = ocs[fn]
    # 1) OCS видит то же, что kmod
    ok = len(km.items) == len(oc) and all(
        (a.sid, a.type, a.name, a.change, len(a.values), {k: len(v) for k, v in a.refs.items() if v}) ==
        (b["sid"], b["type"], b["name"], b["change"], b["nvalues"], {k: v for k, v in b["refs"].items() if v})
        for a, b in zip(km.items, oc))
    # 2) kmod читает вывод OcsWriter, содержимое семантически то же (OCS сортирует значения)
    back = kmod.read(O + "ocs\\" + fn + ".ocs")
    same = [(s[0], s[1], s[2], s[3], sorted(s[4].items()), s[5], s[6]) for s in sem(back)] == \
           [(s[0], s[1], s[2], s[3], sorted(s[4].items()), s[5], s[6]) for s in sem(km)]
    print(f"{fn}: OCS==kmod по составу: {ok};  kmod(read OCS-write)==исходник по смыслу: {same}")
spk = ocs["KMM_Spike1.mod"]
print("удалённых ссылок по версии OCS:", {i["sid"]: i["deletedRefs"] for i in spk if i["deletedRefs"]})
