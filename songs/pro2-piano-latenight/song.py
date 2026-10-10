"""Cellar Hours - a late-night F-minor AABA for solo piano, medium swing, composed by hand (the second "pro" reference
set for the blind comparison with the endless jazz-piano generator; written from songs/_blind/ROUNDS.md).
Build: python -m agentsound build songs/pro2-piano-latenight
Lead sheet + tune.json for the judge (after a build): python songs/pro2-piano-latenight/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound.endless.perform.band: the solo_piano preset, the genre's master
gain; the 'straight' feel = pianist style 'straight', left hand 'shell'), swung at 0.58. Only the composition and its
performance plan differ (BRIEF.md, ARRANGEMENT.md).

The tune is built from two small ideas: a = a tension falling by step and skipping down (G F Eb C: the 9th of Fm
resolving), b = a breath, then a leap up to a held colour tone (D G: the 13th of Bb13). Phrase 1 states a-b and
sequences it a step down (b widened to a 5th, its G now the #11 of Dbmaj7); phrase 2 answers with a stepwise climb to
the A's peak (Eb6, the #9 of C7alt) and a leading-tone landing on Ab. A2 turns its cadence through F7#9 into the
bridge; A3 cadences deceptively (Dbmaj7#11) and through the tritone (Gb7#11). The bridge has its own register and
rhythm: half notes and quarter-note triplets low in the piano, a descending-fifths walk (Bbm9 Eb13 Abmaj9 Dbmaj9),
then the head's one peak (F6 over Dm7b5, tied across the bar line into G7alt) and a chromatic fall home.
The solo is written out: a displaced quote of a, target-note chains with enclosures, a quarter-triplet version of a
answered by rising 8th lines, the bridge's triplet rhythm quoted, ONE peak (Ab6, a expanded at the top of solo A3,
b echoed an octave up), then a descent that ends on Db - the first note of the head-out's bridge.
Intro / tag: a plagal vamp over an F pedal into the Neapolitan Gbmaj7#11 with b developed (4th, 4th, 5th); the tag
stays on the Neapolitan and falls straight to Fm6/9 (no dominant), spread, with the tune's first note G on top.
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
FEEL = 'straight'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Cellar Hours', 'F minor', 'minor', 108, 4, 0.58, 7311

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#20263a', '#c98b4e'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the lead sheet
# chords per part: (symbol, bars)
A_FRONT = [('Fm9', 1), ('Bb13', 1), ('Ebm9', 0.5), ('Ab13', 0.5), ('Dbmaj7#11', 1), ('Gm7b5', 1), ('C7alt', 1)]
CHANGES = {
    'A1': A_FRONT + [('Fm9', 1), ('Db7#11', 0.5), ('C7b9', 0.5)],
    'A2': A_FRONT + [('Fm9', 1), ('Cm7b5', 0.5), ('F7#9', 0.5)],
    'B': [('Bbm9', 1), ('Eb13', 1), ('Abmaj9', 1), ('Dbmaj9', 1), ('Dm7b5', 1), ('G7alt', 1), ('Gm7b5', 1),
          ('C7alt', 1)],
    'A3': A_FRONT + [('Dbmaj7#11', 1), ('Gm7b5', 0.5), ('Gb7#11', 0.5)],
}
INTRO = [('Bbm9/F', 1), ('Fm9', 1), ('Gbmaj7#11', 1), ('C7sus4', 0.5), ('C7b9', 0.5)]
TAG = [('Bbm9/F', 1), ('Fm9', 1), ('Gbmaj7#11', 2)]
END_CHORD = 'Fm69'
BLOCKS = {'A1': ['i_IV7_ivm_bVII7_bVImaj7#11', 'ii0_Valt_i_bVI7_V'],
          'A2': ['i_IV7_ivm_bVII7_bVImaj7#11', 'ii0_Valt_i_V/iv'],
          'B': ['iv_bVII_bIII_bVI', 'vi0/V_V/V_ii0_Valt'],
          'A3': ['i_IV7_ivm_bVII7_bVImaj7#11', 'ii0_Valt_bVI_ii0_subV']}

# the melody (notation: absolute pitches; 8ths swing by the feel). a = bar 1, b = bar 2.
A_MEL = ('G5/4. F5/8 Eb5/8 C5/8~ C5/4 | r/4 D5/8 G5/8~ G5/2 '               # a (Fm9) | b (Bb13)
         '| F5/4. Eb5/8 C5/8 Bb4/8~ Bb4/4 | r/4 C5/8 G5/8~ G5/2 '           # a down a step, re-fitted | b widened (#11)
         '| r/8 Bb5/8 C6/8 Db6/8~ Db6/4 C6/8 Bb5/8 | r/8 Eb6/8~ Eb6/4 Db6/8 Bb5/8 Ab5/8 E5/8 ')   # climb, the A's peak
MEL = {
    # each A's last two bars its own: A1 a half note + a quarter-note-triplet answer, then the bVI7 turnaround
    'A1': A_MEL + '| F5/2 {G5 Ab5 C6}/2 | B5/4. Ab5/8 G5/4 E5/4',
    # A2 climbs to the 7th and falls in quarter-note triplets through F7#9 into the bridge's low Db
    'A2': A_MEL + '| F5/2 G5/8 Ab5/8 C6/8 Eb6/8~ | Eb6/4 Gb5/4 {A5 Ab5 Eb5}/2',
    # the bridge: low, half notes and quarter-note triplets; then the head's one peak (F6 tied into G7alt), home
    'B': ('Db5/2 {C5 Db5 F5}/2 | G5/2. r/4 | C5/2 {Bb4 C5 Eb5}/2 | F5/2. r/4 '
          '| Ab5/4. C6/8~ C6/4 F6/4~ | F6/4 Eb6/8 Db6/8~ Db6/4 B5/4 | Bb5/2. Db6/8 C6/8 | Bb5/4. Ab5/8~ Ab5/4 E5/8 F5/8'),
    # A3: the deceptive Dbmaj7#11 under a long F, a pickup G into the tritone cadence
    'A3': A_MEL + '| F5/2. r/8 G5/8~ | G5/4 Bb5/8 Db6/8~ Db6/4 C6/4',
}
# intro: b developed over a plagal vamp on an F pedal into the Neapolitan (5th, 4th, then 5 -> #11 of Gb), the
# dominant's sus4 falling to its b9 and 3rd
INTRO_MEL = 'r/4 F5/8 C6/8~ C6/2 | r/8 Eb5/8~ Eb5/8 Ab5/8~ Ab5/2 | Db6/4. C6/8~ C6/2 | F5/2 Db5/4 E5/4'
# tag: the vamp again, but it stays on the Neapolitan and falls straight to the tonic (the twist)
TAG_MEL = 'r/4 F5/8 C6/8~ C6/2 | r/8 Eb5/8~ Eb5/8 Ab5/8~ Ab5/2 | F5/4 C6/2. | Db6/4. Bb5/8 F5/2'
# the head out's last A: thinned, a held longer, the peak given up (Db6 instead of Eb6), the last bar left open
OUT_A3 = ('G5/2 F5/8 Eb5/8 C5/4 | r/4 D5/8 G5/8~ G5/2 | F5/2 Eb5/8 C5/8 Bb4/4 | r/4 C5/8 G5/8~ G5/2 '
          '| r/8 Bb5/8 C6/8 Db6/8~ Db6/2 | r/4 Db6/8 Ab5/8~ Ab5/4 E5/4 | F5/2. r/8 G5/8~ | G5/4 Bb5/8 Db6/8~ Db6/4 r/4')
# the written-out solo chorus (AABA): call / response with a, target-note chains, the bridge's triplets, ONE peak.
# Each A's ii-V (bars 5-6) gets its own territory: A1 low and from below, A2 one long line up from G4, A3 the descent.
SOLO = {
    'A1': ('r/2 r/8 G5/8 F5/8 Eb5/8 | D5/4 r/4 r/8 Ab5/8 G5/8 F5/8 '                     # a quoted late | on D
           '| Gb5/4. F5/8 Eb5/8 C5/8 r/4 | r/8 Eb5/8 F5/8 Ab5/8~ Ab5/4 r/4 '              # Gb | over Dbmaj7#11
           '| r/4 Bb4/8 C5/8 Db5/4 F5/8 Eb5/8 | E5/4 r/8 Gb5/8 Ab5/8 Bb5/8 Db6/4 '          # low, enclosure -> E
           '| C6/4. Ab5/8~ Ab5/4 r/4 | r/8 F5/8 Ab5/8 B5/8 Bb5/4 G5/8 E5/8'),
    'A2': ('{Ab5 G5 Eb5}/2 C5/4. r/8 | r/8 D5/8 F5/8 G5/8 Ab5/8 G5/8 D5/4 '               # a in quarter triplets
           '| {Gb5 F5 Db5}/2 Bb4/4. r/8 | r/8 C5/8 Eb5/8 F5/8 G5/4 r/4 '                   # down a step | answer
           '| r/8 Bb4/8 Db5/8 C5/8 Eb5/8 F5/8 Ab5/8 G5/8 | Bb5/4 Gb5/8 E5/8 Gb5/8 Ab5/8~ Ab5/4 '   # one line up
           '| r/4 G5/8 F5/8 C5/4 r/8 F5/8 | Gb5/4 Eb5/8 C5/8 A5/8 Ab5/8 C6/8 Eb6/8'),
    # the bridge 2 + 2 + 4: a line from the Db, a half-bar breath, an answer, then one long line with ONE
    # enclosure (C-Bb -> B, the 3rd of G7alt), the last bar half empty before the peak's pickup
    'B': ('Db6/4 r/8 C6/8 Db6/8 Eb6/8 Db6/8 Bb5/8 | C6/8 Bb5/8 Gb5/8 G5/8~ G5/2~ '
          '| G5/4 r/4 r/8 Eb5/8 F5/8 Ab5/8~ | Ab5/4 Bb5/8 C6/8 Db6/8 C6/8 Eb6/4 '
          '| r/8 F6/8 E6/8 D6/8 C6/8 Ab5/8 C6/8 Bb5/8 | B5/4 Db6/8 Eb6/8 Db6/8 B5/8 Ab5/8 G5/8 '
          '| Bb5/4 C6/8 Db6/8 F6/4 Eb6/8 Db6/8 | C6/4 r/4 r/4 r/8 Eb6/8'),
    'A3': ('Ab6/4. G6/8 F6/8 Eb6/8 C6/4 | r/4 D6/8 G6/8~ G6/2 '                            # THE peak: a, b at the top
           '| F6/8 Eb6/8 Db6/8 Bb5/8 C6/8 Bb5/8 Gb5/8 F5/8 | Eb5/4 r/8 C5/8 F5/8 G5/8 Ab5/8 C6/8~ '
           '| C6/4 Bb5/8 Db6/8~ Db6/4 C6/8 Bb5/8 | Ab5/4. Gb5/8 E5/8 Db5/8 Eb5/8 E5/8 '
           # the last bar turns to the bridge (Cm7b5 F7#9, V of iv): #9 / b9 / b7 falling to its Db
           '| F5/2. r/8 Ab5/8 | Bb5/4. Gb5/8 A5/8 Ab5/8 Gb5/8 Eb5/8'),
}
# the solo's last A ends like A2 (into the head out's bridge): Cm7b5 F7#9 instead of the tritone cadence
A3S = A_FRONT + [('Dbmaj7#11', 1), ('Cm7b5', 0.5), ('F7#9', 0.5)]
PARTS = ['A1', 'A2', 'B', 'A3']
REC: dict = {}                                           # section:part -> the pianist's Arrangement


def _line(spec, bars):
    return notes(spec, length=bars * METER)


def _touched(spec, frames):
    """A part's melody touched in pieces: frames = [(bars, lo, hi), ...] split the spec at its bar lines (the bridge:
    a soft low first half, then the climb to the head's peak)."""
    bars = [x for x in spec.split('|')]
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
    return Tune(genre=G.name, seed=SEED, mood='late-night', title=TITLE, key=KEY, mode=MODE, tempo=TEMPO,
                meter=METER, feel=FEEL, swing=SWING, form='AABA', parts=list(PARTS),
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
             **{f"solo {p}": (SOLO[p], A3S if p == PARTS[-1] else CHANGES[p], 8) for p in PARTS},
             **{'out A3': (OUT_A3, CHANGES['A3'], 8)},
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
    parts.update(A=parts['A1'], A3S=_changes_str(A3S), intro=_changes_str(INTRO), tag=_changes_str(TAG),
                 end=f"{END_CHORD}:{P['end']}")
    intro, head, solo, out, tag, end = s.form(
        f"intro:{P['intro']} head:AABA solo:A1,A2,B,A3S out:B,A3 tag:{P['tag']} end:{P['end']}", parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.band), swung at 0.58
    feel = jazz.Feel(TEMPO, ratio=SWING, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)
    lh = F['lh']                                             # 'shell': solo piano, the root in the left hand
    mem = pianist.Memory(once=True)                          # every fast figure at most once in the piece
    orn = P['head'].get('ornaments')
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ornaments=orn, ceiling='C7')), record=REC, **k)
    mel = {p: _line(MEL[p], 8) for p in PARTS}

    # ---- intro: the vamp rubato, ballad touch, tenths in the left hand (piano alone)
    calm = {'mordent': 1.0, 'restrike': 1.4, 'crush': 0.8, 'roll': 1.0}   # no fast figure, no turn here
    play(intro, _line(INTRO_MEL, 4), piano=dict(style='ballad', density=0.45, seed=11, lead_in=True, touch=(36, 72),
                                               ornaments=calm,
                                               lh='tenths', lh_vel=44, section_end=False, fill=0.2))
    s.rubato(intro, depth=F['rubato'], phrase='lean')

    # ---- head: the written rhythms kept (no extra anticipations); every A from the same hands (a theme restated),
    # the bridge opens up to the head's peak, A3 settles
    theme = dict(seed=101, anticipate=0.05, delay=0.0, fill=0.3, embellish=0.25, quick=0.04)
    mel['B'] = _touched(MEL['B'], [(4, 40, 72), (4, 50, 102)])     # the low half soft, the climb to the peak
    play(head, [mel[p] for p in PARTS], piano=dict(
        lead_in=True,
        A1=dict(theme, lead_in=False, touch=(42, 80), density=0.45, lh_vel=48),
        A2=dict(theme, touch=(46, 88), density=0.5, lh_vel=52),
        B=dict(seed=131, anticipate=0.05, delay=0.0, fill=0.35, density=0.6, lh_vel=54),
        A3=dict(theme, touch=(46, 90), density=0.5, lh_vel=52)))

    # ---- solo: written out; single lines with guide tones under the long notes -> 3rds / 6ths in the answers -> the
    # bridge's long targets voiced -> the peak line in octaves only on its top notes (doubles soft), then down.
    # The soloist's 8ths keep their written places (anticipate / delay 0) and few fills (the line is the solo).
    line = dict(anticipate=0.0, delay=0.0, fill=0.12, embellish=0.2, quick=0.05, lh_vel=54)
    sol = {p: _line(SOLO[p], 8) for p in PARTS}
    # the bridge's line, and its last 8th (the pickup into the peak) leaned on: the peak is reached, not switched on
    sol['B'] = _touched(SOLO['B'], [(4, 54, 88), (4, 66, 106)])   # a ceiling that rises
    sol['B'] = Clip._raw([n._replace(vel=106) if n.start >= 7 * METER + 3.4 else n for n in sol['B']], 8 * METER)
    sol['A3'] = _touched(SOLO['A3'], [(2, 64, 124), (1, 60, 112), (5, 50, 100)])  # the peak, then the line comes down
    play(solo, [sol[p] for p in PARTS], piano=dict(
        lead_in=True,
        A1=dict(line, seed=201, touch=(42, 80), density=0.3, devices={'single': 3.0, 'guide': 2.0}),
        A2=dict(line, seed=211, touch=(48, 92), density=0.4,
                devices={'single': 2.0, 'guide': 2.0, 'thirds': 1.0, 'sixths': 1.0}),
        B=dict(line, seed=221, density=0.5,
               devices={'guide': 2.0, 'single': 1.0, 'sixths': 1.0, 'drop2': 1.2, 'quartal': 1.0}),
        A3S=dict(line, seed=231, density=0.55, quick=0.0, ornaments=calm,     # the peak note itself, no grace turn doubles=0.78, lh_vel=58,
                devices={'octave': 1.5, 'drop2': 1.5, 'guide': 1.5, 'single': 1.0})))

    # ---- the head out from the bridge (near the head's level), then the thinned last A, softer, ballad voicings
    play(out, [_touched(MEL['B'], [(4, 44, 76), (4, 52, 98)]), _line(OUT_A3, 8)], piano=dict(
        lead_in=True, anticipate=0.05, delay=0.0,
        # no trill on the bridge's held G (blind r3: a fast figure on the 11th of a dominant): no fast ornaments
        B=dict(seed=311, density=0.55, fill=0.3,
               ornaments={'turn': 1.2, 'mordent': 1.0, 'restrike': 1.4, 'crush': 0.8, 'roll': 1.0}),
        A3=dict(seed=321, touch=(38, 80), density=0.45, style='ballad', lh_vel=46, fill=0.25)))

    # ---- no hole between the sections (as perform.build): a sweep over the last chord where a bar is left empty
    for k, (boundary, sym) in enumerate(((solo.start, CHANGES['A3'][-1][0]), (out.start, A3S[-1][0]))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the vamp again, ballad, ritardando; it stays on the Neapolitan and falls to Fm6/9 (spread, G on top)
    play(tag, _line(TAG_MEL, 4), pedal_end=end.start - 0.1, piano=dict(
        touch=(34, 70), style='ballad', density=0.45, seed=401, lead_in=True, lh='tenths', lh_vel=44,
        bpm=TEMPO * 0.85, section_end=False, fill=0.2))
    # the last chord voiced by hand (not the endless _end_clips): F C Ab low and open, Ab C D G above - the 6th and
    # the 9th, the tune's first note G on top; spread slowly
    lh_end = hold('F2=60 C3=50 Ab3=48', 2 * METER - 0.1, length=2 * METER)
    rh_end = hold('Ab4=52 C5=54 D5=58 G5=74', 2 * METER - 0.6, length=2 * METER)
    s.ending(end, chords=[(b.comp, lh_end, 140), (b.piano, rh_end, 120, 0.5)],
             rit=tag.bar(tag.bars // 2), to=0.75, hold=2, length=4, room=(-13, -8))
    # after the chord: the tune's first two notes (G F, the opening of a) high and soft, dying into the room
    b.piano.play(Clip([(0.0, 0.9, 91, 40), (0.75, 2.5, 89, 32)], length=4.0), end.start + 4.5)
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
