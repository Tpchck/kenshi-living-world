import json, time
exec(open(r"C:\KenshiModMap\tools\cults.py", encoding="utf-8").read().split("if __name__")[0])
cols = json.load(open(r"C:\KenshiModMap\data\collections.json"))
our = set(cols["2839009285"])
cult = {r[2] for r in json.load(open(r"C:\KenshiModMap\data\cults.json", encoding="utf-8"))}
NEW = ["3550504382", "3211907381", "1898460183", "3586168016", "2967435666"]
meta = details(NEW)
for c in NEW:
    kids = set(children(c))
    m = meta.get(c, {})
    rest = sorted(kids - our - cult)
    d = details(rest) if rest else {}
    items = [(int(v.get("subscriptions", 0)), k, v.get("title", "?")[:55]) for k, v in d.items() if v.get("result") == 1 and str(v.get("file_size", "0")) != "0"]
    items.sort(reverse=True)
    print(f"\n== {c} | {m.get('title','?')[:55]} | fav {m.get('favorited','?')} | upd {time.strftime('%Y-%m-%d', time.gmtime(m.get('time_updated',0)))} | mods {len(kids)} | общих с нашей {len(kids & our)} | новых {len(items)}")
    for s, k, t in items[:10]:
        print(f"  {s:>7} | {k} | {t}")
