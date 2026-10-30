# Runtime guards and compatibility

The runtime resolves the primary named `ResourceLoadWorker_Package` interface through RTTI. Slot 5 handles equal-length postdecoded replacements. Slot 4 handles variable-length postdecoded replacements through the game's resize function at RVA `0x1501310` on the supported build.

Activation requires the exact full EXE SHA256 and 24-byte prefixes for both read methods and the resize method. Those prefixes are generated from the user's own supported EXE and never checked into this repository. The build derives read-method RVAs locally and compares them with the known supported-build metadata.

Each substitution requires the matching asset path, worker, complete read, declared size, writable buffer, and byte-exact original resource. Partial reads and unrelated or modified resources pass through. A failed native resize returns failure rather than a truncated resource. Fixtures cover both successful replacements and guarded pass-through behavior.

Steam build `26317560` has EXE SHA256 `d4855c08998638f07fa8fae08bd6249261f10c8fec2215effc29cb339e7fa525`. Steam build `26329202`, EXE version `1.0.0.3446`, has SHA256 `fec07be1b725a46624d31fcd74bf3730ea809765226cea6bde01607ab2d79f66` and separate compatibility metadata.

For build `26329202`, slot 5 is at RVA `0x15859a0`, slot 4 is at `0x15858e0`, and the allocator is at `0x1501e20`. The builder verifies the direct allocator call at slot 4 plus `0x80`. The offline audit compared normalized read-method and handle-constructor instructions with the prior build and inspected allocator semantics. Buffer offsets and the size-plus-two terminator contract are unchanged. Ten of twelve original resources are unchanged. The inventory and item-icon component binaries have unrelated changes, so revision 7 transforms their current originals. No old replacement blob is reused.

The revision-5 inventory layout is user-verified on build `26317560`. Revision 7 has offline compatibility evidence and fixture checks, with live UI validation pending. A rebuilt binary still needs its own live check. The experimental shop has no valid live layout test. The runtime does not add a list-mode toggle.
