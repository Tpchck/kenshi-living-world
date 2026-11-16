"""PUBLISH (2026-11-16): KenshiLua runs every scripts/init/*.lua in its own sandbox, so `KMM_X = ...` is invisible to
other modules (KMM_Probe saw 14 modules as absent; Fates bounty link idle). Every global module table must also be
published with rawset(_G, "KMM_X", ...) or _G.KMM_X = .... Static check over build/*/scripts/init."""
import glob, re, sys
bad = []
for f in glob.glob(r"C:\KenshiModMap\build\*\scripts\init\*.lua"):
    t = open(f, encoding="utf-8").read()
    for nm in set(re.findall(r"(?m)^(KMM_[A-Za-z]+)\s*=", t)):
        if not re.search(r'_G\.%s\s*=|rawset\(_G,\s*"%s"' % (nm, nm), t):
            bad.append(f.split("\\")[-1] + ":" + nm)
print("OK" if not bad else "FAIL unpublished: " + ", ".join(sorted(bad)))
sys.exit(1 if bad else 0)
