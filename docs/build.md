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

Ten native suites exercise nine raw-read cases and ten full-read cases, then repeat the harness with a missing interface, a changed executable, and three changed method fingerprints. A final suite repeats the read cases with a shorter replacement to check reuse of the existing allocation. The refinement suite detours a synthetic native style refresh and checks 27 cases, including both tab directions, unrelated controls, invalid pointers, cycles, native class removal, helper ordering, exact arguments, and `LastError`. The Crafting suite tests 35 cases through a real detour, including initial and recycled empty image caches, native completion, unavailable resources, retry, native parent-to-child traversal, helper reentry, unrelated menus, invalid pointers, and all five ABI arguments. The shop count suite covers 69 cases through the shared layout detour, including repeated pooled-label transitions, scope exclusions, helper reentry, and removal before text measurement. The resource harness checks ABI arguments, return values, `LastError`, canaries, exact bytes, partial reads, invalid pointers, read-only buffers, resize failure, and nested reads.

Installer fixtures use synthetic files under `build`. They never touch the real game. All tests must pass before installation. Do not run Python with `-O`, because transform assertions are required.

## Build from supported game files

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\inventory-5
```

The build selects compatibility metadata by the exact EXE hash. `nativegrid/supported_build.json` preserves build `26317560`. The files under `nativegrid/builds/` separately describe builds `26329202` and `26345091`. The builder also requires the exact master-index, UI-index, original asset, and replacement hashes for that build. It derives the package-worker methods from named RTTI in the local EXE, checks their known RVAs, generates local payload headers, runs the native fixtures, and compiles `NativeGrid.asi` with `-Wall -Wextra -Werror`.

The output includes `manifest.json`, three install files, licenses, fixture results, runtime log paths, and generated headers. Keep the whole package for verification and rollback. Runtime logs are written to the package's absolute path, so keep that directory in place after installation. Different output paths can produce different binary hashes.

To include the experimental six-column NPC buy-store grid, add `--experimental-shop` and choose another output directory, such as `build\shop-6`. The default remains inventory only. The shop transforms rename scoped component styles while retaining native script and binding attributes. They do not add purchase logic. Shop behavior still needs an active runtime and live UI validation.

Build `26329202` uses allocator RVA `0x1501e20`. Build `26345091` uses `0x1504f30`. Both verify the direct call at full-read RVA plus `0x80`. Game originals are extracted afresh. Each compatibility record follows a separate offline method and allocator audit. An unknown EXE or changed asset is refused. Successful offline builds do not establish the visible in-game result.

To add the experimental refinement gear grid on build `26329202`, use both `--experimental-shop` and `--experimental-refinement`. For example:

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\refinement-new --experimental-shop --experimental-refinement
```

