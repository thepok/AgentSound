"""Synthwave sound library, part 2: leads, arps/plucks, FX hits and the delay/width return buses.

  leads     synthwave/supersaw_lead pulse_lead solo_lead sync_lead soft_lead brass_lead dx_lead
  arps      synthwave/stranger_arp arp_pluck arp_glass seq_pulse
  fx        synthwave/noise_riser downlifter impact laser
  returns   bus/echo bus/tape_echo bus/echo_quarter bus/wide

Every instrument patch is level-calibrated: at gain_db 0, playing its natural material (see each
patch's notes: `python -m agentsound audition <name> --notes phrase|arp|chord`), the track lands at
about -18 LUFS integrated, so a song starts from a balanced mix. The calibration lives in the
instrument's `level` param (gain_db stays 0 for the composer). Space (reverb) is left to the shared
send buses (bus/hall, bus/plate, bus/echo, bus/gated) except where it is part of the sound (FX hits).

Version: synthwave_leads_fx v5 (2026-09-29). v2 = producer review: impact rebuilt, arp_glass high-pass, laser top
tamed; v3 = vibrato, PWM and pitch sweeps moved to the va modulation matrix ('mods', agentsound.vamod) - same sound;
v4 = DX7 engine fixes: arp_glass thump high-pass removed, DX levels re-matched to the phrase autolevel; v5 = lush
pass: leads get a `microshift` doubler (a wide halo around a strong centre: 20-45 % wide instead of 5-30 %), arps
Juno chorus II + `dimension` (40-75 % wide), risers stereo noise, the echo returns are wide ping-pongs again
(bus/echo was 5 % wide) and calibrated audible, default sends at the recipe's recommended levels (leads hall -10..-12
+ echo -12, arps echo -10 + hall -14). Modulation amounts are params: .but(**{'mod.vib.amount': 25}); swap a route by
its id with .with_mods(...).
"""

from __future__ import annotations

from ..vamod import env, lfo
from . import Patch, fx, inst, register

VERSION = 5


def _reg(name, instrument=None, fx_=(), sends=None, notes=''):
    register(Patch(name, instrument=instrument, fx=list(fx_), gain_db=0.0, pan=0.0, sends=sends or {},
                   notes=notes.strip()))


def _shift(style='smooth', detune=9, mix=0.35):
    """Micro-pitch-shift doubler for leads: left +detune / right -detune voices around the untouched centre."""
    return fx.microshift(style=style, detune=detune, mix=mix)


# ------------------------------------------------------------------------------------------ leads

_reg('synthwave/supersaw_lead',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.3, osc2__semi=12,
             unison=7, unison__detune=0.68, unison__spread=0.8, drift__pitch=2,
             filter__type='ladder', cutoff=4200, resonance=0.1, filter__drive=0.25, filter__keytrack=0.5,
             filter__env=1.0, fenv__attack=0.005, fenv__decay=0.6, fenv__sustain=0.5, fenv__release=0.4,
             hpf=180, amp__attack=0.004, amp__decay=0.5, amp__sustain=0.9, amp__release=0.4, amp__velocity=0.3,
             level=-3.3),
     [fx.eq(**{'peak1.freq': 320, 'peak1.gain': -2, 'peak3.freq': 3400, 'peak3.gain': -2, 'peak3.q': 1.2,
               'high.freq': 10000, 'high.gain': 1.5}),
      _shift()],
     sends={'hall': -10, 'echo': -12},
     notes="""
JP-8000 supersaw lead: 7-voice saw unison (detune 0.68) plus an octave-up saw layer, bright ladder filter - the big anthem lead,
then an H3000-style micro-pitch doubler (smooth, +-9 ct, mix 0.35): ~35 % wide (v1 20 %) around a strong, mono-safe centre.
Play: hooks and octave lines in A4-C6 (keep it above ~A4 so it clears the pads). Poly: chords/stabs work but sit ~4 dB louder (4-note chord -14 LUFS).
Use: chorus hook, final-chorus lift, doubled an octave below by synthwave/pulse_lead or synthwave/soft_lead at -6 dB. Over a bed of two
pad/string layers give the lead gain_db +2 (the bed should sit 0-5 dB under it).
Tweak: unison.detune 0.55-0.8 (0.68 classic; lower = cleaner, more focused), unison.spread 0.5-1, cutoff 2500-8000
(automate with 'exp' for builds), osc2.level 0-0.5 (octave sparkle), amp.release 0.2-0.8, mode='legato' + glide 0.03-0.08 for slides,
but_fx('microshift', mix=0-0.5) (width halo).
Insert EQ: -2 dB at 320 Hz and 3.4 kHz, +1.5 dB air shelf; if the report flags harsh presence lower cutoff or set .but_fx('eq', **{'peak3.gain': -4}).
Sends: hall -10, echo -12 (dotted-8th ping-pong: the repeats fill the gaps of the hook). Light kick sidechain (depth 4-6) if it fights the pads.
Level: -18.0 LUFS on the audition phrase at gain 0 (instrument level -3.3 dB).
v2 (lush pass: + microshift doubler, sends hall -12 -> -10, echo -15 -> -12).""")

