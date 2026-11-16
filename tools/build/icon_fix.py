"""ICON_FIX (2026-11-16, owner: Southern Bee Larva has no icon): some mods ship inventory icons of 1600-2500 px
(Buzzing, Metro, TEXT TEXTURE, 40K Necrons). The game shows the small ones and leaves the huge ones blank
(Western Bee Larva 113x174 shows, Southern Bee Larva 1672x2508 does not). KMM_Fix gets a downscaled copy
(longest side <= MAX) under build/KMM_Fix/icons/<mod folder>/<same path>, and the item's 'icon' points there.
Source mods are never touched. Pure data change: safe for an ongoing save."""
import os
import re
import struct

KENSHI = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"
WORKSHOP = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
OUT_REL = "./mods/KMM_Fix/icons/"

_DIRS = None


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


def dims(path):
    try:
        with open(path, "rb") as f:
            b = f.read(32)
    except OSError:
        return None
    if b[1:4] == b"PNG":
        return struct.unpack(">II", b[16:24])
    return None   # dds/other: leave as is


def resolve(icon):
    m = re.match(r"\.[/\\]mods[/\\]([^/\\]+)[/\\](.+)", icon or "")
    if not m or m.group(1).lower() == "kmm_fix":
        return None
    d = mod_dirs().get(m.group(1).lower())
    if not d:
        return None
    rel = m.group(2).replace("\\", "/")
    p = os.path.join(d, *rel.split("/"))
    return (m.group(1), rel, p) if os.path.isfile(p) else None


def run(items, out_dir, limit=1024, target=512):
    """items: iterable of (sid, icon). Returns {sid: new icon value}, stats."""
    from PIL import Image
    new, st = {}, {"checked": 0, "big": 0, "written": 0, "cached": 0, "failed": 0}
    for sid, icon in items:
        r = resolve(icon)
        if not r:
            continue
        st["checked"] += 1
        mod, rel, src = r
        wh = dims(src)
        if not wh or max(wh) <= limit:
            continue
        st["big"] += 1
        dst = os.path.join(out_dir, mod, *rel.split("/"))
        dst = os.path.splitext(dst)[0] + ".png"
        if os.path.isfile(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            st["cached"] += 1
        else:
            try:
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                im = Image.open(src).convert("RGBA")
                k = target / float(max(im.size))
                im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))), Image.LANCZOS)
                im.save(dst, "PNG", optimize=True)
                st["written"] += 1
            except Exception:
                st["failed"] += 1
                continue
        new[sid] = OUT_REL + mod + "/" + os.path.splitext(rel)[0] + ".png"
    return new, st
