"""Проверка Lua-файла без интерпретатора: токенизация (строки, комментарии, длинные скобки) + баланс блоков и скобок.
python -I -X utf8 check_lua.py file.lua"""
import re
import sys

s = open(sys.argv[1], encoding="utf-8").read()
toks, i, n, line = [], 0, len(s), 1
while i < n:
    c = s[i]
    if c == "\n":
        line += 1; i += 1; continue
    if s.startswith("--", i):
        m = re.match(r"--\[(=*)\[", s[i:])
        if m:
            end = s.find("]" + m.group(1) + "]", i)
            line += s.count("\n", i, end); i = end + len(m.group(1)) + 2; continue
        j = s.find("\n", i); i = n if j < 0 else j; continue
    m = re.match(r"\[(=*)\[", s[i:])
    if m:
        end = s.find("]" + m.group(1) + "]", i)
        line += s.count("\n", i, end); toks.append(("str", line)); i = end + len(m.group(1)) + 2; continue
    if c in "\"'":
        j = i + 1
        while j < n and s[j] != c:
            if s[j] == "\\":
                j += 1
            if s[j] == "\n":
                sys.exit(f"незакрытая строка, строка {line}")
            j += 1
        toks.append(("str", line)); i = j + 1; continue
    m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", s[i:])
    if m:
        toks.append((m.group(0), line)); i += len(m.group(0)); continue
    toks.append((c, line)); i += 1

stack = []
for t, ln in toks:
    if t in ("function", "do", "then", "repeat"):
        if t == "do" and stack and stack[-1][0] in ("for", "while"):
            stack[-1] = ("do", stack[-1][1]); continue
        if t == "then" and stack and stack[-1][0] == "elseif":
            stack.pop(); continue             # elseif … then продолжает тот же блок if
        if t == "then" and stack and stack[-1][0] == "if":
            stack[-1] = ("then", stack[-1][1]); continue
        stack.append((t, ln))
    elif t in ("for", "while", "if"):
        stack.append((t, ln))
    elif t == "elseif":
        stack.append(("elseif", ln))
    elif t == "then":
        pass
    elif t == "end":
        if not stack:
            sys.exit(f"лишний end, строка {ln}")
        stack.pop()
    elif t == "until":
        stack.pop()
pairs_ = {"(": ")", "{": "}", "[": "]"}
st = []
for t, ln in toks:
    if t in pairs_:
        st.append((t, ln))
    elif t in pairs_.values():
        if not st or pairs_[st[-1][0]] != t:
            sys.exit(f"скобка {t} не к месту, строка {ln}")
        st.pop()
print("OK" if not stack and not st else f"незакрыто: блоки {stack[-3:]}, скобки {st[-3:]}", "| токенов", len(toks))
