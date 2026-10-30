# PSM v1.0.5 — Public installer path, local Windows testing only

**Status: staging implementation available for Windows QA, but no tested public installer exists yet.** This work does not alter the working private QA installer, original source host/DLL, public v1.0.4 release, or stable signed updater.

## What changed in this staging branch

1. The PyInstaller spec explicitly bundles all four co-dependent runtime files: `mod-tools.exe`, `cslol-dll.dll`, `ltk_patcher_host.exe`, and `ltk_patcher_dll.dll`. The earlier spec enumerated only three.
2. `PSM_RELEASE_LTK_DIR` selects isolated LTK host/DLL files. `PSM_RELEASE_CSLOL_DIR` independently selects an isolated CSLOL companion, avoiding silent bundling of a private original.
3. `scripts/preflight_v105_public_candidate.ps1` prints a **read-only** staged-file and signature audit, known-bad-runtime check, and manual license gate.
4. `scripts/build_v105_public_path_local_test.ps1` builds only in a **fresh linked Git worktree** and insists on audited inputs. It does **not** create a public release or attest to licensing, content enforcement, or gameplay success.
5. All the added Python contract checks are source-level, not substitute Windows/gameplay tests.

## Public distribution constraints

- The official LTK patcher host/DLL must have League Toolkit's signatures removed from copies used in a third-party installer, unless written permission says otherwise. A PSM-owned signature is optional under that patcher license, and may merit compatibility testing; it is not guaranteed to solve the earlier hook failure.
- The **CSLOL DLL Addendum v1.1** is separate. It requires a publicly trusted CA-issued distributor signing certificate, trusted timestamp, published publisher certificate identity/fingerprint and DLL SHA-256, and functional launcher-level blocking of prohibited content. An unsigned or upstream-signed CSLOL copy **cannot** be approved for public redistribution by this build workflow.
- PSM's existing unowned-skin carrier flow requires a separate content policy review. Keeping source behavior unchanged for test purposes is not a licensing approval.
- `Get-AuthenticodeSignature` reporting `Valid` alone does not prove the issuing CA meets all upstream requirements; trusted publisher identity/chain must be reviewed before publication.
- Preserve the original working signed private QA installer and original LTK binaries; do not upload or overwrite them.

## October 30 preflight evidence and corrected certificate gate

The maintainer's installed-preparation preflight passed 8/8 packaging contract tests and found all four components. Observed values:

| Component | SHA-256 | Signature |
| --- | --- | --- |
| `mod-tools.exe` | `25FA57EB81ED308DCF8E3E2ABA1E3981E1697C99752F879E84746D1D90B4CB44` | Valid |
| `cslol-dll.dll` | `4A009619C6DEA691780B2F20CF17E08DE478A78B3F11CD72759DD71C00AD1C90` | Valid; third-party certificate |
| `ltk_patcher_host.exe` | `5E52DC5A30220E735599BE57308CE7BF52E21416CF2C2D9D449A8637F683C4E9` | NotSigned; previously failed hook |
| `ltk_patcher_dll.dll` | `B164A14A2D6C1F1EA6D546782C556050F6F9045DFAB686E4967E7D7CD2E87E29` | NotSigned; previously failed hook |

The CSLOL certificate was observed with subject `CN=Daniel Langov, O=Daniel Langov, L=Burgas, S=Burgas, C=BG`, public certificate SHA-256 `1F51EA1346FF54970541227A4A88E9B4B11FB9A0ADB6B17040DC5DB84E905CE9`, and a timestamp. **This is not a PSM publisher-issued signing identity.** The initial builder only detected signers mentioning "League Toolkit" and could have mistaken this `Valid` third-party signature for PSM-owned signing authority.

The corrected local-only builder rejects this exact CSLOL DLL/certificate pair and requires `-ExpectedDistributorCertSha256`, an independently verified **PSM-owned CA-issued signing certificate SHA-256**. A matching fingerprint is necessary, **not** sufficient: verify its public CA trust chain, responsible distributor identity, timestamp, notices, and prohibited-content enforcement separately. The two original upstream-signed LTK fingerprints are also now expressly rejected, as well as the known failed unsigned pair.

**Do not** set the expected distributor certificate hash to the Daniel Langov certificate fingerprint to force a pass. A code-signing certificate isn't a payment/subscription feature, but acquiring a publicly trusted publisher signing certificate generally involves identity verification and possible cost. Free, public software is compatible with a third-party code-signing requirement, though the project cannot claim a fully no-cost *build process* without an alternative rights agreement or authorized backend.

### Before a new builder run

Run the existing source-only signed/unsigned A/B helper from the working original checkout. It validates the working source host/DLL hashes before opening a local QA session and does not replace them. This test is needed because the staged unsigned host/DLL exactly match a known failing installed candidate. If unsigned source fails too, no new installer should be built from those bytes. If unsigned source works, compare installed-only process context and sanitized current-session logs. Either way, do not reproduce the failed public-path candidate.

## October 30 unsigned-source QA result and installed-binary parity follow-up

The maintainer subsequently confirmed **visible non-default skin rendering from the isolated unsigned LTK source tester**, which uses the exact SHA-256-identified unsigned v1.28.1 host and DLL above. This **supersedes the hypothesis that the unsigned pair is universally nonfunctional**. It does not erase the earlier installed candidate's failed hook or prove that a newly packaged installer works.

The previous unsigned-installed failure and working unsigned-source result can coexist. Investigate runtime layout, bundled-component identity and launch context. The historical hash guard in the public-path builder remains a conservative **installed-artifact failure gate**, not proof those bytes fail everywhere.

