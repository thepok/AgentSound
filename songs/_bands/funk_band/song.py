"""funk_band demo: 'Brass Tacks' - 24 bars of funk in E at 104 BPM, built only from the funk_band preset and ordinary
composition code: a drums + chicken-scratch guitar intro, an E9 vamp with syncopated bass, clavinet and horn stabs
under a tenor sax line, an A9 / B7#9 B section with horn swells, and a hit ending.

Credits: Orange Tree Jazz Funk Kit (freeware, no redistribution), FreePats FSBS guitar, Karoryfer Growlybass /
Emilyguitar dead-note scratches (CC0), Lithalean Clavinet (licence not stated), Virtual Playing Orchestra 3 brass (Paul
Battersby), MTG solo tenor sax (CC-BY 4.0), Lexicon 224XL ambience / plate (Little Devil), Overdriven clean cabinet IR.
"""
from agentsound import *
from agentsound import articulation as art, bands

ANALYSIS = {'profile': 'pop'}
METADATA = {'title': 'Brass Tacks', 'artist': 'AgentSound', 'album': 'Band Presets', 'genre': 'Funk'}

SW = 0.55    # 16th swing: the pocket


def scratch(voicing, pattern, bars=1, vel=96):
    """Chicken-scratch guitar: 16th strums of `voicing`; 'X' open accent, 'x' dead-note scratch, '.' rest."""
    notes = []
    for bar in range(bars):
        for i, ch in enumerate(pattern):
            if ch in 'Xx':
                for p in voicing:
                    notes.append((bar * 4 + i * 0.25, 0.2 if ch == 'X' else 0.1, note(p),
                                  vel + (14 if ch == 'X' else 0)))
    c = Clip(notes, length=bars * 4)
    return c.articulate('dead', where=lambda n: n.dur < 0.15)


def stabs(voicing, pattern, vel=100, dur=0.2, bars=1):
    notes = [(bar * 4 + i * 0.25, dur, note(p), vel) for bar in range(bars) for i, ch in enumerate(pattern)
             if ch == 'x' for p in voicing]
    return Clip(notes, length=bars * 4)


