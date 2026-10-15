"""Set up and brief one blind new-age round's judges (the prompts stay the same from round to round).

    python songs/_blind/judge_newage.py ROUND JUDGE_ROOT     # -> JUDGE_ROOT/<judge>/{JUDGE.md, packets/}, prompts

Every judge gets an isolated folder with JUDGE_NEWAGE.md (as JUDGE.md) and a copy of packets_newage/ (as packets/),
nothing else; JUDGE_ROOT/<judge>/prompt.txt is the brief to hand the judge agent. The answer goes to
JUDGE_ROOT/verdicts/<judge>.md, scored by `score_round.py KEY_newage.json JUDGE_ROOT/verdicts --tells`.
"""
from __future__ import annotations

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
                     "look for template regularities shared by a subset of the pieces. Cite the numbers you count."),
    'pianist': ("You are a concert and session pianist who plays and records this repertoire. Judge as a player: "
                "whether the writing lies naturally under two hands, whether the phrasing, breaths, dynamics and "
                "pedal-like holds feel like a person shaping music, whether the left-hand figures and the "
                "right-hand line feel idiomatic, and what a real composer-pianist would never write."),
}
JUDGES = {'composerA': 'composer', 'composerB': 'composer', 'composerC': 'composer',
          'statistician': 'statistician', 'pianist': 'pianist'}


def prompt(name: str, folder: Path, out: Path) -> str:
    return (f"{LENS[JUDGES[name]]}\n\n"
            f"Your working folder is {folder.as_posix()}. Read {folder.as_posix()}/JUDGE.md first and follow it "
            f"exactly; then read every packet in {folder.as_posix()}/packets/. You may read ONLY those files: do not "
            f"open, list or search any other file or folder (no repository files, no KEY files, nothing outside "
            f"your working folder). Take your time and compare the packets with each other before deciding.\n\n"
            f"Write your complete answer, in JUDGE.md's answer format (every packet in alphabetical ID order, then "
            f"## Advice), to {out.as_posix()} with the Write tool. Reply with one line: done.")


def main() -> int:
    rnd, root = sys.argv[1], Path(sys.argv[2]).resolve()
    (root / 'verdicts').mkdir(parents=True, exist_ok=True)
    for name in JUDGES:
        d = root / name
        if d.exists():
            shutil.rmtree(d)
        (d / 'packets').mkdir(parents=True)
        shutil.copy(HERE / 'JUDGE_NEWAGE.md', d / 'JUDGE.md')
        for p in sorted((HERE / 'packets_newage').glob('*.txt')):
            shutil.copy(p, d / 'packets' / p.name)
        (d / 'prompt.txt').write_text(prompt(name, d, root / 'verdicts' / f"{name}.md"), encoding='utf-8')
        print(f"{rnd} {name}: {d}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
