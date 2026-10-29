"""Set up and brief one blind new-age round's judges (the prompts stay the same from round to round).

    python songs/_blind/judge_newage.py ROUND JUDGE_ROOT [--panel P]   # -> JUDGE_ROOT/<judge>/{JUDGE.md, packets/}

Every judge gets an isolated folder with JUDGE_NEWAGE.md (as JUDGE.md) and a copy of packets_newage/ (as packets/),
nothing else; JUDGE_ROOT/<judge>/prompt.txt is the brief to hand the judge agent. The answer goes to
JUDGE_ROOT/verdicts/<judge>.md, scored by `score_round.py KEY_newage.json JUDGE_ROOT/verdicts --tells`.
Round g3 on (the quality rounds: JUDGE_NEWAGE.md rates every piece; the old verdict brief JUDGE_NEWAGE_g1g2.md): the
fifth judge is the PERFORMANCE judge ('performer') instead of the pianist. Round g12 on: seven judges - two more
composer lenses, composerD the dramatist (the arc, the climax's preparation, contrast, the ending) and composerE the
melodist (the tune, its breath, the hook's returns, B's own hook, the sung high point); score_round.py also prints the
generated pieces relative to the references within each judge (rel_scores).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LENS = {
    'composer': ("You are an experienced composer and arranger of song-like solo piano music (Yiruma, Einaudi, "
                 "film and pop-classical piano). Judge as a composer: the melody's shape and memorability, how the "
                 "theme is developed between its statements, the harmony and its voice-leading, the form and its "
                 "climax, the left hand's choices per section."),
    'statistician': ("You are a statistician who detects machine-generated music by its distributions. Judge by "
                     "counting: compare the packets with each other on measurable features (copied bars between "
                     "sections, phrase lengths and rest positions, rhythm-cell variety, interval and repeated-note "
                     "rates, chord vocabulary and loop reuse, velocity / loudness statistics, section layouts) and "
                     "look for template regularities shared by a subset of the pieces. Cite the numbers you count; "
                     "your ratings follow from what you count."),
    'pianist': ("You are a concert and session pianist who plays and records this repertoire. Judge as a player: "
                "whether the writing lies naturally under two hands, whether the phrasing, breaths, dynamics and "
                "pedal-like holds feel like a person shaping music, whether the left-hand figures and the "
                "right-hand line feel idiomatic, and what a real composer-pianist would never write."),
    # (round g3 on: the PERFORMANCE judge - the hands' balance, the register, touch, pedal, rubato weigh most)
    'performer': ("You are a concert pianist and recording producer of this repertoire, the panel's PERFORMANCE "
                  "judge. Rate every dimension, but weigh what the hands do most: the balance between the hands "
                  "(per section in the analysis), the register (a singing right hand, high notes as rare events), "
                  "touch and dynamics (does the melody ride one line per phrase or is every note placed on its "
                  "own), pedal-like holds, rubato and tempo shaping, and whether the right hand voices its melody "
                  "with the other fingers - thirds, sixths, chords, inner voices - or plays one note at a time."),
    # (round g12 on: two more composer lenses, seven judges - the five-judge mean moved as much between rounds as
    # the generated set did; each a different composer's ear, not a third copy of the same one)
    'dramatist': ("You are a film and theatre composer who also releases solo piano albums. Judge as a dramatist: "
                  "the piece's arc and pacing - how the climax is prepared and whether it pays off what came "
                  "before, the contrast between sections (register, texture, harmony, energy), the transitions, "
                  "the proportions, and whether the ending feels earned rather than appended. Rate every dimension "
                  "with that ear."),
    'melodist': ("You are a songwriter and melodist (pop ballads, hymn and folk tunes, piano songs without words). "
                 "Judge the tune first: whether you could hum the theme after one hearing, whether its phrases "
                 "breathe and answer each other, whether the hook comes back changed rather than copied, whether "
                 "the contrasting section has a hook of its own, and whether the high point of the melody is "
                 "sung or merely loud and high. Rate every dimension with that ear."),
}
JUDGES = {'composerA': 'composer', 'composerB': 'composer', 'composerC': 'composer',
          'composerD': 'dramatist', 'composerE': 'melodist',
          'statistician': 'statistician', 'performer': 'performer'}


def prompt(name: str, folder: Path, out: Path) -> str:
    return (f"{LENS[JUDGES[name]]}\n\n"
            f"Your working folder is {folder.as_posix()}. Read {folder.as_posix()}/JUDGE.md first and follow it "
            f"exactly; then read every packet in {folder.as_posix()}/packets/. You may read ONLY those files: do not "
            f"open, list or search any other file or folder (no repository files, no KEY files, nothing outside "
            f"your working folder). Take your time and compare the packets with each other before rating.\n\n"
            f"Write your complete answer, in JUDGE.md's answer format (every packet in alphabetical ID order, then "
            f"## Count, then ## Advice), to {out.as_posix()} with the Write tool. Reply with one line: done.")


def main() -> int:
    rnd, root = sys.argv[1], Path(sys.argv[2]).resolve()
    # (round g14, a paired round - make_packets_paired.py: --panel P gives the judges that panel's packets only,
    # packets_newage/PANELS.json)
    panel = sys.argv[sys.argv.index('--panel') + 1] if '--panel' in sys.argv else None
    only = set(json.loads((HERE / 'packets_newage' / 'PANELS.json').read_text(encoding='utf-8'))[panel]) \
        if panel else None
    (root / 'verdicts').mkdir(parents=True, exist_ok=True)
    for name in JUDGES:
        d = root / name
        if d.exists():
            shutil.rmtree(d)
        (d / 'packets').mkdir(parents=True)
        shutil.copy(HERE / 'JUDGE_NEWAGE.md', d / 'JUDGE.md')
        for p in sorted((HERE / 'packets_newage').glob('*.txt')):
            if only is None or p.stem in only:
                shutil.copy(p, d / 'packets' / p.name)
        (d / 'prompt.txt').write_text(prompt(name, d, root / 'verdicts' / f"{name}.md"), encoding='utf-8')
        print(f"{rnd} {name}: {d}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
