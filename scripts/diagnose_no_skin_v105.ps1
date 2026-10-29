# PSM v1.0.5 - read-only no-skin diagnostics; does not modify game/PSM/runtime.
# Run after a failed test: powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File .\scripts\diagnose_no_skin_v105.ps1
param(
    [int]$LogLines = 6000,
    [ValidateSet("Source", "Installed")]
    [string]$Runtime = "Source",
    [string]$InstalledDir = "C:\Program Files\Personal Skin Manager"
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$RuntimeTools = Join-Path $Root "injection\tools"
if ($Runtime -eq "Installed") {
    $RuntimeTools = Join-Path $InstalledDir "_internal\injection\tools"
    if (-not (Test-Path -LiteralPath $RuntimeTools -PathType Container)) {
        $RuntimeTools = Join-Path $InstalledDir "injection\tools"
    }
}
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
    "LTK host verification refused" = '(?i)host verification failed.*refusing overlay|LTK host verification refused the overlay|LTK_HOST_VERIFICATION_FAILED'
    "LTK hook initialization failed" = '(?i)failed to install .* hook|LTK could not initialize a required hook|hook install failed|SetWindowsHookEx failed'
    "LTK WAD integrity scan error" = '(?i)LTK WAD integrity scan failed'
    "Patcher injected or attached" = '(?i)\bstatus\s+\S+\s+injected\b|\bdll attached\b|host\s+injected'
    "LTK runtime unsupported or expired" = '(?i)end.of.life|runtime does not support this League build|patcher DLL reached|LTK_PATCHER_EOL'
    "Patcher joined too late" = '(?i)joined too late|started before the LTK scanner was ready'
    "Patcher startup failed" = '(?i)Could not arm LTK scanner|Scanner exited before|Scanner failed before|Missing LTK runtime|Could not start scanner'
    "Overlay builder error or timeout" = '(?i)\bmkoverlay\s+(?:failed\b|timeout\b|timed out\b|error:)'
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
# Check for stale shared-log evidence. A late report does not mean the
# application produced an associated game session. Never turn zero markers
# in an older log into proof that the installed patcher succeeded or failed.
$NewestLogAgeMinutes = $null
if ($Logs.Count -gt 0) {
    $NewestLogAgeMinutes = [int][math]::Floor(((Get-Date) - $Logs[0].LastWriteTime).TotalMinutes)
}
# Analyze only the latest log so older game sessions cannot hide current behavior.
$EvidenceLogs = @($RecentLogs | Select-Object -First 1)
$lines = @()
foreach ($Item in $EvidenceLogs) {
    $lines += @(Get-Content -LiteralPath $Item.FullName -Tail $LogLines -ErrorAction SilentlyContinue)
}

# Distinguish a prior failed build from the last selected-skin attempt.
# Keep the full session evidence for host/DLL counters and support signatures.
$lastSkinIndex = -1
for ($index = 0; $index -lt $lines.Count; $index++) {
    if ($lines[$index] -match '(?i)\[INJECT\] Using skin file:\s*') {
        $lastSkinIndex = $index
    }
}
$attemptLines = @($lines)
if ($lastSkinIndex -ge 0) {
    $attemptLines = @($lines[$lastSkinIndex..($lines.Count - 1)])
}
$builderOutcome = "unknown"
foreach ($line in $attemptLines) {
    if ($line -match '(?i)\bmkoverlay completed in\b|mkoverlay \+ WAD rebase done.*overlay ready') {
        $builderOutcome = "succeeded"
    }
    if ($line -match '(?i)\bmkoverlay\s+(?:failed\b|timeout\b|timed out\b|error:)' -or
        $line -match $Markers["WAD header validation failed"]) {
        $builderOutcome = "failed"
    }
}

$summary = [System.Collections.Generic.List[string]]::new()
$summary.Add("PSM v1.0.5 - no-skin diagnosis")
$summary.Add("Generated: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss zzz"))
$summary.Add("This report contains only known failure markers and hashes, not raw logs.")
$summary.Add("Runtime files selected: $Runtime")
if ($Runtime -eq "Installed") {
    $summary.Add("Installed runtime path: provided or default, omitted from report.")
    $summary.Add("Log source: shared Rose directory; NOT positively attributed to installed PSM.")
}
$summary.Add("Log origin: shared application logs (process attribution unverified).")
$summary.Add("")
$summary.Add("Log sessions found: $($Logs.Count)")
$summary.Add("Session logs since current runtime staging: $($RecentLogs.Count)")
$summary.Add("Analyzed most recent staged-runtime log only: $($EvidenceLogs.Count)")
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
if ($Logs.Count -gt 0) {
    $summary.Add("Newest shared-log age in minutes: " + $NewestLogAgeMinutes)
    if ($NewestLogAgeMinutes -gt 10) {
        $summary.Add("WARNING: latest shared log is stale (>10 minutes). It may not cover the installed-app test.")
    }
}
$summary.Add("Latest session evidence (no raw paths):")
$debugRequested = @($lines | Where-Object { $_ -match 'DLL log level:\s*DEBUG \(local source QA\)' }).Count -gt 0
$infoRequested = @($lines | Where-Object { $_ -match 'DLL log level:\s*INFO' }).Count -gt 0
$summary.Add(" - LTK DEBUG requested in latest session: $debugRequested")
$summary.Add(" - LTK INFO requested in latest session: $infoRequested")
$summary.Add(" - Last selected-skin builder outcome: $builderOutcome")
$sessionSummary = @($lines | Where-Object { $_ -match 'Rose-compatible session completed' } | Select-Object -Last 1)
if ($sessionSummary.Count -gt 0) {
    $match = [regex]::Match($sessionSummary[0], 'last_state=([^,]+), injected=([^,]+), dll_lines=(\d+), verified_wads=([^,]+), redirected_wads=(\d+)')
    if ($match.Success) {
        $summary.Add(" - Last host state: " + $match.Groups[1].Value)
        $summary.Add(" - Host DLL attached: " + $match.Groups[2].Value)
        $summary.Add(" - DLL event lines: " + $match.Groups[3].Value)
        $summary.Add(" - Verified WAD verdict observed: " + $match.Groups[4].Value)
        $summary.Add(" - Redirected WAD events observed: " + $match.Groups[5].Value)
    }
    else {
        $summary.Add(" - Session completion found, but its counters were not in the expected format.")
    }
}
else {
    $summary.Add(" - No completed LTK host session summary in this log.")
}
$rebaseLines = @($lines | Where-Object { $_ -match 'WAD header rebase:\s*restored\s+\d+/\d+' } | Select-Object -Last 1)
if ($rebaseLines.Count -gt 0) {
    $match = [regex]::Match($rebaseLines[0], 'WAD header rebase:\s*restored\s+(\d+)/(\d+)')
    if ($match.Success) {
        $summary.Add(" - Latest WAD headers rebased: " + $match.Groups[1].Value + "/" + $match.Groups[2].Value)
    }
}

