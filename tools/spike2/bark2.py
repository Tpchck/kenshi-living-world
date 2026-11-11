import sys, glob, os, collections; sys.path.insert(0, r"C:\KenshiModMap\tools")
import kmod
K = "C:/Program Files (x86)/Steam/steamapps/common/Kenshi/data/newland/leveldata/"
lv = kmod.read(K + "rebirth/leveldata.level")
st = next(i for i in lv.items if i.sid == "142-rebirth-INGAME-S5e")
print("TOWN STATE:", st.type_name, st.name, st.values, st.refs)
tl = next(i for i in lv.items if i.type_name == "GAMESTATE_TOWN_INSTANCE_LIST")
print("townlist:", tl.sid, tl.name, len(tl.instances), tl.values, tl.refs)
hits = collections.Counter()
for f in glob.glob(K + "*/*.zone"):
    raw = open(f, "rb").read()
    if b"142-rebirth-INGAME" in raw: hits[os.path.relpath(f, K)] += raw.count(b"142-rebirth-INGAME")
print("zones mentioning town id:", hits.most_common(10))
