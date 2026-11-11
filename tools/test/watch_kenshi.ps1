# Фоновый наблюдатель тестового запуска Kenshi.
# Ждёт kenshi_x64.exe, каждые $Interval с пишет память в logs\mem.csv, фиксирует выход и код выхода.
# Если игра перезапустилась в течение $IdleExitSec после выхода — следит и за новым процессом.
# В конце: копирует логи игры, новые .dmp и события журнала Application в logs\run_<время>\ и пишет test_done.json.
param(
    [string]$Out = 'C:\KenshiModMap\logs',
    [int]$Interval = 5,
    [int]$IdleExitSec = 120,
    [int]$MaxWaitStartMin = 720,
    [string]$ProcName = 'kenshi_x64'
)
$ErrorActionPreference = 'Continue'
$Game = 'C:\Program Files (x86)\Steam\steamapps\common\Kenshi'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$csv = Join-Path $Out 'mem.csv'
$evlog = Join-Path $Out 'watch_events.log'
$started = Get-Date
function Log($m) { $l = "{0:yyyy-MM-dd HH:mm:ss} {1}" -f (Get-Date), $m; Add-Content -LiteralPath $evlog -Value $l -Encoding UTF8 }

Set-Content -LiteralPath (Join-Path $Out 'test_start.txt') -Value ($started.ToString('yyyy-MM-dd HH:mm:ss')) -Encoding UTF8
if (-not (Test-Path $csv)) { Set-Content -LiteralPath $csv -Value 'time,pid,working_set_mb,private_mb,peak_working_set_mb,cpu_s,handles' -Encoding UTF8 }
Log "watcher started; test start = $started; waiting for kenshi_x64.exe (max $MaxWaitStartMin min)"

$sessions = @()
$deadline = $started.AddMinutes($MaxWaitStartMin)
$lastExit = $null
while ($true) {
    $p = Get-Process -Name $ProcName -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $p) {
        if ($lastExit -and ((Get-Date) - $lastExit).TotalSeconds -ge $IdleExitSec) { break }
        if (-not $lastExit -and (Get-Date) -gt $deadline) { Log 'timeout: kenshi_x64.exe не появился'; break }
        Start-Sleep -Seconds 2; continue
    }
    $null = $p.Handle   # держим хэндл, чтобы после выхода прочитать ExitCode
    $s = [ordered]@{ pid = $p.Id; start = $p.StartTime.ToString('yyyy-MM-dd HH:mm:ss'); exit = $null; exit_code = $null;
                     exit_code_hex = $null; peak_working_set_mb = 0; peak_private_mb = 0; samples = 0 }
    Log "process found pid=$($p.Id) start=$($s.start)"
    while (-not $p.HasExited) {
        try {
            $p.Refresh()
            $ws = [math]::Round($p.WorkingSet64 / 1MB, 1); $pr = [math]::Round($p.PrivateMemorySize64 / 1MB, 1)
            $pk = [math]::Round($p.PeakWorkingSet64 / 1MB, 1)
            $cpu = [math]::Round($p.TotalProcessorTime.TotalSeconds, 1)
            Add-Content -LiteralPath $csv -Value ("{0:yyyy-MM-dd HH:mm:ss},{1},{2},{3},{4},{5},{6}" -f (Get-Date), $p.Id, $ws, $pr, $pk, $cpu, $p.HandleCount) -Encoding UTF8
            if ($pk -gt $s.peak_working_set_mb) { $s.peak_working_set_mb = $pk }
            if ($pr -gt $s.peak_private_mb) { $s.peak_private_mb = $pr }
            $s.samples++
        } catch { }
        Start-Sleep -Seconds $Interval
    }
    $p.WaitForExit()
    $lastExit = Get-Date
    $s.exit = $p.ExitTime.ToString('yyyy-MM-dd HH:mm:ss')
    try { $s.exit_code = $p.ExitCode; $s.exit_code_hex = ('0x{0:X8}' -f $p.ExitCode) } catch { $s.exit_code = 'unknown' }
    Log "process exited pid=$($s.pid) at $($s.exit) code=$($s.exit_code) ($($s.exit_code_hex)) peakWS=$($s.peak_working_set_mb)MB peakPrivate=$($s.peak_private_mb)MB"
    $sessions += [pscustomobject]$s
}

# --- сбор артефактов ---
$run = Join-Path $Out ('run_' + $started.ToString('yyyy-MM-dd_HHmm'))
New-Item -ItemType Directory -Force -Path $run | Out-Null
foreach ($f in 'kenshi.log', 'kenshi_info.log', 'save.log', 'Havok.log', 'MyGUI.log', 'RE_Kenshi_log.txt') {
    $src = Join-Path $Game $f
    if ((Test-Path $src) -and ((Get-Item $src).LastWriteTime -ge $started)) { Copy-Item -LiteralPath $src -Destination $run }
}
$dumpDirs = @((Join-Path $Game 'crashDump'), $Game, (Join-Path $env:LOCALAPPDATA 'CrashDumps'), (Join-Path $env:LOCALAPPDATA 'kenshi'))
$dumps = @()
# архивы/дампы краш-хендлера RE_Kenshi (crashDump*.zip и т.п.) — ищем рекурсивно в папке игры, кроме mods/data
Get-ChildItem -LiteralPath $Game -Recurse -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Extension -in '.zip', '.dmp' -and $_.LastWriteTime -ge $started -and $_.FullName -notmatch '\\(mods|data)\\' } | ForEach-Object {
        Copy-Item -LiteralPath $_.FullName -Destination $run -ErrorAction SilentlyContinue; $dumps += $_.FullName }
foreach ($d in $dumpDirs) {
    if (Test-Path $d) {
        Get-ChildItem -LiteralPath $d -Filter '*.dmp' -File -ErrorAction SilentlyContinue | Where-Object { $_.LastWriteTime -ge $started } | ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $run; $dumps += $_.FullName }
    }
}
$events = @()
try {
    $events = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; StartTime = $started } -ErrorAction Stop |
        Where-Object { ($_.ProviderName -in 'Application Error', 'Windows Error Reporting', 'Application Hang', '.NET Runtime') -and $_.Message -match 'kenshi' } |
        ForEach-Object { [pscustomobject]@{ time = $_.TimeCreated.ToString('yyyy-MM-dd HH:mm:ss'); id = $_.Id; provider = $_.ProviderName; message = $_.Message } }
} catch { Log "events: $($_.Exception.Message)" }
$events | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $run 'app_events.json') -Encoding UTF8
Copy-Item -LiteralPath $csv -Destination $run
[pscustomobject]@{ test_start = $started.ToString('yyyy-MM-dd HH:mm:ss'); finished = (Get-Date).ToString('yyyy-MM-dd HH:mm:ss');
                   run_dir = $run; sessions = $sessions; dumps = $dumps; app_events = @($events).Count } |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $Out 'test_done.json') -Encoding UTF8
Log "done; artifacts in $run; sessions=$(@($sessions).Count) dumps=$(@($dumps).Count) events=$(@($events).Count)"
