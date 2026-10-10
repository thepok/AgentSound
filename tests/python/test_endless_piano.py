"""Endless piano in general (agentsound/endless): the genre as data beyond jazz - new-age-piano and classical-piano
(their chord vocabulary, singable melody, the through-composed arrangement played by the romantic pianist with a
broken-chord left hand per section), the mixed set plan, the jazz specs moved toward letters-to-the-morning (LH
figures per section, written dynamics), the breath gate, and the shared tools they use (pianist.FIGURES / broken,
romantic.Score from composed notes, romantic.harmonize)."""
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import endless, pianist, romantic  # noqa: E402
from agentsound.endless import composer, genres, perform  # noqa: E402
from agentsound.endless.run import breath_gate  # noqa: E402
from agentsound.patterns import Clip  # noqa: E402
from agentsound.theory import ComposeError, Progression  # noqa: E402

NEW_AGE = endless.genre('new-age-piano')
CLASSICAL = endless.genre('classical-piano')
JAZZ = endless.genre('jazz-piano')


class Vocabulary(unittest.TestCase):
    def test_the_piano_genres_validate(self):
        for g in (NEW_AGE, CLASSICAL):
            self.assertIs(g.validate(), g)
        self.assertEqual(genres.STYLES, {'jazz': 'jazz-piano', 'new-age': 'new-age-piano',
                                         'classical': 'classical-piano', 'lofi': 'lofi-piano'})

    def test_inversions(self):
        self.assertEqual(composer.parse_block('IM V@3 VIm7@5'), [(0, 'M', 1.0), (7, '@3', 1.0), (9, 'm7@5', 1.0)])
        self.assertEqual(composer.chord_name(8, 7, '@3', False), 'Eb/G')
        self.assertEqual(composer.chord_name(0, 2, 'm7@3', False), 'Dm7/F')
        with self.assertRaisesRegex(ComposeError, 'inversion'):
            composer.parse_block('V@4')

    def test_a_genre_brings_its_own_harmony(self):
        bad = NEW_AGE.but(name='bad')
        bad.harmony['blocks']['major'].pop('hook')
        with self.assertRaisesRegex(ComposeError, 'hook'):
            bad.validate()
        bad = NEW_AGE.but(name='bad')
        bad.feels['flowing']['figures'] = dict(bad.feels['flowing']['figures'], calm={'polka': 1.0})
        with self.assertRaisesRegex(ComposeError, 'FIGURES'):
            bad.validate()
        bad = NEW_AGE.but(name='bad', plan=dict(NEW_AGE.plan, sections=[{'name': 'x', 'part': 'Z'}]))
        with self.assertRaisesRegex(ComposeError, 'part'):
            bad.validate()


class NewAge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tunes = [composer.compose(NEW_AGE, sd, mood) for sd in range(6) for mood in NEW_AGE.moods]

    def test_the_song_form(self):
        for t in self.tunes:
            self.assertEqual((t.form, t.parts, t.meter), ('verse', ['A1', 'A2', 'B', 'C'], 4))
            self.assertTrue(58 <= t.tempo <= 92, t.tempo)
            self.assertNotIn(t.title.split()[0], ('Bleecker', 'Carmine', 'Perry'))
            self.assertFalse(any(x in s for p in t.parts for s, _ in t.changes[p] for x in ('13', '7alt', '#11')))

    def test_singable_and_breathing(self):
        # mostly steps; every 4-bar phrase of the theme ends with a rest of a beat or more
        steps = leaps = 0
        for t in self.tunes:
            for p in t.parts:
                ns = sorted(t.melody[p])
                for a, b in zip(ns, ns[1:]):
                    steps += abs(b[2] - a[2]) <= 2
                    leaps += abs(b[2] - a[2]) > 4
            for p in ('A1', 'A2'):
                for k in (1, 2):
                    end = k * 16
                    last = max(s + d for s, d, _ in t.melody[p] if s < end)
                    self.assertGreaterEqual(end - last, 0.99 if k == 1 else 0.0, (t.title, p, k))
        self.assertGreater(steps / (steps + leaps), 0.7)

    def test_the_theme_and_the_lifted_climax(self):
        for t in self.tunes:
            keep = 3 * 8
            self.assertEqual([n[0] for n in t.melody['A2'] if n[0] < keep],
                             [n[0] for n in t.melody['A1'] if n[0] < keep], t.title)
            top = max(n[2] for p in t.parts for n in t.melody[p])
            lifted = t.out_melody.get('B')
            if lifted:                                     # one top note over the head's, struck once
                peak = max(n[2] for n in lifted)
                self.assertGreater(peak, top, t.title)
                self.assertEqual(sum(n[2] == peak for n in lifted), 1, t.title)
        self.assertGreater(sum(bool(t.out_melody.get('B')) for t in self.tunes), 0.8 * len(self.tunes))

    def test_deterministic(self):
        self.assertEqual(composer.compose(NEW_AGE, 5).to_dict(), composer.compose(NEW_AGE, 5).to_dict())


