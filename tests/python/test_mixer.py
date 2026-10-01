import contextlib
import io
import os
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli, mixer
from agentsound.patches import inst
from agentsound.song import Song
from agentsound.theory import ComposeError

BARS = 8


def report(levels: dict, profile='synthwave', sections=(('verse', -12.0), ('chorus', -10.0)), roles=None, k=None,
           peaks=None, bed=None, warnings=(), third=None, shares=None):
    """A synthetic report.json: `levels` = {node: {section: bar level dB (K-weighted-ish) or None}}; every section is
    BARS bars; K offsets (lufs - rmsDb) default 0 so the levels are what the mixer measures."""
    rows, secs = [], []
    for i, (name, lufs) in enumerate(sections):
        secs.append({'name': name, 'startBar': 1 + i * BARS, 'endBar': 1 + (i + 1) * BARS, 'lufs': lufs})
    rows = [[b] for b in range(1, 1 + BARS * len(sections))]
    nodes = []
    for nid, per in levels.items():
        bars = []
        for name, _ in sections:
            v = per.get(name)
            bars += [-120 if v is None else v] * BARS
        kk = (k or {}).get(nid, 0.0)
        nodes.append({'id': nid, 'bus': False, 'role': (roles or {}).get(nid, 'other'), 'rmsDb': -25.0,
                      'lufs': -25.0 + kk, 'peakDb': (peaks or {}).get(nid, -6.0), 'barsRmsDb': bars,
                      'mixSharePct': (shares or {}).get(nid, {})})
    space = {'sections': [{'section': s, 'bedVsLeadDb': v, 'lead': 'lead'} for s, v in (bed or {}).items()]}
    g = {}
    if third:
        g['thirdOctave'] = {'hz': [f for f, _ in third], 'vsRefDb': [d for _, d in third]}
    return {'reference': {'profile': profile, 'lufsTarget': [-12, -9]}, 'sections': secs, 'timeline': {'rows': rows},
            'nodes': nodes, 'space': space, 'warnings': list(warnings), 'global': g}


SYNTH_ROLES = {'lead': 'lead', 'drums': 'drums', 'bass': 'bass', 'pad': 'bed', 'keys': 'other'}


class Roles(unittest.TestCase):
    def test_role_from_id(self):
        cases = {'pad_hi': 'bed', 'sub_808': 'low', 'bass_drum': 'rhythm', 'drums': 'rhythm', 'hook': 'lead',
                 'sunrise_lead': 'lead', 'keys': 'other', 'riser': 'fx', 'strings': 'bed', 'shaker': 'rhythm',
                 'upright_bass': 'low', 'arp': 'other'}
        for nid, role in cases.items():
            self.assertEqual(mixer.role_from_id(nid), role, nid)

    def test_priority_explicit_over_report_over_id(self):
        rep = report({'lead': {'verse': -20}, 'robot': {'verse': -24}, 'melody2': {'verse': -26}},
                     roles={'lead': 'lead', 'robot': 'bass'})
        roles, why = mixer.infer_roles(report=rep, bed=['robot'])
        self.assertEqual(roles['robot'], 'bed')
        self.assertEqual(why['robot'], 'explicit')
        self.assertEqual(roles['lead'], 'lead')
        roles, _ = mixer.infer_roles(report=rep)
        self.assertEqual(roles['robot'], 'low')       # report role 'bass'
        self.assertEqual(roles['melody2'], 'other')   # report role wins over the id ('other')
        with self.assertRaises(ComposeError):
            mixer.infer_roles(report=rep, roles={'robot': 'singer'})

    def test_melodic_lead_fallback(self):
        rep = report({'piano': {'verse': -20}, 'drums': {'verse': -35}}, roles={'drums': 'drums'}, profile='jazz')
        rep['nodes'][0]['dynamics'] = {'kind': 'lead'}
        roles, why = mixer.infer_roles(report=rep)
        self.assertEqual(roles['piano'], 'lead')
        self.assertIn('dynamics', why['piano'])


