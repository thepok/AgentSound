"""Window on Barrow - a late-night C-minor AABA for solo piano, composed by hand (the "pro" reference set for the blind
comparison with the endless jazz-piano generator). Build: python -m agentsound build songs/pro-piano-latenight
Lead sheet + tune.json for the judge (after a build): python songs/pro-piano-latenight/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound/endless/genres.py JAZZ_PIANO, the 'straight' feel, swing 0.6
like `endless jazz-piano --swing 0.6`): the band from agentsound.endless.perform.band (the solo_piano preset, the
genre's master gain), the same intro rubato, section sweeps and s.ending. Only the composition and its performance plan
differ (BRIEF.md, ARRANGEMENT.md).

The tune: a hook that rises in two widening steps (G C Eb D -> Ab C Eb G F) and leans on the #11 (D over Ab7#11), a
bridge that turns the hook into Eb major, darkens to Ebm9 and lifts to Dbmaj7#11 (the Neapolitan: the head's peak)
before the tritone fall to G7alt; A3 cadences through the tritone sub (Dm7b5 Db7#11 Cm). The solo is written out:
the hook displaced and quiet, call and response sequenced up, a bridge of rising lines, the hook in octaves at the top
(G6 over Bb13 = the one climax), a resolution down. The head out from the bridge, A3 thinned to its hook, a tag that
states the hook twice (the second an octave up) and ends on its signature note D on the minor-major chord.
"""
import json
import sys
from pathlib import Path

if __name__ == '__main__':
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentsound import jazz, notes, pianist
from agentsound.endless import Tune, genre as _genre
from agentsound.endless import perform
from agentsound.endless.perform import end_clips
from agentsound.song import Song

G = _genre('jazz-piano')
FEEL = 'straight'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Window on Barrow', 'C minor', 'minor', 100, 4, 0.6, 7301

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#1f3b57', '#d9a441'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the lead sheet
# chords per part: (symbol, bars)
A_OPEN = [('Cm9', 1), ('Ab7#11', 1), ('Fm9', 1), ('Bb13', 1), ('Ebmaj9', 1), ('Abmaj7', 1)]
CHANGES = {
    'A1': A_OPEN + [('Dm7b5', 1), ('G7alt', 1)],
    'A2': A_OPEN + [('Dm7b5', 0.5), ('G7b9', 0.5), ('Cm9', 0.5), ('C7b9', 0.5)],
    'B': [('Fm9', 1), ('Bb13', 1), ('Ebmaj9', 2), ('Ebm9', 1), ('Ab13', 1), ('Dbmaj7#11', 1), ('G7alt', 1)],
    'A3': A_OPEN + [('Dm7b5', 0.5), ('Db7#11', 0.5), ('CmMaj9', 1)],
}
INTRO = [('Abmaj7#11', 1), ('G7b9', 1), ('Abmaj7#11', 1), ('G7b9', 1)]
TAG = [('Abmaj7#11', 1), ('G7b9', 1), ('Abmaj7#11', 1), ('Dm7b5', 0.5), ('Db7#11', 0.5)]
END_CHORD = 'CmMaj9'
BLOCKS = {'A1': ['i_bVI7#11_iv_bVII', 'III_bVI_ii_Valt'], 'A2': ['i_bVI7#11_iv_bVII', 'III_bVI_ii_V_to_iv'],
          'B': ['iv_bVII_III_iii_bVI_bII_Valt'], 'A3': ['i_bVI7#11_iv_bVII', 'III_bVI_ii_subV_iMaj']}

# the melody (notation: absolute pitches, 8ths swing by the feel). The hook = A1 bars 1-2.
HOOK = 'r/4 G4/8 C5/8 Eb5/4. D5/8~ | D5/2 C5/8 Bb4/8 C5/4'
A_FRONT = (HOOK + ' | r/8 Ab4/8 C5/8 Eb5/8 G5/4. F5/8 | F5/2 Eb5/8 D5/8 G5/4 '
           '| r/8 Bb5/8 G5/8 F5/8 D5/4 Bb4/4')