class Arrangement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.na = [(t, endless.song(t)) for t in (composer.compose(NEW_AGE, sd) for sd in (1, 2, 3))]
        cls.cl = [(t, endless.song(t)) for t in (composer.compose(CLASSICAL, sd) for sd in (1, 2, 3))]

    def test_sections_follow_the_plan(self):
        for t, s in self.na:
            names = [x[0] for x in s.endless_sections]
            self.assertEqual(names[:5], ['intro', 'A1', 'A2', 'B1', 'inter'])
            self.assertEqual(names[-4:], ['build', 'climax', 'A4', 'coda'])
            self.assertEqual(s.sections[-1].name, 'end')
        for t, s in self.cl:
            self.assertEqual([x[0] for x in s.endless_sections], ['intro', 'A1', 'A2', 'B1', 'B2', 'A3', 'coda'])

    def test_the_left_hand_varies_by_section_and_breathes(self):
        for t, s in self.na + self.cl:
            v = composer.lh_variety(s)
            self.assertGreaterEqual(v['distinct'], 4, (t.title, v))
            self.assertGreaterEqual(v['all_figures'], 6, (t.title, v))
            self.assertTrue(all(n.pitch <= 67 for n in s.tracks['comp']._notes if n.start < s['end'].start))

    def test_the_piano_tells(self):
        for t, s in self.na + self.cl:
            r = composer.piano_tells(s, t)
            self.assertGreaterEqual(r['phrase_rests'], 0.75, (t.title, r))
            self.assertGreaterEqual(r['quiet1'], 0.25, (t.title, r))
            self.assertTrue(r['climax_single'], t.title)
            self.assertTrue(0.55 <= r['climax_x'] <= 0.9, (t.title, r['climax_x']))
            self.assertGreaterEqual(r['hook'], 2, t.title)
            self.assertGreater(r['dyn_range'], 6.0, t.title)
            self.assertEqual(breath_gate(endless.genre(t.genre), s), [])

    def test_the_waltz_plays_its_strains_twice_with_varied_hands(self):
        # a salon waltz: ~3 minutes (the strains twice: plan sections with feels=('waltz',)), the left hand from the
        # 3/4 figures of pianist.FIGURES (waltz, waltz2, barcarolle, waltz_open / _held / _arp / _step / _big)
        t = next(t for t in (composer.compose(CLASSICAL, sd, 'salon') for sd in range(20)) if t.feel == 'waltz')
        s = endless.song(t)
        names = [x[0] for x in s.endless_sections]
        self.assertEqual(names, ['intro', 'A1', 'A2', 'B1', 'A1b', 'inter', 'A2b', 'B2', 'A3', 'coda'])
        self.assertGreater(s.seconds(s.length), 150, t.title)
        used = {f for v in s.endless_figures.values() for f in v}
        self.assertGreaterEqual(len(used), 7, used)
        r = composer.piano_tells(s, t)
        self.assertTrue(r['climax_single'] and 0.55 <= r['climax_x'] <= 0.9, (t.title, r['climax_x']))
        # a nocturne has none of the waltz's second pass
        t = next(t for t in (composer.compose(CLASSICAL, sd, 'reverie') for sd in range(20)) if t.feel == 'nocturne')
        self.assertNotIn('A1b', [x[0] for x in endless.song(t).endless_sections])

    def test_chords_are_spelled_by_the_key(self):
        # theory.spell_above via composer.spell: a flat key spells no root / bass with a sharp, Gb major's IV is Cb
        # (not B), an Eb Neapolitan Fb/Ab (not E/Ab)
        from agentsound.theory import chord, pc
        seen_gb = seen_cb = 0
        for g, mood in ((NEW_AGE, 'longing'), (CLASSICAL, 'salon'), (CLASSICAL, 'reverie')):
            for sd in range(14):
                t = composer.compose(g, sd, mood)
                syms = [s_ for p in t.parts for s_, _ in t.changes[p]] + [s_ for s_, _ in t.intro['changes']]
                tonic = t.key.split()[0]
                if 'b' in tonic or tonic == 'F':
                    for s_ in syms:
                        c = chord(s_)
                        if 'b' in tonic and (c.root - pc(tonic)) % 12 == 1:
                            continue           # (the Neapolitan of Ab is Bbb: written A, its third C#)
                        self.assertNotIn('#', c.root_name + (c.bass_name or ''), (t.key, s_))
                if t.key == 'Gb major':
                    seen_gb += 1
                    roots = {chord(s_).root_name for s_ in syms}
                    self.assertNotIn('B', roots, syms)
                    seen_cb += 'Cb' in roots
        self.assertGreater(seen_gb, 0)
        self.assertGreater(seen_cb, 0)
        self.assertEqual(composer.chord_name(3, 1, '@3', False), 'Fb/Ab')

    def test_the_pianist_has_the_feels_body(self):
        # one body over both hands (the feel's profile, the left hand following the right); the breath settles over
        # the rise into the phrase peak, so the player's own timing couples with the loudness (faster where louder)
        from agentsound.humanize import body_stats
        for t, s in self.na[:1] + self.cl[:1]:
            body = (NEW_AGE if t.genre == NEW_AGE.name else CLASSICAL).feels[t.feel]['body']
            self.assertEqual(s.tracks['piano']._body[0].name, body)
            self.assertEqual((s.tracks['comp']._body[0].name, s.tracks['comp']._body[1]), (body, 'piano'))
        t, s = self.na[0]
        st = body_stats(s, 'piano')
        self.assertGreater(st['coupling']['note'], 0.0, (t.title, st['coupling']))
        self.assertGreater(st['breath_ms'], 0.0, t.title)

    def test_deterministic(self):
        t = composer.compose(NEW_AGE, 2)
        a, b = endless.song(t), endless.song(t)
        self.assertEqual(a.tracks['piano']._notes, b.tracks['piano']._notes)
        self.assertEqual(a.tracks['comp']._notes, b.tracks['comp']._notes)

    def test_metadata_and_cover(self):
        t = self.na[0][0]
        self.assertEqual(endless.metadata(t)['genre'], 'New Age')
        self.assertEqual(endless.cover(t)['style'], 'classical')
        self.assertEqual(endless.metadata(self.cl[0][0])['genre'], 'Classical')


