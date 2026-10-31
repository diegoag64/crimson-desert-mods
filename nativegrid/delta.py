"""Bounded copy/XOR patches; original resources are supplied by the game."""
import hashlib
import json
from pathlib import Path
import subprocess


def make_patch(before, after):
    if not before or not after or max(len(before), len(after)) >= 2_000_000:
        raise ValueError('Resource size outside audited limit')
    # Index every fourth byte, retaining bounded alternatives for repeated runs.
    anchors = {}
    for at in range(0, len(before) - 15, 4):
        key = before[at:at + 16]
        slots = anchors.setdefault(key, [])
        if len(slots) < 8:
            slots.append(at)
    literals = bytearray()
    ops = []
    at = 0
    pending = 0
    while at < len(after):
        best, source = 0, 0
        for candidate in anchors.get(after[at:at + 16], ()):
            limit = min(len(before) - candidate, len(after) - at)
            length = 16
            while length + 1024 <= limit and before[candidate + length:candidate + length + 1024] == after[at + length:at + length + 1024]:
                length += 1024
            while length < limit and before[candidate + length] == after[at + length]:
                length += 1
            if length > best:
                best, source = length, candidate
        if best:
            if at > pending:
                ops.append((1, len(literals), at - pending))
                literals.extend(after[j] ^ before[j % len(before)] for j in range(pending, at))
            ops.append((0, source, best))
            at += best
            pending = at
        else:
            at += 1
    if at > pending:
        ops.append((1, len(literals), at - pending))
        literals.extend(after[j] ^ before[j % len(before)] for j in range(pending, at))
    return ops, bytes(literals)


def apply_patch(before, ops, literals, size):
    result = bytearray()
    if not before or not 0 < size < 2_000_000:
        raise ValueError('Invalid output size')
    for kind, offset, length in ops:
        source = literals if kind == 1 else before
        if kind not in (0, 1) or offset < 0 or length <= 0 or offset + length > len(source) or len(result) + length > size:
            raise ValueError('Invalid patch operation')
        if kind == 1:
            start = len(result)
            result.extend(source[offset + j] ^ before[(start + j) % len(before)] for j in range(length))
        else:
            result.extend(source[offset:offset + length])
    if len(result) != size:
        raise ValueError('Incomplete patch')
    return bytes(result)


def emit_payloads(payloads):
    arrays, entries, report = [], [], []
    def array(name, data):
        arrays.append('static const unsigned char ' + name + '[] = {' + ','.join(map(str, data or b'\0')) + '};')
    for i, (path, before, after) in enumerate(payloads):
        ops, literals = make_patch(before, after)
        if apply_patch(before, ops, literals, len(after)) != after:
            raise ValueError('Patch reconstruction differs: ' + path)
        array(f'literals_{i}', literals)
        arrays.append(f'static const struct PatchOp ops_{i}[] = {{' + ','.join(
            '{' + f'{offset}u,{length}u,{kind}u' + '}' for kind, offset, length in ops) + '};')
        digests = ['{' + ','.join(map(str, hashlib.sha256(data).digest())) + '}' for data in (before, after)]
        entries.append('{' + ','.join([json.dumps(path), *digests, f'literals_{i}', f'{len(literals)}u', f'ops_{i}', f'{len(ops)}u', f'{len(before)}u', f'{len(after)}u']) + '}')
        report.append(dict(path=path, original_size=len(before), replacement_size=len(after),
                           literal_bytes=len(literals), operations=len(ops),
                           original_sha256=hashlib.sha256(before).hexdigest(), replacement_sha256=hashlib.sha256(after).hexdigest()))
    arrays.extend(['static const struct Payload payloads[] = {' + ','.join(entries) + '};', f'#define PAYLOAD_COUNT {len(payloads)}u'])
    return '\n'.join(arrays) + '\n', report


def verify_native(folder, payloads, gcc):
    """Exercise the actual C decoder against every freshly extracted resource."""
    arrays = []
    for i, (_, before, after) in enumerate(payloads):
        for name, data in [('original', before), ('expected', after), ('copy', before)]:
            arrays.append(f'static unsigned char {name}_{i}[] = {{' + ','.join(map(str, data)) + '};')
    for name, prefix in [('originals', 'original'), ('expected', 'expected'), ('original_copies', 'copy')]:
        arrays.append(f'static unsigned char *fixture_{name}[] = {{' + ','.join(f'{prefix}_{i}' for i in range(len(payloads))) + '};')
    (folder/'patch_fixture_data.h').write_text('\n'.join(arrays) + '\n')
    exe = folder/'patch-fixture.exe'
    subprocess.run([str(gcc), '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-I', str(folder),
                    '-o', str(exe), str(Path(__file__).parent/'fixtures/patch_fixture.c'), '-lbcrypt'], check=True, timeout=90)
    result = subprocess.run([str(exe)], capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('Native patch fixture failed: ' + result.stdout + result.stderr)
    # Neither complete original nor replacement resources may occur in the ASI.
    binary = (folder/'NativeGrid.asi').read_bytes()
    for path, before, after in payloads:
        if before in binary or after in binary:
            raise ValueError('Complete resource embedded in release binary: ' + path)
    record = dict(case='native reconstruction, malformed patches, source preservation and full-resource exclusion',
                  passed=True, output=result.stdout)
    (folder/'patch-fixture-results.json').write_text(json.dumps(record, indent=2) + '\n')
    print(result.stdout.strip(), flush=True)
    return record
