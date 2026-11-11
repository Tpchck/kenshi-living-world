"""kmod — чтение/запись файлов данных Kenshi (.mod / .base), формат типов 16 и 17.

Спайк 1 (CORE.md §12). Формат сверен с OpenConstructionSet 4.1.0 (IO/OcsReader.cs, OcsWriter.cs)
и проверен побайтовым round-trip на ванильных gamedata.base / rebirth.mod / Newwworld.mod / Dialogue.mod.

Ключевые свойства:
- Порядок значений, категорий ссылок и инстансов сохраняется как в файле (в отличие от OCS,
  который сортирует значения по ключу) → read+write даёт идентичные байты.
- Строки: UTF-8 с surrogateescape, чтобы любой мусор в чужих модах переживал round-trip.
"""
from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from typing import Any

# --- типы файлов ---------------------------------------------------------
FILE_DATA = 15   # .save/.platoon/.zone
FILE_MOD = 16    # старый формат мода / .base
FILE_MOD17 = 17  # текущий формат FCS 1.0.6x (заголовок с длиной + merge-данные)

# --- изменение записи (младшие 4 бита saveData) ---------------------------
CHANGE_NEW, CHANGE_CHANGED, CHANGE_RENAMED = 0, 1, 2

# --- типы записей (порядок как в OCS ItemType; индекс = код в файле) ------
ITEM_TYPES = [
    "BUILDING", "CHARACTER", "WEAPON", "ARMOUR", "ITEM", "ANIMAL_ANIMATION", "ATTACHMENT", "RACE",
    "LOCATION", "WAR_SAVESTATE", "FACTION", "NULL_ITEM", "ZONE_MAP", "TOWN", "WORLDMAP_CHARACTER",
    "CHARACTER_APPEARANCE_OLD", "LOCATIONAL_DAMAGE", "COMBAT_TECHNIQUE", "DIALOGUE", "DIALOGUE_LINE",
    "TECHTREE", "RESEARCH", "AI_TASK", "AI_STATE", "ANIMATION", "STATS", "PERSONALITY", "CONSTANTS",
    "BIOMES", "BUILDING_PART", "INSTANCE_COLLECTION", "DIALOG_ACTION", "TEMPORARY_INFO",
    "MOD_FILENAME", "PLATOON", "GAMESTATE_BUILDING", "GAMESTATE_CHARACTER", "GAMESTATE_FACTION",
    "GAMESTATE_TOWN_INSTANCE_LIST", "STATE", "SAVED_STATE", "INVENTORY_STATE",
    "INVENTORY_ITEM_STATE", "REPEATABLE_BUILDING_PART_SLOT", "MATERIAL_SPEC",
    "MATERIAL_SPECS_COLLECTION", "CONTAINER", "MATERIAL_SPECS_CLOTHING",
    "GAMESTATE_BUILDING_INTERIOR", "VENDOR_LIST", "MATERIAL_SPECS_WEAPON", "WEAPON_MANUFACTURER",
    "SQUAD_TEMPLATE", "ROAD", "LOCATION_NODE", "COLOR_DATA", "CAMERA", "MEDICAL_STATE",
    "MEDICAL_PART_STATE", "FOLIAGE_LAYER", "FOLIAGE_MESH", "GRASS", "BUILDING_FUNCTIONALITY",
    "DAY_SCHEDULE", "NEW_GAME_STARTOFF", "GAMESTATE_CRAFTING", "CHARACTER_APPEARANCE",
    "GAMESTATE_AI", "WILDLIFE_BIRDS", "MAP_FEATURES", "DIPLOMATIC_ASSAULTS",
    "SINGLE_DIPLOMATIC_ASSAULT", "AI_PACKAGE", "DIALOGUE_PACKAGE", "GUN_DATA", "HUMAN_CHARACTER",
    "ANIMAL_CHARACTER", "UNIQUE_SQUAD_TEMPLATE", "FACTION_TEMPLATE", "AI_SCHEDULE", "WEATHER", "SEASON",
    "EFFECT", "ITEM_PLACEMENT_GROUP", "WORD_SWAPS", "NEST", "NEST_ITEM", "CHARACTER_PHYSICS_ATTACHMENT",
    "LIGHT", "HEAD", "BLUEPRINT", "SHOP_TRADER_CLASS", "FOLIAGE_BUILDING", "FACTION_CAMPAIGN",
    "GAMESTATE_TOWN", "BIOME_GROUP", "EFFECT_FOG_VOLUME", "FARM_DATA", "FARM_PART",
    "ENVIRONMENT_RESOURCES", "RACE_GROUP", "ARTIFACTS", "MAP_ITEM", "BUILDINGS_SWAP", "ITEMS_CULTURE",
    "ANIMATION_EVENT", "TUTORIAL", "CROSSBOW", "TERRAIN_DECALS", "AMBIENT_SOUND", "WORLD_EVENT_STATE",
    "LIMB_REPLACEMENT", "ANIMATION_FILE", "BOAT", "GAMESTATE_BOAT", "BUILD_GRID", "BUILDING_SHELL",
]
# коды сверены по ванильным записям (72 AI_PACKAGE … 112 ANIMATION_FILE)


