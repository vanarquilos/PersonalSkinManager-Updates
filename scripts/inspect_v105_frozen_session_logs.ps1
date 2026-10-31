# PSM v1.0.5 - read-only frozen-session log fingerprint, sanitized counts.
# Execute after local QA test with -SinceLocal set to the time recorded
# BEFORE the test began. Shared Rose logs may contain unrelated sessions.
param(
    [Parameter(Mandatory = $true)][datetime]$SinceLocal
)
$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$LogDir = Join-Path $env:LOCALAPPDATA "Rose\logs"
Write-Host "PSM frozen-source comparison: sanitized, read-only log summary" -ForegroundColor Cyan
Write-Host ("Test-start local: " + $SinceLocal.ToString("yyyy-MM-dd HH:mm:ss"))
if (-not (Test-Path -LiteralPath $LogDir -PathType Container)) {
    Write-Warning "Shared Rose log directory not found. Application may have used a different user profile."
    exit 0
}
$Candidates = @(Get-ChildItem -LiteralPath $LogDir -File -ErrorAction SilentlyContinue |
    Where-Object { $_.Name -match '^rose_.*\.log' -and $_.LastWriteTime -ge $SinceLocal } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 3)
Write-Host ("Recent shared PSM log files modified since test start: " + $Candidates.Count)
if ($Candidates.Count -eq 0) {
    Write-Warning "No updated PSM log files were found; cannot classify the frozen run."
    exit 0
}
$Patterns = [ordered]@{
    "LTK startup" = '(?i)Starting LTK patcher-host scanner|Scanner armed before'
    "LTK hook failure" = '(?i)SetWindowsHookEx failed|failed to install .* hook|hook install failed'
    "Host verification refused" = '(?i)host verification failed|LTK_HOST_VERIFICATION_FAILED'
    "Unsupported runtime" = '(?i)end.of.life|does not support this League build|LTK_PATCHER_EOL'
    "Host attached" = '(?i)status=injected|status\s+[\d.]+\s+\S+\s+injected|dll attached'
    "WAD verification" = '(?i)overlay verified\s+\d+\s+wad'
    "WAD redirection" = '(?i)redirected wad:|WAD redirection observed'
    "WAD rejected" = '(?i)overlay verification failed|lazy verification failed|WAD verification failed'
    "Overlay ready" = '(?i)mkoverlay completed|overlay ready'
    "Overlay failed" = '(?i)mkoverlay failed|Overlay builder error|mkoverlay timeout'
    "Skin not selected" = '(?i)no skin ID available|skipping injection for default skin|no selected skin'
    "League not detected" = '(?i)League game directory not found|client disconnected|LCU.*offline'
    "Startup process error" = '(?i)Could not start scanner|could not arm LTK scanner|FileNotFoundError|WinError\s+\d+'
}
foreach ($File in $Candidates) {
    $Age = [int][math]::Round(((Get-Date) - $File.LastWriteTime).TotalMinutes)
    $Lines = @(Get-Content -LiteralPath $File.FullName -Tail 8000 -ErrorAction SilentlyContinue)
    Write-Host ("--- Shared log age: " + $Age + " min; lines read: " + $Lines.Count)
    foreach ($Label in $Patterns.Keys) {
        $Count = @($Lines | Where-Object { $_ -match $Patterns[$Label] }).Count
        if ($Count -gt 0) { Write-Host ("  " + $Label + ": " + $Count) }
    }
}
Write-Warning "Shared Rose logs are not conclusively attributed to the tested frozen process; verify no other PSM was running."
Write-Host "No raw paths, tokens, mod archive names or user identities are printed. No files were changed."
