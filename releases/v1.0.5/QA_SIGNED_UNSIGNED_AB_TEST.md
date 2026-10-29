# v1.0.5 — source-only LTK signed-vs-unsigned A/B test

**Status: Awaiting a real Windows gameplay result. No release or installer approval.**

## Reason

The source tester, which uses the original signed official LTK v1.28.1 binaries, has rendered a non-default skin. The installed release candidate, built from signature-removed copies of the same upstream files, fails at Windows hook installation (`SetWindowsHookEx failed: 0x00000000`). The overlay builder completed and rebased a WAD in the installed test, so rebuilding the same unsigned pair cannot fix this issue.

Changing Authenticode signatures changes the file hashes, but the evidence does not yet establish that the signature removal itself is the cause; installed launch context may also differ.

## Stage 1 — isolated source test, no packaging

1. Close PSM and League gameplay. **Keep** the signed v1.28.1 host and DLL in `injection/tools` exactly as they were when the source tester worked. Do not run `-Action Restore`.
2. Ensure the original reviewed pair exists in `installer/candidates/v1.0.5/audit-only-ltk-v1.28.1`, and the previously built unsigned pair exists in `installer/candidates/v1.0.5/release-unsigned-ltk`.
3. Update this branch, run the unit tests, then run the isolated comparison:

```powershell
Set-Location -LiteralPath "C:\Users\Van Arquilos\Desktop\PersonalSkinManager-Updates"
git pull --ff-only origin fix/v1.0.5-pre-release-hardening
python -m unittest tests.test_ltk_qa_runtime_selector tests.test_ltk_host_protocol
powershell.exe -NoProfile -ExecutionPolicy RemoteSigned -File ".\scripts\test_v105_isolated_ltk_source.ps1" -Variant Unsigned
```

4. In the source app launched by the script, select a non-default skin in Practice Tool. Exit PSM after viewing the actual rendered skin. Record **works**, **default skin**, or **hook failure**, and the most recent sanitized game log markers. Do not consider a successful overlay build to be a skin-rendering pass.

The script validates the original source files and isolated test pair by SHA-256 before starting; it sets the `PSM_LTK_QA_RUNTIME_DIR` process environment variable only for the launched source session, then restores the prior environment value. It never copies, removes, signs or overwrites either pair. It launches the host from the selected runtime directory so the host loads the adjacent DLL. QA override accepts *only* the reviewed original and known unsigned v1.28.1 SHA-256 pairs.

## Decision matrix

| Signed source | Unsigned source | Previous unsigned installed | What we know |
|---|---|---|---|
| Works | Fails hook | Fails hook | Altered unsigned runtime is a leading cause; cannot infer a safe or authorized packaging workaround |
| Works | Works | Fails hook | Installed-only launch context is the next investigation target |
| Works | Works | Works on new game test | Recheck logs and gameplay, then perform clean install, Swiftplay and consecutive-match QA |
| Fails | Any | Any | Baseline regressed; stop changes and diagnose source run |

## Stage 2 — only after an authorized fix passes gameplay

The current `build_v105_distribution_candidate.ps1` and `publish_v105_prerelease.ps1` **block the known failing unsigned host/DLL hashes**. This is intentional: there is no value in rebuilding the candidate with identical incompatible files.

To distribute v1.0.5, use a genuinely compatible and license-compliant runtime (e.g. signed under the publisher's own certificate when supported, express written upstream permission, or an independently installed official LTK runtime integrated without redistributing its signed binaries). **Do not** distribute upstream-signed host/DLL files inside the PSM installer without upstream permission, or bypass game/OS integrity checks.

After that fix, run all relevant tests, create a **new** installer candidate, and test **that installed candidate** in Practice Tool, Swiftplay and a second match before publishing a GitHub pre-release.

Working local source tester and previous GitHub releases remain untouched.
