"""Grandpa Konrad & Timo - Title Theme (20.0 s) for the cartoon's cold-open title montage (D:/Projekte/cartoon/intro).

Spooky-adventurous sci-fi cartoon theme: an eerie theremin over a dark drone, then driving drums and the bouncy
series bass under the series theme (THEME_A / THEME_B of songs/operation-no-wifi-3min, the Sockenkrieg phrase),
the Smog Monster's chromatic brass motif (songs/the-smog-monster, moved to D minor) on the monster shot, orchestra
stabs on every gross-up flash, a snare-roll vortex into the title hit, a stop for Konrad's burp, a button.
Original composition (no quotes of any other show's theme).

Picture grid (intro/shots.py): 144 BPM, 4/4, 12 bars = exactly 20.0 s, one beat = 0.41667 s:
  intro   bars 1-2   beats  0- 8   portal / laundry / living room / garden (cuts on beats 2, 4, 6): drone,
                                   theremin hook, ticking pulse, a riser into the hit
  drive   bars 3-10  beats  8-40   HIT on Konrad (beat 8), driving groove + theme; stabs on the gross-up cuts
                                   (beats 10, 15, 20, 23, 31, 34, 36), Oma's stomps (16, 17), the monster hit +
                                   smog motif (28), the ant queen buzz (32), snare roll + sweep into the vortex
                                   white-out (37-40)
  title   bars 11-12 beats 40-48   title HIT (16.67 s), the hook on theremin + brass, stop-time for the burp
                                   (beat 44 = 18.33 s, the burp sfx is mixed in by the intro mux), BUTTON at beat 46
                                   (19.17 s), ring out to 20.0

Build: python -m agentsound build songs/grandpa-konrad-intro
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Grandpa Konrad & Timo (Title Theme)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'cartoon title theme, 144 BPM, D minor, 20.0 s'}
ANALYSIS = {'profile': 'synthwave'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'GRANDPA KONRAD & TIMO', 'subtitle': 'AgentSound',
         'seed': 11}

BPM = 144
PROG = ['Dm', 'Dm', 'Eb', 'A7']                      # the series loop
ROOTS = {'Dm': 38, 'Eb': 39, 'A7': 33, 'Bb': 34, 'Gm': 31}
THEME_A = 'D5/2 F5/4 E5/8 D5/8 | A5/2. r/4 | Bb5/4 A5/4 G5/4 Bb5/4 | A5/1'
THEME_B = 'r/4 A5/4 C6/4 A5/4 | D6/2. r/4 | Eb6/4 D6/8 C6/8 Bb5/4 G5/4 | A5/2 C#5/2'
SMOG = 'D5/8 D5/8 F5/8 D5/8 G#5/4 A5/4'               # the Smog Monster motif (C minor -> D minor)
GROSS_BEATS = (10, 15, 20, 23, 31, 34, 36)


def theremin():
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.04, amp__decay=0.3, amp__sustain=0.95, amp__release=0.3, amp__velocity=0.8,
                   mods=[vamod.lfo('sine', hz=5.8, delay=0.12, fade=0.3, id='vib') >> ('pitch', 34),
                         vamod.velocity(id='accent') >> ('amp', 12)],
                   hpf=200, level=-5.0)


def drone():
    """Dark detuned saw drone (the eerie opening)."""
    return inst.va(osc1__wave='saw', osc1__fine=-18, osc2__wave='triangle', osc2__level=0.7, osc2__fine=19,
                   drift__pitch=26, filter__type='ladder', cutoff=480, resonance=0.2, filter__env=0.4,
                   amp__attack=0.8, amp__decay=1.0, amp__sustain=0.9, amp__release=0.6, hpf=50, level=-6.0)


def riser():
    """Resonant saw sweep (glide = the whoosh / suction)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__semi=7, mode='mono', glide=1.2,
                   filter__type='lp12', cutoff=3000, resonance=0.6, filter__env=0.8, fenv__decay=1.5,
                   amp__attack=0.3, amp__decay=1.0, amp__sustain=0.85, amp__release=0.2, level=-9.0)


