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

**Revision 17 failed its live loading test. Do not copy its grouped-selector rule.** The user reported a stall after clicking Play, and revision 16 was restored with installed-file verification. Both revision 15 and 17 introduced comma-separated selectors; a scan of 185 extracted stylesheet files found none in uncommented rule headers. This is evidence for a syntax limitation, not proof of the internal failure mechanism.

Revision 18 retains the same translation and scope but uses two separate rules:

```css
.shop-grid-price #CoinMoneyLabel { translate-y: -18px; }
.shop-grid-price #CoinMoneyImpossibleLabel { translate-y: -18px; }
```

`validate_shop_selectors` rejects grouped selectors in the custom stylesheet before compaction. It ignores commas in declaration values, comments, and quoted strings. This limited guard does not replace live testing or validate every supported game CSS property. Revision 18 loaded successfully in the user's test, but its icons did not move. Its log confirms replacement of the stylesheet and compiled item-icon resource. Do not interpret a replacement entry as proof that a selector matched or a positioning property took effect.

Revision 19 replaces that rule with `.coin-money-label.shop-grid-font-minor { top: -18px; }`. Both compiled requirement labels already have these two classes after the existing shop transform, and the original currency rule sets `position: relative`. The compound selector targets the labels directly, without relying on an ancestor match. The build serializes the existing shop font alias to `font-text-minor-whit_`; it does not add a new class, change font metrics, or modify components. This is scoped to the audited compiled shop labels and still needs live placement verification. All fourteen non-stylesheet payloads remain unchanged.

The revision 19 live test showed the same gap. Static inspection then found a coverage difference: the source `Currency.CenterRowCoinWithoutPriceRate` labels keep the original font class because the shop template had no label overrides. A class present in the expanded compiled component is not proof that every creation path receives it. The log shows resource replacements, not which nested construction path produced an individual control.

Revision 20 maps `coin-money-label` to a same-length shop alias in the two scoped compiled card records. It also adds `override-type="merge"` entries for `#CoinMoneyLabel` and `#CoinMoneyImpossibleLabel` inside the source `StoreInfoIcon` currency widget. Both paths receive the same dedicated style. The regression fixture checks the two source overrides, their scope, and preservation of native bindings.

The new labels use absolute positioning at `(0, 0)` inside the price widget, a width of 118 pixels, a height and line height of 24 pixels, and a nonzero 13-pixel font. The parent price widget receives a fixed 118-pixel width; its own row starts at card y=79. This places the intended label box at y=79–103, below the name's y=61–78 box and within the 112-pixel card. Do not force display or remove `!cpp-none`, since the game controls which label is visible. Use separate rules for the two IDs. These are intended layout coordinates, not a claim about observed glyph bounds; verify both unavailable-item icons and ordinary price alignment in game.

After installation, verify that both requirement icons fit within the locked card, the selected-item panel still explains the restriction, and selecting an unavailable item cannot bypass the original requirement. Also test an ordinary purchasable item and the adjacent empty slot. Offline record checks do not establish runtime delivery or glyph placement.

### Requirement icons stay at the bottom after currency-label edits

Revisions 20 and 21 loaded successfully, but the user's screenshots still showed the requirement icons at the bottom border. Their runtime logs confirm stylesheet replacement. Delivery did not prove that either selector matched the visible control.

The shop card binds `selector-buy-item-count-text` to `#ItemAvailableCountText`. Native code reuses this count element as the container for formatted requirement icons. Currency labels are separate controls. Two native paths use different state classes on the count element; do not infer a shared state from a shared selector.

Revision 21 followed the path that binds member `+0x220` at RVA `0x10f8894` and applies `cpp-condition-fail` at `0x1104f92`. That trace establishes a stock-control path, but it did not establish the path used by this shop card. Its conditional rule had no visible effect in the user's test.

The `StoreInfoIcon` source names `UIGamePlayControlCommonInfoDescription`. The corresponding count-update path in the audited build `26329202` uses a different state:

