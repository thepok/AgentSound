"""The singer: a SUNG lead vocal with lyrics, driven from the score - a player with micro-performance like the
hornist, rendered by a licensed DiffSinger voicebank (agentsound.voicebank) and played back as audio on a track.

User feedback (recipes/HUMAN_FEEDBACK.md): realism first; never "a child pressing key by key". A singer does not
step from pitch to pitch on the beat with a flat voice: the consonants come BEFORE the beat so the vowel lands on it,
long notes hold the vowel and grow a late vibrato, the voice scoops into phrase openers and leaps, glides between
notes, falls off phrase ends, breathes audibly in the gaps, gets softer and breathier when quiet and tighter when
loud, and phrases dynamically (touch arcs).

    from agentsound import singer
    vox = singer.sing(s, melody, 'Hold - on to the night, we were young', at=verse, voice='hanami', style='pop',
                      seed=3)                       # creates track 'vocal' (or pass a track made with singer.voice())
    print(vox.summary(), vox.budget)                # the moves it sang / what the budget dropped
    hero(vox.track, family='vocal', bed=[pad], competitors=[keys])     # the vocal chain + mix rules (heroes)
    singer.double(vox, pan=-0.6); singer.double(vox, pan=0.6)          # re-rendered doubles (other takes)
    singer.harmony(vox, steps=2, key='C major')                        # a third above, sung again (not shifted)

The line: a Clip, a notation Line or a notation string (agentsound.notation: its ^scoop ^fall ^doit ^bend ^vib
^shake gestures become the singer's moves at those notes, ^peak notes its hook peaks). The lyrics: one token per
note (agentsound.lyrics: words take one note per syllable, '-' melisma, '_' hold, to-geth-er, word{ph ...}, ','
phrase marks).

MOVES (MOVES; logged in .moves, budgeted song-wide with a Memory like the hornist's):
  consonants  placed BEFORE the beat: the onset cluster ends where the vowel starts (on the beat, plus the style's
              timing feel); its length is the voicebank duration model's own prediction (x style 'cons'), squeezed to
              at most `cons_share` of the note before; a word-final consonant links onto a vowel-initial next word
              ('hold on' -> 'hol-don') in legato
  hold        the vowel holds through a long note; the coda closes at its end
  diction     word-final consonants are sung and audible: they close the word at the END of its last note (after a
              run / hold), never shorter than a minimum per class (DICTION: stops, sibilants, nasals ...; a legato
              cluster is never squeezed to nothing); a stop before a rest gets a short silent closure and a released
              burst (a faded release vowel: "out" -> ou-t(h), not an unreleased ou(t)); the phrase-end release /
              taper / fall act on the vowel and end where the coda starts, the coda keeps the vowel's level (+ a few dB
              of consonant lift, a vocal engineer's clip-gain ride). singer.diction() reports codas that end too short
  glide       portamento between notes: an S-curve of 40-180 ms starting before the next onset (faster in a melisma),
              a small overshoot on leaps up that settles
  scoop       into phrase openers, leaps up and hook peaks: starts 40-120 cents flat and rises (big ones: SPICE)
  vibrato     late-onset (after ~0.3 s), growing over ~0.5 s, 5-6 Hz with a player's wobble; deeper on peaks
  fall / doit at phrase ends (SPICE budget: every `spice_every` bars at most)
  release     the phrase end: the air runs out (-8 dB over ~120 ms) and the pitch sags a little
  swell / messa_di_voce / taper    the air over held peaks and long notes; accents: note-to-note dynamics from the
              velocities (humanize.touch arcs)
  breath      an audible breath (the voicebank's AP) in every gap long enough (>= 0.25 s): deeper before long phrases
  colour      the voice mode follows the dynamics: soft passages blend in the bank's soft mode (breathier), loud /
              high ones its power mode (tension) - per frame
  timing      a style's lay-back and a correlated human jitter on the vowel onsets
  drift       slow pitch drift of a few cents (nobody holds a pitch like an oscillator)
  mic_pull    on a long held vowel she slowly pulls back from the mic after the onset: a few dB quieter by its end
              (shaped), less proximity bass, a touch more room; leaning back in for the word-final consonant (MIC_PULL:
              on by default for 'jazz' / 'ballad', sing(mic_pull=True) for pop / rock; budgeted; written as automation
              after the vocal compressor when the song compiles - the takes stay the same)
EXPRESSION (on top of the moves; per style, sing(back_phrase=, ornament=, messa_di_voce=, emphasis=)):
  back_phrase whole phrases laid back against the band (pop / rock: also pushed ahead), caught up on a landing note
  ornament    a melody's repeats embellished (grace, turn, run, blue note, upper neighbour, anticipation)
  messa       messa di voce on held peaks: the voice mode and the level after the compressor swell and recede
  emphasis    the lyrics' *word* leaned into, (( ... )) sung intimate and close; 'auto': the title words
moves=False sings the same notes and words robotically (flat pitch steps, consonants on the beat, no breaths, one
level, one voice mode): the A/B baseline.

Rendering happens when the song compiles (a compile hook: the tempo map is final then), batched per voicebank into two
WSL calls (duration prediction, then synthesis), cached by a hash of everything that shapes a phrase in
<song folder>/samples/vocals/<voice>/ (with SOURCE.json: the credits find the voicebank's licence there). One WAV per
phrase (breath + consonants included) is a sampler zone; one note triggers it at the right moment.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import sys

from dataclasses import dataclass, field
from pathlib import Path

from . import gesture as G
from . import lyrics as _lyr
from . import voicebank as _vb
from .budget import Budget
from .patterns import Clip, as_clip, seed_int
from .theory import ComposeError, Key

__all__ = ['STYLES', 'MOVES', 'FORMAT', 'DICTION', 'MIC_PULL', 'TUNE', 'PRISM', 'Memory', 'Vocal', 'Prism', 'voice', 'sing',
           'double', 'harmony', 'prism', 'mouth', 'chops', 'Chops', 'CHOP', 'chops_lines', 'tune_curve', 'render',
           'phrase_notes', 'check', 'diction', 'report_lines', 'log_lines', 'mic_lines', 'SingerError']

FORMAT = 5                      # bump when the rendering below changes (new cache keys)
MOVES = ('consonants', 'hold', 'diction', 'glide', 'scoop', 'vibrato', 'fall', 'doit', 'release', 'swell',
         'messa_di_voce', 'taper', 'accents', 'breath', 'colour', 'timing', 'drift', 'link', 'mic_pull')

_CLASS = {**{p: 'stop' for p in ('p', 'b', 't', 'd', 'k', 'g')}, 'ch': 'affricate', 'jh': 'affricate',
          **{p: 'sibilant' for p in ('s', 'z', 'sh', 'zh')}, **{p: 'fricative' for p in ('f', 'v', 'th', 'dh', 'hh')},
          **{p: 'nasal' for p in ('m', 'n', 'ng')}, 'l': 'liquid', 'r': 'liquid', 'w': 'glide', 'y': 'glide',
          # German symbols (lyrics.DE_CONSONANTS)
          'q': 'stop', 'ts': 'affricate', 'pf': 'affricate', 'cc': 'fricative', 'x': 'fricative', 'l1': 'liquid',
          'rh': 'liquid'}
DICTION = {
    # class: (min s before a rest, min s in legato, max s before a rest, warn below s, lift dB rest, lift dB legato)
    'stop':      (0.060, 0.045, 0.090, 0.040, 6.0, 3.0),
    'affricate': (0.080, 0.055, 0.160, 0.050, 3.0, 1.5),
    'sibilant':  (0.100, 0.060, 0.200, 0.050, 2.0, 1.0),
    'fricative': (0.080, 0.050, 0.180, 0.040, 3.0, 1.5),
    'nasal':     (0.070, 0.050, 0.250, 0.035, 0.0, 0.0),
    'liquid':    (0.060, 0.040, 0.250, 0.030, 0.0, 0.0),
    'glide':     (0.040, 0.030, 0.200, 0.025, 0.0, 0.0),
}
"""Word-final consonants (codas) per class: the shortest a coda is sung before a rest / in a legato cluster, the
longest a coda before a rest may get (a stop held longer renders as an unreleased closure), the length under which
singer.diction() warns, and the consonant lift (dB over the vowel's own level) before a rest / in legato."""
CLOSURE_S = 0.035               # the silent closure before a final stop (rest): the model then releases the burst
RELEASE = {'unvoiced': (0.04, 6.0, -14.0, 0.0), 'voiced': (0.025, -10.0, -26.0, -8.0)}
"""The released burst of a final stop before a rest: a short release vowel after it (RELEASE_VOWEL) - length s, gain
from / to (dB vs the word's vowel), and a fade over the stop's own last 35 ms (dB). Unvoiced p t k: the vowel only
carries the aspiration (ou-t(h)); voiced b d g: short and low, the stop's voiced tail faded, so it never becomes a
sung schwa (loud-uh). Measured on Hanami: the burst of a phrase-final t went from -51 dBFS / unreleased to -30 dBFS."""
RELEASE_VOWEL = 'ah'
_VOICED_STOPS = ('b', 'd', 'g')
ONSET_MIN_S = 0.03              # an onset consonant in a legato cluster is never squeezed below this
LEGATO_SHARE = 0.6              # a legato cluster may take up to this share of the note before it to keep its minimums


def _cls(p: str) -> str:
    return _CLASS.get(p, 'glide')


SR = 44100
HOP = 512
HYBRID_SCOOP = 0.6
"""pitch='hybrid': the player's scoops x this (the voicebank's pitch model has its own approach into a note)."""
FR = HOP / SR                   # one acoustic frame: 11.6 ms


class SingerError(ComposeError):
    """A singer problem (a ComposeError)."""


STYLES = {
    'pop': dict(vel=(66, 108), late_ms=6.0, jitter_ms=9.0, cons=1.0, speed=1.0, cons_share=0.45,
                glide_ms=75.0, melisma_glide=0.55, overshoot_ct=14.0,
                scoop_first=0.45, scoop_leap=0.6, scoop_peak=0.8, scoop_ct=70.0, scoop_ms=120.0,
                vib_other=0.7, vib_peak=0.95, vib_ct=26.0, peak_vib_ct=38.0, vib_hz=5.5, vib_delay=0.32,
                vib_grow=0.5, vib_min_s=0.55, wobble=0.15,
                fall=0.22, doit=0.03, fall_semis=-2.2, release=0.75, taper=0.5, swell=0.55, messa=0.0,
                accent=0.12, breath_db=-4.0, breath_min_s=0.25, drift_ct=5.0,
                power=0.55, soft=0.55, base_power=0.0, base_soft=0.0, pitch_power=0.03,
                spice_every=2, link=True, steps=24),
    # the calm, intimate styles (HUMAN_FEEDBACK "Vocals": "im Jazz-Song ist die Stimme viel zu aufgeregt, sollte
    # ruhiger sein"): the soft mode as the base and the power mode only on the loudest peaks, few small scoops (and the
    # pitch model's own approach / wobble damped: expr, model_vib), a slow, narrow vibrato that starts late and only on
    # long notes, no falls / doits, small swings, smooth legato; SUNG SOFT ("leiser singen lassen und dann nachtraeglich
    # lauter machen": every model in the soft mode alone, the level back by the zone's make-up) and LAID BACK ("sie
    # klingt gerusht": the vowels ~30-40 ms behind the beat, a phrase's first ~50 ms - with ~75 ms of consonants before
    # the vowel the syllable's P-centre lands on the beat instead of ~20 ms ahead of it)
    'jazz': dict(vel=(60, 88), late_ms=34.0, jitter_ms=5.0, cons=1.05, speed=0.9, cons_share=0.4,
                 glide_ms=110.0, melisma_glide=0.7, overshoot_ct=3.0,
                 scoop_first=0.12, scoop_leap=0.15, scoop_peak=0.2, scoop_ct=40.0, scoop_ms=110.0,
                 vib_other=0.35, vib_peak=0.75, vib_ct=16.0, peak_vib_ct=24.0, vib_hz=4.6, vib_delay=0.6,
                 vib_grow=0.8, vib_min_s=0.9, wobble=0.1,
                 fall=0.0, doit=0.0, fall_semis=-1.2, release=0.9, taper=0.6, swell=0.3, messa=0.2,
                 accent=0.07, breath_db=-4.0, breath_min_s=0.25, drift_ct=4.0,
                 power=0.6, soft=0.5, base_power=0.0, base_soft=1.0, pitch_power=0.0,
                 spice_every=8, link=True, steps=24,
                 expr=0.45, model_vib=0.4, base_core=0.6, power_knee=0.35, sing_soft=True, late_first_ms=16.0,
                 pcentre_ms=2.0),
    'ballad': dict(vel=(58, 92), late_ms=30.0, jitter_ms=6.0, cons=1.08, speed=0.92, cons_share=0.4,
                   glide_ms=105.0, melisma_glide=0.65, overshoot_ct=4.0,
                   scoop_first=0.15, scoop_leap=0.2, scoop_peak=0.25, scoop_ct=45.0, scoop_ms=120.0,
                   vib_other=0.4, vib_peak=0.8, vib_ct=18.0, peak_vib_ct=26.0, vib_hz=4.8, vib_delay=0.55,
                   vib_grow=0.75, vib_min_s=0.85, wobble=0.12,
                   fall=0.0, doit=0.0, fall_semis=-1.2, release=0.9, taper=0.65, swell=0.4, messa=0.3,
                   accent=0.08, breath_db=-4.0, breath_min_s=0.25, drift_ct=4.0,
                   power=0.6, soft=0.5, base_power=0.0, base_soft=0.8, pitch_power=0.0,
                   spice_every=8, link=True, steps=24,
                   expr=0.5, model_vib=0.45, base_core=0.7, power_knee=0.3, sing_soft=True, late_first_ms=14.0,
                   pcentre_ms=2.0,
                   # at a slow tempo the vibrato on the long notes reads wide (12.4 ct median at 62 BPM, the jazz
                   # style 8.0): narrower, later, less of the model's own wobble - songs/when-the-year-turns-gold
                   slow=(80.0, {'vib_ct': 13.0, 'peak_vib_ct': 19.0, 'vib_min_s': 1.1, 'model_vib': 0.35})),
    'rock': dict(vel=(76, 116), late_ms=0.0, jitter_ms=8.0, cons=0.9, speed=1.1, cons_share=0.45,
                 glide_ms=65.0, melisma_glide=0.5, overshoot_ct=18.0,
                 scoop_first=0.6, scoop_leap=0.75, scoop_peak=0.9, scoop_ct=95.0, scoop_ms=110.0,
                 vib_other=0.5, vib_peak=0.9, vib_ct=28.0, peak_vib_ct=42.0, vib_hz=5.8, vib_delay=0.35,
                 vib_grow=0.45, vib_min_s=0.6, wobble=0.2,
                 fall=0.35, doit=0.06, fall_semis=-3.0, release=0.6, taper=0.35, swell=0.4, messa=0.0,
                 accent=0.15, breath_db=-3.0, breath_min_s=0.22, drift_ct=6.0,
                 power=0.8, soft=0.3, base_power=0.2, base_soft=0.0, pitch_power=0.05,
                 spice_every=2, link=True, steps=24),
}
STYLE_EXTRAS = {'expr': 0.85, 'model_vib': 1.0, 'base_core': 1.0, 'power_knee': 0.0, 'sing_soft': False,
                'makeup_db': None, 'late_first_ms': 0.0, 'pcentre_ms': None, 'slow': None}
"""Style keys with a default (a style that leaves them out - pop, rock - renders as before): expr = the voicebank pitch
model's expressiveness in pitch='hybrid' / 'model' (0..1: lower = flatter, its own scoops into notes and its wobble
smaller), model_vib = how much of the pitch model's own wobble stays on the steady part of a held note outside a
planned vibrato (1 = all, 0.25 = a quarter: only the singer's own late vibrato is heard), base_core = the core mode's
weight in the colour blend (below 1 with base_soft: the soft mode is the base), power_knee = the loudness (0..1 of the
blend's range) above which the power mode comes in (0.6: only the loudest peaks). sing_soft: SING SOFT, THEN MAKE UP
THE GAIN - the voicebank is driven with its softest inputs (100 % of the soft mode for the acoustic, the duration and
the pitch model: no core / power crossfade at all; Hanami's acoustic model takes no energy / breathiness / voicing /
tension input - only speaker, gender, velocity = consonant speed, depth, steps) and the level is restored by a static
make-up gain on the take's sampler zone (before the vocal chain, as a quieter singer closer to the mic): makeup_db
(None: the bank's SOFT_MAKEUP_DB). The calm comes from the delivery, not from the level. late_first_ms: extra
lay-back of a phrase's first vowel (a calm singer starts phrases behind the beat). pcentre_ms (the calm styles): the
lay-back follows the consonants - each vowel lands half its onset consonants + pcentre_ms behind the beat (the
syllable's P-centre just behind it) instead of the constant late_ms (jitter and late_first_ms stay on top): at 72 BPM
the duration model gives ~120 ms of onset consonants, at 100 BPM ~70 - a constant 34 ms put the P-centre 24 ms AHEAD
of the beat on the slow song ("sie klingt gerusht"); None: late_ms as given. slow: (bpm, {key: value}) - the style's
values at or under that tempo, where the call does not set them (the ballad's narrower, later vibrato); slow=None
turns it off."""
SOFT_MAKEUP_DB = {'hanami': -0.7}
"""sing_soft's make-up gain per voicebank (dB on the take's zone): the level difference of the soft-mode takes against
the blended ones, measured on the same parts (songs/jane-street-bossa/calm_ab.py)."""
MIC_PULL = {
    # on: default for the style; db: the pull's depth (dB at the end of the held vowel, a phrase-end note of >= ~1.4 s);
    # prox / room: dB of proximity bass (~300 Hz) / reverb send by then; min_s: the shortest held vowel (s) that
    # gets it; after_s: the onset blooms at full level first; curve: u ** curve (slow, then more); every: bars between
    # two pulls (the budget); end / peak / other: the chance on a phrase-end note / a peak (hook) / any other long
    # note (scaled 1.0 / 0.75 / 0.6 deep); coda_keep: share of the pull left on the word-final consonant
    'jazz':   dict(on=True, db=-4.5, prox=-2.0, room=1.5, min_s=1.0, after_s=0.35, curve=1.7, every=1.0,
                   end=1.0, peak=0.85, other=0.5, coda_keep=0.25),
    'ballad': dict(on=True, db=-5.0, prox=-2.5, room=2.0, min_s=1.0, after_s=0.35, curve=1.6, every=1.0,
                   end=1.0, peak=0.85, other=0.55, coda_keep=0.25),
    'pop':    dict(on=False, db=-3.5, prox=-1.5, room=1.0, min_s=1.1, after_s=0.3, curve=1.8, every=2.0,
                   end=0.9, peak=0.7, other=0.35, coda_keep=0.25),
    'rock':   dict(on=False, db=-3.0, prox=-1.5, room=1.0, min_s=1.2, after_s=0.3, curve=1.9, every=2.0,
                   end=0.85, peak=0.6, other=0.3, coda_keep=0.3),
}
"""The singer's mic technique (move 'mic_pull'): on a long held vowel, after the onset has bloomed, she slowly pulls
back from the microphone - the note fades a few dB (shaped), loses some proximity bass and gets a touch more room;
for the word-final consonant she leans back in (the coda keeps its level: the diction check counts the pull). Written
at compile time as automation on the vocal track - the level on its 'air' stage AFTER the compressor (so the
compressor does not undo it), the proximity on the 'mic' stage (agentsound.hornist.mic_stage), the room on the reverb
sends - through hornist.render(mic_post=True) and gesture.pull_back. Per style (sing(mic_pull=): None = the style's
'on', True / False, a number = the depth in dB, or a dict of these keys); budgeted song-wide with the Memory."""
PARAMS_NOT_SUNG = ('makeup_db',)
"""Style keys that do not change the takes (left out of the cache key): the make-up gain sits on the zone."""
"""Per style: vel (touch range), timing (late_ms lay-back, jitter_ms), consonants (cons: x the model's length, speed:
the voicebank's consonant-speed embedding, cons_share: the most of a note before them the consonants may take),
glides (glide_ms, melisma_glide x in runs, overshoot_ct), scoops (chances: scoop_first / _leap / _peak, scoop_ct,
scoop_ms), vibrato (vib_other / vib_peak chances, vib_ct / peak_vib_ct depth in cents, vib_hz, vib_delay s, vib_grow s,
vib_min_s, wobble), phrase ends (fall, doit, fall_semis, release, taper), air (swell, messa on long notes, accent dB
per velocity step), breath_db (the breath's level), breath_min_s (the shortest gap that gets a breath), drift_ct,
voice colour (power / soft: how far the dynamics blend in the power / soft mode, base_power / base_soft, pitch_power
per semitone above the phrase), spice_every (bars between two falls / doits / big scoops), link, steps (diffusion
steps); STYLE_EXTRAS (expr, model_vib, base_core, power_knee). 'jazz' and 'ballad' are the calm, intimate styles,
'pop' and 'rock' the outgoing ones."""


# ------------------------------------------------------------------------------------------------ pitch correction

TUNE = {
    # retune_ms: how fast the pitch is pulled onto the target note (the correction's time constant: 0 = at once, a
    # step - the robotic Cher / T-Pain sound; 20-50 ms = audible but smooth, the vibrato partly survives); hold: how much
    # closer (semitones) another note must be before the target flips to it (no chatter between two notes); dwell_ms:
    # the shortest a target note lasts (shorter flips - a consonant's pitch dip - are ignored: no 10 ms blips)
    'hard': dict(retune_ms=0.0, hold=0.06, dwell_ms=30.0),
    'soft': dict(retune_ms=40.0, hold=0.15, dwell_ms=45.0),
}
"""sing(tune=): pitch correction on the sung curve - the auto-tune effect, applied to the f0 the voicebank is given
(the voice is synthesised AT the corrected pitch: formants stay the voice's own, no chipmunk). Every frame's pitch is
snapped to the nearest note of the scale (with a little hysteresis, 'hold'), and the correction (target - sung) is
smoothed with a one-pole of retune_ms: 'hard' (0 ms) turns glides into stair steps through the scale and quantises
the vibrato away - the flip / yodel on every note change; 'soft' (40 ms) centres held notes but lets the transitions
and part of the vibrato through. The planned moves (scoops, glides, vibrato) stay: the correction acts on them."""


def _tune_pcs(scale, key, song, pitches) -> list:
    """The pitch classes the tune snaps to: scale = 'notes' (the line's own pitch classes), 'chromatic', a scale name
    of theory.SCALES ('minor_pentatonic' ... on `key`'s tonic or the song key's), a list of pitch classes / note names;
    None: `key`'s (or the song key's) scale, else the line's notes."""
    from .theory import SCALES, pc as _pc, scale as _scale
    if isinstance(scale, (list, tuple, set, frozenset)):
        out = sorted({(int(x) if isinstance(x, int) else _pc(x)) % 12 for x in scale})
        if not out:
            raise SingerError("tune: scale= is an empty list")
        return out
    if scale == 'notes' or (scale is None and key is None and getattr(song, 'key', None) is None):
        return sorted({int(p) % 12 for p in pitches}) or list(range(12))
    if scale == 'chromatic':
        return list(range(12))
    k = Key(key) if key is not None else Key(song.key)
    if scale is None:
        return sorted(k.pcs)
    if not isinstance(scale, str):
        raise SingerError(f"tune: scale= must be 'notes', 'chromatic', a scale name or a list, got {scale!r}")
    return sorted({(k.tonic + i) % 12 for i in _scale(scale)})


def _tune_opts(tune, retune_ms, key, scale, song, pitches) -> dict | None:
    """sing(tune=, retune_ms=, key=, scale=) -> the resolved correction {'mode', 'retune_ms', 'hold', 'pcs'} or None."""
    if tune is None or tune is False:
        if retune_ms is not None:
            raise SingerError("retune_ms= needs tune='hard' or 'soft'")
        return None
    extra = {}
    if isinstance(tune, dict):
        bad = sorted(k for k in tune if k not in ('mode', 'retune_ms', 'hold', 'dwell_ms', 'scale', 'key'))
        if bad:
            raise SingerError(f"tune: unknown key(s) {bad} (mode, retune_ms, hold, dwell_ms, scale, key)")
        extra = dict(tune)
        tune = extra.pop('mode', 'hard')
        scale = extra.pop('scale', scale)
        key = extra.pop('key', key)
    if tune is True:
        tune = 'hard'
    if tune not in TUNE:
        raise SingerError(f"tune must be one of {', '.join(TUNE)} (or None), got {tune!r}")
    O = dict(TUNE[tune], **extra)
    if retune_ms is not None:
        O['retune_ms'] = retune_ms
    r = float(O['retune_ms'])
    if not 0.0 <= r <= 400.0:
        raise SingerError(f"retune_ms = {r}: 0 (robotic steps) .. 400 ms")
    return {'mode': tune, 'retune_ms': r, 'hold': float(O['hold']), 'dwell_ms': float(O['dwell_ms']),
            'pcs': _tune_pcs(scale, key, song, pitches)}


def _nearest_note(x: float, pcs) -> int:
    b = int(math.floor(x))
    return min((n for n in range(b - 6, b + 8) if n % 12 in pcs), key=lambda n: (abs(x - n), n))


def tune_curve(midi: list, tune: dict, frame_s: float | None = None) -> list:
    """Pitch correction of a pitch curve (MIDI per frame, `frame_s` apart: the singer's acoustic frame by default):
    each frame's target is the nearest note of tune['pcs'] (it flips only when another note is `hold` semitones
    closer); a target that lasts less than tune['dwell_ms'] (a consonant's pitch dip, a wobble across the middle
    between two notes) is absorbed by the target before it (the whole curve is known: no lag on real note changes);
    the correction target - sung is smoothed with a one-pole of tune['retune_ms'] (0: applied at once)."""
    pcs = set(tune['pcs'])
    fr = FR if frame_s is None else float(frame_s)
    r = float(tune['retune_ms']) / 1000.0
    a = 1.0 if r <= 0 else 1.0 - math.exp(-fr / r)
    hold = float(tune.get('hold', 0.0))
    tg, cur = [], None
    for x in midi:
        n = _nearest_note(x, pcs)
        if cur is None or abs(x - n) + hold < abs(x - cur):
            cur = n
        tg.append(cur)
    # blips: runs shorter than dwell take the previous run's note (the first run: the next one's)
    least = max(1, round(float(tune.get('dwell_ms', 0.0)) / 1000.0 / fr))
    if least > 1 and tg:
        runs, i = [], 0
        while i < len(tg):
            j = i
            while j < len(tg) and tg[j] == tg[i]:
                j += 1
            runs.append([i, j, tg[i]])
            i = j
        for k, run in enumerate(runs):
            if run[1] - run[0] < least and len(runs) > 1:
                run[2] = runs[k - 1][2] if k else runs[1][2]
        tg = [n for i0, i1, n in runs for _ in range(i1 - i0)]
    out, c = [], None
    for x, t in zip(midi, tg):
        corr = t - x
        c = corr if c is None else c + a * (corr - c)
        out.append(round(x + c, 4))
    return out


# ------------------------------------------------------------------------------------------------ memory

class Memory:
    """What one singer already sang in a song: pass the same Memory to every sing() call and the spice budget
    (falls, doits, big scoops) counts song-wide."""

    def __init__(self):
        self.budget = Budget({'spice': 0.0})
        self.melodies: list = []        # [interval signature, statements]: ornaments on a melody's repeats
        self.used: list = []            # the ornaments sung: (beat, kind, word)

    def __repr__(self) -> str:
        return f"singer.Memory({self.budget.count('spice')} spice)"


# ------------------------------------------------------------------------------------------------ the part

@dataclass
class _SNote:
    start: float            # beats (song)
    dur: float
    pitch: int
    vel: int
    kind: str               # 'syllable' | 'melisma' | 'hold'
    syl: object             # lyrics.Syllable
    word_start: bool
    word_end: bool
    mark: str = ''
    hook: bool = False
    emph: str = ''          # the lyrics' markup: '' | 'emph' | 'intimate' (sing(emphasis=))


@dataclass
class Vocal:
    """A sung part (what sing() made): track, notes (_SNote, song beats), phrases (lists of note indices), plan
    (the moves per note), moves (log: (beat, name, params)), budget, and how it renders (voice, style, seed, take,
    formant, offset_ms, mode, pitch). .summary(), .describe(); after a build .rendered (the phrase files)."""
    song: object
    track: object
    bank: object
    style: str
    params: dict
    notes: list
    phrases: list
    plan: dict
    moves: list
    budget: dict
    seed: int
    take: int = 0
    formant: float = 0.0
    offset_ms: float = 0.0
    moves_on: bool = True
    pitch_mode: str = 'player'
    mode: str | None = None
    gain_db: float = 0.0
    lyrics_text: str = ''
    line: object = None
    expression: dict | None = None  # what back_phrase / ornament / messa / emphasis did (expression_lines())
    src: list = field(default_factory=list)          # the written notes (song beats) before the expression
    keys: list = field(default_factory=list)
    rendered: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    mic_pull: object = None          # what sing() got (None / bool / dB / dict): doubles and harmonies inherit it
    mic_opts: dict = field(default_factory=dict)    # the resolved MIC_PULL settings ('on' ...)
    mic: dict = field(default_factory=dict)         # planned pulls: note index (a syllable's first note) -> params
    mic_pulls: list = field(default_factory=list)   # after a compile: the pulls as written (beats, dB, word, coda)
    tune: dict | None = None         # the resolved pitch correction (TUNE: mode, retune_ms, hold, pcs) or None
    tune_args: tuple = (None, None, None, None)     # what sing() got (tune, retune_ms, key, scale): re-sung parts
    level_ref: object = None         # a Vocal whose takes this part's takes are level-matched to (prism voices)
    level_match_db: float = 0.0      # after a compile: the zone gain that matched them

    def summary(self) -> dict:
        out: dict = {}
        for _, name, _ in self.moves:
            out[name] = out.get(name, 0) + 1
        return dict(sorted(out.items()))

    def describe(self) -> str:
        lines = [f"{self.track.id}: {self.bank.id} ({self.style}{'' if self.moves_on else ', robotic: moves off'}), "
                 f"{len(self.notes)} notes in {len(self.phrases)} phrases, take {self.take}"]
        lines += [f"  {b:8.3f}  {n:<14} {p}" for b, n, p in self.moves]
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"Vocal({self.track.id!r}, {self.bank.id}, {len(self.notes)} notes, {self.summary()})"


# ------------------------------------------------------------------------------------------------ the track

def voice(bank='hanami', *, level: float | None = None):
    """The instrument of a vocal track (a one-shot sampler whose zones the singer fills with the rendered phrases
    when the song compiles): s.track('vocal', singer.voice('hanami')). Same as letting sing() create the track.
    level: the sampler's level in dB (None: the voice's calibration, manifest 'level_db': its sung part lands near
    -18 LUFS like a library patch)."""
    from .patches import Instrument
    b = _vb.get(bank)
    if level is None:
        level = float(b.entry.get('level_db', 0.0))
    # no zones yet (inst.sampler() would refuse that): render() writes them when the song compiles
    ins = Instrument('sampler', {'samples': []}, oneshot='on', velsens=0, polyphony=8, level=float(level))
    ins.info = {'singer_voice': b.id}
    return ins


def _vocal_track(target, track_id: str, bank, pan, gain_db):
    from .song import Song, Track
    if isinstance(target, Song):
        song = target
        if track_id in song.tracks:
            t = song.tracks[track_id]
            if getattr(t, '_singer', None) is None:
                raise SingerError(f"track {track_id!r} exists and is not a vocal track; pass track_id= another id")
            return song, t
        t = song.track(track_id, voice(bank), pan=pan, gain_db=gain_db)
        t._singer = {'bank': _vb.get(bank).id, 'parts': []}
        return song, t
    if isinstance(target, Track):
        t = target
        if getattr(t, '_singer', None) is None:
            if t.instrument.type != 'sampler' or t.instrument.params.get('samples'):
                raise SingerError(f"track {t.id!r}: sing() needs a vocal track - create it with "
                                  f"s.track('{t.id}', singer.voice('{_vb.get(bank).id}')) or pass the song")
            if t._notes:
                raise SingerError(f"track {t.id!r} already plays notes; a vocal track is the singer's alone")
            t._singer = {'bank': _vb.get(bank).id, 'parts': []}
        elif t._singer['bank'] != _vb.get(bank).id:
            raise SingerError(f"track {t.id!r} sings with {t._singer['bank']!r}; one voicebank per vocal track")
        return t._song, t
    raise SingerError(f"sing() takes the song or a vocal track, got {target!r}")


# ------------------------------------------------------------------------------------------------ planning

def _line_of(line):
    """(Clip, gestures, peaks) of a Clip / notation Line / notation string / notes."""
    if isinstance(line, str):
        from . import notation
        line = notation.notes(line)
    gestures = list(getattr(line, 'gestures', []) or [])
    peaks = list(getattr(line, 'peaks', []) or [])
    return as_clip(line), gestures, peaks


def _phrases(notes: list, secs, split_s: float) -> list:
    out: list = []
    for i, n in enumerate(notes):
        if i == 0:
            out.append([0])
            continue
        p = notes[i - 1]
        gap = secs(n.start) - secs(p.start + p.dur)
        # a melisma / hold always continues; a new syllable after a long enough gap starts a new phrase
        if n.kind == 'syllable' and gap >= split_s - 1e-9:
            out.append([i])
        else:
            out[-1].append(i)
    return out


def sing(target, line, lyrics: str, at=0.0, *, voice: str = 'hanami', style: str = 'pop', seed=0, vel=None,
         mode=None, transpose: int = 0, moves: bool = True, pitch: str = 'hybrid', memory: Memory | None = None,
         back_phrase=None, ornament=None, messa_di_voce=None, emphasis=None,
         peaks=None, take: int = 0, formant: float = 0.0, offset_ms: float = 0.0, track_id: str = 'vocal',
         pan: float | None = None, gain_db: float = 0.0, split_s: float = 0.6, range_check: bool = True,
         mic_pull=None, tune=None, retune_ms: float | None = None, key=None, scale=None, **overrides) -> Vocal:
    """Sing `line` with `lyrics` at `at` (beat or Section) -> a Vocal (the part; .track is the vocal track).

    target: the Song (creates / reuses track `track_id` with the voice) or a vocal track (singer.voice()).
    voice: a voicebank id of assets/voices/manifest.json ('hanami', 'tiger'). style: STYLES ('pop', 'rock'; the calm
    'jazz', 'ballad'); overrides= any STYLES / STYLE_EXTRAS key (vib_ct=35, fall=0, expr=0.6 ...). vel: (lo, hi) for humanize.touch phrase arcs (None:
    the style's; False keeps the line's velocities). mode: a fixed voice mode for the part ('core' / 'soft' / 'power'
    or a bank speaker name, e.g. 'tiger_glam'; None: the dynamics blend the bank's core / soft / power modes).
    transpose: semitones (e.g. -12 for a male voice). moves=False: the robotic baseline (see the module docstring).
    pitch: 'player' (the singer's own curve: glides, scoops, vibrato, falls), 'hybrid' (the voicebank's pitch
    predictor - transitions learned from the recorded singer - with the player's moves on top) or 'model' (the
    predictor alone, for comparison). memory: a Memory shared by a song's sing() calls (the spice budget). peaks: beats of
    hook peaks in the line (a notation Line's ^peak notes are used too). take / seed: another take sings the same
    part with other human variation (doubles). formant: semitones of the voicebank's formant (gender) shift (+ =
    brighter / smaller, - = darker). offset_ms: the whole part later / earlier (a double's lag). split_s: rests at
    least this long (seconds) start a new phrase (a new take file). range_check: warn about notes outside the
    voicebank's range. mic_pull: the mic technique on long held notes (MIC_PULL; None = the style's default: on for
    'jazz' / 'ballad', off for 'pop' / 'rock'; True / False; a number = the depth in dB, e.g. 6; a dict of MIC_PULL
    keys) - automation after the vocal compressor, the takes are not re-rendered for it.
    EXPRESSION (each None = the style's default, True / False, a number or a dict of its table's keys): back_phrase
    (BACK_PHRASE; on for 'jazz' / 'ballad'; a number = the most lay-back in beats), ornament (ORNAMENT; the repeats of
    a melody embellished - the Memory knows the statements; on for 'jazz' / 'ballad'; a number = the amount),
    messa_di_voce (MESSA: held peaks; on for 'jazz' / 'ballad'; a number = the swell's peak dB), emphasis (EMPHASIS:
    the lyrics' *word* / (( ... )) markup, honoured unless False; 'auto' adds the title / hook words; a number = the dB
    of an emphasised word).
    PITCH CORRECTION (TUNE; the auto-tune effect on the sung pitch curve): tune='hard' (the robotic Cher / T-Pain step:
    retune 0 ms, vibrato quantised away, glides become stair steps with a flip on every note change) or 'soft' (40 ms:
    held notes centred, transitions and some vibrato kept), or a dict (mode, retune_ms, hold, scale, key); retune_ms
    overrides the speed; key= / scale= what it snaps to (scale: 'notes' = the line's own pitch classes, 'chromatic', a
    theory.SCALES name such as 'minor_pentatonic', a list; default: key= or the song's key, else the line's notes).
    The voice is synthesised at the corrected pitch, so its formants stay its own. Doubles / harmonies inherit it."""
    if style not in STYLES:
        raise SingerError(f"singer style must be one of {', '.join(STYLES)}, got {style!r}")
    if pitch not in ('player', 'model', 'hybrid'):
        raise SingerError(f"pitch must be 'player', 'hybrid' or 'model', got {pitch!r}")
    S = dict(STYLES[style])
    if pitch == 'hybrid':      # the pitch model already approaches notes from below: the player's scoops are smaller
        S['scoop_ct'] *= HYBRID_SCOOP
    for k, v in overrides.items():
        if k not in S and k not in STYLE_EXTRAS:
            raise SingerError(f"sing(): unknown option {k!r} (a STYLES key: {', '.join(list(S) + list(STYLE_EXTRAS))})")
        S[k] = v
    bank = _vb.get(voice)
    song, track = _vocal_track(target, track_id, bank, pan, gain_db)
    slow = S.pop('slow', None)
    if slow and song.tempo_at(song._at(at)) <= slow[0]:
        S.update({k: v for k, v in slow[1].items() if k not in overrides})
    if mode is not None:
        bank.mode(mode) if bank.installed() else None
    clip, gestures, line_peaks = _line_of(line)
    if transpose:
        clip = clip.transpose(int(transpose))
    tune_o = _tune_opts(tune, retune_ms, key, scale, song, [n.pitch for n in clip])
    from .humanize import touch
    v = S['vel'] if vel is None else vel
    if v:
        if not isinstance(v, (tuple, list)) or len(v) != 2:
            raise SingerError(f"vel must be (lo, hi) for humanize.touch or False, got {v!r}")
        clip = touch(clip, v[0], v[1])
    warns: list = []
    sung = _lyr.align(clip, lyrics, extra=bank.dictionary() if bank.installed() else None, warnings=warns)
    ns = _lyr.melody_notes(clip)
    base = song._at(at)
    hooks = [float(p) for p in list(peaks or []) + line_peaks]
    notes = [_SNote(base + n.start, n.dur, n.pitch, n.vel, s.kind, s.syllable, s.word_start, s.word_end, s.mark,
                    any(abs(n.start - h) < 0.2 for h in hooks), s.emph) for n, s in zip(ns, sung)]
    if range_check:
        lo, hi = bank.range
        out_of = sorted({n.pitch for n in notes if not lo <= n.pitch <= hi})
        if out_of:
            warns.append(f"singer {bank.id}: notes {out_of} are outside the voice's range {lo}-{hi} (MIDI); "
                         f"transpose the line (transpose=) or choose another voice")
    if bank.installed():
        from .lyrics import CONSONANTS, VOWELS
        need = {p for n in notes for p in n.syl.phonemes}
        missing = sorted(p for p in need if p not in bank.phonemes)
        if missing:
            raise SingerError(f"voicebank {bank.id!r} has no phoneme(s) {missing}")
    secs = song.seconds
    phrases = _phrases(notes, secs, float(split_s))
    sd = seed_int(seed) * 1009 + int(take) * 7919
    XO = _expr_options(style, S, back_phrase, ornament, messa_di_voce, emphasis)
    notes, phrases, xinfo = _express(song, notes, phrases, S, XO, sd, memory, base, moves, int(transpose),
                                     float(split_s))
    plan, mlog, bud = _plan(notes, phrases, S, song, sd, memory, moves, gestures, base)
    xmessa, xtaken = _express_plan(song, notes, phrases, plan, mlog, xinfo, XO, sd, memory, base, moves)
    mopts = _mic_opts(style, mic_pull)
    mic = (_mic_plan(notes, phrases, song, mopts, sd, memory, base, mlog, track.id, skip=xtaken)
           if moves and mopts['on'] else {})
    vo = Vocal(song, track, bank, style, S, notes, phrases, plan, mlog, bud, seed_int(seed), int(take),
               float(formant), float(offset_ms), bool(moves), pitch, mode, 0.0, lyrics, line, warnings=warns,
               mic_pull=mic_pull, mic_opts=mopts, mic=mic, tune=tune_o, tune_args=(tune, retune_ms, key, scale))
    _express_record(vo, xinfo, XO, xmessa)
    track._singer['parts'].append(vo)
    for w in warns:
        song.advice.append(w)
    _place_preliminary(track)
    if not hasattr(song, '_singer_dir'):
        song._singer_dir = _song_dir()          # the song's folder: the vocal cache goes to <it>/samples/vocals/
    if not hasattr(song, '_singer_hook'):
        song._singer_hook = True
        song.add_compile_hook(render)
    return vo


def _plan(notes, phrases, S, song, sd, memory, moves_on, gestures, base):
    """The moves per note (decided in beats; realised in seconds when rendered)."""
    rng = random.Random(sd)
    plan: dict = {i: {} for i in range(len(notes))}
    log: list = []
    budget = {'spice_every': S['spice_every'], 'kept': 0, 'dropped': []}
    if not moves_on:
        return plan, log, budget
    secs = song.seconds
    bud = memory.budget if memory is not None else Budget({'spice': 0.0})
    bpb = 4.0
    bud.every['spice'] = float(S['spice_every']) * bpb

    def jit(v, spread=0.2):
        return v * (1.0 + spread * (2 * rng.random() - 1))

    def sound_s(i):              # how long note i's syllable group sounds (its run included)
        j = i
        end = notes[i].start + notes[i].dur
        while j + 1 < len(notes) and notes[j + 1].kind != 'syllable':
            j += 1
            end = notes[j].start + notes[j].dur
        return secs(end) - secs(notes[i].start), j

    cands = []
    for ph_i, ph in enumerate(phrases):
        held = [i for i in ph if secs(notes[i].start + notes[i].dur) - secs(notes[i].start) >= 0.45]
        peak = max(held, key=lambda i: (notes[i].pitch, notes[i].dur)) if held else None
        mean = sum(notes[i].pitch for i in ph) / len(ph)
        for k, i in enumerate(ph):
            n = notes[i]
            d_s = secs(n.start + n.dur) - secs(n.start)
            first = k == 0
            last = k == len(ph) - 1
            prev = notes[ph[k - 1]] if k else None
            is_peak = i == peak
            leap = prev is not None and n.pitch - prev.pitch >= 4
            p = plan[i]
            p['peak'] = is_peak
            # scoops (on new syllables and on runs' leaps)
            pr = (S['scoop_peak'] if (n.hook or is_peak) else S['scoop_first'] if first
                  else S['scoop_leap'] if leap else 0.0)
            if pr and d_s >= 0.2 and rng.random() < pr:
                ct = jit(S['scoop_ct'], 0.3) * (1.2 if n.hook else 1.0)
                big = ct >= 85
                c = dict(t=n.start - base, cls='spice', name='scoop', score=1.0 + n.hook + is_peak, i=i,
                         params=dict(cents=-round(ct, 1), ms=round(jit(S['scoop_ms'], 0.25), 1)))
                if big:
                    cands.append(c)
                else:
                    p['scoop'] = c['params']
                    log.append((round(n.start, 4), 'scoop', c['params']))
            # vibrato on held notes (a run: on its last note)
            if (n.kind == 'syllable' or n.kind == 'melisma') and (S['vib_ct'] > 0 or S['peak_vib_ct'] > 0):
                nxt_cont = i + 1 < len(notes) and notes[i + 1].kind == 'hold'
                if d_s >= S['vib_min_s'] and not nxt_cont:
                    pv = S['vib_peak'] if (is_peak or n.hook) else S['vib_other']
                    if d_s >= 1.2:          # a long held note nearly always sings out with vibrato
                        pv = max(pv, 0.95)
                    if rng.random() < pv:
                        dep = jit(S['peak_vib_ct'] if (is_peak or n.hook) else S['vib_ct'], 0.15)
                        p['vibrato'] = dict(depth=round(dep, 1), hz=round(jit(S['vib_hz'], 0.05), 2),
                                            delay=round(jit(S['vib_delay'], 0.2), 3),
                                            grow=round(jit(S['vib_grow'], 0.2), 3), wobble=S['wobble'])
                        log.append((round(n.start, 4), 'vibrato', p['vibrato']))
            # diction: a word-final consonant closes the word at the end of its last note (a run's / hold's last)
            if n.word_end and n.syl.coda:
                nx = notes[i + 1] if i + 1 < len(notes) else None
                at_rest = last or nx is None or secs(nx.start) - secs(n.start + n.dur) >= 0.08
                p['diction'] = dict(coda=' '.join(n.syl.coda), word=n.syl.word, at='rest' if at_rest else 'legato')
                log.append((round(n.start, 4), 'diction', p['diction']))
            # the air over held notes
            if d_s >= 1.0 and (is_peak or n.hook) and rng.random() < S['swell']:
                p['swell'] = dict(lo=-round(jit(2.0), 2), peak=round(jit(1.6), 2), end=-round(jit(1.0), 2),
                                  peak_at=round(jit(0.55, 0.15), 3))
                log.append((round(n.start, 4), 'swell', p['swell']))
            elif d_s >= 2.0 and S['messa'] and rng.random() < S['messa']:
                p['messa_di_voce'] = dict(lo=-round(jit(4.0), 2), peak=round(jit(2.0), 2), end=-round(jit(4.0), 2))
                log.append((round(n.start, 4), 'messa_di_voce', p['messa_di_voce']))
            # phrase ends
            if last:
                nxt = phrases[ph_i + 1][0] if ph_i + 1 < len(phrases) else None
                rest_s = (secs(notes[nxt].start) - secs(n.start + n.dur)) if nxt is not None else 9.0
                if d_s >= 0.3 and rest_s >= 0.4:
                    r = rng.random()
                    if r < S['doit']:
                        cands.append(dict(t=n.start - base, cls='spice', name='doit', score=1.0, i=i,
                                          params=dict(semis=round(jit(2.5, 0.2), 2), ms=round(jit(150, 0.2), 1))))
                    elif r < S['doit'] + S['fall']:
                        cands.append(dict(t=n.start - base, cls='spice', name='fall', score=1.0 + 0.3 * (d_s > 0.8), i=i,
                                          params=dict(semis=round(jit(S['fall_semis'], 0.3), 2),
                                                      ms=round(jit(220, 0.25), 1))))
                    if rng.random() < S['release']:
                        p['release'] = dict(db=-round(jit(8.0), 2), ms=round(jit(120, 0.25), 1),
                                            drop=-round(jit(14.0, 0.3), 1))
                        log.append((round(n.start, 4), 'release', p['release']))
                    if d_s >= 0.8 and rng.random() < S['taper']:
                        p['taper'] = dict(db=-round(jit(3.5), 2), frac=round(jit(0.45, 0.2), 3))
                        log.append((round(n.start, 4), 'taper', p['taper']))
        # breath before the phrase (the gap before it)
        i0 = ph[0]
        if ph_i == 0:
            gap = 9.0
        else:
            pl = notes[phrases[ph_i - 1][-1]]
            gap = secs(notes[i0].start) - secs(pl.start + pl.dur)
        if gap >= S['breath_min_s']:
            span = secs(notes[ph[-1]].start + notes[ph[-1]].dur) - secs(notes[i0].start)
            depth = 'deep' if span >= 4.0 else 'normal' if span >= 1.5 else 'catch'
            plan[i0]['breath'] = dict(depth=depth, gap=round(min(gap, 9.0), 3))
            log.append((round(notes[i0].start, 4), 'breath', plan[i0]['breath']))
    # the spice budget (falls, doits, big scoops): best-placed first, song-wide with a Memory
    kept = bud.keep(cands, base, (base, base + max((n.start + n.dur for n in notes), default=0) - base + 1),
                    slots=False)
    keep_ids = {id(c) for c in kept}
    for c in cands:
        if id(c) in keep_ids:
            plan[c['i']][c['name']] = c['params']
            log.append((round(notes[c['i']].start, 4), c['name'], c['params']))
            budget['kept'] += 1
        else:
            budget['dropped'].append((round(notes[c['i']].start, 4), c['name']))
            if c['name'] == 'scoop':          # a big scoop the budget refused: a small one instead
                small = dict(c['params'], cents=max(c['params']['cents'], -60.0))
                plan[c['i']]['scoop'] = small
                log.append((round(notes[c['i']].start, 4), 'scoop', small))
    # hand-written gestures of a notation Line (^scoop ^fall ^doit ^bend ^vib ^shake)
    for g in gestures:
        st = base + float(g['start'])
        hit = min(range(len(notes)), key=lambda i: abs(notes[i].start - st)) if notes else None
        if hit is None:
            continue
        kind, args, kw = g['kind'], list(g.get('args') or []), dict(g.get('kw') or {})
        prm = {'scoop': ('cents', -70.0), 'fall': ('semis', -3.0), 'doit': ('semis', 3.0), 'bend': ('semis', 2.0),
               'vib': ('depth', S['peak_vib_ct']), 'shake': ('interval', 3.0)}[kind]
        params = dict(kw)
        params.setdefault(prm[0], float(args[0]) if args else prm[1])
        name = {'vib': 'vibrato'}.get(kind, kind)
        plan[hit][name] = {**plan[hit].get(name, {}), **params, 'hand': True}
        log.append((round(notes[hit].start, 4), name, plan[hit][name]))
    # timing feel: correlated jitter on the vowel onsets (+ the extra lay-back of a phrase's first vowel)
    walk = 0.0
    firsts = {ph[0] for ph in phrases}
    lf = float(S.get('late_first_ms', 0.0))
    for i, n in enumerate(notes):
        walk = 0.6 * walk + 0.4 * (2 * rng.random() - 1)
        plan[i]['late_ms'] = round(S['late_ms'] + S['jitter_ms'] * walk * (0.5 if n.kind != 'syllable' else 1.0)
                                   + (lf if i in firsts else 0.0), 2)
    log.sort(key=lambda x: x[0])
    return plan, log, budget


def _mic_opts(style: str, mic_pull) -> dict:
    """sing(mic_pull=) -> the MIC_PULL settings of the style with it applied ('on' decides)."""
    O = dict(MIC_PULL[style])
    if mic_pull is None:
        return O
    if isinstance(mic_pull, bool):
        O['on'] = mic_pull
    elif isinstance(mic_pull, (int, float)):
        x = abs(float(mic_pull))
        if not 0.5 <= x <= 12.0:
            raise SingerError(f"mic_pull = {mic_pull!r}: the depth in dB must be 0.5..12")
        O.update(on=True, db=-x)
    elif isinstance(mic_pull, dict):
        bad = sorted(k for k in mic_pull if k not in O)
        if bad:
            raise SingerError(f"mic_pull: unknown key(s) {bad} (MIC_PULL keys: {', '.join(O)})")
        O.update(mic_pull)
        O['on'] = bool(mic_pull.get('on', True))
        O['db'] = -abs(float(O['db']))
    else:
        raise SingerError(f"mic_pull must be None, True / False, a depth in dB or a dict, got {mic_pull!r}")
    return O


def _syllable_groups(notes, ph) -> list:
    """The note indices of a phrase grouped per sung syllable (a syllable note + its melisma / hold notes) - the
    grouping of the takes' timeline (_groups)."""
    out: list = []
    for i in ph:
        if notes[i].kind == 'syllable' or not out:
            out.append([i])
        else:
            out[-1].append(i)
    return out


def _mic_plan(notes, phrases, song, O, sd, memory, base, log, tid: str = 'vocal', skip=()) -> dict:
    """The mic pulls: per syllable whose held vowel (its last pitch with the holds tied to it) lasts >= O['min_s'],
    by chance per role (a phrase end, a peak / hook, any other long note), deeper the longer the note and the more
    structural (end 1.0, peak 0.75, other 0.6 of O['db']); budgeted (one per O['every'] bars on this track,
    best-placed first; song-wide with a Memory). Own random stream: the rest of the plan (and the takes) is unchanged.
    Returns {first note index of the syllable: params}."""
    rng = random.Random(sd * 13 + 90001)
    secs = song.seconds
    cls = f"mic:{tid}"                  # per vocal track: a harmony part pulls with the lead, not instead of it
    bud = memory.budget if memory is not None else Budget({})
    cands = []
    for ph in phrases:
        held = [i for i in ph if secs(notes[i].start + notes[i].dur) - secs(notes[i].start) >= 0.45]
        peak = max(held, key=lambda i: (notes[i].pitch, notes[i].dur)) if held else None
        groups = _syllable_groups(notes, ph)
        for gk, g in enumerate(groups):
            j1 = js = g[-1]
            while js > g[0] and notes[js].kind == 'hold' and notes[js - 1].pitch == notes[js].pitch:
                js -= 1
            sus = secs(notes[j1].start + notes[j1].dur) - secs(notes[js].start)
            r, jd, jc = rng.random(), rng.random(), rng.random()
            if sus < O['min_s'] - 1e-9 or any(i in skip for i in g):     # a messa di voce's note (on a peak)
                continue
            last = gk == len(groups) - 1
            is_peak = peak in g or any(notes[i].hook for i in g)
            role = 'end' if last else 'peak' if is_peak else 'held'
            if r >= O[{'end': 'end', 'peak': 'peak', 'held': 'other'}[role]]:
                continue
            f = {'end': 1.0, 'peak': 0.75, 'held': 0.6}[role] * min(1.0, 0.5 + 0.35 * sus)
            db = max(-12.0, min(-0.5, O['db'] * f * (1.0 + 0.15 * (2 * jd - 1))))
            params = dict(db=round(db, 2), prox=round(O['prox'] * f, 2), room=round(O['room'] * f, 2),
                          curve=round(O['curve'] * (1.0 + 0.15 * (2 * jc - 1)), 3), after_s=float(O['after_s']),
                          coda_keep=float(O['coda_keep']), role=role, held_s=round(sus, 3),
                          word=notes[g[0]].syl.word, at=js)
            cands.append(dict(t=notes[js].start - base, cls=cls, name='mic_pull', i=g[0], params=params,
                              score={'end': 2.0, 'peak': 1.5, 'held': 1.0}[role] + 0.3 * min(sus, 3.0)))
    out: dict = {}
    if not cands:
        return out
    bud.every[cls] = max(0.0, float(O['every'])) * 4.0 or 1e-3
    end = max(n.start + n.dur for n in notes)
    for c in bud.keep(cands, base, (base, end + 1.0), slots=False):
        out[c['i']] = c['params']
        log.append((round(notes[c['params']['at']].start, 4), 'mic_pull', c['params']))
    log.sort(key=lambda x: x[0])
    return out


# ------------------------------------------------------------------------------------------------ placement

def _place_preliminary(track) -> None:
    """Trigger notes at approximate positions right away (so other compile hooks - a hero's echo throws - see the
    phrases); render() places them exactly."""
    from .patterns import Note
    parts = track._singer['parts']
    track._notes, track._origin = [], []
    key = 0
    for vo in parts:
        vo.keys = []
        for ph in vo.phrases:
            a = vo.notes[ph[0]]
            z = vo.notes[ph[-1]]
            pre = 0.6 * vo.song.tempo_at(a.start) / 60.0
            st = max(0.0, a.start - pre)
            track._notes.append(Note(st, max(0.05, z.start + z.dur - st), key, 127))
            track._origin.append('singer.sing')
            vo.keys.append(key)
            key += 1
    if key > 128:
        raise SingerError(f"track {track.id!r}: {key} phrases - a vocal track holds at most 128; split the part "
                          f"over two tracks (track_id=)")


# ------------------------------------------------------------------------------------------------ rendering

def _song_dir() -> Path:
    """Folder of the first calling file outside the agentsound package (the song), else the working directory."""
    pkg = Path(__file__).resolve().parent
    f = sys._getframe(1)
    while f is not None:
        fn = f.f_globals.get('__file__')
        if fn:
            p = Path(fn).resolve()
            if pkg not in p.parents and p.parent != pkg:
                return p.parent
        f = f.f_back
    return Path.cwd()


def _caller_dir(song) -> Path:
    d = getattr(song, '_singer_dir', None)
    return Path(d) if d is not None else _song_dir()


def _phrase_spec(vo: Vocal, ph: list) -> dict:
    """Everything that shapes one phrase, as plain data (seconds from the phrase's first note)."""
    song = vo.song
    a = vo.notes[ph[0]].start
    t0 = song.seconds(a)
    ns = []
    for i in ph:
        n = vo.notes[i]
        s = n.syl
        ns.append(dict(t=round(song.seconds(n.start) - t0, 5), d=round(song.seconds(n.start + n.dur) -
                                                                         song.seconds(n.start), 5),
                       m=n.pitch, v=n.vel, k=n.kind, on=list(s.onset), nu=s.nucleus, co=list(s.coda),
                       ws=n.word_start, we=n.word_end, w=s.word, st=s.stress, hook=n.hook,
                       plan={k: v for k, v in vo.plan[i].items()}))
    S = vo.params
    # the rest after the phrase (s): room for a final stop's release before the next phrase's breath
    k = vo.phrases.index(ph) if ph in vo.phrases else -1
    z = vo.notes[ph[-1]]
    rest = 9.0
    if 0 <= k < len(vo.phrases) - 1:
        rest = song.seconds(vo.notes[vo.phrases[k + 1][0]].start) - song.seconds(z.start + z.dur)
    return dict(format=FORMAT, bank=vo.bank.id, bank_sha=vo.bank.entry.get('sha256', ''), style=vo.style,
                params={k: v for k, v in S.items() if k not in PARAMS_NOT_SUNG}, notes=ns, seed=vo.seed, take=vo.take, formant=vo.formant, moves=vo.moves_on,
                pitch=vo.pitch_mode, mode=vo.mode, rest_after=round(min(9.0, rest), 4),
                release_vowel=RELEASE_VOWEL if RELEASE_VOWEL in _bank_phonemes(vo.bank) else None,
                **({'tune': vo.tune} if vo.tune else {}))


def _bank_phonemes(bank) -> set:
    try:
        return bank.phonemes if bank.installed() else set()
    except (OSError, ValueError):
        return set()


def _key(spec: dict) -> str:
    return hashlib.sha1(json.dumps(spec, sort_keys=True).encode('utf-8')).hexdigest()[:16]


def render(song, *, log=print) -> None:
    """The compile hook (idempotent): render every vocal part of the song that is not cached yet (batched per
    voicebank: duration prediction, then synthesis - two WSL calls), then write each vocal track's zones and trigger
    notes at the exact times of the final tempo map."""
    tracks = [t for t in song.tracks.values() if getattr(t, '_singer', None)]
    if not tracks:
        return
    root = _caller_dir(song) / 'samples' / 'vocals'
    todo: dict = {}                      # bank id -> [(vocal, phrase index, spec, path)]
    for t in tracks:
        for vo in t._singer['parts']:
            folder = root / vo.bank.id
            vo.rendered = []
            for k, ph in enumerate(vo.phrases):
                spec = _phrase_spec(vo, ph)
                word = ''.join(ch for ch in vo.notes[ph[0]].syl.word.lower() if ch.isalnum())[:16] or 'phrase'
                path = folder / f"{t.id}-{word}-{_key(spec)}.wav"
                vo.rendered.append({'path': path, 'spec': spec, 'phrase': k})
                if not (path.is_file() and path.with_suffix('.json').is_file()):   # a take is its wav + its timing json
                    todo.setdefault(vo.bank.id, []).append((vo, k, spec, path))
    for bank_id, items in todo.items():
        bank = _vb.get(bank_id).require()
        _vb.write_source(bank, root / bank_id)
        _synthesize(bank, items, root / bank_id, log)
    for t in tracks:
        _write_track(song, t)
        _write_mic(song, t)


MIC_MIN_S = 0.3
"""A pull needs at least this long (s) between the bloomed onset and the end of the vowel, else it is left out."""


def _mic_gestures(vo: Vocal, k: int, tl: dict) -> list:
    """The planned mic pulls of phrase k as gesture.pull_back in song beats, placed on the take's own timeline (the
    vowel's real onset and end, the word-final consonant's tokens): [(pull dict, Gesture)]."""
    song = vo.song
    ph = vo.phrases[k]
    a0 = vo.notes[ph[0]].start
    s0 = song.seconds(a0)
    lag = vo.offset_ms / 1000.0
    tm = song.tempo_map()

    def B(x):                       # phrase seconds -> song beats
        return tm.beat_at(max(0.0, s0 + x + lag))
    toks = [tuple(x) for x in tl.get('tokens', [])]
    vowels = list(tl.get('vowels', []))
    dic = list(tl.get('diction', []))
    groups = _syllable_groups(vo.notes, ph)
    out = []
    if len(vowels) != len(groups):
        return out
    for gk, g in enumerate(groups):
        P = vo.mic.get(g[0])
        if P is None:
            continue
        V = vowels[gk]
        nuc = next((j for j, (p, a, b) in enumerate(toks) if abs(a - V) < 2e-3 and p not in ('SP', 'AP')), None)
        if nuc is None:
            continue
        vend = toks[nuc][2]
        js = P['at']
        on = V if js == g[0] else max(V, song.seconds(vo.notes[js].start) - s0)
        p0 = on + P['after_s']
        if vend - p0 < MIC_MIN_S:
            continue
        nxt_v = vowels[gk + 1] if gk + 1 < len(vowels) else float('inf')
        cod = [d for d in dic if vend - 2e-3 <= d['a'] < nxt_v]
        coda = (min(d['a'] for d in cod), max(d['b'] for d in cod)) if cod else None
        cend = coda[1] if coda else vend
        later = [a for p, a, b in toks if a >= cend - 1e-4 and p != 'SP']
        back = min(cend + 0.25, (min(later) if later else cend + 9.0) - 0.01)
        back = max(back, cend + 0.03)
        bpm = song.tempo_at(vo.notes[js].start)
        ge = G.pull_back(B(p0), max(0.05, B(vend) - B(p0)), bpm, db=P['db'], prox=P['prox'], room=P['room'],
                         curve=P['curve'], coda=(B(coda[0]), B(coda[1])) if coda else None,
                         coda_keep=P['coda_keep'], back=B(back) + 1e-4)
        # what the pull does to the consonant against its vowel (the diction check adds it): the lane's mean over the
        # coda minus its median over the vowel
        vs = [ge.value('mic', B(V + (vend - V) * u / 40.0)) for u in range(41)]
        vs.sort()
        cv = (sum(ge.value('mic', B(coda[0] + (coda[1] - coda[0]) * u / 10.0)) for u in range(11)) / 11.0
              if coda else 0.0)
        pull = dict(word=P['word'], role=P['role'], db=P['db'], prox=P['prox'], room=P['room'], held_s=P['held_s'],
                    beat=round(B(p0), 4), end_beat=round(B(vend), 4), at_s=round(s0 + p0 + lag, 3),
                    end_s=round(s0 + vend + lag, 3), phrase=k, coda=(round(coda[0], 5), round(coda[1], 5)) if coda else None,
                    coda_vs_vowel_db=round(cv - vs[len(vs) // 2], 2) if coda else 0.0)
        out.append((pull, ge))
    return out


def _write_mic(song, t) -> None:
    """The mic pulls of a vocal track's parts as automation (idempotent: a second compile replaces the lanes it wrote):
    hornist.render(mic_post=True) - the level on the 'air' stage after the compressor, the proximity on the 'mic'
    stage, the room on the reverb sends."""
    st = t._singer
    old = {id(x) for x in st.get('mic_auto', [])}
    if old:
        t._auto = [x for x in t._auto if id(x) not in old]
    st['mic_auto'] = []
    gs = []
    for vo in st['parts']:
        vo.mic_pulls = []
        if not vo.mic:
            continue
        for r in vo.rendered:
            try:
                tl = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))['timeline']
            except (OSError, ValueError, KeyError):
                continue
            for pull, ge in _mic_gestures(vo, r['phrase'], tl):
                vo.mic_pulls.append(pull)
                gs.append(ge)
    gs += _expression_post(song, t)        # messa di voce / emphasis: the same lanes, written in the same call
    if not gs:
        return
    from . import hornist
    n0 = len(t._auto)
    hornist.render(t, gs, bpm=song.tempo, level='air', vibrato=False, accents=False, mic_post=True)
    st['mic_auto'] = list(t._auto[n0:])


def mic_lines(target) -> list[str]:
    """The mic pulls as written by the last compile (a Song, a vocal track or a Vocal): one line per pulled note -
    time, word, role, depth (dB at the end of the vowel), how long the vowel was held."""
    parts = _parts_of(target)
    out = []
    for vo in parts:
        for p in vo.mic_pulls:
            m, s = divmod(p['at_s'], 60.0)
            out.append(f"{vo.track.id!r} {int(m)}:{s:04.1f}-{p['end_s'] - p['at_s']:.1f}s  {p['word']!r:<12} "
                       f"{p['role']:<4} {p['db']:+.1f} dB (prox {p['prox']:+.1f}, room {p['room']:+.1f}), "
                       f"held {p['held_s']:.1f} s")
    return out


def _parts_of(target) -> list:
    if isinstance(target, Vocal):
        return [target]
    if getattr(target, '_singer', None):
        return list(target._singer['parts'])
    return [vo for t in getattr(target, 'tracks', {}).values() if getattr(t, '_singer', None)
            for vo in t._singer['parts']]


def _dur_job(spec: dict) -> dict:
    """The duration model's input for a phrase: words start at vowels (DiffSinger's convention): word 0 = SP + the
    first onset; word k = vowel k + its coda + the next syllable's onset; then a SP word."""
    groups = _groups(spec['notes'])
    head = 0.3
    ph, wd, wdur, midi = ['SP'] + list(groups[0]['on']), [], [], []
    wd.append(len(ph))
    wdur.append(max(1, round(head / FR)))
    midi += [groups[0]['m']] * len(ph)
    for k, g in enumerate(groups):
        nxt = groups[k + 1] if k + 1 < len(groups) else None
        w = [g['nu']] + list(g['co']) + (list(nxt['on']) if nxt else [])
        ph += w
        wd.append(len(w))
        span = (nxt['t'] - g['t']) if nxt else g['end'] - g['t']
        wdur.append(max(len(w), round(span / FR)))
        midi += [g['m']] * (1 + len(g['co'])) + ([nxt['m']] * len(nxt['on']) if nxt else [])
    ph.append('SP')
    wd.append(1)
    wdur.append(max(1, round(0.3 / FR)))
    midi.append(groups[-1]['m'])
    job = {'op': 'duration', 'phonemes': ph, 'word_div': wd, 'word_dur': wdur, 'ph_midi': midi}
    if spec['params'].get('sing_soft') and spec['moves']:
        job['speaker'] = {_soft_speaker(spec): 1.0}
    return job


def _soft_speaker(spec: dict) -> str:
    """The bank's soft mode (sing_soft: every model sings with it)."""
    b = _vb.get(spec['bank'])
    return b.mode(spec['mode']) if spec.get('mode') else b.mode('soft')


def _groups(ns: list) -> list:
    """Syllable groups of a phrase: a syllable note + its melisma / hold notes."""
    out = []
    for n in ns:
        if n['k'] == 'syllable' or not out:
            out.append(dict(t=n['t'], end=n['t'] + n['d'], m=n['m'], on=list(n['on']), nu=n['nu'], co=list(n['co']),
                            notes=[n], we=n['we'], ws=n['ws'], w=n.get('w', '')))
        else:
            out[-1]['notes'].append(n)
            out[-1]['end'] = n['t'] + n['d']
            out[-1]['we'] = n['we']
    return out


def _synthesize(bank, items: list, folder: Path, log) -> None:
    work = folder / '_work'
    # 1. consonant lengths from the bank's duration model
    jobs = [_dur_job(spec) for _, _, spec, _ in items]
    durs = _vb.run(bank, jobs, work=work, log=log)
    plans = []
    for (vo, k, spec, path), job, res in zip(items, jobs, durs):
        cons = _cons_lengths(job, res['ph_dur'], spec)
        plans.append(_timeline(spec, cons, bank))
    # 2. the voicebank's pitch model (pitch='model' parts only)
    pj = [(i, _pitch_job(p, spec, bank)) for i, (p, (_, _, spec, _)) in enumerate(zip(plans, items))
          if spec['pitch'] in ('model', 'hybrid')]
    if pj:
        res = _vb.run(bank, [j for _, j in pj], work=work, log=log)
        for (i, _), r in zip(pj, res):
            plans[i]['model_pitch'] = r['pitch']
            plans[i]['midi'] = r['pitch'] if items[i][2]['pitch'] == 'model' else _hybrid(r['pitch'], plans[i])
    # 3. pitch correction (sing(tune=)) on the final curve, then synthesis
    for p, (vo, k, spec, path) in zip(plans, items):
        if spec.get('tune'):
            p['midi_sung'] = p['midi']
            p['midi'] = tune_curve(p['midi'], spec['tune'])
    sj = []
    for p, (vo, k, spec, path) in zip(plans, items):
        path.parent.mkdir(parents=True, exist_ok=True)
        sj.append(_sing_job(p, spec, bank, path))
    _vb.run(bank, sj, work=work, log=log)
    for p, (vo, k, spec, path) in zip(plans, items):
        meta = dict(p)
        path.with_suffix('.json').write_text(json.dumps({'spec': spec, 'timeline': meta}, indent=1), encoding='utf-8')
    try:
        work.rmdir()
    except OSError:
        pass


def _cons_lengths(job: dict, pred: list, spec: dict) -> list:
    """Per group: (onset lengths s, coda lengths s) from the duration model's prediction (frames)."""
    groups = _groups(spec['notes'])
    pos = 1                                      # after the leading SP
    out = []
    on0 = [pred[pos + j] * FR for j in range(len(groups[0]['on']))]
    pos += len(groups[0]['on'])
    for k, g in enumerate(groups):
        pos += 1                                 # the vowel
        co = [pred[pos + j] * FR for j in range(len(g['co']))]
        pos += len(g['co'])
        nxt = groups[k + 1] if k + 1 < len(groups) else None
        on = [pred[pos + j] * FR for j in range(len(nxt['on']))] if nxt else []
        pos += len(on)
        out.append([on0 if k == 0 else out[k - 1][2], co, on])
    return [(o[0], o[1]) for o in out]


def _ease(u: float) -> float:
    u = 0.0 if u <= 0 else 1.0 if u >= 1 else u
    return 0.5 - 0.5 * math.cos(math.pi * u)


def _timeline(spec: dict, cons: list, bank) -> dict:
    """The phoneme tokens with their frames, and per-frame curves: midi, gain dB, voice-mode weights."""
    S = spec['params']
    mv = spec['moves']
    rng = random.Random(spec['seed'] * 31 + spec['take'] * 101 + int(spec['notes'][0]['t'] * 1000))
    groups = _groups(spec['notes'])
    # vowel onsets: the beat plus the timing feel (the consonants come before it)
    for g in groups:
        g['V'] = g['t'] + (g['notes'][0]['plan'].get('late_ms', 0.0) / 1000.0 if mv else 0.0)
    cf = S['cons'] if mv else 1.0
    on_len = [[x * cf for x in c[0]] for c in cons]
    co_len = [[x * cf for x in c[1]] for c in cons]
    if mv:
        _expr_cons(groups, on_len)              # an emphasised word's onset consonants a little longer
    # linking: a word-final consonant onto a vowel-initial next word (legato)
    if mv and S.get('link'):
        for k in range(len(groups) - 1):
            g, h = groups[k], groups[k + 1]
            if g['we'] and g['co'] and not h['on'] and h['t'] - g['end'] < 0.06:
                h['on'] = [g['co'][-1]]
                on_len[k + 1] = [co_len[k][-1]]
                g['co'] = g['co'][:-1]
                co_len[k] = co_len[k][:-1]
                g['linked'] = True
    if mv and S.get('pcentre_ms') is not None:   # the calm lay-back follows the consonants (STYLE_EXTRAS)
        for g, o in zip(groups, on_len):
            g['V'] += (0.5 * sum(o) * 1000.0 + float(S['pcentre_ms']) - float(S['late_ms'])) / 1000.0
    toks: list = []                 # (phoneme, start s, end s) relative to the first vowel onset ... shifted later

    def add(p, a, b):
        toks.append([p, a, b])
    # the leading part: SP, breath, SP, the first onset
    first = groups[0]
    o0 = on_len[0]
    o_total = sum(o0)
    if not mv:
        # robotic: the consonants start ON the beat, the vowel follows them
        first['V'] = first['t'] + o_total
    bplan = first['notes'][0]['plan'].get('breath') if mv else None
    pre_room = 0.0
    breath = 0.0
    if bplan:
        gap = bplan['gap']
        want = {'deep': 0.48, 'normal': 0.34, 'catch': 0.2}[bplan['depth']]
        breath = max(0.12, min(want, gap - o_total - 0.08))
    lead_sp = 0.12
    start = first['V'] - o_total - (breath + 0.07 if breath else 0.0) - lead_sp
    add('SP', start, start + lead_sp)
    t = start + lead_sp
    if breath:
        add('AP', t, t + breath)
        add('SP', t + breath, t + breath + 0.07)
        t += breath + 0.07
    for p, d in zip(first['on'], o0):
        add(p, t, t + d)
        t += d
    # the syllables
    dic: list = []                  # diction: the codas (+ a final stop's release) with their lift and vowel span
    rel_v = spec.get('release_vowel')

    def close(g, co, cl, V, end, after):
        """The vowel + its coda before a rest: the coda ends at `end` (the end of the word's last note), each
        consonant within its class's min / max, at most half the note; a final stop gets a silent closure before
        it and (moves on) a released burst after it. Returns the time after the last token."""
        lens = []
        for p, x in zip(co, cl):
            mn, _, mx = DICTION[_cls(p)][:3]
            lens.append(min(max(x, mn), max(mn, mx)))
        stop = g['we'] and bool(co) and _cls(co[-1]) == 'stop'
        closure = CLOSURE_S if stop and (len(co) == 1 or _cls(co[-2]) in ('sibilant', 'fricative')) else 0.0
        total = sum(lens) + closure
        lim = 0.5 * max(0.05, end - V)
        if total > lim:
            lens = [x * lim / total for x in lens]
            closure *= lim / total
        c0 = end - sum(lens) - closure
        g['vend'] = c0
        add(g['nu'], V, c0)
        tt = c0
        rs, ra, rb, fade = RELEASE['voiced' if co and co[-1] in _VOICED_STOPS else 'unvoiced']
        released = stop and mv and rel_v and min(rs, 0.25 * after) >= 0.015
        for j, (p, d) in enumerate(zip(co, lens)):
            if closure and j == len(co) - 1:
                add('SP', tt, tt + closure)
                tt += closure
            add(p, tt, tt + d)
            if g['we']:
                dic.append(dict(word=g['w'], ph=p, cls=_cls(p), a=round(tt, 5), b=round(tt + d, 5), at='rest',
                                lift=DICTION[_cls(p)][4] if mv else 0.0, vowel=(V, c0),
                                fade=fade if released and j == len(co) - 1 else 0.0))
            tt += d
        if released:
            r = min(rs, 0.25 * after)
            add(rel_v, tt, tt + r)
            dic.append(dict(word=g['w'], ph=rel_v, cls='release', a=round(tt, 5), b=round(tt + r, 5), at='rest',
                            lift=ra, to=rb, vowel=(V, c0)))
            tt += r
        return tt

    for k, g in enumerate(groups):
        nxt = groups[k + 1] if k + 1 < len(groups) else None
        V = g['V']
        end = g['end']                            # the written end of the syllable's last note
        co, cl = list(g['co']), list(co_len[k])
        if nxt is not None:
            on, ol = list(nxt['on']), list(on_len[k + 1])
            if not mv:
                nxt['V'] = nxt['t'] + sum(ol)
            Vn = nxt['V']
            gap = nxt['t'] - end
            if gap < 0.08:                        # legato: the cluster sits before the next vowel
                share = S['cons_share'] * _expr_share(g) if mv else 0.6
                room = (Vn - V) * share
                tot = sum(cl) + sum(ol)
                f = min(1.0, room / tot) if tot > 0 else 1.0
                # never squeezed to nothing: a coda keeps its class's legato minimum, an onset ONSET_MIN_S - the
                # cluster may then take up to LEGATO_SHARE of the note
                cl = [max(x * f, DICTION[_cls(p)][1]) for p, x in zip(co, cl)]
                ol = [max(x * f, ONSET_MIN_S) for x in ol]
                tot = sum(cl) + sum(ol)
                lim = (Vn - V) * max(share, LEGATO_SHARE)
                if tot > lim > 0:
                    cl = [x * lim / tot for x in cl]
                    ol = [x * lim / tot for x in ol]
                c0 = Vn - sum(cl) - sum(ol)
                g['vend'] = c0
                add(g['nu'], V, c0)
                tt = c0
                for j, (p, d) in enumerate(zip(co + on, cl + ol)):
                    add(p, tt, tt + d)
                    if j < len(co) and g['we']:
                        dic.append(dict(word=g['w'], ph=p, cls=_cls(p), a=round(tt, 5), b=round(tt + d, 5),
                                        at='legato', lift=DICTION[_cls(p)][5] if mv else 0.0, vowel=(V, c0)))
                    tt += d
            else:                                 # a rest: the coda closes the note, the onset leads the next
                f2 = min(1.0, 0.8 * gap / sum(ol)) if ol and sum(ol) > 0 else 1.0
                ol = [x * f2 for x in ol]
                o_start = Vn - sum(ol)
                tt = close(g, co, cl, V, end, o_start - end)
                bp = nxt['notes'][0]['plan'].get('breath') if mv else None
                rest = o_start - tt
                if bp and rest >= S['breath_min_s'] - 0.02:
                    b = max(0.12, min({'deep': 0.45, 'normal': 0.32, 'catch': 0.2}[bp['depth']], rest - 0.12))
                    add('SP', tt, o_start - 0.06 - b)
                    add('AP', o_start - 0.06 - b, o_start - 0.06)
                    add('SP', o_start - 0.06, o_start)
                elif rest > 0:
                    add('SP', tt, o_start)
                tt = max(tt, o_start)
                for p, d in zip(on, ol):
                    add(p, tt, tt + d)
                    tt += d
        else:
            tt = close(g, co, cl, V, end, float(spec.get('rest_after', 9.0)))
            add('SP', tt, tt + 0.35)
    # frames (from the file start)
    t0 = toks[0][1]
    bounds = [0]
    for p, a, b in toks:
        bounds.append(max(bounds[-1] + 1, round((b - t0) / FR)))
    # a word-final consonant never loses its audible length to the frame grid (a 45 ms coda is 3 or 4 frames,
    # depending on where the note falls: off-grid notes - a back-phrased phrase, an ornament - would warn
    # 'coda_short'): it takes the missing frame from the vowel before it. Takes without such a coda are unchanged.
    for e in dic:
        if e['cls'] == 'release':
            continue
        i = next(i for i, (p, a, b) in enumerate(toks) if p == e['ph'] and abs(a - e['a']) < 1e-4)
        need = math.ceil(DICTION[e['cls']][3] / FR - 1e-6) - (bounds[i + 1] - bounds[i])
        j = i - 1                                # the giver: the vowel before the cluster (or a longer consonant in it)
        while need > 0 and j >= 0 and toks[j][0] not in ('SP', 'AP'):
            have = bounds[j + 1] - bounds[j]
            vowel = toks[j][0] in _lyr.SUNG_VOWELS
            keep = 4 if vowel else math.ceil(DICTION[_cls(toks[j][0])][3] / FR - 1e-6)
            if have - need >= keep:
                for k in range(j + 1, i + 1):
                    bounds[k] -= need
                break
            if vowel:
                break
            j -= 1
    durs =[bounds[i + 1] - bounds[i] for i in range(len(toks))]
    nf = bounds[-1]
    ftime = [t0 + (f + 0.5) * FR for f in range(nf)]          # phrase seconds of each frame centre
    if mv:
        moves, vmask = _move_lane(groups, _segments(groups, mv), S, ftime)
    else:
        moves, vmask = [0.0] * len(ftime), [0] * len(ftime)
    midi = _pitch_curve(spec, groups, ftime, rng, mv, S, moves)
    steady = _steady_mask(groups, ftime) if mv and S.get('model_vib', 1.0) < 1.0 else None
    for e in dic:                                             # the frames each coda / release really gets
        i = next(i for i, (p, a, b) in enumerate(toks) if p == e['ph'] and abs(a - e['a']) < 1e-4)
        e['f'] = (bounds[i], bounds[i + 1])
        va, vb_ = (max(0, min(nf, round((x - t0) / FR))) for x in e['vowel'])
        e['vf'] = (va, max(va + 1, vb_))
    gain, mix = _air_and_colour(spec, groups, ftime, toks, t0, mv, S, bank, rng, dic)
    diction = []
    for e in dic:
        fa, fb = e['f']
        va, vb_ = e['vf']
        vg = sorted(gain[va:vb_]) or [0.0]
        level = sum(gain[fa:fb]) / max(1, fb - fa) - vg[len(vg) // 2]
        diction.append(dict(word=e['word'], ph=e['ph'], cls=e['cls'], at=e['at'], a=e['a'], b=e['b'],
                            ms=round((fb - fa) * FR * 1000, 1), lift=e['lift'], level_db=round(level, 2)))
    return {'phonemes': [p for p, _, _ in toks], 'durations': durs, 'offset_s': t0, 'frames': nf, 'midi': midi,
            'vowels': [round(g['V'], 5) for g in groups], 'moves': [round(x, 4) for x in moves], 'vibmask': vmask,
            'gain': gain, 'mix': mix, 'diction': diction,
            'tokens': [(p, round(a, 4), round(b, 4)) for p, a, b in toks],
            **({'steadymask': steady, 'model_vib': float(S['model_vib'])} if steady is not None else {})}


STEADY_MIN_S = 0.45
"""A note is 'held' for model_vib when it sounds at least this long: its steady part runs from 0.12 s after its onset
to 0.06 s before its end (the transitions into and out of it stay the model's)."""


def _steady_mask(groups, ftime) -> list:
    nf = len(ftime)
    mask = [0] * nf
    for g in groups:
        for j, n in enumerate(g['notes']):
            st = g['V'] if j == 0 else n['t']
            end = g['end'] if j == len(g['notes']) - 1 else g['notes'][j + 1]['t']
            if end - st < STEADY_MIN_S:
                continue
            a, b = st + 0.12, end - 0.06
            for f, x in enumerate(ftime):
                if a <= x <= b:
                    mask[f] = 1
    return mask


def _segments(groups: list, mv: bool) -> list:
    """Pitch segments (start s, midi, kind) - each note's pitch from its vowel onset (a run's notes on their own
    onsets, with half the timing feel)."""
    segs = []
    for g in groups:
        for j, n in enumerate(g['notes']):
            if j == 0:
                st = g['V']
            else:
                st = n['t'] + (n['plan'].get('late_ms', 0.0) / 1000.0 if mv else 0.0)
            segs.append(dict(t=st, m=float(n['m']), k=n['k'] if j else 'syllable', note=n,
                             end=n['t'] + n['d']))
    return segs


def _pitch_curve(spec, groups, ftime, rng, mv, S, moves) -> list:
    segs = _segments(groups, mv)
    nf = len(ftime)
    out = [0.0] * nf
    starts = [s['t'] for s in segs]
    import bisect
    for f, t in enumerate(ftime):
        i = max(0, bisect.bisect_right(starts, t) - 1)
        out[f] = segs[i]['m']
    if not mv:
        return [round(x, 4) for x in out]
    # glides: an S-curve into each next note, starting before its onset; overshoot on leaps up
    shapes = []
    for i in range(1, len(segs)):
        a, b = segs[i - 1], segs[i]
        dm = b['m'] - a['m']
        if abs(dm) < 1e-6:
            continue
        T = S['glide_ms'] / 1000.0 * (0.75 + 0.08 * min(abs(dm), 7))
        if b['k'] == 'melisma':
            T *= S['melisma_glide']
        T = max(0.035, min(0.2, T))
        c = b['t'] - 0.35 * T
        shapes.append((c, c + T, a['m'], b['m'], dm, b))
    for c0, c1, ma, mb, dm, b in shapes:
        for f, t in enumerate(ftime):
            if c0 - FR <= t <= c1 + 0.25:
                if t <= c1:
                    u = (t - c0) / (c1 - c0)
                    if t >= c0:
                        out[f] = ma + (mb - ma) * _ease(u)
                if dm >= 2 and S['overshoot_ct']:
                    ov = S['overshoot_ct'] / 100.0 * min(1.0, dm / 5.0)
                    if c1 - 0.02 <= t <= c1 + 0.2:
                        x = (t - (c1 - 0.02)) / 0.22
                        out[f] += ov * math.sin(math.pi * min(1.0, x)) * (1 - x) * 1.6
    # gestures (gesture.py with bpm=60: beats are seconds): scoops, vibrato, falls, releases, notation moves
    for f in range(nf):
        out[f] += moves[f]
    # drift: slow random walk of a few cents (two smoothed noises)
    if S['drift_ct']:
        a = b = 0.0
        d = S['drift_ct'] / 100.0
        for f in range(nf):
            a = 0.985 * a + 0.015 * (2 * rng.random() - 1) * 6
            b = 0.9 * b + 0.1 * (2 * rng.random() - 1)
            out[f] += d * (0.8 * a + 0.2 * b)
    return [round(x, 4) for x in out]


def _move_lane(groups, segs, S, ftime) -> tuple[list, list]:
    """The planned pitch moves (scoops, vibrato, falls, releases, notation moves) summed per frame (semitones), and
    a mask of the frames under a planned vibrato."""
    nf = len(ftime)
    gs = _gestures(groups, segs, S)
    bend = [s for g in gs for s in g.shapes if s.lane == 'bend']
    vib = [s for g in gs for s in g.shapes if s.lane == 'vib']
    spans = [(g.start, g.end) for g in gs if g.name == 'vibrato']
    lane, mask = [0.0] * nf, [0] * nf
    for f, t in enumerate(ftime):
        v = 0.0
        for s in bend:
            if s.t0 - 1e-6 <= t <= s.t1 + 1e-6:
                v += s(t)
        for s in vib:
            if s.t0 - 1e-6 <= t <= s.t1 + 1e-6:
                v += s(t) / 100.0
        lane[f] = v
        mask[f] = 1 if any(a <= t <= b for a, b in spans) else 0
    return lane, mask


def _hybrid(model: list, plan: dict) -> list:
    """pitch='hybrid': the voicebank pitch model's own curve (its natural transitions, preparations and overshoots)
    with the player's moves on top: under a planned vibrato the model's own wobble is smoothed out (a 190 ms moving
    average) so the two never stack; a calm style (model_vib < 1) keeps only that share of the model's wobble on the
    steady part of every held note too (plan 'steadymask')."""
    nf = len(model)
    moves, mask = plan['moves'], plan['vibmask']
    steady, keep = plan.get('steadymask'), float(plan.get('model_vib', 1.0))
    w = max(1, round(0.19 / FR / 2))
    out = list(model)
    for f in range(nf):
        if mask[f] or (steady and steady[f]):
            a, b = max(0, f - w), min(nf, f + w + 1)
            sm = sum(model[a:b]) / (b - a)
            out[f] = sm if mask[f] else sm + keep * (model[f] - sm)
    return [round(out[f] + moves[f], 4) for f in range(nf)]


def _vend(g: dict) -> float:
    """Where a syllable group's vowel ends (its coda starts; the timeline sets it), else the end of its last note.
    A phrase end's fall / doit / release / taper end here, so they shape the vowel and leave the consonant alone."""
    return max(g['V'] + 0.05, g['vend']) if 'vend' in g else g['end']


def _gestures(groups, segs, S) -> list:
    """The planned moves as gesture.Gesture objects in phrase seconds (gesture.py at bpm=60)."""
    out = []
    by_note = {id(s['note']): s for s in segs}
    for gi, g in enumerate(groups):
        for j, n in enumerate(g['notes']):
            p = n['plan']
            s = by_note[id(n)]
            st = s['t']
            if j == len(g['notes']) - 1:
                end = g['end']
            else:
                end = g['notes'][j + 1]['t']
            dur = max(0.05, end - st)
            if 'scoop' in p:
                out.append(G.scoop(st, 60, cents=p['scoop']['cents'], ms=p['scoop']['ms']))
            if 'blue' in p:                     # the blue note: sung from the flat, bent up slowly
                out.append(G.scoop(st, 60, cents=p['blue']['cents'], ms=p['blue']['ms']))
            if 'vibrato' in p:
                v = p['vibrato']
                # the vibrato of a run's last note / a held note: until the note (and its holds) end
                vend = g['end'] if j == len(g['notes']) - 1 else end
                kw = {k: v[k] for k in ('depth', 'hz', 'delay', 'grow', 'wobble') if k in v}
                out.append(G.vibrato(st, max(0.06, vend - st), 60, shape='centre', lane='bend',
                                     seed=int(st * 1000) + gi, **kw))
            # the phrase-end moves act on the vowel: they end where the coda starts (never on the consonant)
            ve = _vend(g)
            if 'fall' in p:
                out.append(G.fall(ve, 60, semis=p['fall']['semis'], ms=p['fall'].get('ms', 220.0), air=0.0))
            if 'doit' in p:
                out.append(G.doit(ve, 60, semis=p['doit']['semis'], ms=p['doit'].get('ms', 160.0), air=0.0))
            if 'release' in p:
                out.append(G.breath_release(ve, 60, db=0.0, ms=p['release']['ms'], drop=p['release']['drop']))
            if 'bend' in p:
                out.append(G.bend(st, dur, 60, semis=p['bend']['semis']))
            if 'shake' in p:
                out.append(G.shake(st, dur, 60, interval=p['shake']['interval']))
    return out


def _diction_gain(dic, nf, a_db) -> list:
    """Diction over the codas (frames from _timeline): the coda keeps its vowel's level (the median of a_db over
    the vowel - a release / taper / swell end never reaches it; a_db is set so in place, so the colour follows) and
    gets its class's lift (a final stop's voiced tail faded by its 'fade' over the last 35 ms); a final stop's release
    vowel goes from its 'lift' to its 'to' (RELEASE). Returns the lift per frame."""
    lift = [0.0] * nf
    nfade = max(1, round(0.035 / FR))
    for e in dic:
        va, vb_ = e['vf']
        v = sorted(a_db[va:vb_]) or [0.0]
        ref = v[len(v) // 2]
        fa, fb = max(0, e['f'][0]), min(nf, e['f'][1])
        n = max(1, fb - fa)
        for f in range(fa, fb):
            a_db[f] = ref
            if e['cls'] == 'release':
                lift[f] = e['lift'] + (e['to'] - e['lift']) * (f - fa + 1) / n
            else:
                j = f - (fb - min(nfade, n))
                lift[f] = e['lift'] + (e.get('fade', 0.0) * (j + 1) / min(nfade, n) if j >= 0 else 0.0)
    return lift


def _air_and_colour(spec, groups, ftime, toks, t0, mv, S, bank, rng, dic=()):
    """Gain (dB per frame) and the voice-mode blend ({speaker: [weight per frame]})."""
    nf = len(ftime)
    core = bank.mode('core')
    mode = spec.get('mode')
    if mode:
        sp = bank.mode(mode)
        lift = _diction_gain(dic, nf, [0.0] * nf) if mv else [0.0] * nf
        return [round(x, 3) for x in lift], {sp: 1.0}
    if not mv:
        return [0.0] * nf, {core: 1.0}
    # air moves (dB) from gesture.py
    gs = []
    allv = [n['v'] for g in groups for n in g['notes']]
    mean_v = sum(allv) / len(allv)
    for g in groups:
        for j, n in enumerate(g['notes']):
            p = n['plan']
            st = g['V'] if j == 0 else n['t']
            end = g['end'] if j == len(g['notes']) - 1 else g['notes'][j + 1]['t']
            d = max(0.05, end - st)
            if 'swell' in p:
                gs.append(G.swell(st, d, 60, **p['swell'], bright=0.0))
            if 'messa_di_voce' in p:
                gs.append(G.messa_di_voce(st, d, 60, **p['messa_di_voce'], bright=0.0))
            if 'taper' in p:
                gs.append(G.taper(st, max(0.05, _vend(g) - st), 60, **p['taper'], bright=0.0))
            if 'release' in p:
                gs.append(G.breath_release(_vend(g), 60, db=p['release']['db'], ms=p['release']['ms'], drop=0.0))
    notes = [(g['V'] if j == 0 else n['t'], max(0.05, n['d']), n['v']) for g in groups for j, n in enumerate(g['notes'])]
    if S['accent'] and notes:
        gs.append(G.accents(notes, 60, db_per_vel=S['accent'], limit=5.0))
    air = [s for g in gs for s in g.shapes if s.lane == 'air']
    a_db = [0.0] * nf
    for f, t in enumerate(ftime):
        a_db[f] = sum(s(t) for s in air if s.t0 - 1e-6 <= t <= s.t1 + 1e-6)
    lift = _diction_gain(dic, nf, a_db)
    # level relative to the part's mean velocity (dB), for the colour
    vel_db = [0.0] * nf
    import bisect
    starts = [x[0] for x in notes]
    for f, t in enumerate(ftime):
        i = max(0, bisect.bisect_right(starts, t) - 1)
        vel_db[f] = (notes[i][2] - mean_v) * 0.12
    # breath frames at their own level
    br = [0.0] * nf
    for p, a, b in toks:
        if p == 'AP':
            fa, fb = int((a - t0) / FR), int((b - t0) / FR)
            for f in range(max(0, fa), min(nf, fb + 1)):
                br[f] = S['breath_db']
    gain = [round(a_db[f] + br[f] + lift[f], 3) for f in range(nf)]
    xc = _expr_curves(groups, ftime, toks)      # messa di voce / emphasis / intimate (None: none in this phrase)
    if S.get('sing_soft'):           # sing soft: the soft mode alone, no core / power crossfade
        return gain, ({bank.mode('soft'): 1.0} if xc is None else _expr_mix(xc, gain, {}, bank, True))
    # colour: soft when quiet, power when loud / high
    soft_n = bank.mode('soft')
    pow_n = bank.mode('power')
    pm = sum(n['m'] for g in groups for n in g['notes']) / max(1, sum(len(g['notes']) for g in groups))
    segs = _segments(groups, mv)
    sst = [s['t'] for s in segs]
    w_core, w_soft, w_pow = [], [], []
    for f, t in enumerate(ftime):
        lvl = a_db[f] + vel_db[f]
        x = max(-1.0, min(1.0, lvl / 6.0))
        i = max(0, bisect.bisect_right(sst, t) - 1)
        hi = max(0.0, segs[i]['m'] - pm)
        knee = S.get('power_knee', 0.0)
        ps = S['base_power'] + max(0.0, x - knee) / (1.0 - knee) * S['power'] + hi * S['pitch_power']
        ss = S['base_soft'] + max(0.0, -x) * S['soft']
        w_core.append(float(S.get('base_core', 1.0)))
        w_soft.append(round(min(1.5, ss), 4))
        w_pow.append(round(min(1.5, ps), 4))
    mix = {core: w_core}
    mix[soft_n] = [a + b for a, b in zip(mix.get(soft_n, [0.0] * nf), w_soft)] if soft_n in mix else w_soft
    mix[pow_n] = [a + b for a, b in zip(mix.get(pow_n, [0.0] * nf), w_pow)] if pow_n in mix else w_pow
    if xc is not None:
        mix = _expr_mix(xc, gain, mix, bank, False)
    return gain, mix


def _pitch_job(p: dict, spec: dict, bank) -> dict:
    """The voicebank pitch model's input: the notes as frames (rests SP), the player's curve as the base."""
    groups = _groups(spec['notes'])
    for g, v in zip(groups, p['vowels']):
        g['V'] = v
    t0 = p['offset_s']
    nf = p['frames']
    marks = []
    for g in groups:
        for j, n in enumerate(g['notes']):
            st = g['V'] if j == 0 else n['t']
            marks.append((st, n['m']))
    note_midi, note_rest, note_dur = [], [], []
    cur = 0
    fs = [max(0, min(nf, round((st - t0) / FR))) for st, _ in marks]
    if fs[0] > 0:
        note_midi.append(float(marks[0][1]))
        note_rest.append(True)
        note_dur.append(fs[0])
        cur = fs[0]
    for k, (st, m) in enumerate(marks):
        e = fs[k + 1] if k + 1 < len(fs) else nf
        if e - cur <= 0:
            continue
        note_midi.append(float(m))
        note_rest.append(False)
        note_dur.append(e - cur)
        cur = e
    return {'op': 'pitch', 'phonemes': p['phonemes'], 'ph_dur': p['durations'], 'note_midi': note_midi,
            'note_rest': note_rest, 'note_dur': note_dur, 'pitch': p['midi'],
            'expr': float(spec['params'].get('expr', STYLE_EXTRAS['expr'])), 'retake': True,
            'speaker': {(_soft_speaker(spec) if spec['params'].get('sing_soft') and spec['moves']
                         else bank.mode('core')): 1.0}, 'steps': 10}


def _sing_job(p: dict, spec: dict, bank, path: Path) -> dict:
    S = spec['params']
    f0 = [round(440.0 * 2 ** ((m - 69) / 12.0), 3) for m in p['midi']]
    rngk = bank.key_shift_range or 5.0
    return {'op': 'sing', 'phonemes': p['phonemes'], 'durations': p['durations'], 'f0': f0,
            'gender': max(-1.0, min(1.0, spec['formant'] / rngk)),
            'velocity': S['speed'] if spec['moves'] else 1.0, 'speaker': p['mix'], 'steps': int(S['steps']),
            'depth': 0.6, 'gain_db': p['gain'], 'out': _vb.wsl_path(path)}


def _write_track(song, t) -> None:
    """Zones + trigger notes of a vocal track from its parts' rendered phrases (exact, through the tempo map)."""
    from .patches import inst
    from .patterns import Note
    tm = song.tempo_map()
    zones, notes = [], []
    key = 0
    for vo in t._singer['parts']:
        vo.keys = []
        match = vo.level_match_db = _level_match(vo)
        for r in vo.rendered:
            path = Path(r['path'])
            meta = json.loads(path.with_suffix('.json').read_text(encoding='utf-8'))
            off = float(meta['timeline']['offset_s'])
            ph = vo.phrases[r['phrase']]
            a = vo.notes[ph[0]]
            z = vo.notes[ph[-1]]
            t_start = song.seconds(a.start) + off + vo.offset_ms / 1000.0
            st = tm.beat_at(max(0.0, t_start)) if t_start > 0 else 0.0
            zone = {'file': str(path.resolve()).replace(os.sep, '/'), 'root': key, 'lo': key, 'hi': key}
            mk = makeup_db(vo) + match
            if mk:
                zone['gain'] = round(mk, 3)
            if t_start < 0:          # a take whose breath / consonants start before the song: skip that much of it
                zone['offset'] = int(round(-t_start * SR))
            # the trigger lasts as long as the sung notes (one-shot: the file plays out anyway); the phrase ends where
            # the score's last note ends - what echo throws, the mixer and the report read
            end_b = z.start + z.dur + vo.offset_ms / 1000.0 * song.tempo_at(z.start) / 60.0
            zones.append(zone)
            notes.append(Note(st, max(0.05, end_b - st), key, 127))
            vo.keys.append(key)
            key += 1
    old = t.instrument
    params = {k: v for k, v in old.params.items() if k not in ('zones', 'samples')}
    params.update(oneshot='on', velsens=0)
    ins = inst.sampler(zones=zones, **params)
    ins.info = old.info
    t.instrument = ins
    t._notes = notes
    t._origin = ['singer.render'] * len(notes)


LEVEL_MATCH_DB = 12.0
"""The most a prism voice's takes are raised / lowered to match the lead's (a low voice in the bottom of the bank's range
sings several dB quieter: Hanami at A3 ~11 dB under her A4)."""


def take_db(path) -> float:
    """The active level of a rendered take (dBFS): the power of its 50 ms blocks within 30 dB of the loudest one
    (breaths and the silence around the phrase left out)."""
    from .speech import _read_pcm16
    x, sr = _read_pcm16(path)
    n = max(1, int(0.05 * sr))
    ps = [sum(v * v for v in x[i:i + n]) / n for i in range(0, max(1, len(x) - n + 1), n)]
    top = max(ps) if ps else 0.0
    act = [p for p in ps if p > top * 1e-3]
    return 10.0 * math.log10(max(1e-12, sum(act) / max(1, len(act))))


def _level_match(vo) -> float:
    """The zone gain (dB) that brings a part's takes to the active level of its level_ref's takes (phrase by phrase,
    averaged; +-LEVEL_MATCH_DB), 0 without a reference or a rendered take."""
    ref = vo.level_ref
    if ref is None:
        return 0.0
    mine = {r['phrase']: r['path'] for r in vo.rendered}
    diffs = []
    for r in ref.rendered:
        p = mine.get(r['phrase'])
        try:
            if p is not None:
                diffs.append(take_db(r['path']) + makeup_db(ref) - take_db(p) - makeup_db(vo))
        except (OSError, ValueError, EOFError):
            continue
    if not diffs:
        return 0.0
    return max(-LEVEL_MATCH_DB, min(LEVEL_MATCH_DB, sum(diffs) / len(diffs)))


def makeup_db(vo) -> float:
    """The static make-up gain (dB, on the take's zone) of a part sung with sing_soft (0 otherwise)."""
    S = vo.params
    if not S.get('sing_soft') or not vo.moves_on:
        return 0.0
    if S.get('makeup_db') is not None:
        return float(S['makeup_db'])
    return float(SOFT_MAKEUP_DB.get(vo.bank.id, 0.0))


def phrase_notes(track) -> list:
    """The sung phrases of a vocal track as notes (first sung note's beat .. last note's end): what the phrase-end
    logic of other modules reads (heroes' echo throws) instead of the takes' trigger notes, which start early (the
    breath and consonants before the beat)."""
    from .patterns import Note
    out = []
    for vo in track._singer['parts']:
        lag = vo.offset_ms / 1000.0
        for k, ph in enumerate(vo.phrases):
            a, z = vo.notes[ph[0]], vo.notes[ph[-1]]
            sh = lag * vo.song.tempo_at(a.start) / 60.0
            out.append(Note(a.start + sh, max(0.05, z.start + z.dur - a.start), vo.keys[k] if k < len(vo.keys) else 0,
                            100))
    return sorted(out, key=lambda n: n.start)


# ------------------------------------------------------------------------------------------------ expression
# Four singer techniques on top of the moves (a separate block: the plan above stays as it was, every technique draws
# from its own random stream, a part that uses none of them sings - and caches - exactly as before):
#   back_phrase   whole phrases laid back against the band and caught up by a landing note (Holiday / Sinatra)
#   ornament      the first statement of a melody plain, its repeats embellished (grace, turn, run, blue note ...)
#   messa         messa di voce on held peaks: the take's colour swells (soft -> core / power -> soft) and the level
#                 swells AFTER the vocal compressor (the 'air' stage), so the compressor does not flatten it
#   emphasis      the lyrics' markup: *word* leaned into, (( ... )) sung intimate and close; 'auto': the title words

MOVES = MOVES + ('back_phrase', 'ornament', 'blue', 'messa', 'emphasis', 'intimate')
__all__ += ['CALM_STYLES', 'BACK_PHRASE', 'ORNAMENT', 'MESSA', 'EMPHASIS', 'ORNAMENT_KINDS', 'expression_lines']

CALM_STYLES = ('jazz', 'ballad')
"""The calm, intimate styles: a back-phrased phrase there only ever lays BACK (HUMAN_FEEDBACK "sie klingt gerusht":
never push ahead of the band)."""

BACK_PHRASE = {
    # late: (lo, hi) beats a phrase starts behind the written rhythm; early: the share of the back-phrased phrases
    # pushed AHEAD instead (anticipated; 0 in the calm styles - and refused there); chance: per eligible phrase;
    # every: bars between two (the budget, song-wide with a Memory); min_beats: the shortest stretch from the phrase's
    # first note to its landing note (a bar line inside the phrase, else its last syllable); min_notes: per phrase
    'jazz':   dict(on=True, late=(0.12, 0.25), early=0.0, chance=0.6, every=4.0, min_beats=2.0, min_notes=3),
    'ballad': dict(on=True, late=(0.08, 0.18), early=0.0, chance=0.5, every=4.0, min_beats=2.0, min_notes=3),
    'pop':    dict(on=False, late=(0.06, 0.15), early=0.35, chance=0.4, every=4.0, min_beats=2.0, min_notes=3),
    'rock':   dict(on=False, late=(0.05, 0.12), early=0.45, chance=0.35, every=4.0, min_beats=2.0, min_notes=3),
}
"""BACK-PHRASING (move 'back_phrase'): the singer delays (or, pop / rock, anticipates) a whole phrase against the
band's steady time and catches up by its landing note - the next bar line inside the phrase, else its last
syllable: an offset curve d x (1 - ease(u)) over the stretch (late at the start, the middle compressed, exactly on the
target). Its notes move with it (consonants, breath, glides follow the vowels); the style's lay-back (late_ms) comes
on top. A part sung over an earlier one (a double, a harmony) follows that part's phrasing note for note."""

ORNAMENT_KINDS = ('grace', 'turn', 'run', 'blue', 'neighbour', 'anticipation')
ORNAMENT = {
    # amount: the chance an eligible note of a melody's SECOND statement gets one (before the budget); grow: +amount
    # x this per further statement; end: +amount x this toward the song's end (linear in the position); every: bars
    # between two ornaments (budget, song-wide with a Memory); same_every: bars between two of one kind; ms: one
    # ornament note (a voice is slower than fingers); first: True = a first statement is embellished too; kinds:
    # the weights of ORNAMENT_KINDS
    'jazz':   dict(on=True, amount=0.35, grow=0.5, end=0.6, every=2.0, same_every=8.0, ms=115.0, first=False,
                   kinds=dict(grace=1.0, turn=0.7, run=0.5, blue=1.0, neighbour=0.6, anticipation=0.8)),
    'ballad': dict(on=True, amount=0.3, grow=0.5, end=0.6, every=2.0, same_every=8.0, ms=125.0, first=False,
                   kinds=dict(grace=1.0, turn=0.8, run=0.6, blue=0.3, neighbour=0.5, anticipation=0.7)),
    'pop':    dict(on=False, amount=0.35, grow=0.5, end=0.6, every=2.0, same_every=8.0, ms=95.0, first=False,
                   kinds=dict(grace=0.8, turn=0.5, run=1.0, blue=0.3, neighbour=0.6, anticipation=0.8)),
    'rock':   dict(on=False, amount=0.3, grow=0.5, end=0.6, every=2.0, same_every=8.0, ms=90.0, first=False,
                   kinds=dict(grace=1.0, turn=0.2, run=0.6, blue=0.8, neighbour=0.4, anticipation=0.6)),
}
"""ORNAMENTATION ON REPEATS (move 'ornament'; 'blue' for the blue note): the first statement of a melody is sung plain,
its later statements (a 2nd verse, the last chorus, an out chorus - recognised by the Memory's record of the melodies
sung: the same interval sequence) get sparse embellishments, more on every further statement and toward the song's
end. The kinds (the shared ornaments of agentsound.pianist / agentsound.romantic, at a voice's speed, sung as a
melisma on the note's own syllable - the lyrics' run mechanics, so the words stay where they are):
  grace         a crushed grace note into a held note (pianist.crush: a half step below in jazz, a step else)
  turn          a turn at the end of a held note, leading into the next (romantic.turn, where='after')
  run           a small run on an open vowel at a phrase end: up a third and back (romantic.fioritura, 'arch')
  blue          the blue note on a held 3rd / 7th of a major key: sung from the flat (b3 / b7), bent up slowly
  neighbour     an upper neighbour flicked in after the attack (pianist.mordent, upper=True)
  anticipation  the next note's pitch reached early, on the end of this note's vowel"""

MESSA = {
    # chance: per held peak; every: bars between two (budget); min_s: the shortest held peak (s); lo / peak / end: dB of
    # the level lane (after the compressor) at the vowel's start / middle / end, scaled by the note's length; colour:
    # the weight of the core mode (sing_soft styles) / power mode (the blend) added at the swell's top; bright: the
    # tone that opens with the level (x dB, the mic stage's high shelf)
    'jazz':   dict(on=True, chance=0.7, every=2.0, min_s=0.8, lo=-2.0, peak=1.8, end=-1.5, colour=0.3, bright=0.3),
    'ballad': dict(on=True, chance=0.8, every=2.0, min_s=0.9, lo=-2.5, peak=2.2, end=-2.0, colour=0.35, bright=0.3),
    'pop':    dict(on=False, chance=0.6, every=4.0, min_s=0.9, lo=-2.5, peak=2.0, end=-2.0, colour=0.4, bright=0.35),
    'rock':   dict(on=False, chance=0.5, every=4.0, min_s=1.0, lo=-2.0, peak=2.0, end=-1.5, colour=0.45, bright=0.35),
}
"""MESSA DI VOCE (move 'messa'): on a long held note at a phrase's peak (its highest held note or a ^peak hook note -
never the phrase's last syllable: the phrase-end holds are the mic pull's, feat/mic-pull) the voice swells and recedes:
in the take the voice mode blends from the soft mode toward the core (sing_soft) / power mode and back, and the level
lane after the vocal compressor ('fx.air.gain', hornist.render) rises from lo to peak and falls to end dB (written when
the song compiles, from the take's own vowel times). Replaces the in-take 'swell' on that note."""

EMPHASIS = {
    # db / shelf / prox: an emphasised word's level after the compressor, its brightness (the mic stage's high shelf)
    # and proximity, dB; colour: core (sing_soft) / power weight added on its vowel; cons: x its onset consonants'
    # length (crisper); cons_db: their lift in the take; vowel: x the share of the next note the consonants after the
    # word may take (< 1: the vowel holds longer); soft_db / soft_prox / soft_room / soft_shelf: an intimate line
    # ((( ... ))) - softer after the compressor, closer (proximity), drier, a touch darker; it sings the soft mode
    # alone; auto: emphasise the song's title words / ^peak hook words automatically (sing(emphasis='auto'));
    # auto_max: at most this many auto-emphasised words per phrase
    'jazz':   dict(on=True, db=1.5, shelf=1.5, prox=0.5, colour=0.2, cons=1.15, cons_db=2.0, vowel=0.75,
                   soft_db=-2.0, soft_prox=2.5, soft_room=-3.0, soft_shelf=-1.0, auto=False, auto_max=1),
    'ballad': dict(on=True, db=1.5, shelf=1.5, prox=0.5, colour=0.2, cons=1.15, cons_db=2.0, vowel=0.75,
                   soft_db=-2.0, soft_prox=2.5, soft_room=-3.0, soft_shelf=-1.0, auto=False, auto_max=1),
    'pop':    dict(on=True, db=2.0, shelf=2.0, prox=0.5, colour=0.25, cons=1.15, cons_db=2.5, vowel=0.75,
                   soft_db=-2.5, soft_prox=2.5, soft_room=-3.0, soft_shelf=-1.0, auto=False, auto_max=1),
    'rock':   dict(on=True, db=2.0, shelf=2.0, prox=0.5, colour=0.3, cons=1.1, cons_db=2.5, vowel=0.8,
                   soft_db=-2.5, soft_prox=2.0, soft_room=-2.5, soft_shelf=-1.0, auto=False, auto_max=1),
}
"""WORD EMPHASIS (moves 'emphasis' / 'intimate'), from the lyrics' markup (agentsound.lyrics): `*word*` - the singer
leans into it: a little louder and brighter after the compressor, a touch more core / power mode, a crisper (longer,
lifted) onset consonant and a longer vowel; `(( ... ))` - an intimate, near-whispered line: the soft mode alone,
softer, closer (proximity) and drier. emphasis='auto' adds the title / hook words. The codas keep their diction (the
take's consonant lift is untouched; the level moves sit after the chain over the whole word)."""

_STOP = {'a', 'an', 'the', 'on', 'in', 'of', 'to', 'and', 'or', 'but', 'is', 'am', 'are', 'i', 'you', 'me', 'my',
         'we', 'it', 'at', 'by', 'for', 'so', 'be', 'as', 'up', 'down'}
_NAMES = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B']


def _xopts(table: dict, style: str, value, what: str, number: str) -> dict:
    """sing(<technique>=) -> the settings of the style: None = the style's, True / False = on / off, a number = `number`
    (its key), a dict = these keys (on, unless it says on=False)."""
    O = {k: (dict(v) if isinstance(v, dict) else v) for k, v in table[style].items()}
    if value is None:
        return O
    if isinstance(value, bool):
        O['on'] = value
        return O
    if isinstance(value, (int, float)):
        O['on'] = True
        O[number] = float(value)
        return O
    if isinstance(value, dict):
        bad = sorted(k for k in value if k not in O)
        if bad:
            raise SingerError(f"{what}: unknown key(s) {bad} (keys: {', '.join(O)})")
        for k, v in value.items():
            O[k] = {**O[k], **v} if isinstance(O[k], dict) and isinstance(v, dict) else v
        O['on'] = bool(value.get('on', True))
        return O
    raise SingerError(f"{what} must be None, True / False, a number or a dict, got {value!r}")


def _expr_options(style: str, S: dict, back_phrase, ornament, messa, emphasis) -> dict:
    bp = _xopts(BACK_PHRASE, style, back_phrase, 'back_phrase', 'late')
    if isinstance(bp['late'], (int, float)):
        bp['late'] = (0.5 * float(bp['late']), float(bp['late']))
    lo, hi = bp['late']
    if not 0.0 <= lo <= hi <= 1.0:
        raise SingerError(f"back_phrase late = {bp['late']!r}: (lo, hi) beats, 0 <= lo <= hi <= 1")
    calm = style in CALM_STYLES or S.get('sing_soft')
    if calm and bp['early']:
        raise SingerError(f"back_phrase early = {bp['early']}: a calm style ({style}) never pushes a phrase ahead of the "
                          f"band (HUMAN_FEEDBACK 'gerusht') - lay back only (early=0)")
    om = _xopts(ORNAMENT, style, ornament, 'ornament', 'amount')
    bad = sorted(k for k in om['kinds'] if k not in ORNAMENT_KINDS)
    if bad:
        raise SingerError(f"ornament kinds {bad}: the kinds are {', '.join(ORNAMENT_KINDS)}")
    om['_style'] = style
    om['_off'] = ornament is False             # said so: not even a double's replay
    ms = _xopts(MESSA, style, messa, 'messa_di_voce', 'peak')
    if isinstance(emphasis, str):
        if emphasis != 'auto':
            raise SingerError(f"emphasis must be None, True / False, 'auto', a number (dB) or a dict, got {emphasis!r}")
        em = _xopts(EMPHASIS, style, None, 'emphasis', 'db')
        em.update(on=True, auto=True)
    else:
        em = _xopts(EMPHASIS, style, emphasis, 'emphasis', 'db')
    return {'back_phrase': bp, 'ornament': om, 'messa': ms, 'emphasis': em}


def _registry(song) -> dict:
    """The song's record of what its singers did (warps by beat, ornamented notes, melodies when no Memory): a part
    sung later over an earlier one (a double, a harmony) follows it."""
    return song.__dict__.setdefault('_singer_expr', {'warps': [], 'notes': {}, 'melodies': [], 'beats': set()})


def _sung_key(song, transpose: int):
    k = Key(song.key) if getattr(song, 'key', None) is not None else Key('C major')
    if transpose:
        k = Key(_NAMES[(k.tonic + int(transpose)) % 12], k.mode)
    return k


def _express(song, notes: list, phrases: list, S: dict, O: dict, sd: int, memory, base: float, moves_on: bool,
             transpose: int, split_s: float):
    """Back-phrasing, emphasis marks and ornaments on the part's notes (song beats) before the moves are planned ->
    (notes, phrases, info). info: what was decided (logged after the plan) and the pending plan entries (blue)."""
    reg = _registry(song)
    info = {'back_phrase': [], 'ornaments': [], 'emphasis': [], 'blue': {}, 'follow': False, 'statement': None,
            'src': [(n.start, n.dur, n.pitch, n.vel) for n in notes]}
    if not notes:
        return notes, phrases, info
    starts = {round(n.start, 3) for n in notes}
    over = len(starts & reg['beats']) / len(starts)
    info['follow'] = over >= 0.6                # sung over an earlier part: a double / a harmony follows it
    _back_phrase(song, notes, phrases, O['back_phrase'], sd, memory, base, moves_on, info, reg)
    _emphasis_marks(song, notes, phrases, O['emphasis'], moves_on, info)
    if moves_on:
        notes = _ornament(song, notes, phrases, S, O['ornament'], sd, memory, base, transpose, info, reg)
    reg['beats'] |= starts
    phrases = _phrases(notes, song.seconds, split_s)
    return notes, phrases, info


# ---- back-phrasing

def _landing(song, notes, ph, O) -> int | None:
    """The note a phrase catches up on: the first one on a bar line at least min_beats after its first note, else
    its last syllable (when far enough)."""
    a = notes[ph[0]].start
    grid = song.meter_grid()
    for i in ph[1:]:
        n = notes[i]
        if n.kind != 'syllable' or n.start - a < O['min_beats'] - 1e-9:
            continue
        x = grid.bar_at(n.start)
        if abs(x - round(x)) < 1e-6:
            return i
    last = max((i for i in ph if notes[i].kind == 'syllable'), default=None)
    if last is not None and notes[last].start - a >= O['min_beats'] - 1e-9:
        return last
    return None


def _warp(t: float, t0: float, land: float, d: float) -> float:
    if t >= land:
        return t
    if t <= t0:
        return t + d
    u = (t - t0) / (land - t0)
    return t + d * (1.0 - (0.5 - 0.5 * math.cos(math.pi * u)))


def _back_phrase(song, notes, phrases, O, sd, memory, base, moves_on, info, reg) -> None:
    rng = random.Random(sd * 17 + 40013)
    secs = song.seconds
    decided = []
    cands = []
    for k, ph in enumerate(phrases):
        a = notes[ph[0]].start
        z = notes[ph[-1]].start + notes[ph[-1]].dur
        follow = [w for w in reg['warps'] if w['t0'] < z - 1e-6 and a < w['end'] - 1e-6]
        r_ok, r_d, r_e = rng.random(), rng.random(), rng.random()        # one draw per phrase (stable streams)
        if follow:
            decided.append((k, follow, True))
            continue
        land = _landing(song, notes, ph, O) if moves_on and O['on'] else None
        if land is None or len(ph) < O['min_notes'] or r_ok >= O['chance']:
            decided.append((k, dict(t0=a, land=a, d=0.0, end=z), False))
            continue
        lo, hi = O['late']
        d = lo + (hi - lo) * r_d
        if r_e < O['early']:               # pushed ahead (pop / rock): never into the previous phrase's breath
            prev_end = notes[phrases[k - 1][-1]].start + notes[phrases[k - 1][-1]].dur if k else base - 4.0
            d = -min(d, max(0.0, a - prev_end - 0.25))
        if abs(d) < 0.02:
            decided.append((k, dict(t0=a, land=a, d=0.0, end=z), False))
            continue
        span = notes[land].start - a
        score = 1.0 + 0.25 * min(4.0, span) + 0.1 * len(ph)
        cands.append(dict(t=a - base, cls='phrasing', name='back_phrase', score=score, k=k,
                          w=dict(t0=a, land=notes[land].start, d=d, end=z)))
    bud = memory.budget if memory is not None else Budget({})
    bud.every['phrasing'] = float(O['every']) * 4.0 or 1e-3
    kept = {id(c) for c in bud.keep(cands, base, slots=False)} if cands else set()
    for c in cands:
        decided.append((c['k'], c['w'] if id(c) in kept else dict(c['w'], land=c['w']['t0'], d=0.0), False))
    for k, w, followed in sorted(decided, key=lambda x: x[0]):
        ph = phrases[k]
        ws = w if followed else [w]
        if not followed:
            reg['warps'].append(dict(w))
        if all(abs(x['d']) < 1e-9 for x in ws):
            continue
        offs = []
        for i in ph:
            n = notes[i]
            s0, e0 = n.start, n.start + n.dur
            x = next((x for x in ws if x['t0'] - 1e-6 <= s0 < x['end'] - 1e-6), None)
            if x is not None and abs(x['d']) > 1e-9:
                s1, e1 = _warp(s0, x['t0'], x['land'], x['d']), _warp(e0, x['t0'], x['land'], x['d'])
                n.start, n.dur = s1, max(0.02, e1 - s1)
            offs.append((n.start - s0) * 60.0 / song.tempo_at(s0) * 1000.0)
        a = notes[ph[0]].start
        x0 = next((x for x in ws if abs(x['d']) > 1e-9), ws[0])
        info['back_phrase'].append(dict(beat=round(a, 4), ms=round(offs[0], 1), beats=round(x0['d'], 3),
                                        land=round(x0['land'], 4), notes=sum(1 for x in offs if abs(x) > 0.5),
                                        follow=followed, word=notes[ph[0]].syl.word,
                                        mean_ms=round(sum(offs) / len(offs), 1)))


# ---- word emphasis

def _emphasis_marks(song, notes, phrases, O, moves_on, info) -> None:
    """The lyrics' markup (and emphasis='auto') onto the notes (n.emph)."""
    if not (moves_on and O['on']):
        for n in notes:
            n.emph = ''
        return
    if O.get('auto'):
        title = {w for w in re.findall(r"[a-z']+", str(getattr(song, 'title', '')).lower()) if w not in _STOP
                 and len(w) >= 3}
        for ph in phrases:
            words = {}
            for i in ph:
                n = notes[i]
                w = n.syl.word.lower()
                if n.kind == 'syllable' and n.syl.stress == 1 and (w in title or n.hook) and w not in _STOP:
                    words.setdefault(w, []).append(i)
            best = sorted(words.items(), key=lambda kv: -max(notes[i].dur for i in kv[1]))[:int(O['auto_max'])]
            for _, idx in best:
                for i in idx:
                    if not notes[i].emph:
                        notes[i].emph = 'emph'
                        notes[i].auto = True
    # a melisma / hold continues its syllable's mark
    for i in range(1, len(notes)):
        if notes[i].kind != 'syllable' and not notes[i].emph:
            notes[i].emph = notes[i - 1].emph
    seen = set()
    for i, n in enumerate(notes):
        if n.emph and n.kind == 'syllable' and n.word_start:
            key = (n.emph, round(n.start, 3))
            if key not in seen:
                seen.add(key)
                info['emphasis'].append(dict(beat=round(n.start, 4), word=n.syl.word, kind=n.emph,
                                             auto=bool(getattr(n, 'auto', False))))


# ---- ornaments on repeats

def _signature(notes) -> tuple:
    ps = [n.pitch for n in notes if n.kind == 'syllable']
    return tuple(b - a for a, b in zip(ps, ps[1:]))


def _statement(sig: tuple, store: list) -> int:
    """How many times this melody was sung before (the same interval sequence, >= 80 % alike); records it."""
    import difflib
    for rec in store:
        s = rec[0]
        if not s or not sig or min(len(s), len(sig)) / max(len(s), len(sig)) < 0.7:
            continue
        if difflib.SequenceMatcher(None, s, sig, autojunk=False).ratio() >= 0.8:
            rec[1] += 1
            return rec[1] - 1
    store.append([sig, 1])
    return 0


def _orn_notes(kind: str, n, d_s: float, nxt, bpm: float, key, O, rng) -> list:
    """The ornament's notes [(start beat, pitch, vel)] over note n (song beats) from the shared ornaments."""
    from . import pianist as _pn
    from . import romantic as _ro
    ms = float(O['ms']) * (0.9 + 0.2 * rng.random())
    a, D, p, v = n.start, n.dur, n.pitch, n.vel
    if kind == 'grace':
        c = _pn.crush(p, D, bpm, grace=-1 if O.get('_jazzy') else -2 if not key.contains(p - 1) else -1,
                      ms=min(90.0, 0.7 * ms), vel=v, at=a)
    elif kind == 'turn':
        c = _ro.turn(p, D, bpm, at=a, key=key, where='after', ms=ms, vel=v, light=10.0)
    elif kind == 'neighbour':
        c = _pn.mordent(p, D, bpm, upper=True, key=key, ms=ms, vel=v, light=12.0, at=a)
    elif kind == 'run':
        up1 = next(q for q in range(p + 1, p + 3) if key.contains(q))
        up2 = next(q for q in range(up1 + 1, up1 + 3) if key.contains(q))
        dur = min(D * 0.45, 5 * ms / 1000.0 * bpm / 60.0 * 1.15)
        at = a + min(0.3 * D, D - dur - 0.15 * D)
        c = _ro.fioritura([p, up1, up2, up1, p], dur, bpm, at=at, vel=(v, v - 4), max_rate=14.0, wobble_ms=0.0)
        c = [(a, 0.0, p, v)] + [(x.start, 0.0, x.pitch, x.vel) for x in c]
        return [(s, q, w) for s, _, q, w in c]
    elif kind == 'anticipation':
        tail = min(0.3 * D, 0.2 * bpm / 60.0)
        return [(a, p, v), (a + D - tail, nxt.pitch, max(1, nxt.vel - 8))]
    else:
        raise SingerError(f"unknown ornament {kind!r}")
    return [(x.start, x.pitch, x.vel) for x in c]


def _ornament(song, notes, phrases, S, O, sd, memory, base, transpose, info, reg) -> list:
    """Ornaments on a repeated melody: decided per note, budgeted, then sung as melisma notes of the note's own
    syllable (blue: a pitch move, applied to the plan later)."""
    secs = song.seconds
    store = memory.melodies if memory is not None else reg['melodies']
    replay = info['follow'] and not O.get('_off')
    if not replay:
        info['statement'] = _statement(_signature(notes), store)
    st = info['statement']
    if replay:
        # a double sings the ornaments of the part it doubles (same beat, same pitch); a harmony none
        plan = {i: reg['notes'][(round(notes[i].start, 3), notes[i].pitch)]
                for i in range(len(notes)) if (round(notes[i].start, 3), notes[i].pitch) in reg['notes']}
        return _apply_ornaments(song, notes, plan, O, sd, transpose, info, reg, record=False)
    if not O['on'] or (st == 0 and not O['first']):
        return notes
    rng = random.Random(sd * 29 + 7019)
    key = _sung_key(song, transpose)
    jazzy = O.get('_style') == 'jazz'
    L = max(1.0, float(song.length))
    amount = float(O['amount']) * (1.0 + float(O['grow']) * max(0, st - 1))
    kinds = {k: float(w) for k, w in O['kinds'].items() if w > 0}
    cands = []
    for ph in phrases:
        last_syl = max((i for i in ph if notes[i].kind == 'syllable'), default=None)
        for i in ph:
            n = notes[i]
            r_on, r_kind = rng.random(), rng.random()
            if n.kind != 'syllable' or (i + 1 < len(notes) and notes[i + 1].kind != 'syllable'):
                continue
            if n.syl.word.lower() in _STOP:        # a singer embellishes the words that carry the line, not 'the'
                continue
            d_s = secs(n.start + n.dur) - secs(n.start)
            nxt = notes[i + 1] if i + 1 < len(notes) and i + 1 in ph else None
            legato_next = nxt is not None and nxt.start - (n.start + n.dur) < 0.1
            pc = (n.pitch - key.tonic) % 12
            ok = {}
            if d_s >= 0.5:
                ok['grace'] = 1.0
            if d_s >= 0.8 and legato_next:
                ok['turn'] = 1.0
            if d_s >= 1.0 and i == last_syl and _lyr.vowel_class(n.syl.nucleus) == 'open':
                ok['run'] = 1.3
            if d_s >= 0.5 and not key.minorish and pc in (4, 11):
                ok['blue'] = 1.0
            if 0.45 <= d_s and not (i == last_syl):
                ok['neighbour'] = 0.8
            if d_s >= 0.5 and legato_next and nxt.pitch != n.pitch and nxt.kind == 'syllable':
                ok['anticipation'] = 0.9
            ws = [(k, kinds[k] * ok[k]) for k in ORNAMENT_KINDS if k in ok and k in kinds]
            if not ws:
                continue
            pos = min(1.0, max(0.0, n.start / L))
            if r_on >= min(0.95, amount * (1.0 + float(O['end']) * pos)):
                continue
            tot = sum(w for _, w in ws)
            x, kind = r_kind * tot, ws[-1][0]
            for k, w in ws:
                if x < w:
                    kind = k
                    break
                x -= w
            score = 1.0 + 0.4 * min(3.0, d_s) + (0.6 if i == last_syl else 0.0) + 0.5 * pos
            cands.append(dict(t=n.start - base, kind=kind, i=i, score=score))
    bud = memory.budget if memory is not None else Budget({})
    bud.every['ornament'] = float(O['every']) * 4.0 or 1e-3
    for k in ORNAMENT_KINDS:
        bud.every[f'ornament:{k}'] = float(O['same_every']) * 4.0 or 1e-3
    plan = {}
    for c in sorted(cands, key=lambda c: (-c['score'], c['t'])):
        T = base + c['t']
        if bud.allows(T, 'ornament') and bud.allows(T, f"ornament:{c['kind']}"):
            bud.book(T, 'ornament', c['kind'])
            bud.book(T, f"ornament:{c['kind']}", c['kind'])
            plan[c['i']] = dict(kind=c['kind'], jazzy=jazzy)
    return _apply_ornaments(song, notes, plan, O, sd, transpose, info, reg, record=True, memory=memory)


def _apply_ornaments(song, notes, plan, O, sd, transpose, info, reg, record, memory=None) -> list:
    if not plan:
        return notes
    rng = random.Random(sd * 31 + 9029)
    key = _sung_key(song, transpose)
    secs = song.seconds
    out = []
    for i, n in enumerate(notes):
        p = plan.get(i)
        if p is None:
            out.append(n)
            continue
        kind = p['kind']
        if record:
            reg['notes'][(round(n.start, 3), n.pitch)] = dict(p)
            if memory is not None:
                memory.used.append((round(n.start, 4), kind, n.syl.word))
        d_s = secs(n.start + n.dur) - secs(n.start)
        entry = dict(beat=round(n.start, 4), kind=kind, word=n.syl.word, pitch=n.pitch, held_s=round(d_s, 3),
                     statement=info['statement'], follow=not record)
        if kind == 'blue':
            cents = -100.0
            ms_ = round(200.0 + 80.0 * rng.random(), 1)
            info['blue'][(round(n.start, 6), n.pitch)] = dict(cents=cents, ms=ms_)
            info['ornaments'].append(dict(entry, cents=cents, ms=ms_))
            out.append(n)
            continue
        nxt = notes[i + 1] if i + 1 < len(notes) else None
        if kind == 'anticipation' and (nxt is None or nxt.kind != 'syllable'):
            out.append(n)
            continue
        O2 = dict(O, _jazzy=p.get('jazzy', False))
        try:
            pts = _orn_notes(kind, n, d_s, nxt, song.tempo_at(n.start), key, O2, rng)
        except ComposeError:
            out.append(n)            # too short for it at this tempo: sung plain
            continue
        end = n.start + n.dur
        seq = []
        for s, q, v in sorted(pts, key=lambda x: x[0]):
            s = min(max(n.start, s), end)
            if seq and abs(s - seq[-1][0]) < 1e-6:
                seq[-1] = (seq[-1][0], q, seq[-1][2])
            elif seq and seq[-1][1] == q:
                continue
            else:
                seq.append((s, q, v))
        # every sub-note sounds at least 50 ms
        sub = []
        for k, (s, q, v) in enumerate(seq):
            e = seq[k + 1][0] if k + 1 < len(seq) else end
            if secs(e) - secs(s) < 0.05 and sub:
                continue
            sub.append((s, q, v))
        if len(sub) < 2:
            out.append(n)
            continue
        for k, (s, q, v) in enumerate(sub):
            e = sub[k + 1][0] if k + 1 < len(sub) else end
            first, lastk = k == 0, k == len(sub) - 1
            m = _SNote(s, max(0.02, e - s), int(q), int(max(1, min(127, round(v if not first else n.vel)))),
                       n.kind if first else 'melisma', n.syl, n.word_start and first, n.word_end and lastk,
                       n.mark if lastk else '', n.hook, n.emph)
            out.append(m)
        info['ornaments'].append(dict(entry, notes=[int(q) for _, q, _ in sub]))
    return out


# ---- after the plan: blue notes, emphasis and messa di voce on the plan (before the mic pull: the peaks are the
# messa's, the phrase-end holds the mic pull's - never both on one note)

def _express_plan(song, notes, phrases, plan, log, info: dict, O: dict, sd: int, memory, base: float,
                  moves_on: bool) -> tuple[list, set]:
    """The pending plan entries of the expression (blue notes, emphasis, messa di voce) and their log lines ->
    (messa records, the note indices the messa took: the mic pull leaves them alone)."""
    secs = song.seconds
    for b in info['back_phrase']:
        log.append((b['beat'], 'back_phrase', {k: b[k] for k in ('ms', 'beats', 'land', 'notes', 'follow')}))
    for o in info['ornaments']:
        log.append((o['beat'], 'blue' if o['kind'] == 'blue' else 'ornament',
                    {k: o[k] for k in ('kind', 'word', 'held_s', 'statement') if k in o}))
    for i, n in enumerate(notes):
        bl = info['blue'].get((round(n.start, 6), n.pitch))
        if bl and n.kind == 'syllable':
            plan[i]['blue'] = dict(bl)
            if 'scoop' in plan[i]:                  # the blue bend replaces a scoop into the note
                sc = plan[i].pop('scoop')
                log[:] = [x for x in log if not (x[1] == 'scoop' and x[2] is sc)]
    E = O['emphasis']
    for i, n in enumerate(notes):
        if n.emph and moves_on and E['on']:
            plan[i]['emph'] = (dict(kind='emph', colour=E['colour'], cons=E['cons'], cons_db=E['cons_db'],
                                    vowel=E['vowel']) if n.emph == 'emph' else dict(kind='intimate'))
    for e in info['emphasis']:
        log.append((e['beat'], 'emphasis' if e['kind'] == 'emph' else 'intimate', {'word': e['word'],
                                                                                    'auto': e['auto']}))
    M = O['messa']
    messa, taken = [], set()
    if moves_on and M['on']:
        rng = random.Random(sd * 37 + 3301)
        cands = []
        for ph in phrases:
            groups = []
            for i in ph:
                if notes[i].kind == 'syllable' or not groups:
                    groups.append([i])
                else:
                    groups[-1].append(i)
            peak = next((i for i in ph if plan[i].get('peak')), None)
            for g in groups[:-1]:               # never the phrase's last syllable (the mic pull's phrase-end hold)
                r_on, r_j = rng.random(), rng.random()
                held = secs(notes[g[-1]].start + notes[g[-1]].dur) - secs(notes[g[0]].start)
                is_peak = peak in g or any(notes[i].hook for i in g)
                if (not is_peak or held < M['min_s'] - 1e-9 or r_on >= M['chance']
                        or notes[g[0]].emph == 'intimate'):
                    continue
                f = min(1.0, 0.45 + 0.4 * held) * (1.0 + 0.15 * (2 * r_j - 1))
                prm = dict(lo=round(M['lo'] * f, 2), peak=round(M['peak'] * f, 2), end=round(M['end'] * f, 2),
                           colour=round(M['colour'] * min(1.0, f), 3), bright=float(M['bright']),
                           held_s=round(held, 3), word=notes[g[0]].syl.word)
                cands.append(dict(t=notes[g[0]].start - base, cls='messa', name='messa', score=1.0 + held, g=g,
                                  params=prm))
        bud = memory.budget if memory is not None else Budget({})
        bud.every['messa'] = float(M['every']) * 4.0 or 1e-3
        for c in (bud.keep(cands, base, slots=False) if cands else []):
            g = c['g']
            for i in g:
                plan[i].pop('swell', None)          # the messa replaces an in-take swell on the note
            beats = {round(notes[i].start, 4) for i in g}
            log[:] = [x for x in log if not (x[1] == 'swell' and x[0] in beats)]
            plan[g[0]]['messa'] = dict(c['params'], n=len(g))
            messa.append(dict(c['params'], beat=round(notes[g[0]].start, 4)))
            taken |= set(g)
            log.append((round(notes[g[0]].start, 4), 'messa', {k: c['params'][k] for k in ('lo', 'peak', 'end',
                                                                                            'colour', 'held_s')}))
    log.sort(key=lambda x: x[0])
    return messa, taken


def _express_record(vo, info: dict, O: dict, messa: list) -> None:
    """What the expression did on the part: vo.expression (and vo.src, the written notes)."""
    vo.expression = {'options': O, 'statement': info['statement'], 'follow': info['follow'],
                     'back_phrase': info['back_phrase'], 'ornaments': info['ornaments'], 'messa': messa,
                     'emphasis': info['emphasis'], 'post': []}
    vo.src = list(info['src'])


# ---- in the take (timeline / colour)

def _expr_cons(groups, on_len) -> None:
    """An emphasised syllable's onset consonants a little longer (crisper)."""
    for k, g in enumerate(groups):
        e = g['notes'][0]['plan'].get('emph')
        if e and e.get('kind') == 'emph' and k < len(on_len):
            on_len[k] = [x * float(e.get('cons', 1.0)) for x in on_len[k]]


def _expr_share(g) -> float:
    """The share of the next note the consonants after an emphasised syllable may take (x the style's): its vowel
    holds longer."""
    e = g['notes'][-1]['plan'].get('emph') or g['notes'][0]['plan'].get('emph')
    return float(e.get('vowel', 1.0)) if e and e.get('kind') == 'emph' else 1.0


def _onset_start(toks, V: float, nucleus: str | None = None) -> tuple[float, int | None]:
    """Where the consonants before the vowel starting at V start (phrase seconds), and the vowel token's index."""
    j = next((j for j, (p, a, b) in enumerate(toks) if abs(a - V) < 2e-3 and p not in ('SP', 'AP')
              and (nucleus is None or p == nucleus)), None)
    if j is None:
        return V, None
    a0, i = toks[j][1], j
    while i > 0 and toks[i - 1][0] not in ('SP', 'AP') and toks[i - 1][0] not in _lyr.SUNG_VOWELS:
        i -= 1
        a0 = toks[i][1]
    return a0, j


def _expr_curves(groups, ftime, toks):
    """Per frame: extra colour weight (messa / emphasis), intimate mask, onset lift dB - or None when the phrase has
    no expression (the take renders as before)."""
    nf = len(ftime)
    if not any(n['plan'].get('messa') or n['plan'].get('emph') for g in groups for n in g['notes']):
        return None
    col, soft, lift = [0.0] * nf, [0] * nf, [0.0] * nf
    for g in groups:
        p0 = g['notes'][0]['plan']
        V = g['V']
        ve = g.get('vend', g['end'])
        m = p0.get('messa')
        if m:
            for f, t in enumerate(ftime):
                if V <= t <= ve:
                    u = (t - V) / max(1e-6, ve - V)
                    col[f] += float(m['colour']) * math.sin(math.pi * u) ** 2
        e = p0.get('emph')
        a0, _ = _onset_start(toks, V, g['nu'])
        if e and e.get('kind') == 'intimate':
            for f, t in enumerate(ftime):
                if a0 - 0.03 <= t <= ve + 0.05:
                    soft[f] = 1
        elif e:
            for f, t in enumerate(ftime):
                if V <= t <= ve:
                    col[f] += float(e['colour']) * _ease(min(1.0, (t - V) / 0.06, (ve - t) / 0.06))
                elif a0 <= t < V:                  # the onset consonants lifted (crisper)
                    lift[f] = float(e.get('cons_db', 0.0))
    return col, soft, lift


def _expr_mix(curves, gain, mix: dict, bank, sing_soft: bool):
    """The colour of the expression on the take's voice-mode blend (and the onset lift on its gain)."""
    col, soft, lift = curves
    nf = len(col)
    for f in range(nf):
        gain[f] = round(gain[f] + lift[f], 3)
    core, soft_n, pow_n = bank.mode('core'), bank.mode('soft'), bank.mode('power')
    if sing_soft:
        out = {soft_n: [1.0] * nf}
        if any(col):
            out[core] = [round(0.0 if soft[f] else col[f], 4) for f in range(nf)]
        return out
    out = {k: (list(v) if isinstance(v, list) else [float(v)] * nf) for k, v in mix.items()}
    out.setdefault(pow_n, [0.0] * nf)
    out.setdefault(soft_n, [0.0] * nf)
    for f in range(nf):
        if soft[f]:                                  # intimate: the soft mode alone
            for k in out:
                out[k][f] = 0.0
            out[soft_n][f] = 1.0
        else:
            out[pow_n][f] = round(out[pow_n][f] + col[f], 4)
    return out


# ---- after the takes: the level / tone lanes after the compressor

def _expression_post(song, t) -> list:
    """The messa di voce / emphasis / intimate gestures of a vocal track's parts (song beats), from the takes'
    timelines - written by _write_mic together with the mic pulls in ONE hornist.render call (their lanes sum: an
    emphasised word that is also pulled back gets both; messa and mic pull never share a note)."""
    gs = []
    for vo in t._singer['parts']:
        if getattr(vo, 'expression', None) is None:
            continue
        vo.expression['post'] = []
        if not (vo.expression['messa'] or vo.expression['emphasis']):
            continue
        for r in vo.rendered:
            try:
                meta = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))
            except (OSError, ValueError):
                continue
            for post, ge in _expr_gestures(vo, r['phrase'], meta):
                vo.expression['post'].append(post)
                gs.append(ge)
    return gs


def _expr_gestures(vo, k: int, meta: dict) -> list:
    """The post-chain gestures of phrase k from its take's timeline: [(record, Gesture)] in song beats."""
    song = vo.song
    ph = vo.phrases[k]
    tl, spec = meta.get('timeline', {}), meta.get('spec', {})
    groups = _groups(spec.get('notes', []))
    vowels = list(tl.get('vowels', []))
    toks = [tuple(x) for x in tl.get('tokens', [])]
    if not groups or len(vowels) != len(groups):
        return []
    s0 = song.seconds(vo.notes[ph[0]].start)
    lag = vo.offset_ms / 1000.0
    tm = song.tempo_map()

    def B(x):
        return tm.beat_at(max(0.0, s0 + x + lag))
    E = vo.expression['options']['emphasis']
    dic = list(tl.get('diction', []))

    def vowel_end(gk):
        a0, j = _onset_start(toks, vowels[gk], groups[gk]['nu'])
        return (toks[j][2], j, a0) if j is not None else (groups[gk]['end'], None, vowels[gk])

    def word_end(gk, ve):
        nxt = vowels[gk + 1] if gk + 1 < len(vowels) else float('inf')
        cod = [d['b'] for d in dic if ve - 2e-3 <= d['a'] < nxt]       # the word-final consonants (+ a release)
        return max(cod) if cod else ve

    out, spans = [], []
    for gk, g in enumerate(groups):
        p0 = g['notes'][0].get('plan', {})
        V = vowels[gk]
        ve, j, a0 = vowel_end(gk)
        m = p0.get('messa')
        if m:
            nxt_on = vowel_end(gk + 1)[2] if gk + 1 < len(groups) else ve + 0.6
            a, b = B(V), B(ve)
            if b - a > 0.05:
                ge = G.messa_di_voce(a, b - a, song.tempo_at(a), lo=m['lo'], peak=m['peak'], end=m['end'],
                                     tied=True, back=B(nxt_on) + 1e-4, bright=float(m.get('bright', 0.0)))
                out.append((dict(kind='messa', word=m.get('word', g['w']), beat=round(a, 4), end_beat=round(b, 4),
                                 at_s=round(s0 + V + lag, 3), end_s=round(s0 + ve + lag, 3), lo=m['lo'],
                                 peak=m['peak'], end=m['end'], depth_db=round(m['peak'] - min(m['lo'], m['end']), 2),
                                 phrase=k), ge))
        e = p0.get('emph')
        if e and e.get('kind') == 'intimate':
            we = word_end(gk, ve)
            if spans and a0 - spans[-1][1] < 0.6:
                spans[-1] = (spans[-1][0], we, spans[-1][2] + ([g['w']] if g['ws'] else []))
            else:
                spans.append((a0, we, [g['w']]))
        elif e:
            we = word_end(gk, ve)
            a, b = B(a0), B(we)
            if b - a > 0.02:
                ge = G.lean(a, b - a, song.tempo_at(a), air=E['db'], shelf=E['shelf'], prox=E['prox'], ms=50.0,
                            name='emphasis')
                out.append((dict(kind='emphasis', word=g['w'], beat=round(a, 4), end_beat=round(b, 4),
                                 at_s=round(s0 + a0 + lag, 3), db=E['db'], shelf=E['shelf'], phrase=k), ge))
    for x0, x1, words in spans:                # an intimate run of words: one close, soft plateau
        a, b = B(x0), B(x1)
        if b - a > 0.05:
            ge = G.lean(a, b - a, song.tempo_at(a), air=E['soft_db'], prox=E['soft_prox'], room=E['soft_room'],
                        shelf=E['soft_shelf'], ms=200.0, name='intimate')
            out.append((dict(kind='intimate', words=' '.join(words), beat=round(a, 4), end_beat=round(b, 4),
                             at_s=round(s0 + x0 + lag, 3), db=E['soft_db'], prox=E['soft_prox'],
                             room=E['soft_room'], phrase=k), ge))
    return out


def expression_lines(target) -> list[str]:
    """What the expression did, per sung part (a Song, a vocal track or a Vocal): back-phrased phrases (ms at their
    start), ornaments (kind, word), messa di voce (depth), emphasised / intimate words; after a compile the lanes
    written after the compressor."""
    if isinstance(target, Vocal):
        parts = [target]
    elif getattr(target, '_singer', None):
        parts = list(target._singer['parts'])
    else:
        parts = [vo for t in getattr(target, 'tracks', {}).values() if getattr(t, '_singer', None)
                 for vo in t._singer['parts']]
    out = []
    for vo in parts:
        x = getattr(vo, 'expression', None)
        if not x or not (x['back_phrase'] or x['ornaments'] or x['messa'] or x['emphasis']):
            continue
        bits = []
        if x['back_phrase']:
            ms = [b['ms'] for b in x['back_phrase']]
            bits.append(f"back-phrased {len(ms)} phrase(s) {min(ms):+.0f}..{max(ms):+.0f} ms"
                        + (' (following)' if any(b['follow'] for b in x['back_phrase']) else ''))
        if x['ornaments']:
            bits.append(f"ornaments (statement {x['statement'] + 1 if x['statement'] is not None else '-'}): "
                        + ', '.join(f"{o['kind']} '{o['word']}'" for o in x['ornaments']))
        if x['messa']:
            bits.append('messa di voce ' + ', '.join(f"'{m['word']}' {m['peak'] - min(m['lo'], m['end']):.1f} dB"
                                                     for m in x['messa']))
        if x['emphasis']:
            bits.append('emphasis ' + ', '.join(f"{'*' if e['kind'] == 'emph' else '(('}{e['word']}"
                                                 f"{'*' if e['kind'] == 'emph' else '))'}" for e in x['emphasis']))
        if x.get('post'):
            bits.append(f"{len(x['post'])} lane move(s) after the compressor")
        out.append(f"{vo.track.id!r} @{vo.notes[0].start:g}: " + '; '.join(bits))
    return out


# ------------------------------------------------------------------------------------------------ production

def double(vo: Vocal, *, pan: float = -0.6, take: int | None = None, offset_ms: float | None = None,
           gain_db: float = -7.0, track_id: str | None = None, formant: float | None = None, depth: float = 0.65,
           **overrides) -> Vocal:
    """A double of a sung part: the same line and words SUNG AGAIN (another take: other timing, vibrato and drift;
    a slightly different formant) on its own track, `gain_db` under, panned, a few ms late - not a copy (a copy
    phases). depth scales its vibrato / scoops (doubles sing plainer); overrides= STYLES keys. Returns the new
    Vocal."""
    n = sum(1 for t in vo.song.tracks.values() if getattr(t, '_singer', None)) + 1
    take = _free_take(vo, vo.take + n) if take is None else take
    off = (14.0 + 9.0 * ((take * 7) % 3)) if offset_ms is None else offset_ms
    fm = (0.35 if pan < 0 else -0.35) if formant is None else formant
    tid = track_id or f"{vo.track.id}_dbl{'_l' if pan < 0 else '_r' if pan > 0 else ''}{n}"
    ov = dict(vib_ct=vo.params['vib_ct'] * depth, peak_vib_ct=vo.params['peak_vib_ct'] * depth,
              scoop_ct=vo.params['scoop_ct'] * depth, fall=vo.params['fall'] * 0.5, doit=0.0)
    for k, v in overrides.items():
        if k not in STYLES['pop'] and k not in STYLE_EXTRAS:
            raise SingerError(f"double(): unknown option {k!r} (a STYLES key: "
                              f"{', '.join(list(STYLES['pop']) + list(STYLE_EXTRAS))})")
        ov[k] = v
    return _resing(vo, take=take, formant=fm, offset_ms=off, track_id=tid, pan=pan, gain_db=gain_db, overrides=ov)


def _free_take(vo: Vocal, take: int) -> int:
    """`take`, or the next one no other singing of this line (same words, same start) uses: a double / harmony
    added to tracks that already exist counted the same tracks twice - L and R sang one take (catch-fire)."""
    at = vo.notes[0].start if vo.notes else 0.0
    used = {p.take for t in vo.song.tracks.values() for p in (getattr(t, '_singer', None) or {}).get('parts', [])
            if p.lyrics_text == vo.lyrics_text and p.notes and abs(p.notes[0].start - at) < 1e-6}
    while take in used:
        take += 1
    return take


def _follow_mic(lead: Vocal, part: Vocal) -> None:
    """A re-sung part (double, harmony, prism voice) pulls back from the mic with the lead - the same notes, the same
    depth - instead of planning its own pulls (its own random stream and budget)."""
    if not part.mic_opts.get('on'):
        return
    same = len(part.notes) == len(lead.notes)

    def idx(i):
        if same:
            return i
        st = lead.notes[i].start
        j = min(range(len(part.notes)), key=lambda k: abs(part.notes[k].start - st))
        return j if abs(part.notes[j].start - st) < 0.5 else None
    out = {}
    for i, p in lead.mic.items():
        j, at = idx(i), idx(p['at'])
        if j is not None and at is not None:
            out[j] = dict(p, at=at)
    part.mic = out


def _resing(vo: Vocal, *, take, formant, offset_ms, track_id, pan, gain_db, overrides, steps: int = 0,
            semitones: int = 0, key=None, mode=None, pitches=None, tune='inherit') -> Vocal:
    """sing() the part of `vo` again (its notes as sung: velocities kept) with changes. pitches: a new pitch per
    written note (prism); tune: 'inherit' (the part's own sing(tune=...) arguments) or a (tune, retune_ms, key, scale)
    tuple."""
    src = vo.src or [(n.start, n.dur, n.pitch, n.vel) for n in vo.notes]
    if pitches is not None:
        if len(pitches) != len(src):
            raise SingerError(f"_resing: {len(pitches)} pitches for {len(src)} notes")
        src = [(st, d, int(q), v) for (st, d, _, v), q in zip(src, pitches)]
    base = src[0][0] if src else 0.0
    c = Clip([(st - base, d, p, v) for st, d, p, v in src])
    if steps:
        if key is None:
            key = getattr(vo.song, 'key', None)
        c = c.transpose_scale(int(steps), key)
    if semitones:
        c = c.transpose(int(semitones))
    ov = {k: v for k, v in vo.params.items() if k != 'vel'}
    if vo.pitch_mode == 'hybrid':            # sing() scales them again
        ov['scoop_ct'] = ov['scoop_ct'] / HYBRID_SCOOP
    ov.update(overrides)
    ta = vo.tune_args if tune == 'inherit' else tuple(tune)
    if vo.pitch_mode == 'hybrid' and 'scoop_ct' in overrides:
        ov['scoop_ct'] = overrides['scoop_ct'] / HYBRID_SCOOP
    part = sing(vo.song, c, vo.lyrics_text, at=base, voice=vo.bank.id, style=vo.style, seed=vo.seed, vel=False,
                mode=mode if mode is not None else vo.mode, moves=vo.moves_on, pitch=vo.pitch_mode, take=take,
                formant=formant, offset_ms=offset_ms, track_id=track_id, pan=pan, gain_db=gain_db,
                mic_pull=vo.mic_pull, tune=ta[0], retune_ms=ta[1], key=ta[2], scale=ta[3], **ov)
    _follow_mic(vo, part)
    return part


def harmony(vo: Vocal, *, steps: int = 2, semitones: int = 0, key=None, pan: float = 0.35, gain_db: float = -6.0,
            take: int | None = None, offset_ms: float = 8.0, track_id: str | None = None, formant: float = 0.2,
            depth: float = 0.7, mode: str | None = None) -> Vocal:
    """A harmony part: the line moved by `steps` scale steps in `key` (2 = a third above, -2 a third below; the song's
    key by default) or by `semitones`, with the same words, SUNG again by the voicebank (not a pitch shift) on its own
    track, `gain_db` under, panned. depth scales its vibrato / scoops. Returns the new Vocal."""
    n = sum(1 for t in vo.song.tracks.values() if getattr(t, '_singer', None)) + 1
    tk = _free_take(vo, vo.take + 10 + n) if take is None else take
    tid = track_id or f"{vo.track.id}_harm{n}"
    ov = dict(vib_ct=vo.params['vib_ct'] * depth, peak_vib_ct=vo.params['peak_vib_ct'] * depth,
              scoop_ct=vo.params['scoop_ct'] * depth, fall=vo.params['fall'] * 0.5, doit=0.0)
    return _resing(vo, take=tk, formant=formant, offset_ms=offset_ms, track_id=tid, pan=pan, gain_db=gain_db,
                   overrides=ov, steps=steps, semitones=semitones, key=key, mode=mode)


PRISM = {
    # voices: prism voices besides the lead; below: how many of them sit under it (the rest above); octave: one more
    # voice an octave under the lead (a phrase that leaves the voice's range under it: over it); spread: the pan width (0..1);
    # gain_db: each voice against the lead (before the bus); offset_ms: (lo, hi) of each voice's lag; formant: the
    # largest formant (gender) shift in semitones (voices below darker, above brighter); depth: x the lead's vibrato /
    # scoops; tune: the pitch correction of the voices (None = natural); retune_ms
    'choir-of-one': dict(voices=4, below=3, octave=False, spread=0.85, gain_db=-9.0, offset_ms=(8.0, 30.0),
                         formant=0.8, depth=0.5, tune=None, retune_ms=None),
    'prismizer': dict(voices=4, below=2, octave=True, spread=1.0, gain_db=-6.0, offset_ms=(0.0, 6.0),
                      formant=1.8, depth=0.0, tune='hard', retune_ms=0.0),
}
"""singer.prism() presets. 'choir-of-one': the singer stacked with herself on the chord tones under her line - a
small, human, loosely-timed choir of takes, natural pitch (Imogen Heap's stacked self-harmonies without the
harmoniser). 'prismizer': the shimmering Bon Iver / Francis and the Lights stack - the voices tight on the beat, hard
pitch correction on every voice, wide formant spread (bigger / smaller versions of the same voice), an octave under,
panned wall to wall."""
_BACKING = r'_(dbl|harm|prism)'
"""Track-id suffixes of re-sung backing parts (doubles, harmonies, prism voices): never the lead in the vocal checks."""
VOCABLES = {'ah', 'ahh', 'aah', 'oh', 'ohh', 'ooh', 'oo', 'whoa', 'woah', 'hey', 'yeah', 'la', 'na', 'mm', 'mmm', 'hm',
            'uh', 'ha', 'ho', 'wo', 'yeh', 'eh', 'doo', 'da', 'ba', 'sha'}
"""Wordless syllables: a part that sings only these (a gang's "whoa / hey", backing "ahs") is not a lead vocal."""
CHECK = {
    # genre (the report's analysis profile): (presence_min %, rival x the vocal's share, buried dB: a part this much
    # over the vocal in a section it sings). The voice IN the band in rock (HUMAN_FEEDBACK), a soft jazz voice in
    # its trio; pop / ballad / film: the voice in front.
    'default': (40.0, 0.6, 1.0),
    'rock': (30.0, 0.8, 3.0),
    'jazz': (35.0, 0.7, 2.0),
}
"""singer.check() thresholds per genre (analysis profile; 'default' for the others)."""


def wordless(vo: Vocal) -> bool:
    """Does this part sing only vocables (VOCABLES: "whoa", "ah", "hey" ...)?"""
    words = [w for w in re.split(r"[^a-z']+", str(vo.lyrics_text).lower()) if w]
    return bool(words) and all(w.strip("'") in VOCABLES for w in words)


def lead_tracks(song) -> list[str]:
    """The sung tracks the vocal checks judge: not backing (_dbl / _harm / _prism) and not wordless."""
    return [t.id for t in song.tracks.values() if getattr(t, '_singer', None) and not re.search(_BACKING, t.id)
            and not all(wordless(p) for p in t._singer.get('parts', []))]


@dataclass
class Prism:
    """What singer.prism() made: the prism voices (Vocals, one track each), the bus they sum on (or None), and the
    pitch each voice sings per written note of the lead ([voice][note])."""
    lead: Vocal
    voices: list
    bus: object
    pitches: list
    preset: str

    @property
    def tracks(self) -> list:
        return [v.track for v in self.voices]

    def __repr__(self) -> str:
        return f"Prism({self.preset!r} on {self.lead.track.id!r}: {len(self.voices)} voices)"


def _harmony_of(song, harmony, at):
    """prism(harmony=): a voicing.Harmony in song beats (a Harmony placed with s.harmony(..., at) is used as is; a
    Progression / progression string is placed at `at`)."""
    from .voicing import Harmony
    from .theory import Progression
    if harmony is None:
        return None
    if isinstance(harmony, Harmony):
        return harmony if (harmony.origin or at is None) else Harmony(harmony, at=song._at(at))
    if isinstance(harmony, (str, Progression)):
        return Harmony(harmony if isinstance(harmony, str) else harmony, key=song.key,
                       at=song._at(at if at is not None else 0.0))
    raise SingerError(f"prism(harmony=): a voicing.Harmony, a Progression or a progression string, got {harmony!r}")


def _prism_chord(H, key, beat: float, lead: int) -> set:
    """The pitch classes the prism voices may sing at `beat`: the chord sounding there, else (no harmony) the diatonic
    triad with the lead note on top (key's scale, thirds stacked down)."""
    if H is not None:
        c = H.at(beat)
        if c is not None:
            return set(c.pcs)
    k = key
    if k is None:
        return {lead % 12, (lead - 4) % 12, (lead - 7) % 12}
    sc = sorted(k.pcs)
    p = lead % 12
    if p not in sc:
        p = min(sc, key=lambda x: min(abs(x - p), 12 - abs(x - p)))
    i = sc.index(p)
    return {sc[i], sc[(i - 2) % len(sc)], sc[(i - 4) % len(sc)]}


def _prism_lines(src: list, H, key, n_below: int, n_above: int, lo: int, hi: int) -> list:
    """Voice-led prism lines on the chord tones around a lead: per written note, the voices below take chord tones
    under the lead (the nearest first, voice 1 closest), the voices above chord tones over it; among the candidate
    sets the one moving least from the voices' previous pitches wins (common tones held), with a pull back to close
    position. Never a unison or a second against the lead, never outside lo..hi. -> [voice][note] pitches (below
    voices first, nearest the lead first; then above)."""
    from itertools import combinations
    prev_b: list | None = None
    prev_a: list | None = None
    lines_b = [[] for _ in range(n_below)]
    lines_a = [[] for _ in range(n_above)]

    def pick(cands, n, prev):
        if n == 0:
            return []
        pool = cands[:n + 3]
        if len(pool) < n:                       # not enough room: repeat the outermost candidate
            pool = pool + [pool[-1] if pool else None] * (n - len(pool))
        best, bs = None, None
        for combo in combinations(range(len(pool)), n):
            ch = [pool[i] for i in combo]
            if any(x is None for x in ch):
                sc = 99.0
            else:
                close = sum(combo) - sum(range(n))     # how far from close position (candidate ranks skipped)
                move = sum(abs(a - b) for a, b in zip(ch, prev)) if prev else 0.0
                sc = move + 1.5 * close
            if bs is None or sc < bs - 1e-9:
                best, bs = ch, sc
        return best

    for st, d, lead, v in src:
        pcs = _prism_chord(H, key, st, lead)
        down = [p for p in range(lead - 2, lead - 25, -1) if p % 12 in pcs and lo <= p <= hi]
        up = [p for p in range(lead + 2, lead + 25) if p % 12 in pcs and lo <= p <= hi]
        b = pick(down, n_below, prev_b)
        a = pick(up, n_above, prev_a)
        # the voice range is exhausted on one side: borrow from the other (fewer distinct pitches, never silence)
        b = [x if x is not None else (up[0] if up else lead) for x in b]
        a = [x if x is not None else (down[0] if down else lead) for x in a]
        for k, x in enumerate(b):
            lines_b[k].append(x)
        for k, x in enumerate(a):
            lines_a[k].append(x)
        prev_b, prev_a = b, a
    return lines_b + lines_a


def _octave_line(src: list, lo: int, hi: int, gap: float = 0.75) -> list:
    """The prismizer's octave voice: phrase by phrase (rests of `gap` beats apart) an octave under the lead, over it when
    the phrase does not fit under in lo..hi; a phrase that fits neither way decides per note (under, over, else the
    lead's own pitch: a double)."""
    groups, cur, end = [], [], None
    for i, (st, d, p, v) in enumerate(src):
        if cur and st - end >= gap:
            groups.append(cur)
            cur = []
        end = max(end, st + d) if cur else st + d
        cur.append(i)
    if cur:
        groups.append(cur)
    out = [0] * len(src)
    for g in groups:
        ps = [src[i][2] for i in g]
        sh = -12 if min(ps) - 12 >= lo else 12 if max(ps) + 12 <= hi else 0
        for i in g:
            p = src[i][2]
            out[i] = p + sh if sh else p - 12 if p - 12 >= lo else p + 12 if p + 12 <= hi else p
    return out


def prism(vo: Vocal, harmony=None, *, preset: str = 'choir-of-one', at=None, voices: int | None = None,
          below: int | None = None, octave: bool | None = None, spread: float | None = None,
          mix: float | None = None, offset_ms=None, formant: float | None = None, depth: float | None = None,
          tune='preset', retune_ms: float | None = None, key=None, scale=None, bus: bool | str = True,
          track_id: str | None = None) -> Prism:
    """A harmoniser / Prismizer made of real takes: the lead's line RE-SUNG by the same voicebank on the chord tones of
    `harmony` around it (not pitch-shifted copies): each prism voice is its own take (other timing, vibrato, drift),
    lagged a little, with its own formant (gender) shift, panned across the stereo field, voice-led (common tones held,
    no unisons / seconds against the lead, the voice's range kept). Returns a Prism (.voices: the Vocals, .bus).

    harmony: a voicing.Harmony in song beats (s.harmony('Am F C G', at=chorus)), or a Progression / progression string
    placed at `at` (default beat 0); None: diatonic triads under each lead note in the song key (key=).
    preset: PRISM 'choir-of-one' (natural, loose, mostly below) or 'prismizer' (tight, hard-tuned, wide formants, an
    octave under); every PRISM key can be overridden: voices (prism voices besides the lead, 1-8), below (how many under
    the lead), octave, spread (pan width 0..1), mix (dB of each voice against the lead = PRISM gain_db), offset_ms
    ((lo, hi) lag range or one number), formant (the largest formant shift, st), depth (x the lead's vibrato / scoops),
    tune / retune_ms / key / scale (the voices' pitch correction, as sing(); tune='preset' = the preset's).
    bus: True sums the voices on a bus '<lead>_prism' (a str: that bus id; False: each voice to the master)."""
    if preset not in PRISM:
        raise SingerError(f"prism preset must be one of {', '.join(PRISM)}, got {preset!r}")
    P = dict(PRISM[preset])
    for k, v in (('voices', voices), ('below', below), ('octave', octave), ('spread', spread), ('gain_db', mix),
                 ('offset_ms', offset_ms), ('formant', formant), ('depth', depth)):
        if v is not None:
            P[k] = v
    n = int(P['voices'])
    if not 1 <= n <= 8:
        raise SingerError(f"prism(voices={n}): 1..8 voices besides the lead")
    if below is None and voices is not None:      # more / fewer voices: the preset's share of them below
        P['below'] = round(n * PRISM[preset]['below'] / PRISM[preset]['voices'])
    nb = max(0, min(n, int(P['below'])))
    sp = float(P['spread'])
    if not 0.0 <= sp <= 1.0:
        raise SingerError(f"prism(spread={sp}): 0..1")
    off = P['offset_ms']
    off = (float(off), float(off)) if isinstance(off, (int, float)) else (float(off[0]), float(off[1]))
    song = vo.song
    H = _harmony_of(song, harmony, at)
    k = Key(key) if key is not None else (Key(song.key) if getattr(song, 'key', None) is not None else None)
    src = vo.src or [(x.start, x.dur, x.pitch, x.vel) for x in vo.notes]
    lo, hi = vo.bank.range
    lines = _prism_lines(src, H, k, nb, n - nb, lo, hi)
    if P['octave']:
        lines.append(_octave_line(src, lo, hi))
    if tune == 'preset':
        ta = (P['tune'], P['retune_ms'] if retune_ms is None else retune_ms, key, scale)
    else:
        ta = (tune, retune_ms, key, scale)
    if ta[0] is None:
        ta = (None, None, None, None)
    rng = random.Random(vo.seed * 7717 + 31 * n + len(src))
    base_id = track_id or f"{vo.track.id}_prism"
    b = None
    if bus:
        bid = bus if isinstance(bus, str) else f"{vo.track.id}_prism"
        b = song.buses.get(bid) or song.bus(bid)
    # pans: the voices ordered by mean pitch, spread from left to right, neighbours on opposite sides
    mean = [sum(L) / max(1, len(L)) for L in lines]
    order = sorted(range(len(lines)), key=lambda i: mean[i])
    m = len(lines)
    slots = [(-sp + 2 * sp * j / (m - 1)) if m > 1 else 0.0 for j in range(m)]
    inter = slots[0::2] + slots[1::2][::-1]          # low voices alternate sides: -1, +0.5, -0.5, +1 ...
    pan_of = {i: inter[j] for j, i in enumerate(order)}
    lead_mean = sum(p for _, _, p, _ in src) / max(1, len(src))
    dep = float(P['depth'])
    ov = dict(vib_ct=vo.params['vib_ct'] * dep, peak_vib_ct=vo.params['peak_vib_ct'] * dep,
              scoop_ct=vo.params['scoop_ct'] * max(dep, 0.2), fall=vo.params['fall'] * 0.5 * dep, doit=0.0)
    out = []
    count = sum(1 for t in song.tracks.values() if getattr(t, '_singer', None))
    for i, L in enumerate(lines):
        rel = (mean[i] - lead_mean) / 12.0           # octaves above (+) / below (-) the lead
        fm = max(-float(P['formant']), min(float(P['formant']), float(P['formant']) * rel * 1.6
                                           + (rng.random() - 0.5) * 0.3 * float(P['formant'])))
        tid = f"{base_id}{i + 1}"
        pv = _resing(vo, take=vo.take + 30 + count + i, formant=round(fm, 3),
                     offset_ms=round(off[0] + (off[1] - off[0]) * rng.random(), 2), track_id=tid,
                     pan=round(pan_of[i], 3), gain_db=float(P['gain_db']), overrides=ov, pitches=L, tune=ta)
        pv.level_ref = vo                           # each voice's takes at the lead's level, then `mix` under it
        if b is not None:
            pv.track.to(b)
        out.append(pv)
    return Prism(vo, out, b, lines, preset)


MOUTH = dict(vib_ct=0.0, peak_vib_ct=0.0, scoop_ct=0.0, scoop_first=0.0, scoop_leap=0.0, scoop_peak=0.0, fall=0.0,
             doit=0.0, overshoot_ct=0.0, drift_ct=0.0, swell=0.0, messa=0.0, taper=0.0, release=0.0, breath_db=-30.0)
"""singer.mouth(): the moves a talk-box player's mouth does not make (no pitch moves, no air moves, a breath you
cannot hear through the tube) - only the vowels and consonants matter."""


def mouth(target, line, lyrics: str, at=0.0, *, voice: str = 'tiger', pitch='low', track_id: str = 'talkbox_mouth',
          style: str = 'pop', seed=0, **kw) -> Vocal:
    """The talk-box player's mouth (the modulator of speech.talkbox): the words of `lyrics` mouthed in the rhythm of
    `line` - sung by the voicebank on ONE steady low pitch (pitch='low': 5 semitones over the voice's lowest note;
    a note name / MIDI number; 'line': the line's own pitches), no vibrato, scoops, falls or swells, the LINE's
    velocities (vel=False: in LPC mode the talk box's level follows the mouth, so shape the line with
    humanize.touch - a mouth at one level is a flat_dynamics talk box), the voicebank's pitch curve the player's
    (flat). A low steady voice has dense harmonics, so the talk box's formant
    follower (the vocoder in LPC mode) reads clean vowel shapes from it; the instrument gives the pitch. Returns the
    Vocal (its track `track_id`; speech.talkbox() mutes it). kw: more sing() options (take, formant, offset_ms ...)."""
    from .theory import note as _note
    bank = _vb.get(voice)
    clip, _, _ = _line_of(line)
    if pitch != 'line':
        p = bank.range[0] + 5 if pitch == 'low' else _note(pitch)
        clip = Clip([(n.start, n.dur, p, n.vel) for n in clip], length=clip.length)
    opts = dict(MOUTH)
    opts.update({k: v for k, v in kw.items() if k in STYLES['pop'] or k in STYLE_EXTRAS})
    rest = {k: v for k, v in kw.items() if k not in opts}
    rest.setdefault('pitch', 'player')
    rest.setdefault('vel', False)            # the line's own velocities: the talk box's level follows the mouth
    for k in ('back_phrase', 'ornament', 'messa_di_voce', 'mic_pull'):
        rest.setdefault(k, False)
    return sing(target, clip, lyrics, at, voice=voice, style=style, seed=seed, track_id=track_id,
                range_check=False, **rest, **opts)


# ------------------------------------------------------------------------------------------------ vocal chops

CHOP = dict(attack_ms=4.0, release_ms=35.0, pre_ms=6.0, tail_ms=25.0, velsens=0.85, polyphony=12,
            fx='edm/vocal_chop')
"""singer.chops(): a slice's fade in / out (ms: the zone's attack and the release after its note), how much before the
slice's first consonant it starts and after its last one it ends (ms), the sampler's velocity sensitivity and
polyphony, and the insert chain of a new chops track (a library chain patch, None = none)."""
CHOP_UNITS = ('syllable', 'word', 'phrase')


@dataclass
class Chops:
    """What singer.chops() made: the chops track, the slices of the source part (index, unit, word / text, the sung
    pitch, the beat it was sung at, its phrase) and the chops played [(beat, slice index, semitones, velocity)]."""
    track: object
    source: Vocal
    unit: str
    slices: list
    picks: list

    def describe(self) -> str:
        lines = [f"{self.track.id}: {len(self.picks)} chops from {self.source.track.id!r} ({self.unit}s: "
                 + ', '.join(f"{s['index']} {s['text']!r}" for s in self.slices) + ')']
        lines += [f"  {b:8.3f}  slice {i} {self.slices[i]['text']!r} {st:+d} st vel {v}" for b, i, st, v in self.picks]
        return '\n'.join(lines)

    def __repr__(self) -> str:
        return f"Chops({self.track.id!r}, {len(self.picks)} chops of {len(self.slices)} {self.unit}s)"


def _chop_slices(vo: Vocal, unit: str) -> list:
    """The slices of a sung part: one per syllable group (a syllable + its melisma / hold notes), word or phrase, with
    the note indices they cover (their audio is found in the take's timeline when the song compiles)."""
    out = []
    for k, ph in enumerate(vo.phrases):
        groups: list = []
        for i in ph:
            if vo.notes[i].kind == 'syllable' or not groups:
                groups.append([i])
            else:
                groups[-1].append(i)
        if unit == 'phrase':
            spans = [list(range(len(groups)))]
        elif unit == 'word':
            spans = []
            for g, idx in enumerate(groups):
                if vo.notes[idx[0]].word_start or not spans:
                    spans.append([g])
                else:
                    spans[-1].append(g)
        else:
            spans = [[g] for g in range(len(groups))]
        for sp in spans:
            first = vo.notes[groups[sp[0]][0]]
            words = []
            for g in sp:
                w = vo.notes[groups[g][0]].syl.word
                if not words or vo.notes[groups[g][0]].word_start:
                    words.append(w)
            text = (' '.join(words) if unit != 'syllable'
                    else ''.join(ch for ch in ''.join(first.syl.phonemes) if ch.isalpha()) or first.syl.word)
            out.append(dict(index=len(out), unit=unit, phrase=k, groups=(sp[0], sp[-1]), word=first.syl.word.lower(),
                            text=text, pitch=first.pitch, beat=round(first.start, 4)))
    return out


def chops(vo: Vocal, line, at=0.0, *, slices=None, unit: str = 'syllable', track_id: str = 'chops',
          gain_db: float = 0.0, pan: float | None = None, sends: dict | None = None, fx=None) -> Chops:
    """VOCAL CHOPS from a sung part: slices of `vo`'s own takes (one per syllable, word or phrase: `unit`) retriggered in
    the rhythm of `line` and PITCHED to its notes - the EDM / future-bass chop (the slice is resampled: a chop played
    5 st up sounds smaller and brighter, the classic chipmunk-y chop). Returns Chops (.track, .slices, .picks,
    .describe()).

    line: a Clip / notation string - the chops' rhythm, pitches and velocities (each note plays one slice, gated by the
    note's length: a 16th = a stab, a long note = the whole slice). slices: which slice each note plays, cycled - None
    (0, 1, 2, ...), a list of slice indices and / or words ('night', 'oh': the first slice of that word), or one
    index / word for every note. at: where `line` starts (beat or Section). The track `track_id` (created on the first
    call, a sampler whose zones are the slices, written when the song compiles after the takes are rendered: the
    'offset' / 'end' frames of each slice in its take file, a 4 ms fade in, a 35 ms release - CHOP) gets the library
    chain CHOP['fx'] ('edm/vocal_chop': high-pass, presence, a compressor, a touch of drive and chorus) plus `fx`;
    sends= e.g. {echo: -10, hall: -14}. More calls with the same track_id add more chops (also from other parts).
    Tip: sing the source with tune='hard' - the chops then land exactly on their notes. `python -m agentsound` build
    prints `chops ...` lines (chops_lines)."""
    from .song import Song  # noqa: F401  (type of vo.song)
    if not isinstance(vo, Vocal):
        raise SingerError(f"chops() takes a sung part (what sing() returned), got {vo!r}")
    if unit not in CHOP_UNITS:
        raise SingerError(f"chops unit must be one of {', '.join(CHOP_UNITS)}, got {unit!r}")
    song = vo.song
    sl = _chop_slices(vo, unit)
    if not sl:
        raise SingerError(f"chops(): {vo.track.id!r} has no sung notes to slice")
    clip, _, _ = _line_of(line)
    notes = list(clip)
    if not notes:
        raise SingerError("chops(): the line has no notes")
    if slices is None:
        picks = list(range(len(sl)))
    elif isinstance(slices, (int, str)):
        picks = [slices]
    else:
        picks = list(slices)
        if not picks:
            raise SingerError("chops(): slices= is empty")

    def resolve(p) -> int:
        if isinstance(p, bool) or not isinstance(p, (int, str)):
            raise SingerError(f"chops(): a slice is an index or a word, got {p!r}")
        if isinstance(p, int):
            if not 0 <= p < len(sl):
                raise SingerError(f"chops(): slice {p} does not exist ({len(sl)} {unit}s: 0..{len(sl) - 1})")
            return p
        w = p.lower().strip()
        for s in sl:
            if s['word'] == w or s['text'].lower() == w:
                return s['index']
        raise SingerError(f"chops(): no {unit} {p!r} in {vo.track.id!r} "
                          f"({', '.join(repr(s['text']) for s in sl)})")
    idx = [resolve(p) for p in picks]
    if pan is not None and not -1.0 <= pan <= 1.0:
        raise SingerError(f"chops(): pan must be -1..1, got {pan!r}")
    t = song.tracks.get(track_id)
    if t is None:
        from .patches import Instrument
        ins = Instrument('sampler', {'samples': []}, oneshot='off', velsens=CHOP['velsens'],
                         polyphony=CHOP['polyphony'], release=CHOP['release_ms'] / 1000.0)
        ins.info = {'singer_chops': vo.bank.id}
        chain = []
        if CHOP['fx']:
            from . import patches as _patches
            chain = [f.copy() for f in _patches.get(CHOP['fx']).fx]
        t = song.track(track_id, ins, fx=chain + list(fx or ()), gain_db=gain_db, pan=pan, sends=sends)
        t._chops = {'parts': [], 'keys': {}}
        if not hasattr(song, '_chops_hook'):
            song._chops_hook = True
            song.add_compile_hook(_write_chops)
    elif getattr(t, '_chops', None) is None:
        raise SingerError(f"track {track_id!r} exists and is not a chops track; pass track_id= another id")
    base = song._at(at)
    keys = t._chops['keys']
    placed = []
    for j, n in enumerate(notes):
        i = idx[j % len(idx)]
        st = int(n.pitch) - int(sl[i]['pitch'])
        if not -36 <= st <= 36:
            raise SingerError(f"chops(): note {n.pitch} is {st:+d} st from slice {i} ({sl[i]['text']!r}, sung at "
                              f"{sl[i]['pitch']}); keep chops within +-36 st of the sung pitch")
        k = (id(vo), unit, i, st)
        if k not in keys:
            if len(keys) >= 128:
                raise SingerError(f"chops track {t.id!r}: more than 128 (slice, pitch) pairs - use a second track_id")
            keys[k] = len(keys)
        placed.append((base + n.start, n.dur, keys[k], n.vel, i, st))
    t._chops['parts'].append({'vo': vo, 'unit': unit, 'slices': sl, 'notes': placed})
    _place_chops(t)
    return Chops(t, vo, unit, sl, [(round(b, 4), i, st, v) for b, _, _, v, i, st in placed])


def _place_chops(t) -> None:
    """The chops' trigger notes as written (render time shortens a note longer than its slice)."""
    from .patterns import Note
    t._notes = [Note(b, d, k, v) for p in t._chops['parts'] for b, d, k, v, _, _ in p['notes']]
    t._origin = ['singer.chops'] * len(t._notes)


def _slice_span(sl: dict, toks: list, spec: dict, vowels: list) -> tuple[float, float]:
    """(start, end) phrase seconds of a slice in its take: from the first onset consonant of its first syllable to the
    last coda consonant of its last one (+ a final stop's released burst) - read from the take's own timeline (the
    nucleus of syllable group g is the vowel token that starts at timeline['vowels'][g])."""
    groups = _groups(spec['notes'])
    if len(vowels) != len(groups):
        raise SingerError("chops(): the take's timeline does not match its notes")

    def nucleus(g: int) -> int:
        V = float(vowels[g])
        best = min(range(len(toks)), key=lambda i: (toks[i][0] != groups[g]['nu'], abs(float(toks[i][1]) - V)))
        if toks[best][0] != groups[g]['nu'] or abs(float(toks[best][1]) - V) > 0.005:
            raise SingerError(f"chops(): no vowel {groups[g]['nu']!r} at {V:.3f} s in the take")
        return best

    def cons(p: str) -> bool:
        return p not in ('SP', 'AP') and p not in _lyr.SUNG_VOWELS
    g0, g1 = sl['groups']
    a = nucleus(g0)
    for _ in range(len(groups[g0]['on'])):
        if a - 1 >= 0 and cons(toks[a - 1][0]):
            a -= 1
    j = nucleus(g1)
    need = len(groups[g1]['co'])
    while need > 0 and j + 1 < len(toks):
        p = toks[j + 1][0]
        if p == 'SP' and j + 2 < len(toks) and cons(toks[j + 2][0]):     # the silent closure before a final stop
            j += 1
            continue
        if not cons(p):
            break
        j += 1
        need -= 1
    rv = spec.get('release_vowel')
    if (rv and cons(toks[j][0]) and j + 1 < len(toks) and toks[j + 1][0] == rv
            and (j + 2 >= len(toks) or toks[j + 2][0] in ('SP', 'AP'))):
        j += 1                                                             # the released burst of that stop
    return float(toks[a][1]), float(toks[j][2])


def _write_chops(song) -> None:
    """The compile hook (after singer.render): every chops track's zones (the slices in the rendered takes) and its
    trigger notes, a note longer than its slice cut to it."""
    from .patches import inst
    from .patterns import Note
    for t in song.tracks.values():
        info = getattr(t, '_chops', None)
        if not info:
            continue
        zones: dict = {}
        notes = []
        for part in info['parts']:
            vo = part['vo']
            if not vo.rendered:
                raise SingerError(f"chops track {t.id!r}: the source part {vo.track.id!r} was not rendered (sing it "
                                  f"in this song before the chops)")
            spans: dict = {}
            for b, d, k, v, i, st in part['notes']:
                if i not in spans:
                    sl = part['slices'][i]
                    r = next(x for x in vo.rendered if x['phrase'] == sl['phrase'])
                    meta = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))
                    tl = meta['timeline']
                    a, z = _slice_span(sl, [tuple(x) for x in tl['tokens']], meta['spec'], tl['vowels'])
                    off = float(tl['offset_s'])
                    a -= CHOP['pre_ms'] / 1000.0
                    z += CHOP['tail_ms'] / 1000.0
                    spans[i] = (r['path'], max(0, int(round((a - off) * SR))), int(round((z - off) * SR)), z - a)
                path, f0, f1, secs = spans[i]
                if k not in zones:
                    zone = {'file': str(Path(path).resolve()).replace(os.sep, '/'), 'root': k, 'lo': k, 'hi': k,
                            'offset': f0, 'end': max(f0 + 64, f1), 'loop': 'none',
                            'attack': CHOP['attack_ms'] / 1000.0, 'release': CHOP['release_ms'] / 1000.0}
                    if st:
                        zone['tune'] = 100 * st
                    mk = makeup_db(vo) + vo.level_match_db
                    if mk:
                        zone['gain'] = round(mk, 3)
                    zones[k] = zone
                # resampled up by st semitones the slice plays 2^(st/12) faster: it lasts secs / that
                room = secs / (2.0 ** (st / 12.0)) - CHOP['release_ms'] / 1000.0
                d_max = max(0.03, room) * song.tempo_at(b) / 60.0
                notes.append(Note(b, round(min(d, d_max), 6), k, v))
        old = t.instrument
        params = {k: v for k, v in old.params.items() if k not in ('zones', 'samples')}
        ins = inst.sampler(zones=[zones[k] for k in sorted(zones)], **params)
        ins.info = old.info
        t.instrument = ins
        t._notes = notes
        t._origin = ['singer.chops'] * len(notes)


