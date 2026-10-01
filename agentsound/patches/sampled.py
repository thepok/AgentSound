"""Sampled instruments from the downloaded SFZ libraries (instrument 'sampler' via inst.sfz): pianos, electric
pianos, vibraphone, upright bass, brush and jazz kits, saxophones, nylon guitar and the Virtual Playing Orchestra.

  keys:      sampled/grand_piano sampled/piano_lead sampled/upright_piano sampled/rhodes sampled/wurlitzer sampled/vibraphone
             sampled/celesta
  jazz:      sampled/upright_bass sampled/brush_kit sampled/jazz_kit sampled/tenor_sax sampled/alto_sax
             sampled/nylon_guitar
  orchestra: sampled/strings sampled/strings_staccato sampled/strings_pizz sampled/violins sampled/cellos
             sampled/basses sampled/flute sampled/clarinet sampled/oboe sampled/french_horns sampled/trumpet
             sampled/trombones sampled/harp sampled/timpani sampled/choir
  played:    sampled/solo_violin sampled/solo_cello sampled/violin_section sampled/viola_section
             sampled/cello_section sampled/bass_section (keyswitched articulations, live dynamics, legato soloists:
             docs/COMPOSE_API.md "Realistic performance"; articulation.perform(track, line, at) plays a line on them)

Each patch reads its .sfz only when a song renders it (inst.sfz(..., lazy=True)): importing the library never needs
the samples, and a patch whose pack is not installed fails at use with the pack id to fetch
(`python -m agentsound samples fetch <id>`). Only the zones the song's notes can reach are loaded (zone pruning at
compile), so a 16-layer piano playing a few chords loads a fraction of its files. Any other program of these packs:
inst.sfz('samples/<pack>/<file>.sfz', ...); `python -m agentsound sfz <file>` shows its keys, layers, controllers
and articulations. Controller and microphone tweaks named in the notes (cc=..., mics=...) are import settings: use
inst.sfz(<the patch's file>, cc=..., level=<its level>) for them; params (pedal, expression, cutoff, velsens, width
...) work on the patch directly: patches.get('sampled/grand_piano').but(velsens=0.8). attack / decay / sustain /
release only reach zones without an ampeg_* of their own (most SFZ instruments set them).

Level calibration: every patch at gain_db 0 lands at about -18 LUFS integrated (track node, dry) playing its audition
material, like the synth and GM libraries (the calibration lives in the sampler 'level' param). Measured with
`python -m agentsound audition <patch>`. Licenses differ per pack (`python -m agentsound samples -v`): credit the
CC-BY packs; rhodes and vibraphone are non-commercial (CC-BY-NC). Version: see VERSION (bump it when a sound changes
audibly).
"""

from . import Patch, fx, inst, register
from ..sfz import even_velcurve as _even_velcurve

# Levels of the 'played' patches (audition-calibrated to -18 LUFS)
LEVELS = {'solo_violin': -0.8, 'solo_cello': 4.6, 'violin_section': 2.7, 'viola_section': -7.2, 'cello_section': -5.5,
          'bass_section': 5.2}

VERSION = 3


def _hp(freq: float, slope: int = 24):
    """Clean-up high-pass (also removes the DC offset some sample sets carry)."""
    return fx.eq({'hp.freq': freq, 'hp.slope': slope})


def _sfz(path: str, level: float, **kw):
    return inst.sfz(path, lazy=True, level=level, **kw)


def _multi(programs: dict, level: float, **kw):
    return inst.sfz_multi(programs, lazy=True, level=level, **kw)


# --------------------------------------------------------------------------------------------- keys

