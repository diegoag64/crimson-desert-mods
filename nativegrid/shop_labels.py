"""Scoped buy-card emblem and whole-label fixes, applied after legacy shop transforms."""
from pathlib import Path
import re

from .inventory import sized
from .shop import component_end, compact_css, fit_bytes, validate_shop_selectors

LABEL_PATHS = (
    'ui/bin__/itemicon_component_game.uibinary',
    'ui/bin__/itemicon_game.uibinary',
    'ui/xml/gamemain/template/itemicon.thtml',
    'ui/xml/gamemain/title/itemicon.css',
)
OLD_EMBLEM = 'item-icon-emoji'
NEW_EMBLEM = 'item-icon-emoj_'


def transform(path, before):
    if path not in LABEL_PATHS:
        raise ValueError('Unsupported buy-label asset: ' + path)
    if path.endswith('.uibinary'):
        start = component_end(before, 'StoreInfoIconWithChart')
        end = component_end(before, 'StoreInfoIcon')
        if not start < before.index(sized('StoreInfoIcon')) < end:
            raise ValueError('Unexpected buy-card component order')
        block = before[start:end]
        if block.count(sized(OLD_EMBLEM)) != 1 or sized(NEW_EMBLEM) in block:
            raise ValueError('Missing or ambiguous buy-card frame emblem')
        changed = block.replace(sized(OLD_EMBLEM), sized(NEW_EMBLEM))
        assert changed.replace(sized(NEW_EMBLEM), sized(OLD_EMBLEM)) == block
        return before[:start] + changed + before[end:]
    if path.endswith('.thtml'):
        matches = list(re.finditer(rb'<component\b[^>]*\bname="StoreInfoIcon"[^>]*>.*?</component>', before, re.S))
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous source buy card')
        match = matches[0]
        needle = OLD_EMBLEM.encode()
        # Match a CSS token, leaving selector-item-icon-emoji and the ID intact.
        pattern = rb'(\bcss="[^"]*\b)' + needle + rb'(?=[ "])'
        block, count = re.subn(pattern, lambda m: m[1] + NEW_EMBLEM.encode(), match[0])
        if count != 1 or NEW_EMBLEM.encode() in match[0]:
            raise ValueError('Missing or ambiguous source frame-emblem class')
        assert len(block) == len(match[0])
        return before[:match.start()] + block + before[match.end():]
    styles = Path(__file__).with_name('shop_labels.css').read_text(encoding='utf8')
    validate_shop_selectors(styles)
    return fit_bytes(compact_css(before.decode('utf-8-sig') + '\n' + styles).encode('utf8'), len(before))
