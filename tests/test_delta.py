import random
import unittest
from nativegrid.delta import make_patch, apply_patch, emit_payloads


class DeltaTests(unittest.TestCase):
    def test_realistic_insert_delete_and_move(self):
        rng = random.Random(42)
        before = rng.randbytes(20000)
        variants = [before[:300] + b'new styles' + before[300:], before[900:] + before[:400],
                    before[:100] + bytes(400) + before[500:], b'new', before * 2]
        for after in variants:
            ops, residuals = make_patch(before, after)
            self.assertEqual(apply_patch(before, ops, residuals, len(after)), after)

    def test_residuals_depend_on_original(self):
        before, after = b'original', b'replacement'
        ops, residuals = make_patch(before, after)
        self.assertNotEqual(residuals, after)
        self.assertEqual(apply_patch(before, ops, residuals, len(after)), after)

    def test_repeated_runs_and_short_inputs(self):
        for before, after in [(b'x', b'abc'), (b'ab' * 10000, b'ab' * 8000 + b'new'), (bytes(500), bytes(700))]:
            ops, residuals = make_patch(before, after)
            self.assertEqual(apply_patch(before, ops, residuals, len(after)), after)

    def test_bounds_rejected(self):
        for ops in [[(0, 5, 1)], [(1, 1, 1)], [(2, 0, 1)], [(0, -1, 1)], [(0, 0, 0)], [(0, 0, 4)], []]:
            with self.assertRaises(ValueError):
                apply_patch(b'abc', ops, b'x', 2)

    def test_emit_has_digests_and_no_complete_resources(self):
        header, report = emit_payloads([('fixture', b'original source', b'modified destination')])
        self.assertNotIn('before_0[]', header)
        self.assertNotIn('after_0[]', header)
        self.assertEqual(len(report[0]['original_sha256']), 64)

    def test_empty_resource_rejected(self):
        for before, after in [(b'', b'a'), (b'a', b'')]:
            with self.assertRaises(ValueError):
                make_patch(before, after)
