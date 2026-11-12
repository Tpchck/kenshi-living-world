"""Рубильники: rules/features.json -> существующие места (Lua-код не меняется).

native.enabled/ws_hook/faction_force/tooltip_compact -> build/KMM_Native/kmm_native.json
ore_campaign                          -> conductor params.links2.ore_campaign.enabled
links2 / traces / self                -> conductor params.links2.enabled / params.traces.enabled / params.self.enabled
   (conductor: rules/conductor.json и копия build/KMM_Conductor/conductor.json, которую читает Lua)
slots_ext / dedup_pools               -> rules/streams/wardrobe.json (ключ enabled в секции)
merge                                 -> rules/merge.json enabled

apply() идемпотентна: пишет файл только если значение изменилось, сохраняя формат файла (отступ, переводы строк).
python tools\build\features.py   — показать/разложить.
"""
import json
import os
import sys

ROOT = r"C:\KenshiModMap"
FEATURES = os.path.join(ROOT, "rules", "features.json")


def _load_exact(path):
    """-> (data, writer) где writer(data) сохраняет в том же формате, что был в файле."""
    raw = open(path, "rb").read().decode("utf-8")
    data = json.loads(raw)
    style = None
    for ind in (None, 1, 2, 4, "\t"):
        for nl in ("\n", "\r\n"):
            for tail in ("", "\n", "\r\n"):
                s = json.dumps(data, ensure_ascii=False, indent=ind)
                if ind is not None:
                    s = s.replace("\n", nl)
                if s + tail == raw:
                    style = (ind, nl, tail)
                    break
            if style:
                break
        if style:
            break
    if style is None:
        style = (1, "\r\n", "")
    ind, nl, tail = style

    def writer(d):
        s = json.dumps(d, ensure_ascii=False, indent=ind)
        if ind is not None:
            s = s.replace("\n", nl)
        open(path, "wb").write((s + tail).encode("utf-8"))
    return data, writer


def load():
    return json.load(open(FEATURES, encoding="utf-8"))


def _set(path, setter):
    """setter(data) -> список изменений (строки); пусто = ничего не писать."""
    if not os.path.exists(path):
        return []
    data, w = _load_exact(path)
    ch = setter(data)
    if ch:
        w(data)
    return [f"{os.path.relpath(path, ROOT)}: {c}" for c in ch]


def _key(d, key, val, label):
    if d.get(key) != val:
        old = d.get(key)
        d[key] = val
        return [f"{label} {old} -> {val}"]
    return []


def apply():
    """-> список изменённых мест (пусто, если всё уже совпадает)."""
    f = load()
    out = []
    n = f.get("native", {})
    out += _set(os.path.join(ROOT, "build", "KMM_Native", "kmm_native.json"),
                lambda d: sum((_key(d, k, bool(n[k]), k) for k in ("enabled", "ws_hook", "faction_force", "tooltip_compact") if k in n), []))

    def cond(d):
        p = d["params"]
        ch = []
        if "ore_campaign" in f:
            ch += _key(p.setdefault("links2", {}).setdefault("ore_campaign", {}), "enabled", bool(f["ore_campaign"]), "ore_campaign")
        for k in ("links2", "traces", "self"):
            if k in f and k in p:
                ch += _key(p[k], "enabled", bool(f[k]), k)
        return ch
    out += _set(os.path.join(ROOT, "rules", "conductor.json"), cond)
    out += _set(os.path.join(ROOT, "build", "KMM_Conductor", "conductor.json"), cond)
    out += _set(os.path.join(ROOT, "rules", "streams", "wardrobe.json"),
                lambda d: sum((_key(d[k], "enabled", bool(f[k]), k) for k in ("slots_ext", "dedup_pools") if k in f and k in d), []))
    if "merge" in f:
        out += _set(os.path.join(ROOT, "rules", "merge.json"), lambda d: _key(d, "enabled", bool(f["merge"]), "merge"))
    return out


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ch = apply()
    print("\n".join("изменено: " + c for c in ch) if ch else "рубильники уже совпадают с rules/features.json")
