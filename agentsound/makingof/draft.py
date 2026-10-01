"""The first draft of a song's film.py, generated from its facts - a starting point for the film director (an agent
or a person), not the final film: the arc is the generic one (wish, team, blueprint, tracks, performance, verdict,
what we tried, song, credits), the lines are the facts in template sentences, the scenes follow the genre / energy
plan. `python -m agentsound makingof songs/<slug> --draft` writes it; then make it the song's own film.

Also: loading a film.py (exec, like song.py) -> the Film."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

from . import story
from .film import Film
from .timeline import scene_plan


def _q(s: str) -> str:
    return repr(s)


def _line(ln, indent: str) -> str:
    fn = 'AR' if ln.voice == 'ar' else 'N'
    d = f", {_q(ln.direction)}" if ln.direction and ln.direction != story.DIRECTIONS.get('crisis-ar') else ''
    return f"{indent}{fn}({_q(ln.text)}{d}),"


def draft_source(facts: dict, *, n_excerpts: int = 3, episodes: list | None = None) -> str:
    """Python source of a film.py for the song (episodes: the before / after items history.py found)."""
    chs = {c.id: c for c in story.build(facts, n_excerpts)}
    title = facts['title']
    plan = scene_plan(facts)
    out = [f'"""The making-of of {title} - a DRAFT generated from the song\'s files',
           '(python -m agentsound makingof songs/%s --draft). Make it this song\'s film: find its real story in' % facts['slug'],
           'the logs (BRIEF.md log, AR.md, the players\' moves), choose the angle, the moments, the words and the scenes.',
           'Facts only: every line must say what the files say. Brief: roles/film-director.md."""', '',
           'from agentsound.makingof.film import AR, Episode, Excerpt, Film, Item, N', '', '',
           'def build(facts):', '    f = Film(facts)', '']
    looks = ', '.join(f"{_q(p['section'])}: {_q(p['scene'] + ('+hw' if p['highway'] else ''))}" for p in plan)
    out += ['    # one visual scene per section (nebula, ink, ring, grid, mandala, scope; +hw = the note highway)',
            f'    f.look(scenes={{{looks}}})', '']

    def chapter(call: str, c, extra: str = ''):
        out.append(f'    f.{call}(')
        for ln in c.lines:
            out.append(_line(ln, '        '))
        if extra:
            out.append(f'        {extra}')
        out.append('    )')
        out.append('')

    chapter('cold_open', chs['cold'])
    chapter('team', chs['team'])
    chapter('blueprint', chs['blueprint'])
    items = ',\n'.join(f"            Item({_q(it.name)}, {it.ids!r}, {it.at:.2f})" for it in chs['tracks'].items)
    chapter('tracks', chs['tracks'], f"items=[\n{items},\n        ]," if items else '')
    exs = []
    for ex in chs['performance'].excerpts:
        ls = ' '.join(_line(ln, '').rstrip(',') + ',' for ln in ex.lines)
        exs.append(f"            Excerpt({ex.start:.2f}, {ex.end:.2f}, {_q(ex.label)}, [{ls}]),")
    chapter('performance', chs['performance'], "excerpts=[\n" + '\n'.join(exs) + "\n        ]," if exs else '')
    crisis = chs['crisis']
    if episodes:        # the fixes are told bar for bar in 'tried': the verdict keeps the A&R's words only
        crisis.lines = [ln for ln in crisis.lines if ln.voice == 'ar' or 'went back' in ln.text]
    chapter('crisis', crisis)
    if episodes:
        eps = []
        for e in episodes:
            p = e['pairs'][0]
            u = f" {p['unit']}" if p['unit'] else ''
            before = f"AR({_q(docs_clip(e['issue'] + '.', 240))})"
            head = re.sub(r'\s*\([^)]*\)\s*$', '', e['fix'])
            fix_text = (f"{head}: {story._low(p['label'])}, {story._num(p['before'])} to "
                        f"{story._num(p['after'])}{u}.")
            after = f"N({_q(docs_clip(fix_text, 240))}, {_q(story.DIRECTIONS['crisis-fix'])})"
            eps.append(f"            Episode({e['n']}, before_lines=[{before}], after_lines=[{after}]),")
        out.append('    f.tried(')
        out.append(f"        N({_q('Here is what the A&R heard, and what the fix did, bar for bar.')}, "
                   f"{_q(story.DIRECTIONS['crisis'])}),")
        out.append('        episodes=[\n' + '\n'.join(eps) + '\n        ],')
        out.append('    )')
        out.append('')
    chapter('song', chs['song'])
    chapter('credits', chs['end'])
    out.append('    return f')
    return '\n'.join(out) + '\n'


def docs_clip(s: str, n: int) -> str:
    from .docs import clip
    return clip(s, n)


def load(film_py: Path, facts: dict) -> Film:
    """Run a film.py (build(facts) -> Film)."""
    name = 'agentsound_film_' + re.sub(r'\W', '_', film_py.parent.name)
    spec = importlib.util.spec_from_file_location(name, film_py)
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(film_py.parent))
    try:
        spec.loader.exec_module(mod)
    finally:
        try:
            sys.path.remove(str(film_py.parent))
        except ValueError:
            pass
    if not hasattr(mod, 'build'):
        raise ValueError(f"{film_py} must define build(facts) -> Film")
    film = mod.build(facts)
    if not isinstance(film, Film):
        raise ValueError(f"{film_py}: build() must return a makingof.film.Film, got {type(film).__name__}")
    return film


def load_source(src: str, facts: dict, where: Path) -> Film:
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(src, encoding='utf-8')
    return load(where, facts)