def chops_lines(song) -> list[str]:
    """One line per chops track: how many chops of which slices, and the pitch range."""
    out = []
    for t in song.tracks.values():
        info = getattr(t, '_chops', None)
        if not info:
            continue
        for p in info['parts']:
            used = sorted({i for *_, i, _ in p['notes']})
            sts = [st for *_, st in p['notes']]
            out.append(f"{t.id!r}: {len(p['notes'])} chops of {p['vo'].track.id!r} ({p['unit']}s "
                       + ', '.join(repr(p['slices'][i]['text']) for i in used)
                       + f"), {min(sts):+d}..{max(sts):+d} st")
    return out


# ------------------------------------------------------------------------------------------------ the ears

def log_lines(song) -> list[str]:
    """One line per sung part: voice, style, notes / phrases, the moves it sang and what the budget dropped (+ one line
    per chops track: chops_lines)."""
    out = []
    for t in song.tracks.values():
        info = getattr(t, '_singer', None)
        if not info:
            continue
        for vo in info['parts']:
            sm = ', '.join(f"{k} {v}" for k, v in vo.summary().items()) or 'none (moves off)'
            drop = f"; spice budget dropped {len(vo.budget['dropped'])}" if vo.budget.get('dropped') else ''
            mp = ''
            if vo.mic_pulls:
                dbs = [p['db'] for p in vo.mic_pulls]
                mp = f"; mic pulls {len(dbs)} ({max(dbs):+.1f}..{min(dbs):+.1f} dB)"
            tn = (f", tune {vo.tune['mode']} {vo.tune['retune_ms']:g} ms" if vo.tune else '')
            if vo.level_ref is not None:
                tn += f", takes {vo.level_match_db:+.1f} dB (matched to {vo.level_ref.track.id!r})"
            out.append(f"{t.id!r}: {vo.bank.id} {vo.style}{'' if vo.moves_on else ' ROBOTIC'} pitch={vo.pitch_mode}{tn}, "
                       f"take {vo.take}, {len(vo.notes)} notes in {len(vo.phrases)} phrases; moves: {sm}{drop}{mp}")
            out += [f"{t.id!r}: {w}" for w in vo.warnings]
    return out + [f"chops {x}" for x in chops_lines(song)]