register(Patch(
    'sampled/grand_piano',
    instrument=_sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz', level=1.7),
    fx=[_hp(30)],
    sends={'hall': -12},
    notes='v1. Salamander Grand Piano V3 (Yamaha C5, 16 velocity layers, retuned to equal temperament) with its '
          'release samples: damper and string noises play at key-up (or at pedal-up while the pedal is down), '
          'softer the longer the key was held. Stereo from the player\'s seat: bass left, treble right. Sustain '
          'pedal: automate instrument.pedal with steps (1 down, 0 up; lift and re-press just after each chord '
          'change). Range: A0-C8; comping A2-E5, melodies C4-C6; velocities 40-110 for a jazz touch. Tweak: velsens '
          '0.8 (flatter dynamics), cutoff 9000 (softer), width 0.7 (narrower image), expression (swells). Credit: '
          'Alexander Holm, CC-BY 3.0. Sends: hall -12. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/jazz_grand',
    instrument=_sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz', level=1.7, hammers=0.75),
    fx=[_hp(30)],
    sends={'hall': -12},
    notes='v1. The Salamander Grand voiced warm for jazz and ballads: softened hammers (inst.sfz hammers=0.75: the '
          'loud velocity layers -5 dB at 3 kHz / -7 dB at 7.5 kHz, the soft ones a little clearer - loud notes '
          'bloom instead of turning glassy and percussive, soft ones still speak). Everything else as '
          'sampled/grand_piano (release samples, pedal, A0-C8). User feedback 2026-09-30 (perry-street-rain): "es '
          'klingt hart". The jazz presets (bands.make(\'jazz_trio\' ...)) play it. Credit: Alexander Holm, CC-BY 3.0. '
          'Sends: hall -12. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/piano_lead',
    instrument=_sfz('samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz', level=8.2, width=0.0,
                    polyphony=128),
    fx=[fx.eq({'hp.freq': 210, 'hp.slope': 24, 'peak1.freq': 420, 'peak1.gain': -3.0, 'peak1.q': 0.9,
               'peak3.freq': 3600, 'peak3.gain': 3.0, 'peak3.q': 0.8, 'high.freq': 9500, 'high.gain': 3.0}),
        fx.compressor(threshold=-13, ratio=3.0, attack=4, release=150, knee=8),
        fx.chorus(mode='I', mix=0.22),
        fx.dimension(mode=2, width=0.8)],
    sends={'plate': -12, 'hall': -14},
    notes='v1. The 80s pop piano hook (The Midnight, FM-84, Timecop1983, power-ballad right hand): the Salamander '
          'Grand (Yamaha C5, 16 velocity layers, release samples) voiced to carry a melody through a dense synth mix. '
          'Chain: the key panning summed to a mono centre (width 0: the high keys would lean right), high-pass 210 Hz '
          '(24 dB/oct: no body fighting pads and bass), -3 dB at 420 Hz (boxy body), +3 dB presence at 3.6 kHz and '
          '+3 dB air shelf at 9.5 kHz (the hammer sparkle), a compressor that evens the attacks and lifts the '
          'decaying sustain (peak, threshold -13, 3:1, 4 ms / 150 ms: about 4-5 dB off the attacks), Juno chorus I '
          '(mix 0.22) and a Dimension-D side layer (mode 2, width 0.8): ~27 % wide, correlation ~0.6, the dry piano '
          'intact in mono. Range: C5-C7 for hooks (it cuts from C5 up; below A4 use sampled/grand_piano). How to '
          'play: octave-doubled right hand - the melody plus the octave below at ~80 % velocity '
          '(clip.octave_double(-12, vel=0.8)) or above for the top sparkle; velocities 90-115 (the bright upper '
          'layers start ~90; vary them, accent the downbeats); a piano decays, so write the hook in repeated / '
          'rhythmic notes (8ths, dotted rhythms, re-struck long notes) rather than held synth-lead notes; for legato '
          'lines automate instrument.pedal in steps (down on the phrase, lift and re-press at chord changes). Pair '
          'it with a soft pad under it, or double the hook with synthwave/epiano_bright or synthwave/arp_glass on a '
          'second track at -8..-12 dB for extra FM sparkle. Tweak: velsens 0.8 (more even), .but_fx("chorus", '
          'mix=0) (a dry, natural piano), .but_fx("compressor", threshold=-18) (squashier 80s ballad), cutoff 9000 '
          '(softer). Bands: lead="piano" on the synthwave presets. Credit: Alexander Holm, CC-BY 3.0. Sends: '
          'plate -12, hall -14. Measured -18.0 LUFS (audition melody). GM fallback: gm/piano_lead.',
    audition={'notes': 'phrase'}))

