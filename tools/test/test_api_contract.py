"""Самопроверка api_audit (B3 И1): контракт движка для аргументов-объектов.
Фикстура KMM_X: литеральный nil в squad (createRandomSquad #6, как Runtime до 2026-11-15) и строка вместо GameData -> нарушение (код 1);
«local gd = nil» с присваиванием только внутри if -> предупреждение; правильные вызовы (как Elite/createItem с nil в weaponMesh) -> чисто.
На живом build/ нарушений сигнатур 0. python -I -X utf8 tools/test/test_api_contract.py -> ALL OK / FAIL (код 1)."""
import os
import subprocess
import sys
import tempfile

AUDIT = r"C:\KenshiModMap\tools\api_audit.py"
FAILS = []


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def audit(root):
    env = dict(os.environ)
    if root:
        env["KMM_AUDIT_ROOT"] = root
    else:
        env.pop("KMM_AUDIT_ROOT", None)
    r = subprocess.run([sys.executable, "-I", "-X", "utf8", AUDIT], env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=120)
    return r.returncode, r.stdout + r.stderr


def fixture(lua):
    root = tempfile.mkdtemp(prefix="kmm_audit_")
    d = os.path.join(root, "KMM_X", "scripts", "init")
    os.makedirs(d)
    open(os.path.join(d, "x.lua"), "w", encoding="utf-8").write(lua)
    return root


BAD = '''
local function probe(fobj, p, h)
  return getGameWorld().theFactory:createRandomSquad(fobj, p, nil, 3, nil, nil, nil, nil, nil, false, h, nil, 1.0, 2, false)
end
local function by_sid(fobj, p, h)
  return getGameWorld().theFactory:createRandomSquad(fobj, p, nil, 3, nil, "sq_sid", nil, nil, nil, false, h, nil, 1.0, 2, false)
end
'''
WARN = '''
local function spawn(fobj, sid, p, h)
  local gw = getGameWorld()
  local gd = nil
  if sid then
    gd = gw.gamedata:getData(sid, 52)
    if not gd then error("no template") end
  end
  return gw.theFactory:createRandomSquad(fobj, p, nil, 5, nil, gd, nil, nil, nil, false, h, nil, 1.0, 2, false)
end
'''
GOOD = '''
local function spawn(fobj, sid, p, h)
  local gw = getGameWorld()
  local gd = gw.gamedata:getData(sid, 52)
  if not gd then error("no template") end
  local it = gw.theFactory:createItem(gd, nil, nil, nil, -1, nil)
  return gw.theFactory:createRandomSquad(fobj, { x = 1, y = 2, z = 3 }, nil, 5, nil, gd, nil, nil, nil, false, h, nil, 1.0, 2, false)
end
local function spawn2(fobj, sid, p, h)
  local gd
  gd = getGameWorld().gamedata:getData(sid, 52)
  return getGameWorld().theFactory:createRandomSquad(fobj, p, nil, 5, nil, gd, nil, nil, nil, false, h, nil, 1.0, 2, false)
end
'''

rc, out = audit(fixture(BAD))
check(rc == 1, f"литеральный nil / строка в squad -> код 1 (код {rc})")
check("createRandomSquad() аргумент #6 = nil" in out, "nil в #6 пойман")
check("аргумент #6 = string-литерал" in out, "строка вместо GameData поймана")
rc, out = audit(fixture(WARN))
check(rc == 0 and "аргумент #6 'gd' может быть nil" in out, f"local gd = nil + if -> предупреждение, код 0 (код {rc})")
rc, out = audit(fixture(GOOD))
check(rc == 0 and "нарушений сигнатур: 0" in out and "может быть nil (" not in out, f"правильные вызовы -> чисто (код {rc})")
rc, out = audit(None)
check("нарушений сигнатур: 0" in out, "живой build/: нарушений сигнатур 0")
print("ALL OK" if not FAILS else "FAIL %d" % len(FAILS))
sys.exit(1 if FAILS else 0)
