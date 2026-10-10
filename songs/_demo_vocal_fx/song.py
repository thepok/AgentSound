"""Processed-voice effects demo (singer.sing(tune=), singer.prism, singer.mouth + speech.talkbox): original lyrics
(lyrics.txt), short builds for A/B listening - make_ab.py builds every variant into out/fx_ab/ with a README.txt.

$AGENTSOUND_VOCAL_FX = one of:
  natural     'Radio Heart' (A minor, 96 BPM, Am F C G x2): Hanami sings 8 bars over a light pop band (drums, bass,
              Rhodes, pad) - no pitch correction (the reference)
  hard        the same, sing(tune='hard'): retune 0 ms - the robotic Cher / T-Pain step, a flip on every note change
  soft        the same, sing(tune='soft'): 40 ms - held notes centred, the transitions and some vibrato kept
  choir       natural lead + singer.prism(preset='choir-of-one'): 4 re-sung takes on the chord tones (3 under, 1 over)
  prismizer   hard-tuned lead + singer.prism(preset='prismizer'): 4 hard-tuned takes + one an octave under, wide
              formants, tight, panned wall to wall (Bon Iver / Francis and the Lights)
  talkbox     'Box Talk' (E dorian funk, 100 BPM, 6 bars): a funk_band groove (drums, bass, clav, scratch guitar) and a
              lead guitar played THROUGH A TALK BOX - TIGER mouths the words (singer.mouth) and the vocoder in LPC
              mode (speech.talkbox) shapes the amp's sound with them
  guitar      the same groove and lead guitar line WITHOUT the talk box (the reference for 'talkbox')
$AGENTSOUND_VOCAL_FX_SOLO=1: the voices alone (the band muted) - the correction is easiest to hear there.
Build: AGENTSOUND_VOCAL_FX=hard python -m agentsound build songs/_demo_vocal_fx   (needs the voicebanks + the WSL
singing venv: COMPOSE_API "Vocals"). Voices Hanami / TIGER: non-commercial - private listening.
"""
import os

from agentsound import *
from agentsound import articulation as art, bands, singer, speech
from agentsound.humanize import touch

VARIANT = os.environ.get('AGENTSOUND_VOCAL_FX', 'natural')
SOLO = bool(os.environ.get('AGENTSOUND_VOCAL_FX_SOLO'))      # 1: the voices alone (the band muted)
TALK = VARIANT in ('talkbox', 'guitar')
ANALYSIS = {'profile': 'pop'}
METADATA = {'title': f"{'Box Talk' if TALK else 'Radio Heart'} (vocal fx: {VARIANT})", 'artist': 'AgentSound',
            'album': 'Demos', 'genre': 'Funk' if TALK else 'Pop', 'year': 2026}
COVER = {'style': 'pop'}

# ------------------------------------------------------------------ 'Radio Heart' (lyrics.txt), one token per note
LYRICS = ("Paper moon over the parking lot, I can feel the signal, I can feel it drop. "
          "Turn it up, turn it up, all the static in my heart, we were made of radio and falling apart.")