register(Patch(
    'sampled/upright_piano',
    instrument=_sfz('samples/upright-piano-kw/UprightPianoKW-20220221.sfz', level=-0.9),
    fx=[_hp(35)],
    sends={'hall': -14},
    notes='v1. Upright Piano KW (FreePats, CC0): a warm upright, 2 velocity layers, looped sustain in the upper half. '
          'Bar-room, ballad, lo-fi and pop keys. Range: A0-C8. Tweak: velsens (0.8 = flatter dynamics), cutoff, pedal '
          '(sustain pedal, automate with steps). Sends: hall -14. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/rhodes',
    instrument=_sfz('samples/jrhodes3d/jRhodes3d-st.sfz', level=-7.9),
    fx=[_hp(40)],
    sends={'hall': -16},
    notes='v1. jRhodes3d (Jeff Learman, stereo version): a Rhodes Mark I, 5 velocity layers from soft bell to hard '
          'bark. Jazz ballads, neo-soul, lo-fi. Range: A0-C8. Tweak: cc={1: 0..127} (stereo width of the samples, '
          'default 64), pedal, velsens, fx.tremolo(rate=4.5, depth=0.3) for the suitcase vibrato. License CC-BY-NC '
          '4.0 (non-commercial). Sends: hall -16. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/wurlitzer',
    instrument=_sfz('samples/lithalean-wurlitzer/Wurlitzer.sfz', level=-1.7),
    fx=[_hp(40)],
    sends={'hall': -16},
    notes='v1. Lithalean Wurlitzer: reedy electric piano, 5 velocity layers, bites when played hard. Soul, 70s pop, '
          'lo-fi. Range: A1-C7. Tweak: fx.tremolo for the built-in vibrato, fx.saturator for growl. License not '
          'stated by the author: fine for sketches, check before releasing. Sends: hall -16. Measured -18.0 LUFS '
          '(audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/vibraphone',
    instrument=_sfz('samples/mslp-vibes/mslp_vibes.sfz', level=-4.4),
    fx=[_hp(60)],
    sends={'hall': -12},
    notes='v1. MSLP vibraphone (Music Sample Library Project, played by Joakim Linde): one sample per bar F3-F6, '
          'long looped ring. Jazz heads, 3-4 note comping, ballads. Tweak: pedal (let chords ring), cc={1: 40..127} '
          '(pitch vibrato), fx.tremolo(rate=5, depth=0.3) for the motor. License CC-BY-NC 3.0 (non-commercial). '
          'Sends: hall -12. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'sampled/celesta',
    instrument=_sfz('samples/vpo-scripts-standard/Keys/celesta.sfz', level=-6.2),
    fx=[_hp(120)],
    sends={'hall': -9},
    notes='v1. Virtual Playing Orchestra celesta: the bell-toy of the orchestra, lullabies and music-box lines an '
          'octave or two above the strings. Sends: hall -9. Measured -18.0 LUFS (audition arpeggio).',
    audition={'notes': 'arp'}))

# --------------------------------------------------------------------------------------------- jazz