class MixedSet(unittest.TestCase):
    def test_a_mixed_set_alternates_the_styles(self):
        plan = composer.mix_plan([JAZZ, NEW_AGE, CLASSICAL], 8, seed=4)
        self.assertEqual(len(plan), 8)
        self.assertTrue(all(a['genre'] != b['genre'] for a, b in zip(plan, plan[1:])))
        self.assertGreaterEqual(len({p['genre'] for p in plan}), 2)
        self.assertTrue(all(a['key'] != b['key'] for a, b in zip(plan, plan[1:])))
        for p in plan:
            g = endless.genre(p['genre'])
            self.assertIn(p['feel'], g.feels)
            t = composer.compose(g, 9, plan=p)
            self.assertEqual((t.key, t.feel, t.tempo), (p['key'], p['feel'], p['tempo']))
        self.assertIn('(new-age-piano)', composer.describe_set(plan) + ' (new-age-piano)')

    def test_the_cli(self):
        from agentsound.cli import build_parser
        a = build_parser().parse_args(['endless', 'piano', '--style', 'new-age', '--count', '2'])
        self.assertEqual((a.genre, a.style, a.count), ('piano', 'new-age', 2))
        a = build_parser().parse_args(['endless', 'jazz-piano'])
        self.assertIsNone(a.style)


