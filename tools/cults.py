"""Культовые моды: пересечения популярных коллекций Workshop. Вывод — сводка в stdout + data\cults.json."""
import json, sys, time, urllib.request, urllib.parse, collections, os

API = "https://api.steampowered.com/ISteamRemoteStorage/"
OUR = "2839009285"
CANDS = sys.argv[1:] or ["2822248814", "2983145281", "3211907381", "3276600292", "2850143028", "3658803602", "2967435666"]


def post(method, data):
    body = urllib.parse.urlencode(data).encode()
    return json.load(urllib.request.urlopen(urllib.request.Request(API + method, body), timeout=60))["response"]


def details(ids):
    out = {}
    for i in range(0, len(ids), 100):
        chunk = ids[i:i + 100]
        d = {"itemcount": len(chunk)}
        d.update({f"publishedfileids[{k}]": v for k, v in enumerate(chunk)})
        for it in post("GetPublishedFileDetails/v1/", d).get("publishedfiledetails", []):
            out[it["publishedfileid"]] = it
    return out


def children(cid):
    r = post("GetCollectionDetails/v1/", {"collectioncount": 1, "publishedfileids[0]": cid})
    c = r["collectiondetails"][0]
    return [x["publishedfileid"] for x in c.get("children", [])]


if __name__ != "__main__":
    raise ImportError  # only details() is reused via exec below
meta = details(CANDS + [OUR])
print("== коллекции")
cols = {}
for c in CANDS + [OUR]:
    m = meta.get(c, {})
    try:
        kids = children(c)
    except Exception:
        kids = []
    cols[c] = set(kids)
    print(f"{c} | {m.get('title','?')[:50]} | subs {m.get('subscriptions','?')} | fav {m.get('favorited','?')} | upd {time.strftime('%Y-%m-%d', time.gmtime(m.get('time_updated',0)))} | mods {len(kids)}")
json.dump({k: sorted(v) for k, v in cols.items()}, open(r"C:\KenshiModMap\data\collections.json", "w"), indent=0)
