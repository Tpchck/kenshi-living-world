"""Офлайн-проверка потока DIPLO после правки отбора посланников и дерева (журнал docs/journal/DIPLO_DLG.md).
python -I -X utf8 tools/streams/_diplo_dlg_check.py   (читает собранный build/KMM_Diplo/KMM_Diplo.mod и kmm_diplo_data.lua; ~1 мин на загрузку цепочки)"""
import collections
import os
import re
import sys

ROOT = r"C:\KenshiModMap"
for sub in ("tools", r"tools\build", r"tools\fast", r"tools\streams"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import kmm_build  # noqa: E402
import kmod  # noqa: E402

c = kmm_build.Ctx()
M = c.M


def envoys_of(path):
    txt = open(path, encoding="utf-8").read()
    blk = txt.split('["envoys"] = {')[1].split('["params"]')[0]
    return dict(re.findall(r'\["([^"]+)"\] = "([^"]*)"', blk))


def pkg_dialogs(psid, seen):
    if psid in seen or psid not in M:
        return []
    seen.add(psid)
    out = []
    for cat, rs in M[psid].refs.items():
        if cat == "dialogs":
            out += [(r.target, r.v0) for r in rs]
        elif cat == "inheritsFrom":
            for r in rs:
                out += pkg_dialogs(r.target, seen)
    return out


def has_trade(d, seen, W):
    if d in seen or d not in W:
        return False
    seen.add(d)
    for r in W[d].refs.get("effects", []):
        a = W.get(r.target)
        if a is not None and a.values.get("action name") == 1:
            return True
    return any(has_trade(r.target, seen, W) for r in W[d].refs.get("lines", []))


new = envoys_of(os.path.join(ROOT, "build", "KMM_Diplo", "scripts", "kmm_diplo_data.lua"))
_pre = os.path.join(ROOT, "build", "KMM_Diplo", "_dev", "kmm_diplo_data.lua.pre_dlg.txt")
old = envoys_of(_pre) if os.path.exists(_pre) else dict(new)   # снимок «до» удалён чисткой _dev — сравнение пропускается
mod = kmod.read(os.path.join(ROOT, "build", "KMM_Diplo", "KMM_Diplo.mod"))
W = dict(M)
for it in mod.items:
    W[it.sid] = it
dlg = next(i for i in mod.items if i.type_name == "DIALOGUE" and i.name == "KMM Diplomacy")
fails = []
# 1. по реальным ссылкам «dialogue» в собранном моде (а не по data.lua)
linked = [it.sid for it in mod.items if it.type_name == "CHARACTER" and any(r.target == dlg.sid for r in it.refs.get("dialogue", []))]
if set(linked) != set(new):
    fails.append(f"ссылки dialogue ({len(linked)}) != envoys в data.lua ({len(new)})")
bad = []
for sid in linked:
    if sid not in M:   # персонаж из более раннего потока (KMM_Elite) — в ванильном контексте его нет
        continue
    ch = M[sid]
    ds = [d for r in ch.refs.get("dialogue package", []) for d, v0 in pkg_dialogs(r.target, set()) if v0 == 1]
    ds += [r.target for r in ch.refs.get("dialogue", []) if r.target in M and r.target != dlg.sid]
    if any(has_trade(d, set(), W) for d in ds):
        bad.append((sid, ch.name))
if bad:
    fails.append(f"посланники с торговым пакетом: {bad}")
nm = [(s, M[s].name) for s in linked if s in M and re.search(r"barman|trader|seller|merchant|shopkeep|vendor|dealer", M[s].name, re.I)]
if nm:
    fails.append(f"торговые имена среди посланников: {nm}")
# 2. корень
roots = [r.target for r in dlg.refs["lines"]]
assert len(roots) == 1
greet = W[roots[0]]
_dtxt = open(os.path.join(ROOT, "build", "KMM_Diplo", "scripts", "kmm_diplo_data.lua"), encoding="utf-8").read()
twins = set(re.findall(r'\["([^"]+)"\] = \{[^{}]*\["twin"\] = true', _dtxt))   # S4: близнецы без жетона — взаимоисключающие с оригиналом
n_root = len([r for r in greet.refs.get("lines", []) if r.target not in twins])
if n_root > 4:
    fails.append(f"у корня {n_root} реплик игрока")
# 3. Lua-карта: все id реплик существуют, ролей достаточно
txt = open(os.path.join(ROOT, "build", "KMM_Diplo", "scripts", "kmm_diplo_data.lua"), encoding="utf-8").read()
ids = re.findall(r'^ {2}\["([^"]+)"\] = \{\n\s+\["role"\]', txt, re.M)
missing = [i for i in ids if i not in W]
roles = collections.Counter(re.findall(r'\["role"\] = "(\w+)"', txt))
if missing:
    fails.append(f"id реплик в data.lua нет в моде: {missing[:5]}")


def fname(f):
    return M[f].name if f in M else (f or "(фракция в рантайме)")


def byf(e):
    return collections.Counter(fname(f) for f in e.values())


bo, bn = byf(old), byf(new)
print(f"посланников: было {len(old)}, стало {len(new)}; фракций (с фракцией в данных): {len(set(old.values()) - {''})} -> {len(set(new.values()) - {''})}")
print("корень: реплик игрока", n_root, "| роли Lua:", dict(roles))
lost = sorted(set(bo) - set(bn))
print("фракции, потерявшие всех посланников:", lost)
print("по фракциям (было -> стало):")
for f in sorted(set(bo) | set(bn)):
    if bo[f] != bn[f]:
        print(f"   {f}: {bo[f]} -> {bn[f]}")
gone = [(s, M[s].name, fname(old[s])) for s in old if s not in new]
came = [(s, M[s].name, fname(new[s])) for s in new if s not in old]
print("убраны:", len(gone)); [print("   -", g[1], "|", g[2], "|", g[0]) for g in gone]
print("добавлены взамен:", len(came)); [print("   +", g[1], "|", g[2], "|", g[0]) for g in came]
print("FAIL" if fails else "OK", fails)
sys.exit(1 if fails else 0)
