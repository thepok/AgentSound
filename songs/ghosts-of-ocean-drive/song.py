"""Ghosts of Ocean Drive - cinematic 80s night-drive retrowave (The Midnight / FM-84 / Timecop1983 territory).

Sub-style: retrowave pop, 104 BPM, B minor, straight 8ths, four on the floor in the choruses. Original composition.

The hook (the chorus, 8 + 8 bars over G A Bm D | G A Em F#, then G A Bm D | G A Bm Bm): one cell - two 8ths, a leap
up to a quarter, two 8ths falling back to a quarter (F# G B, B A G) - sung over G, then sequenced a step higher over
A (G A C#, C# B A), answered by a held B that settles on the tonic chord. The second half climbs further (C#6 D6, then
the whole run to F#6) and finally comes home to B. It is teased in the intro, returns in the interlude after the first
chorus, is re-coloured by the Dorian major IV (E major: the G turns into G#) in the breakdown, and the last chorus
lifts a whole step to C# minor after the sax solo lands on G#7.

Sound: the retrowave band preset (80s pop kit + TR-909 kick, Linn claps, keyed gated snare, octave bass, Juno pad,
bright DX e-piano, brass stabs, Fairlight choir, 224XL hall + plate, dotted-8th echo, master chain) without its lead;
the hook on a hero sound played by the pianist (octaves / sixths / thirds under the melody, budgeted ornaments), the
solo on the hero sax played by the wind player, drums by the drummer (synthpop machine style), bass by the bassist
(synth octave style), real strings, a pluck arp, glass arp, risers / impacts / downlifters.

Build: python -m agentsound build songs/ghosts-of-ocean-drive
Compare: python -m agentsound compare songs/ghosts-of-ocean-drive --section chorus2
         --ref "<refs>/The Midnight - Sunset (Official Audio) [URma_gu1aNE].opus" --ref-start 1:51 --ref-end 2:21
"""
from agentsound import *
from agentsound import bands, bassist, drummer, hornist, mastering, pianist

BPM = 104
ANALYSIS = {'profile': 'synthwave'}
METADATA = {'title': 'Ghosts of Ocean Drive', 'artist': 'AgentSound', 'album': 'Neon Archive', 'genre': 'Synthwave',
            'year': 2026,
            'comment': 'Cinematic 80s night-drive retrowave: hero synth-piano hook, sax solo, gated drums'}
COVER = {'style': 'outrun', 'title': 'GHOSTS OF OCEAN DRIVE', 'subtitle': 'AgentSound', 'seed': 86}

# the hook sound, chosen by measurement against the references (SOUND.md: piano_synth won the A/B)
LEAD_SOUND = 'hero/synth_piano'

# ---------------------------------------------------------------------- melody (degrees of B minor, 8 = B5 at octave 4)
C = {
    1: '5:1/8 6:1/8 8:1/4 8:1/8 7:1/8 6:1/4',          # F# G B  B A G       the cell (over G)
    2: '6:1/8 7:1/8 9:1/4 9:1/8 8:1/8 7:1/4',          # G A C#  C# B A      a step higher (over A)
    3: '8:1/4. 7:1/8 8:1/2',                            # B A B               settling (over Bm)
    4: 'r:1/4 5:1/8 6:1/8 5:1/4 3:1/4',                 # . F# G F# D         the answer (over D)
    6: '6:1/8 7:1/8 9:1/4 10:1/8 9:1/8 8:1/4',         # G A C# D C# B       reaching higher
    7: '8:1/4. 7:1/8 6:1/4 5:1/4',                      # B A G F#            (over Em)
    8: '#7:1/2 r:1/4 3:1/8 4:1/8',                      # A# ... D E          the leading tone hangs, a pickup
    14: '6:1/8 7:1/8 9:1/4 10:1/8 11:1/8 12:1/4',      # G A C# D E F#6      the climb
    15: '12:1/4. 10:1/8 8:1/2',                         # F# D B              down the chord
    16: '8:1/2 r:1/2',                                  # B                   home
}
HOOK_A = [1, 2, 3, 4, 1, 6, 7, 8]
HOOK_B = [1, 2, 3, 4, 1, 14, 15, 16]
VERSE = ('r:1/4 5:1/8 5:1/8 5:1/4 4:1/8 3:1/8 | 3:1/4. 2:1/8 1:1/2 | r:1/4 3:1/8 3:1/8 3:1/4 5:1/8 3:1/8 | 2:1/2. r:1/4'
         ' | r:1/4 5:1/8 5:1/8 5:1/4 8:1/8 7:1/8 | 6:1/4. 5:1/8 3:1/2')
