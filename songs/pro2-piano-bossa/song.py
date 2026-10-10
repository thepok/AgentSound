"""Veranda Light - a tender straight-eighth ABAC bossa in E-flat for solo piano, composed by hand (the second "pro"
reference set for the blind comparison with the endless jazz-piano generator; written from songs/_blind/ROUNDS.md).
Build: python -m agentsound build songs/pro2-piano-bossa
Lead sheet + tune.json for the judge (after a build): python songs/pro2-piano-bossa/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound.endless.perform.band: the solo_piano preset, the genre's master
gain + the bossa feel's -1.5 dB), the endless bossa left hand (rootless bossa comping + the root-fifth line 'R__f'),
straight 8ths with the piano's lay-back. Only the composition and its performance plan differ (BRIEF.md,
ARRANGEMENT.md).

The tune: one small idea, a three-note sigh that falls onto a syncopated long note (C Bb G: 6-5-3 of Ebmaj9). It is
moved chromatically onto the lydian dominant (B Bb Gb over Ab7#11: the Cb a passing tone from the chord's #9), then
onto Gm9, where the falling guide-tone line G - Gb - F - Eb carries the phrase down to the passing diminished chord.
Phrase 2 inverts the sigh (rising C Eb G, then a 4th higher F Ab C) and peaks on D6 over Gm7 before the b9 of C7
resolves by step. The bridge (B) has its own register and rhythm: low (G4-G5), on the beat, quarters and halves,
a descending circle (Cm9 Cm7/Bb Am7b5 D7b9 Gm9 C13 Fm9 Bb7b9) answered by little walks up. A2 bends the A's peak to
Db over Bbm9 (the cadence varied) and turns to the subdominant; C climbs to the head's one peak (F6 over Abmaj9),
sighs through the minor iv (Abm9 Db13), falls by half steps (Gm9 Gb7#11 Fm9 E7#11) and ends with the hook bent onto
the 9th - open, not resolved.
The solo is written out: the sigh displaced and answered, rising lines to the lydian #11, call and response in the
bridge (falling sighs answered by climbs, enclosures), a denser A2 that builds to ONE peak (Ab6 over Bbm9), then the
C section winds down with the head's own sighs and lands on the 9th / the sus4.
Intro / tag: a vamp of their own (Ebmaj9 - Bmaj7#11, the bVI a third away, the sigh landing on common tones); the tag
turns the vamp's second half into the minor iv (Abm9 Db13, the backdoor) and the last chord Eb6/9 rings while the
hook's three notes come back softly above it.
"""
import json
import sys
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentsound import jazz, notes, pianist
from agentsound.endless import Tune, genre as _genre
from agentsound.endless import perform
from agentsound.notation import hold
from agentsound.patterns import Clip
from agentsound.song import Song

G = _genre('jazz-piano')
FEEL = 'bossa'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Veranda Light', 'Eb major', 'major', 118, 4, None, 7312

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#2f4a44', '#f0c9a0'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the lead sheet
A_FRONT = [('Ebmaj9', 1), ('Ab7#11', 1), ('Gm9', 1), ('Gbo7', 1), ('Fm9', 1), ('Bb13', 1)]
CHANGES = {
    'A1': A_FRONT + [('Gm7', 0.5), ('C7b9', 0.5), ('Fm9', 0.5), ('Bb7sus4', 0.5)],
    'B': [('Cm9', 1), ('Cm7/Bb', 1), ('Am7b5', 1), ('D7b9', 1), ('Gm9', 1), ('C13', 1), ('Fm9', 1), ('Bb7b9', 1)],
    'A2': A_FRONT + [('Bbm9', 1), ('Eb7b9', 1)],
    'C': [('Abmaj9', 1), ('Abm9', 0.5), ('Db13', 0.5), ('Gm9', 1), ('Gb7#11', 1), ('Fm9', 1), ('E7#11', 1),
          ('Ebmaj9', 1), ('Fm9', 0.5), ('Bb7sus4', 0.5)],
}
INTRO = [('Ebmaj9', 1), ('Bmaj7#11', 1), ('Ebmaj9', 1), ('Bmaj7#11', 0.5), ('Bb7sus4', 0.5)]
TAG = [('Ebmaj9', 1), ('Bmaj7#11', 1), ('Abm9', 1), ('Db13', 1)]
END_CHORD = 'Eb69'
BLOCKS = {'A1': ['I_IV7#11_iii_biiio', 'ii_V_iii_VI_ii_V'], 'B': ['vi_vi/5_vii0/iii_V/iii', 'iii_VI_ii_V'],
          'A2': ['I_IV7#11_iii_biiio', 'ii_V_v_I7'], 'C': ['IV_iv_bVII_iii_bIII7#11', 'ii_subV_I_ii_V']}

