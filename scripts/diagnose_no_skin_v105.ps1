# PSM v1.0.5 - read-only no-skin diagnostics; does not modify game/PSM/runtime.
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
    "Patcher redirected a WAD" = '(?i)redirected wad:|WAD redirection observed'
    "LTK DLL overlay initialized" = '(?i)DLL overlay initialization confirmed|DLL overlay initialization observed: True'
    "LTK lazy WAD rejection" = '(?i)lazy verification failed, not overlaying|LTK did not apply the overlay: WAD verification failed'
    "LTK hook initialization failed" = '(?i)failed to install .* hook|LTK could not initialize a required hook'
    "LTK WAD integrity scan error" = '(?i)LTK WAD integrity scan failed'
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

# Exclude pre-staging failures and outdated session logs. Otherwise the previous
# expired-DLL messages can falsely classify a new v1.30.1 test as failed.
$EvidenceSince = (Get-Date).AddHours(-48)
$OriginPath = Join-Path $Root "injection\tools\_v105_runtime_origin.json"
if (Test-Path -LiteralPath $OriginPath -PathType Leaf) {
    try {
        $Origin = Get-Content -LiteralPath $OriginPath -Raw | ConvertFrom-Json
        $StagedAt = ([datetimeoffset]::Parse([string]$Origin.created_utc)).LocalDateTime
        if ($StagedAt -gt $EvidenceSince) { $EvidenceSince = $StagedAt }
    }
    catch {
        # An unavailable provenance timestamp is not evidence of a runtime failure.
    }
}
$RecentLogs = @($Logs | Where-Object { $_.LastWriteTime -ge $EvidenceSince })
$lines = @()
foreach ($Item in $RecentLogs) {
    $lines += @(Get-Content -LiteralPath $Item.FullName -Tail $LogLines -ErrorAction SilentlyContinue)
}

$summary = [System.Collections.Generic.List[string]]::new()
$summary.Add("PSM v1.0.5 - no-skin diagnosis")
$summary.Add("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"))
$summary.Add("This report contains only known failure markers and hashes, not raw logs.")
$summary.Add("")
$summary.Add("Log sessions found: $($Logs.Count)")
$summary.Add("Session logs since current runtime staging: $($RecentLogs.Count)")
if ($RecentLogs.Count -eq 0) {
    $summary.Add("No recent logs for the staged runtime; older failure signatures excluded.")
}
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
if ($Counts["LTK lazy WAD rejection"] -gt 0) {
    $summary.Add("LTK explicitly declined the modded WAD. Check the WAD rejection using the local development log; do not override verification.")
}
elseif ($Counts["LTK hook initialization failed"] -gt 0) {
    $summary.Add("LTK reported a required hook initialization error. Review the local diagnostic log without changing game security.")
}
elseif ($Counts["LTK WAD integrity scan error"] -gt 0) {
    $summary.Add("LTK reported a WAD integrity scan error; treat the overlay as not applied.")
}
elseif ($Counts["Patch 26.21 material format parsing"] -gt 0) {
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
elseif ($Counts["Patcher injected or attached"] -gt 0 -and $Counts["LTK DLL overlay initialized"] -eq 0) {
    $summary.Add("Host attached, but the DLL did not report overlay initialization. Attachment alone is not skin success.")
}
elseif ($Counts["LTK DLL overlay initialized"] -gt 0 -and $Counts["Patcher redirected a WAD"] -eq 0) {
    $summary.Add("DLL overlay initialized, but no WAD redirection was observed. This may be limited DLL logging; verify mod content.")
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
    # The audit is a local JSON file that may contain user paths. Include
    # only build/cutoff UTC timestamps and sanitized test findings.
    try {
        $audit = Get-Content -LiteralPath $candidateAudit -Raw -Encoding UTF8 | ConvertFrom-Json
        $summary.Add("Build-time runtime audit: present")
        if ($null -ne $audit.game_build_pe_timestamp) {
            $summary.Add("League PE game build timestamp: " + $audit.game_build_pe_timestamp)
            $summary.Add("League PE game build UTC: " + $audit.game_build_utc)
        }
        else {
            $summary.Add("League game build timestamp: unavailable in build audit")
        }
        if ($null -ne $audit.dll_cutoff_pe_timestamp) {
            $summary.Add("Bundled DLL cutoff timestamp: " + $audit.dll_cutoff_pe_timestamp)
            $summary.Add("Bundled DLL cutoff UTC: " + $audit.dll_cutoff_utc)
        }
        else {
            $summary.Add("Bundled DLL cutoff: not detected in build audit")
        }
        if (
            $null -ne $audit.game_build_pe_timestamp -and
            $null -ne $audit.dll_cutoff_pe_timestamp
        ) {
            if ([long]$audit.game_build_pe_timestamp -gt [long]$audit.dll_cutoff_pe_timestamp) {
                $summary.Add("Build-time cutoff comparison: UNSUPPORTED (game build newer than DLL cutoff)")
            }
            else {
                $summary.Add("Build-time cutoff comparison: NOT EXPIRED by this check (other incompatibilities possible)")
            }
        }
        if ($null -ne $audit.errors) {
            foreach ($item in $audit.errors) {
                # The supported audit errors are static messages. Never copy
                # arbitrary source paths/command output to this shareable report.
                if ($item -match '^The bundled patcher DLL is older than the installed League build') {
                    $summary.Add("Runtime audit confirmed: bundled patcher DLL older than installed League build")
                }
                elseif ($item -match '^Could not establish League build') {
                    $summary.Add("Runtime audit warning: could not read installed League build")
                }
                elseif ($item -match '^Required runtime binaries missing') {
                    $summary.Add("Runtime audit warning: runtime binaries missing at build")
                }
            }
        }
    }
    catch {
        $summary.Add("Build-time runtime audit: found, but could not parse JSON")
    }
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
