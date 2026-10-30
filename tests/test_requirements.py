"""Synthetic localization fixtures: icon-only labels and strict format guards."""
import struct
import unittest
import lz4.block
from nativegrid.requirements import LABELS, transform, unpack, records


def record(key, value, tag=11, reserved=0):
    key, value = key.encode(), value.encode('utf8')
    return struct.pack('<III', tag, reserved, len(key)) + key + struct.pack('<I', len(value)) + value


def envelope(inner):
    packed = lz4.block.compress(inner, store_size=False)
    return b'paloc\0\0\0\0' + struct.pack('<II', len(packed), len(inner)) + bytes(495) + packed


def fixture(labels=None):
    labels = LABELS if labels is None else labels
    entries = [record(key, value) for key, value in labels.items()]
    entries += [record('100', 'Trust'), record('101', 'Detailed requirement explanation: unchanged.')]
    return envelope(b''.join(entries) + struct.pack('<I', len(entries)))


class RequirementChecks(unittest.TestCase):
    def test_only_short_labels_change_and_icons_keep_order_and_case(self):
        before = fixture()
        original = records(unpack(before))
        after = transform(before)
        result = records(unpack(after))
        self.assertEqual(len(original), len(result))
        by_key = {row[0]: row[3] for row in result}
        self.assertEqual(by_key['6675443097217794224'],
                         '{emoji:cd_hud_affinity_gauge_bg_05} {emoji:cd_Icon_map_item_paper}')
        self.assertEqual(by_key['5944274002255020208'], '{emoji:cd_hud_affinity_gauge_bg_05}')
        self.assertEqual(by_key['578823104575307952'],
                         '{emoji:cd_icon_map_camp_housing_00} {emoji:cd_hud_affinity_gauge_bg_05}')
        for old, new in zip(original, result):
            self.assertEqual(old[:3], new[:3])
            if old[0] not in LABELS:
                self.assertEqual(unpack(before)[old[4]:old[6]], unpack(after)[new[4]:new[6]])

    def test_missing_changed_and_already_patched_labels_are_refused(self):
        changed = dict(LABELS)
        changed[next(iter(changed))] += ' changed'
        for data in (fixture({}), fixture(changed), transform(fixture())):
            with self.subTest(size=len(data)), self.assertRaises(ValueError):
                transform(data)

    def test_bad_envelope_sizes_and_reserved_header_are_refused(self):
        valid = fixture()
        bad_header = bytearray(valid); bad_header[20] = 1
        bad_size = bytearray(valid); struct.pack_into('<I', bad_size, 9, len(valid))
        for data in (valid[:100], bytes(bad_header), bytes(bad_size), valid + b'x'):
            with self.assertRaises(ValueError):
                transform(data)

    def test_count_duplicate_key_truncation_and_category_guard(self):
        valid = unpack(fixture())
        wrong_tag = bytearray(valid); struct.pack_into('<I', wrong_tag, 0, 12)
        duplicate = record('1', 'a') + record('1', 'b') + struct.pack('<I', 2)
        for inner in (valid[:-4] + struct.pack('<I', 1), valid[:15] + bytes(4), duplicate, bytes(wrong_tag)):
            with self.assertRaises(ValueError):
                transform(envelope(inner))


if __name__ == '__main__':
    unittest.main()
