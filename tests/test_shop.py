"""Check shop transform scope and preservation of native handler attributes."""
import unittest
from nativegrid.shop import style_template, transform


class ShopChecks(unittest.TestCase):
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
