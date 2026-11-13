"""Разбор minidump Kenshi (только чтение): где упало и какие модули в стеке.
python tools\\mdmp.py <crashDump.dmp>"""
import struct
import sys


def main(p):
    b = open(p, "rb").read()
    _, _, n, rdir = struct.unpack_from("<IIII", b, 0)
    st = {}
    for i in range(n):
        t, size, rva = struct.unpack_from("<III", b, rdir + 12 * i)
        st.setdefault(t, (size, rva))

    def mstr(rva):
        k = struct.unpack_from("<I", b, rva)[0]
        return b[rva + 4: rva + 4 + k].decode("utf-16le", "replace")
    mods = []
    if 4 in st:
        _, rva = st[4]
        for i in range(struct.unpack_from("<I", b, rva)[0]):
            o = rva + 4 + 108 * i
            base, sz = struct.unpack_from("<QI", b, o)
            mods.append((base, sz, mstr(struct.unpack_from("<I", b, o + 20)[0]).split("\\")[-1]))

    def where(a):
        for base, sz, nm in mods:
            if base <= a < base + sz:
                return f"{nm}+0x{a - base:X}"
        return None
    if 6 not in st:
        print("нет потока исключения"); return
    _, rva = st[6]
    code = struct.unpack_from("<I", b, rva + 8)[0]
    addr = struct.unpack_from("<Q", b, rva + 24)[0]
    print(f"исключение 0x{code:08X} в {where(addr) or hex(addr)}")
    csize, crva = struct.unpack_from("<II", b, rva + 8 + 152)
    ctx = b[crva: crva + csize]
    if len(ctx) < 0x100 or 5 not in st:
        return
    rsp = struct.unpack_from("<Q", ctx, 0x98)[0]
    _, mr = st[5]
    for i in range(struct.unpack_from("<I", b, mr)[0]):
        start, dsz, drva = struct.unpack_from("<QII", b, mr + 4 + 16 * i)
        if start <= rsp < start + dsz:
            off, hits = rsp - start, []
            for k in range(0, min(dsz - off, 0x6000), 8):
                w = where(struct.unpack_from("<Q", b, drva + off + k)[0])
                if w and not w.lower().startswith(("kernel", "ntdll", "ucrtbase", "msvcr", "msvcp")):
                    hits.append(w)
            print("модули в стеке:", hits[:30])


if __name__ == "__main__":
    main(sys.argv[1])
