"""Sockenkrieg (Theme) - 32-second background cue for an absurd sci-fi cartoon sketch.

Mad-scientist grandpa + nervous grandson, a washing-machine portal, the sock dimension, the Sock King, fabric
softener. Quirky retro sci-fi cartoon theme: a wobbly theremin-ish mono lead (sine + detuned triangle, glide,
wide vibrato, tape drift), a bouncy plucked synth bass, light 808 drums, a soft spooky organ bed.

120 BPM, D minor, 16 bars = exactly 32.0 s (tail 0):
  hit    bar 1       (0-2 s)    intro hit at 0.0 s (orchestra hit + boom + crash), theremin swoop in
  groove bars 2-14   (2-28 s)   steady groove, sparse lead, mids kept open for dialogue
  sting  bars 15-16  (28-32 s)  dramatic stinger chord at 28.0 s, decays to silence by 32 s

Build: python -m agentsound build songs/sockenkrieg-theme
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Sockenkrieg (Theme)', 'artist': 'AgentSound', 'genre': 'Soundtrack', 'year': 2026,
            'comment': 'cartoon sci-fi cue, 120 BPM, D minor, 32 s'}
ANALYSIS = {'profile': 'synthwave'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'SOCKENKRIEG', 'subtitle': 'AgentSound', 'seed': 3}

# 4-bar spooky-goofy loop: Dm | Dm | Eb (bII, the wobbly one) | A7
PROG = ['Dm', 'Dm', 'Eb', 'A7']
ROOTS = {'Dm': 38, 'Eb': 39, 'A7': 33}        # D2, Eb2, A1


def bass_bar(sym, bar_start):
    """Bouncy octave pluck: root, octave, root on the 'and', fifth/octave pickups."""
    r = ROOTS[sym]
    fifth = r + 7
    pat = [(0.0, 0.4, r, 104), (0.5, 0.3, r + 12, 84), (1.0, 0.4, r, 96), (1.75, 0.25, r, 80),
           (2.0, 0.4, fifth, 98), (2.5, 0.3, r + 12, 84), (3.0, 0.4, r, 96), (3.5, 0.3, fifth, 86)]
    return [(bar_start + t, d, p, v) for t, d, p, v in pat]


def theremin():
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.6,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def build() -> Song:
    s = Song('Sockenkrieg (Theme)', tempo=120, key='D minor', seed=3, tail=0.0)
    hit = s.section('hit', bars=1)
    groove = s.section('groove', bars=13)
    sting = s.section('sting', bars=2)

    s.hall(), s.plate(), s.echo()
    s.master.use('master/synthwave')

    kit = s.track('drums', 'synthwave/drums_808', gain_db=-1,
                  fx=[fx.eq({'low.freq': 60, 'low.gain': -4})]).humanize(2, 4)
    bass = s.track('bass', 'synthwave/pluck_bass', gain_db=0)
    organ = s.track('organ', 'synthwave/organ', gain_db=-6, pan=-0.25,
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.6})])
    lead = s.track('theremin', theremin(), gain_db=-2, pan=0.1, sends={'hall': -9, 'echo': -12},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    zap = s.track('zap', 'synthwave/laser', gain_db=-16, pan=0.4)
    stab = s.track('stab', 'synthwave/brass_stab', gain_db=-3)
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-3)
    boom = s.track('boom', 'synthwave/impact', gain_db=-6)

    # ---------------------------------------------------------------- intro hit (0.0 s)
    kit.play(drums({'kick': 'X', 'crash': 'X'}, bars=1), hit.start)
    ohit.play(Clip([(0, 1.5, 50, 118), (0, 1.5, 57, 118), (0, 1.5, 62, 118)], length=4), hit.start)
    boom.play(Clip([(0, 2.0, 38, 120)], length=4), hit.start)
    stab.play(Clip([(0, 0.6, p, 112) for p in (50, 57, 62, 65)], length=4), hit.start)
    # spooky theremin swoop up into the groove
    lead.play(Clip([(1.0, 1.0, 62, 80), (2.0, 1.0, 74, 88), (3.0, 1.0, 69, 84)], length=4), hit.start)

    # ---------------------------------------------------------------- groove (2-28 s)
    groove_bars = 13
    bnotes, onotes = [], []
    for b in range(groove_bars):
        sym = PROG[b % 4]
        bnotes += bass_bar(sym, b * 4.0)
        tones = chord(sym).notes(4)                      # organ: short off-beat 'boop' chords, low and quiet
        tones = [t - 12 if t > 69 else t for t in tones][:3]
        for off in (1.5, 3.5):
            onotes += [(b * 4.0 + off, 0.35, t, 70) for t in tones]
    bass.play(Clip(bnotes, length=groove_bars * 4.0), groove.start)
    organ.play(Clip(onotes, length=groove_bars * 4.0), groove.start)

    beat = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...',
                  'hat': 'x.o.x.o.x.o.x.o.', 'cowbell': '..............o.'}, vel=78)
    beat_b = drums({'kick': 'x.....x.x.....x.', 'snare': '....x.......x.o.',
                    'hat': 'x.o.x.o.x.o.x.ox', 'clap': '............x...'}, vel=80)
    for b in range(groove_bars):
        kit.play(beat_b if b % 4 == 3 else beat, groove.start + b * 4.0)

    # theremin melody: sparse, high, long notes with slides (4-bar phrases, call / answer)
    A = 'D5/2 F5/4 E5/8 D5/8 | A5/2. r/4 | Bb5/4 A5/4 G5/4 Bb5/4 | A5/1'
    B = 'r/4 A5/4 C6/4 A5/4 | D6/2. r/4 | Eb6/4 D6/8 C6/8 Bb5/4 G5/4 | A5/2 C#5/2'
    C = 'D5/2 A5/2 | F5/4 E5/4 D5/2 | Eb5/2 G5/4 Bb5/4 | A5/2. r/4 | A4/1'
    mel = notes(f'vel=86 {A} | {B} | {C}').arch(4, 0.35)          # velocity arc per 4-bar phrase
    lead.play(mel, groove.start)

    # sci-fi garnish: the odd 'pew' at phrase ends
    for bar in (3, 7, 11):
        zap.play(Clip([(0, 0.25, 84, 80), (0.5, 0.25, 88, 70)], length=1), groove.start + bar * 4.0 + 3.0)

    # ---------------------------------------------------------------- stinger (28.0 s)
    t = sting.start
    kit.play(drums({'kick': 'X', 'crash': 'X', 'tom_lo': 'X'}, bars=1), t)
    kit.play(drums({'snare': '..........xxXX', 'tom_lo': '............X.'}, bars=1, vel=70), t - 4.0 + 0.0)
    ohit.play(Clip([(0, 5.0, p, 124) for p in (38, 50, 57, 62)], length=8), t)
    boom.play(Clip([(0, 7.0, 38, 127)], length=8), t)
    stab.play(Clip([(0, 6.5, p, 120) for p in (50, 53, 57, 62, 65)], length=8), t)
    bass.play(Clip([(0, 6.0, 26, 120), (0, 6.0, 38, 110)], length=8), t)
    lead.play(Clip([(0, 0.5, 62, 96), (0.5, 6.5, 86, 100)], length=8), t)     # theremin shriek up to D7
    lead.automate('gainDb', ramp(t + 2.0, t + 8.0, 0, -30))
    s.master.automate('gainDb', hold(0, t + 2.5, 0), ramp(t + 2.5, t + 8.0, 0, -42))   # natural decay to ~silence at 32 s
    return s
