"""The endless generators (agentsound/endless): genre specs (validation, extension by data), the rule-based tune
composer (determinism, form lengths, harmony blocks and colours, melody rules), swing as an option (default off),
the performer (a Song from a tune, played by the library's players) and the quality gate."""
import copy
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import endless  # noqa: E402
from agentsound.endless import composer, genres  # noqa: E402
from agentsound.endless.run import gate  # noqa: E402
from agentsound.theory import ComposeError, chord, note  # noqa: E402

PIANO = endless.genre('jazz-piano')


def tunes(n=24, genre=PIANO, **kw):
    for sd in range(n):
        for mood in genre.moods:
            yield composer.compose(genre, sd, mood, **kw)


class GenreSpec(unittest.TestCase):
    def test_the_genres_validate(self):
        for g in endless.GENRES.values():
            self.assertIs(g.validate(), g)

    def test_a_broken_spec_is_an_error(self):
        bad = PIANO.but(name='bad')
        bad.moods['late-night']['feels'] = {'polka': 1}
        with self.assertRaisesRegex(ComposeError, "unknown feel 'polka'"):
            bad.validate()
        bad = PIANO.but(name='bad', forms={'rondo': 1})
        with self.assertRaisesRegex(ComposeError, "unknown form 'rondo'"):
            bad.validate()
        bad = PIANO.but(name='bad')
        bad.feels['ballad']['style'] = 'thrash'
        with self.assertRaisesRegex(ComposeError, 'pianist style'):
            bad.validate()
        with self.assertRaisesRegex(ComposeError, 'unknown endless genre'):
            endless.genre('polka')

    def test_but_copies_deeply(self):
        g = PIANO.but(name='copy')
        g.moods['bright']['tempo'] = 99
        self.assertNotEqual(PIANO.moods['bright']['tempo'], 99)

    def test_a_new_genre_is_data(self):
        # a 'calm waltz' generator: only waltz feels, slower, major - no new code
        g = PIANO.but(name='calm-waltz', moods={'calm': {'feels': {'waltz': 1}, 'modes': {'major': 1},
                                                         'keys': {'major': ['F', 'Bb']}, 'tempo': -10}})
        g.validate()
        t = composer.compose(g, 3)
        self.assertEqual((t.feel, t.meter, t.mood, t.mode), ('waltz', 3, 'calm', 'major'))
        self.assertIn(t.key, ('F major', 'Bb major'))

    def test_blocks_and_cells(self):
        self.assertEqual(composer.parse_block('IIm V7 IM:2'), [(2, 'm', 1.0), (7, '7', 1.0), (0, 'M', 2.0)])
        self.assertEqual(composer.parse_block('bVII7 #IVø:0.5'), [(10, '7', 1.0), (6, 'ø', 0.5)])
        for spec in ('XYZ', 'IIq7', 'V7:0.3', ''):
            with self.assertRaises(ComposeError):
                composer.parse_block(spec)
        for mode, kinds in genres.BLOCKS.items():
            for kind, table in kinds.items():
                want = {'blues': 12, 'bridge': 8, 'contrast': 8}.get(kind, 4)
                for name, spec in table.items():
                    self.assertEqual(sum(b for *_, b in composer.parse_block(spec)), want, f"{mode}/{kind}/{name}")


class Harmony(unittest.TestCase):
    def test_colours_follow_the_resolution(self):
        import random
        rng = random.Random(1)
        for _ in range(30):
            to_minor = composer.colour(composer.parse_block('VIIø III7 VIm VIm'), rng)
            self.assertIn(to_minor[1][1], genres.COLOURS['7_minor'])
            to_major = composer.colour(composer.parse_block('IIm V7 IM:2'), rng)
            self.assertIn(to_major[1][1], genres.COLOURS['7_major'])
            self.assertIn(to_major[2][1], genres.COLOURS['M_tonic'])

    def test_tritone_substitution(self):
        import random
        out = composer.colour(composer.parse_block('IIm V7 IM:2'), random.Random(2), tritone=1.0)
        self.assertEqual(out[1][0], 1)                        # G7 -> Db7 in C
        self.assertIn(out[1][1], genres.COLOURS['7_sub'])

    def test_changes_parse_and_fill_the_form(self):
        for t in tunes(12):
            fd = genres.FORMS[t.form]
            self.assertEqual(tuple(t.parts), fd['parts'])
            stretch = 2 if t.meter == 3 else 1
            for p in t.parts:
                self.assertAlmostEqual(t.part_beats(p), fd['bars'] * stretch * t.meter, msg=f"{t.title} {p}")
                for sym, _ in t.changes[p]:
                    chord(sym)
            if t.form == 'blues':
                self.assertEqual(t.meter, 4)
            for a in [p for p in t.parts if p.startswith('A')][1:]:   # the A sections open alike
                self.assertEqual(t.changes[a][:2], t.changes[t.parts[0]][:2])


