"""Blueprint Boulevard - an original light urban-jazz instrumental in the style of the SimCity 3000 soundtrack
(Jerry Martin and the Maxis audio team, 1999; recipes/simcity.md). Every note is original: own hook, own changes, own
title - only the idiom is borrowed: bright, optimistic, relaxed city-building jazz on a straight-8th groove, the
Rhodes and a live-sounding alto sax in front, a grand piano solo, lydian colour on the IV chord, a sunrise lift
through bVI - bVII. 112 BPM, C major, straight 8ths, ~4:00.
Build: python -m agentsound build songs/blueprint-boulevard

  intro       8   the Rhodes vamps Cmaj9 / Fmaj7#11 alone; bass + drums + shaker join, the vibes hint the hook
  head1      16   the alto states the hook (A: Cmaj9 Fmaj7#11 x2, Em7 A9 Dm9 G13sus4; a second 8 that turns to Fm6)
  lift1       8   the sunrise: Abmaj7#11 Bbmaj9 -> Cmaj9; the sax climbs, the pad and soft horn swells enter
  head2      16   the grand piano takes the hook (pianist.arrange), the sax answers in its gaps
  sax_solo   16   the alto's solo (soloist + the wind player's vocabulary) on the A changes
  piano_solo 16   the piano's solo (soloist + the pianist's vocabulary), the Rhodes lays out
  lift2       8   the sunrise again, the tenor a third under the alto, the horns' festive stabs
  head3      16   the hook last time: the vibes double it an octave up, the second half climbs to the top G5
  outro       4   the vamp, the sax quotes the hook's head
  end         2   Cmaj9 (6/9) rolled into the pedal, ritardando, a cymbal swell (loops back into the intro vamp)

The melody lines are written in F and played a fourth lower (notes(..., transpose=-5)): the Weresax alto's range is
C#3-G#5, the hook sits E4-G5.
"""
from agentsound import *
from agentsound import bands, bassist, drummer, hornist, jazz, mastering, patches, pianist, soloist
from agentsound.bandlib import jazz as jazzband
from agentsound.humanize import touch

ANALYSIS = {'profile': 'pop', 'loudness': [-14.5, -11.0]}
METADATA = {'title': 'Blueprint Boulevard', 'artist': 'AgentSound', 'album': 'City Sessions', 'genre': 'Jazz',
            'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#1f6f8b', '#f2c14e'], 'title': 'blueprint boulevard',
         'subtitle': 'AgentSound - City Sessions', 'seed': 3000}

# the mix engineer's moves (MIX.md)
MIX = {
    'trim': {'bass': -6.5},
    'eq': {'bass': [{'freq': 1000, 'gain': -3.5, 'q': 0.8}, {'freq': 3500, 'gain': -4.0, 'q': 0.7}]},
}

TEMPO = 112
T = -5                 # the lines are written in F, sounding in C (a fourth lower: the alto's range)
SOLO = {}              # 'sax' / 'piano' -> the soloist.Performance
PIANO_DB = -4.0        # the grand peaked +2 dBFS pre-master at 0 dB (the solo's accents)
LIMITER = -5.0         # dB off the funk master's limiter drive: background music breathes (-13 LUFS, not -9.6)

# ------------------------------------------------------------------------------------------------ changes
CHANGES = {
    'In': 'Cmaj9 Fmaj7#11 Cmaj9 Fmaj7#11 | Cmaj9 Fmaj7#11 Dm9 G13sus4',
    'A': 'Cmaj9 Fmaj7#11 Cmaj9 Fmaj7#11 | Em7 A9 Dm9 G13sus4 | Cmaj9 Fmaj7#11 Em7 Am9 | '
         'Dm9 Fm6 Em7:0.5 A7b9:0.5 Dm9:0.5 G13sus4:0.5',
    'B': 'Abmaj7#11 Bbmaj9 Cmaj9 Em7:0.5 A9:0.5 | Fmaj9 Em7 Dm9 G13sus4:0.5 G7b9:0.5',
    'Out': 'Cmaj9 Fmaj7#11 Cmaj9 Fmaj7#11',
    'E': 'Cmaj9:2',
}
FORM = ('intro:In head1:A lift1:B head2:A sax_solo:A piano_solo:A lift2:B head3:A outro:Out end:E')