class Measure(unittest.TestCase):
    def test_group_sum_and_k_offset(self):
        rep = report({'lead': {'verse': -20, 'chorus': -20}, 'kick': {'verse': -26, 'chorus': -26},
                      'snare': {'verse': -26, 'chorus': -26}, 'pad': {'verse': -24, 'chorus': -24}},
                     roles={'lead': 'lead', 'kick': 'drums', 'snare': 'drums', 'pad': 'bed'}, k={'pad': 2.0})
        bal = mixer.measure(rep, mixer.infer_roles(report=rep)[0], mixer.get_profile('synthwave'))
        ch = next(b for b in bal if b.name == 'chorus')
        self.assertTrue(ch.judged and ch.hook)
        self.assertAlmostEqual(ch.rel['rhythm'], -3.0, delta=0.05)   # two parts at -26 sum to -23
        self.assertAlmostEqual(ch.rel['bed'], -2.0, delta=0.05)      # -24 + K offset 2
        self.assertFalse(next(b for b in bal if b.name == 'verse').hook)

    def test_a_featured_track_leads_its_section(self):
        # a bass solo (bass.feature(bass_solo)): the bass is that section's lead, the drums are judged against it and
        # the bass is not 'low' there; in the other sections the piano leads as before
        lv = {'piano': {'head': -20, 'bass_solo': -38}, 'bass': {'head': -25, 'bass_solo': -23},
              'drums': {'head': -34.5, 'bass_solo': -37}}
        rep = report(lv, profile='jazz', sections=(('head', -15.0), ('bass_solo', -17.0)),
                     roles={'piano': 'lead', 'drums': 'drums', 'bass': 'bass'})
        roles = mixer.infer_roles(report=rep)[0]
        bal = mixer.measure(rep, roles, mixer.get_profile('jazz'), featured={'bass_solo': 'bass'})
        head, bs = bal
        self.assertEqual(head.lead, 'piano')
        self.assertEqual(bs.lead, 'bass')
        self.assertAlmostEqual(bs.rel['rhythm'], -14.0, delta=0.05)
        self.assertNotIn('low', bs.rel)
        s = Song('t', tempo=120)
        head = s.section('head', bars=8)
        sec = s.section('bass_solo', bars=8)
        t = s.track('bass', inst.va())
        t.feature(sec, db=2)
        self.assertEqual(mixer.features(s), {'bass_solo': 'bass'})
        s.track('drums', inst.va()).feature(head, db=1)        # a feature from beat 0: no glide before the start
        self.assertEqual(mixer.features(s), {'bass_solo': 'bass', 'head': 'drums'})

    def test_space_bed_and_unjudged_sections(self):
        rep = report({'lead': {'verse': None, 'chorus': -20}, 'pad': {'verse': -24, 'chorus': -24}},
                     roles={'lead': 'lead', 'pad': 'bed'}, bed={'chorus': -1.2})
        bal = mixer.measure(rep, mixer.infer_roles(report=rep)[0], mixer.get_profile('synthwave'))
        self.assertFalse(bal[0].judged)
        self.assertIn('no lead', bal[0].why)
        self.assertEqual(bal[1].rel['bed'], -1.2)
        self.assertEqual(bal[1].bed_from, 'space')

    def test_hooks_by_name_or_loudness(self):
        rep = report({'lead': {'a': -20, 'b': -20}}, sections=(('a', -14.0), ('b', -10.0)), roles={'lead': 'lead'})
        self.assertEqual(mixer.hook_sections(mixer.View(rep)), {'b'})
        rep = report({'lead': {'verse': -20, 'drop': -20}}, sections=(('verse', -10.0), ('drop', -12.0)))
        self.assertEqual(mixer.hook_sections(mixer.View(rep)), {'drop'})
        self.assertEqual(mixer.hook_sections(mixer.View(rep), ['verse']), {'verse'})


