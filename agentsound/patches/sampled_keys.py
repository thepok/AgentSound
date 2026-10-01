"""Sampled keyboards beyond the core set in sampled.py: more acoustic pianos, vintage electric pianos, the clavinet,
tonewheel / chamber / Renaissance organs, the harpsichord, the Mellotron and sampled vintage string machine and
polysynths (instrument 'sampler' via inst.sfz / inst.sfz_multi / inst.organ / inst.multisample, all lazy).

  pianos:    sampled/soft_piano sampled/studio_piano sampled/recital_grand sampled/concert_grand sampled/upright_yamaha
             sampled/honky_tonk
  electric:  sampled/rhodes_vibrato sampled/cp80 sampled/pianet sampled/clavinet
  organs:    sampled/tonewheel_organ sampled/jazz_organ sampled/chamber_organ sampled/renaissance_organ
  baroque:   sampled/harpsichord
  mellotron: sampled/mellotron_strings sampled/mellotron_flute sampled/mellotron_choir sampled/mellotron_cello
  synths:    sampled/solina_strings sampled/poly_synth sampled/soft_poly

Which piano: sampled/grand_piano (Salamander, 16 layers, retuned to equal temperament) stays the all-rounder;
recital_grand for classical solo piano (the Headroom C3 voiced and measured against a concert recording:
velocity response, audience width, sympathetic resonance), concert_grand for concerto / orchestral parts (a
Steinway, even and big, but dark: -10 dB above 3 kHz against real piano recordings), studio_piano for pop ballads
(a close, modern C3), soft_piano
for film and quiet intimate cues (a C2 played softly with the una corda), upright_yamaha / honky_tonk for bar-room,
folk and ragtime. The acoustic pianos here keep their natural stretch tuning (the treble rises to about +20 ct at C7
and +40 ct at C8, the low bass sits 10-20 ct flat, like a tuned concert instrument); above C7 with synths or other
pianos prefer sampled/grand_piano.

Each patch reads its files only when a song renders it (lazy): importing the library never needs the samples, and a
patch whose pack is missing fails at use with the pack id (`python -m agentsound samples fetch <id>`). Level
calibration: every patch at gain_db 0 lands at about -18 LUFS integrated (track node, dry) playing its audition
material (`python -m agentsound audition <patch>`), measured value in the notes. Licences differ per pack: CC0 and
public domain need nothing, CC-BY needs the credit in the notes, CC-BY-NC / 'free, not in commercial software' /
royalty-free-no-redistribution / unclear packs are fine for private listening and songs but must be checked before a
commercial release (the build's credits.txt lists them). Version: see VERSION.
"""

from . import Patch, fx, inst, register

VERSION = 1


def _hp(freq: float, slope: int = 24, **bands):
    """Clean-up high-pass (+ optional EQ bands, e.g. peak1__freq=...)."""
    return fx.eq({'hp.freq': freq, 'hp.slope': slope, **{k.replace('__', '.'): v for k, v in bands.items()}})


def _sfz(path: str, level: float, **kw):
    return inst.sfz(path, lazy=True, level=level, **kw)


def _multi(programs: dict, level: float, **kw):
    return inst.sfz_multi(programs, lazy=True, level=level, **kw)


def _ms(path: str, level: float, **kw):
    return inst.multisample(path, lazy=True, level=level, **kw)


_PEDAL = ('Sustain pedal: automate instrument.pedal in steps (1 down, 0 up; lift and re-press just after each chord '
          'change).')

# --------------------------------------------------------------------------------------------- acoustic pianos

