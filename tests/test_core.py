"""Synthetic malformed-input and output-containment checks; no game assets."""
import struct
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nativegrid.archive import Pamt, checksum, safe_asset_path
from nativegrid.build import output_directory
from nativegrid.inventory import INVENTORY_PATHS, SELL_PATHS, transform, transform_sell, sized
from nativegrid.pe import PE, audit_method


def synthetic_index():
    def blob(data):
        return struct.pack('<I', len(data)) + data
    body = struct.pack('<III', 4, 0, 512)
    body += blob(b'\0\x02ui') + blob(b'\0\x04test')
    body += struct.pack('<I', 1) + struct.pack('<IiII', checksum(b'ui'), 0, 0, 1)
    body += struct.pack('<I', 1) + struct.pack('<IIIIHBB', 0, 32, 20, 50, 4, 0x32, 0)
    body += blob(b'.css\0')
    return struct.pack('<II', checksum(body), 1) + b'\x02\x04\0\0' + body


class ArchiveChecks(unittest.TestCase):
    def test_method_body_guard_rejects_changes_after_the_prefix(self):
        data = bytes(range(64))
        method = dict(rva=0, size=48, prefix=data[:24].hex(),
                      sha256=hashlib.sha256(data[:48]).hexdigest())
        with patch('nativegrid.pe.PE') as pe:
            pe.return_value.raw.side_effect = lambda rva: rva
            pe.return_value.section.return_value = dict(rva=0, vsize=64, rawsize=64, flags=0x20000000)
            audit_method(data, method)
            damaged = bytearray(data)
            damaged[30] ^= 1
            with self.assertRaises(ValueError):
                audit_method(damaged, method)
            with self.assertRaises(ValueError):
                audit_method(data, dict(method, size=65))
            pe.return_value.section.return_value['flags'] = 0x40000000
            with self.assertRaises(ValueError):
                audit_method(data, method)

    def test_sell_grid_preserves_other_layouts_and_handlers(self):
        old = sized('column') + sized('6') + sized('row') + sized('8')
        other = sized('column') + sized('6') + sized('row') + sized('4')
        before = sized('native_sell_handler') + old + other
        after = transform_sell(SELL_PATHS[0], before)
        self.assertEqual(after, sized('native_sell_handler') + sized('column') + sized('8') + sized('row') + sized('11') + other)
        for bad in (other, old + old):
            with self.assertRaises(AssertionError):
                transform_sell(SELL_PATHS[0], bad)

    def test_sell_source_changes_only_inventory_override(self):
        before = b'<override selector="#InventoryItemList" script="native_sell" inventory-key="Character"></override><override selector="#Other" column="6" row="8"></override>'
        after = transform_sell(SELL_PATHS[1], before)
        self.assertEqual(after.replace(b' column="8" row="11"', b'', 1), before)
        with self.assertRaises(AssertionError):
            transform_sell(SELL_PATHS[1], after)

    def test_valid_synthetic_entry(self):
        entry, = Pamt.parse(synthetic_index()).entries()
        self.assertEqual((entry.path, entry.offset, entry.stored, entry.original, entry.chunk, entry.flags),
                         ('ui/test.css', 32, 20, 50, 4, 0x32))

    def test_corrupt_body_and_truncation_refused(self):
        data = synthetic_index()
        damaged = data[:-1] + bytes([data[-1] ^ 1])
        for candidate in (damaged, data[:9], data[:-8]):
            with self.subTest(length=len(candidate)), self.assertRaises(ValueError):
                Pamt.parse(candidate)

    def test_asset_path_traversal_refused(self):
        for path in ('../file', 'ui/../../file', 'ui//file', 'C:/file', 'ui\\file', '/file'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                safe_asset_path(path)

    def test_bad_pe_refused(self):
        with self.assertRaises(ValueError):
            PE(b'not an executable')

    def test_unexpected_assets_fail_closed(self):
        for path in INVENTORY_PATHS:
            with self.subTest(path=path), self.assertRaises(AssertionError):
                transform(path, b'changed unsupported asset')
        with self.assertRaises(ValueError):
            transform('unrelated.txt', b'data')

    def test_build_cannot_write_in_game(self):
        base = Path(__file__).resolve().parents[1] / 'build'
        base.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=base) as folder:
            game = Path(folder) / 'game'
            game.mkdir()
            for target in (game, game / 'output', game.parent):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    output_directory(target, game)
            self.assertFalse((game / 'output').exists())


if __name__ == '__main__':
    unittest.main()
