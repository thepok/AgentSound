"""Orchestral sections demo: the symphonic sections one per track (agentsound/patches/sampled_sections.py). Build:
    python -m agentsound build songs/_demo_orch_sections

Sections (66 BPM, D minor, 16 bars, ~1:00):
  chorale  4   a 5-part string chorale on five tracks, each section seated where an orchestra sits it:
               sampled/violins_1 (melody), violins_2, violas, celli, double_basses - p -> mf -> p swells
  winds    4   a woodwind section line: sampled/flutes (melody) + sampled/clarinets (a third / sixth under),
               sampled/oboes (held inner notes), sampled/bassoons staccato bass; the strings pizzicato underneath
  muted    4   the muted brass moment: sampled/horns_muted chords swelling out of pp, a sampled/trumpets_muted
               fanfare figure, over a pp violin tremolo bed and a held bass
  tutti    4   strings (marcato downbeat, then sustain) with the winds doubling, a long diminuendo to the end
Measured (full build): -18.9 LUFS-I (classical -23..-16), 0 clicks, 0 silent notes, no flat dynamics; the muted
section is the deliberate pp dip (-23.5 LUFS) before the tutti (-16.0). The report's remaining masking warnings are the
orchestration itself (flutes over clarinets in thirds, the muted horns under the muted trumpets).
Credits: Sonatina Symphonic Orchestra (CC Sampling Plus 1.0), Virtual Playing Orchestra 3 (royalty-free), VSCO 2 CE
(CC0).
"""
from agentsound import *
from agentsound import articulation as art

ANALYSIS = {'profile': 'classical'}

# Track faders (dB): every patch lands at -18 LUFS alone; the strings carry, the winds colour, the brass sits back
GAIN = {'vln1': -6.0, 'vln2': -9.0, 'vla': -9.0, 'vc': -8.0, 'cb': -7.0, 'fl': -7.0, 'ob': -8.0, 'cl': -9.0,
        'bn': -7.0, 'hn': -5.0, 'tp': -8.0}

# chorale: half-note chords, (bass, cello, viola, violin 2, violin 1); the last chord is held a whole bar
CHORALE = [('D2', 'D3', 'A3', 'F4', 'A4'), ('C2', 'F3', 'A3', 'F4', 'D5'), ('A#1', 'D3', 'A#3', 'F4', 'D5'),
           ('G1', 'D3', 'A#3', 'G4', 'A#4'), ('A1', 'E3', 'A3', 'E4', 'C#5'), ('A1', 'E3', 'G3', 'E4', 'E5'),
           ('D2', 'D3', 'A3', 'F4', 'D5')]
CHORALE_VEL = [62, 70, 82, 90, 84, 76, 64]


def line(notes, start=0.0) -> Clip:
    """(beats, pitch, vel) in sequence; pitch None = rest."""
    out, t = [], start
    for d, p, v in notes:
        if p:
            out.append((t, d, p, v))
        t += d
    return Clip(out, length=16)


def swell(track, pts):
    """The sampler's 'dynamics' lane (the libraries' mod wheel) from (beat, value) points."""
    track.automate('instrument.dynamics', [(b, v) for b, v in pts])


