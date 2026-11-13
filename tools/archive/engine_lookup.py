#!/usr/bin/env python
"""engine_lookup — поиск по индексу движка Kenshi (data/engine_index.json).

  python -I -X utf8 tools/engine_lookup.py "<запрос>" [-n 25] [--kind class|method|field|enum|fcs|fcsfield]
  python -I -X utf8 tools/engine_lookup.py --rebuild     # пересобрать индекс из заголовков KenshiLib/BR/ER/fcs.def

Запрос: слова через пробел — все должны входить в имя (без регистра). Формы:
  Class            класс (+ его поля/методы, базы, FCS-типы с похожим именем)
  Class.member / Class:member   член класса
  TYPE_NAME        тип записи FCS (поля с описаниями)
  EnumName         enum (значения)
Пометки: [L] доступно из Lua (BindingsReference, номер строки), [C++] только C++.
"""
import json, os, re, sys, glob

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IDX = os.path.join(ROOT, "data", "engine_index.json")
KLIB = os.path.join(ROOT, "tools", "ref")
LUADOCS = r"C:\Program Files (x86)\Steam\steamapps\workshop\content\233860\3817000612\docs"
KENSHI = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi"


# ------------------------------------------------------------------ build
def _strip(line):
    code, _, com = line.partition("//")
    return code.strip(), com.strip()


