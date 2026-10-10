"""Catch Fire - an original arena pop-rock anthem in the spirit of Imagine Dragons (124 BPM, D minor, sung by TIGER).

The idiom, not the songs: stomp-and-clap verses (taikos + hand claps over a sub and a filtered synth pulse), a
pre-chorus that builds (the riff chugging up, a riser, a one-beat breath), a half-time chorus drop with a massive kick
+ sub, a chantable hook ("Strike me down, I catch fire") doubled and harmonized by the sung voice, a "whoa-oh" gang
chant (TIGER x3 + a harmony + Hanami an octave up) that opens the song and follows every chorus, a stripped bridge
(piano, choir, voice) that rebuilds over toms, and a final double chorus where "I'll" becomes "we'll".
Plan: BRIEF.md, LYRICS.md, ARRANGEMENT.md, SOUND.md, MIX.md, MASTER.md, AR.md.
Build: python -m agentsound build songs/catch-fire   (needs the TIGER + Hanami voicebanks and the WSL singing venv)
"""
from agentsound import *
from agentsound import bands, bassist, drummer, library, mastering, pianist, singer
from agentsound import guitarist as gt
from agentsound.bandlib.pop import hand_perc

ANALYSIS = {'profile': 'rock'}     # pop-rock with a live band: the rock balance (mid-forward guitars) fits; see BRIEF
METADATA = {'title': 'Catch Fire', 'artist': 'AgentSound', 'album': 'Arena', 'genre': 'Pop Rock', 'year': 2026}
COVER = {'style': 'rock', 'palette': ['#ff5a1f', '#ffc23d'], 'title': 'CATCH FIRE',
         'subtitle': 'ARENA'}     # 'AgentSound' (10 letters) ran under the rock style's disc: the album name fits
MIX = {
    'trim': {'drums': 1.5, 'claps': 3.5, 'gtr_l': 2.5, 'gtr_r': 2.5, 'vocal': -1.0, 'choir': 5.0, 'bass': 1.0,
             'sub': 1.0},
    'ride': {'vocal': {'verse1': 1.0, 'pre1': 1.0, 'verse2': 1.0, 'pre2': 1.0, 'bridge': 1.0, 'build': 1.75,
                       'chorus1': 0.75, 'chorus2': 0.75, 'chorus3': 0.75},
             'gang': {'intro': -2.5}, 'gang_dbl_l': {'intro': -2.0}, 'gang_dbl_r': {'intro': -2.0},
             'gang_harm': {'intro': -2.0}, 'gang_dbl_hi': {'intro': -2.0},
             'drums': {'build': -1.0, 'chorus1': 1.5, 'post1': 1.0, 'chorus2': 1.5, 'post2': 1.0, 'chorus3': 1.5, 'post3': 1.0},
             'choir': {'bridge': 3.5, 'build': 4.0}},
    'eq': {'drums': [{'freq': 45, 'gain': -3.0, 'q': 0.8}],
           'gtr_l': [{'freq': 400, 'gain': -3.5, 'q': 1.0}], 'gtr_r': [{'freq': 400, 'gain': -3.5, 'q': 1.0}],
           'keys': [{'freq': 350, 'gain': -2.0, 'q': 1.0}], 'choir': [{'freq': 350, 'gain': -3.0, 'q': 0.9}]},
    'duck': [{'targets': ['sub'], 'key': 'drums', 'pitches': 'kick', 'depth': 10, 'attack': 1, 'hold': 40, 'release': 160}],
}

# ------------------------------------------------------------------ the sung lines (male register, TIGER as written)
VERSE1 = ('D3/8 D3 C3 D3 F3/4 D3/4 | r/1 | '                       # Gravel in my pockets,
          'F3/8. D3/16 D3/8 C3 D3/4. r/8 | r/2. r/8 C3/8 | '        # ashes on my shoes, they
          'F3/8 F3 A3/4. G3/8 G3 F3 | r/2. r/8 C3/8 | '             # wrote my name in pencil like
          'E3/8 D3 E3/4. G3/8 E3/4~ | E3/4 r/2. | '                 # I'd be gone by June.
          'D3/8. D3/16 F3/8 F3 A3/8. G3/16 F3/8 D3 | r/1 | '         # Kept my head below the window,
          'D3/8 D3 F3 D3 F3/2 | r/1 | '                             # kept my matches dry,
          'F3/8 F3 A3/8 G3/8 A3/8. G3/16 A3/8 C4 | r/1 | '             # every fist that came to find me
          'C4/8. A3/16 G3/8 E3 G3/2 | r/1')                         # struck another light.
