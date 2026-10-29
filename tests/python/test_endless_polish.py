"""Round op1: the endless orchestra-symphonic POLISH (genres.symphony_polish) of the CHOIR v2 / SOLO / COLOUR
features: the switch restoring master, the set plan's memories (the title's form label, the summit's texture and cap,
the guests' signature gestures), and - with SSO + VSCO 2 CE installed - a piece's solo blocks (no parade), the cello
event and the guest's coda. Notes only, no audio."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from agentsound import endless  # noqa: E402
from agentsound.bandlib import orchestra as orch  # noqa: E402
from agentsound.endless import choir, colour, composer, genres, solo  # noqa: E402
from agentsound.theory import note  # noqa: E402

SSO = orch.installed('sso') and orch.installed('vsco2-ce')


def _g():
    return genres.get('orchestra-symphonic').validate()


class Switch(unittest.TestCase):
    def tearDown(self):
        genres.symphony_polish(False)

    def test_switch_restores_master(self):
        before = (dict(choir.CHOIR), dict(solo.SOLO), dict(colour.COLOUR))
        plan0 = composer.set_plan(_g(), 8, 168000)
        genres.symphony_polish(True)
        self.assertTrue(_g().plan.get('set_polish'))
        self.assertEqual(choir.CHOIR['caps']['summit'], 2)
        self.assertIn('polish', solo.SOLO)
        self.assertIn('polish', colour.COLOUR)
        self.assertIs(choir.plans(), choir.PLANS_POLISH)
        genres.symphony_polish(False)
        self.assertEqual((choir.CHOIR, solo.SOLO, colour.COLOUR), before)
        self.assertNotIn('set_polish', _g().plan)
        self.assertEqual(composer.set_plan(_g(), 8, 168000), plan0)

    def test_set_memories(self):
        genres.symphony_polish(True)
        g = _g()
        for seed in (168000, 168300):
            plan = composer.set_plan(g, 12, seed)
            forms = [x.get('title_form', '') for x in plan]
            for i in range(len(forms)):                       # (a form label at most once in any 4 slots)
                self.assertLessEqual(sum(1 for f in forms[i:i + 4] if f), 1, forms)
            summits = [int('summit' in choir.plans()[x['choir']]['events']) for x in plan]
            for i in range(len(summits)):                     # (the sung summit at most twice in any 8 slots)
                self.assertLessEqual(sum(summits[i:i + 8]), 2, [x['choir'] for x in plan])
            for x in plan:
                self.assertEqual('choir_tex' in x, 'summit' in choir.plans()[x['choir']]['events'])
            seen = {}
            for x in plan:                                    # (a guest's gesture new while variants are left)
                gst = x['guest']
                if gst.get('gest'):
                    vs = colour.COLOUR_POLISH['gestures'][gst['colour']]
                    prev = seen.setdefault(gst['colour'], [])
                    if len(prev) < len(vs):
                        self.assertNotIn(gst['gest'], prev, (gst, prev))
                    prev.append(gst['gest'])
                self.assertNotEqual(gst['colour'] == 'guitar' and x.get('size'), 'chamber')
        t = endless.compose(g, 168020, plan=dict(plan[2], title_form='Overture'))
        self.assertTrue(t.title.startswith('Overture:'), t.title)
        t = endless.compose(g, 168020, plan=dict(plan[2], title_form=''))
        self.assertNotIn(':', t.title)


@unittest.skipUnless(SSO, 'SSO / VSCO 2 CE not installed')
class Piece(unittest.TestCase):
    def setUp(self):
        genres.symphony_polish(True)

    def tearDown(self):
        genres.symphony_polish(False)

    def test_a_piece(self):
        g = _g()
        plan = composer.set_plan(g, 5, 168000)
        slot = dict(plan[4], solo='cello')
        t = endless.compose(g, 168040, plan=slot)
        s = endless.song(t)
        ev = s.solo_events
        exposed = {e['block'] for e in ev if e['what'] in ('wind', 'event', 'concertmaster')}
        run = 0
        for b in t.symphony['blocks']:                        # (no parade: at most 2 solo blocks in a row)
            run = run + 1 if b['name'] in exposed else 0
            self.assertLessEqual(run, solo.SOLO_POLISH['run'], [x['what'] + ':' + x['block'] for x in ev])
        cello = [e for e in ev if e['what'] == 'event']
        self.assertTrue(cello and cello[0]['role'] == 'cello_solo', cello)
        part = next(p for p in s.orchestration.parts if p.role == 'cello_solo')
        lo, hi = (note(x) for x in orch.SOLO_RANGE['cello_solo'])
        self.assertTrue(all(lo <= q <= hi for _, _, q in part.notes))
        st = colour.colour_stats(s)
        if st['events']:
            last = max(e['end'] for e in st['events'])
            self.assertGreater(last, max(p.notes[-1][0] for p in s.orchestration.parts if p.notes) - 16)


if __name__ == '__main__':
    unittest.main()
