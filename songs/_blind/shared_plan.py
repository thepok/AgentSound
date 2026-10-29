"""A paired round with ONE set plan for both codes (new-age round g16 on, the orchestra round o2 on): the plan drawn
once, every code renders it.

    # 1. the plan, by one code (its composer.set_plan; checked to compose alike after the JSON round trip)
    python songs/_blind/shared_plan.py plan CODE_ROOT SEED N PLAN.json [--genre G]
    # 2. per code: `endless GENRE --count N --seed SEED --out OUT ...` with that code's run.set_plan patched to
    #    return the plan (the candidates' seeds, best-of-N and the gates as the code has them)
    python songs/_blind/shared_plan.py run CODE_ROOT PLAN.json OUT --count N --seed SEED [--genre G] [--flag NAME]
        [endless args]          # --flag chroma / event / derive / fugue / tech / shape / pdiv / choir / choir2 / rank_gates: a code's module switches (FLAGS)
        [endless args]          # --flag chroma / event / derive / fugue / tech / shape / pdiv / choir / colour / rank_gates: a code's module switches (FLAGS)
    # or the endless CLI as it is (the code's own set plan), with the flags: e.g. round p-div's sets
    python songs/_blind/shared_plan.py cli CODE_ROOT [--flag NAME] piano --style new-age --count 8 --seed S --out OUT

CODE_ROOT is a checkout of the code (this repo, or a `git archive` of master); the script imports agentsound from it,
so one copy of this file serves every code. --genre: new-age-piano (default; `endless piano --style new-age`) or
orchestra-symphonic (round o2: the plan carries the set draws - layout, motto, development, proportions ...; a code
that does not know a draw ignores it, compose() reads the draws it has; round o3: a drawn VALUE the code's set table
does not offer - a new motto cell, a new intro kind - is dropped for that code, which draws its own: fit()). Round g15's paired result mixed plan changes
(its SET_SPREAD) with composition changes in five of eight slots - with one plan the halves differ by composition
only.
"""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path


def _genre_arg(argv: list) -> tuple:
    if '--genre' in argv:
        i = argv.index('--genre')
        return argv[i + 1], argv[:i] + argv[i + 2:]
    return 'new-age-piano', argv


def _notes(endless, composer, g, seed, slot):
    s = endless.song(composer.compose(g, seed, plan=slot))
    return sorted((round(x.start, 4), x.pitch, x.vel) for t in s.tracks.values() for x in getattr(t, '_notes', ()))


def plan(root: Path, seed: int, n: int, out: Path, genre: str) -> int:
    from agentsound import endless
    from agentsound.endless import composer, genres
    g = genres.get(genre)
    p = composer.set_plan(g, n, seed)
    back = json.loads(json.dumps(p))
    for j, (a, b) in enumerate(zip(p, back)):
        if _notes(endless, composer, g, seed + 37 * j, a) != _notes(endless, composer, g, seed + 37 * j, b):
            print(f"slot {j + 1}: the plan composes differently after JSON - not written")
            return 1
    out.write_text(json.dumps(p, indent=1) + '\n', encoding='utf-8')
    print(composer.describe_set(p))
    return 0


def fit(slot: dict, table: dict) -> tuple:
    """The slot as a code with the set-draw table `table` (genre.plan['set']) can compose it: a draw whose value the
    table does not offer is dropped (the code draws its own); returns (slot, the dropped keys)."""
    out, dropped = dict(slot), []
    for k, opts in table.items():
        if k not in out or not isinstance(opts, dict):
            continue
        v = out[k]
        if isinstance(v, dict):                                  # (the motto: one cell per family)
            keep = {f: c for f, c in v.items() if isinstance(opts.get(f), dict) and str(c) in map(str, opts[f])}
            if keep != v:
                dropped.append(k)
                out[k] = keep
                if not keep:
                    del out[k]
        elif str(v) not in map(str, opts) and not (k == 'skeleton' and isinstance(v, int)):
            dropped.append(k)
            del out[k]
    return out, dropped


