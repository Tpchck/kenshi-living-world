"""Регион (BIOME_GROUP) по мировым координатам: data/newland/land/areasmap.tga, цвет пикселя = BIOME_GROUP.index (0xRRGGBB).
Мир 64 зоны x 4608 ед., начало -147456 -> 1152 ед. на пиксель, без переворота по z (сверено: Admag=Stenn Desert, Heng=Heng,
Mud Town/Shark=The Swamp, Squin/The Hub=Border Zone, Mongrel=Fog Islands). Только чтение.
    rm = areas.RegionMap(M); rm.at(x, z) -> Item BIOME_GROUP | None; rm.adj[name] -> set соседних имён"""
import collections
import os

AREAS = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\newland\land\areasmap.tga"
ORIGIN, PX = 147456, 1152


def pix(x, z):
    return max(0, min(255, int((x + ORIGIN) / PX))), max(0, min(255, int((z + ORIGIN) / PX)))


class RegionMap:
    def __init__(self, M, path=AREAS):
        from PIL import Image
        im = Image.open(path).convert("RGB")
        self.W, self.H = im.size
        self.by_color = {}
        for t in M.values():
            if t.type_name == "BIOME_GROUP" and not t.values.get("REMOVED"):
                self.by_color.setdefault(int(t.values.get("index", 0)) & 0xFFFFFF, t)
        self.cell = [[None] * self.H for _ in range(self.W)]
        for x in range(self.W):
            for y in range(self.H):
                r, g, b = im.getpixel((x, y))
                self.cell[x][y] = self.by_color.get((r << 16) | (g << 8) | b)
        self.adj = collections.defaultdict(set)
        for x in range(self.W):
            for y in range(self.H):
                a = self.cell[x][y]
                if not a or a.name == "NONE":
                    continue
                for dx, dy in ((1, 0), (0, 1)):
                    if x + dx < self.W and y + dy < self.H:
                        b = self.cell[x + dx][y + dy]
                        if b and b is not a and b.name != "NONE":
                            self.adj[a.name].add(b.name); self.adj[b.name].add(a.name)

    def at(self, x, z):
        px, pz = pix(x, z)
        t = self.cell[px][pz]
        return None if (t is None or t.name == "NONE") else t
