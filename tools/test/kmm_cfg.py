"""Переключение mods.cfg для теста/бисекции (Kenshi должен быть закрыт).

python -I -X utf8 tools/test/kmm_cfg.py full                     # backup/mods.cfg.test2 как есть
python -I -X utf8 tools/test/kmm_cfg.py without KMM_Relics,KMM_Economy   # без указанных KMM_*
python -I -X utf8 tools/test/kmm_cfg.py only KMM_Core,KMM_Conductor      # из KMM_* только указанные
python -I -X utf8 tools/test/kmm_cfg.py restore                  # вернуть backup/mods.cfg.pre_test1
"""
import subprocess
import sys

CFG = r"C:\Program Files (x86)\Steam\steamapps\common\Kenshi\data\mods.cfg"
FULL = r"C:\KenshiModMap\backup\mods.cfg.test2"
PRE = r"C:\KenshiModMap\backup\mods.cfg.pre_test1"

if "kenshi_x64.exe" in subprocess.run(["tasklist"], capture_output=True, text=True).stdout.lower():
    sys.exit("Kenshi запущен — закройте игру")
mode = sys.argv[1]
src = PRE if mode == "restore" else FULL
lines = [l for l in open(src, "rb").read().decode("utf-8").split("\r\n") if l]
if mode in ("without", "only"):
    names = {n if n.endswith(".mod") else n + ".mod" for n in sys.argv[2].split(",")}
    kmm = [l for l in lines if l.startswith("KMM_")]
    unknown = names - set(kmm)
    if unknown:
        sys.exit(f"нет в списке: {sorted(unknown)}; есть: {kmm}")
    keep = (lambda l: l not in names) if mode == "without" else (lambda l: l in names)
    lines = [l for l in lines if not l.startswith("KMM_") or keep(l)]
open(CFG, "wb").write("".join(l + "\r\n" for l in lines).encode("utf-8"))
print(f"mods.cfg <- {mode}: {len(lines)} модов; KMM: {[l for l in lines if l.startswith('KMM_')]}")
