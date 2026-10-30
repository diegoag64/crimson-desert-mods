"""Exact, reversible inventory layout and CSS transforms."""
import re
import struct

def sized(value):
    data = value.encode()
    return struct.pack("<I", len(data)) + data

def change_css(before):
    # Edit the existing rules in the stylesheet that defines each property.
    edits={
        '.item-icon-wrap': {'width': '64px','height':'64px'},
        '.item-icon-size': {'width':'52px','height':'52px'},
        '.gridlist-item-icon-size': {'width':'58px','height':'58px'},
        '.item-gauge-cooltime.normal-slot-icon': {'width':'60px','height':'60px'},
        '.item-icon-count': {'right':'5px','bottom':'4px'},
        '#ItemIconBaseLayer_Unified': {'width':'62px','height':'62px'},
        '#ItemIconBaseLayer_Unified[13]': {'width':'52px','height':'52px','texturelayer-left':'5px','texturelayer-top':'5px','background-size':'52px 52px'},
        '#ItemIconBaseLayer_Unified[14]': {'width':'52px','height':'52px','texturelayer-left':'5px','texturelayer-top':'5px','background-size':'52px 52px'},
        '#ItemIconBaseLayer_Unified[15]': {'width':'52px','height':'52px','texturelayer-left':'5px','texturelayer-top':'5px','background-size':'52px 52px'},
        '#ItemIconBaseLayer_Unified[19]': {'width':'18px','height':'18px','texturelayer-left':'4px','texturelayer-top':'40px','background-size':'18px 18px'},
        '#ItemIconBaseLayer_Unified[20]': {'width':'15px','height':'28px','texturelayer-left':'4px','texturelayer-top':'4px','background-size':'15px 28px'},
        '#ItemIconBaseLayer_Unified[21]': {'texturelayer-left':'4px','texturelayer-bottom':'4px','background-size':'18px 18px'},
    }
    text=before.decode('utf-8-sig'); changes=[]
    for selector,values in edits.items():
        pattern=re.compile(r'(?m)^'+re.escape(selector)+r'\s*\{([^}]*)\}')
        matches=list(pattern.finditer(text)); assert len(matches)==1,(selector,len(matches))
        match=matches[0]; body=match[1]
        for key,value in values.items():
            prop=re.compile(r'(?<![\w-])'+re.escape(key)+r'\s*:\s*([^;]+);')
            pm=list(prop.finditer(body)); assert len(pm)==1,(selector,key)
            changes.append(dict(selector=selector,property=key,before=pm[0][1],after=value))
            body=prop.sub(lambda m:key+': '+value+';',body)
        text=text[:match.start(1)]+body+text[match.end(1):]
    after=(b'\xef\xbb\xbf' if before.startswith(b'\xef\xbb\xbf') else b'')+text.encode()
    assert len(after)<=len(before)
    after+=b' '*(len(before)-len(after))
    assert after.count(b'.item-icon-wrap { position: relative; width: 64px; height: 64px; }')==1
    assert b'width: 86px; height: 86px' not in after.splitlines()[0]
    return after,changes

def repair_special_icons(data):
    edits={
        '.item-icon-size.cpp-fold-group-item': {'width':'45px','height':'45px'},
        '#ItemIconBaseLayer_Unified.cpp-fold-group-item[13]': {'width':'45px','height':'45px','texturelayer-left':'9px','texturelayer-top':'9px','background-size':'45px 45px'},
        '#ItemIconBaseLayer_Unified.cpp-fold-group-item[14]': {'width':'45px','height':'45px','texturelayer-left':'9px','texturelayer-top':'9px','background-size':'45px 45px'},
        '.free-item-bg-unified': {'width':'64px','height':'64px'},
        '.free-item-bg-unified[0]': {'texturelayer-left':'-3px','texturelayer-top':'-3px','background-size':'70px 70px'},
        '.free-item-bg-unified[1]': {'texturelayer-left':'16px','texturelayer-top':'12px','background-size':'31px 40px'},
    }
    text=data.decode('utf-8-sig'); changes=[]
    for selector,values in edits.items():
        matches=list(re.finditer(r'(?m)^'+re.escape(selector)+r'\s*\{([^}]*)\}',text))
        assert len(matches)==1,(selector,len(matches))
        match=matches[0]; body=match[1]
        for key,value in values.items():
            prop=re.compile(r'(?<![\w-])'+re.escape(key)+r'\s*:\s*([^;]+);')
            pm=list(prop.finditer(body)); assert len(pm)==1,(selector,key)
            changes.append(dict(selector=selector,property=key,before=pm[0][1],after=value))
            body=prop.sub(lambda m:key+': '+value+';',body)
        text=text[:match.start(1)]+body+text[match.end(1):]
    after=(b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'')+text.encode()
    # The revision-2 asset has trailing padding available for edited declarations.
    after=after.rstrip(b' ')
    assert len(after)<=len(data)
    after+=b' '*(len(data)-len(after))
    # Category layers must fit inside the 62px base, and locks inside 64px slots.
    for selector,bounds in [(s,(62,62)) for s in edits if 'Unified.cpp-fold' in s]:
        props=edits[selector]
        assert int(props['width'][:-2])+int(props['texturelayer-left'][:-2])<=bounds[0]
        assert int(props['height'][:-2])+int(props['texturelayer-top'][:-2])<=bounds[1]
    assert 16+31<=64 and 12+40<=64
    return after,changes

