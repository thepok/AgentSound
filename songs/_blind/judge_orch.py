"""Set up and brief one blind ORCHESTRA round's judges (the prompts stay the same from round to round).

    python songs/_blind/judge_orch.py ROUND JUDGE_ROOT     # -> JUDGE_ROOT/<judge>/{JUDGE.md, packets/}, prompts

Every judge gets an isolated folder with JUDGE_ORCH.md (as JUDGE.md) and a copy of packets_orch/ (as packets/),
nothing else; JUDGE_ROOT/<judge>/prompt.txt is the brief to hand the judge agent. The answer goes to
JUDGE_ROOT/verdicts/<judge>.md, scored by `score_round.py KEY_orch.json JUDGE_ROOT/verdicts --tells`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

LENS = {
    'composer': ("You are an experienced film and concert composer of lyrical orchestral music (the register of "
                 "James Horner, Rachel Portman, Alexandre Desplat, Joe Hisaishi, Thomas Newman and Morricone's lyrical "
                 "scores). Judge as a composer: the theme and its development, harmony and cadences, the counter-"
                 "melodies, the form and its climax, how each section's texture serves the music."),
    'statistician': ("You are a statistician who detects machine-generated music by its distributions. Judge by "
                     "counting: compare the packets with each other on measurable features (copied bars between "
                     "sections, phrase lengths and rest positions, rhythm-cell variety, interval and repeated-note "
                     "rates, chord vocabulary, the number of roles per bar and how it changes, which roles carry the "
                     "melody, doubling intervals, note-length distributions per role, '%' repeats, section layouts) "
                     "and look for template regularities shared by a subset of the pieces. Cite the numbers you "
                     "count."),
    'orchestrator': ("You are a professional orchestrator and conductor who prepares and conducts film and concert "
                     "scores every week (you have orchestrated for composers in this idiom and read scores at sight). "
                     "Judge as an orchestrator and conductor: whether every part lies well on its instrument (range, "
                     "sweet spot, breathing, idiomatic figures), spacing and voice-leading of the inner parts, "
                     "doublings by register, balance (would the melody be heard?), colour changes and their timing, "
                     "the density curve and the climax, the dynamics plan - and what a real orchestrator would never "
                     "write."),
}
JUDGES = {'composerA': 'composer', 'composerB': 'composer', 'composerC': 'composer',
          'statistician': 'statistician', 'orchestrator': 'orchestrator'}


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
        shutil.copy(HERE / 'JUDGE_ORCH.md', d / 'JUDGE.md')
        for p in sorted((HERE / 'packets_orch').glob('*.txt')):
            shutil.copy(p, d / 'packets' / p.name)
        (d / 'prompt.txt').write_text(prompt(name, d, root / 'verdicts' / f"{name}.md"), encoding='utf-8')
        print(f"{rnd} {name}: {d}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
