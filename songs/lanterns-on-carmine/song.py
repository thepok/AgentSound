"""Lanterns on Carmine Street - an original medium-swing tune for tenor quartet (Eb major, 140 BPM, ~4:05).
Build: python -m agentsound build songs/lanterns-on-carmine

A small group in a Village club after midnight: Salamander grand, Meatbass upright, Swirly brushes, the MTG tenor
(bands.make('jazz_quartet')). The tune is a 32-bar AABA:

  A1   Ebmaj7 | C7b9      | Fm9 | Bb13          | Gm7 C7b9 | Fm7 Bb7 | Ebmaj7 C7b9 | Fm7 Bb7
  A2   Ebmaj7 | Gb7#11    | Fm9 | Bb7sus4 Bb7b9 | Gm7 C7b9 | Fm7 Bb7 | Eb6         | Bbm7 Eb7    (tritone sub, sus)
  B    Abmaj7 | Db9       | Gm7 | C7b9          | Cm9      | F13     | Fm9         | E7#11       (backdoor, V/V, tritone sub)
  A3   = A2 with the A1 ending (turnaround into the next chorus / the tag)

The head's motif is a rising arpeggio that lands, syncopated, on the maj7 (Bb Eb G - D) and falls back through the
b9 of the dominant; bar 3 sequences it a half step higher onto the 7th of Fm; the bridge sequences a two-bar
phrase (Ab: G..C / Db9: #11) down a step (Gm / C7b9: #11) and climbs to Eb5 over Cm9 before the tritone sub E7#11
leads home.

  intro       4   piano alone in time: rolled drop-2 block chords preview the motif over a Bb pedal, brushes stir
  head       32   tenor states the head (A2/A3 paraphrased), bass in two for the A's then walking; piano fills the
                  gaps at the end of A1 and A2, comping answers the horn
  sax_solo   32   tenor chorus: quotes the motif, sequences it, bebop lines with enclosures, builds through the
                  bridge (brushes move to the ride) to the high E5 over Gb7#11, winds down
  piano_solo 32   drops back: single-note lines (motif development), bridge in locked-hands block chords, last A
                  in octaves, left hand in shells
  bass_solo  16   Meatbass solo over the A's (slides, ghosts), piano whispers, brushes just stir + hat foot
  head_out   16   tenor takes it from the bridge, calmer
  tag         6   iii-VI-ii-V tag, then with tritone subs, ritardando
  end         2   rolled Ebmaj9#11, tenor holds the 3rd with a swell and vibrato, fermata, the room rings
"""
from agentsound import *
from agentsound import bands, jazz
from agentsound.bandlib import jazz as jazzband
import random

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Lanterns on Carmine Street', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#1d3f8f', '#e3a72f'], 'title': 'lanterns on carmine street',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 11}

TEMPO = 140

# ------------------------------------------------------------------------------------------------ changes
A1 = 'Ebmaj7 C7b9 Fm9 Bb13 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Ebmaj7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5'
A2 = ('Ebmaj7 Gb7#11 Fm9 Bb7sus4:0.5 Bb7b9:0.5 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Eb6 '
      'Bbm7:0.5 Eb7:0.5')
BR = 'Abmaj7 Db9 Gm7 C7b9 | Cm9 F13 Fm9 E7#11'
A3 = ('Ebmaj7 Gb7#11 Fm9 Bb7sus4:0.5 Bb7b9:0.5 | Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Ebmaj7:0.5 C7b9:0.5 '
      'Fm7:0.5 Bb7:0.5')
INTRO = 'Fm9 Bb13 Fm9 Bb7b9'
TAG = 'Gm7:0.5 C7b9:0.5 Fm7:0.5 Bb7:0.5 Gm7:0.5 Gb7#11:0.5 Fm7:0.5 E7#11:0.5 Gm7:0.5 C7alt:0.5 Fm9:0.5 Bb7sus4:0.5'
END = 'Ebmaj7#11:2'