_reg('synthwave/pulse_lead',
     inst.va(osc1__wave='square', osc1__pw=0.36, osc2__wave='square', osc2__pw=0.5, osc2__level=0.55, osc2__fine=7,
             filter__type='ladder', cutoff=2600, resonance=0.2, filter__drive=0.3, filter__keytrack=0.5,
             filter__env=1.4, fenv__attack=0.004, fenv__decay=0.35, fenv__sustain=0.45, fenv__release=0.3,
             amp__attack=0.004, amp__decay=0.4, amp__sustain=0.85, amp__release=0.25, amp__velocity=0.35,
             mods=[lfo('sine', hz=5.5, delay=0.3, fade=0.45, id='vib') >> ('pitch', 16)],
             hpf=120, polyphony=8, level=-4.8),
     [fx.chorus(mode='I', mix=0.25), _shift()],
     sends={'echo': -12, 'hall': -12},
     notes="""
Kavinsky-style pulse lead: 36 % pulse + detuned square through a warm ladder, delayed vibrato (5.5 Hz, 16 ct after 0.3 s), light Juno chorus
and a micro-pitch doubler (~24 % wide, v1 8 %; the centre stays focused).
Play: A4-A5 melodies with some held notes so the vibrato blooms; poly (8 voices) so harmonies in 3rds/6ths work.
Use: outrun / night-drive hooks, verse melodies, the octave double under synthwave/supersaw_lead.
Tweak: osc1.pw 0.2-0.5 (thinner = more nasal), vibrato depth mod.vib.amount 8-30 ct (.but(**{'mod.vib.amount': 25})), its
delay 0.15-0.6 s (.with_mods(vamod.lfo('sine', hz=5.5, delay=0.5, fade=0.45, id='vib') >> ('pitch', 16))), cutoff 1800-4500,
filter.env 0.5-2.5, mode='mono' + glide 0.03-0.06 for portamento runs.
Sends: echo -12, hall -12.
Level: -18.0 LUFS on the audition phrase at gain 0 (level -4.8); 4-note chords -13 LUFS.
v2 (lush pass: + microshift doubler, hall -15 -> -12).""")

_reg('synthwave/solo_lead',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.8, osc2__fine=6, sub__level=0.1,
             filter__type='ladder', cutoff=1500, resonance=0.25, filter__drive=0.4, filter__keytrack=0.6,
             filter__env=2.0, fenv__attack=0.01, fenv__decay=0.5, fenv__sustain=0.45, fenv__release=0.3,
             amp__attack=0.005, amp__decay=0.5, amp__sustain=0.9, amp__release=0.2, amp__velocity=0.3,
             mods=[lfo('sine', hz=5.2, delay=0.4, fade=0.5, id='vib') >> ('pitch', 20)],
             mode='legato', glide=0.07, hpf=110, level=-4.7),
     [fx.saturator(mode='tube', drive=4, tone=-1), fx.chorus(mode='I', mix=0.2), _shift()],
     sends={'echo': -12, 'hall': -12},
     notes="""
Keytar solo lead: two detuned saws + a touch of sub into a driven Moog ladder, mono legato with 70 ms glide, delayed vibrato, tube drive, Juno chorus
and a micro-pitch doubler (~21 % wide, v1 5 %).
Play: expressive monophonic solos in E4-E6. Overlapping notes glide without retriggering: make durations a little longer than
the step, e.g. clip.legato() (0.02-beat overlap), clip.legato(0.05) or clip.gate(1.08).
Separated notes re-articulate the envelopes. Monophonic: do not feed it chords.
Use: bridge/breakdown solos, final-chorus ad-libs, call-and-response with the hook.
Tweak: glide 0.03-0.15 s, cutoff 1000-3000 with filter.env 1-3 oct, resonance 0.1-0.5, filter.drive 0.2-0.7 (grit),
vibrato mod.vib.amount 10-35 ct (automate 'instrument.mod.vib.amount' for expressive swells), its delay 0.2-0.8 s
(.with_mods(vamod.lfo('sine', hz=5.2, delay=0.6, fade=0.5, id='vib') >> ('pitch', 20))); automate instrument.pitchbend
(-2..+2 st, 'smooth') for keytar bends.
Sends: echo -12, hall -12.
Level: -17.9 LUFS on an overlapping legato line, -18.4 on the audition phrase, at gain 0 (level -4.7).
v2 (lush pass: + microshift doubler, hall -14 -> -12).""")

