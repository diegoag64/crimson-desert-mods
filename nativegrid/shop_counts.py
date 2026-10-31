"""Audit the native helper and owner scope for recycled buy-card stock labels."""
import struct
from .pe import PE, audit_method


def audit_runtime(exe, pins):
    pe = PE(exe)
    audit_method(exe, pins['remove_property'])
    for name in ('description', 'list', 'root'):
        vt = pins[name+'_vtable']
        locator = struct.unpack_from('<Q', exe, pe.raw(vt['rva']-8))[0] - pe.base
        td = struct.unpack_from('<I', exe, pe.raw(locator)+12)[0]
        expected = vt['type'].encode('ascii') + b'\0'
        start = pe.raw(td)+16
        if exe[start:start+len(expected)] != expected:
            raise ValueError('Shop count owner differs from audit: ' + name)
    init = pins['negative_atom_initializer']
    audit_method(exe, init)
    raw = pe.raw(init['rva'])
    # Initializer loads the class name into RDX and atom storage into RCX.
    if exe[raw:raw+3] != b'\x48\x8d\x15' or exe[raw+13:raw+16] != b'\x48\x8d\x0d':
        raise ValueError('Shop requirement atom initializer changed')
    name_rva = init['rva']+7+struct.unpack_from('<i', exe, raw+3)[0]
    atom_rva = init['rva']+20+struct.unpack_from('<i', exe, raw+16)[0]
    expected = b'font-text-sub-red-negative\0'
    start = pe.raw(name_rva)
    if atom_rva != pins['negative_atom_rva'] or exe[start:start+len(expected)] != expected:
        raise ValueError('Shop requirement atom differs from audit')
