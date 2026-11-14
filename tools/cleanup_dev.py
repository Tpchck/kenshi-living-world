"""Чистка папки разработки: старые бэкапы *.pre_*, _bak, логи прогонов, старые релизы (кроме 3 последних) -> один zip; __pycache__ удаляется."""
import os, zipfile, shutil, re, glob, sys
R = r'C:\KenshiModMap'
os.chdir(R)
N = lambda p: os.path.normpath(p).replace(os.sep, '/')
skip = ('tools/ref', 'tools/cpp', 'backup/archive', 'tools/rekenshi', 'backup/releases', 'backup/cfg')
pat = re.compile(r'(\.pre_|_pre_|^_bak_)')
KEEP = re.compile(r'(_pre_perf|_pre_s5|_pre_t2|pre_test1)')  # эталоны бенчей: test_perf/test_perf2 (_pre_perf*), test_s5_perf (_pre_s5), test_t2_gov (_pre_t2)
# + любой файл, имя которого упоминает какой-либо тест/инструмент (build/*/_dev/*.py, tools/**/*.py): его читают — не архивировать
READ = set()
for _p in glob.glob('build/*/_dev/*.py') + glob.glob('tools/**/*.py', recursive=True):
    if N(_p).startswith(('tools/ref/', 'tools/archive/')) or N(_p) == 'tools/cleanup_dev.py':
        continue
    try:
        READ.update(re.findall(r'[\w.-]*(?:\.pre_|_pre_|_bak_)[\w.-]*', open(_p, encoding='utf-8', errors='replace').read()))
    except OSError:
        pass
targets = []
for d, ds, fs in os.walk('.'):
    nd = N(d)
    if any(nd == s or nd.startswith(s + '/') for s in skip): ds[:] = []; continue
    for f in fs:
        if pat.search(f) and not KEEP.search(f) and f not in READ: targets.append(N(os.path.join(d, f)))
rel = sorted(glob.glob('backup/releases/*'))
dirs = ['tools/streams/_bak', 'backup/logs', 'logs/ref_vanilla_spike1_1946'] + glob.glob('logs/run_*') + rel[:-3]
files = targets + glob.glob('logs/verify_fail_*') + glob.glob('logs/_*.txt')
z = sys.argv[1]
n = size = 0
with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as Z:
    for f in files:
        if os.path.isfile(f): size += os.path.getsize(f); Z.write(f); n += 1
    for d in dirs:
        for dd, _, fs in os.walk(d):
            for f in fs:
                p = os.path.join(dd, f); size += os.path.getsize(p); Z.write(p); n += 1
with zipfile.ZipFile(z) as Z:
    bad = Z.testzip(); cnt = len(Z.namelist())
assert bad is None and cnt == n, (bad, cnt, n)
for f in files:
    if os.path.isfile(f): os.remove(f)
for d in dirs:
    if os.path.isdir(d): shutil.rmtree(d)
pc = 0
for d, ds, fs in os.walk('.'):
    for x in list(ds):
        if x == '__pycache__': shutil.rmtree(os.path.join(d, x)); ds.remove(x); pc += 1
print('archived', n, 'files', round(size / 1e6, 1), 'MB ->', round(os.path.getsize(z) / 1e6, 1), 'MB; pycache', pc, '; releases kept', [N(r) for r in rel[-3:]])
