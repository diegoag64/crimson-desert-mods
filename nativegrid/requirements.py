"""Exact English short requirement labels; detailed explanations stay intact."""
import re
import struct
import lz4.block

PATH = 'gamedata/stringtable/binary__/eng/localstringinfo.paloc'
INDEX = '0020/0.pamt'
LABELS = {
    '578823104575307952': '{emoji:cd_icon_map_camp_housing_00} Ranch, {emoji:cd_hud_affinity_gauge_bg_05} Trust',
    '5944274002255020208': '{emoji:cd_hud_affinity_gauge_bg_05} Trust',
    '6675443097217794224': '{emoji:cd_hud_affinity_gauge_bg_05} Trust, {emoji:cd_Icon_map_item_paper} Contract Complete',
}


def unpack(data):
    """Validate the audited 512-byte PALOC envelope and decode its LZ4 block."""
    if len(data) < 512 or data[:9] != b'paloc\0\0\0\0' or any(data[17:512]):
        raise ValueError('Unknown PALOC envelope')
    packed, original = struct.unpack_from('<II', data, 9)
    if packed != len(data) - 512 or not 4 <= original < 2_000_000:
        raise ValueError('Invalid PALOC envelope sizes')
    inner = lz4.block.decompress(data[512:], uncompressed_size=original)
    if len(inner) != original:
        raise ValueError('PALOC decoded size differs')
    return inner


def records(inner):
    """Return validated record spans; the final u32 independently counts them."""
    if len(inner) < 4:
        raise ValueError('Truncated PALOC table')
    end, pos, result, keys = len(inner) - 4, 0, [], set()
    def take(size):
        nonlocal pos
        if size < 0 or pos + size > end:
            raise ValueError('Truncated PALOC record')
        value = inner[pos:pos+size]
        pos += size
        return value
    while pos < end:
        start = pos
        tag, reserved, length = struct.unpack('<III', take(12))
        if not 1 <= length <= 128:
            raise ValueError('Invalid PALOC key length')
        key = take(length).decode('ascii')
        if not key.isdecimal() or key in keys:
            raise ValueError('Invalid or duplicate PALOC key')
        keys.add(key)
        size_at = pos
        value = take(struct.unpack('<I', take(4))[0]).decode('utf8')
        result.append((key, tag, reserved, value, start, size_at, pos))
    if len(result) != struct.unpack_from('<I', inner, end)[0]:
        raise ValueError('PALOC trailer count differs from parsed records')
    return result


def transform(before):
    inner = unpack(before)
    parsed = records(inner)
    output, changed = [], set()
    for key, tag, reserved, value, start, size_at, end in parsed:
        if key not in LABELS:
            output.append(inner[start:end])
            continue
        if tag != 11 or reserved != 0 or value != LABELS[key]:
            raise ValueError('Short requirement label changed: ' + key)
        # Retain the engine's inline emoji tokens and their order, including
        # case. These are not substitute images or changes to purchase rules.
        icons = ' '.join(re.findall(r'\{emoji:[^{}]+\}', value)).encode('utf8')
        output.append(inner[start:size_at] + struct.pack('<I', len(icons)) + icons)
        changed.add(key)
    if changed != LABELS.keys():
        raise ValueError('Missing short requirement labels')
    after_inner = b''.join(output) + inner[-4:]
    checked = records(after_inner)
    assert len(checked) == len(parsed)
    for old, new in zip(parsed, checked):
        assert old[:3] == new[:3]
        if old[0] not in LABELS:
            assert inner[old[4]:old[6]] == after_inner[new[4]:new[6]]
    packed = lz4.block.compress(after_inner, mode='high_compression', compression=9, store_size=False)
    header = bytearray(before[:512])
    struct.pack_into('<II', header, 9, len(packed), len(after_inner))
    after = bytes(header) + packed
    assert unpack(after) == after_inner
    return after
