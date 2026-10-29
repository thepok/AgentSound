"""Afterglow Express - original instrumental outrun/nightdrive, 110 BPM, D minor.
96 bars: a dusk departure, two neon-lit hooks, quiet tunnel, final open-road lift.
Build: python -m agentsound build songs/afterglow-express
"""
from agentsound import *


def build() -> Song:
    s = Song('Afterglow Express', tempo=110, key='D minor', seed=928, tail=10)
    intro = s.section('departure', 8)
    verse = s.section('city_lights', 16)
    pre = s.section('acceleration', 4)
    chorus = s.section('open_road', 16)
    verse2 = s.section('passing_signals', 8)
    pre2 = s.section('overpass', 4)
    chorus2 = s.section('neon_horizon', 16)
    bridge = s.section('tunnel', 8)
    final = s.section('afterglow', 12)
    outro = s.section('arrival', 4)

    pv = s.prog('Dm9 Bbmaj7 Fadd9 C')
    pc = s.prog('Bbadd9 C Dm Dm Bb C F A7')
    pp = s.prog('Gm Bb Asus4 A')
    pb = s.prog('Bbmaj7:2 Cadd9:2 Dm9:2 Gadd9 A7')
    po = s.prog('Bb C Dm:2')
    form = [(intro, pv), (verse, pv), (pre, pp), (chorus, pc),
            (verse2, pv), (pre2, pp), (chorus2, pc), (bridge, pb),
            (final, pc + s.prog('Bb C Dm:2')), (outro, po)]

    # Eight-bar melody: repeated syncopation, rising answer, harmonic-minor cadence.
    hook = s.motif(
        '5:1/8 8:1/4 7:1/8 5:1/4 3:1/4 | '
        '4:1/4. 5:1/8 7:1/4 9:1/4 | '
        '8:1/2. 5:1/8 7:1/8 | 8:1/2 r:1/4 3:1/8 5:1/8 | '
        '6:1/4 8:1/4 10:1/4. 8:1/8 | '
        '9:1/2 7:1/4 5:1/4 | '
        '10:1/4. 9:1/8 8:1/4 5:1/4 | '
        '#7:1/2 5:1/4 r:1/4').clip(octave=4, vel=101)
    verse_line = s.motif(
        'r:1/2 5:1/8 3:1/8 2:1/4 | 3:1/2. r:1/4 | '
        'r:1/4 5:1/4 7:1/4 5:1/4 | 4:1/2 r:1/2').clip(octave=4, vel=84)

    hall = s.hall(decay=4.8, predelay=38, size=0.95, diffusion=0.94,
                  moddepth=0.72, modrate=0.38, damping=7800, lowcut=280, width=1.0)
    hall.gain_db = -2
    hall.add_fx(fx.eq(**{'peak1.freq': 400, 'peak1.gain': -2, 'peak1.q': 0.7}))
    plate = s.plate(decay=2.6, predelay=26, moddepth=0.6, width=1.1)
    echo = s.echo(time=0.75, feedback=0.43, highcut=6500, width=1.1)
    wide = s.bus('wide', 'bus/wide')
    bloom = s.bus('bloom', [fx.delay(mode='stereo', time=1.0, offset=3, feedback=0.28,
                       lowcut=300, highcut=5500, wow=0.12, mix=1),
                       fx.reverb(type='hall', decay=3.8, predelay=0, moddepth=0.7,
                                 diffusion=0.95, lowcut=300, mix=0.5)])
    gatebus = s.gated(gain_db=-5, hold=85, release=25, decay=0.5,
                      flat=0, tone=0.42, width=0.7, threshold=-12)
    music = s.bus('music', 'bus/music', gain_db=-2)
    dbus = s.bus('drumbus', 'bus/drums', gain_db=-3)
    kitpatch = patches.get('synthwave/drums_linn').but_fx('eq', **{'lp.freq': 17000})
    kit = s.track('kit', kitpatch, output=dbus)
    snarepatch = kitpatch.but(snare__decay=0.20, snare__noisedecay=0.55,
        snare__bodydecay=0.75, snare__tone=0.9, snare__snappy=0.38,
        snare__lpf=8500, clap__decay=0.08, clap__spread=5,
        clap__bursts=3, clap__level=-8, clap__tone=0.4)
    snare = s.track('snare', snarepatch, output=dbus, gain_db=1,
                    sends={gatebus: -9, plate: -22}).groove('laidback').humanize(2, 3)
    s.gated(key=snare, pitches='snare')
    bass = s.track('bass', 'synthwave/octave_bass', output=music, gain_db=0)
    pad_sound = patches.get('synthwave/warm_pad').but(
        unison=4, unison__detune=0.46, unison__spread=0.95,
        amp__attack=0.3, amp__release=2.5, hpf=100).but_fx('eq', **{'peak1.gain': -1.5})
    pad = s.track('pad', pad_sound, output=music, gain_db=-3,
                  sends={hall: -2, wide: -10}, fx=[fx.width(width=1.2, monobass=160)])
    arp_sound = patches.get('synthwave/arp_pluck').but(
        amp__decay=0.48, amp__release=0.25, fenv__decay=0.23, cutoff=900)
    arp = s.track('arp', arp_sound, output=music, gain_db=-6, pan=0.18,
                  sends={echo: -4, hall: -8, wide: -8},
                  fx=[fx.eq(**{'hp.freq': 220, 'hp.slope': 12})])
    keys = s.track('keys', 'synthwave/epiano', output=music, gain_db=-3, pan=-0.2,
                   sends={plate: -6, bloom: -10})
    # Smooth seven-voice saw stack: remove the old pulse timbre and octave fizz.
    lead_sound = patches.get('synthwave/supersaw_lead').but(
        osc2__semi=0, osc2__level=0.65, osc2__fine=-9, cutoff=3400,
        unison__detune=0.64, unison__spread=0.75, hpf=100,
        amp__attack=0.018, amp__release=0.6, lfo1__pitch=8,
        lfo1__delay=0.45, lfo1__fade=0.5).with_fx(
            fx.chorus(mode='custom', rate=0.32, depth=1.4, delay=16,
                      voices=3, spread=1, mix=0.28))
    lead = s.track('lead', lead_sound, output=music, gain_db=-1.5,
                   sends={hall: -5, echo: -7, wide: -7, bloom: -12}).humanize(3, 4)
    soar = s.track('soar', 'synthwave/brass_lead', output=music, gain_db=-8,
                   sends={hall: -5, wide: -8})
    glass = s.track('glass', 'synthwave/epiano', output=music, gain_db=-3, pan=-0.2,
                    sends={plate: -5, hall: -8, bloom: -7})
    strings = s.track('strings', 'synthwave/jupiter_strings', output=music, gain_db=-3,
                      sends={hall: -3, wide: -9})
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-8)
    down = s.track('down', 'synthwave/downlifter', gain_db=-5)

    kickhat = drums({'kick': 'x...x...x...x...', 'hat': 'o.X.o.X.o.X.o.X.'})
    full = drums({'kick': 'x...x...x...x...', 'hat': 'xoXoxoXoxoXoxo..', 'ohh': '..............x.'})
    backbeat = drums({'snare': '....X.......X...'})
    bigsnare = drums({'snare': '....X.......X...', 'clap': '....x.......x...'})
    for sec, prog in form:
        pad.loop(prog.block(register=('D3', 'D5'), voices=4), sec)
        if sec not in (intro, bridge, outro):
            bass.loop(prog.bass('octave', rate='1/8'), sec)
            kit.loop(full if sec in (chorus, chorus2, final) else kickhat, sec)
            snare.loop(bigsnare if sec in (chorus, chorus2, final) else backbeat, sec)
        if sec != bridge:
            arp.loop(prog.arp('updown' if sec != verse2 else 'downup', rate='1/16',
                              register=('D4', 'D5'), octaves=1, vel=80), sec)

    kit.loop(drums({'hat': '..o...x...o...x.'}), intro.bar(4), bars=4)
    glass.play(hook.slice(0, 8).velocity(0.75), intro.bar(4))
    keys.loop(pv.block(register=('F4', 'F5'), rhythm='x..x..x.', voices=3), verse, verse2)
    lead.play(verse_line, verse.bar(4)).play(verse_line.transpose_scale(2, s.key).fit(pv, s.key), verse.bar(12))
    glass.loop(pv.arp('up', rate='1/8', register=('D4', 'D5'), vel=82), verse2)
    lead.play(verse_line.transpose_scale(2, s.key).fit(pv, s.key), verse2.bar(4))

    for sec in (chorus, chorus2):
        lead.loop(hook, sec)
        keys.loop(pc.block(register=('F4', 'F5'), rhythm='..x...x.', voices=3), sec)
        kit.play(crash(), sec)
        kit.play(tom_fill(2), sec.beat(-2), replace=True)
        down.note('D3', sec.start, 4, 88)
    soar.play(hook, chorus2.bar(8), vel=0.85)
    strings.loop(pc.block(register=('A3', 'A5'), voices=3), chorus, chorus2)
    kit.loop(drums({'tamb': '..o...x...o...x.'}), chorus2.bar(8), bars=8)

    for sec in (pre, pre2):
        bass.clear(sec.bar(-1), sec.end)
        kit.clear(sec.bar(-1), sec.end)
        snare.play(snare_roll(3, build=True, vel=(45, 105)), sec.bar(-1), replace=True)
        snare.clear(sec.beat(-1), sec.end)
        riser_t.note('D4', sec.start, sec.length-1, 95)
        riser_t.automate('instrument.cutoff', exp_ramp(sec.start, sec.end-1, 300, 10000))
    # A quieter sustained bed keeps the breakdown lush underneath the piano.
    pad.automate('gainDb', per_section({intro: -3, bridge: -6, final: -3}, glide=2))
    keys.play(pb.block(register=('F3', 'D5'), voices=4).strum(ms=24, bpm=110), bridge)
    glass.play(hook.slice(0, 16).stretch(2).velocity(0.8), bridge)
    down.note('D3', bridge.start, 6, 82)
    kit.play(tom_fill(3), bridge.beat(-3))
    lead.loop(hook, final, bars=8)
    ending = s.motif('6:1/4 8:1/4 10:1/2 | 9:1/4 7:1/4 5:1/2 | 8:4 _:4').clip(octave=4, vel=106)
    lead.play(ending, final.bar(8))
    soar.play(hook, final).play(ending, final.bar(8))
    strings.loop((pc + s.prog('Bb C Dm:2')).block(register=('A3', 'A5'), voices=3), final)
    kit.loop(drums({'tamb': '..x...x...x...x.'}), final)
    kit.play(crash(), final).play(tom_fill(2), final.beat(-2), replace=True)
    # The outro returns to pad and glass alone, leaving the low mids open.
    glass.play(ending.velocity(0.7), outro)
    bass.note('D2', outro.bar(2), 7.5, 80)
    arp.clear(outro.bar(2), outro.end)

    s.sidechain(pad, arp, strings, key=kit, pitches='kick', depth=4.5, release=210)
    s.sidechain(bass, key=kit, pitches='kick', depth=14, hold=25, release=240, curve=0.25)
    pad.automate('instrument.cutoff', exp_ramp(0, intro.end, 500, 2300),
                 exp_ramp(bridge.start, bridge.bar(4), 2300, 900),
                 exp_ramp(bridge.bar(4), final.start, 900, 3000),
                 exp_ramp(outro.start, outro.end, 3000, 500))
    for node, base in ((music, -2), (dbus, -3)):
        node.automate('gainDb', per_section({intro: base-3, verse: base-2, pre: base-1.5,
            chorus: base+0.5, verse2: base-2, pre2: base-1, chorus2: base+0.5,
            bridge: base-3, final: base+1, outro: base-3}, glide=0.2))
    for sec in (chorus, chorus2, final):
        for bar in range(3, int(sec.bars), 4):
            at = sec.bar(bar)
            lead.automate('send.bloom', [(at, -12), (at + 1.5, -3, 'smooth'),
                                        (at + 3.9, -12, 'smooth')])
    s.master.use(patches.get('master/synthwave').but_fx('limiter', gain=3.4).but_fx('width', width=1.05))
    s.master.automate('gainDb', fade(0, 4, -20, 0), fade(outro.bar(2), outro.end + 6, 0, -26))
    return s
