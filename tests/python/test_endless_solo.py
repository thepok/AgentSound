"""Round os1: the endless orchestra-symphonic SOLO (agentsound/endless/solo.py) and the orchestra presets' solo
players (orch.SOLOS, film_orchestra / symphony_orchestra solos=): the switch restoring master, the set's solo-event
draw with memory, the solo band, and - with SSO + VSCO 2 CE installed - a piece whose exposed wind lines, string solo
event and concertmaster reach the solo players. Notes only, no audio."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import Song, bands, endless  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.endless import composer, genres, solo  # noqa: E402

SSO = orch.installed('sso') and orch.installed('vsco2-ce')


class Switch(unittest.TestCase):
    def tearDown(self):
        genres.symphony_solo(False)

    def test_switch_restores_master(self):
        g = genres.get('orchestra-symphonic')
        genres.symphony_solo(True)
        self.assertTrue(g.plan.get('set_solo'))
        self.assertIsNotNone(solo.SOLO)
        genres.symphony_solo(False)
        self.assertIsNone(solo.SOLO)
        self.assertNotIn('set_solo', g.plan)
        self.assertFalse(any('solo' in x for x in composer.set_plan(g.validate(), 4, 160000)))
        for preset in ('film_orchestra', 'symphony_orchestra'):        # (the solo players are opt-in)
            self.assertFalse(set(orch.SOLOS) & set(orch.role_table(preset)), preset)

    def test_set_draw_memory(self):
        genres.symphony_solo(True)
        g = genres.get('orchestra-symphonic').validate()
        for seed in (160000, 160100, 160200):
            got = [x['solo'] for x in composer.set_plan(g, 12, seed)]
            self.assertTrue(set(got) <= set(solo.SOLO_ON['event']['kinds']), got)
            for a, b in zip(got, got[1:]):
                self.assertFalse(a == b != 'none', got)
            for a, b, c in zip(got, got[1:], got[2:]):
                self.assertFalse(a == b == c == 'none', got)
        r1 = solo.solo_draw(random.Random(5), ['violin'])
        self.assertNotEqual(r1, 'violin')
        self.assertEqual(r1, solo.solo_draw(random.Random(5), ['violin']))


@unittest.skipUnless(SSO, 'SSO / VSCO 2 CE not installed')
class Band(unittest.TestCase):
    def test_solo_players(self):
        s = Song('t', tempo=80)
        keep = ('violins1', 'oboes')
        b = bands.make('film_orchestra', s, without=tuple(r for r in bands.get('film_orchestra').roles
                                                          if r not in keep),
                       solos=('oboe_solo', 'violin_concertmaster'))
        self.assertEqual(set(b.roles), {'violins1', 'oboes', 'oboe_solo', 'violin_concertmaster'})
        self.assertIn('oboe_solo', b.info['mono'])
        self.assertIn('violin_concertmaster', b.info['mono'])
        self.assertAlmostEqual(b['oboe_solo'].gain_db - b['oboes'].gain_db, orch.SOLO_GAIN['oboe_solo'], places=1)
        self.assertAlmostEqual(b['violin_concertmaster'].gain_db - b['violins1'].gain_db,
                               orch.SOLO_GAIN['violin_concertmaster'], places=1)
        with self.assertRaises(Exception):
            bands.make('film_orchestra', Song('u', tempo=80), solos=('piccolo_solo',))


@unittest.skipUnless(SSO, 'SSO / VSCO 2 CE not installed')
class Piece(unittest.TestCase):
    def setUp(self):
        genres.symphony_solo(True)

    def tearDown(self):
        genres.symphony_solo(False)

    def test_a_piece_plays_its_solos(self):
        g = genres.get('orchestra-symphonic').validate()
        plan = composer.set_plan(g, 3, 121000)
        t = endless.compose(g, 121020, plan=plan[2])
        self.assertEqual(t.arrange['solo'], plan[2]['solo'])
        s = endless.song(t)
        info = s.orch_scores[0].band.info
        parts = [p for p in s.orchestration.parts if p.role in orch.SOLOS]
        self.assertTrue(s.solo_events and parts)
        winds = [e for e in s.solo_events if e['what'] == 'wind']
        self.assertTrue(winds)
        for p in parts:
            ons = [round(a, 3) for a, _, _ in p.notes]
            self.assertEqual(len(ons), len(set(ons)), p.role)                  # (one player: one note at a time)
            self.assertTrue(p.role in info['mono'], p.role)
        for e in s.solo_events:
            if e['what'] == 'concertmaster':
                cm = next(p for p in s.orchestration.parts if p.role == 'violin_concertmaster' and p.block == e['block'])
                v1 = next(p for p in s.orchestration.parts if p.role == 'violins1' and p.block == e['block']
                          and p.function == 'melody')
                self.assertEqual({a for a, _, _ in cm.notes}, {a for a, _, _ in v1.notes})
        st = solo.solo_stats(s)
        self.assertGreater(st['share'], 0.0)


if __name__ == '__main__':
    unittest.main()
