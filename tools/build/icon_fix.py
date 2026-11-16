"""ICON_FIX (2026-11-16): inventory icons the game leaves blank, fixed by copies in KMM_Fix.
1) huge icons: some mods ship 1600-2500 px icons (Buzzing, Metro, TEXT TEXTURE, 40K Necrons); the game shows small ones
   and leaves huge ones blank (Western Bee Larva 113x174 shows, Southern Bee Larva 1672x2508 does not) -> downscaled copy
   (longest side <= target).
2) moved icons: the path points into a mod folder that does not hold the file (mod compilations moved 'Side Quest - ...'
   icons) -> the same file name found elsewhere (longest path-tail match) is copied.
Copies go to build/KMM_Fix/icons/<mod folder>/<same path>, and the item's 'icon' points there.
Source mods are never touched. Pure data change: safe for an ongoing save."""
import os
import re
import shutil
import struct

KENSHI = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
WORKSHOP = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
OUT_REL = "./mods/KMM_Fix/icons/"
ICON_RE = re.compile(r"\.[/\\]mods[/\\]([^/\\]+)[/\\](.+)")

_DIRS = None
_FILES = None


def mod_dirs():
    """mod folder name (lower) -> real folder: Kenshi/mods/<name> or the workshop folder holding <name>.mod."""
    global _DIRS
    if _DIRS is None:
        d = {}
        for base in (WORKSHOP, os.path.join(KENSHI, "mods")):
            if not os.path.isdir(base):
                continue
            for sub in os.listdir(base):
                p = os.path.join(base, sub)
                if not os.path.isdir(p):
                    continue
                for f in os.listdir(p):
                    if f.lower().endswith(".mod"):
                        d[f[:-4].lower()] = p
                if base.endswith("mods"):
                    d[sub.lower()] = p
        _DIRS = d
    return _DIRS


def by_name(rel):
    """Same file name elsewhere; the longest matching path tail wins (sorted, so the pick is stable)."""
    global _FILES
    if _FILES is None:
        _FILES = {}
        for base in (WORKSHOP, os.path.join(KENSHI, "mods")):
            for r, _ds, fs in os.walk(base):
                if os.sep + "KMM_" in r:
                    continue
                for f in fs:
                    if f.lower().endswith((".png", ".dds")):
                        _FILES.setdefault(f.lower(), []).append(os.path.join(r, f))
    parts = rel.lower().split("/")
    best, bn = None, -1
    for p in sorted(_FILES.get(parts[-1], [])):
        q = re.split(r"[\\/]", p.lower())
        n = 0
        while n < len(parts) and n < len(q) and parts[-1 - n] == q[-1 - n]:
            n += 1
        if n > bn:
            best, bn = p, n
    return best


def dims(path):
    try:
        with open(path, "rb") as f:
            b = f.read(32)
    except OSError:
        return None
    if b[1:4] == b"PNG":
        return struct.unpack(">II", b[16:24])
    return None   # dds/other: size not checked


def resolve(icon):
    """-> (mod, rel, file, moved) or None."""
    m = ICON_RE.match(icon or "")
    if not m or m.group(1).lower() == "kmm_fix":
        return None
    rel = m.group(2).replace("\\", "/")
    d = mod_dirs().get(m.group(1).lower())
    p = os.path.join(d, *rel.split("/")) if d else None
    if p and os.path.isfile(p):
        return m.group(1), rel, p, False
    q = by_name(rel)
    return (m.group(1), rel, q, True) if q else None


def run(items, out_dir, limit=1024, target=512):
    """items: iterable of (sid, icon). Returns {sid: new icon value}, stats; stats["lost_sids"]: file found nowhere."""
    from PIL import Image
    new = {}
    st = {"checked": 0, "big": 0, "moved": 0, "lost": 0, "written": 0, "cached": 0, "failed": 0}
    lost = []
    for sid, icon in items:
        r = resolve(icon)
        if not r:
            m = ICON_RE.match(icon or "")
            if m and m.group(1).lower() != "kmm_fix":
                st["lost"] += 1
                lost.append(sid)
            continue
        st["checked"] += 1
        mod, rel, src, moved = r
        wh = dims(src)
        big = bool(wh and max(wh) > limit)
        if not (big or moved):
            continue
        st["big" if big else "moved"] += 1
        ext = ".png" if big else os.path.splitext(src)[1]
        rel = os.path.splitext(rel)[0] + ext
        dst = os.path.join(out_dir, mod, *rel.split("/"))
        if os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            st["cached"] += 1
        else:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if big:
                    im = Image.open(src).convert("RGBA")
                    k = target / float(max(im.size))
                    im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
                    im.save(dst, "PNG", optimize=True)
                else:
                    shutil.copyfile(src, dst)
                st["written"] += 1
            except Exception:
                st["failed"] += 1
                continue
        new[sid] = OUT_REL + mod + "/" + rel
    st["lost_sids"] = lost
    return new, st
