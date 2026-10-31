"""Three-column recipe cards for the native Smithy/CookingView3 document."""
from pathlib import Path
import re
import hashlib
import struct
from .pe import PE

from .inventory import sized
from .shop import compact_css, fit_bytes, fit_markup, validate_shop_selectors

CRAFTING_PATHS = (
    'ui/bin__/cookingview3_game.uibinary',
    'ui/xml/gamemain/play/cookingview3.html',
    'ui/xml/gamemain/play/cookingview3.css',
)

# These decorations are commented out in the source and absent from the compiled
# tree. The sequence selectors use a class that is also absent (the real class
# starts with cpp-). Remove only these audited dead rules to fit fixed-buffer reads.
UNUSED_SELECTORS = (
    '#CookingRecipeDecoLineHor01', '#CookingRecipeDecoLineHor02',
    '#CookingNeedStuffDecoLineHor01',
    '.cooking-recipe-list-container.cpp-show',
    '.cooking-recipe-list-container.cpp-hide',
)


def recipe_attributes(columns='1'):
    pairs = (
        ('column', columns), ('row', '4'), ('scroll-direction', 'vertical'),
        ('selector-panel', '.cpp-grid-list-panel'),
        ('selector-thumb', '.cpp-grid-list-thumb'),
        ('selector-track', '.cpp-grid-list-track'),
        ('item-component1', 'ItemIcon.CraftListItemIcon'),
        ('IsFocusSave', 'True'), ('receive-wasseen-event', 'true'),
        ('selector-show-layer-list', '#CookingRecipeList'),
    )
    return b''.join(sized(key) + sized(value) for key, value in pairs)


def transform(path, before):
    if path == CRAFTING_PATHS[0]:
        old, new = recipe_attributes(), recipe_attributes('3')
        if before.count(old) != 1 or new in before:
            raise ValueError('Missing or ambiguous crafting recipe-list attributes')
        for selector in UNUSED_SELECTORS:
            name = selector[1:].split('.')[0]
            if sized(name) in before:
                raise ValueError('Previously unused crafting selector now exists: ' + name)
        after = before.replace(old, new)
        assert len(after) == len(before)
        assert sum(a != b for a, b in zip(before, after)) == 1
        return after
    if path == CRAFTING_PATHS[1]:
        matches = list(re.finditer(rb'<widget\s+id="CookingRecipeList"[^>]*>', before))
        if len(matches) != 1:
            raise ValueError('Missing or ambiguous source recipe list')
        match = matches[0]
        if b'column=' in match[0] or match[0].count(b'row="4"') != 1:
            raise ValueError('Unexpected source recipe dimensions')
        tag = match[0].replace(b'row="4"', b'column="3" row="4"')
        return fit_markup(before[:match.start()] + tag + before[match.end():], len(before))
    if path == CRAFTING_PATHS[2]:
        css = before.decode('utf-8-sig')
        for selector in UNUSED_SELECTORS:
            css, count = re.subn(re.escape(selector) + r'\s*\{[^}]*\}', '', css)
            if count != 1:
                raise ValueError('Missing or duplicated unused crafting rule: ' + selector)
        # Reuse the user-confirmed revision 30 card layout, including whole-label
        # centering. CraftListItemIcon wraps ProductionItemIcon: its inner margin
        # must not be counted a second time. Variant handlers/controls stay native.
        styles = Path(__file__).with_name('refinement_grid.css').read_text(encoding='utf8')
        styles += '\n#ItemDescription.two-colunm-item-icon3 { margin: 0px; }'
        validate_shop_selectors(styles)
        return fit_bytes(compact_css(css + '\n' + styles).encode('utf8'), len(before))
    raise ValueError('Unsupported crafting asset: ' + path)


def audit_runtime(exe, pins):
    """Check the observed cache-repair path against the audited executable."""
    pe = PE(exe)
    for name in ('layout', 'background_size', 'background_position'):
        method = pins['methods'][name]
        raw = pe.raw(method['rva'])
        prefix = bytes.fromhex(method['prefix'])
        section = pe.section(method['rva'])
        if (len(prefix) != 24 or not section or not section['flags'] & 0x20000000 or
                exe[raw:raw+24] != prefix or method['size'] < 24 or
                hashlib.sha256(exe[raw:raw+method['size']]).hexdigest() != method['sha256']):
            raise ValueError('Crafting method differs from audit: ' + name)
    for name in ('description', 'card', 'list', 'root'):
        vt = pins[name+'_vtable']
        locator = struct.unpack_from('<Q', exe, pe.raw(vt['rva']-8))[0] - pe.base
        td = struct.unpack_from('<I', exe, pe.raw(locator)+12)[0]
        expected = vt['type'].encode('ascii') + b'\0'
        start = pe.raw(td)+16
        if exe[start:start+len(expected)] != expected:
            raise ValueError('Crafting owner type differs from audit: ' + name)
