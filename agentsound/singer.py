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
from .theory import ComposeError

__all__ = ['STYLES', 'MOVES', 'FORMAT', 'Memory', 'Vocal', 'voice', 'sing', 'double', 'harmony', 'render',
           'phrase_notes', 'check', 'report_lines', 'log_lines', 'SingerError']

FORMAT = 3                      # bump when the rendering below changes (new cache keys)
MOVES = ('consonants', 'hold', 'glide', 'scoop', 'vibrato', 'fall', 'doit', 'release', 'swell', 'messa_di_voce',
         'taper', 'accents', 'breath', 'colour', 'timing', 'drift', 'link')
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
    'ballad': dict(vel=(56, 100), late_ms=14.0, jitter_ms=12.0, cons=1.12, speed=0.92, cons_share=0.4,
                   glide_ms=100.0, melisma_glide=0.6, overshoot_ct=10.0,
                   scoop_first=0.5, scoop_leap=0.6, scoop_peak=0.7, scoop_ct=60.0, scoop_ms=150.0,
                   vib_other=0.75, vib_peak=1.0, vib_ct=30.0, peak_vib_ct=44.0, vib_hz=5.2, vib_delay=0.38,
                   vib_grow=0.6, vib_min_s=0.6, wobble=0.18,
                   fall=0.1, doit=0.0, fall_semis=-1.6, release=0.85, taper=0.7, swell=0.6, messa=0.5,
                   accent=0.14, breath_db=-3.0, breath_min_s=0.25, drift_ct=6.0,
                   power=0.35, soft=0.8, base_power=0.0, base_soft=0.2, pitch_power=0.03,
                   spice_every=4, link=True, steps=24),
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
"""Per style: vel (touch range), timing (late_ms lay-back, jitter_ms), consonants (cons: x the model's length, speed:
the voicebank's consonant-speed embedding, cons_share: the most of a note before them the consonants may take),
glides (glide_ms, melisma_glide x in runs, overshoot_ct), scoops (chances: scoop_first / _leap / _peak, scoop_ct,
scoop_ms), vibrato (vib_other / vib_peak chances, vib_ct / peak_vib_ct depth in cents, vib_hz, vib_delay s, vib_grow s,
vib_min_s, wobble), phrase ends (fall, doit, fall_semis, release, taper), air (swell, messa on long notes, accent dB
per velocity step), breath_db (the breath's level), breath_min_s (the shortest gap that gets a breath), drift_ct,
voice colour (power / soft: how far the dynamics blend in the power / soft mode, base_power / base_soft, pitch_power
per semitone above the phrase), spice_every (bars between two falls / doits / big scoops), link, steps (diffusion
steps)."""


# ------------------------------------------------------------------------------------------------ memory