- RVA `0x10ade95` resolves `selector-buy-item-count-text` (atom storage `0x7116a8c`) into the local element pointer at `[rsp+0x50]`.
- The ordinary branch removes atom `0x7116ac4` at `0x10ae278`, then writes the numeric count to that element at `0x10ae2fc`.
- The unavailable branch loads the same element at `0x10ae3e4` and adds atom `0x7116ac4` at `0x10ae40c`. The initializer at `0x179b73` identifies this atom as `font-text-sub-red-negative`.
- At `0x10ae48d`, the element is passed as the output container to the requirement formatter at `0x70b860`. The following lookup targets a generated `cpp-icon-emoji` child and applies `condition-fail` to it. This child state is distinct from `cpp-condition-fail` on the other path's parent.

These addresses document this EXE only. They are not new runtime hooks or addresses to patch. After an update, inspect the new executable rather than reusing these addresses.

Revision 22 replaces the ineffective revision 21 rule with:

```css
.shop-grid-stock-count.font-text-sub-red-negative { top: -18px; }
```

The builder emits the same-length alias `item-available-count-tex_` in place of `shop-grid-stock-count`. The count wrapper starts at card y=97; the offset moves its requirement container toward y=79, below the title box ending at y=78. Native code removes the extra font class in the ordinary branch, so the rule does not match normal stock counts. Preserve native state and visibility changes. The final glyph position still requires live verification.

Only the stylesheet payload changes from revision 21. The other fourteen payloads, including localization, compiled cards, sell layout, and inventory resources, must remain byte-identical. Currency-label styles from revision 20 remain unchanged to isolate this test.

For future layout failures, identify the card's script, follow its exact selector lookup, and inspect both the ordinary and unavailable branches. Distinguish the original container from generated icon children. A state applied by another handler is not evidence that the current card has it. Test a locked item, an ordinary item, and the adjacent empty card after a fresh launch. Revision 22 loaded, but the user's screenshot still shows the icons crossing the bottom border. Its parent `top` rule had no visible effect. The static path identifies a candidate container and state; it does not prove the runtime classes, selector match, or layout-property precedence of the displayed card.

### Target the generated requirement symbols

Revision 23 removes revision 22's parent offset and tests a translation on the generated images:

```css
#ItemAvailableCountWrap.shop-grid-counts .cpp-icon-emoji { translate-y: -18px; }
```

The requirement formatter at RVA `0x70b930` calls the image-creation path at `0x70f930`. That path appends the image to the supplied text element at `0x70fb83` and adds atom `0x70ddaa0` (`cpp-icon-emoji`) at `0x70fc10`. A second branch adds the same class at `0x70fee1`. These are generated child elements, not texture layers in the compiled card. Existing game styles also address `.cpp-icon-emoji.condition-fail` for the red requirement tint.

The selector limits translation to emoji descendants of the compact shop count wrapper. Stock and owned-count icons in the template are separate background-image elements without this class. The rule preserves generated sizes, red/white requirement states, native visibility, and purchase logic. It avoids relying on the parent font-state class or its relative `top` behavior. Why the earlier parent rule had no visible effect remains unresolved; no live element inspection established its computed style.

Only the stylesheet changes from revision 22. Verify that the other fourteen payloads remain identical. Revision 23 is a targeted layout test, not a confirmed fix: inspect both requirement symbols after launch, along with ordinary counts and the adjacent empty tile. A successful build or replacement log does not establish selector matching or final glyph placement.

### Inspect the live tree before changing another selector

Revision 23 loaded but did not move either requirement icon. Read-only inspection of the open grocer shop on build `26329202` then established the actual tree:

```text
compact StoreInfoIcon
  ItemAvailableCountWrap
    item-available-count-wra_, store-info-count-wra_, cpp-show
    ItemAvailableCountText
      item-available-count-tex_, font-text-sub-whit_, font-text-sub-red-negative
      image: cpp-icon-emoji, condition-fail, cpp-able-layer
      image: cpp-icon-emoji, cpp-able-layer
```

The native selector registry contained revision 23's rule as:

```text
#ItemAvailableCountWrap.cpp-icon-emoji.item-available-count-wra_
```

The parser flattened the intended descendant selector into a compound selector. No element in the live tree has that ID and both classes. The generated images' matched-rule lists did not contain the rule, and their resolved property maps had no `translate-y` entry. This establishes why revision 23 did not move the icons. It does not establish why revision 22's relative `top` offset had no visible effect.