# Meatbass pizz: the mean attack level (first 100 ms, dBFS) of each velocity layer's samples (all keys and takes).
# The file ramps every layer to full level at its top (amp_velcurve_32 / 64 / 96 = 1) and leaves the top layer on
# the default (v/127)^2: velocity 96 played ~3 dB LOUDER than 103 and 57..103 spanned ~4 dB, non-monotonic - a line
# with velocities 57-103 measured 0.0 dB of level explained by velocity. even_velcurve() gives one smooth response.
MEATBASS_LAYERS = [(1, 32, -21.15), (33, 64, -16.64), (65, 96, -13.54), (97, 127, -12.03)]

register(Patch(
    'sampled/upright_bass',
    instrument=_sfz('samples/meatbass/Programs/04_pizz.sfz', level=4.3,
                    velcurve=_even_velcurve(MEATBASS_LAYERS, power=2.0)),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v2. Meatbass (Karoryfer, CC0): pizzicato double bass, 4 velocity layers x 5 random takes, body and finger '
          'noise in the samples; the layers evened into one smooth velocity response ((v/127)^2: ~10 dB between '
          'velocity 57 and 103, the file alone gave ~4 dB and played 96 louder than 103). Walking lines: '
          'jazz.walking_bass / prog.bass("walk", low="E1") at velocity 70-110, shaped by humanize.bass_touch (phrase '
          'arcs, beat accents, ghosted pickups) - keep the chain\'s compression gentle so the notes stay different. '
          'Range: E1-G3 for real lines. Tweak: cutoff 3000 (darker), velsens; import settings cc={104: 0..127} '
          '(release time, default 25), cc={107: 14..81} (Voices: more players, a bass section). Sends: plate -20. '
          'Measured -18.0 LUFS (audition 8th bass).',
    audition={'notes': 'bass'}))

register(Patch(
    'sampled/brush_kit',
    instrument=_sfz('samples/swirly-drums/Programs/Basic_kit.sfz', level=9.2,
                    cc={4: 127, 14: 0, 57: 127, 56: 127, 58: 127}),
    fx=[_hp(30)],
    sends={'plate': -16},
    notes='v2. Swirly Drums (Karoryfer, CC0): the brush kit, close + room microphones. Keys: 36 kick, 38 snare, 40 '
          'rim/edge, 39 dig; 42 tight hat, 46 open hat, 44 hat foot, 54 hat splash; 51 ride, 49 crash; 41 / 45 / 47 '
          'toms. The sweeps: 60 slow stir, 64 fast stir - a swell (~0.6 s in, then an exponential tail); the next '
          'stir crossfades with it. For a continuous "shhh" start one about every second: jazz.swirly_sweep(tempo) '
          '(half bars at medium tempos, beats at ballads; measured: ~9 dB swell per stir, 25-30 dB gaps with one '
          'per bar). 62 stops the stir, 61 / 63 flutters. Brush taps are soft by nature: play snare and ride at '
          'velocity 40-90 over the stirs (stir volume raised: cc 57 = 127; stir tail cc 56 and release cc 58 at '
          '127 so the stirs overlap; cc 14 = 0 keeps the stir curve simple). Tweak (in your own inst.sfz of the same '
          'file, with these cc): cc 60 = 90 (snare room), cc 55 (stir attack time), mics={"wet": None} (close mics '
          'only). Sends: plate -16. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/jazz_kit',
    instrument=_sfz('samples/avl-blonde-bop/BLONDE_BOP.sfz', level=-0.8),
    fx=[_hp(30)],
    sends={'plate': -16},
    notes='v1. AVL Drumkits "Blonde Bop" (Glen MacArthur, CC-BY-SA 3.0): a small bebop kit played with sticks, 5 '
          'velocity layers per piece, hi-hats and cymbals choke by group. Keys: 36 kick 18", 37 side stick, 38 '
          'snare, 40 snare edge, 35 stick click, 39 clap; 42 hat closed, 44 hat pedal, 46 hat semi-open, 48 hat '
          'swish; 41 / 43 floor tom (centre / edge), 45 / 47 tom; 51 ride tip, 59 ride shank, 53 ride bell, 49 / 57 '
          'crashes (50 / 58 choked), 55 splash, 60 china, 54 tambourine, 56 cowbell, 61 shaker. Swing: ride '
          '"x..x.xx..x.xx..x" with .swing(0.62), hat pedal on 2 and 4. Sends: plate -16. Measured -18.0 LUFS '
          '(audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tenor_sax',
    instrument=_sfz('samples/mtg-solo-sax/MTG Solo Saxophones/MTG Tenor Sax.sfz', level=11.8, mono='legato',
                    legatotime=50),
    fx=[_hp(70)],
    sends={'hall': -12},
    notes='v2. MTG solo tenor saxophone (MTG / Freesound samples, SFZ by kinwie; CC-BY 4.0): soft (velocity <= 100) '
          'and loud (101-127) layers x 3 round robins; a filter envelope opens each note and closes slowly on long '
          'ones. A monophonic legato player (mono=\'legato\'): overlapping notes (articulation.legato, '
          'jazz.horn_line) are legato transitions - no new attack, level-matched - and notes after a rest attack; '
          'clip.glide(ms) for portamento. Range: D#2-E5 (sounding). Lines at velocity 70-115. Tweak: \'dynamics\' '
          '(live: the file\'s CC11 level), vibrato= / articulation.vibrato (delayed vibrato), cc={80: 0} (no key '
          'noises), mono=\'on\' (re-attacked notes, as v1). Sends: hall -12. Measured -18.0 LUFS (audition melody).',
    audition={'notes': 'phrase'}))

