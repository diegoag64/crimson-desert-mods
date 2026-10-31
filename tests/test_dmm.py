import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from nativegrid.dmm import export_package


class DmmExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.package = self.root / 'source'
        self.package.mkdir()
        (self.package / 'licenses').mkdir()
        for name in ('MinHook.txt', 'CDUMM.txt'):
            (self.package / 'licenses' / name).write_text('test notice ' + name)
        self.manifest = dict(schema=1, revision=41, fixture_tests_passed=10,
                             game_build='fixture', exe_sha256='fixture', files=[])
        for name in ('NativeGrid.asi', 'winmm.dll', 'winmm.ini'):
            data = b'fixture ' + name.encode()
            (self.package / name).write_bytes(data)
            self.manifest['files'].append(dict(name=name, sha256=hashlib.sha256(data).hexdigest()))
        self.save()

    def save(self):
        (self.package / 'manifest.json').write_text(json.dumps(self.manifest))

    def test_exact_export_and_reproducibility(self):
        # A scratch file must never leak into the import or become a companion.
        (self.package / 'secret-local.json').write_text('private fixture')
        first = export_package(self.package, self.root / 'first')
        second = export_package(self.package, self.root / 'second')
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as z:
            self.assertEqual(set(z.namelist()), {
                'NativeGrid/NativeGrid.asi', 'NativeGrid/NativeGrid-README.txt',
                'NativeGrid/NativeGrid-license-MinHook.txt',
                'NativeGrid/NativeGrid-license-CDUMM.txt',
            })
            self.assertEqual(z.read('NativeGrid/NativeGrid.asi'),
                             (self.package / 'NativeGrid.asi').read_bytes())
        receipt = json.loads((first.parent / 'export-receipt.json').read_text())
        self.assertFalse(receipt['dmm_import_tested'])
        self.assertFalse(receipt['dmm_runtime_coexistence_tested'])

    def test_tampered_plugin_or_loader_refused(self):
        for name in ('NativeGrid.asi', 'winmm.dll', 'winmm.ini'):
            with self.subTest(name=name):
                path = self.package / name
                original = path.read_bytes()
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    export_package(self.package, self.root / 'bad')
                self.assertFalse((self.root / 'bad').exists())
                path.write_bytes(original)

    def test_failed_or_untested_revision_refused(self):
        for revision, count in ((40, 10), (41, 9)):
            self.manifest.update(revision=revision, fixture_tests_passed=count)
            self.save()
            with self.assertRaises(ValueError):
                export_package(self.package, self.root / 'bad')

    def test_manifest_cannot_add_or_traverse_files(self):
        self.manifest['files'][0]['name'] = '../unexpected.asi'
        self.save()
        with self.assertRaisesRegex(ValueError, 'three standalone'):
            export_package(self.package, self.root / 'bad')

    def test_preserve_source_and_existing_output(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            export_package(self.package, self.package / 'nested')
        export_package(self.package, self.root / 'out')
        with self.assertRaises(FileExistsError):
            export_package(self.package, self.root / 'out')

    def test_missing_notice_refused_before_output(self):
        (self.package / 'licenses' / 'MinHook.txt').unlink()
        with self.assertRaises(FileNotFoundError):
            export_package(self.package, self.root / 'bad')
        self.assertFalse((self.root / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
