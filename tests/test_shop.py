"""Check shop transform scope and preservation of native handler attributes."""
import unittest
from nativegrid.shop import style_template, style_binary, transform, STYLE_MAP, compact_css, fit_bytes
from nativegrid.inventory import sized


class ShopChecks(unittest.TestCase):
    def test_compiled_cards_isolate_shared_styles_and_preserve_bindings(self):
        styles = b''.join(sized(name) for name in STYLE_MAP)
        bindings = sized('cpp-item-slot-name') + sized('selector-item-price') + sized('.cpp-item-slot-price')
        card = sized('StoreInfoIcon') + styles + bindings
        free = sized('FreeStoreInfoIcon') + styles + bindings
        untouched = sized('StoreInfoIcon2') + styles
        source = card + untouched + free + sized('FreeStoreInfoIconWithChart') + styles
        result, records = style_binary(source)
        self.assertEqual(len(result), len(source))
        self.assertIn(untouched, result)
        self.assertTrue(result.endswith(sized('FreeStoreInfoIconWithChart') + styles))
        self.assertEqual(result.count(bindings), 2)
        self.assertEqual(len(records), 2)
        first = result[:result.index(sized('StoreInfoIcon2'))]
        for name in ('font-text-minor-white', 'font-text-sub-white', 'self-center', 'item-icon-wrap'):
            self.assertNotIn(sized(name), first)
            self.assertIn(sized(STYLE_MAP[name]), first)

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
