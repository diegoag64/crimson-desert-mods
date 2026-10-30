"""Experimental NPC buy-store transforms; native handlers are preserved."""
import re
import struct
from pathlib import Path
from .inventory import sized

SHOP_PATHS = (
    'ui/bin__/npcstorebuyview2_game.uibinary',
    'ui/bin__/itemicon_component_game.uibinary',
    'ui/bin__/itemicon_game.uibinary',
    'ui/xml/gamemain/template/itemicon.thtml',
    'ui/xml/gamemain/play/npcstorebuyview2.html',
)


def transform(path, before):
    if path.endswith('/itemicon.css'):
        # The caller supplies the already transformed inventory stylesheet.
        styles = Path(__file__).with_name('shop_grid.css').read_text(encoding='utf8')
        styles = re.sub(r'(?<=\.)shop-grid-[\w-]+', lambda m: CSS_ALIASES[m[0]], styles)
        return fit_bytes(compact_css(before.decode('utf-8-sig') + '\n' + styles).encode('utf8'), len(before))
    if path.endswith('npcstorebuyview2_game.uibinary'):
        old = sized('column') + sized('2') + sized('row') + sized('4')
        new = sized('column') + sized('6') + sized('row') + sized('3')
        assert before.count(old) == 1
        after = before.replace(old, new)
        assert after.replace(new, old) == before
        return after
    if path.endswith('.uibinary'):
        return style_binary(before)[0]
    if path.endswith('.thtml'):
        return style_template(before)
    if path.endswith('npcstorebuyview2.html'):
        needle = b'<widget id="NpcStoreList"'
        assert before.count(needle) == 1
        return fit_markup(before.replace(needle, needle + b' column="6" row="3"'), len(before))
    raise ValueError('Unsupported shop asset: ' + path)

STYLE_NAMES={
    'item-icon-wrap':'shop-grid-root',
    'self-center':'shop-grid-center',
    'size-100per':'shop-grid-fill',
    'font-text-minor-white':'shop-grid-font-minor',
    'font-text-sub-white':'shop-grid-font-sub',
    'two-colunm-item-icon':'shop-grid-card',
    'two-colunm-item':'shop-grid-bg',
    'two-colunm-item2':'shop-grid-bg-alt',
    'two-colunm-item-icon-img':'shop-grid-image',
    'two-colunm-item-tier-texture':'shop-grid-tier',
    'item-icon-title-name-wrap':'shop-grid-titlebox',
    'item-icon-name-wrap':'shop-grid-titlewrap',
    'item-icon-name':'shop-grid-name',
    'store-info-item-item-title':'shop-grid-title-text',
    'two-line':'shop-grid-single-line',
    'item-icon-trade-price-wrap':'shop-grid-pricebox',
    'item-trade-coin-money':'shop-grid-price',
    'coin-money-list':'shop-grid-coinlist',
    'coin-money-wrap':'shop-grid-coinwrap',
    'small-coin-icon':'shop-grid-coinicon',
    'coin-money-value':'shop-grid-coinvalue',
    'store-item-coin-money-value':'shop-grid-pricevalue',
    'item-available-count-wrap':'shop-grid-counts',
    'store-info-count-wrap':'shop-grid-counts-extra',
    'item-available-count-icon':'shop-grid-stock-icon',
    'item-have-count-icon':'shop-grid-owned-icon',
    'item-available-count-text':'shop-grid-stock-count',
    'item-inventory-have-count-text':'shop-grid-owned-count',
    'slot-bg-item-list-hover':'shop-grid-hover',
    'list-item-focus-line':'shop-grid-focus-border',
    'item-icon-disabled-action-layer-colunm':'shop-grid-disabled',
}

# Some consumers call the fixed-buffer read directly. Keep every serialized
# class and every shop resource at its original length so both hooks replace it.
STYLE_MAP = {old: old[:-1] + '_' for old in STYLE_NAMES}
CSS_ALIASES = {name: STYLE_MAP[old] for old, name in STYLE_NAMES.items()}
assert len(set(STYLE_MAP.values())) == len(STYLE_MAP)
assert all(len(old) == len(new) for old, new in STYLE_MAP.items())


def fit_bytes(data, size):
    if len(data) > size:
        raise ValueError(f'Shop replacement exceeds original size: {len(data)} > {size}')
    return data + b' ' * (size - len(data))


def fit_markup(data, size):
    # Only discard formatting between tags; text nodes and attributes stay exact.
    return fit_bytes(re.sub(rb'>[\r\n\t ]+<', b'><', data), size)


