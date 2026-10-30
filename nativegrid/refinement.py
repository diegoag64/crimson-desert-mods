"""Experimental refinement gear grid; preserve native item and material handlers."""
from pathlib import Path
import re

from .inventory import sized
from .shop import compact_css, fit_bytes, validate_shop_selectors

REFINEMENT_PATHS = (
    'ui/bin__/itemenchantpanel_game.uibinary',
    'ui/xml/gamemain/play/itemenchantpanel.html',
    'ui/xml/gamemain/play/itemenchantpanel.css',
)


def transform(path, before):
    if path == REFINEMENT_PATHS[0]:
        # Include the following owner binding: ingredient lists must stay vertical.
        old = (sized('column') + sized('1') + sized('row') + sized('4') +
               sized('selector-show-layer-list') + sized('#InventoryContent'))
        new = old.replace(sized('column') + sized('1'), sized('column') + sized('3'), 1)
        if before.count(old) != 1 or new in before:
            raise ValueError('Missing or ambiguous refinement gear-list attributes')
        after = before.replace(old, new)
        assert after.replace(new, old) == before
        assert sum(a != b for a, b in zip(before, after)) == 1
        return after
    if path == REFINEMENT_PATHS[1]:
        matches = list(re.finditer(rb'<widget\s+id="InventoryContent"[^>]*>', before))
        if len(matches) != 1 or matches[0][0].count(b'column="1" row="4"') != 1:
            raise ValueError('Missing or ambiguous refinement source gear list')
        match = matches[0]
        tag = match[0].replace(b'column="1" row="4"', b'column="3" row="4"')
        return before[:match.start()] + tag + before[match.end():]
    if path == REFINEMENT_PATHS[2]:
        styles = Path(__file__).with_name('refinement_grid.css').read_text(encoding='utf8')
        validate_shop_selectors(styles)
        # This stylesheet belongs to the refinement document. Shared item templates
        # and their stylesheets remain byte-identical to the working shop build.
        return fit_bytes(compact_css(before.decode('utf-8-sig') + '\n' + styles).encode('utf8'), len(before))
    raise ValueError('Unsupported refinement asset: ' + path)
