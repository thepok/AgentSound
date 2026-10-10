"""Endless music generators: genres as data, one rule-based tune composer, the library's players, a quality gate.

    python -m agentsound endless jazz-piano --count 3 --mood late-night [--swing] [--play]

    from agentsound import endless
    tune = endless.compose(endless.genre('jazz-piano'), seed=7)       # the lead sheet (no LLM, deterministic)
    song = endless.song(tune)                                          # a Song played by pianist / soloist / ending
"""
from .composer import Tune, compose, melody_issues
from .genres import GENRES, Genre
from .genres import get as genre

__all__ = ['GENRES', 'Genre', 'Tune', 'compose', 'cover', 'genre', 'melody_issues', 'metadata', 'song']


def song(tune, **kw):
    """The Song of a tune (agentsound.endless.perform.build)."""
    from .perform import build
    return build(tune, **kw)


def metadata(tune) -> dict:
    """METADATA for a song.py (mp3 tags) of a tune."""
    from .perform import metadata as _m
    return _m(tune)


def cover(tune) -> dict:
    """COVER for a song.py of a tune."""
    from .perform import cover as _c
    return _c(tune)
