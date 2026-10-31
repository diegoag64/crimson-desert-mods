# Install and roll back

Build a package using [the build guide](build.md). Keep each package intact. Installation requires one of the audited supported game fingerprints and a stopped game. Further game updates need a new compatibility audit before installation. Revision 7 targets build `26329202` and still needs live UI validation.

## Verify a package

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Verify -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\inventory-5
```

Verification checks the package hashes, supported game pins, and existing owned files. It writes nothing to the game. Conflicting files stop the operation.

Revision 15 through 34 shop packages also require the pinned English localization index, `0020/0.pamt`. This is a read-only compatibility check. Installation still changes only the three files listed below. Revisions 15 and 17 failed live loading tests. Revisions 16 and 18 through 23 loaded and displayed icons-only requirements, but spacing remained unresolved. Revision 24 uses a direct container selector after live inspection proved that revision 23's descendant selector could not match. The user confirmed revision 24's spacing fix in the live shop. Preserve `build/shop-24-live-container-translation` as the working shop checkpoint. Preserve revision 23 and its installation rollback journal, and retain revision 16 as an earlier checkpoint.

## Install a package

Revision 33 is installed. Preserve `build/shop-33-whole-labels` and its installation rollback journal, `build/rollback/rollback-07fb54249ccc4f6881e75c4591ea52ba`, along with earlier packages. The user reports that Extraction's scrollbar is too far from its grid and that Crafting thumbnails sometimes appear only after switching tabs.

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
