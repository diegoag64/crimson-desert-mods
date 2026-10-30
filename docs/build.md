# Build and test the inventory mod

Use Windows x64, Python 3.12, and MinGW-w64 x64 GCC. GCC 14.2.0 from MSYS2 UCRT64 is used for the publication checks. Supply your own supported Steam installation. The builder reads the game files and never installs or launches the game.

## Prepare dependencies

Run these commands from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m nativegrid.dependencies
```

The last command downloads hash-pinned artifacts from their upstream repositories into `.deps`. It fetches only MinHook source, two CDUMM archive helpers, their licenses, and the official Ultimate ASI Loader release. Later builds verify the cached artifacts and run offline. Use `python -m nativegrid.dependencies --offline` to check the cache without network access.

## Run fixtures without the game

Choose a new output directory for each run:

```powershell
.venv\Scripts\python.exe -m nativegrid.build --test-only --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\fixtures-1
powershell -NoProfile -ExecutionPolicy Bypass -File tests\test_installer.ps1
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py"
```

Eight native suites exercise nine raw-read cases and ten full-read cases, then repeat the harness with a missing interface, a changed executable, and three changed method fingerprints. A final suite repeats the read cases with a shorter replacement to check reuse of the existing allocation. The refinement suite detours a synthetic native style refresh and checks 27 cases, including both tab directions, unrelated controls, invalid pointers, cycles, native class removal, helper ordering, exact arguments, and `LastError`. The resource harness checks ABI arguments, return values, `LastError`, canaries, exact bytes, partial reads, invalid pointers, read-only buffers, resize failure, and nested reads.

Installer fixtures use synthetic files under `build`. They never touch the real game. All tests must pass before installation. Do not run Python with `-O`, because transform assertions are required.

## Build from supported game files

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\inventory-5
```

The build selects compatibility metadata by the exact EXE hash. `nativegrid/supported_build.json` preserves build `26317560`; `nativegrid/builds/26329202.json` describes build `26329202`. It also requires the exact master-index, UI-index, original asset, and replacement hashes for that build. It derives the package-worker methods from named RTTI in the local EXE, checks their known RVAs, generates local payload headers, runs the native fixtures, and compiles `NativeGrid.asi` with `-Wall -Wextra -Werror`.

The output includes `manifest.json`, three install files, licenses, fixture results, runtime log paths, and generated headers. Keep the whole package for verification and rollback. Runtime logs are written to the package's absolute path, so keep that directory in place after installation. Different output paths can produce different binary hashes.

To include the experimental six-column NPC buy-store grid, add `--experimental-shop` and choose another output directory, such as `build\shop-6`. The default remains inventory only. The shop transforms rename scoped component styles while retaining native script and binding attributes. They do not add purchase logic. Shop behavior still needs an active runtime and live UI validation.

The current build uses allocator RVA `0x1501e20` and verifies the direct call at full-read RVA plus `0x80`. Current game originals are extracted afresh, including the two component binaries changed by the update. The new pins follow a separate offline method and allocator audit. An unknown EXE or changed asset is refused. Successful offline builds do not establish the visible in-game result.

To add the experimental refinement gear grid on build `26329202`, use both `--experimental-shop` and `--experimental-refinement`. For example:

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\refinement-new --experimental-shop --experimental-refinement
```

Revision 30 retains the three refinement assets and the revision 27 native badge filter. Its stylesheet centers the complete gear label in its wrapper and leaves the icon and name runs left-aligned. Revision 29 failed the live alignment check. Asset pins are in `refinement_revisions.30`; earlier pins remain available for rollback. Asset lengths stay unchanged so either read hook can replace them. `refinement_runtime_revisions.27` remains the shared runtime audit for revisions 27 through 30. The compiler verifies its native methods and owner types before emitting the optional hook configuration. The default shop build remains revision 24 and has no badge hook. See [refinement grid troubleshooting](grid-layout-troubleshooting.md#center-the-complete-rich-text-label-not-its-individual-runs) for the live measurements and regression model.

On build `26329202`, experimental shop packages also read `0020/0.pamt` and the English `localstringinfo.paloc` resource. The `shop_requirements` metadata pins this index and both resource hashes. The installer verifies the additional index before replacement. The localization transform changes three short requirement labels to their original inline icons and verifies that all other records remain identical. Its compressed envelope changes size, so delivery requires the existing full-read hook. See [requirement-label troubleshooting](grid-layout-troubleshooting.md#requirement-text-overflows-a-shop-card) for the format, scope, and live checks.

## Audit files before publication

```powershell
.venv\Scripts\python.exe scripts\audit_publication.py
git diff --cached --check
git diff --cached --stat
```

`tracked-files.txt` is the explicit public allowlist. `.gitignore` denies every unlisted file. Add new source files to both files before staging them by exact path. Never stage the entire scratch workspace.
