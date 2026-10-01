"""Vocal grit in a ROCK context: 'Exit Nine' - a sung lead over the band of The Drummer Speaks (116 BPM, E minor).

The grit A/B of songs/_demo_vocal was heard over a soft pop band and the user disliked every variant - maybe because
of the soft backing (recipes/HUMAN_FEEDBACK.md "Vocals"). This demo re-tests it where grit belongs: the rock_band of
songs/the-drummer-speaks as it is now (the Big Rusty kit, the riff through guitarist.riff + guitarist.double, the
bass rig, the organ), 2 bars of the chugged riff, a verse (4 bars of the palm-muted riff, the C D Em B7 turn) and a
chorus (C D Em Em C D B7 B7 at the chorus wall's energy), a 2-bar ending hit. The lead is SUNG (agentsound.singer) -
no lead guitar - on an original lyric (lyrics.txt).

Variants ($AGENTSOUND_ROCK_VOICE = tiger (default) | hanami, $AGENTSOUND_ROCK_GRIT = clean (default) | light | crunch
| megaphone | a grit dict as JSON): TIGER sings the line as written (male rock register, D3-A4), the verse in his rock
blend (Fresh + Electric by the dynamics), the chorus leaning on his power mode (Electric); Hanami sings it an octave
up (D4-A5, inside her F3-A5), leaning on her power mode (Fragrance) the same way. grit_rock_ab.py builds the
level-matched set into out/grit_rock_ab/.
Build: python -m agentsound build songs/_demo_vocal_rock   (needs the voicebanks + the WSL singing venv)
"""
import json
import os

from agentsound import *
from agentsound import bands, bassist, drummer, mastering, patches, singer
from agentsound import guitarist as gt

ANALYSIS = {'profile': 'rock'}
VOICE = os.environ.get('AGENTSOUND_ROCK_VOICE', 'tiger')
GRIT = os.environ.get('AGENTSOUND_ROCK_GRIT', 'clean')
METADATA = {'title': 'Exit Nine (vocal grit test)', 'artist': 'AgentSound', 'album': 'Demos', 'genre': 'Rock',
            'year': 2026}
COVER = {'style': 'rock'}

