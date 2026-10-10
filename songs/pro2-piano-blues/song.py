"""Hollis Street Shuffle Club - a medium-swing jazz blues in Eb for solo piano (riff head, 4/4, swing 0.58, 112 BPM),
head AND three solo choruses written by hand with recipes/jazz-composition.md (the second "pro" reference set for the
blind test). Build: python -m agentsound build songs/pro2-piano-blues
Lead sheet + tune.json for the judge (after a build): python songs/pro2-piano-blues/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound.endless.perform.band: the solo_piano preset, the genre's master
gain, the 'piano' profile), its 'straight' feel swung lightly (0.58, the most HUMAN_FEEDBACK allows); the same players
(pianist.arrange via jazz.chorus, the endless _ending in its 'cadenza' style). Only the writing differs
(ARRANGEMENT.md). The lines and charts are notated in F (names below) and played a whole step down (SHIFT).

The tune (in F): a two-bar riff - the blue third bending up (F Ab A), a jump to C6 and back, answered by the IV
chord's Ab F D (which is also exactly the Bdim7 of bar 6: the answer returns there literally) - stated AAB: bars 1-8
riff, riff, riff re-fitted to Bb and D7b9, then a punchline that climbs the Gm9 by scale and falls down C13 through
its b9. Three charts: the plain jazz blues; a second chorus with the Am7 Abm7-Db9 walk-down and tritone subs
(Gb7#11, Ab13, Db9) whose punchline climbs to the head's top E6; a backdoor chorus (Bbm9 Eb9 in bars 9-10) for the
last solo chorus and the head out. Intro: a dominant pedal (C9sus4 / C7b9) with the riff's blue figure, into the
head through Gb7#11; the tag reprises the riff and closes with a minor plagal Bbm6 into F13, a short cadenza into it.
"""
import json
import math
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
FEEL = 'straight'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Hollis Street Shuffle Club', 'Eb major', 'major', 112, 4, 0.58, 6143
SHIFT = -2     # the lines and charts below are notated in F (the sketch) and played a whole step down, in Eb: the
               # riff's register (C5-G6 in F) sat on the 800 Hz-2.5 kHz band of the locked genre sound (+6 dB mids)

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#3b2a1f', '#d97b41'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the charts
# (symbol, bars); three variants of the jazz blues
FRONT = [('F13', 1), ('Bb13', 1), ('F13', 1), ('Cm9', 0.5), ('F13', 0.5), ('Bb13', 1), ('Bdim7', 1)]
C1 = FRONT + [('F13', 1), ('D7b9', 1), ('Gm9', 1), ('C13', 1), ('F13', 0.5), ('D7b9', 0.5), ('Gm9', 0.5),
              ('C7b9', 0.5)]
# the second chorus: the walk-down Am7 - Abm7 Db9 into Gm9, the tritone sub Gb7#11 for C13, a tritone turnaround
C2 = FRONT + [('Am7', 1), ('Abm7', 0.5), ('Db9', 0.5), ('Gm9', 1), ('Gb7#11', 1), ('F13', 0.5), ('Ab13', 0.5),
              ('Db9', 0.5), ('Gb7#11', 0.5)]
# the backdoor chorus (the last solo chorus and the head out's second): iv - bVII7 in bars 9-10
C3 = FRONT + [('F13', 1), ('D7b9', 1), ('Bbm9', 1), ('Eb9', 1), ('F13', 0.5), ('D7b9', 0.5), ('Gm9', 0.5),
              ('C7b9', 0.5)]
CHANGES = {'A1': C1, 'A2': C2}
INTRO = [('C9sus4', 1), ('C7b9', 1), ('C9sus4', 1), ('Gb7#11', 1)]
TAG = [('F13', 1), ('Bb13', 1), ('F13', 1), ('Bbm6', 1)]
END_CHORD = 'F13'                                        # played as Eb13 (_sym)
PARTS = ['A1', 'A2']
BLOCKS = {'A1': ['jazz_blues'], 'A2': ['jazz_blues_walkdown_tritone']}