def parse_header(path, rel, classes, enums):
    try:
        lines = open(path, encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return
    stack = []          # (kind, name)  kind: class|enum|other
    pending = None
    enum_buf = None
    in_block = False
    for raw in lines:
        if in_block:
            if "*/" in raw:
                in_block = False
            continue
        if raw.strip().startswith("/*"):
            if "*/" not in raw:
                in_block = True
            continue
        code, com = _strip(raw)
        if not code:
            continue
        top = stack[-1] if stack else None
        # объявление class/struct/enum
        m = re.match(r"^(?:template\s*<[^>]*>\s*)?(class|struct)\s+([A-Za-z_]\w*)\s*(?::\s*(.+?))?\s*(\{)?$", code)
        me = re.match(r"^enum\s*(?:class\s+)?([A-Za-z_]\w*)?\s*(?::\s*\w+\s*)?(\{.*)?$", code)
        if m and not code.endswith(";") and (top is None or top[0] == "class"):
            outer = top[1] if top else ""
            full = (outer + "::" if outer else "") + m.group(2)
            bases = []
            if m.group(3):
                for b in re.split(r",(?![^<]*>)", m.group(3)):
                    b = re.sub(r"^(public|protected|private|virtual)\s+", "", b.strip())
                    b = re.sub(r"^(public|protected|private|virtual)\s+", "", b)
                    if b:
                        bases.append(b)
            cl = classes.setdefault(full, {"h": rel, "b": bases, "f": {}, "m": {}})
            if not cl["b"]:
                cl["b"] = bases
            pending = ("class", full)
            if m.group(4):
                stack.append(pending); pending = None
            continue
        if me and not code.endswith(";") and (top is None or top[0] == "class") and re.match(r"^enum\b", code):
            outer = top[1] if top else ""
            nm = me.group(1) or "anon"
            full = (outer + "::" if outer else "") + nm
            enums.setdefault(full, {"h": rel, "vals": {}})
            pending = ("enum", full)
            enum_buf = []
            rest = me.group(2) or ""
            if rest.startswith("{"):
                stack.append(pending); pending = None
                body = rest[1:]
                if "}" in body:
                    _finish_enum(enums[full], enum_buf + [body.split("}")[0]]); stack.pop(); enum_buf = None
                else:
                    enum_buf.append(body)
            continue
        if code == "{":
            if pending:
                stack.append(pending); pending = None
            else:
                stack.append(("other", ""))
            continue
        if top and top[0] == "enum":
            if "}" in code:
                enum_buf.append(code.split("}")[0])
                _finish_enum(enums[top[1]], enum_buf); enum_buf = None
                stack.pop()
            else:
                enum_buf.append(code)
            continue
        # скобки внутри строки
        opens, closes = code.count("{"), code.count("}")
        if top and top[0] == "class" and code.endswith(";") and opens == closes:
            _member(classes[top[1]], code, com)
            continue
        if code.startswith("public:") or code.startswith("private:") or code.startswith("protected:"):
            continue
        for _ in range(opens):
            stack.append(("other", ""))
        for _ in range(closes):
            if stack:
                stack.pop()
        if opens == 0 and closes == 0 and top and top[0] == "class" and "(" in code and not code.endswith(";"):
            pass


def _finish_enum(e, buf):
    n = 0
    for tok in ",".join(buf).split(","):
        tok = tok.strip()
        if not tok:
            continue
        if "=" in tok:
            name, val = [x.strip() for x in tok.split("=", 1)]
            try:
                n = int(val, 0)
            except ValueError:
                e["vals"][name] = val
                continue
        else:
            name = tok
        if re.match(r"^\w+$", name):
            e["vals"][name] = n
            n += 1


def _member(cl, code, com):
    if code.startswith(("typedef", "using", "friend", "static_assert", "return")):
        return
    if "(" in code and not re.search(r"\)\s*(const)?\s*(override)?\s*;?$", code) and "(*" not in code:
        pass
    if "(" in code:
        mm = re.search(r"((?:operator\s*\S+?)|~?\w+)\s*\(", code)
        if not mm:
            return
        name = mm.group(1)
        if name.startswith("_NV_") or name.startswith("_CONSTRUCTOR") or "no_addr" in com:
            return
        sig = re.sub(r"\s+", " ", code.rstrip(";"))
        fl = ""
        if sig.startswith("virtual "):
            fl += "v"; sig = sig[8:]
        if sig.startswith("static "):
            fl += "s"; sig = sig[7:]
        cl["m"].setdefault(name, []).append([sig, fl, 0])
    else:
        mm = re.match(r"^(.*?[\s\*&>])(\w+)(\[[^\]]*\])?\s*;$", code)
        if not mm:
            return
        off = re.search(r"(0x[0-9A-Fa-f]+)\s+Member", com)
        cl["f"][mm.group(2)] = [mm.group(1).strip() + (mm.group(3) or ""), off.group(1) if off else "", 0]


def parse_br():
    """BindingsReference: класс -> {line, fields{name:(line,rw)}, methods{name:line}}"""
    out, cur, sect = {}, None, None
    p = os.path.join(LUADOCS, "BindingsReference.md")
    for i, ln in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
        if ln.startswith("## ") and i > 480:
            cur = ln[3:].strip()
            out[cur] = {"line": i, "fields": {}, "methods": {}, "parent": ""}
            sect = None
        elif cur and ln.startswith("**Parent Class:**"):
            m = re.search(r"\[`([^`]+)`\]", ln)
            out[cur]["parent"] = m.group(1) if m else ""
        elif ln.startswith("### Fields"):
            sect = "fields"
        elif ln.startswith("### Methods") or ln.startswith("### Static"):
            sect = "methods"
        elif cur and sect and ln.startswith("| ") and not ln.startswith("| Lua Name") and not ln.startswith("|---"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            nm = re.sub(r"\s*\[\d+\]$", "", cells[0])
            if sect == "fields":
                out[cur]["fields"][nm] = (i, cells[2] if len(cells) > 2 else "")
            else:
                out[cur]["methods"].setdefault(nm, i)
    return out


def parse_er():
    out, cur, hdr = {}, None, ""
    p = os.path.join(LUADOCS, "EnumsReference.md")
    for ln in open(p, encoding="utf-8", errors="replace"):
        if ln.startswith("## ") and ln.strip().endswith(".h"):
            hdr = ln[3:].strip()
        m = re.match(r"^### Table: `([^`]+)`", ln)
        if m:
            cur = m.group(1); out[cur] = {"h": hdr, "vals": {}, "cpp": ""}
            continue
        m = re.match(r"^\| `([^`]+)` \| `(-?\d+)` \| `([^`]+)` \|", ln)
        if m and cur:
            out[cur]["vals"][m.group(1).rsplit(".", 1)[-1]] = int(m.group(2))
            out[cur]["cpp"] = m.group(3).rsplit("::", 1)[0]
    return out


def parse_fcs():
    types = {}
    cur, group = [], ""
    line_re = re.compile(r'^(?P<key>[^:"]+?):\s*(?P<rest>.*)$')
    for raw in open(os.path.join(KENSHI, "fcs.def"), encoding="utf-8", errors="replace"):
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("//"):
            continue
        if line.startswith("["):
            cur = [t.strip() for t in line.strip().strip("[]").split(",")]
            group = ""
            for t in cur:
                types.setdefault(t, {"fields": {}, "alias": [x for x in cur if x != t]})
            continue
        if line.startswith("TRANSLATE"):
            continue
        m = line_re.match(line)
        if not m or not cur:
            continue
        key, rest = m.group("key").strip(), m.group("rest").strip()
        if not rest:
            group = key
            continue
        desc = ""
        dm = re.search(r'"((?:[^"\\]|\\.)*)"\s*$', rest)
        if dm and not rest.startswith('"'):
            desc = dm.group(1); rest = rest[:dm.start()].strip()
        elif rest.startswith('"'):
            q = re.match(r'^"((?:[^"\\]|\\.)*)"\s*(.*)$', rest)
            if q:
                rest = '"' + q.group(1) + '"'
                desc = q.group(2).strip().strip('"') if q.group(2).startswith('"') else ""
        fd = {"g": group, "t": rest[:60]}
        if desc:
            fd["d"] = desc[:300]
        for t in cur:
            types[t]["fields"][key] = fd
    enums = {}
    txt = open(os.path.join(KENSHI, "fcs_enums.def"), encoding="utf-8", errors="replace").read()
    txt = re.sub(r"//[^\n]*", "", txt)
    for m in re.finditer(r"enum\s+(\w+)\s*\{([^}]*)\}", txt):
        vals, n = {}, 0
        for tok in re.split(r"[,\s]+", m.group(2)):
            if not tok:
                continue
            if "=" in tok:
                a, b = tok.split("=", 1); n = int(b); tok = a
            vals[tok] = n; n += 1
        enums[m.group(1)] = vals
    return types, enums


def rebuild():
    classes, enums = {}, {}
    seen = set()
    for lib in ("KenshiLib", "KenshiLib_Erano01"):
        base = os.path.join(KLIB, lib, "Include")
        for sub in ("kenshi", "core"):
            for p in glob.glob(os.path.join(base, sub, "**", "*.h"), recursive=True):
                rel = os.path.relpath(p, base).replace("\\", "/")
                if rel in seen:
                    continue
                seen.add(rel)
                parse_header(p, rel, classes, enums)
    br = parse_br()
    er = parse_er()
    # Lua-доступность
    def lua_lookup(cname, kind, name, depth=0):
        b = br.get(cname)
        if b:
            d = b["fields"] if kind == "f" else b["methods"]
            if name in d:
                v = d[name]
                return v[0] if kind == "f" else v
        if depth < 8:
            for base in classes.get(cname, {}).get("b", []):
                base = re.sub(r"<.*", "", base).split("::")[-1] if base not in classes else base
                r = lua_lookup(base, kind, name, depth + 1)
                if r:
                    return r
            b2 = (b or {}).get("parent")
            if b2:
                return lua_lookup(b2, kind, name, depth + 1)
        return 0
    nm = nf = lm = lf = 0
    for cn, c in classes.items():
        c["lua"] = br[cn]["line"] if cn in br else 0
        for fn, f in c["f"].items():
            f[2] = lua_lookup(cn, "f", fn); nf += 1; lf += bool(f[2])
        for mn, lst in c["m"].items():
            ln = lua_lookup(cn, "m", mn)
            for e in lst:
                e[2] = ln; nm += 1; lm += bool(ln)
    # enum: объединяем с ER
    cppmap = {}
    for tn, t in er.items():
        cppmap[t["cpp"]] = tn
    for en, e in enums.items():
        for cand in (en, en + "::Enum"):
            if cand in cppmap:
                e["lua"] = cppmap[cand]; er[cppmap[cand]]["used"] = True
    for tn, t in er.items():
        if not t.get("used"):
            enums.setdefault(t["cpp"] or tn, {"h": t["h"], "vals": t["vals"], "lua": tn})
    ftypes, fenums = parse_fcs()
    idx = {"classes": classes, "enums": enums, "fcs_types": ftypes, "fcs_enums": fenums,
           "lua_only": sorted(c for c in br if c not in classes),
           "stats": {"classes": len(classes), "methods": nm, "methods_lua": lm, "fields": nf, "fields_lua": lf,
                     "enums": len(enums), "fcs_types": len(ftypes), "br_classes": len(br), "headers": len(seen)}}
    os.makedirs(os.path.dirname(IDX), exist_ok=True)
    json.dump(idx, open(IDX, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(json.dumps(idx["stats"], ensure_ascii=False))


# ------------------------------------------------------------------ lookup
def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _match(words, name):
    n = name.lower()
    return all(w in n for w in words)


def _rank(words, name):
    n = name.lower(); q = "".join(words)
    return (0 if n == q else 1 if n.startswith(q) else 2, len(n))


def lua_tag(v):
    return "[L:%s]" % v if v else "[C++]"


def show_class(idx, cn, c, full):
    print("CLASS %s  %s  %s" % (cn, c["h"], lua_tag(c["lua"]) if c["lua"] else "[C++]"))
    if c["b"]:
        print("  bases: " + ", ".join(c["b"]))
    for f, v in c["f"].items():
        if full:
            print("  .%s : %s %s %s" % (f, v[0], v[1], lua_tag(v[2])))
    for m, lst in c["m"].items():
        if full:
            for s, fl, ln in lst:
                print("  :%s %s%s" % (s, ("(%s) " % fl) if fl else "", lua_tag(ln)))
    if not full:
        print("  fields: %d (Lua %d), methods: %d (Lua %d)" % (
            len(c["f"]), sum(1 for v in c["f"].values() if v[2]),
            sum(len(v) for v in c["m"].values()), sum(1 for v in c["m"].values() if v[0][2])))
    # связанные типы FCS
    cn0 = _norm(cn.split("::")[-1])
    rel = [t for t in idx["fcs_types"] if _norm(t) == cn0 or _norm(t).startswith(cn0) and len(cn0) > 4]
    if rel:
        print("  FCS types: " + ", ".join(rel[:8]))


def lookup(q, n=25, kind=None):
    idx = json.load(open(IDX, encoding="utf-8"))
    q = q.strip()
    mem = re.match(r"^([\w:]+)\s*[.:]\s*(\w+)$", q)
    out = 0
    if mem and mem.group(1) in idx["classes"]:
        cn, member = mem.groups()
        c = idx["classes"][cn]
        words = [member.lower()]
        for f, v in c["f"].items():
            if _match(words, f):
                print("%s.%s : %s %s %s  (%s)" % (cn, f, v[0], v[1], lua_tag(v[2]), c["h"])); out += 1
        for m, lst in c["m"].items():
            if _match(words, m):
                for s, fl, ln in lst:
                    print("%s:%s  %s %s  (%s)" % (cn, s, ("(%s)" % fl) if fl else "", lua_tag(ln), c["h"])); out += 1
        if out:
            return
    words = [w.lower() for w in re.split(r"[\s.:]+", q) if w]
    if not words:
        return
    exact = idx["classes"].get(q)
    if exact and kind in (None, "class"):
        show_class(idx, q, exact, True)
        return
    def lim(lst):
        return sorted(lst, key=lambda x: x[0])[:n]
    if kind in (None, "class"):
        hits = lim([(_rank(words, k), k) for k in idx["classes"] if _match(words, k)])
        for _, k in hits:
            show_class(idx, k, idx["classes"][k], len(hits) == 1)
    if kind in (None, "method", "field"):
        res = []
        for cn, c in idx["classes"].items():
            if kind in (None, "field"):
                for f, v in c["f"].items():
                    if _match(words, f) or _match(words, cn + "." + f):
                        res.append((_rank(words, f), "%s.%s : %s %s %s" % (cn, f, v[0], v[1], lua_tag(v[2]))))
            if kind in (None, "method"):
                for m, lst in c["m"].items():
                    if _match(words, m) or _match(words, cn + ":" + m):
                        s, fl, ln = lst[0]
                        res.append((_rank(words, m), "%s:%s %s%s" % (cn, s, "+%d overloads " % (len(lst) - 1) if len(lst) > 1 else "", lua_tag(ln))))
        for _, s in lim(res):
            print(s)
    if kind in (None, "enum"):
        res = []
        for en, e in idx["enums"].items():
            if _match(words, en):
                res.append((_rank(words, en), "ENUM %s%s (%s): %s" % (en, " Lua=" + e["lua"] if e.get("lua") else "", e["h"],
                            ", ".join("%s=%s" % kv for kv in list(e["vals"].items())[:40]))))
            else:
                for vn, vv in e["vals"].items():
                    if _match(words, vn):
                        res.append((_rank(words, vn), "ENUMVAL %s.%s=%s" % (en, vn, vv)))
        for _, s in lim(res):
            print(s)
        for en, vals in idx["fcs_enums"].items():
            if _match(words, en):
                print("FCS-ENUM %s: %s" % (en, ", ".join("%s=%s" % kv for kv in list(vals.items())[:40])))
    if kind in (None, "fcs", "fcsfield"):
        for t, d in idx["fcs_types"].items():
            if kind in (None, "fcs") and _match(words, t):
                print("FCS-TYPE [%s]%s: %d полей" % (t, " (= " + ",".join(d["alias"]) + ")" if d["alias"] else "", len(d["fields"])))
                for k, f in list(d["fields"].items())[:60]:
                    print("   %s [%s] %s  -- %s" % (k, f["g"], f["t"], f.get("d", "")[:110]))
        res = []
        for t, d in idx["fcs_types"].items():
            for k, f in d["fields"].items():
                if _match(words, k) or (len(words) > 1 and _match(words, t + " " + k)) or (kind == "fcsfield" and _match(words, f.get("d", ""))):
                    res.append((_rank(words, k), "FCS %s.%s [%s] %s -- %s" % (t, k, f["g"], f["t"], f.get("d", "")[:110])))
        for _, s in lim(res):
            print(s)


if __name__ == "__main__":
    a = sys.argv[1:]
    if "--rebuild" in a:
        rebuild()
    elif not a:
        print(__doc__)
    else:
        kind = None; n = 25
        if "--kind" in a:
            i = a.index("--kind"); kind = a[i + 1]; del a[i:i + 2]
        if "-n" in a:
            i = a.index("-n"); n = int(a[i + 1]); del a[i:i + 2]
        lookup(" ".join(a), n, kind)
