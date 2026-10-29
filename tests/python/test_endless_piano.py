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
            self.assertEqual((t.form, t.parts), ('verse', ['A1', 'A2', 'B', 'C']))
            self.assertIn(t.meter, (3, 4))                 # (the waltz: HUMAN_FEEDBACK 2026-10-12, a set must vary)
            self.assertTrue(55 <= t.tempo <= 106, t.tempo)
            self.assertNotIn(t.title.split()[0], ('Bleecker', 'Carmine', 'Perry'))
            self.assertFalse(any(x in s for p in t.parts for s, _ in t.changes[p] for x in ('13', '7alt', '#11')))

    def test_singable_and_breathing(self):
        # mostly steps; most 4-bar phrases of the theme end with a rest of a beat or more (the drawn phrase
        # ends also let some run on into the answer with a pickup or an anticipation)
        steps = leaps = breaths = halves = 0
        for t in self.tunes:
            for p in t.parts:
                ns = sorted(t.melody[p])
                for a, b in zip(ns, ns[1:]):
                    steps += abs(b[2] - a[2]) <= 2
                    leaps += abs(b[2] - a[2]) > 4
            for p in ('A1', 'A2'):
                for k in (1, 2):
                    end = k * t.part_beats(p) / 2
                    last = max(s + d for s, d, _ in t.melody[p] if s < end)
                    self.assertGreaterEqual(end - last, 0.0, (t.title, p, k))
                    if k == 1:
                        halves += 1
                        breaths += end - last >= 0.99
        self.assertGreater(steps / (steps + leaps), 0.7)
        self.assertGreater(breaths / halves, 0.4)

    def test_the_theme_and_the_lifted_climax(self):
        left = 0
        for t in self.tunes:
            keep = 8                                       # (the hook: melody['restate'] keeps 1-2 units of 2 bars)
            self.assertEqual([n[0] for n in t.melody['A2'] if n[0] < keep],
                             [n[0] for n in t.melody['A1'] if n[0] < keep], t.title)
            left += [n for n in t.melody['A2'] if n[0] < 24] != [n for n in t.melody['A1'] if n[0] < 24]
            top = max(n[2] for p in t.parts for n in t.melody[p])
            lifted = t.out_melody.get('B')
            if lifted:                                     # one top note over the head's, struck once
                peak = max(n[2] for n in lifted)
                self.assertGreater(peak, top, t.title)
                self.assertEqual(sum(n[2] == peak for n in lifted), 1, t.title)
        self.assertGreater(sum(bool(t.out_melody.get('B')) for t in self.tunes), 0.8 * len(self.tunes))
        self.assertGreater(left, 0.8 * len(self.tunes))    # (round r2: A2 = A1's first 6 bars in every tune)

    def test_deterministic(self):
        self.assertEqual(composer.compose(NEW_AGE, 5).to_dict(), composer.compose(NEW_AGE, 5).to_dict())


