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

## First: inspect the current Windows inputs

On the working repository checkout of this staging branch (or a linked worktree with this branch), run:

```powershell
python -m unittest tests.test_v105_public_installer_staging_contract
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\preflight_v105_public_candidate.ps1" `
  -LtkDir "C:\path\to\separately-staged-LTK" `
  -CslolDir "C:\path\to\distributor-signed-CSLOL" `
  -ModToolsFile "C:\path\to\working-original-repo\injection\tools\mod-tools.exe"
```

The preflight neither signs nor modifies files. A linked worktree normally does not contain the original untracked runtime files, so pass `-ModToolsFile` pointing to the existing audited source `mod-tools.exe` rather than copying it into the worktree. The preflight prints the public CSLOL certificate subject and SHA-256 fingerprint, but a `Valid` signature does not prove the certificate belongs to the PSM distributor. If it flags the known failing unsigned hashes, **stop** and diagnose the original-vs-unsigned source A/B result using `scripts/test_v105_isolated_ltk_source.ps1`. Do not recreate the same failed RC.

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
  -CslolDir "C:\path\to\distributor-signed-CSLOL"
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