# ZIP/Fantome metadata inspection only; no extraction or raw paths reported.
$skinLines = @($lines | Where-Object { $_ -match '\[INJECT\] Using skin file:\s*' } | Select-Object -Last 1)
if ($skinLines.Count -gt 0) {
    $match = [regex]::Match($skinLines[0], '(?i)\[INJECT\] Using skin file:\s*(.+)$')
    if ($match.Success) {
        $skinPath = $match.Groups[1].Value.Trim()
        $summary.Add(" - Selected skin archive observed in PSM debug log: True")
        if (Test-Path -LiteralPath $skinPath -PathType Leaf) {
            try {
                Add-Type -AssemblyName System.IO.Compression -ErrorAction Stop
                Add-Type -AssemblyName System.IO.Compression.FileSystem -ErrorAction Stop
                $archive = [System.IO.Compression.ZipFile]::OpenRead($skinPath)
                try {
                    $entries = @($archive.Entries | Where-Object { -not $_.FullName.EndsWith("/") })
                    $wadEntries = @($entries | Where-Object { $_.FullName -match '(?i)\.wad\.client$' })
                    $assetEntries = @($entries | Where-Object { $_.FullName -match '(?i)^(WAD|DATA|RAW)/' })
                    $summary.Add(" - Selected archive file entries: $($entries.Count)")
                    $summary.Add(" - Selected archive WAD archive entries: $($wadEntries.Count)")
                    $summary.Add(" - Selected archive WAD/DATA/RAW asset entries: $($assetEntries.Count)")
                }
                finally {
                    $archive.Dispose()
                }
            }
            catch {
                $summary.Add(" - Could not inspect selected ZIP/Fantome member metadata.")
            }
        }
        else {
            $summary.Add(" - Selected skin archive no longer exists at the logged location.")
        }
    }
}
else {
    $summary.Add(" - Selected skin archive not recorded (check source DEBUG logging).")
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
if ($Counts["LTK host verification refused"] -gt 0) {
    $summary.Add("LTK host integrity/provenance verification refused the overlay. Check vendor-compatible host and DLL files; never bypass verification.")
}
elseif ($Counts["LTK lazy WAD rejection"] -gt 0) {
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
elseif ($builderOutcome -eq "failed") {
    $summary.Add("Latest selected-skin overlay build failed. Review the current PSM debug log without sharing secrets or raw paths.")
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
$summary.Add("Selected runtime hashes (identity only; not compatibility proof):")
foreach ($Name in @("mod-tools.exe", "ltk_patcher_host.exe", "ltk_patcher_dll.dll")) {
    $p = Join-Path $RuntimeTools $Name
    if (Test-Path -LiteralPath $p -PathType Leaf) {
        $hash = (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash
        $size = (Get-Item -LiteralPath $p).Length
        $summary.Add(" - " + $Name + ": " + $size + " bytes | SHA-256 " + $hash)
    }
    else {
        $summary.Add(" - " + $Name + ": missing in selected runtime directory")
    }
}
# The older source audit may cover an entirely different host/DLL pair.
# Do not represent it as the installed runtime's compatibility verdict.
$candidateAudit = Join-Path $Root "installer\candidates\v1.0.5\reports\runtime-audit.json"
if ($Runtime -eq "Installed") {
    $summary.Add("Historical source build-time audit: excluded from installed-runtime compatibility verdict.")
}
if ($Runtime -eq "Source" -and (Test-Path -LiteralPath $candidateAudit -PathType Leaf)) {
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