def type_name(code: int) -> str:
    return ITEM_TYPES[code] if 0 <= code < len(ITEM_TYPES) else f"TYPE_{code}"


def type_code(name: str) -> int:
    return ITEM_TYPES.index(name)


# --- типизированные значения ---------------------------------------------
class F32(float):
    """float32-значение (чтобы int и float не путались при записи)."""


class Vec3(tuple):
    pass


class Vec4(tuple):  # x, y, z, w
    pass


class FilePath(str):
    """Значение-путь к файлу (отдельная секция в формате)."""


VALUE_KINDS = (bool, F32, int, Vec3, Vec4, str, FilePath)  # порядок секций в записи


def _kind(v: Any) -> int:
    if isinstance(v, bool):
        return 0
    if isinstance(v, F32):
        return 1
    if isinstance(v, int):
        return 2
    if isinstance(v, Vec3):
        return 3
    if isinstance(v, Vec4):
        return 4
    if isinstance(v, FilePath):
        return 6
    if isinstance(v, str):
        return 5
    if isinstance(v, float):
        return 1
    raise TypeError(f"неподдерживаемое значение {v!r}")


@dataclass
class Ref:
    target: str
    v0: int = 0
    v1: int = 0
    v2: int = 0


@dataclass
class Instance:
    id: str
    target: str
    pos: tuple = (0.0, 0.0, 0.0)
    rot: tuple = (1.0, 0.0, 0.0, 0.0)  # w, x, y, z (в файле w первым)
    states: list = field(default_factory=list)


@dataclass
class Item:
    type: int
    id: int
    name: str
    sid: str
    save_data: int = 0
    values: dict = field(default_factory=dict)       # key -> типизированное значение, порядок = порядок в файле
    refs: dict = field(default_factory=dict)         # категория -> [Ref]
    instances: list = field(default_factory=list)
    _kind_order: list | None = None                  # порядок ключей по секциям (для точного round-trip)
    _len_zero: bool = False                          # в исходнике поле длины было 0 (встречается и в формате 17)
    _len_raw: int | None = None                      # исходное значение поля (для data-файлов пишем как было)

    @property
    def change(self) -> int:
        return self.save_data & 0xF

    @property
    def type_name(self) -> str:
        return type_name(self.type)


@dataclass
class Header:
    version: int = 1
    author: str = ""
    description: str = ""
    dependencies: list = field(default_factory=list)
    references: list = field(default_factory=list)
    save_count: int = 1
    last_merge: int = 0
    merge_entries: list = field(default_factory=list)    # [(key, u1, u2)]
    delete_requests: list = field(default_factory=list)  # [(key, ver, items_str)]
    has_merge_block: bool = True
    has_delete_block: bool = True
    tail: bytes = b""                                    # неразобранный хвост заголовка (страховка)


@dataclass
class ModFile:
    ftype: int = FILE_MOD17
    header: Header | None = field(default_factory=Header)
    last_id: int = 0
    items: list = field(default_factory=list)
    tail_ids: list | None = None   # .zone: хвост «u32 count + count×u32» (занятые номера объектов); None — хвоста нет

    def by_sid(self) -> dict:
        return {it.sid: it for it in self.items}


