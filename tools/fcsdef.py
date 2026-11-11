"""fcsdef — парсер схемы FCS (Kenshi\\fcs.def + fcs_enums.def) и валидатор записей kmod.

Схема описывает для каждого типа записи: поля (тип значения + дефолт) и категории ссылок
(тип цели + дефолтные val0..2). Используется генератором как «компилятор»: запись, не прошедшая
валидацию, не попадает в KMM_Core.mod.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import kmod

_FIELD = re.compile(r'^(?P<key>[^:"]+?):\s+(?P<rest>.+)$')
_CAT = re.compile(r'^[^:"]+:\s*$')
_REF = re.compile(r'^(?P<type>[A-Z][A-Z0-9_]+)(\s*\((?P<vals>[^)]*)\))?(\s+"|$)')
_ENUM = re.compile(r'^(?P<enum>[A-Za-z_]+)\.(?P<val>[A-Za-z0-9_]+)')


@dataclass
class FieldDef:
    key: str
    kind: str            # bool | float | int | enum | string | file | ref
    default: object = None
    ref_type: str = ""   # для kind == ref
    ref_vals: tuple = ()
    enum: str = ""


@dataclass
class Schema:
    fields: dict = field(default_factory=dict)   # TYPE -> {key: FieldDef}
    enums: dict = field(default_factory=dict)    # EnumName -> {VALUE: int}

    def for_type(self, tname: str) -> dict:
        return self.fields.get(tname, {})


def _parse_enums(text: str) -> dict:
    enums = {}
    for m in re.finditer(r"enum\s+(\w+)\s*\{([^}]*)\}", text):
        vals, n = {}, 0
        body = re.sub(r"/\*.*?\*/", " ", m.group(2), flags=re.S)
        body = re.sub(r"//[^\n]*", " ", body)   # //-комментарии внутри enum {} давали мусорные члены (напр. taskType)
        for tok in re.split(r"[,.\s]+", body):
            tok = tok.strip()
            if not tok:
                continue
            if "=" in tok:
                name, num = tok.split("=", 1); n = int(num); tok = name
            vals[tok] = n; n += 1
        enums[m.group(1)] = vals
    return enums


def load(kenshi_dir: str) -> Schema:
    sch = Schema()
    sch.enums = _parse_enums(open(f"{kenshi_dir}\\fcs_enums.def", encoding="utf-8", errors="replace").read())
    types: list = []
    for raw in open(f"{kenshi_dir}\\fcs.def", encoding="utf-8", errors="replace"):
        line = raw.split("//", 1)[0].rstrip() if not raw.lstrip().startswith('"') else raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("["):
            types = [t.strip() for t in line.strip("[]").split(",")]
            continue
        if line.startswith("TRANSLATE") or _CAT.match(line):
            continue
        m = _FIELD.match(line)
        if not m:
            continue
        key, rest = m.group("key").strip(), m.group("rest").strip()
        fd = _field(key, rest, sch.enums)
        if fd:
            for t in types:
                sch.fields.setdefault(t, {})[key] = fd
    return sch


def _field(key: str, rest: str, enums: dict) -> FieldDef | None:
    if rest.startswith('"'):
        end = rest.find('"', 1)
        lit = rest[1:end]
        return FieldDef(key, "file" if "|*." in lit else "string", "" if "|*." in lit else lit)
    tok = rest.split()[0]
    if tok in ("True", "False"):
        return FieldDef(key, "bool", tok == "True")
    m = _REF.match(rest)
    if m and m.group("type") in kmod.ITEM_TYPES:
        vals = tuple(int(x) for x in re.findall(r"-?\d+", m.group("vals") or ""))
        return FieldDef(key, "ref", ref_type=m.group("type"), ref_vals=vals)
    m = _ENUM.match(tok)
    if m:
        return FieldDef(key, "enum", enums.get(m.group("enum"), {}).get(m.group("val")), enum=m.group("enum"))
    try:
        if re.fullmatch(r"-?\d+", tok):
            return FieldDef(key, "int", int(tok))
        return FieldDef(key, "float", float(tok))
    except ValueError:
        return None


# --- валидация -----------------------------------------------------------
_PY_KIND = {"bool": (bool,), "float": (kmod.F32, float), "int": (int,), "enum": (int,),
            "string": (str,), "file": (kmod.FilePath, str)}


# ссылка на базовый тип принимает подтипы (в ванили material -> MATERIAL_SPECS_*)
_FAMILY = {"MATERIAL_SPEC": "MATERIAL_SPEC"}


def validate(item: kmod.Item, sch: Schema, resolve=None) -> tuple[list, list]:
    """Возвращает (ошибки, предупреждения). resolve(sid) -> Item|None проверяет цели ссылок."""
    errs, warns = [], []
    fdefs = sch.for_type(item.type_name)
    if not fdefs:
        warns.append(f"{item.sid}: тип {item.type_name} не описан в fcs.def")
        return errs, warns
    for k, v in item.values.items():
        if k == "DELETED":
            continue
        fd = fdefs.get(k)
        if fd is None:
            warns.append(f"{item.sid} {item.name!r}: поле {k!r} нет в схеме {item.type_name}")
        elif fd.kind == "ref":
            errs.append(f"{item.sid}: {k!r} — это категория ссылок, а записано значение")
        elif fd.kind == "int" and isinstance(v, (bool, kmod.F32)) or fd.kind == "float" and not isinstance(v, kmod.F32) \
                or not isinstance(v, _PY_KIND[fd.kind]) or fd.kind != "bool" and isinstance(v, bool):
            errs.append(f"{item.sid} {item.name!r}: поле {k!r} ожидается {fd.kind}, записано {type(v).__name__}={v!r}")
    for cat, refs in item.refs.items():
        fd = fdefs.get(cat)
        if fd is None or fd.kind != "ref":
            warns.append(f"{item.sid} {item.name!r}: категории ссылок {cat!r} нет в схеме {item.type_name}")
            continue
        if resolve:
            for r in refs:
                if (r.v0, r.v1, r.v2) == (2147483647,) * 3:
                    continue
                tgt = resolve(r.target)
                if tgt is None:
                    errs.append(f"{item.sid} {item.name!r}: {cat} -> {r.target} не найдено")
                elif tgt.type_name != fd.ref_type and not tgt.type_name.startswith(_FAMILY.get(fd.ref_type, "\0")):
                    errs.append(f"{item.sid} {item.name!r}: {cat} -> {tgt.name!r} тип {tgt.type_name}, ждали {fd.ref_type}")
    return errs, warns