FLAGS = {'chroma': "the orchestra-symphonic CHROMA_CADENCE on (symphony.CHROMA_CADENCE_ON)",
         'event': "the orchestra-symphonic CHROMA_EVENT on (symphony.CHROMA_EVENT_ON: the chromatic chord as an event "
                  "- the final tutti predominant, the chord chain into the retransition's pedal)",
         'derive': "the orchestra-symphonic DEV_WALK on (symphony.DEV_WALK_ON: the development as a planned walk through "
                   "the derivation space, the return's counter-line from it, the dev_own gate replaced by the graph's "
                   "metrics - genres.symphony_derive)",
         'nosetplan': "the orchestra-symphonic SET_PLAN off (genres.symphony_setplan(False); v4 is the default since round o22)",
         'setplan': "the orchestra-symphonic SET_PLAN on, v4 (genres.symphony_setplan: the set-level choices diverse "
                    "and memoryful - build gestures, the layered summit, contours, ending families, motto rhythm "
                    "families, the meter mix; v3: the shape by merging, the section textures with set memory, the "
                    "fade capped, no crisis arc, the climax at 0.7+; v4: a change at every merged join, the set's "
                    "memory on the mode / key, the realised bar plan, the endings' dynamic and the fragmentation's "
                    "ladder; apply BEFORE the set plan is drawn)",
         'setplan3': "the orchestra-symphonic SET_PLAN v3 (round o20's: genres.symphony_setplan(True, version=3))",
         'setplan2': "the orchestra-symphonic SET_PLAN v2 (round o19a's: genres.symphony_setplan(True, version=2))",
         'fugue': "the orchestra-symphonic FUGUE on (symphony.FUGUE_ON: the dev_fugato as a fugal exposition - subject, "
                  "tonal answer, counter-subject, entries over the choirs -, a modulating episode from a fragment and the "
                  "final entry; the joint voice-leading core voicing.cp_issues / counterline / repair; round o21: v2 - "
                  "the subject from the first theme's opening, a pedal / pad under the first entries, the dynamics "
                  "rising entry by entry, the counter-subject heard, the fast feels capped over the dance, the "
                  "subject back at the summit, the entry spacing drawn)",
         'nofugue': "the orchestra-symphonic FUGUE off (symphony.FUGUE = None: the old Writer.fugato; the default since round o21 is v2)",
         'fugue1': "the orchestra-symphonic FUGUE v1 (symphony.FUGUE_ON_V1: round o19b's fugato)",
         'polish': "the orchestra-symphonic POLISH on (genres.symphony_polish, round op1: the concertmaster louder, "
                   "no parade of solo blocks, the cello event on the theme; the guest's returns / coda / gestures "
                   "with set memory, the bells' hint, the guitar's brass climax; the orchestra leaves the sung "
                   "summit, the summit's texture with set memory, at most 2 summits per 8; the title's form label "
                   "with set memory; apply BEFORE the set plan is drawn)",
         'noshape3': "the orchestra-symphonic SHAPE3 + TECH2 off (genres.symphony_shape3(False); on by default since round o25)",
         'nocolour': "the orchestra-symphonic COLOUR off (genres.symphony_colour(False); on by default since round ox1)",
         'nosolo': "the orchestra-symphonic SOLO off (genres.symphony_solo(False); on by default since round os1)",
         'pumping': "reduce the automatic symphonic phrase arc (genres.symphony_pumping(True); opt-in)",
         'nopumping': "restore the original symphonic phrase arc (genres.symphony_pumping(False))",
         'nochoir': "the orchestra-symphonic CHOIR off (genres.symphony_choir(False); v2 on by default since round oc2)",
         'notech': "the orchestra-symphonic TECH off (genres.symphony_tech(False); on by default since round o23)",
         'tech': "the orchestra-symphonic TECH on (genres.symphony_tech: round o23's playing techniques - the palette "
                 "symphony.TECHNIQUES as events per piece, ranked with the set's memory, the band's mutes / col legno / "
                 "harmonics levels; apply BEFORE the set plan is drawn)",
         'shape': "the orchestra-symphonic MACRO on (genres.symphony_shape: round o24's macro shapes - the opening, "
                  "the climax's place / count / kind, the ending drawn per set slot with the whole set's memory - and "
                  "TECH v2: the pizzicato choir / col legno on the theme and the motto, the techniques' whole-set "
                  "memory, the harmonics' home, the harp glissando heard; apply BEFORE the set plan is drawn)",
         'tech2': "the orchestra-symphonic TECH v2 alone (genres.symphony_tech2: round o24b - 3 techniques a "
                  "piece, each featured at most twice a set, the pizzicato choir once per 3 slots, the trill's crown "
                  "once a set, the pizzicato choir / col legno on the theme and the motto, the harmonics on the soft "
                  "endings, the harp glissando into the climax with the build thinned; apply BEFORE the set plan)",
         'shape2': "the orchestra-symphonic SHAPE2 (genres.symphony_shape2: round o24b's macro shapes - the early / "
                   "mid climax's material moved, the loud / cut endings at the climax's level, the climax types' own "
                   "textures, the set's memory on the motto's rhythm, the first theme's texture and the pumping "
                   "bass's figures; with --flag tech2 for the techniques; apply BEFORE the set plan is drawn)",
         'shape3': "the orchestra-symphonic SHAPE3 (genres.symphony_shape3: round o25 - SHAPE2 with the aftermath "
                   "after an early / mid climax a second build and a rising theme return, the chorale climax with "
                   "the motto's rhythm and a walking bass, a shorter way into the late / cut climax, the cut's chords "
                   "in the motto's rhythm; with --flag tech2 for the techniques; apply BEFORE the set plan is drawn)",
         'pdiv': "the new-age-piano PIANO_DIVERSE on (genres.piano_diverse(True), round p-div: the score a gate and "
                 "the set's memory choosing among the near-ties - run.diverse_pick -, per piece the climax's left hand, "
                 "the peak's place and kind, the ending gesture and the interlude from the theme drawn - "
                 "perform.PIANO_DIVERSE_ON)",
         'choir': "the orchestra-symphonic CHOIR on (genres.symphony_choir: round oc1's real SATB choir - the "
                  "vocalset-choir pack - as events per piece: the summit, the lead-in, an a cappella, a halo, the coda; "
                  "the plan drawn with the set's memory; apply BEFORE the set plan is drawn)",
         'choir2': "the orchestra-symphonic CHOIR v2 on (genres.symphony_choir(True, v2=True), round oc2: the choir "
                   "sings the theme at the summit - in octaves or harmonised, the brass / woodwind doublings softer "
                   "under it -, the set's memory per gesture, the a cappella twice as likely, the halo and the coda "
                   "sing a phrase; apply BEFORE the set plan is drawn)",
         'solo': "the orchestra-symphonic SOLO on (genres.symphony_solo, round os1: the exposed woodwind / horn lines "
                 "on the solo players - orch.SOLOS -, a string solo event per piece with the set's memory, the "
                 "concertmaster on the violins I's soft cantilena; apply BEFORE the set plan is drawn)",
         'colour': "the orchestra-symphonic COLOUR on (genres.symphony_colour: round ox1's guest colours - an organ, a "
                   "classical guitar, a harpsichord, a celesta / glockenspiel or tubular bells per piece, the piece "
                   "built around it, drawn with the set's memory; apply BEFORE the set plan is drawn)",
         'rank_gates': "the symphony score's round-o12 ranking (genres.symphony_ranking(True): the construction-"
                       "guaranteed SYMPHONY_GATES weighted again)"}