Revision 24 targets the confirmed parent directly, using a translation instead of a layout offset:

```css
.shop-grid-stock-count.font-text-sub-red-negative { translate-y: -18px; }
```

After alias substitution, the selector requires `item-available-count-tex_` and `font-text-sub-red-negative` on one element. Both were present on the live requirement container. The ordinary count-update branch removes the negative-font class, so the scope excludes ordinary numeric counts. Translation should move the container and its generated contents together. Its applied property and final placement still require verification after installation.

`validate_shop_selectors` now accepts only a single compound of ID/class tokens in custom shop CSS. It rejects descendant, child, sibling, grouped, and other unverified selector forms before the build. The regression check includes the exact failing revision 23 shape. This is a narrow supported subset for this mod, not a complete game-CSS parser. The generic CSS compactor preserves whitespace; compaction was not the source of the flattening.

For this audited EXE, the read-only inspection followed these structures:

1. Derive the `UIGamePlayControlCommonInfoDescription` primary vtable from named RTTI; its RVA is `0x59cf598`. Scan readable committed game heap regions for aligned instances. Refresh the region inventory after loading the save. Prioritize the high-address game heap rather than spending the scan budget on low-address graphics buffers; heap addresses change each launch.
2. Follow the control's owner at `+0x08`. Check the owner's compact card classes, then traverse child pointers at `+0x40` with the count at `+0x48`. Bound counts and traversal depth, and reject unreadable pointers.
3. The element's style object is at `+0x20`. Its class-vector pointer is at `+0x08`; the vector has a pointer at `+0x00` and count at `+0x08`. Resolve class atom IDs through the string registry rooted at image RVA `0x70cdc60`, whose table pointer is at `+0x58`. Entries are 16 bytes, with the text pointer first.
4. The style object's matched-rule pointer array is at `+0x10`, with its count at `+0x18`. A rule's selector atom is at `+0xa8`. Inspect the normalized selector, not just the original CSS text.
5. With the element's `+0x97` dirty bit `0x02` clear, the style object's resolved-property block at `+0x20` is the getter's cached source. The block has 16-byte values at the pointer `+0x70`, a byte-index map at `+0x80`, and map length at `+0x88`; index `0xff` means absent. Property ID 75 is `translate-y`. Confirm IDs through the descriptor table at image RVA `0x70ce0e0` rather than assuming them on other builds.

These observations are process- and build-specific. Recheck the executable fingerprint and process liveness before reads; never reuse object addresses across launches. Use only `PROCESS_QUERY_INFORMATION | PROCESS_VM_READ`. Do not write to these structures or invoke game functions as part of inspection. Keep raw snapshots local and untracked.

When diagnosing a recurrence, check all three forms of evidence: the direct compound appears in the requirement container's matched rules, its resolved translation is -18 layout pixels, and the rendered icons fit below the name. Check that an ordinary item retains its unshifted count row. Offline fixtures alone cannot satisfy these checks.

On October 30, 2026, revision 24 was installed and its installed-file verification passed. The user then confirmed that the spacing was fixed in the live shop. This establishes the visible result for that screen; no post-install property-map measurement was taken. Preserve revision 24 as the working checkpoint. The successful change uses a direct compound selector on the actual requirement container and `translate-y`, rather than a descendant selector or a relative `top` offset.

## Refinement gear list

The refinement menu uses `ItemList.EnchantItemList_Vertical` with `UIGamePlayControlCommon_ItemList`. Its gear widget, `InventoryContent`, specifies one column and four rows. The cards use `ItemIcon.ProductionItemIcon`. The native controller already accepts column and row attributes; revision 25 changes only the gear list's column attribute to three.

Read-only inspection on build `26329202` found four live gear cards with `item-icon-wrap` and `two-colunm-item-icon3`. Their ancestors include the grid panel, `enchant-item-container-wrap`, and the refinement body. Their style context differs from those of the inventory, storage, and shop documents. An archive search of the source HTML, templates, and CSS found only `itemenchantpanel.html` importing `itemenchantpanel.css`.

