"""Round ox1: the guest colours of orchestra-symphonic (endless.colour, genres.symphony_colour) - the draw's set memory,
the switch, the set plan's arrangement (size / tempo), and with the packs a piece per guest whose events are placed,
written in the instrument's range, played on their own tracks in the orchestra's hall, the orchestra thinned under the
guitar, the organ's credits naming Lars Palo."""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import endless  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.endless import colour as CO, composer, genres  # noqa: E402
from agentsound.theory import note  # noqa: E402

SSO = orch.installed('sso')
FEELS = ('allegro', 'andante', 'scherzo', 'river', 'vivace')


class ColourDraw(unittest.TestCase):
    """The draw with every guest's pack taken as installed (the draw's rules, not this machine's packs)."""

    def setUp(self):
        self._avail = CO.available
        CO.available = lambda name: True

    def tearDown(self):
        CO.available = self._avail

    def test_the_draw_and_its_memory(self):
        self.assertEqual(CO.guest_draw('allegro', random.Random(3)), CO.guest_draw('allegro', random.Random(3)))
        for name, G in CO.GUESTS.items():
            for plan, evs in G['plans'].items():
                self.assertTrue(evs, (name, plan))
        nones, sets = 0, 60
        for k in range(sets):
            hist = []
            for j in range(8):
                hist.append(CO.guest_draw(FEELS[(k + j) % 5], random.Random(f"{k}:{j}"), hist, 8))
            names = [h['colour'] for h in hist]
            for a, b in zip(names, names[1:]):
                self.assertNotEqual(a, b)                      # (never the neighbour's colour, nor two without)
            for c in set(names) - {'none'}:
                self.assertLessEqual(names.count(c), 2, names)  # (at most two of a colour per 8-piece set)
            nones += names.count('none')
        self.assertTrue(0.05 < nones / (8.0 * sets) < 0.3, nones)    # (most pieces get one, some none)

    def test_feels_steer_the_guest(self):
        got = {f: [CO.guest_draw(f, random.Random(i))['colour'] for i in range(300)] for f in FEELS}
        self.assertNotIn('guitar', got['scherzo'])
        self.assertNotIn('harpsichord', got['scherzo'])
        self.assertGreater(got['andante'].count('guitar'), got['allegro'].count('guitar'))
        self.assertGreater(got['scherzo'].count('celesta'), got['allegro'].count('celesta'))

    def test_switch_and_the_set_plan(self):
        try:
            genres.symphony_colour(True)
            self.assertEqual(CO.COLOUR, CO.COLOUR_ON)
            self.assertTrue(genres.ORCHESTRA_SYMPHONIC.plan.get('set_guest'))
            g = genres.get('orchestra-symphonic').validate()
            plan = composer.set_plan(g, 8, 163000)
            for x in plan:
                gu = x['guest']
                self.assertIn(gu['colour'], tuple(CO.GUESTS) + ('none',))
                if gu['colour'] in ('guitar', 'harpsichord') and \
                        g.moods[x['mood']]['size'].get('chamber', 0) > 0:
                    self.assertEqual(x['size'], 'chamber')
                if gu['colour'] == 'guitar':
                    lo, hi = g.feels[x['feel']]['tempo']
                    self.assertLessEqual(x['tempo'], round(lo + CO.COLOUR_ON['guitar_tempo'] * (hi - lo)))
        finally:
            genres.symphony_colour(False)
        self.assertIsNone(CO.COLOUR)
        self.assertNotIn('set_guest', genres.ORCHESTRA_SYMPHONIC.plan)
        g = genres.get('orchestra-symphonic').validate()
        self.assertNotIn('guest', composer.set_plan(g, 3, 163000)[0])


class ColourPieces(unittest.TestCase):
    """One piece per guest (the set plan 163000's slots: celesta, guitar, organ, harpsichord, bells)."""

    @classmethod
    def setUpClass(cls):
        cls.ok = SSO and all(CO.available(c) for c in CO.GUESTS)

    def _piece(self, colour):
        g = genres.get('orchestra-symphonic').validate()
        plan = composer.set_plan(g, 8, 163000)
        j = next(i for i, x in enumerate(plan) if x['guest']['colour'] == colour)
        t = endless.compose(g, 163000 + 37 * j, plan=plan[j])
        self.assertEqual(t.arrange['guest'], plan[j]['guest'])
        return t, endless.song(t)

    def _tracks(self, render, ids):
        return {tr['id']: [n for n in tr.get('notes', []) if n[2] >= 21] for tr in render['tracks'] if tr['id'] in ids}

    @unittest.skipUnless(SSO, 'SSO not installed')
    def test_pieces(self):
        if not self.ok:
            self.skipTest('a guest pack is not installed')
        from agentsound import delivery
        try:
            genres.symphony_colour(True)
            for colour, ids, rng in (('guitar', ('guitar',), ('E2', 'B5')),
                                     ('harpsichord', ('harpsichord',), ('F1', 'C6')),
                                     ('celesta', ('celesta', 'glockenspiel'), ('C4', 'C8')),
                                     ('bells', ('bells',), ('C4', 'G5'))):
                t, s = self._piece(colour)
                st = CO.colour_stats(s)
                self.assertEqual(st['plan']['colour'], colour)
                self.assertGreaterEqual(len(st['events']), 2, (colour, st))
                tr = self._tracks(s.compile(), ids)
                self.assertTrue(tr, colour)
                lo, hi = note(rng[0]), note(rng[1])
                for tid, ns in tr.items():
                    self.assertTrue(all(lo <= n[2] <= hi for n in ns), (tid, sorted({n[2] for n in ns})))
                if colour == 'guitar':                         # (the serenade: no brass / harp / timpani under it)
                    ev = next(e for e in st['events'] if e['event'] == 'serenade')
                    for p in s.orchestration.parts:
                        if any(ev['start'] + 1e-6 <= n[0] < ev['end'] - 1e-6 for n in p.notes):
                            self.assertNotIn(p.role, CO.LOUD_ROLES + ('harp',), p.role)
            t, s = self._piece('organ')
            st = CO.colour_stats(s)
            self.assertIn('summit', [e['event'] for e in st['events']])
            render = s.compile()
            org = [tr['id'] for tr in render['tracks'] if tr['id'].startswith('organ_')]
            self.assertIn('organ_full', org)
            self.assertIn('organ_pedal_full', org)
            cr = delivery.collect_credits(render)
            self.assertTrue(any('Lars Palo' in a for a in cr['attributions']), cr['attributions'])
        finally:
            genres.symphony_colour(False)


if __name__ == '__main__':
    unittest.main()