Revision 30 retains the three refinement assets and the revision 27 native badge filter. Its stylesheet centers the complete gear label in its wrapper and leaves the icon and name runs left-aligned. Revision 29 failed the live alignment check. Asset pins are in `refinement_revisions.30`; earlier pins remain available for rollback. Asset lengths stay unchanged so either read hook can replace them. `refinement_runtime_revisions.27` remains the shared runtime audit for revisions 27 through 30. The compiler verifies its native methods and owner types before emitting the optional hook configuration. The default shop build remains revision 24 and has no badge hook. See [refinement grid troubleshooting](grid-layout-troubleshooting.md#center-the-complete-rich-text-label-not-its-individual-runs) for the live measurements and regression model.

The user confirmed revision 30's Refinement layout in game. To add the same card geometry to Crafting, add `--experimental-crafting` to the command above and use a new output directory. This builds revision 31 with 21 payloads. It preserves all eighteen revision 30 payloads and the existing runtime hook. The three added resources belong to `CookingView3`, the document used by the open Smithy Crafting screen. Other recipe screens using that document also receive the layout. The user confirmed the Smithy Crafting layout in revision 31; other recipe screens and crafting actions still need separate live coverage.

The `crafting_revisions.31` pins cover the original and replacement compiled document, HTML, and stylesheet. The recipe list changes from one to three columns with four rows. Ingredient and material lists keep their dimensions. All added assets retain their original byte lengths. The stylesheet reuses `refinement_grid.css`; a future change to that file must pass both sets of payload pins.

To add the Extraction item grid, also pass `--experimental-extraction`. This builds revision 32 with 24 payloads, preserving all twenty-one revision 31 payloads and the native runtime hook. The three added assets are the compiled `ItemExtractPanel` document, its source HTML, and its stylesheet. `extraction_revisions.32` pins their original and replacement hashes. This option requires the other three experimental flags so the working layouts remain included.

Extraction reuses the Refinement gear-list transform and card CSS. Its item selector changes to three columns and four rows, with a 390-by-435-pixel viewport. The separate extraction-level and result lists remain vertical. The new assets keep their original byte lengths. Revision 32 requires a live UI check after installation.

To include the buy-card emblem fix with the prepared Extraction update, add `--experimental-buy-labels` to all four existing experimental flags. This builds revision 33. The default builds and their historical pins remain unchanged. The label transform runs after the legacy shop transform and pins four replacements under `buy_label_revisions.33`. It changes one byte in each of two compiled component resources and the source template to isolate the shop's frame-emblem class, then appends scoped stylesheet rules. It retains the native inline emblem and centers the complete name label. No native runtime method changes.

To align the Extraction scrollbar, append `--experimental-extraction-scroll` to the revision 33 command. This builds revision 34, changing only the Extraction stylesheet among the 24 payloads. It overrides the imported track offset inside that document and retains all earlier payloads and native hooks. `extraction_revisions.34` records the independently checked replacement hash. Omit the new flag to reproduce revision 33. Crafting's intermittent missing thumbnails remain under investigation; revision 34 does not change their loading behavior.

To include the Crafting image-cache repair, add `--experimental-crafting-icons` to the revision 34 command. Revision 35 retains all 24 revision 34 payloads. It adds a native layout detour with exact method-body hashes and owner types under `crafting_runtime_revisions.35`. The detour lets the native layout pass finish, then uses the game's background-size and background-position helpers if a recipe image still has an empty cached rectangle. The installed layout and item bindings are unchanged. Omit the flag to build revision 34 without this detour.

Revision 35 passed its original fixtures but failed the live first-open check. Current source builds revision 36 with the same `--experimental-crafting-icons` flag, method pins, and asset payloads. The corrected guard allows normal nested child layout and blocks helper reentry. Check the first weapon category after a fresh launch, then a category that reveals previously unused cards. See [Crafting image-cache troubleshooting](grid-layout-troubleshooting.md#crafting-icons-appear-only-after-category-changes) for the measured failure and the runtime repair guard.

On build `26329202`, experimental shop packages also read `0020/0.pamt` and the English `localstringinfo.paloc` resource. The `shop_requirements` metadata pins this index and both resource hashes. The installer verifies the additional index before replacement. The localization transform changes three short requirement labels to their original inline icons and verifies that all other records remain identical. Its compressed envelope changes size, so delivery requires the existing full-read hook. See [requirement-label troubleshooting](grid-layout-troubleshooting.md#requirement-text-overflows-a-shop-card) for the format, scope, and live checks.

## Build the Crafting repair for Steam 26345091

Game EXE version `1.0.0.3460` has SHA-256 `4e38ce1d8fe98eee7be0e26026a1d24ea6a17e80aa88e906b5f3ed553af11f63`. Its separate compatibility record preserves the earlier build's records. Use all seven experimental flags to build revision 36:

```powershell
.venv\Scripts\python.exe -m nativegrid.build --game "E:\Steam\steamapps\common\Crimson Desert" --gcc C:\msys64\ucrt64\bin\gcc.exe --out build\crafting-36-nested-layout --experimental-shop --experimental-refinement --experimental-crafting --experimental-extraction --experimental-buy-labels --experimental-extraction-scroll --experimental-crafting-icons
```

Choose a new output directory if this package already exists. Omitting `--experimental-crafting-icons` builds revision 34 for the same game build. That fallback retains the layouts and scrollbar correction without the Crafting cache hook. An old-game package cannot serve as a runnable fallback after Steam updates the EXE.

The offline audit found 22 unchanged resources among the 24 replacements. `itemicon_component_game.uibinary` has 14 changed bytes at the same file length. None overlaps the mod's edits, and all 14 survive the transform. The English localization table adds two records, with no removed or changed existing records. Its transform preserves the new records and changes only the same three requirement labels.

The native audit independently resolves package-worker RTTI, each UI owner type, and the `!cpp-none` atom initializer. The following RVAs belong only to build `26345091`:

| Method | RVA |
| --- | --- |
| Raw resource read | `0x1588ab0` |
| Full resource read | `0x15889f0` |
| Buffer resize | `0x1504f30` |
| Refinement style refresh | `0x38930d0` |
| Add class | `0x3896780` |
| Sort classes | `0x38971b0` |
| Crafting native layout | `0x3868ce0` |
| Background size | `0x387ebf0` |
| Background position | `0x387ed10` |

The relocated methods retain their calling conventions and audited field accesses. Address-normalized comparisons cover 3,235 instructions from retained previous-build disassembly. These include the complete resource readers, class helpers, background helpers, and the retained portion of the layout method. The earlier layout dump starts inside that method, so this is not a complete old/new layout-body comparison. The new prologue, five-argument forwarding, native helper call sites, cached-rectangle accesses, and return path were inspected separately. The resize routine still owns allocation, length, capacity, and the two terminator bytes.

The new record pins all nine method spans with full-body hashes. The sort helper spans its split unwind entries through the final return. Build checks enforce these hashes in addition to the full EXE hash, prefixes, RTTI owners, and archive pins. Native object constructors and description binding code retain the fields used by the scoped hooks. The hidden-class atom moves to `0x710a7c8`; its initializer still receives `!cpp-none`.

Revision 35 failed the live first-open Crafting check. Revision 36 passes the expanded fixtures. After installation on build `26345091`, the user reported that the initial Crafting icons appear fixed. The runtime log also records eight successful repairs, its logging limit. This is a user-confirmed checkpoint for the reported initial-icon failure, not validation of every category or other game build.

## Audit files before publication

```powershell
.venv\Scripts\python.exe scripts\audit_publication.py
git diff --cached --check
git diff --cached --stat
```

`tracked-files.txt` is the explicit public allowlist. `.gitignore` denies every unlisted file. Add new source files to both files before staging them by exact path. Never stage the entire scratch workspace.

## Build the recycled shop-count correction

On build `26345091`, append `--experimental-shop-counts` to the revision 36 command and choose a new output directory, such as `build/shop-38-count-translation`. This now produces revision 38. The flag requires `--experimental-crafting-icons` so the working Crafting repair remains enabled. Omit the new flag to rebuild revision 36.

Revision 37 adds no asset transform or layout detour. It adds a scoped preparation step to the existing layout hook. `shop_count_runtime_revisions.37` pins the full property-removal helper body, the requirement-class initializer and atom address, and three owner types. The builder audits them before compilation. Older game builds have no revision 37 support record and are rejected for this option. Do not copy these addresses to another build.

Revision 37 passed ten native suites, 50 Python checks, and the installer fixtures, but failed the live scrolling check. It removed the stale line height while leaving a separate cached translation. Preserve that package and its evidence.

Revision 38 adds an explicit zero translation for normal stock labels. The two-class requirement rule retains its existing offset. A separate `shop_count_assets_revisions.38` record pins the changed stylesheet. The other 23 payloads and every native method pin remain unchanged. Builds without the count flag retain the previous stylesheet and pins. The revision 38 package passes ten native suites, 51 Python checks, and the installer fixtures. Its visible scrolling behavior still needs a live check.

## Build the Manage Comrades portrait grid

On build `26345091`, append `--experimental-comrades` to the revision 38 command and choose a new output directory, such as `build/comrades-41-validated-tree`. The option now builds revision 41 and requires `--experimental-shop-counts` to preserve the user-confirmed shop correction. Omitting it retains revision 38.

Revision 39 adds three exact-sized replacements: `mercenarymanagementpanel_game.uibinary`, `mercenarymanagementpanel.html`, and `mercenarymanagementpanel.css`. The compatibility record pins each original and replacement hash under `comrades_revisions.39`. The compiled transform changes only the management list's column and row bytes. The source transform supplies the same dimensions on `MercenaryList`. Ship-station and crew-selection list attributes remain unchanged.

The document-local stylesheet creates five columns and three visible rows. Each card is 124 by 108 pixels, with a 130-by-112-pixel pitch. Portraits retain the native texture binding and 100-pixel image size. Names use a centered row beneath the portrait. Occupation text and large assignment marks are hidden; native disabled shading, selection, and hover behavior remain. Shared Pet templates and stylesheets are not replaced.

Five unused decoration rules are removed to fit the stylesheet's original 5,062-byte buffer. The compiled transform rejects the build if any corresponding ID appears. The final stylesheet has 419 padding bytes. The original three asset sizes and all 24 revision 38 payloads remain unchanged. No new native hook is added.

The package passes ten native suites, 55 Python checks, and the installer fixtures. These checks establish transform scope, native-binding preservation, capacity, and compatibility guards. They do not establish live scrolling or portrait rendering. The comrades grid remains experimental pending installation and a live check.


### Revision 40: isolate management card styles

Revision 39 failed live because shared selector definitions replaced its card width, name wrapper, and occupation visibility rules. Revision 40 is retained as a failed startup experiment; the current option builds revision 41. See [the selector diagnosis](grid-layout-troubleshooting.md#duplicate-selectors-can-discard-the-entire-custom-rule) for the evidence and scope.

Build into a new directory such as `build/comrades-40-isolated-styles`. The package pins six comrades assets under `comrades_revisions.40`, including the shared Pet source, compiled component, and stylesheet. All replacements retain their original byte length. Only the management card receives the two extra container classes; other components and all original shared CSS rules are preserved. Native bindings and runtime method pins remain unchanged.

Ten native suites, 59 Python tests, and installer fixtures pass. All 24 revision 38 payloads remain identical. The package is prepared but not installed or live-verified. Retain revision 39 for exact installation rollback and revision 38 as the user-confirmed checkpoint.


### Revision 40 failed startup; revision 38 restored

Do not install revision 40. The user reported a startup loading stall after its installation. The runtime log reaches replacement of `pet_component_game.uibinary`; the following localization replacement is its last recorded entry. This ordering alone does not identify a blocked thread.

Inspection found that `card_binary` inserted class records after ordinary element IDs, using the component-footer format for child elements. Existing child classes precede those IDs. The round-trip fixture used the same incorrect format, so its passing result did not validate the game's parser. A replacement implementation needs independent format validation before another build is installed.

After the user exited and requested rollback, revision 38 was restored from `build/shop-38-count-translation`. Package, game fingerprints, installed files, and the exact ASI SHA-256 (`7315a9cf1675efc4e3c2aed61d7d3817a8a3016cb57520ecfa9b638b6ff71246`) pass verification. The transaction preserved revision 40 under `build/rollback/rollback-f5d2594457d0403db2b06359263bfc5f`. Preserve its package and startup log. The comrades grid is unresolved; revision 38 restores the original comrades list and the previously confirmed shop/Crafting changes.


### Revision 41: validate child records before inserting classes

Use the same experimental flags with a new output directory, `build/comrades-41-validated-tree`. The builder selects `comrades_revisions.41`. Only the compiled Pet component differs from revision 40; its five other comrades payloads and all 24 working revision 38 payloads remain identical.

`CardReader` decodes the management card before editing it. It bounds counts, lengths, recursion, flags, element kinds, and the exact component boundary. The transform inserts the two `ng` class records at decoded class-vector positions. It then parses the result and compares every node's ID, script, attributes, references, element kind, child order, and classes against the original tree with those two additions. Other components and the total buffer length must remain unchanged.

The original decoder output was checked against an independently captured working UI tree: all 37 element IDs, static classes, and child orders match. The failed revision 40 binary is rejected by the reader. Regression tests reproduce that malformed insertion and reject it even though its length is correct. These checks validate the audited structure; they do not run the game's deserializer or renderer.

Ten native suites, 61 Python tests, installer fixtures, and real-package verification against installed revision 38 pass. Revision 41 is prepared but not installed or live-verified. Preserve revision 38 for rollback. Do not reuse the failed revision 40 component or its earlier fixture as evidence of valid serialization.
