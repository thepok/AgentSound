"""Wavetable sound library (engine 'wavetable', inst.wavetable): the va's voice engine with morphing wavetables.

  wavetable/warm_pad      soft triangle-saw tables, slow shared drift of the position: the warm bed
  wavetable/evolving_pad  vowel table that keeps turning (slow random position) + a harmonic sweep that blooms
  wavetable/pluck         harmonic burst that falls back to the fundamental: marimba-like / glassy plucks, arps
  wavetable/bass          saw-square table + sine sub, mono legato, a position 'bite' on every note
  wavetable/lead          vocal (formant) lead WITH body: an octave-down saw layer, delayed vibrato, glide,
                          a breath of position movement - never a thin beep (recipes/HUMAN_FEEDBACK.md)

Level calibration as everywhere: every patch at gain_db 0 lands at about -18 LUFS on its audition phrase
(`python -m agentsound audition wavetable/<name>`); the calibration is the instrument's `level`. Built-in tables
only, so nothing needs installing. A file table: patches.get('wavetable/warm_pad').but(**{'osc1.table': 'x.wav'}).
"""

from ..vamod import env, lfo, velocity
from . import Patch, fx, inst, register

VERSION = 1


def _wt(table, table2=None, **p):
    """inst.wavetable with '__' -> '.' in the keyword names (osc1__position -> osc1.position)."""
    return inst.wavetable(table, {k.replace('__', '.'): v for k, v in p.items()}, table2=table2)


register(Patch(
    'wavetable/warm_pad',
    instrument=_wt('basic', 'basic',
                   osc1__position=0.48, osc2__position=0.56, osc2__level=0.75, osc2__fine=7,
                   unison=3, unison__detune=0.25, unison__spread=0.8,
                   mods=[lfo('smoothrandom', hz=0.15, mode='global', id='drift') >> ('osc1.position', 0.12),
                         lfo('sine', hz=0.11, mode='global', phase=0.5, id='drift2') >> ('osc2.position', 0.1)],
                   filter__type='ladder', cutoff=2200, resonance=0.1, filter__keytrack=0.5, filter__velocity=0.3,
                   filter__env=0.8, fenv__attack=0.8, fenv__decay=3.0, fenv__sustain=0.5, fenv__release=1.5,
                   amp__attack=0.5, amp__decay=2.0, amp__sustain=1.0, amp__release=1.8, amp__velocity=0.3,
                   hpf=140, drift__pitch=3, drift__cutoff=0.8, level=-6.9),
    fx=[fx.chorus(mode='II', mix=0.5),
        fx.eq({'peak1.freq': 320, 'peak1.gain': -2.5, 'peak1.q': 0.8}),
        fx.dimension(mode=1)],
    sends={'hall': -8},
    notes='v1. Warm wavetable pad: two "basic" tables between triangle and saw (positions 0.48 / 0.56, 7 ct apart), '
          'unison 3, each position drifting slowly on a shared global LFO (smooth random 0.15 Hz / sine 0.11 Hz), so '
          'held chords breathe without a filter wobble; 24 dB ladder at 2.2 kHz with a slow bloom, 0.5 s attack, '
          '1.8 s release, HPF 140 Hz, Juno chorus II + dimension. Range: chords C3-C5. Use: a softer, rounder '
          'alternative to synthwave/warm_pad, ambient / new-age beds. Tweak: osc1.position 0.33 (pure triangle, '
          'darker) .. 0.67 (saw, brighter), mod.drift.amount 0-0.25 (movement), cutoff 1200-5000, amp.attack '
          '0.1-2. Sends: hall -8. Measured -18.1 LUFS (audition chords).'))