The stylesheet override therefore belongs in `itemenchantpanel.css`, not in the shared item stylesheet. Existing direct compound selectors identify the production card, image, title, and equipped badge. No descendant selectors or template renames are needed. Percentage-based background and hover rules also fit the unchanged ingredient cards within the same document.

The first layout uses a 124-by-106-pixel card with the original two-pixel horizontal margins and bottom margin. Three column pitches occupy 384 layout pixels, the same width as the original single card including margins. Four row pitches retain the original 432-pixel height. The 52-pixel image sits below the equipped badge, and the name retains native horizontal scrolling. Native focus, disabled, selected, and equipped visibility states remain attached.

The transform changes these three files:

- `itemenchantpanel_game.uibinary`: one byte changes the column count, guarded by the following `#InventoryContent` binding.
- `itemenchantpanel.html`: the same column change in the exact gear widget. Material-list attributes remain intact.
- `itemenchantpanel.css`: compact existing rules, append refinement overrides, and pad to the original byte length.

All fifteen revision 24 payloads remain identical. The game executable, indexes, runtime hooks, native scripts, comparison panels, and refinement actions are unchanged. The new original and replacement asset hashes are pinned separately. The builder refuses unsupported refinement builds, and the installer checks the new payload pins.

Revision 25 passed seven native suites, 23 Python tests, ten installer cases, and package verification. It was then installed, and the user confirmed the three-column grid. The user also reported badge clutter and image alignment problems. Further live checks remain:

1. Open Refinement and confirm three columns, fitted artwork, readable names, equipped badges, and refinement marks.
2. Move selection across columns and rows. Confirm that both comparison and material panels follow the selected item.
3. Switch between equipped and available gear. Scroll beyond twelve items if the inventory has enough eligible gear.
4. Check mouse hover and keyboard or controller focus. Check that the material-selection screen still displays its list correctly.
5. Confirm that inventory, buy, and sell screens retain their working layout.

Do not perform a refinement merely to validate layout. The test can inspect navigation and previews without consuming materials. If the layout fails, inspect the live classes and resolved properties before changing another rule. Preserve revision 24 for rollback.

### Imported child styles can defeat the compact card rules

Revision 25 changed the card root to 124 by 106 pixels, but live inspection found an 88-by-88 image and a 270-pixel title wrapper. The intended child rules were not the resolved values. Revision 26's direct ID/class selectors successfully changed those dimensions to 52 by 52 and 116 pixels. Check the child properties, not just the root, when a compact card still looks wrong.

Revision 26 also exposed a containment error: `ItemTierTexture` is a child of `ItemIconImg`. Its left offset of -30 placed the upgrade indicator outside the smaller image box. The live node still existed without a hidden class, but the indicator was absent from the screenshot. Moving a child toward the card's corner does not move its containing box.

Revision 27 uses a 124-by-76 image container at x=0, y=4. The background artwork is explicitly 52 by 52 at x=36, y=20 inside that container: its card position remains x=36, y=24. The upgrade indicator uses its original 19.8-by-37 size at x=4, y=4 inside the container. Both fit inside the box. The horizontal mask now has opacity one at both ends so it does not fade the indicator. Title containment and the other card geometry stay unchanged.

For a recurrence, inspect the actual parent, its resolved dimensions, and any mask before changing child offsets. Verify the active payload hash. After installing revision 27, check the resolved image box, background size/position, and tier bounds, then confirm the visible marks on several upgraded items. The user's revision 27 screenshots show centered artwork and restored upgrade indicators.

### Follow the actual native badge visibility path

The Equipped Gear tab contains only equipped items. Inventory can also contain equipped items, so a blanket CSS hide is incorrect. The live trees expose no tab-specific ancestor class on the badge.

Revision 26's ownership and native tab-flag checks matched the live card, but its hooked state setter was not the visibility path used by the item-card code. The earlier state-5 interpretation was wrong. Native item updates remove `!cpp-none` through both a helper and an inlined path, then refresh the style. Revision 27 restores the class before that common refresh only when the exact badge, refinement root, gear list, and equipped-only flag match. See the [native audit and guards](runtime.md#refinement-badge-filter).