def buzz_bass():
    """The ant queen's buzzing insect bass (ep2)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__pw=0.15, osc2__level=0.8, osc2__fine=9,
                   sub__level=0.5, filter__type='ladder', cutoff=420, resonance=0.35, filter__drive=0.6,
                   filter__env=1.5, fenv__decay=0.25, fenv__sustain=0.2,
                   amp__attack=0.005, amp__decay=0.4, amp__sustain=0.85, amp__release=0.15,
                   mods=[vamod.lfo('square', hz=18, id='buzz') >> ('cutoff', 0.6)], level=-4.0)


def bass_bar(sym, at, vel=1.0):
    """The bouncy octave pluck of the series."""
    r = ROOTS[sym]
    pat = [(0.0, 0.4, r, 104), (0.5, 0.3, r + 12, 84), (1.0, 0.4, r, 96), (1.5, 0.3, r + 12, 80),
           (2.0, 0.4, r + 7, 98), (2.5, 0.3, r + 12, 84), (3.0, 0.4, r, 96), (3.5, 0.3, r + 7, 86)]
    return [(at + t, d, p, int(v * vel)) for t, d, p, v in pat]


def build() -> Song:
    s = Song('Grandpa Konrad & Timo (Title Theme)', tempo=BPM, key='D minor', seed=11, tail=0.0)
    intro = s.section('intro', bars=2)
    drive = s.section('drive', bars=8)
    title = s.section('title', bars=2)
    s.hall(), s.plate(), s.echo()
    s.master.use('master/synthwave')

    kit = s.track('drums', 'synthwave/drums_808', gain_db=-1, fx=[fx.eq({'low.freq': 60, 'low.gain': -3})]).humanize(2, 3)
    perc = s.track('perc', inst.sf2('Standard 1 Kit'), gain_db=-7, pan=0.1).humanize(2, 4)
    bass = s.track('bass', 'synthwave/pluck_bass', gain_db=-1)
    organ = s.track('organ', 'synthwave/organ', gain_db=-3, pan=-0.25,
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.6})])
    lead = s.track('theremin', theremin(), gain_db=-5, pan=0.1, sends={'hall': -8, 'echo': -11},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    pad = s.track('drone', drone(), gain_db=-5, sends={'hall': -6})
    rise = s.track('riser', riser(), gain_db=-9, sends={'hall': -8})
    buzz = s.track('buzz', buzz_bass(), gain_db=2, fx=[fx.saturator(mode='tube', drive=8, tone=-3)])
    brass = s.track('brass', inst.sf2('Brass Section'), gain_db=-5, pan=-0.35, sends={'hall': -7, 'echo': -14},
                    fx=[fx.chorus(mode='I', mix=0.4)])
    trem = s.track('tremolo', inst.sf2('Tremolo Strings'), gain_db=4, pan=-0.1, sends={'hall': -7})
    timp = s.track('timpani', inst.sf2('Timpani'), gain_db=-3, sends={'hall': -8})
    tuba = s.track('tuba', inst.sf2('Tuba'), gain_db=-3, sends={'hall': -12})
    glock = s.track('glock', inst.sf2('Glockenspiel'), gain_db=-11, pan=0.3, sends={'hall': -6})
    revcym = s.track('revcym', inst.sf2('Reverse Cymbal'), gain_db=-9, sends={'hall': -8})
    pew = s.track('pew', 'synthwave/laser', gain_db=-14, pan=0.4)
    stab = s.track('stab', 'synthwave/brass_stab', gain_db=-4)
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-4, sends={'hall': -10})
    boom = s.track('boom', 'synthwave/impact', gain_db=-5)

    def big_hit(at, pitches=(38, 50, 57, 62), ring=1.5, stab_notes=(50, 57, 62, 65), vel=120, crash=True):
        ohit.play(Clip([(0, ring, p, vel) for p in pitches], length=4), at)
        boom.play(Clip([(0, max(2.0, ring), 38, min(127, vel + 4))], length=4), at)
        stab.play(Clip([(0, min(ring, 2.0), p, vel - 6) for p in stab_notes], length=4), at)
        kit.play(drums({'kick': 'X' + '.' * 7, 'crash': ('X' if crash else '.') + '.' * 7}), at)

    def blip(at, vel=100):
        """A gross-up flash: a short orchestra stab + a glock 'ew' (a falling minor second)."""
        ohit.play(Clip([(0, 0.3, p, vel) for p in (51, 58, 63)], length=1), at)
        glock.play(Clip([(0, 0.2, 87, 70), (0.2, 0.25, 86, 64)], length=1), at)

    # ================================================================== intro: eerie (beats 0-8)
    pad.play(Clip([(0, 8.0, p, 70) for p in (26, 38, 45)], length=8), intro.start)
    trem.play(Clip([(0, 8.0, 62, 40), (0, 8.0, 63, 34)], length=8), intro.start)        # a creepy minor 2nd
    trem.automate('gainDb', [(0, -12.0), (8.0, 0.0, 'smooth'), (8.01, -40.0)])
    lead.play(notes('vel=80 r/8 A4/8 D5/2 F5/8 E5/8 | D5/8 A5/2. r/8'), intro.start)    # the hook, eerie
    perc.play(drums({76: 'x.x.x.x.x.x.x.x.'}, vel=40), intro.start)                   # a ticking pulse
    kit.play(drums({'hat': 'x.x.x.x.x.x.x.x.', 'kick': 'x.......x.......'}, vel=55), mbar(intro, 2))
    bass.play(Clip([(i * 0.5, 0.3, 38 + (12 if i % 2 else 0), 60 + i * 4) for i in range(8)], length=4), mbar(intro, 2))
    for b in (2, 4, 6):                                                                  # whip-pan cuts
        pew.play(Clip([(0, 0.25, 88, 70)], length=1), b)
    rise.play(Clip([(0, 0.05, 50, 60), (0.05, 3.9, 86, 80)], length=4), mbar(intro, 2))
    revcym.play(Clip([(0, 3.0, 60, 90)], length=4), 8.0 - 3.0)

    # ================================================================== drive (beats 8-40)
    big_hit(8.0, ring=1.6)
    pew.play(Clip([(0, 0.2, 96, 96), (0.25, 0.2, 91, 90), (0.5, 0.3, 84, 84)], length=1), 8.0)  # the ray gun
    beat = drums({'kick': 'x...x...x...x.x.', 'snare': '....x.......x...', 'hat': 'xxx.xxx.xxx.xxx.',
                  'ohh': '..x...x...x...x.'}, vel=84)
    beat_b = drums({'kick': 'x...x...x.x.x.x.', 'snare': '....x.......x.xx', 'hat': 'xxx.xxx.xxx.xxx.',
                    'clap': '............x...'}, vel=88)
    bn, on = [], []
    for b in range(7):                                      # bars 3-9 groove; bar 10 is the vortex build
        sym = PROG[b % 4]
        bn += bass_bar(sym, b * 4.0)
        tones = [t - 12 if t > 69 else t for t in chord(sym).notes(4)][:3]
        on += [(b * 4.0 + off, 0.3, t, 62) for off in (1.5, 3.5) for t in tones]
        kit.play(beat_b if b % 4 == 3 else beat, drive.start + b * 4.0)
    bass.play(Clip(bn, length=28.0), drive.start)
    organ.play(Clip(on, length=28.0), drive.start)
    lead.play(notes(f'vel=92 {THEME_A}').arch(4, 0.6), drive.start)
    lead.play(notes('vel=90 r/4 A5/4 C6/4 A5/4 | D6/2. r/4 | Eb6/4 D6/8 C6/8 Bb5/4 G5/4').arch(3, 0.6),
              drive.start + 16.0)
    # gross-up flash stabs
    for g in GROSS_BEATS:
        blip(float(g), vel=104)
    # Oma's two stomps (beats 16, 17): timpani + tuba + boom
    for at, v in ((16.0, 124), (17.0, 112)):
        timp.play(Clip([(0, 0.8, 38, v)], length=1), at)
        tuba.play(Clip([(0, 0.6, 26, v - 6)], length=1), at)
        boom.play(Clip([(0, 1.0, 38, v - 8)], length=1), at)
    # Finn's sigh (beat 18.3): a sagging trombone-ish brass note
    brass.play(Clip([(0.3, 1.2, 57, 64)], length=2), 18.0)
    brass.automate('instrument.pitchbend', [(0, 0.0), (18.4, 0.0), (19.6, -1.0, 'smooth'), (20.0, 0.0)])
    # the free fall (beat 21): a slide-whistle-ish theremin dive is in the theme; add a pew
    pew.play(Clip([(0, 0.4, 96, 80)], length=1), 21.0)
    # Sock King roar (24): a low brass stab
    brass.play(Clip([(0, 0.6, p, 100) for p in (38, 45, 50)], length=1), 24.0)
    # Clean-O-Matic reverse (26-28): the suction sweep
    rise.play(Clip([(0, 0.05, 86, 70), (0.05, 1.9, 40, 80)], length=2), 26.0)
    # the SMOG MONSTER (28): hit + the monster motif on brass and tuba
    big_hit(28.0, pitches=(26, 38, 50, 57, 62), ring=1.2, stab_notes=(50, 53, 57, 62))
    brass.play(notes(f'vel=104 {SMOG}'), 28.25)
    tuba.play(notes(f'vel=96 {SMOG}', transpose=-36), 28.25)
    # the ANT QUEEN (32-34): the insect buzz bass
    buzz.play(Clip([(i * 0.5, 0.4, (38, 38, 41, 38, 44, 38, 45, 38)[i], 96) for i in range(8)], length=4), 32.0)
    brass.play(Clip([(0, 0.4, p, 96) for p in (50, 53, 56)], length=1), 32.0)
    glock.play(Clip([(0, 0.2, 94, 70), (0.25, 0.3, 98, 64)], length=1), 35.0)          # crash zoom ping
    # bar 10 (beats 36-40): the vortex - snare roll, rising bass, riser, reverse cymbal, white-out
    kit.play(drums({'snare': 'x.x.x.x.xxxxxxxx', 'kick': 'x...x...x...x...', 'hat': 'xxxxxxxxxxxxxxxx'}, vel=70), 36.0)
    bass.play(Clip([(i * 0.5, 0.35, 38 + i, 84 + i * 4) for i in range(8)], length=4), 36.0)
    trem.play(Clip([(0, 3.9, p, 76) for p in (57, 61, 64, 67)], length=4), 36.0)
    rise.play(Clip([(0, 0.05, 50, 70), (0.05, 3.8, 98, 96)], length=4), 36.0)
    lead.play(notes('vel=92 A5/8 Bb5/8 B5/8 C6/8 C#6/8 D6/8 Eb6/8 E6/8'), 37.0)
    revcym.play(Clip([(0, 3.0, 60, 100)], length=4), 40.0 - 3.0)

    # ================================================================== title (beats 40-48)
    big_hit(40.0, pitches=(26, 38, 50, 57, 62, 65), ring=2.4, stab_notes=(50, 57, 62, 65, 69), vel=124)
    kit.play(drums({'kick': 'x...x...x...x.x.', 'snare': '....x.......x...', 'hat': 'xxx.xxx.xxx.xxx.',
                    'ohh': '..x...x...x...x.'}, vel=86), 40.0)
    bass.play(Clip(bass_bar('Dm', 0.0), length=4), 40.0)
    lead.play(notes('vel=96 D5/4 F5/8 E5/8 D5/8 A5/4.'), 40.0)                          # the hook, once more
    brass.play(Clip([(0, 0.4, p, 96) for p in (50, 57, 62)] + [(2.5, 1.0, p, 100) for p in (57, 61, 64)],
                    length=4), 40.0)
    timp.play(Clip([(3.0 + i * 0.125, 0.125, 45, 70 + i * 6) for i in range(4)], length=4), 40.0)
    # beat 43.5: everything stops; the burp (beat 44, sfx) gets the stage; a tuba 'blat' under it
    tuba.play(Clip([(0, 0.5, 26, 88), (0.6, 0.6, 21, 80)], length=2), 44.05)
    glock.play(Clip([(0, 0.2, 98, 70), (0.4, 0.2, 93, 60)], length=1), 45.25)           # a tiny 'ting' pickup
    # the BUTTON (beat 46): D minor + the series' wobbly theremin note, ring to the end
    big_hit(46.0, pitches=(26, 38, 50, 57, 62), ring=2.0, stab_notes=(50, 57, 62, 65), vel=122)
    lead.play(Clip([(0, 2.0, 74, 96)], length=2), 46.0)
    timp.play(Clip([(0, 1.0, 38, 112)], length=2), 46.0)
    s.master.automate('gainDb', [(0, 0.0), (43.45, 0.0), (43.55, -16.0), (45.95, -16.0), (46.0, 0.0),
                                 (47.0, 0.0), (48.0, -24.0, 'smooth')])
    return s


def mbar(section, n, beat=0.0):
    return section.bar(n - 1, beat=beat)