register(Patch(
    'sampled/alto_sax',
    instrument=_sfz('samples/karoryfer-weresax/Programs/Sax.sfz', level=-0.7, mono='legato', legatotime=50),
    fx=[_hp(90)],
    sends={'hall': -12},
    notes='v2. Weresax (Karoryfer, CC0): alto saxophone, 2 velocity layers x 2 round robins, two microphones blended '
          'by cc 120. A monophonic legato player (mono=\'legato\': overlapping notes are legato transitions). Range: '
          'C#3-G#5. Tweak: cc={111: 40..127} (vibrato depth), cc={120: 0..127} (mic blend). Its '
          'variable EQ modulation (varN) is not supported and is left out (one warning). Sends: hall -12. Measured '
          '-18.0 LUFS (audition melody).',
    audition={'notes': 'phrase'}))

register(Patch(
    'sampled/nylon_guitar',
    instrument=_sfz('samples/freepats-spanish-classical-guitar/SpanishClassicalGuitar-20190618.sfz', level=-3.4),
    fx=[_hp(70)],
    sends={'hall': -14},
    notes='v1. FreePats Spanish classical guitar (CC0): nylon strings, one sample per note. Bossa comping (strum the '
          'chords a few ms apart), arpeggios, ballads. Range: E2-B5 for real parts. Sends: hall -14. Measured '
          '-18.0 LUFS (audition arpeggio).',
    audition={'notes': 'arp'}))

# --------------------------------------------------------------------------------------------- orchestra (VPO)

_VPO = 'samples/vpo-scripts-standard/'
_VPO_NOTE = ('Virtual Playing Orchestra 3 (Paul Battersby; samples from Sonatina Symphonic Orchestra, No Budget '
             'Orchestra, VSCO 2 CE, Univ. of Iowa MIS, Philharmonia; royalty-free; needs the packs '
             'vpo-scripts-standard and vpo-wav). Velocity picks the dynamics.')

