"""EDM sound library: the sounds of house / techno / big room / future bass / melodic house (recipes/edm.md) that the
synthwave library does not already have - reused there wherever a sound fits (pads, risers, impacts, sub).

  basses   edm/bass (sub + mid layer, the club bass), edm/reese (a wide, phasing reese mid over the same sub)
  chords   edm/supersaw (big-room / melodic supersaw chords with an octave-down body), edm/future_chords (future-bass
           saw chords with a formant colour and a slow pitch wobble: play them with the kick pump)
  plucks   edm/pluck (the melodic-house / progressive pluck: plays into the echo)
  leads    edm/lead (the supersaw hook WITH body: a supersaw over an octave-down saw - never a thin beep)
  chains   edm/vocal_chop (the vocal chop insert chain: singer.chops), master/edm (the loud club master)

The kick pump (sidechain), the 909 / 808 / main-room kits, the sub thump under the kick and the transitions are the
band presets' job (agentsound/bandlib/edm.py, bands.make('house' ...)), not patches: one sound, one patch.

Levels: every instrument patch lands at about -18 LUFS on its audition material at gain_db 0, like the rest of the
library (`python -m agentsound audition edm/<name>`); the measured value is in the notes. Version: VERSION.
"""

from __future__ import annotations

from ..vamod import lfo
from . import Patch, fx, inst, layer, register
from . import synthwave_drums_bass, synthwave_leads_fx  # noqa: F401  (layers name their patches)

VERSION = 1

# audition-calibrated gain_db (python -m agentsound audition edm/<name>: -18.0 LUFS)
LEVELS = {'bass': 0.6, 'reese': 3.2, 'supersaw': 2.3, 'future_chords': 2.4, 'pluck': 0.0, 'lead': -1.3}


def _eq(**bands):
    return fx.eq({k.replace('__', '.'): v for k, v in bands.items()})


# ------------------------------------------------------------------------------------------------ basses

def _mid_bass():
    """The mid layer of the club bass: two saws (7 ct apart) + a square an octave up for bite, a ladder that opens on
    every note, mono legato (slides between overlapping notes)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__semi=12, osc2__level=0.35, osc2__fine=7,
                   mode='legato', glide=0.03, filter__type='ladder', cutoff=900, resonance=0.25, filter__drive=0.45,
                   filter__keytrack=0.5, filter__env=1.6, filter__velocity=0.8, fenv__attack=0.002, fenv__decay=0.22,
                   fenv__sustain=0.35, fenv__release=0.1, amp__attack=0.003, amp__decay=0.6, amp__sustain=0.9,
                   amp__release=0.07, amp__velocity=0.6, drift__pitch=1, level=-3.0)


register(Patch.layered(
    'edm/bass',
    layer(_mid_bass(), 'mid', fx=[_eq(hp__freq=100, hp__slope=24, peak1__freq=350, peak1__gain=-2.0),
                                  fx.saturator(mode='tube', drive=6, mix=0.5)]),
    layer('synthwave/sub_bass', 'sub', level=-1.0, cutoff=110),
    gain_db=LEVELS['bass'],
    fx=[fx.compressor(threshold=-20, ratio=4, attack=8, release=90, knee=6, automakeup='on')],
    audition={'notes': 'bass'},
    notes=f"""v{VERSION}. The club bass, SUB + MID: a clean sine sub (synthwave/sub_bass, low-passed at 110 Hz, mono) under