# ------------------------------------------------------------------------------------------------ the head
RIFF = 'r/8 F5/8 Ab5/8 A5/8 r/8 C6/8 A5/4'            # the blue third bending up, the jump to C6 and back
ANSWER = 'r/8 Ab5/8 F5/8 D5/8 F5/4 r/4'               # Ab F D: Bb13's 7-5-3, and Bdim7 note for note
FRONT_MEL = (f"{RIFF} | {ANSWER} | {RIFF} | {ANSWER} | "
             'r/8 Bb5/8 Db6/8 D6/8 r/8 F6/8 D6/4 | ' + ANSWER + ' | ' + RIFF + ' | ')
MEL = {
    # punchline 1: D7b9's answer re-fitted (C A F# Eb), the Gm9 climbed by scale from the Eb's resolution D, C13
    # walked down through its b9, the riff's head over F13 and the D7's upper notes, a turnaround onto E
    'A1': FRONT_MEL + ('r/8 C6/8 A5/8 F#5/8 Eb5/4 r/4 | D5/4 r/8 F5/8 G5/8 A5/8 Bb5/8 C6/8 | '
                       'D6/8 Db6/8 C6/8 Bb5/8 A5/8 G5/8 E5/4 | F5/4 r/8 Ab5/8 A5/8 C6/8 Eb6/4 | '
                       'D6/4 Bb5/8 G5/8 Bb5/8 A5/8 G5/8 E5/8'),
    # punchline 2 (the walk-down chart): the answer re-fitted to Abm7 (Cb Ab Gb) and Db9 (F), the scale climb to D6,
    # the head's top E6 = the Gb7#11's 7th, its #11 C6, down the tritone turnaround (Ab13, Db9) onto Gb's #11
    'A2': FRONT_MEL + ('r/8 Cb6/8 Ab5/8 Gb5/8 F5/4 r/4 | D5/4 r/8 F5/8 G5/8 A5/8 Bb5/8 D6/8 | '
                       'E6/4. Db6/8 C6/4 Bb5/4 | A5/4 r/4 Gb5/8 F5/8 Eb5/8 C5/8 | F5/4 Eb5/8 Cb5/8 Bb4/4 C5/4'),
}
# the head out's second chorus (the backdoor chart): bars 1-8 as written, the punchline sinks over Bbm9 / Eb9, the
# riff's head alone in bar 11, a pickup into the tag
OUT2 = FRONT_MEL + ('r/8 C6/8 A5/8 F#5/8 Eb5/4 r/4 | Db6/4. C6/8 Bb5/8 Ab5/8 F5/4 | G5/4. F5/8 Db5/4 r/4 | '
                    'r/8 F5/8 Ab5/8 A5/8 r/2 | r/2 r/8 E5/8 G5/8 Bb5/8')
# intro: a dominant pedal (C9sus4 / C7b9) with the riff's blue figure, over Gb7#11 into the head (its #11 C5)
INTRO_MEL = ('r/8 F5/8 Ab5/8 A5/8 r/2 | r/8 Db6/8 Bb5/8 A5/8 G5/8 E5/8 r/4 | ' + RIFF.replace('A5/4', 'Bb5/4') + ' | '
             'r/8 Ab5/8 Fb5/8 Db5/8 C5/4 r/4')
# tag: the riff and its answer, the riff an octave down (softer), the minor plagal Bbm6 (Db Bb G) into F13
TAG_MEL = (f"{RIFF} | {ANSWER} | r/8 F4/8 Ab4/8 A4/8 r/8 C5/8 A4/4 | r/8 F5/8 Db5/8 C5/8 Bb4/4 G4/4")

