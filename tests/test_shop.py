"""Check shop transform scope and preservation of native handler attributes."""
import unittest
import struct
import re
import xml.etree.ElementTree as ET
from nativegrid.shop import style_template, style_binary, transform, STYLE_MAP, compact_css, fit_bytes, component_end, validate_shop_selectors
from nativegrid.inventory import sized


class ShopChecks(unittest.TestCase):
    def test_recycled_stock_translation_has_explicit_normal_and_requirement_states(self):
        # Inspect the delivered, aliased CSS rather than the authoring class names.
        source = b'.unrelated{translate-y:7px;}' + b' ' * 20000
        old = transform('ui/xml/gamemain/title/itemicon.css', source)
        new = transform('ui/xml/gamemain/title/itemicon.css', source, reset_counts=True)
        self.assertEqual(len(new), len(source))
        reset = b'.item-available-count-tex_{translate-y:0px;} '
        self.assertEqual(new.count(reset.rstrip()), 1)
        self.assertEqual(new.replace(reset.rstrip(), b'').rstrip(), old.rstrip())
        rules = []
        for selector, body in re.findall(r'([^{}]+)\{([^{}]*)\}', new.decode()):
            value = re.search(r'(?:^|;)translate-y:([^;]+)', body)
            if value:
                rules.append((set(re.findall(r'\.([\w!-]+)', selector)), value[1]))
        def resolve(classes):
            matches = [(len(required), order, value) for order, (required, value) in enumerate(rules)
                       if required and required <= classes]
            return max(matches)[2] if matches else None
        normal = {'item-available-count-tex_', 'font-text-sub-whit_'}
        for _ in range(20):
            self.assertEqual(resolve(normal | {'font-text-sub-red-negative'}), '-18px')
            self.assertEqual(resolve(normal), '0px')
        self.assertIsNone(resolve({'item-inventory-have-count-tex_'}))
        self.assertEqual(resolve({'unrelated'}), '7px')

    def test_grouped_selectors_refused_without_confusing_values_or_strings(self):
        for css in ('.a, .b { top: 0px; }', '.a/* comment */, #b { translate-y: -18px; }'):
            with self.assertRaises(ValueError):
                validate_shop_selectors(css)
        validate_shop_selectors('#b.a { color: rgba(0, 0, 0, 1); content: "{,}"; } /* .a,.b{} */ #c.a { top: 0px; }')

    def test_selector_combinators_refused_after_live_parser_flattening(self):
        for selector in ('.a .b', '.a > .b', '.a>.b', '.a+.b', '.a~.b',
                         '#ItemAvailableCountWrap.shop-grid-counts .cpp-icon-emoji'):
            with self.assertRaises(ValueError):
                validate_shop_selectors(selector + ' { translate-y: -18px; }')
        validate_shop_selectors('.item-available-count-tex_.font-text-sub-red-negative { translate-y: -18px; }')

    def test_compiled_cards_isolate_shared_styles_and_preserve_bindings(self):
        styles = b''.join(sized(name) for name in STYLE_MAP if name != 'two-colunm-item-icon')
        bindings = (sized('cpp-item-slot-name') + sized('selector-item-price') + sized('.cpp-item-slot-price')
                    + sized('CoinMoneyImpossibleLabel'))
        def record(name):
            # The fixture puts child data BEFORE the named root footer, as the
            # game does. The previous name-to-next-name slice edits the wrong card.
            footer = (sized(name) + struct.pack('<I', 1) + sized('two-colunm-item-icon')
                      + sized('native_buy') + b'\x61' + struct.pack('<I', 1)
                      + sized('selector-item-price') + sized('.cpp-item-slot-price'))
            return struct.pack('<I', 1) + styles + bindings + footer
        previous = record('StoreInfoIconWithChart')
        card = record('StoreInfoIcon')
        free = record('FreeStoreInfoIcon')
        untouched = record('StoreInfoIcon2')
        following = record('FreeStoreInfoIconWithChart')
        source = previous + card + untouched + free + following
        result, records = style_binary(source)
        self.assertEqual(len(result), len(source))
        self.assertTrue(result.startswith(previous))
        self.assertIn(untouched, result)
        self.assertTrue(result.endswith(following))
        self.assertEqual(result.count(bindings), 5)
        self.assertEqual(len(records), 2)
        first = result[len(previous):len(previous)+len(card)]
        for name in ('font-text-minor-white', 'font-text-sub-white', 'self-center', 'item-icon-wrap', 'coin-money-label'):
            self.assertNotIn(sized(name), first)
            self.assertIn(sized(STYLE_MAP[name]), first)

    def test_component_footer_refuses_truncation_and_duplicate_name(self):
        with self.assertRaises(ValueError):
            component_end(sized('Card') + b'\x01', 'Card')
        with self.assertRaises(ValueError):
            component_end(sized('Card') * 2, 'Card')

    def test_template_retains_handlers_and_unrelated_component(self):
        source = (
            '<component name="StoreInfoIcon"><widget id="ItemIconPrice" css="two-colunm-item-icon" '
            'script="native_buy" selector-item="value" tabindex="7"></widget></component>'
            '<component name="FreeStoreInfoIcon"><widget css="two-colunm-item-icon" script="native_quantity"></widget></component>'
            '<component name="Other"><widget css="two-colunm-item-icon" script="unchanged"></widget></component>'
        ).encode().replace(b'><', b'>' + b' ' * 1800 + b'<', 1)
        after = style_template(source)
        for attribute in (b'script="native_buy"', b'script="native_quantity"', b'selector-item="value"', b'tabindex="7"'):
            self.assertIn(attribute, after)
        self.assertIn(b'<component name="Other"><widget css="two-colunm-item-icon" script="unchanged"></widget></component>', after)
        root = ET.fromstring(b'<root>' + after + b'</root>')
        for component in root:
            overrides = [node for node in component.iter('override')
                         if node.get('selector') in ('#CoinMoneyLabel', '#CoinMoneyImpossibleLabel')]
            self.assertEqual(len(overrides), 2 if component.get('name') == 'StoreInfoIcon' else 0)
            for override in overrides:
                self.assertEqual(override.attrib, {'selector': override.get('selector'),
                    'override-type': 'merge', 'css': STYLE_MAP['coin-money-label']})
        self.assertEqual(len(after), len(source))

    def test_css_compaction_preserves_strings_and_descendant_selectors(self):
        source = '.a .b { content: " a : b ; /* literal */ "; color: red; } /* comment */ .c { width: calc(100% - 2px); }'
        result = compact_css(source)
        self.assertIn('.a .b{', result)
        self.assertIn('" a : b ; /* literal */ "', result)
        self.assertIn('calc(100% - 2px)', result)
        self.assertNotIn('/* comment */', result)
        self.assertEqual(result, compact_css(result))

    def test_fixed_size_delivery_refuses_overflow(self):
        with self.assertRaises(ValueError):
            fit_bytes(b'longer', 3)
        self.assertEqual(fit_bytes(b'x', 3), b'x  ')

    def test_wrong_shop_layout_refused(self):
        with self.assertRaises(AssertionError):
            transform('ui/bin__/npcstorebuyview2_game.uibinary', b'unknown layout')


if __name__ == '__main__':
    unittest.main()
