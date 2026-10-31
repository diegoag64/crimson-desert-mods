"""Portrait-and-name cards in the Manage Comrades document."""
from pathlib import Path
import re
import struct

from .inventory import sized
from .shop import compact_css, component_end, fit_bytes, fit_markup, validate_shop_selectors

COMRADES_PATHS = (
    'ui/bin__/mercenarymanagementpanel_game.uibinary',
    'ui/xml/gamemain/play/mercenarymanagementpanel.html',
    'ui/xml/gamemain/play/mercenarymanagementpanel.css',
    'ui/bin__/pet_component_game.uibinary',
    'ui/xml/gamemain/template/pet.thtml',
    'ui/xml/gamemain/template/pet.css',
)

# Two six-byte class records replace twelve bytes saved in the root class.
# Keep every ID, native selector, script, flag, and the total buffer size intact.
OLD_ROOT = 'mercenary-list-item-wrapper'
CARD_ROOT = 'ng-comrade-tile'
CONTAINERS = ('MercenaryItemNameWrap', 'MercenaryOccupationStateWrap')
PREVIOUS_COMPONENT = 'MercenaryListItem_NotFocusable'
CARD_COMPONENT = 'MercenaryManagementListItem'


class CardReader:
    """Strict reader for the audited management card's 37 child elements.

    Child classes precede their children and ID. Component footer classes use a
    different format. Keep unknown fields explicit and reject changed encodings.
    This reader is deliberately not a general-purpose UI binary decoder.
    """
    def __init__(self, data):
        self.data = data
        self.pos = component_end(data, PREVIOUS_COMPONENT)
        self.limit = data.index(sized(CARD_COMPONENT))
        self.nodes = []

    def take(self, count):
        if count < 0 or self.pos + count > self.limit:
            raise ValueError('Truncated management card element')
        result = self.data[self.pos:self.pos + count]
        self.pos += count
        return result

    def count(self):
        result = struct.unpack('<I', self.take(4))[0]
        if result > 256:
            raise ValueError('Unexpected management element count')
        return result

    def string(self):
        length = struct.unpack('<I', self.take(4))[0]
        if length > 4096:
            raise ValueError('Unexpected management element string length')
        return self.take(length).decode('utf8')

    def flag(self):
        flag = self.take(1)[0]
        if flag not in (0, 1):
            raise ValueError('Unexpected management element flag')
        return flag

    def exact(self, expected):
        if self.take(len(expected)) != expected:
            raise ValueError('Unexpected management element reserved fields')

    def node(self, depth=0):
        if depth > 32:
            raise ValueError('Management card hierarchy is too deep')
        present = self.flag()
        classes_pos = self.pos if present else None
        classes = [self.string() for _ in range(self.count())] if present else []
        children = [self.node(depth + 1) for _ in range(self.count())] if self.flag() else []
        attributes = [(self.string(), self.string()) for _ in range(self.count())] if self.flag() else []
        self.exact(bytes(5))
        ident = self.string()
        references = [self.string() for _ in range(3)]
        script = self.string()
        self.exact(bytes(4))
        kind = self.take(1)[0]
        if kind not in (1, 4):
            raise ValueError('Unexpected management element kind')
        self.exact(bytes([0, 6]))
        node = dict(id=ident, classes=classes, children=children, attributes=attributes,
                    references=references, script=script, kind=kind)
        self.nodes.append((classes_pos, node))
        return node

    def parse(self):
        tree = [self.node() for _ in range(self.count())]
        self.exact(bytes(4))
        if self.pos != self.limit:
            raise ValueError('Management card did not end at its component footer')
        return tree


def card_binary(before):
    start = component_end(before, PREVIOUS_COMPONENT)
    end = component_end(before, CARD_COMPONENT)
    block = before[start:end]
    if block.count(sized(OLD_ROOT)) != 1 or sized(CARD_ROOT) in before:
        raise ValueError('Unexpected management card root classes')
    reader = CardReader(before)
    expected = reader.parse()
    edits = []
    for target in CONTAINERS:
        matches = [(pos, node) for pos, node in reader.nodes if node['id'] == target]
        if len(matches) != 1 or matches[0][0] is None or matches[0][1]['classes']:
            raise ValueError('Unexpected management container classes: ' + target)
        pos, node = matches[0]
        node['classes'] = ['ng']
        edits.append(pos)
    after = before
    for pos in sorted(edits, reverse=True):
        after = after[:pos] + struct.pack('<I', 1) + sized('ng') + after[pos + 4:]
    # The component footer alone owns this root class. No child string changes.
    root_start = after.index(sized(CARD_COMPONENT))
    after = after[:root_start] + after[root_start:].replace(sized(OLD_ROOT), sized(CARD_ROOT), 1)
    if len(after) != len(before) or after[:start] != before[:start] or after[end:] != before[end:]:
        raise ValueError('Management card edit escaped its fixed-size component')
    if CardReader(after).parse() != expected or component_end(after, CARD_COMPONENT) != end:
        raise ValueError('Management card structure or native bindings changed')
    return after


def card_source(before):
    matches = list(re.finditer(rb'<component name="MercenaryManagementListItem".*?</component>', before, re.S))
    if len(matches) != 1:
        raise ValueError('Missing or ambiguous management card source')
    match = matches[0]
    block = match[0]
    if block.count(OLD_ROOT.encode()) != 1 or CARD_ROOT.encode() in before:
        raise ValueError('Unexpected management source root classes')
    changed = block.replace(OLD_ROOT.encode(), CARD_ROOT.encode())
    for target in CONTAINERS:
        old = f'<div id="{target}">'.encode()
        if changed.count(old) != 1:
            raise ValueError('Unexpected management source container: ' + target)
        changed = changed.replace(old, old[:-1] + b' css="ng">')
    return before[:match.start()] + fit_markup(changed, len(block)) + before[match.end():]

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
    if path == COMRADES_PATHS[3]:
        return card_binary(before)
    if path == COMRADES_PATHS[4]:
        return card_source(before)
    if path == COMRADES_PATHS[5]:
        # Other documents can instantiate this shared component. Give its alias
        # exactly the original base/animation rules there; only the management
        # document supplies the more specific grid rule.
        css = before.decode('utf-8-sig')
        extra = []
        for selector in ('.' + OLD_ROOT, '.' + OLD_ROOT + '.cpp-main-mercenary'):
            matches = list(re.finditer(re.escape(selector) + r'\s*\{[^}]*\}', css))
            if len(matches) != 1:
                raise ValueError('Missing or ambiguous shared card fallback: ' + selector)
            extra.append(matches[0][0].replace(OLD_ROOT, CARD_ROOT))
        return fit_bytes(compact_css(css + '\n' + '\n'.join(extra)).encode('utf8'), len(before))
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
