"""Orchestra player A/B, piece 1: songs/unbowed (Symphony in C minor, I.: an orch.Score on the symphony_orchestra).
Build: python -m agentsound build songs/_demo_orchestra_player/unbowed
The same notes before / after the orchestra's performance rules (docs/ORCHESTRA_RULES.md): out/ab_old.mp3,
out/ab_new.mp3 (songs/_demo_orchestra_player/README.md says how they were rendered)."""
import importlib.util
import sys
from pathlib import Path

_dir = Path(__file__).resolve().parents[2] / 'unbowed'
sys.path.insert(0, str(_dir))                     # unbowed's own score.py
_spec = importlib.util.spec_from_file_location('unbowed_song', _dir / 'song.py')
_unbowed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_unbowed)

ANALYSIS = _unbowed.ANALYSIS
METADATA = dict(_unbowed.METADATA)
MIX = _unbowed.MIX


def build():
    return _unbowed.build()
