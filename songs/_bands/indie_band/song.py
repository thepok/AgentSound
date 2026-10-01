"""indie_band demo: 'Paper Satellites' - 24 bars of driving indie rock in D major at 152 BPM, built only from the
indie_band preset and ordinary composition code: a jangly arpeggio intro, a verse over floor-tom drums with the
crunch guitar palm-muting, a chorus with open chords, octave lead melody and open hats.

Credits: Karoryfer Big Rusty Drums / Emilyguitar / Fashionbass / Shinyguitar (CC0), FreePats FSBS guitar (CC0),
Greg Sullivan Wurlitzer EP200 (CC-BY 3.0), Lexicon 224XL room / plate (Little Devil), Overdriven cabinet IRs.
"""
from agentsound import *
from agentsound import articulation as art, bands

ANALYSIS = {'profile': 'rock'}
METADATA = {'title': 'Paper Satellites', 'artist': 'AgentSound', 'album': 'Band Presets', 'genre': 'Indie Rock'}


def build() -> Song:
    s = Song('Paper Satellites', tempo=152, key='D major', seed=11)
    intro = s.section('intro', bars=4)
    verse = s.section('verse', bars=8)
    chorus = s.section('chorus', bars=8)
    outro = s.section('outro', bars=4)

    b = bands.indie_band(s)
    prog = s.prog('D A Bm G')
    cprog = s.prog('G D A Bm')

    # --- jangle guitar (left): add9 arpeggios, then 8th strums in the chorus
    held = prog.block(voicing='spread', register=('D3', 'F#5'), vel=90)
    jangle = held.arpeggiate('pinky', rate='1/8', gate=1.4)
    b.gtr_l.loop(jangle, intro, verse)
    strum = cprog.block(voicing='spread', register=('D3', 'F#5'), rhythm='x.xxx.x.xx.x.xx.', step='1/16', vel=96)
    b.gtr_l.loop(strum.strum(ms=9, bpm=s.tempo, direction='alternate'), chorus)
    b.gtr_l.play(jangle.slice(0, 8), outro)                   # the jangle stops for the final chord

    # --- crunch guitar (right): palm-muted 8ths in the verse, open power chords in the chorus
    roots = Clip([(bar * 4 + i * 0.5, 0.45, r, 100) for bar, r in enumerate(['D2', 'A2', 'B2', 'G2'])
                  for i in range(8)], length=16)
    b.gtr_r.loop(roots.chordify('power').articulate('palm').strum(ms=6, bpm=s.tempo), verse)
    ch = Clip([(bar * 4 + t, d, r, 108) for bar, r in enumerate(['G2', 'D3', 'A2', 'B2'])
               for t, d in ((0, 1.45), (1.5, 1.0), (2.5, 1.45))], length=16)
    b.gtr_r.loop(ch.chordify('power').strum(ms=10, bpm=s.tempo, direction='alternate'), chorus)
    b.gtr_r.play(Clip([(0, 7.5, 'D2', 110)], length=8).chordify('power').strum(ms=14, bpm=s.tempo), outro.bar(2))

    # --- drums: floor-tom groove in the verse, open-hat drive in the chorus
    b.drums.loop(drums({'kick': 'x.......x.x.....', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=86), intro)
    b.drums.play(snare_roll(2, build=True), intro.bar(3, 2), replace=True)
    b.drums.play(crash(), verse)
    b.drums.loop(drums({'kick': 'x.......x.x.....', 'snare': '....x.......x...', 'tom_lo': 'x.x.x.x.x.x.x.x.'},
                       vel=92), verse)
    b.drums.play(tom_fill(2), verse.bar(-1, 2), replace=True)
    b.drums.play(crash(), chorus).play(crash(), chorus.bar(4))
    b.drums.loop(drums({'kick': 'x.....x.x.......', 'snare': '....X.......X...', 'ohh': 'x.x.x.x.x.x.x.x.'},
                       vel=106), chorus)
    b.drums.play(drums({'kick': 'x...............', 'crash': 'x...............'}, vel=118), outro.bar(2))

    # --- bass: 8ths with octave jumps
    b.bass.loop(prog.bass('octave', rate='1/8', low='D1', vel=92), verse)
    b.bass.loop(cprog.bass('octave', rate='1/8', low='D1', vel=104), chorus)
    b.bass.note('D2', outro.bar(2), 7.5, 104)

    # --- Wurlitzer offbeats
    b.keys.loop(prog.block(voicing='drop2', register=('A3', 'A4'), rhythm='..x...x.', step='1/8', vel=80), verse)
    b.keys.loop(cprog.block(voicing='drop2', register=('A3', 'A4'), rhythm='x..x..x.', step='1/8', vel=86), chorus)

    # --- lead: verse answer phrases, chorus octave melody with slides and vibrato
    # (durations in beats: 0.5 = an 8th)
    v = s.motif('r:2 3:1 2:1 | 1:1 2:0.5 3:0.5 5:2 | r:2 6:1 5:1 | 3:1 2:0.5 1:0.5 2:2').clip(octave=4, vel=92)
    c = s.motif('5:1 6:0.5 5:0.5 3:1 2:1 | 1:2 3:1 5:1 | 6:1 8:0.5 6:0.5 5:1 3:1 | 5:4').clip(octave=4, vel=104)
    c = c.octave_double(12, vel=0.85)
    b.lead.play(v, verse).play(v, verse.bar(4))
    b.lead.play(c, chorus).play(c, chorus.bar(4))
    art.vibrato(b.lead, v, verse, depth=20, rate=5.5)
    art.vibrato(b.lead, c, chorus, depth=22, rate=5.8)
    # the last chord rings into the plate
    for tr in (b.gtr_l, b.gtr_r, b.keys):
        tr.automate('send.plate', hold(verse.start, outro.bar(2), -18), ramp(outro.bar(2), outro.bar(3), -18, -6))
    b.keys.play(s.prog('D').block(voicing='drop2', register=('A3', 'A4'), vel=84).stretch(2), outro.bar(2))
    return s