# ------------------------------------------------------------------------------------------------ the solo
# three choruses written as lines (recipes/jazz-composition.md section 5): S1 the riff's blue figure displaced, short
# calls and answers in the middle register; S2 longer 8th lines across the bar lines over the walk-down chart, the
# tritone subs' own scales; S3 (backdoor chart) the riff figure an octave up, a chromatic run into Bbm9 and the
# piece's peak G6 (Eb9's 3rd), a scale descent home
SOLO = {
    'S1': ('r/2 r/8 F5/8 Ab5/8 A5/8 | Ab5/4. F5/8 D5/4 r/4 | r/4 {C5 Eb5 E5}/4 F5/4. A5/8 | '
           'G5/4 Eb5/8 D5/8 Eb5/8 C5/8 A4/4 | r/8 Db5/8 D5/8 F5/8 Ab5/4. G5/8 | r/8 F5/8 Ab5/8 G5/8 F5/4 r/4 | '
           'r/8 C5/8 A4/8 B4/8 C5/4 Eb5/8 E5/8 | F#5/4 G5/8 F#5/8 Eb5/8 C5/8 A4/4 | '
           'r/8 D5/8 E5/8 F5/8 A5/4 G5/4 | r/8 G5/8 A5/8 Bb5/8 D6/4. Db6/8 | C6/4. A5/8 {Eb5 D5 F#5}/4 A5/4 | '
           'G5/2 r/8 E5/8 G5/8 Bb5/8'),
    'S2': ('A5/4 r/8 C6/8 D6/8 C6/8 A5/8 Ab5/8 | D5/8 Db5/8 C5/8 Bb4/4. {D5 F5 Ab5}/4 | '
           'A5/4 C6/8 Eb6/8 D6/8 C6/8 A5/8 B5/8 | C6/4. Bb5/8 A5/8 G5/8 F5/8 Eb5/8 | '
           'D5/4 r/8 F5/8 Ab5/8 C6/8 B5/8 Bb5/8 | Ab5/8 G5/8 F5/8 E5/8 D5/4 r/8 C5/8 | '
           'E5/4 G5/8 A5/8 C6/4 B5/8 G5/8 | Gb5/8 F5/8 Eb5/8 Cb5/8 Bb4/4 {Db5 F5 Ab5}/4 | '
           'G5/8 A5/8 Bb5/4. A5/8 G5/8 F5/8 | E5/8 Gb5/8 Ab5/8 Bb5/8 C6/8 Db6/8 E6/4 | '
           'Eb6/4 D6/8 Db6/8 C6/4 Gb5/4 | F5/4. Eb5/8 Bb4/8 C5/8 Db5/8 E5/8'),
    'S3': ('F5/8 Ab5/8 A5/8 C6/8 Eb6/4 D6/8 C6/8 | Ab5/4 r/8 C6/8 D6/8 F6/8 Eb6/8 D6/8 | '
           'D6/4 C6/4 A5/8 B5/8 C6/8 Eb6/8 | D6/4 C6/8 Bb5/8 A5/4 {Ab5 G5 F5}/4 | '
           'D5/8 F5/8 Ab5/8 C6/8 D6/4 Db6/8 Eb6/8 | F6/4 E6/8 D6/8 B5/8 Ab5/8 G5/8 Bb5/8 | '
           'C6/8 Eb6/8 E6/8 F6/4. Eb6/8 C6/8 | A5/4 F#5/8 G5/8 A5/8 Bb5/8 B5/8 C6/8 | '
           'Db6/4 C6/8 Db6/8 F6/8 Eb6/8 F6/8 Gb6/8 | G6/2. F6/8 Eb6/8 | D6/4 C6/8 A5/8 C6/8 Bb5/8 A5/8 F#5/8 | '
           'G5/4 Bb5/8 A5/8 G5/8 E5/8 C5/4'),
}
REC: dict = {}


def _line(spec, bars):
    return notes(spec, length=bars * METER, transpose=SHIFT)


def _sym(s):
    """A chord symbol of the F sketch moved to the played key (SHIFT semitones, flat spelling)."""
    names = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']
    root = s[:2] if s[1:2] == 'b' else s[:1]
    return names[(names.index(root) + SHIFT) % 12] + s[len(root):]


