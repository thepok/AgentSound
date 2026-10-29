"""The endless 'orchestra-symphonic' genre (agentsound/endless/symphony.py: its own composer layer, orchestrated
through bandlib/orchestration.py's symphonic textures): the motto's transforms, the material (keys, charts, theme
lines, the fugato's voices), the texture windows (a role entering / leaving inside a block), and - with the SSO pack
installed - whole pieces: every note in its role's range, the motto's life, the drive, the metrics and score,
determinism and the arrangement record replayed. Notes only, no audio."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import endless  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.bandlib import orchestration as orc  # noqa: E402
from agentsound.endless import composer, symphony  # noqa: E402
from agentsound.theory import Key  # noqa: E402

SSO = orch.installed('sso')
MAJOR = {0, 2, 4, 5, 7, 9, 11}


def setUpModule():
    """These tests pin the piece-level rules on the plain set plan (SET_PLAN off, as they were written); the default
    since round o22 is SET_PLAN v4 (SetPlanDefault checks it) - its own tests switch it on themselves."""
    from agentsound.endless import genres
    genres.symphony_setplan(False)
    genres.symphony_tech(False)                  # (TECH, on by default since round o23: its own tests switch it on)
    genres.symphony_choir(False)                 # (CHOIR v2, on by default since round oc2: its own tests switch it on)
    genres.symphony_solo(False)                  # (SOLO, on by default since round os1)
    genres.symphony_colour(False)                # (COLOUR, on by default since round ox1)
    genres.symphony_shape3(False)                # (SHAPE3 + TECH2, on by default since round o25)
    genres.symphony_tech2(False)
    genres.symphony_pumping(False)               # (the phrase-arc fix, on by default since 2026-10-25)


def tearDownModule():
    from agentsound.endless import genres
    genres.symphony_setplan(False)
    genres.symphony_setplan(True)
    genres.symphony_tech(True)
    genres.symphony_choir(True, v2=True)
    genres.symphony_solo(True)
    genres.symphony_colour(True)
    genres.symphony_tech2(True)
    genres.symphony_shape3(True)
    genres.symphony_pumping(True)


class SetPlanDefault(unittest.TestCase):
    def test_v4_is_the_default(self):
        import subprocess
        out = subprocess.run([sys.executable, '-c', 'from agentsound.endless import genres, symphony; '
                              'print(genres.SYMPHONY_SETPLAN, symphony.SET_PLAN == symphony.SET_PLAN_V4, bool(symphony.TECH)); from agentsound.endless import choir, solo, colour; print(bool(choir.CHOIR), bool(solo.SOLO), bool(colour.COLOUR))'],
                             capture_output=True, text=True, cwd=str(Path(__file__).resolve().parents[2]))
        self.assertEqual(out.stdout.split(), ['True'] * 6, out.stderr)   # (+ TECH o23, CHOIR oc2, SOLO os1, COLOUR ox1)


def _overlaps(notes) -> int:
    ns = sorted(notes)
    return sum(1 for a, b in zip(ns, ns[1:]) if a[0] + a[1] > b[0] + 1e-6)


class Motto(unittest.TestCase):
    M = {'family': 'duple', 'kind': 'hammer', 'land': 3, 'member': 'root'}

    def test_transforms(self):
        plain = symphony.motto_notes(self.M, 0.0, 60, MAJOR)
        self.assertEqual([p for _, _, p in plain], [60, 60, 62, 64, 69])        # the landing: 3 steps over E
        inv = symphony.motto_notes(self.M, 0.0, 60, MAJOR, ('invert',))
        self.assertEqual([p for _, _, p in inv], [60, 60, 59, 57, 52])
        aug = symphony.motto_notes(self.M, 0.0, 60, MAJOR, ('augment',))
        self.assertEqual([a for a, _, _ in aug], [2 * a for a, _, _ in plain])
        ker = symphony.motto_notes(self.M, 0.0, 60, MAJOR, ('kernel',))
        self.assertTrue(all(a < 2.0 for a, _, _ in ker) and max(a + d for a, d, _ in ker) <= 2.0 + 1e-9)
        head = symphony.motto_notes(self.M, 0.0, 60, MAJOR, ('head',))
        self.assertLessEqual(head[-1][1], 1.0)

    def test_mono_makes_one_line(self):
        ns = symphony.motto_notes(self.M, 0.0, 60, MAJOR) + symphony.motto_notes(self.M, 1.0, 64, MAJOR)
        self.assertGreater(_overlaps(ns), 0)
        self.assertEqual(_overlaps(symphony._mono(ns)), 0)

    def test_never_the_famous_knock(self):
        g = endless.genre('orchestra-symphonic')
        for sd in range(40):
            t = composer.compose(g, sd)
            m = t.symphony['motto']
            self.assertFalse(m['kind'] == 'knock' and m['land'] in (-2, 2), sd)


class Material(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic').validate()

    def test_deterministic_and_the_feel_sets_tempo_and_meter(self):
        for sd in (3, 5, 7):
            a, b = composer.compose(self.g, sd), composer.compose(self.g, sd)
            self.assertEqual((a.title, a.key, a.tempo, a.melody), (b.title, b.key, b.tempo, b.melody), sd)
            lo, hi = self.g.feels[a.feel]['tempo']
            self.assertTrue(lo <= a.tempo <= hi, sd)
            self.assertEqual(a.symphony['family'], self.g.feels[a.feel]['family'], sd)

    def test_blocks_keys_and_lines(self):
        for sd in (1, 2, 5):
            mat = composer.compose(self.g, sd).symphony
            U = mat['U']
            home = mat['blocks'][0]['key']
            if any(b['kind'] in ('trans', 't2', 'episode', 'close') for b in mat['blocks']):   # (variations: none)
                self.assertIn(mat['second'], {b['key'] for b in mat['blocks']}, sd)  # the second key is visited
            # the piece ends home (round o3: a minor piece whose climax turned to the tonic major may end there)
            self.assertEqual(Key(mat['blocks'][-1]['key']).tonic, Key(home).tonic, sd)
            t = 0.0
            for b in mat['blocks']:
                self.assertAlmostEqual(b['start'], t, msg=(sd, b['name']))
                t += b['bars'] * U
                for ln in [b['theme'], b['answer']] + list(b['voices'].values()):
                    self.assertEqual(_overlaps(ln), 0, (sd, b['name']))
                    self.assertTrue(all(b['start'] - 1e-6 <= a < b['start'] + b['bars'] * U for a, _, _ in ln),
                                    (sd, b['name']))
                if b['kind'] == 'dev_fugato':                 # the entries in register, none in the cellar
                    heard = {v: ns for v, ns in b['voices'].items() if ns}   # (FUGUE v2: a capped fugato may not reach v1)
                    for v, ns in heard.items():
                        self.assertGreaterEqual(min(p for _, _, p in ns), 40, (sd, v))
                    self.assertGreaterEqual(len(heard), 3, sd)
                if b['kind'] in ('retrans', 'coda') and b['theme']:
                    self.assertEqual(_overlaps(b['theme']), 0, sd)

    def test_second_key_relations(self):
        self.assertEqual(symphony._second_key('C major', 'dominant'), 'G major')
        self.assertEqual(symphony._second_key('A minor', 'relative'), 'C major')
        self.assertTrue(Key(symphony._second_key('C major', 'relative')).minorish)


class SetDiversity(unittest.TestCase):
    """Round o2 (the user: a set must not be one template): the set arc's feel dice and cap, the tempo spread, the
    climax / build / size draws, modal keys - the piano genres' sets untouched."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic').validate()

    def test_feels_vary_per_set_and_none_more_than_twice(self):
        orders = set()
        for sd in (95000, 96000, 96100, 96200):
            p = composer.set_plan(self.g, 8, sd)
            feels = [x['feel'] for x in p]
            self.assertLessEqual(max(feels.count(f) for f in feels), self.g.arc['set']['feel_max'], sd)
            self.assertTrue(all(a != b for a, b in zip(feels, feels[1:])), sd)
            orders.add(tuple(feels))
            for x in p:
                lo, hi = self.g.feels[x['feel']]['tempo']
                self.assertTrue(lo <= x['tempo'] <= hi, (sd, x))
                self.assertIn(x['climax'], symphony.CLIMAXES)
                self.assertIn(x['build'], symphony.BUILDS)
        self.assertGreaterEqual(len(orders), 3)
        for name in ('new-age-piano', 'jazz-piano', 'orchestra-film'):     # (their arcs keep the old dice)
            self.assertNotIn('feel_max', endless.genre(name).arc['set'], name)

    def test_the_climax_and_build_draws_reach_their_blocks(self):
        # (round o11: no 'restate' draw any more - a material without its own texture, 'reharm', keeps the type's)
        base = {'feel': 'allegro', 'key': 'D major', 'tempo': 124, 'layout': 'sonata', 'slow': 0, 'apex': 'reharm'}
        # (round o8: the chorale climax draws the choir or the brass choir - symphony.ARRIVALS; round o9: the brass
        # choir only - o8's judges: "the choir only in the last 10 bars")
        for climax, tex in (('strings', {'apotheosis_strings': 1.0}),
                            ('chorale', {'tutti_chorale_brass': 1.0})):
            mat = composer.compose(self.g, 11, 'heroic', plan=dict(base, climax=climax, build='pulse')).symphony
            peak = [b for b in mat['blocks'] if b['peak']]
            self.assertEqual(len(peak), 1)
            self.assertEqual(symphony.kind_data(self.g, peak[0]['kind'], peak[0]['over'])['tex'], tex)
            rt = next(b for b in mat['blocks'] if b['kind'] == 'retrans')
            self.assertEqual(symphony.kind_data(self.g, 'retrans', rt['over'])['tex'], {'pulse_build': 1.0})
            self.assertEqual(mat['climax'], climax)
        # a climax the mood does not have: the mood's own draw ('quiet' is no heroic climax)
        mat = composer.compose(self.g, 11, 'heroic', plan=dict(base, climax='quiet')).symphony
        self.assertIn(mat['climax'], self.g.moods['heroic']['climax'])

    def test_a_modal_key_composes_in_its_scale(self):
        t = composer.compose(self.g, 777, 'journey', plan={'feel': 'river', 'key': 'D dorian', 'tempo': 100})
        home = [b for b in t.symphony['blocks'] if b['key'] == 'D dorian' and b['theme']]
        pcs = {p % 12 for b in home for _, _, p in b['theme']}
        self.assertIn(11, pcs)            # dorian's raised sixth (B natural)
        self.assertNotIn(10, pcs)         # not the minor's B flat


class Forms(unittest.TestCase):
    """Round o4 (o3's judges: one section plan for the whole set, recapitulations copied, one build frame, second
    themes as held notes, folded runs): the layouts beyond the sonata, the drawn phrase lengths and the elision, the
    recomposed returns, the build frames, the period, the runs that turn."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic').validate()

    def _mat(self, sd, mood, **plan):
        return composer.compose(self.g, sd, mood, plan=plan).symphony

    def test_every_feel_layout_composes_with_its_kinds(self):
        moods = {'allegro': 'heroic', 'vivace': 'dance', 'scherzo': 'dance', 'river': 'journey', 'andante': 'lyrical'}
        for feel, F in self.g.feels.items():
            for lay in F['layouts']:
                mat = self._mat(31, moods[feel], feel=feel, layout=lay, phrase='square', elide=0, slow=0)
                self.assertEqual(mat['layout'], lay, (feel, lay))
                kinds = [b['kind'] for b in mat['blocks']]
                self.assertEqual(sum(1 for b in mat['blocks'] if b['peak']), 1, (feel, lay))
                if lay == 'variations':
                    self.assertGreaterEqual(kinds.count('var'), 3)
                if lay in ('rondo', 'false'):
                    self.assertIn('refrain', kinds)
                if lay in ('rondo', 'ternary', 'scherzo_trio'):
                    self.assertIn('trio', kinds)
        # a layout the feel does not play: one of its own
        mat = self._mat(31, 'dance', feel='scherzo', layout='variations')
        self.assertIn(mat['layout'], self.g.feels['scherzo']['layouts'])

    def test_free_phrases_capped_and_one_elision(self):
        sq = self._mat(41, 'heroic', feel='allegro', layout='sonata', phrase='square', elide=0, slow=0, span='even')
        fr = self._mat(41, 'heroic', feel='allegro', layout='sonata', phrase='free', elide=0, slow=0, span='even')
        n_sq, n_fr = (sum(b['bars'] for b in m['blocks']) for m in (sq, fr))
        self.assertLessEqual(n_fr, symphony.PHRASE_CAP * n_sq + 1e-9)
        self.assertNotEqual([b['bars'] for b in sq['blocks']], [b['bars'] for b in fr['blocks']])
        for b in fr['blocks']:
            if b['kind'] in ('dev_dialogue',):
                self.assertEqual(b['bars'] % 2, 0)
        el = self._mat(41, 'heroic', feel='allegro', layout='sonata', phrase='square', elide=1, slow=0, span='even')
        cut = [b for b in el['blocks'] if b.get('elided')]
        self.assertEqual(len(cut), 1)
        self.assertIn(cut[0]['kind'], symphony.ELIDE)
        U = el['U']
        z = cut[0]['start'] + cut[0]['bars'] * U
        self.assertTrue(all(a < z for a, _, _ in cut[0]['theme']))

    def test_the_build_frames(self):
        base = dict(feel='allegro', key='C minor', tempo=124, layout='compact', phrase='square', elide=0, slow=0,
                    build='tremolo')
        for frame in symphony.BUILD_FRAMES:
            mat = self._mat(53, 'stormy', frame=frame, **base)
            rt = next(b for b in mat['blocks'] if b['kind'] == 'retrans')
            self.assertEqual(rt['chart'][-1][2], 'G7', frame)
            pitches = {p for _, _, p in rt['pedal']}
            if frame == 'pedal':
                self.assertEqual({p % 12 for p in pitches}, {7}, frame)       # the dominant held
            else:
                self.assertGreaterEqual(len(pitches), 3, frame)               # the bass walks
                self.assertTrue(all(36 <= p <= 50 for p in pitches), frame)

    def test_the_second_theme_a_period_and_its_return_changed(self):
        w = symphony.Writer('C major', 'duple', {'family': 'duple', 'kind': 'leap', 'land': 3, 'member': 'root'},
                            {'seed': 7}, __import__('random').Random(1))
        mel, ch = w.cantilena('t2', 'G major', 0.0, 8)

        def bar_rhythm(i):
            return [(round(a - 4 * i, 3), d) for a, d, _ in mel if 4 * i <= a < 4 * i + 4]
        self.assertEqual(bar_rhythm(0), bar_rhythm(4))
        self.assertEqual(bar_rhythm(1), bar_rhythm(5))         # the answer phrase in the head's rhythm
        self.assertGreaterEqual(len(bar_rhythm(0)), 3)
        top = max(p for _, _, p in mel)
        self.assertTrue(all(20 <= a < 24 for a, _, p in mel if p == top))      # the one high point: bar 6
        back, _ = w.cantilena('recap2', 'C major', 0.0, 8, vary=True)
        self.assertNotEqual([(a, d) for a, d, _ in back], [(a, d) for a, d, _ in mel])
        self.assertEqual(len(symphony.stretch((3, 5, 4, 2, 3, 6, 5, 1), 10)), 10)
        self.assertEqual(symphony.stretch((3, 5, 4, 2, 3, 6, 5, 1), 10)[7], 6)  # the deceptive cadence

    def test_runs_turn_at_the_range_edge(self):
        chart = [(4.0 * i, 4.0, s) for i, s in enumerate(('C', 'F', 'G', 'C') * 4)]
        for sd in range(6):
            run = symphony.figuration(chart, 'C major', 'run', 0.25, 67, 86, 4.0, sd, start=74)
            ps = [p for _, _, p in run]
            self.assertFalse(any(abs(b - a) >= 10 for a, b in zip(ps, ps[1:])), sd)
            self.assertTrue(all(62 <= p <= 91 for p in ps), sd)

    def test_timpani_tuning(self):
        self.assertEqual(symphony._timp_pitch(9, 9), 45)       # A minor: A2, E2
        self.assertEqual(symphony._timp_pitch(4, 9), 40)
        self.assertEqual(symphony._timp_pitch(11, 11), 47)     # B: B2 (not B3), F#2
        self.assertEqual(symphony._timp_pitch(0, 0), 48)       # C: C3, G2
        self.assertEqual(symphony._timp_pitch(7, 0), 43)


class RoundO5(unittest.TestCase):
    """Round o5 (o4's judges): the scherzo's dance tune, figuration on the chords, voiced cadences, the coda plans,
    the trumpets' tune floor."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')

    def test_the_scherzo_theme_is_a_dance(self):
        mat = composer.compose(self.g, 31, 'dance', plan={'feel': 'scherzo', 'layout': 'scherzo_trio'}).symphony
        t1 = next(b for b in mat['blocks'] if b['kind'] == 't1')
        bar = mat['U'] / 2.0                                      # (one 3/4 bar of the song)
        n = int(round(t1['bars'] * 2))
        busy = sum(1 for i in range(n - 1) if sum(1 for a, _, _ in t1['theme']
                                                  if t1['start'] + i * bar - 1e-6 <= a < t1['start'] + (i + 1) * bar - 1e-6) >= 2)
        self.assertGreaterEqual(busy, 0.75 * (n - 1))           # (no bar-long held notes over the oom-pah)
        self.assertTrue(any(e['tf'] == 'dance' for e in mat['log']))

    def test_figuration_strong_notes_are_chord_tones(self):
        chart = [(4.0 * i, 4.0, s) for i, s in enumerate(('C', 'F', 'G7', 'Am') * 2)]
        for sd in range(6):
            run = symphony.figuration(chart, 'C major', 'run', 0.25, 67, 86, 4.0, sd, start=74)
            for a, _, p in run:
                if abs(a * 2 - round(a * 2)) < 1e-6:            # (the 8th positions)
                    sym = next(s for x, b, s in chart if x <= a < x + b)
                    self.assertIn(p % 12, symphony._cpcs(sym), (sd, a))

    def test_endings_are_voiced_cadences(self):
        # (round o7: the cadential six-four before V7, a predominant before the held ending; round o9: a predominant
        # bar first - symphony.END_PRE: IV before the dominant plans, vi before the predominant / plagal ones; round
        # o11: the plagal ending a real V - I too, ENDING_CADENCE)
        for ending, approach in (('cadence', ['F', 'C/G', 'G7']), ('strokes', ['F', 'G7']),
                                 ('plagal', ['Am', 'F', 'G7']),
                                 ('motto', ['F', 'G7']), ('held', ['Am', 'F', 'G7'])):
            mat = composer.compose(self.g, 41, 'heroic', plan={'feel': 'allegro', 'key': 'C major', 'tempo': 120,
                                                               'ending': ending, 'coda': 'triumph'}).symphony
            end = mat['blocks'][-1]
            self.assertEqual([s for _, _, s in end['chart']], approach + ['C'], ending)
            self.assertEqual(end['theme'][-1][2] % 12, 0, ending)

    def test_coda_plans(self):
        for plan, coda in (('stretto', 'triumph'), ('pedal', 'triumph'), ('hymn', 'triumph'), ('descent', 'dissolve'),
                           ('echo', 'dissolve'), ('memory', 'dissolve')):
            mat = composer.compose(self.g, 43, 'lyrical', plan={'feel': 'andante', 'coda': coda, 'coda_plan': plan,
                                                                'layout': 'sonata'}).symphony
            c = next(b for b in mat['blocks'] if b['kind'] in ('coda', 'coda_soft'))
            self.assertEqual(c['plan'], plan)
            self.assertTrue(c['theme'] and c['chart'], plan)

    def test_trumpet_tunes_stay_over_their_floor(self):
        table = orch.role_table('film_orchestra')
        R = dict(orc.RULES, idiom=True)
        self.assertFalse(orc._tune_ok('trumpets', [(0.0, 1.0, 58), (1.0, 1.0, 62)], table, R, fit=False))
        self.assertTrue(orc._tune_ok('trumpets', [(0.0, 1.0, 69), (1.0, 1.0, 74)], table, R, fit=False))
        self.assertTrue(orc._tune_ok('trumpets', [(0.0, 1.0, 58)], table, dict(R, idiom=False), fit=False))


