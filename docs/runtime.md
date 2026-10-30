# Runtime guards and compatibility

The runtime resolves the primary named `ResourceLoadWorker_Package` interface through RTTI. Slot 5 handles equal-length postdecoded replacements. Slot 4 handles variable-length postdecoded replacements through the game's resize function at RVA `0x1501310` on the supported build.

Activation requires the exact full EXE SHA256 and 24-byte prefixes for both read methods and the resize method. Those prefixes are generated from the user's own supported EXE and never checked into this repository. The build derives read-method RVAs locally and compares them with the known supported-build metadata.

Each substitution requires the matching asset path, worker, complete read, declared size, writable buffer, and byte-exact original resource. Partial reads and unrelated or modified resources pass through. A failed native resize returns failure rather than a truncated resource. Fixtures cover both successful replacements and guarded pass-through behavior.

The supported Steam build is `26317560`. Its EXE SHA256 is `d4855c08998638f07fa8fae08bd6249261f10c8fec2215effc29cb339e7fa525`. EXE version `1.0.0.3446` has SHA256 `fec07be1b725a46624d31fcd74bf3730ea809765226cea6bde01607ab2d79f66` and is unsupported. Do not substitute that hash into the metadata without auditing methods, signatures, asset hashes, and fixture behavior.

The revision-5 inventory layout is user-verified on the supported build. A rebuilt binary still needs its own live check. The runtime does not add a list-mode toggle.