for _name, _file, _level, _material, _hp_hz, _send, _desc in (
        ('strings', 'Strings/all-strings-SEC-sustain.sfz', -7.3, 'chord', 40, -8,
         'Full string section sustain (violins, violas, cellos, basses split by range): pads and chorales, 4-6 '
         'note voicings C2-C6.'),
        ('strings_staccato', 'Strings/all-strings-SEC-staccato.sfz', -7.0, 'stab', 40, -9,
         'Full string section staccato: ostinatos and rhythmic chords in 8ths and 16ths.'),
        ('strings_pizz', 'Strings/all-strings-SEC-pizzicato.sfz', -7.0, 'arp', 40, -9,
         'Full string section pizzicato: plucked accompaniment, walking lines, playful ostinatos.'),
        ('violins', 'Strings/1st-violin-SEC-sustain.sfz', -1.6, 'phrase', 150, -8,
         'First violin section sustain: soaring lines G3-E7. Other articulations: '
         'inst.sfz("samples/vpo-scripts-standard/Strings/1st-violin-SEC-KS-C2.sfz", articulation="staccato") '
         '(sfz.articulations() lists them).'),
        ('cellos', 'Strings/cello-SEC-sustain.sfz', -7.5, 'chord', 50, -8,
         'Cello section sustain: warm lines and the tenor voice of chords, C2-A5.'),
        ('basses', 'Strings/bass-SEC-sustain.sfz', -5.2, 'roots', 30, -10,
         'Double bass section sustain: the orchestral foundation, C1-G3 (sounding).'),
        ('flute', 'Woodwinds/flute-SOLO-sustain.sfz', -1.7, 'phrase', 200, -10,
         'Solo flute: melodies C4-C7.'),
        ('clarinet', 'Woodwinds/clarinet-SOLO-sustain.sfz', -3.0, 'phrase', 120, -10,
         'Solo clarinet (sounding pitch): melodies and inner voices D3-B6.'),
        ('oboe', 'Woodwinds/oboe-SOLO-sustain.sfz', -3.9, 'phrase', 180, -10,
         'Solo oboe: plaintive melodies Bb3-G6.'),
        ('french_horns', 'Brass/french-horn-SEC-sustain.sfz', -9.3, 'chord', 60, -8,
         'French horn section sustain: noble pads and heroic lines B1-F5.'),
        ('trumpet', 'Brass/trumpet-SOLO-sustain.sfz', -7.3, 'phrase', 150, -10,
         'Solo trumpet: fanfares and lines E3-C6.'),
        ('trombones', 'Brass/trombone-SEC-sustain.sfz', -9.1, 'chord', 60, -9,
         'Trombone section sustain: brass chords and bass lines E1-F5.'),
        ('harp', 'Strings/harp-sustain.sfz', -8.0, 'arp', 40, -10,
         'Concert harp: arpeggios, glissandi (fast scales), chords.'),
        ('timpani', 'Percussion/timpani-hit.sfz', 2.6, 'hit', 30, -10,
         'Timpani hits C2-C4: downbeat accents, rolls as repeated 1/32 notes.'),
        ('choir', 'Vocals/choir-FEMALE-sustain.sfz', -1.7, 'chord', 120, -8,
         'Female choir "ah" sustain: angelic pads and chorales G4-C6 (the samples: notes below G4 are silent).')):
    register(Patch(
        f'sampled/{_name}',
        instrument=_sfz(_VPO + _file, level=_level),
        fx=[_hp(_hp_hz)],
        sends={'hall': _send},
        notes=f'v1. {_desc} {_VPO_NOTE} Sends: hall {_send}. Measured -18.0 LUFS (audition {_material}).',
        audition={'notes': _material, 'pitch': 'A2', 'length': 2} if _material == 'hit' else {'notes': _material}))


# --------------------------------------------------------------------------------------------- played (realism)
# Keyswitched articulations in one instrument (clip.articulate('spiccato') -> keyswitches at compile), live dynamics
# ('dynamics' automation crossfades the recorded layers: articulation.expression), legato soloists (mono='legato').

_VSCO = 'samples/vsco2-ce/'
_VSCO_NOTE = 'VSCO 2 Community Edition (Versilian Studios, CC0).'
_PLAYED_NOTE = ('Automate \'dynamics\' (0..1) for crescendi and swells - the recorded layers crossfade while notes sound '
                '(layers=\'dynamics\': velocity only sets the level) and the tone opens - or let '
                'articulation.perform(track, line, at) write it with the articulations, vibrato and legato. Unmarked '
                'notes play the first articulation.')