_reg('synthwave/sync_lead',
     inst.va(osc1__wave='saw', osc1__level=0.0, osc2__wave='saw', osc2__level=1.0, osc2__sync='on', osc2__semi=7,
             unison=2, unison__detune=0.2, unison__spread=0.5,
             filter__type='ladder', cutoff=3500, resonance=0.1, filter__drive=0.3, filter__keytrack=0.4,
             filter__env=1.0, fenv__attack=0.001, fenv__decay=0.35, fenv__sustain=0.3, fenv__release=0.3,
             amp__attack=0.003, amp__decay=0.4, amp__sustain=0.85, amp__release=0.2, amp__velocity=0.3,
             mods=[env(a=0.001, d=0.35, r=0.3, id='sync') >> ('osc2.pitch', 1600),
                   lfo('sine', hz=5.5, delay=0.35, fade=0.4, id='vib') >> ('pitch', 12)],
             mode='mono', glide=0.02, hpf=150, level=-2.1),
     [fx.eq(**{'peak3.freq': 3200, 'peak3.gain': -2.5, 'peak3.q': 1.0}), _shift(style='classic')],
     sends={'echo': -12, 'hall': -12},
     notes="""
Prophet-style hard-sync lead: synced saw (osc2 +7 st over a silent master) swept down from +16 st by the envelope on every attack - the screaming
formant bite; mono, 20 ms glide; ~38 % wide (v1 22 %).
Play: A4-A5 riffs and hooks with rhythmic articulation (1/8-1/4 notes; each new attack gets the sweep). Mono: one line only.
Use: darksynth / outrun hooks, aggressive answers to the main hook, solos with more bite than synthwave/solo_lead.
Tweak: sweep size mod.sync.amount 800-3000 ct (.but(**{'mod.sync.amount': 2400})), sweep speed 0.15-0.6 s
(.with_mods(vamod.env(a=0.001, d=0.2, r=0.3, id='sync') >> ('osc2.pitch', 1600))), osc2.semi 0-19 (sustained timbre),
osc1.level 0-0.5 (adds the plain fundamental), cutoff 2500-6000, vibrato mod.vib.amount 0-25 ct, mode='poly' for sync chords/stabs.
Sends: echo -12, hall -12.
Level: -18.0 LUFS on the audition phrase at gain 0 (level -2.1). Dense spectrum, low crest (~7 dB): it reads loud for its level.
v2 (lush pass: + H910-style microshift doubler (classic: slightly grainy, it suits the aggressive bite), sends echo -13 -> -12, hall -15 -> -12).""")

_reg('synthwave/soft_lead',
     inst.va(osc1__wave='triangle', osc2__wave='sine', osc2__level=0.35, osc2__semi=12, noise__level=0.03,
             noise__color='pink',
             filter__type='lp12', cutoff=2600, resonance=0.05, filter__drive=0.1, filter__keytrack=0.5,
             filter__env=0.8, fenv__attack=0.03, fenv__decay=0.4, fenv__sustain=0.5, fenv__release=0.4,
             amp__attack=0.03, amp__decay=0.5, amp__sustain=0.9, amp__release=0.45, amp__velocity=0.3,
             mods=[lfo('sine', hz=5.0, delay=0.45, fade=0.6, id='vib') >> ('pitch', 14)],
             hpf=120, level=-5.4),
     [fx.chorus(mode='I', mix=0.35), _shift()],
     sends={'hall': -10, 'echo': -12},
     notes="""
Dreamwave soft lead: triangle + octave sine with a breath of pink noise through a gentle 12 dB filter, 30 ms attack, delayed vibrato, Juno chorus I
and a micro-pitch doubler - flute/ocarina-like, ~31 % wide (v1 16 %).
Play: A4-A6 slow melodies and long notes (80-100 BPM dreamwave/chillsynth); poly.
Use: soft toplines, intros/outros, a counter-melody or octave double under a brighter lead.
Tweak: noise.level 0-0.1 (breath), osc2.level 0-0.6 (octave shine), cutoff 1500-5000, amp.attack 0.01-0.15, vibrato
mod.vib.amount 8-25 ct.
Sends: hall -10, echo -12 (it wants space; bus/hall_lush + a shimmer send for dreamwave).
Level: -18.0 LUFS on the audition phrase at gain 0 (level -5.4); 4-note chords -13.5 LUFS.
v2 (lush pass: + microshift doubler, echo -14 -> -12).""")

_reg('synthwave/brass_lead',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.9, osc2__fine=9, unison=2, unison__detune=0.25,
             unison__spread=0.5,
             filter__type='ladder', cutoff=800, resonance=0.12, filter__drive=0.35, filter__keytrack=0.55,
             filter__env=2.6, fenv__attack=0.06, fenv__decay=0.55, fenv__sustain=0.55, fenv__release=0.3,
             amp__attack=0.025, amp__decay=0.6, amp__sustain=0.85, amp__release=0.25, amp__velocity=0.4,
             mods=[lfo('sine', hz=5.3, delay=0.5, fade=0.5, id='vib') >> ('pitch', 10)],
             hpf=120, polyphony=8, level=-3.0),
     [fx.chorus(mode='I', mix=0.3), fx.saturator(mode='tape', drive=3), _shift(detune=8, mix=0.3)],
     sends={'hall': -10, 'plate': -14},
     notes="""
Bold OB-X / Jupiter synth brass lead: detuned saws (2-voice unison) with a slow-attack filter envelope 'blat' (60 ms), chorus, tape drive and a
micro-pitch doubler (~43 % wide, v1 31 %: a brass section rather than one player).
Play: lead lines and fanfares in C4-C6, and stabs/chords (poly 8).
Use: chorus hooks, brass stabs on off-beats, unison riffs with the bass an octave or two below.
Tweak: fenv.attack 0.02-0.15 (blat speed), filter.env 1.5-4 oct, cutoff 500-1500, osc2.fine 5-15 ct, amp.release 0.15-0.5,
vibrato mod.vib.amount 0-20 ct.
Sends: hall -10, plate -14.
Level: -17.9 LUFS on the phrase at gain 0 (level -3.0); 4-note chords land ~-13.7 LUFS, so give chord/stab tracks gain_db -4.
Note: `audition` guesses 'chord' from the name; use --notes phrase to hear it as a lead.
v2 (lush pass: + microshift doubler, hall -12 -> -10, plate -16 -> -14).""")

