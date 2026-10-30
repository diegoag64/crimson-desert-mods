# Crimson Desert compact inventory

A native ASI mod that fits eight columns and eleven rows into the inventory and Private Storage screens. Tiles measure 64 by 62.5 pixels. Category artwork, empty slots, hover, and focus effects follow the compact layout. A list-mode toggle is not implemented.

Revision 5 was verified in game by the user on Steam build `26317560`. The runtime replaces exact decoded UI resources in memory and leaves signed archives, indexes, and saves untouched.

Steam build `26329202`, EXE version `1.0.0.3446`, has separate compatibility pins following an offline audit of the native methods, allocator, and current assets. The builder selects the supported build by its full EXE hash. Revision 7 activated in game and displayed six shop columns, but card backgrounds and labels overlapped. Inventory regression testing on that build is still pending.

This repository contains source, transform rules, hash pins, fixtures, and build instructions. It contains no game assets, generated payload headers, or executable downloads. Build packages contain game-derived data and must remain local.

- [Build and test](docs/build.md)
- [Install and roll back](docs/install.md)
- [Runtime guards and compatibility](docs/runtime.md)
- [Third-party dependencies](THIRD_PARTY.md)

No license has been selected for the project code. The third-party components retain their own licenses.

An optional experimental NPC buy-store layout uses six columns and three rows of 124 by 112 pixel cards. Build it with `--experimental-shop`. It preserves native purchase and quantity handlers. Revisions 8 and 9 still showed overlapping cards in game. Revision 10 corrects the compiled component boundaries: children precede the named root footer, so the earlier name-to-next-name ranges changed the following component's children. The transform now reads each footer and edits the intended card's complete record, with adjacent components unchanged. Shop resources retain their original byte lengths. Revision 10 needs live validation; fixture success does not establish correct rendering.