def synth(lead=-20.0, drums=-23.0, bass=-23.0, pad=-24.0, keys=-28.0, peak=-6.0, **kw):
    lv = {n: {'verse': v - 1.0 if n != 'lead' else v, 'chorus': v} for n, v in
          (('lead', lead), ('drums', drums), ('bass', bass), ('pad', pad), ('keys', keys))}
    return report(lv, roles=SYNTH_ROLES, peaks={'lead': peak}, **kw)


class Propose(unittest.TestCase):
    prof = mixer.get_profile('synthwave')

    def moves(self, rep, **kw):
        roles = mixer.infer_roles(report=rep)[0]
        return mixer.propose(rep, roles, self.prof, **kw)[0]

    def test_balanced_mix_needs_nothing(self):
        self.assertEqual(self.moves(synth()), [])

    def test_buried_lead_goes_up(self):
        # everything 2.5 dB too close to the lead: the shared part is the lead's (it has the headroom)
        m = self.moves(synth(lead=-20, drums=-19.5, bass=-19.5, pad=-19.5))
        trims = {x.node: x.db for x in m if x.kind == 'trim'}
        self.assertGreater(trims['lead'], 0.5)
        self.assertLessEqual(trims['lead'], mixer.MAX_STEP)
        self.assertTrue(all(x.db <= mixer.MAX_STEP for x in m))

    def test_no_headroom_band_comes_down(self):
        m = self.moves(synth(lead=-20, drums=-19.5, bass=-19.5, pad=-19.5, peak=-0.3))
        trims = {x.node: x.db for x in m if x.kind == 'trim'}
        self.assertNotIn('lead', trims)
        for n in ('drums', 'bass'):
            self.assertLess(trims[n], -1.0, n)

    def test_bed_crowding_is_carved_first(self):
        m = self.moves(synth(pad=-19.0))
        ducks = [x for x in m if x.kind == 'duck']
        self.assertEqual(len(ducks), 1)
        self.assertEqual(ducks[0].params['key'], 'lead')
        self.assertEqual(ducks[0].params['targets'], ['pad'])
        self.assertEqual(ducks[0].params['depth'], self.prof.bed_duck_db)
        # already ducked (MIX): no second duck
        mix = {'duck': [{'targets': ['pad'], 'key': 'lead', 'depth': 2.5}]}
        self.assertFalse([x for x in self.moves(synth(pad=-19.0), mix=mix) if x.kind == 'duck'])

    def test_other_part_over_the_lead(self):
        m = self.moves(synth(keys=-18.0))
        k = [x for x in m if x.node == 'keys']
        self.assertEqual(len(k), 1)
        self.assertLess(k[0].db, -4.0)

    def test_moves_are_bounded(self):
        m = self.moves(synth(drums=-5.0))
        d = [x for x in m if x.node == 'drums']
        self.assertEqual(d[0].db, -mixer.MAX_STEP)
        m = self.moves(synth(drums=-5.0), max_step=3.0)
        self.assertEqual([x for x in m if x.node == 'drums'][0].db, -3.0)

    def test_deterministic(self):
        rep = synth(lead=-20, drums=-18, pad=-18, keys=-17)
        self.assertEqual([str(x) for x in self.moves(rep)], [str(x) for x in self.moves(rep)])

    def test_jazz_drums_behind_the_piano(self):
        lv = {'piano': {'head': -20, 'solo': -20}, 'drums': {'head': -31, 'solo': -30.5}, 'bass': {'head': -24.5, 'solo': -24.5}}
        rep = report(lv, profile='jazz', sections=(('head', -15.0), ('solo', -14.5)),
                     roles={'piano': 'lead', 'drums': 'drums', 'bass': 'bass'})
        roles = mixer.infer_roles(report=rep)[0]
        m, _ = mixer.propose(rep, roles, mixer.get_profile('jazz'))
        d = {x.node: x.db for x in m if x.kind == 'trim'}
        self.assertLessEqual(d['drums'], -2.0)          # 10.5-11 dB under -> into 13-16
        self.assertNotIn('piano', d)
        self.assertFalse([x for x in m if x.kind == 'duck'])   # no pumping in jazz
        lv['drums'] = {'head': -34.5, 'solo': -34.5}
        self.assertEqual(mixer.propose(report(lv, profile='jazz', sections=(('head', -15.0), ('solo', -14.5)),
                                              roles={'piano': 'lead', 'drums': 'drums', 'bass': 'bass'}),
                                       roles, mixer.get_profile('jazz'))[0], [])

    def test_masking_with_the_lead_gets_a_dip_and_kick_bass_a_duck(self):
        w = [{'code': 'masking', 'nodes': ['lead', 'keys'], 'message': "'lead' and 'keys' both carry >35% of the mid band "
                                                                       "(800 Hz-2.5 kHz) in 'chorus': they mask each other."},
             {'code': 'masking', 'nodes': ['drums', 'bass'], 'message': "'drums' and 'bass' both carry >35% of the bass band "
                                                                        "(60-250 Hz) in 'chorus' (...): they overlap in time"}]
        m = self.moves(synth(warnings=w))
        eq = [x for x in m if x.kind == 'eq']
        self.assertEqual(eq[0].node, 'keys')
        self.assertEqual(eq[0].params['freq'], 1400.0)
        duck = [x for x in m if x.kind == 'duck']
        self.assertEqual(duck[0].params['targets'], ['bass'])
        self.assertEqual(duck[0].params['key'], 'drums')