_reg('synthwave/dx_lead',
     inst.dx7('LEAD BRASS', detune=7, width=0.5, brightness=-0.1, modwheel=0.1, level=5.0),
     [fx.compressor(threshold=-12, ratio=4, attack=0.1, release=50, knee=4), fx.chorus(mode='I', mix=0.15),
      fx.eq(**{'hp.freq': 150}), _shift()],
     sends={'echo': -12, 'hall': -12},
     notes="""
DX7 lead: ROM 'LEAD BRASS' doubled (+/-3.5 ct, width 0.5) with a little mod-wheel vibrato, a peak compressor on its spiky FM attack, light chorus,
150 Hz high-pass and a micro-pitch doubler - a bright, reedy lead that cuts, ~33 % wide (v1 17 %).
Play: A4-A5 hooks; strong on sustained notes and 1/8 lines (each note swells in with a brassy FM bite). Poly: harmonies OK.
Use: 80s-pop hooks, a digital contrast to the analog leads, doubling a VA lead an octave up at -6 dB.
Tweak: modwheel 0-0.3 (vibrato), brightness -0.5..0.3, detune 0-12 ct, velsens 0.3-1. Other DX lead voices via .but(voice=...):
'SYN-LEAD 5' (brighter, saw-like), 'rom2b:SYN-LEAD 3' (percussive attack, mellow sustain), 'rom1a:SYN-LEAD 1' (hollow, sounds
an octave up) - DX autolevel keeps them near the same loudness, but re-check the report.
Sends: echo -12, hall -12.
Level: -18.0 LUFS on the audition phrase at gain 0 (level +5.0); 4-note chords about the same (-18.0) thanks to the compressor.
v2 (lush pass: + microshift doubler, sends echo -13 -> -12, hall -14 -> -12).""")

_reg('synthwave/stranger_arp',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.7, osc2__fine=8,
             filter__type='ladder', cutoff=650, resonance=0.55, filter__drive=0.3, filter__keytrack=0.45,
             filter__env=2.8, fenv__attack=0.002, fenv__decay=0.28, fenv__sustain=0.15, fenv__release=0.25,
             amp__attack=0.002, amp__decay=0.5, amp__sustain=0.4, amp__release=0.22, amp__velocity=0.3,
             hpf=90, level=0.5),
     [fx.chorus(mode='I', mix=0.4),
      fx.delay(mode='pingpong', balanced='off', time=0.75, feedback=0.35, highcut=3000, lowcut=250, width=0.9, mix=0.22)],
     sends={'hall': -14},
     notes="""
S U R V I V E / Stranger Things arpeggio synth: two detuned free-running saws through a resonant (0.55) ladder with a short filter envelope,
Juno chorus I and a built-in dotted-8th ping-pong delay (mix 0.22): a mono analog core with echoes bouncing left/right (~20 % wide).
Play: 1/8 or 1/16 arpeggios of maj7/min7 chord tones in A2-A4 (e.g. C E G B C B G E), 70-110 BPM.
Use: sci-fi / soundtrack intros and verses. Signature move: automate instrument.cutoff slowly, e.g. exp_ramp(intro.start, verse.start, 400, 2500),
so the arp opens over 8-16 bars; pair it with a pulsing bass and a slow pad.
Tweak: cutoff 300-2500, resonance 0.3-0.75, filter.env 1.5-4 oct, fenv.decay 0.15-0.5, amp.sustain 0.2-0.6; the delay via
.but_fx('delay', mix=0-0.35, time=0.5 or 0.75, feedback=0.2-0.5).
Sends: hall -14 (up to -8 for a dreamier wash).
Level: -18.0 LUFS on the audition arp (--notes arp) at gain 0 (level +0.5); 16th sequences in A2-A3 about -19.
v2 (lush pass: + Juno chorus I, the built-in delay is a classic ping-pong again (the balanced one bounced almost nothing to the sides),
hall -16 -> -14).""")

# ---------------------------------------------------------------------------------- arps / plucks