def _beats(ch):
    return [(_sym(s), b * METER) for s, b in ch]


def _changes_str(ch):
    return ' '.join(f"{_sym(s)}:{b:g}" for s, b in ch)


def _triples(clip):
    return [(round(n.start, 4), round(n.dur, 4), n.pitch) for n in sorted(clip, key=lambda n: n.start)]


def tune() -> Tune:
    """The lead sheet as an endless Tune (same lead-sheet / tune.json format as the generator's)."""
    mel = {p: _triples(_line(MEL[p], 12)) for p in PARTS}
    return Tune(genre=G.name, seed=SEED, mood='blue', title=TITLE, key=KEY, mode=MODE, tempo=TEMPO,
                meter=METER, feel=FEEL, swing=SWING, form='blues', parts=list(PARTS),
                changes={p: _beats(CHANGES[p]) for p in PARTS}, melody=mel,
                motif=[n for n in mel['A1'] if n[0] < 2 * METER],
                intro={'changes': _beats(INTRO), 'melody': _triples(_line(INTRO_MEL, 4))},
                tag={'changes': _beats(TAG), 'melody': _triples(_line(TAG_MEL, 4))}, end_chord=_sym(END_CHORD),
                blocks=BLOCKS, retries=0, end_kind='cadenza', second='answer')


TUNE = tune()

LINES = {'head A1': (_line(MEL['A1'], 12), _beats(C1)), 'head A2': (_line(MEL['A2'], 12), _beats(C2)),
         'solo S1': (_line(SOLO['S1'], 12), _beats(C1)), 'solo S2': (_line(SOLO['S2'], 12), _beats(C2)),
         'solo S3': (_line(SOLO['S3'], 12), _beats(C3)), 'out A3': (_line(OUT2, 12), _beats(C3)),
         'intro': (_line(INTRO_MEL, 4), _beats(INTRO)), 'tag': (_line(TAG_MEL, 4), _beats(TAG))}


def check_melody() -> list:
    """The endless composer's melody checks: every head chorus in full, the solo / intro / tag lines for clashes."""
    k = Key(KEY)
    out = []
    for name, (clip, ch) in LINES.items():
        head = name.startswith(('head', 'out'))
        lo, hi = (note('Eb4'), note('Eb6')) if head else (note('C4'), note('G6'))
        out += [f"{name}: {i}" for i in melody_issues(_triples(clip), Harm(ch, set(k.pcs)), lo, hi, meter=METER)
                if head or 'clash' in i]
    return out


# ------------------------------------------------------------------------------------------------ the performance

