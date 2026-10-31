# Prepare the Nexus release

**Status: local release candidate, not installed or published.** Revision 41 remains the working game installation. Version `0.1.0-rc1` is internal revision 42. Its layout outputs match all 30 revision 41 resource hashes, but the candidate changes runtime resource delivery and logging and needs its own live check.

## Release files

Build into a new ignored directory using the complete revision 41 command in [the build guide](build.md), plus `--release-patches`. This variant supports only Steam build `26345091`, EXE `1.0.0.3460`. All original executable, native-method, archive-index, and asset pins remain enforced.

Export the candidate separately:

```powershell
.venv\Scripts\python.exe -m nativegrid.release --package build\release42-candidate-final --out build\nexus-0.1.0-rc1-final
```

The exporter produces `NativeGrid-0.1.0-rc1-DMM.zip` and a local `release-audit.json`. It validates compatibility and resource hashes, fixture reports, ASI integrity, private-path exclusion, exact ZIP contents, and ZIP round-trip bytes. It refuses revision 41 and never overwrites an export.

The ZIP contains one `NativeGrid` folder:

| File | Purpose |
| --- | --- |
| `NativeGrid.asi` | Portable patch-based plugin |
| `NativeGrid-README.txt` | Installation, removal, compatibility, and credits |
| `NativeGrid-LICENSE.txt` | NativeGrid MIT license |
| `NativeGrid-license-MinHook.txt` | MinHook and HDE notices |
| `NativeGrid-license-CDUMM.txt` | Builder-helper notice |
| `NativeGrid-release.json` | Version, compatibility, payload hashes, and validation limits |

Only this ZIP is a candidate upload. The build directory contains generated game-resource fixtures, headers, loader files, and logs that must stay local. The revision 41 DMM ZIP also stays local because it contains complete game-derived resources and an absolute log path. Do not use the standalone installer for revision 42; it supports the historical package format.

## What changed for distribution

The release compiler emits copy operations and XOR residuals instead of complete original/replacement resources. Reconstruction requires the exact original resource read from the player's game. Input and output SHA-256 checks run before replacing bytes or requesting a native buffer resize. Invalid input, malformed operations, or a failed output hash leave the original resource unchanged. The existing resize-failure behavior is preserved.

`NativeGrid.log` is written beside the loaded ASI. An unwritable log does not prevent initialization. The ASI no longer depends on the author's build-folder path. Runtime hooks still check the full EXE fingerprint, method prefixes, and bounded native owner relationships.

Patch-based delivery removes the complete resource copies found in the old package. It is not a determination that every relevant game agreement permits distribution. Game content, dependency rights, and NativeGrid's MIT grant remain separate.

## Nexus page fields

| Field | Prepared value |
| --- | --- |
| Title | NativeGrid - Compact Inventory and Menu Grids |
| Summary | Compact grids for inventory, storage, shops, Refinement, Crafting, Extraction, and Manage Comrades. See more items and portraits at once. |
| Version | 0.1.0-rc1 |
| File title | NativeGrid 0.1.0-rc1 - DMM ASI package - Steam 26345091 |
| File description | Experimental compact UI grids for Steam build 26345091 only. Requires one x64 ASI loader. DMM import recommended. Read compatibility and validation notes. |
| Category | User Interface, if available in Crimson Desert's category list |
| Requirements | Crimson Desert Steam build 26345091; one x64 ASI loader; DMM 4.6.0 recommended for management |
| Description | Paste [nexus-description.txt](nexus-description.txt), which uses BBCode |
| Source | https://github.com/diegoag64/crimson-desert-mods |

The description includes a candid candidate-status paragraph. After a successful live check, replace that paragraph with the specific build, package hash, and menus checked. Do not call the current candidate stable or universally compatible.

### Permissions and credits

The author selected MIT for NativeGrid's original code and mod changes. Use custom permission text if needed to avoid a Nexus preset imposing extra restrictions:

> NativeGrid's original code and mod changes are licensed under MIT. You may reuse, modify, redistribute, and use them commercially, provided you retain the copyright and license notice. Dependency licenses and game content remain separate. This permission does not license Pearl Abyss assets or third-party components under MIT; follow their applicable terms.

Credit diegoag64, MinHook/HDE, CDUMM's build helpers, and the separate loader/manager projects. The packaged notices must accompany redistribution. Do not claim ownership of the game's artwork, names, or screenshots' underlying game content.

Apply **AI-Generated Content** for the extensively AI-generated code and **AI Media** if using the generated page description. The screenshots are user-provided game captures. Recheck the current [Nexus submission guidelines](https://help.nexusmods.com/article/28-file-submission-guidelines) before publication, including game-content permissions and AI tagging. The author must confirm applicable game terms; no publisher permission has been established here.

### Screenshot order

Upload the existing PNGs from `docs/images/` separately to the page's gallery. Do not include them in the mod ZIP. Use `manage-comrades-after.png` as the initial cover candidate: its portraits make the grid change easy to see.

| Pair | Caption |
| --- | --- |
| `manage-comrades-before.png`, `manage-comrades-after.png` | Manage Comrades: original list / five-column portrait grid |
| `npc-buy-before.png`, `npc-buy-after.png` | Shop Buy: original layout / six-column item grid |
| `refinement-before.png`, `refinement-after.png` | Refinement: original list / three-column gear grid |
| `crafting-before.png`, `crafting-after.png` | Crafting: original list / three-column recipe grid |
| `inventory-storage-before.png`, `inventory-storage-after.png` | Inventory and Private Storage: original / denser eight-column grids |

These screenshots show the working revision 41 layouts. Label them that way until the candidate has been visually checked. No supplied screenshot covers Extraction or Shop Sell; do not imply otherwise.

## Verification and remaining steps

Offline evidence is separate from live UI evidence:

| Check | Result |
| --- | --- |
| Historical runtime fixtures | 10 suites passed |
| Patch runtime fixtures | 12 suites passed, including relocation and blocked logging |
| Native reconstruction against actual game resources | 330 checks passed across all 30 resources |
| Layout output hashes | All match revision 41 |
| Python regression tests | 83 passed |
| Installer fixtures | Passed using synthetic files only |
| Build in a different output folder | Byte-identical ASI; ASLR remains enabled |
| Complete original/replacement resources in ASI | None found by exact-byte scan |
| Candidate game launch and UI | Pending |
| Candidate DMM import and disable/re-enable | Pending; revision 41's four-file import was verified previously |
| Coexistence with DmmRuntime.asi / other mods | Pending |

Before publishing:

1. Review the candidate ZIP and page draft. Keep the working revision 41 package and installed-file hashes.
2. With authorization and the game closed, import the candidate into DMM. Confirm one managed ASI and the deployed hash. Do not add a second loader. Initially leave archive mods unmounted.
3. Launch and check the new log's activation lines. Inspect inventory/storage, Shop Sell and Buy, Refinement, Crafting on first open, Extraction, and Manage Comrades. Scroll enough to reuse cards and check names, counts, portraits, and thumbnails. Layout checks require no purchases, crafting, extraction, refinement, or dispatch.
4. Close the game. Verify DMM disable/re-enable and rollback ownership. Record candidate hash, game build, tested menus, and remaining gaps. Keep the candidate's validation statement accurate.
5. Confirm applicable game-content permissions and review Nexus metadata, MIT permissions, credits, tags, screenshots, and dependency links.
6. Upload only the reviewed ZIP and gallery images when publication is authorized. Wait for Nexus's scan result; no malware scan result is claimed by the local build audit. Nexus recommends ZIP or 7z and rejects nested archives; see its [quarantine guidance](https://help.nexusmods.com/article/117-why-has-my-mod-been-quarantined).

No Nexus page, upload, game launch, or installation is performed by the release build/export commands.
