"""Dry, close and calm sung vocals (recipes/HUMAN_FEEDBACK.md "Vocals": "der Gesang hat immer viel Hall und/oder
Reverb" and "im Jazz-Song ist die Stimme viel zu aufgeregt"): the vocal hero's space per genre (its own short
pre-delayed plate at the genre's level, no constant echo, deliberate throws only on section ends for pop / rock, none
for jazz / ballad, no inherited band sends; doubles get the same space), the de-esser after the presence / air boosts,
and the calm singing styles ('jazz', 'ballad': the STYLE_EXTRAS - the pitch model's expressiveness, its wobble damped on
held notes, the soft mode as the base, power only on the loudest peaks, no falls). No WSL / voicebank needed."""

import math
import pathlib
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from agentsound import Song, heroes, mixer, patches, singer  # noqa: E402
from agentsound import voicebank as vb  # noqa: E402
from agentsound.patches import hero_vocal, inst  # noqa: E402
from test_singer import LINE, TEXT, _Env, _fake_run, _song  # noqa: E402


def _vocal_song(sections=('a',)):
    s = Song('dry', tempo=100, key='C major')
    for n in sections:
        s.section(n, bars=4)
    t = s.track('vocal', inst.va())
    for k, sec in enumerate(s.sections):
        t.note('E4', sec.start, 2.0, 90)          # a held phrase end ...
        t.note('G4', sec.start + 6, 3.0, 90)      # ... and the section's last one
    return s, t


class VocalSpace(unittest.TestCase):
    def test_genre_levels_and_echo(self):
        for genre, plate, throws in (('pop', -21.0, True), ('rock', -20.0, True), ('jazz', -25.0, False),
                                     ('ballad', -25.0, False), (None, -21.0, True)):
            s, t = _vocal_song()
            heroes.hero(t, family='vocal', genre=genre)
            self.assertIn('vocal_plate', s.buses, genre)
            self.assertEqual(t.sends['vocal_plate'], plate, genre)
            self.assertEqual(hero_vocal.VOCAL_SPACE.get(genre or 'pop'), plate)
            self.assertNotIn('hero_plate', s.buses)
            self.assertEqual(t.hero.options['throws'], throws, genre)
            if throws:      # no constant echo: the send sits at -60 between the throws
                self.assertEqual(t.sends['echo'], -60.0)
            else:
                self.assertNotIn('echo', s.buses, genre)
                self.assertNotIn('echo', t.sends)
                self.assertTrue(any('throws: off' in x for x in t.hero.log))

    def test_the_plate_is_short_and_predelayed(self):
        p = patches.get('bus/vocal_plate')
        rev = next(f for f in p.fx if f.type == 'reverb')
        self.assertLessEqual(rev.params['decay'], 1.6)
        self.assertGreaterEqual(rev.params['predelay'], 40)
        self.assertLessEqual(rev.params['predelay'], 90)

    def test_explicit_switches_win(self):
        s, t = _vocal_song()
        heroes.hero(t, family='vocal', genre='jazz', throws=True)
        self.assertEqual(t.sends['echo'], -60.0)
        s, t = _vocal_song()
        heroes.hero(t, family='vocal', genre='pop', echo=False)
        self.assertNotIn('echo', s.buses)
        s, t = _vocal_song()
        t.send(s.hall(), -14)                           # asked for: the song's own send stays
        heroes.hero(t, family='vocal', genre='jazz')
        self.assertEqual(t.sends['hall'], -14)

    def test_no_inherited_band_sends(self):
        s = Song('inherit', tempo=100)
        s.section('a', bars=2)
        s.hall()
        t = s.track('vocal', patches.Patch('test/voice', inst.va(), sends={'hall': -9.0, 'plate': -10.0}))
        t.note('C4', 0, 2)
        heroes.hero(t, family='vocal', chain=False)
        self.assertNotIn('hall', t._patch_sends)
        self.assertTrue(any("patch's sends dropped" in x for x in t.hero.log))
        r = s.compile()
        tr = next(x for x in r['tracks'] if x['id'] == 'vocal')
        self.assertNotIn('hall', tr['sends'])
        self.assertIn('vocal_plate', tr['sends'])
        # another hero keeps its patch sends (inherit stays True outside the vocal)
        self.assertTrue(heroes.get_preset('sax').space_for(None)['inherit'])

    def test_throws_only_on_section_ends(self):
        s, t = _vocal_song(('verse', 'chorus'))
        heroes.hero(t, family='vocal', genre='pop')
        s.compile()
        self.assertTrue(any('throws: 2 section ends' in x for x in t.hero.compile_log), t.hero.compile_log)
        lane = dict(t._auto)['send.echo']
        self.assertEqual(len(lane), 8)                  # 4 points per throw, two sections
        self.assertEqual(min(p[1] for p in lane), -60.0)
        self.assertEqual(max(p[1] for p in lane), -10.0)

    def test_bad_space_key(self):
        with self.assertRaises(Exception):
            heroes.define('x_bad_space', family='x', chain={}, gain_db=0.0, sends={}, space={'plate_db': -3})
        with self.assertRaises(Exception):
            heroes.define('x_bad_scope', family='x', chain={}, gain_db=0.0, sends={},
                          space={'genres': {'pop': {'throw_scope': 'bars'}}})

    def test_deesser_after_the_boosts(self):
        s, t = _vocal_song()
        heroes.hero(t, family='vocal')
        names = [f.name for f in t.fx]
        self.assertLess(names.index('presence'), names.index('deess'))
        self.assertLess(names.index('drive'), names.index('deess'))
        self.assertEqual(names[-1], 'hero_ride')
        self.assertEqual(names[-2], 'air')

    def test_ballad_profile(self):
        self.assertEqual(mixer.get_profile('ballad').name, 'ballad')


