"""Operation No Wi-Fi (3-min cut) - the 187.5-second score for episode 2 of the Grandpa Konrad & Timo cartoon.

Re-score of songs/operation-no-wifi (the 128 s cut, left untouched) for the extended timeline: a sneak sequence
(lines 25-29, D3/D4) after the ant city, and a longer fight (lines 30-36, F3b-F3e) between the net snap and the
queen's meltdown. Same musical world: wobbly theremin lead, bouncy pluck bass, light 808 drums, spooky organ,
D minor. Every chapter is a section whose tempo is set so its first downbeat lands exactly on the picture anchor
(clip starts from ep2_couch/manifest.json chapters[].clips[].start + ep2_couch/build/timeline.json spans, which
are in ep2_couch/episode.json panel order; the song ends at the episode length, tail 0).

  sunday     0.000 -  19.513  10 bars ~123.0  rainy Sunday: silence, clock tick, lazy pad (A3); cut before the bang
  bang       19.514 -   45.582  13 bars ~119.7  B1 door BANG hit, conspiracy groove, stop-time line 8, build
  shrink     45.582 -   50.916   3 bars  135    C1 zap down, tiny music-box theme
  antcity    50.916 -   60.965   5 bars ~119.4  D1 mysterious ant march
  sneak      60.965 -   70.447   4 bars ~101.3  D3 tiptoe: pizzicato + bassoon, rim ticks under the whispers
  approach   70.447 -   73.047   1 bar  ~92.3   D4 the line creeps to the barrier: chromatic creep, freeze ...
  halt       73.047 -   78.185   2 bars ~93.4   "Halt!" stop hit, suspense: tremolo, heartbeat timpani, ticking
  respect    78.185 -   82.016   2 bars ~125.3  "...Respect." comic release (D major plink + tuba), tiptoe on
  queen      82.016 - 105.891  12 bars ~120.6  E1 villain theme, the WORLD hit at 99.894, tense
  fight    105.891 - 110.923   3 bars ~143    F1 action ... CUT
  burp     110.923 - 115.341   2 bars         silence for the mega burp (line 18)
  slam     115.341 - 120.683   3 bars ~134.8  slam back in, braces (line 19), build into ...
  rally    120.683 - 128.449   4 bars ~123.6  F3b rally sting on line 30, villain march as the guards get up
  softener 128.449 - 136.884   5 bars ~142.3  F3c fabric-softener fanfare (D major, absurd), poofs as they go fluffy
  gross    136.884 - 139.884   2 bars  160    F3d gross-up of the foamed captain: an "eww" chord
  duel     139.884 - 151.214   7 bars ~148.3  swashbuckling toothpick duel (gallop), clangs on the parries
  poke     151.214 - 154.714   2 bars ~137.1  F3e the poke (boing, captain flies off), build under line 36 ...
  cable    154.714 - 156.565   1 bar  ~129.7  ... the "Pull the CABLE!" hit, timpani roll into
  melt     156.565 - 163.504   4 bars ~138.3  F4/F5 meltdown + chase groove, "Reverse polarity!" build
  home     163.504 - 172.398   4 bars ~107.9  the reverse-ray flash hit, warm major resolution
  sting    172.398 - 179.638   3 bars ~99.4   comic sting on the last burp (line 24), decays to silence

Build: python -m agentsound build songs/operation-no-wifi-3min
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Operation No Wi-Fi (Score, 3-min cut)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'cartoon score to picture, episode 2 (3-min cut), D minor, ~120 BPM, 187.5 s'}
ANALYSIS = {'profile': 'synthwave'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'OPERATION NO WI-FI', 'subtitle': 'AgentSound',
         'seed': 7}

# Picture anchors in seconds: ep2_couch/build/timeline.json spans (by line id, episode.json panel order) + the
# manifest clip offsets. S[id] = span start of that line.
# (preshort, 2026-10-15: the opening was cut - lead-in 5.0->2.8, line 1 take 8.81->5.90 s, pauses 2.0->1.1,
#  2.8->1.1, 1.6->1.4 - so every anchor from line 4 on moved 7.909396 s earlier; the old numbers are in
#  song_v_preshort.py.txt)
T_BANG = 20.413188 - 0.9            # B1: line 4 - 0.9 (door bang)
T_SHRINK = 44.181584 + 1.4          # C1: line 9 + 1.4 (shrink ray)
T_ANTS = 51.915792 - 1.0            # D1: line 11 - 1.0
T_SNEAK = 62.165022 - 1.2           # D3: line 25 - 1.2 (disguise, whispers)
T_APPROACH = 73.046501 - 2.6        # D4: line 27 - 2.6 (the line moves to the barrier)
T_HALT = 73.046501                  # line 27 start: "Halt!" (the word is at +0.0)
T_RESPECT = 78.185064               # line 29 start: "...Respect." (the word is at +0.0)
T_QUEEN = 83.015543 - 1.0           # E1: line 13 - 1.0
T_WORLD = 90.293689 + 9.6           # line 15 "...we take the WORLD!" - the word at ~9.6 s into the take
T_FIGHT = 106.090398 - 0.2          # F1: line 17 - 0.2
T_BURP = 110.922481                 # line 18 start: the mega burp (F2)
T_SLAM = 110.922481 + 4.417979      # line 18 end: slam back in
T_RALLY = 120.682918                # line 30 start: the queen rallies the guards (F3b cut is 0.4 s earlier)
T_SOFT = 128.448960                 # line 31 start: "Fabric softener!" battle cry (F3c cut is 1.6 s earlier)
T_GROSS = 139.883565 - 3.2 + 0.2    # F3d (line 33 - 3.2) + gross-up offset 0.2: the foamed captain, 3.0 s
T_DUEL = 139.883565                 # line 33 start: "Fluffy... but still DANGEROUS!" - the duel
T_POKE = 153.214066 - 2.0           # F3e: line 36 - 2.0 (Timo pokes the captain, who flies off)
T_CABLE = 153.214066 + 1.50         # line 36 "Pull the CABLE!" - "CA-" at ~1.50 s into the take
T_MELT = 156.864441 - 0.3           # F4: line 20 - 0.3 (the yank, queen meltdown)
T_FLASH = 161.046983 + 2.456729     # line 21 end: the reverse-ray flash
T_STING = 172.397296                # line 24 start: the last burp
T_END = 179.637546                  # timeline total = episode length

# (name, start s, end s, bars): the tempo of each section is bars * 4 beats over its length
SUN_BARS = 10      # (preshort: 14)
PLAN = [('sunday', 0.0, T_BANG, SUN_BARS), ('bang', T_BANG, T_SHRINK, 13), ('shrink', T_SHRINK, T_ANTS, 3),
        ('antcity', T_ANTS, T_SNEAK, 5), ('sneak', T_SNEAK, T_APPROACH, 4), ('approach', T_APPROACH, T_HALT, 1),
        ('halt', T_HALT, T_RESPECT, 2), ('respect', T_RESPECT, T_QUEEN, 2),
        ('queen', T_QUEEN, T_FIGHT, 12), ('fight', T_FIGHT, T_BURP, 3),
        ('burp', T_BURP, T_SLAM, 2), ('slam', T_SLAM, T_RALLY, 3), ('rally', T_RALLY, T_SOFT, 4),
        ('softener', T_SOFT, T_GROSS, 5), ('gross', T_GROSS, T_DUEL, 2), ('duel', T_DUEL, T_POKE, 7),
        ('poke', T_POKE, T_CABLE, 2), ('cable', T_CABLE, T_MELT, 1), ('melt', T_MELT, T_FLASH, 4),
        ('home', T_FLASH, T_STING, 4), ('sting', T_STING, T_END, 3)]

# the hits checked on the rendered mix (largest loudness jump near each target)
HITS = {'bang': T_BANG, 'shrink': T_SHRINK, 'halt': T_HALT, 'respect': T_RESPECT, 'world': T_WORLD,
        'slam': T_SLAM, 'rally': T_RALLY, 'softener': T_SOFT, 'poke': T_POKE, 'cable': T_CABLE, 'flash': T_FLASH,
        'sting': T_STING}


def mbar(section, n, beat=0.0):
    """Musical (1-based) bar n of a section: mbar(sec, 1) = its first downbeat."""
    return section.bar(n - 1, beat=beat)


def bpm_of(a, b, bars):
    return bars * 4 * 60.0 / (b - a)


# 4-bar spooky-goofy loop of the series: Dm | Dm | Eb (bII) | A7
PROG = ['Dm', 'Dm', 'Eb', 'A7']
ROOTS = {'Dm': 38, 'Eb': 39, 'A7': 33, 'Bb': 34, 'Gm': 31, 'C': 36, 'D': 38, 'G': 43, 'A': 33}

# the series theme (phrase A of Sockenkrieg) and its answer
THEME_A = 'D5/2 F5/4 E5/8 D5/8 | A5/2. r/4 | Bb5/4 A5/4 G5/4 Bb5/4 | A5/1'
THEME_B = 'r/4 A5/4 C6/4 A5/4 | D6/2. r/4 | Eb6/4 D6/8 C6/8 Bb5/4 G5/4 | A5/2 C#5/2'


def bass_bar(sym, bar_start, vel=1.0):
    """Bouncy octave pluck (the series bass): root, octave, root, fifth/octave pickups."""
    r = ROOTS[sym]
    fifth = r + 7
    pat = [(0.0, 0.4, r, 104), (0.5, 0.3, r + 12, 84), (1.0, 0.4, r, 96), (1.75, 0.25, r, 80),
           (2.0, 0.4, fifth, 98), (2.5, 0.3, r + 12, 84), (3.0, 0.4, r, 96), (3.5, 0.3, fifth, 86)]
    return [(bar_start + t, d, p, int(v * vel)) for t, d, p, v in pat]


def theremin():
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.9,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def lazy_pad():
    """A tired, slightly out-of-tune low pad: two detuned saws, heavy drift, dark, slow swell."""
    return inst.va(osc1__wave='saw', osc1__fine=-18, osc2__wave='triangle', osc2__level=0.7, osc2__fine=19,
                   drift__pitch=26, filter__type='ladder', cutoff=520, resonance=0.1, filter__env=0.5,
                   amp__attack=2.5, amp__decay=2.0, amp__sustain=0.9, amp__release=1.2, hpf=60, level=-6.0)


def zap_synth():
    """Shrink-ray zap: a resonant saw that glides from the top of the keyboard to the bottom."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__semi=7, mode='mono', glide=0.9,
                   filter__type='lp12', cutoff=5000, resonance=0.55, filter__env=1.0, fenv__decay=1.2,
                   amp__attack=0.003, amp__decay=1.2, amp__sustain=0.6, amp__release=0.4, level=-8.0)


