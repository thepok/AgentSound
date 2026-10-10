"""Carousel on Morton Street - a jazz waltz for solo piano (AABA, 16-bar parts, Eb major, 3/4, straight 8ths, 150 BPM),
head AND solo written by hand with recipes/jazz-composition.md (the second "pro" reference set for the blind test).
Build: python -m agentsound build songs/pro2-piano-waltz
Lead sheet + tune.json for the judge (after a build): python songs/pro2-piano-waltz/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound.endless.perform.band: the solo_piano preset, the genre's master
gain, the 'piano' profile), its 'waltz' feel played straight like the v1 waltz; the same players (pianist.arrange via
jazz.chorus, s.ending through the endless _ending). Only the writing differs (ARRANGEMENT.md).

The tune: a motif that climbs two steps and leaps a 4th (Bb C D | G), sequenced and re-fitted onto the ii-V of C minor
(Ab Bb C | F over the half-diminished chord), answered by an 8th line that reaches the A natural of F13; the A's peak
D6 over Gm7 in its third phrase, a chromatic descent home. A2 turns down a chromatic line (D C Cb Bb) into the bridge;
A3's tritone sub E7#11 takes the A1's D as its 7th. The bridge: long high notes falling by half steps (Eb D C Cb: Ab
lydian -> Ab minor), the same shape a step down in Gb, then the climb to the head's F6 over Abm6. The solo (one
chorus, written out): the motif displaced and re-fitted, 8th lines with enclosures and chromatic passing notes, a
call-and-response bridge, the motif in diminution climbing to the piece's one peak G6 over Bb13 in the last A, which
takes the chart's reharm (B7#11 for F13, shared with the head out's A3).
"""
import json
import sys
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentsound import jazz, notes, pianist
from agentsound.endless import Tune, genre as _genre
from agentsound.endless import perform
from agentsound.endless.composer import Harm, melody_issues
from agentsound.song import Song
from agentsound.theory import Key, note

G = _genre('jazz-piano')
FEEL = 'waltz'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Carousel on Morton Street', 'Eb major', 'major', 150, 3, None, 5821

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#5a2f4f', '#e8b04a'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the chart
# (symbol, bars); one chord per bar mostly - a waltz breathes in whole bars
A_FRONT = [('Ebmaj9', 2), ('Dm7b5', 1), ('G7b9', 1), ('Cm9', 2), ('F13', 2), ('Fm9', 1), ('Bb13', 1), ('Gm7', 1),
           ('C7b9', 1)]
CHANGES = {
    'A1': A_FRONT + [('Fm9', 1), ('Bb13', 1), ('Ebmaj9', 1), ('Bb13', 1)],          # turnaround to the top
    'A2': A_FRONT + [('Fm9', 1), ('Bb7b9', 1), ('Ebmaj9', 1), ('Eb13', 1)],         # V of IV into the bridge
    'B': [('Abmaj7#11', 2), ('Abm9', 1), ('Db13', 1), ('Gbmaj7#11', 2), ('Fm9', 1), ('Bb13', 1), ('Gm7', 1), ('C7b9', 1),
          ('Fm9', 1), ('Abm6', 1), ('Gm7', 1), ('Gb7#11', 1), ('Fm9', 1), ('Bb7b9', 1)],
    'A3': A_FRONT + [('Fm9', 1), ('E7#11', 1), ('Ebmaj9', 2)],                      # tritone sub: the A1's D = its 7th
}
# the chart variant of the last solo A and the head out's A3: the F13 bar 7 becomes its tritone sub B7#11 - the
# head's A5 there is its 7th (the reharm is tied to the melody note)
A3X = A_FRONT[:4] + [('B7#11', 1), ('F13', 1)] + A_FRONT[5:] + [('Fm9', 1), ('E7#11', 1), ('Ebmaj9', 2)]
INTRO = [('Ebmaj9', 1), ('Ab7#11', 1), ('Ebmaj9', 1), ('Ab7#11', 1), ('Gm7', 1), ('C7b9', 1), ('Fm9', 1),
         ('Bb7sus4', 1)]
