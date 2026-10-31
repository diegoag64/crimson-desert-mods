"""Compact Extraction item selection without changing levels or result lists."""
from .refinement import REFINEMENT_PATHS, transform as refinement_transform
from .shop import compact_css, fit_bytes

EXTRACTION_PATHS = (
    'ui/bin__/itemextractpanel_game.uibinary',
    'ui/xml/gamemain/play/itemextractpanel.html',
    'ui/xml/gamemain/play/itemextractpanel.css',
)

# Extraction's item selector is narrower than Refinement's. Three 128px
# pitches and four 108px pitches require 384 by 432px before scrollbar space.
OLD_ITEM_LIST_RULE = b'.select-itemlist-wrap { position: relative; width: 350px; height: 428px; }'
NEW_ITEM_LIST_RULE = b'.select-itemlist-wrap { position: relative; width: 390px; height: 435px; }'
SCROLLBAR_RULE = '.enchant-item-list-scroll.builtin-vscroll-track { right: 0px; }'


def transform(path, before, *, align_scrollbar=False):
    if path not in EXTRACTION_PATHS:
        raise ValueError('Unsupported extraction asset: ' + path)
    index = EXTRACTION_PATHS.index(path)
    if index == 2:
        if before.count(OLD_ITEM_LIST_RULE) != 1 or NEW_ITEM_LIST_RULE in before:
            raise ValueError('Missing or ambiguous extraction item-list dimensions')
        before = before.replace(OLD_ITEM_LIST_RULE, NEW_ITEM_LIST_RULE)
    # Both documents bind the same EnchantItemList_Vertical to InventoryContent.
    # The existing transform guards that exact owner and its one-column/four-row
    # attributes, leaving ShowDetailContentList and ExtractResultList intact.
    # Reuse revision 30's whole-label centering and tier-safe image container.
    after = refinement_transform(REFINEMENT_PATHS[index], before)
    if index == 2 and align_scrollbar:
        # The imported itemlist.css places this track 45px outside its viewport.
        # Two classes beat that imported rule; this document-local override does
        # not affect Refinement or the separate extraction level/result tracks.
        after = fit_bytes(compact_css(after.decode('utf8') + '\n' + SCROLLBAR_RULE).encode('utf8'), len(after))
    return after
