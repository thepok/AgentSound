"""A/B: the strum demo's passage (same seed, same decisions) on the old sampled/steel_guitar (FreePats FSS). See
song.py for the set."""
from demo import STEEL, strum

ANALYSIS = {'profile': 'jazz'}


def build():
    return strum(STEEL, title='Acoustic strum (FSS steel)', gain_db=-9.2)   # loudness-matched to song.py