class Arrangement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # (the production path: run.prepare's arc and breath checks reroll a seed - round g5 measured 20 % breath
        # rejects in plain compose(); the first three new-age seeds from 1 that pass both)
        from types import SimpleNamespace
        from agentsound.endless.run import prepare
        cls.na, sd = [], 1
        while len(cls.na) < 3:
            got = prepare(NEW_AGE, sd, SimpleNamespace(mood=None, swing=None), lambda _m: None)
            cls.na += [got] if got else []
            sd += 1
        cls.cl = [(t, endless.song(t)) for t in (composer.compose(CLASSICAL, sd) for sd in (1, 2, 3))]

    def test_sections_follow_the_plan(self):
        # (the learned generator's blind round 2: one frame in every piece - the intro and the interludes are drawn:
        # 'chance')
        want = {'song': (['intro', 'A1', 'A2', 'B1', 'inter'], ['build', 'climax', 'A4', 'coda']),
                'chorus': (['intro', 'A1', 'B1', 'A2', 'build'], ['build', 'climax', 'A4', 'coda']),
                'return': (['intro', 'A1', 'A2', 'B1', 'build'], ['climax', 'inter', 'A3', 'coda']),
                # (blind round g2: one form skeleton - the arch, theme and variations, the late climax)
                'arch': (['intro', 'A1', 'B1', 'build'], ['climax', 'inter', 'B2', 'A3', 'coda']),
                'variations': (['intro', 'A1', 'B1', 'A3'], ['climax', 'A4', 'coda']),   # (round g5: B1 its contrast)
                'late': (['intro', 'A1', 'A2', 'B1', 'inter'], ['A3', 'build', 'climax', 'A4', 'coda'])}
        drawn = {'intro', 'inter', 'A3'}
        for t, s in self.na:                           # (the layout: the tune's set-level draw)
            names = [x[0] for x in s.endless_sections]
            head, tail = want[t.arrange['layout']]
            self.assertEqual(s.endless_arrangement.piece['layout'], t.arrange['layout'])
            full = head + [n for n in tail if n not in head]
            if t.meter == 3 and full[full.index('A1') + 1] in perform.WALTZ_FORM['after_a1']:
                full.remove(full[full.index('A1') + 1])  # (round g7: a waltz's A1 is a 16-bar period - no A A)
            self.assertEqual([n for n in names if n not in drawn], [n for n in full if n not in drawn])
            self.assertEqual(names[-1], 'coda')
            self.assertEqual(s.sections[-1].name, 'end')
        for t, s in self.cl:
            self.assertEqual([x[0] for x in s.endless_sections], ['intro', 'A1', 'A2', 'B1', 'B2', 'A3', 'coda'])

    def test_the_left_hand_varies_by_section_and_breathes(self):
        for t, s in self.na + self.cl:
            v = composer.lh_variety(s)
            self.assertGreaterEqual(v['distinct'], 4, (t.title, v))
            self.assertGreaterEqual(v['all_figures'], 6, (t.title, v))
            # (under its cap - G4 - outside the bloom; in the bloom it may rise to a whole step under the melody)
            # (a signature cascade's hands leapfrog: its left hand crosses over - composer.sig_spans)
            bl = getattr(s, 'endless_bloom', None)
            x = s[bl['section']] if bl else None
            casc = composer.sig_spans(s, 'cascade')
            self.assertTrue(all(n.pitch <= (67 + 12 if x and x.start - 1e-6 <= n.start < x.end else 67)
                                for n in s.tracks['comp']._notes if n.start < s['end'].start
                                and not any(a - 1e-6 <= n.start < z for a, z in casc)))

    def test_the_piano_tells(self):
        for t, s in self.na + self.cl:
            r = composer.piano_tells(s, t)
            # (new-age melody['half_line']: a chorus's inner half cadence may run on - the references 0.73-1.0)
            # (HUMAN_FEEDBACK 2026-10-15 "one finger": connecting notes and inner voices may lead a phrase into the
            # next one - plan['texture'])
            self.assertGreaterEqual(r['phrase_rests'], 0.45, (t.title, r))
            self.assertGreaterEqual(r['quiet1'], 0.2, (t.title, r))
            self.assertTrue(r['climax_single'], t.title)
            # (blind round g2: the peak at 71-76 % in every piece - the forms now place it from ~45 % to ~90 %)
            self.assertTrue(0.45 <= r['climax_x'] <= 0.92, (t.title, r['climax_x']))
            self.assertGreaterEqual(r['hook'], 2, t.title)
            # (round g7: the climax swells from a softer entry, the sung theme lower - 2-bar windows' 10-95 % spread
            # over 48 seeds 8.85 -> 8.5 dB, the lowest 5.1 -> 4.6)
            self.assertGreater(r['dyn_range'], 4.5, t.title)
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
        # (the heard coupling; the player's own timing alone wanders -0.25..+0.24 over seeds 1-8 since the drawn
        # arrangement fills / re-sequences the melody and the set-level draws move layout / register - near zero on
        # average, never strongly against the loudness)
        # (the heard coupling over seeds 1-12: -0.11..+0.37, mean 0.18 since the sections' dynamics are drawn per piece
        # - a falling mark under a phrase's rising rubato - positive on average, never strongly against)
        notes, heard = [], []
        for t, s in self.na:
            st = body_stats(s, 'piano')
            self.assertGreater(st['coupling']['heard'], -0.15, (t.title, st['coupling']))
            self.assertGreater(st['coupling']['note'], -0.3, (t.title, st['coupling']))
            self.assertGreater(st['breath_ms'], -1.5, t.title)     # (near zero for one of seeds 1-3 since round g4)
            notes.append(st['coupling']['note'])
            heard.append(st['coupling']['heard'])
        self.assertGreater(sum(notes) / len(notes), -0.1, notes)
        self.assertGreater(sum(heard) / len(heard), 0.05, heard)

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