class RoundO9(unittest.TestCase):
    """Round o9 (o8's judges): the climax carries the theme at its own speed over its augmentation, no literal
    restatements, episodes from the theme, no static stretches, a descent after the climax, endings from a
    predominant, the choir out, the melody's tracks named for the report (analysis.leads)."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic').validate()

    def test_unrepeat_sequences_literal_copies(self):
        pcs = symphony.pcs_of('C major')
        bar = [(0.0, 1.0, 64), (1.0, 1.0, 67), (2.0, 2.0, 72)]
        line = [(a + 4.0 * k, d, p) for k in range(3) for a, d, p in bar]
        out = symphony._unrepeat(line, 0.0, 4.0, pcs)
        units = [tuple(p for a, _, p in out if 4.0 * k <= a < 4.0 * (k + 1)) for k in range(3)]
        self.assertEqual(units[0], (64, 67, 72))
        self.assertNotEqual(units[1], units[0])
        self.assertNotEqual(units[2], units[1])
        self.assertEqual(symphony._unrepeat(line[:3], 0.0, 4.0, pcs), sorted(line[:3]))      # (one statement: kept)

    def test_augmented_climax_sings_the_motto_at_its_own_speed(self):
        base = {'feel': 'allegro', 'key': 'D major', 'tempo': 124, 'layout': 'sonata', 'slow': 0, 'climax': 'brass'}
        for apex, tex in (('augment', 'apex_augment'), ('theme_aug', 'apex_theme')):
            t = composer.compose(self.g, 11, 'heroic', plan=dict(base, apex=apex))
            peak = next(b for b in t.symphony['blocks'] if b['peak'])
            self.assertTrue(peak['answer'], apex)                   # (the counter: the material at its own speed)
            mel = sorted(p for _, _, p in peak['theme'])
            self.assertGreater(sum(p for _, _, p in peak['answer']) / len(peak['answer']), mel[len(mel) // 2], apex)
            s = endless.song(t)
            b = next(x for x in s.orch_score.blocks if x.peak)
            self.assertEqual(b.texture, tex, apex)
            self.assertTrue(any(p.block == b.name and p.function == 'counter' and p.notes
                                for p in s.orchestration.parts), apex)
            figs = [p for p in s.orchestration.parts if p.block == b.name and p.function == 'figuration' and p.notes]
            self.assertTrue(all(min(a for a, _, _ in p.notes) >= b.start + b.length / 2 - 1e-6 for p in figs), apex)

    def test_a_folded_note_never_holds_into_the_next_chord(self):
        # (o9's judges, UZWK: the violins II's B4 over the approach's dipping soprano was folded to D#4 under B7 and
        # held into the final E minor: FOLD cuts it at the chord change)
        g = self.g
        plan = composer.set_plan(g, 8, 109300)
        t = composer.compose(g, 109326, plan=plan[6])
        s = endless.song(t)
        last = s.orch_score.blocks[-1]
        a1 = max(a for a, _, _ in last.chart)
        tonic = set(symphony._cpcs(symphony._chart_at(last.chart, a1 + 0.01).split("/")[0]))
        for p in s.orchestration.parts:
            if p.block == last.name and p.function in ('harmony', 'inner') and p.notes:
                for a, d, q in p.notes:
                    if a + d > a1 + 1e-6:
                        self.assertIn(q % 12, tonic, (p.role, a, d, q))

    def test_end_opens_on_a_predominant_with_the_motto(self):
        t = composer.compose(self.g, 41, 'heroic', plan={'feel': 'allegro', 'key': 'C major', 'tempo': 120,
                                                         'ending': 'strokes', 'coda': 'triumph'})
        end = t.symphony['blocks'][-1]
        self.assertTrue(symphony.END_LEN['min'] <= end['bars'] <= symphony.END_LEN['max'])   # (o10: proportional)
        self.assertGreater(end['approach'], end['start'])
        self.assertGreaterEqual(sum(1 for a, _, _ in end['theme'] if a < end['approach']), 2)

    def test_openings_state_the_theme_early(self):
        # (round o10: at most OPENING['bars'] bars before the first theme, the slow bars at their own tempo)
        for sd in (1, 5, 7, 41):
            blocks = endless.compose(self.g, sd).symphony['blocks']
            first = next(b for b in blocks if b['kind'] in ('t1', 'river', 'dance'))
            pre = sum(b['bars'] for b in blocks[:blocks.index(first)])
            self.assertLessEqual(pre, symphony.OPENING['bars'] / symphony.SLOW['tempo'] + 1, sd)

    def test_inner_voices_and_folds(self):
        # (round o10: folds at the source - chord runs lowered as a whole, inner voices over G3)
        for sd in (1, 5, 7):
            s = endless.song(endless.compose(self.g, sd))
            self.assertEqual(s.orchestration.folded, 0, sd)

    def test_violins_not_in_unison_at_the_top(self):
        # (round o10 - o9's judges: violins I + II in unison up to B6: the seconds an octave under above VLN_UNISON)
        for sd in (1, 5, 7):
            s = endless.song(endless.compose(self.g, sd))
            v1 = {(round(a, 3), p) for x in s.orchestration.parts if x.role == 'violins1' for a, _, p in x.notes}
            v2 = [(round(a, 3), p) for x in s.orchestration.parts if x.role == 'violins2' for a, _, p in x.notes]
            self.assertFalse([n for n in v2 if n in v1 and n[1] > symphony.VLN_UNISON], sd)

    def test_river_episode_is_its_tune_varied(self):
        t = composer.compose(self.g, 5, plan={'feel': 'river', 'layout': 'journey'})
        mat = t.symphony
        river = next(b for b in mat['blocks'] if b['kind'] == 'river')
        epi = next(b for b in mat['blocks'] if b['kind'] == 'episode')
        self.assertEqual(epi['key'], mat['second'])
        # (the variation's tune: the river tune's pitches in the second key, dotted)
        sh = (Key(mat['second']).tonic - Key(river['key']).tonic) % 12
        a = [p % 12 for _, _, p in river['theme'][:6]]
        b = [(p - sh) % 12 for _, _, p in epi['theme'][:6]]
        self.assertGreaterEqual(sum(1 for x, y in zip(a, b) if x == y), 4)

    def test_no_choir_and_the_lead_hint(self):
        self.assertNotIn('choir', self.g.plan['sizes']['full'])
        t = endless.compose(self.g, 7)
        s = endless.song(t)
        r = s.compile()
        leads = r['analysis']['leads']
        secs = {x['name'] for x in r['sections']}
        tracks = {x['id'] for x in r['tracks']}
        self.assertTrue(leads)
        for tid, names in leads.items():
            self.assertIn(tid, tracks)
            self.assertTrue(set(names) <= secs)
        mel = {(p.role, p.block) for p in s.orchestration.parts if p.function == 'melody' and p.notes}
        self.assertEqual({(r_, b) for r_, bs in leads.items() for b in bs}, mel)

    def test_long_blocks_move_their_held_harmony(self):
        chart = [(0.0, 16.0, 'C'), (16.0, 16.0, 'G')]
        held = {'h1': [(0.0, 16.0, 76), (16.0, 16.0, 74)], 'h2': [(0.0, 16.0, 67), (16.0, 16.0, 67)]}
        moved = symphony._move_inner(held, chart, 'C major', 4.0)
        self.assertGreater(len(moved['h1']), 2)


class RoundO6(unittest.TestCase):
    """Round o6 (o5's judges): the climax from the piece's own material, the climax's key per set, the second theme
    one tune in either mode, the development working the first theme, the river's stream moving, the scherzo's tune
    on top."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')

    def test_the_wave_stream_moves(self):
        chart = [(3.0 * i, 3.0, s) for i, s in enumerate(('Em', 'Em', 'Am', 'B'))]
        for sd in range(4):
            f = symphony.figuration(chart, 'E minor', 'wave', 0.25, 60, 79, 3.0, sd, start=67)
            rep = sum(1 for a, b in zip(f, f[1:]) if a[2] == b[2]) / (len(f) - 1)
            self.assertLess(rep, 0.2, sd)                       # (o5: one pitch for bars - 0.9)

    def test_clx_keys(self):
        self.assertEqual(symphony.clx_keys('E minor', 'parallel'), ('E major', 'E major', 'E major'))
        self.assertEqual(symphony.clx_keys('E minor', 'picardy'), ('E minor', 'E minor', 'E major'))
        self.assertEqual(symphony.clx_keys('E minor', 'relative'), ('G major', 'E minor', 'E minor'))
        self.assertEqual(symphony.clx_keys('D major', 'parallel'), ('D minor', 'D major', 'D major'))
        self.assertEqual(symphony.clx_keys('D major', 'picardy'), ('D major',) * 3)

    def test_the_climax_carries_the_motto(self):
        for apex in ('combine', 'augment', 'theme_aug'):
            mat = composer.compose(self.g, 51, 'stormy', plan={'feel': 'allegro', 'key': 'D minor', 'tempo': 126,
                                                               'layout': 'sonata', 'apex': apex,
                                                               'clx_mode': 'home'}).symphony
            rc = next(b for b in mat['blocks'] if b['peak'])
            self.assertEqual(rc['key'], 'D minor', apex)
            tfs = {e['tf'] for e in mat['log'] if e['block'] == rc['name'] and e['fn'] == 'melody'}
            self.assertTrue(tfs and 'cantilena' not in tfs, (apex, tfs))   # (the motto / the first theme on top)
            if apex == 'combine':
                self.assertTrue(rc['answer'])                   # (the second theme under it)
                self.assertLess(max(p for _, _, p in rc['answer']), max(p for _, _, p in rc['theme']))

    def test_the_second_theme_is_one_tune_in_either_mode(self):
        w = symphony.Writer('A minor', 'duple', {'family': 'duple', 'kind': 'arch', 'land': 3, 'member': 'root'},
                            {'seed': 3, 'skeleton': {'major': (3, 5, 4, 2, 3, 6, 5, 1),
                                                     'minor': (5, 3, 4, 2, 5, 8, 7, 8)}}, None)
        a, _ = w.cantilena('t2', 'C major', 0.0, 8)
        b, _ = w.cantilena('x', 'A minor', 0.0, 8)
        def degrees(key, notes):
            sc = [Key(key).degree(i, octave=4) % 12 for i in range(1, 8)]
            return [sc.index(p % 12) if p % 12 in sc else None for _, _, p in notes]
        da, db = degrees('C major', a), degrees('A minor', b)
        self.assertEqual(da[:4], db[:4])                                    # (one head, by degree)
        self.assertEqual([x for x, _, _ in a], [x for x, _, _ in b])        # (one rhythm)

    def test_the_development_works_the_first_theme(self):
        mat = composer.compose(self.g, 53, 'heroic', plan={'feel': 'allegro', 'key': 'C major', 'tempo': 124,
                                                           'layout': 'compact', 'dev_tech': 'theme'}).symphony
        dv = next(b for b in mat['blocks'] if b['kind'] == 'dev_dialogue')
        self.assertTrue(any(e['tf'] == 'theme' and e['block'] == dv['name'] for e in mat['log']))
        self.assertTrue(dv['theme'] and dv['answer'])

    def test_the_scherzo_theme_has_its_tune_on_top(self):
        for sd in (61, 62, 63):
            t = composer.compose(self.g, sd, 'dance', plan={'feel': 'scherzo', 'layout': 'compact'})
            s = endless.song(t)
            for b in s.orch_score.blocks:
                kind = next(x['kind'] for x in t.symphony['blocks'] if x['name'] == b.name)
                if kind in symphony.SCHERZO_TEX['kinds']:
                    self.assertNotIn(b.texture, symphony.SCHERZO_TEX['tex'], (sd, b.name))


class RoundO7(unittest.TestCase):
    """Round o7 (o6's judges): the scherzo's climax at the dance's speed, the voiced final cadence (the approach, the
    voice order, the tendency tones), the inner strings moving, the tune not stacked in the bass."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')

    def test_the_scherzo_climax_is_the_dance_not_augmented(self):
        for apex in ('combine', 'augment', 'theme_aug'):
            mat = composer.compose(self.g, 71, 'dance', plan={'feel': 'scherzo', 'layout': 'compact', 'apex': apex,
                                                              'clx_mode': 'home'}).symphony
            rc = next(b for b in mat['blocks'] if b['peak'])
            tfs = {e['tf'] for e in mat['log'] if e['block'] == rc['name'] and e['fn'] == 'melody'}
            self.assertNotIn('augment', tfs, apex)
            bar = mat['U'] / 2                                  # (a 3/4 bar of the song, internal beats)
            held = sum(1 for _, d, _ in rc['theme'] if d >= bar - 1e-6)
            self.assertLess(held / len(rc['theme']), 0.15, apex)    # (o6: one note per 3/4 bar)

    def test_the_approach_bars(self):
        ch, sop = symphony._approach('C major', 'cad64', 0.0, 4.0, 72)
        self.assertEqual([s for _, _, s in ch], ['C/G', 'G7'])
        self.assertEqual([p for _, _, p in sop], [76, 74])              # (3 - 2, then 1)
        ch, sop = symphony._approach('A minor', 'pre', 0.0, 4.0, 69)
        self.assertEqual([s for _, _, s in ch], ['Dm', 'E7'])
        self.assertEqual([p for _, _, p in sop], [69, 68])              # (1 - the raised 7)
        ch, sop = symphony._approach('C major', 'pedal', 0.0, 4.0, 72)
        self.assertEqual([s for _, _, s in ch], ['F/C'])

    def test_the_leading_tone_rises_and_the_seventh_falls(self):
        chart = [(0.0, 4.0, 'G7'), (4.0, 4.0, 'C')]
        parts = {'h1': [(0.0, 4.0, 71), (4.0, 4.0, 67)], 'h2': [(0.0, 4.0, 65), (4.0, 4.0, 67)]}
        out = symphony._resolve(parts, chart, 'C major', mel=[(0.0, 4.0, 74), (4.0, 4.0, 76)])
        self.assertEqual(out['h1'][1][2], 72)                           # (B -> C)
        self.assertEqual(out['h2'][1][2], 64)                           # (F -> E)
        out = symphony._resolve(parts, chart, 'C major', mel=[(0.0, 4.0, 71), (4.0, 4.0, 72)])
        self.assertEqual(out['h1'][1][2], 67)                           # (an inner B under the tune's C may fall)

    def test_the_final_chord_in_score_order(self):
        for sd in (81, 82, 83):
            t = composer.compose(self.g, sd, 'heroic', plan={'feel': 'allegro', 'ending': 'cadence',
                                                            'coda': 'triumph'})
            s = endless.song(t)
            last = s.orch_score.blocks[-1]
            t1 = sorted(last.chart)[-1][0]
            top = {}
            for p in s.orchestration.parts:
                if p.block == last.name:
                    for a, d, q in p.notes:
                        if a <= t1 + 0.01 < a + d:
                            top[p.role] = max(top.get(p.role, 0), q)
            for hi, lo in (('clarinets', 'bassoons'), ('horns', 'trombones')):
                if hi in top and lo in top:
                    self.assertGreaterEqual(top[hi], top[lo], (sd, hi, lo))
            self.assertEqual(max(top.values()), max(top.get(r, 0) for r in ('violins1', 'flutes', 'oboes',
                                                                            'trumpets')), sd)

    def test_the_inner_voices_move(self):
        chart = [(0.0, 4.0, 'C'), (4.0, 4.0, 'C'), (8.0, 4.0, 'F'), (12.0, 4.0, 'G')]
        o = {'o1': [(0.0, 8.0, 67), (8.0, 4.0, 69), (12.0, 4.0, 67)], 'o2': [(0.0, 8.0, 60), (8.0, 4.0, 60),
                                                                            (12.0, 4.0, 59)]}
        out = symphony._move_inner(o, chart, 'C major', 4.0)
        for v in out:
            self.assertGreater(len({p for _, _, p in out[v]}), len({p for _, _, p in o[v]}), v)
            self.assertAlmostEqual(sum(d for _, d, _ in out[v]), 16.0)

    def test_the_bass_in_the_tunes_rhythm(self):
        chart = [(0.0, 4.0, 'C'), (4.0, 4.0, 'G')]
        theme = [(0.0, 1.0, 76), (1.0, 1.0, 79), (2.0, 2.0, 77), (4.0, 2.0, 74), (6.0, 2.0, 71)]
        b = symphony._bass_in_rhythm(theme, chart, 'C major', 0.5)
        self.assertEqual([a for a, _, _ in b], [a for a, _, _ in theme])
        self.assertEqual({p % 12 for a, _, p in b if a < 4}, {0})          # (the chord's bass, not the tune)


class RoundO8(unittest.TestCase):
    """Round o8 (o7's judges): the development through the related keys, the motto recalled in the coda, the build
    and the climax in proportion, the final chord's low root, no octave folds where the accompaniment goes under the
    tune."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')

    def test_the_development_keys_are_related(self):
        for home in ('C major', 'A minor', 'D dorian', 'Eb major', 'G minor'):
            scale = set(Key(home).pcs)
            for path in symphony.DEV_PATHS:
                ks = symphony.dev_keys(home, path)
                self.assertEqual(len(ks), 4, (home, path))
                for k in ks:
                    self.assertIn(Key(k).tonic % 12, scale, (home, path, k))
                    third = (Key(k).tonic + (3 if Key(k).minorish else 4)) % 12
                    self.assertIn(third, scale, (home, path, k))       # (the key's own triad is diatonic)

    def test_the_coda_recalls_the_motto(self):
        for plan_, coda in (('hymn', 'triumph'), ('memory', 'dissolve')):
            mat = composer.compose(self.g, 91, 'lyrical', plan={'feel': 'andante', 'layout': 'sonata', 'coda': coda,
                                                                'coda_plan': plan_}).symphony
            cb = next(b for b in mat['blocks'] if b['kind'] in ('coda', 'coda_soft'))
            if cb['bars'] < symphony.CODA_RECALL['bars'] + 4:
                continue
            tfs = [e['tf'] for e in mat['log'] if e['block'] == cb['name']]
            self.assertIn('cantilena', tfs, plan_)
            self.assertTrue(any(x != 'cantilena' for x in tfs), plan_)

    def test_the_build_and_the_climax_in_proportion(self):
        for sd in (3, 4, 5):
            mat = composer.compose(self.g, sd, 'heroic', plan={'feel': 'allegro', 'span': 'tight',
                                                              'layout': 'compact'}).symphony
            total = sum(b['bars'] for b in mat['blocks'])
            rt = next(b for b in mat['blocks'] if b['kind'] == 'retrans')
            pk = next(b for b in mat['blocks'] if b['peak'])
            self.assertGreaterEqual(rt['bars'], max(symphony.PROPORTION['build']['min'],
                                                    symphony.PROPORTION['build']['share'] * total - 1), sd)
            self.assertGreaterEqual(pk['bars'], symphony.PROPORTION['peak']['min'], sd)

    def test_the_final_bass_is_a_low_root(self):
        b = symphony._end_bass([(0.0, 2.0, 55), (2.0, 2.0, 62)], 'cellos')        # (G3 then D4: the D at D3)
        self.assertEqual(b[-1][2], 50)
        self.assertEqual(b[0][2], 55)
        b = symphony._end_bass([(0.0, 4.0, 62)], 'basses')
        self.assertEqual(b[-1][2], 38)

    def test_no_octave_folds_under_the_tune(self):
        notes = [(0.0, 0.5, 62), (0.5, 0.5, 62), (1.0, 0.5, 74), (1.5, 0.5, 74)]
        over = [False, False, True, True]
        out = symphony._lower(notes, over, 55, lambda a: 72, symphony._chart_pcs([(0.0, 4.0, 'D')]))
        self.assertTrue(all(abs(b[2] - a[2]) < symphony.FOLD['jump'] for a, b in zip(out, out[1:])), out)
        self.assertTrue(all(q < 72 for a, _, q in out if a >= 1.0), out)

    def test_the_arrival_draws_the_cymbals_away(self):
        for arr, m in symphony.ARRIVAL_FIG.items():
            self.assertIn(arr, symphony.ARRIVALS)
            if arr in ('timp', 'none'):
                self.assertTrue(all(m.get(f, f) is None for f in ('crash', 'crash_dry', 'swell_cym')), arr)


class RoundO11(unittest.TestCase):
    """Round o11 (the masterpiece panel: the form's argument): the development's share and its shrinking unit, the
    return in the home key with the second theme, the dominant pedal before it, one summit, a real last cadence, the
    movement's length (songs/_blind/ROUNDS.md "Round o11")."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')

    def test_the_ladder(self):
        for tech in ('sequence', 'fragment', 'stretto', 'combine', 'bass', 'theme'):
            for n in range(1, 13):
                st = symphony.dev_stages(tech, n)
                self.assertEqual(len(st), n)
                self.assertLessEqual(st.count(0), symphony.DEV_LADDER['links'] + 1, (tech, n))
                self.assertEqual(st, sorted(st), (tech, n))          # (the unit only shrinks)
                if n >= 3:
                    self.assertEqual(st[-1], 3, (tech, n))

    def test_the_forms_proportions(self):
        F = self.g.feels
        for feel, layout in (('allegro', 'sonata'), ('allegro', 'compact'), ('allegro', 'through'),
                             ('andante', 'ternary'), ('scherzo', 'scherzo_trio'), ('vivace', 'rondo')):
            for frame in ('pedal', 'ascent'):
                sc = F[feel].get('scale', 1)
                rows = symphony.form_rows(self.g, layout, {'frame': frame, 'build': 'tremolo'}, F[feel], 1,
                                          bar_s=4 * sc * 60 / 120)
                total = sum(r[2] for r in rows)
                dev = sum(r[2] for r in rows if r[1] in symphony.DEV_SHARE['kinds'])
                self.assertGreaterEqual(dev * sc, 16, (layout, frame))
                self.assertGreaterEqual(dev / total, 0.25 - 1e-9, (layout, frame))
                self.assertLessEqual(dev / total, symphony.DEV_SHARE['max'] + 1e-9, (layout, frame))
                self.assertTrue(all(r[2] * sc <= symphony.DEV_SHARE['block'] + 4 for r in rows
                                    if r[1] in symphony.DEV_SHARE['kinds']), (layout, rows))
                rt = next(r for r in rows if r[1] == 'retrans')
                self.assertGreaterEqual(rt[2] * sc, symphony.RT_PEDAL['bars'], (layout, frame))
                self.assertGreaterEqual(total * 4 * sc * 60 / 120, symphony.MIN_LEN['seconds'] - 1e-6, layout)
                if layout in ('sonata', 'compact', 'through', 'rondo'):
                    self.assertIn('recap2', [r[1] for r in rows], layout)

    def test_the_return_and_the_summit(self):
        for sd, mood, plan in ((11, 'heroic', {'feel': 'allegro', 'layout': 'compact', 'clx_mode': 'home'}),
                               (12, 'journey', {'feel': 'river', 'apex': 'reharm'}),
                               (13, 'heroic', {'feel': 'allegro', 'layout': 'through', 'apex': 'reharm',
                                               'key': 'D major'})):
            t = composer.compose(self.g, sd, mood, plan=plan)
            s = endless.song(t)
            f = symphony.form_stats(s)
            self.assertEqual(f['t1_home'], 1, sd)
            self.assertEqual(f.get('t2_home', 1), 1, sd)
            self.assertEqual(f['cadence_end'], 1, sd)
            self.assertGreaterEqual(f['pre_semis'], 3, sd)
            self.assertLessEqual(f['seq_links'], symphony.DEV_LADDER['links'] + 1, sd)
            peak = next(b for b in t.symphony['blocks'] if b['peak'])
            self.assertEqual(Key(peak['key']).tonic, Key(t.key).tonic, sd)     # (the summit at home)

    def test_no_ending_fades_without_its_dominant(self):
        self.assertNotIn('IV', symphony.SOFT_ENDINGS)
        self.assertNotIn('pedal', symphony.SOFT_ENDINGS)
        self.assertNotIn('IV', symphony.ENDING_CADENCE.values())
        self.assertTrue(set(symphony.SOFT_OF.values()) <= set(symphony.SOFT_ENDINGS))

    def test_the_retransition_ends_on_the_dominant_pedal(self):
        for frame in ('ascent', 'circle', 'lament'):
            t = composer.compose(self.g, 21, 'heroic', plan={'feel': 'allegro', 'key': 'C major', 'frame': frame,
                                                              'build': 'tremolo'})
            rt = next(b for b in t.symphony['blocks'] if b['kind'] == 'retrans')
            U = t.symphony['U']
            P = int(-(-symphony.RT_PEDAL['bars'] // t.symphony['scale']))
            z = rt['start'] + rt['bars'] * U
            tail = [x for x in rt['pedal'] if x[0] + x[1] > z - P * U + 1e-6]
            self.assertTrue(tail and all(p % 12 == 7 for _, _, p in tail), (frame, rt['pedal']))
            self.assertTrue(rt['answer'], frame)                     # (the head in imitation over it)


class RoundO12(unittest.TestCase):
    """Round o12 (the masterpiece panel, second pass): the motto's character (a leap, no scale run), the summit with
    the brass and the violins' top, the accompaniment never unchanged over TEX_RUN bars, the dominant drive into the
    return (songs/_blind/ROUNDS.md "Round o12")."""

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic')
        cls.made = {}
        for sd, plan in ((21, {'feel': 'allegro', 'layout': 'sonata'}), (22, {'feel': 'andante'}),
                         (23, {'feel': 'scherzo'})):
            t = composer.compose(cls.g, sd, plan=plan)
            cls.made[sd] = (t, endless.song(t))

    def test_the_motto_has_a_profile(self):
        for sd, (t, _) in self.made.items():
            self.assertTrue(symphony.motto_character(t.symphony['motto']), sd)
            ps = [p for _, _, p in symphony.motto_notes(t.symphony['motto'], 0.0, 60, {0, 2, 4, 5, 7, 9, 11})]
            iv = [b - a for a, b in zip(ps, ps[1:])]
            self.assertGreaterEqual(max(abs(x) for x in iv), symphony.MOTTO_CHARACTER['leap'], sd)

    def test_the_summit(self):
        for sd, (t, s) in self.made.items():
            f = symphony.summit_stats(s)
            self.assertEqual(f['tutti_peak'], 1, sd)
            self.assertEqual(f['brass_peak'], 2, sd)
            self.assertGreaterEqual(f['vln_over'], 1, sd)

    def test_no_endless_accompaniment(self):
        for sd, (t, s) in self.made.items():
            f = symphony.summit_stats(s)
            self.assertLessEqual(f['acc_run'], symphony.TEX_RUN['bars'], sd)

    def test_the_drive_into_the_return(self):
        from agentsound.bandlib import orchestration as orc
        for sd, (t, s) in self.made.items():
            sb = s.orch_score.blocks
            i = next(j for j, x in enumerate(sb) if x.peak)
            if t.symphony['blocks'][i - 1]['kind'] != 'retrans':
                continue
            b = sb[i - 1]
            # (the basses / cellos re-strike the dominant - or carry the motto there, a 'bass' texture - and the
            # timpani drive)
            low = ('timpani',) if orc.TEXTURES[b.texture].get('theme') == 'bass' else ('basses', 'cellos')
            parts = [p for p in s.orchestration.parts if p.block == b.name and p.notes and p.role in low]
            self.assertTrue(any(len(p.notes) >= 4 for p in parts), sd)


class Chroma(unittest.TestCase):
    """The chromatic vocabulary (the code review's A2 step 1): spelling, voice-led resolutions, the chooser's hooks and
    CHROMA_CADENCE (off by default: bit-identical - the protected hashes, songs/_blind/ROUNDS.md)."""
    KEYS = ('C major', 'A minor', 'Eb major', 'F# minor')

    def test_spelling(self):
        sp = symphony.chroma_spell
        self.assertEqual(sp('C major', 'Ger6'), ['Ab', 'C', 'Eb', 'F#'])
        self.assertEqual(sp('C major', 'It6'), ['Ab', 'C', 'F#'])
        self.assertEqual(sp('C major', 'Fr6'), ['Ab', 'C', 'D', 'F#'])
        self.assertEqual(sp('C major', 'N6'), ['Db', 'F', 'Ab'])
        self.assertEqual(sp('C major', 'vii°7/V'), ['F#', 'A', 'C', 'Eb'])
        self.assertEqual(sp('C major', 'V7/V'), ['D', 'F#', 'A', 'C'])
        self.assertEqual(sp('A minor', 'Ger6'), ['F', 'A', 'C', 'D#'])
        self.assertEqual(sp('Eb major', 'N6'), ['Fb', 'Ab', 'Cb'])
        self.assertEqual(symphony.chroma_symbol('C major', 'Ger6'), 'Ab7')
        self.assertEqual(symphony.chroma_symbol('C major', 'N6'), 'Db/F')
        self.assertEqual(symphony.chroma_symbol('C major', 'cad64'), 'C/G')
        self.assertFalse(symphony.chroma_fits('A minor', 'bVI'))         # (mixture: major only)
        self.assertFalse(symphony.chroma_fits('D dorian', 'Ger6'))       # (no church modes)

    def test_resolutions_by_step_without_parallels(self):
        from agentsound.theory import chord
        made = 0
        for key in self.KEYS:
            for rn, C in symphony.CHROMA.items():
                if not symphony.chroma_fits(key, rn):
                    continue
                pcs = [symphony._chroma_pc(key, t) for t in C['tones']]
                tend = {pcs[i]: d for i, d in C['tend'].items()}
                for tgt in symphony.chroma_targets(key, rn):
                    chromatic = tgt == 'cad64' or tgt in symphony.CHROMA
                    sym = symphony.chroma_symbol(key, tgt) if chromatic else symphony._roman(key, tgt)
                    npcs = set(chord(sym).pcs)
                    for n in (2, 3, 4):
                        got = symphony.realise(key, rn, tgt, n)
                        if got is None:
                            continue
                        made += 1
                        (b0, up0), (b1, up1) = got
                        v0, v1 = [b0] + up0, [b1] + up1
                        self.assertEqual(b0 % 12, pcs[C['bass']], (key, rn))
                        self.assertLessEqual(set(pcs) if n + 1 >= len(pcs) else set(tend), {q % 12 for q in v0})
                        self.assertLessEqual({q % 12 for q in v1}, npcs, (key, rn, tgt, n))
                        for q0, q1 in zip(v0, v1):
                            d = tend.get(q0 % 12)
                            if d:                       # (the tendency tones by step their way - a seventh may hold)
                                ok = 1 <= (q1 - q0) * (1 if d > 0 else -1) <= 2 or (abs(d) == 2 and q1 == q0)
                                self.assertTrue(ok, (key, rn, tgt, n, q0, q1))
                        for i in range(len(v0)):        # (no parallel fifths / octaves - the outer voices too)
                            for j in range(i + 1, len(v0)):
                                self.assertFalse(symphony._parallel(v0[i], v1[i], v0[j], v1[j]), (key, rn, tgt, n))
                        self.assertTrue(all(a < b for a, b in zip(up1, up1[1:])))
            for rn, tgt in (('Ger6', 'cad64'), ('It6', 'V'), ('Fr6', 'V'), ('N6', 'V'), ('vii°7/V', 'V'),
                            ('V7/V', 'V'), ('V7/IV', 'iv' if Key(key).minorish else 'IV')):
                self.assertIsNotNone(symphony.realise(key, rn, tgt, 3), (key, rn, tgt))
        self.assertGreater(made, 150)
        (b0, up0), (b1, up1) = symphony.realise('C major', 'Ger6', 'cad64', 3)
        self.assertEqual((b0, b1), (44, 43))                                # (b6 - 5 in the bass)
        self.assertIn(66, up0)                                              # (#4 ...)
        self.assertEqual(up1[up0.index(66)], 67)                            # (... up to 5)

    def test_the_chooser_hooks(self):
        mel = [(0.0, 2.0, 64), (2.0, 2.0, 65), (4.0, 4.0, 67), (8.0, 4.0, 60)]
        base = symphony.harmonize(mel, 'C major', 0.0, 3, 4.0, {2: 'I'})
        self.assertEqual(base, symphony.harmonize(mel, 'C major', 0.0, 3, 4.0, {2: 'I'}, chroma={}))
        self.assertTrue(all(w == 0 for w in symphony.CHROMA_WEIGHTS.values()))    # (the default: none)
        ch = symphony.harmonize([], 'C major', 0.0, 3, 4.0, {(1, 1): ('Ger6', 'N6'), 2: 'cad64'}, split={0, 1})
        syms = [s for _, _, s in ch]
        self.assertIn(syms[-2], ('Ab7', 'Db/F'))
        self.assertEqual(syms[-1], 'C/G')
        # (a chromatic candidate moves only into its resolution)
        ch = symphony.harmonize([], 'C major', 0.0, 2, 4.0, {1: 'V'}, split={0}, chroma={(0, 1): {'Ger6': 5.0,
                                                                                                    'It6': 5.0}})
        self.assertNotIn('Ab7', [s for _, _, s in ch])                        # (Ger6 goes to the six-four, not V)
        rows, rec = symphony.chroma_pre('A minor', 0.0, 4.0, 2, 'V', 'iv', None)
        self.assertEqual(len(rows), 4)                                        # (two chords a bar: the acceleration)
        self.assertEqual(rows[0][2], 'Dm')
        self.assertEqual(rec[0][0], 6.0)
        self.assertIn(rec[0][2], symphony.CHROMA_PRE['V'])
        self.assertIsNone(symphony.chroma_pre('D dorian', 0.0, 4.0, 2, 'V'))

    def test_chroma_cadence(self):
        g = endless.genre('orchestra-symphonic')
        plan = {'feel': 'allegro', 'layout': 'sonata', 'ending': 'cadence', 'frame': 'pedal', 'build': 'tremolo'}
        off = composer.compose(g, 31, plan=plan)
        self.assertFalse(any(b.get('chroma') for b in off.symphony['blocks']))
        old = symphony.CHROMA_CADENCE
        symphony.CHROMA_CADENCE = dict(symphony.CHROMA_CADENCE_ON)
        try:
            t = composer.compose(g, 31, plan=plan)
            s = endless.song(t)
        finally:
            symphony.CHROMA_CADENCE = old
        K = Key(t.key)
        if K.mode not in ('major', 'minor'):
            self.skipTest('a church mode: no chromatic vocabulary')
        kinds = {b['kind']: b for b in t.symphony['blocks'] if b.get('chroma')}
        self.assertTrue(kinds, [b['kind'] for b in t.symphony['blocks']])
        for kind, b in kinds.items():
            ch = sorted(b['chart'])
            for a, d, rn, tgt in b['chroma']:
                i = next(j for j, r in enumerate(ch) if abs(r[0] - a) < 1e-6)
                self.assertEqual(ch[i][2], symphony.chroma_symbol(b['key'], rn), kind)
                nxt = ch[i + 1][2] if i + 1 < len(ch) else None
                if kind == 'retrans':                                         # (into the dominant pedal)
                    self.assertEqual(nxt, symphony._roman(b['key'], 'V'))
                self.assertLess(ch[i - 1][1], t.symphony['U'] + 1e-6)          # (the accelerated harmonic rhythm)
        sc = composer.score(s, t, g)
        self.assertGreater(sc['mean'], 60)


class ChromaEvent(unittest.TestCase):
    """Round o15b: CHROMA_EVENT - the chromatic chord as an event (the final tutti predominant, the chord chain into
    the retransition's pedal), off by default; the gate fixes (SEQ_BREAK)."""

    def _rules(self, chords, got):
        for k, (c, (b, up)) in enumerate(zip(chords, got)):
            self.assertEqual(b % 12, c['bass'])
            have = {q % 12 for q in up} | {b % 12}
            need = set(c['pcs'])
            if c['name'] in symphony.EVENT_FIFTH and c['pcs'][2] != c['bass']:
                need.discard(c['pcs'][2])
            self.assertLessEqual(need, have, (c['sym'], up))
            self.assertTrue(all(x < y for x, y in zip(up, up[1:])))
            if k + 1 < len(got):
                nb, nup = got[k + 1]
                npcs = set(chords[k + 1]['pcs'])
                v0, v1 = [b] + up, [nb] + nup
                for i in range(len(v0)):
                    for j in range(i + 1, len(v0)):
                        self.assertFalse(symphony._parallel(v0[i], v1[i], v0[j], v1[j]), (c['sym'], v0, v1))
                for q0, q1 in zip(up, nup):
                    d = c['tend'].get(q0 % 12)
                    tg = [x for x in (q0 + (1 if d and d > 0 else -1), q0 + (2 if d and d > 0 else -2))
                          if x % 12 in npcs] if d else []
                    if tg:
                        self.assertTrue(q1 in tg or (abs(d) == 2 and q1 == q0), (c['sym'], q0, q1))

    def test_chains_voiced_by_the_rules(self):
        for key in ('C major', 'A minor', 'Eb major', 'F# minor', 'D minor'):
            mode = 'minor' if Key(key).minorish else 'major'
            for name, spec in symphony.EVENT_CHAINS.items():
                chords = [symphony._ev_chord(key, nm, bi) for nm, bi in spec[mode]] + [symphony._ev_chord(key, 'V')]
                got = symphony._event_voice(chords, n=4, lo=53, hi=81, centre=70)
                self.assertIsNotNone(got, (key, name))
                self._rules(chords, got)
            I = 'i' if mode == 'minor' else 'I'
            for rn, tail in (('Ger6', [(I, 2), ('V7', 0)]), ('N', [(I, 2), ('V7', 0)]), ('N', [('V7', 0)]),
                             ('Fr6', [('V7', 0)])):
                chords = [symphony._ev_chord(key, rn)] + [symphony._ev_chord(key, x, b) for x, b in tail] + \
                    [symphony._ev_chord(key, I)]
                got = symphony._event_voice(chords, n=4, lo=55, hi=84, centre=70)
                self.assertIsNotNone(got, (key, rn))
                self._rules(chords, got)
        c = symphony._ev_chord('C major', 'N')
        self.assertEqual((c['sym'], c['bass']), ('Db', 1))                       # (the bass on b2)
        self.assertEqual(symphony._ev_chord('C major', 'Ger6')['bass'], 8)       # (... on b6)
        self.assertEqual(symphony._ev_chord('A minor', 'V', 1)['sym'], 'E/G#')
        self.assertEqual(symphony._ev_chord('D minor', 'vii°')['sym'], 'C#dim')

    def test_events_in_the_piece(self):
        g = endless.genre('orchestra-symphonic')
        plan = {'feel': 'allegro', 'layout': 'sonata', 'ending': 'cadence', 'frame': 'pedal', 'build': 'tremolo',
                'key': 'D minor'}
        off = composer.compose(g, 31, plan=plan)
        self.assertIsNone(symphony.CHROMA_EVENT)
        self.assertFalse(any(b.get('event') for b in off.symphony['blocks']))
        old = symphony.CHROMA_EVENT
        symphony.CHROMA_EVENT = dict(symphony.CHROMA_EVENT_ON)
        try:
            t = composer.compose(g, 31, plan=plan)
            s = endless.song(t)
        finally:
            symphony.CHROMA_EVENT = old
        evs = {b['kind']: b for b in t.symphony['blocks'] if b.get('event')}
        self.assertEqual(set(evs), {'retrans', 'end'})
        U = t.symphony['U']
        e = evs['end']['event']
        self.assertIn(e['rn'], ('N', 'Ger6', 'Fr6'))
        self.assertEqual(e['hold'][1], U)                                         # (a full bar)
        self.assertIn(e['chords'][0][3] % 12, ((Key(t.key).tonic + 1) % 12, (Key(t.key).tonic + 8) % 12))
        r = evs['retrans']['event']
        self.assertEqual(r['chords'][-1][2], symphony._roman(t.key, 'V'))        # (into the dominant)
        ch = dict((a, sy) for a, _, sy in evs['retrans']['chart'])
        for a, d, sy, b, up in r['chords'][:-1]:
            self.assertEqual(ch[a], sy)
        th = {a: p for a, _, p in evs['retrans']['theme']}
        self.assertTrue(all(th.get(a) == p for a, _, p in r['tops']))            # (the melody on the top voice)
        tut = [p for p in s.orchestration.parts if p.voice.startswith('ev_')]
        self.assertTrue({p.block for p in tut} == {evs['retrans']['name'], evs['end']['name']})
        self.assertIn('trumpets', {p.role for p in tut})
        roles = {}
        for p in s.orchestration.parts:
            if p.notes and p.role not in symphony.TUTTI_SKIP:
                roles.setdefault(p.block, set()).add(p.role)
        peak = next(x.name for x in s.orch_score.blocks if x.peak)
        self.assertLessEqual(max(len(v) for v in roles.values()), len(roles[peak]))   # (tutti_peak holds)

    def test_seq_break(self):
        unit = [(0.0, 1.0, 60), (1.0, 1.0, 62), (2.0, 2.0, 64)]
        line = [(a + 4 * i, d, p + i) for i in range(5) for a, d, p in unit]
        self.assertEqual(symphony._seq_links(line, 4.0, 0.0, 20.0), 4)
        out = symphony._break_links(line, 4.0, 0.0, 20.0)
        self.assertLessEqual(symphony._seq_links(out, 4.0, 0.0, 20.0), symphony.SEQ_BREAK)
        self.assertLessEqual(symphony._seq_links(out, 8.0, 0.0, 20.0), symphony.SEQ_BREAK)
        self.assertEqual(sum(d for _, d, _ in out), sum(d for _, d, _ in line))   # (tied, not cut)
        short = line[:9]
        self.assertIs(symphony._break_links(short, 4.0, 0.0, 12.0), short)


class SetPlan(unittest.TestCase):
    """Round o18b: SYMPHONY_SETPLAN (genres.symphony_setplan, off by default) - the set-level draws diverse and
    memoryful (builds, endings, motto rhythm families, climaxes, the crisis arc, the meter mix); off restores all."""

    def setUp(self):
        from agentsound.endless import genres
        self.genres = genres
        self.g = endless.genre('orchestra-symphonic').validate()
        self.before = (composer.set_plan(self.g, 8, 133000), {f: dict(c) for f, c in symphony.CELLS.items()})
        genres.symphony_setplan(True, version=2)        # (round o20: v3 is the default; these are v1 / v2's)

    def tearDown(self):
        self.genres.symphony_setplan(False)

    def test_the_set_draws_never_repeat_within_their_memory(self):
        mem = self.g.plan['set_memory']
        for sd in (133000, 134000):
            p = composer.set_plan(self.g, 16, sd)
            for key in ('build', 'ending'):
                seq = [x[key] for x in p]
                for i, v in enumerate(seq):
                    self.assertNotIn(v, seq[max(0, i - mem[key]):i], (sd, key, seq))
                self.assertGreaterEqual(len(set(seq)), 5, (sd, key))
            for m, fams in symphony.MOTTO_FAMILIES.items():     # (the motto's rhythm family, per meter family)
                seq = [fams.get(x['motto'][m], x['motto'][m]) for x in p]
                for i, v in enumerate(seq):
                    self.assertNotIn(v, seq[max(0, i - mem['motto']):i], (sd, m, seq))
            for x in p:
                self.assertIn(x['build'], symphony.GESTURES)
                self.assertIn(x['ending'], symphony.END_TEX)
                self.assertIn(x['arc'], ('return', 'crisis'))
            meters = [tuple(self.g.feels[x['feel']]['time_sig']) for x in p]
            self.assertLessEqual(meters.count((6, 8)), 6, sd)
            self.assertIn('crisis', [x['arc'] for x in p], sd)

    def test_pieces_compose_and_the_endings_lose_harp_and_lone_timpani(self):
        p = composer.set_plan(self.g, 6, 133000)
        for k, slot in enumerate(p):
            t = composer.compose(self.g, 133000 + k, plan=slot)
            s = endless.song(t)
            mat = t.symphony
            self.assertEqual(sum(b['peak'] for b in mat['blocks']), 1, k)
            ends = {b['name'] for b in mat['blocks'] if b['kind'] in ('coda', 'coda_soft', 'end', 'end_soft')}
            parts = [q for q in s.orchestration.parts if q.notes]
            self.assertFalse(any(q.role == 'harp' and q.block in ends for q in parts), k)
            if t.arrange['ending'] != 'strokes':
                last = mat['blocks'][-1]['name']
                self.assertFalse(any(q.role == 'timpani' and q.block == last for q in parts), k)

    def test_off_restores_the_old_draws(self):
        self.genres.symphony_setplan(False)
        self.assertIsNone(symphony.SET_PLAN)
        self.assertEqual(composer.set_plan(self.g, 8, 133000), self.before[0])
        self.assertEqual({f: dict(c) for f, c in symphony.CELLS.items()}, self.before[1])
        self.assertNotIn('set_feel', self.g.plan)
        self.assertNotIn('set_shape', self.g.plan)

    def test_v2_shapes_never_repeat_per_feel_and_the_scherzo_is_capped(self):
        """Round o19a: a feel's (layout, sections) never twice in a set, at most 2 scherzos (3/4) in 16, the climax's
        place and the section count drawn."""
        for sd in (135000, 136000):
            p = composer.set_plan(self.g, 16, sd)
            shapes = [(x['feel'], x['layout'], x['sections']) for x in p]
            self.assertEqual(len(set(shapes)), len(shapes), (sd, shapes))
            self.assertLessEqual(sum(tuple(self.g.feels[x['feel']]['time_sig']) == (3, 4) for x in p), 2, sd)
            self.assertGreaterEqual(len({x['peak_at'] for x in p}), 4, sd)
            self.assertGreaterEqual(len({x['sections'] for x in p}), 4, sd)

    def test_v2_rows_shape_and_climax_place(self):
        rows = symphony._rows(self.g, 'scherzo_trio')
        less = symphony._shape_rows(rows, -2)
        more = symphony._shape_rows(rows, 2)
        self.assertEqual(len(less), len(rows) - 2)
        self.assertGreater(len(more), len(rows))
        self.assertEqual(len({r[0] for r in more}), len(more))
        self.assertEqual(more[-1][1], 'end')
        rows = symphony._rows(self.g, 'sonata')
        early = symphony._place_peak(self.g, rows, 0.62)
        late = symphony._place_peak(self.g, rows, 0.86)
        self.assertLess(symphony._peak_pos(self.g, early), symphony._peak_pos(self.g, late) - 0.1)

    def test_v2_pieces_no_harp_after_the_climax_and_the_endings(self):
        p = composer.set_plan(self.g, 16, 135000)
        seen = set()
        for k, slot in enumerate(p):
            if slot['ending'] in seen and len(seen) < 3:
                continue
            seen.add(slot['ending'])
            t = composer.compose(self.g, 135000 + 10 * k, plan=slot)
            s = endless.song(t)
            mat = t.symphony
            pi = next(i for i, b in enumerate(mat['blocks']) if b['peak'])
            after = {b['name'] for b in mat['blocks'][pi + 1:]}
            harp = [q for q in s.orchestration.parts if q.notes and q.role == 'harp']
            self.assertFalse(any(q.block in after for q in harp), k)
            self.assertTrue(not harp or sum(len(q.notes) for q in harp) >= symphony.POST_HARP['min'], k)
            last = mat['blocks'][-1]
            if last.get('amen') is not None:      # (V7 - I, then IV - I with 4 - 3 on top)
                ch = [sy for _, d, sy in sorted(last['chart']) if d > 1e-6]
                from agentsound.theory import Key, chord
                K = Key(last['key'])
                self.assertEqual([chord(x.split('/')[0]).root % 12 for x in ch[-4:]],
                                 [(K.tonic + i) % 12 for i in (7, 0, 5, 0)], ch)
            if len(seen) >= 4:
                break

    def test_the_set_keys_apart_per_meter(self):
        """Round o19a (master, flag off too): no key twice per time signature in a set - o18b's two F major scherzos
        played the same development bars."""
        self.genres.symphony_setplan(False)
        for sd in (133000, 135000, 136000):
            p = composer.set_plan(self.g, 16, sd)
            ks = [(tuple(self.g.feels[x['feel']]['time_sig']), x['key']) for x in p]
            self.assertEqual(len(set(ks)), len(ks), (sd, ks))


class SetPlanV3(unittest.TestCase):
    """Round o20: SET_PLAN v3 (genres.symphony_setplan(True, version=3); v4 the default since round o22, v2 still
    reachable) - the shape by merging and lengthening, the section textures with set memory, the dissolving fade
    capped, no crisis arc, the climax at 0.66 or later, the harp gated on its level (no empty harp track)."""

    def setUp(self):
        from agentsound.endless import genres
        self.genres = genres
        self.g = endless.genre('orchestra-symphonic').validate()
        genres.symphony_setplan(True, version=3)

    def tearDown(self):
        self.genres.symphony_setplan(False)

    def test_v3_and_v2_reachable(self):
        self.assertTrue(symphony.SET_PLAN.get('v3') and not symphony.SET_PLAN.get('v4'))
        self.genres.symphony_setplan(True, version=2)
        self.assertEqual(symphony.SET_PLAN, symphony.SET_PLAN_V2)
        self.assertIn(2, self.g.plan['set']['sections'])
        self.genres.symphony_setplan(True, version=3)
        self.assertEqual(symphony.SET_PLAN, symphony.SET_PLAN_V3)
        self.assertEqual(set(self.g.plan['set']['sections']), set(symphony.FORM_MERGE['deltas']))
        self.assertNotIn('frag', self.g.plan['set'])
        self.assertNotIn('set_bars', self.g.plan)

    def test_v3_draws_no_crisis_and_textures_never_repeat_within_memory(self):
        mem = self.g.plan['set_memory']
        for sd in (139000, 140000):
            p = composer.set_plan(self.g, 16, sd)
            self.assertEqual({x['arc'] for x in p}, {'return'})
            self.assertGreaterEqual(min(x['peak_at'] for x in p), 0.7)
            for key in ('tex_t1', 'tex_dev', 't2col'):
                seq = [x[key] for x in p]
                for i, v in enumerate(seq):
                    self.assertNotIn(v, seq[max(0, i - mem[key]):i], (sd, key, seq))

    def test_merge_rows_folds_and_caps(self):
        rows = symphony._rows(self.g, 'sonata')
        out = symphony._merge_rows(self.g, rows, 2, symphony.FORM_MERGE['cap'])
        self.assertLessEqual(len(out), symphony.FORM_MERGE['cap'])
        self.assertEqual(sum(r[2] for r in out) <= sum(r[2] for r in rows), True)
        self.assertEqual([r[1] for r in out][-1], 'end')
        self.assertTrue(any(r[1] == 'recap' for r in out) and any(r[1] == 'retrans' for r in out))
        self.assertEqual(len(symphony._merge_rows(self.g, rows, 0, 99)), len(rows))

    def test_v3_pieces_shape_fade_peak_and_harp(self):
        from agentsound.endless.perform import build
        p = composer.set_plan(self.g, 16, 139000)
        for k in (0, 4, 8, 10):                 # (two dissolving codas, the scherzo, a rondo)
            t = composer.compose(self.g, 139000 + 10 * k, plan=p[k])
            s = build(t, self.g)
            mat = t.symphony
            blocks = mat['blocks']
            self.assertLessEqual(len(blocks), symphony.FORM_MERGE['cap'], k)
            sc = float(mat['scale'])
            bars = [b['bars'] * sc for b in blocks]
            pi = next(i for i, b in enumerate(blocks) if b['peak'])
            pos = (sum(bars[:pi]) + bars[pi] / 2) / sum(bars)
            self.assertGreaterEqual(pos, symphony.PEAK_AT_V3['floor'] - 0.03, k)
            fade = sum(x for x, b in zip(bars, blocks) if b['kind'] in ('coda_soft', 'end_soft'))
            self.assertLessEqual(fade, symphony.FADE_V3['max'] + 1e-6, k)
            self.assertFalse(any(b['over'].get('crisis') for b in blocks), k)
            parts = s.orchestration.parts
            self.assertTrue(all(any(q.notes for q in parts if q.role == r) for r in {q.role for q in parts}), k)
            after = {b['name'] for b in blocks[pi + 1:]}
            self.assertFalse(any(q.role == 'harp' and q.block in after and q.notes for q in parts), k)


class SetPlanV4(unittest.TestCase):
    """Round o22: SET_PLAN v4 (genres.symphony_setplan(True), the default version; v3 reachable) - a change at every
    merged join inside one section (JOIN_V4), the set's memory on the mode / key over every meter, the endings'
    dynamic alternating, the realised bar plans apart (bar_plan, the layout once per feel), the fragmentation's shape
    with memory (FRAG_V4: the ladder one shape of five)."""

    def setUp(self):
        from agentsound.endless import genres
        self.genres = genres
        self.g = endless.genre('orchestra-symphonic').validate()
        self.arc0 = dict(self.g.arc['set'])
        genres.symphony_setplan(True)

    def tearDown(self):
        self.genres.symphony_setplan(False)

    def test_v4_is_the_default_and_off_restores(self):
        self.assertEqual(symphony.SET_PLAN, symphony.SET_PLAN_V4)
        self.assertIn('frag', self.g.plan['set'])
        self.assertIn('set_bars', self.g.plan)
        self.genres.symphony_setplan(False)
        self.assertNotIn('frag', self.g.plan['set'])
        self.assertNotIn('set_bars', self.g.plan)
        self.assertEqual(self.g.arc['set'], self.arc0)
        self.genres.symphony_setplan(True)

    def test_v4_set_memory_mode_key_endings_layouts_bars_frag(self):
        X = self.g.plan['set_bars']
        mem = self.g.plan['set_memory']['frag']
        for sd in (143500, 139700, 143800):
            p = composer.set_plan(self.g, 8, sd)
            keys = [s['key'] for s in p]
            self.assertGreaterEqual(sum(not k.endswith(' major') for k in keys), 2, (sd, keys))
            self.assertLessEqual(max(keys.count(k) for k in keys), 2, (sd, keys))
            codas = [s['coda'] for s in p]
            for i, c in enumerate(codas):
                self.assertIn(c, self.g.moods[p[i]['mood']]['coda'], (sd, i))
                if i and codas[i - 1] == 'dissolve':
                    self.assertEqual(c, 'triumph', (sd, codas))
                if i >= 2 and codas[i - 2] == codas[i - 1] == 'triumph':
                    self.assertEqual(c, 'dissolve', (sd, codas))
            fl = [(s['feel'], s['layout']) for s in p]
            self.assertEqual(len(fl), len(set(fl)), (sd, fl))
            frag = [s['frag'] for s in p]
            for i, v in enumerate(frag):
                self.assertNotIn(v, frag[max(0, i - mem):i], (sd, frag))
            vs = [symphony.bar_plan(self.g, s) for s in p]
            for i in range(1, len(vs)):
                self.assertLessEqual(max(composer._bar_sim(vs[i], h, X['tol']) for h in vs[:i]), X['sim'] + 1e-9,
                                     (sd, i, vs))

    def test_merge_parts_and_split_joins(self):
        rows = symphony._rows(self.g, 'sonata')
        out = symphony._merge_rows(self.g, rows, 3, symphony.FORM_MERGE['cap'], parts=True)
        merged = [r for r in out if r[3].get('parts')]
        self.assertTrue(merged)
        self.assertEqual([r[:3] for r in symphony._merge_rows(self.g, rows, 3, symphony.FORM_MERGE['cap'])],
                         [r[:3] for r in out])
        sp = symphony._split_joins(out, 1)
        self.assertEqual(sum(r[2] for r in sp), sum(r[2] for r in out))
        joined = [r for r in sp if r[3].get('joined')]
        self.assertTrue(joined)
        self.assertTrue(all(r[2] >= symphony.JOIN_V4['least'] for r in sp if r[3].get('joined')))
        self.assertFalse(any(r[3].get('parts') for r in sp))
        names = [r[0] for r in sp]
        self.assertEqual(len(names), len(set(names)))
        for r in joined:                          # (a later part follows the block it joins or a part of it)
            i = names.index(r[0])
            self.assertTrue(sp[i - 1][0] == r[3]['joined'] or sp[i - 1][3].get('joined') == r[3]['joined'])

    def test_the_fragmentation_shape(self):
        m = {'family': 'duple', 'kind': 'arch', 'land': 3, 'member': 'root'}

        def frag(shape):
            w = symphony.Writer('C major', 'duple', m, {'answer': 'dominant', 'frag': shape}, random.Random(1))
            mel, _ = w.sentence('t1', 'C major', 0.0, 12)
            tops = [max((p for a, _, p in mel if 4 * b <= a < 4 * b + 4), default=None) for b in range(4, 10)]
            return mel, tops
        rise, tr = frag('rise')
        fall, tf = frag('fall')
        self.assertNotEqual(rise, fall)
        self.assertGreater(tr[-1], tr[0])
        self.assertLess(tf[-1], tf[0])

    def test_v4_pieces_join_inside_one_section(self):
        from agentsound.endless.perform import build
        p = composer.set_plan(self.g, 8, 143500)
        seen = 0
        for k in (2, 4, 7):                     # (an episode join, the scherzo's t1b / trio joins, a close join)
            t = composer.compose(self.g, 143500 + 10 * k, plan=p[k])
            s = build(t, self.g)
            blocks = t.symphony['blocks']
            tex = {b.name: b.texture for b in s.orch_score.blocks}
            names = [b['name'] for b in blocks]
            secs = {x.name for x in s.sections}
            self.assertLessEqual(len(secs), symphony.FORM_MERGE['cap'], k)
            for i, b in enumerate(blocks):
                if b.get('joined'):
                    seen += 1
                    self.assertNotIn(b['name'], secs, k)
                    self.assertNotEqual(tex[b['name']], tex[names[i - 1]], (k, b['name']))
            bpb = s.beats_per_bar
            got = []
            for x in s.sections:
                n = round((x.end - x.start) / bpb)
                if x.name == 'end' and got:
                    got[-1] += n
                else:
                    got.append(n)
            want = symphony.bar_plan(self.g, p[k])
            self.assertEqual(len(got), len(want), k)
            self.assertLessEqual(max(abs(a - b) for a, b in zip(got, want)), 2, (k, got, want))
        self.assertGreaterEqual(seen, 3)


class ScoreGates(unittest.TestCase):
    """The code review's G1: the construction-guaranteed metrics are assertions (weight 0, hard), not best-of-N rank."""

    def test_gates_rank_nothing_and_cap(self):
        from agentsound.endless import genres
        new, old = genres.symphony_table(False), genres.symphony_table(True)
        for k in genres.SYMPHONY_GATES:
            self.assertEqual(new[k][2:4], (0, True), k)
            self.assertGreater(old[k][2], 0, k)
        self.assertEqual(set(new), set(old))
        m = {k: (v[0] + v[1]) / 2 for k, v in old.items()}
        hi = composer.score(None, metrics=m, table=new, style='symphony')
        self.assertEqual((hi['score'], hi['hard']), (100.0, []))
        bad = dict(m, acc_run=20)
        self.assertEqual(composer.score(None, metrics=bad, table=new, style='symphony')['hard'], ['acc_run'])
        self.assertLessEqual(composer.score(None, metrics=bad, table=new, style='symphony')['score'],
                             genres.SCORE_HARD_CAP)
        was = genres.SYMPHONY_RANK_GATES
        tab = genres.SCORES['symphony']
        try:
            genres.symphony_ranking(True)
            self.assertIs(genres.SCORES['symphony'], tab)
            self.assertEqual(tab, old)
        finally:
            genres.symphony_ranking(was)
        self.assertEqual(genres.SCORES['symphony'], genres.symphony_table())


def _legacy_motto_notes(m, t, anchor, pcs, tf=(), land=None, fill=None):
    """motto_notes as it was before the derivation engine (round o16's step 1 is bit-identical to it)."""
    from agentsound.endless.symphony import _EPS, _step, cell_of
    L = m['land'] if land is None else land
    k = 2.0 if 'augment' in tf else 0.5 if 'diminish' in tf else 1.0
    out, seen_l = [], False
    prev, ls = 0, None
    for on, du, st in cell_of(m):
        if isinstance(st, tuple):
            s = (ls if ls is not None else prev + L) + st[1]
        elif st == 'L':
            if 'head' in tf and seen_l:
                break
            s, seen_l = prev + L, True
            ls = s
        else:
            s = st
        prev = s
        if 'chordal' in tf:
            s = 0
        if 'invert' in tf:
            s = -s
        dur = du * k
        if 'head' in tf and st == 'L':
            dur = min(dur, 1.0 * k)
        out.append((t + on * k, dur, _step(anchor, s, pcs)))
        if 'head' in tf and st == 'L':
            break
    if 'kernel' in tf and out:
        kl = (2.0 if m['family'] == 'duple' else 1.5) * k
        keep = [n for n in out if n[0] - t < kl - _EPS]
        keep = keep if len(keep) >= 2 else out[:2]
        a, d, p = keep[-1]
        keep[-1] = (a, max(0.25 * k, t + kl - a) if a - t < kl else d, p)
        out = keep
    if fill is not None and out:
        a, d, p = out[-1]
        out[-1] = (a, max(d, fill - a), p)
    return out


class DevWalk(unittest.TestCase):
    """Round o16: the code review's A1 - the Kernel / transform algebra (motto_notes through it, bit-identical), the
    development as a planned walk (DEV_WALK, off by default), the derivation graph's metrics."""

    def test_kernel_is_motto_notes(self):
        import itertools
        tfs = [(), ('invert',), ('augment',), ('diminish',), ('head',), ('kernel',), ('chordal',),
               ('head', 'invert'), ('kernel', 'diminish', 'invert'), ('head', 'augment'), ('head', 'diminish')]
        for fam, cells in symphony.CELLS.items():
            for kind, land, member in itertools.product(cells, (-2, 1, 3), ('root',)):
                m = {'family': fam, 'kind': kind, 'land': land, 'member': member}
                for tf in tfs:
                    for t, fill in ((0.0, None), (13.25, 20.0)):
                        self.assertEqual(symphony.motto_notes(m, t, 64, MAJOR, tf, None, fill),
                                         _legacy_motto_notes(m, t, 64, MAJOR, tf, None, fill), (kind, land, tf))

    def test_the_ops(self):
        K = symphony.Kernel.motto({'family': 'duple', 'kind': 'hammer', 'land': 3, 'member': 'root'})
        self.assertEqual(K.intervals(), (0, 1, 1, 3))
        self.assertEqual(K.contour(), (0, 1, 1, 1))
        self.assertEqual(K.signature(), (0, 4))
        plain = K.steps(0.0)
        retro = K.steps(0.0, ('retro',))
        self.assertEqual([s for _, _, s in retro], [0, -3, -4, -5, -5])          # (from the anchor, reversed)
        self.assertAlmostEqual(max(a + d for a, d, _ in retro), K.span())
        self.assertEqual([s for _, _, s in K.steps(0.0, ('expand',))], [0, 0, 2, 4, 8])
        self.assertEqual([s for _, _, s in K.steps(0.0, ('contract',))], [0, 0, 1, 2, 4])
        self.assertEqual([s for _, _, s in K.steps(0.0, ('liquidate',))], [0, 0, 1, 2, 3])
        self.assertEqual([a for a, _, _ in K.steps(0.0, ('displace',))], [a + 0.5 for a, _, _ in plain])
        self.assertEqual([a for a, _, _ in K.steps(0.0, ('shift',))], [a + 2.0 for a, _, _ in plain])
        f2 = K.steps(0.0, ('frag2',))
        self.assertEqual(len(f2), 2)
        self.assertGreaterEqual(f2[-1][1], 1.0)
        other = symphony.Kernel([(0, 1, 0), (1, 1, 2), (2, 2, 'L')], -1, 'duple', 'K2')
        self.assertEqual(other.intervals(), (2, -1))
        self.assertEqual([s for _, _, s in K.steps(0.0, ('combine',), other=other)], [0, 2, 1, 3, 2])
        for op in ('mode', 'reharm', 'recall'):                                  # (harmony / log ops: the notes pass)
            self.assertEqual(K.steps(0.0, (op,)), plain)
        ln = [(0.0, 1.0, 64), (1.0, 0.5, 67), (1.5, 0.5, 65), (2.0, 2.0, 69)]
        K2 = symphony.Kernel.line(ln, 'C major', 'duple', 4.0)
        self.assertEqual([p for _, _, p in K2.apply(0.0, 64, MAJOR)], [64, 67, 65, 69])

    def test_off_by_default_and_the_walk(self):
        from agentsound.endless import genres
        self.assertIsNone(symphony.DEV_WALK)
        self.assertFalse(genres.SYMPHONY_DERIVE)
        g = endless.genre('orchestra-symphonic')
        plan = {'feel': 'allegro', 'layout': 'sonata', 'key': 'D minor'}
        off = composer.compose(g, 31, plan=plan)
        self.assertFalse(any(b.get('route') for b in off.symphony['blocks']))
        self.assertNotIn('dev_ops', symphony.derive_stats(endless.song(off)))
        old = symphony.DEV_WALK
        symphony.DEV_WALK = dict(symphony.DEV_WALK_V1)         # (round o16's walk: the phases split into blocks)
        try:
            t = composer.compose(g, 31, plan=plan)
            t2 = composer.compose(g, 31, plan=plan)
            self.assertEqual(t.symphony['blocks'], t2.symphony['blocks'])       # (deterministic)
            s = endless.song(t)
            st = symphony.derive_stats(s)
        finally:
            symphony.DEV_WALK = old
        U = t.symphony['U']
        dev = [b for b in t.symphony['blocks'] if b['kind'] == 'dev_dialogue']
        n_off = sum(b['bars'] for b in off.symphony['blocks'] if b['kind'] == 'dev_dialogue')
        self.assertEqual(sum(b['bars'] for b in dev), n_off)                     # (the phases: the same bars)
        self.assertGreaterEqual(len(dev), sum(1 for b in off.symphony['blocks'] if b['kind'] == 'dev_dialogue'))
        for b in dev:
            self.assertIn(b['phase'], symphony.WALK['arrange'])
            self.assertEqual(b['over']['tex'], symphony.WALK['tex'][b['phase']])
            self.assertTrue(b['route'])
            self.assertEqual(sum(r['len'] * r['reps'] for r in b['route']), b['bars'])
            for r in b['route']:
                self.assertTrue(1 <= r['len'] <= 4 and 1 <= r['reps'] <= 3, r)
                self.assertEqual(r['depth'], len(r['ops']))
            for a, d, _ in b['theme'] + b['answer']:
                self.assertTrue(b['start'] - 1e-6 <= a and a + d <= b['start'] + b['bars'] * U + 1e-6)
            self.assertEqual(_overlaps(b['theme']), 0)
            self.assertEqual(sum(d for _, d, _ in b['chart']), b['bars'] * U)
        last = dev[-1]['route'][-1]
        self.assertEqual(last['goal'], t.key)                                    # (into the retransition)
        names = {b['name'] for b in t.symphony['blocks']}
        nodes = {e['node']: e for e in t.symphony['log'] if 'node' in e}
        for e in t.symphony['log']:
            self.assertIn(e['block'], names)
            if e['block'] in {b['name'] for b in dev}:
                self.assertTrue(e['parent'] in nodes or e['parent'] in ('K1', 'K2'), e)
        rec = [e for e in t.symphony['log'] if e['tf'] == 'recall']
        self.assertTrue(rec)
        self.assertTrue(all(e['ops'][-1] == 'recall' and e['parent'] in nodes for e in rec))
        self.assertGreaterEqual(st['dev_ops'], 6)
        self.assertEqual(st['dev_literal'], 0)
        self.assertIn('dev_depth', st)

    def test_v2_one_block_of_processes(self):
        """Round o17: DEV_WALK v2 (DEV_WALK_V2) - the layout's development blocks unsplit, each 1-3 worked processes
        of 8+ song bars, every statement at most WALK2 'cap' ops with one interval op, one texture per block, the
        level rising per process."""
        g = endless.genre('orchestra-symphonic')
        old = symphony.DEV_WALK
        for plan, seed in (({'feel': 'allegro', 'layout': 'sonata', 'key': 'D minor'}, 31),
                           ({'feel': 'scherzo', 'key': 'A minor'}, 129070), ({'feel': 'vivace', 'key': 'F major'}, 33)):
            symphony.DEV_WALK = None
            try:
                off = composer.compose(g, seed, plan=plan)
                symphony.DEV_WALK = dict(symphony.DEV_WALK_V2)
                t = composer.compose(g, seed, plan=plan)
                t2 = composer.compose(g, seed, plan=plan)
                self.assertEqual(t.symphony['blocks'], t2.symphony['blocks'])   # (deterministic)
            finally:
                symphony.DEV_WALK = old
            mat = t.symphony
            U, sc = mat['U'], mat['scale']
            dev = [b for b in mat['blocks'] if b['kind'] == 'dev_dialogue']
            self.assertEqual([(b['name'], b['bars']) for b in dev],
                             [(b['name'], b['bars']) for b in off.symphony['blocks'] if b['kind'] == 'dev_dialogue'])
            names = {b['name'] for b in dev}
            for b in dev:
                self.assertNotIn('phase', b)
                self.assertEqual(sum(r['bars'] for r in b['route']), b['bars'])
                if b['bars'] * sc >= symphony.WALK2['bars'][0]:
                    self.assertTrue(all(r['bars'] * sc >= symphony.WALK2['bars'][0] for r in b['route']), b['route'])
                for r in b['route']:
                    self.assertIn(r['arr'], symphony.WALK2['procs'])
                    self.assertLessEqual(len(r['ops']), symphony.WALK2['cap'])
                    self.assertLessEqual(len(set(r['ops']) & set(symphony.WALK2['interval'])), 1)
                    self.assertNotIn('retro', r['ops'])
                self.assertEqual(len(b['over']['tex']) >= 1, True)
                self.assertTrue(all(x in orc.TEXTURES for x in b['over']['tex']))
                for a, d, _ in b['theme'] + b['answer']:
                    self.assertTrue(b['start'] - 1e-6 <= a and a + d <= b['start'] + b['bars'] * U + 1e-6)
                self.assertEqual(_overlaps(b['theme']), 0)
                self.assertAlmostEqual(sum(d for _, d, _ in b['chart']), b['bars'] * U)
            self.assertEqual(dev[-1]['route'][-1]['goal'], t.key)               # (into the retransition)
            for e in mat['log']:
                if e['block'] in names and 'node' in e:
                    self.assertLessEqual(len(e['ops']), symphony.WALK2['cap'], e)
                    self.assertLessEqual(len(set(e['ops']) & set(symphony.WALK2['interval'])), 1, e)

    def test_v3_one_key_time_sized_stretto(self):
        """Round o18a: DEV_WALK_ON is v3 - every development block in one key or with ONE prepared modulation (into
        the next block's key, by a pivot chord or the new key's dominant), the last process before the retransition
        driving into it (the home key's dominant, no cadence), the drive at most WALK3 'drive' bars, no note under
        WALK3's least length, the stretto's tenor and bass entries inside its window; the processes sized by seconds
        (an andante's block holds more of them)."""
        g = endless.genre('orchestra-symphonic')
        old = symphony.DEV_WALK
        W3 = symphony.WALK3
        for plan, seed in (({'feel': 'allegro', 'layout': 'sonata', 'key': 'D minor'}, 31),
                           ({'feel': 'andante', 'key': 'F major'}, 131030),
                           ({'feel': 'scherzo', 'key': 'A minor'}, 129070), ({'feel': 'vivace', 'key': 'F major'}, 33)):
            symphony.DEV_WALK = None
            try:
                off = composer.compose(g, seed, plan=plan)
                symphony.DEV_WALK = dict(symphony.DEV_WALK_ON)
                t = composer.compose(g, seed, plan=plan)
                t2 = composer.compose(g, seed, plan=plan)
                self.assertEqual(t.symphony['blocks'], t2.symphony['blocks'])   # (deterministic)
                s = endless.song(t)
            finally:
                symphony.DEV_WALK = old
            self.assertTrue(symphony.DEV_WALK_ON.get('v3'))
            mat = t.symphony
            U, sc = mat['U'], mat['scale']
            blocks = mat['blocks']
            dev = [b for b in blocks if b['kind'] == 'dev_dialogue']
            self.assertEqual([(b['name'], b['bars']) for b in dev],
                             [(b['name'], b['bars']) for b in off.symphony['blocks'] if b['kind'] == 'dev_dialogue'])
            for b in dev:
                r = b['route']
                self.assertEqual(sum(x['bars'] for x in r), b['bars'])
                self.assertEqual(b['key'], r[0]['key'])
                self.assertLessEqual(len({x['key'] for x in r} | {r[-1]['goal']}), 2, r)      # (one key or one move)
                self.assertLessEqual(sum(1 for x in r if x['mod']), 1, r)
                for x in r:
                    self.assertEqual(x['mod'], x['goal'] != x['key'])
                    if x['mod'] and x['arrive'] != 'drive':
                        self.assertIn(x['arrive'], W3['modulate'])
                    self.assertLessEqual(len(x['ops']), W3['cap'])
                    self.assertFalse({'diminish', 'mode'} & set(x['ops']))
                    self.assertLessEqual(x['drive'], W3['drive'], x)
                    if len(r) > 1:
                        self.assertGreaterEqual(x['bars'], W3['least'])
                nxt = blocks[blocks.index(b) + 1]
                if nxt['kind'] == 'retrans':
                    self.assertEqual((r[-1]['arrive'], r[-1]['goal']), ('drive', t.key))
                elif nxt['kind'] == 'dev_dialogue':
                    self.assertEqual(r[-1]['goal'], nxt['key'])                      # (prepared: the next block's key)
                for a, d, _ in b['theme'] + b['answer']:
                    self.assertTrue(b['start'] - 1e-6 <= a and a + d <= b['start'] + b['bars'] * U + 1e-6)
                    self.assertGreaterEqual(d, W3['min_beat'] / sc - 1e-6)
                self.assertEqual(_overlaps(b['theme']), 0)
                self.assertAlmostEqual(sum(d for _, d, _ in b['chart']), b['bars'] * U)
                self.assertTrue(all(x in orc.TEXTURES for x in b['over']['tex']))
                e = b.get('entries')
                if any(x['arr'] == 'stretto' for x in r):
                    self.assertTrue(e and e['bass'] and e['win'], b['name'])
                    if 'dialogue_brass' not in b['over']['tex']:
                        self.assertEqual(b['over']['tex'], W3['tex']['stretto'])
                    for a, d, _ in e['inner'] + e['bass']:
                        self.assertTrue(any(w0 - 1e-6 <= a < w1 for w0, w1 in e['win']))
                else:
                    self.assertIsNone(e)
            self.assertTrue(s.orch_score.blocks)
        # the time: an andante's block holds more processes than the same bars at an allegro
        w = symphony.Writer('C major', 'duple', {'family': 'duple', 'kind': 'hammer', 'land': 3, 'member': 'root'},
                            {'seed': 1}, random.Random(1))
        counts = []
        for bar_s in (1.8, 3.2):
            w.bar_s = bar_s
            w.walk_mem = {'used': {}, 'false': False, 'chain': None, 'lines': []}
            got = w.walk3('dev1', ['A minor', 'F major'], 0.0, 16, 'C major', None, (0.0, 1.0), {},
                          ('C major', 'retrans'), 0)
            counts.append(len(got[4]))
        self.assertLess(counts[0], counts[1])

    def test_the_graph_table(self):
        from agentsound.endless import genres
        tab = genres.SCORES['symphony']
        try:
            genres.symphony_derive(True)
            self.assertIs(genres.SCORES['symphony'], tab)
            self.assertEqual(tab['dev_own'][2:4], (0, False))
            self.assertTrue(tab['dev_ops'][3] and tab['dev_literal'][3])
        finally:
            genres.symphony_derive(False)
        self.assertEqual(genres.SCORES['symphony'], genres.symphony_table())
        self.assertNotIn('dev_ops', genres.SCORES['symphony'])


class Fugue(unittest.TestCase):
    """Round o19b: FUGUE_ON - the dev_fugato as a fugal exposition (subject, answer at the fifth, counter-subject,
    entries in 3-4 voices over the choirs), an episode modulating into a related key, the final entry; the joint voice
    leading checked (voicing.cp_issues) and the entering voice in front."""

    def test_fugue_on(self):
        g = endless.genre('orchestra-symphonic')
        for F_, plan, seed in (
                (symphony.FUGUE_ON_V1, {'feel': 'allegro', 'layout': 'sonata', 'key': 'D minor',
                                        'dev': 'fugato_dialogue'}, 31),
                (symphony.FUGUE_ON_V1, {'feel': 'andante', 'key': 'Eb major', 'dev': 'fugato_dialogue'}, 137120),
                (symphony.FUGUE_ON, {'feel': 'allegro', 'layout': 'sonata', 'key': 'D minor',
                                     'dev': 'fugato_dialogue'}, 31),
                (symphony.FUGUE_ON, {'feel': 'andante', 'key': 'Eb major', 'dev': 'fugato_dialogue'}, 137120),
                (symphony.FUGUE_ON, {'feel': 'scherzo', 'key': 'A minor', 'dev': 'fugato'}, 137080),
                (symphony.FUGUE_ON, {'feel': 'river', 'key': 'G minor', 'dev': 'fugato_dialogue'}, 137060)):
            V2 = F_.get('v2')
            old = symphony.FUGUE
            try:
                symphony.FUGUE = None
                off = composer.compose(g, seed, plan=plan)
                symphony.FUGUE = dict(F_)
                t = composer.compose(g, seed, plan=plan)
                t2 = composer.compose(g, seed, plan=plan)
                self.assertEqual(t.symphony['blocks'], t2.symphony['blocks'])          # (deterministic)
                s = endless.song(t) if SSO else None
            finally:
                symphony.FUGUE = old
            self.assertFalse([b for b in off.symphony['blocks'] if b.get('fugue')])
            mat = t.symphony
            U, home = mat['U'], t.key
            fug = [b for b in mat['blocks'] if b['kind'] == 'dev_fugato']
            self.assertTrue(fug, plan)
            for b in fug:
                f = b['fugue']
                rel = {symphony.fugue_key(home, rn) for rn in F_['keys']['minor' if Key(home).minorish else 'major']}
                self.assertIn(b['key'], rel)
                self.assertEqual(set(b['voices']), {'v1', 'v2', 'v3', 'v4'})
                leads = f['leads']
                self.assertGreaterEqual(len({v for v, _, _ in leads}), 3)
                (v1, a1, z1), (v2, a2, _) = leads[:2]
                self.assertNotEqual(v1, v2)
                s1 = [p for a, _, p in b['voices'][v1] if a1 - 1e-6 <= a < z1 - 1e-6]
                s2 = [p for a, _, p in b['voices'][v2] if a2 - 1e-6 <= a < a2 + z1 - a1 - 1e-6]
                self.assertEqual(len(s1), len(s2))
                self.assertTrue(all((q - p) % 12 == 7 for p, q in zip(s1[1:], s2[1:])))   # (the answer at the fifth)
                cs = [n for n in b['voices'][v1] if a2 - 1e-6 <= n[0] < a2 + z1 - a1 - 1e-6]
                self.assertTrue(cs)                                                 # (the counter-subject under it)
                self.assertNotEqual([round(n[0] - a2, 3) for n in cs],
                                    [round(n[0] - a2, 3) for n in b['voices'][v2] if a2 - 1e-6 <= n[0] < a2 + z1 - a1])
                if any(x[0] == 'ep' for x in f['form']) and b['bars'] >= 10:
                    self.assertGreater(len(set(f['keys'])), 1, f['form'])              # (the episode modulates)
                self.assertEqual(sum(x[1] for x in f['form']), b['bars'])
                self.assertAlmostEqual(sum(d for _, d, _ in b['chart']), b['bars'] * U)
                self.assertIn(list(b['over']['tex'])[0], V2['tex'] | V2['tex_dance'] if V2 else F_['tex'])
                if V2:                                  # (round o21: v2's exposition)
                    ents = f['entries']
                    self.assertEqual(ents[0], b['start'])
                    self.assertGreaterEqual(f['pad'], ents[min(1, len(ents) - 1)])     # (the pad under two entries)
                    if leads[0][0] != 'v4':                                      # (a pedal under the first entry)
                        self.assertTrue(b['pedal'] and b['pedal'][0][0] == b['start'], b['pedal'])
                    self.assertTrue(f['cs'] and f['cs_notes'])                  # (the counter-subject, its notes)
                    marks = [m[1] for m in b['over']['dyn']]
                    self.assertLess(orc._MARKS.index(marks[0]), orc._MARKS.index(marks[-1]))
                    if t.feel in V2['cap']:
                        self.assertLessEqual(b['bars'], V2['cap'][t.feel])
                        self.assertIn(list(b['over']['tex'])[0], V2['tex_dance'])
                    k1, th, _ = next(((x['key'], x['theme'], x['start']) for x in mat['blocks']
                                      if x['kind'] in ('t1', 'river')), (None, None, None))
                    sub = f['subject']
                    if th:                                                      # (the first theme's opening)
                        t1s = next(x['start'] for x in mat['blocks'] if x['kind'] in ('t1', 'river'))
                        op = [(round(a - t1s, 3), q) for a, _, q in th if a < t1s + U - 1e-6]
                        self.assertEqual([a for a, _ in op], [round(a, 3) for a, _, _ in sub][:len(op)])
                    peak = [x for x in mat['blocks'] if x['peak'] and x['start'] > b['start']]
                    if peak and peak[0]['theme']:                               # (the subject back at the summit)
                        r_ = peak[0].get('fug_return')
                        self.assertTrue(r_, peak[0]['name'])
                        lo, hi = V2['ret']['range']
                        self.assertTrue(lo - 5 <= sum(q for _, _, q in r_) / len(r_) <= hi + 5)
                notes = sum(len(ns) for ns in b['voices'].values())
                # (v2: the first theme's opening as the subject - a river tune's arpeggios leave more weak-beat
                # clashes against the held free voices: notes // 5)
                self.assertLessEqual(f['n_issues'], max(10, notes // (5 if V2 else 8)), f['issues'])
                for ns in b['voices'].values():
                    self.assertEqual(_overlaps(ns), 0)
                    self.assertLessEqual(symphony._seq_links(ns, U, b['start'], b['start'] + b['bars'] * U),
                                         symphony.SEQ_BREAK)
                if s is not None:                                                   # (the choirs: 3+ families)
                    roles = {p.role for p in s.orchestration.by_block(b['name']) if p.function == 'voice' and p.notes}
                    fam = {orch.ROLE_TRAITS.get(r, {}).get('family') or r[:4] for r in roles}
                    self.assertGreaterEqual(len(roles), 3, roles)
                    self.assertGreaterEqual(len(fam), 2, roles)


class Windows(unittest.TestCase):
    def test_a_role_enters_inside_the_block(self):
        sc = orc.OrchScore('t', 'C major', 4, 120)
        b = sc.block('A', 0.0, 32.0, [(4.0 * i, 4.0, 'C') for i in range(8)], 'C major', marks=[(0, 'mf')])
        b.add(orc.Line('melody', [(float(k), 1.0, 76) for k in range(32)]))
        b.texture, b.meta = 'drive_strings', {'lead': 'violins1'}
        slot = orc.needs('drive_strings')['melody'][0]
        win = orc._window(lambda blk, k, w: max(w, key=lambda x: (w[x], x)), b, slot, 'flutes', 4)
        self.assertEqual(win, (16.0, 32.0))                       # {0.5: 1.0, 0.0: 0.4}: from the middle
        self.assertIsNone(orc._window(lambda *a: None, b, slot, 'violins1', 4))   # no enter: the whole block
        self.assertTrue(set(orc.SYMPHONIC) <= set(orc.TEXTURES))


@unittest.skipUnless(SSO, 'sso not installed')
class SymphonicGenre(unittest.TestCase):
    SEEDS = (1, 5, 7)

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-symphonic').validate()
        cls.made = {sd: (t, endless.song(t)) for sd in cls.SEEDS for t in [endless.compose(cls.g, sd)]}

    def test_pieces_in_range_with_a_living_motto(self):
        for sd, (t, s) in self.made.items():
            o = s.orchestration
            info = s.orch_scores[0].band.info
            self.assertEqual(o.folded, 0, sd)
            for p in o.parts:
                lo, hi = (orc._n(v) for v in info['range'][p.role])
                self.assertTrue(all(lo <= n[2] <= hi for n in p.notes), (sd, p.role, p.block))
            m = symphony.symphony_metrics(s)
            self.assertGreaterEqual(m['motto'], 16, sd)
            # (round o9: a river piece's episode is its own tune varied - symphony.EPISODE_FROM - not the motto's
            # sentence: seed 5's river works the motto in 3 transforms)
            self.assertGreaterEqual(m['motto_tf'], 3 if t.feel == 'river' else 5, sd)
            self.assertGreaterEqual(m['motto_roles'], 4, sd)
            # (round o6: seed 7 draws a mysterious through-composed andante with a quiet climax - 2.45; round o8: 2.14,
            # the quiet climax is the first theme reharmonised and the build / climax longer - symphony.PROPORTION)
            self.assertGreater(m['nps'], 2.0, sd)
            # (round o5: seed 7 drew a mysterious andante - 1.3; seeds 1-16 mean 2.04, master 2.13, both min 1.27)
            self.assertGreater(m['roles_sd'], 1.2, sd)
            if self.g.feels[t.feel]['family'] == 'compound':
                self.assertEqual(tuple(s.time_sig), tuple(self.g.feels[t.feel]['time_sig']), sd)
            sc = composer.score(s, t, self.g)
            # (round o12: dev_own is a hard gate for the best-of-N draw - seed 5's river variations work their own
            # tune varied, 0.39 - so a single draw is judged on its weighted mean, the gate alone may cap it)
            self.assertGreater(sc['mean'], 60, sd)
            self.assertLessEqual(set(sc['hard']), {'dev_own'}, sd)

    def test_the_orchestration_pass(self):
        # (round o4, o3's orchestrators: timpani on the tonic / dominant in their octave, the flute's top A6, violas
        # under the violins)
        for sd, (t, s) in self.made.items():
            blocks = {b.name: b for b in s.orch_score.blocks}
            kh = Key(t.key).tonic
            vio = [n for p in s.orchestration.parts if p.role in ('violins1', 'violins2') for n in p.notes]
            over = total = 0
            for p in s.orchestration.parts:
                if p.role == 'timpani':
                    kb = Key(blocks[p.block].key).tonic
                    ok = {kh % 12, (kh + 7) % 12, kb % 12, (kb + 7) % 12}
                    self.assertTrue(all(q % 12 in ok and 38 <= q <= 55 for _, _, q in p.notes), (sd, p.block))
                elif p.role == 'flutes':
                    self.assertTrue(all(q <= 93 for _, _, q in p.notes), (sd, p.block))
                elif p.role == 'violas':
                    for a, _, q in p.notes:
                        on = [y for x, d, y in vio if x - 1e-6 <= a < x + d - 1e-6]
                        total += 1
                        over += bool(on) and q > max(on)
            self.assertLessEqual(over, 0.05 * max(1, total), sd)

    def test_the_climax_is_the_peak_block(self):
        for sd, (t, s) in self.made.items():
            peaks = [b for b in s.orch_score.blocks if b.peak]
            self.assertEqual(len(peaks), 1, sd)
            self.assertTrue(orc.TEXTURES[peaks[0].texture].get('peak') or peaks[0].texture in orc.SYMPHONIC, sd)

    def test_repair_meter_text_and_fermata_spans(self):
        # (round o2's infrastructure: the sustaining sections repair their samples' glitches, a 6/8 prints as 6/8,
        # the opening call's fermatas are given their spans)
        for sd, (t, s) in self.made.items():
            s.compile()
            info = s.orch_scores[0].band.info
            for role, kind in info['kind'].items():
                rep = s.tracks[role].instrument.params.get('repair')
                self.assertEqual(rep, 9.0 if kind == 'sustain' else None, (sd, role))
            ts = tuple(self.g.feels[t.feel]['time_sig'])
            self.assertEqual(t.meter_text, f"{ts[0]}/{ts[1]}", sd)

    def test_slow_introduction_fermatas_and_repair(self):
        # (round o2: the slow introduction's fermata before the call's two - their spans read from the notes placed
        # so far overlapped; every span is given now) and the sustaining sections repair their samples' glitches
        t = endless.compose(self.g, 777, 'stormy', plan={'feel': 'allegro', 'key': 'A minor', 'tempo': 120,
                                                         'slow': 1, 'intro': 'call'})
        s = endless.song(t)
        s.compile()
        info = s.orch_scores[0].band.info
        for role, kind in info['kind'].items():
            rep = s.tracks[role].instrument.params.get('repair')
            self.assertEqual(rep, 9.0 if kind == 'sustain' else None, role)

    def test_deterministic_and_the_record_replays(self):
        sd, (t, s) = next(iter(self.made.items()))
        arr = s.endless_arrangement
        self.assertEqual(arr.kind, 'symphony')
        s2 = endless.song(t, arrangement=arr)
        for name, tr in s.tracks.items():
            self.assertEqual([tuple(n) for n in tr.notes], [tuple(n) for n in s2.tracks[name].notes], name)



class TechO23(unittest.TestCase):
    """Round o23: the playing techniques (symphony.TECH, genres.symphony_tech) - the palette's data, the ranking's set
    memory, the switch restoring the band, and with SSO a piece whose techniques reach its parts."""

    def test_palette_and_ranking(self):
        known = set(symphony.KINDS) | {'peak', 'pre_peak'}
        for name, x in symphony.TECHNIQUES.items():
            self.assertTrue(x['fn'], name)
            self.assertTrue(x['kinds'] is None or set(x['kinds']) <= known, name)
        r1 = symphony.tech_rank('allegro', random.Random(1))
        self.assertEqual(r1, symphony.tech_rank('allegro', random.Random(1)))
        self.assertEqual(sorted(r1), sorted(n for n, x in symphony.TECHNIQUES.items()
                                            if x['feels'].get('allegro', 1.0) > 0))
        self.assertNotIn('col_legno', symphony.tech_rank('andante', random.Random(2)))
        # (the set's memory: the slot before's featured techniques come back less often at the top)
        feat = symphony.TECH_ON['feature']
        back = sum(len(set(symphony.tech_rank('allegro', random.Random(k), [r1])[:feat]) & set(r1[:feat]))
                   for k in range(200)) / 200
        fresh = sum(len(set(symphony.tech_rank('allegro', random.Random(k))[:feat]) & set(r1[:feat]))
                    for k in range(200)) / 200
        self.assertLess(back, fresh - 0.5)

    def test_switch_restores_the_band(self):
        from agentsound.endless import genres
        self.assertNotIn('muted', orch.role_table('film_orchestra')['horns']['arts'])
        try:
            genres.symphony_tech(True)
            if orch.installed('vsco2-ce'):          # (the mutes are VSCO 2 CE programs)
                self.assertIn('muted', orch.role_table('film_orchestra')['horns']['arts'])
            self.assertTrue(genres.ORCHESTRA_SYMPHONIC.plan.get('set_tech'))
        finally:
            genres.symphony_tech(False)
        self.assertNotIn('muted', orch.role_table('film_orchestra')['horns']['arts'])
        self.assertIsNone(symphony.TECH)
        self.assertNotIn('set_tech', genres.ORCHESTRA_SYMPHONIC.plan)

    @unittest.skipUnless(SSO and orch.installed('vsco2-ce'), 'SSO / VSCO 2 CE not installed')
    def test_a_piece_plays_its_techniques(self):
        from agentsound.endless import genres
        try:
            genres.symphony_setplan(True)
            genres.symphony_tech(True)
            g = genres.get('orchestra-symphonic').validate()
            plan = composer.set_plan(g, 3, 143000)
            self.assertTrue(all(len(x['tech']) >= symphony.TECH_ON['feature'] for x in plan))
            t = endless.compose(g, 143010, plan=plan[1])
            s = endless.song(t)
            self.assertTrue(s.tech_events)
            self.assertLessEqual(len(s.tech_plan['done']), symphony.TECH_ON['feature'])
            arts = s.orch_scores[0].band.info['articulations']
            st = symphony.tech_stats(s)
            for role, c in st['counts'].items():
                for a in c:
                    self.assertTrue(a in ('hit', 'marcato') or a in (arts.get(role) or ()) or
                                    a in orch.FALLBACK, (role, a))
            for p in s.orchestration.parts:
                if p.art == 'muted':
                    lo, hi = orch.MUTES[p.role]['range']
                    self.assertTrue(all(lo <= q <= hi for _, _, q in p.notes), p.role)
        finally:
            genres.symphony_tech(False)
            genres.symphony_setplan(False)


class MacroO24(unittest.TestCase):
    """Round o24: the macro shapes (symphony.MACRO, genres.symphony_shape) and TECH v2 - the set's memory over the whole
    set, the switch restoring master, the shapes realised on the layout's rows."""

    def setUp(self):
        from agentsound.endless import genres
        genres.symphony_setplan(True)
        genres.symphony_tech(True)
        genres.symphony_shape(True)
        self.g = genres.get('orchestra-symphonic').validate()

    def tearDown(self):
        from agentsound.endless import genres
        genres.symphony_shape(False)
        genres.symphony_tech(False)
        genres.symphony_setplan(False)

    def test_switch_restores_master(self):
        from agentsound.endless import genres
        genres.symphony_shape(False)
        self.assertIsNone(symphony.MACRO)
        self.assertNotIn('v2', symphony.TECH)
        self.assertEqual(symphony.TECH['feature'], symphony.TECH_ON['feature'])
        self.assertNotIn('set_macro', genres.ORCHESTRA_SYMPHONIC.plan)
        plan = composer.set_plan(self.g, 4, 151000)
        self.assertFalse(any('shape' in x or 'tech2' in x for x in plan))

    def test_set_memory(self):
        plan = composer.set_plan(self.g, 8, 153000)
        sh = [x['shape'] for x in plan]
        for d in ('open', 'arc', 'end', 'climax'):
            self.assertFalse(any(a[d] == b[d] for a, b in zip(sh, sh[1:])), d)
            self.assertLessEqual(max(sum(1 for x in sh if x[d] == v) for v in {x[d] for x in sh}), 3, d)
        feat = symphony.TECH['feature']
        cnt = {}
        for x in plan:
            for t in x['tech2'][:feat]:
                cnt[t] = cnt.get(t, 0) + 1
        self.assertLessEqual(max(cnt.values()), 3)
        pz = [j for j, x in enumerate(plan) if 'pizz_choir' in x['tech2'][:feat] or x['shape']['open'] == 'dance']
        self.assertTrue(all(b - a > symphony.TECH_V2['pizz_gap'] for a, b in zip(pz, pz[1:])), pz)
        crowned = [x for x in plan if x['tech_crown'] and 'trill' in x['tech2'][:feat]]
        self.assertLessEqual(len(crowned), 1)

    def test_shapes_on_the_rows(self):
        slot = composer.set_plan(self.g, 1, 151000)[0]
        F = self.g.feels[slot['feel']]
        lay = symphony._layout_of(self.g, F, slot, symphony._form_seed(slot, slot['key'], 0))
        rows0 = symphony._rows(self.g, lay)
        med = symphony._macro_rows(self.g, rows0, {'open': 'medias', 'arc': 'classic', 'end': 'cut'})
        self.assertNotIn(med[0][1], ('intro', 'source'))
        self.assertNotIn('coda', [r[1] for r in med])
        if med[0][1] in ('t1', 'river'):
            self.assertEqual(med[0][3].get('sh'), 'medias')
        late = symphony._macro_rows(self.g, rows0, {'open': 'soft', 'arc': 'late', 'end': 'loud'})
        pi = symphony._peak_index(self.g, late)
        self.assertNotIn('recap2', [r[1] for r in late[pi + 1:]])

    def test_a_piece_composes(self):
        plan = composer.set_plan(self.g, 3, 153000)
        for j, slot in enumerate(plan):
            t = composer.compose(self.g, 153000 + 10 * j, plan=slot)
            self.assertEqual(t.arrange['shape'], slot['shape'])
            self.assertEqual(t.arrange['tech'], slot['tech2'])
            mat = t.symphony
            if slot['shape']['open'] in ('medias', 'dance'):
                self.assertNotIn(mat['blocks'][0]['kind'], ('intro', 'source', 'slow'))
            if slot['shape']['end'] == 'cut':
                self.assertNotIn('coda', [b['kind'] for b in mat['blocks']])


class ChoirOC1(unittest.TestCase):
    """Round oc1: the choir (endless.choir, genres.symphony_choir) - the plan draw's set memory, the switch, and with
    the vocalset-choir pack a piece whose a cappella and summit are sung in range, the orchestra thinned, the credits
    naming VocalSet."""

    def test_the_draw_and_its_memory(self):
        from agentsound.endless import choir as CH
        self.assertEqual(CH.choir_draw('allegro', random.Random(3)), CH.choir_draw('allegro', random.Random(3)))
        for name, x in CH.PLANS.items():
            self.assertTrue(set(x['events']) <= set(CH.EVENTS), name)
        hist, seen = [], []
        for k in range(400):
            hist.append(CH.choir_draw(('allegro', 'andante', 'scherzo', 'river', 'vivace')[k % 5],
                                      random.Random(k), hist[-2:]))
        for a, b in zip(hist, hist[1:]):
            self.assertFalse(a == b == 'none')
            seen.append(a == b)
        none = hist.count('none') / len(hist)
        self.assertTrue(0.15 < none < 0.4, none)             # (the choir in 60-85 % of the pieces)
        self.assertLess(sum(seen) / len(seen), 0.06)          # (rarely the slot before's plan again)

    def test_switch(self):
        from agentsound.endless import choir as CH, genres
        try:
            genres.symphony_choir(True)
            self.assertEqual(CH.CHOIR, CH.CHOIR_ON)
            self.assertTrue(genres.ORCHESTRA_SYMPHONIC.plan.get('set_choir'))
        finally:
            genres.symphony_choir(False)
        self.assertIsNone(CH.CHOIR)
        self.assertNotIn('set_choir', genres.ORCHESTRA_SYMPHONIC.plan)

    @unittest.skipUnless(SSO and orch.installed('vocalset-choir'), 'SSO / vocalset-choir not installed')
    def test_a_piece_sings(self):
        from agentsound import delivery
        from agentsound.endless import choir as CH, genres
        from agentsound.theory import note
        try:
            genres.symphony_choir(True)
            g = genres.get('orchestra-symphonic').validate()
            plan = composer.set_plan(g, 3, 155000)
            self.assertTrue(all(x.get('choir') in CH.PLANS for x in plan))
            self.assertEqual(plan[0]['choir'], 'acappella')
            t = endless.compose(g, 155000, plan=plan[0])
            self.assertEqual(t.arrange['choir'], 'acappella')
            s = endless.song(t)
            st = CH.choir_stats(s)
            self.assertEqual([e['event'] for e in st['events']], ['acappella', 'summit'])
            self.assertEqual(st['parts'], ['A', 'B', 'S', 'T'])
            acap = st['events'][0]
            self.assertGreater(acap['thinned'], 0)
            self.assertIn('ah', acap['vowels'])
            for p in s.orchestration.parts:                  # (the a cappella: only the bass line under the choir)
                if any(acap['start'] + 1e-6 <= n[0] < acap['end'] - 1e-6 for n in p.notes):
                    self.assertIn(p.role, ('basses', 'cellos'), p)
            render = s.compile()
            sung = 0
            for tr in render['tracks']:
                if tr['id'].startswith('choir_'):
                    lo, hi = (note(x) for x in orch.VOCALSET_PARTS[tr['id'].split('_')[1].upper()])
                    ps = [n[2] for n in tr.get('notes', [])]
                    sung += len(ps)
                    self.assertTrue(all(lo <= q <= hi for q in ps), tr['id'])
            self.assertGreater(sung, 40)
            cr = delivery.collect_credits(render)
            self.assertIn('vocalset-choir', [x['id'] for x in cr['sources']])
            self.assertTrue(any('VocalSet' in a for a in cr['attributions']))
        finally:
            genres.symphony_choir(False)


class ChoirOC2(unittest.TestCase):
    """Round oc2: CHOIR v2 (genres.symphony_choir(True, v2=True)) - the gestures' memory over a set of 8, the a
    cappella more often, the summit singing the theme (in octaves: the tenors an octave under the sopranos) with the
    brass / woodwind doublings softer under it."""

    def test_the_gesture_memory(self):
        from agentsound.endless import choir as CH, genres
        try:
            genres.symphony_choir(True, v2=True)
            self.assertTrue(CH.CHOIR['v2'])
            self.assertIs(CH.plans(), CH.PLANS_V2)
            for name, x in CH.PLANS_V2.items():
                self.assertTrue(set(x['events']) <= set(CH.EVENTS), name)
            hist = []
            for k in range(400):
                hist.append(CH.choir_draw(('allegro', 'andante', 'scherzo', 'river', 'vivace')[k % 5],
                                          random.Random(k), hist))
            W = CH.CHOIR['window']
            for i in range(len(hist)):           # (no gesture more often than its cap in any 8 slots)
                win = hist[max(0, i - W):i + 1]
                for e, cap in CH.CHOIR['caps'].items():
                    self.assertLessEqual(sum(e in CH.PLANS_V2[h]['events'] for h in win), cap, (i, e, win))
            for a, b in zip(hist, hist[1:]):
                self.assertFalse(a == b == 'none')
            none = hist.count('none') / len(hist)
            acap = sum('acappella' in CH.PLANS_V2[h]['events'] for h in hist) / len(hist)
            self.assertTrue(0.2 < none < 0.42, none)              # (the choir in 60-75 % of the pieces)
            self.assertGreater(acap, 0.15)
        finally:
            genres.symphony_choir(False)
        self.assertIs(CH.plans(), CH.PLANS)

    @unittest.skipUnless(SSO and orch.installed('vocalset-choir'), 'SSO / vocalset-choir not installed')
    def test_the_summit_sings_the_theme(self):
        from agentsound.endless import choir as CH, genres
        try:
            genres.symphony_setplan(True)        # (the round's defaults: the slot is the round's slot 13)
            genres.symphony_tech(True)
            genres.symphony_choir(True, v2=True)
            CH.CHOIR['tex'] = {'unison': 1.0}
            g = genres.get('orchestra-symphonic').validate()
            plan = composer.set_plan(g, 16, 161000)
            self.assertEqual(plan[12]['choir'], 'summit')
            s = endless.song(endless.compose(g, 161120, plan=plan[12]))
            ev = CH.choir_stats(s)['events'][0]
            self.assertEqual((ev['event'], ev['tex']), ('summit', 'unison'))
            self.assertTrue(ev['line'].endswith(':melody'), ev)
            self.assertGreater(ev['softened'], 0)
            render = s.compile()
            notes = {tr['id']: [(round(n[0], 2), n[2]) for n in tr.get('notes', [])]
                     for tr in render['tracks'] if tr['id'].startswith('choir_')}
            sop, ten = dict(notes['choir_s_ah']), dict(notes['choir_t_ah'])
            both = [t for t in sop if t in ten]
            self.assertGreater(len(both), 10)
            self.assertGreater(sum(sop[t] - ten[t] == 12 for t in both) / len(both), 0.8)
        finally:
            genres.symphony_choir(False)
            genres.symphony_setplan(False)
            genres.symphony_tech(False)



class Shape2O24b(unittest.TestCase):
    """Round o24b: TECH2 alone (genres.symphony_tech2) and SHAPE2 (genres.symphony_shape2, symphony.MACRO2_ON) - the
    switches restoring master, the climax's material moved for the early / mid arcs, the cut on the climax, the set's
    memory on the motto / t1 texture / bass figures."""

    def setUp(self):
        from agentsound.endless import genres
        genres.symphony_setplan(True)
        genres.symphony_tech(True)
        genres.symphony_tech2(True)
        genres.symphony_shape2(True)
        self.g = genres.get('orchestra-symphonic').validate()

    def tearDown(self):
        from agentsound.endless import genres
        genres.symphony_shape2(False)
        genres.symphony_tech2(False)
        genres.symphony_tech(False)
        genres.symphony_setplan(False)

    def test_switches_restore_master(self):
        from agentsound.endless import genres
        genres.symphony_shape2(False)
        genres.symphony_tech2(False)
        self.assertIsNone(symphony.MACRO)
        self.assertNotIn('v2', symphony.TECH)
        self.assertEqual(symphony.TECH['feature'], symphony.TECH_ON['feature'])
        self.assertNotIn('set_macro', genres.ORCHESTRA_SYMPHONIC.plan)
        self.assertNotIn('set_tech2', genres.ORCHESTRA_SYMPHONIC.plan)

    def test_tech2_alone(self):
        from agentsound.endless import genres
        genres.symphony_shape2(False)
        plan = composer.set_plan(self.g, 3, 157000)
        self.assertFalse(any('shape' in x for x in plan))
        self.assertTrue(all(len(x['tech2']) >= symphony.TECH['feature'] for x in plan))
        t = composer.compose(self.g, 157000, plan=plan[0])
        self.assertEqual(t.arrange['tech'], plan[0]['tech2'])

    def test_early_arc_moves_the_material(self):
        for lay in ('sonata', 'rondo', 'arch'):
            rows0 = symphony._rows(self.g, lay)
            p0 = symphony._peak_pos(self.g, rows0)
            rows = symphony._macro_rows(self.g, rows0, {'open': 'soft', 'arc': 'early', 'end': 'dying', 'at': 0.52})
            pi = symphony._peak_index(self.g, rows)
            after = [r for r in rows[pi + 1:] if r[3].get('sh') == 'after']
            self.assertTrue(after, lay)
            self.assertLess(symphony._peak_pos(self.g, rows), p0, lay)
            self.assertTrue(all(r[1] in symphony.MACRO2_V2['move'] for r in after), lay)
        cut = symphony._macro_rows(self.g, symphony._rows(self.g, 'sonata'),
                                   {'open': 'soft', 'arc': 'classic', 'end': 'cut', 'at': 0.78})
        pi = symphony._peak_index(self.g, cut)
        self.assertEqual([r[1] for r in cut[pi + 1:]], ['end'])

    def test_set_memory_extras(self):
        plan = composer.set_plan(self.g, 4, 157000)
        figs = [tuple(x['shape']['bass_figs']) for x in plan]
        self.assertTrue(all(len(f) == symphony.MACRO2_V2['bass_n'] for f in figs))
        self.assertFalse(any(a == b for a, b in zip(figs, figs[1:])), figs)
        fams = {}
        for x in plan:
            fam = self.g.feels[x['feel']]['family']
            cell = (x['shape'].get('motto') or x['motto'])[fam]
            fams.setdefault(fam, []).append(symphony.MOTTO_FAMILIES[fam][cell])
        for fam, fs in fams.items():
            self.assertEqual(len(fs), len(set(fs)), (fam, fs))
        for j, slot in enumerate(plan[:2]):
            t = composer.compose(self.g, 157000 + 10 * j, plan=slot)
            if isinstance(slot['shape'].get('motto'), dict):
                self.assertEqual(t.arrange['motto'], slot['shape']['motto'])


class Shape3O25(unittest.TestCase):
    """Round o25: SHAPE3 (genres.symphony_shape3, symphony.MACRO3_ON) - the switch restoring master, the aftermath after
    a moved climax a second build with a rising return, the shorter way into the late / cut climax, the chorale /
    cut textures."""

    def setUp(self):
        from agentsound.endless import genres
        genres.symphony_setplan(True)
        genres.symphony_tech(True)
        genres.symphony_tech2(True)
        genres.symphony_shape3(True)
        self.g = genres.get('orchestra-symphonic').validate()

    def tearDown(self):
        from agentsound.endless import genres
        genres.symphony_shape3(False)
        genres.symphony_tech2(False)
        genres.symphony_tech(False)
        genres.symphony_setplan(False)

    def test_switch_restores_master(self):
        from agentsound.endless import genres
        self.assertTrue(symphony.MACRO['v2'].get('v3'))
        genres.symphony_shape3(False)
        self.assertIsNone(symphony.MACRO)
        self.assertNotIn('set_macro', genres.ORCHESTRA_SYMPHONIC.plan)

    def test_aftermath_builds_and_rises(self):
        V = symphony.MACRO3_V2
        for lay in ('sonata', 'arch'):
            sh = {'open': 'soft', 'arc': 'early', 'end': 'dying', 'at': 0.52}
            rows = symphony._macro_marks(self.g, symphony._macro_rows(self.g, symphony._rows(self.g, lay), sh), sh)
            pi = symphony._peak_index(self.g, rows)
            run = []
            for r in rows[pi + 1:]:
                if r[3].get('sh') != 'after' and r[1] not in V['move']:
                    break
                run.append(r)
            self.assertTrue(run, lay)
            self.assertEqual(run[-1][3]['sh_dyn'][-1][1], 'f', lay)        # (the second build ends at f)
            self.assertIn('mp', [m[1] for r in run for m in r[3]['sh_dyn']], lay)   # (after a release)
            nxt = rows[pi + 1 + len(run)]
            if nxt[1] in V['rise']['kinds']:
                self.assertEqual(nxt[3].get('sh'), 'rise', lay)

    def test_shorter_runup(self):
        for sh in ({'open': 'motto', 'arc': 'late', 'end': 'loud', 'at': 0.88},
                   {'open': 'motto', 'arc': 'classic', 'end': 'cut', 'at': 0.78}):
            rows = symphony._macro_rows(self.g, symphony._rows(self.g, 'sonata'), sh)
            self.assertNotIn('recap2', [r[1] for r in rows], sh)
            self.assertTrue(all(r[2] <= symphony.MACRO3_V2['runup']['retrans'] for r in rows if r[1] == 'retrans'))

    def test_textures(self):
        from agentsound.bandlib import orchestration as O
        for t in ('apex_chorale3', 'hammer_motto'):
            self.assertIn(t, O.SYMPHONIC)
        self.assertEqual(O.TEXTURES['apex_chorale3']['ostinato']['figure'], 'motto')
        self.assertEqual(O.TEXTURES['apex_chorale3']['bass']['figure'], 'walk')
        self.assertEqual(symphony.MACRO3_V2['climax_tex']['chorale'], {'tex': {'apex_chorale3': 1.0}})
        self.assertEqual(symphony.MACRO3_V2['cut']['tex'], {'hammer_motto': 1.0})


if __name__ == '__main__':
    unittest.main()
