# Install and roll back

This guide covers the standalone installer. For DMM ownership and loader handling, use [Manage NativeGrid with DMM](dmm.md).

Build a package using [the build guide](build.md). Keep each package intact. Installation requires one of the audited supported game fingerprints and a stopped game. Further game updates need a new compatibility audit before installation. Revision 7 targets build `26329202` and still needs live UI validation.

## Verify a package

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Verify -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\inventory-5
```

Verification checks the package hashes, supported game pins, and existing owned files. It writes nothing to the game. Conflicting files stop the operation.

Revision 15 through 41 shop packages also require the pinned English localization index, `0020/0.pamt`. This is a read-only compatibility check. Installation still changes only the three files listed below. Revisions 15 and 17 failed live loading tests. Revisions 16 and 18 through 23 loaded and displayed icons-only requirements, but spacing remained unresolved. Revision 24 uses a direct container selector after live inspection proved that revision 23's descendant selector could not match. The user confirmed revision 24's spacing fix in the live shop. Preserve `build/shop-24-live-container-translation` as the working shop checkpoint. Preserve revision 23 and its installation rollback journal, and retain revision 16 as an earlier checkpoint.

## Install a package

Revision 33 is an earlier layout checkpoint. Preserve `build/shop-33-whole-labels` and its installation rollback journal, `build/rollback/rollback-07fb54249ccc4f6881e75c4591ea52ba`, along with earlier packages. The reported issues were Extraction's scrollbar distance and Crafting thumbnails that appeared only after switching tabs.

Revision 34 corrects the Extraction scrollbar offset. It does not address the Crafting thumbnail issue. The package is prepared separately and requires installation authorization and a live check. Use the installed revision 33 package as `-PreviousPackage` when installing it.

Close the game. Keep archive-manager mods unmounted. Run the same command with `-Action Install`.

The installer owns exactly `bin64\NativeGrid.asi`, `bin64\winmm.dll`, and `bin64\winmm.ini`. It refuses other ASIs because the loader is shared. It preserves previous files and a transaction journal under `build\rollback` before changing any installed files. Game archives, indexes, and saves are never written.

The loader comes from Ultimate ASI Loader 10.0.2. Its official x64 `dinput8.dll` is verified and renamed to `winmm.dll`. There is no archive-overload folder in its configuration.

## Upgrade or return to a previous package

Supply both the target package and the currently installed package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Install -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\inventory-target -PreviousPackage build\inventory-current
```

The installer checks the current installed hashes against `-PreviousPackage` and preserves rollback bytes. Reverse the two package paths to return to the previous build. Keep package manifests and binaries together. Historical scratch packages without the public manifest schema remain managed by their original installer.

If the game starts during a transaction, the installer stops further changes and retains its rollback journal. Close the game before recovery. Compare installed hashes with `transaction.json` and the preserved package. Do not delete files whose hashes differ from the recorded owned files.

## Uninstall owned files

Close the game and run the verification command with `-Action Uninstall`. The installer removes only matching owned files and preserves copies in its rollback directory. Uninstall checks ownership hashes even after a game update. A changed installed file or another ASI stops removal.

## Check the result in game

Launch the game yourself. Test normal inventory, Private Storage, category icons, empty slots, hover, and focus. Record the game build, package hash, observed behavior, and any failures. Fixture success and an `ACTIVE` log establish technical checks. Only a live UI test establishes the visible result.

## Install the Crafting image-cache repair

Revision 35 includes revision 34's Extraction scrollbar correction and preserves all of its asset hashes. The additional Crafting hook requires nine passing native suites and the exact method and owner pins in `crafting_runtime_revisions.35`. The installer rejects altered or missing runtime metadata.

Close Crimson Desert before installation. Keep DMM unmounted. The original build `26329202` installation upgraded revision 33 to `build/crafting-35-image-cache`. Its rollback journal is `build/rollback/rollback-91d1c7cbc3dd4c95871c51e5af6949b1`. Revision 34 was prepared but was not installed. Preserve these packages and journals.

After the user launches the game, inspect `build/crafting-35-image-cache/runtime.log` for the Crafting hook activation. A successful cache repair writes `CRAFTING: repaired empty recipe background with native layout helpers.` Logging stops after eight repairs. No repair message is expected when the native pass already produces a valid rectangle. Activation and fixture results alone do not establish visible success.