"""`run --flag NAME` (repeatable): a code's module switches for a paired round (the code review's flags)."""


def _flags(rest: list) -> list:
    """Apply and strip the --flag NAME arguments (FLAGS) - the code must have them."""
    out, names = [], []
    it = iter(rest)
    for a in it:
        if a == '--flag':
            names.append(next(it))
        else:
            out.append(a)
    for name in names:
        if name == 'chroma':
            from agentsound.endless import symphony
            symphony.CHROMA_CADENCE = dict(symphony.CHROMA_CADENCE_ON)
        elif name == 'event':
            from agentsound.endless import symphony
            symphony.CHROMA_EVENT = dict(symphony.CHROMA_EVENT_ON)
        elif name == 'derive':
            from agentsound.endless import genres, symphony
            symphony.DEV_WALK = dict(symphony.DEV_WALK_ON)
            genres.symphony_derive(True)
        elif name == 'nosetplan':
            from agentsound.endless import genres
            genres.symphony_setplan(False)
        elif name in ('setplan', 'setplan2', 'setplan3'):
            from agentsound.endless import genres
            genres.symphony_setplan(True, version={'setplan2': 2, 'setplan3': 3}.get(name))
        elif name == 'fugue':
            from agentsound.endless import symphony
            symphony.FUGUE = dict(symphony.FUGUE_ON)
        elif name == 'nofugue':
            from agentsound.endless import symphony
            symphony.FUGUE = None
        elif name == 'fugue1':
            from agentsound.endless import symphony
            symphony.FUGUE = dict(symphony.FUGUE_ON_V1)
        elif name == 'polish':
            from agentsound.endless import genres
            genres.symphony_polish(True)
        elif name == 'noshape3':
            from agentsound.endless import genres
            genres.symphony_shape3(False)
            genres.symphony_tech2(False)
        elif name == 'nocolour':
            from agentsound.endless import genres
            genres.symphony_colour(False)
        elif name in ('pumping', 'nopumping'):
            from agentsound.endless import genres
            genres.symphony_pumping(name == 'pumping')
        elif name == 'nosolo':
            from agentsound.endless import genres
            genres.symphony_solo(False)
        elif name == 'nochoir':
            from agentsound.endless import genres
            genres.symphony_choir(False)
        elif name == 'notech':
            from agentsound.endless import genres
            genres.symphony_tech(False)
        elif name == 'tech':
            from agentsound.endless import genres
            genres.symphony_tech(True)
        elif name == 'shape':
            from agentsound.endless import genres
            genres.symphony_shape(True)
        elif name == 'tech2':
            from agentsound.endless import genres
            genres.symphony_tech2(True)
        elif name == 'shape2':
            from agentsound.endless import genres
            genres.symphony_shape2(True)
        elif name == 'shape3':
            from agentsound.endless import genres
            genres.symphony_shape3(True)
        elif name == 'pdiv':
            from agentsound.endless import genres
            genres.piano_diverse(True)
        elif name == 'choir':
            from agentsound.endless import genres
            genres.symphony_choir(True)
        elif name == 'choir2':
            from agentsound.endless import genres
            genres.symphony_choir(True, v2=True)
        elif name == 'solo':
            from agentsound.endless import genres
            genres.symphony_solo(True)
        elif name == 'colour':
            from agentsound.endless import genres
            genres.symphony_colour(True)
        elif name == 'rank_gates':
            from agentsound.endless import genres
            genres.symphony_ranking(True)
        else:
            raise SystemExit(f"--flag {name}: one of {', '.join(FLAGS)}")
        print(f"flag {name}: {FLAGS[name]}")
    import agentsound.endless.run as R
    if hasattr(R, 'SLOT_REROLLS') and '--rerolls' not in out:
        out += ['--rerolls', '0']        # (a slot failing the gate is skipped, not rerolled: dropped for both codes)
    return out