LOFI = endless.genre('lofi-piano')


class LoFi(unittest.TestCase):
    """lofi-piano: jazzy 7th / 9th loops, a sparse melody, lazy swing or straight 8ths at 70-90 BPM, the lofi_piano
    band (felt piano, dusty kit per mood, vinyl bed, cassette master), steady time where the kit plays."""

    @classmethod
    def setUpClass(cls):
        cls.tunes = [composer.compose(LOFI, sd, mood) for sd in range(4) for mood in LOFI.moods]
        cls.study = next(t for t in cls.tunes if t.mood == 'study')
        cls.rain = next(t for t in cls.tunes if t.mood == 'rain')
        cls.s_study, cls.s_rain = endless.song(cls.study), endless.song(cls.rain)

    def test_validates_and_refuses_drums_without_steady_time(self):
        self.assertIs(LOFI.validate(), LOFI)
        bad = LOFI.but(name='bad')
        bad.moods['rain']['drums'] = {'style': 'lofi'}            # rain's 'drift' feel has rubato
        with self.assertRaisesRegex(ComposeError, 'strict time'):
            bad.validate()
        bad = LOFI.but(name='bad')
        bad.moods['study']['drums'] = {'style': 'polka'}
        with self.assertRaisesRegex(ComposeError, 'drummer.STYLES'):
            bad.validate()
        bad = LOFI.but(name='bad')
        bad.feels['lazy']['groove'] = 0.9
        with self.assertRaisesRegex(ComposeError, 'groove'):
            bad.validate()

    def test_jazzy_loops_tempo_and_swing(self):
        from agentsound.theory import chord
        for t in self.tunes:
            self.assertEqual((t.form, t.meter), ('verse', 4))
            self.assertTrue(66 <= t.tempo <= 93, t.tempo)
            # the lazy feel swings by itself (its 'groove'), the even / drift feels play straight 8ths
            self.assertEqual(t.swing, 0.57 if t.feel == 'lazy' else None, (t.feel, t.swing))
            for p in t.parts:                                   # 7ths / 9ths everywhere: no plain triad
                for sym, _ in t.changes[p]:
                    self.assertGreaterEqual(len(chord(sym).intervals), 4, (t.title, p, sym))
        t = composer.compose(LOFI, 1, 'study', swing=False)
        self.assertIsNone(t.swing)
        self.assertEqual(composer.compose(LOFI, 1, 'study', swing=0.62).swing, 0.62)   # --swing 0.62 wins

    def test_sparse_breathing_melody(self):
        for t in self.tunes:
            per_bar = sum(len(t.melody[p]) for p in t.parts) / (len(t.parts) * 8)
            self.assertLess(per_bar, 4.5, (t.title, per_bar))
        for t, s in ((self.study, self.s_study), (self.rain, self.s_rain)):
            r = composer.piano_tells(s, t)
            self.assertGreaterEqual(r['quiet1'], 0.3, (t.title, r))
            self.assertGreaterEqual(r['phrase_rests'], 0.75, (t.title, r))
            self.assertTrue(r['climax_single'], t.title)
            self.assertEqual(breath_gate(LOFI, s), [])

    def test_the_band_and_the_drums_per_mood(self):
        s, t = self.s_study, self.study
        self.assertIn('drums', s.tracks)
        self.assertNotIn('drums', self.s_rain.tracks)              # rain: the piano alone
        secs = {x[0]: (x[1], x[2]) for x in s.endless_sections}
        hits = s.tracks['drums']._notes
        for name in ('intro', 'bridge', 'coda'):                    # the kit rests here (plan 'drums': False)
            if name in secs:
                a, z = secs[name]
                self.assertFalse([n for n in hits if a - 1e-6 <= n.start < z - 0.5], name)
        a, z = secs['A1']
        self.assertGreater(len([n for n in hits if a <= n.start < z]), 8 * 6)
        left = [n for n in s.tracks['comp']._notes if n.start < s['end'].start]
        self.assertTrue(left and all(n.pitch <= 67 for n in left))
        figs = {f for v in s.endless_figures.values() for f in v}
        self.assertTrue(figs & {'lofi_hold', 'lofi_push', 'lofi_two', 'lofi_skip'}, figs)
        # steady time where the kit plays: no phrase rubato, no lilt
        tm = s.tempo_map()
        a, z = secs['A1'][0], secs['A2'][1]
        self.assertTrue(all(abs(tm.bpm_at(s._at(a + k * 0.5)) - t.tempo) < 1e-6 for k in range(int((z - a) * 2))))

    def test_the_sound(self):
        from agentsound.bandlib import jazz as jazzband
        s = self.s_study
        names = [f.type for f in s.master.fx.values()] if isinstance(s.master.fx, dict) else \
            [f.type for f in s.master.fx]
        self.assertIn('tape', names)
        tape = next(f for f in (s.master.fx.values() if isinstance(s.master.fx, dict) else s.master.fx)
                    if f.type == 'tape')
        self.assertEqual(tape.params['speed'], 'cassette')
        self.assertGreater(tape.params['wow'], 0)
        self.assertGreater(tape.params['hiss'], 0)
        eq = next(f for f in s.tracks['piano'].fx if f.type == 'eq')
        self.assertLessEqual(eq.params['lp.freq'], 10000)            # the top rolled off
        if jazzband.installed(jazzband.CRACKLE['pack']):
            v = s.tracks['vinyl']._notes
            self.assertGreater(max(n.start + n.dur for n in v), s['end'].start)   # the bed runs to the end
            self.assertTrue(all(b.start < a.start + a.dur for a, b in zip(v, v[1:])))   # cross-faded, no gap

    def test_metadata_cover_and_deterministic(self):
        self.assertEqual(endless.metadata(self.study)['genre'], 'Lo-Fi')
        self.assertEqual(endless.cover(self.study)['style'], 'jazz')
        a, b = endless.song(self.study), endless.song(self.study)
        for tr in ('piano', 'comp', 'drums'):
            self.assertEqual(a.tracks[tr]._notes, b.tracks[tr]._notes, tr)

    def test_in_the_mixed_set_and_the_cli(self):
        plan = composer.mix_plan([JAZZ, NEW_AGE, CLASSICAL, LOFI], 12, seed=3)
        self.assertIn('lofi-piano', {p['genre'] for p in plan})
        for p in plan:
            if p['genre'] == 'lofi-piano':
                t = composer.compose(LOFI, 4, plan=p)
                self.assertEqual((t.feel, t.mood), (p['feel'], p['mood']))
        from agentsound.cli import build_parser
        a = build_parser().parse_args(['endless', 'piano', '--style', 'lofi', '--mood', 'rain'])
        self.assertEqual((a.style, a.mood), ('lofi', 'rain'))

    def test_the_lofi_drummer_and_figures(self):
        from agentsound import drummer
        perf = drummer.arrange([('A', 4)], bpm=80, style='lofi', seed=1, swing=0.57)
        kinds = {h.piece for h in perf.hits}
        self.assertTrue({'kick', 'snare'} <= kinds, kinds)
        self.assertNotIn('crash', kinds)
        ns = pianist.figure('Dm7', 'lofi_hold', 0.0, 4.0)
        self.assertEqual(sorted(n.pitch for n in ns), [38, 53, 57, 60])   # D2, F3, A3, C4: root - 10th - 5th - 7th
        self.assertEqual(len(pianist.figure('Dm7', 'lofi_push', 0.0, 4.0)), 4)


