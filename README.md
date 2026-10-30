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

Both failed revisions introduced comma-separated selectors. None of 185 extracted stylesheets uses that syntax. Revision 18 expressed the two label selectors as separate rules. The user reached the shop successfully, but its icons remained at the bottom of the card. The runtime log confirms the stylesheet replacement. A build check rejects grouped selectors in custom shop CSS; the exact internal cause of the earlier stalls remains unproven.

Revision 19 loaded, but the user's screenshot shows the same gap beneath the unavailable item's name. Its direct compound selector and relative `top` offset did not establish a visible improvement. Revisions 16, 18, and 19 are retained as earlier checkpoints.

Revision 20 gives both requirement labels an explicit 118-by-24-pixel box at the start of the card's price row. It applies a dedicated style in the compiled components and adds matching overrides to the source-created currency widget. The price widget has a fixed 118-pixel width so absolutely positioned labels have a defined containing box. Native visibility and purchase handlers remain unchanged; all original localization and inventory/sell payloads are preserved. Offline checks pass, but the spacing still needs live verification.

Revision 20 loaded successfully, but its requirement spacing did not improve. Revision 21 targeted `cpp-condition-fail` on a stock-label path and also had no visible effect. Further inspection found that this shop card's `CommonInfoDescription` handler instead marks the requirement container with `font-text-sub-red-negative`. Revision 22 targets that state and preserves the fourteen other payloads. The user reached the shop, but the icons still crossed the card border. Revision 22 is retained as a rollback checkpoint. The troubleshooting guide documents both native paths and the correction.

Revision 23 tests translation of the generated requirement symbols inside the compact shop count wrapper. It removes the ineffective parent offset and preserves all fourteen other payloads. The live test showed no movement.

Read-only inspection found that the game flattened revision 23's descendant selector into an impossible compound. The icons had no resolved translation property. Revision 24 targets the confirmed requirement container directly, and the builder now rejects descendant selectors. The troubleshooting guide records the live tree, normalized selector, and diagnostic property checks.

Revision 24 is installed. On October 30, 2026, the user confirmed that the requirement-icon spacing is fixed in the live shop. Keep `build/shop-24-live-container-translation` as the working shop checkpoint. Seven native suites, 20 Python tests, 10 installer cases, and publication checks passed before installation; installed-file verification also passed. The visual result is user-confirmed, not a post-install memory measurement. Broader shop behavior remains experimental beyond the tested screens.

Revision 25 is installed, and the user confirmed its three-column, four-row refinement grid. Live inspection then found that imported rules kept the images at 88 pixels and the title wrappers at 270 pixels. The Equipped Gear tab also repeats an Equipped badge on every card.

Revision 26 loaded, but its live test exposed two failures: the upgrade indicators disappeared, and Equipped badges remained visible. Read-only inspection confirmed the resized image and title wrapper. The indicator remained a child of the image but sat outside its bounds; the badge's native update changed CSS classes directly, bypassing revision 26's state-setter hook.

Revision 27 gives the indicator space inside the image container while keeping the artwork centered at 52 pixels. It replaces the ineffective state hook with a guarded style-refresh filter scoped to the Equipped Gear tab. Seventeen of eighteen payloads match revision 26, including inventory and shop. Eight native suites, 27 Python tests, 20 installer cases, and package verification pass. Revision 27 was installed. The subsequent user screenshots show restored upgrade indicators and hidden Equipped badges in Equipped Gear; runtime logs also confirm the scoped badge corrections. Other-tab badge behavior is not yet separately confirmed.

Revision 28 refines the card labels: it hides the overflowing material warning on the card, keeps the contribution emblem in the name while removing the duplicate frame overlay, and centers short names with a minimum-width title line. Native disabled shading, material counts, and long-name scrolling remain available. Only the refinement stylesheet changes among the eighteen payloads; runtime source and guards match revision 27. Eight native suites, 27 Python tests, 22 installer cases, and package verification pass. Revision 28 awaits installation and live confirmation. Keep revision 27 for rollback.
