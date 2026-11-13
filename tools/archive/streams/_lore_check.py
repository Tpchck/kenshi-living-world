"""Офлайн-проверка ветки «What is the word?» (поток diplo): у каждого затронутого CHARACTER сохранились все исходные ссылки
«dialogue» и «dialogue package» (с учётом того, как итоговая запись = исходная + дельта KMM_Diplo), ванильные диалоги и KMM Diplomacy на месте.
python -I -X utf8 tools/streams/_lore_check.py   (~1-2 мин на загрузку цепочки; читает build/KMM_Diplo/KMM_Diplo.mod)"""
import os, sys
ROOT = r"C:\KenshiModMap"
for sub in ("tools", r"tools\build", r"tools\streams"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import kmm_build  # noqa: E402
import kmod  # noqa: E402

c = kmm_build.Ctx()
M = c.M
mod = kmod.read(os.path.join(ROOT, "build", "KMM_Diplo", "KMM_Diplo.mod"))
W = {i.sid: i for i in mod.items}
fails, n, lore_n, seal_n = [], 0, 0, 0
for it in mod.items:
    if it.type_name != "CHARACTER":
        continue
    n += 1
    base = M.get(it.sid)
    if base is None:
        fails.append(("нет базовой записи", it.sid))
        continue
    delta = {r.target for r in it.refs.get("dialogue", [])}
    orig = {r.target for r in base.refs.get("dialogue", [])}
    # дельта должна содержать только новые диалоги KMM или (если полная замена) надмножество исходных
    new_only = delta - orig
    bad_new = [t for t in new_only if t not in W or W[t].type_name != "DIALOGUE"]
    if bad_new:
        fails.append(("ссылка не на DIALOGUE мода", base.name, bad_new))
    if set(it.refs) - {"dialogue"}:
        fails.append(("изменена не только категория dialogue", base.name, sorted(set(it.refs) - {"dialogue"})))
    if it.values:
        fails.append(("изменены значения", base.name))
    # итог: исходные не потеряны? (если дельта = полный список, то orig <= delta; если только добавка — исходные остаются в базе)
    full = orig <= delta
    only_add = not (delta & orig) or full
    if not only_add:
        fails.append(("частичная перезапись списка", base.name))
    lore_n += any(W[t].name.startswith("KMM Lore") for t in new_only if t in W)
    seal_n += any(W[t].name == "KMM Diplomacy" for t in new_only if t in W)
    pk0 = {r.target for r in base.refs.get("dialogue package", [])}
    if "dialogue package" in it.refs and {r.target for r in it.refs["dialogue package"]} != pk0:
        fails.append(("dialogue package изменён", base.name))
print(f"персонажей в KMM_Diplo: {n}; с веткой Lore: {lore_n}; с печатью посланника: {seal_n}")
print("FAIL" if fails else "OK", fails[:10])