After installation, check for `REFINEMENT: kept Equipped Gear badge hidden during native style refresh.` in the package log. Check both tabs in one session, including selection, scrolling, and returning to Equipped Gear. Read-only inspection can verify the badge's class and tab flag. An equipped item in Inventory must retain native badge behavior. Do not refine an item to validate presentation.

Revision 27 changes only the refinement stylesheet among the eighteen payloads and replaces the optional native badge hook. Eight native suites, 27 Python checks, and 20 installer cases pass. These checks cover the new class path and preserve verification of earlier packages. The user screenshots and runtime log confirm the Equipped Gear badge correction in revision 27. The other tab still needs a separate live check. Keep revision 27 as the current refinement rollback checkpoint.

### Card warning text, duplicate emblems, and short names

Live inspection after revision 27 found three independent card elements:

- `ItemIconDisableTextWrap` with `product-item1` still resolves to a 270-pixel wrapper. Its material warning overflows a 124-pixel card. Revision 28 hides this parent with a direct ID/class rule. The native disabled shading and the separate materials panel remain, and native refinement validation is unchanged.
- `ItemIconEmoji` with `product-item-icon` draws a full-card overlay. The contribution ring also has a generated inline emblem inside `ItemIconTitle`. Revision 28 hides the frame overlay and retains the inline emblem. The comparison panel uses a different title element and is unchanged.
- `ItemIconTitle` retains an automatic content width inside its 116-pixel scrolling wrapper. Revision 28 adds a 116-pixel minimum width and centers text/content within that width. Longer names can retain their intrinsic width and the existing horizontal scrolling; the outer wrapper remains aligned to its start.

These rules exist only in the refinement document stylesheet. No shared name formatter, localization record, material requirement, or native hook changes. Check a short name, a long name, the contribution ring, and an item with insufficient materials after installation. The expected result is one emblem, no card warning overflow, centered short names, and readable long names during focus/scrolling. Revision 28's fixture results do not establish those visible outcomes.

### Center the complete rich-text label, not its individual runs

Revisions 28 and 29 failed the live ring check. `ItemIconEmoji` resolved to `display: none`, so the frame-copy hide worked. The remaining emblem came from the name formatter. Revision 29's generic `.cpp-icon-emoji` rule did not fix it and displaced some short names. Do not repeat that rule or interpret a zero-size generated child as the whole rendering mechanism.

Read-only inspection of revision 29 on build `26329202` identified the separate native text runs. The layout loop near RVA `0x3867630` walks the element's run list. For `text-align: center`, the branch at `0x38676cc` adds `(label_width - run_width) / 2` to each run's existing x position. It does not center the assembled icon-and-name line once.

The live ring had a 172-pixel intrinsic line, split into a 24-pixel emblem and a 148-pixel name run, including the separating space. Relative to the label origin, the emblem moved from x=0 to x=74. The name moved from x=24 to x=36. The emblem therefore overlapped the name. Both measured positions match the native arithmetic. The previous change targeted the generated child's alignment instead of this parent run-layout operation.

The same session measured Ignir's visible run at 44 pixels inside a 154.667-pixel viewport. It started 91.333 pixels from the viewport's left edge, although the centered position is 55.333 pixels. The title's forced minimum width participated in native text measurement. A resolved `text-align: center` property alone is not evidence that a label is centered.

Revision 30 assigns alignment to the outer `ItemIconTitleWrap` flex container. The inner title has automatic width, minimum width zero, maximum width 116 CSS pixels, left-aligned text, and start-aligned contents. Short label boxes can be centered as a unit. Long label boxes are capped at the viewport, with the complete name still available in the detail panel. The inline emblem and text keep their native sequential run positions. The generic emoji override is removed, so tooltip and material symbols retain their original styles. The separate frame copy stays hidden.

To investigate a recurrence:

1. Verify the active package and the replacement log before inspecting layout.
2. Read the title, wrapper, and generated child styles and their actual bounds. Element x, y, width, and height are four floats at `+0x70` on this build.
3. Read the text-run vector through `element +0xa0`, then `+0x10`. Its data pointer is at `+0`, and its count is at `+8`. Each run's metrics pointer is at `+0x50`; the first four floats give x, y, width, and height. Bound reads and verify the current process before following pointers. These offsets are observations for this exact build, not portable runtime pins.
4. Compare the full run sequence with the viewport. Short names need equal side margins. An emblem must end before its following text begins. Long names must start inside the left edge and stay clipped by the viewport.
5. Inspect an emblem-bearing label, a short plain label, and a long label in the same live session. Do not infer all three from a CSS property check.

