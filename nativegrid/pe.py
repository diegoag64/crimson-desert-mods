"""Read-only PE inspection and named package-worker resolution."""
import struct

class PE:
    def __init__(self, data):
        self.data = data
        if data[:2] != b'MZ': raise ValueError('Not PE')
        pe = struct.unpack_from('<I', data, 0x3c)[0]
        if data[pe:pe+4] != b'PE\0\0': raise ValueError('Bad PE signature')
        _, count, _, _, _, optional_size, _ = struct.unpack_from('<HHIIIHH', data, pe+4)
        optional = pe+24
        if struct.unpack_from('<H', data, optional)[0] != 0x20b: raise ValueError('Not PE32+')
        self.base = struct.unpack_from('<Q', data, optional+24)[0]
        self.sections = []
        for i in range(count):
            pos = optional+optional_size+i*40
            name, vsize, rva, rawsize, raw = struct.unpack_from('<8sIIII',data,pos)
            flags = struct.unpack_from('<I',data,pos+36)[0]
            self.sections.append(dict(name=name.rstrip(b'\0').decode('ascii'),rva=rva,
                                      vsize=vsize,raw=raw,rawsize=rawsize,flags=flags))

    def rva(self, raw):
        for s in self.sections:
            if s['raw'] <= raw < s['raw']+s['rawsize']: return raw-s['raw']+s['rva']
        raise ValueError('Raw offset outside section')

    def raw(self, rva):
        for s in self.sections:
            if s['rva'] <= rva < s['rva']+min(s['rawsize'],s['vsize']): return rva-s['rva']+s['raw']
        raise ValueError('RVA not backed by file')

    def section(self, rva):
        return next((s for s in self.sections if s['rva'] <= rva < s['rva']+s['vsize']), None)

def positions(data, needle):
    pos=data.find(needle)
    while pos>=0:
        yield pos
        pos=data.find(needle,pos+1)
def exported_rva(data,name):
    pe=PE(data); header=struct.unpack_from('<I',data,0x3c)[0]
    export_rva=struct.unpack_from('<I',data,header+24+112)[0]
    off=pe.raw(export_rva)
    values=struct.unpack_from('<IIHHIIIIIII',data,off)
    count=values[7]; funcs,names,ordinals=map(pe.raw,values[8:11])
    for i in range(count):
        n=pe.raw(struct.unpack_from('<I',data,names+i*4)[0])
        if data[n:data.index(0,n)].decode()==name:
            ordinal=struct.unpack_from('<H',data,ordinals+i*2)[0]
            return struct.unpack_from('<I',data,funcs+ordinal*4)[0]
    raise ValueError('Export missing')


def package_methods(data):
    """Derive slots 5 and 4 from the unique named primary RTTI table."""
    pe = PE(data)
    tables = set()
    for name_offset in positions(data, b'.?AVResourceLoadWorker_Package@pa@@\0'):
        type_rva = pe.rva(name_offset - 16)
        for reference in positions(data, struct.pack('<I', type_rva)):
            start = reference - 12
            if start < 0 or start + 24 > len(data):
                continue
            signature, offset, constructor, _, hierarchy, self_rva = struct.unpack_from('<6I', data, start)
            if signature != 1 or offset != 0 or constructor != 0:
                continue
            try:
                if pe.rva(start) != self_rva:
                    continue
                pe.raw(hierarchy)
            except ValueError:
                continue
            for pointer in positions(data, struct.pack('<Q', pe.base + self_rva)):
                if pointer + 56 > len(data):
                    continue
                methods = tuple(struct.unpack_from('<Q', data, pointer + 8 + slot * 8)[0] - pe.base for slot in (5, 4))
                if all((pe.section(rva) or {}).get('flags', 0) & 0x20000000 for rva in methods):
                    tables.add((pe.rva(pointer + 8), methods))
    if len(tables) != 1:
        raise ValueError('Named package-worker primary vtable is missing or ambiguous')
    return list(next(iter(tables))[1])