TAG = [('Ebmaj9', 1), ('Ab7#11', 1), ('Ebmaj9', 1), ('Ab7#11', 1), ('Abm9', 1), ('Db13', 1), ('Ebmaj9', 2)]
END_CHORD = 'Eb69'
PARTS = ['A1', 'A2', 'B', 'A3']
BLOCKS = {'A1': ['I_viiø_V/ii_ii_V/V', 'ii_V_iii_VI_ii_V_turn'], 'A2': ['I_viiø_V/ii_ii_V/V', 'ii_V7b9_I_V/IV'],
          'B': ['IV_iv_bVII_bIII_ii_V_iii_VI_ii_ivm6_iii_subV/ii'], 'A3': ['I_viiø_V/ii_ii_V/V', 'ii_subV_I']}

# ------------------------------------------------------------------------------------------------ the head
# the motif: r/4 Bb4 C5 D5 | G5 (two steps up, a 4th leap to the 3rd). Phrase plan of the A (4 x 4 bars):
#   1 motif + its sequence re-fitted to the ii-V of Cm (lands on the b9 Ab -> G)    register Ab4-Ab5
#   2 an 8th answer falling then rising Eb G Ab -> the A natural of F13, lands on the 13th D5
#   3 the peak phrase: D resolves to C, chromatic G Ab A Bb, the A's top D6 over Gm7, b9 Db6 -> Bb5
#   4 home: Ab G F Eb, D held over Bb13, down to the 3rd G4 (A2: D C Cb Bb into the bridge; A3: the motif's head)
A_HEAD = ('r/4 Bb4/8 C5/8 D5/4 | G5/2. | r/4 Ab4/8 Bb4/8 C5/4 | F5/2 Ab5/4 | '
          'G5/4. F5/8 Eb5/8 D5/8 | C5/4 r/8 Eb5/8 G5/8 Ab5/8 | A5/2. | G5/4. F5/8 D5/4 | '
          'r/8 C5/8 Eb5/8 F5/8 Ab5/4 | G5/4 Ab5/8 A5/8 Bb5/4 | D6/2. | Db6/4. C6/8 Bb5/4 | ')
MEL = {
    'A1': A_HEAD + 'Ab5/4. G5/8 F5/8 Eb5/8 | D5/2 C5/8 Bb4/8 | G4/2. | r/2.',
    'A2': A_HEAD + 'Ab5/4. G5/8 F5/8 Eb5/8 | D5/4. C5/8 Cb5/4 | Bb4/4. C5/8 D5/8 G5/8 | Bb5/4 C6/4 Db6/8 D6/8',
    # the bridge: long notes high, falling by half steps (Eb D C Cb), the shape a step down in Gb, then the climb to
    # the head's peak F6 (the 6th of Abm6) and the hand-back
    'B': ('Eb6/2. | D6/2 C6/4 | Cb6/2. | Bb5/4. Ab5/8 F5/4 | Db6/2. | C6/2 Bb5/4 | Ab5/2. | G5/4 F5/4 Ab5/8 A5/8 | '
          'Bb5/2 C6/8 D6/8 | E6/4. Db6/8 Bb5/4 | Ab5/4 C6/8 Db6/8 Eb6/4 | F6/2. | D6/4. C6/8 Bb5/4 | '
          'Bb5/4 C6/4 Ab5/4 | Ab5/2 G5/4 | F5/4 D5/4 Cb5/4'),
    'A3': A_HEAD + 'Ab5/4. G5/8 F5/8 Eb5/8 | D5/2 Bb4/4 | r/8 Bb4/8 C5/8 D5/8 G5/4~ | G5/2 r/4',
}
# intro: a vamp of its own (I - IV7#11): the motif's first bar stops on its D, which the Ab7 takes as its #11; the
# second try reaches G and bends to Gb (the Ab7's 7th), a ii-V of the ii down into the head
INTRO_MEL = ('r/4 Bb4/8 C5/8 D5/4 | D5/2. | r/4 C5/8 D5/8 G5/4 | Gb5/2. | F5/4. D5/8 Bb4/4 | E5/4. Db5/8 Bb4/4 | '
             'Ab4/2. | r/2.')
