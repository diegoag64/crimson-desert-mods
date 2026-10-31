"""Check comrades grid ownership, fixed-size delivery, and native bindings."""
import re
import struct
import unittest

from nativegrid.comrades import (COMRADES_PATHS, UNUSED_SELECTORS, list_attributes, transform,
                                OLD_ROOT, CARD_ROOT, CONTAINERS, PREVIOUS_COMPONENT, CARD_COMPONENT, CardReader)
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
        card = rules['.ng-comrade-tile.inherit-pickable']
        width = int(re.search(r'width:(\d+)px', card)[1])
        height = int(re.search(r'height:(\d+)px', card)[1])
        top, right, bottom, left = map(int, re.search(r'margin:(\d+)px (\d+)px (\d+)px (\d+)px', card).groups())
        self.assertEqual((width + left + right) * 5, 650)
        self.assertLessEqual((height + top + bottom) * 3, 345)
        self.assertIn('justify-content:center;', rules['#MercenaryItemNameWrap.ng'])
        self.assertIn('display:none;', rules['#MercenaryOccupationStateWrap.ng'])
        self.assertNotIn('background-image', rules['#MercenaryItemTexture.mercenary-item-texture'])
        for invalid in (active.encode(), (active + dead + dead).encode(), (active + dead).encode()):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[2], invalid)

    @staticmethod
    def card_fixture(marker=False):
        # Child records: class vector, child vector, attributes, then ID/script.
        # Component footers have a separate layout. No game asset bytes are used.
        def node(ident, children=(), classes=(), script='', attrs=()):
            return (b'\x01' + struct.pack('<I', len(classes)) + b''.join(map(sized, classes)) +
                    (b'\x01' + struct.pack('<I', len(children)) + b''.join(children) if children else b'\x00') +
                    (b'\x01' + struct.pack('<I', len(attrs)) + b''.join(sized(k) + sized(v) for k, v in attrs) if attrs else b'\x00') +
                    bytes(5) + sized(ident) + bytes(12) + sized(script) + bytes(4) + bytes([1, 0, 6]))
        def footer(name, classes=()):
            return (sized(name) + struct.pack('<I', len(classes)) + b''.join(map(sized, classes)) +
                    sized('NativeStatus') + b'\x00' + struct.pack('<I', 1) +
                    sized('selector-name') + sized('#Name'))
        leaf = node('Name', classes=['font', '!cpp-none'], script='NativeShow', attrs=[('selector-show', '#Name')])
        roots = [node(key, children=[leaf], classes=['ng'] if marker else []) for key in CONTAINERS]
        return (b'untouched-earlier-components' + footer(PREVIOUS_COMPONENT) +
                struct.pack('<I', 2) + b''.join(roots) + bytes(4) +
                footer(CARD_COMPONENT, [CARD_ROOT if marker else OLD_ROOT, 'inherit-pickable']) + b'untouched-horses')

    def test_scoped_component_classes_keep_ids_bindings_and_fixed_length(self):
        before = self.card_fixture()
        after = transform(COMRADES_PATHS[3], before)
        self.assertEqual(after, self.card_fixture(marker=True))
        self.assertEqual(len(after), len(before))
        reader = CardReader(after)
        tree = reader.parse()
        self.assertEqual([n['id'] for n in tree], list(CONTAINERS))
        for parent in tree:
            self.assertEqual(parent['classes'], ['ng'])
            self.assertEqual(parent['children'][0]['script'], 'NativeShow')
            self.assertEqual(parent['children'][0]['attributes'], [('selector-show', '#Name')])
            self.assertEqual(parent['children'][0]['classes'], ['font', '!cpp-none'])
        for invalid in (before + before, before.replace(sized(OLD_ROOT), sized('other')), self.card_fixture(marker=True)):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[3], invalid)

    def test_rejects_revision40_class_records_after_ids(self):
        before = self.card_fixture()
        failed = before.replace(sized(OLD_ROOT), sized(CARD_ROOT))
        for target in CONTAINERS:
            failed = failed.replace(sized(target) + bytes(4), sized(target) + struct.pack('<I', 1) + sized('ng'))
        self.assertEqual(len(failed), len(before))
        with self.assertRaises(ValueError):
            CardReader(failed).parse()

    def test_reader_rejects_truncated_or_unknown_element_records(self):
        before = self.card_fixture()
        reader = CardReader(before)
        tree = reader.parse()
        first = reader.nodes[0][0]
        for bad in (before[:first] + struct.pack('<I', 1000) + before[first + 4:],
                    before.replace(bytes([1, 0, 6]), bytes([7, 0, 6]), 1),
                    before.replace(sized('NativeShow'), struct.pack('<I', 5000) + b'NativeShow', 1),
                    before.replace(sized(CONTAINERS[1]), sized('different-id'))):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[3], bad)

    def test_source_changes_only_management_card_and_preserves_native_selectors(self):
        lead = b'<component name="Horse"><div id="MercenaryItemNameWrap"></div></component>'
        tail = b'<component name="Crew"><div id="MercenaryOccupationStateWrap"></div></component>'
        card = (f'<component name="{CARD_COMPONENT}" css="{OLD_ROOT} inherit-pickable" '
                'script="NativeStatus" selector-mercenary-item-name="#MercenaryItemName">\n' +
                ''.join(f'    <div id="{key}"></div>\n' for key in CONTAINERS) +
                '    <div id="MercenaryItemName" css="!cpp-none"></div>\n</component>').encode()
        before = lead + card + tail
        after = transform(COMRADES_PATHS[4], before)
        self.assertEqual(len(after), len(before))
        self.assertTrue(after.startswith(lead))
        self.assertTrue(after.endswith(tail))
        self.assertEqual(re.findall(rb'\b(?:id|script|selector-[\w-]+)="[^"]*"', before),
                         re.findall(rb'\b(?:id|script|selector-[\w-]+)="[^"]*"', after))
        for invalid in (b'', before * 2, before.replace(b'<div id="MercenaryItemNameWrap">',
                                                       b'<div id="MercenaryItemNameWrap" css="changed">')):
            with self.assertRaises(ValueError):
                transform(COMRADES_PATHS[4], invalid)

    def test_shared_fallback_preserves_other_documents_and_animation(self):
        before = ('.mercenary-list-item-wrapper { position: absolute; width: 650px; height: 84px; margin-bottom: 3px; }'
                  '.mercenary-list-item-wrapper.cpp-main-mercenary { sequencer-name: example; }'
                  '#MercenaryItemNameWrap { width: 280px; }' + ' ' * 600).encode()
        after = transform(COMRADES_PATHS[5], before).decode()
        rules = dict((a.strip(), b) for a, b in re.findall(r'([^{}]+)\{([^{}]*)\}', after))
        for suffix in ('', '.cpp-main-mercenary'):
            self.assertEqual(rules['.' + OLD_ROOT + suffix], rules['.' + CARD_ROOT + suffix])
        self.assertIn('#MercenaryItemNameWrap{width:280px;}', after)
        self.assertEqual(len(after.encode()), len(before))
        with self.assertRaises(ValueError):
            transform(COMRADES_PATHS[5], b'.unrelated { width: 1px; }')

    def test_late_shared_rules_cannot_replace_grid_selectors(self):
        # The live failure retained only the last block with each exact selector.
        # Model that collision explicitly, with shared rules loaded AFTER ours.
        from pathlib import Path
        grid = Path('nativegrid/comrades_grid.css').read_text()
        shared = ('.mercenary-list-item-wrapper{width:650px;height:84px;}'
                  '.ng-comrade-tile{width:650px;height:84px;}'
                  '#MercenaryItemNameWrap{width:280px;height:58px;}'
                  '#MercenaryOccupationStateWrap{display:flex;}'
                  '#MercenaryItemHyosiMark{width:644px;}'
                  '#MercenaryItemFriendlyIcon{width:18px;}')
        rules = {a.strip(): b for a, b in re.findall(r'([^{}]+)\{([^{}]*)\}', compact_css(grid) + shared)}
        self.assertIn('width:124px;', rules['.ng-comrade-tile.inherit-pickable'])
        self.assertIn('width:116px;', rules['#MercenaryItemNameWrap.ng'])
        self.assertIn('display:none;', rules['#MercenaryOccupationStateWrap.ng'])
        self.assertIn('display:none;', rules['#MercenaryItemHyosiMark.cpp-show-layer'])
        # A unique compound selector is required for every custom rule.
        self.assertTrue(all(len(re.findall(r'[.#][\w!-]+', selector)) >= 2
                            for selector, _ in re.findall(r'([^{}]+)\{([^{}]*)\}', compact_css(grid))))

    def test_unrelated_asset_refused(self):
        with self.assertRaises(ValueError):
            transform('ui/xml/gamemain/play/horsestableview.css', b'')


if __name__ == '__main__':
    unittest.main()