def repair_effects(before):
    rules={
        '.list-item-hover-bg.square-middle': (79,58),
        '.list-item-focus-bg.square-middle': (83,61),
        '.list-item-focus-effect-line': (84,62),
    }
    after=before; edits=[]
    for selector,(old,new) in rules.items():
        pattern=re.compile(rb'(?m)^'+re.escape(selector.encode())+rb'\s*\{[^}]*\}')
        matches=list(pattern.finditer(after)); assert len(matches)==1,selector
        m=matches[0]; rule=m[0]
        for key in ['width','height']:
            needle=f'{key}: {old}px;'.encode(); replacement=f'{key}: {new}px;'.encode()
            assert rule.count(needle)==1,(selector,key)
            rule=rule.replace(needle,replacement)
            edits.append(dict(selector=selector,property=key,before=f'{old}px',after=f'{new}px'))
        after=after[:m.start()]+rule+after[m.end():]
        assert 0<new<=62
    assert len(after)==len(before)
    # Only the six dimension values change. Other effect shapes retain their rules.
    assert sum(a!=b for a,b in zip(before,after))==12
    for shape in ['square-small','square-large','circle-middle']:
        p=re.compile(rb'(?m)^\.list-item-hover-bg\.'+shape.encode()+rb'\s*\{[^}]*\}')
        assert p.findall(before)==p.findall(after)
    return after,edits

def fit_rows(path,data):
    if path.endswith('.uibinary'):
        needle=sized('column')+sized('8')+sized('row')+sized('9')
        expected=1 if 'inventoryequipmentpanel_game' in path else 2
        assert data.count(needle)==expected,(path,data.count(needle))
        changed=data.replace(needle,sized('column')+sized('8')+sized('row')+sized('11'))
        if 'inventoryequipmentpanel_game' in path:
            folded=sized('column')+sized('1')+sized('row')+sized('8')
            assert changed.count(folded)==1
            changed=changed.replace(folded,sized('column')+sized('1')+sized('row')+sized('11'))
        restored=changed.replace(sized('column')+sized('8')+sized('row')+sized('11'),needle)
        if 'inventoryequipmentpanel_game' in path:
            restored=restored.replace(sized('column')+sized('1')+sized('row')+sized('11'),folded)
        assert restored==data,'Layout changes must reverse byte-exactly'
        return changed
    if path.endswith('.thtml'):
        assert data.count(b'column="8" row="9"')==2
        return data.replace(b'column="8" row="9"',b'column="8" row="11"')
    if path.endswith('/itemicon.css'):
        after=data
        for selector in [b'.item-icon-wrap',b'.free-item-bg-unified']:
            pattern=re.compile(rb'(?m)(?:^|\xef\xbb\xbf)'+re.escape(selector)+rb'\s*\{[^}]*\}')
            matches=list(pattern.finditer(after));assert len(matches)==1
            m=matches[0];assert m[0].count(b'height: 64px;')==1
            rule=m[0].replace(b'height: 64px;',b'height: 62.5px;')
            after=after[:m.start()]+rule+after[m.end():]
        after=after.rstrip(b' ')
        if len(after)<=len(data):after+=b' '*(len(data)-len(after))
        return after
    return data

INVENTORY_PATHS = (
    'ui/bin__/inventoryequipmentpanel_game.uibinary',
    'ui/bin__/inventory2_game.uibinary',
    'ui/bin__/inventory2_component_game.uibinary',
    'ui/xml/gamemain/template/inventory2.thtml',
    'ui/xml/gamemain/title/itemicon.css',
    'ui/bin__/warehouseview2_game.uibinary',
    'ui/xml/gamemain/template/itemlist.css',
)

def transform(path, before):
    if path.endswith('.uibinary'):
        count = 1 if 'inventoryequipmentpanel_game' in path else 2
        old = sized('column') + sized('6') + sized('row') + sized('8')
        new = sized('column') + sized('8') + sized('row') + sized('9')
        assert before.count(old) == count, (path, before.count(old))
        after = before.replace(old, new)
        assert after.replace(new, old) == before
        if 'warehouseview2' in path:
            for row in ('2', '4'):
                other = sized('column') + sized('6') + sized('row') + sized(row)
                assert before.count(other) == after.count(other) > 0
        return fit_rows(path, after)
    if path.endswith('.thtml'):
        old, new = b'column="6" row="8"', b'column="8" row="9"'
        assert before.count(old) == 2
        after = before.replace(old, new)
        assert after.replace(new, old) == before
        return fit_rows(path, after)
    if path.endswith('/itemicon.css'):
        after, _ = change_css(before)
        after, _ = repair_special_icons(after)
        return fit_rows(path, after)
    if path.endswith('/itemlist.css'):
        return repair_effects(before)[0]
    raise ValueError('Unsupported inventory asset: ' + path)
