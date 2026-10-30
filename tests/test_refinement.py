import unittest

from nativegrid.inventory import sized
from nativegrid.refinement import REFINEMENT_PATHS, transform


class RefinementChecks(unittest.TestCase):
    def test_binary_changes_only_owned_gear_list(self):
        def attrs(owner):
            return (sized('column') + sized('1') + sized('row') + sized('4') +
                    sized('selector-show-layer-list') + sized(owner))
        gear = attrs('#InventoryContent')
        material = attrs('#IngredientContentList')
        before = b'prefix' + material + gear + b'native-handler'
        after = transform(REFINEMENT_PATHS[0], before)
        self.assertEqual(len(before), len(after))
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
        self.assertIn(material, after)
        self.assertTrue(after.endswith(b'native-handler'))
        for invalid in (material, gear + gear):
            with self.assertRaises(ValueError):
                transform(REFINEMENT_PATHS[0], invalid)

    def test_source_preserves_materials_and_handlers(self):
        before = (b'<widget id="IngredientContentList" column="1" row="4"></widget>'
                  b'<widget id="InventoryContent" script="native" column="1" row="4" '
                  b'filter-type="MultiChangeMaterial" selector-show-layer-list="#InventoryContent"></widget>')
        after = transform(REFINEMENT_PATHS[1], before)
        self.assertEqual(after.replace(b'column="3"', b'column="1"'), before)
        for invalid in (b'', before + before, before.replace(b'column="1"', b'column="2"')):
            with self.assertRaises(ValueError):
                transform(REFINEMENT_PATHS[1], invalid)

    def test_css_keeps_existing_rules_and_fixed_read_size(self):
        original = b'#Existing { width: 40px; } /* reserve space */' + b' ' * 3000
        result = transform(REFINEMENT_PATHS[2], original)
        self.assertEqual(len(result), len(original))
        self.assertIn(b'#Existing{width:40px;}', result)
        with self.assertRaises(ValueError):
            transform(REFINEMENT_PATHS[2], b'#Existing{width:40px;}')


if __name__ == '__main__':
    unittest.main()
