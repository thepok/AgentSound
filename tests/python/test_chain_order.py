"""Signal-chain order: taps (sends / sidechain keys / followers before the fader or the inserts), pre= inserts, the
chain-order warnings (agentsound.chain_order), the gated reverb keyed from the kit's snare by default, the hero chain
(air before echo, the bed keyed before the echo / ride with fader-following thresholds, the explicit echo bus, the
duplicate hall), the jazz / rock master guard, rock_band's split room and the hornist's mic stage before the
compressor. Compile-level checks (no render)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import Song, chain_order, fx, heroes, hornist, patches  # noqa: E402
from agentsound.bandlib.rock import installed  # noqa: E402
from agentsound.modulation import follow  # noqa: E402
from agentsound.patches import FX, inst  # noqa: E402
from agentsound.theory import ComposeError  # noqa: E402


def _song():
    s = Song('chain order', tempo=120, seed=3)
    s.section('a', bars=2)
    return s


def _node(render, nid):
    return next(n for n in render['tracks'] + render['buses'] if n['id'] == nid)


def _orders(s):
    return [w for w in s.warnings if w.startswith('chain order')]


class Taps(unittest.TestCase):
    def test_send_taps_compile_to_db_tap_objects(self):
        s = _song()
        crush = s.bus('crush', [fx.compressor(threshold=-30, ratio=8)])
        hall = s.hall()
        t = s.track('lead', inst.va(), fx=[fx.eq({'hp.freq': 100}, name='tone'), fx.chorus(mix=0.3)],
                    sends={crush: (-6, 'prefader'), hall: -12})
        e = s.echo()
        t.send(e, -14, tap='pre:chorus')
        t.note(60, 0, 2)
        r = s.compile()
        sends = _node(r, 'lead')['sends']
        self.assertEqual(sends['crush'], {'db': -6.0, 'tap': 'prefader'})
        self.assertEqual(sends['hall'], -12.0)                       # post: a plain number (render-identical)
        self.assertEqual(sends['echo'], {'db': -14.0, 'tap': 'pre:1'})
        t.send(e, -14, tap='pre:tone')                                # the first insert: = prefx
        self.assertEqual(_node(s.compile(), 'lead')['sends']['echo'], {'db': -14.0, 'tap': 'prefx'})
        t.send(e, -14)                                                # back to post-fader
        self.assertEqual(_node(s.compile(), 'lead')['sends']['echo'], -14.0)

    def test_bad_taps(self):
        s = _song()
        b = s.bus('b')
        with self.assertRaises(ComposeError):
            s.track('x', inst.va(), sends={b: (-6, 'pre-fader')})
        with self.assertRaises(ComposeError):
            s.track('y', inst.va(), sends={b: (-6, 'prefader', 1)})
        t = s.track('z', inst.va(), sends={b: (-6, 'pre:nothing')})
        t.note(60, 0, 1)
        with self.assertRaisesRegex(ComposeError, "no insert named or of type 'nothing'"):
            s.compile()
        with self.assertRaises(ComposeError):
            FX('ducker', tap='sideways')

    def test_keys_and_followers(self):
        s = _song()
        lead = s.track('lead', inst.va(), fx=[fx.compressor(name='comp'), fx.delay(mix=0.3, name='echo')])
        pad = s.track('pad', inst.va())
        s.sidechain(pad, key=lead, tap='pre:echo', depth=3)
        s.carve(pad, key=lead, tap='prefader')
        pad.modulate('instrument.cutoff', follow(lead, tap='prefx', min=300, max=3000))
        for t in (lead, pad):
            t.note(60, 0, 4)
        r = s.compile()
        fxs = _node(r, 'pad')['fx']
        self.assertEqual((fxs[0]['sidechain'], fxs[0]['tap']), ('lead', 'pre:1'))
        self.assertEqual(fxs[1]['tap'], 'prefader')
        self.assertEqual(_node(r, 'pad')['modulators'][0]['source']['tap'], 'prefx')
        # the default writes no tap at all
        s2 = _song()
        a, b2 = s2.track('a', inst.va()), s2.track('b', inst.va())
        s2.sidechain(b2, key=a)
        a.note(60, 0, 1)
        b2.note(60, 0, 1)
        self.assertNotIn('tap', _node(s2.compile(), 'b')['fx'][0])

    def test_tap_without_sidechain_is_an_error(self):
        s = _song()
        t = s.track('t', inst.va(), fx=[FX('eq', tap='prefx')])
        t.note(60, 0, 1)
        with self.assertRaisesRegex(ComposeError, 'no sidechain key to tap'):
            s.compile()

    def test_pre_inserts_go_in_front_of_the_patch(self):
        s = _song()
        t = s.track('lead', 'synthwave/sync_lead', pre=[fx.saturator(drive=6)], fx=[fx.eq({'hp.freq': 200})])
        self.assertEqual([f.type for f in t.fx], ['saturator'] + [f.type for f in patches.get('synthwave/sync_lead').fx]
                         + ['eq'])


class Warnings(unittest.TestCase):
    def _warn(self, chain, kind='track', **kw):
        s = _song()
        if kind == 'track':
            n = s.track('n', inst.va(), fx=chain, **kw)
            n.note(60, 0, 1)
        else:
            src = s.track('src', inst.va())
            n = s.bus('n', chain)
            src.send(n, -6)
            src.note(60, 0, 1)
        s.compile()
        return _orders(s), n

    def test_nonlinear_after_modulation_warns(self):
        w, _ = self._warn([fx.chorus(mix=0.3), fx.saturator(drive=6)])
        self.assertEqual(len(w), 1)
        self.assertIn("after chorus", w[0])
        w, _ = self._warn([fx.delay(mix=0.2), fx.compressor()])
        self.assertIn('repeats / tails', w[0])

    def test_correct_orders_are_quiet(self):
        self.assertEqual(self._warn([fx.saturator(drive=6), fx.chorus(mix=0.3)])[0], [])
        self.assertEqual(self._warn([fx.chorus(mix=0.3), fx.eq({'hp.freq': 100}), fx.width(width=1.2)])[0], [])
        # a return: the 100 %-wet delay then tape (bus/tape_echo), a room then its crush
        self.assertEqual(self._warn([fx.delay(mix=1.0), fx.tape(drive=6)], kind='bus')[0], [])
        self.assertEqual(self._warn([fx.reverb(mix=1.0), fx.compressor(ratio=6)], kind='bus')[0], [])
        # a keyed compressor after a chorus is a duck, not a level-dependent stage
        s = _song()
        k = s.track('k', inst.va())
        t = s.track('t', inst.va(), fx=[fx.chorus(mix=0.3), FX('compressor', sidechain=k)])
        k.note(60, 0, 1)
        t.note(60, 0, 1)
        s.compile()
        self.assertEqual(_orders(s), [])
        # a cabinet IR (a fully wet convolver on a track) then a compressor
        self.assertFalse(chain_order._time(FX('convolver', {'ir': 'x.wav', 'mix': 1.0}), 'track'))
        # tape without drive is not a saturation stage
        self.assertEqual(self._warn([fx.chorus(mix=0.3), fx.tape(drive=0)])[0], [])

    def test_allow_order_silences(self):
        s = _song()
        t = s.track('t', inst.va(), fx=[fx.chorus(mix=0.3), fx.saturator(drive=6)])
        t.note(60, 0, 1)
        t.allow_order('a chorused fuzz on purpose')
        s.compile()
        self.assertEqual(_orders(s), [])
        with self.assertRaises(ComposeError):
            t.allow_order('')

    def test_master_after_limiter_and_two_limiters(self):
        s = _song()
        t = s.track('t', inst.va())
        t.note(60, 0, 1)
        s.master.add(fx.limiter(), fx.utility(gain=-0.5))
        s.compile()
        self.assertEqual(_orders(s), [])
        s.master.add(fx.eq({'high.gain': 2}))
        s.compile()
        self.assertTrue(any('after the last limiter' in w for w in _orders(s)))
        s.master.add(fx.limiter())
        s.compile()
        self.assertTrue(any('2 limiters' in w for w in _orders(s)))

    def test_library_is_clean(self):
        """Every library patch: no chain-order finding (the intended exceptions are in chain_order.ALLOW)."""
        s = _song()
        bad = []
        for i, name in enumerate(patches.list()):
            p = patches.get(name)
            try:
                node = s.track(f't{i}', p) if p.instrument is not None else s.bus(f'b{i}', p)
            except ComposeError:
                continue
            if name.startswith('master/'):
                bad += [f"{name}: {m}" for m in chain_order.master_findings(node)]
            else:
                bad += [f"{name}: {m}" for m in chain_order.findings(node)]
        self.assertEqual(bad, [])

    def test_fixed_patches(self):
        self.assertEqual([f.type for f in patches.get('synthwave/brass_lead').fx], ['saturator', 'chorus', 'microshift'])
        organ = [f.name or f.type for f in patches.get('hero/organ').fx]
        self.assertLess(organ.index('drive'), organ.index('leslie'))
        self.assertLess(organ.index('comp'), organ.index('leslie'))
        dark = patches.get('hero/darksynth')
        sync = next(x for x in dark.instrument.params['layers'] if x.id == 'sync')
        self.assertNotIn('microshift', [f.type for f in sync.fx])


class GatedKey(unittest.TestCase):
    def _kit_song(self, **gated):
        s = _song()
        kit = s.track('drums', 'synthwave/drums_outrun')
        kit.note(36, 0, 0.25)
        kit.note(38, 1, 0.25)
        kit.note(42, 0.5, 0.25)
        g = s.gated(**gated)
        return s, kit, g

    def test_kit_patch_send_keys_the_gate_from_its_snare(self):
        s, kit, g = self._kit_song()
        r = s.compile()
        gate = next(f for f in _node(r, 'gated')['fx'] if f['type'] == 'gatedreverb')
        key = _node(r, gate['sidechain'])
        self.assertTrue(key['mute'])
        self.assertEqual({n[2] for n in key['notes']}, {38})

    def test_opt_outs(self):
        s, kit, g = self._kit_song(key=False)
        r = s.compile()
        self.assertNotIn('sidechain', next(f for f in _node(r, 'gated')['fx'] if f['type'] == 'gatedreverb'))
        s, kit, g = self._kit_song()
        kit.automate('send.gated', [(0, -60), (1, -6)])          # a song-written throw gates what it sends
        r = s.compile()
        self.assertNotIn('sidechain', next(f for f in _node(r, 'gated')['fx'] if f['type'] == 'gatedreverb'))

    def test_kit_plate_sends_are_light(self):
        self.assertLessEqual(patches.get('synthwave/drums_linn').sends['plate'], -16)
        self.assertLessEqual(patches.get('synthwave/drums_808').sends['plate'], -18)


class Heroes(unittest.TestCase):
    def test_air_before_echo(self):
        self.assertLess(heroes.ORDER.index('air'), heroes.ORDER.index('echo'))
        self.assertEqual(heroes.air_order({}, ('drive', 'tone', 'air', 'comp'))[-1], 'air')
        st = heroes.air_order({}, heroes.ORDER)
        self.assertEqual(st[st.index('air') + 1], 'echo')

    def test_bed_keyed_before_air_with_fader_following_thresholds(self):
        if not installed('salamander-grand'):
            self.skipTest('salamander-grand not installed')
        s = _song()
        pad = s.track('pad', inst.va())
        lead = heroes.hero(s.track('lead', 'hero/piano_pop', gain_db=-4.0), bed=[pad])
        pad.note(48, 0, 8)
        lead.note(72, 0, 2)
        r = s.compile()
        keyed = [f for f in _node(r, 'pad')['fx'] if f.get('sidechain') == 'lead']
        self.assertEqual(len(keyed), 2)                       # the duck and the carve
        chain = [f.name or f.type for f in lead.fx]
        self.assertEqual({f['tap'] for f in keyed}, {f"pre:{chain.index('air')}"})
        duck = next(f for f in keyed if f['type'] == 'ducker')
        self.assertAlmostEqual(duck['params']['threshold'],
                               lead.hero.preset.mix_value('duck_threshold') - lead.gain_db, places=3)
        lead.gain_db -= 3.0                                   # the fader moves after hero(): the threshold follows
        duck2 = next(f for f in _node(s.compile(), 'pad')['fx'] if f['type'] == 'ducker')
        self.assertAlmostEqual(duck2['params']['threshold'] - duck['params']['threshold'], 3.0, places=3)

    def test_echo_bus_is_explicit(self):
        s = _song()
        s.bus('pre_delay_hall', [fx.reverb(mix=1.0, predelay=80)])
        self.assertEqual(heroes._echo_bus(s, None), ('echo', True))
        self.assertEqual(heroes._echo_bus(s, None), ('echo', False))

    def test_quieter_hall_dropped_next_to_the_plate(self):
        s = _song()
        s.hall()
        sax = heroes.hero(s.track('sax', inst.va()), family='sax')
        self.assertNotIn('hall', sax._patch_sends)
        self.assertTrue(any('hall send' in x for x in sax.hero.log))
        s2 = _song()
        s2.hall()
        vln = heroes.hero(s2.track('vln', inst.va()), family='strings')   # hall -9 over plate -16: its room
        self.assertIn('hall', vln._patch_sends)


class Bands(unittest.TestCase):
    def test_jazz_master_width_after_tape_and_guarded(self):
        from agentsound import bands
        s = _song()
        bands.make('jazz_trio', s)
        types = [f.type for f in s.master.fx]
        self.assertEqual(types, ['eq', 'compressor', 'tape', 'width', 'limiter'])
        s2 = _song()
        s2.master.add(fx.limiter())
        b = bands.make('jazz_trio', s2)
        self.assertEqual([f.type for f in s2.master.fx], ['limiter'])
        self.assertIsNone(b.info['master_gain'])

    def test_rock_band_room_split(self):
        from agentsound import bands
        s = _song()
        b = bands.make('rock_band', s)
        self.assertIn('drum_room', s.buses)
        self.assertEqual(set(b.drums.sends), {'drum_room', 'plate'})
        room = [f.type for f in s.buses['room'].fx]
        self.assertNotIn('compressor', room)
        self.assertIn('compressor', [f.type for f in s.buses['drum_room'].fx])
        if room[0] == 'convolver':
            self.assertEqual(s.buses['room'].fx[0].params['crossfeed'], 0.5)
        for role in ('bass', 'gtr_l', 'gtr_r', 'lead', 'keys'):
            self.assertNotIn('drum_room', getattr(b, role).sends)

    def test_darksynth_drives_first(self):
        from agentsound import bands
        s = _song()
        b = bands.make('darksynth', s)
        self.assertEqual(b.lead.fx[0].type, 'saturator')
        self.assertEqual(b.stab.fx[0].type, 'saturator')


class Hornist(unittest.TestCase):
    def test_mic_stage_before_the_compressor(self):
        s = _song()
        t = s.track('sax', inst.va(), fx=[fx.eq({'hp.freq': 100}), fx.compressor(threshold=-20, name='comp'),
                                          fx.delay(mix=0.2, name='echo')])
        hornist.mic_stage(t)
        names = [f.name or f.type for f in t.fx]
        self.assertEqual(names.index('mic') + 1, names.index('comp'))
        st, p = hornist.air_stage(t)
        names = [f.name or f.type for f in t.fx]
        self.assertTrue(names.index('comp') < names.index('air') < names.index('echo'))
        s2 = _song()
        t2 = s2.track('fl', inst.va())
        hornist.mic_stage(t2)
        self.assertEqual(t2.fx[-1].name, 'mic')            # no compressor: appended


if __name__ == '__main__':
    unittest.main()