# --- чтение ----------------------------------------------------------------
class _R:
    def __init__(self, data: bytes):
        self.b = data
        self.p = 0

    def i32(self):
        v = struct.unpack_from("<i", self.b, self.p)[0]; self.p += 4; return v

    def u32(self):
        v = struct.unpack_from("<I", self.b, self.p)[0]; self.p += 4; return v

    def u8(self):
        v = self.b[self.p]; self.p += 1; return v

    def f32(self):
        v = struct.unpack_from("<f", self.b, self.p)[0]; self.p += 4; return F32(v)

    def s(self):
        n = self.i32()
        v = self.b[self.p:self.p + n].decode("utf-8", "surrogateescape"); self.p += n; return v


def read(path_or_bytes) -> ModFile:
    data = path_or_bytes if isinstance(path_or_bytes, (bytes, bytearray)) else open(path_or_bytes, "rb").read()
    r = _R(data)
    m = ModFile(ftype=r.i32(), header=None)
    if m.ftype in (FILE_MOD, FILE_MOD17):
        h = Header()
        end = 0
        if m.ftype >= FILE_MOD17:
            end = r.i32() + r.p
        h.version = r.i32(); h.author = r.s(); h.description = r.s()
        h.dependencies = [x for x in r.s().split(",") if x]
        h.references = [x for x in r.s().split(",") if x]
        h.has_merge_block = m.ftype >= FILE_MOD17 and r.p < end
        if h.has_merge_block:
            h.save_count = r.u32(); h.last_merge = r.u32()
            h.merge_entries = [(r.s(), r.u32(), r.u32()) for _ in range(r.u8())]
            h.has_delete_block = r.p < end
            if h.has_delete_block:
                h.delete_requests = [(r.s(), r.u32(), r.s()) for _ in range(r.u8())]
        if end:
            h.tail = data[r.p:end]; r.p = end
        m.header = h
    m.last_id = r.i32()
    for _ in range(r.i32()):
        m.items.append(_read_item(r))
    if r.p + 4 <= len(data):  # хвост .zone
        n = struct.unpack_from("<i", data, r.p)[0]
        if 0 <= n and r.p + 4 + 4 * n == len(data):
            m.tail_ids = list(struct.unpack_from(f"<{n}I", data, r.p + 4)); r.p = len(data)
    if r.p != len(data):
        raise ValueError(f"лишние байты в конце: {len(data) - r.p}")
    return m


def _read_item(r: _R) -> Item:
    lenfield = r.i32()  # длина записи (mod 17) / 0 / число инстансов (data)
    it = Item(type=r.i32(), id=r.i32(), name=r.s(), sid=r.s(), save_data=r.u32())
    it._len_zero = lenfield == 0
    it._len_raw = lenfield
    readers = [lambda: bool(r.u8()), r.f32, r.i32,
               lambda: Vec3((r.f32(), r.f32(), r.f32())),
               lambda: Vec4((r.f32(), r.f32(), r.f32(), r.f32())),
               r.s, lambda: FilePath(r.s())]
    order = []
    for k, rd in enumerate(readers):
        for _ in range(r.i32()):
            key = r.s()
            it.values[key] = rd()
            order.append((k, key))
    it._kind_order = order
    for _ in range(r.i32()):
        cat = r.s()
        it.refs[cat] = [Ref(r.s(), r.i32(), r.i32(), r.i32()) for _ in range(r.i32())]
    for _ in range(r.i32()):
        it.instances.append(Instance(r.s(), r.s(), (r.f32(), r.f32(), r.f32()),
                                     (r.f32(), r.f32(), r.f32(), r.f32()),
                                     [r.s() for _ in range(r.i32())]))
    return it


# --- запись ----------------------------------------------------------------
class _W:
    def __init__(self):
        self.o = io.BytesIO()

    def i32(self, v): self.o.write(struct.pack("<i", v))
    def u32(self, v): self.o.write(struct.pack("<I", v))
    def u8(self, v): self.o.write(struct.pack("<B", v))
    def f32(self, v): self.o.write(struct.pack("<f", v))

    def s(self, v: str):
        b = v.encode("utf-8", "surrogateescape"); self.i32(len(b)); self.o.write(b)