**Read-only next test:** inspect the currently installed PSM without modifying binaries:

```powershell
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$Repo = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File (Join-Path $Repo "scripts\inspect_v105_installed_parity.ps1") -SourceToolsDir (Join-Path $Original "injection\tools") -UnsignedLtkDir (Join-Path $Original "installer\candidates\v1.0.5\release-unsigned-ltk") -InstalledDir "C:\Program Files\Personal Skin Manager" -InstalledIdentity Unknown
```

Set `-InstalledIdentity HistoricalUnsignedFailed` **only if that exact failed installation is still present and independently identified**. If it was replaced by the working private version, leave identity `Unknown` or use `WorkingPrivate`; current fingerprints cannot prove anything about the old failed installation.

The parity report prints hashes, signature status, relative layouts, missing/duplicate components and newest shared-log age only. It does not start League, read raw confidential logs, run patcher binaries or write files. For installed-only failure, examine new-session evidence and Windows launch context without disabling integrity checks.

## First: inspect the current Windows inputs

On the working repository checkout of this staging branch (or a linked worktree with this branch), run:

```powershell
python -m unittest tests.test_v105_public_installer_staging_contract
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\preflight_v105_public_candidate.ps1" `
  -LtkDir "C:\path\to\separately-staged-LTK" `
  -CslolDir "C:\path\to\distributor-signed-CSLOL" `
  -ExpectedDistributorCertSha256 "64_CHARACTER_PSM_PUBLISHER_CERTIFICATE_SHA256" `
  -ModToolsFile "C:\path\to\working-original-repo\injection\tools\mod-tools.exe"
```

The preflight neither signs nor modifies files. A linked worktree normally does not contain the original untracked runtime files, so pass `-ModToolsFile` pointing to the existing audited source `mod-tools.exe` rather than copying it into the worktree. The preflight prints the public CSLOL certificate subject and SHA-256 fingerprint, but a `Valid` signature does not prove the certificate belongs to the PSM distributor. If it flags the historically failed installed hashes, **do not assume the unsigned source is broken**: the maintainer has confirmed visible skin rendering in source QA. Compare installed paths and binaries using `scripts/inspect_v105_installed_parity.ps1`; do not recreate the same installed release candidate without an explained change.

## Only once compliant, compatible inputs are available: make an isolated test installer

The project already contains the working private source checkout. Do not branch-switch it or run a build against it. Use a **fresh linked worktree**:

```powershell
$SourceRepo = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
$BuildRepo = "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
if (Test-Path -LiteralPath $BuildRepo) { throw "Build worktree exists; do not overwrite" }
git -C $SourceRepo fetch origin release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Git fetch failed" }
git -C $SourceRepo show-ref --quiet --verify refs/heads/release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) {
    git -C $SourceRepo branch release/v105-public-installer-staging origin/release/v105-public-installer-staging
    if ($LASTEXITCODE -ne 0) { throw "Cannot create local release staging branch" }
}
git -C $SourceRepo worktree add $BuildRepo release/v105-public-installer-staging
if ($LASTEXITCODE -ne 0) { throw "Cannot create isolated build worktree" }
```

In the **fresh linked worktree**, with PSM/League/gameplay and patcher closed:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PSM-v105-Public-Local-Test-Worktree"
$Original = "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\build_v105_public_path_local_test.ps1" `
  -ModToolsFile (Join-Path $Original "injection\tools\mod-tools.exe") `
  -LtkDir "C:\path\to\separately-staged-LTK" `
  -CslolDir "C:\path\to\distributor-signed-CSLOL" `
  -ExpectedDistributorCertSha256 "64_CHARACTER_PSM_PUBLISHER_CERTIFICATE_SHA256"
```

The builder rejects missing inputs, the known failed LTK pair, unsigned/non-timestamped CSLOL and upstream-signed patcher/CSLOL, plus reused worktree outputs. It tests source packaging, builds PyInstaller/Inno only in the linked worktree, checks all four bundled-file SHA-256 values, and records a local provenance manifest. The output is:

`installer/candidates/v1.0.5/PersonalSkinManager_v1.0.5_PUBLIC-PATH-LOCAL-TEST.exe`

**Local test only. Do not upload.** A successful build proves packaging, not in-game compatibility, publisher CA validation, or content restrictions.

## Installed candidate QA

Test the **exact** installer digest, never a renamed/rebuilt alternative:

- Clean install into a separate test environment; verify all four runtime files, LCU/WebSocket, Pengu activation and absence of fresh runtime errors.
- With authorized cosmetic content, verify visible skin rendering in Practice Tool; overlay-ready or DLL attach alone is not sufficient.
- Verify actual skin rendering in Swiftplay, reconnect, and a consecutive second match.
- Re-run runtime fingerprint checks and compare new-session game logs. Do not treat stale `%LOCALAPPDATA%\Rose` diagnostics as current proof.
- Clean uninstall/reinstall and re-hash the installer. Investigate any antivirus flag rather than disabling protections.

## Publication gate (later, separate action)

Do not run `publish_v105_prerelease.ps1` as a substitute for compliance review; the existing legacy publisher does **not** validate the new CSLOL addendum end-to-end or the new public-path manifest. We must first record successful *installed* QA, verified public CA certificate/CSLOL DLL hash and timestamp, effective prohibited-content blocking, upstream notices, approved release notes, and explicit owner approval. Keep the signed stable updater manifest unchanged.
