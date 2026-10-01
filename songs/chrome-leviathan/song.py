"""Chrome Leviathan - darksynth (Perturbator / Carpenter Brut), 124 BPM, C# minor with the phrygian bII (D).

Sub-style: Darksynth. Built on the reference-calibrated band preset bands.darksynth (distorted TR-909, growl bass,
dark pad, 16th sequence, distorted brass stabs, sync lead, 224XL dark hall + IR plate, echo, master/darksynth), plus
a sampled lead guitar (FSBS DI -> Marshall 4x12) for the solo, a real choir, a vocoder robot, a keytar and fx.

Form (120 bars at 124 BPM, ritardando + fermata on the last chord, 3:55 + tail = 4:02):
  intro 8 | verse 16 | build 8 | chorus 16 | verse2 8 | build2 8 | chorus2 16 | breakdown 8 | solo 8 |
  final 16 | outro 8

Ideas
  * The signature is the phrygian neighbour cell C#-D-C# in a 3+3+2 sixteenth rhythm. The intro whispers it on a
    filtered lead, the verse teases it an octave down, the chorus hook is built from it: the cell, then G#-A-G#;
    bar 3 sequences it up (A-B-A, C#-D-C# over F#m), the phrase climbs to D6 (the b2 over the bII chord) and snarls
    D6 against G# (a tritone) before it falls B#-A-G# onto the dominant.
  * Harmony: verse i i bII bVII (C#m C#m D B), chorus i bVI iv bVII | i bVI bII V (C#m A F#m B | C#m A D G#), build
    bVI-bVII-bII-V (A B D G#: Neapolitan -> dominant), breakdown i bVI iv V (the B theme), solo i bVI bII V.
  * The rolling bass leaves the kick alone in the verses (3 sixteenths per beat); the chorus riff has the same
    character (octave jumps, approach tones, a D-B#-C# enclosure back into the tonic) with ghost roots on the kick
    steps, so the chorus low end is a dense wall (as on the record) instead of a spiky kick.
  * Every repeat changes: verse 1 half 2 gets 16th hats and the tease; verse 2 a new bass riff, ride, ghosts and
    laser answers; chorus 1 half 2 a ride and lead2 answers in the gaps; the hook's 2nd pass ends up on C#6 instead
    of G#5; chorus 2 the choir, a harmony a sixth below, 16th hats; the final chorus the octave double (1st half), then
    the guitar an octave below the lead (2nd half), crashes every 4 bars. Builds: the bass high-pass rises,
    the kick leaves for the whole last bar, 1 beat of silence before the drop.
  * Breakdown: drums out, a new B theme on a keytar over the choir, the robot says "beneath the city ... it wakes".
    Solo: a guitar solo over the driving beat. Ending: the outro strips down in stages, the robot says the title,
    the lead falls D -> C#, the tempo slows into the last chord and the hall rings out.
"""
from agentsound import *
from agentsound import bands, speech
from agentsound import articulation as art
from agentsound.bandlib.rock import FSBS_DI, amp, guitar_di

ANALYSIS = {'profile': 'darksynth'}

METADATA = {'title': 'Chrome Leviathan', 'artist': 'AgentSound', 'album': 'Neon Archive', 'genre': 'Synthwave',
            'year': 2026, 'comment': 'Darksynth, 124 BPM, C# minor / phrygian'}
COVER = {'style': 'darksynth', 'palette': 'violet', 'title': 'CHROME LEVIATHAN', 'subtitle': 'AgentSound',
         'seed': 13}

ACC, GHOST = 120, 70
BASS_TRIM = -1.0
MASTER_COMP, MASTER_GAIN = -15.0, 9.8      # master bus compressor threshold (preset -20), limiter drive
MASTER_TAPE = 6.5                           # master tape drive (preset 9): less soft-clipping of the snare
MASTER_WIDTH = 1.25                         # preset 1.15: a wider wall above 150 Hz (mono below)
KIT_ATTACK = 15.0                           # kit compressor attack (preset 5 ms): the 909 snare/hat attacks punch through


def line(spec, step='1/16', vel=100, gate=0.9):
    """One token per step: note name, '.' rest, '_' hold previous; suffix '!' accent, '?' ghost."""
    st = beats(step)
    notes, t = [], 0.0
    for tok in spec.split():
        if tok == '|':
            continue
        if tok == '.':
            pass
        elif tok == '_':
            if notes:
                n = notes[-1]
                notes[-1] = (n[0], n[1] + st, n[2], n[3])
        else:
            v = vel
            if tok.endswith('!'):
                v, tok = ACC, tok[:-1]
            elif tok.endswith('?'):
                v, tok = GHOST, tok[:-1]
            notes.append((t, st, tok, v))
        t += st
    return Clip([(a, d * gate, p, v) for a, d, p, v in notes], length=t)


def mel(spec, vel=100, gate=0.9):
    """Tokens 'C#5:1/8.' / 'r:1/4' (note value or beats), suffix '!' accent, '?' softer."""
    notes, t = [], 0.0
    for tok in spec.split():
        if tok == '|':
            continue
        p, _, d = tok.partition(':')
        d = beats(d or '1/8')
        if p not in ('r', '.'):
            v = vel
            if p.endswith('!'):
                v, p = min(127, vel + 18), p[:-1]
            elif p.endswith('?'):
                v, p = int(vel * 0.75), p[:-1]
            notes.append((t, d * gate, p, v))
        t += d
    return Clip(notes, length=t)


def ostinato(chords, vel=96):
    """Seq-pulse cell per bar: root, octave, colour, octave, fifth, octave, third, octave (x2)."""
    notes = []
    for b, (root, third, colour) in enumerate(chords):
        r = note(root)
        cell = [r, r + 12, r + colour, r + 12, r + 7, r + 12, r + third, r + 12]
        for i, p in enumerate(cell * 2):
            v = vel + 18 if i % 8 == 0 else (vel if i % 2 == 0 else vel - 18)
            notes.append((b * 4 + i * 0.25, 0.22, p, min(127, v)))
    return Clip(notes, length=4 * len(chords))