def check(report, vocals=None, *, presence_min: float | None = None, rival: float | None = None,
          harsh: float = 22.0) -> list[dict]:
    """The vocal's ears on a build's report (report.json path or dict): findings [{'severity', 'code', 'node',
    'message'}].
      intelligibility  the words live at 2-6 kHz (the report's 'presence' band): the lead vocal should own at least
                       `presence_min` % of the mix there (its grit bus '<id>_grit', hero(..., grit=), counted with
                       it); a competitor (keys, guitars, pads ...) with more than
                       `rival` x the vocal's share masks the words (fix: its presence dip / the vocal hero's carve);
      buried           the vocal under the loudest other track in the sections it sings;
      harsh            more than `harsh` % of the vocal's own energy in 2.5-6 kHz (de-ess / less presence);
      masking          the report's own masking warnings that name a vocal track.
    vocals: track ids (default: the report's nodes named vocal* / vox*, or the song's vocal tracks). The thresholds
    come from CHECK by the report's profile (presence_min / rival override them); the presence share is the vocal's
    share of the presence band in the sections it sings (not over the whole song: an instrumental intro or solo does
    not count against it)."""
    import re
    rep = report if isinstance(report, dict) else json.loads(Path(report).read_text(encoding='utf-8'))
    p_min, p_rival, buried_db = CHECK.get((rep.get('reference') or {}).get('profile'), CHECK['default'])
    presence_min = p_min if presence_min is None else presence_min
    rival = p_rival if rival is None else rival
    nodes = {n['id']: n for n in rep.get('nodes', [])}
    if vocals is None:
        vocals = [i for i in nodes if re.match(r'^(vocal|vox|lead_vocal)', i) and not re.search(_BACKING, i)
                  and not nodes[i].get('bus')]
    out = []
    for vid in vocals:
        v = nodes.get(vid)
        if v is None:
            continue
        share = (v.get('mixSharePct') or {}).get('presence', 0.0)
        grit = nodes.get(f'{vid}_grit')       # hero(..., grit=): the parallel amp bus is part of the vocal
        if grit is not None:
            share = min(100.0, share + (grit.get('mixSharePct') or {}).get('presence', 0.0))
        sung = _sung_part(rep, v)              # the song's presence energy in the sections it sings
        if sung:
            share = min(100.0, share / sung)
        if share < presence_min:
            out.append(dict(severity='warn', code='vocal_intelligibility', node=vid,
                            message=f"{vid!r} owns only {share:.0f} % of the mix's 2.5-6 kHz presence band (the words "
                                    f"live there; >= {presence_min:.0f} %): raise it, or dip / carve the competitors"))
        for oid, o in nodes.items():
            if oid == vid or o.get('bus') or re.match(r'^(vocal|vox)', oid):
                continue
            os_ = (o.get('mixSharePct') or {}).get('presence', 0.0)
            if share > 0 and os_ >= rival * share and os_ >= 15.0:
                out.append(dict(severity='warn', code='vocal_masked', node=vid,
                                message=f"{oid!r} carries {os_:.0f} % of the presence band against the vocal's "
                                        f"{share:.0f} %: it masks the words - a presence dip on it (mixer.add_eq_dip / "
                                        f"hero competitors=) or song.carve(it, key=vocal)"))
        own = (v.get('bandsPct') or {}).get('presence', 0.0)
        if own > harsh:
            out.append(dict(severity='info', code='vocal_harsh', node=vid,
                            message=f"{vid!r} has {own:.0f} % of its energy at 2.5-6 kHz: harsh / sibilant - check the "
                                    f"de-esser (hero deess=) and the presence boost"))
        secs = {s['section']: s for s in v.get('sections', [])}
        for sec in rep.get('sections', []):
            me = secs.get(sec.get('name'))
            others = [a for a in sec.get('active', []) if a['id'] != vid and not a.get('bus')
                      and not re.match(r'^(vocal|vox)', a['id'])]
            loudest = max((x.get('rmsDb', -120.0) for x in secs.values()), default=-120.0)
            if not me or me.get('rmsDb', -120) < loudest - 10.0:     # it does not really sing here (a pickup, a tail)
                continue
            if others and others[0]['rmsDb'] > me['rmsDb'] + buried_db:
                out.append(dict(severity='warn', code='vocal_buried', node=vid,
                                message=f"in {sec['name']!r} the vocal ({me['rmsDb']:.1f} dB RMS) sits under "
                                        f"{others[0]['id']!r} ({others[0]['rmsDb']:.1f} dB): a lead vocal leads"))
    for w in rep.get('warnings', []):
        if w.get('code') == 'masking' and any(n in vocals for n in w.get('nodes', [])):
            out.append(dict(severity='info', code='vocal_masking', node=','.join(w.get('nodes', [])),
                            message=w.get('message', '')))
    return out