MELODY = Clip([
    # Paper moon over the parking lot,                    (Am | F)
    (0.0, 0.5, 'E4'), (0.5, 0.5, 'E4'), (1.0, 1.0, 'A4'), (2.0, 0.5, 'G4'), (2.5, 0.5, 'A4'), (3.0, 0.5, 'G4'),
    (3.5, 0.75, 'E4'), (4.25, 0.25, 'D4'), (4.5, 2.0, 'C4'),
    # I can feel the signal, I can feel it drop.          (C | G)
    (8.0, 0.5, 'C4'), (8.5, 0.5, 'D4'), (9.0, 1.0, 'E4'), (10.0, 0.5, 'G4'), (10.5, 0.5, 'G4'), (11.0, 0.5, 'E4'),
    (11.5, 0.5, 'D4'), (12.0, 0.5, 'D4'), (12.5, 0.5, 'E4'), (13.0, 0.5, 'D4'), (13.5, 2.0, 'B3'),
    # Turn it up, turn it up, all the static in my heart, (Am | F) - the hook
    (16.0, 0.5, 'A4'), (16.5, 0.25, 'A4'), (16.75, 0.75, 'C5'), (17.5, 0.5, 'A4'), (18.0, 0.25, 'A4'),
    (18.25, 0.75, 'C5'), (19.0, 0.5, 'B4'), (19.5, 0.5, 'A4'), (20.0, 0.5, 'A4'), (20.5, 0.5, 'G4'),
    (21.0, 0.5, 'A4'), (21.5, 0.5, 'C5'), (22.0, 1.5, 'C5'),
    # we were made of radio and falling apart.            (C | G)
    (24.0, 0.5, 'G4'), (24.5, 0.5, 'E4'), (25.0, 1.0, 'G4'), (26.0, 0.5, 'E4'), (26.5, 0.5, 'D4'), (27.0, 0.5, 'E4'),
    (27.5, 0.5, 'G4'), (28.0, 0.5, 'A4'), (28.5, 0.5, 'G4'), (29.0, 0.5, 'E4'), (29.5, 0.5, 'D4'), (30.0, 2.0, 'D4'),
], length=32)
PEAKS = [16.75, 18.25, 22.0]

# ------------------------------------------------------------------ 'Box Talk': what the talk box says
TALK_LYRICS = "Talk to me, talk to me, say it slow. Ooh wah, let the box do the talk-ing."
TALK_LINE = Clip([
    # Talk to me, talk to me, say it slow.                (Em7 | A7)
    (0.0, 0.5, 'B4'), (0.5, 0.25, 'D5'), (0.75, 0.75, 'E5'), (1.75, 0.5, 'B4'), (2.25, 0.25, 'D5'),
    (2.5, 1.0, 'E5'), (4.0, 0.5, 'G5'), (4.5, 0.5, 'E5'), (5.0, 2.0, 'D5'),
    # Ooh wah, let the box do the talking.                (Em7 | A7)
    (8.0, 1.0, 'E5'), (9.0, 1.5, 'G5'), (11.0, 0.5, 'E5'), (11.5, 0.25, 'D5'), (11.75, 0.75, 'E5'),
    (12.5, 0.5, 'D5'), (13.0, 0.5, 'B4'), (13.5, 0.5, 'D5'), (14.0, 2.0, 'E5'),
], length=16)
SW = 0.55


def radio_heart() -> Song:
    s = Song(METADATA['title'], tempo=96, key='A minor', seed=7)
    intro = s.section('intro', bars=1)
    verse = s.section('verse', bars=8)
    tail = s.section('tail', bars=1)
    b = bands.pop_band(s, without=('perc', 'pluck', 'lead'), keys='rhodes')
    prog = s.prog('Am F C G')
    b.pad.loop(prog.block(voicing='spread', register=('E3', 'E5'), vel=70), verse)
    b.pad.play(s.prog('Am').block(voicing='spread', register=('E3', 'E5'), vel=60), intro)
    b.pad.play(s.prog('Am').block(voicing='spread', register=('E3', 'E5'), vel=64), tail)
    b.keys.loop(touch(prog.block(voicing='drop2', register=('A3', 'C5'), rhythm='x..x..x.', step='1/8', vel=62), 50, 76),
                verse)
    b.keys.play(s.prog('Am').block(voicing='drop2', register=('A3', 'C5'), vel=58), tail)
    b.drums.loop(drums({'kick': 'x.........x.....', 'snare': '....x.......x...', 'hat': '..x...x...x...x.'},
                       vel=92), verse)
    b.drums.play(drums({'kick': 'x...............', 'crash': 'x...............'}, vel=100), tail)
    b.bass.loop(prog.bass('root', rate='1/2', low='E1', vel=80), verse)
    b.bass.note('A1', tail.start, 3.5, 90)

    # the vocal: Hanami, pop, the same seed / take in every variant - only the processing differs
    tune = {'hard': 'hard', 'soft': 'soft', 'prismizer': 'hard'}.get(VARIANT)
    vox = singer.sing(s, MELODY, LYRICS, at=verse, voice='hanami', style='pop', seed=3, peaks=PEAKS, tune=tune)
    hero(vox.track, family='vocal', genre='pop', bed=[b.pad], competitors=[b.keys])
    if VARIANT in ('choir', 'prismizer'):
        pr = singer.prism(vox, s.harmony('Am F C G Am F C G', at=verse), preset='choir-of-one'
                          if VARIANT == 'choir' else 'prismizer')
        # the stack's own small space: thinned below 180 Hz (the lead owns the body), a touch of air, the plate
        pr.bus.add_fx(fx.eq(hp__freq=180, peak1__freq=350, peak1__gain=-2.0, high__freq=9000, high__gain=1.5))
        pr.bus.send(s.node('plate'), -12)
        print(pr, [[note_name(p) for p in L[:4]] for L in pr.pitches])
    if SOLO:
        for t in (b.drums, b.bass, b.keys, b.pad):
            t.mute = True
    print(vox.describe())
    return s