_reg('synthwave/arp_pluck',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.6, osc2__fine=7,
             filter__type='ladder', cutoff=520, resonance=0.3, filter__drive=0.25, filter__keytrack=0.5,
             filter__env=3.4, fenv__attack=0.001, fenv__decay=0.14, fenv__sustain=0.0, fenv__release=0.12,
             amp__attack=0.001, amp__decay=0.3, amp__sustain=0.0, amp__release=0.12, amp__velocity=0.4,
             osc__retrig='on', hpf=140, level=4.8),
     [fx.eq(**{'peak1.freq': 400, 'peak1.gain': -2, 'peak1.q': 0.7}), fx.chorus(mode='II', mix=0.55), fx.dimension(mode=2)],
     sends={'echo': -10, 'hall': -14},
     notes="""
Plucky 16th-arp saw: two detuned saws, retriggered oscillators (identical punchy attacks), ladder with a snappy filter envelope (decay 0.14 s,
sustain 0), a -2 dB dip at 400 Hz (it sits above the pads), Juno chorus II and a Dimension-D side layer: the arp spreads across the stereo
field (~74 % wide, v1 5 %) while its mono sum stays clean.
Play: arp(...) 1/16 (or 1/8) patterns in A3-A5 (the default arp register 57-76 is ideal); velocity accents open the filter.
Use: the classic outrun 16th arp under pads, rolling sequencer lines, verse/chorus arps (sidechain it with the pads); pan it +0.2..0.35 against
the e-piano / keys on the other side.
Tweak: fenv.decay 0.08-0.3 (pluck length), filter.env 2-5 oct, cutoff 300-1200 (automate for builds), resonance 0.1-0.5,
amp.decay 0.15-0.5, osc2.fine 0-15 ct, but_fx('dimension', mix=0) for a narrower arp.
Sends: echo -10 (the dotted-8th ping-pong is half the sound), hall -14. Sharp transients: peaks ~15 dB above loudness.
Level: -18.0 LUFS on the audition arp (--notes arp) at gain 0 (level +4.8).
v2 (lush pass: chorus I 0.2 -> II 0.55, + dimension mode 2, -2 dB at 400 Hz, hall -16 -> -14).""")

_reg('synthwave/arp_glass',
     inst.dx7('CELESTE', detune=7, width=0.6, level=0.2),
     [fx.chorus(mode='II', mix=0.4), fx.dimension(mode=1)],
     sends={'echo': -10, 'hall': -14},
     notes="""
Glassy FM pluck: DX7 'CELESTE' (sounds an octave above the written note) doubled, chorused and dimension-widened for stereo shimmer
(~58 % wide, v1 25 %) - bell-like inharmonic attack, clean sine-ish decay.
Play: arps/ostinatos written in A3-A5 (sounds A4-A6), 1/8-1/16.
Use: sparkle layer over synthwave/arp_pluck or pads, intros, dreamwave counter-lines, music-box moments.
Tweak: detune 0-12 ct, width 0-1, brightness -0.5..0.5, velsens 0.5 (evens out arp dynamics). Alternatives via .but(voice=...):
'GLOKENSPL' (higher, harder), 'E.PIANO 1' (tine), 'KOTO' (plucky, harmonic).
Sends: echo -10, hall -14.
Level: -18.0 LUFS on the audition arp (--notes arp) at gain 0 (level +0.2).
v2 (lush pass: + Juno chorus II 0.4 and dimension mode 1, echo -11 -> -10).""")

_reg('synthwave/seq_pulse',
     inst.va(osc1__wave='square', osc1__pw=0.28, osc2__wave='square', osc2__pw=0.5, osc2__level=0.4, osc2__semi=-12,
             filter__type='ladder', cutoff=800, resonance=0.3, filter__drive=0.3, filter__keytrack=0.4,
             filter__env=2.4, fenv__attack=0.001, fenv__decay=0.16, fenv__sustain=0.1, fenv__release=0.1,
             amp__attack=0.001, amp__decay=0.22, amp__sustain=0.3, amp__release=0.08, amp__velocity=0.4,
             mods=[lfo('triangle', hz=0.35, mode='global', id='pwm') >> ('osc1.pw', 0.1575),
                   lfo('triangle', hz=0.35, mode='global', id='pwm2') >> ('osc2.pw', 0.1575)],
             osc__retrig='on', hpf=100, level=2.5),
     [fx.chorus(mode='II', mix=0.45), fx.dimension(mode=1)],
     sends={'echo': -11},
     notes="""
Sequenced pulse: narrow PWM pulse (28 %, slow 0.35 Hz LFO) + square an octave below through a ladder with a short envelope - the Tangerine Dream /
Carpenter sequencer throb, now ~43 % wide (v1 mono).
Play: 1/16 or 1/8 repeating sequences in A2-A4 (root-octave-fifth cells), retriggered for even attacks. Keep it above the bass octave.
Use: driving verse sequences under pads, darksynth ostinatos, a pulsing counterpart to the bass.
Tweak: osc1.pw 0.1-0.5, PWM depth mod.pwm.amount 0-0.25 (osc2: mod.pwm2.amount), cutoff 400-2000 (automate), filter.env 1-4 oct,
fenv.decay 0.08-0.3, amp.sustain 0-0.5, osc2.level 0-0.6 (sub weight), but_fx('chorus', mix=0) + but_fx('dimension', mix=0) for the dry mono throb.
Sends: echo -11.
Level: -18.0 LUFS on the audition arp (--notes arp) at gain 0 (level +2.5).
v2 (lush pass: + Juno chorus II 0.45 and dimension mode 1; the sub octave stays centred below 150 Hz).""")