VERSE_END1 = ' | r:1/8 3:1/8 4:1/8 5:1/8 6:1/4 5:1/8 4:1/8 | 4:1/2. r:1/4'          # a half cadence on E (over A)
VERSE_END2 = ' | 3:1/8 4:1/8 5:1/4 8:1/4 7:1/8 6:1/8 | 7:1/2 r:1/2'                 # up to A: into the pre-chorus
PRE = ('3:1/4 4:1/4 5:1/2 | 5:1/4 4:1/4 3:1/4 4:1/4 | 3:1/4 4:1/4 5:1/2 | 6:1/4 5:1/4 4:1/2'
       ' | 4:1/4 5:1/4 6:1/2 | 7:1/4 6:1/4 5:1/2 | 8:1/2 7:1/4 6:1/4 | #7:1/2. r:1/4')
# the breakdown: the hook at half speed, bar 2 re-coloured by the major IV (E: G -> G#)
BREAK = C[1] + ' | #6:1/8 7:1/8 9:1/4 9:1/8 8:1/8 7:1/4 | ' + C[3] + ' | ' + C[4]
# the sax solo (octave 3: D4-F#5, the alto's singing range), landing on G#7 for the lift to C# minor
SOLO = ('r:1/4 5:1/8 6:1/8 8:1/2 | 9:1/4. 8:1/8 7:1/8 6:1/8 5:1/4 | 3:1/8 5:1/8 8:1/4 10:1/2 '
        '| 10:1/8 9:1/8 8:1/8 6:1/8 5:1/2 | r:1/8 5:1/8 6:1/8 8:1/8 9:1/4 10:1/4 | 11:1/2. 10:1/8 9:1/8 '
        '| 12:1/4. 11:1/8 10:1/4 8:1/4 | G#5:1/4 C6:1/4 D#6:1/2')   # note names read at octave 4


# the mix engineer's moves (python -m agentsound mix): the bass and the bed step back in the verses and the
# breakdown (bed >= 2.5 dB under the hook, the verse thinner than the chorus), the drums carry the choruses
MIX = {
    # lead +1: gives back what its 800 Hz honk dip (eq below) took from its K-weighted level (-0.9 dB)
    'trim': {'drums': 2.0, 'bass': -0.5, 'strings': -1.0, 'choir': -1.0, 'sax': -3.0, 'lead': 1.0},
    'ride': {
        'pad': {'verse1': -1.0, 'verse2': -1.0, 'pre1': -2.0, 'pre2': -1.2, 'chorus1': 1.0, 'interlude': 1.0,
                'breakdown': -4.5, 'solo': 1.5, 'outro': -2.5},   # revision: pre2 / verse1 thin_bed; solo bed 6 dB under the sax
        'lead': {'verse1': 1.5, 'pre1': 1.0, 'verse2': 1.5, 'pre2': 1.0, 'breakdown': 1.5},   # the verse tune in front too
        'sax': {'solo': 4.0},        # A&R revision: +2.5 more (was +1.5) over a thinned, quieter band
        # the groove carries the hooks, the sax solo in front (a song-wide +0.8 brought the kick / bass masking back)
        'drums': {'chorus1': 1.2, 'chorus2': 1.5, 'breakdown': -2.0, 'solo': -1.5, 'chorus3': 1.8},   # revision: the harder kit up in the hooks
        'strings': {'breakdown': -3.5},
        'choir': {'breakdown': -3.5},
        'bass': {'verse1': -2.5, 'verse2': -2.0, 'pre1': -1.5, 'pre2': -1.5, 'breakdown': -2.0, 'solo': -2.5,
                 'outro': -2.0},
    },
    'eq': {'pad': [{'freq': 450.0, 'gain': -2.0, 'q': 1.0}, {'freq': 1400.0, 'gain': -1.5, 'q': 1.0}],
           'keys': [{'freq': 1400.0, 'gain': -2.0, 'q': 1.0},       # room for the verse tune
                    {'freq': 3000.0, 'gain': -2.0, 'q': 0.9}],      # revision: the hook owns the presence band now
           'arp': [{'freq': 3500.0, 'gain': -2.0, 'q': 0.9}],       # (its glass layer; the profile's +4 dB limit)
           'lead': [{'freq': 800.0, 'gain': -1.5, 'q': 2.0}],       # the hook's honk (800 Hz +4-5 dB vs Sunset)
           'drums': [{'freq': 3300.0, 'gain': -4.0, 'q': 0.9},     # the crack's presence: the hook owns 2.5-6 kHz now
                     {'freq': 10000.0, 'gain': -4.0, 'q': 0.8}]},  # the crack's tick / air (Sunset: air +2..2.6 dB)
    # a short, fast second duck of the bass under the kick hits only: the kick owns its first ~100 ms (kick / bass
    # ducking was 2.0 dB in chorus 3 = masking; Sunset's kick punch 19 dB vs our 13-14)
    'duck': [{'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 10, 'attack': 1, 'hold': 50,
              'release': 110}],
}

