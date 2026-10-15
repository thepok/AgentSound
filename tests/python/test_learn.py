"""The learned generator (agentsound.learn): the token schema's round trip (tune -> tokens -> tune note-identical at
composition level, the players then play the same notes) and the decoder's strictness. No torch needed."""
import importlib.util
import pathlib
import sys
import unittest
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from agentsound import endless  # noqa: E402
from agentsound.endless.genres import GENRES  # noqa: E402
from agentsound.learn import tokens as T  # noqa: E402


class Spelling(unittest.TestCase):
    def test_roman_keeps_the_letter(self):
        self.assertEqual(T.roman('Cb', 'Bb'), 'bII')
        self.assertEqual(T.unroman('bII', 'Bb'), 'Cb')
        self.assertEqual(T.roman('F#', 'C'), '#IV')
        self.assertEqual(T.unroman('bbbVII', 'G#'), 'Fb')
        for tonic in ('C', 'Db', 'F#', 'G#', 'Cb', 'Bb'):
            for name in ('C', 'Eb', 'F#', 'Ab', 'B', 'Cb', 'E#'):
                self.assertEqual(T.unroman(T.roman(name, tonic), tonic), name)

    def test_chord_tokens(self):
        self.assertEqual(T.chord_tokens('Gadd9/B', 'G'), ['Root_I', 'Q_add9', 'Bass_III'])
        self.assertEqual(T.chord_tokens('Bbm7b5', 'Ab'), ['Root_II', 'Q_m7b5'])


class RoundTrip(unittest.TestCase):
    SEEDS = range(6)

    def test_every_genre_round_trips(self):
        for g in GENRES:
            G = endless.genre(g)
            for s in self.SEEDS:
                tune = endless.compose(G, s)
                toks = T.encode(tune)
                self.assertEqual(toks[0], 'BOS')
                self.assertEqual(toks[-1], 'EOS')
                back = T.decode(toks, G, seed=tune.seed, title=tune.title)
                self.assertEqual(T.diff(tune, back), [], (g, s))
                self.assertEqual(T.encode(back), toks, (g, s))

    def test_the_players_play_the_same_notes(self):
        for g, s in (('new-age-piano', 3), ('jazz-piano', 1)):
            G = endless.genre(g)
            tune = endless.compose(G, s)
            back = T.decode(T.encode(tune), G, seed=tune.seed, title=tune.title)
            a, b = endless.song(tune), endless.song(back)
            for name, tr in a.tracks.items():
                na = [(n.start, n.dur, n.pitch, n.vel) for n in tr._notes]
                nb = [(n.start, n.dur, n.pitch, n.vel) for n in b.tracks[name]._notes]
                self.assertEqual(na, nb, (g, name))


class Grammar(unittest.TestCase):
    def test_the_grammar_admits_every_teacher_piece(self):
        from agentsound.learn import grammar
        for g in GENRES:
            G = endless.genre(g)
            for s in range(4):
                toks = T.encode(endless.compose(G, s))
                self.assertIsNone(grammar.check(toks), (g, s))

    def test_the_grammar_rejects_a_misplaced_token(self):
        from agentsound.learn import grammar
        toks = T.encode(endless.compose(endless.genre('lofi-piano'), 1))
        bad = list(toks)
        bad[1], bad[2] = bad[2], bad[1]                  # Feel before Mood
        self.assertEqual(grammar.check(bad), 1)


