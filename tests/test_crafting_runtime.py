import hashlib
import struct
import unittest
from unittest.mock import patch

from nativegrid.crafting import audit_runtime


class CraftingRuntimeChecks(unittest.TestCase):
    def fixture(self):
        data = bytearray(4096)
        pins = {'methods': {}}
        for i, name in enumerate(('layout', 'background_size', 'background_position')):
            rva = 64 + i*64
            body = bytes(range(48))
            data[rva:rva+len(body)] = body
            pins['methods'][name] = dict(rva=rva, size=len(body), prefix=body[:24].hex(),
                                        sha256=hashlib.sha256(body).hexdigest())
        for i, name in enumerate(('description', 'card', 'list', 'root')):
            vt, locator, td = 512+i*512, 576+i*512, 640+i*512
            text = '.?AV' + name + '@@'
            pins[name+'_vtable'] = dict(rva=vt, type=text)
            struct.pack_into('<Q', data, vt-8, 0x140000000+locator)
            struct.pack_into('<I', data, locator+12, td)
            data[td+16:td+17+len(text)] = text.encode()+b'\0'
        return data, pins

    def audit(self, data, pins, flags=0x60000020):
        with patch('nativegrid.crafting.PE') as pe:
            pe.return_value.base = 0x140000000
            pe.return_value.raw.side_effect = lambda rva: rva
            pe.return_value.section.return_value = {'flags': flags}
            audit_runtime(data, pins)

    def test_audited_layout_helpers_and_owners(self):
        self.audit(*self.fixture())

    def test_changes_after_prologue_are_rejected(self):
        for name in ('layout', 'background_size', 'background_position'):
            with self.subTest(method=name):
                data, pins = self.fixture()
                data[pins['methods'][name]['rva']+30] ^= 1
                with self.assertRaisesRegex(ValueError, name):
                    self.audit(data, pins)

    def test_short_prefix_and_non_executable_methods_are_rejected(self):
        for name in ('layout', 'background_size', 'background_position'):
            data, pins = self.fixture()
            pins['methods'][name]['prefix'] = pins['methods'][name]['prefix'][:-2]
            with self.assertRaises(ValueError):
                self.audit(data, pins)
        with self.assertRaises(ValueError):
            self.audit(*self.fixture(), flags=0x40000040)

    def test_all_owner_types_are_guarded(self):
        for i, name in enumerate(('description', 'card', 'list', 'root')):
            data, pins = self.fixture()
            data[640+i*512+16] ^= 1
            with self.assertRaisesRegex(ValueError, name):
                self.audit(data, pins)


if __name__ == '__main__':
    unittest.main()