# dB added to each section's limiter drive (the mastering engineer's loudness move). A&R revision: +2 everywhere
# squashed chorus 3 into a brick (6.5 dB of limiting, LRA 0.7) and flattened the arc; now the choruses climb (first
# statement softer), verses / pres get +0.5, and the solo steps back under chorus 3 (-1.3: its sax is ridden up instead)
MASTER_DRIVE = {'chorus1': 0.5, 'chorus2': 1.0, 'chorus3': 1.3, 'solo': -1.3, 'other': 0.5}


def bars(*ids):
    return ' | '.join(C[i] for i in ids)


def build() -> Song:
    s = Song('Ghosts of Ocean Drive', tempo=BPM, key='B minor', seed=1986, tail=8.0)
    key, up = s.key, Key('C# minor')

    # ------------------------------------------------------------------ harmony
    P_intro = s.prog('Gmaj7:2 A6:2 Bm9:2 Asus4 A')
    P_verse = s.prog('i VI III VII i VI iv VII')                  # Bm G D A | Bm G Em A
    P_pre = s.prog('iv:2 VI:2 VII:2 V7sus4 V7')                   # Em G A F#7sus4 F#7
    P_chA = s.prog('VI VII i III VI VII iv V')                    # G A Bm D | G A Em F#
    P_chB = s.prog('VI VII i III VI VII i:2')                     # G A Bm D | G A Bm
    P_chorus = P_chA + P_chB
    P_inter = s.prog('VI VII i III')
    P_break = s.prog('Gmaj7:2 E:2 D:2 Asus4 A')                   # VImaj7 IV(major: Dorian hope) III VIIsus4 VII
    P_solo = s.prog('G A Bm D G A Em G#7')                        # ... the last bar: V of C# minor
    # the last chorus a whole step up; its last bar turns to A (VI of C#m = VII of B minor): the pivot back home, so
    # the outro's G arrives a step down instead of a tritone away from C#m
    P_up = (P_chA + s.prog('VI VII i III VI VII i VI')).transpose(2)   # A B C#m E | A B F#m G# | A B C#m E | A B C#m A
    P_outro = s.prog('G A Bm D Gmaj7:2 Bm9:2')

    # ------------------------------------------------------------------ form: 124 bars, ~4:46
    intro = s.section('intro', 8, prog=P_intro)          # pad + glass arp opening, the hook cell teased far away
    verse1 = s.section('verse1', 16, prog=P_verse * 2)   # drums (half), bass, e-piano, the verse tune on the hero piano
    pre1 = s.section('pre1', 8, prog=P_pre)              # the ladder: Em G A F#7, strings swell, drum build, riser, a breath
    chorus1 = s.section('chorus1', 16, prog=P_chorus)    # the hook, four on the floor, claps
    inter = s.section('interlude', 4, prog=P_inter)      # the hook cell once more over the groove (the lamplight rule)
    verse2 = s.section('verse2', 8, prog=P_verse)        # the verse again, the pluck arp joins, busier drums
    pre2 = s.section('pre2', 8, prog=P_pre)
    chorus2 = s.section('chorus2', 16, prog=P_chorus)    # + choir, strings, brass stabs, the hook harmonized
    brk = s.section('breakdown', 8, prog=P_break)        # drums gone, the hook at half speed in new colours (E major)
    solo = s.section('solo', 8, prog=P_solo)             # the hero sax over the chorus changes, landing on G#7
    chorus3 = s.section('chorus3', 16, prog=P_up)        # a whole step up (C# minor): everything, the pianist's climax
    outro = s.section('outro', 8, prog=P_outro)          # back in B minor, the sax sings the cell, the beat strips away

    hook_a, hook_b = s.motif(bars(*HOOK_A)), s.motif(bars(*HOOK_B))
    hook = hook_a + hook_b                                         # 16 bars

    # ------------------------------------------------------------------ the band (retrowave preset, own lead)
    b = bands.retrowave(s, without=('lead',))
    kit, bass, pad, keys, brass, choir = b.drums, b.bass, b.pad, b.keys, b.brass, b.choir
    hall, plate = b.buses['hall'], b.buses['plate']
    echo = b.buses.get('echo') or s.echo()
    shimmer = s.bus('shimmer', 'bus/shimmer')
    pad.send(shimmer, -20)

    strings = s.track('strings', 'sampled/strings', gain_db=-4, sends={hall: -8},
                      fx=[fx.eq({'peak1.freq': 480, 'peak1.gain': -2.5, 'peak1.q': 1.0}),
                          fx.width(width=1.35)])        # A&R revision: width lives in the low mids
    arp = s.track('arp', 'synthwave/arp_pluck', gain_db=-5, pan=0.45, sends={echo: -10, hall: -14})
    keys.pan = -0.45                                    # e-piano and arp further apart (were -0.3 / +0.3)
    pad.add_fx(fx.width(name='pw', width=1.2, monobass=150))   # wider in the low mids from verse 1 on (the intro
    pad.automate('fx.pw.width', [(0, 1.0), (verse1.start - 1, 1.0), (verse1.start, 1.2, 'smooth')])  # stays mono-safe)
    for f in pad.fx:                                    # the preset's +2 dB presence on the pad goes: the hook owns it
        if f.type == 'eq' and f.params.get('peak3.gain') == 2.0:
            f.params['peak3.gain'] = 0.0
    glass = s.track('glass', 'synthwave/arp_glass', gain_db=-5, pan=-0.35, sends={echo: -12, hall: -10, shimmer: -18},
                    fx=[fx.filter(name='gf', mode='lp', cutoff=20000)])
    riser_t = s.track('riser', 'synthwave/noise_riser', gain_db=-11)
    impact = s.track('impact', 'synthwave/impact', gain_db=-1)
    down = s.track('down', 'synthwave/downlifter', gain_db=-10)

    # the hook: a "hohe Piano-Taste" needs its top (A&R revision): the hero tone's -1.5 dB at 3.3 kHz gone, a +3 dB
    # shelf from 5 kHz instead of the +1.5 dB air at 9.5 kHz, the saw layer opened (1.5 -> 2.0 kHz) and kept to the
    # melody register (from A4 up, faded over 5 semitones): the left hand and the doubles below stay piano, so the
    # sustaining saw no longer thickens the low mids under the top note
    lead = s.track('lead', LEAD_SOUND)
    lead = hero(lead, genre='synthwave', bed=[pad, choir, strings], competitors=[keys, arp, brass, glass],
                sections=[chorus1, chorus2, chorus3],
                tone={'peak3.gain': 0.0, 'high.freq': 5000, 'high.gain': 3.0})
    lead.instrument = lead.instrument.but(**{'layers.saw.cutoff': 2000, 'layers.saw.keylo': 69, 'layers.saw.keyhi': 108,
                                             'layers.saw.keyfade': 5})
    # ... and the FM sparkle of layered/piano_glass_lead: the DX glass (synthwave/arp_glass) an octave up, -13 dB,
    # on the melody register only (from E5): the hook's own 2.5-6 kHz (the shelves alone moved the mix < 0.1 dB)
    lead.instrument = lead.instrument.but(layers=list(lead.instrument.params['layers']) + [
        layer('synthwave/arp_glass', 'glass', transpose=12, level=-13, bend=False, pedal=True, keys=('E5', 'C8'),
              keyfade=4)])
    # the solo sax in front of a thinned band: the bed ducked and carved deeper under it (6-8 dB, the lamplight rule)
    sax = hero(s.track('sax', 'hero/sax'), family='sax', genre='synthwave', bed=[pad, choir, strings],
               competitors=[keys, arp, glass], sections=[solo], duck=4.0, carve=4.5)
    sax.send(s.buses['hero_plate'], -11)     # its own big plate 3 dB wetter (was -14): an epic, wider solo image

    # ------------------------------------------------------------------ the hook instrument, played by a pianist
    # a synthwave hook is sung, not decorated: restrikes and rolls (the piano's way to sustain), a rare crush or turn
    ORN = {'restrike': 3.0, 'roll': 1.5, 'crush': 0.6, 'turn': 0.4, 'trill': 0.3}
    HOOKDEV = {'octave': 3.0, 'sixths': 1.5, 'thirds': 1.5, 'drop2': 0.8, 'guide': 0.8, 'single': 0.4}
    pp = pianist.Player(lead, bpm=BPM, key=key, ornaments=ORN, log=print)
    # intro: the cell, far away, twice (the second answered by the settle)
    pp.play(bars(1, 2, 3), s.prog('Gmaj7 A6 Bm9'), intro.bar(3), lo=46, hi=70, style='sparse', density=0.3, seed=1)
    # verses: the verse tune (lower, softer, single notes and guide tones - the hook's octaves are saved)
    pp.play(VERSE + VERSE_END1 + ' | ' + VERSE + VERSE_END2, P_verse * 2, verse1, lo=52, hi=88, style='sparse',
            density=0.35, seed=2)
    pp.play(VERSE + VERSE_END2, P_verse, verse2, lo=56, hi=92, style='sparse', density=0.45, seed=3)
    # pre-chorus: the ladder, thirds and sixths growing; the hook voice then falls silent (pre1: its last bar, pre2:
    # the last two, where the brass hits take over) so each chorus arrives from a hole, not as the same piano busier
    pp.play(PRE, P_pre, pre1, lo=60, hi=96, density=0.45, seed=4, devices={'thirds': 2, 'sixths': 2, 'guide': 1},
            until=28)
    pp.play(PRE, P_pre, pre2, lo=64, hi=100, density=0.55, seed=5, devices={'thirds': 2, 'sixths': 2, 'drop2': 1},
            until=24)
    # choruses: first statement a little softer, the second harmonized more, the last one up a step, climax; the
    # doubles under the melody at 75 % so the top note leads (A&R: the hook's top)
    pp.play(hook, P_chorus, chorus1, lo=70, hi=108, density=0.45, seed=6, devices=HOOKDEV, doubles=0.75)
    pp.play(bars(1, 2, 3, 4), P_inter, inter, lo=64, hi=98, density=0.4, seed=7, devices=HOOKDEV, doubles=0.75)
    pp.play(hook, P_chorus, chorus2, lo=74, hi=112, density=0.6, seed=8, devices=HOOKDEV, doubles=0.75)
    pp.play(s.motif(BREAK).stretch(2).clip(octave=4, gate=0.95), P_break, brk, lo=50, hi=86, style='ballad',
            density=0.55, seed=9, lh='tenths')
    pp.play(hook.clip(octave=4, gate=0.95).transpose(2), P_up, chorus3, lo=78, hi=118,
            density=0.7, seed=10, climax=True, key=up, devices=HOOKDEV, doubles=0.75)
    # outro: the sax sings the cell (bars 1-3), the piano only answers it (bar 4), then the last chord
    pp.play(bars(4), s.prog('D'), outro.bar(3), lo=50, hi=80, style='sparse', density=0.35, seed=11)
    last = Clip([(0, 8, p, v) for p, v in (('B2', 60), ('F#3', 54), ('D4', 52), ('C#5', 56), ('F#5', 62))],
                length=8).strum(ms=40, bpm=BPM)
    lead.play(last, outro.bar(4))
    pp.pedal()

    # ------------------------------------------------------------------ sax: the solo, and a farewell in the outro
    hmem = hornist.Memory()
    line = s.motif(SOLO).clip(octave=3, gate=0.95)
    # deeper breath than the default (A&R: 3.1 dB note dynamics in the solo): pushes x1.35, accents 0.18 dB / step
    perf = hornist.arrange(line, BPM, family='sax', style='hero', section='solo', peaks=(10, 20, 24, 30),
                           vel=(76, 124), seed=12, memory=hmem, at=solo, climax=True, depth=1.35, accent=0.18)
    perf.place(sax, solo)
    fare = s.motif(bars(1, 2, 3)).clip(octave=3, gate=0.95)
    perf2 = hornist.arrange(fare, BPM, family='sax', style='hero', section='outro', peaks=(10,), vel=(64, 100),
                            seed=13, memory=hmem, at=outro)
    perf2.place(sax, outro)
    print('hornist solo:', perf.summary(), '| outro:', perf2.summary())

    # ------------------------------------------------------------------ drums: the drummer (80s machine)
    # kit A has no cymbals, so the drummer left its crashes out; it gets a crash on 49 (played by the 'cymbals' track
    # below from the same pack's kit C): every section arrival and the ending hit crash again (A&R issue 1)
    dkit = drummer.Kit.of(kit)
    dkit.pieces['crash'] = 49
    part = drummer.arrange(s, style='synthpop', density=0.55, seed=7, kit=dkit, ending='hit', plan={
        'intro': {'mode': 'time', 'energy': 0.3},
        'verse1': {'mode': 'half', 'energy': 0.4},
        'interlude': {'role': 'post'},
        'verse2': {'energy': 0.42},
        'breakdown': 'break',
        # the solo is a step below chorus 3: half time, lighter - the sax and its bed carry it (A&R issues 1 + 4)
        'solo': {'role': 'solo', 'mode': 'half', 'energy': 0.45},
        'outro': {'role': 'outro', 'energy': 0.5},
    })
    # the hats (A&R revision): the "punch high" of the compare (15.3 vs Sunset 11.1 dB) is mostly NOT the hats - on
    # their own track they sat 35 dB under the kit (kit gain -14 dB, velocities x0.7 on top: -54 LUFS, nearly
    # inaudible); the top-band hits are the snare / clap crack. The hats go on their own track through the kit's chain,
    # back to the drummer's velocities, +2 dB, darkened (-1.5 dB at 4.2 kHz, -3 dB shelf from 9 kHz, low-pass 14 kHz):
    # a soft 16th sheen instead of ticks (+6 dB was tried: air +2.6 dB over Sunset and the top-band punch +0.8 dB)
    HATS = (42, 44, 46)
    CRASH = (49, 57)
    hat_clip = part.clip.filter(lambda n: n.pitch in HATS)
    cym_clip = part.clip.filter(lambda n: n.pitch in CRASH)
    part.clip = part.clip.filter(lambda n: n.pitch not in HATS + CRASH)
    part.play(kit)
    hats = s.track('hats', kit.instrument.but(), gain_db=kit.gain_db + 2.0, pan=kit.pan,
                   fx=[f.copy() for f in kit.fx] + [fx.eq({'peak3.freq': 4200, 'peak3.gain': -1.5, 'peak3.q': 0.8,
                                                            'high.freq': 9000, 'high.gain': -3.0,
                                                            'lp.freq': 14000})],
                   sends={plate: -18})
    hats.humanize(0, 0)
    hats.play(hat_clip, part.start)
    # the crashes on the same pack's kit C (sampled/80s_gated_kit, 49), high-passed: only the wash, no second kick
    cym = s.track('cymbals', 'sampled/80s_gated_kit', gain_db=6, fx=[fx.eq({'hp.freq': 350, 'hp.slope': 24})],
                  sends={hall: -18})
    cym.humanize(0, 0)
    cym.play(cym_clip, part.start)
    # the 80s kick (A&R issue 2): kit A's kick is soft and long (punch 13.6 vs Sunset 18.9 dB); the LinnDrum kick
    # layered under it at -3 dB, low-passed at 3 kHz, gives the hit its thump (chorus 3: punch 14.0 -> 16.7 dB; at
    # -6 dB 15.7). Tried and dropped: a harder kit compressor (5:1, 30 ms: 12.5 dB), less master drive (+0.3 dB only)
    kick = s.track('kick', 'sampled/linndrum', gain_db=-3, fx=[fx.eq({'lp.freq': 3000})])
    kick.humanize(0, 0)
    kick.play(part.clip.filter(lambda n: n.pitch == 36), part.start)
    for t in (kit, hats, cym, kick):
        t.clear(0, intro.bar(4))
        t.clear(outro.bar(4), outro.end + 8)
    print('drummer:', part.summary())

    # ------------------------------------------------------------------ bass: the bassist (synth octave pulse)
    bp = bassist.Player(bass, bpm=BPM, key=key, style='synth', kick='x...x...x...x...')
    bp.play(P_verse * 2, verse1, 'verse', kick='x.......x.x.....', seed=1, interlock=True)  # answers the sparse kicks
    bp.play(P_pre, pre1, 'pre', seed=2)
    bp.play(P_chorus, chorus1, 'chorus', seed=3)
    bp.play(P_inter, inter, 'chorus', seed=4)
    bp.play(P_verse, verse2, 'verse', seed=5)
    bp.play(P_pre, pre2, 'pre', seed=6)
    bp.play(P_chorus, chorus2, 'chorus', seed=7)
    bass.play(P_break.bass('root', vel=70), brk)
    bp.play(P_solo, solo, 'solo', seed=8)
    bp.play(P_up, chorus3, 'chorus', key=up, seed=9)
    bp.play(s.prog('G A Bm D'), outro, 'outro', seed=10, ending='ring', interlock=True)

    # ------------------------------------------------------------------ pads, strings, choir, brass
    keys.instrument.params['velsens'] = 0.85            # was 0.5: the velocity arcs must reach the level
    brass.instrument.params['amp.velocity'] = 0.75      # was 0.5

    def arc4(c, accents=(1.25, 0.78, 1.0, 0.84), grid='1/8', depth=0.35):
        """Played chords: accents on the beat, lighter off-beats, and a 4-bar arch (rise to bar 3, relax)."""
        return c.vel_pattern(list(accents), grid=grid).arch(4, depth)

    pad.chords(s.sections, voicing='spread', register=('C3', 'C5'),
               vel={intro: 70, verse1: 72, pre1: 76, chorus1: 80, inter: 76, verse2: 74, pre2: 78, chorus2: 82,
                    brk: 80, solo: 80, chorus3: 84, outro: 72})
    strings.chords(pre1, pre2, chorus1, chorus2, brk, solo, chorus3, outro, voices=4,
                   register={'*': ('A3', 'E5'), brk: ('F#3', 'C#5')}, crescendo={pre1: (0.55, 1.0), pre2: (0.55, 1.0)},
                   vel={pre1: 64, pre2: 70, chorus1: 62, chorus2: 80, brk: 74, solo: 60, chorus3: 88, outro: 64},
                   bars={chorus1: 8, solo: (0, 4)})
    # the solo: soft, wide strings under the sax, swelling in its second half (the build into chorus 3)
    strings.play(P_solo.block(register=('A3', 'E5'), voices=4, vel=74).slice(16, 32).crescendo(0.6, 1.0), solo.bar(5))
    choir.chords(chorus2, brk, chorus3, register=('C#3', 'C#5'), voices=4, vel={chorus2: 74, brk: 70, chorus3: 82},
                 prog={chorus2: P_chB}, bars={chorus2: 8})

    stab = dict(rhythm='..x...x.', register=('C4', 'C5'), voices=3, gate=0.5)
    brass.play(arc4(P_chorus.block(**stab, vel=80), accents=(1, 1.2, 1, 0.78), grid='1/4'), chorus2)
    brass.play(arc4(P_up.block(**stab, vel=88), accents=(1, 1.2, 1, 0.78), grid='1/4'), chorus3)
    brass.play(P_pre.block(rhythm='x.......', register=('C4', 'C5'), voices=3, gate=0.6, vel=76).slice(24, 32),
               pre2.bar(6))

    # ------------------------------------------------------------------ keys (bright DX e-piano) and arps
    ek = dict(voicing='drop2', register=('C4', 'C5'))
    keys.play(arc4((P_verse * 2).block(**ek, rhythm='x..x..x.', vel=70)), verse1)
    keys.play(arc4(P_pre.block(**ek, rhythm='x.x.x.x.', vel=70), depth=0.1).crescendo(0.6, 1.0), pre1)
    keys.play(arc4(P_chorus.block(**ek, rhythm='x..x..x.', vel=72)), chorus1)
    keys.play(arc4(P_inter.block(**ek, rhythm='x..x..x.', vel=70)), inter)
    # verse 2 thinner than before (A&R: the chorus must arrive): the e-piano on two chords a bar, softer
    keys.play(arc4(P_verse.block(**ek, rhythm='x...x...', vel=66), accents=(1.2, 0.8, 0.95, 0.85), grid='1/4'), verse2)
    keys.play(arc4(P_pre.block(**ek, rhythm='x.x.x.x.', vel=72), depth=0.1).crescendo(0.6, 1.0), pre2)
    # the solo: long chords under the sax (was a 3-3-2 comp), the room is the sax's
    keys.play(arc4(P_solo.block(**ek, rhythm='x.......', vel=60), depth=0.6), solo)

    glass.arp({'*': 'up', chorus2: 'updown', chorus3: 'updown'}, intro, brk, chorus2, chorus3, outro, rate='1/8',
              register={'*': (62, 74), brk: (62, 76), chorus2: (62, 76), chorus3: (64, 78)},
              vel={intro: 70, brk: 72, chorus2: 72, chorus3: 76, outro: 66}, prog={chorus2: P_chB}, bars={chorus2: 8})
    # the pluck arp: out of verse 2 and the solo (A&R), it enters in the second half of pre 2 as part of the build and
    # drives chorus 2 and 3
    arp.play(P_pre.arp('up', rate='1/16', register=('D4', 'D5'), vel=76).slice(16, 32).crescendo(0.6, 1.0),
             pre2.bar(5))
    arp.arp({'*': 'updown', chorus1: 'up'}, chorus2, chorus3, chorus1, rate={'*': '1/16', chorus1: '1/8'},
            octaves={chorus2: 2, chorus3: 2}, register={'*': ('B3', 'B4'), chorus3: ('C#4', 'C#5')},
            vel={chorus2: 84, chorus3: 86, chorus1: 74})

    # ------------------------------------------------------------------ transitions
    riser_t.rise(pre1.end - 1, 15, pitch='B3', hpf=None)
    riser_t.rise(pre2.end - 1, 15, pitch='B3', hpf=None)
    riser_t.rise(chorus3, 16, pitch='B3', vel=96, cutoff=(300, 10000), hpf=None)
    impact.note('B1', chorus1.start, 4, 116).note('B1', chorus2.start, 4, 120).note('C#2', chorus3.start, 4, 124)
    down.note('B3', brk.start, 8, 110).note('B3', outro.start, 6, 90)

    # a one-beat breath before the first two choruses: only the tails (and the hero's own pickup, if any)
    s.breath(before=[chorus1, chorus2], tracks=[kit, bass, pad, keys, strings, arp, glass, brass, choir], cut=False)

    # ------------------------------------------------------------------ production moves
    s.sidechain(arp, glass, strings, key=kit, pitches='kick', depth=6, release=240)
    pad.automate('instrument.cutoff', exp_ramp(intro.start, intro.end, 600, 2800), hold(verse1.start, pre1.start, 2400),
                 exp_ramp(pre1.start, chorus1.start, 1800, 3600), hold(chorus1.start, brk.start, 3400),
                 exp_ramp(brk.start, solo.start, 1400, 3000), hold(solo.start, outro.start, 3600),
                 exp_ramp(outro.start, outro.end, 3000, 500))
    glass.automate('fx.gf.cutoff', exp_ramp(intro.start, intro.end, 900, 18000))
    for t, lo in ((pad, -20), (glass, -18)):
        t.automate('send.shimmer', [(0, -8), (verse1.start, lo, 'smooth'), (brk.start, -6, 'smooth'),
                                    (solo.start, lo, 'smooth'), (outro.start, -8, 'smooth')])
    for t in (pad, glass, strings):
        t.automate('gainDb', [(outro.bar(4), 0), (outro.end + 6, -30, 'smooth')])
    s.master.fx['width'].set(monobass=150)                 # the pad-only intro read < 0.8 correlation below 150 Hz
    bass.fx['ducker'].set(depth=9, threshold=-48)          # preset 5: the kick punches through (punch 13 vs 19 dB)
    # A&R revision, the 80s kick: the kit's console compressor opens later (10 -> 28 ms: the kick's first hit passes
    # before it clamps, then it holds the body and the room), a little less tape clip on the transients; with the Linn
    # kick layer (drums section) the low end is split: the kit -3 dB at 160 Hz (the kick's and toms' boom: drums 48 %
    # of 111-224 Hz), the bass -3 dB at 150 Hz (89-354 Hz read +2.8 dB vs Sunset). Chorus 3 vs Sunset: kick punch
    # 13.6 -> 18.0 dB (ref 18.9), 111-224 Hz +2.8 -> +2.0 dB. Tried first: the bass alone -3 dB at 140 Hz and a 70 Hz
    # kit shelf -3 -> -1.5 dB (the drums' share of the bass band 44-54 %: masking warnings in every section); a kit dip
    # at 125 Hz without the Linn layer (punch 13.3); a harder kit compressor 5:1 / 30 ms (12.5)
    kit.fx['compressor'].set(attack=28, ratio=3.0, release=120)
    kit.fx['saturator'].set(drive=3.5)
    kit.add_fx(fx.eq({'peak2.freq': 160, 'peak2.gain': -3.0, 'peak2.q': 1.3}))
    bass.add_fx(fx.eq({'peak2.freq': 150, 'peak2.gain': -3.0, 'peak2.q': 1.1}))
    # the mastering engineer (MASTER.md; python -m agentsound master ... --ref Sunset 4:00-4:30 --section chorus2): a broad
    # -1 dB mid dip first in the chain (both Sunset and the synthwave profile read the mids hot; the plan's +1.5 dB
    # presence lift refused - the hook now carries its own top, A&R revision), ceiling -1.2 for -1 dBTP, release
    # 120 ms, and the extra drive per section in MASTER_DRIVE (was +2 dB everywhere)
    mastering.apply(s, eq={'peak1.freq': 1250.0, 'peak1.gain': -1.0, 'peak1.q': 0.7},
                    limiter={'ceiling': -1.2, 'release': 120.0})
    # the energy arc: the master limiter's drive per section (the preset's 3.5 dB is the chorus-1 level), gliding
    # over a beat into each; the verses and the breakdown hold back, the last chorus pushes (the arrangement makes
    # the rest of the difference)
    drive = {intro: 3.0, verse1: 2.0, pre1: 2.6, chorus1: 3.8, inter: 3.0, verse2: 2.2, pre2: 2.8, chorus2: 4.1, brk: 1.8,
             solo: 2.9, chorus3: 4.5, outro: 2.8}
    s.master.lane('fx.limiter.gain', {sec: g + MASTER_DRIVE.get(sec.name, MASTER_DRIVE['other'])
                                      for sec, g in drive.items()}, glide=1)
    return s