def _sung_part(rep: dict, v: dict) -> float | None:
    """The share (0..1) of the mix's presence-band energy that lies in the sections where node `v` sings (its level
    there within 10 dB of its loudest section); None when the report cannot tell."""
    secs = {s['section']: s.get('rmsDb', -120.0) for s in v.get('sections', [])}
    if not secs:
        return None
    top = max(secs.values())
    tot = mine = 0.0
    for s in rep.get('sections', []):
        if 'startSec' not in s or 'rmsDb' not in s:
            return None
        e = 10 ** (s['rmsDb'] / 10.0) * (s['endSec'] - s['startSec']) * (s.get('bandsPct') or {}).get('presence', 0.0)
        tot += e
        if secs.get(s['name'], -120.0) >= top - 10.0:
            mine += e
    return mine / tot if tot > 0 and mine > 0 else None


def diction(target) -> list[dict]:
    """The singer's diction check on the rendered takes (a Song, a vocal track or a Vocal; after a build / compile):
    every word-final consonant (the timeline's 'diction' list) must last at least its class's warn length
    (DICTION: a stop 40 ms, a sibilant 50 ms ...) and must not sit more than 3 dB under its vowel (a release or taper
    swallowing it). Findings [{'severity', 'code', 'node', 'message'}] - 'coda_short' / 'coda_buried' - and an 'info'
    'diction' summary per part (how many codas, the shortest). A mic pull over the word (mic_pull) counts: its level
    on the consonant against its median over the vowel is added."""
    parts = _parts_of(target)
    out = []
    for vo in parts:
        tid = vo.track.id
        codas = []
        for r in vo.rendered:
            try:
                tl = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))['timeline']
            except (OSError, ValueError, KeyError):
                continue
            pulls = [p for p in vo.mic_pulls if p['phrase'] == r['phrase'] and p['coda']]
            for c in tl.get('diction', []):
                if c['cls'] == 'release':
                    continue
                adj = next((p['coda_vs_vowel_db'] for p in pulls
                            if p['coda'][0] - 1e-3 <= c['a'] <= p['coda'][1] + 1e-3), 0.0)
                codas.append(dict(c, level_db=round(c.get('level_db', 0.0) + adj, 2)) if adj else c)
        for c in codas:
            lim = DICTION.get(c['cls'], DICTION['glide'])[3] * 1000
            where = f"{c['word']!r} /{c['ph']}/ ({'before a rest' if c['at'] == 'rest' else 'legato'})"
            if c['ms'] < lim - 1e-6:
                out.append(dict(severity='warn', code='coda_short', node=tid,
                                message=f"{tid!r}: the word-final {where} lasts {c['ms']:.0f} ms (< {lim:.0f} ms for a "
                                        f"{c['cls']}): it will not be heard - give the word a longer last note or a "
                                        f"gap after it"))
            if c.get('level_db', 0.0) < -3.0:
                out.append(dict(severity='warn', code='coda_buried', node=tid,
                                message=f"{tid!r}: the word-final {where} sits {c['level_db']:.1f} dB under its vowel "
                                        f"(a release / taper over the consonant)"))
        if codas:
            short = min(codas, key=lambda c: c['ms'])
            out.append(dict(severity='info', code='diction', node=tid,
                            message=f"{tid!r}: {len(codas)} word-final consonants sung, the shortest {short['word']!r} "
                                    f"/{short['ph']}/ {short['ms']:.0f} ms"))
    return out


