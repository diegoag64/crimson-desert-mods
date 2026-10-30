import re
import unittest

from nativegrid.crafting import CRAFTING_PATHS, UNUSED_SELECTORS, recipe_attributes, transform
from nativegrid.inventory import sized
from nativegrid.shop import compact_css


class CraftingChecks(unittest.TestCase):
    def test_binary_changes_only_recipe_columns(self):
        recipe = recipe_attributes()
        ingredients = recipe.replace(sized('ItemIcon.CraftListItemIcon'), sized('ItemIcon.CookingIngredientItemIcon'))
        before = b'header' + ingredients + recipe + b'native-crafting-controls'
        after = transform(CRAFTING_PATHS[0], before)
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
        self.assertEqual(len(before), len(after))
        self.assertEqual(after.replace(recipe_attributes('3'), recipe), before)
        for invalid in (ingredients, recipe * 2, recipe_attributes('3'),
                        recipe + sized('CookingRecipeDecoLineHor01')):
            with self.assertRaises(ValueError):
                transform(CRAFTING_PATHS[0], invalid)

    def test_source_preserves_other_lists_and_native_handlers(self):
        before = (b'<widget id="CookingRecipeList" item-component1="ItemIcon.CraftListItemIcon" row="4" '
                  b'IsFocusSave="True" selector-show-layer-list="#CookingRecipeList"></widget>\n\t\t\t\t\t\t\t\t'
                  b'<widget id="CookingNeedStuffList" row="5"></widget>\n'
                  b'<widget id="CookingIngredientList" row="5"></widget>\n'
                  b'<widget id="InventoryContent" column="4" row="5"></widget>\n'
                  b'<widget id="Make" keyMapName="CookingMake"></widget>' + b' ' * 50)
        after = transform(CRAFTING_PATHS[1], before)
        self.assertEqual(len(after), len(before))
        normalized = re.sub(rb'>\s+<', b'><', before).rstrip()
        self.assertEqual(after.replace(b'column="3" ', b'').rstrip(), normalized)
        for invalid in (b'', before + before, before.replace(b'row="4"', b'row="6"')):
            with self.assertRaises(ValueError):
                transform(CRAFTING_PATHS[1], invalid)

    def test_css_reuses_verified_geometry_and_preserves_active_rules(self):
        dead = ''.join(selector + ' { width: 1px; }' for selector in UNUSED_SELECTORS)
        active = '#CookingNeedStuffListContainer { width: 350px; }'
        before = (active + dead + ' ' * 3000).encode()
        after = transform(CRAFTING_PATHS[2], before)
        self.assertEqual(len(after), len(before))
        self.assertIn(compact_css(active).encode(), after)
        self.assertIn(b'#ItemDescription.two-colunm-item-icon3{margin:0px;}', after)
        self.assertIn(b'text-align:left;justify-content:flex-start;', after)
        self.assertIn(b'width:124px;height:106px;', after)
        for invalid in (active.encode(), (active + dead + dead).encode(), (active + dead).encode()):
            with self.assertRaises(ValueError):
                transform(CRAFTING_PATHS[2], invalid)


if __name__ == '__main__':
    unittest.main()
