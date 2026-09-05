# Security Policy

## Supported release

Security fixes are evaluated against the latest maintained Personal Skin Manager source/release line. Older tagged releases may receive fixes only when a supported upgrade path requires them.

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
- private copies of `cslol-dll.dll`
- Riot Games credentials/assets or other unlawfully obtained material

## Reporting

Do not post passwords, tokens, signing keys, private certificates, or sensitive local files in a public issue.

If GitHub Private Vulnerability Reporting is enabled for the public source repository, use it for sensitive vulnerability details. Otherwise, open a minimal public issue that contains no exploit secrets or credentials and asks the maintainer for a private reporting channel.

For non-sensitive bugs, use a normal GitHub issue with:

- affected PSM version/commit
- Windows version
- clear reproduction steps
- expected vs actual behavior
- relevant sanitized logs
- confirmation that secrets/local private data were removed

## Signing-key handling

The PSM Ed25519 update-signing private key must remain outside the repository. Only the public verification key belongs in source.

If a signing key is ever suspected to be exposed or compromised, stop using it and rotate the update trust root through an explicit, reviewed release process.
