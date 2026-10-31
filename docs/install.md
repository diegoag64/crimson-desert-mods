# Install and roll back

Build a package using [the build guide](build.md). Keep each package intact. Installation requires one of the audited supported game fingerprints and a stopped game. Further game updates need a new compatibility audit before installation. Revision 7 targets build `26329202` and still needs live UI validation.

## Verify a package

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Verify -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\inventory-5
```

Verification checks the package hashes, supported game pins, and existing owned files. It writes nothing to the game. Conflicting files stop the operation.

Revision 15 through 37 shop packages also require the pinned English localization index, `0020/0.pamt`. This is a read-only compatibility check. Installation still changes only the three files listed below. Revisions 15 and 17 failed live loading tests. Revisions 16 and 18 through 23 loaded and displayed icons-only requirements, but spacing remained unresolved. Revision 24 uses a direct container selector after live inspection proved that revision 23's descendant selector could not match. The user confirmed revision 24's spacing fix in the live shop. Preserve `build/shop-24-live-container-translation` as the working shop checkpoint. Preserve revision 23 and its installation rollback journal, and retain revision 16 as an earlier checkpoint.

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