def small_song() -> Song:
    s = Song('Mix Test', tempo=120, key='A minor', seed=3)
    verse = s.section('verse', bars=2)
    chorus = s.section('chorus', bars=2)
    s.hall()
    lead = s.track('lead', inst.va(), sends={'hall': -12})
    pad = s.track('pad', inst.va())
    lead.play(s.motif('1:1 3:1 5:1 8:1'), verse).play(s.motif('8:1 5:1 3:1 1:1'), chorus)
    pad.play(s.prog('i VI', bars=2).block(), 0)
    return s


class Apply(unittest.TestCase):
    MIX = {'trim': {'lead': 1.5, 'pad': -2.0}, 'ride': {'pad': {'chorus': -1.0}},
           'duck': [{'targets': ['pad'], 'key': 'lead', 'depth': 2.5, 'threshold': -34}],
           'eq': {'pad': [{'freq': 1400, 'gain': -2, 'q': 1.0}]}}

    def test_apply_writes_explicit_settings(self):
        s = small_song().mix(self.MIX)
        r = s.compile()
        tr = {t['id']: t for t in r['tracks']}
        lead_fx = tr['lead']['fx']
        self.assertEqual(lead_fx[-1], {'type': 'utility', 'params': {'gain': 1.5}})
        pad_fx = [f['type'] for f in tr['pad']['fx']]
        self.assertEqual(pad_fx, ['eq', 'ducker', 'utility'])
        self.assertEqual(tr['pad']['fx'][1]['sidechain'], 'lead')
        self.assertEqual(tr['pad']['fx'][0]['params']['peak1.gain'], -2.0)
        lane = next(a for a in tr['pad']['automation'] if a['target'] == 'fx.2.gain')
        self.assertEqual(lane['points'][0], [0.0, -2.0])
        self.assertEqual(lane['points'][-1], [8.0, -3.0])          # the chorus starts at beat 8
        self.assertEqual(lane['points'][-2], [7.0, -2.0])          # ramped over 1 beat before it
        self.assertEqual(s.applied_mix['trim'], {'lead': 1.5, 'pad': -2.0})

    def test_strict(self):
        with self.assertRaisesRegex(ComposeError, "unknown key"):
            small_song().mix({'trims': {}})
        with self.assertRaisesRegex(ComposeError, "did you mean lead"):
            small_song().mix({'trim': {'leed': 1}})
        with self.assertRaisesRegex(ComposeError, "no section 'chrous'"):
            small_song().mix({'ride': {'pad': {'chrous': -1}}})
        with self.assertRaisesRegex(ComposeError, "must be a number"):
            small_song().mix({'trim': {'pad': 'loud'}})
        with self.assertRaisesRegex(ComposeError, "unknown key"):
            small_song().mix({'duck': [{'targets': ['pad'], 'key': 'lead', 'dept': 3}]})
        with self.assertRaisesRegex(ComposeError, "already has a MIX"):
            small_song().mix({}).mix({})

    def test_song_with_gain_lane_keeps_it(self):
        s = small_song()
        s.tracks['lead'].automate('gainDb', [(0, -3), (8, 0, 'step')])
        r = s.mix({'trim': {'lead': 2.0}}).compile()
        lead = next(t for t in r['tracks'] if t['id'] == 'lead')
        self.assertEqual([a['target'] for a in lead['automation']], ['gainDb'])
        self.assertEqual(lead['fx'][-1]['params'], {'gain': 2.0})

    def test_merge_and_code(self):
        m = mixer.merge({'trim': {'a': 11.0}}, [mixer.Move('trim', 'a', 4.0), mixer.Move('ride', 'b', -1.0, 'x'),
                                                mixer.Move('ride', 'b', -0.5, 'x')])
        self.assertEqual(m['trim'], {'a': mixer.MAX_TRIM})
        self.assertEqual(m['ride'], {'b': {'x': -1.5}})
        code = mixer.to_code(m, ['pass 1: trim a'])
        ns = {}
        exec(code, ns)
        self.assertEqual(mixer.normalize(ns['MIX'])['trim'], {'a': 12.0})
        self.assertTrue(code.startswith('# pass 1: trim a'))
        self.assertIn('2 dB', mixer.describe_mix({'trim': {'a': 1}}) + ' 2 dB')