# the melody (straight 8ths). The hook = A1 bar 1: the sigh C Bb G onto the syncopated 3rd.
A_MEL = ('r/8 C6/8 Bb5/8 G5/8~ G5/2 | r/8 B5/8 Bb5/8 Gb5/8~ Gb5/2 '          # the sigh | moved down chromatically
         '| r/4 Bb5/8 A5/8 F5/2 | Eb5/2. r/4 '                       # the guide line G Gb F Eb lands
         '| r/4 C5/8 Eb5/8 G5/2 ')                                            # the sigh inverted
MEL = {
    # phrase 2 is one 4-bar arc: the inversion a 4th higher runs on into the D6 peak over the bar line
    'A1': A_MEL + '| r/4 F5/8 Ab5/8 C6/4. D6/8~ | D6/2 Db6/2 | C6/4 r/8 Ab5/8~ Ab5/2',
    # bridge: lower, on the beat; a fall and a rise, the fall's answer, then a longer line (no sequence copied)
    'B': ('G5/4 Eb5/8 D5/8~ D5/2 | r/4 C5/8 D5/8 Eb5/2 | F5/4 Eb5/4 C5/2 | F#5/2 Eb5/4 C5/4 '
          '| D5/2. F5/8 A5/8~ | A5/2 Bb5/8 A5/8 G5/4 | Ab5/4. G5/8~ G5/4 F5/4 | D5/4. F5/8 Ab5/8 B5/8~ B5/4'),
    # A2: the arc bent - Db (the b3 of Bbm9) instead of D, and the turn to the subdominant
    'A2': A_MEL + '| r/4 F5/8 Ab5/8 C6/2 | Db6/4. C6/8~ C6/2 | Bb5/4. G5/8~ G5/2',
    # C: the head's one peak (F6), the minor iv, half steps down, the hook bent onto the 9th
    'C': ('r/8 Bb5/8 C6/8 F6/8~ F6/2 | Eb6/4. B5/8~ B5/4 Ab5/4 | Bb5/4 A5/8 F5/8~ F5/2 | E5/4. Eb5/8~ Eb5/2 '
          '| r/4 Ab5/8 G5/8 C6/2 | B5/2 Bb5/2 | r/8 C6/8 Bb5/8 F5/8~ F5/2 | r/2 r/8 Eb5/8 F5/8 Ab5/8'),
}
INTRO_MEL = 'r/2 r/8 D6/8 C6/8 Bb5/8~ | Bb5/2. r/4 | r/2 r/8 G5/8 F5/8 Eb5/8~ | Eb5/2 F5/4 Ab5/4'
TAG_MEL = 'r/2 r/8 D6/8 C6/8 Bb5/8~ | Bb5/2. r/4 | r/2 r/8 Eb6/8 Db6/8 B5/8~ | B5/2 Bb5/4 F5/4'
# the head out: A2 paraphrased by hand (a later entrance, an added 13th, a pickup); the C with its peak entered late,
# the E7#11 bar turned through its 13th, the last bar held
OUT = {
    'A2': ('r/4 C6/8 Bb5/8 G5/2 | r/8 B5/8 Bb5/8 Gb5/8~ Gb5/4 F5/4 | r/4 Bb5/8 A5/8 F5/2 '
           '| Eb5/2 r/8 D5/8 Eb5/8 F5/8 | G5/4 C5/8 Eb5/8 G5/2 | r/4 F5/8 Ab5/8 C6/2 | Db6/4. C6/8~ C6/2 '
           '| Bb5/4. G5/8~ G5/2'),
    'C': ('r/4 Bb5/8 C6/8 F6/2 | Eb6/4. B5/8~ B5/4 Ab5/4 | Bb5/4 A5/8 F5/8~ F5/2 | E5/4. Eb5/8~ Eb5/2 '
          '| r/4 Ab5/8 G5/8 C6/2 | B5/4. C#6/8~ C#6/4 Bb5/4 | r/8 C6/8 Bb5/8 F5/8~ F5/2 | Eb5/1'),
}
# the solo: lines that cross the bar lines (phrases start on an "and" / tied over), one arpeggio figure (the
# bridge's D7b9 call), call and response in the bridge, the A2 building to ONE peak, the C winding down
SOLO = {
    'A1': ('r/4 r/8 C6/8 Bb5/8 G5/8~ G5/4 | r/4 F5/8 Gb5/8 Ab5/8 C6/8 D6/4~ '               # the sigh late | to #11
           '| D6/8 C6/8 Bb5/8 A5/8 Bb5/4 r/8 F5/8~ | F5/4 Eb5/8 D5/8 Eb5/8 Gb5/8 B5/8 A5/8 '   # over the bar lines
           '| Ab5/4. G5/8~ G5/4 r/8 D5/8 | F5/4 r/8 G5/8 Ab5/8 G5/8 Gb5/8 F5/8~ '
           '| F5/4 A5/8 F5/8 Eb5/8 E5/8 G5/8 Db6/8 | C6/8 Ab5/8 G5/2 r/4'),            # a pickup into the bridge
    'B': ('r/8 D5/8 F5/8 G5/8 Bb5/8 A5/8 G5/8 D6/8~ | D6/4 C6/8 Bb5/8 G5/4 r/8 Eb6/8~ '         # call | the sigh answers
          '| Eb6/4 D6/8 C6/8 A5/8 C6/8 G5/4 | F#5/8 A5/8 C6/8 Eb6/8~ Eb6/4 D6/8 C6/8 '
          '| Bb5/2 r/2 | r/8 D6/8 Bb5/8 A5/8 G5/4 E5/8 G5/8 '
          '| Ab5/4. Bb5/8 C6/8 Eb6/8 D6/8 C6/8 | B5/4. Bb5/8 Ab5/8 G5/8 F5/4'),
    'A2': ('G5/4 r/8 D6/8 C6/8 Bb5/8 G5/8 Bb5/8~ | Bb5/4 C6/8 D6/8 Eb6/8 D6/8 C6/8 B5/8 '      # denser, building
           '| Bb5/4 {D6 C6 Bb5}/4 A5/4 F5/8 G5/8 | A5/4 B5/8 C6/8~ C6/4 r/4 '
           '| r/8 G5/8 Ab5/8 Bb5/8 C6/4 Bb5/8 Ab5/8 | G5/8 Bb5/8 C6/8 D6/8 F6/4. G6/8 '
           '| Ab6/4. F6/8 Db6/8 C6/8 Bb5/8 Ab5/8 | G5/4 r/8 Ab5/8 A5/8 Bb5/8 Db6/8 B5/8'),     # THE peak | enclosure
    'C': ('C6/4. Bb5/8 C6/8 D6/8 Eb6/8 F6/8 | Eb6/4 Db6/8 B5/8 Bb5/8 Ab5/8 r/4 '
          '| r/8 Bb5/8 A5/8 F5/8~ F5/4 D5/4 | E5/4. Eb5/8 C5/4 Db5/8 Ab5/8~ '                 # the head's sigh
          '| Ab5/4 G5/8 F5/8~ F5/4 r/8 A5/8 | G#5/4. A#5/8 B5/8 C#6/8 B5/8 G#5/8 '
          '| G5/2. r/8 F5/8~ | F5/2 Eb5/4 r/4'),
}
PARTS = ['A1', 'B', 'A2', 'C']
REC: dict = {}                                           # section:part -> the pianist's Arrangement