def buzz_bass():
    """The queen's buzzing bass: saw + narrow pulse, a gritty ladder, a fast wobble (an insect drone)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__pw=0.15, osc2__level=0.8, osc2__fine=9,
                   sub__level=0.5, filter__type='ladder', cutoff=420, resonance=0.35, filter__drive=0.6,
                   filter__env=1.5, fenv__decay=0.25, fenv__sustain=0.2,
                   amp__attack=0.005, amp__decay=0.4, amp__sustain=0.85, amp__release=0.15,
                   mods=[vamod.lfo('square', hz=18, id='buzz') >> ('cutoff', 0.6)], level=-4.0)


def build() -> Song:
    s = Song('Operation No Wi-Fi (Score, 3-min cut)', tempo=bpm_of(*PLAN[0][1:]), key='D minor', seed=7, tail=0.0)
    sec = {}
    for name, a, b, bars in PLAN:
        sec[name] = s.section(name, bars=bars)
    for name, a, b, bars in PLAN[1:]:
        s.set_tempo(sec[name], bpm_of(a, b, bars))
    sunday, bang, shrink, antcity, queen = (sec[k] for k in ('sunday', 'bang', 'shrink', 'antcity', 'queen'))
    sneak, approach, halt, respect = (sec[k] for k in ('sneak', 'approach', 'halt', 'respect'))
    fight, burp, slam, home, sting = (sec[k] for k in ('fight', 'burp', 'slam', 'home', 'sting'))
    rally, softener, gross, duel = (sec[k] for k in ('rally', 'softener', 'gross', 'duel'))
    poke, cable, melt = (sec[k] for k in ('poke', 'cable', 'melt'))

    s.hall(), s.plate(), s.echo()
    s.master.use('master/synthwave')

    # ------------------------------------------------------------------ the band (mids kept open for dialogue)
    kit = s.track('drums', 'synthwave/drums_808', gain_db=-2,
                  fx=[fx.eq({'low.freq': 60, 'low.gain': -4})]).humanize(2, 4)
    march = s.track('march', inst.sf2('Standard 1 Kit'), gain_db=-10, pan=0.15,
                    fx=[fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 0.7})]).humanize(3, 6)
    bass = s.track('bass', 'synthwave/pluck_bass', gain_db=-1)
    organ = s.track('organ', 'synthwave/organ', gain_db=-8, pan=-0.25,
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -5.0, 'peak2.q': 0.6})])
    lead = s.track('theremin', theremin(), gain_db=-4, pan=0.1, sends={'hall': -9, 'echo': -12},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    pad = s.track('pad', lazy_pad(), gain_db=-6, sends={'hall': -10},
                  fx=[fx.eq({'peak2.freq': 1000, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    tick = s.track('clock', inst.sf2('Wood Block'), gain_db=-14, pan=0.35, sends={'hall': -16})
    zap = s.track('zap', zap_synth(), gain_db=-10, pan=-0.1, sends={'hall': -10})
    pew = s.track('pew', 'synthwave/laser', gain_db=-16, pan=0.4)
    box = s.track('musicbox', inst.sf2('Music Box'), gain_db=-6, pan=0.2, sends={'hall': -8})
    glock = s.track('glock', inst.sf2('Glockenspiel'), gain_db=-12, pan=-0.3, sends={'hall': -8})
    pizz = s.track('pizz', inst.sf2('Pizzicato Strings'), gain_db=-5, pan=-0.15, sends={'hall': -12})
    harpsi = s.track('harpsichord', inst.sf2('Harpsichord'), gain_db=-7, pan=0.3, sends={'hall': -11})
    buzz = s.track('buzz', buzz_bass(), gain_db=-6, fx=[fx.saturator(mode='tube', drive=8, tone=-3)])
    timp = s.track('timpani', inst.sf2('Timpani'), gain_db=-4, sends={'hall': -9})
    tuba = s.track('tuba', inst.sf2('Tuba'), gain_db=-4, sends={'hall': -14})
    stab = s.track('stab', 'synthwave/brass_stab', gain_db=-5)
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-3, sends={'hall': -12})
    boom = s.track('boom', 'synthwave/impact', gain_db=-6)
    # new for the 3-min cut: the sneak (bassoon, tremolo strings) and the bigger fight (trumpet, brass section)
    bsn = s.track('bassoon', inst.sf2('Bassoon'), gain_db=-8, pan=0.2, sends={'hall': -12})
    trem = s.track('tremolo', inst.sf2('Tremolo Strings'), gain_db=-9, pan=-0.1, sends={'hall': -10},
                   fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    tpt = s.track('trumpet', inst.sf2('Trumpet'), gain_db=-8, pan=0.15, sends={'hall': -9})
    brass = s.track('brass', inst.sf2('Brass Section'), gain_db=-8, pan=-0.1, sends={'hall': -10},
                    fx=[fx.eq({'peak2.freq': 1800, 'peak2.gain': -3.0, 'peak2.q': 0.7})])

    def big_hit(at, pitches=(38, 50, 57, 62), ring=1.5, stab_notes=(50, 57, 62, 65), vel=120, kick=True):
        """The series hit: orchestra hit + impact boom + brass stab (+ kick and crash)."""
        ohit.play(Clip([(0, ring, p, vel) for p in pitches], length=4), at)
        boom.play(Clip([(0, max(2.0, ring), 38, min(127, vel + 4))], length=4), at)
        stab.play(Clip([(0, min(ring, 2.0), p, vel - 6) for p in stab_notes], length=4), at)
        if kick:
            kit.play(drums({'kick': 'X', 'crash': 'X'}, bars=1), at)

    # ================================================================== A: boring Sunday (no music at first)
    # (preshort: the opening is ~7.9 s shorter - 10 bars instead of 14 at the same ~123 BPM; the clock starts as
    #  line 1 ends (bar 4 beat 2, was bar 7), the lazy lead answers the sigh, the pad swells from the A3 cut)
    ticks = []
    for b in range(4, SUN_BARS):
        for half in (0, 2):
            if (b == 4 and half == 0) or (b == SUN_BARS - 1 and half == 2):
                continue                                      # the clock 'stops' just before the bang
            v = 28 + (b - 4) * 6
            ticks.append((b * 4 + half, 0.2, 77 if half == 0 else 76, v))
    tick.play(Clip(ticks, length=SUN_BARS * 4), sunday)
    pad.play(Clip([(0, 6.0, p, 62) for p in (38, 45, 53)] + [(6.0, 1.6, p, 58) for p in (37, 45, 52)],
                  length=8), sunday.bar(8))
    pad.automate('gainDb', ramp(sunday.bar(8), sunday.bar(9), -8, 0), hold(sunday.bar(9), bang.start, 0))
    lead.play(notes('vel=54 A4/2 F4/2 | D4/1').arch(2, 0.5), sunday.bar(4, beat=2))

    # ================================================================== B: the BANG + the conspiracy groove
    big_hit(bang.start, ring=2.0)
    kit.play(drums({'tom_lo': 'X...', 'tom_mid': '..x.'}, bars=1, vel=90), bang.start)
    lead.play(Clip([(1.0, 1.0, 62, 84), (2.0, 1.0, 74, 92), (3.0, 1.0, 69, 86)], length=4), bang.start)

    g0 = mbar(bang, 2)
    groove_bars = 10
    bnotes, onotes = [], []
    for b in range(groove_bars):
        sym = PROG[b % 4]
        bnotes += bass_bar(sym, b * 4.0, vel=0.9)
        tones = chord(sym).notes(4)
        tones = [t - 12 if t > 69 else t for t in tones][:3]
        ov = 60 + (6 + b * 2 if b >= 6 else 0)
        for off in (1.5, 3.5):
            onotes += [(b * 4.0 + off, 0.35, t, ov) for t in tones]
    bass.play(Clip(bnotes, length=groove_bars * 4.0), g0)
    organ.play(Clip(onotes, length=groove_bars * 4.0), g0)
    beat = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...',
                  'hat': 'x.o.x.o.x.o.x.o.', 'cowbell': '..............o.'}, vel=70)
    beat_b = drums({'kick': 'x.....x.x.....x.', 'snare': '....x.......x.o.',
                    'hat': 'x.o.x.o.x.o.x.ox', 'clap': '............x...'}, vel=72)
    for b in range(groove_bars):
        kit.play(beat_b if b % 4 == 3 else beat, g0 + b * 4.0)
    lead.play(notes(f'vel=72 {THEME_A}').arch(4, 0.5), g0)
    lead.play(notes(f'vel=74 {THEME_B}').arch(4, 0.5), g0 + 24.0)
    for bar in (4, 5):
        pew.play(Clip([(0, 0.25, 84, 76), (0.5, 0.25, 88, 66)], length=1), g0 + bar * 4.0 + 3.0)

    stop = mbar(bang, 12)
    bass.play(Clip([(0, 0.5, 38, 96)], length=4), stop)
    organ.play(Clip([(0, 0.35, p, 58) for p in (50, 53, 57)], length=4), stop)
    tick.play(Clip([(1, 0.2, 77, 40), (2, 0.2, 76, 40), (3, 0.2, 77, 44)], length=4), stop)
    b13 = mbar(bang, 13)
    kit.play(drums({'snare': 'x.x.x.x.xxxxxxXX', 'kick': 'x...x...x...x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                   vel=64), b13)
    bass.play(Clip([(i * 0.5, 0.4, p, 84 + i * 4) for i, p in enumerate((38, 41, 43, 44, 45, 47, 49, 50))],
                   length=4), b13)
    zap.play(Clip([(0, 3.9, 50, 50), (0.05, 3.85, 74, 60)], length=4), b13)
    zap_auto = [ramp(b13, shrink.start, -18, -4), hold(shrink.start, shrink.end, -4)]

    # ================================================================== C: shrink - zap down, tiny theme
    zap.play(Clip([(0, 0.05, 108, 120), (0.05, 2.4, 36, 110)], length=4), shrink.start)
    kit.play(drums({'kick': 'X', 'crash': 'x'}, bars=1, vel=80), shrink.start)
    boom.play(Clip([(0, 1.5, 38, 96)], length=4), shrink.start)
    tiny = notes('vel=78 D7/8 F7/8 E7/16 D7/16 A7/4 r/8 Bb7/8 A7/8 G7/8 Bb7/8 A7/4 r/4 '
                 'D7/16 E7/16 F7/16 G7/16 A7/4').arch(2, 0.5)
    box.play(tiny, mbar(shrink, 1, beat=2))
    pizz.play(Clip([(i, 0.3, p, 70) for i, p in enumerate((62, 69, 62, 69, 62, 69, 61, 69, 62, 69))], length=10),
              mbar(shrink, 1, beat=2))
    march.play(drums({'rim': 'x.x.x.x.x.x.x.x.'}, bars=2, vel=46), mbar(shrink, 2))

    # ================================================================== D: the ant city - mysterious march
    ant_prog = ['Dm', 'Bb', 'Gm', 'A7', 'Dm']
    snare_march = drums({'snare': 'x..xx.x.x..xxxxx', 'kick': 'x.......x.......'}, vel=52)
    snare_march2 = drums({'snare': 'x..xx.x.x.x.x.xx', 'kick': 'x.......x.......'}, vel=58)
    for b in range(5):
        march.play(snare_march2 if b % 2 else snare_march, mbar(antcity, b + 1))
        r = ROOTS[ant_prog[b]]
        pizz.play(Clip([(0, 0.4, r + 12, 78), (1, 0.3, r + 19, 62), (2, 0.4, r + 7, 74), (3, 0.3, r + 19, 62)],
                       length=4), mbar(antcity, b + 1))
        tones = [t - 12 if t > 65 else t for t in chord(ant_prog[b]).notes(4)][:3]
        organ.play(Clip([(0, 3.8, t, 56 + b * 2) for t in tones], length=4), mbar(antcity, b + 1))
    lead.play(notes('vel=66 A4/2 Bb4/4 A4/4 | D5/2. r/4 | r/1 | C#5/2 E5/2').arch(2, 0.5), mbar(antcity, 1))
    glock.play(notes('vel=70 D6/16 F6/16 A6/16 D7/16 r/4 A6/16 F6/16 D6/8 r/4').arch(1, 0.5), mbar(antcity, 4))

    # ================================================================== D3: the sneak - tiptoe pizzicato
    # quiet under the whispers (lines 25/26): staccato pizzicato tiptoes, a sneaky bassoon, rim ticks for the
    # little ant feet. Dm | Dm | Gm | A7
    sneak_prog = [('Dm', 38), ('Dm', 38), ('Gm', 43), ('A7', 45)]
    for b, (sym, r) in enumerate(sneak_prog):
        at = mbar(sneak, b + 1)
        pizz.play(Clip([(0, 0.2, r, 70), (0.5, 0.2, r + 7, 52), (1, 0.2, r + 12, 62), (1.5, 0.2, r + 7, 50),
                        (2, 0.2, r, 66), (2.5, 0.2, r + 7, 50), (3, 0.2, r + 12, 60), (3.5, 0.15, r + 11, 52),
                        (3.75, 0.15, r + 12, 56)], length=4), at)
        march.play(drums({'rim': 'x...o...x...o...', 'hat': '..o...o...o...o.'}, vel=40), at)
    # the bassoon creeps along (soft, low: under the whispered dialogue), a tip-toe figure, then a cheeky turn
    bsn.play(notes('vel=58 D3/8 r/8 F3/8 r/8 E3/8 r/8 D3/8 r/8 | A2/8 r/8 C#3/8 D3/8 r/2 | '
                   'G2/8 r/8 Bb2/8 r/8 A2/8 r/8 G2/8 r/8 | E3/8 F3/8 E3/8 C#3/8 A2/4 r/4').arch(4, 0.4),
             mbar(sneak, 1))
    # a single sly theremin glide in the gap between the whispers (74.48 - 75.08)
    lead.play(Clip([(0, 0.5, 62, 50), (0.5, 0.7, 65, 54)], length=2), s.beat_at(74.50 - 7.909396))

    # D4: the line moves to the barrier - chromatic creep up, crescendo ... and a freeze right before "Halt!"
    creep = [(i * 0.5, 0.22, 38 + i, 56 + i * 6) for i in range(7)]
    pizz.play(Clip(creep, length=4), approach.start)
    bsn.play(Clip([(i * 0.5, 0.22, 26 + i, 54 + i * 5) for i in range(7)], length=4), approach.start)
    trem.play(Clip([(0, 3.4, p, 52) for p in (50, 51)], length=4), approach.start)
    trem.automate('gainDb', ramp(approach.start, mbar(approach, 1, beat=3.4), -20, -4),
                  hold(mbar(approach, 1, beat=3.4), halt.start, -60),
                  hold(halt.start, mbar(halt, 1, beat=1), -60),
                  ramp(mbar(halt, 1, beat=1), mbar(halt, 2, beat=3), -14, -3),
                  hold(mbar(halt, 2, beat=3), respect.end, -60), hold(respect.end, sting.end, -4))
    march.play(drums({'rim': 'x.x.x.x.x.x.x...'}, vel=50), approach.start)

    # ================================================================== "Halt!": the stop + suspense
    ohit.play(Clip([(0, 0.35, p, 112) for p in (38, 50, 51, 57)], length=4), halt.start)
    boom.play(Clip([(0, 1.2, 38, 104)], length=4), halt.start)
    timp.play(Clip([(0, 1.0, 38, 112)], length=4), halt.start)
    kit.play(drums({'kick': 'X'}, bars=1), halt.start)
    # suspense: a low tremolo cluster under the check, heartbeat timpani, the clock motif ticking, slow crescendo
    trem.play(Clip([(1, 6.6, p, 60) for p in (38, 45, 51)], length=8), halt.start)
    timp.play(Clip([(t, 0.4, 38, v) for t, v in ((2, 50), (2.4, 40), (4, 56), (4.4, 46), (6, 62), (6.4, 52))],
                   length=8), halt.start)
    tick.play(Clip([(t, 0.2, 77 if i % 2 == 0 else 76, 36 + i * 3) for i, t in enumerate((1, 2, 3, 4, 5, 6))],
                   length=8), halt.start)
    # the long suspicious pause after line 28 (85.29 - 86.09): a high sustained bassoon question, then air
    bsn.play(Clip([(5.6, 1.4, 45, 50)], length=8), halt.start)

    # ================================================================== "...Respect. Carry on." - comic release
    pizz.play(Clip([(0, 0.6, p, 96) for p in (38, 50, 54, 57, 62)], length=4), respect.start)       # D MAJOR plink
    glock.play(notes('vel=82 A6/16 D7/16 F#7/8'), respect.start)
    tuba.play(Clip([(0, 0.5, 26, 104), (0.75, 0.9, 33, 86)], length=4), respect.start)               # phew-bwomp
    kit.play(drums({'kick': 'X'}, bars=1, vel=90), respect.start)
    lead.play(Clip([(0.25, 0.5, 74, 74), (0.75, 1.2, 66, 66)], length=4), respect.start)            # a relieved sigh
    # "Carry on." (87.49) - the tiptoe march resumes, a little perkier, and grows into the queen reveal
    march.play(drums({'rim': '....x.x.x.x.x.x.', 'snare': '..............xx'}, vel=52), respect.start)
    march.play(drums({'snare': 'x.x.x.x.xxxxxxxx', 'kick': 'x.......x.......'}, vel=56), mbar(respect, 2))
    pizz.play(Clip([(2 + i * 0.5, 0.2, p, 66 + i * 3) for i, p in enumerate((50, 57, 53, 57))], length=4),
              respect.start)
    pizz.play(Clip([(i * 0.5, 0.2, p, 72 + i * 3) for i, p in enumerate((45, 52, 49, 52, 45, 49, 52, 57))],
                   length=4), mbar(respect, 2))
    organ.play(Clip([(0, 3.9, p, 54) for p in (45, 49, 52)], length=4), mbar(respect, 2))

    # ================================================================== E: the queen - villain theme
    lam = [('Dm', 38), ('Dm', 36), ('Bb', 34), ('A7', 33)]
    q_world = s.beat_at(T_WORLD)
    for b in range(12):
        sym, root = lam[b % 4]
        at = mbar(queen, b + 1)
        if b == 9:
            continue
        grow = min(1.0, max(0.0, (b - 3) / 5.0))
        if b >= 10:
            grow = 0.4
        tones = chord(sym).notes(4)
        top = [t for t in tones if t >= 62][:3] or tones[:3]
        arp = [root + 24] + sorted(top)
        if b < 4 or b >= 10:
            figure = [(i * 0.5, 0.45, arp[i % len(arp)], 74 if i % 4 == 0 else 62) for i in range(8)]
        else:
            seq = arp + arp[::-1][1:-1]
            figure = [(i * 0.25, 0.24, seq[i % len(seq)] + (12 if i % 8 == 7 else 0), int(64 + grow * 28))
                      for i in range(16)]
        if b == 8:
            figure = [n for n in figure if n[0] < 3.5]
        harpsi.play(Clip(figure, length=4), at)
        if grow < 0.3:
            buzz.play(Clip([(0, 3.8, root - 12, 92)], length=4), at)
        else:
            buzz.play(Clip([(i * 0.5, 0.42, root - 12 + (12 if i % 4 == 3 else 0), int(80 + grow * 30))
                            for i in range(8 if b != 8 else 7)], length=4), at)
        if b >= 4:
            timp.play(Clip([(0, 1, root, int(60 + grow * 50)), (2, 1, root + 7 if root + 7 < 48 else root - 5,
                                                                  int(54 + grow * 50))], length=4), at)
            organ.play(Clip([(0, 3.9, t - 12 if t > 62 else t, int(50 + grow * 30)) for t in top], length=4), at)
    buzz_auto = [hold(queen.start, mbar(queen, 5), -4), ramp(mbar(queen, 5), q_world, -4, 2),
                 hold(q_world, mbar(queen, 11), 0), hold(mbar(queen, 11), queen.end, -6)]
    lead.play(notes('vel=70 D6/4 C#6/8 D6/8 F6/2 | E6/4 D6/4 C#6/2').arch(2, 0.5), mbar(queen, 3, beat=2))
    kit.play(drums({'snare': '11223344556677..', 'tom_lo': '............7.7.'}, vel=70), mbar(queen, 9))
    timp.play(Clip([(i * 0.25, 0.25, 38, 50 + i * 3) for i in range(14)], length=4), mbar(queen, 9))
    big_hit(q_world, pitches=(26, 38, 50, 57, 62, 65), ring=3.0, stab_notes=(50, 53, 57, 62, 65), vel=124)
    timp.play(Clip([(0, 2, 38, 120)], length=4), q_world)
    organ.play(Clip([(0, 3.5, p, 90) for p in (38, 50, 53, 57)], length=4), q_world)
    lead.play(Clip([(0, 0.4, 74, 92), (0.4, 2.6, 86, 96)], length=4), q_world)
    tick.play(Clip([(i, 0.2, 77 if i % 2 == 0 else 76, 50) for i in range(8)], length=8), mbar(queen, 11))

    # ================================================================== F: the fight
    action = drums({'kick': 'x..x..x.x..x..x.', 'snare': '....X.......X...', 'hat': 'xxxxxxxxxxxxxxxx',
                    'tom_lo': '..............x.'}, vel=74)
    action2 = drums({'kick': 'x..x..x.x.x...x.', 'snare': '....X..o....X.x.', 'hat': 'x.xxx.xxx.xxx.xx',
                     'tom_mid': '.............x..', 'tom_lo': '..............xx'}, vel=78)
    kit.play(drums({'kick': 'X', 'crash': 'x'}, bars=1, vel=88), fight.start)
    for b in range(2):
        kit.play(action if b == 0 else action2, mbar(fight, b + 1))
        bass.play(Clip([(i * 0.5, 0.35, 38 + (12 if i % 4 == 2 else 0) + (3 if b == 1 and i >= 6 else 0), 96)
                        for i in range(8)], length=4), mbar(fight, b + 1))
    kit.play(drums({'snare': 'x.x.xxxxxxxxXXXX', 'kick': 'x...x...x.x.xxxx', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=66),
             mbar(fight, 3))
    bass.play(Clip([(i * 0.5, 0.35, p, 100) for i, p in enumerate((38, 39, 40, 41, 42, 43, 44, 45))], length=4),
              mbar(fight, 3))
    stab.play(Clip([(0, 0.3, p, 92) for p in (50, 57, 62)] + [(1.5, 0.3, p, 96) for p in (51, 58, 63)], length=4),
              mbar(fight, 2))
    lead.play(notes('vel=78 D5/8 F5/8 E5/8 D5/8 A5/2').arch(1, 0.5), mbar(fight, 1, beat=2))
    # the burp: total silence (master gate), then SLAM back in
    gate_out, gate_in = s.beat_at(T_BURP - 0.02), s.beat_at(T_SLAM - 0.004)
    master_gate = [hold(0, gate_out, 0), ramp(gate_out, burp.start, 0, -90),
                   hold(burp.start, gate_in, -90), ramp(gate_in, slam.start, -90, 0)]

    # ================================================================== F2/F3: slam back in, the braces
    big_hit(slam.start, pitches=(26, 38, 50, 57, 62), ring=1.5, vel=124)
    slam_beat = drums({'kick': 'x..x..x.x..x..x.', 'snare': '....X.......X...', 'hat': 'x.xxx.xxx.xxx.xx',
                       'ohh': '..x...........x.'}, vel=74)
    for b in range(2):
        kit.play(slam_beat, mbar(slam, b + 1))
        r = ROOTS[('Dm', 'Eb')[b]]
        bass.play(Clip([(i * 0.5, 0.35, r + (12 if i % 2 else 0), 96 if i % 2 == 0 else 82) for i in range(8)],
                       length=4), mbar(slam, b + 1))
    # "Braces don't fail me now!" (124.05) - a glinting glock 'ting' on the braces close-up, theme fragment after
    glock.play(notes('vel=84 A7/16 D8/8'), s.beat_at(124.05 - 7.909396 + 1.80))
    stab.play(Clip([(2.5, 0.25, p, 86) for p in (50, 57, 62)] + [(3.5, 0.25, p, 90) for p in (51, 58, 63)],
                   length=4), mbar(slam, 2))
    # bar 3: the floss snaps, the queen inhales - snare build + bass climb into the rally sting
    kit.play(drums({'snare': '2233445566778...', 'kick': 'x...x...x.x.x...', 'tom_lo': '........x.x.x...'},
                   vel=66), mbar(slam, 3))
    bass.play(Clip([(i * 0.5, 0.35, p, 92) for i, p in enumerate((33, 35, 36, 37, 38, 39, 40))], length=4),
              mbar(slam, 3))
    lead.play(notes('vel=76 D5/8 F5/8 E5/8 D5/8 A5/4 r/4').arch(1, 0.5), mbar(slam, 2))

    # ================================================================== F3b: the rally - villain march
    big_hit(rally.start, pitches=(26, 38, 50, 53, 57), ring=1.4, stab_notes=(50, 53, 57, 62), vel=120)
    timp.play(Clip([(0, 1.5, 38, 116)], length=4), rally.start)
    for b in range(3):
        sym, root = lam[b]
        at = mbar(rally, b + 1)
        tones = chord(sym).notes(4)
        top = [t for t in tones if t >= 62][:3] or tones[:3]
        arp = [root + 24] + sorted(top)
        harpsi.play(Clip([(i * 0.5, 0.45, arp[i % len(arp)], 70 if i % 4 == 0 else 60) for i in range(8)],
                         length=4), at)
        buzz.play(Clip([(i * 0.5, 0.42, root - 12 + (12 if i % 4 == 3 else 0), 84 + b * 6) for i in range(8)],
                       length=4), at)
        # the guards stagger up: a dazed, lurching tuba oom-pah and marching timpani, steadier every bar
        tuba.play(Clip([(0.25 if b == 0 else 0, 0.8, root - 12, 80 + b * 6), (2.15 if b == 0 else 2, 0.8, root - 5, 72 + b * 6)],
                       length=4), at)
        timp.play(Clip([(1, 0.5, root, 56 + b * 10), (3, 0.5, root, 56 + b * 10)], length=4), at)
        march.play(drums({'snare': 'x..x..x.x...x...', 'kick': 'x.......x.......'}, vel=50 + b * 8), at)
    # bar 4: the softener bottle comes out (F3c cut 134.76) - snare + timpani roll into the fanfare
    r4 = mbar(rally, 4)
    kit.play(drums({'snare': '1122334455667788', 'kick': 'x...x...x...x...'}, vel=70), r4)
    timp.play(Clip([(i * 0.25, 0.25, 33, 50 + i * 4) for i in range(15)], length=4), r4)
    bass.play(Clip([(i * 0.5, 0.35, p, 86 + i * 2) for i, p in enumerate((33, 35, 37, 38, 40, 42, 44))], length=4),
              r4)

    # ================================================================== F3c: fabric-softener fanfare, then poofs
    # heroic and absurd: a D-major brass fanfare with timpani and crash, the theme turned into a jingle
    big_hit(softener.start, pitches=(38, 50, 54, 57, 62), ring=1.0, stab_notes=(50, 54, 57, 62), vel=118)
    tpt.play(notes('vel=96 D5/8. D5/16 D5/8 F#5/8 A5/4 D6/4 | B5/8 A5/8 G5/8 F#5/8 E5/4 A5/4 | D6/2 r/2')
             .arch(2, 0.4), softener.start)
    fan = [('D', (50, 54, 57)), ('G', (50, 55, 59)), ('A', (49, 52, 57)), ('D', (50, 54, 57))]
    for i, (sym, v) in enumerate(fan[:3]):
        at = mbar(softener, 1, beat=i * 2.0) if i < 2 else mbar(softener, 2, beat=0)
        brass.play(Clip([(0, 0.4, p, 92) for p in v] + [(0.75, 0.25, p, 80) for p in v] +
                        [(1.0, 0.8, p, 88) for p in v], length=2), at)
    brass.play(Clip([(0, 1.6, p, 96) for p in (50, 54, 57, 62)], length=4), mbar(softener, 3))
    timp.play(Clip([(0, 0.5, 38, 100), (1, 0.5, 33, 90), (2, 0.5, 38, 96), (3, 0.25, 33, 84), (3.5, 0.25, 33, 90)],
                   length=4), softener.start)
    timp.play(Clip([(0, 0.5, 31, 96), (2, 0.5, 33, 100)], length=4), mbar(softener, 2))
    for b in range(2):
        kit.play(drums({'snare': 'x..xx.x.x..xx.x.', 'kick': 'x.......x.......', 'hat': 'x.x.x.x.x.x.x.x.'},
                       vel=62), mbar(softener, b + 1))
        bass.play(Clip([(0, 0.4, ROOTS[('D', 'G')[b]], 98), (1, 0.4, ROOTS[('D', 'G')[b]] + 7, 86),
                        (2, 0.4, ROOTS[('D', 'A')[b]], 98), (3, 0.4, ROOTS[('D', 'A')[b]] + 7, 86)], length=4),
                  mbar(softener, b + 1))
    # bars 3-5: the guards go fluffy - poof, poof, poof (open hat 'pff' + music-box plink + a tiny tuba 'pomf'),
    # a bouncy, soft D-major oom-pah underneath (pizzicato + tuba), thin for line 32 (142.41)
    poofs = [(0.0, 79), (1.5, 74), (2.5, 77), (4.0, 81), (5.0, 76), (6.5, 82), (7.5, 78), (9.0, 84), (10.0, 80)]
    p3 = mbar(softener, 3)
    for t, n in poofs:
        march.play(Clip([(0, 0.3, 46, 66)], length=1), p3 + t)
        box.play(Clip([(0, 0.3, n + 12, 70)], length=1), p3 + t)
        tuba.play(Clip([(0, 0.25, 50, 56)], length=1), p3 + t)
        zap.play(Clip([(0, 0.03, 96, 60), (0.03, 0.3, 84, 54)], length=1), p3 + t)
    for b in range(3):
        sym, root = (('D', 38), ('G', 43), ('A', 45))[b]
        tuba.play(Clip([(0, 0.4, root - 12, 72), (2, 0.4, root - 5, 64)], length=4), mbar(softener, b + 3))
        pizz.play(Clip([(1, 0.25, p, 56) for p in chord(sym).notes(4)[:3]] +
                       [(3, 0.25, p, 56) for p in chord(sym).notes(4)[:3]], length=4), mbar(softener, b + 3))
    # a deflating tuba slide into the gross-up
    tuba.play(Clip([(3.0, 0.5, 33, 70), (3.5, 0.5, 32, 64)], length=4), mbar(softener, 5))

    # ================================================================== F3d: gross-up of the foamed captain
    # "eww": a queasy minor-second organ chord, a low tuba, a wobbling theremin drooping down; then the duel pickup
    organ.play(Clip([(0, 7.0, p, 64) for p in (38, 44, 51, 52)], length=8), gross.start)
    tuba.play(Clip([(0, 3.0, 26, 82), (4, 2.5, 25, 74)], length=8), gross.start)
    lead.play(Clip([(0.3, 1.5, 69, 70), (1.8, 1.5, 68, 66), (3.3, 2.4, 62, 60)], length=8), gross.start)
    glock.play(Clip([(0, 0.4, 87, 50), (0.25, 0.4, 88, 46)], length=4), gross.start)
    march.play(drums({'snare': '........x.x.xxxx'}, vel=58), mbar(gross, 2))

    # ================================================================== F3d/e: the toothpick duel (swashbuckler)
    # galloping 6/8-feel in 4/4 (8th + two 16ths), D minor; fencing harpsichord runs, 'clang' on the parries
    duel_prog = [('Dm', 38), ('Gm', 43), ('A7', 45), ('Dm', 38), ('Bb', 34), ('A7', 33), ('A7', 33)]
    gallop = drums({'snare': 'x.xxx.xxx.xxx.xx', 'kick': 'x.......x.......', 'hat': 'x...x...x...x...'}, vel=60)
    for b, (sym, r) in enumerate(duel_prog):
        at = mbar(duel, b + 1)
        loud = 1.0 if b < 5 else 1.12
        if b < 6:
            kit.play(gallop, at)
        beats_ = (0, 1, 2, 3) if b < 6 else (0, 1, 2)            # bar 7: the last beat is held free for the poke
        bass.play(Clip([(beat, 0.35, r, int(96 * loud)) for beat in beats_] +
                       [(beat + 0.5, 0.2, r + 12, int(76 * loud)) for beat in beats_] +
                       [(beat + 0.75, 0.2, r + 7, int(72 * loud)) for beat in beats_], length=4), at)
        tones = [t - 12 if t > 69 else t for t in chord(sym).notes(4)][:3]
        run = sorted(tones) + [t + 12 for t in sorted(tones)]
        harpsi.play(Clip([(i * 0.25, 0.22, run[i % 6] if (i // 6) % 2 == 0 else run[5 - i % 6], 58 + (i % 4 == 0) * 10)
                          for i in range(16 if b < 6 else 12)], length=4), at)
    # parry clangs (glock + cowbell) in the gaps and on the action
    for t in (6.5, 10.0, 11.5, 15.0, 17.5, 21.5, 22.5):
        glock.play(Clip([(0, 0.3, 93, 82)], length=1), duel.start + t)
        march.play(Clip([(0, 0.2, 56, 70)], length=1), duel.start + t)
    # the trumpet swashbuckler call in the gap after line 33 (150.66 - 152.16) and after line 34 (154.19 - 154.79)
    tpt.play(notes('vel=90 A4/8 D5/16 D5/16 D5/8 F5/8 A5/4. G5/8 | F5/8 E5/8 D5/4').arch(1, 0.4),
             mbar(duel, 2, beat=2.0))
    tpt.play(notes('vel=88 A5/16 A5/16 Bb5/8 A5/8 G5/8').arch(1, 0.4), mbar(duel, 5, beat=0.5))
    brass.play(Clip([(0, 0.3, p, 84) for p in (50, 53, 57)] + [(0.75, 0.3, p, 88) for p in (50, 53, 57)], length=4),
               mbar(duel, 3))
    # bars 6-7 (after line 35): the theremin hero line + the climb toward the poke
    lead.play(notes('vel=84 D5/8 F5/8 A5/8 D6/8 C#6/4 A5/4 | Bb5/8 A5/8 G5/8 F5/8 E5/4 r/4').arch(2, 0.5),
              mbar(duel, 6))
    kit.play(drums({'snare': 'x.xxx.xxx.xxxx..', 'kick': 'x...x...x...x...', 'tom_lo': '............x...'},
                   vel=72), mbar(duel, 7))
    brass.play(Clip([(i, 0.5 if i < 3 else 0.35, p, 80 + i * 6) for i in range(4) for p in (45 + i, 49 + i, 52 + i)], length=4),
               mbar(duel, 7))

    # ================================================================== F3e: the poke, then the build to CABLE
    # the poke: a 'boing' (tuba up + zap slide up) as the captain flies off, kick + crash
    kit.play(drums({'kick': 'X', 'crash': 'X'}, bars=1, vel=110), poke.start)
    boom.play(Clip([(0, 1.5, 38, 110)], length=4), poke.start)
    stab.play(Clip([(0, 0.3, p, 112) for p in (50, 57, 62, 66)], length=4), poke.start)
    tuba.play(Clip([(0, 0.3, 26, 112), (0.3, 0.5, 38, 104)], length=4), poke.start)
    zap.play(Clip([(0, 0.05, 50, 100), (0.05, 1.6, 96, 92)], length=4), poke.start)
    glock.play(notes('vel=80 D7/16 A7/16 D8/8'), poke.start + 0.5)
    # bar 1 rest of it: comic beat (pizz tiptoe), bar 2 under line 36: snare roll + bass climb + ray riser
    pizz.play(Clip([(2 + i * 0.5, 0.2, p, 70) for i, p in enumerate((57, 62, 57, 62))], length=4), poke.start)
    p2 = mbar(poke, 2)
    kit.play(drums({'snare': '11223344556677..', 'kick': 'x...x...x.x.x...', 'hat': 'x.x.x.x.x.x.x...'},
                   vel=66), p2)
    timp.play(Clip([(i * 0.25, 0.25, 33, 50 + i * 4) for i in range(14)], length=4), p2)
    bass.play(Clip([(i * 0.5, 0.35, p, 84 + i * 3) for i, p in enumerate((33, 35, 36, 37, 38, 39, 40))],
                   length=4), p2)
    trem.play(Clip([(0, 3.4, p, 70) for p in (45, 49, 52, 57)], length=4), p2)          # a breath before CABLE
    zap.play(Clip([(0, 0.05, 38, 60), (0.05, 3.3, 84, 70)], length=4), p2)

    # ================================================================== "Pull the CABLE!" - the hit, then a roll
    big_hit(cable.start, pitches=(33, 45, 52, 57, 61), ring=1.6, stab_notes=(49, 52, 57, 61), vel=122)
    timp.play(Clip([(0, 1, 33, 118)] + [(1 + i * 0.25, 0.25, 33, 60 + i * 4) for i in range(11)], length=4),
              cable.start)
    lead.play(Clip([(0, 0.4, 69, 90), (0.4, 2.0, 81, 92)], length=4), cable.start)
    trem.play(Clip([(0.5, 3.4, p, 76) for p in (45, 49, 52, 55)], length=4), cable.start)

    # ================================================================== F4/F5: meltdown + chase, flash build
    kit.play(drums({'kick': 'X', 'crash': 'X'}, bars=1, vel=100), melt.start)
    stab.play(Clip([(0, 0.6, p, 104) for p in (50, 57, 62)], length=4), melt.start)
    for b in range(3):
        kit.play(slam_beat if b < 2 else action2, mbar(melt, b + 1))
        sym = PROG[b % 4]
        r = ROOTS[sym]
        bass.play(Clip([(i * 0.5, 0.35, r + (12 if i % 2 else 0), 100 if i % 2 == 0 else 86) for i in range(8)],
                       length=4), mbar(melt, b + 1))
    for b, (frag, st) in enumerate([('D5/8 F5/8 E5/8 D5/8 A5/2', (50, 57, 62)), ('Bb5/4 A5/4 G5/4 A5/4', (51, 58, 63)),
                                    ('Eb6/4 D6/8 C6/8 Bb5/4 A5/4', (45, 52, 61))]):
        lead.play(notes(f'vel=80 {frag}').arch(1, 0.5), mbar(melt, b + 1, beat=0.5) if b == 0 else mbar(melt, b + 1))
        stab.play(Clip([(2.5, 0.25, p, 90) for p in st] + [(3.5, 0.25, p, 96) for p in st], length=4),
                  mbar(melt, b + 1))
    # bar 4: "Reverse polarity!" - snare build + riser into the flash
    kit.play(drums({'snare': '2233445566778..', 'kick': 'x...x...x.x.x...', 'tom_lo': '........x.x.x...'},
                   vel=70), mbar(melt, 4))
    bass.play(Clip([(i * 0.5, 0.35, p, 100) for i, p in enumerate((38, 40, 41, 43, 45, 46, 48, 49))], length=4),
              mbar(melt, 4))
    zap.play(Clip([(0, 0.05, 38, 70), (0.05, 3.9, 86, 80)], length=4), mbar(melt, 4))
    zap_auto += [hold(shrink.end, mbar(melt, 4), -10), ramp(mbar(melt, 4), home.start, -16, -4),
                 hold(home.start, home.end, -4)]
    zap.automate('gainDb', *zap_auto)

    # ================================================================== G: the flash, then home
    big_hit(home.start, pitches=(26, 38, 50, 54, 57, 62), ring=3.0, stab_notes=(50, 54, 57, 62, 66), vel=124)
    timp.play(Clip([(0, 2, 38, 110)], length=4), home.start)
    glock.play(notes('vel=86 D6/16 F#6/16 A6/16 D7/16 F#7/16 A7/16 D8/8'), home.start)
    warm = [('D', (50, 54, 57, 62), 38), ('G', (50, 55, 59, 62), 43), ('A', (49, 52, 57, 61), 45)]
    for b, (sym, voicing, root) in enumerate(warm):
        at = mbar(home, b + 2)
        organ.play(Clip([(0, 3.9, p, 62) for p in voicing], length=4), at)
        pad.play(Clip([(0, 4.0, root, 52), (0, 4.0, root + 12, 48)], length=4), at)
        bass.play(Clip([(0, 0.8, root, 80), (2, 0.8, root + 7, 70), (3.5, 0.4, root + 12, 60)], length=4), at)
    lead.play(notes('vel=72 D5/2 F#5/4 E5/8 D5/8 | B5/2. A5/4 | G5/4 F#5/4 E5/4 C#5/4').arch(3, 0.5), mbar(home, 2))

    # ================================================================== the last burp: comic sting, then decay
    big_hit(sting.start, pitches=(38, 50, 54, 57, 62), ring=1.0, stab_notes=(50, 54, 57, 62), vel=118)
    tuba.play(Clip([(0, 0.35, 26, 118), (0.5, 1.2, 33, 100), (1.75, 1.6, 26, 110)], length=4), sting.start)
    lead.play(Clip([(0, 0.4, 62, 90), (0.4, 1.2, 81, 94), (1.6, 1.4, 74, 86)], length=4), sting.start)
    organ.play(Clip([(0, 6.0, p, 60) for p in (50, 54, 57, 62)], length=8), mbar(sting, 2))
    pad.play(Clip([(0, 6.0, 38, 50), (0, 6.0, 50, 46)], length=8), mbar(sting, 2))
    box.play(notes('vel=64 A6/8 D7/8 F#7/8 r/8 D7/2').arch(1, 0.5), mbar(sting, 2, beat=1))

    buzz.automate('gainDb', *buzz_auto, hold(queen.end, rally.start, -6), ramp(rally.start, mbar(rally, 4), -6, -2),
                  hold(mbar(rally, 4), sting.end, -6))
    pad.automate('gainDb', hold(home.start, home.end, -4))
    s.master.automate('gainDb', *master_gate, hold(slam.start, mbar(sting, 2, beat=2), 0),
                      ramp(mbar(sting, 2, beat=2), sting.end, 0, -60))
    return s