If initial weapon icons remain blank, capture their cached rectangles before any category switch. If loading regresses, close the game and restore the exact preceding package through the recorded rollback journal. Do not alter game archives or remove the journal.

## Install after Steam updates to 26345091

Use `build/crafting-35-build-26345091`, built from the separate audited compatibility record. The old `build/crafting-35-image-cache` package remains revision 35 but targets a different EXE. Reinstalling its bytes cannot enable it on the new game build.

For the first upgrade from the old-game revision 35 package:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Install -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\crafting-35-build-26345091 -PreviousPackage build\crafting-35-image-cache
```

Installation still requires user authorization and a stopped game. The installer uses the previous package to establish ownership and preserve exact rollback bytes. It validates the current game against the target package's pins. Keep DMM unmounted.

Use the rebuilt package's `runtime.log` for the subsequent live check. `build/layout-34-build-26345091` is a separately built fallback with the same UI resources but no Crafting image-cache hook. To use it after an authorized exit, supply it as `-Package` and the installed new-game revision 35 package as `-PreviousPackage`. Restoring old-game bytes would disable the mod on the updated EXE. The previous packages remain available for their original game build.

## Install the nested-layout correction

Revision 35 for build `26345091` failed its first-open Crafting icon check and was replaced by revision 36. Revision 36 in `build/crafting-36-nested-layout` corrects the recursion guard. It preserves all 24 resource payloads, native method pins, and the existing layouts.

After an authorized exit, install revision 36 with `build/crafting-35-build-26345091` as `-PreviousPackage`. Keep DMM unmounted. Preserve the installation journal and `build/layout-34-build-26345091` as the compatible fallback without the Crafting hook.

Check `build/crafting-36-nested-layout/runtime.log` after the next user launch. Its Crafting activation line must include `nested children enabled`. Repair messages establish that the guarded helpers ran. Only a live first-open screen check establishes visible success.

Revision 36 is installed and its installed ASI hash matches the package. The user reported that the initial Crafting icons appear fixed, and the runtime log records eight successful repairs. Preserve `build/crafting-36-nested-layout` as this working checkpoint. The installation preserved revision 35 under `build/rollback/rollback-adc5220bf6894a138932dbc24f152e75`. The installed ASI SHA-256 is `644a35a119ba0265db4a75934a45085b47efceb1f82c435f35852620b9677b57`.

## Install the recycled shop-count correction

Revision 37 is prepared in `build/shop-37-recycled-counts`. It preserves the revision 36 layouts and Crafting fix. After the user authorizes installation and exits the game, use this package as `-Package` and `build/crafting-36-nested-layout` as `-PreviousPackage`. Keep DMM unmounted.

Preserve revision 36 and the new transaction journal for rollback. After the user's next launch, inspect the revision 37 runtime log for `ACTIVE: recycled shop stock line-height repair`. Check the live shop after repeated scrolling through ordinary and requirement items. Fixture success does not establish the visible result.

## Install the explicit shop-count translation reset

Revision 37 was installed with matching hashes, preserving revision 36 under `build/rollback/rollback-d36486d549c14a8aaacb3d9be796a820`. The user reported continued misalignment. Live inspection confirmed its line-height cleanup ran, but all 18 visible stock labels retained the requirement state's upward translation.

Revision 38 is prepared in `build/shop-38-count-translation`. After the user authorizes installation and exits, use this package as `-Package` and `build/shop-37-recycled-counts` as `-PreviousPackage`. Keep DMM unmounted. Preserve revision 36 as the earlier working Crafting checkpoint and revision 37 as the exact installed rollback source.

The reset changes only the shop stock-label stylesheet. Check ordinary stock quantities after scrolling in both directions through rows that contain requirement items. Confirm that requirement icons retain their spacing and that prices, stock, and owned counts remain on their respective rows. Offline tests and runtime log messages do not establish this visible result.

Revision 38 is installed and its ASI hash matches the package: `7315a9cf1675efc4e3c2aed61d7d3817a8a3016cb57520ecfa9b638b6ff71246`. The user confirmed that the shop numbers now look correct after testing. The active runtime records stock line-height repairs. Preserve `build/shop-38-count-translation` as the working shop checkpoint. Its installation preserved revision 37 under `build/rollback/rollback-1a58f705f50640d999d8335d7e459ba3`. This confirms the reported shop issue, not every shop or game build.

## Install the Manage Comrades grid

Revision 39 is prepared in `build/comrades-39-portrait-grid`. After the user authorizes installation and exits the game, use that package as `-Package` and `build/shop-38-count-translation` as `-PreviousPackage`. Keep DMM unmounted. Preserve revision 38 and the transaction journal as the working rollback checkpoint.

After the user's next launch, inspect the package runtime log for successful replacement of the three `mercenarymanagementpanel` assets. Confirm five portrait-and-name cards per row, centered short names, fitted hover and selection borders, and scrolling through the last partial row. Select different comrades to verify that the details panel still follows selection. Do not dispatch, dismiss, equip, or otherwise change comrades merely to test layout. Follow the user's input-control restrictions. Runtime replacement messages alone do not establish visible success.


## Install the isolated Manage Comrades styles

Revision 39 is installed with matching package hashes. Its installation preserved revision 38 in `build/rollback/rollback-d17f48cdb61942618807c45492b1dcc4`. It failed the user's live layout check; do not describe it as a working grid.

Revision 40 is prepared in `build/comrades-40-isolated-styles`. After the user authorizes installation and exits, use it as `-Package` and `build/comrades-39-portrait-grid` as `-PreviousPackage`. Keep DMM unmounted. Preserve both packages, the new transaction journal, and the working revision 38 checkpoint.

After launch, inspect replacement messages for all six comrades resources, including `pet_component_game.uibinary`, `pet.thtml`, and `pet.css`. Inspect the live card root for `ng-comrade-tile` and the two container classes for `ng`. Confirm 124-by-108-pixel card bounds, five visible columns, centered portraits and names, and hidden occupation text. Check selection and the last partial row without dispatching, dismissing, or changing equipment. Follow the user's input-control restriction; do not take over the mouse.


### Revision 40 failed startup; revision 38 restored

Do not install revision 40. The user reported a startup loading stall after its installation. The runtime log reaches replacement of `pet_component_game.uibinary`; the following localization replacement is its last recorded entry. This ordering alone does not identify a blocked thread.

Inspection found that `card_binary` inserted class records after ordinary element IDs, using the component-footer format for child elements. Existing child classes precede those IDs. The round-trip fixture used the same incorrect format, so its passing result did not validate the game's parser. A replacement implementation needs independent format validation before another build is installed.

After the user exited and requested rollback, revision 38 was restored from `build/shop-38-count-translation`. Package, game fingerprints, installed files, and the exact ASI SHA-256 (`7315a9cf1675efc4e3c2aed61d7d3817a8a3016cb57520ecfa9b638b6ff71246`) pass verification. The transaction preserved revision 40 under `build/rollback/rollback-f5d2594457d0403db2b06359263bfc5f`. Preserve its package and startup log. The comrades grid is unresolved; revision 38 restores the original comrades list and the previously confirmed shop/Crafting changes.


## Install the structurally checked comrades grid

Revision 41 is installed from `build/comrades-41-validated-tree`. It upgraded `build/shop-38-count-translation` and preserved revision 38 under `build/rollback/rollback-166dee5463684db4bc99fdda46174cd2`. The user confirmed that the comrades grid looks good after launch. Keep both packages and the transaction journal. Keep DMM unmounted. Do not install revision 40.

After the user's next launch, check successful startup and replacement of all six comrades assets. In Manage Comrades, inspect the card classes and bounds described above, including the first visible row and final partial row. Keep fixture results separate from this live evidence. Do not control the mouse or change comrade assignments without authorization.


The installed revision 41 ASI SHA-256 is `02621114dcb317cdb4724dd4a8b71095fa16d2a7b96eeb08b8622d744848b3e9`, matching its package. The runtime is active and records successful replacement of all six comrades assets. This is the working checkpoint for the reported comrades layout; scrolling through every row and every assignment state was not separately confirmed.