def build() -> Song:
    s = Song('Orchestral Sections', tempo=66, key='D minor', seed=5)
    chorale = s.section('chorale', bars=4)
    winds = s.section('winds', bars=4)
    muted = s.section('muted', bars=4)
    tutti = s.section('tutti', bars=4)
    s.hall()
    s.master.add(fx.eq({'high.freq': 9000, 'high.gain': 2.0}), fx.limiter())

    vln1 = s.track('violins_1', 'sampled/violins_1', gain_db=GAIN['vln1'])
    vln2 = s.track('violins_2', 'sampled/violins_2', gain_db=GAIN['vln2'])
    vla = s.track('violas', 'sampled/violas', gain_db=GAIN['vla'])
    vc = s.track('celli', 'sampled/celli', gain_db=GAIN['vc'])
    cb = s.track('basses', 'sampled/double_basses', gain_db=GAIN['cb'])
    fl = s.track('flutes', 'sampled/flutes', gain_db=GAIN['fl'])
    ob = s.track('oboes', 'sampled/oboes', gain_db=GAIN['ob'])
    cl = s.track('clarinets', 'sampled/clarinets', gain_db=GAIN['cl'])
    bn = s.track('bassoons', 'sampled/bassoons', gain_db=GAIN['bn'])
    hn = s.track('horns_muted', 'sampled/horns_muted', gain_db=GAIN['hn'])
    tp = s.track('trumpets_muted', 'sampled/trumpets_muted', gain_db=GAIN['tp'])
    strings = (cb, vc, vla, vln2, vln1)
    # mix: the violins carry the 1-5 kHz band - a little less mid / presence there; the flutes leave the low mids
    # to the clarinets under them; a touch of air on the master
    vln1.add_fx(fx.eq({'peak2.freq': 1000, 'peak2.gain': -2.0, 'peak2.q': 0.9, 'peak3.freq': 3300, 'peak3.gain': -3.0,
                       'peak3.q': 1.0}))
    vln2.add_fx(fx.eq({'peak2.freq': 1000, 'peak2.gain': -1.5, 'peak2.q': 0.9}))
    fl.add_fx(fx.eq({'peak1.freq': 450, 'peak1.gain': -3.0, 'peak1.q': 1.0}))

    # ------------------------------------------------------------------ chorale: 5 string parts
    c0 = chorale.start
    for i, chord in enumerate(CHORALE):
        dur = 4.0 if i == len(CHORALE) - 1 else 2.0
        for k, (tr, p) in enumerate(zip(strings, chord)):
            vel = CHORALE_VEL[i] + (6 if k == 4 else 0) - (4 if k in (1, 2) else 0)
            tr.note(p, c0 + 2 * i, dur + 0.05, vel=vel)      # a hair of overlap: no gap at the bow change
    for k, tr in enumerate(strings):
        swell(tr, [(c0, 0.3), (c0 + 6, 0.62), (c0 + 9, 0.7), (c0 + 13, 0.5), (c0 + 16, 0.28)])

    # ------------------------------------------------------------------ winds: the section line, pizzicato strings
    w0 = winds.start
    flute = line([(1, 'F5', 78), (0.5, 'E5', 70), (0.5, 'D5', 72), (2, 'A5', 92),
                  (1.5, 'G5', 86), (0.5, 'F5', 74), (1, 'E5', 78), (1, 'D5', 72),
                  (1, 'E5', 80), (1, 'G5', 90), (2, 'E5', 82),
                  (3, 'D5', 70), (1, None, 0)])
    clar = line([(1, 'D5', 72), (0.5, 'C5', 64), (0.5, 'A#4', 66), (2, 'F5', 84),
                 (1.5, 'A#4', 78), (0.5, 'A4', 68), (1, 'C5', 72), (1, 'A#4', 66),
                 (1, 'C5', 74), (1, 'E5', 84), (2, 'C#5', 76),
                 (3, 'A4', 64), (1, None, 0)])
    art.perform(fl, flute, w0, tie=False, shapes='auto', vib=False, seed=1)
    art.perform(cl, clar, w0, tie=False, shapes='auto', vib=False, seed=2)
    ob.play(line([(4, 'A4', 66), (4, 'A#4', 72), (2, 'G4', 70), (2, 'A4', 74), (3, 'F4', 62)]), w0)
    swell(ob, [(w0, 0.35), (w0 + 6, 0.55), (w0 + 12, 0.5), (w0 + 15, 0.3)])
    bass_line = [('D3', 'A2', 'D3', 'A2'), ('G2', 'D3', 'G2', 'D3'), ('C3', 'G2', 'A2', 'E2'), ('D2',)]
    accents = [104, 62, 84, 58]                               # strong 1, lighter 3, soft passing quarters
    bassoon = Clip([(4 * b + q, 0.4, p, accents[q] - 4 * (b == 2)) for b, bar in enumerate(bass_line)
                    for q, p in enumerate(bar)], length=16).articulate('staccato')
    bn.play(bassoon, w0)
    roots = ['D2', 'G1', 'C2', 'D2']
    cb.play(Clip([(4 * b, 1, p, 92) for b, p in enumerate(roots)] + [(4 * b + 2, 1, p, 76) for b, p in
                                                                      enumerate(roots[:3])],
                 length=16).articulate('pizzicato'), w0)
    vc.play(Clip([(4 * b + 2, 1, p, 80) for b, p in enumerate(['A2', 'D3', 'G2'])] + [(12, 1, 'D3', 84)],
                 length=16).articulate('pizzicato'), w0)
    vla_pizz = [(4 * b + q, 0.5, p, v) for b, ch in enumerate([('F3', 'A3'), ('G3', 'A#3'), ('G3', 'C4'), ('F3', 'A3')])
                for q, v in ((1, 72), (3, 66)) if not (b == 3 and q == 3) for p in ch]
    vla.play(Clip(vla_pizz, length=16).articulate('pizzicato'), w0)
    for tr in (cb, vc, vla):
        swell(tr, [(w0, 0.6)])

    # ------------------------------------------------------------------ muted: horns + trumpets, tremolo bed
    m0 = muted.start
    for b, ch in enumerate([('D3', 'F3', 'A#3'), ('D3', 'G3', 'A#3'), ('D#3', 'G3', 'A#3'), ('C#3', 'E3', 'A3')]):
        for i, p in enumerate(ch):
            hn.note(p, m0 + 4 * b, 4.1, vel=70 + 6 * i + (8 if b == 2 else 0))
    swell(hn, [(m0, 0.2), (m0 + 2.5, 0.65), (m0 + 4, 0.4), (m0 + 6.5, 0.7), (m0 + 8, 0.45), (m0 + 10.5, 0.9),
               (m0 + 12, 0.55), (m0 + 16, 0.2)])
    fanfare = line([(5, None, 0), (0.5, 'D5', 84), (0.5, 'D5', 72), (1, 'G5', 96), (1, 'F5', 82),
                    (0.5, 'D#5', 84), (0.5, 'D#5', 72), (1, 'G5', 98), (2, 'F5', 86), (4, 'E5', 76)])
    tp.play(fanfare, m0)
    swell(tp, [(m0 + 5, 0.45), (m0 + 10, 0.7), (m0 + 12, 0.5), (m0 + 16, 0.15)])
    for tr, notes in ((vln1, ['D5', 'D5', 'D#5', 'E5']), (vln2, ['F4', 'G4', 'G4', 'A4'])):
        tr.play(Clip([(4 * b, 4.02, p, 60 + 4 * b) for b, p in enumerate(notes)], length=16).articulate('tremolo'),
                m0)
        swell(tr, [(m0, 0.15), (m0 + 8, 0.3), (m0 + 12, 0.4), (m0 + 16, 0.2)])
    cb.play(Clip([(4 * b, 4.02, p, 64 + 3 * b) for b, p in enumerate(['A#1', 'G1', 'D#2', 'A1'])], length=16), m0)
    swell(cb, [(m0, 0.3), (m0 + 16, 0.4)])

    # ------------------------------------------------------------------ tutti: strings + winds, diminuendo
    t0 = tutti.start
    parts = {
        vln1: [(2, 'A#5', 104), (2, 'A5', 94), (1, 'G5', 92), (1, 'F5', 86), (2, 'E5', 88), (8, 'D5', 78)],
        vln2: [(4, 'D5', 96), (4, 'C#5', 90), (8, 'A4', 74)],
        vla: [(4, 'A#3', 94), (4, 'G3', 88), (8, 'F3', 72)],
        vc: [(4, 'D3', 96), (4, 'E3', 90), (8, 'D3', 74)],
        cb: [(4, 'G1', 100), (4, 'A1', 94), (8, 'D2', 78)],
    }
    for tr, notes in parts.items():
        c = line(notes)
        c = c.articulate('marcato', span=(0, 0.5))           # the downbeat accented, then held
        tr.play(c, t0)
        swell(tr, [(t0, 0.72), (t0 + 4, 0.66), (t0 + 8, 0.52), (t0 + 15.5, 0.12)])
    fl.play(line([(2, 'A#5', 92), (2, 'A5', 86), (1, 'G5', 84), (1, 'F5', 80), (2, 'E5', 82), (6, 'D5', 70)]), t0)
    cl.play(line([(4, 'D5', 86), (4, 'C#5', 82), (6, 'A4', 68)]), t0)
    ob.play(line([(4, 'A#4', 84), (4, 'A4', 80), (6, 'F4', 66)]), t0)
    bn.play(line([(4, 'G2', 88), (4, 'A2', 84), (6, 'D2', 70)]), t0)
    for tr in (fl, cl, ob, bn):
        swell(tr, [(t0, 0.6), (t0 + 8, 0.48), (t0 + 14, 0.15)])
    return s