a driven saw / square mid layer high-passed at 100 Hz (24 dB/oct) - the sub carries 40-90 Hz, the mid the notes you hear
on a phone (150 Hz-2 kHz), and the crossover keeps the two fundamentals apart. Mono legato (overlapping notes slide 30
ms). Play roots / octaves / offbeat 8ths E1-E2 (house: the off-beat bass between the kicks; future bass / melodic:
held roots under the drops), velocities 80-120 (velocity opens the mid's filter). The band presets sidechain it 8-12
dB to the kick. Tweak: .layer('sub', level=2) (more weight), .but(**{{'layers.mid.cutoff': 1400}}) (brighter),
.layer('mid', mute=True) (sub only, breakdowns). No reverb.""" + f" Level: {LEVELS['bass']:+.1f} dB = -18 LUFS (audition bass)."))


register(Patch.layered(
    'edm/reese',
    layer(inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=1.0, osc2__fine=18, unison=3, unison__detune=0.35,
                  unison__spread=0.6, mode='legato', glide=0.05, filter__type='ladder', cutoff=700, resonance=0.2,
                  filter__drive=0.6, filter__keytrack=0.4, filter__env=1.0, fenv__decay=0.5, fenv__sustain=0.6,
                  amp__attack=0.005, amp__sustain=1.0, amp__release=0.12, amp__velocity=0.5,
                  mods=[lfo('sine', rate=8, mode='global', id='move') >> ('cutoff', 0.6)], level=-6.0),
          'mid', fx=[fx.compressor(threshold=-20, ratio=3, attack=10, release=120, knee=6, automakeup='on'),
                     _eq(hp__freq=110, hp__slope=24), fx.saturator(mode='tape', drive=8, mix=0.6),
                     fx.chorus(mode='I', mix=0.3)]),
    layer('synthwave/sub_bass', 'sub', level=-1.0, cutoff=110),
    gain_db=LEVELS['reese'],
    audition={'notes': 'roots'},
    notes=f"""v{VERSION}. The reese: two detuned saw stacks phasing against each other (osc2 +18 ct, 3-voice unison), driven,
its filter breathing over 2 bars, chorused above 110 Hz - over the same clean mono sub as edm/bass. Techno rumbles,
melodic-house / progressive drops, a dark breakdown bass. Play held roots and slow lines E1-E2 (legato slides).
Tweak: .but(**{{'layers.mid.cutoff': 1100}}) (more growl), .but(**{{'layers.mid.mod.move.amount': 1.2}}) (deeper
movement). Level: {LEVELS['reese']:+.1f} dB = -18 LUFS (audition roots)."""))


# ------------------------------------------------------------------------------------------------ chords

register(Patch(
    'edm/supersaw',
    instrument=inst.va(osc1__wave='saw', osc2__wave='saw', osc2__semi=-12, osc2__level=0.35, unison=7,
                       unison__detune=0.7, unison__spread=0.9, filter__type='ladder', cutoff=5200, resonance=0.1,
                       filter__drive=0.2, filter__keytrack=0.4, filter__env=0.8, fenv__decay=0.5, fenv__sustain=0.7,
                       amp__attack=0.004, amp__decay=0.6, amp__sustain=0.85, amp__release=0.3, amp__velocity=0.8,
                       hpf=150, polyphony=24, level=-5.1),
    fx=[_eq(peak1__freq=350, peak1__gain=-3.0, peak3__freq=3200, peak3__gain=-2.0, peak3__q=1.0, high__freq=10000,
            high__gain=1.5),
        fx.width(width=1.15)],
    gain_db=LEVELS['supersaw'],
    sends={'hall': -14},
    audition={'notes': 'chord'},
    notes=f"""v{VERSION}. Big-room / melodic supersaw CHORDS: 7-voice JP-8000 unison (detune 0.7, spread 0.9) plus a saw an
octave down for body under the wall, ladder open at 5.2 kHz, high-passed at 150 Hz (the bass owns the low end), -3 dB at
350 Hz and -2 dB at 3.2 kHz (no mud, no fizz). Play 3-4 note chords C3-C5 (spread voicings) as whole-bar pads, 8th /
offbeat stabs or the drop's rhythm; the band presets pump it 6-10 dB from the kick. Not a hook sound on its own: the
hook goes on edm/lead, a sampled piano or the vocal. Tweak: unison.detune 0.5-0.8, cutoff 2500-8000 (automate it with
automation.riser in builds), amp.release 0.1-0.6. Sends: hall -14. Level: {LEVELS['supersaw']:+.1f} dB = -18 LUFS
(audition chord)."""))

register(Patch(
    'edm/future_chords',
    instrument=inst.va(osc1__wave='saw', osc2__wave='square', osc2__pw=0.35, osc2__level=0.6, osc2__fine=-9,
                       unison=5, unison__detune=0.45, unison__spread=0.85, filter__type='ladder', cutoff=2600,
                       resonance=0.2, filter__drive=0.3, filter__keytrack=0.5, filter__env=1.2, fenv__attack=0.01,
                       fenv__decay=0.35, fenv__sustain=0.55, amp__attack=0.006, amp__decay=0.8, amp__sustain=0.85,
                       amp__release=0.25, amp__velocity=0.8, hpf=160, polyphony=24,
                       mods=[lfo('sine', hz=0.35, mode='global', id='wob') >> ('pitch', 12)], level=-4.6),
    fx=[fx.vowel(vowel='a', morph=0.6, gender=0.4, resonance=0.4, mix=0.35),
        fx.saturator(mode='tape', drive=4, mix=0.5),
        fx.chorus(mode='I+II', mix=0.35),
        _eq(peak1__freq=400, peak1__gain=-2.5, peak3__freq=3000, peak3__gain=-1.5, high__freq=9000, high__gain=2.0)],
    gain_db=LEVELS['future_chords'],
    sends={'hall': -12},
    audition={'notes': 'chord'},
    notes=f"""v{VERSION}. FUTURE-BASS chords (wavetable-ish): saw + detuned narrow pulse in a 5-voice unison through a ladder,
a slow 12 ct pitch wobble (the detuned-tape sway), a formant filter half way between 'ah' and 'eh' (the vowel colour of
the genre's chords, 35 % wet), tape drive, Juno chorus I+II. Play 4-5 note chords C3-E5 (add9 / maj7 / min9 voicings) in
the drop's rhythm: 8th / 16th stabs and held swells; the genre's 'breathing' is the kick pump (the future_bass preset
ducks them 12 dB with a long release) and pitch bends INTO the chords (automate instrument.pitchbend -2 -> 0 over an
8th: patches / chords sliding up). Tweak: mod.wob.amount 0-30 ct, fx.vowel.morph 0-1 (a -> e), cutoff 1500-5000.
Sends: hall -12. Level: {LEVELS['future_chords']:+.1f} dB = -18 LUFS (audition chord)."""))


# ------------------------------------------------------------------------------------------------ pluck, lead

register(Patch(
    'edm/pluck',
    instrument=inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.5, osc2__fine=8, unison=3,
                       unison__detune=0.3, unison__spread=0.7, filter__type='ladder', cutoff=900, resonance=0.25,
                       filter__keytrack=0.6, filter__env=3.2, filter__velocity=1.0, fenv__attack=0.001,
                       fenv__decay=0.16, fenv__sustain=0.0, fenv__release=0.12, amp__attack=0.002, amp__decay=0.38,
                       amp__sustain=0.0, amp__release=0.2, amp__velocity=0.7, hpf=220, polyphony=16, level=5.7),
    fx=[fx.chorus(mode='I', mix=0.3), _eq(peak3__freq=3500, peak3__gain=-1.5, high__freq=9000, high__gain=1.0)],
    gain_db=LEVELS['pluck'],
    sends={'echo': -10, 'hall': -14},
    audition={'notes': 'arp'},
    notes=f"""v{VERSION}. The melodic-house / progressive PLUCK: saw + square (3-voice unison) with a fast filter blip
(3.2 octaves, 160 ms) and no sustain, velocity -> brightness, high-passed at 220 Hz, a little chorus. Play 16th / 8th
chord-tone patterns C4-C6 (patterns.arp, a syncopated riff) INTO the dotted-8th echo (the repeats are half the sound);
accents on the off-beats. Tweak: fenv.decay 0.1-0.3 (longer = more 'pluck-pad'), cutoff 600-2000, amp.decay 0.2-0.6.
Sends: echo -10, hall -14. Level: {LEVELS['pluck']:+.1f} dB = -18 LUFS (audition arp)."""))

register(Patch.layered(
    'edm/lead',
    layer('synthwave/supersaw_lead', 'saw'),
    layer(inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.5, osc2__fine=-6, filter__type='ladder',
                  cutoff=1100, resonance=0.15, filter__drive=0.35, filter__keytrack=0.4, filter__env=0.8,
                  fenv__decay=0.4, fenv__sustain=0.6, amp__attack=0.004, amp__sustain=0.9, amp__release=0.3,
                  amp__velocity=0.6, polyphony=8,
                  mods=[lfo('sine', hz=5.4, delay=0.35, fade=0.4, id='vib') >> ('pitch', 14)], level=-6.0),
          'body', transpose=-12, level=-5.0,
          fx=[fx.compressor(threshold=-20, ratio=2.5, attack=15, release=120, knee=6, automakeup='on'),
              _eq(hp__freq=120, lp__freq=2500)]),
    gain_db=LEVELS['lead'],
    sends={'hall': -12, 'echo': -12},
    audition={'notes': 'phrase'},
    notes=f"""v{VERSION}. The EDM hook lead WITH BODY (recipes/HUMAN_FEEDBACK.md: never a thin beep): the supersaw lead
(synthwave/supersaw_lead: 7-voice saw + octave sparkle, microshift halo) over a saw + pulse body an octave DOWN
(low-passed at 2.5 kHz, delayed vibrato 14 ct) - the weight under 1 kHz that makes a high hook sing instead of beep.
A loose 2.5:1 compressor on the body (the saw layer's microshift stays after any compression) keeps the note-to-note dynamics (velocity -> level and brightness). Play the hook A4-C6 (the
body sounds A3-C5), velocities 64-118 with phrase arcs; slides with clip.legato() + glide. Tweak: .layer('body',
level=-2) (fatter), .layer('saw', level=-3) (darker). Sends: hall -12, echo -12. Level: {LEVELS['lead']:+.1f} dB = -18
LUFS (audition phrase)."""))


# ------------------------------------------------------------------------------------------------ chains

register(Patch(
    'edm/vocal_chop',
    fx=[_eq(hp__freq=220, hp__slope=24, peak1__freq=400, peak1__gain=-2.0, peak3__freq=3500, peak3__gain=2.0,
            high__freq=10000, high__gain=2.0),
        fx.compressor(threshold=-22, ratio=2.5, attack=12, release=80, knee=6, automakeup='on'),
        fx.saturator(mode='tape', drive=4, mix=0.4),
        fx.chorus(mode='I', mix=0.2)],
    notes=f"""v{VERSION}. The vocal CHOP insert chain (singer.chops puts it on a new chops track): high-passed at 220 Hz (the
chops sit above the bass and the chords' body), -2 dB at 400 Hz, +2 dB presence and air, a 2.5:1 compressor with a 12 ms
attack (the chops even, their velocity accents kept), tape drive and a little Juno chorus. Sends are the song's: echo -10..-14 (the chop's tail in the
gaps), hall -14."""))

register(Patch(
    'master/edm',
    fx=[_eq(hp__freq=25, peak1__freq=300, peak1__gain=-1.5, peak1__q=0.8, peak3__freq=3500, peak3__gain=-0.5,
            high__freq=11000, high__gain=1.5),
        fx.compressor(threshold=-10, ratio=2, attack=30, release=150, knee=8, detector='rms', keyhp=100,
                      automakeup='on'),
        fx.saturator(mode='tape', drive=3, mix=0.5),
        fx.width(width=1.2, monobass=150),
        fx.limiter(gain=8.0, ceiling=-1.2, release=30)],
    notes=f"""v{VERSION}. The club master: -1.5 dB at 300 Hz (room for the kick / bass split), an air shelf, a 2:1 glue
compressor that only works above -10 dB (the drops), tape (a soft clip that rounds the kick's peaks before the limiter),
width 1.2 with everything under 150 Hz mono, a fast limiter (30 ms release, ceiling -1.2 dBFS true-peak safe: past ~10 dB of drive
the loudness only follows the release - a dense drop lands at -9..-8.5 LUFS). Set the limiter gain
for drops at -9..-6 LUFS (the edm profile: -10..-6 integrated): .but_fx('limiter', gain=10); ride it per section (s.master.lane('fx.limiter.gain',
...)) so the breakdowns stay softer."""))