# ------------------------------------------------------------------------------------------- FX

_reg('synthwave/noise_riser',
     inst.va(osc1__level=0.0, noise__level=1.0, noise__color='white', noise__stereo=0.7,
             filter__type='lp12', cutoff=300, resonance=0.45, filter__drive=0.0, filter__keytrack=0.0,
             filter__env=0.0, filter__velocity=0.0,
             amp__attack=1.5, amp__decay=1.0, amp__sustain=1.0, amp__release=0.8, amp__velocity=0.0, hpf=30,
             level=-5.7),
     [fx.chorus(mode='custom', rate=0.3, depth=4, delay=12, voices=2, spread=1, mix=0.5),
      fx.reverb(type='hall', mix=0.25, decay=3.0, lowcut=200)],
     notes="""
White-noise riser: resonant 12 dB low-pass on stereo noise with a 1.5 s fade-in, chorus for width and its own hall - built for ONE long note plus automation.
Play: one note (pitch irrelevant) lasting the whole build (4-16 bars), ending on the drop.
Automate (required - without it this is static dark noise):
  instrument.cutoff  riser(drop, length=L, lo=300, hi=12000)   (the sweep; 'exp' is the default curve)
  instrument.hpf     riser(drop, length=L, lo=20, hi=1500)     (thins it out as it rises)
  optional: instrument.resonance 0.3 -> 0.7 (more whistle), gainDb swell -12 -> 0, a flutter
  .with_mods(vamod.lfo('square', rate='1/16', mode='global', unipolar=True, id='flutter') >> ('amp', -12)) with
  'instrument.mod.flutter.amount' automated 0 -> -12, or osc1.level 0.2 + instrument.pitchbend 0 -> 12 (tonal saw rise).
Example:  r = s.track('riser', 'synthwave/noise_riser', gain_db=-3); r.note('A3', chorus.start - 16, 16)
          r.automate('instrument.cutoff', riser(chorus, length=16, lo=300, hi=12000))
          r.automate('instrument.hpf', riser(chorus, length=16, lo=20, hi=1500))
Tweak: noise.stereo 0 (centred, v1) .. 1 (fully decorrelated).
Level: -18.5 LUFS integrated over an automated 8-bar build at gain 0 (level -5.7); short-term peak ~-15 LUFS at the top.
v2 (lush pass: noise.stereo 0.7 - independent left/right noise: the riser fills the whole stereo field, ~63 % wide instead of 33 %).""")

_reg('synthwave/downlifter',
     inst.va(osc1__wave='saw', osc1__level=0.3, unison=3, unison__detune=0.3, unison__spread=0.8,
             noise__level=1.0, noise__color='white', noise__stereo=0.8,
             filter__type='lp12', cutoff=120, resonance=0.35, filter__drive=0.0, filter__keytrack=0.0,
             filter__env=7.0, fenv__attack=0.002, fenv__decay=6.0, fenv__sustain=0.0, fenv__release=3.0,
             mods=[env(a=0.002, d=6.0, r=3.0, id='drop') >> ('pitch', 2400)], filter__velocity=0.0,
             amp__attack=0.03, amp__decay=5.0, amp__sustain=0.0, amp__release=2.5, amp__velocity=0.0, hpf=40,
             level=0.4),
     [fx.chorus(mode='custom', rate=0.3, depth=4, delay=12, voices=2, spread=1, mix=0.5),
      fx.reverb(type='hall', mix=0.25, decay=3.0, lowcut=250)],
     notes="""
Downlifter / fall: stereo white noise + detuned saws swept down together (filter env 7 oct over ~6 s, pitch falling 2 octaves onto the note), chorus + hall -
a self-contained whoosh down, no automation needed.
Play: one note on the downbeat where the energy drops (after a chorus, into a breakdown, after an impact), pitch ~A3 (the saw layer
lands on the played note), duration 1-2 bars (the sound decays in ~4 s either way).
Tweak: fenv.decay 2-8 s (filter sweep length; the pitch fall: .with_mods(vamod.env(a=0.002, d=4, r=3, id='drop') >> ('pitch', 2400))),
pitch fall mod.drop.amount 0-2400 ct, osc1.level 0-0.5 (tonal fall), noise.level 0.5-1, noise.stereo 0-1, amp.decay 2-8 s, hpf 40-400 to keep it
off the bass.
Level: -17.8 LUFS with one hit every 2 bars at gain 0 (level +0.4); the first 50 ms peak ~-4 dBFS.
v2 (lush pass: noise.stereo 0.8 - the whoosh spreads over the whole stereo field, ~70 % wide instead of 40 %).""")

