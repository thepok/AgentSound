"""Chorale Prelude on an original hymn tune in F major - a hand-written organ chorale prelude in the Bach /
Pachelbel / Brahms tradition, a 'pro' organ reference for the blind listening test. Every note is written below; the
shared organ player (agentsound.organist) performs it on the Burea church organ.
Build: python -m agentsound build songs/pro-organ-prelude

The tune (4 phrases of 6 quarters + a half note, F4-G5):
  1  F G A F | C Bb A      imperfect authentic cadence (V7 - I, the cantus on the third)
  2  A C D C | Bb A G      half cadence (ii - I6 - V)
  3  C D E F | G E F       deceptive cadence (V - vi, a cadential trill on the leading tone)
  4  D C Bb A | Bb G F     perfect authentic cadence (IV - V - I, a cadential trill on G)

Form (4/4, see NOTES.md):
  verse 1  16 bars q=54  the cantus plain (mordents, a pralltriller, two cadential trills) on the Huvudverk cornet
                         (Gedakt 8, Rorflojt 4, Sesquialtera II) over the Brostverk flutes (Gedakt 8, Koppelflojt 4)
                         and the pedal Subbas 16 + Gedakt 8; 3 bars of Vorspiel, a bar of interlude after each of the
                         first three phrases (the third one turns to D minor and its dominant A, deceptively resolved
                         to Bb under phrase 4), a plagal postlude (IV - I) over the pedal
  verse 2  18 bars q=50  the cantus coloured (16th-note diminutions, Bach's 'coloratura' chorale manner) on the
                         Krumhorn 8 (Brostverk) over the same accompaniment moved to the swell Salicional 8 (the box
                         breathing with the phrases); the Vorspiel and interludes as in verse 1, then a 4-bar coda
                         over a tonic pedal point: ii7/F - V7/F - IV/F - I, the cantus' last farewell G Bb | D C | A

The accompaniment's ONE motif (both inner voices, the whole piece): an 8th rest and three stepwise 8ths running into
a held half note - the alto runs into every downbeat while the tenor holds, the tenor into every third beat while the
alto holds, so the 8ths flow without a break and each voice breathes on its rest.
"""
from agentsound import *
from agentsound import bands, organist
from agentsound.bandlib import orchestra as orch

ANALYSIS = {'profile': 'organ'}
METADATA = {'title': 'Chorale Prelude in F', 'artist': 'AgentSound', 'album': 'Organ References', 'genre': 'Classical',
            'year': 2026}

_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def P(name: str) -> int:
    """'Bb3' / 'C#3' / 'F4' -> MIDI (C4 = 60)."""
    acc = {'b': -1, '#': 1}.get(name[1], 0) if len(name) > 2 else 0
    return 12 * (int(name[-1]) + 1) + _PC[name[0]] + acc


def line(text: str, start: float = 0.0) -> list:
    """'F4 G4:2 r:.5 A4:.5 ...' -> [(start, dur, pitch)]: a token is PITCH[:dur] or r[:dur], the duration (beats)
    carries over to the next token until a new one is given; '|' is a bar line (4 beats: checked)."""
    out, t, dur = [], float(start), 1.0
    bar_start = t
    for tok in text.split():
        if tok == '|':
            if abs(t - bar_start - 4.0) > 1e-6:
                raise ValueError(f"bar of {t - bar_start:g} beats before '|' at beat {t:g} in {text[:40]!r}")
            bar_start = t
            continue
        name, _, d = tok.partition(':')
        if d:
            dur = float(d)
        if name != 'r':
            out.append((t, dur, P(name)))
        t += dur
    return out


def end_of(text: str, start: float = 0.0) -> float:
    n = line(text, start)
    return max(a + b for a, b, _ in n)


# =============================================================================================== the notes
# Bars are numbered 1.. in the comments (b4 = the fourth bar of the verse). The harmony per half bar:
#  b1 F | Dm   b2 Gm | C    b3 Dm | C       b4 F (C/E) | F/A    b5 C7 | F       b6 Bb (Gm) | C
#  b7 F | Bb F  b8 Gm Dm/F | C   b9 Dm | C/E   b10 F Dm | Am   b11 C | Dm      b12 Gm | A (V of D minor)
#  b13 Bb F/A | Gm Dm/F   b14 Bb C | F     b15 F | Bb (plagal)   b16 F

