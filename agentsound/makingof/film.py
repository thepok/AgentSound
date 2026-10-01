"""A song's making-of written as code: songs/<slug>/film.py composes the reusable chapters for THAT song.

    from agentsound.makingof.film import Film, N, AR, Item, Excerpt

    def build(facts):                       # facts: everything the song's files say (facts.py), read-only
        f = Film(facts)
        f.look(scenes={'intro': 'ink', 'finale': 'mandala'})     # scene per section of the song (optional)
        f.cold_open(N("It started with a wish, typed into a chat."))
        f.team(N("Six roles and four players made it."))
        f.blueprint(N("The blueprint: 19 sections in four parts."), show=('form', 'tempo', 'hook'))
        f.act('I Candlelight', N("Act one: a piano ballad by candlelight."), scene='ink', play=12)
        f.tracks(N("Sound design: every part its own sound."), items=[Item('Strings', ['violins1', 'cellos'], 295.9)])
        f.performance(excerpts=[Excerpt(227.1, 238.1, 'solo', [N("The solo: bends and slides.")])])
        f.tried(N("The A&R said revise."), episodes=[1, 2])      # before / after of the revision items
        f.crisis(AR("Verdict: revise."))
        f.song(N("And now, the song."))
        f.credits()
        return f

Every chapter method takes narration lines first (N(...) = the narrator, AR(...) = the A&R's voice; a plain str is
the narrator) and chapter options after. Chapters can repeat (several acts) and come in any order. Lines must say
only what the song's files say - the facts dict has it all (see `python -m agentsound makingof songs/<slug> --draft`
for a generated first draft built from them). The same chapter kinds render in every film; the story, the order,
the pacing, the moments, the words and the scenes are the song's own."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .story import Chapter, DIRECTIONS, Excerpt, Line, MAX_LINE, TrackItem as Item, VOICES  # noqa: F401

KINDS = ('cold', 'team', 'blueprint', 'act', 'tracks', 'performance', 'tried', 'crisis', 'song', 'end')
SCENES = ('nebula', 'ink', 'ring', 'grid', 'mandala', 'scope')


def N(text: str, direction: str = '', pause: int = 360) -> Line:
    """A narrator line (direction: a few words of delivery, e.g. 'Warm, quietly amazed.')."""
    return Line(text, 'narrator', direction, pause)


def AR(text: str, direction: str = 'Firm, clipped and uncompromising.', pause: int = 500) -> Line:
    """A line in the A&R's voice (its verdicts and issues, as written in AR.md)."""
    return Line(text, 'ar', direction, pause)


class FilmError(ValueError):
    pass


@dataclass
class Episode:
    """A before / after moment: n = the AR.md revision item; the clip positions come from the logs (history.py)
    unless given; lines: spoken before the BEFORE clip (the issue) and before the AFTER clip (the fix)."""
    n: int
    before_lines: list = field(default_factory=list)
    after_lines: list = field(default_factory=list)
    at: float | None = None


