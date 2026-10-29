"""Guest selection, melodic handover and saved-plan reproducibility."""
import copy
import json
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from agentsound.bandlib import orchestration as o
from agentsound.endless import hero_sax as hs
from agentsound.theory import ComposeError


class HeroSax(unittest.TestCase):
    def fixture(self):
        score = o.OrchScore()
        parts = []
        for i in range(7):
            b = score.block(f'b{i}', i*8, 8, peak=i==3)
            ns = [(i*8+j, .8, 65+j%4) for j in range(8)]
            parts += [o.Part('violins1', b.name, 'melody', '', ns, 'sustain', 0, True),
                      o.Part('horns', b.name, 'doubling', 'melody', ns.copy(), 'sustain', 0, True),
                      o.Part('violas', b.name, 'harmony', '', ns.copy(), 'sustain', -5, False),
                      o.Part('basses', b.name, 'bass', '', ns.copy(), 'sustain', -3, True)]
        return o.Orchestration(parts), score, SimpleNamespace(tempo=80, arrange={'hero_sax_enabled':True})

    def test_modes_determinism_and_spacing(self):
        for mode in hs.MODES:
            history=[]
            for seed in range(100):
                got=hs.draw(mode,seed,history)
                self.assertEqual(got,hs.draw(mode,seed,history))
                self.assertFalse(got and history and history[-1])
                history.append(got)
            if mode=='off': self.assertFalse(any(history))
            else: self.assertGreater(sum(history),10)
        with self.assertRaises(ComposeError): hs.draw('typo',1)

    def test_off_has_no_mutations(self):
        p,s,t=self.fixture(); t.arrange['hero_sax_enabled']=False
        before=copy.deepcopy(p)
        self.assertEqual(hs.prepare(p,s,t),[])
        self.assertEqual(p,before)

    def test_handover_removes_only_melody_doublings_and_keeps_bass(self):
        p,s,t=self.fixture(); before=copy.deepcopy(p)
        events=hs.prepare(p,s,t)
        self.assertEqual([e['block'] for e in events],['b1','b3','b5'])
        selected={e['block'] for e in events}
        for x,y in zip(p.parts,before.parts):
            if x.block not in selected: self.assertEqual(x,y)
            elif x.function in ('melody','doubling'): self.assertFalse(x.notes)
            elif x.function=='bass': self.assertEqual(x,y)
            else: self.assertEqual(x.notes,y.notes); self.assertLess(x.off,y.off)

    def test_choir_and_existing_solo_keep_their_blocks(self):
        p,s,t=self.fixture()
        p.parts[4].role='violin_solo'
        events=hs.prepare(p,s,t,choir={'events':[{'block':'b2'},{'block':'b3'}]})
        self.assertFalse(any(e['block'] in ('b1','b2','b3') for e in events))

    def test_fit_preserves_intervals_and_rejects_unplayable_lines(self):
        ns=[(i,.8,48+i) for i in range(8)]
        fitted=hs.fit(ns,80)
        self.assertTrue(fitted)
        self.assertEqual([q-ns[i][2] for i,(_,_,q) in enumerate(fitted)],[24]*8)
        self.assertFalse(hs.fit([(i*.1,.09,65) for i in range(8)],120))
        self.assertFalse(hs.fit([(0,1,65)]*8,80))
        self.assertFalse(hs.fit([(i,1,40+i*8) for i in range(8)],80))
        high=hs.fit([(i,1,77+i%6) for i in range(12)],80)
        self.assertTrue(high)
        self.assertTrue(all(57 <= q <= 80 for _,_,q in high))

    def test_archived_tune_replay_keeps_guest_off(self):
        self.check_replay(None, {'hero_sax':'off'})

    def test_new_tune_replay_preserves_saved_draw(self):
        plan={'hero_sax':'frequent','hero_sax_enabled':True}
        self.check_replay(plan, plan)

    def test_guest_only_plan_still_pins_best_of_n_music(self):
        from agentsound.endless import run
        from agentsound.endless.genres import get
        guest={'hero_sax':'frequent','hero_sax_enabled':True}
        tune=SimpleNamespace(title='test', form='rondo', feel='andante', mood='journey',
                             key='F major', tempo=76, arrange=guest)
        with patch.object(run,'prepare',return_value=(tune,object())) as prepare, \
                patch.object(run,'score',return_value={'score':1,'hard':[],'worst':[]}):
            run.candidates(get('orchestra-symphonic'),1,2,SimpleNamespace(),lambda _:None,plan=guest)
        next_plan=prepare.call_args_list[1].kwargs['plan']
        self.assertEqual(next_plan['feel'],'andante')
        self.assertEqual(next_plan['key'],'F major')
        self.assertTrue(next_plan['hero_sax_enabled'])
        self.assertEqual(guest,{'hero_sax':'frequent','hero_sax_enabled':True})

    def check_replay(self, plan, expected):
        from agentsound.endless import run
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp,'tune.json').write_text(json.dumps(dict(genre='orchestra-symphonic',title='test',
                compose=dict(seed=1,mood=None,plan=plan))))
            with patch.object(run,'compose',return_value=SimpleNamespace(title='test')) as compose, \
                    patch('agentsound.endless.perform.build',return_value='song'):
                self.assertEqual(run.load_scored(Path(tmp))[0],'song')
                self.assertEqual(compose.call_args.kwargs['plan'],expected)


if __name__=='__main__': unittest.main()
