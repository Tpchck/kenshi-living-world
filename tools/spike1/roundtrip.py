import sys, time, collections, hashlib
sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data"
for fn in ["gamedata.base", "Newwworld.mod", "rebirth.mod", "Dialogue.mod"]:
    raw = open(f"{K}\{fn}", "rb").read()
    t = time.time(); m = kmod.read(raw); t1 = time.time() - t
    t = time.time(); out = kmod.write(m); t2 = time.time() - t
    same = out == raw
    h = m.header
    print(f"{fn}: type={m.ftype} items={len(m.items)} lastId={m.last_id} read={t1:.2f}s write={t2:.2f}s identical={same}")
    if h: print(f"   hdr v={h.version} author={h.author!r} deps={h.dependencies} refs={h.references} merge={h.has_merge_block} saveCount={h.save_count} lastMerge={h.last_merge} me={h.merge_entries[:3]} del={len(h.delete_requests)} tail={len(h.tail)}")
    if not same:
        i = next(i for i,(a,b) in enumerate(zip(raw,out)) if a!=b) if len(raw)==len(out) else min(len(raw),len(out))
        print("   first diff at", i, len(raw), len(out))
    ch = collections.Counter(it.change for it in m.items)
    print("   change types:", dict(ch))
    if fn == "gamedata.base":
        c = collections.Counter(it.type_name for it in m.items)
        print("   ", c.most_common(40))