def build() -> Song:
    for issue in check_melody():
        print('melody check:', issue)
    s = Song(TITLE, tempo=TEMPO, key=KEY, seed=SEED, tail=6, meter=(METER, 4))
    parts = {'A1': _changes_str(C1), 'A2': _changes_str(C2), 'A3': _changes_str(C3), 'S1': _changes_str(C1),
             'S2': _changes_str(C2), 'S3': _changes_str(C3), 'intro': _changes_str(INTRO), 'tag': _changes_str(TAG),
             'end': f"{_sym(END_CHORD)}:2"}
    intro, head, solo, out, tag, end = s.form('intro:4 head:A1,A2 solo:S1,S2,S3 out:A1,A3 tag:4 end:2', parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.band), swung lightly like `--swing 0.58`
    feel = jazz.Feel(TEMPO, ratio=SWING, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)
    lh = F['lh']
    mem = pianist.Memory()
    orn = dict(P['head'].get('ornaments') or {}, blues_crush=1.2)           # a blues pianist's crushed thirds
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=lh, lh_vel=56, style=F['style'], ornaments=orn, lh_answers=0.8)), record=REC, **k)

    # ---- intro: the dominant pedal in tempo, soft, the riff's blue figure; Gb7#11 into the head
    play(intro, _line(INTRO_MEL, 4), piano=dict(style='sparse', density=0.45, seed=11, lead_in=False,
                                               touch=(40, 78), lh_vel=44, section_end=True))

    # ---- head: the riff chorus plain, the walk-down chorus a shade stronger (its E6 the head's top)
    play(head, [_line(MEL[p], 12) for p in PARTS], piano=dict(
        seed=101, lead_in=True, fill=0.3,
        A1=dict(lead_in=False, touch=(46, 86), density=0.55),
        A2=dict(touch=(50, 94), density=0.6)))

    # ---- solo: three written choruses, harmonized more and more; fills only as answers / approaches / enclosures
    solo_fills = {'answer': 2.0, 'approach': 1.5, 'enclosure': 1.5, 'stabs': 1.2}
    play(solo, [_line(SOLO[p], 12) for p in ('S1', 'S2', 'S3')], piano=dict(
        seed=201, lead_in=True, lh_vel=60, fills=solo_fills,
        S1=dict(touch=(44, 84), density=0.35, devices={'single': 3.0, 'guide': 2.0, 'thirds': 0.5}),
        S2=dict(touch=(48, 90), density=0.5, devices={'guide': 2.0, 'single': 1.5, 'thirds': 1.5, 'sixths': 1.2}),
        S3=dict(touch=(56, 110), density=0.75, climax=True, doubles=0.8,
                devices={'octave': 3.0, 'locked': 1.0, 'drop2': 1.5, 'quartal': 0.5})))

    # ---- head out: the riff chorus near the head's level, the backdoor chorus sinks into the tag
    play(out, [_line(MEL['A1'], 12), _line(OUT2, 12)], piano=dict(
        seed=311, lead_in=True,
        A1=dict(touch=(50, 94), density=0.6),
        A3=dict(touch=(42, 82), density=0.45)))

    # ---- no hole between the sections (as perform.build): a sweep over the last chord where a bar is left empty
    for k, (boundary, sym) in enumerate(((solo.start, _sym('Gb7#11')), (out.start, _sym('C7b9')))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the riff, its answer, the riff an octave down, the minor plagal Bbm6; a short cadenza into the F13
    play(tag, _line(TAG_MEL, 4), pedal_end=end.start - 0.1, piano=dict(
        touch=(38, 76), style='ballad', density=0.45, seed=401, lead_in=True, lh='tenths', lh_vel=46,
        bpm=TEMPO * 0.9, section_end=False))
    perform._ending(s, b, TUNE, end, tag, METER, False, False, None)
    _lh_breath(b.comp, head.start, tag.start)
    return s


def _lh_breath(track, a: float, z: float, bars: int = 2) -> None:
    """The left hand breathes with the phrase: every `bars`-bar phrase an arc (x0.84 at its ends, x1.16 at 60 %), the
    bar's first attack leaned on, its off-beat answers lighter - the pianist's left hand plays its chords at a
    near-even level, which the dynamics ear reads as flat (the right hand has jazz.touch for this)."""
    span = bars * METER
    out = []
    for n in track._notes:
        if a - 1e-6 <= n.start < z - 1e-6:
            x = ((n.start - a) % span) / span
            arc = 0.84 + 0.32 * math.sin(math.pi * (x / 0.6 * 0.5 if x < 0.6 else 0.5 + (x - 0.6) / 0.4 * 0.5))
            arc *= 1.06 if (n.start - a) % METER < 0.1 else 0.94
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
                intro=_changes_str(INTRO), tag=_changes_str(TAG), end_chord=_sym(END_CHORD))
    (out_dir / 'tune.json').write_text(json.dumps(info, indent=1, ensure_ascii=False), encoding='utf-8')
    print(f"wrote {out_dir / 'leadsheet.txt'} and {out_dir / 'tune.json'}")


if __name__ == '__main__' and '--leadsheet' in sys.argv:
    write_leadsheet(Path(__file__).resolve().parent / 'out')