register(Patch(
    'wavetable/evolving_pad',
    instrument=_wt('formant', 'harmonics',
                   osc1__position=0.3, osc2__position=0.05, osc2__level=0.45, osc2__semi=12, osc2__fine=4,
                   unison=5, unison__detune=0.3, unison__spread=0.9,
                   mods=[lfo('smoothrandom', rate=8, mode='global', id='vowel') >> ('osc1.position', 0.45),
                         env(a=3.0, d=6.0, s=0.5, r=3.0, id='bloom') >> ('osc2.position', 0.5),
                         lfo('triangle', rate=16, mode='global', id='breathe') >> ('cutoff', 0.4)],
                   filter__type='lp12', cutoff=3200, resonance=0.15, filter__keytrack=0.4, filter__velocity=0.4,
                   filter__env=0.0, amp__attack=1.2, amp__decay=2.0, amp__sustain=1.0, amp__release=3.0,
                   amp__velocity=0.3, hpf=160, drift__pitch=3, level=-7.3),
    fx=[fx.chorus(mode='I', mix=0.4), fx.dimension(mode=2)],
    sends={'hall': -6},
    notes='v1. Evolving wavetable pad: a vowel table (formant: a-e-i-o-u) whose position wanders on a slow tempo-synced '
          'smooth-random LFO (every 8 beats a new vowel, glided), plus an octave-up harmonic-sweep table that blooms '
          'over the first 3 s of each chord (env -> osc2.position) and a 16-beat filter breath; unison 5, 1.2 s '
          'attack, 3 s release. The chord keeps changing colour while it is held - for intros, breakdowns, ambient '
          'and film beds (one long chord per bar or two). Range: C3-C5. Tweak: mod.vowel.amount 0.2-0.6 (how far the '
          'vowels travel), mod.bloom.amount 0-0.8, osc2.level 0-0.7 (the glassy top), cutoff 2000-6000. Sends: hall -6 '
          '(+ shimmer for dreamier). Measured -18.0 LUFS (audition chords).'))

register(Patch(
    'wavetable/pluck',
    instrument=_wt('harmonics', 'basic',
                   osc1__position=0.06, osc2__position=0.62, osc2__level=0.35, osc2__semi=-12,
                   osc__retrig=True, unison=2, unison__detune=0.15, unison__spread=0.6,
                   mods=[env(a=0.0, d=0.22, s=0.0, r=0.2, id='strike') >> ('osc1.position', 0.5),
                         velocity(id='hard') >> ('osc1.position', 0.15)],
                   filter__type='ladder', cutoff=1800, resonance=0.15, filter__keytrack=0.6, filter__velocity=1.2,
                   filter__env=2.5, fenv__attack=0.001, fenv__decay=0.25, fenv__sustain=0.0, fenv__release=0.25,
                   amp__attack=0.001, amp__decay=0.9, amp__sustain=0.0, amp__release=0.35, amp__velocity=0.7,
                   hpf=120, drift__pitch=1, level=7.3),
    fx=[fx.eq({'peak1.freq': 300, 'peak1.gain': -2, 'peak1.q': 0.8}), fx.dimension(mode=1)],
    sends={'plate': -12, 'echo': -16},
    notes='v1. Wavetable pluck: the "harmonics" table struck at a bright frame and falling back to the fundamental '
          'in ~0.2 s (env -> osc1.position; harder notes start brighter: velocity -> position and cutoff), a soft '
          'saw an octave below for body, a quick ladder envelope, 0.9 s decay. Reads like a mallet / glassy pluck, '
          'not a beep: arps, ostinatos, counter-lines in C4-C6, 8ths and 16ths (velocities 60-120 make it speak). '
          'Tweak: mod.strike.amount 0.3-0.8 (brightness of the strike), amp.decay 0.3-2, osc2.level 0-0.6. '
          'Sends: plate -12, echo -16 (dotted 8ths). Measured -18.0 LUFS (audition arp).'))

