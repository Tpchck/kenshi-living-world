r"""Песочница логов для офлайн-тестов (B3 И9, 2026-11-15): тесты не пишут в живые C:\KenshiModMap\logs\.

Как работает: после каждого luaL_openlibs у lua51.dll (ctypes) в состояние Lua ставится обёртка io.open / io.lines /
os.remove / os.rename. Пути под C:/KenshiModMap/logs/ (любой регистр, / или \) уходят в папку песочницы
(env KMM_TEST_LOG_DIR, иначе новая временная папка). Подпапки сплющиваются: logs/a/b.log -> <песочница>/a__b.log.
Остальные пути не трогаются. Свои перенаправления стенда (STUBS test_runtime, save_world) ставятся поверх и срабатывают первыми.
Каждый перехваченный путь один раз пишется в <песочница>/_redirected.txt (тест test_log_sandbox это проверяет).

Подключение:
  1) обёртка запуска (так делает verify_all):  python -I -X utf8 tools/test/log_sandbox.py <test.py> [args]
  2) в самом тесте до ctypes.CDLL:  sys.path.insert(0, r"C:\KenshiModMap\tools\test"); import log_sandbox; log_sandbox.install()
"""
import ctypes
import os
import runpy
import sys
import tempfile

ENV_DIR = "KMM_TEST_LOG_DIR"
LIVE_LOGS = r"C:\KenshiModMap\logs"
_ORIG_CDLL = getattr(ctypes, "_kmm_orig_CDLL", ctypes.CDLL)
_HELPERS = {}

LUA = r'''
do
  if rawget(_G, "__KMM_LOG_SANDBOX") then return end
  local DIR = [==[@DIR@]==]
  local PFX = "c:/kenshimodmap/logs/"
  local seen = {}
  local r_open, r_lines, r_remove, r_rename = io.open, io.lines, os.remove, os.rename
  local function map(p)
    if type(p) ~= "string" then return p end
    local n = p:gsub("\\", "/"):gsub("/+", "/")
    if n:sub(1, #PFX):lower() ~= PFX then return p end
    local rest = n:sub(#PFX + 1)
    if rest == "" then return p end
    rest = rest:gsub("/", "__")
    if not seen[rest] then
      seen[rest] = true
      local f = r_open(DIR .. "/_redirected.txt", "a")
      if f then f:write(rest, "\n"); f:close() end
    end
    return DIR .. "/" .. rest
  end
  io.open = function(p, ...) return r_open(map(p), ...) end
  io.lines = function(p, ...) if p == nil then return r_lines() end; return r_lines(map(p), ...) end
  os.remove = function(p) return r_remove(map(p)) end
  os.rename = function(a, b) return r_rename(map(a), map(b)) end
  __KMM_LOG_SANDBOX = DIR
end
'''


def sandbox_dir():
    """Папка песочницы: env KMM_TEST_LOG_DIR (создаётся при нужде) или новая временная; пишется в env для дочерних процессов."""
    d = os.environ.get(ENV_DIR)
    if not d:
        d = tempfile.mkdtemp(prefix="kmm_testlogs_")
        os.environ[ENV_DIR] = d
    os.makedirs(d, exist_ok=True)
    if os.path.normcase(os.path.abspath(d)).startswith(os.path.normcase(LIVE_LOGS)):
        raise RuntimeError(f"{ENV_DIR} указывает в живые logs/: {d}")
    return d.replace("\\", "/").rstrip("/")


def lua_code():
    return LUA.replace("@DIR@", sandbox_dir())


def _helper(path):
    h = _HELPERS.get(path)
    if h is None:
        h = _ORIG_CDLL(path)
        for fn, at in [("luaL_loadstring", [ctypes.c_void_p, ctypes.c_char_p]),
                       ("lua_pcall", [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_int]),
                       ("lua_settop", [ctypes.c_void_p, ctypes.c_int])]:
            getattr(h, fn).argtypes = at
        h.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        h.lua_tolstring.restype = ctypes.c_char_p
        _HELPERS[path] = h
    return h


def inject(dll_path, st):
    """Поставить обёртку в уже открытое состояние Lua (после luaL_openlibs)."""
    h = _helper(dll_path)
    p = ctypes.c_void_p(st.value if isinstance(st, ctypes.c_void_p) else st)
    if h.luaL_loadstring(p, lua_code().encode("utf-8")) or h.lua_pcall(p, 0, 0, 0):
        msg = h.lua_tolstring(p, -1, None)
        h.lua_settop(p, -2)
        raise RuntimeError("log_sandbox: " + (msg.decode("utf-8", "replace") if msg else "?"))


class _OpenLibs:
    """Прокси luaL_openlibs: атрибуты (argtypes/restype) уходят в настоящую функцию, вызов + inject."""

    def __init__(self, real, dll_path):
        object.__setattr__(self, "_real", real)
        object.__setattr__(self, "_dll", dll_path)

    def __setattr__(self, k, v):
        setattr(self._real, k, v)

    def __getattr__(self, k):
        return getattr(self._real, k)

    def __call__(self, st, *a):
        r = self._real(st, *a)
        inject(self._dll, st)
        return r


class _SandboxCDLL(_ORIG_CDLL):
    def __getattr__(self, name):
        f = super().__getattr__(name)
        if name == "luaL_openlibs" and "lua" in os.path.basename(str(self._name)).lower():
            f = _OpenLibs(f, self._name)
            setattr(self, name, f)
        return f


def install():
    """Подменить ctypes.CDLL: все последующие состояния lua51 получают песочницу логов. Повторный вызов безвреден."""
    sandbox_dir()
    if not getattr(ctypes, "_kmm_orig_CDLL", None):
        ctypes._kmm_orig_CDLL = _ORIG_CDLL
    ctypes.CDLL = _SandboxCDLL
    return os.environ[ENV_DIR]


def redirected(d=None):
    """Какие файлы logs/ были перехвачены в песочнице d (по _redirected.txt)."""
    p = os.path.join(d or os.environ.get(ENV_DIR, ""), "_redirected.txt")
    try:
        return sorted({x.strip() for x in open(p, encoding="utf-8") if x.strip()})
    except OSError:
        return []


def main(argv):
    if not argv:
        sys.exit("usage: log_sandbox.py <script.py> [args]")
    install()
    script = os.path.abspath(argv[0])
    sys.argv = [script] + argv[1:]
    runpy.run_path(script, run_name="__main__")


if __name__ == "__main__":
    main(sys.argv[1:])
