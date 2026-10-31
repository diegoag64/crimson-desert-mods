import re
import unittest

from nativegrid.extraction import EXTRACTION_PATHS, OLD_ITEM_LIST_RULE, NEW_ITEM_LIST_RULE, transform
from nativegrid.inventory import sized
from nativegrid.shop import compact_css


class ExtractionChecks(unittest.TestCase):
    def test_only_item_selection_columns_change(self):
        def attrs(owner, rows):
            return (sized('column') + sized('1') + sized('row') + sized(rows) +
                    sized('selector-show-layer-list') + sized(owner))
        items = attrs('#InventoryContent', '4')
        levels = attrs('#ShowDetailContentList', '9')
        results = attrs('#ExtractResultList', '5')
        before = b'header' + items + levels + results + b'ExtractStart'
        after = transform(EXTRACTION_PATHS[0], before)
        self.assertEqual(len(after), len(before))
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
        self.assertIn(levels + results + b'ExtractStart', after)
        for invalid in (levels + results, items * 2, attrs('#InventoryContent', '9')):
            with self.assertRaises(ValueError):
                transform(EXTRACTION_PATHS[0], invalid)

    def test_source_retains_extraction_depths_and_handlers(self):
        before = (b'<div id="ExtractItemSelectDepth"><widget id="InventoryContent" '
                  b'column="1" row="4" SendEventInsteadAutoFocus="true"></widget></div>'
                  b'<div id="ExtractLevelSelectDepth"><widget id="ShowDetailContentList" '
                  b'column="1" row="9"></widget><widget id="ExtractResultList" row="5"></widget></div>'
                  b'<widget id="Extract" keyMapName="ExtractStart"></widget>')
        after = transform(EXTRACTION_PATHS[1], before)
        self.assertEqual(after.replace(b'column="3"', b'column="1"'), before)

    def test_scrollbar_override_moves_only_selection_track_to_viewport_edge(self):
        from nativegrid.extraction import SCROLLBAR_RULE
        before = OLD_ITEM_LIST_RULE + b' ' * 2000
        legacy = transform(EXTRACTION_PATHS[2], before)
        aligned = transform(EXTRACTION_PATHS[2], before, align_scrollbar=True)
        rule = compact_css(SCROLLBAR_RULE).encode()
        self.assertEqual(len(aligned), len(before))
        self.assertNotIn(rule, legacy)
        self.assertEqual(aligned.count(rule), 1)
        self.assertEqual(aligned.replace(rule, b'').rstrip(), legacy.rstrip())

    def test_geometry_fits_all_rows_without_changing_results_panel(self):
        result_rule = b'#ExtractResultList { height: 435px; }'
        before = OLD_ITEM_LIST_RULE + result_rule + b' ' * 2000
        after = transform(EXTRACTION_PATHS[2], before)
        self.assertEqual(len(after), len(before))
        self.assertIn(compact_css(NEW_ITEM_LIST_RULE.decode()).encode(), after)
        self.assertIn(compact_css(result_rule.decode()).encode(), after)
        width, height = map(int, re.search(rb'width:(\d+)px;height:(\d+)px;', after).groups())
        self.assertGreaterEqual(width, 3 * (124 + 4))
        self.assertGreaterEqual(height, 4 * (106 + 2))
        self.assertIn(b'text-align:left;justify-content:flex-start;', after)
        for invalid in (result_rule, OLD_ITEM_LIST_RULE * 2 + b' ' * 2000, NEW_ITEM_LIST_RULE):
            with self.assertRaises(ValueError):
                transform(EXTRACTION_PATHS[2], invalid)


if __name__ == '__main__':
    unittest.main()
