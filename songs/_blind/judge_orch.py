"""Set up and brief one blind ORCHESTRA round's judges (the prompts stay the same from round to round).

    python songs/_blind/judge_orch.py ROUND JUDGE_ROOT     # -> JUDGE_ROOT/<judge>/{JUDGE.md, packets/}, prompts
    python songs/_blind/judge_orch.py ROUND JUDGE_ROOT --quality   # a quality round: JUDGE_ORCH_Q.md, 7 judges
    python songs/_blind/judge_orch.py ROUND JUDGE_ROOT --quality --panel P   # a paired round's panel (o2 on)

Every judge gets an isolated folder with JUDGE_ORCH.md (as JUDGE.md) and a copy of packets_orch/ (as packets/),
nothing else; JUDGE_ROOT/<judge>/prompt.txt is the brief to hand the judge agent. The answer goes to
JUDGE_ROOT/verdicts/<judge>.md, scored by `score_round.py KEY_orch.json JUDGE_ROOT/verdicts --tells`.
"""
from __future__ import annotations

import json
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
# (the QUALITY rounds, --quality: JUDGE_ORCH_Q.md rates every piece 1-10 - melody, harmony, form, development,
# orchestration, life, overall, memorable; seven judges as in the new-age rounds g12 on, lenses that know both the
# lyrical film idiom and the symphonic allegro: HUMAN_FEEDBACK 2026-10-16, the endless orchestra-symphonic genre)
LENS_Q = {
    'composer': ("You are an experienced concert and film composer who writes both lyrical orchestral pieces (Horner, "
                 "Portman, Desplat, Hisaishi) and symphonic movements in the classical-romantic tradition (the "
                 "overtures, allegros and scherzos of Beethoven, Mendelssohn, Dvorak, Smetana). Judge as a composer: "
                 "the themes and their development, harmony and modulation, the counter-lines, the form and its "
                 "climax, how each section's texture serves the music."),
    'statistician': LENS['statistician'][:-1] + "; your ratings follow from what you count.",
    'orchestrator': LENS['orchestrator'].replace("film and concert scores", "film scores and the symphonic repertoire"),
    'dramatist': ("You are a film, ballet and theatre composer. Judge as a dramatist: the piece's arc and pacing - "
                  "whether something happens, how the climax is prepared and whether it pays off what came before, "
                  "the contrast between sections (register, texture, harmony, energy, sudden dynamics), the "
                  "transitions, the proportions, and whether the ending feels earned. Rate every dimension with "
                  "that ear."),
    'melodist': ("You are a melodist (themes, hymn and folk tunes, the great symphonic mottos and second themes). "
                 "Judge the tunes first: whether you could hum the main theme or motto after one hearing, whether "
                 "its phrases breathe and answer each other, whether it comes back changed rather than copied, "
                 "whether the contrasting theme has a shape of its own. Rate every dimension with that ear."),
}
JUDGES_Q = {'composerA': 'composer', 'composerB': 'composer', 'composerC': 'composer',
            'composerD': 'dramatist', 'composerE': 'melodist',
            'statistician': 'statistician', 'orchestrator': 'orchestrator'}


def prompt(name: str, folder: Path, out: Path, quality: bool = False) -> str:
    if quality:
        return (f"{LENS_Q[JUDGES_Q[name]]}\n\n"
                f"Your working folder is {folder.as_posix()}. Read {folder.as_posix()}/JUDGE.md first and follow it "
                f"exactly; then read every packet in {folder.as_posix()}/packets/. You may read ONLY those files: do "
                f"not open, list or search any other file or folder (no repository files, no KEY files, nothing "
                f"outside your working folder). Take your time and compare the packets with each other before "
                f"rating.\n\n"
                f"Write your complete answer, in JUDGE.md's answer format (every packet in alphabetical ID order, "
                f"then ## Count, then ## Advice), to {out.as_posix()} with the Write tool. Reply with one line: done.")
    return (f"{LENS[JUDGES[name]]}\n\n"
            f"Your working folder is {folder.as_posix()}. Read {folder.as_posix()}/JUDGE.md first and follow it "
            f"exactly; then read every packet in {folder.as_posix()}/packets/. You may read ONLY those files: do not "
            f"open, list or search any other file or folder (no repository files, no KEY files, nothing outside "
            f"your working folder). Take your time and compare the packets with each other before deciding.\n\n"
            f"Write your complete answer, in JUDGE.md's answer format (every packet in alphabetical ID order, then "
            f"## Advice), to {out.as_posix()} with the Write tool. Reply with one line: done.")


def main() -> int:
    rnd, root = sys.argv[1], Path(sys.argv[2]).resolve()
    quality = '--quality' in sys.argv
    # (round o2, a paired round - make_packets_paired.py deal --orch: --panel P gives the judges that panel's
    # packets only, packets_orch/PANELS.json)
    panel = sys.argv[sys.argv.index('--panel') + 1] if '--panel' in sys.argv else None
    only = set(json.loads((HERE / 'packets_orch' / 'PANELS.json').read_text(encoding='utf-8'))[panel]) \
        if panel else None
    (root / 'verdicts').mkdir(parents=True, exist_ok=True)
    for name in (JUDGES_Q if quality else JUDGES):
        d = root / name
        if d.exists():
            shutil.rmtree(d)
        (d / 'packets').mkdir(parents=True)
        shutil.copy(HERE / ('JUDGE_ORCH_Q.md' if quality else 'JUDGE_ORCH.md'), d / 'JUDGE.md')
        for p in sorted((HERE / 'packets_orch').glob('*.txt')):
            if only is None or p.stem in only:
                shutil.copy(p, d / 'packets' / p.name)
        (d / 'prompt.txt').write_text(prompt(name, d, root / 'verdicts' / f"{name}.md", quality), encoding='utf-8')
        print(f"{rnd} {name}: {d}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
