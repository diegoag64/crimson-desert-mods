# Crimson Desert compact inventory

A native ASI mod that fits eight columns and eleven rows into the inventory and Private Storage screens. Tiles measure 64 by 62.5 pixels. Category artwork, empty slots, hover, and focus effects follow the compact layout. A list-mode toggle is not implemented.

Revision 5 was verified in game by the user on Steam build `26317560`. The runtime replaces exact decoded UI resources in memory and leaves signed archives, indexes, and saves untouched.

Steam build `26329202`, EXE version `1.0.0.3446`, has separate compatibility pins following an offline audit of the native methods, allocator, and current assets. The builder selects the supported build by its full EXE hash. Revision 7 activated in game and displayed six shop columns, but card backgrounds and labels overlapped. Inventory regression testing on that build is still pending.

This repository contains source, transform rules, hash pins, fixtures, and build instructions. It contains no game assets, generated payload headers, or executable downloads. Build packages contain game-derived data and must remain local.

- [Build and test](docs/build.md)
- [Fix compact grids that leave unused space](docs/grid-layout-troubleshooting.md)
- [Install and roll back](docs/install.md)
- [Runtime guards and compatibility](docs/runtime.md)
- [Third-party dependencies](THIRD_PARTY.md)

No license has been selected for the project code. The third-party components retain their own licenses.

Revision 12 failed to launch in the user's test. Do not install revisions 11 or 12. Revision 10 has been restored on the test installation. The runtime log stopped before either sell asset was replaced, but no crash record established the exact cause.

Revision 13 retains the sell menu's 8-column, 11-row layout on build `26329202` and restores all twelve inventory and buy-menu payloads to revision 10. It is a staged isolation test, not a confirmed launch fix. It has not been installed.

An optional NPC buy-store layout uses six columns and three rows of 124 by 112 pixel cards. Build it with `--experimental-shop`. It preserves native purchase and quantity handlers. The user verified revision 10's populated card layout on build `26329202`; empty-slot alignment and overflowing requirement text remain unresolved. The revision 11 styling, including its unverified zero-font-size technique, has been removed pending investigation.