register(Patch(
    'wavetable/bass',
    instrument=_wt('basic', 'sine',
                   osc1__position=0.78, osc2__level=0.0, sub__level=0.65, sub__wave='sine', sub__octave=-1,
                   mode='legato', glide=0.035, osc__retrig=True,
                   mods=[env(a=0.0, d=0.12, s=0.0, r=0.1, id='bite') >> ('osc1.position', -0.3)],
                   filter__type='ladder', cutoff=420, resonance=0.25, filter__drive=0.35, filter__keytrack=0.4,
                   filter__velocity=0.6, filter__env=2.4, fenv__attack=0.002, fenv__decay=0.28, fenv__sustain=0.3,
                   fenv__release=0.12, amp__attack=0.003, amp__decay=0.8, amp__sustain=0.9, amp__release=0.1,
                   amp__velocity=0.4, drift__pitch=1, level=2.1),
    fx=[fx.eq({'hp.freq': 28, 'peak1.freq': 250, 'peak1.gain': -1.5, 'peak1.q': 0.9})],
    notes='v1. Wavetable bass: the "basic" table between saw and square (position 0.78) whose attack dips towards the '
          'saw for a moment (env -> position: a vocal "bite" on every note), a clean sine sub an octave down for the '
          'weight, mono legato with a 35 ms glide on overlapping notes, a driven 24 dB ladder at 420 Hz with a quick '
          'envelope. Roots E1-A2, 8ths or held notes. Tweak: cutoff 250-1000, filter.env 1.5-4, sub.level 0.4-0.9, '
          'mod.bite.amount -0.5..0, osc1.warp "bend" + osc1.warp.amount 0.2-0.5 for growl. No reverb; sidechain to '
          'the kick (depth 4-8 dB). Measured -18.0 LUFS (audition 8th roots / octaves).'))

register(Patch(
    'wavetable/lead',
    instrument=_wt('formant', 'basic',
                   osc1__position=0.22, osc2__position=0.62, osc2__level=0.7, osc2__semi=-12, osc2__fine=-3,
                   sub__level=0.0, unison=3, unison__detune=0.18, unison__spread=0.5,
                   mode='mono', glide=0.03,
                   mods=[lfo('sine', hz=5.2, delay=0.35, fade=0.5, id='vib') >> ('pitch', 16),
                         env(a=0.25, d=1.2, s=0.4, r=0.4, id='open') >> ('osc1.position', 0.18),
                         velocity(id='hard') >> ('cutoff', 1.0)],
                   filter__type='ladder', cutoff=2100, resonance=0.18, filter__drive=0.3, filter__keytrack=0.45,
                   filter__velocity=0.0, filter__env=1.0, fenv__attack=0.02, fenv__decay=0.6, fenv__sustain=0.45,
                   fenv__release=0.3, amp__attack=0.012, amp__decay=1.0, amp__sustain=0.85, amp__release=0.3,
                   amp__velocity=0.85, hpf=90, drift__pitch=3, level=1.8),
    fx=[fx.eq({'peak1.freq': 300, 'peak1.gain': -1.5, 'peak1.q': 0.8, 'peak3.freq': 3200, 'peak3.gain': -2,
               'peak3.q': 1.0}),
        fx.chorus(mode='I', mix=0.3)],
    sends={'plate': -10, 'echo': -14},
    notes='v1. Wavetable lead with body (not a beep: recipes/HUMAN_FEEDBACK.md "Melody / lead sound"): a vocal formant '
          'table (between "a" and "e") opening a little over each note (env -> position), doubled an octave below by '
          'a warm saw-square layer at -3 dB (the weight below 1 kHz), unison 3, mono (every note re-attacks, so the '
          'velocities speak: amp.velocity 0.85) with a 30 ms glide, a delayed vibrato (16 ct, after 0.35 s), velocity '
          '-> cutoff, a driven ladder. Play the line in C3-C5 (not A4-A6) with velocity arcs (60-120). For a hook still '
          'prefer a sampled lead / hero; this is the synth lead that may carry a counter-line or a solo. Tweak: '
          'osc1.position 0 ("a", open) .. 0.5 ("i", nasal), mod.vib.amount 0-30, glide 0-0.12, mode "legato" (slides '
          'only between overlapping notes, no re-attack), osc2.level 0.4-0.9. Sends: plate -10, echo -14. Measured '
          '-18.0 LUFS (audition phrase).'))
