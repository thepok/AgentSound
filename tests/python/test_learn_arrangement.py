"""The players' arrangement record (endless.arrangement) and its Arr token block (learn.tokens schema 2): tune +
arrangement -> tokens -> decode -> perform plays the same notes, the record is what the players play (a changed
record changes the piece, through the tokens too), the old schema still decodes, the decoder is strict. No torch."""
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.endless import perform  # noqa: E402
from agentsound.learn import grammar  # noqa: E402
from agentsound.learn import tokens as T  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402

GENRES = ('new-age-piano', 'classical-piano', 'lofi-piano', 'jazz-piano', 'jazz-trio', 'new-age-epiano')


def notes(song) -> dict:
    return {k: [(n.start, n.dur, n.pitch, n.vel) for n in tr._notes] for k, tr in song.tracks.items()}


def composed(g, seeds):
    G = endless.genre(g)
    for s in seeds:
        try:
            yield G, endless.compose(G, s)
        except ComposeError:
            continue


class RoundTrip(unittest.TestCase):
    def test_seeds_100_149_round_trip_and_play_the_same_notes(self):
        for g in GENRES:
            n = 0
            for G, tune in composed(g, range(100, 150)):
                arr = perform.arrange(tune, G)
                toks = T.encode(tune, arr)
                self.assertIsNone(grammar.check(toks), (g, tune.seed))
                back = T.decode(toks, G, seed=tune.seed, title=tune.title)
                self.assertTrue(T.same_arrangement(back.arrangement, arr), (g, tune.seed))
                self.assertEqual(T.diff(tune, back), [], (g, tune.seed))
                self.assertEqual(T.encode(back, back.arrangement), toks, (g, tune.seed))
                song = endless.song(tune)
                self.assertTrue(T.same_arrangement(song.endless_arrangement, arr), (g, tune.seed))
                self.assertEqual(notes(song), notes(endless.song(back)), (g, tune.seed))
                n += 1
            self.assertGreater(n, 40, g)

    def test_the_record_is_what_the_players_play(self):
        G = endless.genre('new-age-piano')
        tune = endless.compose(G, 101)
        arr = perform.arrange(tune, G)
        mod = arr.copy()
        mod.sections['climax']['climax'] = 'step' if arr.sections['climax'].get('climax') != 'step' else 'lift'
        mod.sections.pop('inter', None)
        mod.sections['A1']['figures'] = 'chorus'                 # (a fixed key told otherwise: in the tokens too)
        # (round g9: seed 101's 'key' arrival draws the climax a step up - 'step' then plays as 'theme' did; the
        # A1 figures sit under its ostinato: B1's figures are told otherwise too)
        mod.sections['B1']['figures'] = 'calm' if arr.sections['B1'].get('figures') != 'calm' else 'chorus'
        base, told = notes(endless.song(tune)), notes(endless.song(tune, arrangement=mod))
        self.assertNotEqual(base, told)
        back = T.decode(T.encode(tune, mod), G, seed=tune.seed, title=tune.title)
        self.assertTrue(T.same_arrangement(back.arrangement, mod))
        self.assertEqual(notes(endless.song(back)), told)
        song = endless.song(back)
        self.assertNotIn('inter', [x.name for x in song.sections])

    def test_the_layout_the_waltz_bass_and_the_intro_are_told_too(self):
        from agentsound.endless.arrangement import MOVES, section_specs
        G = endless.genre('new-age-piano')
        tune = endless.compose(G, 101)                          # (a 3/4 waltz: its second bars carry drawn moves)
        arr = perform.arrange(tune, G)
        self.assertNotEqual(arr.piece['layout'], 'chorus')
        mod = arr.copy()
        mod.piece['layout'] = 'chorus'
        keep = section_specs(G, 'chorus')
        for k in [k for k in mod.sections if k not in keep]:
            mod.sections.pop(k)
        mv = mod.sections['A1']['moves']
        mod.sections['A1']['moves'] = [MOVES[(MOVES.index(m) + 1) % 3] for m in mv]
        told = notes(endless.song(tune, arrangement=mod))
        self.assertNotEqual(notes(endless.song(tune)), told)
        toks = T.encode(tune, mod)
        self.assertIn('ALayout_chorus', toks)
        back = T.decode(toks, G, seed=tune.seed, title=tune.title)
        self.assertTrue(T.same_arrangement(back.arrangement, mod))
        song = endless.song(back)
        self.assertEqual(notes(song), told)
        self.assertNotIn('inter', [x.name for x in song.sections])
        self.assertEqual(song.endless_arrangement.sections['A1']['moves'], mod.sections['A1']['moves'])

    def test_a_jazz_record_is_played_too(self):
        G = endless.genre('jazz-piano')
        for tune in (t for _, t in composed('jazz-piano', range(100, 120))):
            arr = perform.arrange(tune, G)
            heads = [k for k, d in arr.sections.items() if k.startswith('head:') and 'lh' in d]
            if heads:
                break
        mod = arr.copy()
        mod.sections[heads[0]]['lh'] = 'stride' if arr.sections[heads[0]]['lh'] != 'stride' else 'shell'
        mod.sections['solo']['quotes'] = 0 if arr.sections['solo']['quotes'] else 1
        told = notes(endless.song(tune, arrangement=mod))
        self.assertNotEqual(notes(endless.song(tune)), told)
        back = T.decode(T.encode(tune, mod), G, seed=tune.seed, title=tune.title)
        self.assertEqual(notes(endless.song(back)), told)