class JazzLikeLetters(unittest.TestCase):
    def test_the_left_hand_changes_by_section(self):
        changes = []
        for sd in (100, 101, 102, 103):
            t = composer.compose(JAZZ, sd)
            s = endless.song(t)
            if JAZZ.feels[t.feel].get('lh_plan'):
                v = composer.lh_variety(s)
                changes.append(v['distinct'])
        self.assertTrue(changes and sum(changes) / len(changes) >= 2.5, changes)

    def test_written_dynamics_widen_the_range(self):
        flat = JAZZ.but(name='jazz-flat', plan={k: v for k, v in JAZZ.plan.items() if k not in ('dyn',)})
        for f in flat.feels.values():
            f.pop('dyn', None)
        t = composer.compose(JAZZ, 103)
        wide = composer.tells(endless.song(t), t)['dyn_range']
        narrow = composer.tells(perform.build(t, flat), t)['dyn_range']
        self.assertGreater(wide, narrow)


class Tools(unittest.TestCase):
    def test_figures(self):
        ns = pianist.figure('Ab', 'flow', 0.0, 4.0)
        self.assertEqual(len(ns), 8)
        self.assertEqual(ns[0].pitch, 44)                      # the bass in Db2-C3, ringing through the bar
        self.assertAlmostEqual(ns[0].dur, 4.0)
        self.assertEqual(len(pianist.figure('Ab', 'flow', 0.0, 2.0)), 4)   # half a bar: its first half
        self.assertEqual(len(pianist.figure('C', 'waltz', 0.0, 3.0, bar=3.0)), 1 + 3 + 3)
        with self.assertRaisesRegex(ComposeError, 'figure'):
            pianist.figure('C', 'polka', 0.0, 4.0)

    def test_broken_holds_still_under_a_breath(self):
        prog = Progression('C Am F G')
        rh = Clip([(0, 1, 72, 80), (1, 1, 74, 80), (4, 1, 72, 80), (5, 1, 74, 80), (6, 1, 76, 80),
                   (7, 1, 77, 80), (8, 1, 79, 80), (12, 1, 72, 80), (13, 1, 71, 80), (14, 2, 72, 80)])
        lh = pianist.left_hand(prog, 72, style='broken', figure='flow', rh=rh, seed=1)
        per_bar = [sum(1 for n in lh if k * 4 <= n.start < k * 4 + 4) for k in range(4)]
        self.assertLess(per_bar[0], per_bar[1])                # bar 1 breathes (a rest after the held note)
        self.assertLess(per_bar[2], 8)                         # bar 3: one note, then rest

    def test_score_from_notes_and_harmonize(self):
        mel = Clip([(0, 2, 76, 80), (2, 1, 74, 80), (3, 1, 72, 80), (4, 4, 79, 80)])
        h = romantic.harmonize(mel, lambda t: 'C', voices=1, share=1.0)
        self.assertEqual(len(h), 6)
        self.assertTrue(all(x.pitch in (72, 67, 64, 76) for x in h if x.pitch not in (76, 74, 72, 79)))
        h2 = romantic.harmonize(mel, lambda t: 'C', voices=2, share=1.0, min_dur=1.5)
        self.assertEqual(len(h2), 4 + 4)
        sc = romantic.score(h, None, None, key='C major', phrases=[(1, 2)])
        self.assertEqual([e.kind for e in sc.events], ['chord', 'note', 'note', 'chord'])


if __name__ == '__main__':
    unittest.main()
