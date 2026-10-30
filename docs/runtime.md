# Runtime guards and compatibility

The runtime resolves the primary named `ResourceLoadWorker_Package` interface through RTTI. Slot 5 handles equal-length postdecoded replacements. Slot 4 handles variable-length postdecoded replacements through the game's resize function at RVA `0x1501310` on the supported build.

Activation requires the exact full EXE SHA256 and 24-byte prefixes for both read methods and the resize method. The resource-method prefixes are generated from the user's own supported EXE and never checked into this repository. The build derives read-method RVAs locally and compares them with the known supported-build metadata.

Each substitution requires the matching asset path, worker, complete read, declared size, writable buffer, and byte-exact original resource. Partial reads and unrelated or modified resources pass through. A failed native resize returns failure rather than a truncated resource. Fixtures cover both successful replacements and guarded pass-through behavior.

Steam build `26317560` has EXE SHA256 `d4855c08998638f07fa8fae08bd6249261f10c8fec2215effc29cb339e7fa525`. Steam build `26329202`, EXE version `1.0.0.3446`, has SHA256 `fec07be1b725a46624d31fcd74bf3730ea809765226cea6bde01607ab2d79f66` and separate compatibility metadata.

For build `26329202`, slot 5 is at RVA `0x15859a0`, slot 4 is at `0x15858e0`, and the allocator is at `0x1501e20`. The builder verifies the direct allocator call at slot 4 plus `0x80`. The offline audit compared normalized read-method and handle-constructor instructions with the prior build and inspected allocator semantics. Buffer offsets and the size-plus-two terminator contract are unchanged. Ten of twelve original resources are unchanged. The inventory and item-icon component binaries have unrelated changes, so revision 7 transforms their current originals. No old replacement blob is reused.

The revision-5 inventory layout is user-verified on build `26317560`. Revision 7 has offline compatibility evidence and fixture checks, with live UI validation pending. A rebuilt binary still needs its own live check. The user confirmed the compact shop layout and revision 24 requirement spacing; broader purchase-flow testing remains pending. The runtime does not add a list-mode toggle.

## Refinement badge filter

Revision 26's live test failed: Equipped badges remained visible. Its state-setter hook was active, and the ownership and tab checks matched live objects, but the item-card code bypasses that setter. The earlier claim that state 5 represented `!cpp-none` was incorrect. Do not use that state mapping for visibility fixes.

On build `26329202`, the native item updates near RVAs `0xe05b02` and `0xe1b597` obtain the badge from the description control's `+0x358` field. One path removes `!cpp-none` through a helper; the other removes it inline. Both refresh the style afterward. Live atom lookup identifies the global at RVA `0x71066b8` as `!cpp-none`. Its numeric atom ID is process-specific and is not hard-coded.

Revision 27 replaces the state-setter hook with the style-refresh hook at RVA `0x388f5a0`, signature `void(void *style)`. Before the original refresh, the filter restores `!cpp-none` only on the Equipped Gear badge. It uses the native class-vector insertion helper at `0x3892c50`, signature `unsigned char(void *vector, const uint32_t *atom)`, followed by the native sorting helper at `0x3893680`, signature `void(void *vector)`, only when insertion succeeds. These helpers do not call style refresh, so this sequence does not recursively enter the hook. The original refresh runs once afterward.

The filter requires all these checks:

- The style's owner at `+0x00` points to an element whose style at `+0x20` points back.
- That element's direct parent has a `CommonInfoDescription` control (vtable RVA `0x59cf598`) whose owner is the parent and whose equipped-mark binding at `+0x358` is the input badge.
- A bounded parent walk finds a `Common_ItemList` control (vtable RVA `0x5a406b0`) and then a `RootItemEnchant` control (vtable RVA `0x5a72340`). Each control points back to its owning element.
- The refinement root's gear-list binding at `+0x1a0` identifies that list, excluding ingredient lists and other menus.
- The list's equipped-only flag at `+0x21f` is exactly one.
- The hidden-class atom is initialized, and the class vector has readable entries and bounded count/capacity.

Element parents are at `+0x38`, native controls at `+0xe0`, and control owners at `+0x08`. Parent traversal stops after twelve ancestors. Unknown flags, missing owners, unreadable pointers, cycles, and invalid vectors preserve the native refresh. The plugin uses native helpers for class-vector changes and allocation; it does not write object fields directly or poll the tree. It stores no UI addresses between calls and preserves `LastError` around inspection and helper calls.

Read-only comparison found `+0x21f` set for Equipped Gear and clear for Inventory. The tab callback sets this flag before refreshing the list. Inventory can include equipped items through its separate `+0x21a` flag. In that tab, the plugin leaves native class changes alone, so an equipped item can show its badge. If `!cpp-none` is already present, the plugin skips insertion and sorting.

The full EXE hash and the three method prefixes gate activation. The builder also validates the three RTTI names and the atom's writable image section. Revision 27's pins live in `refinement_runtime_revisions.27`; revision 26's metadata remains unchanged for package verification. Only refinement packages compile this hook. Revision 28 uses the same runtime source and audit pins. The first eight corrections log `REFINEMENT: kept Equipped Gear badge hidden during native style refresh.`

The synthetic MinHook fixture checks 27 cases through a real trampoline, including both native removal paths, tab switches, idempotence, failed insertion, helper ordering, invalid graphs, and `LastError`. It does not execute game code. Revision 27 passed these fixtures and was installed. The user screenshots show hidden badges in Equipped Gear, and the runtime log records scoped corrections. A separate live check of equipped items in the Inventory tab remains pending. Keep revision 27 as the current refinement checkpoint and revision 25 as the earlier package without a presentation hook.
