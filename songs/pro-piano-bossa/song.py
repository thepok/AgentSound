"""Folded Letter Bossa - a tender straight-eighth ABAC bossa for solo piano, composed by hand (the "pro" reference set
for the blind comparison with the endless jazz-piano generator). Build: python -m agentsound build songs/pro-piano-bossa
Lead sheet + tune.json for the judge (after a build): python songs/pro-piano-bossa/song.py --leadsheet

SOUND = the endless jazz-piano genre exactly (agentsound/endless/genres.py JAZZ_PIANO, the 'bossa' feel): the
band from agentsound.endless.perform.band (the solo_piano preset, the genre's master gain + the bossa feel's -1.5
dB), the same bossa left hand (rootless bossa comping + the root-fifth line 'R__f'), the intro rubato, section sweeps
and s.ending. Only the composition and its performance plan differ (BRIEF.md, ARRANGEMENT.md).

The tune: a hook that leaps a sixth up to the held third and sighs down to the major 7th; its sequence lifts onto the
bright II7 (G13: the B natural). B goes to the subdominant through its ii-V and sighs into Bbm6 (the minor iv) before
iii-VI-ii-V. A2 swaps A1's C13 for a sliding Gb7#11 (the surprise). C climbs Bbmaj9 - Eb7#11 - Am9 - Abdim7 to the
head's peak (F6 over the diminished chord), then cadences and quotes the hook's opening over the tonic. The solo is
written out: sparse in the middle register, rising lines through B, the hook's sequence up an octave in A2, the climax
in octaves over C (G6 over Am9), resolving down. The intro and the tag frame the tune with the same figure (the hook's
shape over IV, iv, ii); the tag lands on Gb7#11 and the last chord, F69, has the hook's G on top.
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
FEEL = 'bossa'
F, P, BD = G.feels[FEEL], G.plan, G.band
TITLE, KEY, MODE, TEMPO, METER, SWING, SEED = 'Folded Letter Bossa', 'F major', 'major', 116, 4, None, 7302

ANALYSIS = {'profile': BD['profile']}
METADATA = {'title': TITLE, 'artist': 'AgentSound', 'album': 'Pro Reference (composed)', 'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#6b3b4f', '#e8c4a0'], 'title': TITLE.lower(),
         'subtitle': 'AgentSound - Pro Reference (composed)', 'seed': SEED % 1000}

# ------------------------------------------------------------------------------------------------ the lead sheet
A_OPEN = [('Fmaj9', 2), ('G13', 2), ('Gm9', 1)]
CHANGES = {
    'A1': A_OPEN + [('C13', 1), ('Am7', 0.5), ('D7b9', 0.5), ('Gm9', 0.5), ('C9', 0.5)],
    'B': [('Cm9', 1), ('F13', 1), ('Bbmaj9', 1), ('Bbm6', 1), ('Am9', 1), ('D7b9', 1), ('Gm9', 1),
          ('C7sus4', 0.5), ('C7b9', 0.5)],
    'A2': A_OPEN + [('Gb7#11', 1), ('Fmaj9', 0.5), ('D7b9', 0.5), ('Gm9', 0.5), ('C7b9', 0.5)],
    'C': [('Bbmaj9', 1), ('Eb7#11', 1), ('Am9', 1), ('Abdim7', 1), ('Gm9', 1), ('C7sus4', 0.5), ('C7b9', 0.5),
          ('F69', 2)],
}
INTRO = [('Bbmaj9', 1), ('Bbm6', 1), ('Gm9', 1), ('C7b9', 1)]
TAG = [('Bbmaj9', 1), ('Bbm6', 1), ('Gm9', 1), ('Gb7#11', 1)]
END_CHORD = 'F69'
BLOCKS = {'A1': ['I_II7_ii', 'V_iii_VI_ii_V'], 'B': ['ii_V_IV_iv_iii_VI_ii_V'], 'A2': ['I_II7_ii', 'bII7_I_VI_ii_V'],
          'C': ['IV_bVII7#11_iii_biiio', 'ii_V_I']}

HOOK = 'r/8 C5/8 F5/8 A5/8~ A5/2 | G5/4 A5/8 E5/8~ E5/2'
A_FRONT = HOOK + ' | r/8 D5/8 G5/8 B5/8~ B5/2 | A5/4 B5/8 F5/8~ F5/2 | r/8 Bb4/8 D5/8 F5/8~ F5/4 A5/4'
MEL = {
    'A1': A_FRONT + ' | G5/4. E5/8~ E5/4 D5/4 | E5/4. C5/8~ C5/4 Eb5/4 | D5/2 r/8 E5/8 F5/8 G5/8',
    'B': ('Bb5/4. G5/8~ G5/2 | A5/4 G5/8 Eb5/8~ Eb5/2 | D5/4. F5/8 A5/4 C6/4 | Db6/2 C6/8 Bb5/8 G5/4 '
          '| C6/4. B5/8~ B5/2 | A5/4. F#5/8~ F#5/4 Eb5/4 | D5/4. F5/8~ F5/4 A5/4 | G5/2 E5/4 Db5/4'),
    'A2': A_FRONT + ' | Ab5/4. E5/8~ E5/4 C5/4 | A5/4. G5/8~ G5/8 F#5/8 Eb5/4 | D5/2 r/8 Bb4/8 Db5/8 E5/8',
    'C': ('F5/4. A5/8~ A5/2 | G5/4 A5/8 Db6/8~ Db6/2 | B5/4. E6/8~ E6/2 | F6/4. D6/8~ D6/4 B5/4 '
          '| A5/4. F5/8~ F5/2 | G5/4. F5/8~ F5/8 E5/8 Db5/4 | r/8 C5/8 F5/8 A5/8~ A5/2 | G5/4 A5/8 D5/8~ D5/2'),
}
FRAME = 'r/8 D5/8 F5/8 A5/8~ A5/2 | r/8 Db5/8 F5/8 G5/8~ G5/2 | r/8 Bb4/8 D5/8 F5/8~ '
INTRO_MEL = FRAME + 'F5/4 A5/4 | G5/4. E5/8~ E5/4 Db5/4'
TAG_MEL = FRAME + 'F5/2 | r/8 C5/8 E5/8 Ab5/8~ Ab5/2'
SOLO = {
    'A1': ('r/4 C5/8 F5/8~ F5/4 E5/4 | r/2 r/8 A4/8 C5/8 E5/8~ | E5/4 D5/4 B4/4 r/4 | r/8 F5/8 E5/8 D5/8 B4/4 G4/4 '
           '| r/4 Bb4/8 D5/8 F5/8 A5/8 G5/4 | r/8 E5/8 G5/8 Bb5/8 A5/4 r/4 '
           '| G5/8 E5/8 C5/8 A4/8 C5/8 Eb5/8 F#5/8 A5/8 | Bb5/4 A5/8 F5/8 E5/4 r/4'),
    'B': ('r/8 G4/8 Bb4/8 D5/8 Eb5/8 G5/8 Bb5/4 | A5/8 G5/8 Eb5/8 D5/8 C5/4 A4/4 | r/8 F5/8 A5/8 C6/8 D6/4 C6/8 A5/8 '
          '| Db6/4 Bb5/8 G5/8 F5/8 Db5/8 F5/4 | E5/8 G5/8 B5/8 C6/8 E6/4 D6/8 C6/8 '
          '| B5/8 A5/8 F#5/8 Eb5/8 C5/8 A4/8 F#4/4 | r/8 G4/8 Bb4/8 D5/8 F5/8 A5/8 Bb5/8 D6/8 '
          '| F6/4 C6/4 Bb5/8 G5/8 E5/8 Db5/8'),
    'A2': ('r/8 C5/8 F5/8 A5/8~ A5/4 C6/4 | E6/4. C6/8 A5/8 G5/8 E5/4 | r/8 D5/8 G5/8 B5/8~ B5/4 D6/4 '
           '| F6/4. E6/8 D6/8 B5/8 A5/8 F5/8 | Bb5/8 A5/8 F5/8 D5/8 Bb4/8 D5/8 F5/8 A5/8 '
           '| Bb5/8 C6/8 Db6/8 E6/8 Db6/4 Bb5/4 | A5/4 G5/8 E5/8 F#5/8 A5/8 C6/8 Eb6/8 '
           '| D6/4 Bb5/8 G5/8 E5/8 G5/8 Bb5/8 Db6/8'),
    'C': ('D6/4. F6/8~ F6/2 | Eb6/4 F6/8 Db6/8~ Db6/2 | C6/4. E6/8~ E6/4 G6/4 | F6/4 D6/8 B5/8 Ab5/8 F5/8 D5/4 '
          '| r/8 Bb4/8 D5/8 F5/8~ F5/4 A5/4 | G5/4. F5/8~ F5/8 E5/8 Db5/4 | C5/4. D5/8~ D5/2 | r/1'),
}
PARTS = ['A1', 'B', 'A2', 'C']
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
    return Tune(genre=G.name, seed=SEED, mood='tender', title=TITLE, key=KEY, mode=MODE, tempo=TEMPO,
                meter=METER, feel=FEEL, swing=SWING, form='ABAC', parts=list(PARTS),
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
        f"intro:{P['intro']} head:ABAC solo:ABAC out:A2,C tag:{P['tag']} end:{P['end']}", parts=parts)

    # ---- the band: exactly the endless jazz-piano setup (perform.build), straight 8ths with the piano's lay-back
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=METER)
    b = perform.band(s, G, FEEL, feel)             # the endless genre's sound, by construction
    mem = pianist.Memory()
    orn = P['head'].get('ornaments')
    play = lambda *a, **k: jazz.chorus(b, *a, memory=mem, bass=None, drums=None, defaults=dict(
        piano=dict(lh=None, lh_vel=54, style=F['style'], ornaments=orn)), record=REC, **k)

    def bossa_left(section, vel=1.0, seed=0, pedal_end=None):
        """The endless bossa left hand: rootless bossa comping + the root-fifth bass, both on the comp track."""
        comp = dict(F['comp'])
        roll = comp.pop('roll', None)
        comp['vel'] = comp.get('vel', 54) * vel
        play(section, None, piano=None, pedal_end=pedal_end,
             comp=dict(comp, answer=False, seed=seed, roll=roll, roll_seed=seed))
        blo, bhi = F['bass_vel']
        for i, part in enumerate(section.parts):
            line = part.prog.bass(pattern=F['bass_pattern'], rate='1/8', low='C2', vel=(blo + bhi) / 2 * vel,
                                  gate=0.85)
            b.comp.play(jazz.bass_touch(line, blo * vel, bhi * vel, accent='1-3', seed=seed + i), part)

    mel = {p: _line(MEL[p], 8) for p in PARTS}

    # ---- intro: the frame figure (the hook's shape over IV, iv, ii) rubato, the piano alone, tenths
    play(intro, _line(INTRO_MEL, 4), piano=dict(style='ballad', density=0.5, seed=11, lead_in=True, touch=(46, 86),
                                               lh='tenths', lh_vel=48, section_end=True))
    s.rubato(intro, depth=F['rubato'], phrase='lean')

    # ---- head: soft and singing, the C climbs to the head's peak (F6 over Abdim7)
    play(head, [mel[p] for p in PARTS], lh_pedal=False, piano=dict(
        seed=101, lead_in=True,
        A1=dict(lead_in=False, touch=(50, 90), density=0.5),
        B=dict(touch=(54, 98), density=0.6),
        A2=dict(touch=(52, 94), density=0.55),
        C=dict(touch=(56, 104), density=0.65)))
    bossa_left(head, 0.9, seed=151)

    # ---- solo: written out; single lines + guide tones -> 3rds / 6ths -> drop 2 -> octaves / locked at the climax
    play(solo, [_line(SOLO[p], 8) for p in PARTS], lh_pedal=False, piano=dict(
        seed=201, lead_in=True,
        A1=dict(touch=(50, 84), density=0.35, devices={'single': 3.0, 'guide': 2.0, 'thirds': 0.5}),
        B=dict(touch=(54, 92), density=0.5, devices={'guide': 2.0, 'single': 1.0, 'thirds': 1.5, 'sixths': 1.5}),
        A2=dict(touch=(60, 102), density=0.65, devices={'guide': 1.0, 'drop2': 2.0, 'quartal': 1.5, 'sixths': 1.0}),
        C=dict(touch=(70, 114), density=0.8, climax=True, doubles=0.8,
               devices={'octave': 3.0, 'locked': 2.0, 'drop2': 1.5, 'quartal': 0.5})))
    bossa_left(solo, 1.0, seed=221)

    # ---- the head out: A2 lightly paraphrased (as a singer would), the C as written, softer
    out_a2 = jazz.paraphrase(mel['A2'], seed=301, anticipate=0.25, delay=0.1, embellish=0.15, key=s.key)
    play(out, [out_a2, mel['C']], lh_pedal=False, piano=dict(
        seed=311, lead_in=True,
        A2=dict(touch=(50, 92), density=0.55),
        C=dict(touch=(50, 96), density=0.55)))
    bossa_left(out, 0.9, seed=341)

    # ---- no hole between the sections (as perform.build)
    for k, (boundary, sym) in enumerate(((solo.start, CHANGES['C'][-1][0]), (out.start, CHANGES['C'][-1][0]))):
        onsets = [n.start for n in b.piano._notes if n.start < boundary - 1e-6]
        last = max(onsets) if onsets else 0.0
        if boundary - last >= METER:
            dur = min(2.0, boundary - last - 0.5)
            b.piano.play(pianist.sweep(sym, dur, s.tempo_at(boundary - dur), low='D4', high='D6',
                                       direction='down' if k == 0 else 'up', vel=(50, 72), seed=351 + k),
                         boundary - dur)

    # ---- tag: the intro's frame again, landing on Gb7#11 (A2's surprise), ritardando; F69 with the G on top
    play(tag, _line(TAG_MEL, 4), pedal_end=end.start - 0.1, lh_pedal=False, piano=dict(
        touch=(44, 84), style='ballad', density=0.5, seed=401, lead_in=True, lh='tenths', lh_vel=48,
        bpm=TEMPO * 0.85, section_end=False))
    bossa_left(tag, 0.75, seed=431, pedal_end=end.start - 0.1)
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