class Spread(unittest.TestCase):
    """The set spread (learn sample --spread): deterministic, covering, and every forced header one the composer
    itself plays (HUMAN_FEEDBACK 2026-10-12: a top30 set was all gentle / minor / 65-68 BPM)."""

    def test_deterministic_and_seeded(self):
        from agentsound.learn.sample import spread_headers
        a, b = spread_headers('new-age-piano', 8, 3), spread_headers('new-age-piano', 8, 3)
        self.assertEqual(a, b)
        self.assertNotEqual(a, spread_headers('new-age-piano', 8, 4))

    def test_a_set_covers_the_genre(self):
        from agentsound.learn.sample import TEMPO_BANDS, header_combos, spread_headers
        for g in ('new-age-piano', 'jazz-piano', 'lofi-piano'):
            G = endless.genre(g)
            combos = header_combos(G)
            moods, feels = {c[0] for c in combos}, {c[1] for c in combos}
            forms, modes = {c[2] for c in combos}, {c[3] for c in combos}
            n = max(len(moods), len(feels), len(forms), 6)
            hs = spread_headers(g, n, 0)
            for field, vals in (('mood', moods), ('feel', feels), ('form', forms), ('mode', modes)):
                self.assertEqual({h[field] for h in hs}, vals, (g, field))
            for k in (n, 4 * n):                 # the moods take turns exactly
                c = Counter(h['mood'] for h in spread_headers(g, k, 0))
                self.assertLessEqual(max(c.values()) - min(c.values()), 1, (g, k, c))
            for h, nxt in zip(hs, hs[1:]):
                self.assertNotEqual(h['key'], nxt['key'], g)
            big = spread_headers(g, len(combos) * TEMPO_BANDS, 1)
            for feel in feels:                   # every third of every feel's tempo range is reached
                lo, hi = G.feels[feel]['tempo']
                ts = [h['tempo'] for h in big if h['feel'] == feel]
                self.assertTrue(all(lo <= t <= hi for t in ts), (g, feel, ts))
                self.assertGreater(max(ts) - min(ts), (hi - lo) / 3, (g, feel, ts))

    def test_every_forced_header_is_composable_and_grammar_valid(self):
        from agentsound.learn import grammar
        from agentsound.learn.sample import header_tokens, spread_headers
        for g in ('new-age-piano', 'jazz-piano', 'classical-piano'):
            G = endless.genre(g)
            for i, h in enumerate(spread_headers(g, 6, 2)):
                head = header_tokens(h)
                self.assertIsNone(grammar.check(['BOS'] + head), (g, head))
                tune = endless.compose(G, i, plan={'mood': h['mood'], 'feel': h['feel'], 'form': h['form'],
                                                   'key': f"{h['key']} {h['mode']}", 'tempo': h['tempo']})
                toks = T.encode(tune)
                self.assertEqual(toks[1:8], head, g)    # the teacher plays exactly this header
                self.assertIsNone(grammar.check(toks), g)


    def test_the_spread_also_spreads_the_arrangement(self):
        """Schema 2: the set-level draws (plan['set']: layout, climax kind) take turns too, the rare ones (below
        MIN_PAIR of the commonest: the climax 'step') left out; the arrangement mask forces them where the grammar
        reaches their key, and leaves every other token alone."""
        from agentsound.learn.sample import spread_headers
        G = endless.genre('new-age-piano')
        hs = spread_headers(G, 12, 0)
        for k, vals in (('layout', {'song', 'chorus', 'return'}), ('climax', {'grow', 'theme', 'climb', 'lift'})):
            c = Counter(h[k] for h in hs)
            self.assertEqual(set(c), vals, k)
            self.assertLessEqual(max(c.values()) - min(c.values()), 1, (k, c))
        self.assertNotIn('layout', spread_headers('jazz-piano', 4, 0)[0])

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'torch (the CUDA venv)')
    def test_the_arrangement_mask_forces_only_its_tokens(self):
        import torch
        from agentsound.endless.perform import arrange
        from agentsound.learn import grammar
        from agentsound.learn.data import Vocab
        from agentsound.learn.sample import _with_arr, arr_mask, arr_tokens, spread_headers
        G = endless.genre('new-age-piano')
        hs = spread_headers(G, 12, 0)
        tune = endless.compose(G, 101)
        toks = T.encode(tune, arrange(tune, G))
        vocab = Vocab.build([toks], arrangement=True)
        force = [arr_tokens(hs[0])]
        self.assertEqual(force[0], [f"ALayout_{hs[0]['layout']}", f"AClimax_{hs[0]['climax']}"])
        allowed = _with_arr(grammar.batch_allowed(vocab, 1, 'cpu'), arr_mask(vocab, force))
        seq = torch.tensor([[vocab.bos]])
        for step, t in enumerate(toks[1:], 1):           # walk the teacher's own tokens through the mask
            m = allowed(step, seq)[0]
            if t.startswith(('ALayout_', 'AClimax_')):
                ok = {vocab.itos[i] for i in m.nonzero()[:, 0].tolist() if vocab.itos[i].startswith(t[:5])}
                self.assertEqual(ok, {x for x in force[0] if x.startswith(t.partition('_')[0])})
            else:
                self.assertTrue(bool(m[vocab.stoi[t]]), t)
            seq = torch.cat([seq, torch.tensor([[vocab.stoi[t]]])], dim=1)
        self.assertIsNone(arr_mask(Vocab.build([T.encode(tune)]), force))    # (schema 1: nothing to force)
        from agentsound.learn.sample import player_arr_mask
        pm = player_arr_mask(vocab, 'new-age-piano')                 # (a blend: no jazz left hand in new-age)
        self.assertFalse(bool(pm[vocab.stoi['ALH_stride']]))
        self.assertTrue(all(bool(pm[vocab.stoi[t]]) for t in toks))
        self.assertIn('ALayout_return', Vocab.build([toks], arrangement=True).stoi)


