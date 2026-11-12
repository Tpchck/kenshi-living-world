"""Замер памяти Kenshi во время игре (разрешено 2026-11-12): раз в 60 с, только tasklist, почти без нагрузки.
Ждёт запуска игры до 2 ч, пишет logs\\mem.csv (время, рабочий набор МБ), выходит через 2 мин после закрытия игры."""
import os
import re
import subprocess
import time

OUT = r"C:\KenshiModMap\logs\mem.csv"
WAIT_S = int(os.environ.get("KMM_MEMWATCH_WAIT", "7200"))   # сколько ждать запуска игры владельцем (с)


def mem_mb():
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq kenshi_x64.exe", "/FO", "CSV", "/NH"], capture_output=True, text=True).stdout
    m = re.search(r'"kenshi_x64\.exe".*?"([\d\s.,\xa0]+)\s*K"', out, re.I)
    return int(re.sub(r"\D", "", m.group(1))) // 1024 if m else None


def main():
    t0, seen, gone = time.time(), False, None
    new = not os.path.exists(OUT)
    with open(OUT, "a", encoding="utf-8") as f:
        if new:
            f.write("time,mb\n")
        while True:
            m = mem_mb()
            if m:
                seen, gone = True, None
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')},{m}\n"); f.flush()
            elif seen:
                gone = gone or time.time()
                if time.time() - gone > 120:
                    break
            elif time.time() - t0 > WAIT_S:
                break
            time.sleep(60)


if __name__ == "__main__":
    main()
