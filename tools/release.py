"""Снимки установленной сборки и откат одной командой.

python tools\\release.py snapshot          — снимок: Kenshi\\mods\\KMM_* + data\\mods.cfg + data\\__mods.list
python tools\\release.py rollback          — вернуть предыдущий снимок (до последней установки)
python tools\\release.py rollback <имя>    — вернуть конкретный снимок
python tools\\release.py safe              — аварийный режим: mods.cfg без KMM_* (наши моды выключены, основа сборки остаётся)
python tools\\release.py list              — список снимков

kmm_build.py --install сам делает snapshot перед копированием. Ванильные файлы не трогаются.
"""
import os
import shutil
import subprocess
import sys
import time

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = r"C:\KenshiModMap"
GAME = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
MODS = os.path.join(GAME, "mods")
CFG = os.path.join(GAME, "data", "mods.cfg")
REG = os.path.join(GAME, "data", "__mods.list")
SNAP = os.path.join(ROOT, "backup", "releases")
KEEP = 8


def _game_running():
    try:
        out = subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower()
    except Exception:
        return False
    return "kenshi_x64.exe" in out


def _kmm_dirs():
    return sorted(d for d in os.listdir(MODS) if d.startswith("KMM_") and os.path.isdir(os.path.join(MODS, d)))


def snapshot(tag=""):
    stamp = time.strftime("%Y%m%d_%H%M%S") + (f"_{tag}" if tag else "")
    dst = os.path.join(SNAP, stamp)
    os.makedirs(os.path.join(dst, "mods"), exist_ok=True)
    for d in _kmm_dirs():
        shutil.copytree(os.path.join(MODS, d), os.path.join(dst, "mods", d))
    for f in (CFG, REG):
        if os.path.exists(f):
            shutil.copy2(f, os.path.join(dst, os.path.basename(f)))
    snaps = sorted(os.listdir(SNAP))
    for old in snaps[:-KEEP]:
        shutil.rmtree(os.path.join(SNAP, old), ignore_errors=True)
    print("снимок:", dst)
    return stamp


def _list():
    return sorted(os.listdir(SNAP)) if os.path.isdir(SNAP) else []


def rollback(name=None):
    if _game_running():
        sys.exit("Kenshi запущен — закройте игру")
    snaps = _list()
    if not snaps:
        sys.exit("снимков нет")
    if name is None:
        name = snaps[-1]          # последний снимок = состояние до последней установки
    src = os.path.join(SNAP, name)
    if not os.path.isdir(src):
        sys.exit(f"нет снимка {name}; есть: {', '.join(snaps)}")
    snapshot("before_rollback")   # откат тоже обратим
    for d in _kmm_dirs():
        shutil.rmtree(os.path.join(MODS, d))
    for d in sorted(os.listdir(os.path.join(src, "mods"))):
        shutil.copytree(os.path.join(src, "mods", d), os.path.join(MODS, d))
    for f in (CFG, REG):
        b = os.path.join(src, os.path.basename(f))
        if os.path.exists(b):
            shutil.copy2(b, f)
    print("откат на снимок:", name)


def safe():
    if _game_running():
        sys.exit("Kenshi запущен — закройте игру")
    snapshot("before_safe")
    raw = open(CFG, "rb").read().decode("utf-8")
    lines = [l for l in raw.split("\r\n") if l]
    keep = [l for l in lines if not l.startswith("KMM_") or l == "KMM_Merged.mod"]   # KMM_Merged — слитые чужие малые моды, не наши правки
    open(CFG, "wb").write("".join(l + "\r\n" for l in keep).encode("utf-8"))
    print(f"аварийный режим: выключено {len(lines) - len(keep)} модов KMM_*, осталось {len(keep)}")


if __name__ == "__main__":
    a = sys.argv[1:] or ["list"]
    if a[0] == "snapshot":
        snapshot(a[1] if len(a) > 1 else "")
    elif a[0] == "rollback":
        rollback(a[1] if len(a) > 1 else None)
    elif a[0] == "safe":
        safe()
    else:
        print("\n".join(_list()) or "снимков нет")
