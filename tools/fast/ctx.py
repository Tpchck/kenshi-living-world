"""Слитый контекст: ваниль → основа (713) → WH."""
import json, os, pickle, sys, time
sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
OUT = os.path.join(os.path.dirname(__file__), "out")
DATA = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/"
VANILLA = ["gamedata.base", "Newwworld.mod", "Dialogue.mod", "rebirth.mod"]


def mods(path_list):
    """[(имя, ModFile|None, ошибка)] с кэшем по (путь, mtime, размер)."""
    # кэш на диске отключён: 727 файлов дают ~1.9 ГБ pickle, а разбор без кэша ~11 с
    res = []
    for name, p in path_list:
        try:
            res.append((name, kmod.read(p), None))
        except Exception as e:
            res.append((name, None, f"{type(e).__name__}: {e}"[:200]))
    return res


def load(with_wh=True):
    lo = json.load(open(os.path.join(OUT, "final_lo.json"), encoding="utf-8"))
    van = mods([(v, DATA + v) for v in VANILLA])
    base = mods([(b["file"], b["path"]) for b in lo["base"]])
    wh = mods([(w["file"], w["path"]) for w in lo["wh"] + lo.get("extra", [])]) if with_wh else []   # WH-слой + доп. моды (EXTRA в lo.py)
    return lo, van, base, wh


if __name__ == "__main__":
    t = time.time(); lo, van, base, wh = load()
    bad = [(n, e) for n, m, e in base + wh if m is None]
    print(f"read {len(van)+len(base)+len(wh)} files in {time.time()-t:.1f}s; failures {len(bad)}")
    for b in bad[:20]: print("  ", b)
    import collections
    print("file types:", collections.Counter(m.ftype for n, m, e in base if m))
