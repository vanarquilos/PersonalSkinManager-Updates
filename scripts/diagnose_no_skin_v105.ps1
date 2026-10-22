# PSM v1.0.5 — read-only no-skin diagnostics; does not modify game/PSM/runtime.
# Run after a failed test: powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\diagnose_no_skin_v105.ps1
param([int]$LogLines = 6000)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
$IssueFile = Join-Path $env:LOCALAPPDATA "Rose\rose_diagnostics.txt"
$Report = Join-Path ([Environment]::GetFolderPath("Desktop")) "PSM-v1.0.5-no-skin-report.txt"

$Markers = [ordered]@{
    "Patch 26.21 material format parsing" = '(?i)invalid property kind|no discriminant in enum|original WAD has a corrupt bin|staticmaterialdef.*hash'
    "Overlay verification rejected" = '(?i)overlay verification failed|overlay rejected|base-skin baseline anomaly'
    "Patcher verified zero WAD files" = '(?i)overlay verified\s+0\s+wad'
    "Patcher redirected a WAD" = '(?i)redirected wad:'
    "Patcher injected or attached" = '(?i)\bstatus\s+\S+\s+injected\b|\bdll attached\b|host\s+injected'
    "LTK runtime unsupported or expired" = '(?i)end.of.life|runtime does not support this League build|patcher DLL reached|LTK_PATCHER_EOL'
    "Patcher joined too late" = '(?i)joined too late|started before the LTK scanner was ready'
    "Patcher startup failed" = '(?i)Could not arm LTK scanner|Scanner exited before|Scanner failed before|Missing LTK runtime|Could not start scanner'
    "Overlay builder error or timeout" = '(?i)mkoverlay failed|mkoverlay timeout|mkoverlay error|error.*mkoverlay'
    "Overlay preparation succeeded" = '(?i)mkoverlay completed|overlay ready'
    "WAD header validation failed" = '(?i)No overlay WAD headers could be rebased|WAD magic/version mismatch|WAD header verification failed'
    "Skin selection missing" = '(?i)no skin ID available|skipping injection for default skin|no selected skin'
    "Swiftplay overlay preparation" = '(?i)Swiftplay.*overlay|Swiftplay.*injection|Swiftplay.*skin'
}

$Logs = @(Get-ChildItem -LiteralPath $LogDir -File -Filter "rose_*.log*" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -First 2)
$lines = @()
foreach ($Item in $Logs) {
    $lines += @(Get-Content -LiteralPath $Item.FullName -Tail $LogLines -ErrorAction SilentlyContinue)
}

$summary = [System.Collections.Generic.List[string]]::new()
$summary.Add("PSM v1.0.5 — no-skin diagnosis")
$summary.Add("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"))
$summary.Add("This report contains only known failure markers and hashes, not raw logs.")
$summary.Add("")
$summary.Add("Log sessions found: $($Logs.Count)")
if ($Logs.Count -gt 0) {
    $summary.Add("Latest log modified: " + $Logs[0].LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"))
    if ($Logs[0].LastWriteTime -lt (Get-Date).AddDays(-2)) {
        $summary.Add("WARNING: latest log is older than 48 hours; may not cover this failure.")
    }
}
else {
    $summary.Add("No PSM log found at the default local log location.")
    $summary.Add("To generate a log, run scripts/run_live_qa.ps1 from the candidate branch.")
}

$summary.Add("")
$summary.Add("Known signatures:")
$Counts = @{}
foreach ($Name in $Markers.Keys) {
    $count = @($lines | Where-Object { $_ -match $Markers[$Name] }).Count
    $Counts[$Name] = $count
    $summary.Add(" - " + $Name + ": " + $count)
}
$summary.Add("")
$summary.Add("Preliminary classification:")
if ($Counts["Patch 26.21 material format parsing"] -gt 0) {
    $summary.Add("LIKELY: League 26.21 material-format incompatibility in bundled LTK. Do not bypass verification.")
}
elseif ($Counts["Overlay verification rejected"] -gt 0) {
    $summary.Add("LTK rejected the overlay. Inspect the exact rejection with sanitized logs.")
}
elseif ($Counts["LTK runtime unsupported or expired"] -gt 0) {
    $summary.Add("LTK runtime unsupported for installed League. Do not bypass cutoff.")
}
elseif ($Counts["Overlay builder error or timeout"] -gt 0 -or $Counts["WAD header validation failed"] -gt 0) {
    $summary.Add("Overlay creation or validation failed.")
}
elseif ($Counts["Patcher verified zero WAD files"] -gt 0) {
    $summary.Add("Patcher attached but verified zero overlay WADs.")
}
elseif ($Counts["Patcher joined too late"] -gt 0) {
    $summary.Add("Patcher joined the game after scan startup deadline.")
}
elseif ($Counts["Skin selection missing"] -gt 0) {
    $summary.Add("No usable skin selection/trigger when preparing overlay.")
}
else {
    $summary.Add("Inconclusive; need recent PSM game-session log or live test.")
}

$summary.Add("")
$summary.Add("Candidate source runtime hashes (identity only; not compatibility proof):")
foreach ($Name in @("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
    $p = Join-Path $Root ("injection\tools\" + $Name)
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        $hash = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
        $size = (Get-Item -LiteralPath $p).Length
        $summary.Add(" - " + $Name + ": " + $size + " bytes | SHA-256 " + $hash)
    }
    else {
        $summary.Add(" - " + $Name + ": missing in source checkout")
    }
}
$candidateAudit = Join-Path $Root "installer\candidates\v1.0.5\reports\runtime-audit.json"
if (Test-Path -LiteralPath $candidateAudit -PathType Leaf) {
    $summary.Add("Build-time runtime audit: present (not copied because it contains local paths).")
}
if (Test-Path -LiteralPath $IssueFile -PathType Leaf) {
    $summary.Add("PSM diagnostics summary: present (raw contents not copied).")
}
$summary.Add("")
$summary.Add("Share this report rather than full League Client logs, passwords or tokens.")
$summary | Set-Content -LiteralPath $Report -Encoding UTF8
$summary | ForEach-Object { Write-Host $_ }
Write-Host ""
Write-Host "Saved diagnostic: $Report" -ForegroundColor Cyan