class Check(unittest.TestCase):
    def codes(self, rep, **kw):
        return [f.code for f in mixer.check(rep, **kw)]

    def test_lead_not_in_front(self):
        f = mixer.check(synth(lead=-20, drums=-18.5, bass=-18.5, pad=-18.5))
        self.assertEqual(f[0].code, 'lead_not_in_front')
        self.assertEqual(f[0].severity, 'warn')
        self.assertIn('lead', f[0].mix['trim'])

    def test_jazz_drums(self):
        lv = {'piano': {'head': -20}, 'drums': {'head': -30}, 'bass': {'head': -24.5}}
        rep = report(lv, profile='jazz', sections=(('head', -15.0),), roles={'piano': 'lead', 'drums': 'drums', 'bass': 'bass'})
        f = [x for x in mixer.check(rep) if x.code == 'drums_too_loud_for_jazz']
        self.assertEqual(len(f), 1)
        self.assertLess(f[0].mix['trim']['drums'], -2.5)

    def test_tone_and_space(self):
        third = [(200, 4.0), (250, 4.5), (315, 4.2), (400, 3.9), (2000, 3.0), (2500, 3.2), (3150, 3.1), (4000, 2.9),
                 (5000, 2.6), (8000, 0.0)]
        rep = synth(third=third, shares={'pad': {'lowmid': 40.0}, 'drums': {'presence': 45.0}})
        rep['space'].update({'issues': ['narrow'], 'widthAbove150HzPct': 22, 'correlationAbove150Hz': 0.8,
                             'opportunities': [{'id': 'pad', 'widener': 'chorus'}]})
        f = {x.code: x for x in mixer.check(rep)}
        self.assertEqual(f['mud'].severity, 'warn')
        self.assertEqual(f['mud'].mix['eq']['pad'][0]['freq'], 300.0)
        self.assertEqual(f['harsh'].severity, 'info')
        self.assertIn('drums', f['harsh'].mix['eq'])
        self.assertIn('pad (chorus)', f['width_narrow'].fix)

    def test_masking_findings(self):
        w = [{'code': 'masking', 'nodes': ['lead', 'keys'], 'sections': ['chorus'],
              'message': "'lead' and 'keys' both carry >35% of the presence band (2.5-5 kHz) in 'chorus'"},
             {'code': 'flat_dynamics', 'severity': 'warn', 'nodes': ['lead'], 'message': "'lead' has no played dynamics - x"}]
        f = {x.code: x for x in mixer.check(synth(warnings=w))}
        self.assertEqual(f['masking'].mix, {'eq': {'keys': [{'freq': 3300.0, 'gain': -2.0, 'q': 1.0}]}})
        self.assertIn('flat_dynamics', f)

    def test_plan_without_report(self):
        s = small_song()
        p = mixer.plan(s, hooks=['chorus'], profile='synthwave')
        kinds = sorted({m.kind for m in p.moves})
        self.assertEqual(kinds, ['duck', 'ride'])
        rides = {(m.node, m.section): m.db for m in p.moves if m.kind == 'ride'}
        self.assertEqual(rides[('lead', 'chorus')], 1.0)
        self.assertEqual(rides[('pad', 'verse')], -1.0)
        s.mix(p.mix()).compile()
        self.assertIn('targets vs the lead', p.describe())