def _line(spec, bars):
    return notes(spec, length=bars * METER)


def _touched(spec, frames):
    """A part's line touched in pieces: frames = [(bars, lo, hi), ...] split the spec at its bar lines."""
    bars = spec.split('|')
    out, at = [], 0
    for n, lo, hi in frames:
        clip = jazz.touch(_line(' | '.join(bars[at:at + n]), n), lo, hi)
        out += [x._replace(start=x.start + at * METER) for x in clip]
        at += n
    return Clip._raw(out, at * METER)


def _beats(ch):
    return [(s, b * METER) for s, b in ch]


def _changes_str(ch):
    return ' '.join(f"{s}:{b:g}" for s, b in ch)


def _triples(clip):
    return [(round(n.start, 4), round(n.dur, 4), n.pitch) for n in sorted(clip, key=lambda n: n.start)]


def tune() -> Tune:
    """The lead sheet as an endless Tune (same lead-sheet / tune.json format as the generator's)."""
    mel = {p: _triples(_line(MEL[p], 8)) for p in PARTS}
    return Tune(genre=G.name, seed=SEED, mood='tender', title=TITLE, key=KEY, mode=MODE, tempo=TEMPO,
                meter=METER, feel=FEEL, swing=SWING, form='ABAC', parts=list(PARTS),
                changes={p: _beats(CHANGES[p]) for p in PARTS}, melody=mel,
                motif=[n for n in mel['A1'] if n[0] < 2 * METER],
                intro={'changes': _beats(INTRO), 'melody': _triples(_line(INTRO_MEL, 4))},
                tag={'changes': _beats(TAG), 'melody': _triples(_line(TAG_MEL, 4))}, end_chord=END_CHORD,
                blocks=BLOCKS, retries=0)


