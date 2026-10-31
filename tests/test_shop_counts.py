import hashlib
import struct
import unittest
from unittest.mock import patch
from nativegrid.shop_counts import audit_runtime


class ShopCountAuditChecks(unittest.TestCase):
    def fixture(self):
        data = bytearray(4096)
        data[64:112] = bytes(range(48))
        data[128:153] = bytes.fromhex('488d15') + struct.pack('<i', 256-135) + bytes.fromhex('41b801000000488d0d') + struct.pack('<i', 384-148) + bytes.fromhex('e900000000')
        name = b'font-text-sub-red-negative\0'
        data[256:256+len(name)] = name
        pins = {'negative_atom_rva': 384}
        for key, rva, size in [('remove_property', 64, 48), ('negative_atom_initializer', 128, 25)]:
            pins[key] = dict(rva=rva, size=size, prefix=data[rva:rva+24].hex(), sha256=hashlib.sha256(data[rva:rva+size]).hexdigest())
        for i, owner in enumerate(('description','list','root')):
            vt, col, td = 512+i*512, 576+i*512, 640+i*512
            text = '.?AV'+owner+'@@'
            pins[owner+'_vtable'] = dict(rva=vt, type=text)
            struct.pack_into('<Q', data, vt-8, 0x140000000+col)
            struct.pack_into('<I', data, col+12, td)
            data[td+16:td+17+len(text)] = text.encode()+b'\0'
        return data, pins

    def audit(self, data, pins):
        with patch('nativegrid.shop_counts.PE') as pe, patch('nativegrid.pe.PE') as method_pe:
            for mock in (pe, method_pe):
                mock.return_value.base = 0x140000000
                mock.return_value.raw.side_effect = lambda rva: rva
                mock.return_value.section.return_value = dict(flags=0x60000020, rva=0, rawsize=len(data), vsize=len(data))
            audit_runtime(data, pins)

    def test_audited_helper_owners_and_requirement_atom(self):
        self.audit(*self.fixture())

    def test_body_changes_beyond_prologue_are_rejected(self):
        for key in ('remove_property','negative_atom_initializer'):
            data, pins = self.fixture()
            data[pins[key]['rva']+24] ^= 1
            with self.assertRaises(ValueError):
                self.audit(data, pins)

    def test_wrong_owner_type_is_rejected(self):
        for owner in ('description','list','root'):
            data, pins = self.fixture()
            pins[owner+'_vtable']['type'] += 'Wrong'
            with self.assertRaises(ValueError):
                self.audit(data, pins)

    def test_requirement_atom_address_and_name_are_checked(self):
        data, pins = self.fixture()
        pins['negative_atom_rva'] += 4
        with self.assertRaises(ValueError):
            self.audit(data, pins)
        data, pins = self.fixture()
        data[256] = ord('X')
        with self.assertRaises(ValueError):
            self.audit(data, pins)

    def test_valid_body_hash_cannot_mask_wrong_initializer_instructions(self):
        data, pins = self.fixture()
        data[128] = 0
        init = pins['negative_atom_initializer']
        init['prefix'] = data[128:152].hex()
        init['sha256'] = hashlib.sha256(data[128:153]).hexdigest()
        with self.assertRaises(ValueError):
            self.audit(data, pins)
