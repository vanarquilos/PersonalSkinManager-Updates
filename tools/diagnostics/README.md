# PSM Diagnostics

Small, **read-only** diagnostics used to investigate Personal Skin Manager compatibility issues.

These tools are intentionally designed to inspect local files and write text reports. They do not modify League of Legends, Personal Skin Manager, Fantome packages, the registry, or running processes. They do not bypass or weaken anti-cheat or security controls.

## Requirements

- Windows 10/11
- Python 3.11 or newer
- Personal Skin Manager installed/configured when the selected diagnostic expects PSM data

Run tools from PowerShell with normal user permissions unless a specific diagnostic explicitly says otherwise.

## Revenant Reign Viego 234043 Fantome audit

`PSM_Revenant_234043_Audit.py` validates the local Revenant Reign Viego package used by PSM.

It checks:

- file existence, size, and SHA-256
- ZIP/Fantome structure
- CRC integrity
- duplicate archive members
- Viego/Revenant-relevant member names
- small metadata/text candidates
- the current package versus an optional Desktop backup
- the local Viego Fantome inventory

Run:

```powershell
python .\PSM_Revenant_234043_Audit.py
```

Output:

```text
%USERPROFILE%\Desktop\PSM_Revenant_234043_Audit.txt
```

## Revenant Reign current-League comparator

`PSM_Revenant_26_17_Compare.py` compares seven known Revenant Reign Viego WAD entry hashes against the currently installed League game baseline.

It reads WAD headers only. It does not extract, patch, inject, suspend, or alter the game.

Run:

```powershell
python .\PSM_Revenant_26_17_Compare.py
```

If automatic League detection fails:

```powershell
python .\PSM_Revenant_26_17_Compare.py --game-dir "C:\Riot Games\League of Legends\Game"
```

Output:

```text
%USERPROFILE%\Desktop\PSM_Revenant_26_17_Compare.txt
```

## Privacy

Generated TXT reports can include local filesystem paths and hashes of local packages. Review a report before sharing it publicly.

Do not attach or publish private signing keys, passwords, account tokens, `cslol-dll.dll`, or unrelated local files when reporting an issue.
