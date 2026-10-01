"""Sampled vintage keyboards: the Fairlight CMI's 8-bit factory voices (ORCH5 orchestra hit, choirs, strings, brass)
and pipe organs from GrandOrgue sample sets (inst.organ: real attack, loop and release of every pipe).

  fairlight: sampled/fairlight_orch5 sampled/fairlight_choir sampled/fairlight_aahs sampled/fairlight_strings
             sampled/fairlight_brass
  organ:     sampled/church_organ sampled/church_organ_full sampled/church_organ_flutes sampled/organ_pedal

The Fairlight CMI Series II played one sample per voice stretched over the keyboard; its factory library is tuned to
A (these patches put the recorded pitch on A3 = 57, like the CMI). The samples are 8-bit / 14 kHz: the grit, the
aliasing shimmer and the short loop are the sound of 1983 (Yes, Peter Gabriel, Kate Bush, Art of Noise). Sustained
voices loop the middle of the sample back and forth (ping-pong), so hold notes as long as you like.

The organs use the Burea Church set (Lars Palo, Nils Hammarberg organ 1967, recorded in the church: the release
samples carry the room, so keep the hall send low). Stops layer like a registration; expression is the swell pedal.
A pedal line goes on its own track (sampled/organ_pedal, keys C2-F4). The set is recorded with a spaced microphone
pair (the phase between the channels changes from pipe to pipe): the manual patches play it as recorded, the pedal
uses one microphone ('left': mono, solid bass).

Level calibration: every patch at gain_db 0 lands at about -18 LUFS (track node, dry) playing its audition material,
measured value in the notes. Licences: the Fairlight library is an anonymous archive.org upload ('Unclear-free-
download': fine for sketches, check before releasing); Burea Church organ CC-BY-SA 2.5: credit Lars Palo. Version:
see VERSION.
"""

from . import Patch, fx, inst, register

VERSION = 2

_CMI = 'samples/fairlight-cmi-library-1-3'
_BUREA = 'samples/lars-palo-burea-church'


def _cmi(file: str, level: float, loop: tuple | None, **kw):
    """One Fairlight voice over the whole keyboard (recorded pitch on A3); sustained voices ping-pong loop a steady
    stretch of the 16384-frame sample (frames `loop`, chosen where the level holds within a few dB)."""
    loop = dict(loop='pingpong', loop_start=loop[0], loop_end=loop[1]) if loop else dict(loop='none')
    return inst.multisample(f'{_CMI}/{file}', root='A3', lazy=True, level=level, **loop, **kw)


def _hp(freq: float):
    return fx.eq({'hp.freq': freq, 'hp.slope': 24})


# --------------------------------------------------------------------------------------------- Fairlight CMI

register(Patch(
    'sampled/fairlight_orch5',
    instrument=_cmi('16 STRINGS3/ORCH5.wav', level=-10.8, loop=None, release=0.3),
    fx=[_hp(60), fx.dimension(mode=2)],
    sends={'hall': -16},
    notes='v1. Fairlight CMI ORCH5: THE orchestra hit (a Stravinsky Firebird chord, 8-bit) of Yes "Owner of a Lonely '
          'Heart", Afrika Bambaataa, 80s pop and electro. Its pitch is A: play stabs on chord roots (A3 = the original, '
          'an octave down for weight, up for a brighter crack); short notes, it rings its own tail. License unclear '
          '(anonymous archive.org upload of the factory library). Sends: hall -16. Measured -18.0 LUFS (audition stabs).',
    audition={'notes': 'stab'}))

