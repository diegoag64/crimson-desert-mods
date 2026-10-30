# Fix compact grids that leave unused space

Use this guide when a screen shows smaller inventory tiles but keeps too few columns or rows. The sell-menu fix targets Steam build `26329202`. The user confirmed its visible result in revision 13 after the failed revision 12 bundle was separated from the buy-menu styling changes.

## Identify the screen's own layout

Tile dimensions and grid dimensions come from different assets. `itemicon.css` supplies the shared tile size. Each screen can have an expanded copy of its grid attributes in a `.uibinary` file. Updating `inventory2.thtml` or `inventory2_component_game.uibinary` does not update every expanded copy.

The sell-menu screenshot showed six columns and eight rows of compact tiles, with unused space at the right and bottom. Its `npcstoresellview2_game.uibinary` still contained one `column=6, row=8` pair. The source HTML imports the inventory template, but the compiled screen also needs its own edit.

| Screen | Compiled layout | Target grid |
| --- | --- | --- |
| Character inventory | `ui/bin__/inventoryequipmentpanel_game.uibinary` | 8 columns, 11 rows |
| Shared inventory template | `ui/bin__/inventory2_game.uibinary` and `inventory2_component_game.uibinary` | 8 columns, 11 rows |
| Private Storage | `ui/bin__/warehouseview2_game.uibinary` | 8 columns, 11 rows for the main inventory grids |
| NPC sell menu | `ui/bin__/npcstoresellview2_game.uibinary` | 8 columns, 11 rows |
| NPC buy menu | `ui/bin__/npcstorebuyview2_game.uibinary` | 6 columns, 3 rows of larger shop cards |

Do not replace every grid pair across an asset collection. Storage and other screens contain additional grids with different purposes.

## Measure before changing columns and rows

Read the screen's container styles and the tile styles. Include margins in each tile's pitch.

For the current sell menu:

- `#NpcStoreSellListWrap` has a width of 518 pixels in `npcstore2.css`.
- `.inventory-grid-list-item-wrap.category` has a height of 690 pixels in `inventory2.css`.
- Compact inventory tiles measure 64 by 62.5 pixels.
- Eight columns require 512 pixels. Eleven rows require 687.5 pixels.
- Twelve rows would require 750 pixels and would exceed the container.

These are game UI coordinates. Screenshot pixels can differ because of resolution and UI scaling.

## Patch the current game's original assets

1. Select compatibility metadata by the exact executable hash. Keep the executable, index, method, and original-asset checks.
2. Extract the screen's current original assets into an ignored local directory. Never commit those assets.
3. Locate the grid's serialized attributes and inspect nearby IDs, component references, and native handlers. The sell grid belongs to `InventoryItemList` and uses `UIGamePlayControlCommon_ItemList`.
4. Require the expected number of matches. The current sell screen has exactly one original 6-by-8 pair.
5. Replace complete length-prefixed strings using `nativegrid.inventory.sized`. Changing `8` to `11` also changes the serialized string length. Never overwrite a single byte with two digits.
6. Verify that reversing the replacement restores the entire original byte sequence. Preserve unrelated grids and native handlers.
7. Update the source form as well. For sell, add `column="8" row="11"` to the unique override whose selector is `#InventoryItemList` in `npcstoresellview2.html`.
8. Add the audited original and replacement hashes. Revision 12 uses `sell_assets` in `nativegrid/builds/26329202.json`. The builder includes those assets in both inventory-only and combined shop packages. The older supported build has no audited sell assets and retains its previous behavior.

The implementation is `transform_sell` in `nativegrid/inventory.py`. Its tests reject missing or duplicate matches and verify that other grids and handlers remain unchanged.

## Check delivery and component boundaries

A log entry proves that a resource buffer was replaced. It does not prove that the correct widget was edited or that the result renders correctly.

The runtime has a fixed-buffer read hook and a full-read hook. Equal-length replacements work through the fixed-buffer path. Resized resources require the full-read descriptor and the game's audited allocator. The sell binary grows by one byte, and its source HTML grows by 20 bytes. Check for `REPLACED resized` entries for those paths after opening the sell menu. Never pad or truncate a binary without understanding its format.

For component style changes, use `component_end` in `nativegrid/shop.py`. In the supported compiled component format, children come before the named root footer. The footer contains the name, classes, script, flags, and attributes. The next component starts after that footer.

The earlier shop code sliced from a component name to the next name. That changed one root and the next component's children. The visible card retained its old icons and labels. Revision 10 fixed this by starting after the previous component's footer and ending after the target component's footer. The regression fixture in `tests/test_shop.py` reproduces this order and fails against the earlier implementation.

## Requirement text overflows a shop card

Revision 15 is a failed live test, not an installation recommendation. The user reported a loading stall after launch and requested restoration of revision 14. The log recorded the localization replacement, then continued through compiled UI loads and 100,000 raw reads. No captured evidence identifies whether the localization change, card styling, or another cause produced the stall. Preserve that package and its log for investigation; use revision 14 as the working checkpoint.

