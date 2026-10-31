"""Publication policy checks using synthetic bytes, without game resources."""
import unittest

from scripts.audit_publication import audit_file


class PublicationChecks(unittest.TestCase):
    def test_documentation_image_signatures(self):
        # These are signature fixtures, not decodable images. The publication
        # audit classifies file types; visual review checks image contents.
        samples = {
            'png': b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\x00IEND\xaeB`\x82',
            'jpg': b'\xff\xd8\xff\xff\xd9',
            'jpeg': b'\xff\xd8\xff\xff\xd9',
            'webp': b'RIFF\x04\x00\x00\x00WEBP',
        }
        for suffix, data in samples.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(audit_file('docs/images/example.' + suffix, data), 'image')
                with self.assertRaises(SystemExit):
                    audit_file('research/example.' + suffix, data)
                with self.assertRaises(SystemExit):
                    audit_file('docs/images/example.' + suffix, b'MZnot an image')

    def test_large_and_empty_documentation_images_refused(self):
        for data in (b'', b'x' * (8 * 1024 * 1024 + 1)):
            with self.assertRaises(SystemExit):
                audit_file('docs/images/example.png', data)

    def test_other_binary_and_artifact_guards_remain(self):
        for name, data in (
            ('docs/images/plugin.asi', b'MZbinary'),
            ('docs/images/plugin.txt', b'\0binary'),
            ('research/notes.md', b'private notes'),
            ('docs/large.md', b'x' * 262145),
            ('docs/secret.md', b'-----BEGIN ' + b'PRIVATE KEY-----'),
        ):
            with self.subTest(name=name), self.assertRaises(SystemExit):
                audit_file(name, data)
        self.assertEqual(audit_file('docs/notes.md', b'Ordinary documentation.'), 'text')


if __name__ == '__main__':
    unittest.main()
