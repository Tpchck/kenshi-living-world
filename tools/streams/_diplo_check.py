"""Проверка потока DIPLO без правки tools/build/kmm_build.py: подставляет ("diplo", "KMM_Diplo") в DATA_STREAMS перед KMM_Fix,
гоняет общий build() (конфликты полей, fcsdef, битые ссылки, бюджет) и пишет только build/KMM_Diplo/KMM_Diplo.mod.
build/kmm_build_report.json интегратора восстанавливается как был.  python -I -X utf8 tools/streams/_diplo_check.py"""
import collections
import os
import re
import sys
import time

ROOT = r"C:\KenshiModMap"
sys.path.insert(0, os.path.join(ROOT, "tools", "build"))
sys.path.insert(0, os.path.join(ROOT, "tools"))
import fcsdef  # noqa: E402
import kmm_build  # noqa: E402

REPORT = os.path.join(ROOT, "build", "kmm_build_report.json")
t0 = time.time()
if not any(x[0] == "diplo" for x in kmm_build.DATA_STREAMS):   # diplo уже в штатном порядке (до elite) — не переставлять: иначе зависимость от KMM_Elite
    ds = list(kmm_build.DATA_STREAMS)
    fix_at = next((i for i, x in enumerate(ds) if x[0] == "fix"), len(ds))
    kmm_build.DATA_STREAMS = ds[:fix_at] + [("diplo", "KMM_Diplo")] + ds[fix_at:]
import mods_cfg  # noqa: E402
_check = mods_cfg.check


def check(lines):   # свой мод на диске может быть устаревшим (его и пересобираем): его ошибки порядка — не повод не писать
    e, w, u = _check(lines)
    return [x for x in e if not x.startswith("KMM_Diplo.mod:")], w, u


mods_cfg.check = check

warns = collections.Counter()
_validate = fcsdef.validate


def validate(item, sch, resolve=None):
    e, w = _validate(item, sch, resolve)
    if item.sid.endswith("KMM_Diplo.mod"):
        for x in w:
            warns[re.sub(r"^[^:]*: ", "", x)] += 1
    return e, w


fcsdef.validate = validate
kmm_build.fcsdef.validate = validate
mine = {}
_write = kmm_build.kmod.write


def write(m, path=None):   # перехват байтов своего мода: чужие ошибки (другие потоки) не мешают записать KMM_Diplo
    data = _write(m, path)
    if getattr(m.header, "description", "") == "KMM stream: diplo":
        mine["data"] = data
    return data


kmm_build.kmod.write = write
saved = open(REPORT, "rb").read() if os.path.exists(REPORT) else None
code = 0
try:
    rep = kmm_build.run(write=["diplo"])
except SystemExit:
    import json
    rep = json.load(open(REPORT, encoding="utf-8"))
finally:
    if saved is not None:
        open(REPORT, "wb").write(saved)
errs = rep["errors"]
my_errs = [e for e in errs if e.startswith("KMM_Diplo:") or ("КОНФЛИКТ" in e and "'diplo'" in e)]
other = len(errs) - len(my_errs)
if my_errs:
    code = 1
elif mine.get("data"):
    open(os.path.join(ROOT, "build", "KMM_Diplo", "KMM_Diplo.mod"), "wb").write(mine["data"])
print("\n=== DIPLO CHECK ===")
print("warnings on KMM_Diplo records (ожидаются только LUA_SCRIPT/«run lua script» и DIALOG_ACTION вне fcs.def игры):")
for k, n in warns.most_common():
    print(f"  {n:5d}  {k}")
me = next((x for x in rep["streams"] if x["stream"] == "diplo"), None)
print("diplo:", me)
print(f"errors: KMM_Diplo {len(my_errs)}, other streams {other} (не наши, на запись KMM_Diplo не влияют)")
for e in my_errs[:20]:
    print("  ", e)
print("KMM_Diplo.mod written:", bool(mine.get("data")) and not my_errs)
print(f"done in {time.time() - t0:.1f}s, exit={code}")
sys.exit(code)
