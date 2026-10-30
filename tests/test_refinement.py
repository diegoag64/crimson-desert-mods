import unittest
import struct
from unittest.mock import patch

from nativegrid.inventory import sized
from nativegrid.refinement import REFINEMENT_PATHS, transform, audit_runtime


class RefinementChecks(unittest.TestCase):
    def test_binary_changes_only_owned_gear_list(self):
        def attrs(owner):
            return (sized('column') + sized('1') + sized('row') + sized('4') +
                    sized('selector-show-layer-list') + sized(owner))
        gear = attrs('#InventoryContent')
        material = attrs('#IngredientContentList')
        before = b'prefix' + material + gear + b'native-handler'
        after = transform(REFINEMENT_PATHS[0], before)
        self.assertEqual(len(before), len(after))
        self.assertEqual(sum(a != b for a, b in zip(before, after)), 1)
        self.assertIn(material, after)
        self.assertTrue(after.endswith(b'native-handler'))
        for invalid in (material, gear + gear):
            with self.assertRaises(ValueError):
                transform(REFINEMENT_PATHS[0], invalid)

    def test_source_preserves_materials_and_handlers(self):
        before = (b'<widget id="IngredientContentList" column="1" row="4"></widget>'
                  b'<widget id="InventoryContent" script="native" column="1" row="4" '
                  b'filter-type="MultiChangeMaterial" selector-show-layer-list="#InventoryContent"></widget>')
        after = transform(REFINEMENT_PATHS[1], before)
        self.assertEqual(after.replace(b'column="3"', b'column="1"'), before)
        for invalid in (b'', before + before, before.replace(b'column="1"', b'column="2"')):
            with self.assertRaises(ValueError):
                transform(REFINEMENT_PATHS[1], invalid)

    def test_css_keeps_existing_rules_and_fixed_read_size(self):
        original = b'#Existing { width: 40px; } /* reserve space */' + b' ' * 3000
        result = transform(REFINEMENT_PATHS[2], original)
        self.assertEqual(len(result), len(original))
        self.assertIn(b'#Existing{width:40px;}', result)
        with self.assertRaises(ValueError):
            transform(REFINEMENT_PATHS[2], b'#Existing{width:40px;}')

    def runtime_fixture(self):
        data = bytearray(4096)
        pins = {'hidden_atom_rva': 2048, 'methods': {}}
        for i, name in enumerate(('refresh', 'add_class', 'sort_classes')):
            rva = 64 + 32*i
            pins['methods'][name] = {'rva': rva, 'prefix': bytes(range(24)).hex()}
            data[rva:rva+24] = bytes(range(24))
        for i, name in enumerate(('description', 'list', 'root')):
            vt, locator, td = 256+i*512, 320+i*512, 384+i*512
            pins[name+'_vtable'] = {'rva': vt, 'type': '.?AV' + name + '@@'}
            struct.pack_into('<Q', data, vt-8, 0x140000000+locator)
            struct.pack_into('<I', data, locator+12, td)
            text = pins[name+'_vtable']['type'].encode() + b'\0'
            data[td+16:td+16+len(text)] = text
        return data, pins

    def run_audit(self, data, pins):
        # Synthetic PE mapping isolates the fingerprint/RTTI guard from PE parsing.
        with patch('nativegrid.refinement.PE') as pe:
            pe.return_value.base = 0x140000000
            pe.return_value.section.return_value = {"flags": 0xc0000040}
            pe.return_value.raw.side_effect = lambda rva: rva
            audit_runtime(data, pins)

    def test_runtime_accepts_all_audited_types_and_method(self):
        self.run_audit(*self.runtime_fixture())

    def test_runtime_rejects_changed_method_and_short_pin(self):
        for i, name in enumerate(('refresh', 'add_class', 'sort_classes')):
            with self.subTest(name=name):
                data, pins = self.runtime_fixture()
                data[64+32*i] ^= 1
                with self.assertRaisesRegex(ValueError, 'method fingerprint'):
                    self.run_audit(data, pins)
                data, pins = self.runtime_fixture()
                pins['methods'][name]['prefix'] = pins['methods'][name]['prefix'][:-2]
                with self.assertRaisesRegex(ValueError, 'method fingerprint'):
                    self.run_audit(data, pins)

    def test_runtime_rejects_each_changed_native_owner_type(self):
        for i, name in enumerate(('description', 'list', 'root')):
            with self.subTest(name=name):
                data, pins = self.runtime_fixture()
                data[384+i*512+16] ^= 1
                with self.assertRaisesRegex(ValueError, name):
                    self.run_audit(data, pins)

    def test_runtime_rejects_atom_outside_writable_image_data(self):
        data, pins = self.runtime_fixture()
        for section in (None, {'flags': 0x40000040}):
            with patch('nativegrid.refinement.PE') as pe:
                pe.return_value.raw.side_effect = lambda rva: rva
                pe.return_value.section.return_value = section
                with self.assertRaisesRegex(ValueError, 'writable image data'):
                    audit_runtime(data, pins)


if __name__ == '__main__':
    unittest.main()
