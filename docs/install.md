# Install and roll back

Build a package using [the build guide](build.md). Keep each package intact. Installation requires one of the audited supported game fingerprints and a stopped game. Further game updates need a new compatibility audit before installation. Revision 7 targets build `26329202` and still needs live UI validation.

## Verify a package

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\NativeGrid.ps1 -Action Verify -Game "E:\Steam\steamapps\common\Crimson Desert" -Package build\inventory-5
```

Verification checks the package hashes, supported game pins, and existing owned files. It writes nothing to the game. Conflicting files stop the operation.

## Install a package

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