MEL = {
    'A1': A_FRONT + ' | C5/4. Eb5/8 G5/2 | F5/4. Eb5/8 D5/4 C5/4 | B4/2. r/4',
    'A2': A_FRONT + ' | C5/4. Eb5/8 G5/4 F5/4 | Ab5/4. G5/8 F5/4 Ab4/4 | Eb5/2 r/8 E5/8 G5/8 Bb5/8',
    'B': ('Ab5/2. G5/8 F5/8 | G5/4. F5/8 D5/2 | Bb5/2. G5/8 F5/8 | r/4 Bb4/8 Eb5/8 G5/4. F5/8~ '
          '| F5/2 Db5/8 Eb5/8 Gb5/4 | F5/8 Gb5/8 Ab5/8 Bb5/8 C6/2 | Eb6/4. C6/8 G5/2 | F5/4. Eb5/8 B4/4 Ab4/4'),
    'A3': A_FRONT + ' | C5/4. Eb5/8 G5/2 | F5/4. Ab5/8 G5/4 F5/4 | Eb5/1',
}
INTRO_MEL = ('r/4 G5/8 C6/8 Eb6/4. D6/8~ | D6/2 C6/8 Ab5/8 B5/4 | r/4 G5/8 C6/8 Eb6/4 D6/4 '
             '| Ab5/4 F5/4 D5/4 B4/4')
TAG_MEL = 'r/4 G4/8 C5/8 Eb5/4. D5/8~ | D5/2 C5/8 Ab4/8 B4/4 | r/4 G5/8 C6/8 Eb6/4. D6/8~ | D6/4 C6/4 B5/4 G5/4'
# the head out: the bridge as written, A3 thinned to its hook (space, the hook's D left ringing)
OUT_A3 = ('r/4 G4/8 C5/8 Eb5/4. D5/8~ | D5/1 | r/4 Ab4/8 C5/8 Eb5/4. G5/8~ | G5/2. r/4 '
          '| r/8 Bb5/8 G5/8 F5/8 D5/2 | C5/4. Eb5/8 G5/2 | F5/4. Ab5/8 G5/4 F5/4 | Eb5/1')
# the written-out solo chorus (AABA): statement -> call / response -> rising bridge -> the hook in octaves -> down
SOLO = {
    'A1': ('r/2 r/8 G4/8 C5/8 Eb5/8~ | Eb5/4 D5/4 r/2 | r/4 Ab4/8 C5/8 Eb5/8 G5/8 F5/4 | r/2 D5/8 F5/8 G5/4 '
           '| Bb4/8 D5/8 F5/8 G5/8 Bb5/4 A5/8 G5/8 | F5/8 Eb5/8 C5/8 G4/8 Bb4/4 C5/4 '
           '| r/8 D5/8 F5/8 Ab5/8 C6/4 Bb5/8 Ab5/8 | G5/8 F5/8 Eb5/8 Db5/8 B4/4 r/4'),
    'A2': ('r/4 C5/8 D5/8 Eb5/8 G5/8 Bb5/4 | Ab5/8 Gb5/8 Eb5/8 C5/8 D5/2 | r/4 Eb5/8 F5/8 Ab5/8 C6/8 Bb5/4 '
           '| Ab5/8 F5/8 D5/8 Bb4/8 G5/2 | r/8 Bb4/8 D5/8 F5/8 A5/4 G5/4 | {C6 Bb5 G5}/4 Eb5/4 F5/8 G5/8 C5/4 '
           '| D5/8 F5/8 Ab5/8 C6/8 B5/8 Ab5/8 F5/8 D5/8 | Eb5/4. D5/8 E5/8 G5/8 Bb5/8 Db6/8'),
    'B': ('C6/4 Ab5/8 G5/8 F5/8 Eb5/8 C5/8 Ab4/8 | r/8 G4/8 A4/8 Bb4/8 C5/8 D5/8 F5/8 G5/8 '
          '| Bb5/4. G5/8 F5/8 G5/8 Bb5/8 D6/8 | C6/4 Bb5/4 r/8 Bb4/8 Eb5/8 G5/8 '
          '| Gb5/4 F5/8 Eb5/8 Db5/8 Bb4/8 Gb5/8 F5/8 | Eb5/8 F5/8 Gb5/8 Ab5/8 Bb5/8 C6/8 Eb6/8 F6/8 '
          '| Eb6/4. C6/8 G5/8 Ab5/8 C6/8 Eb6/8 | Ab5/8 B5/8 Db6/8 Eb6/8 F6/4 r/4'),
    'A3': ('r/4 G5/8 C6/8 Eb6/4. D6/8~ | D6/2 C6/8 Bb5/8 C6/4 | r/8 Ab5/8 C6/8 Eb6/8 F6/4. Eb6/8 '
           '| F6/4 Eb6/8 D6/8 G6/2 | Bb5/8 G5/8 F5/8 D5/8 Eb5/8 F5/8 G5/4 | C5/4. Bb4/8 C5/8 Eb5/8 G5/4 '
           '| F5/4 D5/4 B4/4 G4/4 | C5/2. r/4'),
}
PARTS = ['A1', 'A2', 'B', 'A3']
REC: dict = {}                                           # section:part -> the pianist's Arrangement


