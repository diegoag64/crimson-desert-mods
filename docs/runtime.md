# Runtime guards and compatibility

The runtime resolves the primary named `ResourceLoadWorker_Package` interface through RTTI. Slot 5 handles equal-length postdecoded replacements. Slot 4 handles variable-length postdecoded replacements through the game's resize function at RVA `0x1501310` on the supported build.

Activation requires the exact full EXE SHA256 and 24-byte prefixes for both read methods and the resize method. The resource-method prefixes are generated from the user's own supported EXE and never checked into this repository. The build derives read-method RVAs locally and compares them with the known supported-build metadata.

Each substitution requires the matching asset path, worker, complete read, declared size, writable buffer, and byte-exact original resource. Partial reads and unrelated or modified resources pass through. A failed native resize returns failure rather than a truncated resource. Fixtures cover both successful replacements and guarded pass-through behavior.

Steam build `26317560` has EXE SHA256 `d4855c08998638f07fa8fae08bd6249261f10c8fec2215effc29cb339e7fa525`. Steam build `26329202`, EXE version `1.0.0.3446`, has SHA256 `fec07be1b725a46624d31fcd74bf3730ea809765226cea6bde01607ab2d79f66` and separate compatibility metadata.

For build `26329202`, slot 5 is at RVA `0x15859a0`, slot 4 is at `0x15858e0`, and the allocator is at `0x1501e20`. The builder verifies the direct allocator call at slot 4 plus `0x80`. The offline audit compared normalized read-method and handle-constructor instructions with the prior build and inspected allocator semantics. Buffer offsets and the size-plus-two terminator contract are unchanged. Ten of twelve original resources are unchanged. The inventory and item-icon component binaries have unrelated changes, so revision 7 transforms their current originals. No old replacement blob is reused.

The revision-5 inventory layout is user-verified on build `26317560`. Revision 7 has offline compatibility evidence and fixture checks, with live UI validation pending. A rebuilt binary still needs its own live check. The user confirmed the compact shop layout and revision 24 requirement spacing; broader purchase-flow testing remains pending. The runtime does not add a list-mode toggle.

## Refinement badge filter in revision 26

Only `--experimental-refinement` packages enable this third hook. Build `26329202` uses the native element-state setter at RVA `0x41d6a40`, with signature `void(void *element, const unsigned char *state, unsigned char enabled)`. State 5 controls `!cpp-none`: zero shows the element, and one hides it. Native Show/Hide callers and the setter body establish this contract. The package pins the 24-byte method prefix in `refinement_runtime`; the runtime checks it before creating any hooks.

The filter changes a Show request to Hide only when all these checks pass:

- The badge's direct parent has a `CommonInfoDescription` control (vtable RVA `0x59cf598`) whose owner is that parent and whose equipped-mark binding at `+0x358` is the input badge.
- A bounded parent walk finds a `Common_ItemList` control (vtable RVA `0x5a406b0`) and then a `RootItemEnchant` control (vtable RVA `0x5a72340`). Each control points back to its owning element.
- The refinement root's gear-list binding at `+0x1a0` identifies that list. This excludes ingredient lists and other menus.
- The list's equipped-only flag at `+0x21f` is exactly one.

Element parents are at `+0x38`, native controls at `+0xe0`, and control owners at `+0x08`. Reads are bounded and use `ReadProcessMemory` on the current process. Unknown flags, missing owners, unreadable pointers, and cycles preserve the native request. Traversal stops after twelve ancestors. The filter allocates nothing, stores no UI addresses, writes no game objects, and performs no background polling. It forwards the original state pointer and preserves `LastError` around inspection. The native setter performs the actual visibility and layout update on its calling thread.

Read-only comparison of the two live tabs found `+0x21f` set for Equipped Gear and clear for Inventory. The native tab callback sets this flag before refreshing the list. The Inventory list can include equipped items through its separate `+0x21a` flag, so hiding every refinement badge would remove useful information. The filter respects each new Show/Hide request when cards are reused after a tab switch.

The builder verifies the method prefix and all three RTTI names against the exact supported EXE. The optional hook joins the existing read hooks in queued activation, and initialization failures remove the hooks created by this plugin. A synthetic MinHook fixture checks 22 cases through an actual trampoline. These checks establish forwarding and filtering behavior in fixtures, not successful live UI rendering. Revision 26 still requires a live test; revision 25 has no element-state hook and remains the rollback package.
