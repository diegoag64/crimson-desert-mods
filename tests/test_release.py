import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from nativegrid.release import ROOT, check_privacy, digest, expected_payloads, export_package, validation_for


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root/'package'
        self.package.mkdir()
        support = json.loads((ROOT/'nativegrid/builds/26345091.json').read_text())
        records = [dict(path=p, **r) for p, r in expected_payloads(support).items()]
        self.manifest = dict(revision=42, release_patches=True, payloads=records,
                             files=[dict(name='NativeGrid.asi', sha256=digest(b'MZfixture only'))])
        for key in ('game_build', 'exe_sha256', 'master_sha256', 'pamt_sha256'):
            self.manifest[key] = support[key]
        (self.package/'NativeGrid.asi').write_bytes(b'MZfixture only')
        self.write('manifest.json', self.manifest)
        self.write('patch-report.json', records)
        for name, count in [('fixture-results.json', 10), ('release-fixture-results.json', 12)]:
            self.write(name, [dict(case=str(i), passed=True) for i in range(count)])
        self.write('patch-fixture-results.json', dict(passed=True, output='PASS: 330 native patch checks across 30 resources'))

    def write(self, name, value):
        (self.package/name).write_text(json.dumps(value))

    def test_exact_archive_and_reproducible_export(self):
        first = export_package(self.package, self.root/'out1')
        second = export_package(self.package, self.root/'out2')
        self.assertEqual(first.read_bytes(), second.read_bytes())
        with zipfile.ZipFile(first) as archive:
            self.assertEqual(len(archive.namelist()), 6)
            self.assertFalse(any(n.endswith(('.dll', '.exe', '.h', '.log')) for n in archive.namelist()))
            self.assertEqual(archive.read('NativeGrid/NativeGrid.asi'), b'MZfixture only')
            self.assertIn(b'MIT License', archive.read('NativeGrid/NativeGrid-LICENSE.txt'))
        with self.assertRaises(FileExistsError):
            export_package(self.package, self.root/'out1')

    def test_legacy_package_refused(self):
        self.manifest['revision'] = 41
        self.write('manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'portable revision 42'):
            export_package(self.package, self.root/'out')

    def test_changed_plugin_refused(self):
        (self.package/'NativeGrid.asi').write_bytes(b'MZchanged')
        with self.assertRaisesRegex(ValueError, 'integrity'):
            export_package(self.package, self.root/'out')

    def test_resource_mismatch_refused(self):
        self.manifest['payloads'][0]['replacement_sha256'] = '0'*64
        self.write('manifest.json', self.manifest)
        with self.assertRaisesRegex(ValueError, 'Resource hash'):
            export_package(self.package, self.root/'out')

    def test_missing_fixture_refused(self):
        self.write('release-fixture-results.json', [])
        with self.assertRaisesRegex(ValueError, 'fixtures'):
            export_package(self.package, self.root/'out')

    def test_private_paths_rejected(self):
        value = 'C:' + '\\Users\\example\\build'
        for data in (value.encode(), value.encode('utf-16-le'), b'x'+value.encode('utf-16-le')):
            with self.assertRaisesRegex(ValueError, 'Personal build path'):
                check_privacy(data)

    def test_output_cannot_modify_build(self):
        with self.assertRaisesRegex(ValueError, 'separate'):
            export_package(self.package, self.package/'export')

    def test_live_evidence_requires_exact_binary(self):
        record = json.loads((ROOT/'nativegrid/release_validation.json').read_text())
        self.assertTrue(validation_for(record['plugin_sha256'])['live_tested'])
        self.assertIsNone(validation_for('0'*64))

    def test_unvalidated_export_keeps_pending_status(self):
        archive = export_package(self.package, self.root/'pending')
        with zipfile.ZipFile(archive) as z:
            metadata = json.loads(z.read('NativeGrid/NativeGrid-release.json'))
            self.assertFalse(metadata['live_tested'])
            self.assertIsNone(metadata['live_validation'])