register(Patch(
    'sampled/fairlight_choir',
    instrument=_cmi('22 HUMANS1/CHOIR1.wav', level=-6.4, loop=(3600, 14000), attack=0.08, release=0.9),
    fx=[_hp(90), fx.chorus(mode='II', mix=0.35)],
    sends={'hall': -10},
    notes='v1. Fairlight CMI CHOIR1: the breathy 8-bit "aah" choir of 80s ballads and synth-pop (Kate Bush, Peter '
          'Gabriel, Tears for Fears) - a sampled choir that sounds like 1984, not like a modern library. Pads and held '
          'chords C3-C5; the looped middle sustains any length. License unclear (anonymous archive.org upload). Sends: '
          'hall -10. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/fairlight_aahs',
    instrument=_cmi('22 HUMANS1/AAHHL1.wav', level=-11.5, loop=(1500, 14500), attack=0.06, release=0.8),
    fx=[_hp(90), fx.chorus(mode='II', mix=0.3)],
    sends={'hall': -10},
    notes='v1. Fairlight CMI AAHHL1: a single clear "aah" voice layer, lighter than the choir: toplines, octave '
          'doubles, vocal pads in dreamwave. License unclear (anonymous archive.org upload). Sends: hall -10. Measured '
          '-18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/fairlight_strings',
    instrument=_cmi('14 LOSTRING/STRNGENS.wav', level=-3.4, loop=(3000, 15500), attack=0.12, release=0.9),
    fx=[_hp(70), fx.ensemble(mix=0.35)],
    sends={'hall': -10},
    notes='v1. Fairlight CMI STRNGENS: the grainy 8-bit string ensemble of early-80s records, between a real section '
          'and a string machine. Slow chords and pads C3-C5. License unclear (anonymous archive.org upload). Sends: '
          'hall -10. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/fairlight_brass',
    instrument=_cmi('25 ANALOG/BRASSYN5.wav', level=-9.8, loop=(3000, 15500), attack=0.01, release=0.35),
    fx=[_hp(80), fx.chorus(mode='I', mix=0.3)],
    sends={'hall': -14},
    notes='v1. Fairlight CMI BRASSYN5: a sampled analog synth-brass (the CMI\'s own take on the Oberheim / Prophet '
          'brass): stabs and swells C3-C5. License unclear (anonymous archive.org upload). Sends: hall -14. Measured '
          '-18.0 LUFS (audition stabs).',
    audition={'notes': 'stab'}))

# --------------------------------------------------------------------------------------------- pipe organ

register(Patch(
    'sampled/church_organ',
    instrument=inst.organ(_BUREA, stops=['Principal 8', 'Oktava 4'], lazy=True, level=-4.9),
    fx=[_hp(30)],
    sends={'hall': -20},
    notes='v2. Burea Church (Sweden) main manual, Principal 8\' + Oktava 4\': the classic hymn and chorale registration, '
          'every pipe with its recorded attack, sustain loop and release into the church. Hymns, chorales, ballad '
          'intros; hold chords, legato voice leading. Range C2-G6. Tweak: expression (swell), tremulant via '
          "inst.organ('" + _BUREA + "', stops=[...], tremulant=True). CC-BY-SA 2.5: credit Lars Palo. Sends: hall "
          '-20 (the samples carry the church). Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/church_organ_full',
    instrument=inst.organ(_BUREA, stops=['Principal 8', 'Oktava 4', 'Oktava 2', 'Mixtur V'], lazy=True,
                          level=-7.0),
    fx=[_hp(30)],
    sends={'hall': -22},
    notes='v2. Burea Church main manual plenum: Principal 8\', Oktava 4\', Oktava 2\', Mixtur V - the bright full '
          'organ for climaxes, toccatas and the big final chord. CC-BY-SA 2.5: credit Lars Palo. Sends: hall -22. '
          'Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/church_organ_flutes',
    instrument=inst.organ(_BUREA, stops=['Rorflojt 8', 'Halflojt 4'], manual='Svallverk', tremulant=True, lazy=True,
                          level=4.8),
    fx=[_hp(40)],
    sends={'hall': -18},
    notes='v2. Burea Church swell manual, Rorflojt 8\' + Halflojt 4\' with the tremulant: soft, hooty flutes for '
          'quiet interludes, film cues and dreamy pads. CC-BY-SA 2.5: credit Lars Palo. Sends: hall -18. Measured '
          '-18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/organ_pedal',
    instrument=inst.organ(_BUREA, stops=['Subbas 16', 'Principal 8'], manual='pedal', stereo='left', lazy=True,
                          level=6.1),
    fx=[_hp(20)],
    sends={'hall': -24},
    notes='v2. Burea Church pedal, Subbas 16\' + Principal 8\': the deep foundation under the manuals (keys C2-F4 only: '
          'play the bass line in C2-C3 on its own track). One microphone (stereo=\'left\'): mono, solid in the low end '
          '(the spaced pair cancels some pedal pipes in mono). CC-BY-SA 2.5: credit Lars Palo. Sends: hall -24. Measured '
          '-18.0 LUFS (audition bass).',
    audition={'notes': 'bass'}))
