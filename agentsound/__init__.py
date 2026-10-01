"""AgentSound compose layer: write songs as Python, compile them to the engine's render JSON.

    from agentsound import *

    def build():
        s = Song('Night Drive', tempo=100, key='A minor', seed=3)
        verse = s.section('verse', bars=8)
        prog = s.prog('i VI III VII')
        s.track('bass', inst.va(), gain_db=-6).loop(prog.bass('octave', rate='1/16'), verse)
        return s

Build with `python -m agentsound build songs/<slug>`. Reference: docs/COMPOSE_API.md.
"""

from . import articulation, bassist, drummer, guitarist, heroes, hornist, jazz, mastering, midifx, mixer, patches, pianist, vamod
from .automation import CURVES, exp_ramp, fade, hold, per_section, point, ramp, riser, smooth_ramp, swell
from .humanize import (GROOVES, Groove, accent, crescendo, decrescendo, groove, humanize, jitter, swing,
                       vel_jitter)
from .midifx import ARPEGGIATE_MODES, CHORD_SHAPES
from .modulation import LFO_SHAPES, Mod, envelope, follow, gate, lfo, sample_hold, steps
from .patches import FX, Instrument, Layer, Patch, fx, inst, layer
from .patterns import (ARP_MODES, BASS_STYLES, DRUMS, Clip, Motif, Note, arp, as_clip, bassline, beats, chords,
                       crash, dotted, drum, drums, euclid, grid, melody, snare_roll, tom_fill, triplet)
from .heroes import hero
from . import notation
from .notation import Line, Phrases, notes, phrases
from .song import Bus, Section, Song, Track
from .theory import (PROGRESSIONS, SCALES, VOICINGS, Chord, ComposeError, Key, Progression, chord, hz, note,
                     note_name, pc, scale, voice, voice_lead)

__version__ = '1.0.0'

__all__ = [
    # song
    'Song', 'Section', 'Track', 'Bus', 'ComposeError',
    # theory
    'note', 'note_name', 'pc', 'hz', 'scale', 'SCALES', 'Key', 'Chord', 'chord', 'Progression', 'PROGRESSIONS',
    'voice', 'voice_lead', 'VOICINGS',
    # patterns
    'Note', 'Clip', 'Motif', 'as_clip', 'beats', 'dotted', 'triplet', 'DRUMS', 'drum', 'drums', 'grid', 'euclid',
    'arp', 'ARP_MODES', 'bassline', 'BASS_STYLES', 'chords', 'melody', 'snare_roll', 'tom_fill', 'crash',
    # MIDI effects: Clip methods (clip.arpeggiate(...), .strum, .echo, ...), also functions in midifx
    'midifx', 'ARPEGGIATE_MODES', 'CHORD_SHAPES',
    # feel
    'humanize', 'jitter', 'vel_jitter', 'swing', 'groove', 'Groove', 'GROOVES', 'crescendo', 'decrescendo', 'accent',
    # automation (steps({beat: v}) and lfo(start, end, lo, hi) still make points)
    'CURVES', 'point', 'ramp', 'exp_ramp', 'smooth_ramp', 'hold', 'steps', 'per_section', 'swell', 'riser', 'fade',
    'lfo',
    # modulators (node.modulate(target, mod))
    'Mod', 'LFO_SHAPES', 'gate', 'follow', 'envelope', 'sample_hold',
    # sounds
    'Patch', 'Instrument', 'FX', 'fx', 'inst', 'patches', 'vamod',
    # layered instruments: inst.stack(layer(...), layer(...)), Patch.layered(...)
    'layer', 'Layer',
    # played, not triggered: articulations, legato, expression, vibrato (articulation.perform ...)
    'articulation',
    # a jazz pianist's hands: named moves (pianist.trill, .tremolo, .gliss ...) and the arranger (pianist.arrange)
    'pianist',
    # a drummer's hands and feet: grooves per style and section, budgeted fills, crashes, builds, stops
    # (drummer.arrange(song, style='rock', kit=b.drums).play(b.drums); drummer.tom_run, .build, .flam_fill ...)
    'drummer',
    # a bass player's hands: named moves (bassist.slide, .approach, .fill ...) and the arranger (bassist.arrange)
    'bassist',
    # a guitarist's hands: fretboard shapes, strums, picking, lead moves (guitarist.arrange, guitarist.lead)
    'guitarist',
    # the mastering engineer: match the finished mix to a reference / the genre, check it, master it
    # (mastering.match(...).render(), mastering.apply(s, ...) - the snippet a plan prints - mastering.check(...))
    'mastering',
    # THE hero wrapper: hero(s.track('lead', 'sampled/solo_violin'), family='strings', bed=[pad]) - the hero sound
    # (the shared chain voiced per family) + its mix rules (bed duck / carve, dips, rides, echo throws), logged
    'hero', 'heroes',
    # the mix engineer: role targets, auto-mix from the report, findings (mixer.plan / .auto / .check, the MIX dict)
    'mixer',
    # the wind player: breath inside held notes, air-coupled vibrato, mic technique (hornist.arrange(...).place(t, at))
    'hornist',
    # notation: one compact text format for note data - notes('C5/8 Eb5 G5/4. | ...'), phrases(a1=..)('a1 a2+2d'),
    # notation.format(clip) back to text (hold('C3 G3 E4', 8) - the chord - is automation.hold with pitches)
    'notation', 'notes', 'phrases', 'Line', 'Phrases',
]