class Schema(unittest.TestCase):
    def test_the_old_schema_still_decodes(self):
        G = endless.genre('lofi-piano')
        tune = endless.compose(G, 3)
        old = T.encode(tune)
        self.assertEqual(T.schema_of(old), 1)
        self.assertNotIn('Arr', old)
        self.assertIsNone(grammar.check(old))
        self.assertIsNone(T.decode(old, G, seed=3).arrangement)
        new = T.encode(tune, perform.arrange(tune, G))
        self.assertEqual(T.schema_of(new), 2)
        a, z = new.index('Arr'), new.index('EndArr')
        self.assertEqual(new[:a] + new[z + 1:], old)             # (the block between the plan and the harmony)
        none = T.encode(tune, None, schema=2)
        self.assertIn('Arr_none', none)
        self.assertIsNone(grammar.check(none))
        self.assertIsNone(T.decode(none, G, seed=3).arrangement)
        self.assertIsNotNone(grammar.check(new[:a] + new[a + 1:]))   # (a block without its head)

    def test_the_vocabulary_holds_every_arrangement_value(self):
        from agentsound.learn.data import GENRE_NAMES, Vocab
        allowed = T.arrangement_tokens(GENRE_NAMES)
        for g in GENRE_NAMES:
            for G, tune in composed(g, range(200, 206)):
                toks = T.encode(tune, perform.arrange(tune, G))
                a, z = toks.index('Arr'), toks.index('EndArr')
                self.assertLessEqual(set(toks[a:z + 1]), allowed, (g, tune.seed))
        G = endless.genre('lofi-piano')
        toks = T.encode(endless.compose(G, 3), perform.arrange(endless.compose(G, 3), G))
        self.assertLessEqual(allowed, set(Vocab.build([toks], arrangement=True).itos))
        self.assertNotIn('ALayout_chorus', Vocab.build([T.encode(endless.compose(G, 3))], arrangement=True).itos)

    def test_the_decoder_is_strict(self):
        G = endless.genre('new-age-piano')
        tune = endless.compose(G, 2)
        toks = T.encode(tune, perform.arrange(tune, G))
        i = toks.index('ASec_A1')
        for bad in (toks[:i] + ['ASec_nowhere'] + toks[i + 1:],             # no such section
                    toks[:i + 1] + ['AClimax_upside'] + toks[i + 1:],         # no such value
                    toks[:i + 1] + ['AFill_1', 'ADyn_p'] + toks[i + 1:],      # out of order
                    toks[:i] + ['ASec_A1'] + toks[i:]):                       # twice
            with self.assertRaises(T.TokenError):
                T.decode(bad, G)
        O = endless.genre('organ')                                             # an organ takes no arrangement
        org = T.encode(endless.compose(O, 1), None, schema=2)
        i = org.index('Arr_none')
        self.assertIsNone(T.decode(org, O).arrangement)
        with self.assertRaises(T.TokenError):
            T.decode(org[:i] + ['Arr', 'EndArr'] + org[i + 1:], O)


if __name__ == '__main__':
    unittest.main()
