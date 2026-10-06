# Security Policy

## Supported release

The current supported public Personal Skin Manager release is **v1.0.3**. GitHub Releases is the canonical public distribution source. The signed in-app update manifest is a separate channel and may remain on an earlier version until a new manifest is signed.

Security fixes are evaluated against the latest maintained public source/release line. Older tagged releases may receive fixes only when a supported upgrade path requires them.

## What to report

Useful security reports include issues involving:

- PSM update-signature or package-verification logic
- unsafe installer/update behavior
- unintended exposure of secrets or sensitive local data
- dependency/provenance problems
- unsafe file handling or path traversal in PSM-owned code
- vulnerabilities in the local application or its public diagnostics

## Out of scope

Do not use the security channel to request or submit:

- anti-cheat bypass/evasion techniques
- stealth, detection avoidance, or process concealment
- security-control disabling
- driver-based circumvention
- tampering with third-party enforcement controls
- private or unverified runtime binaries
- Riot Games credentials/assets or other unlawfully obtained material

## Reporting

Do not post passwords, tokens, signing keys, private certificates, or sensitive local files in a public issue.

If GitHub Private Vulnerability Reporting is enabled for this repository, use it for sensitive vulnerability details. Otherwise, open a minimal public issue that contains no exploit secrets or credentials and asks the maintainer for a private reporting channel.

For non-sensitive bugs, use a normal GitHub issue with:

- affected PSM version/commit
- Windows version
- clear reproduction steps
- expected vs actual behavior
- relevant sanitized logs
- confirmation that secrets/local private data were removed

## Antivirus and false-positive reports

PSM does not ask users to disable Windows Defender or another antivirus product. If a release is flagged, verify that the file came from the canonical GitHub Release and compare its SHA-256 with the value published in the release notes and website.

For v1.0.3, the official installer is:

- `PersonalSkinManager_Setup.exe`
- `28,162,646 bytes`
- SHA-256 `4E1FB68959577213D773C98A8803850122848A838E0983B1397B5B6A1208C7FB`

PSM packages runtime components and coordinates with League processes as part of its supported skin workflow. Those behaviors can trigger generic heuristic classifications in some security products. That possibility does not make every detection a false positive, so reports should be checked against the exact published artifact and, when appropriate, submitted to the detecting antivirus vendor for review.

## Signing-key handling

The PSM Ed25519 update-signing private key must remain outside the repository. Only the public verification key belongs in source.

If a signing key is ever suspected to be exposed or compromised, stop using it and rotate the update trust root through an explicit, reviewed release process.
