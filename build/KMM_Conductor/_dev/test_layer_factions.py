"""Гейт: ни одному отряду/персонажу разные слои KMM_* не дают разные фракции (баг Mongrel 2026-11-14). python -I -X utf8 build/KMM_Conductor/_dev/test_layer_factions.py -> OK."""
import subprocess, sys
r = subprocess.run([sys.executable, "-I", "-X", "utf8", r"C:\KenshiModMap\tools\check_layer_factions.py"], capture_output=True, text=True, encoding="utf-8")
print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-500:])
sys.exit(r.returncode)