LONG_NOTE_S = 8.0
"""A sung note longer than this (seconds, through the tempo map) is a held_note warning: one breath at full voice
(when-the-year-turns-gold: a tied 2-bar note over the ending's fermata became 13 s, the A&R's only major)."""


def held_notes(song) -> list[dict]:
    """The singer's breath check on the tempo map: a sung note that runs through a fermata (song.fermata / s.ending -
    it is stretched with the band) is 'note_fermata' (info), one that then lasts over LONG_NOTE_S is 'held_note'
    (warn: shorten it, end it on the fermata's beat or let the mic pull / a taper take it). Findings like check()."""
    from . import silent_notes as _sn
    ferm = [f[0] for f in getattr(getattr(song, '_tempo_plan', None), 'fermatas', [])]
    out = []
    for t in song.tracks.values():
        for vo in (getattr(t, '_singer', None) or {}).get('parts', []):
            for n in vo.notes:
                a, b = n.start, n.start + n.dur
                secs = song.seconds(b) - song.seconds(a)
                fs = [f for f in ferm if a <= f < b - 1e-6]
                where = f"{t.id!r} at {_sn._bar_beat(a, song.meter_grid())}"
                if secs > LONG_NOTE_S:
                    out.append(dict(severity='warn', code='held_note', node=t.id,
                                    message=f"{where}: a sung note lasts {secs:.1f} s"
                                    + (" (through a fermata)" if fs else '') + f" - over {LONG_NOTE_S:g} s at full "
                                    "voice: shorten it, end it on the fermata's beat or taper it"))
                elif fs:
                    out.append(dict(severity='info', code='note_fermata', node=t.id,
                                    message=f"{where}: a sung note runs through a fermata ({secs:.1f} s with the "
                                            f"hold)"))
    return out