def write(m: ModFile, path=None) -> bytes:
    w = _W()
    w.i32(m.ftype)
    if m.ftype in (FILE_MOD, FILE_MOD17):
        h = m.header or Header()
        start = 0
        if m.ftype >= FILE_MOD17:
            w.i32(0); start = w.o.tell()
        w.i32(h.version); w.s(h.author); w.s(h.description)
        w.s(",".join(h.dependencies)); w.s(",".join(h.references))
        if m.ftype >= FILE_MOD17:
            if h.has_merge_block:
                w.u32(h.save_count); w.u32(h.last_merge)
                w.u8(len(h.merge_entries))
                for k, a, b in h.merge_entries:
                    w.s(k); w.u32(a); w.u32(b)
                if h.has_delete_block or h.delete_requests:
                    w.u8(len(h.delete_requests))
                    for k, v, s in h.delete_requests:
                        w.s(k); w.u32(v); w.s(s)
            w.o.write(h.tail)
            end = w.o.tell()
            w.o.seek(start - 4); w.i32(end - start); w.o.seek(end)
    w.i32(m.last_id)
    w.i32(len(m.items))
    for it in m.items:
        _write_item(w, it, m.ftype)
    if m.tail_ids is not None:
        w.i32(len(m.tail_ids)); w.o.write(struct.pack(f"<{len(m.tail_ids)}I", *m.tail_ids))
    data = w.o.getvalue()
    if path:
        with open(path, "wb") as f:
            f.write(data)
    return data


def _write_item(w: _W, it: Item, ftype: int):
    start = w.o.tell()
    # data-файлы (.zone/.level): смысл поля не ясен (у INSTANCE_COLLECTION бывает 0 или 5, не число инстансов,
    # вопреки OCS) — пишем как прочитали, для новых записей 0
    w.i32(it._len_raw if ftype == FILE_DATA and it._len_raw is not None else 0)
    w.i32(it.type); w.i32(it.id); w.s(it.name); w.s(it.sid); w.u32(it.save_data)

    # раскладка по секциям: сохраняем исходный порядок, новые ключи — в конец своей секции
    buckets = [[] for _ in VALUE_KINDS]
    seen = set()
    if it._kind_order:
        for k, key in it._kind_order:
            if key in it.values and _kind(it.values[key]) == k:
                buckets[k].append(key); seen.add(key)
    for key, v in it.values.items():
        if key not in seen:
            buckets[_kind(v)].append(key)
    for k, keys in enumerate(buckets):
        w.i32(len(keys))
        for key in keys:
            v = it.values[key]
            w.s(key)
            if k == 0: w.u8(1 if v else 0)
            elif k == 1: w.f32(v)
            elif k == 2: w.i32(int(v))
            elif k == 3: [w.f32(x) for x in v]
            elif k == 4: [w.f32(x) for x in v]
            else: w.s(v)
    w.i32(len(it.refs))
    for cat, refs in it.refs.items():
        w.s(cat); w.i32(len(refs))
        for rf in refs:
            w.s(rf.target); w.i32(rf.v0); w.i32(rf.v1); w.i32(rf.v2)
    w.i32(len(it.instances))
    for ins in it.instances:
        w.s(ins.id); w.s(ins.target)
        [w.f32(x) for x in ins.pos]
        [w.f32(x) for x in ins.rot]
        w.i32(len(ins.states))
        for st in ins.states:
            w.s(st)
    if ftype == FILE_MOD17 and not it._len_zero:  # в формате 16 поле = 0, в 17 — длина записи
        end = w.o.tell()
        w.o.seek(start); w.i32(end - start); w.o.seek(end)


# --- контекст (слияние цепочки модов) и сборщик нового мода ----------------
INT_MAX = 2147483647
DELETED_REF = (INT_MAX, INT_MAX, INT_MAX)


def _copy(it: Item) -> Item:
    return Item(it.type, it.id, it.name, it.sid, it.save_data, dict(it.values),
                {k: [Ref(r.target, r.v0, r.v1, r.v2) for r in v] for k, v in it.refs.items()},
                [Instance(i.id, i.target, i.pos, i.rot, list(i.states)) for i in it.instances])