def compact_css(text):
    # Strings are copied literally. Comments become whitespace, not concatenation.
    parts = re.split(r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|/\*.*?\*/)', text, flags=re.S)
    result = []
    pending = ''
    def flush():
        nonlocal pending
        value = re.sub(r'\s+', ' ', pending)
        value = re.sub(r'([{:;,]) +', r'\1', value)
        value = re.sub(r' +([{};])', r'\1', value)
        result.append(value)
        pending = ''
    for part in parts:
        if part.startswith(('"', "'")):
            flush()
            result.append(part)
        else:
            pending += ' ' if part.startswith('/*') else part
    flush()
    return ''.join(result).strip()

def component_end(data, name):
    """Read the component footer: name, classes, script, flags, attributes.

    Children precede this footer. The next component starts at its end.
    """
    needle = sized(name)
    if data.count(needle) != 1:
        raise ValueError('Component footer is missing or ambiguous: ' + name)
    pos = data.index(needle)

    def take(count):
        nonlocal pos
        if count < 0 or pos + count > len(data):
            raise ValueError('Truncated component footer: ' + name)
        result = data[pos:pos+count]
        pos += count
        return result

    def count(limit):
        value = struct.unpack('<I', take(4))[0]
        if value > limit:
            raise ValueError('Invalid component footer count: ' + name)
        return value

    def string():
        return take(count(4096)).decode('utf8')

    assert string() == name
    for _ in range(count(128)):
        string()
    string()  # Native script name.
    take(1)   # Serialized flags.
    for _ in range(count(128)):
        string()
        string()
    return pos


def style_binary(before):
    after=before; changes=[]
    for previous,name in [('StoreInfoIconWithChart','StoreInfoIcon'),('StoreInfoIcon2','FreeStoreInfoIcon')]:
        start=component_end(after, previous)
        end=component_end(after, name)
        assert start < after.index(sized(name)) < end
        original=after[start:end];block=original
        assert block.count(sized('two-colunm-item-icon'))==1
        assert not any(sized(alias) in original for alias in STYLE_MAP.values())
        replacements=[]
        for old,new in STYLE_MAP.items():
            count=block.count(sized(old))
            if count:
                # Replace a complete serialized string without changing any offsets.
                block=block.replace(sized(old),sized(new));replacements.append((old,new,count))
        # Verify no attribute, native script or binding bytes were lost.
        restored=block
        for old,new,count in reversed(replacements):
            assert restored.count(sized(new))==count,(name,old,new,count)
            restored=restored.replace(sized(new),sized(old))
        assert restored==original
        after=after[:start]+block+after[end:]
        changes.append(dict(component=name,style_strings=sum(r[2] for r in replacements)))
    assert len(after) == len(before)
    return after,changes

def style_template(before):
    text=before.decode('utf8')
    for name in ['StoreInfoIcon','FreeStoreInfoIcon']:
        pattern=re.compile(r'<component\b[^>]*\bname="'+name+r'"[^>]*>.*?</component>',re.S)
        matches=list(pattern.finditer(text));assert len(matches)==1
        m=matches[0];original=m[0]
        block=re.sub(r'\bcss="([^"]*)"',lambda a:'css="'+' '.join(STYLE_MAP.get(t,t) for t in a[1].split())+'"',original)
        # Source-loaded currency components need the same local styles as the compiled expansion.
        if name=='StoreInfoIcon':
            coin=re.search(r'<widget id="ItemIconPrice".*?</widget>',block,re.S);assert coin
            additions=''
            for target,style in [('GoldCoinMark','shop-grid-coinicon'),('SilverCoinMark','shop-grid-coinicon'),('BronzeCoinMark','shop-grid-coinicon'),
                ('GoldCoinWarp','shop-grid-coinwrap'),('SilverCoinWarp','shop-grid-coinwrap'),('BronzeCoinWarp','shop-grid-coinwrap'),('DefaultCoinWrap','shop-grid-coinlist')]:
                additions+=f'<override selector="#{target}" override-type="merge" css="{CSS_ALIASES[style]}"></override>\n'
            block=block[:coin.end()-9]+additions+block[coin.end()-9:]
        for attr in ['selector-[\\w-]+','script','tabindex','tabIndexGroup']:
            assert re.findall(r'\b'+attr+r'="[^"]*"',original)==re.findall(r'\b'+attr+r'="[^"]*"',block)
        text=text[:m.start()]+block+text[m.end():]
    return fit_markup(text.encode('utf8'), len(before))
