"""Vocoder sound library: the carrier synths with their vocoder, ready to be keyed by a voice.

Each patch is a CARRIER (the notes the robot sings) with the engine's 'vocoder' as its first effect. The vocoder
needs a MODULATOR - the words - from a speech track; key it with agentsound.speech:

    from agentsound import speech
    vox = speech.words(['neon lights', 'city nights'], voice='zira')      # Windows TTS, cached next to the song
    voice = s.track('voice', vox.instrument())
    voice.play(vox.clip({0: 'neon lights', 2: 'city nights'}, length=4), verse)
    choir = s.track('choir', 'synthwave/vocoder_choir')
    choir.play(s.prog('i VI III VII').block(), verse)                      # chords = a robot choir
    speech.vocode(choir, voice)                                           # keys the vocoder, mutes the voice

Without the key the engine rejects the song ("needs a sidechain"). The carriers are bright on purpose (the vocoder
can only shape what the carrier has). Level calibration: at gain 0 the vocoded track lands at about -18 LUFS on its
audition (a spoken line at -18 dBFS - what speech.py writes - over held notes); the vocoder keeps roughly the
carrier's loudness while the voice talks and is silent in its pauses. Audition: `python -m agentsound audition
synthwave/vocoder_choir` (says a line with a Windows voice, or a synthetic vowel modulator elsewhere).

Version: see VERSION (bump it when a sound changes audibly).
"""

from __future__ import annotations

from ..vamod import lfo
from . import Patch, fx, inst, register

VERSION = 2


def _reg(name, instrument, fx_, sends, notes, audition):
    register(Patch(name, instrument=instrument, fx=list(fx_), gain_db=0.0, pan=0.0, sends=sends, notes=notes.strip(),
                   audition=audition))


_reg('synthwave/vocoder_choir',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.8, osc2__fine=8, unison=5, unison__detune=0.35,
             unison__spread=0.8, drift__pitch=3, cutoff=9000, resonance=0.05, filter__env=0, filter__keytrack=0,
             filter__drive=0.15, amp__attack=0.03, amp__decay=0.5, amp__sustain=1.0, amp__release=0.6, amp__velocity=0.2,
             hpf=110, polyphony=16, level=-8.7),
     [fx.vocoder(bands=20, release=30, shift=-2, emphasis=5, flatten=0.7, unvoiced=0.4, sibilance=0.35, width=0.8),
      fx.chorus(mode='I', mix=0.35),
      fx.eq(**{'hp.freq': 120, 'peak1.freq': 300, 'peak1.gain': -2, 'high.freq': 9000, 'high.gain': 2})],
     {'hall': -8},
     """
Robot choir (Kraftwerk / Daft Punk / The Midnight): a bright 5-voice unison saw pad as the carrier of a 20-band
classic vocoder (formants 2 st lower = a bigger, choir-like robot, bands spread across the stereo field), Juno chorus.
Play: chords (3-5 notes, C3-C5) that last as long as the words; the voice decides when it speaks, the chords which
notes it sings. Key it: speech.vocode(track, voice_track). Held chords + a sung word = the robot 'aaah' choir.
Tweak (fx.0 = the vocoder): shift -6..+3, release 20-80 ms (smoother), bands 12 (lo-fi) .. 32, width 0-1,
unvoiced / sibilance (crisper 's' and 't'), mode='lpc' (talkbox-like, most intelligible); automate
'fx.0.hold' to 1 to freeze a vowel. Sends: hall -8.
Level: -18 LUFS vocoded on the audition (spoken line over held chords) at gain 0 (level -8.7); the dry pad -16.""",
     {'notes': 'chord'})

_reg('synthwave/vocoder_lead',
     inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.9, osc2__fine=6, unison=3, unison__detune=0.25,
             unison__spread=0.4, cutoff=10000, resonance=0.0, filter__env=0, filter__keytrack=0, filter__drive=0.2,
             amp__attack=0.004, amp__decay=0.4, amp__sustain=1.0, amp__release=0.2, amp__velocity=0.2,
             mode='legato', glide=0.035, hpf=150, level=-7.0),
     [fx.vocoder(bands=24, release=15, emphasis=5, flatten=0.7, unvoiced=0.5, sibilance=0.4, width=0.35),
      fx.eq(**{'hp.freq': 150, 'peak2.freq': 2500, 'peak2.gain': 1.5, 'peak2.q': 0.8})],
     {'echo': -14, 'hall': -12},
     """
Robot lead singer: a bright, slightly detuned 3-voice saw (mono legato, 35 ms glide) through a 24-band classic
vocoder - the voice speaks, the lead line sings. Play: one note per syllable (A3-A4 sounds most vocal, an octave
up for a small, bright robot); overlapping notes glide like a talkbox player's portamento.
Key it: speech.vocode(track, voice_track). Place the words (speech.words(...).clip) on the melody's rhythm.
Tweak (fx.0 = the vocoder): shift -4 (deeper robot) .. +4 (small), release 10-30 ms, bands 16-32,
mode='lpc' (talkbox); glide 0.02-0.08. Sends: echo -14, hall -12.
Level: -18 LUFS vocoded on the audition (spoken line over one held A3) at gain 0 (level -7.0); dry -18.7.""",
     {'notes': 'riser', 'pitch': 'A3'})

_reg('synthwave/talkbox',
     inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.55, osc2__pw=0.35, osc2__semi=0, osc2__fine=4,
             cutoff=12000, resonance=0.0, filter__env=0, filter__keytrack=0, filter__drive=0.45, amp__attack=0.004,
             amp__decay=0.3, amp__sustain=1.0, amp__release=0.12, amp__velocity=0.25, mode='legato', glide=0.05,
             mods=[lfo('sine', hz=5.2, delay=0.35, fade=0.4, id='vib') >> ('pitch', 12)],
             hpf=90, level=-8.8),
     [fx.vocoder(mode='lpc', order=24, release=12, emphasis=4, flatten=0.6, unvoiced=0.45, sibilance=0.3),
      fx.saturator(mode='tube', drive=4, tone=-1),
      fx.dimension(mode=1),
      fx.eq(**{'hp.freq': 100, 'peak1.freq': 350, 'peak1.gain': -2, 'peak3.freq': 3000, 'peak3.gain': 1.5})],
     {'echo': -15, 'hall': -14},
     """
Talkbox (Zapp / Roger Troutman, Daft Punk's 'Around the World' feel, modern synthwave hooks): a buzzy saw + pulse
through the LPC vocoder - the voice's vocal-tract resonances filter the synth like a mouth - smooth and the most
intelligible robot; mono legato with 50 ms glide and delayed vibrato, a touch of tube drive,
Dimension-D width (a pure side signal above 150 Hz: the mono sum stays the dry, clearest talkbox).
Play: melodies one note per syllable (G3-G4 is the natural talkbox range), slides between notes.
Key it: speech.vocode(track, voice_track). Tweak (fx.0 = the vocoder): shift -3..+3 (mouth size), release 8-25 ms,
order 16 (softer) .. 32 (sharper vowels), flatten 0.4-1, unvoiced 0.3-0.7. Sends: echo -15, hall -14.
Level: -18 LUFS vocoded on the audition (spoken line over one held A3) at gain 0 (level -8.8); dry -20.3.""",
     {'notes': 'riser', 'pitch': 'A3'})