TUNE = tune()


def check_melody() -> list:
    """The endless composer's melody checks on the written parts (recipes/jazz-composition.md section 8): clashes,
    register, leaps on the head parts; clashes only on the solo / intro / tag (their range is wider)."""
    from agentsound.endless.composer import Harm, melody_issues
    from agentsound.theory import Key, note
    k = Key(KEY)
    lines = {**{f"head {p}": (MEL[p], CHANGES[p], 8) for p in PARTS},
             **{f"solo {p}": (SOLO[p], CHANGES['C'] if p == PARTS[-1] else CHANGES[p], 8) for p in PARTS},
             **{f'out {p}': (OUT[p], CHANGES[p], 8) for p in OUT},
             'intro': (INTRO_MEL, INTRO, 4), 'tag': (TAG_MEL, TAG, 4)}
    out = []
    for name, (spec, ch, bars) in lines.items():
        head = name.startswith(('head', 'out'))
        lo, hi = (note('G4'), note('G6')) if head else (note('C4'), note('A6'))
        out += [f"{name}: {i}" for i in melody_issues(_triples(_line(spec, bars)), Harm(_beats(ch), set(k.pcs)),
                                                        lo, hi, meter=METER) if head or 'clash' in i]
    return out


def build() -> Song:
    for issue in check_melody():
        print('melody check:', issue)
    s = Song(TITLE, tempo=TEMPO, key=KEY, seed=SEED, tail=6, meter=(METER, 4))
    parts = {p: _changes_str(CHANGES[p]) for p in PARTS}
    parts.update(A=parts['A1'], intro=_changes_str(INTRO), tag=_changes_str(TAG), end=f"{END_CHORD}:{P['end']}")
    intro, head, solo, out, tag, end = s.form(
        f"intro:{P['intro']} head:ABAC solo:ABAC out:A2,C tag:{P['tag']} end:{P['end']}", parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.band), straight 8ths with the piano's lay-back
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)
    mem = pianist.Memory(once=True)                          # every fast figure at most once in the piece
    orn = P['head'].get('ornaments')
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=None, lh_vel=54, style=F['style'], ornaments=orn, ceiling='C7')), record=REC, **k)

    def bossa_left(section, vel=1.0, seed=0, pedal_end=None):
        """The endless bossa left hand: rootless bossa comping + the root-fifth bass, both on the comp track; vel a
        level for the section or one per part."""
        vels = list(vel) if isinstance(vel, (list, tuple)) else [vel] * len(section.parts)
        comp = dict(F['comp'])
        roll = comp.pop('roll', None)
        comp['vel'] = jazz.each(*[comp.get('vel', 54) * v for v in vels])
        play(section, None, piano=None, pedal_end=pedal_end,
             comp=dict(comp, answer=False, seed=seed, roll=roll, roll_seed=seed))
        blo, bhi = F['bass_vel']
        for i, (part, v) in enumerate(zip(section.parts, vels)):
            line = part.prog.bass(pattern=F['bass_pattern'], rate='1/8', low='C2', vel=(blo + bhi) / 2 * v,
                                  gate=0.85)
            # the bass breathes wider than the endless default (blind r5 / flat_dynamics: a level bossa bass)
            b.comp.play(jazz.bass_touch(line, blo * v * 0.7, bhi * v * 1.08, accent='1-3', seed=seed + i), part)

    mel = {p: _line(MEL[p], 8) for p in PARTS}

    # ---- intro: the vamp rubato, the piano alone, tenths
    play(intro, _line(INTRO_MEL, 4), piano=dict(style='ballad', density=0.45, seed=11, lead_in=True, touch=(38, 74),
                                               lh='tenths', lh_vel=44, section_end=False, fill=0.25))
    s.rubato(intro, depth=F['rubato'], phrase='lean')

    # ---- head: soft and singing, the A's from the same hands (the theme restated), the bridge low and quiet, the C
    # climbs to the head's peak
    theme = dict(seed=101, anticipate=0.05, delay=0.0, fill=0.1, embellish=0.15, quick=0.0)
    # the sigh is a sigh: touched, then its three notes lightened towards the landing (C6 leaned on, G5 the lightest)
    for p_, lift in (('A1', 0), ('A2', 6)):
        t_ = jazz.touch(mel[p_], *((42, 82) if p_ == 'A1' else (46, 88)))
        sigh = {84: 80 + lift, 82: 72 + lift, 79: 64 + lift}
        mel[p_] = Clip._raw([n._replace(vel=sigh[n.pitch]) if n.start < 4 and n.pitch in sigh else n for n in t_],
                            t_.length)
    play(head, [mel[p] for p in PARTS], lh_pedal=False, piano=dict(
        lead_in=True,
        A1=dict(theme, lead_in=False, density=0.45),
        B=dict(seed=121, anticipate=0.0, delay=0.0, fill=0.0, quick=0.0, touch=(38, 74), density=0.45),
        A2=dict(theme, density=0.5),
        C=dict(seed=141, anticipate=0.05, delay=0.0, fill=0.3, touch=(50, 100), density=0.55)))
    bossa_left(head, [0.75, 0.7, 0.8, 0.9], seed=151)

    # ---- solo: written out; single lines + guide tones -> 3rds / 6ths in the bridge's answers -> the A2 builds to the
    # peak (drop 2 / octaves on its long notes only) -> the C winds down (guide tones, sixths)
    line = dict(anticipate=0.0, delay=0.0, fill=0.12, embellish=0.2, quick=0.0)
    sol = {p: _line(SOLO[p], 8) for p in PARTS}
    # the A2 builds below the peak's level; only the last three bars (D6 F6 G6 -> Ab6) go above v100
    sol['A2'] = _touched(SOLO['A2'], [(5, 54, 90), (3, 64, 120)])
    play(solo, [sol[p] for p in PARTS], lh_pedal=False, piano=dict(
        lead_in=True,
        A1=dict(line, seed=201, touch=(42, 80), density=0.3, devices={'single': 3.0, 'guide': 2.0}),
        B=dict(line, seed=211, touch=(48, 92), density=0.4,
               devices={'single': 2.0, 'guide': 2.0, 'thirds': 1.0, 'sixths': 1.2}),
        A2=dict(line, seed=221, density=0.55, doubles=0.6,
                devices={'guide': 1.5, 'drop2': 1.5, 'octave': 1.2, 'sixths': 1.0, 'single': 1.0}),
        C=dict(line, seed=231, touch=(46, 86), density=0.45, embellish=0.0,
               devices={'guide': 2.0, 'sixths': 1.2, 'single': 1.5, 'drop2': 1.0})))
    bossa_left(solo, [0.8, 0.9, 0.95, 0.85], seed=221)        # the comping builds with the solo

    # ---- the head out: A2 paraphrased (written above), the C as written with its last bar held, softer
    play(out, [_line(OUT['A2'], 8), _line(OUT['C'], 8)], lh_pedal=False, piano=dict(
        lead_in=True, anticipate=0.05, delay=0.0,
        A2=dict(seed=311, touch=(46, 88), density=0.5, fill=0.3, embellish=0.0),
        C=dict(seed=321, touch=(40, 82), density=0.45, fill=0.25, style='ballad')))
    bossa_left(out, [0.75, 0.65], seed=341)

    # ---- no hole between the sections (as perform.build)
    for k, (boundary, sym) in enumerate(((solo.start, CHANGES['C'][-1][0]), (out.start, CHANGES['C'][-1][0]))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the vamp, its second half turned into the minor iv (the backdoor), ritardando; Eb6/9 rolled, the hook's
    # three notes softly above it
    play(tag, _line(TAG_MEL, 4), pedal_end=end.start - 0.1, lh_pedal=False, piano=dict(
        touch=(36, 72), style='ballad', density=0.45, seed=401, lead_in=True, lh=None,
        bpm=TEMPO * 0.85, section_end=False, fill=0.2))           # the bossa left hand alone (no doubled roots)
    bossa_left(tag, 0.65, seed=431, pedal_end=end.start - 0.1)
    # the last sigh as the top voice: C6 Bb5 over the ringing tag, and the Eb6/9 struck under its G5 (voiced by
    # hand, not the endless _end_clips), the left hand open (Eb Bb G)
    b.piano.play(Clip([(0.0, 0.6, 84, 60), (0.5, 0.6, 82, 54)], length=1.0), end.start)
    lh_end = hold('Eb2=58 Bb2=48 G3=46', 2 * METER - 0.1, length=2 * METER)
    rh_end = hold('F4=48 Bb4=50 C5=52 G5=64', 2 * METER - 1.1, length=2 * METER)
    s.ending(end, chords=[(b.comp, lh_end, 90), (b.piano, rh_end, 60, 1.0)],
             rit=tag.bar(tag.bars // 2), to=0.75, hold=2, length=4, room=(-13, -8))
    return s


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