class Bloom(unittest.TestCase):
    """The bloom (HUMAN_FEEDBACK 2026-10-15, genres._NA_BLOOM, perform._bloom / _handoffs, composer.bloom_tells):
    one section per piece pushes the tempo forward, doubles the motion in both hands and opens the left hand toward
    the melody; the hand-to-hand figure carries the left hand's climb on in the right hand over a held note."""

    @classmethod
    def setUpClass(cls):
        cls.tune = composer.compose(NEW_AGE, 108)      # (round g6: 103 blooms in a B1 without a hand-off now)
        cls.s = endless.song(cls.tune)
        plain = NEW_AGE.but(name='plain', plan=dict(NEW_AGE.plan, bloom=None))
        cls.plain = perform.build(cls.tune, plain)

    def test_a_mirrored_figure_turns_at_its_cap(self):
        up = [n.pitch for n in pianist.figure('C', 'span16', 0.0, 4.0, cap=72, mirror=True)]
        self.assertLessEqual(max(up), 72)
        steps = [b - a for a, b in zip(up, up[1:])]
        self.assertTrue(all(abs(d) <= 9 for d in steps), up)      # no octave folds: the figure turns
        folded = [n.pitch for n in pianist.figure('C', 'span16', 0.0, 4.0, cap=72)]
        self.assertEqual(up[:6], folded[:6])
        self.assertEqual(up[6:9], [67, 64, 67])                   # (folded: 64 67 64 - an octave down, a zigzag)
        self.assertNotEqual(up, folded)

    def test_one_section_blooms(self):
        bl = self.s.endless_bloom
        self.assertIn(bl['section'], NEW_AGE.plan['bloom']['at'])
        self.assertIsNone(self.plain.endless_bloom)
        x = self.s[bl['section']]
        lh = [n for n in self.s.tracks['comp']._notes if x.start <= n.start < x.end]
        lh0 = [n for n in self.plain.tracks['comp']._notes if x.start <= n.start < x.end]
        rh = [n for n in self.s.tracks['piano']._notes if x.start <= n.start < x.end]
        rh0 = [n for n in self.plain.tracks['piano']._notes if x.start <= n.start < x.end]
        # (a blooming climax: its plain figures are already the broad 'big' / 'sweep' 16ths - more, not 1.4x)
        # (round g7: the bloom's second stage triplets with 8ths / 16ths between - 12-13 attacks a bar read as a
        # busy left hand: 1.3x, not 1.4x)
        more = 1.0 if bl['section'] == 'climax' else 1.3
        self.assertGreater(len({round(n.start, 2) for n in lh}), more * len({round(n.start, 2) for n in lh0}))
        self.assertGreater(len({round(n.start, 2) for n in rh}), len({round(n.start, 2) for n in rh0}))
        self.assertGreater(len(self.s.endless_figures[bl['section']]), 0)

    def test_the_tempo_pushes_and_the_climax_keeps_it(self):
        b, b0 = composer.bloom_tells(self.s), composer.bloom_tells(self.plain)
        self.assertGreaterEqual(b['tempo_push'], 1.03, b)
        self.assertLessEqual(b0['tempo_push'], 1.01, b0)
        self.assertGreater(b['climax_tempo'], b0['climax_tempo'])
        self.assertGreater(b['rh_peak_den'], b0['rh_peak_den'])
        m = composer.score_metrics(self.s, self.tune, 'new-age')
        self.assertTrue({'tempo_push', 'climax_tempo', 'rh_peak_den', 'flow32', 'hand_meet'} <= set(m))
        self.assertNotIn('tempo_push', composer.score_metrics(self.s, self.tune, 'classical'))   # (new-age only)

    def test_the_hands_pass_the_figure(self):
        figs = [e for e in self.s.endless_figures.values() for e in e]
        hands = set(NEW_AGE.plan['bloom']['hand'][4]) | set(NEW_AGE.plan['bloom']['bloom_hand'][4])
        self.assertTrue(hands & set(figs), figs)
        # (its signature cascade takes the climax bars after the peak where its hand-offs sat: without the moves)
        bare = perform.build(self.tune, NEW_AGE.but(name='bare', plan=dict(NEW_AGE.plan, signature=None)))
        self.assertGreaterEqual(bare.endless_bloom['handoffs'], 1)

    def test_breathes_and_deterministic(self):
        self.assertEqual(breath_gate(NEW_AGE, self.s), [])
        again = endless.song(self.tune)
        self.assertEqual([tuple(n) for n in again.tracks['piano']._notes], [tuple(n) for n in self.s.tracks['piano']._notes])
        self.assertEqual(again.tempo_points(), self.s.tempo_points())

    def test_the_plan_is_strict(self):
        bad = NEW_AGE.but(name='bad', plan=dict(NEW_AGE.plan, bloom=dict(NEW_AGE.plan['bloom'], speed=2)))
        with self.assertRaisesRegex(ComposeError, "plan\\['bloom'\\]"):
            bad.validate()
        bad = NEW_AGE.but(name='bad', plan=dict(NEW_AGE.plan, bloom=dict(NEW_AGE.plan['bloom'], push={1.5: 1.0})))
        with self.assertRaisesRegex(ComposeError, 'push'):
            bad.validate()


