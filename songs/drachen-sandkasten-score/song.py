"""Drachen im Sandkasten - underscore + stings UNDER the Drama 3 kids scene (scene_gaps_s11.wav, line times from
D:/Repos/drama3/out/scenes/sandkasten_lang/timeline_gaps_s11.json; the voices were assembled with longer gaps where a
sting sits). 120 bpm so 1 beat = 0.5 s; every cue is placed at picture seconds via T(line, 'start'|'end', offset).
Beds under speech stay quiet; stings play in the gaps. Same key/colour as songs/drachen-sandkasten (intro/outro).

Cues: sneaking celesta + contrabassoon (lines 2-3), timpani roll into "Vulkan" (4), orchestra hit on "Lava!" (5) +
tremolo, xylo run up (after 5), the dragon wakes (low tuba/contrabassoon, after 6), snare roll (before 9), comic
bassoon (after 9), sad clarinet (after 10) + warm strings (11), hook fragment (after 12), music-box baby dragon
(13-14), swamp tuba blubs (after 14), princess fanfare (after 16), hook on clarinet (after 17), parents: no music,
tiptoe (after 25), wah-wah trombone (after 26), glockenspiel goodbye (27).

Build: python -m agentsound build songs/drachen-sandkasten-score
"""
import json as _json
import math as _math
from pathlib import Path as _Path
from agentsound import *