VERSE1_WORDS = ("Grav-el in my pock-ets, ash-es on my shoes, they wrote my name in pen-cil like I'd be gone by June. "
                "Kept my head be-low the win-dow, kept my match-es dry, every{eh1 v r iy0} fist that came to find me "
                "struck an-oth-er light.")
VERSE2 = ('D3/8. D3/16 F3/8. D3/16 C3/8 D3 F3 D3 | r/1 | '          # Twenty winters in a cellar,
          'F3/8. D3/16 D3/8 C3 D3/4. r/8 | r/2. C3/8 C3 | '          # now I own the flame, all the
          'F3/8 F3 A3/4. G3/8 G3 F3 | r/2. r/8 C3/8 | '             # doors you nailed together make
          'E3/8 G3/4. E3/8 E3/4.~ | E3/4 r/2.')                     # a fine old blaze.
VERSE2_WORDS = ("Twen-ty win-ters in a cel-lar, now I own the flame, all the doors you nailed to-geth-er "
                "make a fine old blaze.")
PRE = ('F3/8 G3 Bb3/4. r/4 r/8 | '                                  # Bring the rain,
       'F3/8 G3 C4/8 Bb3/4. r/4 | '                                 # bring the water,
       'F3/8 G3 A3 G3 F3 G3 A3/4~ | A3/2 r/2 | '                    # bring the hoses and the hail,
       'A3/8 A3 Bb3 A3 G3 A3 C4 Bb3~ | Bb3/4 r/2. | '                # soaked all the way to the marrow,
       'A3/8 Bb3 A3/4 D4/4. r/8 | C#4/2 r/2')                       # so go on, try me
PRE_WORDS = ("Bring the rain, bring the wa-ter, bring the hos-es and the hail, "
             "soaked all the way to the mar-row, so go on, try me")
CHORUS = ('F4/8 E4 D4/4 r/8 D4/8 E4/8 A4/8~ | A4/4. G4/8 r/2 | '     # Strike me down, I catch fire,
          'G4/8 G4 G4/4. F4/8 E4 D4 | r/1 | '                        # every bruise is kindling,
          'F4/8 E4 D4/4 r/8 D4/8 E4/8 A4/8~ | A4/4. G4/8 r/2 | '     # strike me down, I catch fire,
          'E4/8 G4/4 F4/8 E4 D4 E4/4~ | E4/8 D4/2 r/4 r/8')          # I'll burn on into daylight.
CHORUS_WORDS = ("Strike me down, I catch fi-re, every{eh1 v r iy0} bruise is kin-dling, strike me down, I catch fi-re, "
                "I'll burn on in-to day-light.")
CHORUS_WE = CHORUS_WORDS.replace("I'll burn", "we'll burn")
CHANT = ('A3/4. A3/8 C4/4 D4/4 | C4/2 A3/4 r/4 | '                   # whoa, oh oh oh, oh oh
         'G3/4. G3/8 A3/4 C4/4 | A3/2 r/4 D4/8 r/8')                 # whoa, oh oh oh, oh - hey!
CHANT_WORDS = "Whoa, oh, oh, oh, oh, oh. Whoa, oh, oh, oh, oh, hey!"
BRIDGE = ('D4/8 D4/4 C4/8 D4/4 C4/8 Bb3/8 | A3/2 r/2 | '            # They poured the ocean on me,
          'Bb3/8 Bb3 D4/8 C4/16 r/16 Bb3/2 | r/1 | '                 # I was breathing smoke,
          'D4/8 D4 F4/4 D4/8 r/8 F4/8 D4/8~ | D4/2 r/2 | '           # still I kept one ember
          'Bb3/8 A3 D4/4. C4/8 A3/4~ | A3/2 r/2')                    # underneath my coat.
