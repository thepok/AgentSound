"""Orchestra player A/B, piece 2: songs/_bands/film_orchestra ("Ascension", the film_orchestra preset demo: every
part through orch.perform). Build: python -m agentsound build songs/_demo_orchestra_player/film
The same notes before / after the orchestra's performance rules (docs/ORCHESTRA_RULES.md): out/ab_old.mp3,
out/ab_new.mp3 (songs/_demo_orchestra_player/README.md says how they were rendered)."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    'film_orchestra_demo', Path(__file__).resolve().parents[2] / '_bands' / 'film_orchestra' / 'song.py')
_film = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_film)

ANALYSIS = _film.ANALYSIS
METADATA = dict(_film.METADATA)


def build():
    return _film.build()