def run(root: Path, plan_file: Path, out: str, rest: list, genre: str) -> int:
    fixed_plan = json.loads(plan_file.read_text(encoding='utf-8'))
    os.chdir(root)
    rest = _flags(rest)
    import agentsound.endless.run as R
    from agentsound.endless import genres
    table = genres.get(genre).plan.get('set') or {}
    fitted = []
    for j, x in enumerate(fixed_plan):
        y, dropped = fit(x, table)
        if dropped:
            print(f"slot {j + 1}: this code has no {', '.join(f'{k}={x[k]!r}' for k in dropped)} - its own draw")
        fitted.append(y)
    fixed_plan = fitted

    def fixed(genre_, n, seed, mood=None, prev_key=None):
        if n != len(fixed_plan):
            raise SystemExit(f"--count {n} but the plan has {len(fixed_plan)} slots")
        return [dict(x) for x in fixed_plan]
    R.set_plan = fixed
    head = ['piano', '--style', 'new-age'] if genre == 'new-age-piano' else [genre]
    sys.argv = ['agentsound', 'endless'] + head + ['--out', out] + rest
    runpy.run_module('agentsound', run_name='__main__', alter_sys=True)
    return 0


def cli(root: Path, rest: list) -> int:
    """`endless ...` as the CLI runs it (the code's own set plan) with the code's --flag switches applied."""
    os.chdir(root)
    rest = _flags(rest)
    sys.argv = ['agentsound', 'endless'] + rest
    runpy.run_module('agentsound', run_name='__main__', alter_sys=True)
    return 0


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == 'cli':
        root = Path(sys.argv[2]).resolve()
        sys.path.insert(0, str(root))
        return cli(root, sys.argv[3:])
    genre, argv = _genre_arg(sys.argv)
    if len(argv) < 4 or argv[1] not in ('plan', 'run'):
        print(__doc__)
        return 2
    root = Path(argv[2]).resolve()
    sys.path.insert(0, str(root))
    if argv[1] == 'plan':
        return plan(root, int(argv[3]), int(argv[4]), Path(argv[5]), genre)
    return run(root, Path(argv[3]).resolve(), argv[4], argv[5:], genre)


if __name__ == '__main__':
    sys.exit(main())