def box_talk() -> Song:
    s = Song(METADATA['title'], tempo=100, key='E dorian', seed=41)
    intro = s.section('intro', bars=2)
    talk = s.section('talk', bars=4)
    b = bands.funk_band(s, without=('horns', 'lead'))
    groove = drums({'kick': 'x.....x...x..x..', 'snare': '....X..o.o..X..o', 'hat': 'xxxxxxxxxxxxxxxx'},
                   vel=100).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16').swing(SW)
    b.drums.loop(groove, intro, talk)
    b.drums.play(crash(), talk)
    scratch = []
    for i, ch in enumerate('x.xXx.xxx.xXx.xx'):
        if ch in 'Xx':
            scratch += [(i * 0.25, 0.2 if ch == 'X' else 0.1, note(p), 96 + (14 if ch == 'X' else 0))
                        for p in ('D4', 'F#4', 'B4')]
    sc = Clip(scratch, length=4).articulate('dead', where=lambda n: n.dur < 0.15)
    b.gtr.loop(sc.swing(SW).strum(ms=5, bpm=s.tempo, direction='alternate'), intro, talk)
    line = Clip([(0, 0.45, 'E1', 112), (0.75, 0.2, 'E1', 70), (1.5, 0.2, 'E2', 100), (1.75, 0.2, 'D2', 90),
                 (2.5, 0.45, 'E1', 105), (3.0, 0.2, 'G1', 95), (3.25, 0.2, 'G#1', 100), (3.5, 0.4, 'B1', 104)],
                length=4)
    b.bass.loop(line.articulate('staccato', where=lambda n: n.dur < 0.3).swing(SW), intro, talk)
    clav = Clip([(i * 0.25, 0.15, note(p), 96) for i, ch in enumerate('x..x..x.x..x.x..') if ch == 'x'
                 for p in ('D4', 'G4')], length=4)
    b.keys.loop(clav.swing(SW), intro, talk)

    # the talk box: a DI Strat through the lead amp; the guitarist plays the line legato (slides between the notes),
    # TIGER mouths the words in the same rhythm (one low steady pitch), the vocoder in LPC mode is the tube + mouth
    gtr = s.track('talkbox', 'sampled/lead_guitar', pan=0.0, gain_db=3.0 if VARIANT == 'talkbox' else 0.0,
                  sends={'plate': -16})
    line = touch(TALK_LINE.transpose(-12), 82, 118)      # B3-G4: the mid register speaks (dense harmonics)
    play = art.legato(line, overlap=0.04).glide(70, where=art.leaps(2))
    gtr.play(play, talk)
    art.vibrato(gtr, line, talk, depth=18, rate=5.2)
    if VARIANT == 'talkbox':
        m = singer.mouth(s, TALK_LINE, TALK_LYRICS, at=talk, voice='tiger', seed=5)
        speech.talkbox(gtr, m, mute=not os.environ.get('AGENTSOUND_TALK_MOUTH'))   # (=1: the mouth audible: a check)
        print(m.describe())
    print([f.type for f in gtr.fx])
    return s


def build() -> Song:
    return box_talk() if TALK else radio_heart()
