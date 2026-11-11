import json, sys, collections
sys.path.insert(0, r"C:\KenshiModMap\tools")
_src = open(r"C:\KenshiModMap\tools\cults.py", encoding="utf-8").read().split("if __name__")[0]
exec(_src)
cols = json.load(open(r"C:\KenshiModMap\data\collections.json"))
TOP = ["2822248814", "2983145281", "3276600292"]
our = set(cols["2839009285"])
cnt = collections.Counter(m for c in TOP for m in set(cols[c]))
cult = [m for m, n in cnt.items() if n >= 2]
d = details(cult)
rows = []
for m in cult:
    it = d.get(m, {})
    if it.get("result") != 1 or it.get("file_size", "0") in ("0", 0):
        continue  # коллекции-разделители/удалённые
    rows.append((cnt[m], int(it.get("subscriptions", 0)), m, it.get("title", "?")[:60], m in our))
rows.sort(key=lambda r: (-r[0], -r[1]))
inall = [r for r in rows if r[0] == 3]
print(f"культовых (>=2 из 3): {len(rows)} | во всех 3: {len(inall)} | из них уже в нашей сборке: {sum(r[4] for r in rows)}")
print("== НЕТ в нашей сборке (кандидаты), по числу коллекций и подписчикам:")
for n, s, m, t, ours in rows:
    if not ours:
        print(f"{n} | {s:>7} | {m} | {t}")
json.dump(rows, open(r"C:\KenshiModMap\data\cults.json", "w", encoding="utf-8"), ensure_ascii=False)
