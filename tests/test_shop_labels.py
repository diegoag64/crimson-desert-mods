import re
import struct
import unittest
from pathlib import Path

from nativegrid.inventory import sized
from nativegrid.shop_labels import LABEL_PATHS, OLD_EMBLEM, NEW_EMBLEM, transform


class BuyLabelChecks(unittest.TestCase):
    def test_binary_changes_only_store_overlay_class(self):
        def record(name):
            return (sized(OLD_EMBLEM) + sized('selector-item-icon-emoji') + sized('#ItemIconEmoji') +
                    sized(name) + struct.pack('<I', 0) + sized('native') + b'\x61' + struct.pack('<I', 0))
        previous, card, other = map(record, ('StoreInfoIconWithChart', 'StoreInfoIcon', 'StoreInfoIcon2'))
        before = previous + card + other
        for path in LABEL_PATHS[:2]:
            after = transform(path, before)
            self.assertEqual(len(after), len(before))
            self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
            self.assertTrue(after.startswith(previous))
            self.assertTrue(after.endswith(other))
            self.assertEqual(after.replace(sized(NEW_EMBLEM), sized(OLD_EMBLEM)), before)
            for invalid in (after, before + card, previous + card.replace(sized(OLD_EMBLEM), b'') + other):
                with self.assertRaises(ValueError):
                    transform(path, invalid)

    def test_source_keeps_native_binding_and_other_emblems(self):
        card = (b'<component name="StoreInfoIcon" selector-item-icon-emoji="#ItemIconEmoji">'
                b'<div id="ItemIconEmoji" css="inherit-no-pickable item-icon-emoji !cpp-none"></div></component>')
        other = card.replace(b'StoreInfoIcon', b'Other')
        before = card + other
        after = transform(LABEL_PATHS[2], before)
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
        self.assertTrue(after.endswith(other))
        self.assertIn(b'selector-item-icon-emoji="#ItemIconEmoji"', after)
        for invalid in (other, before + card, after):
            with self.assertRaises(ValueError):
                transform(LABEL_PATHS[2], invalid)

    def test_css_only_targets_scoped_classes_and_preserves_existing_rules(self):
        before = b'#Other { display: block; }' + b' ' * 1000
        after = transform(LABEL_PATHS[3], before)
        self.assertEqual(len(after), len(before))
        self.assertIn(b'#Other{display:block;}', after)
        self.assertIn(b'#ItemIconEmoji.item-icon-emoj_{display:none;}', after)
        self.assertNotIn(b'#ItemIconEmoji.item-icon-emoji', after)
        self.assertNotIn(b'.cpp-icon-emoji', after)
        with self.assertRaises(ValueError):
            transform(LABEL_PATHS[3], b'#Other{}')

    def test_name_runs_remain_sequential_when_centering_short_and_long_labels(self):
        css = Path('nativegrid/shop_labels.css').read_text()
        def rule(selector):
            body = re.search(re.escape(selector) + r'\s*\{([^}]+)\}', css)[1]
            return {k.strip(): v.strip() for k, v in
                    (part.split(':', 1) for part in body.split(';') if part.strip())}
        outer = rule('#ItemIconTitleWrap.item-icon-name-wra_')
        inner = rule('#ItemIconTitle.item-icon-nam_')
        self.assertEqual(outer['justify-content'], 'center')
        self.assertEqual(inner['width'], 'auto')
        self.assertEqual(inner['min-width'], '0px')
        self.assertEqual(inner['text-align'], 'left')
        self.assertEqual(inner['justify-content'], 'flex-start')
        viewport = float(inner['max-width'][:-2]) * 4 / 3
        # The four emblem-bearing live labels had a 24px symbol followed by
        # these name widths. Also cover short names and a short icon/name pair.
        for widths in ([24, 168], [24, 177], [24, 183], [24, 249], [44], [24, 40]):
            total = sum(widths)
            box = min(total, viewport)
            cursor = (viewport - box) / 2
            starts = []
            for width in widths:
                starts.append(cursor)
                cursor += width
            self.assertAlmostEqual(starts[0], max(0, (viewport - total) / 2))
            if len(widths) == 2:
                self.assertEqual(starts[1] - starts[0], widths[0])


if __name__ == '__main__':
    unittest.main()
