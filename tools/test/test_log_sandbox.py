"""Песочница логов (B3 И9): офлайн-тесты не пишут в живые C:\\KenshiModMap\\logs\\.
1) обёртка Lua: все формы пути logs/ (регистр, \\ и /) уходят в песочницу, прочие пути не трогаются, os.remove тоже;
2) обёртка запуска log_sandbox.py ловит произвольный тест без своих перенаправлений;
3) test_y3_ko_hold (KMM_Self пишет «KO hold: override registered at load» при загрузке, до cfg) пишет в песочницу, живой debug.log не растёт;
4) verify_all гоняет тесты через log_sandbox и сверяет logs/ до/после; тесты, грузящие KMM_Self.lua, подключают песочницу.
python -I -X utf8 tools/test/test_log_sandbox.py -> OK / FAIL (код 1)."""
import ctypes
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import log_sandbox  # noqa: E402

ROOT = r"C:\KenshiModMap"
LIVE = os.path.join(ROOT, "logs")
DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
FAILS = []
PROBE = "zz_sandbox_probe_%d" % os.getpid()


def check(c, m):
    print(("OK   " if c else "FAIL ") + m)
    if not c:
        FAILS.append(m)


def live_size(n):
    p = os.path.join(LIVE, n)
    return os.path.getsize(p) if os.path.exists(p) else -1


# 1. обёртка в состоянии Lua
sb = tempfile.mkdtemp(prefix="kmm_sbtest_")
os.environ[log_sandbox.ENV_DIR] = sb
log_sandbox.install()
L = ctypes.CDLL(DLL)
L.luaL_newstate.restype = ctypes.c_void_p
for fn, at in [("luaL_openlibs", [ctypes.c_void_p]), ("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
               ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int])]:
    getattr(L, fn).argtypes = at
L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
L.lua_tolstring.restype = ctypes.c_char_p
st = L.luaL_newstate()
L.luaL_openlibs(st)


def run(code):
    if L.luaL_loadstring(st, code.encode("utf-8")) or L.lua_pcall(st, 0, 0, 0):
        msg = L.lua_tolstring(st, -1, None)
        raise RuntimeError(msg.decode("utf-8", "replace") if msg else "?")


other = os.path.join(sb, "other").replace("\\", "/")
os.makedirs(other)
run(r'''
local P = "%s"
local function w(p, s) local f = io.open(p, "a"); assert(f, "open " .. p); f:write(s, "\n"); f:close() end
w("C:/KenshiModMap/logs/" .. P .. ".log", "a")
w("C:\\KenshiModMap\\logs\\" .. P .. ".log", "b")
w("c:/kenshimodmap/LOGS//" .. P .. ".log", "c")
w("C:/KenshiModMap/logs/sub/" .. P .. ".log", "d")
w("%s/plain.txt", "e")
local n = 0; for _ in io.lines("C:/KenshiModMap/logs/" .. P .. ".log") do n = n + 1 end
assert(n == 3, "io.lines sees " .. n)
assert(os.remove("C:/KenshiModMap/logs/sub/" .. P .. ".log"), "remove")
''' % (PROBE, other))
body = open(os.path.join(sb, PROBE + ".log"), encoding="utf-8").read().split()
check(body == ["a", "b", "c"], f"три формы пути logs/ -> песочница: {body}")
check(not os.path.exists(os.path.join(sb, "sub__" + PROBE + ".log")), "подпапка logs/sub/ сплющена и os.remove перенаправлен")
check(os.path.exists(os.path.join(other, "plain.txt")), "путь вне logs/ не тронут")
check(live_size(PROBE + ".log") == -1 and not os.path.exists(os.path.join(LIVE, "sub")), "в живых logs/ проба не появилась")
check(PROBE + ".log" in log_sandbox.redirected(sb), f"_redirected.txt: {log_sandbox.redirected(sb)}")