def wetness(report, render, vocals) -> dict:
    """How wet each sung track is, from a build's report and its render JSON (no extra render): every reverb / delay
    return's level (report nodes[].lufs) split over its senders by the power each one sends in (sender LUFS + send
    dB; a linear return keeps the shares), so the vocal's part of a return is the return's level + 10 log10(its
    share; song-long energies: lufs + activePct). {vocal id: {'wetLu': total vs the dry vocal, 'returnsLu': {return id:
    LU}}}: -10 LU is a clearly audible
    space, -20 a hint (recipes/HUMAN_FEEDBACK.md: "immer viel Hall"). An estimate: sends with a tap, a return that
    compresses (a crushed room) or an automated send on a shared return (its static level sets the share) shift it
    by a dB or two (_demo_vocal: -14.0 LU vs -14.7 rendered alone; plate -16.6 vs -16.6, the thrown echo -17.5 vs
    -19.1);
    songs/_demo_vocal/wetness.py renders the vocal alone for the exact numbers and the tails."""
    rep = report if isinstance(report, dict) else json.loads(Path(report).read_text(encoding='utf-8'))
    # song-long energy: the gated loudness over the share of the song a node sounds (an echo heard only on the throws
    # is loud while it sounds, quiet over the song)
    lufs = {n['id']: n['lufs'] + 10 * math.log10(max(n.get('activePct', 100.0), 0.1) / 100.0)
            for n in rep.get('nodes', []) if isinstance(n.get('lufs'), (int, float)) and n['lufs'] > -70}
    returns = {n['id'] for n in rep.get('nodes', []) if n.get('role') == 'return'
               and n.get('returnKind') in ('reverb', 'delay') and n['id'] in lufs}
    power: dict = {}
    for node in list(render.get('tracks', [])) + list(render.get('buses', [])):
        for bid, v in (node.get('sends') or {}).items():
            db = v.get('db') if isinstance(v, dict) else v
            if bid in returns and node['id'] in lufs and isinstance(db, (int, float)):
                power.setdefault(bid, {})[node['id']] = 10 ** ((lufs[node['id']] + db) / 10)
    out = {}
    for vid in vocals:
        if vid not in lufs:
            continue
        per = {}
        for bid, src in power.items():
            if vid in src:
                per[bid] = round(lufs[bid] + 10 * math.log10(src[vid] / sum(src.values())) - lufs[vid], 1)
        tot = round(10 * math.log10(sum(10 ** (x / 10) for x in per.values())), 1) if per else None
        out[vid] = {'wetLu': tot, 'returnsLu': per}
    return out


