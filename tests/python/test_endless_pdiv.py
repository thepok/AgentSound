"""Round p-div's PIANO_DIVERSE for endless new-age piano (genres.piano_diverse): off is the code before it (the same
notes), on draws the anti-template choices per piece (perform._diverse: the climax's left hand, the peak's place and
kind, the ending gesture, the interlude from the theme) and run.candidates plays the near-tie most different from the
set so far (run.diverse_pick: the score a gate)."""
import hashlib
import json
import pathlib
import sys
import types
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import pianist  # noqa: E402
from agentsound.endless import composer, genres, perform, run  # noqa: E402

NEW_AGE = genres.get('new-age-piano').validate()
ARGS = types.SimpleNamespace(mood=None, swing=None)


def _song(seed, plan=None):
    tune = composer.compose(NEW_AGE, seed, plan=plan)
    return tune, perform.build(tune, NEW_AGE)


def _hash(song):
    notes = sorted((tr, round(n.start, 6), n.pitch, n.vel, round(n.dur, 6)) for tr, t in song.tracks.items()
                   for n in getattr(t, '_notes', ()))
    return hashlib.sha1(json.dumps(notes).encode()).hexdigest()


class PianoDiverse(unittest.TestCase):
    def tearDown(self):
        genres.piano_diverse(False)

    def test_off_by_default_and_restored(self):
        self.assertIsNone(perform.PIANO_DIVERSE)
        a = _hash(_song(5001)[1])
        genres.piano_diverse(True)
        _, on = _song(5001)
        self.assertIsNotNone(on.endless_diverse)
        genres.piano_diverse(False)
        _, off = _song(5001)
        self.assertIsNone(off.endless_diverse)
        self.assertEqual(_hash(off), a)

    def test_tables_name_real_figures(self):
        D = perform.PIANO_DIVERSE_ON
        for m, hands in D['climax_lh'].items():
            for name, (figs, w) in hands.items():
                self.assertTrue(set(figs) <= set(pianist.FIGURES), name)
        for m, figs in D['quiet_lh'].items():
            self.assertTrue(set(figs) <= set(pianist.FIGURES))
        for f in ('end_bass', 'end_arp', 'end_arp3', 'half', 'waltz_held', 'roll'):
            self.assertIn(f, pianist.FIGURES)
        self.assertEqual(set(D['end_rit']), set(D['ending']))
        self.assertEqual(set(D['at']), set(D['place']))

    def test_draws_vary_and_every_ending_builds(self):
        genres.piano_diverse(True)
        plan = composer.set_plan(NEW_AGE, 8, 320000)
        seen = {k: set() for k in ('climax_lh', 'ending', 'place', 'interlude')}
        for i in range(10):
            tune, song = _song(320000 + 13 * i, plan[i % 8])
            dv = song.endless_diverse
            for k in seen:
                seen[k].add(dv[k])
            end = next(x for x in song.sections if x.name == 'end')
            self.assertEqual(end.length, (2 if dv['ending'] in ('plagal', 'deceptive', 'line', 'arpeggio') else 1)
                             * tune.meter)
            last = [n for n in song.tracks['piano']._notes if n.start >= end.start + end.length - tune.meter - 1e-6]
            self.assertTrue(last, dv['ending'])           # (the last chord / note sounds)
        for k, v in seen.items():
            self.assertGreaterEqual(len(v), 2, k)

    def test_pick_gates_then_prefers_difference(self):
        mk = lambda sd, sc, end: {'seed': sd, 'score': {'score': sc, 'hard': [], 'parts': {}},
                                  'tune': None, 'song': None, '_f': {'ending': end, 'key': 'C major'}}
        ranked = [mk(1, 98.0, 'roll'), mk(2, 97.0, 'line'), mk(3, 95.0, 'open')]
        orig = run.diverse_features
        run.diverse_features = lambda t, s, sc=None: next(c['_f'] for c in ranked if c['score'] is sc)
        try:
            out = run.diverse_pick(ranked, [{'ending': 'roll', 'key': 'C major'}], 1.5, lambda m: None)
        finally:
            run.diverse_features = orig
        self.assertEqual([c['seed'] for c in out], [2, 1, 3])   # (3 is outside the gate, 1 repeats the ending)
        self.assertEqual(run.diverse_pick(ranked, [], 1.5, lambda m: None), ranked)   # (no memory: the best)

    def test_climax_hands_keep_running(self):
        """(round p-div2) every climax hand runs in 8ths / triplets, the bass octave at most once a bar."""
        for m, hands in perform.PIANO_DIVERSE_ON['climax_lh'].items():
            for name, (figs, _) in hands.items():
                for f in figs:
                    toks = pianist.FIGURES[f].split()
                    self.assertEqual(toks.count('-'), 0, f)
                    self.assertLessEqual(toks.count('o'), 1, f)
                    self.assertNotIn('R', toks, f)

    def test_peak_keeps_the_build_and_the_slot_anthem_plays(self):
        """(round p-div2 / p-div3 / p-div4) no section before the climax is dropped; no early place; the sung climax
        states the theme as the set slot drew it (p-div3's own draw reverted)."""
        self.assertNotIn('early', perform.PIANO_DIVERSE_ON['place'])
        plan = composer.set_plan(NEW_AGE, 8, 330000)
        for i in range(16):
            sd, sl = 330000 + 7 * i, plan[i % 8]
            genres.piano_diverse(True)
            _, on = _song(sd, sl)
            genres.piano_diverse(False)
            _, off = _song(sd, sl)
            pre = lambda s: [x.name for x in s.sections][:[x.name for x in s.sections].index('climax')]
            if 'climax' in [x.name for x in off.sections] and 'climax' in [x.name for x in on.sections]:
                self.assertTrue(set(pre(off)) <= set(pre(on)), (sd, pre(off), pre(on)))
            pin = (sl or {}).get('anthem')
            if pin and on.endless_diverse['anthem_played']:
                self.assertEqual(on.endless_diverse['anthem_played'], pin, sd)

    def test_pick_weighs_score_and_guards_dynamics(self):
        mk = lambda sd, sc, end, v: {'seed': sd, 'score': {'score': sc, 'hard': [], 'parts': {'ph_vel': (0, v, 1)}},
                                     'tune': None, 'song': None, '_f': {'ending': end}}
        ranked = [mk(1, 98.0, 'roll', 1.0), mk(2, 97.5, 'line', 0.6), mk(3, 97.4, 'open', 1.0)]
        orig = run.diverse_features
        run.diverse_features = lambda t, s, sc=None: next(c['_f'] for c in ranked if c['score'] is sc)
        try:
            out = run.diverse_pick(ranked, [{'ending': 'roll'}], 0.8, lambda m: None, weigh=0.06,
                                   dyn=('ph_vel',), slack=0.05)
            self.assertEqual(out[0]['seed'], 3)        # (2 plays flatter dynamics than the best)
            out = run.diverse_pick(ranked, [{'ending': 'roll'}], 0.8, lambda m: None, weigh=2.0)
            self.assertEqual(out[0]['seed'], 1)        # (a heavy weight: the difference never pays for 0.5 points)
        finally:
            run.diverse_features = orig

    def test_distance(self):
        f = {'ending': 'roll', 'tempo': 70.0, 'motif': [2, 2, -1]}
        self.assertEqual(run.diverse_distance(f, [dict(f)]), 0.0)
        self.assertGreater(run.diverse_distance(f, [{'ending': 'line', 'tempo': 90.0, 'motif': [5, -3]}]), 0.9)


if __name__ == '__main__':
    unittest.main()
