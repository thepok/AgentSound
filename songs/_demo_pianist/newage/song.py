"""Pianist A/B, piece 1: one endless new-age-piano tune (seed 5, 'Glass Postcards', E major, 73 BPM, flowing).
Build: python -m agentsound build songs/_demo_pianist/newage
The same notes before / after the pianist's expression rules (docs/PIANIST_RULES.md): out/ab_old.mp3, out/ab_new.mp3
(songs/_demo_pianist/README.md says how they were rendered)."""
from agentsound import endless

GENRE, SEED = 'new-age-piano', 5
TUNE = endless.compose(endless.genre(GENRE), SEED, None, None)
ANALYSIS = {'profile': endless.genre(GENRE).band['profile']}
METADATA = endless.metadata(TUNE)


def build():
    return endless.song(TUNE)