def fake_renderer(base: dict):
    """A linear 'engine': each node's bar level = base + its MIX trim + section ride - 1.5 dB where a duck keyed by the
    lead acts; the report is rebuilt from that."""
    calls = []

    def render(song, mix, out, i):
        calls.append(i)
        m = mixer.normalize(mix)
        lv = {}
        for n, per in base.items():
            ducked = any(n in d['targets'] for d in m['duck'])
            lv[n] = {s: (None if v is None else v + m['trim'].get(n, 0.0) + m['ride'].get(n, {}).get(s, 0.0)
                         - (1.5 if ducked else 0.0)) for s, v in per.items()}
        return report(lv, roles=SYNTH_ROLES, peaks={'lead': -8.0})
    return render, calls


class Auto(unittest.TestCase):
    def test_converges_and_logs(self):
        base = {'lead': {'verse': -21, 'chorus': -20}, 'drums': {'verse': -20, 'chorus': -19.5},
                'bass': {'verse': -20, 'chorus': -19.5}, 'pad': {'verse': -19, 'chorus': -18.5},
                'keys': {'verse': -29, 'chorus': -28}}
        render, calls = fake_renderer(base)
        out = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mixer_'))
        self.addCleanup(shutil.rmtree, out, True)
        res = mixer.auto(small_song(), iterations=2, renderer=render, out=out)
        self.assertEqual(calls[:2], [0, 1])         # converged after one pass: nothing left to move
        self.assertIn('nothing to move', res.log[-1])
        after = next(b for b in res.after if b.name == 'chorus')
        p = mixer.get_profile('synthwave')
        for g in ('rhythm', 'low', 'bed'):
            lo, hi = p.window(g, True)
            self.assertTrue(lo - mixer.TOL <= after.rel[g] <= hi + mixer.TOL, (g, after.rel[g]))
        self.assertTrue(res.log and res.log[0].startswith('pass 1:'))
        self.assertTrue((out / 'MIX.py').is_file() and (out / 'log.txt').is_file())
        self.assertIn('chorus', res.table())
        self.assertEqual(res.mix['profile'], 'synthwave')
        # the MIX applies to the song as written
        small_song().mix({k: v for k, v in res.mix.items()}).compile()

    def test_stops_when_inside(self):
        render, calls = fake_renderer({'lead': {'verse': -20, 'chorus': -20}, 'drums': {'verse': -24, 'chorus': -23},
                                       'bass': {'verse': -24, 'chorus': -23}, 'pad': {'verse': -25, 'chorus': -24}})
        res = mixer.auto(small_song(), iterations=3, renderer=render, out=tempfile.mkdtemp(prefix='agentsound_mixer_'))
        self.assertEqual(calls, [0])
        self.assertIn('nothing to move', res.log[-1])
        self.assertEqual(mixer.normalize(res.mix)['trim'], {})


