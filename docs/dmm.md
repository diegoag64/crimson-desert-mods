# Manage NativeGrid with DMM

NativeGrid can be imported into DMM's **ASI Mods** library. The export retains the revision 41 plugin, embedded UI replacements, and native fixes. DMM manages deployment and enablement. No archive mount is needed for NativeGrid itself.

The [DMM release page](https://www.nexusmods.com/crimsondesert/mods/633) documents folder-based ASI imports and companion files. ZIP import and disable/re-enable deployment are verified in DMM 4.6.0. In-game testing after migration and coexistence with `DmmRuntime.asi` remain pending. DMM support does not establish compatibility with other mods.

## Export the working package

Build revision 41 using the [build guide](build.md), or use the preserved working package. Run this command from the repository root:

```powershell
.venv\Scripts\python.exe -m nativegrid.dmm --game "E:\Steam\steamapps\common\Crimson Desert" --package build\comrades-41-validated-tree --out build\dmm-r41-export
```

Choose a new output directory each time. The command runs the existing read-only installer verification, including game, asset, native method, and ownership checks. Conflicting installed files stop export. It supports revision 41 only and does not change DMM settings or game files.

The output contains `NativeGrid-r41-DMM.zip` and a separate `export-receipt.json`. Import only the ZIP. The receipt records source and archive hashes, the exact ZIP entries, and the untested DMM states. The ZIP contains one `NativeGrid` folder with the unchanged ASI, a readme, and dependency notices.

Keep the original build directory. Revision 41 embeds its absolute `runtime.log` path; repackaging does not move that log. Keep the generated ZIP local because its ASI embeds game-derived resources. Do not publish it with the source repository.

## Transfer the existing installation to DMM

The repository workflow requires authorization before changing the game installation. These steps describe the migration; exporting the ZIP does not perform them.

1. Close Crimson Desert. Keep DMM archive mods unmounted for the first check.
2. Preserve the working package and its rollback journal. Record the installed `bin64/NativeGrid.asi` hash and confirm it matches the package receipt.
3. Open **Mods**, select **Import**, and choose `NativeGrid-r41-DMM.zip`. Then open **ASI Mods**. The **Install ASI Mod** picker is for individual plugin files.
4. Check the **ASI Mods** library for one managed NativeGrid entry. Enable that entry. Confirm that the deployed `bin64/NativeGrid.asi` hash still matches the receipt. If DMM reports an ownership conflict or a duplicate entry, stop before deleting either copy.
5. Keep the existing single ASI loader and its configuration. The ZIP deliberately includes neither `winmm.dll` nor `winmm.ini`. Do not add a second loader.
6. Launch the game and inspect the existing runtime log. Check the working layouts before adding other mods.

Import or enablement can deploy files immediately. Do not perform either while the game runs. The standalone plugin is already named `NativeGrid.asi`; migration must leave one deployed copy, with the DMM library holding the managed source.

After migration, use DMM to disable or update NativeGrid. The standalone installer owns the shared loader and refuses other ASIs. Do not use its uninstall action to remove just NativeGrid from a DMM-managed setup.

## Verified migration checkpoint

The local revision 41 migration used DMM 4.6.0 with the game closed and archive mods unmounted. DMM imported all four ZIP entries into `mods/NativeGrid`. Disabling NativeGrid removed the deployed ASI while retaining the library copy. Re-enabling restored the exact plugin and persisted `activeAsiMods: ["NativeGrid"]`.

The deployed ASI SHA-256 remains `02621114dcb317cdb4724dd4a8b71095fa16d2a7b96eeb08b8622d744848b3e9`. Both `winmm.dll` and `winmm.ini` match the prior installation. There is one deployed NativeGrid ASI, one loader, and no `DmmRuntime.asi`. DMM shows **1 active of 1 plugin** and **NOT MOUNTED**.

The pre-migration files and before/after DMM configuration are preserved locally under `build/rollback/dmm-migration-18031ee46455421197bf41b8c78294e7`. The original `build/comrades-41-validated-tree` package remains intact. This checkpoint verifies DMM management and deployed bytes; it does not record a new game launch.

## Check other DMM mods separately

First confirm NativeGrid under DMM with archive mods unmounted. Then test `DmmRuntime.asi` and a small load order separately, with the game closed during changes. Preserve the working installation before that step.

Both runtimes serve game resources. Mods that replace the same UI or English localization resources can conflict, and hook coexistence has not been established. NativeGrid's original-byte guards remain enabled. A DMM mount succeeding does not prove that NativeGrid's replacements or native fixes ran.

Check startup, the runtime activation lines, the comrades grid, Crafting icons on first open, and shop counts after scrolling. Record DMM import results separately from game behavior. Do not buy, craft, refine, extract, or dispatch comrades merely to test the layout.

## Return to the standalone installation

Close the game and disable the managed NativeGrid entry in DMM so it cannot redeploy automatically. Unmount any DMM archive mods. Preserve the DMM library copy and export receipt.

Compare the remaining plugin and loader files with the preserved standalone package before restoring anything. With no other ASIs installed and the original loader intact, use the [standalone installer](install.md) to restore the working package. If `DmmRuntime.asi` or other plugins remain, stop and resolve their ownership first. Do not remove a shared loader or an unfamiliar file to bypass the installer guard.