class Melody(unittest.TestCase):
    def test_deterministic(self):
        a = composer.compose(PIANO, 42, 'bright').to_dict()
        b = composer.compose(PIANO, 42, 'bright').to_dict()
        self.assertEqual(a, b)
        self.assertNotEqual(a, composer.compose(PIANO, 43, 'bright').to_dict())

    def test_the_rules_hold(self):
        lo, hi = note(PIANO.melody['register'][0]), note(PIANO.melody['peak'])   # A4 .. the bridge's peak Db6
        total = bad = 0
        for t in tunes(16):
            for i, p in enumerate(t.parts):
                notes = t.melody[p]
                self.assertTrue(notes, f"{t.title} {p}: no melody")
                self.assertTrue(all(0 <= s and s + d <= t.part_beats(p) + 1e-6 for s, d, _ in notes))
                harm = composer.Harm(t.changes[p])
                issues = composer.melody_issues(notes, harm, lo - 2, hi + 2, meter=t.meter)
                total += 1
                bad += bool(issues)
        self.assertEqual(bad, 0, f"{bad} of {total} parts break the melody rules")

    def test_strong_beats_sit_on_chord_tones(self):
        for t in tunes(8):
            for p in t.parts:
                harm = composer.Harm(t.changes[p])
                for s, d, n in t.melody[p]:
                    if d >= 1.0:
                        ci = harm.under(s, d)
                        self.assertIn(n % 12, ci.core | ci.tensions, f"{t.title} {p} beat {s}: {n} over {ci.sym}")

    def test_the_last_part_ends_on_the_tonic(self):
        for t in tunes(16):
            p = t.parts[-1]
            harm = composer.Harm(t.changes[p])
            last = max(t.melody[p])
            ci = harm.under(last[0], last[1])
            tonic = chord(t.end_chord).root % 12
            if ci.root == tonic:
                self.assertIn((last[2] - tonic) % 12, (0, 3, 4, 7), t.title)

    def test_phrases_breathe(self):
        # rests inside every part: the melody is not a wall of notes
        for t in tunes(8):
            for p in t.parts:
                notes = t.melody[p]
                sounding = sum(d for _, d, _ in notes)
                self.assertLess(sounding / t.part_beats(p), 0.93, f"{t.title} {p}")

    def test_motif_comes_back(self):
        # the A sections share their first two bars (the hook), the motif is A1's opening
        for t in tunes(8):
            a = [p for p in t.parts if p.startswith('A')]
            first = [n for n in t.melody[a[0]] if n[0] < 2 * t.meter]
            self.assertEqual(t.motif, first)
            for p in a[1:]:
                if t.changes[p][:2] == t.changes[a[0]][:2] and t.form != 'blues':
                    self.assertEqual([n for n in t.melody[p] if n[0] < 2 * t.meter], first)

    def test_titles_are_varied(self):
        names = {composer.compose(PIANO, sd).title for sd in range(30)}
        self.assertGreater(len(names), 25)