BRIDGE_WORDS = "They poured the o-cean on me, I was breath-ing smoke, still I kept one em-ber un-der-neath my coat."

LINES = {'verse1': (VERSE1, VERSE1_WORDS), 'verse2': (VERSE2, VERSE2_WORDS), 'pre': (PRE, PRE_WORDS),
         'chorus': (CHORUS, CHORUS_WORDS), 'chant': (CHANT, CHANT_WORDS), 'bridge': (BRIDGE, BRIDGE_WORDS)}
CHORUS_PEAKS = [3.5, 19.5]                       # the held A4 of "fire" (beats from the chorus start)
HEYS = 'r/1 | r/2 D4/8 r/8 r/4 | r/1 | r/2 D4/8 r/8 r/4 | r/1 | r/2 D4/8 r/8 r/4 | r/1 | r/1'   # on the half-time 3
HEY_WORDS = 'hey! hey! hey!'

# ------------------------------------------------------------------ the riff (guitarist.riff steps, 16th grid)
CELL = 'R> - . R . . R . R> - . R . . R .'          # 3 + 3 + 2 + 3 + 3 + 2: the verse / pre chug
BIG = 'R>! - - - - - R . R> - - . R . R .'            # the chorus: a ringing chord, then the half-time push


def riff(roots: str, cell: str = CELL) -> str:
    """One bar of `cell` per root (the riff player plays it at the section's energy)."""
    return ' | '.join(cell.replace('R', r) for r in roots.split())


# ------------------------------------------------------------------ percussion (taiko pitches: G1 huge, C3 medium)
TAIKO_STOMP = 'G1/4.=118 G1/8=92 r/2'
TAIKO_STOMP4 = 'G1/4.=118 G1/8=92 r/4 C3/8=78 C3/8=96'
TAIKO_DROP = 'G1/8=124 C3=70 C3=78 G1=104 r G1=98 C3=72 C3=86'
TAIKO_TRIBE = 'G1/8=124 C3/16=62 C3=70 C3/8=80 G1=106 r G1=100 C3=76 C3/16=70 C3=88'
CLAP3 = {'clap': '........x.......'}                         # the half-time backbeat (beat 3)
CLAP3_PUSH = {'clap': '........X.....x.'}

VOCALS = ('vocal', 'vocal_dbl_l', 'vocal_dbl_r', 'vocal_harm', 'gang', 'gang_dbl_l', 'gang_dbl_r', 'gang_harm', 'gang_dbl_hi')


def sub_root(chord) -> int:
    """The chord root as a sub note in F1..E2."""
    return 29 + (chord.root - 5) % 12


