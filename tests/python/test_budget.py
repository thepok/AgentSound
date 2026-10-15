import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import drummer  # noqa: E402
from agentsound.budget import Budget  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


class TestBudget(unittest.TestCase):
    def test_zero_disabled_or_unlimited(self):
        for zero, allowed in [('disabled', False), ('unlimited', True)]:
            bud = Budget({'fill': 0}, zero=zero).book(8, 'fill')
            self.assertEqual(bud.allows(8, 'fill'), allowed)
            self.assertFalse(bud.allows(8, 'missing'))
        self.assertFalse(Budget({'fill': 0}).allows(8, 'fill'))
        with self.assertRaises(ComposeError):
            Budget(zero='unknown')

    def test_unlimited_keeps_other_rules(self):
        bud = Budget({'flash': 0}, zero='unlimited', same=('flash',), same_every=16,
                     min_score={'flash': 2}, phrase_gap={'flash': 1}).book(8, 'flash', 'slide', 2)
        self.assertFalse(bud.allows(8, 'flash', 'slide', score=2, phrase=4))
        self.assertFalse(bud.allows(8, 'flash', 'pop', score=1, phrase=4))
        self.assertFalse(bud.allows(8, 'flash', 'pop', score=2, phrase=3))
        self.assertTrue(bud.allows(8, 'flash', 'pop', score=2, phrase=4))

    def test_exact_spacing_boundaries_in_both_directions(self):
        bud = Budget({'fill': 32, 'flash': 16}, same=('flash',), same_every=32)
        bud.book(64, 'fill').book(64, 'flash', 'slide')
        for cls, name, gap in [('fill', None, 32), ('flash', 'pop', 16), ('flash', 'slide', 32)]:
            for direction in (-1, 1):
                at = 64 + direction * gap
                self.assertTrue(bud.allows(at, cls, name))
                self.assertTrue(bud.allows(at - direction * 0.5e-6, cls, name))
                self.assertFalse(bud.allows(at - direction * 2e-6, cls, name))

    def test_unlimited_keep_books_and_respects_slots(self):
        bud = Budget({'fill': 0}, zero='unlimited')
        cands = [dict(t=8, cls='fill', name='run', score=2, slot=(0,)),
                 dict(t=8, cls='fill', name='octave', score=1, slot=(0,)),
                 dict(t=8, cls='fill', name='run', score=1, slot=(1,))]
        self.assertEqual(bud.keep(cands), [cands[0], cands[2]])
        self.assertEqual(bud.count('fill'), 2)

    def test_drummer_zero_spacing_and_structural_bypass(self):
        cands = [dict(t=8, score=2, structural=True), dict(t=9, score=1, structural=False)]
        for spacing, expected in [(0, cands), (4, cands[:1])]:
            bud = drummer._fill_budget(drummer.Memory().played(7, 'snare'), 4, spacing, 0, 16)
            kept, refused = drummer._budget(cands, bud, 0, spacing)
            self.assertEqual(kept, expected)
            self.assertEqual(refused, cands[len(expected):])
            self.assertFalse(bud.allows(8, 'flashy', 'toms'))