Two Python regressions replay the observed overlap and check the proposed whole-label geometry using the actual stylesheet. This replay models the audited arithmetic; it does not execute the game's layout engine. Revision 30 passes eight native suites, 29 Python tests, and 26 installer cases. Seventeen of eighteen asset payloads match revision 29, and the native runtime source and audit pins are unchanged. Revision 30 was installed, and the user confirmed the corrected layout. No post-install text-run measurement is claimed.

The same investigation found no tier texture on the Pailunese Signet card, although its tier element had the intended size and position. Its `CommonInfoDescription` field at `+0x8ca` was signed 16-bit zero. The neighboring dagger reported two and had a background texture. The native code near RVA `0xe053f2` reads this field to format `cd_icon_item_tier_%#`; the unsuccessful texture path removes the background property near `0xe056c4`. A blank level-zero slot is therefore different from a clipped nonzero marker. Do not add an I texture just because the refinement preview shows the proposed next level. No game item fields were changed during inspection or by this revision.

## Reuse the card layout in Crafting

Read-only inspection of the open Smithy screen on build `26329202` identified `CookingView3`, with `UIGamePlayControlRootCooking2` at the document root. `CookingRecipeList` uses `UIGamePlayControlCommonGridList`, one column, and four rows. Its compiled attributes identify `ItemIcon.CraftListItemIcon` and bind `#CookingRecipeList`. The material list uses `NeedStuffItemIconAbleFocus`; the ingredient list uses `CookingIngredientItemIcon`. These are separate controls, despite sharing some CSS classes.

Revision 31 changes one byte in the recipe list's compiled attributes: column 1 becomes 3. The source widget receives the same column override. The complete ten-attribute recipe binding must match exactly. No native handlers, materials, tab definitions, or other grid dimensions change.

Crafting wraps `ProductionItemIcon` inside `CraftListItemIcon`. Both have `item-icon-wrap` and `two-colunm-item-icon3`, so both receive the proven 124-by-106-pixel Refinement geometry. The nested `ItemDescription` gets zero margin to avoid counting the shared two-pixel margin twice. The outer card keeps the original 128-pixel column pitch and 108-pixel row pitch. Three columns fit the existing 387-pixel list, and four rows fit its 435-pixel height. Recipe-variant dots and previous/next controls retain their native handlers and percentage-based wrapper dimensions.

The document stylesheet has only 5,878 bytes available for either read hook. The transform removes five audited unused rules before appending the shared card layout: three decoration IDs that occur only in commented-out source markup, and two sequence rules whose class does not occur in the document. Their names are absent from the compiled tree. The transform checks those absences and requires exactly one copy of each removed rule. Active material, tab, background, and key-guide rules remain intact. Do not remove active rules merely to fit a buffer; re-audit changed assets and retain exact pins.

Revision 31's eight native suites, 32 Python tests, and 31 installer cases pass. All eighteen existing payload records match revision 30. These checks establish transform scope and runtime fixture behavior, not the visible Crafting result. The user confirmed the revision 31 Crafting layout after installation. Broader checks still include several categories, a long recipe name, unavailable recipes, scrolling, and recipe variants without crafting an item. Screens that reuse `CookingView3` also receive these cards and need separate live coverage.

## Apply the gear grid to Extraction

Read-only inspection of the open Extraction menu on build `26329202` found `UIGamePlayControlRootItemExtract` and its `InventoryContent` item list. The list creates the same `ProductionItemIcon` cards used by Refinement. Its compiled owner binding is also `#InventoryContent`, with one column and four rows. Revision 32 reuses the guarded Refinement transform to change only that column value and append the same card stylesheet.

