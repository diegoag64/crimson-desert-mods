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

Six native suites exercise nine raw-read cases and ten full-read cases, then repeat the harness with a missing interface, a changed executable, and three changed method fingerprints. The harness checks ABI arguments, return values, `LastError`, canaries, exact bytes, partial reads, invalid pointers, read-only buffers, resize failure, and nested reads.

Installer fixtures use synthetic files under `build`. They never touch the real game. All tests must pass before installation. Do not run Python with `-O`, because transform assertions are required.

## Build from supported game files

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\inventory-5
```

The build requires the exact EXE, master-index, UI-index, and original asset hashes in `nativegrid/supported_build.json`. It derives the package-worker methods from named RTTI in the local EXE, checks their known RVAs, generates local payload headers, runs the native fixtures, and compiles `NativeGrid.asi` with `-Wall -Wextra -Werror`. Each replacement must match the hash of the verified revision-5 payload.

The output includes `manifest.json`, three install files, licenses, fixture results, runtime log paths, and generated headers. Keep the whole package for verification and rollback. Runtime logs are written to the package's absolute path, so keep that directory in place after installation. Different output paths can produce different binary hashes.

To include the experimental six-column NPC buy-store grid, add `--experimental-shop` and choose another output directory, such as `build\shop-6`. The default remains inventory only. The shop transforms rename scoped component styles while retaining native script and binding attributes. They do not add purchase logic. Shop behavior still needs an active runtime and live UI validation.

The updated local EXE is refused before extraction or compilation. A full clean build from the current installation awaits compatibility evidence. Publication checks instead verified all seven transforms against preserved revision-5 originals and ran the native fixture build from the curated source tree. These checks do not establish compatibility with the updated game.

## Audit files before publication

```powershell
.venv\Scripts\python.exe scripts\audit_publication.py
git diff --cached --check
git diff --cached --stat
```

`tracked-files.txt` is the explicit public allowlist. `.gitignore` denies every unlisted file. Add new source files to both files before staging them by exact path. Never stage the entire scratch workspace.