class Film:
    def __init__(self, facts: dict):
        self.facts = facts
        self.chapters: list[Chapter] = []
        self.scene_map: dict[str, str] = {}
        self.highway: set[str] = set()
        self._ids: dict[str, int] = {}

    # ---- helpers
    def _lines(self, lines, kind: str) -> list[Line]:
        out = []
        for ln in lines:
            if isinstance(ln, str):
                ln = Line(ln, 'narrator', DIRECTIONS.get(kind, ''))
            if not isinstance(ln, Line):
                raise FilmError(f"{kind}: narration lines are N('...') / AR('...') or str, got {ln!r}")
            if ln.voice not in VOICES:
                raise FilmError(f"{kind}: unknown voice {ln.voice!r} (known: {', '.join(VOICES)})")
            if len(ln.text) > MAX_LINE:
                raise FilmError(f"{kind}: a line of {len(ln.text)} characters (at most {MAX_LINE}: split it): "
                                f"{ln.text[:60]}...")
            if not ln.direction:
                ln.direction = DIRECTIONS.get(kind, '')
            out.append(ln)
        if out:
            out[-1].pause_ms = max(out[-1].pause_ms, 650)
        return out

    def _add(self, kind: str, title: str, lines, **opts) -> Chapter:
        n = self._ids.get(kind, 0) + 1
        self._ids[kind] = n
        c = Chapter(f"{kind}{n if n > 1 else ''}", title, self._lines(lines, kind))
        c.kind = kind
        c.opts = opts
        self.chapters.append(c)
        return c

    def _section_names(self) -> set[str]:
        return {s['name'] for s in self.facts['sections']}

    # ---- the look
    def look(self, *, scenes: dict | None = None, highway=()) -> 'Film':
        """Visual scene per section of the song ({'intro': 'ink', ...}: nebula, ink, ring, grid, mandala, scope;
        the rest follows the genre / energy plan) and the sections that get the note highway."""
        for sec, sc in (scenes or {}).items():
            if sec not in self._section_names():
                raise FilmError(f"look(): no section {sec!r} (sections: {', '.join(sorted(self._section_names()))})")
            base = sc.split('+')[0]
            if base not in SCENES:
                raise FilmError(f"look(): unknown scene {sc!r} (scenes: {', '.join(SCENES)})")
            self.scene_map[sec] = base
            if sc.endswith('+hw'):
                self.highway.add(sec)
        for sec in highway:
            self.highway.add(sec)
        return self

    # ---- chapters
    def cold_open(self, *lines, title: str = 'The wish') -> Chapter:
        """The user's wish typed out as chat bubbles, then the title card with the cover."""
        return self._add('cold', title, lines)

    def team(self, *lines, title: str = 'The team') -> Chapter:
        """The roles and the players who played, one card each (a line from the log / the players' move counts)."""
        return self._add('team', title, lines)

    def blueprint(self, *lines, title: str = 'The blueprint', show=('form', 'tempo', 'energy', 'hook')) -> Chapter:
        """The form (parts, sections, keys), the tempo curve, the energy per bar, the hook drawn as notes."""
        return self._add('blueprint', title, lines, show=list(show))

    def act(self, part, *lines, title: str | None = None, scene: str = 'nebula', highway: bool = False,
            play: float = 10.0, at=None) -> Chapter:
        """One part of the song told as an act: its sections, key, tempo and what happens in them, then `play`
        seconds of it (at = a section name or song seconds, default its first section) under its own scene."""
        secs = self.facts['sections']
        if isinstance(part, str) and part not in self._section_names():
            names = [s['name'] for s in secs if s.get('part') == part]
            if not names:
                raise FilmError(f"act(): {part!r} is neither a part ({', '.join(sorted({s['part'] for s in secs if s.get('part')}))})"
                                f" nor a section")
        else:
            names = [part] if isinstance(part, str) else list(part)
        bad = [n for n in names if n not in self._section_names()]
        if bad:
            raise FilmError(f"act(): unknown sections {bad}")
        if scene.split('+')[0] not in SCENES:
            raise FilmError(f"act(): unknown scene {scene!r}")
        first = next(s for s in secs if s['name'] == names[0])
        if at is None:
            start = first['start']
        elif isinstance(at, str):
            s = next((x for x in secs if x['name'] == at), None)
            if s is None:
                raise FilmError(f"act(): at={at!r} is not a section")
            start = s['start']
        else:
            start = float(at)
        return self._add('act', title or (first.get('part') or names[0]), lines, sections=names,
                         scene=scene.split('+')[0], highway=highway or scene.endswith('+hw'), start=start,
                         play=float(play))

    def tracks(self, *lines, items=None, title: str = 'Meet the tracks') -> Chapter:
        """Sound design, part by part: each Item's stems solo from its moment, then the band comes back in."""
        c = self._add('tracks', title, lines)
        its = items if items is not None else [Item(i['name'], list(i['ids']), i['at']) for i in self.facts['items']]
        known = {t['id'] for t in self.facts['tracks']}
        for it in its:
            bad = [i for i in it.ids if i not in known]
            if bad:
                raise FilmError(f"tracks(): unknown track ids {bad} (tracks: {', '.join(sorted(known))})")
            it.lines = self._lines(it.lines, 'tracks')
        c.items = list(its)
        return c

    def performance(self, *lines, excerpts=None, title: str = 'The performance') -> Chapter:
        """Excerpts of the song as track lanes, the players' moves popping on the frame they were played."""
        from .story import excerpt_line, pick_excerpts
        c = self._add('performance', title, lines)
        if excerpts is None:
            excerpts = pick_excerpts(self.facts, 3)
            for ex in excerpts:
                ex.lines = [N(excerpt_line(self.facts, ex), DIRECTIONS['performance'], 240)]
        for ex in excerpts:
            if ex.end <= ex.start:
                raise FilmError(f"performance(): an excerpt ends before it starts ({ex.start} - {ex.end})")
            ex.lines = self._lines(ex.lines, 'performance')
        c.excerpts = list(excerpts)
        return c

    def tried(self, *lines, episodes=(1, 2, 3), title: str = 'What we tried') -> Chapter:
        """Before / after: the A&R's issue, the judged version's bars, the fix, today's bars - loudness-matched,
        with the measured change. episodes: revision item numbers of AR.md or Episode(...)s."""
        c = self._add('tried', title, lines)
        eps = []
        for e in episodes:
            ep = e if isinstance(e, Episode) else Episode(int(e))
            ep.before_lines = self._lines(ep.before_lines, 'crisis')
            ep.after_lines = self._lines(ep.after_lines, 'crisis')
            eps.append(ep)
        c.episodes = eps
        return c

    def crisis(self, *lines, title: str = 'The verdict') -> Chapter:
        """The A&R's stamp, the ranked issues, the revision's before -> after numbers."""
        return self._add('crisis', title, lines)

    def song(self, *lines, title: str = 'The song', start: float = 0.0, length: float | None = None) -> Chapter:
        """The whole song (or `length` s from `start`) with the audio-reactive scenes and the section titles."""
        return self._add('song', title, lines, start=float(start), length=length)

    def credits(self, *lines, title: str = 'Credits') -> Chapter:
        """Made with AgentSound, the roles, the sample credits (CC-BY attributions), the narration's licence."""
        return self._add('end', title, lines)