class WarmStart(unittest.TestCase):
    @unittest.skipUnless(importlib.util.find_spec('torch'), 'torch (the CUDA venv)')
    def test_a_grown_vocabulary_keeps_the_old_rows(self):
        """learn train --init on data with new tokens: the old ids keep their rows (the old logits unchanged), a new
        token starts at its key's mean (ARit_0.5 <- every ARit_*)."""
        import torch
        from agentsound.learn.data import Vocab
        from agentsound.learn.model import Config, Student
        from agentsound.learn.train import extend_vocab, related_rows
        v = Vocab(['PAD', 'BOS', 'EOS', 'ARit_0.8', 'ARit_0.9', 'Mood_x', 'P_60'])
        m = Student(Config(vocab=len(v), n_genres=5, d=32, layers=2, heads=2, ctx=16, dropout=0.0)).to('cpu').eval()
        m2, v2 = extend_vocab(m, v, ['ARit_0.5', 'AVary_seq', 'Q_new', 'P_60'], device='cpu')
        m2.eval()
        self.assertEqual(v2.itos[:len(v)], v.itos)
        self.assertEqual(v2.itos[len(v):], ['ARit_0.5', 'AVary_seq', 'Q_new'])
        self.assertEqual(related_rows(v, 'ARit_0.5'), [3, 4])
        self.assertEqual(related_rows(v, 'AVary_seq'), [3, 4])
        x, c = torch.tensor([[1, 3, 5, 6]]), torch.zeros(1, 5)
        with torch.no_grad():
            a, b = m(x, c), m2(x, c)
        self.assertTrue(torch.allclose(a, b[..., :len(v)], atol=1e-5))
        w = m.tok.weight.detach()
        self.assertLess(float((m2.tok.weight.detach()[len(v)] - w[3:5].mean(0)).abs().max()), 0.05)
        from agentsound.learn.train import extend_ctx
        m3 = extend_ctx(m2, 24, device='cpu').eval()                 # (a longer context: the old positions kept)
        self.assertEqual(m3.c.ctx, 24)
        with torch.no_grad():
            self.assertTrue(torch.allclose(m3(x, c), b, atol=1e-5))
            self.assertEqual(tuple(m3(torch.ones(1, 24, dtype=torch.long), c).shape), (1, 24, len(v2)))


class CpuPool(unittest.TestCase):
    def test_the_workers_cannot_see_the_gpu_and_the_parent_env_is_kept(self):
        import os
        from agentsound.learn.evaluate import cpu_pool
        before = os.environ.get('CUDA_VISIBLE_DEVICES')
        with cpu_pool(1) as p:
            self.assertEqual(p.apply(os.getenv, ('CUDA_VISIBLE_DEVICES',)), '-1')
        self.assertEqual(os.environ.get('CUDA_VISIBLE_DEVICES'), before)