ALTO = [   # the motif runs into every downbeat: an 8th rest, three stepwise 8ths, the held half
    'C4:2 r:.5 E4:.5 D4 C4',        # b1
    'Bb3:2 r:.5 A3:.5 Bb3 C4',      # b2
    'D4:2 r:.5 F4:.5 E4 D4',        # b3
    'C4:2 r:.5 Bb3:.5 C4 D4',       # b4   phrase 1
    'E4:2 r:.5 G4:.5 F4 E4',        # b5
    'D4:2 r:.5 F4:.5 E4 D4',        # b6   interlude
    'C4:2 r:.5 E4:.5 F4 E4',        # b7   phrase 2
    'D4:2 r:.5 A3:.5 Bb3 C4',       # b8
    'D4:2 r:.5 D5:.5 C5 Bb4',       # b9   interlude
    'A4:2 r:.5 G4:.5 A4:1',         # b10  phrase 3
    'C5:2 r:.5 E5:.5 D5 C5',        # b11
    'Bb4:2 r:.5 Bb4:.5 A4 G4',      # b12  interlude (D minor)
    'F4:2 r:.5 G4:.5 F4 E4',        # b13  phrase 4
    'D4:1 C4:1 A3:2',               # b14  the cadence: the motif rests
]
TENOR = [  # the motif runs into every third beat
    'r:.5 G3:.5 F3 E3 D3:2',        # b1
    'r:.5 A3:.5 G3 F3 E3:2',        # b2
    'r:.5 G3:.5 A3 Bb3 C4:2',       # b3
    'r:.5 F3:.5 E3 D3 C3:2',        # b4
    'r:.5 F3:.5 E3 D3 C3:2',        # b5
    'r:.5 C4:.5 Bb3 A3 G3:2',       # b6
    'r:.5 Bb3:.5 A3 G3 F3:2',       # b7
    'r:.5 G2:.5 A2 Bb2 C3:2',       # b8
    'r:.5 G3:.5 A3 Bb3 C4:2',       # b9
    'r:.5 G3:.5 A3 Bb3 C4:2',       # b10
    'r:.5 D4:.5 C4 Bb3 A3:2',       # b11  (the deceptive cadence: G of C goes to A, the bass C - D, no fifths)
    'r:.5 A3:.5 G3 F3 E3:2',        # b12
    'r:.5 D3:.5 F3 E3 D3:2',        # b13
    'r:.5 F3:.5 E3 D3 C3:2',        # b14
]
PEDAL = [  # written pitch (the 16' sounds an octave lower)
    'F2 A2 D2 F2', 'G2 Bb2 C3 E2', 'D2 F2 E2 C2',
    'F2 C3 A2 A2', 'C3 C2 F2 A2', 'Bb2 G2 C3 C2',
    'F2 A2 Bb2 F2', 'G2 F2 C2 E2', 'D2 F2 C3 E2',
    'F2 D2 A2 F2', 'C3 C2 D2 D3', 'G2 Bb2 C#3 A2',
    'Bb2 F2 G2 D2', 'Bb2 C3 F2:2',
]
# verse 1's ending: the plagal postlude, the final chord (the fill notes complete it on the accompaniment manual)
ALTO_V1_END = ['C4:2 r:.5 E4:.5 F4 G4', 'A4:3 r:1']
TENOR_V1_END = ['r:.5 G3:.5 F3 E3 D3:2', 'C3:3 r:1']
PEDAL_V1_END = ['F2:2 Bb2:2', 'F2:3 r:1']
FILL_V1 = ['F3', 'C4', 'F4']
# verse 2's coda over the tonic pedal point: ii7/F - V7/F - IV/F - I
ALTO_V2_END = ['C4:2 r:.5 A3:.5 Bb3 C4', 'D4:2 r:.5 F4:.5 G4 A4', 'Bb4:2 r:.5 Bb4:.5 A4 G4', 'F4:4']
TENOR_V2_END = ['r:.5 G3:.5 F3 E3 D3:2', 'r:.5 A3:.5 G3 F3 E3:2', 'r:.5 E3:.5 F3 G3 A3:2', 'A3:4']
PEDAL_V2_END = 'F2:16'       # tied from b14's F2: the tonic pedal point
FILL_V2 = ['F3', 'C4']