The original Extraction viewport is 350 by 428 CSS pixels. Three card pitches need 384 pixels horizontally; four row pitches need 432 pixels vertically. Shrinking the cards without widening this viewport would leave the third column clipped, and the old height could clip the last row. The extraction transform changes the exact `.select-itemlist-wrap` rule to 390 by 435 pixels. The title already has a 390-pixel width. Its `ItemUIContainerWrap` inherits the wider viewport and keeps its existing 35-pixel top offset.

`ShowDetailContentList` is the later extraction-level selector, with one column and nine rows. `ExtractResultList` is the separate result list. Neither receives the column change. Original action bindings, including `ExtractStart`, remain byte-identical. The existing Refinement badge hook remains scoped to the Refinement root and does not hide Extraction badges.

The new package adds three exact-pinned, equal-length assets. All twenty-one revision 31 payloads and the native runtime pins remain unchanged. Eight native suites, 35 Python tests, and 37 installer cases pass. These checks do not establish the visible Extraction result. After installation, inspect item names, tier markers, the third column, the bottom row, scrolling, and the later level/result layout without executing extraction. Keep revision 31 available for rollback.

## Duplicate house emblems on buy cards

The user reported overlapping house symbols on furniture and dye names in a buy menu running revision 31. Read-only inspection found eight visible populated cards. The first four had both a visible `ItemIconEmoji` frame overlay and an inline name symbol. The frame overlay covered the whole card: about 165.33 by 149.33 screen pixels. The name's native text runs were already sequential for these long names: a 24-pixel symbol followed by a 168-, 177-, 183-, or 249-pixel name run. This separates the confirmed duplicate overlay from the short-name centering issue previously diagnosed in Refinement.

Do not hide `.cpp-icon-emoji` globally or remove the name formatter's symbols. Revision 33 assigns `item-icon-emoj_` only to the overlay in `StoreInfoIcon`. The change replaces one byte in each compiled component resource and the source template. `selector-item-icon-emoji`, `ItemIconEmoji`, native scripts, other components, and item data remain unchanged. A direct `#ItemIconEmoji.item-icon-emoj_` rule hides this duplicate. Inventory, gear cards, detail tooltips, and requirement icons do not acquire that class.

The buy title uses shop-specific aliases. Its wrapper now centers an auto-width label capped at 116 CSS pixels. The title itself uses left alignment and start-aligned contents, preserving the icon/name run sequence. Long labels retain their left edge and clip inside the card; short labels are centered together with any inline emblem. Existing price, stock, owned-count, requirement-spacing, hover, and empty-card rules are unchanged.

Revision 33 changes four of revision 32's twenty-four payloads and retains its prepared Extraction assets. Revision 31 remains installed until replacement is authorized. Eight native suites, 39 Python tests, and 43 installer cases pass; the Python geometry test includes the four measured symbol/name pairs. These are offline checks. After installation, inspect the same vendor's house-marked cards, plain short names, long names, and unavailable-item requirements without purchasing anything. Preserve the revision 31 package as the live rollback checkpoint.

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

## Extraction scrollbar sits outside the compact grid

Inspect the track's resolved `right` value before moving the grid. On build `26329202`, `InventoryContent.VerticalListScroll` carries `enchant-item-list-scroll` and `builtin-vscroll-track`. The imported `itemlist.css` sets the first class to `right: -45px`. That offset survives the three-column conversion.

The live revision 33 viewport measured 520 screen pixels wide at a 4/3 UI scale. Its track began 578.667 screen pixels after the viewport's left edge. This matches `(390 + 45 - 1) * 4/3`; the extra space is the inherited negative offset, not unused grid columns.

Revision 34 appends `.enchant-item-list-scroll.builtin-vscroll-track { right: 0px; }` to the Extraction document stylesheet. The two-class selector overrides the imported one-class rule. Keep this rule local to Extraction; its level and result tracks use different classes. The final stylesheet remains 10,804 bytes, with six padding bytes. The other 23 payloads remain identical to revision 33.

Offline checks establish selector scope, fixed asset size, preserved prior rules, and exact payload hashes. A live check must still confirm the scrollbar placement and scrolling behavior. Crafting's intermittent missing images are a separate unresolved issue: the captured blank weapon cards had valid names for existing DDS icon files and 124-by-76-pixel image containers. A blank screenshot alone does not establish whether a thumbnail is unavailable or its render binding is stale.