register(Patch(
    'sampled/soft_piano',
    instrument=_sfz('samples/osiris-piano/Programs/01-natural.sfz', level=-2.6, cc={73: 0}, polyphony=160),
    fx=[_hp(30, peak3__freq=3500, peak3__gain=1.5, peak3__q=0.7)],
    sends={'hall': -10},
    notes='v1. Osiris Piano (Karoryfer, CC0): a Yamaha C2 grand recorded played quietly with the soft pedal (una '
          'corda) down, three microphones blended - the hushed, felt-like close piano of film scores, ambient, '
          'lo-fi and late-night ballads. 2 velocity layers (split at 64): the dynamic range is small by nature '
          '(about 12 dB from velocity 30 to 120): shape phrases with velocity 30-100 and expression, never hammer it. '
          'Range A0-C8; a sample every 2 keys. Measured note to note, a few recordings are softer than their '
          'neighbours (D4-E4, G5-G#5, about 6-10 dB at the same velocity): give exposed melody notes there '
          '+10-15 velocity. Onsets are tight (cc 73 "Ptah" = 0 skips the pre-note hammer and key noise; in your own '
          'inst.sfz of the file cc={73: 127} keeps it: realistic, but notes then speak 10-27 ms late - shift the track '
          'earlier). ' + _PEDAL + ' Tweak: the same file with cc={70: 127} ("Shu": the unfiltered, airy noise '
          'floor), 02-warm.sfz (a darker mapping), cutoff 6000 (even softer), width 0.7. Sends: hall -10. Measured '
          '-18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/studio_piano',
    instrument=_sfz('samples/headroom-piano/Headroom Piano (NoFX).sfz', level=9.3, velsens=0.7, polyphony=160),
    fx=[_hp(30)],
    sends={'hall': -14},
    notes='v1. Headroom Piano (Bengt Nilsson, SFZ by kinwie): a Yamaha C3 grand, 5 velocity layers, close microphones '
          'plus a Decca-tree room pair (mics: close / main) - a modern, clear pop and ballad piano between the '
          'Salamander and a record-ready close piano. velsens 0.7 (the layers carry the dynamics: about 20 dB from '
          'velocity 30 to 120). Range A0-C8, a sample every 3 keys; stretch-tuned treble (+13 ct from C5, +25..+50 '
          'ct above B6). Play: comping velocities 50-95, ballad melodies 70-110, accents up to 120. ' + _PEDAL +
          ' Tweak: in your own inst.sfz of the same file mics={"main": -6} (drier, closer) or mics={"close": None} '
          '(room only), cc={73: 64} (half velocity tracking), cc={72: 20..127} (release time); the file "Headroom '
          'Piano.sfz" adds its own EQ controls. Credit: Bengt Nilsson (Headroom Piano), CC-BY 4.0. Sends: hall -14. '
          'Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

RECITAL = {'velsens': 1.0, 'width': 0.75, 'sympathetic': 0.9}
"""sampled/recital_grand vs sampled/studio_piano (the same Headroom C3): the values the Gymnopedie etude measured
against a concert recording (songs/gymnopedie-etude/NOTES.md)."""

register(Patch(
    'sampled/recital_grand',
    instrument=_sfz('samples/headroom-piano/Headroom Piano (NoFX).sfz', level=11.4, polyphony=192, **RECITAL),
    fx=[_hp(35)],
    sends={'hall': -11},
    notes='v1. The classical recital grand: Headroom Piano (a Yamaha C3, close + Decca-tree room) voiced for solo piano '
          'heard from the hall - Satie, Chopin nocturnes, Debussy, slow film piano. Measured on the Gymnopedie etude '
          'against a concert recording (songs/gymnopedie-etude/NOTES.md), same performance, studio_piano -> this patch: '
          'velsens 1.0 (studio_piano 0.7 squeezed a p-mp melody to 4.5 dB of note-to-note dynamics per phrase - '
          'flat_dynamics - and the melody only 5 dB over the chords; here 5.9 dB per phrase and 8.2 dB over the chords, '
          'the recording 8.2), width 0.75 (the audience image: 49 -> 35 % above 150 Hz, the recording 36 %), '
          'sympathetic string resonance 0.9 (with the pedal down the sound blooms: a held E4 decays 3.3 dB/s instead of '
          '4.3, the recording 3.4), a concert hall send -11 (reverb ~11.5 LU under the mix). Tonal balance within ~4 dB '
          'of the recording in every band (the concert_grand samples read 10 dB darker above 3 kHz). Play: pp 30-45, p '
          '45-60, mp-mf 60-90, the melody 10-15 velocity over the accompaniment, the bass a little under the melody; '
          + _PEDAL + ' A half pedal (0.6-0.8) clears the treble and keeps the bass. Analysis profile "piano" '
          '(ANALYSIS = {"profile": "piano"}). Credit: Bengt Nilsson (Headroom Piano), CC-BY 4.0. Sends: hall -11. '
          'Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/concert_grand',
    instrument=_sfz('samples/splendid-grand-piano/Splendid Grand Piano.sfz', level=1.3, width=0.75, polyphony=160),
    fx=[_hp(28)],
    sends={'hall': -12},
    notes='v1. Splendid Grand Piano (the AKAI Steinway library, public domain; SFZ by kinwie): a big concert Steinway '
          'D, 4 velocity layers (pp, mp, mf, ff) plus key-release resonance, the most even of the sampled grands '
          '(neighbouring notes within 2-3 dB) - classical solo and concerto parts, film themes, grand ballads. Width '
          '0.75 (the spaced pair is wide and nearly uncorrelated; 0.75 keeps it mono-safe). Range A0-C8. Dynamics '
          'follow velocity over about 22 dB (30 -> 120): pp 25-45, mf 60-80, ff 100-125. ' + _PEDAL + ' Tweak: '
          'cc={70: 0..127} (sympathetic resonance amount, default 64), cc={72: 0..127} (release), width 1.0 (the full '
          'spaced image), velsens 0.8. Stretch-tuned like a real concert grand (+20..+50 ct over the top octave). '
          'Public domain: no credit needed. Sends: hall -12. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/upright_yamaha',
    instrument=_sfz('samples/vcsl/Chordophones/Zithers/Upright Piano, Yamaha.sfz', level=3.8, width=0.6, polyphony=160),
    fx=[_hp(35, peak1__freq=300, peak1__gain=-1.5, peak1__q=0.9)],
    sends={'hall': -14},
    notes='v1. VCSL Yamaha upright (Versilian Community Sample Library, CC0): 3 velocity layers x 3 round robins (a '
          'repeated note never repeats the same recording) and a key-release sample per note - a lively, woody '
          'upright, more alive than sampled/upright_piano. Singer-songwriter, folk, indie pop, cafe and bar-room '
          'piano, practice-room intimacy. Width 0.6 (the stereo pair is almost uncorrelated). Range A0-E7 (no top '
          'octave). ' + _PEDAL + ' Velocities 45-110; repeated 8ths and ostinatos sound natural thanks to the round '
          'robins. Tweak: width 1.0, cutoff 7000 (older, darker). The low bass (A0-D#1) is thin and sits flat (the '
          'recording). CC0 (Versilian Studios). Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/honky_tonk',
    instrument=_sfz('samples/freepats-old-piano-fb/PianoFB 20200401.sfz', level=-0.8, polyphony=128),
    fx=[_hp(40, peak3__freq=2500, peak3__gain=1.5, peak3__q=0.8)],
    sends={'plate': -18},
    notes='v1. FreePats Old Piano FB (CC0): an old, slightly out-of-tune player/bar-room piano - the unison strings '
          'beat against each other (measured +-10..30 ct per note, by design) and the tone is bright and tinny. '
          'Ragtime, saloon and western scenes, vaudeville, a rock\'n\'roll boogie right hand, the "old radio" colour '
          'in a film cue. One sample per key (G0-C8), one velocity layer (dynamics = level only): vary the velocity '
          '70-115 and play rhythmically (stride bass, boogie 8ths, tremolo octaves) rather than long legato. Tweak: '
          'velsens 0.7, cutoff 5000 (behind a wall). CC0. Sends: plate -18. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

# --------------------------------------------------------------------------------------------- electric pianos

register(Patch(
    'sampled/rhodes_vibrato',
    instrument=_sfz('samples/jrhodes3d/jRhodes3d-sv.sfz', level=-9.5, polyphony=128),
    fx=[_hp(40)],
    sends={'hall': -16},
    notes='v1. jRhodes3d stereo-vibrato set (Jeff Learman, a 1977 Rhodes Mark I Stage 73, 5 crossfaded velocity '
          'layers from soft bell to bark): the "suitcase" stereo vibrato is in the samples - every note swirls left '
          'and right on its own, a dreamy, liquid ballad / neo-soul / lo-fi Rhodes (sampled/rhodes is the same piano '
          'dry). Range C1-F7. Play: velocities 40-100 for the warm bell tone, 100-127 for the bark (the hardest '
          'layer growls but is not louder). ' + _PEDAL + ' Tweak: cc={1: 0..127} in your own inst.sfz of the file '
          '(vibrato width: 0 mono, 64 as recorded, 127 extra wide). License CC-BY-NC 4.0 in the pack (the SFZ header '
          'says free to use in your music): fine for songs, check before commercial use of the samples. Sends: hall '
          '-16. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/cp80',
    instrument=_sfz('samples/greg-sullivan-epianos/CP80/CP80.sfz', level=5.9, polyphony=128),
    fx=[_hp(40, peak3__freq=3000, peak3__gain=1.5, peak3__q=0.8), fx.chorus(mode='I', mix=0.3)],
    sends={'hall': -14},
    notes='v1. Yamaha CP-80 electric grand (Greg Sullivan, SFZ by kinwie): real piano strings with pickups - the '
          'bright, percussive, slightly out-of-phase "electric grand" of 80s ballads and pop (Genesis, Phil Collins, '
          'U2, Keane, a-ha). 4 velocity layers (pp, mp, f, ff; about 24 dB from velocity 30 to 120), full-length '
          'samples, A0-C8; stretch-tuned bass and treble like the real instrument. With the classic Juno chorus I '
          '(mix 0.3) that gives it width - it is mono. Play: chords and octave riffs at velocity 70-115, a pushed '
          '8th-note pulse in the verse. ' + _PEDAL + ' Tweak: .but_fx("chorus", mix=0) (dry mono CP), '
          '.but_fx("chorus", mode="II") (thicker 80s), cc={72: 20..127} (release). Credit: Greg Sullivan '
          '(E-Pianos), CC-BY 3.0. Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/pianet',
    instrument=_sfz('samples/greg-sullivan-epianos/Pianet T/Pianet T.sfz', level=4.2, polyphony=96),
    fx=[_hp(50)],
    sends={'plate': -16},
    notes='v1. Hohner Pianet T (Greg Sullivan, SFZ by kinwie): sticky reeds plucked by rubber pads - the soft, woody, '
          'short 60s keyboard (The Zombies "She\'s Not There", the Beatles, Lennon; indie and bedroom pop today). '
          '2 velocity layers + key-release clicks, F1-E6 (the real range), mono. It decays fast: play riffs, '
          'broken chords and repeated 8ths (velocity 60-110), not pads. Tweak: fx.tremolo(rate=5.5, depth=0.35) '
          '(amp vibrato), fx.chorus(mode="I", mix=0.25) (width), cc={72: 20..127} (release). Credit: Greg Sullivan '
          '(E-Pianos), CC-BY 3.0. Sends: plate -16. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/clavinet',
    instrument=_sfz('samples/lithalean-clavinet/Clavinet.sfz', level=4.5, velsens=0.3, polyphony=64),
    fx=[_hp(70, peak1__freq=250, peak1__gain=-2.0, peak1__q=0.9, peak3__freq=2800, peak3__gain=2.0, peak3__q=0.8)],
    sends={'plate': -20},
    notes='v1. Hohner Clavinet D6 (Lithalean): 4 velocity layers per key (recorded at velocity 54, 83, 106, 127), '
          'every key F1-E6 sampled - the funk clav of Stevie Wonder\'s "Superstition", Bill Withers, 70s funk and '
          'rock. velsens 0.3: the recorded layers carry the dynamics (the soft layer is 22 dB below the hard one; '
          'with full velocity scaling as well, soft notes vanished; now about 29 dB from velocity 30 to 120). '
          'Play it as a percussion instrument: 16th-note riffs with ghost notes (velocity 40-60) between accents (110-127), short notes (gate 0.3-0.6), '
          'interlocking left and right hand. Tweak: fx.filter envelope / auto-wah for the "Higher Ground" sound, '
          'fx.phaser(rate=0.5, mix=0.4), fx.saturator(drive=9) for rock. License not stated by the author: fine for '
          'sketches and private listening, check before releasing. Sends: plate -20. Measured -18.0 LUFS (audition '
          'stabs).',
    audition={'notes': 'stab'}))

# --------------------------------------------------------------------------------------------- organs

_LESLIE_NOTE = ('Leslie speed: automate fx.leslie.rate and fx.leslie_am.rate together from 0.8 (slow "chorale") to '
                '6.7 (fast "tremolo") over about 1-1.5 s (the rotor spins up; spinning down takes ~2-3 s), e.g. '
                "track.automate('fx.leslie.rate', [(b, 0.8), (b + 2, 6.7, 'exp')]) - the classic moves: fast on the "
                'chorus or a held chord, slow for the verse.')

register(Patch(
    'sampled/tonewheel_organ',
    instrument=_sfz('samples/freepats-drawbar-organ/DrawbarOrganEmulation-20190712.sfz', level=-5.0, polyphony=64),
    fx=[_hp(40),
        fx.saturator(mode='tube', drive=5, tone=-1, mix=0.8),
        fx.chorus(name='leslie', mode='custom', rate=0.8, depth=0.45, delay=1.0, voices=1, spread=1, mix=0.5,
                  tone=9000),
        fx.tremolo(name='leslie_am', rate=0.8, depth=0.2, stereo=120)],
    sends={'hall': -18},
    notes='v1. A Hammond-style tonewheel organ (FreePats drawbar organ, rendered from the setBfree B3 emulation; CC0) '
          'through a Leslie built from effects: a tube pre-amp (saturator), the rotating horn\'s Doppler (a one-voice '
          'chorus, 0.45 ms swing: about +-4 ct slow, +-30 ct fast) and its amplitude / stereo swirl (tremolo, 120 deg '
          'between the sides). Gospel, soul, blues, rock and jazz comping. ' + _LESLIE_NOTE + ' Range A1-D7 (the '
          'full drawbar registration, one layer, no velocity). An organ does not decay: voice-lead held chords, '
          'use rhythmic stabs and short "chucks" in funk, glissandi (fast runs) into the downbeat, and '
          'expression (the swell pedal, 0.4-1.0) for swells. Tweak: .but_fx("saturator", drive=14) (rock growl, '
          'Deep Purple), .but_fx("leslie", mix=0) + .but_fx("leslie_am", depth=0) (no Leslie), '
          'but_fx("leslie", rate=6.7) + but_fx("leslie_am", rate=6.7) (fast from the start). CC0. Sends: hall -18. '
          'Measured -18.0 LUFS (audition chords, slow Leslie).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/jazz_organ',
    instrument=_sfz('samples/freepats-percussive-organ/PercussiveOrganEmulation-20190715.sfz', level=-7.4,
                    width=0.5, polyphony=64),
    fx=[_hp(45)],
    sends={'hall': -20},
    notes='v1. Percussive tonewheel organ (FreePats, rendered from setBfree; CC0): the Hammond "percussion" click on '
          'every attack (the decaying 2nd/3rd harmonic) over soft drawbars, recorded through its (slow) Leslie in '
          'stereo - Jimmy Smith / soul-jazz comping, organ trio, gospel fills, Booker T. Width 0.5: the Leslie '
          'microphones are partly out of phase (correlation -0.4 as recorded; 0.5 keeps it mono-safe). Range G1-C8, '
          'no velocity layers. Play: short, rhythmic comping chords (the percussion only sounds on detached '
          'notes on a real B3 - write them detached), bluesy right-hand lines with grace-note slides (a crushed '
          'note a semitone below), left-hand bass lines on a second track (sampled/organ_pedal or a bass). Tweak: '
          'width 1.0 (the full swirl), fx.saturator(mode="tube", drive=8) (grit). CC0. Sends: hall -20. Measured '
          '-18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/chamber_organ',
    instrument=inst.organ('samples/lars-palo-burea-choir-organ', stops=['Rorflojt 8', 'Principal 4'], lazy=True,
                          level=-5.4),
    fx=[_hp(30)],
    sends={'hall': -18},
    notes='v1. Burea Church choir organ (Lars Palo, GrandOrgue set; a small one-manual organ): Rorflojt 8\' + '
          'Principal 4\' - a soft, clear chamber / continuo organ, every pipe with its attack, sustain loop and '
          'release into the church. Baroque continuo and chorales, hymns, intimate film cues, a folk or indie ballad '
          'bed; smaller and gentler than sampled/church_organ. Range C2-G6, no velocity (dynamics: expression). '
          'Hold chords with legato voice leading. Other stops for inst.organ("samples/lars-palo-burea-choir-organ", '
          'stops=[...]): Rorflojt 8 alone (the softest flute), Gedackt 4, Geigenregal 8 (a buzzy reed), Blockflojt '
          '2, Cymbel (mixture), pedal Subbas 16 (manual="pedal"). CC-BY-SA 2.5: credit "Burea Church choir organ '
          'sample set by Lars Palo". Sends: hall -18. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

_VA = 'samples/vcsl/Aerophones/Edge-blown Aerophones/'
register(Patch(
    'sampled/renaissance_organ',
    instrument=_multi({'8ft': _VA + "Renaissance Organ - 8'.sfz", '4ft+8ft': _VA + "Renaissance Organ - 4'+8'.sfz",
                       'full': _VA + 'Renaissance Organ - Full.sfz', '4ft': _VA + "Renaissance Organ - 4'.sfz"},
                      level=-7.9),
    fx=[_hp(40)],
    sends={'hall': -14},
    notes='v1. VCSL Renaissance positive organ (Versilian Community Sample Library, CC0), recorded in its room: '
          'registrations as articulations (keyswitches C-1.., inserted by the compiler): "8ft" (default: the '
          '8\' stop), "4ft+8ft", "full" (all stops, the strongest), "4ft" (the 4\' alone, an octave up) - '
          'clip.articulate("full", span=(...)) changes the registration for a passage, like an organist '
          'pulling stops. Early music, madrigal and chorale accompaniment, medieval / fantasy film scenes. Range '
          'C2-F6, no velocity. Tweak: expression (swell). CC0. Sends: hall -14. Measured -18.0 LUFS (audition '
          'chords, 8ft).',
    audition={'notes': 'chord'}))

# --------------------------------------------------------------------------------------------- harpsichord

_VC = 'samples/vcsl/Chordophones/Zithers/'
register(Patch(
    'sampled/harpsichord',
    instrument=_multi({'8ft': _VC + "Harpsichord, Flemish - 8'.sfz", 'full': _VC + 'Harpsichord, Flemish - Full.sfz',
                       '4ft': _VC + "Harpsichord, Flemish - 4'.sfz"}, level=5.8, width=0.7, polyphony=96),
    fx=[_hp(60)],
    sends={'hall': -14},
    notes='v1. VCSL Flemish harpsichord (Versilian Community Sample Library, CC0) with its jack release noise on '
          'key-up. Registrations as articulations (keyswitches, inserted by the compiler): "8ft" (default: one '
          'choir of strings), "full" (8\' + 4\': the bright, full sound for tutti and the final section), "4ft" '
          '(the octave-up choir alone: delicate) - clip.articulate("full", span=(...)). A harpsichord has no '
          'dynamics (velocity does not change the level, by design): phrase with articulation instead - detached '
          '8ths and 16ths, arpeggiated (rolled) chords (clip.strum(20-40)), ornaments (trills, mordents as grace '
          'notes), and the registration for contrast. Baroque (Bach, Scarlatti), period film, 60s baroque pop '
          '(the Beatles, the Left Banke). Range F1-C6. Width 0.7 (spaced microphones). CC0. Sends: hall -14. '
          'Measured -18.0 LUFS (audition arpeggio, 8ft).',
    audition={'notes': 'arp'}))

# --------------------------------------------------------------------------------------------- Mellotron

_MT = 'samples/mellotron-sfz/Mellotron/'
_MT_NOTE = ('Real Mellotron tapes (the Leisureland samples, SFZ project by ExistentiaVirae): one tape per key G2-F5 '
            '(35 keys, the real range), each about 7.5 s long - like the instrument, a held note simply ends when the '
            'tape runs out: re-strike long chords every bar or two. The tape wow, flutter and the few cents of '
            'drift between keys are the sound. No velocity layers: dynamics = velocity level and expression. '
            'License: "free to use, but not in any commercial software" (the samples; songs made with them are '
            'fine) - credit Bernie Kornowicz (leisureland.us).')

for _name, _dir, _tune, _lvl, _hz, _send, _material, _desc, _extra in (
        ('strings', 'MkII Violins', 5, -2.0, 120, -12, 'chord',
         'the MkII 3-violin tape: THE Mellotron strings of "Nights in White Satin", King Crimson, Genesis, '
         'Radiohead - slow chords and lines G3-F5, wistful and a little seasick.', ''),
        ('flute', 'MkII Flute', -9, -0.1, 150, -12, 'phrase',
         'the MkII flute tape: "Strawberry Fields Forever", psych and prog, dream pop: melodies and slow '
         'arpeggios C4-F5, soft chords.', ''),
        ('choir', '8 Choir', 6, -1.3, 120, -12, 'chord',
         'the 8-voice mixed choir tape: the eerie "aah" of prog, Bowie\'s "Space Oddity" era, doom and film '
         'horror: held chords G2-F5.', ' The F#3 tape has a small tick 0.55 s in (the recording).'),
        ('cello', 'Cello', 11, -0.6, 60, -14, 'chord',
         'the solo cello tape: dark lines and the low voice of Mellotron string chords G2-C5 (layer it under '
         'sampled/mellotron_strings on its own track).', ' A few tapes carry faint ticks (the recording).')):
    register(Patch(
        f'sampled/mellotron_{_name}',
        instrument=_ms(f'{_MT}{_dir}/samples', level=_lvl, tune=_tune, attack=0.01, release=0.25, polyphony=48),
        fx=[_hp(_hz)],
        sends={'hall': _send},
        notes=f'v1. Mellotron {_name}: {_desc} {_MT_NOTE} Tuning: tune {_tune:+d} ct (the tape set\'s measured '
              f'median).{_extra} Sends: hall {_send}. Measured -18.0 LUFS (audition '
              f'{"melody" if _material == "phrase" else "chords"}).',
        audition={'notes': _material}))

# --------------------------------------------------------------------------------------------- vintage synths

_RADAR = ('License: SampleRadar (MusicRadar) royalty-free: use in your music, the samples themselves may not be '
          'redistributed.')

register(Patch(
    'sampled/solina_strings',
    instrument=_ms('samples/sampleradar-976-classic-synth/ARP Solina/Viola', level=0.4, loop='pingpong',
                   loop_start=22050, loop_end=169000, attack=0.08, release=0.6, polyphony=64),
    fx=[_hp(70), fx.chorus(mode='I', mix=0.2)],
    sends={'hall': -12},
    notes='v1. ARP Solina String Ensemble, sampled from the real machine (SampleRadar 976 classic synth, the viola '
          'register with its own ensemble chorus): the 70s string machine of Jean-Michel Jarre, Pink Floyd, disco '
          'and Joy Division, today in synthwave and dream pop. A sample per white key C2-C6 (range C2-C6), looped '
          '(ping-pong over its steady middle) so chords hold forever; slow attack, long release. Play: held '
          'chords and pads C3-C5, slow voice leading; no velocity layers (level only). Tweak: attack 0.3 (slower '
          'swell), fx.phaser(rate=0.2, mix=0.4) (the Jarre "Oxygene" phaser), the violin register '
          'inst.multisample("samples/sampleradar-976-classic-synth/ARP Solina/Violin", loop="pingpong", '
          'loop_start=22050, loop_end=169000) (C3-C7). ' + _RADAR + ' Sends: hall -12. Measured -18.0 LUFS '
          '(audition chords).',
    audition={'notes': 'chord'}))

_POLY = 'samples/sampleradar-analogue-polysynths/Instruments/'
register(Patch(
    'sampled/poly_synth',
    instrument=_ms(_POLY + 'Big Poly A', level=-1.1, octave=1, loop='pingpong', loop_start=88200,
                   loop_end=507150, release=0.5, polyphony=64),
    fx=[_hp(60), fx.chorus(mode='I', mix=0.3)],
    sends={'hall': -14},
    notes='v1. A big analogue brass-poly (SampleRadar analogue polysynths "Big Poly A", Prophet / Jupiter style, '
          'recorded from hardware-style patches): fat, bright detuned saws - 80s pop stabs and pads, synthwave '
          'chords, Van Halen "Jump"-style riffs. A sample every 2 keys C1-C7 (the pack names middle C "C3": '
          'octave=1 puts it right), 12 s long, looped in the steady part. Play: chord stabs (gate 0.4-0.7) and held '
          'pads C3-C6, velocity 80-120 (level only). Tweak: cutoff 3000 (darker), attack 0.2 (brass swell). '
          + _RADAR + ' Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/soft_poly',
    instrument=_ms(_POLY + 'SoftPoly D', level=-2.9, octave=1, loop='pingpong', loop_start=176400,
                   loop_end=507150, release=0.8, polyphony=64),
    fx=[_hp(60), fx.chorus(mode='II', mix=0.3)],
    sends={'hall': -12},
    notes='v1. A soft analogue poly pad (SampleRadar analogue polysynths "SoftPoly D"): warm, round, slowly '
          'opening - 80s ballads, dreamwave and ambient beds under a piano or a lead. A sample every 2 keys C1-C7 '
          '(octave=1: the pack calls middle C "C3"), looped in its steady part. Play: held chords C3-C5, voice-led; '
          'velocity is level only. Tweak: attack 0.5 (slower swell), cutoff 2500 (darker). ' + _RADAR + ' Sends: '
          'hall -12. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))