# tag: the intro's vamp with the motif an octave up, its echo down, then the backdoor (Abm9 Db13) home
TAG_MEL = ('r/4 Bb5/8 C6/8 D6/4 | D6/2. | r/4 Bb4/8 C5/8 D5/4 | D5/2. | Cb5/2. | Bb4/4. Ab4/8 F4/4 | G4/2. | r/2.')

# ------------------------------------------------------------------------------------------------ the solo
# one chorus, written as lines (recipes/jazz-composition.md section 5): statement -> longer lines -> call and
# response -> the peak, every chord change aimed at a guide tone, enclosures / chromatic passing notes off the beat,
# one upper-structure arpeggio per 8 bars at most
SOLO = {
    # A1: the motif displaced by two beats, re-fitted onto the ii-V (Ab B | D F), a dorian answer, the head's Eb G Ab
    # -> A, a chromatic descent over Bb13, an enclosure of Bb over Gm7, the one diminished climb to C6
    'A1': ('r/2 Bb4/8 C5/8 | D5/4 G5/2 | r/2 Ab4/8 B4/8 | D5/4 F5/2 | '
           'Eb5/4 {D5 C5 Bb4}/4 G4/4 | Bb4/4 r/8 Eb5/8 G5/8 Ab5/8 | A5/4. G5/8 F5/8 Eb5/8 | D5/4 r/2 | '
           'r/8 C5/8 D5/8 Eb5/8 E5/8 F5/8 | G5/4. F5/8 E5/8 Eb5/8 | D5/8 C5/8 A4/8 Bb4/8 D5/8 F5/8 | '
           'E5/8 G5/8 Bb5/8 Db6/8 C6/4~ | C6/4 {Ab5 G5 F5}/4 Eb5/4 | D5/4 Eb5/8 E5/8 F5/8 Ab5/8 | G5/8 F5/8 D5/4 r/4 | '
           'r/4 r/8 F5/8 G5/8 Ab5/8'),
    # A2: the motif inverted from the landing G (G F Eb | Bb), a lydian turn (A natural), a locrian line, scale down
    # the G7b9 into C, the A natural of Cm dorian, a chromatic climb G G# A into F13 with its #11 B natural, longer
    # lines up to C6, the guide-tone chain Bb5 -> C6 -> D5 -> into the bridge on a chromatic B5 -> C6
    'A2': ('G5/4 F5/8 Eb5/8 Bb4/4 | r/8 C5/8 {D5 F5 A5}/4 G5/4 | F5/8 G5/8 Ab5/8 C6/8 Bb5/4 | '
           'G5/8 F5/8 Eb5/8 D5/8 Db5/8 B4/8 | C5/4 r/8 G5/8 Bb5/8 A5/8 | G5/4. Eb5/8 F5/8 G#5/8 | '
           'A5/4 Bb5/8 B5/8 C6/8 A5/8 | G5/8 F5/8 Eb5/8 D5/8 C5/4 | r/8 Eb5/8 Ab5/4 G5/8 F5/8 | '
           'D5/4 r/8 F5/8 G5/8 A5/8 | Bb5/4. A5/8 G5/8 F5/8 | E5/4 r/8 G5/8 A5/8 B5/8 | C6/4. Bb5/8 Ab5/8 G5/8 | '
           'Ab5/8 G5/8 F5/8 Eb5/8 D5/4 | r/4 {F5 G5 Bb5}/4 C6/8 D6/8 | Db6/4. C6/8 Bb5/8 B5/8'),
    # B: call (a long high note) and response (a low line): C6 / lydian Ab line, Cb6 / Db13 line; then the calls get
    # lines of their own, the chromatic Ab A -> Bb5, up to Eb6 over Abm6, the lydian-dominant scale over Gb7#11
    'B': ('C6/2 r/4 | r/8 G4/8 Bb4/8 C5/8 D5/8 Eb5/8 | Cb6/2 r/4 | r/8 Ab4/8 Bb4/8 Cb5/8 Eb5/8 F5/8 | '
          'Bb5/4. Ab5/8 Bb5/8 Db6/8 | C6/4 Db6/8 Bb5/8 F5/4 | r/8 Ab5/8 G5/8 Gb5/8 F5/8 Eb5/8 | '
          'D5/8 E5/8 F5/8 G5/8 Ab5/8 A5/8 | Bb5/4. C6/8 D6/8 Bb5/8 | Db6/4 Bb5/8 A5/8 G5/8 E5/8 | '
          'r/8 F5/8 Ab5/8 C6/8 Eb6/8 D6/8 | Eb6/4. Db6/8 Cb6/4 | Bb5/4. A5/8 G5/8 F5/8 | '
          'Fb5/4 Gb5/8 Ab5/8 Bb5/8 C6/8 | C6/4 B5/8 Bb5/8 Ab5/8 G5/8 | Ab5/8 F5/8 D5/8 Cb5/8 C5/8 A4/8'),
    # A3 (the chart's B7#11 in bar 7): the motif in diminution, sequenced up three times (Bb C D G / D Eb F Bb /
    # F G Ab C), B5 over G7b9, the lydian-dominant climb over B7#11 (A B C# D# F), Eb6 over F13, the arch to the
    # piece's peak G6 over Bb13 (bar 10), down by scale and a chromatic Bb A Ab G, E7#11's line resolving G# -> G
    'A3': ('r/8 Bb4/8 C5/8 D5/8 G5/8 F5/8 | r/8 D5/8 Eb5/8 F5/8 Bb5/8 A5/8 | F5/8 G5/8 Ab5/8 C6/8 Bb5/4 | '
           'B5/4. Ab5/8 F5/4 | Eb5/4 F5/8 G5/8 Bb5/8 D6/8 | Eb6/4. D6/8 C6/8 Bb5/8 | A5/4 B5/8 C#6/8 D#6/8 F6/8 | '
           'Eb6/4. D6/8 C6/8 A5/8 | Ab5/8 Bb5/8 C6/8 Eb6/8 {D6 Eb6 F6}/4 | G6/2. | F6/4 {Eb6 D6 C6}/4 Bb5/4 | '
           'Bb5/8 A5/8 Ab5/8 G5/8 E5/4 | Eb5/4 r/8 Ab5/8 G5/8 F5/8 | D5/4. E5/8 F#5/8 G#5/8 | G5/2. | '
           'r/4 r/8 Bb5/8 C6/8 D6/8'),
}
REC: dict = {}                                           # section:part -> the pianist's Arrangement


