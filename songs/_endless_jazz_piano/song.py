"""One tune of the endless jazz-piano generator as a normal song (full report + images for inspection).
Build: python -m agentsound build songs/_endless_jazz_piano

The endless loop itself: python -m agentsound endless jazz-piano [--count N] [--mood ...] [--swing] [--play]
(its tunes land in out/NNN-<title>/ next to this file; every tune.json names the seed that rebuilds it here).
Set SEED / MOOD / SWING / GENRE to the values in a tune.json to rebuild that tune with the whole image set.
"""
from agentsound import endless

GENRE = 'jazz-piano'
SEED = 11
MOOD = 'blue'           # None: rolled from the seed
SWING = None            # None / False: straight 8ths; True: the genre's swing ratio; 0.58: that ratio

TUNE = endless.compose(endless.genre(GENRE), SEED, MOOD, SWING)
ANALYSIS = {'profile': endless.genre(GENRE).band['profile']}
METADATA = endless.metadata(TUNE)
COVER = endless.cover(TUNE)


def build():
    print(TUNE.describe())
    return endless.song(TUNE)
