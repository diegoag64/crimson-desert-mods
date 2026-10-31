# Crimson Desert compact grids

NativeGrid makes Crimson Desert's inventory and NPC menus more compact, so you can see more items or comrades at once. It replaces several list views with grids while retaining the game's selection, scrolling, and action handlers.

## What changes

| Screen | Layout |
| --- | --- |
| Inventory and Private Storage | 8 columns, 11 visible rows |
| Shop Sell | 8 columns, 11 visible rows |
| Shop Buy | 6 columns, 3 visible rows |
| Refinement and Crafting | 3 columns, 4 visible rows |
| Extraction item selection | 3 columns, 4 visible rows |
| Manage Comrades | 5 columns, 3 visible rows with portraits and names |

The compact cards fit their artwork, labels, selection borders, and empty-slot backgrounds to the grid. Shop cards separate the price row from the aligned stock and owned counts. Refinement hides the redundant Equipped badge in the Equipped Gear tab. Gear cards retain their upgrade indicators and avoid duplicate item emblems.

The mod changes presentation. The game still handles purchases, crafting, refinement, extraction, and comrade actions. There is no toggle back to list view.

## Current status and compatibility

**Revision 41 is the current working checkpoint**, confirmed in game on Steam build `26345091`. Revision 38 remains the earlier checkpoint without the comrades grid.

The expanded layouts use experimental build flags. Some menu states and transaction flows still need testing. See the [changelog](CHANGELOG.md) for individual results and failed revisions.

Compatibility is tied to exact executable, index, and asset fingerprints. A game update needs an audit before a new package can be built or installed. Older compatibility records remain in the repository for previous builds.

## Build and install

This is a source repository. Game assets and ready-to-install binaries are not included. Packages are built locally from your supported game installation and must remain local.

1. Follow the [build guide](docs/build.md) to prepare dependencies, run checks, and choose the layouts to include.
2. Close Crimson Desert and keep DMM unmounted before installation.
3. Follow the [installation guide](docs/install.md) to verify and install the package. Keep its previous package and rollback files.

The ASI plugin replaces decoded UI resources in memory. It does not modify signed game archives, indexes, or saves. The installer manages `NativeGrid.asi`, `winmm.dll`, and `winmm.ini` in `bin64` and preserves rollback copies.

To manage revision 41 through DMM's ASI Mods library, use the [DMM export and migration guide](docs/dmm.md). The export preserves the working plugin and omits the shared loader. DMM import and runtime coexistence still need live verification.

## Development and documentation

Canonical source lives in `nativegrid/`; build and installation scripts live in `scripts/`. Changes use small commits, exact compatibility guards, and relevant fixture checks. Live UI confirmation is recorded separately from offline test results.

- [Changelog](CHANGELOG.md): concise revision history.
- [Grid troubleshooting](docs/grid-layout-troubleshooting.md): layout failures, their causes, and fixes.
- [Runtime and compatibility](docs/runtime.md): replacement hooks and native guards.
- [Repository workflow](AGENTS.md): contribution and publication rules.

## License

No license has been selected for the project code. Dependencies retain their own licenses; see [third-party notices](THIRD_PARTY.md).