def _line(spec, bars):
    return notes(spec, length=bars * METER, meter='3/4')


def _beats(ch):
    return [(s, b * METER) for s, b in ch]


def _changes_str(ch):
    return ' '.join(f"{s}:{b:g}" for s, b in ch)


def _triples(clip):
    return [(round(n.start, 4), round(n.dur, 4), n.pitch) for n in sorted(clip, key=lambda n: n.start)]


def _bars(ch):
    return int(round(sum(b for _, b in ch)))


def tune() -> Tune:
    """The lead sheet as an endless Tune (same lead-sheet / tune.json format as the generator's)."""
    mel = {p: _triples(_line(MEL[p], 16)) for p in PARTS}
    return Tune(genre=G.name, seed=SEED, mood='bright', title=TITLE, key=KEY, mode=MODE, tempo=TEMPO,
                meter=METER, feel=FEEL, swing=SWING, form='AABA', parts=list(PARTS),
                changes={p: _beats(CHANGES[p]) for p in PARTS}, melody=mel,
                motif=[n for n in mel['A1'] if n[0] < 2 * METER],
                intro={'changes': _beats(INTRO), 'melody': _triples(_line(INTRO_MEL, 8))},
                tag={'changes': _beats(TAG), 'melody': _triples(_line(TAG_MEL, 8))}, end_chord=END_CHORD,
                blocks=BLOCKS, retries=0, end_kind='spread', solo_changes={'A3': _beats(A3X)},
                out_melody={})


