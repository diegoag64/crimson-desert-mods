# Changelog

Newest first. Related experimental revisions are grouped to keep the history readable. Detailed diagnostics and test evidence live in [grid troubleshooting](docs/grid-layout-troubleshooting.md) and the [build guide](docs/build.md).

The current working checkpoint is **revision 41 on Steam build `26345091`**. Revision 38 is the earlier fallback without the comrades grid. "Confirmed" refers to the reported in-game behavior, not exhaustive testing.

**Do not install revisions 11, 12, 15, 17, or 40.** They were withdrawn or failed startup or loading checks.

| Revision | Change | Result |
| --- | --- | --- |
| 41 | Corrected comrades component serialization and added structural validation. | Comrades grid confirmed. |
| 40 | Isolated comrades styles from shared list rules. | Startup stalled; restored 38. |
| 39 | Introduced a five-column portrait-and-name comrades grid. | Shared styles kept full-width rows. |
| 38 | Reset stock-label translation when shop cards are reused. | Shop numbers confirmed aligned after scrolling. |
| 37 | Cleared stale stock-label line height on reused shop cards. | Misalignment remained; fixed in 38. |
| 36 | Allowed Crafting image repair during nested layout. | Initial Crafting icons confirmed visible. |
| 35 | Added Crafting image-cache repair; audited compatibility for Steam build `26345091`. | Initial icons still missing; fixed in 36. |
| 34 | Moved Extraction's scrollbar next to the compact grid. | Included in later builds. |
| 33 | Removed duplicate buy-card emblems and centered complete item labels. | Included in later builds. |
| 32 | Added the three-column Extraction item-selection grid. | Scrollbar spacing corrected in 34. |
| 31 | Applied the three-column gear-card layout to Crafting. | Layout confirmed; initial icons fixed later. |
| 30 | Centered complete labels instead of individual text and emblem runs. | Refinement layout confirmed. |
| 29 | Adjusted inline emblem alignment; investigated the ring's missing level indicator. | Alignment still wrong; ring reported tier zero. |
| 28 | Hid overflowing material warnings and duplicate frame emblems; adjusted short names. | Inline emblem overlap remained. |
| 27 | Restored upgrade indicators and hid Equipped badges in the Equipped Gear tab. | Indicators and badge removal confirmed. |
| 26 | Resized Refinement artwork and attempted conditional Equipped badges. | Indicators disappeared; badges remained. |
| 25 | Added a three-column, four-row Refinement grid. | Grid confirmed; card layout needed refinement. |
| 24 | Positioned requirement icons using the live container selector. | Shop requirement spacing confirmed. |
| 18 to 23 | Tested requirement rows, state selectors, and symbol translation. | Loaded, but spacing remained wrong. |
| 17 | Adjusted requirement-icon spacing through CSS. | Loading stalled; restored 16. |
| 16 | Kept working shop layouts and added icons-only English requirement labels. | Loading and icons confirmed; spacing unresolved. |
| 15 | Combined icons-only English requirements with new label styling. | Loading stalled; restored 14. |
| 14 | Fitted empty shop-slot artwork to its card. | Empty-slot alignment confirmed. |
| 13 | Added the eight-column, eleven-row Shop Sell layout. | Sell grid confirmed. |
| 11 to 12 | Tested shop placeholders, requirement labels, and sell-grid changes. | Withdrawn; 12 failed launch. |
| 6 to 10 | Added the buy grid, audited build `26329202`, and repaired fonts, component ranges, and resource delivery. | Buy layout confirmed at 10. |
| 5 | Established the compact Inventory and Private Storage baseline. | Confirmed on Steam build `26317560`. |

Keep future entries to the revision, the visible change, and its result. Put implementation details, package hashes, and test counts in the linked documentation.
