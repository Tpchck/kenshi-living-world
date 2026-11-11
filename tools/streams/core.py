"""Поток core (интегратор): вернуть значения Pathfinding - Collection Pack, перетёртые WH-слоем (WH_LAYER.md)."""
import struct

f32 = lambda v: struct.unpack("<f", struct.pack("<f", v))[0]  # noqa: E731


def build(ctx, s, rules):
    ra = rules["reassert_base_values"]
    pf = next(m for n, m, _ in ctx.base if n == ra["from_mod"])
    for it in pf.items:
        if it.sid not in ctx.M:
            continue
        vals = {k: v for k, v in it.values.items() if k in ra["keys"] and f32(ctx.M[it.sid].values.get(k, v)) != f32(v)}
        if vals:
            s.change(it.sid, values=vals)
            s.report["reasserted_values"] += len(vals)