class CalmStyles(_Env):
    def test_extras_only_on_the_calm_styles(self):
        for st in ('pop', 'rock'):          # their cached takes keep their keys (no re-render)
            self.assertFalse(set(singer.STYLE_EXTRAS) & set(singer.STYLES[st]), st)
        for st in ('jazz', 'ballad'):
            S = singer.STYLES[st]
            self.assertTrue(set(singer.STYLE_EXTRAS) - {'makeup_db'} <= set(S), st)
            self.assertTrue(S['sing_soft'])
            self.assertGreaterEqual(S['late_ms'] - S['jitter_ms'], 20.0)     # behind the beat, never ahead
            self.assertGreater(S['late_first_ms'], 0.0)
            self.assertEqual(S['fall'], 0.0)
            self.assertEqual(S['doit'], 0.0)
            self.assertLess(S['expr'], singer.STYLE_EXTRAS['expr'])
            self.assertLess(S['model_vib'], 1.0)
            self.assertGreater(S['base_soft'], S['base_core'] - 0.5)
            self.assertGreater(S['power_knee'], 0.0)
            self.assertLess(S['vib_hz'], singer.STYLES['pop']['vib_hz'])
            self.assertLess(S['vib_ct'], singer.STYLES['pop']['vib_ct'])
            self.assertGreater(S['vib_delay'], singer.STYLES['pop']['vib_delay'])
            self.assertGreater(S['vib_min_s'], singer.STYLES['pop']['vib_min_s'])
            self.assertLess(S['scoop_first'], singer.STYLES['pop']['scoop_first'])
            self.assertLess(S['vel'][1] - S['vel'][0], singer.STYLES['pop']['vel'][1] - singer.STYLES['pop']['vel'][0])

    def test_overrides_accept_the_extras(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, style='pop', expr=0.6, track_id='p')
        self.assertEqual(vo.params['expr'], 0.6)
        singer.double(vo, model_vib=0.5)
        with self.assertRaises(singer.SingerError):
            singer.sing(s, LINE, TEXT, at=0, expressiveness=0.6, track_id='q')

    def test_jazz_timeline_and_pitch_job(self):
        s = _song()
        s._singer_dir = self.tmp
        mem = singer.Memory()
        line = LINE.transpose(0)
        vo = singer.sing(s, line, TEXT, at=0, style='jazz', seed=5, memory=mem, sing_soft=False)  # the blend
        self.assertFalse([m for _, m, _ in vo.moves if m in ('fall', 'doit')])
        spec = singer._phrase_spec(vo, vo.phrases[0])
        job = singer._dur_job(spec)
        tl = singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec), vb.get('hanami'))
        self.assertIn('steadymask', tl)
        self.assertEqual(len(tl['steadymask']), tl['frames'])
        self.assertTrue(any(tl['steadymask']))
        mix = tl['mix']
        means = {k: (sum(v) / len(v) if isinstance(v, list) else v) for k, v in mix.items()}
        core = vb.get('hanami').mode('core')
        self.assertLess(means[core], max(means.values()))             # the soft mode is the base
        self.assertEqual(singer._pitch_job(tl, spec, vb.get('hanami'))['expr'], singer.STYLES['jazz']['expr'])
        pop = singer.sing(s, line, TEXT, at=0, style='pop', seed=5, track_id='pop')
        ps = singer._phrase_spec(pop, pop.phrases[0])
        pj = singer._dur_job(ps)
        ptl = singer._timeline(ps, singer._cons_lengths(pj, [6.0] * len(pj['phonemes']), ps), vb.get('hanami'))
        self.assertNotIn('steadymask', ptl)
        self.assertEqual(singer._pitch_job(ptl, ps, vb.get('hanami'))['expr'], 0.85)

    def test_hybrid_damps_the_model_wobble_on_held_notes(self):
        n = 200
        model = [60.0 + 0.3 * math.sin(2 * math.pi * 5.5 * f * singer.FR) for f in range(n)]
        plan = {'moves': [0.0] * n, 'vibmask': [0] * n}
        full = singer._hybrid(model, plan)
        calm = singer._hybrid(model, dict(plan, steadymask=[1] * n, model_vib=0.25))

        def dev(c):
            return max(abs(x - 60.0) for x in c[40:160])
        self.assertAlmostEqual(dev(full), 0.3, places=2)
        self.assertLess(dev(calm), 0.3 * 0.4)

    def test_double_gets_the_dry_space(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, style='jazz', seed=3)
        heroes.hero(vo.track, family='vocal')               # no genre: the singing style's space
        self.assertTrue(any("singing style 'jazz'" in x for x in vo.track.hero.log))
        dbl = singer.double(vo, pan=-0.5)
        harm = singer.harmony(vo, steps=2)
        for d in (dbl, harm):
            heroes.hero(d.track, family='vocal', ride=False, duck=False, carve=False, dips=False)
            self.assertEqual(d.track.sends, {'vocal_plate': hero_vocal.VOCAL_SPACE['jazz']})
        self.assertNotIn('echo', s.buses)
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            r = s.compile()
        for tr in r['tracks']:
            if tr['id'].startswith('vocal'):
                self.assertEqual(set(tr['sends']), {'vocal_plate'}, tr['id'])