class Variety(unittest.TestCase):
    def test_variety_is_zero_for_clones_and_high_for_a_spread(self):
        from agentsound.learn.evaluate import variety
        from agentsound.learn.sample import spread_headers
        G = endless.genre('new-age-piano')
        same = [T.encode(endless.compose(G, 0))] * 6
        v = variety(same, G)
        self.assertEqual(v['variety'], 0.0)
        self.assertEqual(v['fields']['mood']['top_share'], 1.0)
        self.assertIsNone(v['fields']['form']['h'])          # one form: cannot vary, not counted
        spread = [T.encode(endless.compose(G, i, plan={'mood': h['mood'], 'feel': h['feel'], 'form': h['form'],
                                                       'key': f"{h['key']} {h['mode']}", 'tempo': h['tempo']}))
                  for i, h in enumerate(spread_headers(G, 6, 0))]
        w = variety(spread, G)
        for f in ('mood', 'feel', 'mode', 'key'):
            self.assertGreaterEqual(w['fields'][f]['h'], 0.9, f)
        self.assertGreater(w['variety'], 0.5)

    def test_header_of_reads_the_climax(self):
        from agentsound.learn.evaluate import header_of
        tune = endless.compose(endless.genre('new-age-piano'), 4)
        h = header_of(T.encode(tune))
        self.assertEqual((h['mood'], h['feel'], h['tempo']), (tune.mood, tune.feel, tune.tempo))
        if tune.climax:
            self.assertEqual(h['climax_pitch'], tune.climax['pitch'])
            self.assertTrue(0.0 <= h['climax_pos'] <= 1.0)
        self.assertIsNone(header_of(['BOS', 'Mood_x']))
        self.assertIsNone(h['layout'])                          # (schema 1: no Arr block)

    def test_the_arrangement_measures(self):
        from agentsound.endless.perform import arrange
        from agentsound.learn.evaluate import arrangement_of, arrangement_table, header_of, variety
        G = endless.genre('new-age-piano')
        tunes = [endless.compose(G, s) for s in range(100, 106)]
        arrs = [arrange(t, G) for t in tunes]
        seqs = [T.encode(t, a) for t, a in zip(tunes, arrs)]
        for s_, a in zip(seqs, arrs):
            got = arrangement_of(s_)
            self.assertEqual(got['layout'], a.piece['layout'])
            self.assertEqual(got['sections'], list(a.sections))
            self.assertEqual(got['climax'], a.sections['climax']['climax'])
            self.assertEqual(header_of(s_)['climax_kind'], got['climax'])
        tab = arrangement_table(seqs, seqs)
        self.assertTrue(all(d['tv'] in (0.0, None) for d in tab.values()), tab)     # (None: no jazz left hand)
        self.assertEqual(tab['layout']['tv'], 0.0)
        self.assertIn('layout', variety(seqs, G)['fields'])
        self.assertIsNone(arrangement_of(T.encode(tunes[0])))


class Genres(unittest.TestCase):
    def test_student_genres_are_pinned_endless_genres(self):
        # a new endless genre must not change the trained checkpoints' conditioning width
        from agentsound.learn.data import GENRE_NAMES
        self.assertEqual(GENRE_NAMES[:5], ['jazz-piano', 'jazz-trio', 'new-age-piano', 'classical-piano', 'lofi-piano'])
        self.assertLessEqual(set(GENRE_NAMES), set(GENRES))


class Strict(unittest.TestCase):
    def setUp(self):
        self.G = endless.genre('new-age-piano')
        self.toks = T.encode(endless.compose(self.G, 2))

    def test_truncated_sequence_is_an_error(self):
        with self.assertRaises(T.TokenError):
            T.decode(self.toks[:len(self.toks) // 2], self.G)

    def test_a_foreign_form_or_feel_is_an_error(self):
        bad = [('Form_blues' if t.startswith('Form_') else t) for t in self.toks]
        with self.assertRaises(T.TokenError):
            T.decode(bad, self.G)

    def test_a_note_outside_its_bar_is_an_error(self):
        i = next(i for i, t in enumerate(self.toks) if t.startswith('Pos_') and i > 100)
        bad = list(self.toks)
        bad[i] = 'Pos_999'
        with self.assertRaises(T.TokenError):
            T.decode(bad, self.G)

    def test_off_grid_time_is_an_error(self):
        with self.assertRaises(T.TokenError):
            T.q12(0.3)


if __name__ == '__main__':
    unittest.main()