# the cantus firmus, verse 1: plain quarters, the ornaments of the cadences (beat in the verse -> ornament)
CANTUS_1 = ('r:4 | r:4 | r:4 | F4:1 G4 A4 F4 | C5 Bb4 A4:2 | r:4 | A4:1 C5 D5 C5 | Bb4 A4 G4:2 | r:4 | '
            'C5:1 D5 E5 F5 | G5 E5 F5:2 | r:4 | D5:1 C5 Bb4 A4 | Bb4 G4 F4:2')
ORN_1 = {12: 'mordent', 17: 'prall', 36: 'mordent', 41: 'trill', 53: 'trill'}
# verse 2: the tune coloured - every tune note keeps its beat, the diminutions fill between (16ths)
CANTUS_2 = ('r:4 | r:4 | r:4 | '
            'F4:.5 E4:.25 F4 G4:.5 A4:.25 Bb4 A4:.5 C5:.25 Bb4 A4:.5 Bb4 | '
            'C5:.5 E5:.25 D5 C5 Bb4 A4 Bb4 A4:2 | r:4 | '
            'A4:.5 G4:.25 A4 C5:.5 Bb4:.25 C5 D5:.5 F5:.25 E5 C5:.5 A4 | '
            'Bb4:.5 D5:.25 C5 A4:.75 Bb4:.25 G4:2 | r:4 | '
            'C5:.5 D5:1 C5:.25 D5 E5:.5 D5:.25 E5 F5:1 | '
            'G5:.5 A5:.25 G5 E5:1 F5:2 | r:4 | '
            'D5:.5 C5:.25 Bb4 C5:.5 A4 Bb4:.75 C5:.25 A4:.5 C5 | '
            'D5:.5 C5:.25 Bb4 G4:1 F4:2 | '
            'r:4 | G4:2 Bb4 | D5:2 C5 | A4:4')
ORN_2 = {28: 'mordent', 41: 'trill', 53: 'trill', 66: 'prall'}


def ornaments(notes, start, marks) -> dict:
    """{beat in the verse: ornament} -> {note index: ornament} (the note starting there)."""
    idx = {round(st - start, 4): i for i, (st, _, _) in enumerate(sorted(notes))}
    out = {}
    for at, kind in marks.items():
        if round(at, 4) not in idx:
            raise ValueError(f"no cantus note starts at verse beat {at}")
        out[idx[round(at, 4)]] = kind
    return out


def verse_voices(v: int, start: float) -> dict:
    """The written voices of verse v (1 or 2) from beat `start`: {name: notes}."""
    end_a, end_t = (ALTO_V1_END, TENOR_V1_END) if v == 1 else (ALTO_V2_END, TENOR_V2_END)
    a = line(' | '.join(ALTO + end_a), start)
    t = line(' | '.join(TENOR + end_t), start)
    if v == 1:
        b = line(' | '.join(PEDAL + PEDAL_V1_END), start)
        fill_at, fill_dur, fill = start + 60, 3.0, FILL_V1
    else:
        ped = line(' | '.join(PEDAL), start)
        st, du, p = ped[-1]                     # b14's F2 tied into the pedal point
        b = ped[:-1] + [(st, du + 16, p)]
        fill_at, fill_dur, fill = start + 68, 4.0, FILL_V2
    s = line(CANTUS_1 if v == 1 else CANTUS_2, start)
    return {'S': s, 'A': a, 'T': t, 'B': b, 'fill': [(fill_at, fill_dur, P(x)) for x in fill]}


