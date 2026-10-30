# Read-only sanitized detail on frozen PSM hook failures since one test start.
# Does not replay an injection, alter files, or report raw log lines.
param(
    [Parameter(Mandatory = $true)][datetime]$SinceLocal
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
Write-Host "PSM v1.0.5 - frozen hook failure classification (read-only)" -ForegroundColor Cyan
Write-Host ("Local test start: " + $SinceLocal.ToString("yyyy-MM-dd HH:mm:ss"))
if (-not (Test-Path -LiteralPath $LogDir -PathType Container)) {
    Write-Warning "No local Rose log directory."
    exit 0
}
$Logs = @(Get-ChildItem -LiteralPath $LogDir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^rose_.*\.log' -and $_.LastWriteTime -ge $SinceLocal } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3)
$Codes = [ordered]@{}
$Counts = [ordered]@{
    "App initialization" = 0
    "Main process ready" = 0
    "LCU/client activity" = 0
    "Gameflow/loadout activity" = 0
    "Selected-skin/injection trigger" = 0
    "LTK scanner startup" = 0
    "Hook failures" = 0
    "Host verification errors" = 0
    "DLL overlay initialized" = 0
    "WAD redirection" = 0
    "Host attached" = 0
    "Overlay preparation" = 0
    "Launcher startup" = 0
    "Startup/runtime errors" = 0
}
$TimedLines = 0
$FirstObserved = $null
$LastObserved = $null
$IgnoredUndatedLines = 0
$Samples = @()
foreach ($Log in $Logs) {
    $Lines = @(Get-Content -LiteralPath $Log.FullName -Tail 10000 -ErrorAction SilentlyContinue)
    foreach ($Line in $Lines) {
        if ($Line -notmatch '^(?<stamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})\s*\|') {
            $IgnoredUndatedLines++
            continue
        }
        $Stamp = [datetime]::ParseExact(
            $Matches.stamp, "yyyy-MM-dd HH:mm:ss",
            [System.Globalization.CultureInfo]::InvariantCulture)
        if ($Stamp -lt $SinceLocal.AddSeconds(-2)) { continue }
        $TimedLines++
        if ($null -eq $FirstObserved -or $Stamp -lt $FirstObserved) { $FirstObserved = $Stamp }
        if ($null -eq $LastObserved -or $Stamp -gt $LastObserved) { $LastObserved = $Stamp }
        if ($Line -match '(?i)Personal Skin Manager Starting|Initializing LCU client|Initializing shared state|Initializing injection manager') {
            $Counts["App initialization"]++
        }
        if ($Line -match '(?i)System ready|WebSocket status is active|App status manager initialized') {
            $Counts["Main process ready"]++
        }
        if ($Line -match '(?i)LCU client initialized|LCU reconnected|LCU disconnected|WebSocket status|client phase|client session') {
            $Counts["LCU/client activity"]++
        }
        if ($Line -match '(?i)ChampSelect|loadout countdown|Loadout Timer|Gameflow|InProgress|game phase') {
            $Counts["Gameflow/loadout activity"]++
        }
        if ($Line -match '(?i)PREPARING INJECTION|Using skin file:|INJECTION FAILED - NO SKIN ID|selected custom mod') {
            $Counts["Selected-skin/injection trigger"]++
        }
        if ($Line -match '(?i)Starting LTK patcher-host scanner|Arming current LTK scanner|scanner pre-armed') {
            $Counts["LTK scanner startup"]++
        }
        if ($Line -match '(?i)FATAL ERROR|Failed to initialize injection manager|Missing LTK runtime|Could not arm LTK scanner|Could not start scanner') {
            $Counts["Startup/runtime errors"]++
        }
        if ($Line -match '(?i)SetWindowsHookEx failed|failed to install .* hook|hook install failed') {
            $Counts["Hook failures"]++
            $Capture = [regex]::Match($Line, '(?i)SetWindowsHookEx failed\s*:\s*(0x[0-9a-f]+|\d+)')
            $Code = if ($Capture.Success) { $Capture.Groups[1].Value.ToUpperInvariant() } else { "NO_NUMERIC_CODE" }
            if (-not $Codes.Contains($Code)) { $Codes[$Code] = 0 }
            $Codes[$Code]++
            if ($Samples.Count -lt 8) {
                $Samples += ("  " + $Stamp.ToString("HH:mm:ss") + " | hook failure | code=" + $Code)
            }
        }
        if ($Line -match '(?i)host verification failed|LTK_HOST_VERIFICATION_FAILED') {
            $Counts["Host verification errors"]++
        }
        if ($Line -match '(?i)DLL overlay initialization confirmed|DLL overlay initialization observed: True') {
            $Counts["DLL overlay initialized"]++
        }
        if ($Line -match '(?i)redirected wad:|WAD redirection observed') {
            $Counts["WAD redirection"]++
        }
        if ($Line -match '(?i)status=injected|status\s+[\d.]+\s+\S+\s+injected|dll attached') {
            $Counts["Host attached"]++
        }
        if ($Line -match '(?i)mkoverlay completed|overlay ready') {
            $Counts["Overlay preparation"]++
        }
        if ($Line -match '(?i)Launcher sequence starting|Launcher sequence completed') {
            $Counts["Launcher startup"]++
        }
    }
}
Write-Host ("Modified shared logs examined: " + $Logs.Count)
Write-Host ("Timestamped log lines since start: " + $TimedLines)
if ($null -ne $FirstObserved) {
    Write-Host ("First observed logged event: " + $FirstObserved.ToString("yyyy-MM-dd HH:mm:ss"))
    Write-Host ("Last observed logged event: " + $LastObserved.ToString("yyyy-MM-dd HH:mm:ss"))
}
foreach ($Category in $Counts.Keys) { Write-Host ($Category + ": " + $Counts[$Category]) }
if ($TimedLines -eq 0) {
    Write-Warning "No timestamped entries since test start. This log cannot establish the QA application was running or logging in this profile."
}
elseif ($Counts["Selected-skin/injection trigger"] -eq 0 -and $Counts["LTK scanner startup"] -eq 0) {
    Write-Warning "Application log activity was observed, but no injection trigger or scanner startup was recorded. Check whether a Practice Tool session occurred and whether this is the correct QA process."
}
Write-Host "Exact hook failure codes:"
if ($Codes.Count -eq 0) { Write-Host "  none extracted" }
foreach ($Code in $Codes.Keys) { Write-Host ("  " + $Code + ": " + $Codes[$Code]) }
Write-Host "Samples (timestamp, category, code only):"
foreach ($Sample in $Samples) { Write-Host $Sample }
Write-Host ("Undated/unparseable lines skipped: " + $IgnoredUndatedLines)
Write-Warning "Rose logs are shared; ensure the installed and source PSM were closed during this test."
Write-Host "Raw log strings, filesystem paths, user names and tokens are not printed. No changes made."
