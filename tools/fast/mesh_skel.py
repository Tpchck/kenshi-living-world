"""Совместимость скелетов брони с основой (баг «растяжка на редких анимациях»).

Одежда в Kenshi делит экземпляр скелета персонажа: индекс кости в весах вершин меша должен означать ту же кость,
что и в ванильном male_skeleton / female_skeleton. Если меш сделан под другой скелет (другой порядок/набор костей),
на анимациях, которые двигают «лишние» кости (редкие анимации из паков), вершины тянутся.

Проверка на меш: веса вершин (чанки 0x4100/0x7000 по 16 байт) → использованные индексы костей → имена по скелету,
на который ссылается меш (0x6000), → сравнение с ванильным скелетом того же индекса.
python -I -X utf8 tools/fast/mesh_skel.py <папка мода> [...]   (или импорт: check_mesh(path, search_dirs))
"""
import functools
import os
import re
import struct
import sys

KD = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
VANILLA_SKEL = {"male": os.path.join(KD, "character", "meshes", "male_skeleton", "male_skeleton.skeleton"),
                "female": os.path.join(KD, "character", "meshes", "female_skeleton", "female_skeleton.skeleton")}
BA = re.compile(rb"(?:\x00\x41|\x00\x70)\x10\x00\x00\x00(.{4})(.{2})(.{4})", re.S)
BONE = re.compile(rb"\x00\x20.{4}([\x20-\x7e]{1,80})\n(.{2})", re.S)
NAME_OK = re.compile(r"^[A-Za-z][\w .\-]{1,79}$")
LINK = re.compile(rb"\x00\x60.{4}([\x20-\x7e]{1,200}\.skeleton)\n", re.S)


@functools.lru_cache(maxsize=None)
def skeleton_bones(path):
    """{handle: имя} из бинарного .skeleton (плоские чанки верхнего уровня, SKELETON_BONE = 0x2000)."""
    b = open(path, "rb").read()
    bones = {}
    for m in BONE.finditer(b):   # длина чанка в старых сериализаторах ненадёжна — ищем сами чанки костей;
        h = struct.unpack("<H", m.group(2))[0]   # отсекаем мусорные совпадения в данных анимаций
        name = m.group(1).decode("latin-1")
        if h < 512 and NAME_OK.match(name):
            bones.setdefault(h, name)
    return bones


def mesh_info(path):
    b = open(path, "rb").read()
    m = LINK.search(b)
    used = set()
    for mm in BA.finditer(b):
        w = struct.unpack("<f", mm.group(3))[0]
        if 0.0 <= w <= 1.0001:
            used.add(struct.unpack("<H", mm.group(2))[0])
    return (m.group(1).decode("ascii") if m else None), used


@functools.lru_cache(maxsize=None)
def _index(d):
    out = {}
    for dp, _, fs in os.walk(d):
        for f in fs:
            if f.lower().endswith(".skeleton"):
                out.setdefault(f.lower(), os.path.join(dp, f))
    return out


def find_skeleton(name, search_dirs):
    for d in list(search_dirs) + [os.path.join(KD, "character"), os.path.join(KD, "items")]:
        p = _index(d).get(os.path.basename(name).lower())
        if p:
            return p
    return None


def norm(n):
    return n.replace("Bip001", "Bip01").lower()


def check_mesh(path, search_dirs):
    """None — совместим/статичный; иначе строка-причина."""
    link, used = mesh_info(path)
    if not used:
        return None  # статичный меш (крепится к кости целиком) — растяжки нет
    if not link:   # так сделана ванильная одежда: индекс кости = индекс в скелете персонажа
        n = min(len(skeleton_bones(v)) for v in VANILLA_SKEL.values())
        base = os.path.splitext(path)[0]
        if max(used) < n or any(os.path.exists(base + x) for x in (".skeleton", ".mesh.skeleton")):
            return None   # свой скелет рядом (плащи с костями ткани, как в ванили)
        return f"индекс кости {max(used)} ≥ {n} (костей у персонажа), без ссылки на скелет"
    sp = find_skeleton(link, search_dirs)
    if not sp:
        return f"скелет {link} не найден"
    mine = skeleton_bones(sp)
    best = None
    for g, vp in VANILLA_SKEL.items():
        van = skeleton_bones(vp)
        bad = sorted(i for i in used if i not in mine or i not in van or norm(mine[i]) != norm(van[i]))
        if best is None or len(bad) < len(best[1]):
            best = (g, bad, van)
    g, bad, van = best
    if not bad:
        return None
    ex = ", ".join(f"{i}:{mine.get(i, '?')}≠{van.get(i, '—')}" for i in bad[:4])
    return f"{len(bad)}/{len(used)} костей не как у {g}_skeleton ({ex})"


if __name__ == "__main__":
    for root in sys.argv[1:]:
        n = bad = 0
        for dp, _, fs in os.walk(root):
            for f in fs:
                if f.lower().endswith(".mesh"):
                    n += 1
                    r = check_mesh(os.path.join(dp, f), [root])
                    if r:
                        bad += 1
                        print(" ", os.path.relpath(os.path.join(dp, f), root), "—", r)
        print(f"{root}: мешей {n}, несовместимых {bad}")
