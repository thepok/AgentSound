"""Pianist A/B, piece 2: songs/pro-newage-lantern (a hand-written new-age rondo) played by the endless pianist.
Build: python -m agentsound build songs/_demo_pianist/lantern
The same notes before / after the pianist's expression rules (docs/PIANIST_RULES.md): out/ab_old.mp3, out/ab_new.mp3
(songs/_demo_pianist/README.md says how they were rendered)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'pro_newage_lantern', Path(__file__).resolve().parents[2] / 'pro-newage-lantern' / 'song.py')
_lantern = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lantern)

ANALYSIS = _lantern.ANALYSIS
METADATA = dict(_lantern.METADATA)


def build():
    return _lantern.build()
