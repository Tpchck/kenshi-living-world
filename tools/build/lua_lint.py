"""Статическая проверка Lua-скриптов модов KMM (без игры, без сети).
python -I -X utf8 tools/build/lua_lint.py [корень=C:/KenshiModMap/build]   → список нарушений; код 1, если они есть.

Правила (по DECISIONS «Безотказность», KMM_Ore v2, сейв в sdata):
  syntax     — файл компилируется lua51.dll из KenshiLua (luaL_loadstring, без выполнения);
  top_event  — Events.on на верхнем уровне файла (вне функций) только для ALLOWED_TOP_EVENTS;
  guarded    — второй аргумент каждого Events.on — вызов guarded(…) (ошибка обработчика отключает только его);
  top_io     — нет io.open / os.* на верхнем уровне (побочные эффекты при загрузке мода);
  data_string — нет обращения к data_string (такого поля нет; сейв — gameData.sdata).
Верхний уровень = вне тела любой function (блоки if/do на верхнем уровне — тоже верхний уровень).
Комментарии и строки в проверке токенов не участвуют."""
import ctypes
import glob
import os
import re
import sys

DLL = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\lua51.dll"
ROOT = sys.argv[1] if len(sys.argv) > 1 else r"C:\KenshiModMap\build"
ALLOWED_TOP_EVENTS = (
    "GameWorld::charsUpdate",
    "PlayerInterface::serialise",
    "PlayerInterface::loadFromSerialise",
    "Character::_NV_hitByMeleeAttack",   # уже существующий хук дирижёра (нападение на игрока)
    "MyGUI::Gui::eventFrameStart",       # только смоук-хук KMM_Native.lua: регистрируется лишь при флаг-файле smoke.py --world
)
# смоук-хук KMM_Native.lua: одна проверка флаг-файла при загрузке и самоудаление флага (2026-11-12, tools\smoke.py --world)
TOP_IO_FILES = ("KMM_Native.lua",)
GUARD_NAMES = ("guarded",)
TOP_FORBIDDEN = (("io", "open"), ("os", None))   # (модуль, поле); None = любое поле

TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<lcomment>--\[(?P<lceq>=*)\[.*?\](?P=lceq)\])
  | (?P<comment>--[^\n]*)
  | (?P<lstr>\[(?P<lseq>=*)\[.*?\](?P=lseq)\])
  | (?P<str>"(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*')
  | (?P<num>0[xX][0-9a-fA-F]+|\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<op>\.\.\.|\.\.|==|~=|<=|>=|.)
""", re.S | re.X)


def tokens(src):
    out, pos, line = [], 0, 1
    while pos < len(src):
        m = TOKEN.match(src, pos)
        kind = None
        for k in ("ws", "lcomment", "comment", "lstr", "str", "num", "name", "op"):
            if m.group(k) is not None:
                kind = k
                break
        text = m.group(0)
        if kind in ("name", "op", "str", "lstr", "num"):
            out.append((kind, text, line))
        line += text.count("\n")
        pos = m.end()
    return out


def str_value(tok):
    kind, text, _ = tok
    if kind == "str":
        return text[1:-1]
    if kind == "lstr":
        return re.sub(r"^\[=*\[\n?|\]=*\]$", "", text)
    return None


def lint_tokens(path, toks):
    viol = []
    stack = []   # "F" — тело функции, "B" — блок (if/do/while/for), "R" — repeat
    n = len(toks)
    for i, (kind, text, line) in enumerate(toks):
        top = "F" not in stack
        prev = toks[i - 1][1] if i > 0 else ""
        member = prev in (".", ":")   # obj.end / obj.function невозможны в Lua, но obj.do тоже — оставляем как защиту
        if kind == "name" and not member:
            if text == "function":
                stack.append("F")
            elif text in ("if", "do"):
                stack.append("B")
            elif text == "repeat":
                stack.append("R")
            elif text in ("end", "until"):
                if stack:
                    stack.pop()
                else:
                    viol.append((path, line, "parse", f"unbalanced '{text}'"))
        if kind == "name" and text == "data_string":
            viol.append((path, line, "data_string", "data_string access (save field is gameData.sdata)"))
        # Events.on( / Events:on(
        if kind == "name" and text == "Events" and i + 3 < n and toks[i + 1][1] in (".", ":") and toks[i + 2][1] == "on" and toks[i + 3][1] == "(":
            ev = str_value(toks[i + 4]) if i + 4 < n else None
            if top and ev not in ALLOWED_TOP_EVENTS:
                viol.append((path, line, "top_event", f"top-level Events.on({ev!r}) not in allowed list"))
            j = i + 5
            ok_guard = False
            if j + 1 < n and toks[j][1] == ",":
                ok_guard = toks[j + 1][0] == "name" and toks[j + 1][1] in GUARD_NAMES and j + 2 < n and toks[j + 2][1] == "("
            if not ok_guard:
                what = toks[j + 1][1] if j + 1 < n else "?"
                viol.append((path, line, "guarded", f"Events.on({ev!r}) handler is not guarded(...) (got '{what}')"))
        # io.open / os.* на верхнем уровне
        if top and kind == "name" and not member and i + 2 < n and toks[i + 1][1] == ".":
            for mod, field in TOP_FORBIDDEN:
                if text == mod and (field is None or toks[i + 2][1] == field) and os.path.basename(path) not in TOP_IO_FILES:
                    viol.append((path, line, "top_io", f"top-level {text}.{toks[i + 2][1]}"))
    if stack:
        viol.append((path, toks[-1][2] if toks else 0, "parse", f"{len(stack)} unclosed block(s)"))
    return viol


def compile_check(L, st, src):
    if L is None:
        return None
    rc = L.luaL_loadstring(st, src.encode("utf-8"))
    msg = None
    if rc:
        m = L.lua_tolstring(st, -1, None)
        msg = m.decode("utf-8", "replace") if m else f"rc={rc}"
    L.lua_settop(st, 0)
    return msg


def main():
    L = st = None
    if os.path.exists(DLL):
        L = ctypes.CDLL(DLL)
        L.luaL_newstate.restype = ctypes.c_void_p
        L.luaL_loadstring.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.lua_tolstring.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p]
        L.lua_tolstring.restype = ctypes.c_char_p
        L.lua_settop.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.lua_close.argtypes = [ctypes.c_void_p]
        st = L.luaL_newstate()
    files = sorted(glob.glob(os.path.join(ROOT, "KMM_*", "scripts", "**", "*.lua"), recursive=True))
    viol = []
    for p in files:
        rel = os.path.relpath(p, ROOT)
        src = open(p, encoding="utf-8-sig", errors="replace").read()
        err = compile_check(L, st, src)
        if err:
            viol.append((rel, 0, "syntax", err))
        viol.extend(lint_tokens(rel, tokens(src)))
    if L is not None:
        L.lua_close(st)
    for p, line, rule, msg in viol:
        print(f"{p}:{line}: [{rule}] {msg}")
    print(f"lua_lint: {len(files)} files, {len(viol)} violation(s){'' if L else ' (lua51.dll not found: syntax not checked)'}")
    return 1 if viol else 0


if __name__ == "__main__":
    sys.exit(main())
