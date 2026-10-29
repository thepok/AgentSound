"""Ab in die Berge! - the music cues of the audio drama. The cues live in berg.py (one Song each);
song.py builds the cue named by $BERG_CUE (default 'outro'). Render every cue: python songs/ab-in-die-berge/render_all.py

Build one: BERG_CUE=intro python -m agentsound build songs/ab-in-die-berge --out songs/ab-in-die-berge/out/intro
"""
import os as _os

from berg import CUES

ANALYSIS = {'profile': 'film'}
METADATA = {'title': 'Ab in die Berge! (Hoerspiel-Musik)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'music cues for the kids audio drama Ab in die Berge'}


def build():
    return CUES[_os.environ.get('BERG_CUE', 'outro')]()