# ------------------------------------------------------------------------------------------------ the tune
# (written in F; ^peak = the held high notes the wind player leans into)
A_FRONT = ('r/8 A4/8 C5 G5/4.^peak E5/8 D5 | E5/2 r/8 D5/8 C5 A4 | r/8 A4/8 C5 A5/4.^peak G5/8 F5 | E5/2. r/4 | '
           'r/4 E5/8 G5 C6/4^peak B5/8 G5 | A5/4. F#5/8 E5/4 D5 | F5/4. D5/8 Bb4/4 A4 | G4/2. r/4 |')
A_BACK = ('r/8 A4/8 C5 G5/4.^peak E5/8 D5 | E5/2 r/8 F5/8 G5 A5 | C6/4.^peak B5/8 G5/4 E5 | F5/4. E5/8 D5/4 A4 | '
          'Bb4/8 D5 F5 A5~ A5/2 | G5/4 F5 Db5 Bb4 | C5/4 E5 Eb5 C5 | D5/4. C5/8 r/2 |')
# the last head: the second half climbs (the top C6 = sounding G5 held over Em7, the lift into the turnaround)
A_CLIMB = ('r/8 A4/8 C5 G5/4.^peak E5/8 D5 | E5/2 r/8 G5/8 A5 B5 | C6/2.^peak B5/8 G5 | A5/4. G5/8 F5/4 E5 | '
           'D5/8 F5 A5 C6~ C6/2^peak | Bb5/4 G5 F5 Db5 | C5/4 E5 G5 Bb5 | A5:3 r/4 |')
B_LIFT = ('F5/4. G5/8 Ab5/2^peak | Bb5/4. G5/8 F5/2 | A5:3^peak G5/8 F5 | E5/4 C5 F#5 A5 | '
          'C6/4.^peak A5/8 F5/2 | G5/4. E5/8 C5/2 | Bb5/8 A5 G5 F5 D5/4 F5 | G5/2 r/2 |')


def line(spec, vel=96):
    return notes(spec, transpose=T, vel=vel, length='bar')


HOOK_A = line(A_FRONT + ' ' + A_BACK)
HOOK_A3 = line(A_FRONT + ' ' + A_CLIMB)
LIFT = line(B_LIFT)
HOOK = line('r/8 A4/8 C5 G5/4.^peak E5/8 D5 | E5/2 r/2 |')                  # the motif (the solos develop it)
# the sax's answers while the piano has the hook (head2): into bar 9 and into the solo
SAX_ANSWERS = notes('@29.5 A4/8 C5 D5 F5/4 @62 G5/8 F5 D5 C5', transpose=T, vel=88, length=64)
# the outro: the hook's head once more, then a long tonic
SAX_OUT = line('r/8 A4/8 C5 G5/4.^peak E5/8 D5 | E5/2 r/2 | r/8 A4/8 C5 D5/4. C5/8 A4 | C5:4 |')
# the intro: the vibes hint the hook's head, high and soft (bars 5-8)
VIBES_HINT = touch(notes('r:16 r/8 A5/8 C6 G6/4. E6/8 D6 | E6/2 r/2 | r/8 A5/8 C6 A6/4. G6/8 F6 | E6:4 |',
                         transpose=T, vel=70, length=32), 46, 96)
END_CHORD = hold('C3=50 E3=52 A3=54 D4=56 G4=58 E5=62', 7.6, length=8)        # C6/9 (the bass has the C)


def harmony(clip, key):
    """The tenor a diatonic third under the alto (a sixth where the third would fall under C#3)."""
    out = []
    for n in clip:
        h = key.transpose(n.pitch, -2)
        out.append(n._replace(pitch=h if h >= note('A3') else key.transpose(n.pitch, -5)))
    return Clip(out, length=clip.length)


