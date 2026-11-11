import re, sys
data = open(sys.argv[1], "rb").read()
pat = re.compile(rb"[\x20-\x7e]{5,}")
keys = [b"leveldata", b".zone", b"townlist", b"buildinglist", b"newland", b"INGAME", b".level", b"zone."]
seen = set()
for m in pat.finditer(data):
    s = m.group()
    if any(k in s.lower() for k in [k.lower() for k in keys]) and s not in seen:
        seen.add(s); print(s.decode())