TUNE = tune()

# every written line with its chart (the scratch lint and check_melody read these)
LINES = {**{f"head {p}": (_line(MEL[p], 16), _beats(CHANGES[p])) for p in PARTS},
         **{f"solo {p}": (_line(SOLO[p], 16), _beats(A3X if p == 'A3' else CHANGES[p])) for p in PARTS},
         'out A3': (_line(MEL['A3'], 16), _beats(A3X)),
         'intro': (_line(INTRO_MEL, 8), _beats(INTRO)), 'tag': (_line(TAG_MEL, 8), _beats(TAG))}


def check_melody() -> list:
    """The endless composer's own melody checks on the written head parts (clashes, register, leaps, the final
    note); the solo lines and intro / tag are checked for clashes on strong beats only (their range is wider)."""
    k = Key(KEY)
    out = []
    for name, (clip, ch) in LINES.items():
        notes_ = _triples(clip)
        head = name.startswith(('head', 'out'))
        lo, hi = (note('G4'), note('F6')) if head else (note('C4'), note('G6'))
        fin = {7, 10, 3} if name in ('head A3', 'out A3') else None
        out += [f"{name}: {i}" for i in melody_issues(notes_, Harm(ch, set(k.pcs)), lo, hi, meter=METER,
                                                       final_pcs=fin)
                if head or 'clash' in i]
    return out


# ------------------------------------------------------------------------------------------------ the performance