def ghost_kick(bar):
    """Fill the rests on the kick steps (every 4th 16th) with a ghost of the bar's root: the rolling wall."""
    toks = bar.split()
    root = toks[1]
    return ' '.join((root + '?') if (i % 4 == 0 and tok == '.') else tok for i, tok in enumerate(toks))


def build() -> Song:
    s = Song('Chrome Leviathan', tempo=124, key='C# minor', seed=13, tail=7.0)

    intro = s.section('intro', bars=8)
    verse = s.section('verse', bars=16)
    build1 = s.section('build', bars=8)
    chorus = s.section('chorus', bars=16)
    verse2 = s.section('verse2', bars=8)
    build2 = s.section('build2', bars=8)
    chorus2 = s.section('chorus2', bars=16)
    brk = s.section('breakdown', bars=8)
    solo_s = s.section('solo', bars=8)
    final = s.section('final', bars=16)
    outro = s.section('outro', bars=8)

    # the last two bars slow down into the final chord (the hall rings out in the tail)
    s.ritardando((outro.bar(6), outro.bar(7)), to=0.72, a_tempo=False)
    s.fermata(outro.bar(7), hold=4)                          # the last chord rings

    # ------------------------------------------------------------------ the band
    b = bands.make('darksynth', s)
    # the preset's master with less bus compression (the sections keep their contrast), no presence lift (the lead and
    # guitar bring plenty) and half the air shelf
    mfx = s.master.fx
    ci = next(i for i, f in enumerate(mfx) if f.type == 'compressor')
    mfx[ci] = mfx[ci].but(threshold=MASTER_COMP)
    mfx[0] = mfx[0].but(**{'peak3.freq': 2600, 'peak3.gain': -1.5, 'peak3.q': 0.6, 'high.gain': 1.5})
    li = next(i for i, f in enumerate(mfx) if f.type == 'limiter')
    mfx[li] = mfx[li].but(gain=MASTER_GAIN)
    ti = next(i for i, f in enumerate(mfx) if f.type == 'tape')
    mfx[ti] = mfx[ti].but(drive=MASTER_TAPE)
    wi = next(i for i, f in enumerate(mfx) if f.type == 'width')
    mfx[wi] = mfx[wi].but(width=MASTER_WIDTH)
    kit, bass, pad, seq, stabs, lead = b.drums, b.bass, b.pad, b.arp, b.stab, b.lead
    hall, plate, echo = b.buses['hall'], b.buses['plate'], b.buses['echo']
    # the IR hall and the gated burst are decorrelated (~110-150 % side/mid): narrowed (more than the preset, under
    # the wider master), so the pad-only intro and the tail stay mono-safe on a phone speaker (correlation >= 0)
    hall.add_fx(fx.width(width=0.7))
    b.buses['gated'].add_fx(fx.width(width=0.7))
    shimmer = s.bus('shimmer', 'bus/shimmer')
    shimmer.add_fx(fx.width(width=0.8))
    lead.add_fx(fx.eq({'peak1.freq': 1100, 'peak1.gain': -1.5, 'peak1.q': 2.0,
                       'peak2.freq': 1900, 'peak2.gain': -2.5, 'peak2.q': 0.8,
                       'peak3.freq': 3000, 'peak3.gain': -3.0, 'peak3.q': 0.8}))
    kit.add_fx(fx.eq({'high.freq': 6000, 'high.gain': -4.0}))
    ki = next(i for i, f in enumerate(kit.fx) if f.type == 'compressor')
    kit.fx[ki] = kit.fx[ki].but(attack=KIT_ATTACK)
    # bass: shelf + compressor BEFORE the preset's kick ducker (a compressor after it pulled the pump back up and
    # left the bass a flat wall under the kick), and a deeper pump
    di = next(i for i, f in enumerate(bass.fx) if f.type == 'ducker')
    bass.fx[di] = bass.fx[di].but(depth=6)
    bass.fx[di:di] = [fx.eq({'low.freq': 45, 'low.gain': 4.5, 'peak1.freq': 170, 'peak1.gain': 4.0, 'peak1.q': 0.7}),
                      fx.compressor(threshold=-26, ratio=5, knee=6, attack=2, release=70, automakeup='on')]
    bass.gain_db = BASS_TRIM

    # ------------------------------------------------------------------ harmony
    verse_prog = s.prog('i i bII bVII')                       # C#m C#m D B
    build_prog = s.prog('bVI:2 bVII:2 bII:2 V:2')             # A B D G#  (Neapolitan -> V)
    chorus_prog = s.prog('i bVI iv bVII i bVI bII V')        # C#m A F#m B | C#m A D G#
    brk_prog = s.prog('i:2 bVI:2 iv:2 V:2')                   # the B theme: C#m A F#m G#
    solo_prog = s.prog('i bVI bII V')                         # C#m A D G#
    outro_prog = s.prog('i i bII bVII bII:2 i:2')                # the riff's chords, then bII -> i

    # seq-pulse cells (root, third, colour interval)
    CSm, A_, Fm, B_ = ('C#3', 3, 10), ('A2', 4, 11), ('F#2', 3, 10), ('B2', 4, 9)
    D_, Gs = ('D3', 4, 11), ('G#2', 4, 10)
    ost_verse = ostinato([CSm, CSm, D_, B_])
    ost_build = ostinato([A_, A_, B_, B_, D_, D_, Gs, Gs])
    ost_chorus = ostinato([CSm, A_, Fm, B_, CSm, A_, D_, Gs])
    ost_brk = ostinato([CSm, CSm, A_, A_, Fm, Fm, Gs, Gs])
    ost_solo = ostinato([CSm, A_, D_, Gs])

    # ------------------------------------------------------------------ melody
    # the hook: the C#-D-C# neighbour cell (3+3+2 sixteenths), busy bars alternating with held ones
    hook_a = mel('C#5!:1/8. D5:1/8. C#5:1/8 G#5!:1/8. A5:1/8. G#5:1/8 | E5!:1/8. F#5:1/8. E5:1/8 C#5:1/2 '
                 '| A5!:1/8. B5:1/8. A5:1/8 C#6!:1/8. D6:1/8. C#6:1/8 | B5!:1/8. A5:1/8. F#5:1/8 D#5:1/2 '
                 '| C#5!:1/8. D5:1/8. C#5:1/8 G#5!:1/8. A5:1/8. G#5:1/8 | E5!:1/8. F#5:1/8. E5:1/8 C#5:1/4 A5:1/4 '
                 '| D6!:1/8. C#6:1/8. A5:1/8 D6!:1/2', vel=104)
    end_1 = mel('D6!:1/8. C6:1/8. A5:1/8 G#5:1/2', vel=104)                 # snarl D over G#, fall onto V
    end_2 = mel('C6!:1/8. D6:1/8. C6:1/8 G#5:1/4 C#6!:1/4', vel=106)          # 2nd pass: up into the tonic
    hook = hook_a + end_1                                     # 8 bars
    hook2 = hook_a + end_2
    tease = mel('C#4:1/8. D4:1/8. C#4:1/8 r:1/2 | r:1/2 G#4:1/8. A4:1/8. G#4:1/8 '
                '| D4:1/8. E4:1/8. D4:1/8 r:1/2 | r:1/2 A4:1/8. B4:1/8. A4:1/8', vel=96)
    whisper = mel('C#5:1/8. D5:1/8. C#5:1/8 r:1/2 | r:4 | D5:1/8. E5:1/8. D5:1/8 r:1/4 A4:1/4 '
                  '| F#4:1/2. G#4:1/4', vel=84)
    call_only = mel('C#5:1/8. D5:1/8. C#5:1/8 G#5:1/8. A5:1/8. G#5:1/8 | r:4 '
                    '| D5:1/8. E5:1/8. D5:1/8 A5:1/8. B5:1/8. A5:1/8 | r:4', vel=98)
    # answers in the half-note gaps of the hook (bars 2, 4, 6 beats 3-4)
    answers = mel('r:4 | r:2 C#6:1/8. D6:1/8. C#6:1/8 | r:4 | r:2 F#5:1/8. G#5:1/8. A5:1/8 '
                  '| r:4 | r:4 | r:2 A5:1/8. F#5:1/8. D5:1/8 | r:4', vel=92)
    # harmony for chorus 2 / final: a diatonic sixth below the hook (chord tones on the accents)
    harm_a = mel('E4:1/8. F#4:1/8. E4:1/8 B4:1/8. C#5:1/8. B4:1/8 | A4:1/8. B4:1/8. A4:1/8 E4:1/2 '
                 '| C#5:1/8. D5:1/8. C#5:1/8 E5:1/8. F#5:1/8. E5:1/8 | D#5:1/8. C#5:1/8. A4:1/8 F#4:1/2 '
                 '| E4:1/8. F#4:1/8. E4:1/8 B4:1/8. C#5:1/8. B4:1/8 | A4:1/8. B4:1/8. A4:1/8 E4:1/4 C#5:1/4 '
                 '| F#5:1/8. E5:1/8. D5:1/8 F#5:1/2', vel=92)
    harm = harm_a + mel('F#5:1/8. D#5:1/8. C5:1/8 C5:1/2', vel=92)
    harm2 = harm_a + mel('D#5:1/8. F#5:1/8. D#5:1/8 C5:1/4 E5:1/4', vel=94)
    # breakdown B theme (4 bars, augmented to 8)
    b_theme = mel('G#4:1 A4:1 G#4:0.5 E4:0.5 D4:1 | C#4:4 | A4:1 B4:1 A4:0.5 F#4:0.5 D4:1 | C4:4', vel=100)

    # ------------------------------------------------------------------ bass riffs (16ths, off the kick)
    riff = line('. C#2 C#2 C#2! . C#2 C#2 C#3 . C#2 C#2 C#2! . C#3 B2 G#2 '
                '| . C#2 C#2 C#2! . C#2 C#2 C#3 . C#2 C#2 E2! . D2! . C#2 '
                '| . D2 D2 D2! . D2 D2 D3 . D2 D2 D2! . D3 C#3 A2 '
                '| . B1 B1 B1! . B1 B1 B2 . B1 B1 B1! . B2 A2 C2!')
    riff2 = line('. C#2 C#2 C#2! . C#2 C#3 C#2 . C#2 C#2 C#2! . C#3 B2 G#2 '
                 '| . C#2 C#3 C#2! . C#2 C#3 C#2 . C#2 C#2 E2! . D2! . C#2 '
                 '| . D2 D3 D2! . D2 D3 D2 . D2 D3 D2! . D3 C#3 A2 '
                 '| . B1 B2 B1! . B1 B2 B1 . B1 B2 B1! . B2 A2 C2!')
    bass_chorus = line(' '.join(ghost_kick(bar) for bar in (
        '. C#2 C#2 C#2! . C#2 C#3 C#2 . C#2 C#2 C#2! . C#3 C#2 B1',
        '. A1 A1 A1! . A1 A2 A1 . A1 A1 A1! . A2 A1 G#1',
        '. F#1 F#1 F#1! . F#1 F#2 F#1 . F#1 F#1 F#1! . F#2 A1 A#1',
        '. B1 B1 B1! . B1 B2 B1 . B1 B1 B1! . B2 D2! C2!',
        '. C#2 C#2 C#2! . C#2 C#3 C#2 . C#2 C#2 C#2! . C#3 C#2 B1',
        '. A1 A1 A1! . A1 A2 A1 . A1 A1 A1! . A2 B1 C#2',
        '. D2 D2 D2! . D2 D3 D2 . D2 D2 D2! . D3 B1 A1',
        '. G#1 G#1 G#1! . G#1 G#2 G#1 . G#1 G#1 G#1! . D2! . C2!')))
    bass_build_a = line('. . A1! _ . . A1! _ . . A1! _ . . A1! _ ' * 2 + '. . B1! _ . . B1! _ . . B1! _ . . B1! _ ' * 2)
    bass_build_b = line('. . D2 D2! . . D2 D2! . . D2 D2! . D2 D2 D3 ' * 2
                        + '. . G#1 G#1! . . G#1 G#1! . G#1 G#1 G#2 . G#1 G#2 G#2! ' * 2)
    bass_brk = line('C#2! _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ' * 2 + 'A1! _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ' * 2
                    + 'F#1! _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ' * 2 + 'G#1! _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ ' * 2,
                    vel=96, gate=0.97)
    bass_solo = line('. C#2 C#2 C#2! . C#2 C#3 C#2 . C#2 C#2 C#2! . C#3 C#2 B1 '
                     '| . A1 A1 A1! . A1 A2 A1 . A1 A1 A1! . A2 B1 C#2 '
                     '| . D2 D2 D2! . D2 D3 D2 . D2 D2 D2! . D3 B1 A1 '
                     '| . G#1 G#1 G#1! . G#1 G#2 G#1 . G#1 G#2 G#1! . D2! . C2!')

    # ------------------------------------------------------------------ drums (the 909 of the preset)
    K4 = 'x...x...x...x...'
    dr_intro = drums({'kick': 'x.........x.....', 'hat': '..x...x...x...x.'})
    dr_v1a = drums({'kick': K4 + K4, 'snare': '....x.......x...' * 2,
                    'hat': '..x...x...x...x.' + '..x...x...x.....', 'ohh': '................' + '..............x.'})
    dr_v1b = drums({'kick': K4 + K4, 'snare': '....x.......x...' + '....x.......x..o',
                    'hat': 'x.xxx.xxx.xxx.xx' + 'x.xxx.xxx.xxx.x.', 'ohh': '................' + '..............x.'})
    dr_chorus = drums({'kick': K4, 'snare': '....X.......X...', 'clap': '....x.......x...',
                       'hat': 'x.xox.xox.xox.xo', 'ohh': '..x...x...x...x.'})
    dr_chorus_b = drums({'kick': K4, 'snare': '....X.......X...', 'clap': '....x.......x...',
                         'ride': 'x.x.x.x.x.x.x.x.', 'hat': 'x...x...x...x...', 'ohh': '..x...x...x...x.'})
    dr_v2 = drums({'kick': 'x...x...x...x.x.' + K4, 'snare': '....x..o....x..o' + '....x..o....x.oo',
                   'ride': 'x.x.x.x.x.x.x.x.', 'hat': '..x...x...x...x.'})
    dr_build = drums({'kick': K4, 'snare': '....x.......x...', 'hat': '..x...x...x...x.'})
    dr_build2 = drums({'kick': K4, 'hat': 'xxxxxxxxxxxxxxxx', 'clap': '....x.......x...'})
    toms_b2 = drums({'tom_mid': 'x..x..x.x..x..x.', 'tom_hi': '......x.......x.', 'kick': K4,
                     'snare': '....x.......x...'})
    heart = drums({'kick': 'x..x............', 'rim': '........x.......'}, vel=80)
    dr_solo = drums({'kick': K4, 'snare': '....X.......X...', 'clap': '....x.......x...',
                     'hat': 'xxXxxxXxxxXxxxXx', 'ohh': '..............x.', 'ride': 'x...x...x...x...'})
    # the final groove: ride on the beats, tight accented off-beat hats (no open-hat wash under the crashes)
    dr_final = drums({'kick': K4, 'snare': '....X.......X...', 'clap': '....x.......x...',
                      'hat': 'x.Xxx.Xxx.Xxx.Xx', 'ride': 'x...x...x...x...'})

    # ------------------------------------------------------------------ extra tracks
    choir = s.track('choir', 'gm/choir_aahs', gain_db=-4, fx=[fx.eq({'hp.freq': 180, 'peak1.freq': 400,
                                                                    'peak1.gain': -2.5})],
                    sends={hall: -8, shimmer: -18})
    lead2 = s.track('lead2', 'synthwave/sync_lead', gain_db=-6, pan=-0.3,
                    fx=[fx.saturator(mode='tube', drive=6), fx.eq({'hp.freq': 250, 'peak2.freq': 900,
                                                                   'peak2.gain': -3, 'peak3.freq': 1800,
                                                                   'peak3.gain': -2.5, 'peak3.q': 1.2})],
                    sends={hall: -9, echo: -12})
    dbl = s.track('dbl', 'synthwave/supersaw_lead', gain_db=-9,
                  fx=[fx.eq({'hp.freq': 220, 'peak3.freq': 3500, 'peak3.gain': -3})], sends={hall: -10})
    keytar = s.track('keytar', 'synthwave/solo_lead', gain_db=-6, sends={hall: -7, echo: -10, shimmer: -14})
    gtr = s.track('gtr', guitar_di(FSBS_DI, 'chrome-leviathan', 'gtr', articulations=(), mono='legato',
                                   legatotime=30, glideshape='fast'),
                  gain_db=-9.5,
                  fx=amp('lead') + [fx.compressor(threshold=-24, ratio=3, attack=8, release=120, automakeup='on'),
                                    fx.eq({'peak1.freq': 300, 'peak1.gain': -2.0, 'peak2.freq': 1700,
                                           'peak2.gain': 1.0, 'peak3.freq': 3000, 'peak3.gain': -3.5,
                                           'lp.freq': 7500})],
                  sends={echo: -9, hall: -10, plate: -16}).humanize(4, 6)
    gtr.add_fx(fx.microshift(style='smooth', detune=9, mix=0.3))
    snare = s.track('snare', 'sampled/80s_gated_kit', gain_db=0, sends={plate: -16},
                    fx=[fx.eq({'hp.freq': 90, 'peak2.freq': 220, 'peak2.gain': 2.0, 'peak2.q': 1.0,
                                             'high.freq': 5600, 'high.gain': -6})]).humanize(2, 4)
    laser = s.track('laser', 'synthwave/laser', gain_db=-8, pan=0.35, sends={echo: -12})
    riser_t = s.track('riser', patches.get('synthwave/noise_riser').with_fx(
        fx.eq({'peak3.freq': 3800, 'peak3.gain': -7, 'peak3.q': 0.7, 'high.freq': 7000, 'high.gain': -3})),
        gain_db=-8, pan=-0.3)
    impact = s.track('impact', 'synthwave/impact', gain_db=-4, sends={hall: -10})
    down = s.track('down', 'synthwave/downlifter', gain_db=-11)

    # the robot: Windows TTS (German voice speaking English), cached in samples/speech/
    vox = speech.words(['chrome leviathan', 'beneath the city', 'it wakes'], voice='onecore:Stefan', rate=-3)
    voice = s.track('voice', vox.instrument())
    robot = s.track('robot', 'synthwave/vocoder_choir', gain_db=-9, sends={hall: -7, echo: -14})

    # ------------------------------------------------------------------ drums placement
    kit.loop(dr_intro, intro.bar(4), bars=3)
    kit.play(snare_roll(4, vel=(40, 110)), intro.bar(7))
    kit.play(crash(96), intro.bar(4))

    kit.loop(dr_v1a, verse, bars=8).loop(dr_v1b, verse.bar(8), bars=8)
    kit.play(crash(), verse).play(crash(100), verse.bar(8))
    kit.play(tom_fill(1), verse.bar(7, beat=3), replace=True)
    kit.play(tom_fill(1), verse.bar(15, beat=3), replace=True)

    kit.loop(dr_build, build1, bars=4)
    kit.loop(drums({'kick': K4}), build1.bar(4), bars=3)
    kit.play(snare_roll(8, step='1/8', vel=(50, 96)), build1.bar(4))
    kit.play(snare_roll(8, build=True, vel=(64, 124)), build1.bar(6))
    kit.clear(build1.beat(-1), build1.end)

    kit.loop(dr_chorus, chorus, bars=8).loop(dr_chorus_b, chorus.bar(8), bars=8)
    kit.play(crash(118), chorus).play(crash(108), chorus.bar(8))
    kit.play(tom_fill(2), chorus.bar(7, beat=2), replace=True)
    kit.play(tom_fill(2), chorus.bar(15, beat=2), replace=True)

    kit.loop(dr_v2, verse2)
    kit.play(crash(104), verse2)

    kit.loop(dr_build2, build2, bars=4).loop(toms_b2, build2.bar(4), bars=3)
    kit.play(snare_roll(4, build=True, vel=(60, 120)), build2.bar(6))
    kit.play(tom_fill(4, vel=(90, 124)), build2.bar(7), replace=True)
    kit.clear(build2.beat(-1), build2.end)

    kit.loop(dr_chorus, chorus2, bars=8).loop(dr_final, chorus2.bar(8), bars=8)
    kit.play(crash(120), chorus2).play(crash(110), chorus2.bar(8))
    kit.play(tom_fill(2), chorus2.bar(7, beat=2), replace=True)
    kit.play(tom_fill(2), chorus2.bar(15, beat=2), replace=True)

    kit.loop(heart, brk.bar(4), bars=4)
    kit.play(snare_roll(4, build=True, vel=(40, 118)), brk.bar(7))

    kit.loop(dr_solo, solo_s)
    kit.play(crash(122), solo_s).play(crash(110), solo_s.bar(4))
    kit.play(tom_fill(2, vel=(96, 126)), solo_s.bar(7, beat=2), replace=True)
    kit.clear(solo_s.beat(-1), solo_s.end)

    kit.loop(dr_final, final)
    for bb in (0, 4, 8, 12):
        kit.play(crash(124 if bb in (0, 8) else 110), final.bar(bb))
    for bb in (3, 7, 11):
        kit.play(tom_fill(1), final.bar(bb, beat=3), replace=True)
    kit.play(tom_fill(4, vel=(96, 126)), final.bar(15), replace=True)

    kit.loop(dr_chorus, outro, bars=4).loop(drums({'kick': K4, 'hat': '..x...x...x...x.'}), outro.bar(4), bars=2)
    kit.play(crash(114), outro)

    # the gated 80s snare under the 909 snare: choruses, solo, final
    big = drums({'snare': '....x.......x...'})
    snare.loop(big, chorus, chorus2, solo_s, final).loop(big, outro, bars=4)
    snare.loop(drums({'snare': '....x.......x...'}, vel=80), build1, bars=4)
    snare.clear(solo_s.beat(-1), solo_s.end)
    for sec, bars_ in ((chorus, (7, 15)), (chorus2, (7, 15)), (final, (15,))):
        for bb in bars_:
            snare.clear(sec.bar(bb, 2), sec.bar(bb + 1))

    # ------------------------------------------------------------------ bass
    bass.loop(riff, verse).loop(riff2, verse2).loop(riff, outro, bars=4)
    bass.play(bass_build_a, build1).play(bass_build_b, build1.bar(4))
    bass.play(bass_build_a, build2).play(bass_build_b, build2.bar(4))
    bass.clear(build1.bar(7), build1.end).clear(build2.beat(-1), build2.end)
    bass.play(line('G#1! _ _ _ _ _ _ _ _ _ _ _', vel=110), build1.bar(7))        # one held note, no kick
    bass.loop(bass_chorus, chorus, chorus2, final)
    bass.play(bass_brk.slice(16, 32), brk.bar(4))                       # the breakdown's first half: no bass
    bass.loop(bass_solo, solo_s)
    bass.clear(solo_s.beat(-1), solo_s.end)
    bass.note('C#2', outro.bar(4), 14, 100)
    bass.note('C#1', outro.bar(7), 4, 110)

    # ------------------------------------------------------------------ seq pulse ostinato
    seq.loop(ost_verse, intro).loop(ost_verse, verse, verse2).loop(ost_build, build1, build2)
    seq.loop(ost_chorus, chorus, chorus2, final)
    seq.play(ost_brk.slice(16, 32), brk.bar(4)).loop(ost_solo, solo_s).play(ost_verse, outro)
    seq.play(ostinato([D_, D_]), outro.bar(4))
    seq.clear(build1.beat(-1), build1.end).clear(build2.beat(-1), build2.end).clear(solo_s.beat(-1), solo_s.end)

    # ------------------------------------------------------------------ pad, stabs, choir
    reg = ('A3', 'A4')
    pad.loop(verse_prog.block(voicing='smooth', register=reg, voices=3), intro, verse, verse2)
    pad.play(build_prog.block(voicing='smooth', register=reg, voices=3), build1)
    pad.play(build_prog.block(voicing='smooth', register=reg, voices=3), build2)
    pad.loop(chorus_prog.block(voicing='smooth', register=reg, voices=3), chorus, chorus2, final)
    pad.play(brk_prog.block(voicing='smooth', register=reg, voices=3), brk)
    pad.loop(solo_prog.block(voicing='smooth', register=reg, voices=3), solo_s)
    choir.loop(solo_prog.block(voicing='open', register=('C#4', 'C#5'), voices=3), solo_s)
    pad.play(outro_prog.block(voicing='smooth', register=reg, voices=3), outro)

    st_reg = ('C#4', 'C#5')
    stab_rh = '........x..x..x.'                                  # 3+3+2 in the second half: the hook's gaps
    stab_ch = chords(chorus_prog, register=st_reg, voices=3, vel=104, rhythm=stab_rh, step='1/16')
    stabs.loop(stab_ch, chorus, chorus2, final)
    stabs.loop(chords(verse_prog, register=st_reg, voices=3, vel=86, rhythm='x.....x.........', step='1/16'),
               verse2)
    stabs.play(chords(build_prog, register=st_reg, voices=3, vel=100, rhythm='x..x..x.x..x..x.', step='1/16')
               .slice(16, 28), build2.bar(4))
    stabs.loop(chords(solo_prog, register=st_reg, voices=3, vel=100, rhythm='x.....x.....x...', step='1/16'),
               solo_s)
    stabs.clear(solo_s.beat(-1), solo_s.end)

    choir_reg = ('C#4', 'C#5')
    choir.play(brk_prog.block(voicing='open', register=('F#3', 'F#4'), voices=3), brk)
    choir.loop(chorus_prog.block(voicing='open', register=choir_reg, voices=3), chorus2, final)
    choir.play(outro_prog.block(voicing='open', register=choir_reg, voices=3).slice(8, 32),
               outro.bar(2))

    # ------------------------------------------------------------------ leads
    lead.play(whisper, intro.bar(4))
    lead.play(tease, verse.bar(8), times=2)
    lead.play(hook, chorus).play(hook2, chorus.bar(8))
    lead.play(call_only, verse2, times=2)
    lead.play(hook, chorus2).play(hook2, chorus2.bar(8))
    lead.play(hook, final).play(hook2, final.bar(8))
    lead.play(mel('D5:1/8. E5:1/8. D5:1/8 A5:1/8. B5:1/8. A5:1/8 | D5:3 C#5:5', vel=94), outro.bar(4))
    lead2.play(answers, chorus.bar(8))
    lead2.play(harm2, chorus2.bar(8)).play(harm, final).play(harm2, final.bar(8))
    dbl.play(hook.octave(-1), final)                          # 2nd half: the guitar takes over the octave below
    keytar.play(art.legato(b_theme.stretch(2).octave(1), overlap=0.05), brk)

    # guitar solo (sounding pitch), then the guitar doubles the hook an octave down in the final's second half
    solo_line = mel('G#4:0.5 C#5:0.5 E5:0.5 F#5:2.5 | A5:0.5 G#5:0.5 E5:0.5 C#5:0.5 E5:1 A5:1 '
                    '| D6:1.5 C#6:0.5 A5:0.5 F#5:0.5 A5:1 | C6:0.5 A5:0.5 G#5:0.5 D#5:0.5 C5:1 G#4:1 '
                    '| G#4:0.25 A4:0.25 B4:0.25 C#5:0.25 D5:0.25 E5:0.25 F#5:0.25 G#5:0.25 B5:2 '
                    '| C#6:0.5 A5:0.5 E5:0.5 C#6:0.5 A5:0.5 E5:0.5 C#6:1 '
                    '| D6:0.5 C#6:0.5 A5:0.5 F#5:0.5 A5:0.5 D6:1.5 | C6:0.5 D6:0.5 C6:0.5 A5:0.5 G#5:2', vel=108,
                    gate=1.0)
    solo_line = art.legato(solo_line, overlap=0.03).glide(100, where=art.leaps(4))
    gtr.play(solo_line, solo_s)
    art.vibrato(gtr, solo_line, solo_s, depth=30, rate=5.6, delay=0.25)
    gtr_dbl = art.legato(hook2.octave(-1), overlap=0.02)
    gtr.play(gtr_dbl, final.bar(8))
    # bends: F#5 -> G#5 (bar 1), B5 -> C#6 (bar 5), D6 up a whole step at its peak (bar 7)
    gtr.automate('instrument.pitchbend', [
        (solo_s.bar(0, 1.5), 0), (solo_s.bar(0, 1.9), 2, 'smooth'), (solo_s.bar(0, 3.9), 2),
        (solo_s.bar(1), 0, 'step'),
        (solo_s.bar(4, 2), 0), (solo_s.bar(4, 2.35), 2, 'smooth'), (solo_s.bar(4, 3.95), 2),
        (solo_s.bar(5), 0, 'step'),
        (solo_s.bar(6, 2.6), 0), (solo_s.bar(6, 3.1), 2, 'smooth'), (solo_s.bar(6, 3.6), 2),
        (solo_s.bar(6, 3.95), 0, 'smooth')])
    gtr.automate('send.echo', hold(solo_s.start, solo_s.bar(7, 2), -9),
                 ramp(solo_s.bar(7, 2), solo_s.bar(7, 2.5), -9, -3), hold(solo_s.bar(7, 2.5), solo_s.end, -3),
                 ramp(solo_s.end, final.start + 1, -3, -12))

    # lasers answer the verse-2 calls; a sparse laser in verse 1's first half
    for bb in (1, 3, 5, 7):
        laser.play(line('. . . . . . . . C#6 . C#6 . G#5 . . .'), verse2.bar(bb))
    for bb in (3, 7):
        laser.play(line('. . . . . . . . . . . . C#6 . B5 .', vel=84), verse.bar(bb))
    laser.play(line('C#6 . G#5 . C#6 . C6 . C#6 G#5 C#6 C6 C#6 G#5 C#6 C6'), build2.bar(6))

    # ------------------------------------------------------------------ the robot
    voice.play(vox.clip({0: 'chrome leviathan'}), intro.bar(2))
    voice.play(vox.clip({0: 'beneath the city'}), brk.bar(1))
    voice.play(vox.clip({0: 'it wakes'}), brk.bar(5, 2))
    voice.play(vox.clip({0: 'chrome leviathan'}), outro.bar(6))
    for at, dur, notes in ((intro.bar(2), 7.5, ('C#3', 'G#3', 'C#4', 'E4')),
                           (brk.bar(1), 7.5, ('C#3', 'A3', 'C#4', 'E4')),
                           (brk.bar(5, 2), 5.5, ('C#3', 'F#3', 'A3', 'C#4')),
                           (outro.bar(6), 7.5, ('C#3', 'G#3', 'C#4', 'E4'))):
        robot.play(Clip([(0, dur, p, 96) for p in notes], length=dur), at)
    speech.vocode(robot, voice, shift=-4)

    # ------------------------------------------------------------------ fx hits
    impact.note('C#2', intro, 4, 110).note('C#2', chorus, 4, 124).note('C#2', chorus2, 4, 124)
    impact.note('C#2', solo_s, 4, 120).note('C#2', final, 4, 127).note('C#2', outro.bar(7), 8, 118)
    down.note('C#4', verse2, 8, 110).note('C#4', brk, 8, 118).note('C#4', outro.bar(4), 8, 104)
    for sec, L in ((intro, 16), (build1, 32), (build2, 32), (brk, 16)):
        riser_t.note('C#4', sec.end - L, L - 1, 100)
        riser_t.automate('instrument.cutoff', riser(sec.end, length=L, lo=300, hi=12000))
        riser_t.automate('instrument.hpf', riser(sec.end, length=L, lo=20, hi=1500))

    # ------------------------------------------------------------------ movement / automation
    pad.automate('instrument.cutoff', [
        (0, 300), (intro.end, 900, 'exp'), (verse.bar(8), 900), (verse.end, 1150, 'exp'),
        (build1.end, 1900, 'exp'), (chorus.start, 1600), (chorus.end, 1700),
        (verse2.start, 1000), (verse2.end, 1100), (build2.end, 1900, 'exp'),
        (chorus2.start, 1800), (chorus2.end, 1900), (brk.start, 500), (brk.end, 1400, 'exp'),
        (solo_s.start, 1800), (solo_s.end, 2400, 'exp'), (final.start, 2000), (final.end, 2200),
        (outro.start, 2000), (outro.end, 300, 'exp')])
    seq.automate('instrument.cutoff', [
        (0, 450), (intro.end, 1200, 'exp'), (verse.start, 800), (verse.end, 1100, 'exp'), (build1.end, 2600, 'exp'),
        (chorus.start, 1300), (chorus.end, 1300), (verse2.start, 1000), (verse2.end, 1300, 'exp'),
        (build2.end, 2600, 'exp'), (chorus2.start, 1500), (chorus2.end, 1500),
        (brk.start, 400), (brk.end, 900, 'exp'), (solo_s.start, 1500), (solo_s.end, 2200, 'exp'),
        (final.start, 1700), (final.end, 1700), (outro.start, 1400), (outro.end, 300, 'exp')])
    bass.automate('instrument.cutoff', [
        (0, 1500), (verse.end, 1500), (build1.end, 2600, 'exp'), (chorus.start, 1900),
        (verse2.start, 1500), (build2.start, 1500), (build2.end, 2600, 'exp'), (chorus2.start, 1900),
        (brk.start, 500), (brk.end, 900, 'exp'), (solo_s.start, 1900), (final.start, 2100),
        (outro.start, 1500), (outro.end, 400, 'exp')])
    # the drop: the bass loses its low end through each build and gets it back on the downbeat
    bass.automate('instrument.hpf', [
        (0, 10), (build1.start, 10), (build1.bar(7), 160, 'exp'), (build1.end, 180, 'exp'), (chorus.start, 10, 'step'),
        (build2.start, 10), (build2.bar(7), 160, 'exp'), (build2.end, 180, 'exp'), (chorus2.start, 10, 'step')])
    bass.modulate('instrument.cutoff', lfo('sine', rate='1/8', depth=0.25, curve='exp'),
                  window=(chorus.start, None))
    pad.modulate('pan', lfo('triangle', rate='4 bars', depth=0.2))
    # scoops into the held D6 of every hook pass, a -12 st dive on the very last hook note
    pb = []
    for sec in (chorus, chorus2, final):
        for bar in (6, 14):
            pb += [(sec.bar(bar, 1.9), 0), (sec.bar(bar, 2), -2, 'step'), (sec.bar(bar, 2.3), 0, 'smooth')]
    pb += [(final.bar(15, 3.1), 0), (final.bar(15, 3.9), -12, 'smooth'), (final.end, 0, 'step')]
    lead.automate('instrument.pitchbend', pb)
    lead.automate('send.echo', hold(intro.start, final.bar(15, 2), -12),
                  ramp(final.bar(15, 2), final.bar(15, 2.3), -12, -4), hold(final.bar(15, 2.3), final.end, -4),
                  ramp(final.end, outro.bar(1), -4, -12), hold(outro.bar(1), outro.bar(5), -12),
                  ramp(outro.bar(5), outro.bar(6), -12, -5))
    pad.send(shimmer, -30)
    pad.automate('send.shimmer', hold(intro.start, intro.end, -10), hold(verse.start, brk.start, -30),
                 hold(brk.start, brk.end, -8), hold(solo_s.start, outro.start, -30),
                 ramp(outro.start, outro.end, -24, -6))
    choir.automate('send.shimmer', hold(chorus2.start, brk.start, -20), hold(brk.start, brk.end, -9),
                   hold(solo_s.start, outro.start, -20), ramp(outro.start, outro.end, -16, -6))

    # mix rides per section (a 'gainDb' lane is dB on the track's gain_db). A section is a number, or a list of
    # (bar, dB) jumps / (bar, dB, 'ramp') ramps inside it; 'drops' silences the section's last beat.
    def ride(track, levels, drops=()):
        pts, cur = [], None
        for sec in s.sections:
            spec = levels.get(sec.name, 0.0)
            for step in (spec if isinstance(spec, list) else [(0, spec)]):
                bar, v = step[0], step[1]

                at = sec.start + bar * sec.beats_per_bar
                if len(step) > 2 and cur is not None:
                    pts.append((at, v))
                else:
                    if cur is not None:
                        pts.append((at, cur))
                    pts.append((at, v))
                cur = v
            if sec.name in drops:
                pts += [(sec.end - 1, cur), (sec.end - 1, -60.0)]
                cur = -60.0
        pts.append((s.length, cur))
        track.automate('gainDb', pts)

    ride(kit, {'intro': -4, 'verse': [(0, -7), (8, -5)], 'build': [(0, -3), (4, -1.5)], 'verse2': -5,
               'build2': [(0, -3), (4, -1)], 'breakdown': -6, 'solo': -1.5, 'final': 0.5,
               'outro': [(0, -2), (4, -6)]})
    ride(snare, {'build': -3, 'chorus': 2, 'chorus2': 2, 'solo': 1, 'final': 2, 'outro': -2})
    ride(bass, {'verse': [(0, -8), (8, -6)], 'build': [(0, -4), (4, -2)], 'verse2': -6,
                'build2': [(0, -3.5), (4, -1.5)], 'breakdown': -7, 'solo': -2.5, 'final': 0.5,
                'outro': [(0, -3), (4, -6), (8, -18, 'ramp')]})
    ride(seq, {'intro': [(0, -12), (4, -4, 'ramp')], 'verse': -2.5, 'build': -3, 'build2': -3, 'chorus': -2,
               'verse2': -1.5, 'chorus2': -2, 'breakdown': -4, 'solo': -2, 'final': -1.5,
               'outro': [(0, -2), (6, -18, 'ramp')]})
    ride(pad, {'intro': [(0, -16), (4, -3, 'ramp')], 'verse': -6.5, 'build': -2, 'verse2': -5, 'build2': -2,
               'breakdown': -8.5, 'solo': -2, 'outro': [(0, -1), (4, -3), (7, -8, 'ramp')]},
         drops=('build', 'build2', 'solo'))
    ride(choir, {'chorus2': -2, 'breakdown': -6.5, 'solo': -5, 'final': -2.5, 'outro': [(0, -1), (7, -7, 'ramp')]})
    ride(stabs, {'verse2': -8, 'build2': -2, 'solo': -3})
    ride(keytar, {'breakdown': 1.5})
    # the hook sits on top of the wall in every chorus; the guitar leads the solo
    ride(lead, {'verse': -2.5, 'verse2': -1, 'chorus': 1.5, 'chorus2': 2.5, 'final': 2.5})
    ride(gtr, {'solo': 3.0, 'final': 1.5})

    # ------------------------------------------------------------------ extra pump
    s.sidechain(choir, lead2, dbl, key=kit, pitches='kick', depth=4, release=180)
    # the wall steps aside for the snare (2 and 4): the backbeat cracks through the synths
    s.sidechain(pad, seq, stabs, choir, key=kit, pitches=['snare', 'clap'], depth=4, attack=1, release=110)
    s.sidechain(bass, key=kit, pitches=['snare', 'clap'], depth=3, attack=1, release=90)
    return s