_reg('synthwave/impact',
     inst.va(osc1__wave='sine', osc1__level=0.4, noise__level=1.0, noise__color='white',
             filter__type='lp12', cutoff=70, resonance=0.0, filter__drive=0.3, filter__keytrack=0.0,
             filter__env=8.0, fenv__attack=0.001, fenv__decay=0.8, fenv__sustain=0.0, fenv__release=1.0,
             mods=[env(a=0.001, d=0.8, r=1.0, id='drop') >> ('pitch', 2400)], filter__velocity=0.0,
             amp__attack=0.001, amp__decay=2.2, amp__sustain=0.0, amp__release=1.5, amp__velocity=0.3,
             osc__retrig='on', hpf=28, level=10.5),
     [fx.saturator(mode='tape', drive=6),
      fx.reverb(type='hall', mix=0.4, decay=4.0, lowcut=700, lowmult=0.4, highcut=10000, predelay=10)],
     notes="""
Impact / boom: sine dropping two octaves onto the played note (sub boom) + a loud white-noise crack that sweeps down through a 12 dB
low-pass into a bright 4 s hall whoosh, tape saturation. The hall is high-passed at 700 Hz with a short bass decay, so the sub stays dry
and no low-mid reverb mud rings under the next bars.
Play: one note on a section downbeat at the song's root in octave 1 (A1, E1, F#1 ...); layer it with the drum crash.
Use: chorus/drop starts, big transitions, trailer-style hits in intros. Clear or duck the bass for a beat under it (its tail is a
tuned ~2 s sub note).
Tweak: pitch drop mod.drop.amount 1200-2400 ct, fenv.decay 0.4-1.2 s (crack length; with the drop speed:
.with_mods(vamod.env(a=0.001, d=0.5, r=1.0, id='drop') >> ('pitch', 2400))), amp.decay 1-4 s, osc1.level 0.25-0.7
(boom vs crack balance), noise.level 0-1, .but_fx('reverb', mix=0.2-0.6, decay=2-6).
Level: -18.3 LUFS with one hit per bar at A1, velocity 120, gain 0 (level +10.5); the crack peaks ~-4 dBFS.
v2 (review): v1 was 30 dB of boom over an inaudible crack and its hall rang at 150-250 Hz; now boom + crack + bright tail.
The sub boom stays mono (lush pass: unchanged).""")

_reg('synthwave/laser',
     inst.va(osc1__wave='square', osc2__wave='saw', osc2__level=0.8, osc2__sync='on', osc2__semi=12,
             mods=[env(a=0.001, d=0.22, r=0.2, id='zap') >> ('pitch', 2400),
                   env(a=0.001, d=0.22, r=0.2, id='zap2') >> ('osc2.pitch', 2400)],
             filter__type='bp12', cutoff=1800, resonance=0.55, filter__drive=0.2, filter__keytrack=0.6,
             filter__env=1.6, fenv__attack=0.001, fenv__decay=0.22, fenv__sustain=0.0, fenv__release=0.2,
             amp__attack=0.001, amp__decay=0.35, amp__sustain=0.0, amp__release=0.2, amp__velocity=0.3,
             osc__retrig='on', hpf=150, level=3.0),
     [fx.eq(**{'high.freq': 6000, 'high.gain': -3, 'lp.freq': 11000})],
     sends={'echo': -10},
     notes="""
Sci-fi laser zap: square + hard-synced saw, both diving two octaves in ~0.2 s through a resonant band-pass - 'pew'.
Play: short notes (1/16-1/8) in C5-A5 (higher = thinner zap), single shots or quick repeats.
Use: ear candy in fills and gaps, intro sci-fi atmosphere, answering a drum fill.
Tweak: dive mod.zap.amount (all oscillators) and mod.zap2.amount (osc2 on top, the sync sweep) 1200-2400 ct, the dive speed
0.08-0.4 s (short = pew, long = descending laser: .with_mods(vamod.env(a=0.001, d=0.4, r=0.2, id='zap') >> ('pitch', 2400),
vamod.env(a=0.001, d=0.4, r=0.2, id='zap2') >> ('osc2.pitch', 2400)); fenv.decay shapes only the filter), resonance 0.3-0.8,
cutoff 1000-4000. Scatter the shots across the stereo field: .with_mods(vamod.random() >> ('pan', 0.5, 'spread')).
Sends: echo -10 (the dotted-8th echoes make the space: the ping-pong bounces every zap left/right).
Level: -18.1 LUFS on scattered 1/8 shots at gain 0 (level +3.0); very transient (peaks ~14 dB above loudness). Insert EQ: -3 dB shelf
at 6 kHz + 11 kHz low-pass keeps the sync fizz from getting piercing.""")

# ------------------------------------------------------------------------------------------ buses