METADATA = {'title': 'Drachen im Sandkasten (Underscore)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'underscore and stings for the kids sandbox audio scene'}
ANALYSIS = {'profile': 'film'}
COVER = {'style': 'synthwave', 'palette': 'sunset', 'title': 'DRACHEN SCORE', 'subtitle': 'AgentSound', 'seed': 4}

TL = _json.loads(_Path('D:/Repos/drama3/out/scenes/sandkasten_lang/timeline_gaps_s11.json').read_text(encoding='utf-8'))
LINES = TL['lines']
BPS = 2.0                                                       # beats per second at 120 bpm


def T(i, edge='start', off=0.0):
    """beat position of line i's start/end + offset seconds"""
    return (LINES[i][edge] + off) * BPS


def build() -> Song:
    s = Song('Drachen Score', tempo=120, key='F major', seed=4)
    s.section('scene', bars=_math.ceil(TL['total'] * BPS / 4) + 2, prog=s.prog('I'))
    s.hall(), s.plate()
    s.master.add(fx.limiter())

    celesta = s.track('celesta', 'sampled/celesta', gain_db=-6, pan=0.3)
    cbsn = s.track('contrabassoon', 'sampled/contrabassoon', gain_db=-8, pan=-0.2)
    timp = s.track('timpani', 'sampled/timpani_rolls', gain_db=-6)
    hit = s.track('hit', 'gm/orchestra_hit', gain_db=-6)
    trem = s.track('tremolo', 'sampled/strings_tremolo', gain_db=-16)
    xylo = s.track('xylo', 'sampled/xylophone', gain_db=-4, pan=0.4)
    tuba = s.track('tuba', 'sampled/tuba', gain_db=-5)
    snare = s.track('snare', 'sampled/orchestral_percussion', gain_db=-10)
    bsn = s.track('bassoon', 'sampled/bassoon', gain_db=-4, pan=-0.3)
    clar = s.track('clarinet', 'sampled/solo_clarinet', gain_db=-3, pan=-0.15)
    strings = s.track('strings', 'sampled/strings', gain_db=-15)
    box = s.track('musicbox', 'gm/music_box', gain_db=-8, pan=0.2)
    tpt = s.track('trumpet', 'sampled/solo_trumpet', gain_db=-5, pan=0.2)
    tbn = s.track('trombone', 'sampled/solo_trombone', gain_db=-4)
    glock = s.track('glock', 'sampled/glockenspiel', gain_db=-12, pan=-0.4)

    def at(track, notes, beat, octave=4, vel=1.0):
        track.play(s.motif(notes).clip(octave=octave).velocity(vel), beat)

    # 2-3 sneaking: celesta tiptoe (staccato 8ths, quiet) + contrabassoon footsteps on the beats
    tip = '1:1/8 r:1/8 3:1/8 r:1/8 5:1/8 r:1/8 4:1/8 r:1/8 | 3:1/8 r:1/8 2:1/8 r:1/8 1:1/8 r:1/8 r:1/4'
    for b in range(int(T(2, 'start', 0.3)), int(T(3, 'end')), 8):
        at(celesta, tip, b, octave=5, vel=0.55)
        at(cbsn, '1:1/8 r:3/8 5:1/8 r:3/8 | 1:1/8 r:3/8 5:1/8 r:3/8', b, octave=2, vel=0.6)
    # 4 Vulkan: timpani roll swelling through the gap into the line
    at(timp, '1:1/1 | 1:1/2', T(3, 'end', 0.1), octave=2, vel=0.75)
    # 5 "Lava!": orchestra hit on the first word, agitated tremolo under the line, xylo run up after it
    at(hit, '1:1/4', T(5, 'start', -0.05), octave=4, vel=1.0)
    at(hit, '5:1/4', T(5, 'start', -0.05), octave=3, vel=0.9)
    at(trem, '1:1/1 | 2:1/1', T(5, 'start'), octave=4, vel=0.8)
    at(trem, '3:1/1 | 4:1/1', T(5, 'start'), octave=4, vel=0.8)
    at(xylo, '1:1/16 2:1/16 3:1/16 4:1/16 5:1/16 6:1/16 7:1/16 8:1/16 | 8:1/4', T(5, 'end', 0.1), octave=5, vel=0.9)
    # after 6: the dragon wakes - two low, slow notes + low tremolo under line 7
    at(tuba, '1:1/2 r:1/4 5:1/2.', T(6, 'end', 0.15), octave=1, vel=0.9)
    at(cbsn, '1:1/2 r:1/4 5:1/2.', T(6, 'end', 0.15), octave=1, vel=0.8)
    at(trem, '1:1/1 | 1:1/1 | 1:1/1', T(7, 'start'), octave=3, vel=0.7)
    # before 9: snare roll + the hit (the tickle reveal), comic bassoon after 9
    at(snare, '1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/32 1:1/8',
       T(8, 'end', 0.05), octave=4, vel=0.7)
    at(bsn, '5:1/8 4:1/8 3:1/8 2:1/8 1:1/4 r:1/8 1:1/8 | 5:1/4', T(9, 'end', 0.1), octave=3, vel=0.9)
    # after 10: sad clarinet sigh; warm strings swell under 11 (comfort)
    at(clar, '3:1/4 2:1/4 1:1/2 | 7:1/2', T(10, 'end', 0.15), octave=4, vel=0.75)
    at(strings, '1:1/1 | 1:1/1 | 1:1/1', T(11, 'start'), octave=4, vel=0.7)
    at(strings, '3:1/1 | 4:1/1 | 5:1/1', T(11, 'start'), octave=4, vel=0.7)
    # after 12: hook fragment on xylophone (the castle-building joy)
    at(xylo, '1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4', T(12, 'end', 0.1), octave=5, vel=0.9)
    # 13-14 baby dragon: music box, tender, quiet under the whisper
    at(box, '5:1/4 3:1/4 1:1/4 3:1/4 | 4:1/4 2:1/4 7:1/2 | 1:1/2. r:1/4', T(13, 'end', 0.1), octave=5, vel=0.7)
    # after 14: swamp blubs (tuba staccato, low)
    at(tuba, '1:1/8 r:1/8 1:1/16 r:1/16 5:1/8 r:1/4 1:1/8', T(14, 'end', 0.1), octave=1, vel=0.9)
    # after 16: the princess fanfare
    at(tpt, '1:1/8 1:1/16 1:1/16 3:1/8 5:1/8 8:1/2', T(16, 'end', 0.1), octave=4, vel=1.0)
    # after 17: the hook on clarinet, out before Mama calls
    at(clar, '1:1/8 3:1/8 5:1/8 r:1/8 6:1/8 5:1/8 3:1/4', T(17, 'end', 0.1), octave=4, vel=0.9)
    # parents: no music; after 25 tiptoe, after 26 the wah-wah
    at(celesta, '1:1/8 r:1/8 3:1/8 r:1/8 5:1/8', T(25, 'end', 0.05), octave=5, vel=0.6)
    at(tbn, '3:1/4 2:1/4 1:1/4 7:1/2', T(26, 'end', 0.1), octave=3, vel=0.85)
    # 27 goodbye: glockenspiel tinkle under the whisper
    at(glock, '8:1/8 5:1/8 3:1/8 1:1/8 r:1/2', T(27, 'start', 0.5), octave=5, vel=0.6)
    return s