def build() -> Song:
    s = Song('Chorale Prelude in F', tempo=54, key='F major', seed=7, tail=8)
    v1 = s.section('verse1', bars=16)
    v2 = s.section('verse2', bars=18)

    # ---- time: the Vorspiel settles, the cadences broaden a little, each verse's end a real ritardando
    s.rubato((v1.start, v1.bar(3)), depth=0.02, phrase='breath')
    s.ritardando((v1.bar(10, 2), v1.bar(11)), to=0.93)                  # into the deceptive cadence
    s.ritardando((v1.bar(13, 2), v1.bar(14, 2)), to=0.9)                # phrase 4's cadence
    s.ritardando((v1.bar(14, 2), v1.bar(15)), to=0.78, a_tempo=False)   # the plagal postlude
    s.fermata(v1.bar(15), hold=1.5)
    s.set_tempo(v2.start, 50)
    s.rubato((v2.start, v2.bar(3)), depth=0.02, phrase='breath')
    s.ritardando((v2.bar(10, 2), v2.bar(11)), to=0.92)
    s.ritardando((v2.bar(13, 2), v2.bar(14)), to=0.9)
    s.ritardando((v2.bar(16), v2.bar(17)), to=0.75, a_tempo=False)     # the coda's last bars
    s.fermata(v2.bar(17), hold=2.5)

    # ---- the organ: verse 1 cornet over the Brostverk flutes; verse 2 Krumhorn over the swell Salicional
    o = bands.church_organ(s, registers=('flute', 'cornet', 'reed', 'strings'),
                           without=('soft', 'principal', 'full', 'pedal_full'))
    # the seat: the Krumhorn's spaced pair is near anti-phase on this set (correlation -0.1: hollow in mono) -
    # narrowed (+2 dB back); the swell Salicional sits ~3 dB under the solo with the box half open (its calibration is a chord's,
    # two lines read 5 dB lower); the Subbas' 16' fundamentals tamed (sub +10 dB over the organ balance)
    o['reed'].add_fx(fx.width(width=0.45))
    o['reed'].gain_db += 2.0
    o['strings'].gain_db += 2.5          # (+3 more in the preset since)
    o['strings'].add_fx(fx.eq({'peak1.freq': 400, 'peak1.gain': -2.0, 'peak1.q': 0.9}))
    o['pedal'].add_fx(fx.eq({'low.freq': 70, 'low.gain': -3.5}))
    w1 = verse_voices(1, v1.start)
    w2 = verse_voices(2, v2.start)
    V = organist.Voice
    voices = [
        V(w1['S'], 'cornet', 'cantus 1', touch='legato', ornaments=ornaments(w1['S'], v1.start, ORN_1)),
        V(w1['A'], 'flute', 'alto 1', touch='legato'),
        V(w1['T'], 'flute', 'tenor 1', touch='legato'),
        V(w1['fill'], 'flute', 'final chord 1', kind='chords', touch='legato'),
        V(w1['B'], 'pedal', 'pedal 1', touch='ordinary'),
        V(w2['S'], 'reed', 'cantus 2', touch='legato', ornaments=ornaments(w2['S'], v2.start, ORN_2)),
        V(w2['A'], 'strings', 'alto 2', touch='legato'),
        V(w2['T'], 'strings', 'tenor 2', touch='legato'),
        V(w2['fill'], 'strings', 'final chord 2', kind='chords', touch='legato'),
        V(w2['B'], 'pedal', 'pedal 2', touch='ordinary'),
    ]
    phrases = [sec.bar(k) for sec in (v1, v2) for k in (3, 6, 9, 12)] + [v2.start, v2.bar(14)]
    organist.perform(s, o, voices, phrases=sorted(phrases), seed=5)

    # ---- the swell box (verse 2's Salicional): it breathes with the cantus phrases, opens for phrase 3, closes
    # over the pedal point
    orch.swell(o, [(v2.start, 0.55), (v2.bar(3), 0.6), (v2.bar(4, 2), 0.75, 'smooth'), (v2.bar(6), 0.6, 'smooth'),
                   (v2.bar(7, 2), 0.75, 'smooth'), (v2.bar(9), 0.7, 'smooth'), (v2.bar(10, 2), 0.95, 'smooth'),
                   (v2.bar(12), 0.75, 'smooth'), (v2.bar(13, 2), 0.85, 'smooth'), (v2.bar(15), 0.6, 'smooth'),
                   (v2.bar(17), 0.45, 'smooth')], roles=['strings'])
    orch.ring(o, v1.bar(15), length=2.0, back=v2.start)
    orch.ring(o, v2.bar(17), length=3.0)
    return s
