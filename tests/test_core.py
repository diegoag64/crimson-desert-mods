"""Synthetic malformed-input and output-containment checks; no game assets."""
import struct
import tempfile
import unittest
from pathlib import Path

from nativegrid.archive import Pamt, checksum, safe_asset_path
from nativegrid.build import output_directory
from nativegrid.inventory import INVENTORY_PATHS, transform
from nativegrid.pe import PE


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