def _line(spec, bars):
    return notes(spec, length=bars * METER)


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


def build() -> Song:
    s = Song(TITLE, tempo=TEMPO, key=KEY, seed=SEED, tail=6, meter=(METER, 4))
    parts = {p: _changes_str(CHANGES[p]) for p in PARTS}
    parts.update(A=parts['A1'], intro=_changes_str(INTRO), tag=_changes_str(TAG), end=f"{END_CHORD}:{P['end']}")
    intro, head, solo, out, tag, end = s.form(
        f"intro:{P['intro']} head:AABA solo:AABA out:B,A3 tag:{P['tag']} end:{P['end']}", parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.build), swung like `--swing 0.6`
    feel = jazz.Feel(TEMPO, ratio=SWING, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)             # the endless genre's sound, by construction
    lh = F['lh']                                             # 'shell': solo piano, the root in the left hand
    mem = pianist.Memory()                                   # one ornament budget for the whole tune
    orn = P['head'].get('ornaments')
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=lh, lh_vel=54, style=F['style'], ornaments=orn)), record=REC, **k)
    mel = {p: _line(MEL[p], 8) for p in PARTS}

    # ---- intro: the hook's head an octave up over Abmaj7#11 / G7b9, rubato, ballad touch (piano alone)
    play(intro, _line(INTRO_MEL, 4), piano=dict(style='ballad', density=0.5, seed=11, lead_in=True, touch=(44, 84),
                                               lh='tenths', lh_vel=48, section_end=True))
    s.rubato(intro, depth=F['rubato'], phrase='lean')

    # ---- head: a soft first statement, A2 a little more, the bridge opens up (its Dbmaj7#11 the head's peak)
    play(head, [mel[p] for p in PARTS], piano=dict(
        seed=101, lead_in=True,
        A1=dict(lead_in=False, touch=(48, 88), density=0.5),
        A2=dict(touch=(50, 92), density=0.55),
        B=dict(touch=(54, 102), density=0.7),
        A3=dict(touch=(50, 94), density=0.6)))

    # ---- solo: written out, harmonized more and more - single lines + guide tones, then 3rds / 6ths, then drop 2 /
    # quartal, the last A in octaves / locked hands (climax=True) at the top, then down to a long C
    play(solo, [_line(SOLO[p], 8) for p in PARTS], piano=dict(
        seed=201, lead_in=True, lh_vel=56,
        A1=dict(touch=(50, 84), density=0.35, devices={'single': 3.0, 'guide': 2.0, 'thirds': 0.5}),
        A2=dict(touch=(54, 92), density=0.5, devices={'guide': 2.0, 'single': 1.5, 'thirds': 1.5, 'sixths': 1.2}),
        B=dict(touch=(60, 102), density=0.65, devices={'guide': 1.5, 'drop2': 2.0, 'quartal': 1.5, 'sixths': 1.0}),
        A3=dict(touch=(70, 116), density=0.8, climax=True, doubles=0.8,
                devices={'octave': 3.0, 'locked': 2.0, 'drop2': 1.5, 'quartal': 0.5})))

    # ---- the head out from the bridge, then A3 thinned to its hook, softer
    play(out, [mel['B'], _line(OUT_A3, 8)], piano=dict(
        seed=311, lead_in=True,
        B=dict(touch=(54, 100), density=0.65),
        A3=dict(touch=(46, 86), density=0.45, style='ballad')))

    # ---- no hole between the sections (as perform.build): a sweep over the last chord where a bar is left empty
    for k, (boundary, sym) in enumerate(((solo.start, CHANGES['A3'][-1][0]), (out.start, CHANGES['A3'][-1][0]))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the hook twice (the second an octave up), ballad, ritardando; the end on CmMaj9 with the 9th (D, the
    # hook's leaning note) on top
    play(tag, _line(TAG_MEL, 4), pedal_end=end.start - 0.1, piano=dict(
        touch=(42, 82), style='ballad', density=0.5, seed=401, lead_in=True, lh='tenths', lh_vel=48,
        bpm=TEMPO * 0.85, section_end=False))
    lh_end, rh_end = end_clips(END_CHORD, METER)
    s.ending(end, chords=[(b.comp, lh_end, 70), (b.piano, rh_end, 80, 0.25)],
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