# ------------------------------------------------------------------------------------------------ notation
def ph(spec: str, vel: float = 90, bars: int | None = None) -> Clip:
    """A written line: tokens PITCH[/len][!|?] separated by spaces, 'r' = rest; len in 8ths (default 1 = an 8th,
    '/3' = dotted quarter, '/t' = an 8th-note triplet, '/2t' = a quarter triplet); '!' accent, '?' ghost;
    'g:PITCH' = a grace (crushed) note just before the next note; '|' checks the bar line (a note may tie over)."""
    t, mark, grace, notes = 0.0, 0.0, None, []
    for tok in spec.replace('|', ' | ').split():
        if tok == '|':
            nb = mark + 4.0
            if abs(t - nb) > 1e-6 and not (notes and notes[-1][0] < nb - 1e-6 and t > nb):
                raise ValueError(f"bar ending at beat {nb} holds {t - mark:.3f} beats: ...{tok} in {spec[:60]!r}")
            mark = nb
            continue
        if tok.startswith('g:'):
            grace = tok[2:]
            continue
        acc = 1.12 ** tok.count('!') * 0.7 ** tok.count('?')
        tok = tok.replace('!', '').replace('?', '')
        p, _, d = tok.partition('/')
        if not d:
            dur = 0.5
        elif d.endswith('t'):
            dur = (float(d[:-1]) if d[:-1] else 1.0) / 3.0
        else:
            dur = float(d) * 0.5
        if p != 'r':
            if grace:
                g = 0.11
                if notes and notes[-1][0] + notes[-1][1] > t - g:
                    notes[-1][1] = max(0.08, t - g - notes[-1][0])
                notes.append([t - g, g, grace, vel * 0.78])
            notes.append([t, dur, p, vel * acc])
        grace = None
        t += dur
    length = bars * 4 if bars else max(4, -(-t // 4) * 4)
    return Clip([(a, d, p, max(1, min(127, int(round(v))))) for a, d, p, v in notes], length=length)


def crush(clip: Clip, prob: float, seed: int, min_dur: float = 0.9) -> Clip:
    """Piano acciaccaturas: a crushed half-step-below note right before some long notes (seeded)."""
    rng = random.Random(seed)
    out = list(clip)
    for n in clip:
        if n.dur >= min_dur and n.start >= 0.2 and rng.random() < prob:
            out.append(Note(n.start - 0.07, 0.09, n.pitch - 1, max(1, int(n.vel * 0.7))))
    return Clip(out, length=clip.length)


def bombs(bars: int, kit: dict, seed: int, density: float = 0.3, vel: int = 58) -> Clip:
    """Drummer comping under a solo: soft kick 'bombs' and snare digs on upbeats, a kick into each 4-bar phrase."""
    rng = random.Random(seed)
    out = []
    for b in range(bars):
        t0 = 4.0 * b
        if b % 4 == 3:                                  # set up the next phrase: & of 4 kick + dig
            out.append((t0 + 3.5, 0.3, kit['kick'], vel + rng.randint(0, 10)))
            out.append((t0 + 3.5, 0.3, kit['dig'], vel - 12 + rng.randint(0, 8)))
        elif rng.random() < density:
            pos = rng.choice((1.5, 2.5, 3.5, 2.0))
            out.append((t0 + pos, 0.3, kit['dig'] if rng.random() < 0.6 else kit['kick'],
                        vel - 10 + rng.randint(0, 12)))
    return Clip(out, length=4.0 * bars)


# ------------------------------------------------------------------------------------------------ the head (concert)
HEAD_A1 = ph("""
 r Bb3 Eb4 G4/2 g:C#5 D5/3 | Db5 C5 Bb4 G4 E4/2 r/2 | r C4 F4 Ab4/2 Eb5/3 | D5 C5 Ab4 F4 G4/3 r |
 r/2 F4 G4 Bb4 Db5 C5 B4 | C5/2 Bb4 Ab4 F4 Ab4/3 | G4/6 r/2 | r/8""", 76)
HEAD_A2 = ph("""
 r Bb3 Eb4 G4/2 D5/3 | Db5 C5 Bb4 G4 E4/2 r/2 | r C4 F4 Ab4/2 Eb5/3 | Eb5 C5 Ab4 F4 G4/3 r |
 r D5 Bb4 G4 E4 G4 Bb4 Db5 | C5 Eb5 C5 Ab4 F4 Ab4 A4 g:C#5 D5 | Eb5/6 r/2 | r/8""", 82)
HEAD_B = ph("""
 r Eb4 F4 G4 C5/4 | B4 Ab4 F4 G4/5 | r D4 F4 G4 Bb4/4 | Bb4 G4 E4 F#4/5 |
 r G4 Bb4 D5 Eb5/4 | D5 C5 A4 F4 Eb4/2 G4 Ab4 | Ab4/3 G4 F4 C5/3 | B4 A#4 G#4 E4 D4/4""", 92)
HEAD_A3 = ph("""
 r Bb3 Eb4 G4/2 g:C#5 D5/3 | Db5 C5 Bb4 G4 E4/2 r/2 | r C4 F4 Ab4/2 Eb5/3 | Eb5 C5 Ab4 F4 G4/3 r |
 r/2 F4 G4 Bb4 Db5 C5 B4 | C5/2 Bb4 Ab4 F4 Ab4/3 | G4/6 r/2 | r/8""", 84)

# ------------------------------------------------------------------------------------------------ the tenor solo
SAX_SOLO = [
    ph("""r/2 Bb3 Eb4 G4 D5/3 | r Db5 C5 Bb4 Ab4 G4 E4/2 | r/2 C4 F4 Ab4 Eb5/3 | r D5 C5 Bb4 Ab4 G4 F4/2 |
          r/2 F4 G4 Bb4 G4 E4 Db4 | C4 Eb4 F4 Ab4 D5 C5 Ab4 F#4 | G4/3 r Bb4 A4 Bb4 Db5 | C5/2 r/6""", 82),
    ph("""r/2 D5/t Eb5/t D5/t Bb4 G4 F4 Eb4 | E4 Gb4 Bb4 Db5 C5/2 Bb4 Ab4 | G4/2 r C4 Eb4 F4 Ab4 C5 |
          Eb5 C5 Bb4 Ab4 B4 Ab4 F4 D4 | r F4 A4 C5 Bb4 Db5 C5 Bb4 | Ab4 G4 F4 Eb4 D4 F4 Ab4 C5 |
          Bb4/2 G4 Bb4 C5/3 r | r Db5 C5 Bb4 G4 Bb4 Db5 C5""", 92),
    ph("""r/2 Eb4 F4 Ab4 C5 Eb5! C5 | B4/2 Ab4 F4 Eb4/2 r F4 | Bb4/t A4/t G4/t F4 D4 F4 G4 Bb4 D5 |
          E4 G4 Bb4 Db5 C5/2 Bb4 G4 | r G4 Bb4 D5 Eb5!/2 D5 C5 | D5/2 A4 C5 Eb5!/2 D5 C5 |
          Ab4/2 G4 F4 Eb4 C4 Eb4 F4 | G#4 B4 D5 B4 G#4 A#4 B4 C#5""", 100),
    ph("""D5/3! Eb5 D5 Bb4 G4 Bb4 | r Db5 E5!/3 Db5 Bb4 Ab4 | C5 Ab4 Eb5 D5 C5 Ab4 F4 G4 |
          Ab4/2 Eb4 F4 B4 Ab4 F4 D4 | D4 F4 A4 C5 Bb4 G4 E4 Db4 | C4/2 r F4 D5/t C5/t Bb4/t Ab4 F#4 |
          G4/8 | r/8""", 108),
]

# ------------------------------------------------------------------------------------------------ piano parts
INTRO_RH = ph("r/2 C5 F5 Ab5 G5/3 | F5 D5 C5 Ab4 G4/4 | r/2 C5 F5 Ab5 Eb6/3 | D6 B5 Ab5 F5 D5/2 r/2", 56)
FILL_A1 = ph("r/8 | r/8 | r/8 | r/8 | r/8 | r/8 | r/8 | r/2 Ab5/t G5/t F5/t D5 F5 Ab5 G5", 72)
FILL_A2 = ph("r/8 | r/8 | r/8 | r/8 | r/8 | r/8 | r/8 | r/2 Db5/t F5/t Ab5/t G5 Db5 Bb4 B4", 74)
PIANO_BRIDGE = ph("""r Eb5 F5 G5/2 Eb5 C5/2 | r Eb5 F5 G5/2 F5 B4/2 | r D5 F5 A5/2 G5 F5/2 |
                     r Db5 E5 G5/2 E5 Db5 Bb4 | r G5 Bb5 D6/2 C6 Bb5 G5 | A5/2 D6 C6 A5 F5 Eb5 D5 |
                     C5/2 Eb5 F5 Ab5/2 G5 F5 | E5 G#5 B5 A#5 G#5 E5 D5/2""", 84)

# ------------------------------------------------------------------------------------------------ bass solo
BASS_SOLO = ph("""
 r/2 Bb2 Eb3? G3/2 F3 D3 | C3/3 Db3 E3 G3 Bb3/2 | Ab3/2 G3 F3 C3/2 r/2 | r D3 F3? G3 Ab3/2 F3 D3? |
 Bb2/2 D3 F3 E3/2 G3 Bb3 | Ab3/2 F3? C3 D3/2 Ab2? A2 | Eb3/t F3/t G3/t Bb3/2 r G3 E3 C3 | F2/2 Ab2 C3 D3/2 r/2 |
 Bb2/2 r G3 F3? Eb3 D3 Bb2? | Bb2/2 Db3 E3 Gb3/2 r/2 | r F3 Ab3 C4/3 Bb3 G3 | Ab3/2 F3 Eb3? D3 F3? Ab3 B3 |
 Bb3/2 A3 G3 E3 Db3 C3 r | r C3 Eb3 F3 D3/2 r/2 | Eb3/2 r Bb2 C3 Eb3 G3/2 | F3 Db3 Bb2 Ab2 G2/2 Bb2 A2""", 100)
BASS_SLIDES = [(0, 2.0, -2.0), (2, 0.0, -1.0), (10, 1.5, -2.0), (14, 3.0, -1.0)]   # (bar, beat, from semitones)

# ------------------------------------------------------------------------------------------------ tag / ending
TAG_SAX = ph("""r/2 F4 G4 Bb4 Db5 C5 B4 | C5/2 Bb4 Ab4 F4 Ab4/3 | r/2 F4 G4 Bb4 Db5 C5 Bb4 | Ab4/2 G4 F4 E4/2 D4 E4 |
                g:A4 Bb4/2 A4 Bb4 Db5/2 C5 Bb4 | Ab4/3 G4 F4/2 Eb4 F4""", 74)
END_SAX = ph("G4/16", 74)


def build() -> Song:
    s = Song('Lanterns on Carmine Street', tempo=TEMPO, key='Eb major', seed=11, tail=6)
    secs = [('intro', 4), ('head', 32), ('sax_solo', 32), ('piano_solo', 32), ('bass_solo', 16), ('head_out', 16),
            ('tag', 6), ('end', 2)]
    intro, head, sax_solo, piano_solo, bass_solo, head_out, tag, end = (s.section(n, bars=b) for n, b in secs)
    b = bands.make('jazz_quartet', s, master_gain=4.0)
    kit, horn = b.info['kit'], b.info['horn']
    P = {k: s.prog(v) for k, v in (('A1', A1), ('A2', A2), ('B', BR), ('A3', A3), ('intro', INTRO), ('tag', TAG),
                                   ('end', END))}
    chorus = [('A1', 0), ('A2', 8), ('B', 16), ('A3', 24)]
    ms = lambda lo, hi, r: r.uniform(lo, hi)
    rng = random.Random(7)

    def comp(sec, part, bar, style, dens, inten, seed, answer=None, voicing='rootless', reg=('A2', 'G4'),
             roll=(8, 22), vel=None):
        c = jazz.comp(P[part], style=style, voicing=voicing, density=dens, intensity=inten, seed=seed,
                      register=reg, answer=answer, vel=vel)
        c = c.strum(ms=ms(*roll, rng), direction='down', bpm=TEMPO)          # a pianist's hands never land flat
        b.comp.play(c, sec.bar(bar))

    def walk(sec, part, bar, seed, vel, feel='four', skip=0.12):
        b.bass.play(jazz.walking_bass(P[part], key=s.key, feel=feel, seed=seed, vel=vel, skip=skip,
                                      skip_grid='triplet' if seed % 2 else 'swing'), sec.bar(bar))

    def bass_fill(at, vel=92):
        """A triplet fill down the Bb7 into the next chorus (replaces beats 3-4 of the bar before it)."""
        b.bass.clear(at + 2.0, at + 4.0)
        for i, p in enumerate(('F3', 'D3', 'Bb2', 'Ab2', 'F2', 'E2')):
            b.bass.note(p, at + 2.0 + i / 3.0, dur=0.3, vel=vel - (8 if i in (1, 4) else 0))

    # ============================================================== intro: piano alone in time, Bb pedal
    b.piano.play(jazz.block_chords(INTRO_RH, P['intro'], style='drop2', vel=0.8).strum(ms=16, bpm=TEMPO), intro)
    b.comp.play(Clip([(0, 3.6, 'Ab2', 58), (0, 3.6, 'Eb3', 54), (0, 3.6, 'G3', 52),
                      (4, 3.6, 'Ab2', 56), (4, 3.6, 'D3', 52), (4, 3.6, 'G3', 50),
                      (8, 3.6, 'Ab2', 60), (8, 3.6, 'Eb3', 55), (8, 3.6, 'G3', 53),
                      (12, 3.2, 'Ab2', 60), (12, 3.2, 'D3', 56), (12, 3.2, 'B3', 55)], length=16)
                .strum(ms=55, bpm=TEMPO), intro)
    jazzband.pedal([b.piano, b.comp], P['intro'], intro)
    b.bass.play(jazz.walking_bass(P['intro'], key=s.key, feel='two', pedal=[(0, 16, 'Bb1')], vel=62, seed=1), intro)
    b.drums.play(jazzband.brushes(b, 4, style='two', fills=False, kick=None, vel=0.45, seed=1), intro)
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(18, 52)), intro.bar(3))

    # ============================================================== head: the tenor
    heads = {'A1': HEAD_A1,
             'A2': jazz.paraphrase(HEAD_A2, seed=2, anticipate=0.35, embellish=0.25, key=s.key),
             'B': HEAD_B,
             'A3': jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.3, delay=0.2, embellish=0.2, key=s.key)}
    head_line = heads['A1'] + heads['A2'] + heads['B'] + heads['A3']
    jazz.horn_line(head_line, TEMPO, seed=11, scoop=0.4, fall=0.35, **horn).place(b.sax, head)
    # piano fills in the horn's gaps, comping answers
    b.piano.play(crush(FILL_A1, 0.0, 1), head)
    b.piano.play(FILL_A2, head.bar(8))
    for (part, bar), (style, dens, inten, seed) in zip(chorus, (('charleston', 0.35, 0.3, 21),
                                                                 ('swing', 0.45, 0.38, 22),
                                                                 ('swing', 0.55, 0.45, 23),
                                                                 ('charleston', 0.5, 0.42, 24))):
        comp(head, part, bar, style, dens, inten, seed, answer=heads[part])
    walk(head, 'A1', 0, 31, 72, feel='two', skip=0.2)
    walk(head, 'A2', 8, 32, 78, feel='two', skip=0.25)
    walk(head, 'B', 16, 33, 90)
    walk(head, 'A3', 24, 34, 90)
    bass_fill(head.bar(31))
    b.drums.play(jazzband.brushes(b, 16, style='two', vel=0.58, seed=41), head)
    b.drums.play(jazzband.brushes(b, 16, style='medium', vel=0.85, seed=42), head.bar(16))
    b.drums.play(jazz.brush_fill('triplets', 1, kit=kit, vel=(30, 70)), head.bar(31))

    # ============================================================== tenor solo
    for i, (part, bar) in enumerate(chorus):
        jazz.horn_line(jazz.phrase_dynamics(SAX_SOLO[i], offbeat=1.07, ghost=0.82), TEMPO, seed=50 + i,
                       scoop=0.35 + 0.1 * i, fall=0.45, **horn).place(b.sax, sax_solo.bar(bar))
        comp(sax_solo, part, bar, ('garland', 'swing', 'swing', 'charleston')[i], 0.5 + 0.08 * i, 0.45 + 0.1 * i,
             60 + i, answer=SAX_SOLO[i], voicing='rootless' if i % 2 == 0 else 'shell')
        walk(sax_solo, part, bar, 70 + i, 88 + 3 * i)
    bass_fill(sax_solo.bar(31), 96)
    b.drums.play(jazzband.brushes(b, 16, style='medium', vel=0.95, seed=81), sax_solo)
    b.drums.play(jazzband.brushes(b, 16, style='medium', ride=0.9, vel=1.12, seed=82), sax_solo.bar(16))
    b.drums.play(bombs(32, kit, seed=83, density=0.35, vel=60), sax_solo)
    b.drums.play(jazz.brush_fill('swell', 1, kit=kit, vel=(30, 72)), sax_solo.bar(15))

    # ============================================================== piano solo
    motif = ph("r Bb4 Eb5 G5/2 D6/3", 88)
    line_aa = jazz.solo_line(P['A1'] + P['A2'], key=s.key, register=('C4', 'C6'), density=0.5, intensity=0.4,
                             seed=5, motif=motif, motif_prob=0.4, vel=76)
    line_a3 = jazz.solo_line(P['A3'], key=s.key, register=('F4', 'Eb6'), density=0.75, intensity=0.8, seed=9,
                             motif=motif, motif_prob=0.5, vel=86)
    b.piano.play(crush(line_aa, 0.45, 3), piano_solo)
    b.piano.play(jazz.block_chords(PIANO_BRIDGE, P['B'], style='locked', vel=0.7), piano_solo.bar(16))
    b.piano.play(crush(line_a3.slice(0, 16).octave_double(-12, vel=0.75) + line_a3.slice(16, 32), 0.3, 4),
                 piano_solo.bar(24))
    pl = {'A1': line_aa.slice(0, 32), 'A2': line_aa.slice(32, 64), 'B': PIANO_BRIDGE, 'A3': line_a3}
    for i, (part, bar) in enumerate(chorus):
        comp(piano_solo, part, bar, ('sparse', 'garland', 'garland', 'swing')[i], (0.4, 0.55, 0.35, 0.65)[i],
             (0.35, 0.45, 0.5, 0.6)[i], 90 + i, answer=pl[part], voicing='shell' if part != 'B' else 'rootless',
             reg=('G2', 'F4'))
        walk(piano_solo, part, bar, 100 + i, (84, 88, 92, 95)[i])
    bass_fill(piano_solo.bar(31), 92)
    b.drums.play(jazzband.brushes(b, 16, style='medium', vel=0.85, seed=111), piano_solo)
    b.drums.play(jazzband.brushes(b, 8, style='medium', vel=1.0, seed=112), piano_solo.bar(16))
    b.drums.play(jazzband.brushes(b, 8, style='medium', vel=1.0, seed=113), piano_solo.bar(24))
    b.drums.play(bombs(16, kit, seed=114, density=0.3, vel=58), piano_solo.bar(16))

    # ============================================================== bass solo
    b.bass.play(BASS_SOLO, bass_solo)
    bend = []
    for bar, beat, frm in BASS_SLIDES:
        t = bass_solo.bar(bar) + beat
        bend += [(t - 0.03, 0.0, 'step'), (t - 0.01, frm, 'step'), (t + 0.22, 0.0, 'smooth')]
    b.bass.automate('instrument.pitchbend', bend)
    # the bassist steps up to the mic: +2.5 dB for the solo, settles back ('gainDb' is dB on the track's gain_db)

    b.bass.automate('gainDb', [(0, 0.0), (bass_solo.start - 1, 0.0), (bass_solo.start, 2.5, 'smooth'),
                               (head_out.start - 1, 2.5), (head_out.start, 0.0, 'smooth')])
    comp(bass_solo, 'A1', 0, 'sparse', 0.3, 0.22, 131, answer=BASS_SOLO.slice(0, 32), voicing='shell',
         reg=('C3', 'A4'), roll=(20, 40))
    comp(bass_solo, 'A2', 8, 'sparse', 0.3, 0.25, 132, answer=BASS_SOLO.slice(32, 64), voicing='shell',
         reg=('C3', 'A4'), roll=(20, 40))
    b.drums.play(jazzband.brushes(b, 16, style='two', taps=False, kick=None, fills=False, vel=0.62, seed=141),
                 bass_solo)
    b.drums.play(jazz.brush_fill('swell', 1, kit=kit, vel=(24, 60)), bass_solo.bar(15))

    # ============================================================== head out (from the bridge), calmer
    out_line = (jazz.paraphrase(HEAD_B, seed=5, anticipate=0.3, embellish=0.3, key=s.key).velocity(0.88)
                + jazz.paraphrase(HEAD_A3, seed=6, anticipate=0.25, delay=0.2, key=s.key).velocity(0.84))
    jazz.horn_line(out_line, TEMPO, seed=12, scoop=0.4, fall=0.25, **horn).place(b.sax, head_out)
    comp(head_out, 'B', 0, 'swing', 0.5, 0.4, 151, answer=out_line.slice(0, 32))
    comp(head_out, 'A3', 8, 'charleston', 0.45, 0.35, 152, answer=out_line.slice(32, 64))
    walk(head_out, 'B', 0, 161, 82)
    walk(head_out, 'A3', 8, 162, 76)
    b.piano.play(ph("r/8 | r/8 | r/8 | r/8 | r/8 | r/8 | r/6 G5/t F5/t Eb5/t | D5 C5 Bb4 Ab4 G4/2 r/2", 66),
                 head_out.bar(8))
    b.drums.play(jazzband.brushes(b, 16, style='medium', vel=0.68, seed=171), head_out)

    # ============================================================== tag + ending
    jazz.horn_line(TAG_SAX, TEMPO, seed=13, scoop=0.4, fall=0.0, **horn).place(b.sax, tag)
    jazz.horn_line(END_SAX, TEMPO * 0.72, seed=14, scoop=1.0, fall=0.0, vib_depth=0.2, **horn).place(b.sax, end)
    comp(tag, 'tag', 0, 'ballad', 0.45, 0.35, 181, answer=TAG_SAX, roll=(25, 45))
    jazzband.pedal([b.piano, b.comp], P['tag'], tag, end=end.start - 0.1)
    b.bass.play(jazz.walking_bass(P['tag'], key=s.key, seed=191, vel=84, skip=0.1), tag)
    b.drums.play(jazzband.brushes(b, 4, style='medium', vel=0.66, fills=False, seed=201), tag)
    b.drums.play(jazzband.brushes(b, 2, style='two', vel=0.6, fills=False, seed=202), tag.bar(4))
    b.drums.play(jazz.brush_fill('swell', 2, kit=kit, vel=(14, 50)), tag.bar(4))
    # the last chord: Ebmaj9#11 rolled up from the left hand to a high sparkle; bass root; a soft cymbal + stir
    last_lh = Clip([(0, 7.9, p, v) for p, v in (('G2', 62), ('D3', 58), ('F3', 56), ('A3', 55))], length=8)
    last_rh = Clip([(0, 7.6, p, v) for p, v in (('D4', 60), ('Bb4', 60), ('F5', 66), ('A5', 58), ('D6', 50))],
                   length=8)
    b.comp.play(last_lh.strum(ms=70, bpm=TEMPO * 0.72), end)
    b.piano.play(last_rh.strum(ms=75, beats=None, bpm=TEMPO * 0.72).shift(0.3), end)
    b.piano.automate('instrument.pedal', [(end.start - 0.05, 0.0, 'step'), (end.start + 0.02, 1.0, 'step')])
    b.comp.automate('instrument.pedal', [(end.start - 0.05, 0.0, 'step'), (end.start + 0.02, 1.0, 'step')])
    b.bass.note('Eb2', end, dur=7, vel=88)
    b.drums.play(Clip([(0, 8, kit['crash'], 30), (0, 0.5, kit['kick'], 34), (0, 2, kit['sweep'], 60),
                       (2, 2, kit['sweep'], 48), (4, 3, kit['sweep'], 36)], length=8), end)

    s.ritardando((tag.bar(4), end.start), to=0.72, a_tempo=False)
    s.fermata(end.start, hold=2, length=4)
    for t in (b.piano, b.comp, b.sax):
        t.automate('send.room', ramp(end.start, end.end, -13, -8))
    return s