def build() -> Song:
    for issue in check_melody():
        print('melody check:', issue)
    s = Song(TITLE, tempo=TEMPO, key=KEY, seed=SEED, tail=6, meter=(METER, 4))
    parts = {p: _changes_str(CHANGES[p]) for p in PARTS}
    parts.update(A=parts['A1'], A3X=_changes_str(A3X), intro=_changes_str(INTRO), tag=_changes_str(TAG),
                 end=f"{END_CHORD}:{P['end']}")
    intro, head, solo, out, tag, end = s.form(
        f"intro:8 head:AABA solo:A1,A2,B,A3X out:B,A3X tag:8 end:{P['end']}", parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.band), the waltz played straight
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)
    lh = F['lh']
    mem = pianist.Memory()                                   # one ornament budget for the whole tune
    orn = P['head'].get('ornaments')
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ornaments=orn)), record=REC, **k)

    # ---- intro: the vamp alone, rubato, ballad touch, left-hand tenths
    play(intro, _line(INTRO_MEL, 8), piano=dict(style='ballad', density=0.5, seed=11, lead_in=True, touch=(42, 80),
                                               lh='tenths', lh_vel=46, section_end=True))
    s.rubato(intro, depth=F['rubato'] + 0.02, phrase='lean')

    # ---- head: A1 plain and singing, A2 a shade more, the bridge opens (its F6 the head's top), A3 settles
    play(head, [_line(MEL[p], 16) for p in PARTS], piano=dict(
        seed=101, lead_in=True,
        A1=dict(lead_in=False, touch=(48, 88), density=0.5),
        A2=dict(touch=(50, 92), density=0.55, seed=101),        # the restated A's from the A1's dice
        B=dict(touch=(54, 100), density=0.65),
        A3=dict(touch=(50, 92), density=0.55, seed=101)))

    # ---- solo: written out; harmonized more and more (single + guide tones -> 3rds / 6ths -> drop 2 / quartal ->
    # octaves / locked hands at the G6 peak); fills only as answers / approaches / enclosures (no arpeggio sweeps)
    solo_fills = {'answer': 2.0, 'approach': 1.5, 'enclosure': 1.5, 'stabs': 1.0}
    play(solo, [_line(SOLO[p], 16) for p in PARTS], piano=dict(
        seed=201, lead_in=True, lh_vel=56, fills=solo_fills,
        A1=dict(touch=(48, 86), density=0.35, devices={'single': 3.0, 'guide': 2.0, 'thirds': 0.5}),
        A2=dict(touch=(52, 94), density=0.45, devices={'guide': 2.0, 'single': 1.5, 'thirds': 1.5, 'sixths': 1.2}),
        B=dict(touch=(56, 100), density=0.55, devices={'guide': 1.5, 'drop2': 1.5, 'quartal': 1.5, 'sixths': 1.0}),
        A3X=dict(touch=(64, 116), density=0.75, climax=True, doubles=0.8,
                 devices={'octave': 3.0, 'locked': 2.0, 'drop2': 1.5, 'quartal': 0.5})))

    # ---- the head out from the bridge (near the head's level), the last A softer, with the B7#11
    play(out, [_line(MEL['B'], 16), _line(MEL['A3'], 16)], piano=dict(
        seed=311, lead_in=True,
        B=dict(touch=(54, 98), density=0.6),
        A3X=dict(touch=(46, 86), density=0.45)))

    # ---- no hole between the sections (as perform.build): a sweep over the last chord where a bar is left empty
    for k, (boundary, sym) in enumerate(((solo.start, 'Ebmaj9'), (out.start, 'Ebmaj9'))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(1.5, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the intro's vamp, the motif 8va then its echo, the backdoor home; ending: spread Eb6/9
    play(tag, _line(TAG_MEL, 8), pedal_end=end.start - 0.1, piano=dict(
        touch=(40, 78), style='ballad', density=0.5, seed=401, lead_in=True, lh='tenths', lh_vel=46,
        bpm=TEMPO * 0.85, section_end=False))
    perform._ending(s, b, TUNE, end, tag, METER, False, False, None)
    _lh_breath(b.comp, head.start, tag.start)
    return s


def _lh_breath(track, a: float, z: float, bars: int = 4) -> None:
    """The left hand breathes with the phrase: every `bars`-bar phrase an arc (x0.84 at its ends, x1.16 at 60 %), the
    bar's first attack leaned on, its off-beat answers lighter - the pianist's left hand plays its chords at a
    near-even level, which the dynamics ear reads as flat (the right hand has jazz.touch for this)."""
    import math
    span = bars * METER
    out = []
    for n in track._notes:
        if a - 1e-6 <= n.start < z - 1e-6:
            x = ((n.start - a) % span) / span
            arc = 0.84 + 0.32 * math.sin(math.pi * min(1.0, x / 0.6 * 0.5 if x < 0.6 else 0.5 + (x - 0.6) / 0.4 * 0.5))
            pos = (n.start - a) % METER
            arc *= 1.06 if pos < 0.1 else 0.94
            n = n._replace(vel=max(20, min(96, round(n.vel * arc))))
        out.append(n)
    track._notes = out


# ------------------------------------------------------------------------------------------------ the judge's files

def write_leadsheet(out_dir: Path) -> None:
    """out/leadsheet.txt (= the endless tune.txt format) + out/tune.json (= the endless tune.json fields)."""
    rep = json.loads((out_dir / 'report.json').read_text(encoding='utf-8'))
    g = rep.get('global') or {}
    audio_s = g.get('durationSec') or 0.0
    t = TUNE
    (out_dir / 'leadsheet.txt').write_text(
        t.describe() + f"\n\n{audio_s:.0f} s of music, {g.get('lufsIntegrated')} LUFS\n", encoding='utf-8')
    info = dict(t.to_dict(), lufs=g.get('lufsIntegrated'), lra=g.get('loudnessRange'), gate='pass',
                files={'mp3': str(out_dir / 'mix.mp3'), 'cover': str(out_dir / 'cover.png')},
                piano_dynamics_db=next((n['dynamics'].get('dynamicsDb') for n in rep.get('nodes') or []
                                        if n.get('id') == 'piano' and isinstance(n.get('dynamics'), dict)), None),
                duration_s=round(audio_s, 1),
                intro=_changes_str(INTRO), tag=_changes_str(TAG), end_chord=END_CHORD)
    (out_dir / 'tune.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f"wrote {out_dir / 'leadsheet.txt'} and {out_dir / 'tune.json'}")


if __name__ == '__main__' and '--leadsheet' in sys.argv:
    write_leadsheet(Path(__file__).resolve().parent / 'out')
