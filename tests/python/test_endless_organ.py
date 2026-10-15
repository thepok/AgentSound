"""The endless 'organ' genre (agentsound/endless/organ.py): the genre data, every texture built, the organ tells and
score - notes only, no audio."""
import unittest

from agentsound import endless
from agentsound.endless import composer, genres, organ
from agentsound.theory import ComposeError


class OrganGenre(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('organ').validate()
        cls.made = {}
        for feel in cls.g.feels:
            mood = next(m for m, d in cls.g.moods.items() if feel in d['feels'])
            t = composer.compose(cls.g, 7, mood=mood, plan={'feel': feel})
            cls.made[feel] = (t, endless.song(t))

    def test_every_feel_builds_its_textures(self):
        for feel, (t, s) in self.made.items():
            self.assertEqual(t.feel, feel)
            tex = {r['texture'] for r in s.organ_plan}
            want = {sd['texture'] for sd in self.g.plan['arrangements'][feel]}
            self.assertEqual(tex, want, feel)
            self.assertTrue(s.organ_voices, feel)
            # registration contrast: at least two registrations or a swell lane
            regs = {r['reg'] for r in s.organ_plan}
            lanes = any(a.target == 'instrument.expression' for tr in s.tracks.values()
                        for a in getattr(tr, 'automation', []) or [])
            self.assertTrue(len(regs) > 1 or lanes, feel)
            self.assertTrue(s.compile()['analysis']['registration'], feel)

    def test_deterministic(self):
        t, s = self.made['chorale']
        s2 = endless.song(composer.compose(self.g, 7, mood=t.mood, plan={'feel': 'chorale'}))
        for name, tr in s.tracks.items():
            self.assertEqual([tuple(n) for n in tr.notes], [tuple(n) for n in s2.tracks[name].notes], name)

    def test_tells_and_score(self):
        for feel, (t, s) in self.made.items():
            m = organ.organ_metrics(s, t)
            self.assertLessEqual(set(genres.SCORES['organ']), set(m), feel)
            r = composer.score(s, t, self.g)
            self.assertEqual(r['style'], 'organ')
            self.assertFalse(r['missing'], feel)
            self.assertTrue(0 <= r['score'] <= 100)
        # the voice leading of the chorale verses: (almost) no parallels
        t, s = self.made['chorale']
        self.assertLessEqual(organ.organ_metrics(s, t)['par58'], 1.0)

    def test_plan_validation(self):
        bad = self.g.but(plan=dict(self.g.plan, arrangements=dict(self.g.plan['arrangements'])))
        bad.plan['arrangements']['trio'] = [dict(name='x', part='A1', texture='trio', reg={'plenum': 1.0})]
        with self.assertRaises(ComposeError):                 # plenum has no solo / acc manual for a trio
            bad.validate()
        bad.plan['arrangements']['trio'] = [dict(name='x', part='A1', texture='nope', reg={'trio': 1.0})]
        with self.assertRaises(ComposeError):
            bad.validate()

    def test_the_other_genres_keep_their_perform(self):
        for name, g in genres.GENRES.items():
            if name != 'organ':
                self.assertNotEqual(g.plan.get('perform'), 'organ')
                g.validate()


if __name__ == '__main__':
    unittest.main()
