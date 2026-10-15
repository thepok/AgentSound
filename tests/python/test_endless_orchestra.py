"""The endless 'orchestra-film' genre (agentsound/endless/orchestra.py, bandlib/orchestration.py): the score
representation and the orchestrator on a stand-in score (no samples), and - with the SSO pack installed - whole
pieces: every note in its role's range, the rules (one tutti at the peak, a light coda, colour changes), the
orchestration metrics and score, determinism, the arrangement record replayed and round-tripped through the learn
tokens (kind 'orchestra'). Notes only, no audio."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import endless  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.bandlib import orchestration as orc  # noqa: E402
from agentsound.endless import composer, perform  # noqa: E402
from agentsound.learn import grammar  # noqa: E402
from agentsound.learn import tokens as T  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

note_number = orc._n

SSO = orch.installed('sso')


def _stand_in(n_blocks=4):
    """A small OrchScore: per block a melody, a bass and a 3-voice harmony over C - F - G - C."""
    sc = orc.OrchScore('test', 'C major', 4, 90)
    chart = [(0, 4, 'C'), (4, 4, 'F'), (8, 4, 'G'), (12, 4, 'C')]
    for i in range(n_blocks):
        st = i * 16.0
        b = sc.block(f"S{i}", st, 16.0, [(st + a, d, s) for a, d, s in chart], 'C major', marks=[(st, 'mp')],
                     peak=(i == n_blocks - 2))
        b.add(orc.Line('melody', [(st + k, 1.0, 72 + (k % 5)) for k in range(16)]))
        b.add(orc.Line('bass', [(st + a, d, p) for (a, d, _), p in zip(chart, (36, 41, 43, 36))]))
        for v, base in (('h1', 64), ('h2', 60), ('h3', 55)):
            b.add(orc.Line('harmony', [(st + a, d, base) for a, d, _ in chart], voice=v))
    return sc


def _pick(block, key, choices):
    """A deterministic pick: the first choice with the largest weight."""
    w = dict(choices)
    return max(w, key=lambda k: (w[k], -list(w).index(k)))


class Orchestrator(unittest.TestCase):
    def test_every_function_is_known_and_every_texture_uses_known_slots(self):
        for name, tex in orc.TEXTURES.items():
            for fn in orc.needs(name):
                self.assertIn(fn, orc.FUNCTIONS, name)
        for role in orch.role_table('film_orchestra'):
            self.assertIn(role, orch.ROLE_TRAITS, role)

    def test_plan_and_orchestrate_a_stand_in_score(self):
        sc = _stand_in()
        table = orch.role_table('film_orchestra')
        roles = [r for r in table if r not in ('drums', 'low_brass')]
        orc.plan_blocks(sc, {}, roles, _pick)
        self.assertTrue(all(b.texture in orc.TEXTURES for b in sc.blocks))
        self.assertTrue(orc.TEXTURES[sc.blocks[-1].texture].get('light'))          # the last block: light
        tutti = [b for b in sc.blocks if orc.TEXTURES[b.texture].get('peak')]
        self.assertLessEqual(len(tutti), orc.RULES['tutti_blocks'])
        self.assertTrue(all(b.peak for b in tutti))
        o = orc.orchestrate(sc, {r: table[r] for r in roles}, _pick)
        self.assertTrue(o.parts)
        for p in o.parts:                                                          # every note in range
            lo, hi = (note_number(v) for v in table[p.role]['range'])
            self.assertTrue(all(lo <= n[2] <= hi for n in p.notes), (p.role, p.block))
        for b in sc.blocks:                                                        # a melody in every block
            self.assertTrue(any(p.function == 'melody' or p.line for p in o.by_block(b.name)), b.name)

    def test_brass_under_a_line_plays_softer(self):
        sc = _stand_in(2)
        table = orch.role_table('film_orchestra')
        sc.blocks[0].texture, sc.blocks[0].meta = 'solo_pad', {'lead': 'violins1'}
        sc.blocks[1].texture, sc.blocks[1].meta = 'harp_solo', {'lead': 'violins1', 'colour0': 'harp'}
        o = orc.orchestrate(sc, table, _pick)
        horns = [p for p in o.parts if p.role == 'horns' and p.function == 'harmony']
        self.assertTrue(horns)
        self.assertLess(horns[0].off, orc.FUNCTIONS['harmony']['off'] - 3.0)


@unittest.skipUnless(SSO, 'sso not installed')
class OrchestraGenre(unittest.TestCase):
    SEEDS = (101, 102, 104)

    @classmethod
    def setUpClass(cls):
        cls.g = endless.genre('orchestra-film').validate()
        cls.made = {}
        for sd in cls.SEEDS:
            try:
                t = endless.compose(cls.g, sd)
            except ComposeError:
                continue
            cls.made[sd] = (t, endless.song(t))

    def test_pieces_follow_the_rules(self):
        self.assertGreaterEqual(len(self.made), 2)
        for sd, (t, s) in self.made.items():
            o, sc = s.orchestration, s.orch_score
            self.assertEqual(o.folded, 0, sd)
            info = s.orch_scores[0].band.info
            for p in o.parts:
                lo, hi = (note_number(v) for v in info['range'][p.role])
                self.assertTrue(all(lo <= n[2] <= hi for n in p.notes), (sd, p.role, p.block))
            tex = [b.texture for b in sc.blocks]
            self.assertLessEqual(sum(bool(orc.TEXTURES[x].get('peak')) for x in tex), 1, sd)
            self.assertTrue(orc.TEXTURES[sc.blocks[-2].texture].get('light'), sd)      # the coda (before 'end')
            self.assertIn(s.orch_size, self.g.plan['sizes'], sd)
            self.assertLessEqual(set(o.roles()), set(self.g.plan['sizes'][s.orch_size]), sd)

    def test_metrics_and_score(self):
        for sd, (t, s) in self.made.items():
            m = composer.score_metrics(s, t, composer.score_style(s))
            for k in ('range_out', 'sweet_mel', 'mel_db', 'colour_chg', 'tutti', 'coda_thin', 'roles_bar',
                      'dbl_share', 'textures', 'climax_x', 'phrase_rests', 'climax_lift'):
                self.assertIn(k, m, (sd, k))
            self.assertEqual(m['range_out'], 0.0, sd)
            sc = composer.score(s, t, self.g)
            self.assertGreater(sc['score'], 60, sd)

    def test_deterministic_and_the_record_replays(self):
        sd, (t, s) = next(iter(self.made.items()))
        arr = s.endless_arrangement
        self.assertEqual(arr.kind, 'orchestra')
        self.assertIn('size', arr.piece)
        self.assertTrue(any('texture' in d for d in arr.sections.values()))
        s2 = endless.song(t, arrangement=arr)
        for name, tr in s.tracks.items():
            self.assertEqual([tuple(n) for n in tr.notes], [tuple(n) for n in s2.tracks[name].notes], name)
        # a told texture is played
        mod = arr.copy()
        name = next(k for k, d in mod.sections.items() if d.get('texture') and k != 'climax')
        mod.sections[name]['texture'] = 'chorale_winds' if arr.sections[name]['texture'] != 'chorale_winds' \
            else 'strings_pad'
        s3 = endless.song(t, arrangement=mod)
        self.assertEqual(next(b.texture for b in s3.orch_score.blocks if b.name == name),
                         mod.sections[name]['texture'])

    def test_learn_tokens_round_trip(self):
        for sd, (t, s) in self.made.items():
            arr = perform.arrange(t, self.g)
            self.assertTrue(T.same_arrangement(arr, s.endless_arrangement), sd)
            toks = T.encode(t, arr)
            self.assertIsNone(grammar.check(toks), sd)
            orch_toks = {x for x in toks if x.split('_')[0] in ('ATex', 'ALead', 'ACtr', 'ASize')}
            self.assertTrue(orch_toks and orch_toks <= T.arrangement_tokens([self.g]), sd)
            back = T.decode(toks, self.g, seed=t.seed, title=t.title)
            self.assertTrue(T.same_arrangement(back.arrangement, arr), sd)
            self.assertEqual(T.encode(back, back.arrangement), toks, sd)

    def test_the_orchestra_tokens_leave_the_piano_vocabulary_alone(self):
        piano = T.arrangement_tokens(['new-age-piano'])
        self.assertFalse({x for x in piano if x.split('_')[0] in ('ATex', 'ALead', 'ACtr', 'ASize')})
        orchv = T.arrangement_tokens(['orchestra-film'])
        self.assertTrue({'ATex_tutti', 'ALead_violins1', 'ACtr_none', 'ASize_full'} <= orchv)


if __name__ == '__main__':
    unittest.main()