def build() -> Song:
    s = Song('Brass Tacks', tempo=104, key='E dorian', seed=41)
    intro = s.section('intro', bars=4)
    a = s.section('groove', bars=8)
    bsec = s.section('bridge', bars=8)
    out = s.section('out', bars=4)

    b = bands.funk_band(s)
    E9 = ['G#3', 'D4', 'F#4', 'B4']
    A9 = ['C#4', 'G4', 'B4', 'E5']
    B7 = ['A3', 'D#4', 'A4', 'D5']        # B7#9 top: 7 3 7 #9

    # --- drums: 16th hats with accents, syncopated kick, ghosted snare
    groove = drums({'kick': 'x.....x...x..x..', 'snare': '....X..o.o..X..o', 'hat': 'xxxxxxxxxxxxxxxx'},
                   vel=100).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16').swing(SW)
    groove2 = drums({'kick': 'x.x...x...x..x..', 'snare': '....X..o.o..X.oo', 'hat': 'xxxxxxxxxxxxxx.x',
                     'ohh': '..............x.'}, vel=100).vel_pattern([1.15, 0.7, 0.9, 0.7], grid='1/16').swing(SW)
    b.drums.loop(drums({'kick': 'x.........x.....', 'rim': '....x.......x...'}, vel=96).swing(SW), intro, bars=2)
    b.drums.loop(drums({'hat': 'x.x.x.x.x.x.x.x.', 'kick': 'x.........x.....', 'rim': '....x.......x...'},
                       vel=90).swing(SW), intro.bar(2), bars=2)
    b.drums.play(snare_roll(1, vel=(50, 110)), intro.bar(3, 3), replace=True)
    b.drums.loop(groove * 3 + groove2, a, bsec)
    b.drums.play(crash(), a).play(crash(), bsec)
    b.drums.play(drums({'kick': 'x.....x.x.......', 'snare': '......x.X.......', 'crash': 'x.........x.....'},
                       vel=118), out.bar(3))

    # --- guitar: chicken scratch everywhere
    b.gtr.loop(scratch(['D4', 'F#4', 'B4'], 'x.xXx.xxx.xXx.xx', bars=1).swing(SW).strum(ms=5, bpm=s.tempo,
                                                                                         direction='alternate'),
               intro, a)
    part_b = scratch(['E4', 'G4', 'B4'], 'x.xXx.xxx.xXx.xx', bars=2) + scratch(['D#4', 'A4', 'D5'],
                                                                                 'x.xXx.xxx.xXx.xx', bars=2)
    b.gtr.loop(part_b.swing(SW).strum(ms=5, bpm=s.tempo, direction='alternate'), bsec)
    b.gtr.loop(scratch(['D4', 'F#4', 'B4'], 'x.xXx.xxx.xXx.xx').swing(SW).strum(ms=5, bpm=s.tempo), out,
               bars=3)

    # --- bass: syncopated 16ths, staccato ghosts
    line = Clip([(0, 0.45, 'E1', 112), (0.75, 0.2, 'E1', 70), (1.5, 0.2, 'E2', 100), (1.75, 0.2, 'D2', 90),
                 (2.5, 0.45, 'E1', 105), (3.0, 0.2, 'G1', 95), (3.25, 0.2, 'G#1', 100), (3.5, 0.4, 'B1', 104)],
                length=4)
    # the bass answers the kick (kick on 1, the & of 2, 3, the e of 4): the one together, then in its gaps
    line_b = Clip([(0, 0.45, 'A1', 110), (0.75, 0.2, 'A1', 70), (1.0, 0.2, 'A2', 100), (2.0, 0.4, 'E2', 100),
                   (2.75, 0.2, 'G2', 96), (3.5, 0.3, 'G1', 96), (4, 0.45, 'B1', 110), (4.75, 0.2, 'B1', 70),
                   (5.0, 0.2, 'B2', 100), (6.0, 0.4, 'F#2', 100), (6.75, 0.2, 'A1', 90), (7.5, 0.4, 'A#1', 100)],
                  length=8)
    short = lambda c: c.articulate('staccato', where=lambda n: n.dur < 0.3)
    b.bass.loop(short(line).swing(SW), a)
    b.bass.loop(short(line_b).swing(SW), bsec)
    b.bass.play(Clip([(0, 3.5, 'E1', 115)], length=4), out.bar(3))

    # --- clav: 16th two-note stabs through the envelope filter
    clav = stabs(['D4', 'G#4'], 'x..x..x.x..x.x..', vel=100, dur=0.15)
    b.keys.loop(clav.swing(SW), a)
    b.keys.loop((stabs(['E4', 'G4'], 'x..x..x.x..x.x..', dur=0.15, bars=2)
                 + stabs(['D#4', 'A4'], 'x..x..x.x..x.x..', dur=0.15, bars=2)).swing(SW), bsec)

    # --- horns: offbeat stabs in the groove, swells + stabs in the bridge, the final hit
    hits = stabs(E9[:3], '......x.......x.', vel=108, dur=0.25) + stabs(E9[:3], '..x...x..x......', vel=108,
                                                                         dur=0.25)
    b.horns.loop(hits.swing(SW), a.bar(4), bars=4)
    swell = Clip([(0, 6, p, 96) for p in A9[:3]] + [(8, 6, p, 100) for p in B7[:3]], length=16).articulate('long')
    b.horns.play(swell, bsec).play(swell, bsec.bar(4))
    b.horns.play(stabs(E9[:3], 'x.....x.x.......', vel=118, dur=0.3), out.bar(3))

    # --- tenor sax: the tune, legato phrases with scoops and vibrato
    head = s.motif('r:0.5 5:0.5 7:0.5 8:0.5 7:1 5:1 | 4:0.5 5:0.5 3:1 1:2 | r:0.5 5:0.5 7:0.5 8:0.5 10:1 8:1 '
                   '| 7:0.75 8:0.25 7:1 5:2').clip(octave=4, vel=100)
    head = art.legato(head, overlap=0.03).glide(80, where=art.leaps(4)).swing(SW)
    b.lead.play(head, a).play(head, a.bar(4))
    art.vibrato(b.lead, head, a, depth=22, rate=5.4)
    art.vibrato(b.lead, head, a.bar(4), depth=22, rate=5.4)
    bridge = s.motif('8:2 7:1 5:1 | 4:3 r:1 | 9:2 8:1 7:1 | 6:3 r:1').clip(octave=4, vel=104)
    bridge = art.legato(bridge, overlap=0.03)
    b.lead.play(bridge, bsec).play(bridge, bsec.bar(4))
    art.vibrato(b.lead, bridge, bsec, depth=26, rate=5.2)
    art.vibrato(b.lead, bridge, bsec.bar(4), depth=26, rate=5.2)
    b.lead.note('E4', out.bar(3), 2, 110)
    return s