def apply(merged: dict, mod: ModFile, strict: bool = False) -> list:
    """Накладывает мод на словарь sid->Item.

    strict=True — семантика игры (проверено по kenshi_info.log 2026-11-11): изменение (change != NEW) записи,
    которой нет, игра пропускает с предупреждением «Item X modified by M does not exist». Для core-файлов
    (gamedata.base/Newwworld/Dialogue/rebirth) strict не используем: там все записи помечены как изменённые.
    Возвращает список пропущенных sid.
    """
    skipped = []
    for it in mod.items:
        cur = merged.get(it.sid)
        if it.values.get("DELETED") is True:
            merged.pop(it.sid, None)
            continue
        if cur is None:
            if strict and it.change != CHANGE_NEW:
                skipped.append(it.sid)
                continue
            merged[it.sid] = _copy(it)
            continue
        cur.name = it.name
        cur.values.update(it.values)
        for cat, refs in it.refs.items():
            lst = {r.target: r for r in cur.refs.get(cat, [])}
            for r in refs:
                if (r.v0, r.v1, r.v2) == DELETED_REF:
                    lst.pop(r.target, None)
                else:
                    lst[r.target] = Ref(r.target, r.v0, r.v1, r.v2)
            cur.refs[cat] = list(lst.values())
        inst = {i.id: i for i in cur.instances}
        for i in it.instances:
            if not i.target:
                inst.pop(i.id, None)
            else:
                inst[i.id] = i
        cur.instances = list(inst.values())
    return skipped


def load_chain(paths) -> dict:
    merged: dict = {}
    for p in paths:
        apply(merged, read(p))
    return merged


class ModBuilder:
    """Собирает новый .mod (формат 17) поверх загруженного контекста.

    new()    — новая запись (change=0), полный набор значений; можно клонировать шаблон.
    change() — дельта к существующей записи (change=1, +2 при переименовании).
    delete() — удаление записи (DELETED=true).
    """

    def __init__(self, filename: str, context: dict, dependencies=(), author="", description="", version=1):
        self.filename = filename
        self.ctx = context
        self.items: dict = {}
        self.last_id = 0
        self.header = Header(version=version, author=author, description=description,
                             dependencies=list(dependencies), save_count=1)

    def _sid(self) -> str:
        self.last_id += 1
        return f"{self.last_id}-{self.filename}"

    def resolve(self, sid: str):
        return self.items.get(sid) or self.ctx.get(sid)

    def new(self, tname: str, name: str, values=None, refs=None, template: str | None = None,
            sid: str | None = None) -> Item:
        it = Item(type_code(tname), 0, name, sid or self._sid(), CHANGE_NEW | (1 << 4))
        if template:
            src = self.resolve(template)
            if src is None or src.type_name != tname:
                raise KeyError(f"шаблон {template} не найден или не {tname}")
            it.values = dict(src.values)
            it.refs = {k: [Ref(r.target, r.v0, r.v1, r.v2) for r in v] for k, v in src.refs.items()}
        it.values.update(values or {})
        for cat, lst in (refs or {}).items():
            it.refs[cat] = [r if isinstance(r, Ref) else Ref(*r) for r in lst]
        self.items[it.sid] = it
        return it

    def change(self, sid: str, values=None, set_refs=None, del_refs=None, rename: str | None = None) -> Item:
        src = self.ctx.get(sid)
        if src is None:
            raise KeyError(sid)
        it = self.items.get(sid) or Item(src.type, 0, src.name, sid, CHANGE_CHANGED | (1 << 4))
        if rename:
            it.name = rename; it.save_data |= CHANGE_RENAMED
        it.values.update(values or {})
        for cat, lst in (set_refs or {}).items():
            it.refs.setdefault(cat, []).extend(r if isinstance(r, Ref) else Ref(*r) for r in lst)
        for cat, targets in (del_refs or {}).items():
            it.refs.setdefault(cat, []).extend(Ref(t, *DELETED_REF) for t in targets)
        self.items[sid] = it
        return it

    def delete(self, sid: str) -> Item:
        src = self.ctx[sid]
        it = Item(src.type, 0, src.name, sid, CHANGE_CHANGED | (1 << 4), {"DELETED": True})
        self.items[sid] = it
        return it

    def build(self) -> ModFile:
        return ModFile(FILE_MOD17, self.header, self.last_id, list(self.items.values()))