class Arc(unittest.TestCase):
    """The plan layer: the form's tension arc, the climax, the hook and the counter-motif - measured by shape()."""

    @classmethod
    def setUpClass(cls):
        cls.tunes = list(tunes(16))
        cls.shapes = [composer.shape(t) for t in cls.tunes]

    def test_arc_at_and_targets(self):
        curve = ((0.0, 0.0), (0.5, 1.0), (1.0, 0.5))
        self.assertAlmostEqual(composer.arc_at(curve, 0.25), 0.5)
        self.assertAlmostEqual(composer.arc_at(curve, 0.75), 0.75)
        self.assertAlmostEqual(composer.arc_at(curve, 2.0), 0.5)
        lo, hi = PIANO.arc['targets']['touch']
        self.assertAlmostEqual(composer.targets(PIANO, 0.0)['touch'], lo)
        self.assertAlmostEqual(composer.targets(PIANO, 1.0)['touch'], hi)

    def test_a_broken_arc_is_an_error(self):
        bad = PIANO.but(name='bad')
        bad.arc['forms']['AABA'] = ((0.2, 0.5), (1.0, 0.5))
        with self.assertRaisesRegex(ComposeError, 'arc forms/AABA'):
            bad.validate()
        bad = PIANO.but(name='bad')
        del bad.arc['forms']['blues']
        with self.assertRaisesRegex(ComposeError, "no curve for form 'blues'"):
            bad.validate()

    def test_one_planned_climax(self):
        # the tune's single highest note sits in the phrase the arc planned for it, near 2/3 of the head (AABA: the
        # end of the bridge; ABAC: the climbing C; the blues: where its second chorus varies (genres.SECOND_CHORUS) -
        # its rewritten bars 9-12, its second statement (bars 5-6), or the first chorus's answer)
        # - or, drawn (genres.PEAK_PART), in the form's last section: an AABA's last A climbs to it in its second half
        where = {'AABA': (0.58, 0.72), 'ABAC': (0.75, 0.9), 'answer': (0.78, 0.95), 'second': (0.65, 0.8),
                 'early': (0.3, 0.45), 'last': (0.78, 0.97)}
        for t, sh in zip(self.tunes, self.shapes):
            c = sh['climax']
            self.assertTrue(c['single'], f"{t.title}: {c}")
            self.assertTrue(c['planned'], f"{t.title}: {c} vs {t.climax}")
            last = t.form == 'AABA' and t.climax['part'] == t.parts[-1]
            lo, hi = where['last' if last else t.second if t.form == 'blues' else t.form]
            self.assertTrue(lo <= c['x'] <= hi, f"{t.title} {t.form} {t.second}: climax at {c['x']}")
            self.assertEqual(t.climax['pitch'], max(n[2] for p in t.parts for n in t.melody[p]))

    def test_climax_is_approached_and_released(self):
        for t in self.tunes:
            mel = t.melody[t.climax['part']]
            k = next(i for i, n in enumerate(mel) if n[0] == t.climax['beat'])
            if k + 1 < len(mel):
                self.assertLess(mel[k + 1][2], mel[k][2], t.title)           # the release falls
            if k:
                self.assertLessEqual(mel[k][2] - mel[k - 1][2], 7, t.title)   # the approach climbs (no wild leap)

    def test_the_hook_recurs(self):
        tagged = 0
        for t, sh in zip(self.tunes, self.shapes):
            n_a = sum(1 for p in t.parts if p[0] == 'A')
            self.assertGreaterEqual(sh['hook']['head'], n_a, t.title)         # stated in every A
            tagged += sh['hook']['tag'] > 0
        self.assertGreater(tagged / len(self.tunes), 0.7)                   # its head developed in the ending

    def test_the_theme_is_restated(self):
        # every later A plays the A1 note for note up to its cadence (re-fitted where the changes differ: the same
        # rhythm, a note held into a chord it does not fit released); only its last two bars (a waltz: four) are its
        # own - the last A carrying the climax (genres.PEAK_PART) restates its first phrase; a blues head repeats bars
        # 1-8 - or bars 1-4 when its second chorus rewrites the second statement (SECOND_CHORUS 'second')
        own = varied = 0
        for t in self.tunes:
            a1 = t.parts[0]
            for p in [p for p in t.parts[1:] if p[0] == 'A']:
                keep = (4 if t.second == 'second' else 8) * t.meter if t.form == 'blues' else \
                    max(1, int(t.part_beats(a1) / (2 * t.meter)) // 2 - 1) * 2 * t.meter \
                    if t.climax.get('part') == p else \
                    t.part_beats(a1) - 2 * t.meter * (2 if t.meter == 3 else 1)
                front = lambda q: [x for x in t.melody[q] if x[0] < keep - 1e-6]  # noqa: E731
                self.assertEqual([x[0] for x in front(p)], [x[0] for x in front(a1)], f"{t.title} {p}")
                self.assertTrue(all(x[1] <= y[1] + 1e-6 for x, y in zip(front(p), front(a1))), f"{t.title} {p}")
                same = composer._slice_changes(t.changes[p], 0, keep) == composer._slice_changes(t.changes[a1], 0, keep)
                if same:
                    self.assertEqual(front(p), front(a1), f"{t.title} {p}")
                own += 1
                varied += [x for x in t.melody[p] if x[0] >= keep] != [x for x in t.melody[a1] if x[0] >= keep]
        self.assertGreater(varied, 0.6 * own)                                # the cadence bars are its own

    def test_a_blues_chorus_is_AAB(self):
        # bars 5-8 restate bars 1-4 (the rhythm; the pitches re-fitted to the IV, a note held into a chord it does
        # not fit released at the change)
        for t in self.tunes:
            if t.form != 'blues':
                continue
            m = t.melody['A1']
            first = [(round(s, 3), d) for s, d, _ in m if s < 16]
            second = [(round(s - 16, 3), d) for s, d, _ in m if 16 <= s < 32]
            self.assertEqual([x[0] for x in first], [x[0] for x in second], t.title)
            self.assertTrue(all(y[1] <= x[1] + 1e-6 for x, y in zip(first, second)), t.title)

    def test_the_bridge_has_a_counter_motif(self):
        # the B's own rhythm (not the hook's), the same in every contrast phrase (a waltz bridge has two)
        for t in self.tunes:
            if 'B' not in t.parts:
                continue
            ub = 2 * t.meter
            ioi = lambda ns: [round(b[0] - a[0], 3) for a, b in zip(ns, ns[1:])]  # noqa: E731
            self.assertTrue(t.counter, t.title)
            rhythm = lambda ns: [(round(s, 3), d) for s, d, _ in ns]  # noqa: E731  (onsets in the unit + lengths)
            self.assertNotEqual(rhythm(t.counter), rhythm(t.motif), t.title)
            if t.meter == 3:
                second = [(s - 4 * ub, d, p) for s, d, p in t.melody['B'] if 4 * ub <= s < 5 * ub]
                self.assertEqual(ioi(second)[:1], ioi(t.counter)[:1], t.title)   # (its return varied:
                                                                                # genre.melody['bridge_return'])

    def test_the_register_follows_the_arc(self):
        follows = sum(sh['arc']['follows'] for sh in self.shapes)
        self.assertGreater(follows / len(self.shapes), 0.85)
        rs = [sh['arc']['part_pitch_r'] for sh in self.shapes if sh['arc']['part_pitch_r'] is not None]
        self.assertGreater(sum(rs) / len(rs), 0.4)

    def test_the_plan_is_deterministic_and_keeps_the_rolls(self):
        # the plan has its own dice: the seed still rolls the same key / tempo / feel / form / title
        t = composer.compose(PIANO, 106, 'late-night', 0.6)
        self.assertEqual((t.title, t.key, t.tempo, t.form, t.feel), ('A Window for Gay Street', 'G minor', 73,
                                                                     'ABAC', 'ballad'))
        self.assertEqual(composer.compose(PIANO, 106, 'late-night', 0.6).to_dict(), t.to_dict())
        # a plan pins the form and the feel (the blind test's slots)
        t = composer.compose(PIANO, 106, None, 0.6, plan={'mood': 'late-night', 'feel': 'straight', 'form': 'AABA'})
        self.assertEqual((t.mood, t.form, t.feel, t.key), ('late-night', 'AABA', 'straight', 'G minor'))

    def test_the_performance_follows_the_plan(self):
        t = composer.compose(PIANO, 106, None, 0.6, plan={'mood': 'late-night', 'feel': 'straight', 'form': 'AABA'})
        sh = composer.shape(t, endless.song(t))
        self.assertEqual(sh['issues'], [])
        played = sh['played']
        self.assertGreater(played['vel_r'], 0.3)                            # the touch follows the part levels
        b = played['parts']['B']
        self.assertEqual(max(p['vel'] for p in played['parts'].values()), b['vel'])
        # the solo: starts sparse with the hook quoted, builds (denser, higher, louder), resolves into the head
        s1, s2, s3 = played['solo']
        self.assertLess(sh['hook']['solo_first'], 1.0)                     # in the first bar (anywhere in it)
        self.assertLess(s1['onsets_per_bar'], max(s2['onsets_per_bar'], s3['onsets_per_bar']))
        self.assertLess(s1['pitch'], max(s2['pitch'], s3['pitch']))
        self.assertLess(s1['vel'], max(s2['vel'], s3['vel']))


class Frame(unittest.TestCase):
    """Blind test round 2: the intro / tag are the tune's own material, the solo plays the chart (one consistent
    reharm at most), a dynamic plan drawn per tune (a 2-bar shout in some)."""

    def test_intro_and_tag_are_their_own(self):
        kinds, approaches, frames = set(), set(), set()
        for t in tunes(8):
            top = max(n[2] for p in t.parts for n in t.melody[p])
            kinds.add(t.intro['kind'])
            self.assertIn(t.intro['kind'], genres.INTROS[t.mode])
            self.assertEqual(composer._copy_of(t.intro['melody'], t.intro['changes'], t), 0, t.title)
            self.assertEqual(composer._copy_of(t.tag['melody'], t.tag['changes'], t), 0, t.title)
            stretch = 2 if t.meter == 3 else 1
            for fr in (t.intro, t.tag):
                self.assertAlmostEqual(composer._beats(fr['changes']), 4 * t.meter * stretch)
                self.assertTrue(fr['melody'] and all(n[2] < top for n in fr['melody']), t.title)   # under the head
            # the tag reprises the intro's vamp (or another vamp / the A's turnaround: TAG_FRAMES - blind round 7: the
            # tag the intro's reprise in every piece) and turns into the end chord through a drawn approach
            # (TAG_APPROACH: the tritone sub, the backdoor bVII, the minor plagal IVm6, a deceptive V-bVI, a cold stop)
            frames.add(t.tag['frame'])
            if t.tag['frame'] == 'reprise':
                self.assertEqual(t.tag['changes'][0], t.intro['changes'][0])
            ap = t.tag['approach']
            approaches.add(ap)
            step = {'tritone': 1, 'backdoor': 10, 'plagal': 5, 'deceptive': 8, 'cold': 7}[ap]
            self.assertEqual((chord(t.tag['changes'][-1][0]).root - chord(t.end_chord).root) % 12, step, t.title)
            self.assertIn(chord(t.end_chord).quality, genres.ENDINGS[t.mode])
            last = max(t.tag['melody'])
            if ap == 'cold':                                                   # a cold stop: struck short
                self.assertLess(last[0] + last[1], composer._beats(t.tag['changes']) - 1.0)
            else:                                                              # its last note held
                self.assertAlmostEqual(last[0] + last[1], composer._beats(t.tag['changes']))
        self.assertGreaterEqual(len(kinds), 4)
        self.assertGreaterEqual(len(approaches), 4)                          # not the bII7#11 in every tag
        self.assertGreaterEqual(len(frames), 2)

    def test_one_consistent_reharm(self):
        n, slots = 0, set()
        for sd in range(100, 124):
            t = composer.compose(PIANO, sd)
            s = endless.song(t)
            solo, out = s['solo'], s['out']
            v = [p.name for p in solo.parts if p.name.endswith('v')]
            self.assertLessEqual(len(v), 1)
            if t.solo_changes:
                n += 1
                (p, ch), = t.solo_changes.items()
                self.assertIn(p, t.out_parts)                                # a part the head out plays
                last_chorus = solo.parts[-(1 if t.form == 'blues' else len(t.parts)):]
                if t.reharm_in == 'both':                                    # the last solo chorus (or the head
                    self.assertIn(p + 'v', [x.name for x in last_chorus])   # out alone) ...
                self.assertIn(p + 'v', [x.name for x in out.parts])         # ... and the head out alike
                self.assertNotEqual(t.out_melody[p], t.melody[p])          # with a new melody note
                slots.add((p, [i for i, (a, b) in enumerate(zip(ch, t.changes[p])) if a != b][0] - len(ch)))
            r = composer.tells(s, t)
            self.assertEqual(r['isolated'], 0, t.title)
        self.assertTrue(4 <= n <= 18, n)
        self.assertGreaterEqual(len(slots), 3, slots)                       # not one fixed slot

    def test_the_dynamic_plan_is_a_distribution(self):
        # blind round 3: one plan in every tune read as a formula - the plans are drawn by weight, a shout ~25 %
        shouts, plans = 0, set()
        for sd in range(100, 124):
            t = composer.compose(PIANO, sd)
            plans.add(t.dynamics)
            self.assertIn(t.dynamics, PIANO.plan['dynamics'])
            if not t.shout:
                continue
            shouts += 1
            first = t.out_parts[0]
            top = max(n[2] for p in t.parts for n in t.melody[p])
            self.assertGreater(max(n[2] for n in t.out_melody[first]), top, t.title)   # the shout's top: the tune's
        self.assertTrue(2 <= shouts <= 11, shouts)
        self.assertGreaterEqual(len(plans), 3)

    def test_the_peak_sits_in_the_solo_and_a_shout_is_two_bars(self):
        # the plan decides: a 'solo' plan peaks in the solo (at or above the head), a late / shout plan in the head
        # out (the solo may stay under the head: a slow build, less is more); the head out near the head
        for sd, sw in ((102, None), (105, None), (106, 0.6), (107, 0.6), (110, None)):
            t = composer.compose(PIANO, sd, None, sw)
            s = endless.song(t)
            r = composer.tells(s, t)
            self.assertTrue(0.55 <= r['peak_x'] <= 0.85, (t.title, r['peak_x']))
            if t.dynamics == 'solo':
                self.assertGreaterEqual(r['solo_db'], 0.0, t.title)
            # the head out near the head (from -2 dB: since the written dynamics it comes down into a soft ending)
            self.assertTrue(-2.0 <= r['out_db'] <= 2.5, (t.title, r['out_db']))
        t = next(t for t in (composer.compose(PIANO, sd) for sd in range(100, 140)) if t.shout)
        s = endless.song(t)
        out = s['out']
        loud = [k for k in range(int(out.parts[0].bars))
                if max((n.vel for n in s.tracks['piano']._notes
                        if out.start + k * t.meter <= n.start < out.start + (k + 1) * t.meter), default=0) >= 112]
        self.assertTrue(1 <= len(loud) <= 2 and (len(loud) == 1 or loud[1] - loud[0] == 1), (t.title, loud))

    def test_the_highest_note_sits_in_the_planned_peak(self):
        # the piece's highest right-hand note (before the tag) lands where the plan puts the peak: the solo (a block-
        # chord chorus owns the top when the arc has no climax stage; the solo's peak note lifted over the head's top)
        # or the head out's lifted part - never the head (a medium swing demo: 34 % in, in the head)
        for sd, mood, sw in ((47, 'bright', True), (51, 'late-night', None), (54, 'bright', True),
                             (50, 'bright', True)):
            t = composer.compose(PIANO, sd, mood, sw)
            s = endless.song(t)
            ns = [n for n in s.tracks['piano']._notes if n.start < s['tag'].start]
            top = max(n.pitch for n in ns)
            first = min(n.start for n in ns if n.pitch == top)
            want = 'out' if PIANO.plan['dynamics'][t.dynamics].get('out_peak') else 'solo'
            self.assertTrue(s[want].start <= first < s[want].end, (t.title, t.dynamics, t.solo_shape, first))

    def test_the_tells_measure(self):
        t = composer.compose(PIANO, 106, None, 0.6, plan={'mood': 'late-night', 'feel': 'straight', 'form': 'AABA'})
        r = composer.tells(endless.song(t), t)
        for k in ('head_5gram', 'solo_entropy', 'dyn_range', 'peak_x', 'top_x', 'lh_silent', 'reharms', 'isolated',
                  'intro_copy', 'tag_copy', 'cell_max', 'quarter_runs'):
            self.assertIn(k, r)
        self.assertEqual((r['intro_copy'], r['tag_copy'], r['isolated']), (0, 0, 0))
        self.assertGreater(r['head_5gram'], 0.1)

    def test_the_round_3_tells(self):
        # the shared players (blind round 3): line velocity by contour not beat, no repeated notes in lines, empty
        # solo bars only as breaths, the chord under strong notes, one fast figure per chorus, a varied left hand
        rs, shell = [], []
        for sd in range(100, 106):
            t = composer.compose(PIANO, sd, None, 0.6 if sd % 2 else None)
            rs.append(composer.tells(endless.song(t), t))
            if PIANO.feels[t.feel]['lh'] == 'shell':
                shell.append(rs[-1]['lh_rootless'])

        def mean(k):
            return sum(r[k] for r in rs) / len(rs)
        self.assertLess(abs(mean('vel_onoff')), 6.0)          # (round 3: 11.6; a few head lines weigh much here)
        self.assertTrue(0.3 <= mean('vel_zigzag') <= 0.6, mean('vel_zigzag'))
        self.assertLess(mean('vel_jumps'), 0.15)
        self.assertLess(mean('rep_notes'), 0.04)
        # silence belongs to a phrase end (endless r6: "an endless monotone line"), a whole silent solo bar at most
        # once a chorus (blind round 6: 4-10 per solo read as a solo falling apart; round 3: sparseness by rule)
        self.assertLessEqual(mean('empty_64'), 6.0, mean('empty_64'))
        self.assertLess(mean('clash_total'), 1.5)
        self.assertLessEqual(mean('orn_chorus'), 1.5)
        self.assertEqual(sum(r['orn_intro_end'] + r['orn_loud'] for r in rs), 0)
        self.assertGreater(sum(shell) / len(shell), 0.2)                   # the shell left hand: a texture

    def test_cells_have_no_quarter_blocks(self):
        for name_, fam in genres.CELLS.items():
            if name_ in ('hymn', 'march'):                # the organ's chorale / march cells: quarters by design
                continue
            for role in ('motif', 'line'):
                for name, cell in fam[role].items():
                    self.assertNotIn('2,2,2,2', ','.join(str(x) for x in cell), name)


class RoundFour(unittest.TestCase):
    """Blind round 4: heads with goals, the second chorus varied by phrase function, solo shapes as a distribution,
    licks once per piece and per set, chart variants, tag approaches and final chords drawn, the feel / form pairing."""

    @classmethod
    def setUpClass(cls):
        cls.tunes = [composer.compose(PIANO, sd, None, 0.6 if sd % 2 else None) for sd in range(100, 140)]

    def test_heads_have_goals(self):
        circ, nct, parts, bad = [], [], 0, 0
        for t in self.tunes:
            ph = 4 * t.meter
            for p in t.parts:
                parts += 1
                bad += bool(composer._style_issues(t.melody[p], t.meter, t.part_beats(p)))
                harm = composer.Harm(t.changes[p])
                for k in range(int(t.part_beats(p) // ph)):
                    ns = [n for n in t.melody[p] if k * ph <= n[0] < (k + 1) * ph]
                    if len(ns) >= 4:
                        circ.append(max(sum(1 for n in ns if n[2] == q[2]) for q in ns) / len(ns))
                        nct.append(any(n[2] % 12 not in harm.under(*n[:2]).core and 0 < abs(m[2] - n[2]) <= 2
                                       and m[2] % 12 in harm.under(*m[:2]).core
                                       and (n[1] >= 1 or n[0] % t.meter == 0 or (t.meter == 4 and n[0] % 4 == 2))
                                       for n, m in zip(ns, ns[1:])))
        self.assertLess(bad / parts, 0.15, 'the rhythm budget / no circling hold in most parts')
        self.assertLess(sum(circ) / len(circ), 0.3)
        self.assertGreater(sum(nct) / len(nct), 0.7, 'a resolved tension on a strong beat in most phrases')

    def test_the_bridge_has_its_own_register_and_rhythm(self):
        regs, longs = [], []
        for t in self.tunes:
            if t.form != 'AABA':
                continue
            a, b = t.melody['A1'], t.melody['B']
            regs.append(sum(n[2] for n in b) / len(b) - sum(n[2] for n in a) / len(a))
            longs.append(sum(n[1] >= 1.5 for n in b) / len(b) - sum(n[1] >= 1.5 for n in a) / len(a))
        self.assertGreater(sum(regs) / len(regs), 1.0)
        self.assertGreater(sum(longs) / len(longs), 0.0, 'long notes against the moving lines')

    def test_the_blues_second_chorus_varies_by_function(self):
        seen, endings = set(), 0
        blues = [composer.compose(PIANO, sd, 'blue') for sd in range(60)]
        blues = [t for t in blues if t.form == 'blues']
        for t in blues:
            seen.add((t.second, t.climax['part']))
            endings += t.changes['A2'] != t.changes['A1']
            self.assertEqual(len(t.solo_charts), genres.FORMS['blues']['solo'])
        self.assertGreaterEqual(len({s for s, _ in seen}), 3, seen)
        self.assertGreaterEqual(len({p for _, p in seen}), 2, 'the climax not always in chorus 2')
        self.assertTrue(0.5 <= endings / len(blues) <= 0.95, 'a second ending in most blues heads')

    def test_solo_shapes_are_a_distribution(self):
        from agentsound.endless import perform
        shapes = {t.solo_shape for t in self.tunes}
        self.assertGreaterEqual(len(shapes), 5, shapes)
        double = [t for t in self.tunes if t.double]
        self.assertTrue(0.15 <= len(double) / len(self.tunes) <= 0.45, len(double))
        where = {[st for st, *_ in perform.solo_arc(t, PIANO)].index('burst') / len(perform.solo_arc(t, PIANO))
                 for t in double}
        self.assertGreaterEqual(len(where), 3, 'double time not at a fixed place')
        for t in self.tunes:
            if not t.double:
                self.assertNotIn('burst', [st for st, *_ in perform.solo_arc(t, PIANO)])

    def test_licks_once_per_piece_and_less_in_the_next_tune(self):
        from agentsound.endless import perform
        prev = None
        for t in self.tunes[:6]:
            s = perform.build(t, prev=prev)
            kinds = [k for _, k, _ in s.endless_memory.fast]
            self.assertEqual(len(kinds), len(set(kinds)), f"{t.title}: a fast figure twice {kinds}")
            if prev is not None:
                self.assertEqual(s.endless_memory.avoid, {k for _, k, _ in prev.endless_memory.fast})
            prev = s

    def test_chart_variants(self):
        ch = [('Dm7', 4.0), ('G7', 4.0), ('Cmaj7', 8.0)]
        roots = {}
        for kind in genres.CHART_VARIANTS:
            v = composer.variant(ch, kind, 0, False, 4.0)
            self.assertIsNotNone(v, kind)
            self.assertAlmostEqual(composer._beats(v), 16.0)
            self.assertEqual(v[-1], ('Cmaj7', 8.0))
            roots[kind] = [chord(s).root % 12 for s, _ in v[:-1]]
        self.assertEqual(roots['tritone'], [2, 1])
        self.assertEqual(roots['backdoor'], [5, 10])
        self.assertEqual(roots['plagal'], [5, 5])
        self.assertEqual(roots['iiV'], [2, 2, 7])
        self.assertIsNone(composer.variant([('Cmaj7', 4.0)], 'tritone', 0, False, 4.0))

    def test_tags_and_endings_are_drawn(self):
        self.assertGreaterEqual(len({t.tag['approach'] for t in self.tunes}), 4)
        self.assertLess(sum(t.tag['approach'] == 'tritone' for t in self.tunes) / len(self.tunes), 0.5)
        self.assertGreaterEqual(len({t.end_kind for t in self.tunes}), 4)

    def test_the_feel_suits_the_form(self):
        pairs = [(t.feel, t.form) for t in (composer.compose(PIANO, sd) for sd in range(300))]
        blues = [f for f, form in pairs if form == 'blues']
        bossa = [form for f, form in pairs if f == 'bossa']
        self.assertLess(blues.count('bossa') / len(blues), 0.06)
        self.assertGreater((blues.count('straight') + blues.count('shuffle')) / len(blues), 0.6)
        self.assertGreater(sum(f != 'blues' for f in bossa) / len(bossa), 0.9)
        self.assertNotIn(('shuffle', 'AABA'), pairs)

    def test_the_round_4_tells_measure(self):
        t = self.tunes[0]
        r = composer.tells(endless.song(t), t)
        for k in ('dir_run', 'ct_run5', 'onbeat_ct', 'dt_bars', 'peak_climb', 'block_run', 'lick_rep', 'circle',
                  'ph_peak_sd', 'period_peak', 'nct_ph', 'endings', 'cell8', 'vary_bar', 'chart_vars', 'solo_shape',
                  'tag_approach', 'end_kind', 'feel_form'):
            self.assertIn(k, r)


class SetPlan(unittest.TestCase):
    """The stream level: a set of tunes along the set arc (contrast, an energy wave)."""

    def check(self, plan, genre=PIANO):
        feels = [p['feel'] for p in plan]
        for a, b in zip(plan, plan[1:]):
            self.assertNotEqual(a['feel'], b['feel'], plan)                 # contrast: never the same feel twice
            self.assertNotEqual(a['key'].split()[0], b['key'].split()[0], plan)
        self.assertNotIn(('ballad', 'ballad'), list(zip(feels, feels[1:])))
        e = [p['energy'] for p in plan]
        n = len(plan)
        top = e.index(max(e))
        self.assertTrue(0.3 * (n - 1) <= top <= 0.8 * (n - 1), e)          # the highlight in the middle
        self.assertEqual(e[-1], min(e))                                      # a quiet closer
        self.assertTrue(0.4 <= e[0] <= 0.7, e)                               # a medium opener
        fe = [genre.feels[f]['energy'] for f in feels]
        self.assertGreater(composer._corr(e, fe), 0.6)                     # the feels follow the energy wave
        for p in plan:
            lo, hi = genre.feels[p['feel']]['tempo']
            self.assertTrue(lo <= p['tempo'] <= hi)
            self.assertIn(p['feel'], genre.moods[p['mood']]['feels'])

    def test_sets_follow_the_arc(self):
        for sd in range(12):
            for n in (4, 6, 10):
                self.check(composer.set_plan(PIANO, n, sd))

    def test_a_ballad_follows_an_up_tempo_tune_and_closes(self):
        plan = composer.set_plan(PIANO, 10, 3)
        self.assertEqual(plan[-1]['feel'], 'ballad')
        k = [p['feel'] for p in plan].index('ballad')
        self.assertGreater(PIANO.feels[plan[k - 1]['feel']]['energy'], 0.5)

    def test_mood_pins_the_set(self):
        plan = composer.set_plan(PIANO, 6, 5, mood='bright')
        self.assertEqual({p['mood'] for p in plan}, {'bright'})
        for a, b in zip(plan, plan[1:]):
            self.assertNotEqual(a['feel'], b['feel'])

    def test_tunes_play_the_plan(self):
        plan = composer.set_plan(PIANO, 4, 9)
        energies = []
        for k, slot in enumerate(plan):
            t = composer.compose(PIANO, 100 + k, plan=slot)
            self.assertEqual((t.mood, t.feel, t.tempo, t.key, t.energy), (slot['mood'], slot['feel'], slot['tempo'],
                                                                         slot['key'], slot['energy']))
            energies.append(t.energy)
        self.assertEqual(energies, [p['energy'] for p in plan])

    def test_the_set_plan_prints(self):
        text = composer.describe_set(composer.set_plan(PIANO, 4, 1))
        self.assertEqual(len(text.splitlines()), 4)
        self.assertIn('BPM', text)


class Swing(unittest.TestCase):
    def test_off_by_default(self):
        for t in tunes(8):
            self.assertIsNone(t.swing)

    def test_optional(self):
        for t in tunes(8, swing=True):
            want = None if not PIANO.feels[t.feel].get('swing', True) else PIANO.swing
            self.assertEqual(t.swing, want, t.feel)
        t = composer.compose(PIANO, 5, 'late-night', swing=0.58)
        self.assertEqual(t.swing, 0.58 if PIANO.feels[t.feel]['swing'] else None)

    def test_the_song_swings_only_when_asked(self):
        t = composer.compose(PIANO, 101, 'late-night')
        self.assertEqual(endless.song(t).tracks['piano']._groove.swing, 0.5)
        t = composer.compose(PIANO, 101, 'late-night', swing=True)
        self.assertEqual(endless.song(t).tracks['piano']._groove.swing, PIANO.swing)


class Perform(unittest.TestCase):
    def test_a_song_from_a_tune(self):
        t = composer.compose(PIANO, 11, 'blue')
        s = endless.song(t)
        self.assertEqual([x.name for x in s.sections], ['intro', 'head', 'solo', 'out', 'tag', 'end'])
        self.assertEqual(s['head'].length, sum(t.part_beats(p) for p in t.parts))
        piano = s.tracks['piano']
        for sec in s.sections[:-1]:
            self.assertTrue(any(sec.start <= n.start < sec.end for n in piano._notes), sec.name)
        render = s.compile()
        self.assertEqual({tr['id'] for tr in render['tracks']}, {'piano', 'comp'})
        self.assertFalse([w for w in s.warnings if 'failed' in w])

    def test_blues_solo_choruses_fit_the_tempo(self):
        for sd in range(40):
            t = composer.compose(PIANO, sd, 'blue')
            if t.form == 'blues':
                s = endless.song(t)
                choruses = round(s['solo'].length / t.part_beats('A1'))
                self.assertTrue(1 <= choruses <= 3)
                self.assertLessEqual(s['solo'].length * 60 / t.tempo, 110)
                return
        self.skipTest('no blues in 40 seeds')

    def test_the_trio_has_bass_and_drums(self):
        t = composer.compose(endless.genre('jazz-trio'), 3, 'late-night')
        s = endless.song(t)
        self.assertTrue(s.tracks['bass']._notes)
        self.assertTrue(s.tracks['drums']._notes)


class Breathing(unittest.TestCase):
    """The user on the r6 tunes: "sounds like an endless monotone line of notes" - the playing breathes: real silence
    between the solo's phrases, phrases that differ in level, decoration as the exception (composer.breath)."""

    @classmethod
    def setUpClass(cls):
        cls.rs = []
        for sd in range(100, 106):
            t = composer.compose(PIANO, sd, None, 0.6 if sd % 2 else None)
            s = endless.song(t)
            cls.rs.append((t, s, composer.breath(s)))

    def mean(self, f):
        return sum(f(b) for _, _, b in self.rs) / len(self.rs)

    def test_the_breath_measure(self):
        b = self.rs[0][2]
        for k in ('att_bar', 'att_sd', 'att_cv4', 'quiet1', 'quiet1_sec', 'quiet1_both', 'rest_half', 'rest_bar',
                  'rest_max', 'ph_on', 'ph_beats', 'long_share', 'lh_bar', 'lh_still', 'orn32', 'ph_reg', 'ph_vel',
                  'ph_den'):
            self.assertIn(k, b)
        self.assertEqual(set(b['att_bar']), {'head', 'solo', 'out'})

    def test_the_solo_breathes(self):
        # in balance (blind round 6: the breath fix overshot - 4-10 silent bars per solo, the solo sparser than the
        # head): the solo breathes between its lines, a beat or two; it is denser than the head; the head keeps its
        # phrase-end breaths (the user's "b sounds better")
        self.assertTrue(0.15 <= self.mean(lambda b: b['quiet1_sec']['solo']) <= 0.42)
        self.assertGreater(self.mean(lambda b: b['quiet1_sec']['head']), 0.3)
        rs = []
        for t, s, _ in self.rs:
            r = composer.tells(s, t)
            rs.append(r)
            self.assertLessEqual(r['single_run'], 3, t.title)                  # breaths, never a solo that stops
            self.assertLessEqual(r['sil_ch_max'], 3, t.title)
        self.assertLessEqual(sum(r['sil_ch'] for r in rs) / len(rs), 1.5)
        self.assertGreaterEqual(sum(r['dens_ratio'] for r in rs) / len(rs), 1.3)
        self.assertGreaterEqual(sum(r['long16'] for r in rs) / len(rs), 0.6)  # a long line in most choruses

    def test_decoration_is_the_exception(self):
        self.assertLess(self.mean(lambda b: b['orn32']), 7.9)                   # (r6, these seeds: 7.9 per 32 bars;
        # r8: 7.7 - the heads' 'tail' endings, the longer answer lines (ANSWER_HOLD); pro2 5.6-7.2: watch it)

    def test_the_head_phrases_differ_in_level(self):
        from agentsound.endless import perform
        for t, _, _ in self.rs:
            for p in t.parts:
                lv = [v for _, v in perform.phrase_levels(t, p, PIANO.plan, t.seed)]
                self.assertEqual(max(lv), 0.0)                                   # the loudest at the plan's level
                self.assertGreaterEqual(min(lv), -PIANO.plan['head']['phrase_touch']['depth'])
                self.assertLess(min(lv), -1.0, (t.title, p, lv))                  # the others breathe down


class Gate(unittest.TestCase):
    def report(self, **over):
        r = {'global': {'clicks': 0, 'lufsIntegrated': -15.5},
             'nodes': [{'id': 'piano', 'dynamics': {'kind': 'lead', 'flat': False, 'dynamicsDb': 9.0},
                        'silentNotes': {'silent': 0, 'notes': 900}},
                       {'id': 'comp', 'dynamics': {'kind': 'bass', 'flat': False},
                        'silentNotes': {'silent': 0, 'notes': 300}}],
             'warnings': [{'severity': 'warn', 'code': 'dry_mix', 'message': 'dry'}]}
        for k, v in over.items():
            r[k] = v
        return r

    def test_shared_verdict_boundaries(self):
        from pathlib import Path
        from types import SimpleNamespace
        import json
        from agentsound.verdicts import evaluate
        cases = json.loads((Path(__file__).parents[1] / 'fixtures/verdicts.json').read_text())
        genre = SimpleNamespace(band={'loudness': (-20, -10)})
        for c in cases:
            with self.subTest(c['name']):
                rep = c['report']
                rep = dict(rep, findings=evaluate(rep))
                failures = gate(rep, genre)
                lufs = rep.get('deliveryMetrics', rep['global'])['lufsIntegrated']
                self.assertEqual(bool(failures), not -20 <= lufs <= -10)

    def test_passes_a_clean_report(self):
        self.assertEqual(gate(self.report(), PIANO), [])

    def test_fails(self):
        r = self.report()
        r['global'] = dict(r['global'], clicks=2)
        self.assertTrue(any('clicks' in x for x in gate(r, PIANO)))
        r = copy.deepcopy(self.report())
        r['nodes'][0]['dynamics']['flat'] = True
        self.assertTrue(any('flat' in x for x in gate(r, PIANO)))
        r = copy.deepcopy(self.report())
        r['nodes'][1]['silentNotes']['silent'] = 3
        self.assertTrue(any('silent' in x for x in gate(r, PIANO)))
        r = copy.deepcopy(self.report())
        r['global'] = dict(r['global'], lufsIntegrated=-24.0)
        self.assertTrue(any('loudness' in x for x in gate(r, PIANO)))
        r = copy.deepcopy(self.report())
        r['warnings'] = [{'severity': 'warn', 'code': 'flat_dynamics', 'message': "'piano' (lead) ..."}]
        self.assertTrue(any('flat_dynamics' in x for x in gate(r, PIANO)))


class Cli(unittest.TestCase):
    def test_parser(self):
        from agentsound.cli import build_parser
        a = build_parser().parse_args(['endless', 'jazz-piano', '--count', '2', '--swing'])
        self.assertEqual((a.genre, a.count, a.swing), ('jazz-piano', 2, True))
        a = build_parser().parse_args(['endless', '--swing', '0.58'])
        self.assertEqual((a.genre, a.swing), ('jazz-piano', 0.58))
        a = build_parser().parse_args(['endless'])
        self.assertIsNone(a.swing)

    def test_a_slot_failing_the_gate_is_rerolled_then_skipped(self):
        # (set 162000 slot 2: every candidate failed the click gate and the CLI stopped the whole set) - a slot whose
        # candidates all fail gets SLOT_REROLLS fresh rounds of seeds, then is skipped; the set goes on, the skipped
        # slot keeps its number free and counts toward --count; --rerolls 0 skips at once (the blind rounds)
        import contextlib
        import io
        import tempfile
        from unittest import mock
        from agentsound.cli import build_parser
        from agentsound.endless import run as R

        def fake_candidates(genre, seed, n, args, log, plan=None, prev=None, memory=None):
            return [{'seed': s, 'tune': None, 'song': None, 'score': {'score': 50.0}, 'plan': plan}
                    for s in range(seed, seed + n)]

        def run(rerolls, fail):
            tried = []

            def fake_render(genre, seed, out_root, index, args, log, plan=None, prev=None, made=None):
                tried.append((index, made['seed']))
                if index in fail:
                    return None
                return {'key': 'C', 'seed': made['seed'], 'timing': {'audio_s': 1.0, 'total_s': 1.0},
                        'files': {'mp3': str(pathlib.Path(out_root) / f'{index:03d}.mp3')}}
            with tempfile.TemporaryDirectory() as d, mock.patch.object(R, 'candidates', fake_candidates), \
                    mock.patch.object(R, 'render_tune', fake_render):
                argv = ['endless', 'jazz-piano', '--count', '4', '--seed', '100', '--candidates', '2', '--tries',
                        '2', '--out', d] + ([] if rerolls is None else ['--rerolls', str(rerolls)])
                a = build_parser().parse_args(argv)
                with contextlib.redirect_stdout(io.StringIO()):
                    rc = R.cmd_endless(a)
                log = (pathlib.Path(d) / 'endless.log').read_text(encoding='utf-8')
            return rc, tried, log
        rc, tried, log = run(None, {2})
        self.assertEqual(rc, 0)
        self.assertEqual(sorted({i for i, _ in tried}), [1, 2, 3, 4])               # slots 3 and 4 still made
        self.assertEqual([s for i, s in tried if i == 2], [102, 103, 104, 105, 106, 107])   # 2 rerolls, fresh seeds
        self.assertEqual([s for i, s in tried if i == 3], [108])                     # (the seeds go on after them)
        self.assertIn('slot 2 (002) skipped', log)
        rc, tried, log = run(0, {2})
        self.assertEqual([s for i, s in tried if i == 2], [102, 103])               # skipped at once
        self.assertEqual([s for i, s in tried if i == 3], [104])                     # seeds as in a passing code
        rc, tried, log = run(0, {1, 2, 3, 4})
        self.assertEqual((rc, len(tried)), (1, 2 * R.MAX_SKIPPED))                  # every slot failing: stops
        self.assertIn('slots in a row: stopping', log)

    def test_list(self):
        from agentsound.endless.run import describe_genres
        text = describe_genres()
        for g in endless.GENRES:
            self.assertIn(g, text)


if __name__ == '__main__':
    unittest.main()