class Memory:
    """What one singer already sang in a song: pass the same Memory to every sing() call and the spice budget
    (falls, doits, big scoops) counts song-wide."""

    def __init__(self):
        self.budget = Budget({'spice': 0.0})

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
    keys: list = field(default_factory=list)
    rendered: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

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
         peaks=None, take: int = 0, formant: float = 0.0, offset_ms: float = 0.0, track_id: str = 'vocal',
         pan: float | None = None, gain_db: float = 0.0, split_s: float = 0.6, range_check: bool = True,
         **overrides) -> Vocal:
    """Sing `line` with `lyrics` at `at` (beat or Section) -> a Vocal (the part; .track is the vocal track).

    target: the Song (creates / reuses track `track_id` with the voice) or a vocal track (singer.voice()).
    voice: a voicebank id of assets/voices/manifest.json ('hanami', 'tiger'). style: STYLES ('pop', 'ballad',
    'rock'); overrides= any STYLES key (vib_ct=35, fall=0, ...). vel: (lo, hi) for humanize.touch phrase arcs (None:
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
    voicebank's range."""
    if style not in STYLES:
        raise SingerError(f"singer style must be one of {', '.join(STYLES)}, got {style!r}")
    if pitch not in ('player', 'model', 'hybrid'):
        raise SingerError(f"pitch must be 'player', 'hybrid' or 'model', got {pitch!r}")
    S = dict(STYLES[style])
    if pitch == 'hybrid':      # the pitch model already approaches notes from below: the player's scoops are smaller
        S['scoop_ct'] *= HYBRID_SCOOP
    for k, v in overrides.items():
        if k not in S:
            raise SingerError(f"sing(): unknown option {k!r} (a STYLES key: {', '.join(S)})")
        S[k] = v
    bank = _vb.get(voice)
    song, track = _vocal_track(target, track_id, bank, pan, gain_db)
    if mode is not None:
        bank.mode(mode) if bank.installed() else None
    clip, gestures, line_peaks = _line_of(line)
    if transpose:
        clip = clip.transpose(int(transpose))
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
                    any(abs(n.start - h) < 0.2 for h in hooks)) for n, s in zip(ns, sung)]
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
    plan, mlog, bud = _plan(notes, phrases, S, song, sd, memory, moves, gestures, base)
    vo = Vocal(song, track, bank, style, S, notes, phrases, plan, mlog, bud, seed_int(seed), int(take),
               float(formant), float(offset_ms), bool(moves), pitch, mode, 0.0, lyrics, line, warnings=warns)
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
            if n.kind == 'syllable' or n.kind == 'melisma':
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
    # timing feel: correlated jitter on the vowel onsets
    walk = 0.0
    for i, n in enumerate(notes):
        walk = 0.6 * walk + 0.4 * (2 * rng.random() - 1)
        plan[i]['late_ms'] = round(S['late_ms'] + S['jitter_ms'] * walk * (0.5 if n.kind != 'syllable' else 1.0), 2)
    log.sort(key=lambda x: x[0])
    return plan, log, budget


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
    return dict(format=FORMAT, bank=vo.bank.id, bank_sha=vo.bank.entry.get('sha256', ''), style=vo.style,
                params=S, notes=ns, seed=vo.seed, take=vo.take, formant=vo.formant, moves=vo.moves_on,
                pitch=vo.pitch_mode, mode=vo.mode)


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
                if not path.is_file():
                    todo.setdefault(vo.bank.id, []).append((vo, k, spec, path))
    for bank_id, items in todo.items():
        bank = _vb.get(bank_id).require()
        _vb.write_source(bank, root / bank_id)
        _synthesize(bank, items, root / bank_id, log)
    for t in tracks:
        _write_track(song, t)


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
    return {'op': 'duration', 'phonemes': ph, 'word_div': wd, 'word_dur': wdur, 'ph_midi': midi}