def build() -> Song:
    s = Song('Catch Fire', tempo=124, key='D minor', seed=7)
    P_INTRO, P_VERSE = 'i III VII VI', 'i:2 VI:2 III:2 VII:2'
    P_PRE, P_CHORUS = 'VI VII i i VI VII iv V', 'i III VII VI i III VII VII'
    P_BRIDGE = 'VI III iv i VI III iv V'
    intro = s.section('intro', 8, prog=P_INTRO)
    verse1 = s.section('verse1', 16, prog=P_VERSE)
    pre1 = s.section('pre1', 8, prog=P_PRE)
    chorus1 = s.section('chorus1', 8, prog=P_CHORUS)
    post1 = s.section('post1', 4, prog=P_INTRO)
    verse2 = s.section('verse2', 8, prog=P_VERSE)
    pre2 = s.section('pre2', 8, prog=P_PRE)
    chorus2 = s.section('chorus2', 8, prog=P_CHORUS)
    post2 = s.section('post2', 4, prog=P_INTRO)
    bridge = s.section('bridge', 8, prog=P_BRIDGE)
    build_ = s.section('build', 8, prog=P_PRE)
    chorus3 = s.section('chorus3', 16, prog=P_CHORUS)
    post3 = s.section('post3', 4, prog=P_INTRO)
    end = s.section('end', 2, prog='i:2')
    choruses, posts, pres = (chorus1, chorus2, chorus3), (post1, post2, post3), (pre1, pre2, build_)
    bpm = s.tempo

    # ------------------------------------------------------------------ the band (rock_band: kit, bass, guitars, piano)
    b = bands.rock_band(s, keys='piano', gain='crunch', without=('lead',))
    kit, bass, keys = b.drums, b.bass, b.keys
    gtrs = (b.gtr_l, b.gtr_r)
    taiko = s.track('taiko', inst.sf2('Taiko Drum', file=library.SAMPLES.joinpath(
        'musescore-general-sf2', 'MuseScore_General.sf2').as_posix(), release=1.5, width=1.3),
        fx=[fx.eq({'hp.freq': 75, 'peak1.freq': 300, 'peak1.gain': -3.0, 'peak1.q': 0.9})],
        gain_db=-3, sends={b.drum_room: -4}).humanize(timing_ms=5, vel=6)
    claps = s.track('claps', hand_perc(), gain_db=-2, sends={b.plate: -14, b.drum_room: -10}).humanize(timing_ms=4, vel=7)
    sub = s.track('sub', 'synthwave/sub_bass', gain_db=-3)
    pulse = s.track('pulse', 'synthwave/seq_pulse', gain_db=-9, pan=-0.2, sends={'echo': -5})
    choir = s.track('choir', 'sampled/choir_oh', gain_db=-6, sends={b.plate: -16})
    s.hall()                                         # the choir's own hall send (its patch default)
    fxh = s.transitions(riser=True, reverse=True, impact=True, down=True, pitch='D3')

    # ------------------------------------------------------------------ drums: the drummer (from verse 1's 2nd half)
    dmem = drummer.Memory()
    common = dict(bpm=bpm, style='rock', density=0.55, kit=kit, memory=dmem, hands='master')
    half = {'style': 'halftime', 'time': 'hat_loose'}       # a washy half-open hat: the arena top
    tribe = {'style': 'halftime', 'time': 'floor'}
    drummer.arrange([('intro', 4)], at=intro.bar(4), seed=3,
                    plan={'intro': dict(tribe, energy=0.78, crash=True)}, **common).play(kit)
    drummer.arrange([('verse1', 8), ('pre1', 8), ('chorus1', 8), ('post1', 4), ('verse2', 8), ('pre2', 8),
                     ('chorus2', 8), ('post2', 4)], at=verse1.bar(8), seed=5,
                    plan={'verse1': {'energy': 0.38, 'time': 'floor', 'mode': 'half'},
                          'pre1': {'energy': 0.62}, 'chorus1': dict(half, energy=0.92),
                          'post1': dict(tribe, energy=0.82), 'verse2': {'energy': 0.5, 'time': 'hat8'},
                          'pre2': {'energy': 0.66}, 'chorus2': dict(half, energy=0.96),
                          'post2': dict(tribe, energy=0.86)}, **common).play(kit)
    drummer.arrange([('build', 8), ('chorus3', 16), ('post3', 4), ('end', 2)], at=build_, seed=9, ending='hit',
                    plan={'build': {'energy': 0.7, 'time': 'floor'}, 'chorus3': dict(half, energy=1.0, time='crash'),
                          'post3': dict(tribe, energy=0.95)}, **common).play(kit)

    # taikos + claps: the stomp (intro, verse 1), the drop (choruses), the tribe (post-choruses, the build)
    stomp = notes(' | '.join([TAIKO_STOMP] * 3 + [TAIKO_STOMP4]))
    drop, tribal = notes(TAIKO_DROP), notes(TAIKO_TRIBE)
    taiko.plan({intro: stomp, verse1: stomp, pre1: [None, (4, stomp)], chorus1: drop, post1: tribal,
                verse2: [None, (4, stomp)], pre2: [None, (4, stomp)], chorus2: drop, post2: tribal,
                build_: [stomp, (4, tribal)], chorus3: drop, post3: tribal})
    clap3, push = drums(CLAP3), drums(CLAP3_PUSH)
    claps.plan({intro: [clap3, (3, push, 1), (4, clap3), (7, push, 1)],
                verse1: [clap3, (7, push, 1), (8, clap3), (15, push, 1)], pre1: clap3, chorus1: push,
                post1: push, verse2: clap3, pre2: clap3, chorus2: push, post2: push, build_: [None, (4, clap3)],
                chorus3: push, post3: push})

    # ------------------------------------------------------------------ bass (the bassist) + the sub under the drops
    bp = bassist.Player(bass, bpm=bpm, key=s.key, style='rock', memory=bassist.Memory())
    bp.play(s.prog(P_INTRO), intro.bar(4), 'intro', seed=1, kick='x.........x.....')
    bp.play(verse1.prog, verse1, 'verse', style='ballad', seed=2, energy=0.25)
    bp.play(verse1.prog, verse1.bar(8), 'verse', seed=3, kick='x.........x.....')
    for k, sec in enumerate(pres):
        bp.play(sec.prog, sec, 'pre', seed=10 + k, kick='x.......x.......')
    for k, sec in enumerate(choruses + posts):
        bp.play(sec.prog * (int(sec.bars) // 8 or 1), sec, 'chorus', seed=20 + k, kick='x.........x.....')
    bp.play(verse2.prog, verse2, 'verse', seed=4, kick='x.......x.x.....')
    bp.play(s.prog('VI III iv V'), bridge.bar(4), 'bridge', style='ballad', seed=5)
    bp.play(end.prog, end, 'outro', seed=6, ending='ring')
    for sec in choruses:                             # the sub is the drop's: the posts' floor toms own the lows
        for bar in range(int(sec.bars)):
            r = sub_root(sec.prog.at(bar * 4 % sec.prog.length))
            sub.note(r, sec.bar(bar), 1.6, 112).note(r, sec.bar(bar, 2.5), 1.2, 96)
    sub.note('D2', end, 6, 118)

    # ------------------------------------------------------------------ the guitar wall (riff player, two takes)
    gmem = gt.Memory()

    def wall(spec, at, energy, seed, **kw):
        part = gt.riff(spec, bpm=bpm, energy=energy, grid='1/16', seed=seed, memory=gmem, at=at, **kw)
        gt.double(part, gtrs, at, seed=seed)

    wall(riff('D F C Bb', BIG), intro.bar(4), 0.85, 1)
    wall(riff('D D Bb Bb F F C C'), verse1.bar(8), 0.4, 2)
    for k, sec in enumerate((pre1, pre2)):
        wall(riff('Bb C D D Bb C G A'), sec, 0.62 + 0.04 * k, 3 + k, into=choruses[k])
    for k, sec in enumerate(choruses):
        wall(riff(' '.join(['D F C Bb D F C C'] * int(sec.bars // 8)), BIG), sec, 0.92 + 0.04 * k, 6 + k)
    for k, sec in enumerate(posts):
        wall(riff('D F C Bb', BIG), sec, 0.86 + 0.04 * k, 10 + k)
    wall(riff('D D Bb Bb F F C C'), verse2, 0.45, 14)
    wall(riff('Bb C D D'), build_, 0.5, 15)
    wall(riff('Bb C G A'), build_.bar(4), 0.72, 16, into=chorus3)
    gt.double(gt.riff('D>! - - -', bpm=bpm, energy=0.95, grid='1/2', seed=17), gtrs, end, seed=17)
    for g in gtrs:
        g.levels({intro: -2, verse1: -6, pre1: -3, chorus1: 1.5, post1: 1, verse2: -5, pre2: -3, chorus2: 1.5,
                  post2: 1, bridge: -6, build_: [(0, -6), (4, -2.5)], chorus3: 2, post3: 1.5, end: 1}, glide=0.5)

    # ------------------------------------------------------------------ piano, choir, the synth pulse
    keys.chords(verse2, pre1, pre2, build_, rhythm='xxxxxxxx', voicing='close', register=('A3', 'D5'), voices=3,
                vel={verse2: 56, '*': 64}, crescendo={pre1: (0.85, 1.15), pre2: (0.85, 1.15), build_: (0.8, 1.2)},
                then=lambda c: c.arch(bars=2, depth=0.25))
    keys.chords(*choruses, rhythm='x.x.x.x.', voicing='close', register=('D5', 'D6'), voices=2, vel=70,
                then=lambda c: c.arch(bars=2, depth=0.2))
    keys.arp('updown', bridge, rate='1/8', register=('A3', 'F5'), vel=62, then=lambda c: c.arch(bars=2, depth=0.3))
    keys.chords(bridge, voices=1, register=('D2', 'C#3'), vel=64)
    keys.automate('instrument.pedal', pianist.pedal(bridge.prog, bridge))
    keys.send('echo', -60).lane('send.echo', {bridge: -12}, default=-60)
    choir.chords(intro, chorus1, post1, chorus2, post2, bridge, build_, chorus3, post3, voicing='spread',
                 register=('D3', 'A4'), voices=4, vel={bridge: 58, build_: 66, '*': 82},
                 bars={intro: (4, 8)}, crescendo={build_: (0.6, 1.15)})
    choir.play(hold('D3 A3 D4 F4', 7.5, 84), end)
    for t in gtrs + (choir,):                        # the last chord rings into the hall
        t.send('hall', -60).lane('send.hall', {end: (-30, -10)}, default=-60)
    pulse.arp('up', intro, verse1, pre1, verse2, pre2, build_, rate='1/8', register=('D4', 'D5'), vel=72,
              then=lambda c: c.arch(bars=2, depth=0.25))
    pulse.lane('instrument.cutoff', {intro: (300, 900, 'exp'), verse1: (700, 1300, 'exp'),
                                     pre1: (1300, 4200, 'exp'), verse2: 1000, pre2: (1300, 4500, 'exp'),
                                     build_: (500, 5000, 'exp')})

    # ------------------------------------------------------------------ the sung lead (TIGER), doubles, harmony
    mem = singer.Memory()
    # rock, but punchy rather than sliding: fewer scoops than the style's (wetness.py: 50 % of the onsets scooped)
    lead = dict(voice='tiger', style='rock', memory=mem, seed=4, scoop_first=0.35, scoop_leap=0.5, scoop_peak=0.7)
    singer.sing(s, VERSE1, VERSE1_WORDS, at=verse1, take=0, **lead)
    singer.sing(s, VERSE2, VERSE2_WORDS, at=verse2, take=1, **lead)
    pre_parts = [singer.sing(s, PRE, PRE_WORDS, at=sec, take=2 + k, base_power=0.3, **lead)
                 for k, sec in enumerate(pres)]
    ch_parts = [singer.sing(s, CHORUS, words, at=at, take=5 + k, peaks=CHORUS_PEAKS, base_power=1.0, power=0.6,
                            **lead)
                for k, (at, words) in enumerate([(chorus1, CHORUS_WORDS), (chorus2, CHORUS_WORDS),
                                                 (chorus3, CHORUS_WORDS), (chorus3.bar(8), CHORUS_WE)])]
    singer.sing(s, BRIDGE, BRIDGE_WORDS, at=bridge, take=9, soft=0.6, base_soft=0.3, vel=(62, 98), **lead)
    for k, vc in enumerate(ch_parts + pre_parts[-1:]):     # explicit takes: L and R are two performances
        singer.double(vc, pan=-0.85, track_id='vocal_dbl_l', take=100 + k)
        singer.double(vc, pan=0.85, track_id='vocal_dbl_r', take=110 + k)
    for k, vc in enumerate(ch_parts):
        singer.harmony(vc, steps=-2, key=s.key, pan=0.0, gain_db=-8, track_id='vocal_harm', take=120 + k)

    # ------------------------------------------------------------------ the gang: the chant + the "hey!" shouts
    gmem_v = singer.Memory()
    for k, at in enumerate([intro, intro.bar(4), post1, post2, post3]):
        g = singer.sing(s, CHANT, CHANT_WORDS, at=at, voice='tiger', style='rock', seed=11, take=20 + k,
                        memory=gmem_v, track_id='gang', base_power=0.7, gain_db=1.5)
        if k == 0:
            continue
        singer.double(g, pan=-0.85, track_id='gang_dbl_l', gain_db=-1.5, take=130 + k)
        singer.double(g, pan=0.85, track_id='gang_dbl_r', gain_db=-1.5, take=140 + k)
        singer.harmony(g, steps=-2, key=s.key, pan=-0.3, gain_db=-6, track_id='gang_harm', take=150 + k)
        singer.sing(s, CHANT, CHANT_WORDS, at=at, voice='hanami', style='pop', seed=12, take=30 + k, transpose=12,
                    track_id='gang_dbl_hi', gain_db=-11, pan=0.35)
    for k, at in enumerate([chorus1, chorus2, chorus3, chorus3.bar(8)]):
        h = singer.sing(s, HEYS, HEY_WORDS, at=at, voice='tiger', style='rock', seed=13, take=40 + k,
                        memory=gmem_v, track_id='gang', base_power=1.0)
        singer.double(h, pan=-0.85, track_id='gang_dbl_l', gain_db=-3, take=160 + k)
        singer.double(h, pan=0.85, track_id='gang_dbl_r', gain_db=-3, take=170 + k)

    tiger = {'deess': {'freq': 5500}}
    hero(s.tracks['vocal'], family='vocal', genre='rock', bed=[choir, pulse, b.gtr_l, b.gtr_r], competitors=[keys, claps], carve=5,
         **tiger)
    # the words through the wall: +1.5 dB at 3 kHz after the de-esser's band (TIGER's sibilants sit at 5.5 kHz)
    s.tracks['vocal'].add_fx(fx.eq({'peak1.freq': 3000, 'peak1.gain': 1.5, 'peak1.q': 1.0}, name='words'))
    for tid in VOCALS[1:]:                           # the gang's own "hey!" gets the echo throws
        hero(s.tracks[tid], family='vocal', genre='rock', ride=False, throws=tid == 'gang', duck=False, carve=False,
             dips=False, **({} if tid == 'gang_dbl_hi' else tiger))

    # ------------------------------------------------------------------ quiet-loud: the stomp under the verse voice, the arc
    taiko.levels({intro: 4, verse1: -2, pre1: -2, verse2: -4, pre2: -2, build_: 0, post1: 2, post2: 2, post3: 2,
                  '*': 3}, glide=0.5)
    fxh.riser.levels({'*': -6})                      # the riser leads into the drop, it must not out-shout it
    kit.send(b.drum_room, 2)     # the arena: more of the crushed room on the kit (preset: -1, KIT_GAIN off the fader)
    for g in gtrs:
        g.send(b.room, -9)
    s.arc({'intro': -5, 'verse1': -5, 'pre1': -4, 'verse2': -4.5, 'pre2': -3.5, 'bridge': -7, 'build': -4,
           'chorus3': 0.5, 'post3': 0.5, 'end': 0.5},
          within={'intro': [(16, -3, 'smooth')], 'pre1': [(24, -2.5, 'smooth')], 'pre2': [(24, -2, 'smooth')],
                  'build': [(16, -4), (31, -1.5, 'smooth')]})
    s.master.fx['limiter'].set(gain=5.0)            # less limiting: the drop must jump out of the pre-chorus

    # ------------------------------------------------------------------ transitions: risers, the breath, impacts
    vox = [s.tracks[t] for t in VOCALS]
    for sec in choruses:
        fxh.into(sec, riser=dict(beats=15, end=-1, dur=15), reverse=2, impact=('D2', 120), breath=1, keep=vox)
    fxh.into(verse1, down=('D3', 6, 90))
    fxh.into(verse2, down=('D3', 8, 96))
    fxh.into(bridge, down=('D3', 8, 104), impact=('D2', 100))

    # ------------------------------------------------------------------ the master (MASTER.md: mastering.match, rock, auto)
    s.master.fx['tape'].set(drive=4.0)              # the tape rounds the drum peaks: a denser chorus
    mastering.apply(s, eq={'high.freq': 6300, 'high.gain': 1.4, 'high.q': 0.7071, 'peak1.freq': 160, 'peak1.gain': 0.5,
                           'peak1.q': 1.0}, width=1.25, limiter={'ceiling': -1.2, 'release': 120.0},
                    loudness_change=+3.7)
    return s