register(Patch(
    'sampled/solo_violin',
    instrument=_multi({'sustain': _VSCO + 'SViolinVib.sfz', 'spiccato': _VSCO + 'SViolinSpic.sfz',
                       'pizzicato': _VSCO + 'SViolinPizz.sfz', 'tremolo': _VSCO + 'SViolinTrem.sfz'},
                      level=LEVELS['solo_violin'], mono='legato', layers='dynamics', dynrange=12, legatotime=70),
    fx=[_hp(180)],
    sends={'hall': -10},
    notes='v2. Solo violin, ' + _VSCO_NOTE + ' Articulations: sustain (vibrato), spiccato, pizzicato, tremolo '
          '(keyswitches C-1 .. D#-1, inserted by the compiler). A legato player (mono=\'legato\': overlapping notes '
          'are legato transitions - articulation.legato ties phrases; clip.glide(150) for portamento). Range: '
          'G3-C7. ' + _PLAYED_NOTE + ' Sends: hall -10. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}))

register(Patch(
    'sampled/solo_cello',
    instrument=_sfz('samples/sso/Sonatina Symphonic Orchestra/Strings - Performance/Cello Solo KS.sfz',
                    level=LEVELS['solo_cello'], mono='legato', legatotime=80),
    fx=[_hp(50)],
    sends={'hall': -10},
    notes='v2. Solo cello, Sonatina Symphonic Orchestra (Mattias Westlund, CC Sampling Plus 1.0): looped sustain, '
          'legato (library transitions), marcato, staccato, pizzicato, harmonics as live keyswitches (G6 .. D7, '
          'inserted by the compiler: clip.articulate(\'staccato\')); its mod-wheel dynamics (volume + a filter) '
          'play live from \'dynamics\' (automate 0..1; default 0.76). A legato player (mono=\'legato\'). Range: '
          'C2-C6. Sends: hall -10. Measured -18.0 LUFS (audition phrase).',
    audition={'notes': 'phrase'}))

for _name, _prefix, _range, _hp_hz in (('violin_section', 'ViolinEns', 'G3-D6', 150),
                                       ('viola_section', 'ViolaEns', 'C3-D6', 110),
                                       ('cello_section', 'CelloEns', 'C2-F5', 50),
                                       ('bass_section', 'Contrabass', 'C1-C4', 30)):
    _sus = 'ContrabassSusVB' if _prefix == 'Contrabass' else _prefix + 'SusVib'
    register(Patch(
        f'sampled/{_name}',
        instrument=_multi({'sustain': _VSCO + _sus + '.sfz', 'spiccato': _VSCO + _prefix + 'Spic.sfz',
                           'pizzicato': _VSCO + _prefix + 'Pizz.sfz', 'tremolo': _VSCO + _prefix + 'Trem.sfz'},
                          level=LEVELS[_name], layers='dynamics', xfspread=2, dynrange=16, dyntone=0.8),
        fx=[_hp(_hp_hz)],
        sends={'hall': -8},
        notes=f'v2. {_name.replace("_", " ").capitalize()}, ' + _VSCO_NOTE + ' Articulations: sustain (vibrato), '
              'spiccato, pizzicato, tremolo (keyswitches C-1 .. D#-1, inserted by the compiler). Range: ' + _range +
              '. ' + _PLAYED_NOTE + ' Chord swells: automate \'dynamics\' 0.1 -> 1 -> 0.1 over the chord. Sends: '
              'hall -8. Measured -18.0 LUFS (audition ' + ('roots' if _name == 'bass_section' else 'chord') + ').',
        audition={'notes': 'chord'} if _name != 'bass_section' else {'notes': 'roots'}))