class SingSoft(_Env):
    """style 'jazz': sing soft, then make up the gain; laid back."""

    def _tl(self, vo, k=0):
        spec = singer._phrase_spec(vo, vo.phrases[k])
        job = singer._dur_job(spec)
        return spec, job, singer._timeline(spec, singer._cons_lengths(job, [6.0] * len(job['phonemes']), spec),
                                           vb.get('hanami'))

    def test_every_model_sings_the_soft_mode(self):
        s = _song()
        s._singer_dir = self.tmp
        bank = vb.get('hanami')
        soft = bank.mode('soft')
        vo = singer.sing(s, LINE, TEXT, at=0, style='jazz', seed=2)
        spec, job, tl = self._tl(vo)
        self.assertEqual(job['speaker'], {soft: 1.0})                       # the duration model
        self.assertEqual(tl['mix'], {soft: 1.0})                            # the acoustic model: no crossfade
        self.assertEqual(singer._pitch_job(tl, spec, bank)['speaker'], {soft: 1.0})
        pop = singer.sing(s, LINE, TEXT, at=0, style='pop', seed=2, track_id='pop')
        pspec, pjob, ptl = self._tl(pop)
        self.assertNotIn('speaker', pjob)                                   # pop: as before (cached takes stay)
        self.assertGreater(len(ptl['mix']), 1)
        self.assertEqual(singer._pitch_job(ptl, pspec, bank)['speaker'], {bank.mode('core'): 1.0})
        # the robot sings no soft mode
        rb = singer.sing(s, LINE, TEXT, at=0, style='jazz', moves=False, track_id='robot')
        self.assertNotIn('speaker', self._tl(rb)[1])

    def test_makeup_on_the_zone_not_in_the_cache_key(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, style='jazz', seed=2)
        self.assertEqual(singer.makeup_db(vo), singer.SOFT_MAKEUP_DB['hanami'])
        loud = singer.sing(s, LINE, TEXT, at=0, style='jazz', seed=2, makeup_db=2.5, track_id='loud')
        self.assertEqual(singer.makeup_db(loud), 2.5)
        k1 = singer._key(singer._phrase_spec(vo, vo.phrases[0]))
        k2 = singer._key(singer._phrase_spec(loud, loud.phrases[0]))
        self.assertEqual(k1, k2)                                             # the same takes, only the zone differs
        self.assertEqual(singer.makeup_db(singer.sing(s, LINE, TEXT, at=0, style='pop', track_id='p')), 0.0)
        calls = []
        with mock.patch.object(vb, 'run', _fake_run(calls)), mock.patch.object(vb, 'runner_ok', lambda: (True, '')):
            r = s.compile()
        zones = {t['id']: t['instrument']['params']['samples'] for t in r['tracks']}
        self.assertTrue(all(z.get('gain') == 2.5 for z in zones['loud']))
        self.assertTrue(all('gain' not in z for z in zones['p']))
        if singer.SOFT_MAKEUP_DB['hanami']:
            self.assertTrue(all(z.get('gain') == singer.SOFT_MAKEUP_DB['hanami'] for z in zones['vocal']))

    def test_laid_back_phrase_openers(self):
        s = _song()
        s._singer_dir = self.tmp
        vo = singer.sing(s, LINE, TEXT, at=0, style='jazz', seed=2)
        S = singer.STYLES['jazz']
        firsts = {ph[0] for ph in vo.phrases}
        for i in range(len(vo.notes)):
            late = vo.plan[i]['late_ms']
            self.assertGreater(late, 0.0)
            if i in firsts:
                self.assertGreaterEqual(late, S['late_ms'] - S['jitter_ms'] + S['late_first_ms'] - 1e-6)
        spec, job, tl = self._tl(vo)
        self.assertGreater(tl['vowels'][0], 0.02)                           # the first vowel lands behind the beat


if __name__ == '__main__':
    unittest.main()