class BlindG12(unittest.TestCase):
    """The g11 judges' fixes (songs/_blind/ROUNDS.md "Round g11"; tells_newage.py g12_tells measures them)."""

    def test_a_head_of_long_notes_has_no_rhythm(self):
        # (KTGG's waltz head: three half notes over two bars passed HEAD_SHAPE)
        harm = composer.Harm([('C', 3.0)] * 4, {0, 2, 4, 5, 7, 9, 11})
        flat = [(0.0, 2.0, 72), (2.0, 2.0, 74), (4.0, 2.0, 79), (6.0, 3.0, 76), (9.0, 3.0, 72)]
        lilt = [(0.0, 1.5, 72), (1.5, 0.5, 74), (2.0, 1.0, 79), (3.0, 1.0, 77), (4.0, 2.0, 76), (6.0, 1.0, 72),
                (7.0, 2.0, 79), (9.0, 2.0, 76), (11.0, 1.0, 74)]
        self.assertFalse(composer.head_shape(flat, harm, 3)['rhy'])
        self.assertTrue(composer.head_shape(lilt, harm, 3)['rhy'])

    def test_the_sung_climax_peaks_at_f6_and_opens_with_the_head(self):
        for sd in (64000, 64003, 64008):
            t = composer.compose(NEW_AGE, sd)
            s = endless.song(t)
            self.assertLessEqual(max(n.pitch for n in s.tracks['piano']._notes), 89, sd)   # (F6; no A6 peaks)
            a, z = next((a, z) for n, a, z in s.endless_sections if n == 'climax')
            mv = [x for x in s.endless_signature['statements'] if x['move'] == 'motto' and x['role'] == 'payoff']
            self.assertTrue(all(x['at'] >= a + 2 * t.meter - 1e-6 for x in mv), sd)       # (the head first)

    def test_the_coda_varies_the_head(self):
        t = composer.compose(NEW_AGE, 64003)
        ch, mel = perform._coda_head(t, [('C', 4.0)], [(0.0, 4.0, 72)], 4, 4.0)
        a1 = sorted(t.melody[t.parts[0]])
        head = [n for n in mel if n[0] < sum(b for _, b in ch) - 4.0 - 1e-6]
        self.assertTrue(head)
        self.assertNotEqual([(n[0], n[2]) for n in head], [(n[0], n[2]) for n in a1[:len(head)]])
        self.assertEqual([n[2] for n in head if n[0] < 2 * t.meter][:2], [n[2] for n in a1][:2])  # (augmented)


