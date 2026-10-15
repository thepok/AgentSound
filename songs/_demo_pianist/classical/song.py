"""Pianist A/B, piece 3: one endless classical-piano tune (seed 3, 'Reverie in E-flat major', 59 BPM, nocturne).
Build: python -m agentsound build songs/_demo_pianist/classical
The same notes before / after the pianist's expression rules (docs/PIANIST_RULES.md): out/ab_old.mp3, out/ab_new.mp3
(songs/_demo_pianist/README.md says how they were rendered)."""
from agentsound import endless

GENRE, SEED = 'classical-piano', 3
TUNE = endless.compose(endless.genre(GENRE), SEED, None, None)
ANALYSIS = {'profile': endless.genre(GENRE).band['profile']}
METADATA = endless.metadata(TUNE)


def build():
    return endless.song(TUNE)
