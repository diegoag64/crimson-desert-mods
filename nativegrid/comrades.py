"""Portrait-and-name cards in the Manage Comrades document."""
from pathlib import Path
import re

from .inventory import sized
from .shop import compact_css, fit_bytes, fit_markup, validate_shop_selectors

COMRADES_PATHS = (
    'ui/bin__/mercenarymanagementpanel_game.uibinary',
    'ui/xml/gamemain/play/mercenarymanagementpanel.html',
    'ui/xml/gamemain/play/mercenarymanagementpanel.css',
)

# These ID rules have no element in the compiled document or its source.
# Remove only these audited decorations to fit the original CSS buffer.
UNUSED_SELECTORS = (
    '#MercenaryShipStationWrap', '#ShipCrewTabBar', '#ShipCrewListWrap',
    '#ShipCrewTabBarSplitLineHorizontal', '#MercenaryStatusDecoRune',
)


def list_attributes(columns='1', rows='4'):
    return b''.join(sized(key) + sized(value) for key, value in (
        ('column', columns), ('row', rows),
        ('item-component1', 'Pet.MercenaryManagementListItem'),
        ('free-slot-component', 'Pet.EmptySlotIcon'),
        ('receive-wasseen-event', 'true'),
        ('selector-panel', '.cpp-grid-list-panel'),
        ('selector-thumb', '.cpp-grid-list-thumb'),
        ('selector-track', '.cpp-grid-list-track'),
        ('IsFocusSave', 'True'), ('SendEventInsteadAutoFocus', 'true'),
    ))


def transform(path, before):
    if path == COMRADES_PATHS[0]:
        old, new = list_attributes(), list_attributes('5', '3')
        if before.count(old) != 1 or new in before:
            raise ValueError('Missing or ambiguous Manage Comrades list attributes')
        for selector in UNUSED_SELECTORS:
            if sized(selector[1:]) in before:
                raise ValueError('Previously unused comrade decoration now exists: ' + selector)
        after = before.replace(old, new)
        assert len(after) == len(before)
        assert sum(a != b for a, b in zip(before, after)) == 2
        return after
    if path == COMRADES_PATHS[1]:
        matches = list(re.finditer(rb'<widget\s+id="MercenaryList"[^>]*>', before))
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous source comrades list')
        match = matches[0]
        if (b'component="Pet.MercenaryList"' not in match[0] or
                b'column=' in match[0] or b'row=' in match[0]):
            raise ValueError('Unexpected source comrades component or dimensions')
        tag = match[0][:-1] + b' column="5" row="3">'
        return fit_markup(before[:match.start()] + tag + before[match.end():], len(before))
    if path == COMRADES_PATHS[2]:
        css = before.decode('utf-8-sig')
        for selector in UNUSED_SELECTORS:
            css, count = re.subn(re.escape(selector) + r'\s*\{[^}]*\}', '', css)
            if count != 1:
                raise ValueError('Missing or ambiguous unused comrade rule: ' + selector)
        styles = Path(__file__).with_name('comrades_grid.css').read_text(encoding='utf8')
        validate_shop_selectors(styles)
        return fit_bytes(compact_css(css + '\n' + styles).encode('utf8'), len(before))
    raise ValueError('Unsupported comrades asset: ' + path)