def _groups(ns: list) -> list:
    """Syllable groups of a phrase: a syllable note + its melisma / hold notes."""
    out = []
    for n in ns:
        if n['k'] == 'syllable' or not out:
            out.append(dict(t=n['t'], end=n['t'] + n['d'], m=n['m'], on=list(n['on']), nu=n['nu'], co=list(n['co']),
                            notes=[n], we=n['we'], ws=n['ws']))
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
    # 3. synthesis
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
                room = (Vn - V) * (S['cons_share'] if mv else 0.6)
                tot = sum(cl) + sum(ol)
                f = min(1.0, room / tot) if tot > 0 else 1.0
                cl = [x * f for x in cl]
                ol = [x * f for x in ol]
                c0 = Vn - sum(cl) - sum(ol)
                add(g['nu'], V, c0)
                tt = c0
                for p, d in zip(co + on, cl + ol):
                    add(p, tt, tt + d)
                    tt += d
            else:                                 # a rest: the coda closes the note, the onset leads the next
                cmax = 0.35 * max(0.05, end - V)
                f = min(1.0, cmax / sum(cl)) if cl and sum(cl) > 0 else 1.0
                cl = [x * f for x in cl]
                c0 = end - sum(cl)
                add(g['nu'], V, c0)
                tt = c0
                for p, d in zip(co, cl):
                    add(p, tt, tt + d)
                    tt += d
                f2 = min(1.0, 0.8 * gap / sum(ol)) if ol and sum(ol) > 0 else 1.0
                ol = [x * f2 for x in ol]
                o_start = Vn - sum(ol)
                bp = nxt['notes'][0]['plan'].get('breath') if mv else None
                rest = o_start - tt
                if bp and rest >= S['breath_min_s'] - 0.02:
                    b = max(0.12, min({'deep': 0.45, 'normal': 0.32, 'catch': 0.2}[bp['depth']], rest - 0.12))
                    add('SP', tt, o_start - 0.06 - b)
                    add('AP', o_start - 0.06 - b, o_start - 0.06)
                    add('SP', o_start - 0.06, o_start)
                elif rest > 0:
                    add('SP', tt, o_start)
                tt = o_start
                for p, d in zip(on, ol):
                    add(p, tt, tt + d)
                    tt += d
        else:
            cmax = 0.35 * max(0.05, end - V)
            f = min(1.0, cmax / sum(cl)) if cl and sum(cl) > 0 else 1.0
            cl = [x * f for x in cl]
            c0 = end - sum(cl)
            add(g['nu'], V, c0)
            tt = c0
            for p, d in zip(co, cl):
                add(p, tt, tt + d)
                tt += d
            add('SP', tt, tt + 0.35)
    # frames (from the file start)
    t0 = toks[0][1]
    bounds = [0]
    for p, a, b in toks:
        bounds.append(max(bounds[-1] + 1, round((b - t0) / FR)))
    durs = [bounds[i + 1] - bounds[i] for i in range(len(toks))]
    nf = bounds[-1]
    ftime = [t0 + (f + 0.5) * FR for f in range(nf)]          # phrase seconds of each frame centre
    if mv:
        moves, vmask = _move_lane(groups, _segments(groups, mv), S, ftime)
    else:
        moves, vmask = [0.0] * len(ftime), [0] * len(ftime)
    midi = _pitch_curve(spec, groups, ftime, rng, mv, S, moves)
    gain, mix = _air_and_colour(spec, groups, ftime, toks, t0, mv, S, bank, rng)
    return {'phonemes': [p for p, _, _ in toks], 'durations': durs, 'offset_s': t0, 'frames': nf, 'midi': midi,
            'vowels': [round(g['V'], 5) for g in groups], 'moves': [round(x, 4) for x in moves], 'vibmask': vmask,
            'gain': gain, 'mix': mix,
            'tokens': [(p, round(a, 4), round(b, 4)) for p, a, b in toks]}


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
    average) so the two never stack."""
    nf = len(model)
    moves, mask = plan['moves'], plan['vibmask']
    w = max(1, round(0.19 / FR / 2))
    out = list(model)
    for f in range(nf):
        if mask[f]:
            a, b = max(0, f - w), min(nf, f + w + 1)
            out[f] = sum(model[a:b]) / (b - a)
    return [round(out[f] + moves[f], 4) for f in range(nf)]


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
            if 'vibrato' in p:
                v = p['vibrato']
                # the vibrato of a run's last note / a held note: until the note (and its holds) end
                vend = g['end'] if j == len(g['notes']) - 1 else end
                kw = {k: v[k] for k in ('depth', 'hz', 'delay', 'grow', 'wobble') if k in v}
                out.append(G.vibrato(st, max(0.06, vend - st), 60, shape='centre', lane='bend',
                                     seed=int(st * 1000) + gi, **kw))
            if 'fall' in p:
                out.append(G.fall(g['end'], 60, semis=p['fall']['semis'], ms=p['fall'].get('ms', 220.0), air=0.0))
            if 'doit' in p:
                out.append(G.doit(g['end'], 60, semis=p['doit']['semis'], ms=p['doit'].get('ms', 160.0), air=0.0))
            if 'release' in p:
                out.append(G.breath_release(g['end'], 60, db=0.0, ms=p['release']['ms'], drop=p['release']['drop']))
            if 'bend' in p:
                out.append(G.bend(st, dur, 60, semis=p['bend']['semis']))
            if 'shake' in p:
                out.append(G.shake(st, dur, 60, interval=p['shake']['interval']))
    return out


def _air_and_colour(spec, groups, ftime, toks, t0, mv, S, bank, rng):
    """Gain (dB per frame) and the voice-mode blend ({speaker: [weight per frame]})."""
    nf = len(ftime)
    core = bank.mode('core')
    mode = spec.get('mode')
    if mode:
        sp = bank.mode(mode)
        return [0.0] * nf, {sp: 1.0}
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
                gs.append(G.taper(st, max(0.05, g['end'] - st), 60, **p['taper'], bright=0.0))
            if 'release' in p:
                gs.append(G.breath_release(g['end'], 60, db=p['release']['db'], ms=p['release']['ms'], drop=0.0))
    notes = [(g['V'] if j == 0 else n['t'], max(0.05, n['d']), n['v']) for g in groups for j, n in enumerate(g['notes'])]
    if S['accent'] and notes:
        gs.append(G.accents(notes, 60, db_per_vel=S['accent'], limit=5.0))
    air = [s for g in gs for s in g.shapes if s.lane == 'air']
    a_db = [0.0] * nf
    for f, t in enumerate(ftime):
        a_db[f] = sum(s(t) for s in air if s.t0 - 1e-6 <= t <= s.t1 + 1e-6)
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
    gain = [round(a_db[f] + br[f], 3) for f in range(nf)]
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
        ps = S['base_power'] + max(0.0, x) * S['power'] + hi * S['pitch_power']
        ss = S['base_soft'] + max(0.0, -x) * S['soft']
        w_core.append(1.0)
        w_soft.append(round(min(1.5, ss), 4))
        w_pow.append(round(min(1.5, ps), 4))
    mix = {core: w_core}
    mix[soft_n] = [a + b for a, b in zip(mix.get(soft_n, [0.0] * nf), w_soft)] if soft_n in mix else w_soft
    mix[pow_n] = [a + b for a, b in zip(mix.get(pow_n, [0.0] * nf), w_pow)] if pow_n in mix else w_pow
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
            'note_rest': note_rest, 'note_dur': note_dur, 'pitch': p['midi'], 'expr': 0.85, 'retake': True,
            'speaker': {bank.mode('core'): 1.0}, 'steps': 10}


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


# ------------------------------------------------------------------------------------------------ production

def double(vo: Vocal, *, pan: float = -0.6, take: int | None = None, offset_ms: float | None = None,
           gain_db: float = -7.0, track_id: str | None = None, formant: float | None = None, depth: float = 0.65,
           **overrides) -> Vocal:
    """A double of a sung part: the same line and words SUNG AGAIN (another take: other timing, vibrato and drift;
    a slightly different formant) on its own track, `gain_db` under, panned, a few ms late - not a copy (a copy
    phases). depth scales its vibrato / scoops (doubles sing plainer); overrides= STYLES keys. Returns the new
    Vocal."""
    n = sum(1 for t in vo.song.tracks.values() if getattr(t, '_singer', None)) + 1
    take = vo.take + n if take is None else take
    off = (14.0 + 9.0 * ((take * 7) % 3)) if offset_ms is None else offset_ms
    fm = (0.35 if pan < 0 else -0.35) if formant is None else formant
    tid = track_id or f"{vo.track.id}_dbl{'_l' if pan < 0 else '_r' if pan > 0 else ''}{n}"
    ov = dict(vib_ct=vo.params['vib_ct'] * depth, peak_vib_ct=vo.params['peak_vib_ct'] * depth,
              scoop_ct=vo.params['scoop_ct'] * depth, fall=vo.params['fall'] * 0.5, doit=0.0)
    for k, v in overrides.items():
        if k not in STYLES['pop']:
            raise SingerError(f"double(): unknown option {k!r} (a STYLES key: {', '.join(STYLES['pop'])})")
        ov[k] = v
    return _resing(vo, take=take, formant=fm, offset_ms=off, track_id=tid, pan=pan, gain_db=gain_db, overrides=ov)


def _clip_of(vo: Vocal) -> Clip:
    base = vo.notes[0].start if vo.notes else 0.0
    return Clip([(n.start - base, n.dur, n.pitch, n.vel) for n in vo.notes])


def _resing(vo: Vocal, *, take, formant, offset_ms, track_id, pan, gain_db, overrides, steps: int = 0,
            semitones: int = 0, key=None, mode=None) -> Vocal:
    """sing() the part of `vo` again (its notes as sung: velocities kept) with changes."""
    base = vo.notes[0].start if vo.notes else 0.0
    c = Clip([(n.start - base, n.dur, n.pitch, n.vel) for n in vo.notes])
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
    if vo.pitch_mode == 'hybrid' and 'scoop_ct' in overrides:
        ov['scoop_ct'] = overrides['scoop_ct'] / HYBRID_SCOOP
    return sing(vo.song, c, vo.lyrics_text, at=base, voice=vo.bank.id, style=vo.style, seed=vo.seed, vel=False,
                mode=mode if mode is not None else vo.mode, moves=vo.moves_on, pitch=vo.pitch_mode, take=take,
                formant=formant, offset_ms=offset_ms, track_id=track_id, pan=pan, gain_db=gain_db, **ov)


def harmony(vo: Vocal, *, steps: int = 2, semitones: int = 0, key=None, pan: float = 0.35, gain_db: float = -6.0,
            take: int | None = None, offset_ms: float = 8.0, track_id: str | None = None, formant: float = 0.2,
            depth: float = 0.7, mode: str | None = None) -> Vocal:
    """A harmony part: the line moved by `steps` scale steps in `key` (2 = a third above, -2 a third below; the song's
    key by default) or by `semitones`, with the same words, SUNG again by the voicebank (not a pitch shift) on its own
    track, `gain_db` under, panned. depth scales its vibrato / scoops. Returns the new Vocal."""
    n = sum(1 for t in vo.song.tracks.values() if getattr(t, '_singer', None)) + 1
    tk = vo.take + 10 + n if take is None else take
    tid = track_id or f"{vo.track.id}_harm{n}"
    ov = dict(vib_ct=vo.params['vib_ct'] * depth, peak_vib_ct=vo.params['peak_vib_ct'] * depth,
              scoop_ct=vo.params['scoop_ct'] * depth, fall=vo.params['fall'] * 0.5, doit=0.0)
    return _resing(vo, take=tk, formant=formant, offset_ms=offset_ms, track_id=tid, pan=pan, gain_db=gain_db,
                   overrides=ov, steps=steps, semitones=semitones, key=key, mode=mode)


# ------------------------------------------------------------------------------------------------ the ears

def log_lines(song) -> list[str]:
    """One line per sung part: voice, style, notes / phrases, the moves it sang and what the budget dropped."""
    out = []
    for t in song.tracks.values():
        info = getattr(t, '_singer', None)
        if not info:
            continue
        for vo in info['parts']:
            sm = ', '.join(f"{k} {v}" for k, v in vo.summary().items()) or 'none (moves off)'
            drop = f"; spice budget dropped {len(vo.budget['dropped'])}" if vo.budget.get('dropped') else ''
            out.append(f"{t.id!r}: {vo.bank.id} {vo.style}{'' if vo.moves_on else ' ROBOTIC'} pitch={vo.pitch_mode}, "
                       f"take {vo.take}, {len(vo.notes)} notes in {len(vo.phrases)} phrases; moves: {sm}{drop}")
            out += [f"{t.id!r}: {w}" for w in vo.warnings]
    return out


def check(report, vocals=None, *, presence_min: float = 40.0, rival: float = 0.6, harsh: float = 22.0) -> list[dict]:
    """The vocal's ears on a build's report (report.json path or dict): findings [{'severity', 'code', 'node',
    'message'}].
      intelligibility  the words live at 2-6 kHz (the report's 'presence' band): the lead vocal should own at least
                       `presence_min` % of the mix there; a competitor (keys, guitars, pads ...) with more than
                       `rival` x the vocal's share masks the words (fix: its presence dip / the vocal hero's carve);
      buried           the vocal under the loudest other track in the sections it sings;
      harsh            more than `harsh` % of the vocal's own energy in 2.5-6 kHz (de-ess / less presence);
      masking          the report's own masking warnings that name a vocal track.
    vocals: track ids (default: the report's nodes named vocal* / vox*, or the song's vocal tracks)."""
    import re
    rep = report if isinstance(report, dict) else json.loads(Path(report).read_text(encoding='utf-8'))
    nodes = {n['id']: n for n in rep.get('nodes', [])}
    if vocals is None:
        vocals = [i for i in nodes if re.match(r'^(vocal|vox|lead_vocal)', i) and not re.search(r'_(dbl|harm)', i)]
    out = []
    for vid in vocals:
        v = nodes.get(vid)
        if v is None:
            continue
        share = (v.get('mixSharePct') or {}).get('presence', 0.0)
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
            if others and others[0]['rmsDb'] > me['rmsDb'] + 1.0:
                out.append(dict(severity='warn', code='vocal_buried', node=vid,
                                message=f"in {sec['name']!r} the vocal ({me['rmsDb']:.1f} dB RMS) sits under "
                                        f"{others[0]['id']!r} ({others[0]['rmsDb']:.1f} dB): a lead vocal leads"))
    for w in rep.get('warnings', []):
        if w.get('code') == 'masking' and any(n in vocals for n in w.get('nodes', [])):
            out.append(dict(severity='info', code='vocal_masking', node=','.join(w.get('nodes', [])),
                            message=w.get('message', '')))
    return out


def report_lines(song, report) -> list[str]:
    """The vocal checks (check()) of a build, as printable lines (none when the song sings nothing)."""
    ids = [t.id for t in song.tracks.values() if getattr(t, '_singer', None) and not re.search(r'_(dbl|harm)', t.id)]
    if not ids:
        return []
    try:
        fs = check(report, ids)
    except (OSError, ValueError):
        return []
    if not fs:
        return [f"vocals    {', '.join(ids)}: intelligible (presence band owned), not buried, no harshness"]
    return [f"vocals    [{f['severity']}] {f['message']}" for f in fs]