def build() -> Song:
    s = Song('Blueprint Boulevard', tempo=TEMPO, key='C major', seed=3000, tail=6)
    (intro, head1, lift1, head2, sax_solo, piano_solo, lift2, head3, outro, end) = s.form(FORM, parts=CHANGES)
    key = Key('C major')

    # ============================================================== the band
    # the funk_band as a late-90s studio jazz band: the Orange Tree jazz-funk kit on sticks in a short ambience, a
    # clean fingered Jazz bass, a stereo Rhodes, the VPO trumpet + trombone section, the Weresax alto lead (the
    # chicken-scratch guitar stays home)
    b = bands.make('funk_band', s, without=('gtr',), keys='rhodes', lead='sax', ids={'lead': 'sax'},
                   sounds={'keys': patches.get('sampled/rhodes_vibrato'),
                           'bass': patches.get('sampled/round_bass')})
    sax, rhodes, kit, bass, horns = b.lead, b.keys, b.drums, b.bass, b.horns
    room, plate = b.room, b.plate
    # the Fashionbass (the user's pick over the growlybass's first-note 'pups') is rounder: room for the Rhodes, piano
    # and sax in the low mids, and less 1 kHz under the vibes
    bass.add_fx(fx.eq({'peak1.freq': 420, 'peak1.gain': -3.5, 'peak1.q': 0.9,
                       'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 1.0,
                       'peak3.freq': 65, 'peak3.gain': -2.5, 'peak3.q': 1.2}))   # the kick's 60-70 Hz
    rhodes.add_fx(fx.eq({'peak1.freq': 300, 'peak1.gain': -2.0, 'peak1.q': 0.9}))
    piano = s.track('piano', 'sampled/jazz_grand', pan=0.15, gain_db=PIANO_DB, sends={room: -10, plate: -16},
                    fx=[fx.eq({'hp.freq': 70, 'peak1.freq': 220, 'peak1.gain': -2.5, 'peak1.q': 0.8,
                               'high.freq': 10000, 'high.gain': 1.5})])
    vibes = s.track('vibes', 'sampled/vibraphone', pan=0.45, gain_db=-4.0, sends={room: -10, plate: -12},
                    fx=[fx.tremolo(rate=4.6, depth=0.22, stereo=0), fx.width(width=0.6)])
    tenor = s.track('tenor', 'sampled/tenor_sax', pan=-0.3, gain_db=-5.0, sends={plate: -12, room: -12},
                    fx=[fx.eq({'hp.freq': 110, 'peak1.freq': 380, 'peak1.gain': -3.0, 'peak1.q': 0.9})])
    pad = s.track('pad', 'sampled/soft_poly', gain_db=-9.0, sends={plate: -14})
    shaker = s.track('shaker', 'sampled/busk_kit', gain_db=-12.0, pan=0.5,
                     fx=[fx.eq({'hp.freq': 400, 'high.freq': 9000, 'high.gain': 1.5})], sends={room: -12})
    # the alto up front as THE hero sax (v2, the user's 2026-10-15 pick: the dynamic mic with a breath trace, 4:1, tube
    # + tape grit, near-mono, the 10 Hz random autopan that was this song's own insert before, the 3.6 s 70s plate),
    # one take (HUMAN_FEEDBACK nowhere-to-be: no microshift / octave layers on an acoustic solo horn), echo throws
    hero(sax, family='sax', genre='pop', double=False, octave=False, bed=[rhodes, pad, vibes],
         competitors=[piano], sections=[head1, lift1, lift2, head3])

    hmem = {sax: hornist.Memory(), tenor: hornist.Memory()}
    pmem = pianist.Memory()
    bmem = bassist.Memory()

    def blow(clip, at, lo, hi, *, track=None, section='verse', seed=1, climax=False):
        t = track or sax
        perf = hornist.arrange(clip, TEMPO, family='sax', style='pop', section=section, vel=(lo, hi),
                               peaks=tuple(getattr(clip, 'peaks', ())), seed=seed, climax=climax,
                               memory=hmem[t], at=at, mic_every=2)   # the user's pick: sway + denser mic moves
        perf.place(t, at)
        return perf

    def comp(sec, vel, *, answer=None, style='swing', density=0.5, intensity=0.4, seed=0, register=('C3', 'G4')):
        c = jazz.comp(sec.prog, style=style, voicing='rootless', register=register, density=density,
                      intensity=intensity, vel=vel, answer=answer, seed=seed)
        rhodes.play(c.roll((8, 18), seed=seed, bpm=TEMPO), sec)

    def groove_bass(sec, part, seed, **kw):
        bassist.arrange(sec.prog, bpm=TEMPO, key=s.key, style='pop', part=part, seed=seed, memory=bmem, at=sec,
                        **kw).place(bass, sec)

    # ============================================================== intro
    vamp = jazz.comp(intro.prog, style='ballad', voicing='rootless', register=('E3', 'B4'), density=0.55,
                     intensity=0.35, vel=62, seed=1)
    rhodes.play(vamp.roll((14, 30), seed=1, bpm=TEMPO), intro)
    bassist.arrange(s.prog('Cmaj9 Fmaj7#11 Dm9 G13sus4'), bpm=TEMPO, key=s.key, style='pop', part='intro', seed=2,
                    memory=bmem, at=intro.bar(4)).place(bass, intro.bar(4))
    vibes.play(VIBES_HINT, intro)
    vibes.automate('instrument.pedal', [(intro.start, 1), (intro.bar(6) - 0.1, 0, 'step'),
                                        (intro.bar(6), 1, 'step'), (intro.end - 0.1, 0, 'step')])

    # ============================================================== head 1: the hook on the alto
    blow(HOOK_A, head1, 70, 108, section='verse', seed=11)
    comp(head1, 62, density=0.5, intensity=0.36, seed=12)
    groove_bass(head1, 'verse', 13)

    # ============================================================== lift 1: the sunrise
    blow(LIFT, lift1, 78, 116, section='chorus', seed=21)
    comp(lift1, 68, style='charleston', density=0.6, intensity=0.45, seed=22)
    groove_bass(lift1, 'chorus', 23)
    pad.chords(lift1, voicing='spread', register=('G2', 'C5'), vel=58)
    swell = lift1.prog.block(voicing='spread', register=('F3', 'E5'), vel=60)
    horns.play(Clip([n for n in swell if n.dur >= 2], length=swell.length).articulate('long'), lift1)
    horns.automate('gainDb', ramp(lift1.start, lift1.end, -10, -4, 'smooth'))

    # ============================================================== head 2: the piano has the hook
    pmel = touch(jazz.paraphrase(HOOK_A, seed=31, anticipate=0.25, delay=0.1, embellish=0.15, key=key).octave(1),
                 58, 100)
    arr = pianist.arrange(pmel, head2.prog, bpm=TEMPO, key=s.key, style='straight', density=0.55, seed=32,
                          lh=None, fill=0.35, memory=pmem, at=head2.start)
    arr.place(piano, head2)
    piano.feature(head2, db=6.0)     # the hook on the piano sat ~7 dB under the sax's (the user: 'piano totally quiet')
    blow(SAX_ANSWERS, head2, 62, 92, section='verse', seed=33)
    comp(head2, 58, style='swing', density=0.4, intensity=0.32, seed=34)
    groove_bass(head2, 'verse', 35)
    shaker.loop(drums({42: 'xoxoxoxoxoxoxoxo'}, vel=58).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16'), head2)

    # ============================================================== sax solo
    vocab = hornist.vocabulary('sax', style='pop', register=('G3', 'F5'), vel=(64, 112))
    sbud = soloist.Budget(spice_every=2, fast_every=16, same_every=32)
    SOLO['sax'] = soloist.solo(s, sax, vocab, at=sax_solo, prog=sax_solo.prog, motif=HOOK, arc='classic',
                               budget=sbud, seed=41)
    comp(sax_solo, 62, style='swing', density=0.5, intensity=0.4, seed=42)
    groove_bass(sax_solo, 'solo', 43)
    shaker.loop(drums({42: 'xoxoxoxoxoxoxoxo'}, vel=60).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16'), sax_solo)

    # ============================================================== piano solo: the Rhodes lays out
    pbud = soloist.Budget(spice_every=2, fast_every=16, same_every=32).save(piano_solo.start + 44)
    pvoc = pianist.vocabulary('straight', lh_track=piano, lh='guide', lh_vel=52, memory=pmem, seed=5, phrase_bars=4)
    SOLO['piano'] = soloist.solo(s, piano, pvoc, at=piano_solo, prog=piano_solo.prog, motif=HOOK.octave(1),
                                 budget=pbud, seed=51)
    piano.feature(piano_solo, db=3.0)
    groove_bass(piano_solo, 'solo', 53)
    shaker.loop(drums({42: 'xoxoxoxoxoxoxoxo'}, vel=56).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16'),
                piano_solo)

    # ============================================================== lift 2: the sunrise, with the section
    blow(LIFT, lift2, 82, 120, section='chorus', seed=61)
    blow(harmony(LIFT, key), lift2, 66, 100, track=tenor, section='chorus', seed=62)
    comp(lift2, 70, style='charleston', density=0.6, intensity=0.5, seed=63)
    groove_bass(lift2, 'chorus', 64)
    pad.chords(lift2, voicing='spread', register=('G2', 'C5'), vel=62)
    stab = Clip([(0.0, 1.5, p, 92) for p in ('E4', 'G4', 'B4')] + [(5.5, 0.4, p, 98) for p in ('F4', 'A4', 'D5')]
                + [(7.0, 0.3, p, 102) for p in ('F4', 'A4', 'D5')], length=8)
    horns.play(stab.articulate('accent'), lift2.bar(2))
    horns.play(Clip([(0.0, 3.5, p, 90) for p in ('G4', 'B4', 'E5')], length=4).articulate('long'), lift2.bar(4))
    horns.play(Clip([(0.0, 0.4, p, 100) for p in ('F4', 'A4', 'E5')] + [(1.5, 1.8, p, 96) for p in ('F4', 'C5', 'E5')],
                    length=4).articulate('accent'), lift2.bar(6))
    shaker.loop(drums({42: 'xoxoxoxoxoxoxoxo', 46: '....x.......x...'}, vel=62)
                .vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16'), lift2)

    # ============================================================== head 3: the hook, doubled, climbing
    blow(HOOK_A3, head3, 76, 122, section='chorus', seed=71, climax=True)
    blow(harmony(HOOK_A3.slice(32, 64), key), head3.bar(8), 64, 98, track=tenor, section='chorus', seed=72)
    vibes.play(touch(HOOK_A3.slice(0, 32).octave(1), 44, 100), head3)
    vibes.automate('instrument.pedal', [(head3.start + 2 * i, 0 if i % 2 else 1, 'step') for i in range(16)])
    comp(head3, 66, answer=HOOK_A3, density=0.6, intensity=0.45, seed=73)
    groove_bass(head3, 'chorus', 74)
    pad.chords(head3, voicing='spread', register=('G2', 'C5'), vel=54, bars={head3: (8, 16)})
    shaker.loop(drums({42: 'xoxoxoxoxoxoxoxo', 46: '....x.......x...'}, vel=62)
                .vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16'), head3)

    # ============================================================== outro + end
    blow(SAX_OUT, outro, 64, 98, section='outro', seed=81)
    comp(outro, 58, style='ballad', density=0.45, intensity=0.32, seed=82)
    groove_bass(outro, 'outro', 83, section_end=False)
    s.ending(end, chords=[(rhodes, END_CHORD, 60), (piano, hold('C5=58 E5=60 G5=62 D6=64', 7.6, length=8), 58)],
             bass=(bass, 'C2', 7, 84), drums=(kit, drummer.swell(4, TEMPO, kit=kit, energy=0.4)),
             rit=outro.bar(2), to=0.8, hold=2, length=4, room=(-12, -8), room_tracks=(vibes,))

    # ============================================================== drums: one drummer for the song
    part = drummer.arrange([intro, head1, lift1, head2, sax_solo, piano_solo, lift2, head3, outro], bpm=TEMPO,
                           style='pop', density=0.42, seed=7, kit=kit, lock=bass, fill_every=8, flashy_every=16,
                           plan={'intro': {'role': 'intro', 'energy': 0.3},
                                 'head1': {'role': 'verse', 'energy': 0.45},
                                 'lift1': {'role': 'chorus', 'energy': 0.7},
                                 'head2': {'role': 'verse', 'energy': 0.5, 'time': 'ride'},
                                 'sax_solo': {'role': 'solo', 'energy': 0.62},
                                 'piano_solo': {'role': 'solo', 'energy': 0.6, 'time': 'ride'},
                                 'lift2': {'role': 'chorus', 'energy': 0.78},
                                 'head3': {'role': 'chorus', 'energy': 0.75},
                                 'outro': {'role': 'outro', 'energy': 0.5}})
    part.play(kit)
    kit.clear(intro.start, intro.bar(4))                     # the Rhodes vamps alone for four bars

    # ============================================================== the arc and the master
    s.arc({'intro': 1.5, 'head1': -1.0, 'lift1': 0.5, 'head2': -0.5, 'sax_solo': 0.0, 'piano_solo': 0.0,
           'lift2': 1.0, 'head3': 1.0, 'outro': -1.0, 'end': -2.0})
    s.master.fx['compressor'].set(threshold=-11)            # glue only on the loudest bars: the arc stays
    mastering.apply(s, width=1.3, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=LIMITER)
    return s
