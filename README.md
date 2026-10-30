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

Revision 12 failed to launch in the user's test. Do not install revisions 11 or 12. Rolling back to revision 10 restored launch. The failed runtime log stopped before either sell asset was replaced, but no crash record established the exact cause.

Revision 13 added the sell menu's 8-column, 11-row layout while preserving all twelve inventory and buy-menu payloads from revision 10. The user confirmed the sell-grid result after launch. The buy-grid appearance was confirmed with revision 10. This does not claim a new exhaustive inventory or purchase-flow test.

Revision 14 is the working rollback checkpoint on build `26329202`. The user confirmed its empty-slot alignment in game. It changes the free shop card's artwork and clipping frame while preserving populated-card records, requirement labels, and the sell grid.

An optional NPC buy-store layout uses six columns and three rows of 124 by 112 pixel cards. Build it with `--experimental-shop`. It preserves native purchase and quantity handlers. The shop remains experimental pending broader purchase-flow testing.

Do not install revision 15: the user reported that the game started but remained loading. Its runtime log confirms the English localization replacement and subsequent UI resource loads; it does not establish the cause of the stall. Revision 14 was restored at the user's request, installed-file verification passed, and the user confirmed that loading works again.

Revision 15 combined native inline icons in three short English labels with a nonzero-font card style. Its seven native suites, 18 Python tests, and 10 installer cases passed, but these checks did not establish successful game loading or the visible result. Other languages and the older supported build do not receive this localization replacement.

Revision 16 is the current working checkpoint. The user confirmed successful loading and icons-only requirements in the shop. Its fourteen UI payloads match revision 14 exactly; the only addition is revision 15's English localization replacement. The runtime log confirms that replacement. This narrows the earlier failure to the revision 15 UI changes, without identifying the exact failing property or override. The icons sit too far below the item name.

Do not install revision 17: the user reported another loading stall after clicking Play. Only its stylesheet differed from revision 16. Revision 16 was restored at the user's request and installed-file verification passed; a fresh launch after this second rollback is not yet confirmed.

Both failed revisions introduced comma-separated selectors. None of 185 extracted stylesheets uses that syntax. Revision 18 keeps the 18-pixel upward translation but expresses the two label selectors as separate rules. A build check rejects grouped selectors in custom shop CSS. This is a targeted test of a suspected parser limitation, not a confirmed fix. All fourteen non-stylesheet payloads still match revision 16, which remains the working rollback checkpoint.