The user confirmed loading works after restoring revision 14. Revision 16 isolates the two changes: its fourteen UI payloads have exactly the revision 14 replacement hashes, and its only added payload is the unchanged revision 15 localization resource. The user then confirmed successful loading and visible icons-only requirements. Its log confirms the localization replacement. This implicates revision 15's UI changes, but does not identify the exact failing property or override.

The Trust and Contract icons are inline emoji tokens inside a localized string. They are not separate child widgets. The native currency control puts that string in `CoinMoneyLabel` or `CoinMoneyImpossibleLabel`. Narrowing the card does not remove its words, and hiding the label removes its icons too.

For English on build `26329202`, revision 15 changes exactly these short-label records in `gamedata/stringtable/binary__/eng/localstringinfo.paloc`:

| Decimal key | Short label | Replacement |
| --- | --- | --- |
| `578823104575307952` | Ranch + Trust | Original ranch and Trust emoji tokens |
| `5944274002255020208` | Trust | Original Trust emoji token |
| `6675443097217794224` | Trust + Contract Complete | Original Trust and contract emoji tokens |

The detailed warning is a different record, `15741278594103509168`, and remains unchanged. Generic Trust text, names, item data, and purchase rules also remain unchanged. These are localization-record replacements, so any other control that reuses one of the three exact short-label keys also receives its icons-only value. The change is not a global word substitution. Other languages and unaudited requirement labels are outside its scope.

The implementation is `nativegrid/requirements.py`. The audited resource has a 512-byte envelope: `paloc` and four zero bytes, two little-endian u32 sizes at offsets 9 and 13, and zero padding through offset 511. Its body is an LZ4 block. The decoded table consists of tag, reserved value, length-prefixed decimal key, and length-prefixed UTF-8 value records, followed by a u32 record count. Preserve the tag and reserved value; they are not string lengths. Reject unknown envelope bytes, truncated records, duplicate keys, mismatched counts, missing keys, or unexpected original values.

The transform retains emoji tokens in their original order and case, recompresses the body, and updates both size fields. It independently decodes the result and checks that all 6,737 non-target records remain byte-identical. Do not pad a compressed binary with CSS-style spaces or modify signed archives. Recompression changes the resource length, so confirm a `REPLACED resized` runtime entry for the English PALOC path after a fresh launch. If there is no entry, investigate when and how localization is loaded before changing the label styling again.

Revision 15 also scoped `coin-money-label` to the shop components and added a 13-pixel font with a 24-pixel line box. Revision 16 removes those class aliases and source overrides, restoring revision 14's label styling. Keep native visibility classes and selectors intact in any later layout change. Never use a zero-sized font to suppress the words: that was part of an earlier failed launch package, whose exact crash cause remains unknown.

Revision 16's icons are visible but sit near the bottom edge of the card. Revision 17 addresses only this gap with `.shop-grid-price #CoinMoneyLabel, .shop-grid-price #CoinMoneyImpossibleLabel { translate-y: -18px; }`. The existing scoped price class limits the rule to shop cards. Translation moves the rendered labels without changing font metrics, flex sizing, native visibility, class names, or source overrides. The property is already used with pixel values in original game styles. All fourteen non-stylesheet payloads must match revision 16. Confirm the final spacing in game; the screenshot estimate is not a layout-engine test.

After installation, verify that both requirement icons fit within the locked card, the selected-item panel still explains the restriction, and selecting an unavailable item cannot bypass the original requirement. Also test an ordinary purchasable item and the adjacent empty slot. Offline record checks do not establish runtime delivery or glyph placement.

## Verify and keep a rollback checkpoint

Build into a new ignored directory. Run the Python checks, native fixtures, installer fixtures, and publication audit described in [the build guide](build.md). Add new source or documentation paths to both `.gitignore` and `tracked-files.txt`. Stage explicit paths and commit each fix separately.

The sell fix must preserve the existing inventory and buy-menu payload hashes. Revision 12 bundled unverified buy-menu refinements and failed to launch. Its log ended before loading either sell asset. Revision 13 instead adds only the two sell assets to the twelve exact revision 10 payloads. This isolates the sell fix from the unresolved styling changes. No crash record established the exact cause of the revision 12 failure.

Close the game before replacing the plugin. Follow [the installation guide](install.md) and supply the currently installed package as `-PreviousPackage`. Preserve both packages and the rollback journal. Do not restore old signed game archives after a Steam update.

After launch, check these behaviors in the affected screen:

- The expected columns and rows fill the container without crossing its borders.
- The scrollbar reaches the last items, and category changes use the same layout.
- Hover, focus, selection, category artwork, and empty slots fit the tiles.
- Prices, quantities, and requirement indicators remain readable.
- The original action and quantity-selection UI still opens correctly.
- Character inventory, Private Storage, and the other shop tab retain their working layouts.

Record the game build, package revision, runtime replacement entries, and observed result. Label offline test results separately from live UI confirmation. If a Steam update changes a fingerprint, audit compatibility before building again.