# the band's mix moves of The Drummer Speaks (its MIX.md) without the lead guitar's
MIX = {
    'trim': {'drums': 2.0, 'bass': 1.0},
    'duck': [{'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 4, 'attack': 2, 'release': 110}],
    'eq': {'drums': [{'freq': 42, 'gain': -2.5, 'q': 0.8}]},
}

BPM = 116
HANDS = 'master'
RIFF_SPEC = 'E> - . E . . G> - - . A - G E - . | D> - . B - . A - . . E . G A# B> -'

# ------------------------------------------------------------------ the lyric (lyrics.txt), one token per note
VERSE_LYRICS = ("Keys on the counter, coffee still hot, dog in the back seat, he don't ask why -. "
                "Sold the TV for a tank of gas, honked{hh aa1 ng k t} twice at the county line.")
CHORUS_LYRICS = ("All the way to Exit Nine, tore the mirror off, threw it in the pines. "
                 "All the way to Exit Nine -, radio's loud and the dog don't mind -.")

# (start beat, length, note) in the male register (TIGER as written; Hanami +12)
VERSE = Clip([
    # Keys on the counter, coffee still hot,                         (the palm-muted riff, Em)
    (0.0, 0.5, 'E3'), (0.5, 0.25, 'E3'), (0.75, 0.25, 'D3'), (1.0, 0.5, 'G3'), (1.5, 0.5, 'E3'),
    (2.0, 0.5, 'D3'), (2.5, 0.5, 'E3'), (3.0, 0.5, 'G3'), (3.5, 2.0, 'A3'),
    # dog in the back seat, he don't ask why -
    (8.0, 0.375, 'E3'), (8.375, 0.375, 'E3'), (8.75, 0.25, 'D3'), (9.0, 0.5, 'G3'), (9.5, 0.75, 'E3'),
    (10.5, 0.5, 'D3'), (11.0, 0.5, 'E3'), (11.5, 0.5, 'G3'), (12.0, 1.5, 'B3'), (13.5, 0.75, 'A3'),
    # Sold the TV for a tank of gas,                                  (C | D)
    (16.0, 0.75, 'G3'), (16.75, 0.25, 'G3'), (17.0, 0.5, 'A3'), (17.5, 0.75, 'B3'), (18.25, 0.25, 'A3'),
    (18.5, 0.5, 'G3'), (19.0, 0.5, 'A3'), (19.5, 0.5, 'G3'), (20.0, 1.75, 'A3'),
    # honked twice at the county line.                                (Em | B7)
    (24.0, 0.75, 'B3'), (24.75, 0.75, 'B3'), (25.5, 0.25, 'A3'), (25.75, 0.25, 'G3'), (26.0, 0.75, 'A3'),
    (26.75, 0.25, 'G3'), (27.0, 2.5, 'F#3'),
], length=32)

CHORUS = Clip([
    # All the way to Exit Nine,                                       (C | D) - 'Nine' pushed a 16th late
    (0.0, 0.5, 'E4'), (0.5, 0.5, 'D4'), (1.0, 0.75, 'G4'), (1.75, 0.25, 'E4'), (2.0, 0.5, 'G4'), (2.5, 0.75, 'E4'),
    (3.25, 2.75, 'A4'),
    # tore the mirror off, threw it in the pines.                  (Em | Em)
    (8.0, 0.5, 'G4'), (8.5, 0.25, 'E4'), (8.75, 0.5, 'E4'), (9.25, 0.25, 'D4'), (9.5, 1.0, 'G4'),
    (10.5, 0.25, 'E4'), (10.75, 0.5, 'D4'), (11.25, 0.5, 'E4'), (11.75, 0.25, 'D4'),
    (12.0, 2.5, 'E4'),
    # All the way to Exit Nine -                                      (C | D) - the leap to the top on 'way'
    (16.0, 0.5, 'E4'), (16.5, 0.5, 'D4'), (17.0, 0.75, 'A4'), (17.75, 0.25, 'G4'), (18.0, 0.5, 'G4'),
    (18.5, 0.75, 'E4'), (19.25, 1.75, 'A4'), (21.0, 1.0, 'F#4'),
    # radio's loud and the dog don't mind -                           (B7 | B7)
    (24.0, 0.25, 'F#4'), (24.25, 0.25, 'E4'), (24.5, 0.5, 'D#4'), (25.0, 1.0, 'F#4'), (26.0, 0.75, 'E4'),
    (26.75, 0.25, 'D#4'), (27.0, 0.5, 'E4'), (27.5, 0.5, 'F#4'), (28.0, 2.0, 'F#4'), (30.0, 1.5, 'E4'),
], length=32)
CHORUS_PEAKS = [3.25, 17.0, 19.25]


def build() -> Song:
    s = Song('Exit Nine (vocal grit test)', tempo=BPM, key='E minor', seed=11)
    intro = s.section('intro', bars=2)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    tail = s.section('tail', bars=2)

    kit_sound = patches.get('sampled/big_rusty_kit').but(level=1.0, restrike=6.0)
    b = bands.rock_band(s, without=('lead',), sounds={'drums': kit_sound})
    kit = b.drums
    s.node(kit.output).add_fx(fx.compressor(threshold=-9, ratio=8, attack=0.3, release=60, knee=3, detector='peak'))
    s.hall()

    # ------------------------------------------------------------------ the riff, the turn, the chorus wall
    rb = Clip([(t, d, note(n), 100 * a) for t, d, n, a in [
        (0.0, 0.5, 'E1', 1.0), (0.75, 0.25, 'E1', 0.7), (1.5, 0.75, 'G1', 0.9), (2.5, 0.5, 'A1', 0.86),
        (3.0, 0.25, 'G1', 0.7), (3.25, 0.5, 'E1', 0.7), (4.0, 0.5, 'D2', 1.0), (4.75, 0.5, 'B1', 0.7),
        (5.5, 0.5, 'A1', 0.88), (6.5, 0.25, 'E1', 0.7), (7.0, 0.25, 'G1', 0.7), (7.25, 0.25, 'A#1', 0.7),
        (7.5, 0.5, 'B1', 0.95)]], length=8)
    for k, (at, times, energy) in enumerate([(intro.start, 1, 0.62), (verse.start, 2, 0.45)]):
        b.bass.play(rb.articulate('staccato', where=lambda n: n.dur < 0.5), at, times=times)
        gt.double(gt.riff(RIFF_SPEC, bpm=BPM, energy=energy, grid='1/16', length=8 * times, seed=40 + k),
                  (b.gtr_l, b.gtr_r), at, seed=k)
    prog_a = s.prog('C D Em B7')
    prog_b = s.prog('C D Em Em C D B7 B7')
    bassist.arrange(prog_a, bpm=BPM, key=s.key, style='rock', part='verse', kick='x.....x.x.......',
                    seed=3).place(b.bass, verse.bar(4))
    bassist.arrange(prog_b, bpm=BPM, key=s.key, style='rock', part='chorus', kick='x.....x.x.......',
                    seed=6).place(b.bass, chorus)
    turn = 'C> - - - C - C - | D> - - - D - D - | E> - - - E - E - | B> - - - B - B -'
    wall = turn.replace('E> - - - E - E - | B> - - - B - B -',
                        'E> - - - E - E - | E> - - - E - E - | C> - - - C - C - | D> - - - D - D - | '
                        'B> - - - B - B - | B> - - - B - B -')
    gt.double(gt.riff(turn, bpm=BPM, energy=0.6, seed=60), (b.gtr_l, b.gtr_r), verse.bar(4), seed=10)
    gt.double(gt.riff(wall, bpm=BPM, energy=0.95, seed=71), (b.gtr_l, b.gtr_r), chorus, seed=21)
    gt.double(gt.riff('E>! -', bpm=BPM, energy=0.95, grid='1/2', seed=82), (b.gtr_l, b.gtr_r), tail, seed=32)
    for gtr in (b.gtr_l, b.gtr_r):
        gtr.automate('gainDb', per_section({intro: -2, verse: -4, chorus: 0, tail: 0}, glide=0.5))
        gtr.automate('send.room', hold(0, tail.start - 0.5, -13), ramp(tail.start - 0.5, tail.start, -13, -6),
                     hold(tail.start, tail.end, -6))
    b.bass.note('E1', tail.start, 3.8, 116)

    # ------------------------------------------------------------------ organ (the swell pedal breathes)
    org = b.keys
    org.play(s.prog('Em7').block(voicing='spread', register=('E3', 'E5'), vel=62).stretch(2), intro)
    org.play(s.prog('Em7 Em7').block(voicing='spread', register=('E3', 'E5'), vel=68), verse, times=2)
    org.play(prog_a.block(voicing='drop2', register=('G3', 'G5'), rhythm='x...x.x.', vel=80), verse.bar(4))
    org.play(prog_b.block(voicing='drop2', register=('G3', 'G5'), rhythm='x..x..x.', vel=96), chorus)
    org.play(s.prog('Em').block(register=('E3', 'B4'), vel=100).stretch(2), tail)
    swell = []
    for at in (intro.start, verse.start, verse.bar(2)):
        t0 = s._at(at)
        swell += [(t0, 0.62), (t0 + 3.0, 0.92, 'smooth'), (t0 + 6.5, 0.74, 'smooth')]
    t0 = s._at(verse.bar(4))
    swell += [(t0, 0.78), (t0 + 6.0, 0.9, 'smooth'), (t0 + 11.0, 0.8, 'smooth'), (t0 + 15.5, 0.95, 'smooth')]
    t0 = s._at(chorus)
    swell += [(t0, 0.86), (t0 + 10.0, 1.0, 'smooth'), (t0 + 16.0, 0.88, 'smooth'), (t0 + 24.0, 1.0, 'smooth'),
              (t0 + 31.5, 0.92, 'smooth')]
    t0 = s._at(tail)
    swell += [(t0, 0.95), (t0 + 7.0, 0.4, 'smooth')]
    org.automate('instrument.expression', swell)
    org.automate('fx.tremolo.rate', hold(intro.start, chorus.start, 0.9), ramp(chorus.start, chorus.bar(1), 0.9, 6.4),
                 hold(chorus.bar(1), tail.end, 6.4))

    # ------------------------------------------------------------------ drums
    mem = drummer.Memory()
    drummer.arrange([('intro', 2), ('verse', 8), ('chorus', 8)], bpm=BPM, style='rock', density=0.55, seed=21,
                    kit=kit, at=intro.start, memory=mem, lock=b.bass, hands=HANDS,
                    plan={'intro': {'energy': 0.62, 'crash': True}, 'verse': {'energy': 0.55, 'time': 'hat8'},
                          'chorus': {'energy': 0.95, 'time': 'ride'}}).play(kit)
    drummer.perform([('hit_choke', 1, 1.0)], bpm=BPM, kit=kit, at=tail.start, seed=12, hands=HANDS).play(kit)

    # ------------------------------------------------------------------ the sung lead
    male = VOICE == 'tiger'
    grit = None if GRIT == 'clean' else json.loads(GRIT) if GRIT.startswith('{') else GRIT
    lead = dict(voice=VOICE, style='rock', seed=3, transpose=0 if male else 12)
    vmem = singer.Memory()
    # the verse: the rock blend (core + power by the dynamics); the chorus leans on the power mode
    # (TIGER: Electric, Hanami: Fragrance) - the blend keeps the air moves (swells, accents) a fixed mode drops
    vox = singer.sing(s, VERSE, VERSE_LYRICS, at=verse, memory=vmem, **lead)
    vch = singer.sing(s, CHORUS, CHORUS_LYRICS, at=chorus, memory=vmem, peaks=CHORUS_PEAKS, take=1,
                      base_power=1.0, power=0.6, **lead)
    hero(vox.track, family='vocal', genre='rock', bed=[b.keys], competitors=[b.gtr_l, b.gtr_r], grit=grit,
         **({'deess': {'freq': 5500}} if male else {}))

    mastering.apply(s, eq={'low.freq': 60, 'low.gain': -0.8, 'low.q': 0.7071, 'peak1.freq': 400, 'peak1.gain': 2.0,
                           'peak1.q': 1.0}, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+3.5)
    print(vox.describe())
    print(vch.describe())
    return s
