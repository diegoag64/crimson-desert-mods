"""Check shop transform scope and preservation of native handler attributes."""
import unittest
from nativegrid.shop import style_template, style_binary, transform, STYLE_MAP
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
        ).encode()
        after = style_template(source)
        for attribute in (b'script="native_buy"', b'script="native_quantity"', b'selector-item="value"', b'tabindex="7"'):
            self.assertIn(attribute, after)
        self.assertTrue(after.endswith(b'<component name="Other"><widget css="two-colunm-item-icon" script="unchanged"></widget></component>'))

    def test_wrong_shop_layout_refused(self):
        with self.assertRaises(AssertionError):
            transform('ui/bin__/npcstorebuyview2_game.uibinary', b'unknown layout')


if __name__ == '__main__':
    unittest.main()