class BlindG1(unittest.TestCase):
    """The all-generated blind round g1's tells fixed in the teacher (songs/_blind/ROUNDS.md 'After g1';
    songs/_blind/tells_newage.py measures them over a seed range)."""

    def test_figures_use_the_local_chord_scale(self):
        # (g1 tell 1: runs and turns in the home key's scale over a chord / a section in another key)
        for sd in (64003, 64009, 64013):              # (a climax in another key; round g9: its 'key' arrival)
            t = composer.compose(NEW_AGE, sd)
            s = endless.song(t)
            spans = [(a, z, composer.RaisedPcs(p)) for a, z, p in s.endless_keys]
            self.assertGreater(len(spans), 1, sd)     # (a section in another key)
            off = []
            for n in s.tracks['piano']._notes:
                t_ = n.start + 0.03                    # (a mordent struck a hair early is its beat's: round g14)
                sym = next((c for a, b, c in s.endless_timeline if a - 1e-6 <= t_ < a + b - 1e-6), None)
                if n.dur <= 1 / 3 and sym and n.pitch % 12 not in perform._local_scale(spans, t_, sym):
                    off.append((round(n.start, 2), sym, n.pitch))
            self.assertEqual(off, [], sd)

    def test_the_grow_climax_can_carry_the_hook_augmented(self):
        ch = [('C', 4.0), ('Am', 4.0), ('F', 4.0), ('G', 4.0)] * 2
        hook = [(0.0, 1.0, 72), (1.0, 0.5, 74), (1.5, 0.5, 76), (2.0, 2.0, 74), (4.0, 2.0, 72)]
        pcs = {0, 2, 4, 5, 7, 9, 11}
        plain = perform._grow(ch, hook, 4, pcs, 86)
        aug = perform._grow(ch, hook, 4, pcs, 86, aug=True)
        self.assertNotEqual(plain, aug)
        self.assertEqual([round(n[0], 2) for n in aug if n[0] < 12], [0.0, 2.0, 3.0, 4.0, 8.0])   # (twice as slow)
        self.assertEqual(max(n[2] for n in aug), max(n[2] for n in plain))                          # (one peak)

    def test_hand_offs_are_phrase_shaped(self):
        # (g1 tell 3: the same 16th run on beat 4 of every build / climax bar)
        for sd in range(64000, 64012):
            s = endless.song(composer.compose(NEW_AGE, sd))
            m = int(s.beats_per_bar)
            fast = [n for n in s.tracks['piano']._notes if n.dur <= 1 / 3]
            runs = []
            for name, a, z in s.endless_sections:
                for k in range(int(round((z - a) / m))):
                    t0 = a + k * m
                    runs.append(sum(t0 + m - 1 - 1e-6 <= n.start < t0 + m - 1e-6 for n in fast) >= 3)
            self.assertFalse(any(all(runs[i:i + 3]) for i in range(len(runs) - 2)), sd)

    def test_the_waltz_keeps_its_line_and_moves_its_chords(self):
        # (g1 tell 6: the right hand silent for 4 bars of a coda / a whole interlude; 'X | X/inversion' pairs)
        for sd in (64002, 64006):
            t = composer.compose(NEW_AGE, sd)
            self.assertEqual(t.meter, 3)
            s = endless.song(t)
            rh = s.tracks['piano']._notes
            body = [(a, z) for name, a, z in s.endless_sections if name != 'intro']
            for a, z in body:
                for k in range(int(round((z - a) / 3))):
                    t0 = a + 3 * k
                    sounding = any(n.start < t0 + 3 - 1e-6 and n.start + n.dur > t0 + 1e-6 for n in rh)
                    later = any(t0 + 3 <= n.start < t0 + 9 for n in rh)
                    self.assertTrue(sounding or later, (sd, t0))       # (never two silent bars after the intro)
            syms = [c for _, _, c in s.endless_timeline]
            pairs = sum(x != y and '/' in y and x.split('/')[0] == y.split('/')[0] for x, y in zip(syms, syms[1:]))
            # (g1: 8-11 a waltz; round g5 over the 10 waltzes of seeds 64000-64059: mean 3.5, before 3.4)
            self.assertLessEqual(pairs, 7, sd)

    def test_the_set_varies_the_theme_s_opening(self):
        plan = composer.set_plan(NEW_AGE, 10, 64000)
        ops = [x['opening']['na'] for x in plan]
        for i in range(len(ops)):
            self.assertNotIn(ops[i], ops[max(0, i - 3):i])       # (no repeat in 3 slots: set_memory)


