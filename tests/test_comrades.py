"""Check comrades grid ownership, fixed-size delivery, and native bindings."""
import re
import unittest

from nativegrid.comrades import COMRADES_PATHS, UNUSED_SELECTORS, list_attributes, transform
from nativegrid.inventory import sized
from nativegrid.shop import compact_css


class ComradesChecks(unittest.TestCase):
    def test_binary_changes_only_management_dimensions(self):
        original = list_attributes()
        unrelated = original.replace(sized('Pet.MercenaryManagementListItem'), sized('Pet.MercenaryListItem'))
        before = b'header' + unrelated + original + b'native-focus-and-selection'
        after = transform(COMRADES_PATHS[0], before)
        self.assertEqual(len(after), len(before))
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 2)
        self.assertEqual(after.replace(list_attributes('5', '3'), original), before)
        for invalid in (unrelated, original * 2, list_attributes('5', '3'),
                        original + sized('MercenaryStatusDecoRune')):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[0], invalid)

    def test_source_keeps_native_focus_and_other_lists(self):
        before = (b'<widget id="MercenaryList" component="Pet.MercenaryList" IsFocusSave="True" '
                  b'SendEventInsteadAutoFocus="true"></widget>\n\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t'
                  b'<widget id="MercenarySelectionList" column="1" row="6"></widget>\n'
                  b'<widget id="ShipStationList" row="6"></widget>' + b' ' * 100)
        after = transform(COMRADES_PATHS[1], before)
        self.assertEqual(len(after), len(before))
        normalized = re.sub(rb'>\s+<', b'><', before).rstrip()
        self.assertEqual(after.replace(b' column="5" row="3"', b'').rstrip(), normalized)
        for invalid in (b'', before + before, before.replace(b'Pet.MercenaryList', b'Pet.VehicleList'),
                        before.replace(b'IsFocusSave=', b'column="1" IsFocusSave=')):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[1], invalid)

    def test_css_preserves_details_and_fits_native_viewport(self):
        dead = ''.join(selector + ' { width: 1px; }' for selector in UNUSED_SELECTORS)
        active = '#MercenaryStatus { top: 110px; } #ShipStationList { height: 440px; }'
        before = (active + dead + ' ' * 2400).encode()
        after = transform(COMRADES_PATHS[2], before)
        self.assertEqual(len(after), len(before))
        self.assertIn(compact_css(active).encode(), after)
        rules = dict(re.findall(r'([^{}]+)\{([^{}]*)\}', after.decode()))
        rules = {key.strip(): value for key, value in rules.items()}
        card = rules['.mercenary-list-item-wrapper']
        width = int(re.search(r'width:(\d+)px', card)[1])
        height = int(re.search(r'height:(\d+)px', card)[1])
        top, right, bottom, left = map(int, re.search(r'margin:(\d+)px (\d+)px (\d+)px (\d+)px', card).groups())
        self.assertEqual((width + left + right) * 5, 650)
        self.assertLessEqual((height + top + bottom) * 3, 345)
        self.assertIn('justify-content:center;', rules['#MercenaryItemNameWrap'])
        self.assertIn('display:none;', rules['#MercenaryOccupationStateWrap'])
        self.assertNotIn('background-image', rules['#MercenaryItemTexture.mercenary-item-texture'])
        for invalid in (active.encode(), (active + dead + dead).encode(), (active + dead).encode()):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[2], invalid)

    def test_unrelated_asset_refused(self):
        with self.assertRaises(ValueError):
            transform('ui/xml/gamemain/play/horsestableview.css', b'')


if __name__ == '__main__':
    unittest.main()