SONG = '''
from agentsound import *

ANALYSIS = {'profile': 'synthwave'}
MIX = {'trim': {'lead': -1.0}}

def build():
    s = Song('Mixer CLI', tempo=120, key='A minor', seed=5)
    verse = s.section('verse', bars=4)
    chorus = s.section('chorus', bars=4)
    s.hall()
    kit = s.track('drums', inst.drums(kit='synthwave'))
    bass = s.track('bass', inst.va(**{'osc1.wave': 'saw', 'sub.level': 0.6, 'cutoff': 500}))
    pad = s.track('pad', inst.va(unison=4, cutoff=1800, **{'amp.attack': 0.3, 'amp.release': 1.0}), sends={'hall': -8})
    lead = s.track('lead', inst.va(unison=2, cutoff=3000), gain_db=-16, sends={'hall': -14})
    beat = drums({'kick': 'x...x...x...x...', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'})
    prog = s.prog('i VI III VII')
    kit.loop(beat, verse, chorus)
    bass.loop(prog.bass('octave', rate='1/8'), verse, chorus)
    pad.loop(prog.block(register=('A3', 'A5')), verse, chorus)
    hook = s.motif('5:1/4 4:1/8 3:1/8 1:1/2 | 3:1/4 5:1/4 8:1/2 | 7:1/4 5:1/4 3:1/2 | 1:1')
    lead.loop(hook.clip(octave=5), verse, chorus)
    s.master.add(fx.limiter())
    return s
'''


def _run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main(argv)
    return code, out.getvalue(), err.getvalue()


class Cli(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mixcli_'))
        (self.dir / 'song.py').write_text(SONG, encoding='utf-8')
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_module_mix_applied_at_check(self):
        code, out, err = _run(['check', str(self.dir), '--engine', str(self.dir / 'missing.exe')])
        self.assertEqual(code, 0, err)
        self.assertIn('MIX (song.py): 1 trim, 0 rides, 0 ducks, 0 eq dips', out)
        rj = (self.dir / 'out' / 'song.render.json').read_text(encoding='utf-8')
        self.assertIn('"utility"', rj)


def _engine():
    try:
        return cli.find_engine(os.environ.get('AGENTSOUND_TEST_ENGINE'))
    except cli.CliError:
        return None


@unittest.skipIf(_engine() is None, 'engine not built (set AGENTSOUND_TEST_ENGINE or build build/agentsound.exe)')
class RealRender(unittest.TestCase):
    def test_auto_brings_a_buried_lead_forward(self):
        d = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_mixreal_'))
        self.addCleanup(shutil.rmtree, d, True)
        (d / 'song.py').write_text(SONG.replace("MIX = {'trim': {'lead': -1.0}}", "MIX = {}"), encoding='utf-8')
        res = mixer.auto(d, iterations=1, engine=str(_engine()), out=d / 'mixer')
        self.assertEqual(len(res.passes), 2)
        b0 = next(b for b in res.before if b.name == 'chorus')
        b1 = next(b for b in res.after if b.name == 'chorus')
        self.assertTrue(b0.judged and b1.judged, (b0.why, b1.why))
        self.assertEqual(b0.lead, 'lead')
        # the lead at -16 dB sits under the band; after one pass every group is further under it
        worst0 = max(b0.rel[g] - mixer.get_profile('synthwave').window(g)[1] for g in b0.rel if g in mixer.GROUPS)
        worst1 = max(b1.rel[g] - mixer.get_profile('synthwave').window(g)[1] for g in b1.rel if g in mixer.GROUPS)
        self.assertGreater(worst0, 1.0)
        self.assertLess(worst1, worst0 - 1.0)
        self.assertTrue(res.log)
        self.assertTrue((d / 'mixer' / 'MIX.py').is_file())
        self.assertTrue((d / 'mixer' / 'pass_1' / 'report.json').is_file())


if __name__ == '__main__':
    unittest.main()