class NewAgeEPiano(unittest.TestCase):
    """new-age-epiano: new-age-piano's composer, plan and score on the DX7 e-piano (a pedalled stack, the left hand
    higher, the level following the velocity); the grand's spec untouched."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('new-age-epiano')
        cls.tune = composer.compose(cls.g, 11)      # (seed 7 blooms in its climax: quiet1 0.233, the runner rerolls)
        cls.s = endless.song(cls.tune)

    def test_derived_from_new_age(self):
        g = self.g
        self.assertIs(g.validate(), g)
        self.assertEqual((g.style, g.harmony, g.melody, g.moods), (NEW_AGE.style, NEW_AGE.harmony, NEW_AGE.melody,
                                                                    NEW_AGE.moods))
        self.assertNotIn('bass_lo', NEW_AGE.plan.get('lh') or {})   # the grand keeps its register
        self.assertNotIn('options', NEW_AGE.band)
        for feel in g.feels.values():
            self.assertFalse({'big', 'sweep'} & set(feel['figures']['big']))   # no bass octaves under the climax
        bad = g.but(name='bad', plan=dict(g.plan, lh={'bass': 40}))
        with self.assertRaisesRegex(ComposeError, "plan\\['lh'\\]"):
            bad.validate()

    def test_the_epiano_band(self):
        s = self.s
        for role in ('piano', 'comp'):
            ins = s.tracks[role].instrument
            self.assertEqual(ins.type, 'stack')
            self.assertTrue(all(L.instrument.type == 'dx7' and L.instrument.params['voice'] == 'E.PIANO 1'
                                for L in ins.params['layers']))
            self.assertIn('instrument.pedal', [t for t, _ in s.tracks[role]._auto])   # the stack holds the FM voices
        self.assertGreaterEqual(len(s.tracks['piano'].instrument.params['layers']), 2)   # level follows velocity

    def test_the_left_hand_sits_higher(self):
        lh = [n.pitch for n in self.s.tracks['comp']._notes]
        self.assertGreaterEqual(min(lh), 43)                       # G2: no muddy FM bass
        self.assertLessEqual(max(lh), 69 + 12)

    def test_scored_and_breathing(self):
        sc = composer.score(self.s, self.tune)
        self.assertEqual(sc['style'], 'new-age')
        self.assertGreater(sc['score'], 60)
        self.assertEqual(breath_gate(self.g, self.s), [])


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
