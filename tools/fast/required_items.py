"""CHECKLIST п.2: Required items со страниц Workshop (Web API без ключа их не отдаёт)."""
import json, os, re, time, urllib.request, concurrent.futures as cf
OUT = os.path.join(os.path.dirname(__file__), "out")
W = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860"
ids = sorted(os.listdir(W))
cache_p = os.path.join(OUT, "required_items.json")
cache = json.load(open(cache_p, encoding="utf-8")) if os.path.exists(cache_p) else {}
RX = re.compile(r'id="RequiredItems">(.*?)</div>\s*</div>', re.S)
IT = re.compile(r'filedetails/\?id=(\d+)"[^>]*>\s*<div class="requiredItem">\s*(.*?)\s*</div>', re.S)


def get(i):
    for attempt in range(6):
        try:
            req = urllib.request.Request(f"https://steamcommunity.com/sharedfiles/filedetails/?id={i}", headers={"User-Agent": "Mozilla/5.0"})
            s = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            m = RX.search(s)
            return i, ([[a, b.strip()] for a, b in IT.findall(m.group(1))] if m else []), None
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(10 * (attempt + 1)); continue
            return i, None, f"HTTP {e.code}"
        except Exception as e:
            time.sleep(3); err = str(e)
    return i, None, "retries exhausted"


todo = [i for i in ids if i not in cache]
with cf.ThreadPoolExecutor(4) as ex:
    for n, (i, items, err) in enumerate(ex.map(get, todo), 1):
        if items is not None: cache[i] = items
        if n % 100 == 0: json.dump(cache, open(cache_p, "w", encoding="utf-8"), ensure_ascii=False)
json.dump(cache, open(cache_p, "w", encoding="utf-8"), ensure_ascii=False)
have = set(ids)
withreq = {k: v for k, v in cache.items() if v}
unmet = {k: [x for x in v if x[0] not in have] for k, v in withreq.items() if any(x[0] not in have for x in v)}
print(f"pages ok {len(cache)}/{len(ids)} | mods with Required items {len(withreq)} | unmet {len(unmet)}")
pfd = json.load(open(os.path.join(OUT, "pfd_all.json"), encoding="utf-8"))
for k, v in unmet.items(): print(f"  {k} {pfd.get(k, {}).get('title', '?')[:45]} ← {v}")