# 2. обёртка запуска ловит тест без своих перенаправлений
tmp2 = tempfile.mkdtemp(prefix="kmm_sbtest2_")
script = os.path.join(tmp2, "bare_test.py")
open(script, "w", encoding="utf-8").write(f'''import ctypes
L = ctypes.CDLL(r"{DLL}")
L.luaL_newstate.restype = ctypes.c_void_p
L.luaL_openlibs.argtypes = [ctypes.c_void_p]
L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
L.lua_pcall.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]
st = L.luaL_newstate(); L.luaL_openlibs(st)
code = b'local f = io.open("C:/KenshiModMap/logs/{PROBE}_bare.log", "a"); f:write("x"); f:close()'
assert L.luaL_loadstring(st, code) == 0 and L.lua_pcall(st, 0, 0, 0) == 0
print("BARE OK")
''')
sb2 = os.path.join(tmp2, "sb")
env = dict(os.environ, KMM_TEST_LOG_DIR=sb2)
r = subprocess.run([sys.executable, "-I", "-X", "utf8", os.path.join(HERE, "log_sandbox.py"), script], cwd=tmp2, env=env,
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
check(r.returncode == 0 and "BARE OK" in r.stdout, "обёртка запуска: тест прошёл " + (r.stdout + r.stderr).strip()[-200:])
check(os.path.exists(os.path.join(sb2, PROBE + "_bare.log")) and live_size(PROBE + "_bare.log") == -1,
      "обёртка запуска: запись теста без перенаправлений ушла в песочницу")

# 3. KMM_Self пишет при загрузке (до cfg): прямой запуск test_y3_ko_hold
ko = os.path.join(ROOT, "build", "KMM_Conductor", "_dev", "test_y3_ko_hold.py")
sb3 = tempfile.mkdtemp(prefix="kmm_sbtest3_")
s0 = live_size("debug.log")
r = subprocess.run([sys.executable, "-I", "-X", "utf8", ko], cwd=os.path.dirname(ko), env=dict(os.environ, KMM_TEST_LOG_DIR=sb3),
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
s1 = live_size("debug.log")
got = ""
if os.path.exists(os.path.join(sb3, "debug.log")):
    got = open(os.path.join(sb3, "debug.log"), encoding="utf-8", errors="replace").read()
check("KO hold: override registered at load" in got, "test_y3_ko_hold: «registered at load» ушло в песочницу (код %d)" % r.returncode)
grew = ""
if s1 > s0 >= 0:
    with open(os.path.join(LIVE, "debug.log"), "rb") as f:
        f.seek(s0)
        grew = f.read().decode("utf-8", "replace")
check("override registered at load" not in grew, "живой debug.log без строк теста (вырос на %d байт)" % max(0, s1 - s0))

# 4. verify_all и тесты, грузящие KMM_Self.lua
va = open(os.path.join(ROOT, "tools", "verify_all.py"), encoding="utf-8").read()
check("SANDBOX, f]" in va and "logs_snapshot()" in va and "KMM_TEST_LOG_DIR" in va, "verify_all: тесты через log_sandbox, сверка logs/ до/после")
tests = sorted({f for g in ("build/*/_dev/test_*.py", "tools/test/test_*.py", "tools/conductor/test_*.py") for f in glob.glob(os.path.join(ROOT, g))})
bad = []
for f in tests:
    src = open(f, encoding="utf-8", errors="replace").read()
    own_state = "luaL_openlibs" in src   # без своего состояния Lua тест берёт стенд у другого теста (importlib), проверяется там
    if own_state and "KMM_Self.lua" in src and "log_sandbox" not in src and "test_runtime.py" not in src:
        bad.append(os.path.relpath(f, ROOT))
check(not bad, f"тесты с KMM_Self.lua подключают песочницу (или STUBS test_runtime): {bad}")

print("ALL OK" if not FAILS else "FAIL %d" % len(FAILS))
sys.exit(1 if FAILS else 0)