def report_lines(song, report) -> list[str]:
    """The vocal checks (check() + diction()) of a build, the vocal's wetness (wetness(): also written into
    report.json as nodes[].wetLu / wetReturnsLu) and the mic pulls written (mic_lines()), as printable lines (none
    when the song sings nothing)."""
    ids = lead_tracks(song)
    if not ids:
        return []
    try:
        fs = check(report, ids)
    except (OSError, ValueError):
        fs = None
    dic = [f for f in diction(song) if f['node'] in ids]
    lines = [f"vocals    [{f['severity']}] {f['message']}" for f in dic if f['severity'] != 'info']
    lines += [f"vocals    diction: {f['message']}" for f in dic if f['severity'] == 'info']
    lines += [f"vocals    [{f['severity']}] {f['message']}" for f in held_notes(song) if f['node'] in ids]
    rj = Path(report).parent / 'song.render.json' if not isinstance(report, dict) else None
    if rj is not None and rj.is_file():
        try:
            rep = json.loads(Path(report).read_text(encoding='utf-8'))
            wet = wetness(rep, json.loads(rj.read_text(encoding='utf-8')), [t.id for t in song.tracks.values()
                                                                          if getattr(t, '_singer', None)])
        except (OSError, ValueError):
            wet = {}
        if wet:
            for n in rep.get('nodes', []):
                if n['id'] in wet:
                    n['wetLu'], n['wetReturnsLu'] = wet[n['id']]['wetLu'], wet[n['id']]['returnsLu']
            Path(report).write_text(json.dumps(rep, indent=2), encoding='utf-8')
        for vid, w in wet.items():
            if vid in ids:
                lines.append(f"vocals    space: {vid!r} " + (
                    f"wet {w['wetLu']:+.1f} LU vs the dry voice (" + ', '.join(
                        f"{b} {x:+.1f}" for b, x in sorted(w['returnsLu'].items(), key=lambda kv: -kv[1]))
                    + "; estimated from the send shares)" if w['wetLu'] is not None else "dry (no reverb / echo send)"))
    lines += [f"vocals    mic pull: {x}" for x in mic_lines(song) if x.split(' ', 1)[0].strip("'") in ids]
    if fs is None:
        return lines
    if not fs:
        return [f"vocals    {', '.join(ids)}: intelligible (presence band owned), not buried, no harshness"] + lines
    return [f"vocals    [{f['severity']}] {f['message']}" for f in fs] + lines
