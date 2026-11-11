"""Самопроверка: искусственный поток, меняющий запись из ECONOMY, должен остановить сборку."""
import sys, types, json, os
sys.path.insert(0, r"C:\KenshiModMap\tools\build")
import kmm_build
fake = types.ModuleType("zz_fake")
def build(ctx, s, rules):
    sid = next(i.sid for i in ctx.all("CHARACTER") if i.name == "Dust Bandit")
    s.change(sid, values={"money max": 999})
fake.build = build
sys.modules["zz_fake"] = fake
p = r"C:\KenshiModMap\rules\streams\zz_fake.json"
json.dump({}, open(p, "w"))
kmm_build.DATA_STREAMS.append(("zz_fake", "KMM_ZZFake"))
try:
    kmm_build.run()
except SystemExit as e:
    print("EXIT", e.code)
finally:
    os.remove(p)