_reg('bus/echo',
     None,
     [fx.delay(mode='pingpong', balanced='off', time=0.75, feedback=0.4, highcut=5500, lowcut=250, wow=0.12,
               flutter=0.05, width=1.0, duck=0.1, mix=1.0),
      fx.eq({'output': 4.0})],
     notes="""
Dotted-8th ping-pong delay return (100 % wet): first repeat left, then right, left, ...; tape-ish wow and a little flutter, each repeat darker
and thinner (5.5 kHz / 250 Hz in the loop), feedback 0.4. The return is ~95 % wide (correlation ~0).
Use: song.echo() picks this patch up automatically; params given to song.echo(...) go to the delay: time (0.75 = dotted 8th,
0.5 = 8th, 0.3333 = 8th triplet, 1 = quarter), feedback 0.2-0.6, highcut 2500-8000, duck 0-0.6 (higher = echoes only in the gaps,
great when only a lead feeds it), start='right' to flip the first bounce.
Calibration: with the library's default sends (leads -12, arps -10) the echo sits about 18-21 LU under a full mix and is clearly heard in
the gaps of the lead (songs/_demo_lush: -18.9 LU while it sounds; the report calls an echo inaudible below -24 LU).
Sends: leads -10..-14 dB, arps/plucks -8..-12, lasers -10.
Note: a classic ping-pong's first repeat is hard left and each repeat is quieter, so this return alone leans left (~8 dB at feedback 0.4);
at normal send levels the whole mix leans well under 0.5 dB. Keep the delay width at 1.0: the repeats already sit hard left / right, and
song.echo(width=1.2) pushes the return out of phase (correlation about -0.25: the report's over_wide).
Tape flavour with more wobble and saturation: bus/tape_echo.
v2 (lush pass: a real ping-pong again (the engine's balanced default put the loud first repeat in the centre: v1 read 5 % wide), brighter
repeats (5.5 kHz), less ducking (0.2 -> 0.1: a busy arp on the same bus kept the echoes ducked all the time), +4 dB output calibration).""")

_reg('bus/tape_echo',
     None,
     [fx.delay(mode='pingpong', balanced='off', start='right', time=0.75, feedback=0.48, highcut=4000, lowcut=300,
               wow=0.3, flutter=0.25, width=1.0, duck=0.25, mix=1.0),
      fx.tape(speed='7.5', drive=6, bias=0.3, bump=1.5, wow=0.1, flutter=0.1, hiss=0.05),
      fx.eq({'output': 6.0})],
     notes="""
Space-Echo style dotted-8th ping-pong through tape: first repeat RIGHT (so it answers bus/echo when both are used), then
left, right, ...; feedback 0.48 (longer trails), repeats darken fast (4 kHz / 300 Hz in the loop) and drift in pitch (wow 0.3, flutter
0.25 - every repeat wobbles a bit more, like a worn tape loop), then a 7.5 ips tape stage (drive 6: warm saturation, +1.5 dB head bump,
very faint hiss), ducked while the input is loud (0.25: the echoes bloom in the gaps), +6 dB output calibration (about as loud as bus/echo
at the same send: a lead at -12 gets repeats ~13 dB under its dry level). Return ~95 % wide.
Use: te = s.bus('tape_echo', 'bus/tape_echo'); sends={te: -12} on a lead, e-piano or bell line; throws: automate 'send.tape_echo' up to
-4 on the last note of a phrase. For dreamwave / lo-fi / soundtrack moods where bus/echo is too clean.
Tweak: but_fx('delay', time=0.5-1, feedback=0.3-0.7, wow=0-0.6), but_fx('tape', drive=0-12).
Sends: -10..-16 dB.
v1 (lush pass).""")

_reg('bus/echo_quarter',
     None,
     [fx.delay(mode='stereo', time=1.0, offset=2, feedback=0.3, highcut=5000, lowcut=200, wow=0.08, mix=1.0)],
     notes="""
Quarter-note stereo echo return (100 % wet): the right side 2 % later for width (balanced, correlation ~0), filtered repeats (200 Hz-5 kHz), feedback 0.3, slight tape wow.
Use: q = song.bus('echo4', 'bus/echo_quarter'); track sends={q: -14}. For pads, keys, E.piano and slow leads where the dotted-8th
bus/echo is too busy. Tweak via .but_fx('delay', time=0.5-2, feedback=0.2-0.5, highcut=3000-8000).
Sends: -12..-18 dB. Output is about -2 LU under the dry signal at a 0 dB send.""")

_reg('bus/wide',
     None,
     [fx.microshift(style='wide', detune=9, delay=12, focus=250, mix=1.0),
      fx.dimension(mode=1),
      fx.eq(**{'hp.freq': 200})],
     notes="""
Width / doubling return (100 % wet): the send is double-tracked by a breathing micro-pitch shifter (style wide: left +9 ct, right -9 ct,
~25-30 ms later, slowly modulated) and spread by a Dimension-D side layer, everything below 200-250 Hz removed - a wide double around a
part whose dry signal stays centred, without phasing (return correlation ~0, ~110 % wide).
Use: w = song.bus('wide', 'bus/wide'); sends={w: -8} on a lead, pluck, keys or a mono GM part to make it bigger while the dry stays centred.
Sends: -6..-12 dB (at 0 dB the return is about as loud as the dry signal). The report lists it as return:width.
Tweak: .but_fx('microshift', detune=5-20, delay=0-30), .but_fx('dimension', mode=2) (wider).
v2 (lush pass: an H3000-style micro-pitch double + Dimension instead of the v1 single chorus voice).""")
