"""General MIDI sound library from the SoundFont GeneralUser GS (instrument 'sf2'): real pianos, strings, choirs,
orchestra hits, guitars, basses and brass as first-class patches. They run through fx, sends, automation and
modulators exactly like the synth patches.

  gm/grand_piano gm/piano_lead gm/strings gm/choir_aahs gm/orchestra_hit gm/warm_pad gm/fretless gm/nylon_guitar
  gm/music_box gm/synth_strings gm/brass_section gm/epiano

Any other preset of the font: inst.sf2('Name') or inst.sf2(bank=..., program=...); list them with
`python -m agentsound sf2 [search]`. Level calibration: every patch at gain_db 0 lands at about -18 LUFS
integrated (track node, dry) playing its audition material, like the synth library; the calibration lives in the
sf2 `level` param. The patches are voiced for big, wide productions: extra stereo width from the font's own
panning (`width`), fx that widen mono presets (a mono-compatible `dimension`, chorus / ensemble + width), and
reverb sends hot enough that the hall return sits ~8-12 LU under the dry part (audible space, not a dry demo).
Measured with `python -m agentsound audition <patch>` (width = side/mid energy of the dry track).

v2 (lush pass): most GM presets are mono or panned by key, so in chord registers they read 0-18 % wide; they now
carry a Dimension-D side layer (modes 1-2, the mono sum stays the dry sample) and, where the font pans, a wider
`width`: piano ~30 %, strings/choir ~55 %, pads ~70 %, guitar/music box/brass 25-50 %. The fretless bass stays mono.
Version: see VERSION (bump it when a sound changes audibly).
"""

from . import Patch, fx, inst, register

VERSION = 2


def _hp(freq):
    """Steep (24 dB/oct) clean-up high-pass."""
    return fx.eq({'hp.freq': freq, 'hp.slope': 24})


def _dim(mode=1, **kw):
    """Dimension-D style width: adds a pure side signal above 150 Hz (the mono sum stays the dry signal)."""
    return fx.dimension(mode=mode, **kw)


register(Patch(
    'gm/grand_piano',
    instrument=inst.sf2('Grand Piano', cutoff=12, width=1.6, level=2.9),
    fx=[fx.eq({'hp.freq': 40, 'hp.slope': 24, 'peak1.freq': 300, 'peak1.gain': -1.5, 'peak1.q': 0.9,
               'high.freq': 8000, 'high.gain': 2.0}),
        _dim(2, width=1.2)],
    sends={'hall': -9},
    notes='v2. GeneralUser GS "Grand Piano": stereo concert grand (bass left, treble right), 8 velocity layers; the '
          'font\'s filter envelope makes hard notes bright and lets the sustain mellow out like a real string. Opened '
          'up an octave (cutoff +12), key spread widened (width 1.6), -1.5 dB at 300 Hz, +2 dB air shelf at 8 kHz. '
          'Range: A0-C8; chords C3-C5, melodies C4-C6. Use: ballads, lo-fi, cinematic, pop keys. For a natural (jazz '
          '/ classical) piano drop the dimension: .but_fx("dimension", mix=0). Tweak: cutoff 0 (the font\'s mellow '
          'original) .. +24, brightness -0.3..0.3, release 1.5-3 (longer tails), velsens 0.6 (more even). Sends: '
          'hall -9 (-6 for a big ballad). Measured -18.0 LUFS (audition chords). Lush pass (v2): + dimension mode 2 '
          '(width 1.2): the font\'s key panning spreads only across the whole keyboard, so chords in C3-C5 read 1 % '
          'wide; now ~31 % with the dry piano intact in mono - the 80s "big ballad piano".',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/piano_lead',
    instrument=inst.sf2('Bright Grand Piano', cutoff=12, width=0.0, polyphony=128, level=8.6),
    fx=[fx.eq({'hp.freq': 210, 'hp.slope': 24, 'peak1.freq': 420, 'peak1.gain': -3.0, 'peak1.q': 0.9,
               'peak3.freq': 3600, 'peak3.gain': 3.0, 'peak3.q': 0.8, 'high.freq': 9500, 'high.gain': 3.0}),
        fx.compressor(threshold=-13, ratio=3.0, attack=4, release=150, knee=8),
        fx.chorus(mode='I', mix=0.22),
        _dim(2, width=0.8)],
    sends={'plate': -12, 'hall': -14},
    notes='v1. GeneralUser GS "Bright Grand Piano" voiced as a melody piano: the fallback of sampled/piano_lead '
          '(same chain) when the salamander-grand pack is missing. Filter opened an octave (cutoff +12), key panning '
          'summed to a mono centre (width 0), high-pass 210 Hz, -3 dB at 420 Hz, +3 dB at 3.6 kHz and +3 dB air '
          'shelf at 9.5 kHz, compressor (peak, threshold -13, 3:1, 4 / 150 ms) evening the attacks, Juno chorus I '
          '(mix 0.22) + dimension mode 2 (width 0.8): ~28 % wide, correlation ~0.6. Range: C5-C7 hooks. Play: '
          'octave-doubled right hand (clip.octave_double(-12, vel=0.8)), velocities 90-115, repeated / rhythmic notes '
          '(a piano decays), pedal steps (instrument.pedal) for legato lines; double with synthwave/epiano_bright at '
          '-8..-12 dB for sparkle. Sends: plate -12, hall -14. Measured -18.0 LUFS (audition melody).',
    audition={'notes': 'phrase'}))

register(Patch(
    'gm/epiano',
    instrument=inst.sf2('Tine Electric Piano', width=1.2, level=2.0),
    fx=[fx.eq({'hp.freq': 60, 'hp.slope': 24, 'peak1.freq': 300, 'peak1.gain': -1.5, 'peak1.q': 0.9}),
        fx.chorus(mode='II', mix=0.4),
        _dim(1)],
    sends={'plate': -12, 'hall': -18},
    notes='v1. GeneralUser GS "Tine Electric Piano": a Rhodes-style tine e-piano, chorused (Juno chorus II 0.4 + '
          'dimension mode 1) like the 80s ballad keys. The DX7-free stand-in for synthwave/epiano (that one needs the '
          'DX7 ROM banks, assets/dx7/README.md); the song template uses it so a fresh clone builds. Range: C3-C6; '
          'comp chords C4-C5. Velocity 70-90 = round, 110+ = bark. Tweak: chorus mix 0.2-0.6, velsens 0.6-1. '
          'Sends: plate -12, hall -18. Measured -18.0 LUFS (audition chords).',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/strings',
    instrument=inst.sf2('Slow Strings', width=1.8, level=-2.5),
    fx=[_hp(60), _dim(2)],
    sends={'hall': -6},
    notes='v2. GeneralUser GS "Slow Strings": a warm, slowly bowed string section (soft notes bow in slower and '
          'start later in the sample, long release). Range: C2-C7; pads of 3-5 notes C3-C5, lines above. Use: '
          'cinematic beds, ballad lifts, synthwave string layer (with synthwave/jupiter_strings). Tweak: attack '
          '0.5-4 (faster / slower swells), release 1-3, cutoff -12 (darker, muted), or inst.sf2("Fast Strings") for '
          'spiccato / rhythmic parts. Sends: hall -6 (-4 for a drenched film score). Measured -18.0 LUFS (audition '
          'chords). Lush pass (v2): width 1.4 -> 1.8, + dimension mode 2: ~52 % wide, v1 15 %.',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/choir_aahs',
    instrument=inst.sf2('Concert Choir', width=1.8, attack=1.5, level=-1.0),
    fx=[_hp(90), _dim(2)],
    sends={'hall': -6},
    notes='v2. GeneralUser GS "Concert Choir" (GM Choir Aahs): mixed choir on "aah", attack slowed x1.5. Range: '
          'C3-C6 (A2 lowest for basses); 3-4 note chords. Use: epic / cinematic swells, 80s power ballads, darksynth '
          'drama, an octave over strings. Tweak: attack 1-4, release 1-2, cutoff -12 (distant), or inst.sf2("Voice '
          'Oohs") for a softer "ooh". Sends: hall -6 (-4 cathedral). Measured -18.0 LUFS (audition chords). Lush '
          'pass (v2): width 1.3 -> 1.8, + dimension mode 2: ~59 % wide, v1 18 %.',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/orchestra_hit',
    instrument=inst.sf2('Orchestra Hit', width=0.8, level=1.5),
    fx=[_hp(80)],
    sends={'hall': -8},
    notes='v1. GeneralUser GS "Orchestra Hit": the Fairlight / 80s stab of a whole orchestra (two different hits '
          'panned left / right; width 0.8 keeps it mono-safe, ~53 % wide). Play single notes or octaves on accents '
          '(C4-C5 is the classic register), short notes (1/8 - 1/4). Use: 80s pop / freestyle / synthwave '
          'accents, dramatic downbeats, hip-hop stabs. Tweak: transpose, cutoff -12 (lo-fi), release 0.5 '
          '(tighter). Sends: hall -8 (the tail is part of the sound). Measured -18.0 LUFS (audition hits on C4, '
          '1/8 notes).',
    audition={'notes': 'hit', 'pitch': 'C4', 'length': 0.5}))

register(Patch(
    'gm/warm_pad',
    instrument=inst.sf2('Warm Pad', level=-2.0),
    fx=[fx.chorus(mode='II', mix=0.55), _hp(90), fx.width(width=1.3, monobass=150), _dim(1)],
    sends={'hall': -6},
    notes='v2. GeneralUser GS "Warm Pad" (GM 89): soft, round analog-style pad; the mono preset is widened by Juno '
          'chorus II, width 1.3 (below 150 Hz stays mono) and a dimension side layer. Range: C3-C5 chords. Use: beds '
          'for ballads, chillwave, dreamwave, cinematic underscore. Tweak: attack 2-4 (slower), release 2, cutoff '
          '-12..+12, or inst.sf2("Halo Pad") / inst.sf2("Polysynth") for other GM pads. Sends: hall -6. Measured '
          '-18.0 LUFS (audition chords). Lush pass (v2): chorus II 0.4 -> 0.55, + dimension mode 1: ~68 % wide, '
          'correlation ~0.2; v1 30 %.',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/fretless',
    instrument=inst.sf2('Fretless Bass', level=7.9),
    fx=[fx.eq({'hp.freq': 32, 'hp.slope': 24, 'peak1.freq': 800, 'peak1.gain': 1.5, 'peak1.q': 1.0}),
        fx.compressor(threshold=-24, ratio=3, attack=15, release=150, makeup=4.9)],
    notes='v1. GeneralUser GS "Fretless Bass": singing, "mwah" fretless electric bass (Pino Palladino / Jaco '
          'flavour), 32 Hz rumble cut, +1.5 dB at 800 Hz for growl, 3:1 compression (+4.9 dB makeup) for an even '
          'line. Mono and dry (keep the low end centred). Range: E1-G3. Use: smooth jazz, city pop, 80s ballads, '
          'sophisti-pop; slides with "instrument.pitchbend" automation (+-2 st). Tweak: cutoff -12 (rounder), '
          'release 0.5 (shorter), inst.sf2("Finger Bass") / inst.sf2("Pick Bass") for other electric basses. '
          'Measured -18.0 LUFS (audition 8th-note bass line).',
    audition={'notes': 'bass'}))

register(Patch(
    'gm/nylon_guitar',
    instrument=inst.sf2('Nylon Guitar', width=1.3, level=2.5),
    fx=[_hp(70), _dim(2)],
    sends={'hall': -10},
    notes='v2. GeneralUser GS "Nylon Guitar": classical / bossa nylon-string guitar, velocity-sensitive. Range: '
          'E2-B5; arpeggios and broken chords (humanized velocities sound best). Use: bossa, lo-fi, ballads, latin, '
          'cinematic. Tweak: release 1.5 (let notes ring), cutoff +5 (brighter pick), inst.sf2("Steel Guitar") for '
          'steel strings, .but_fx("dimension", mix=0) for the plain mono guitar. Sends: hall -10. Measured -18.0 '
          'LUFS (audition 16th arpeggio). Lush pass (v2): + dimension mode 2: ~26 % wide, v1 mono.',
    audition={'notes': 'arp'}))

register(Patch(
    'gm/music_box',
    instrument=inst.sf2('Music Box', width=1.8, level=7.9),
    fx=[_hp(200), _dim(2)],
    sends={'hall': -6, 'echo': -14},
    notes='v2. GeneralUser GS "Music Box": tiny comb-and-cylinder chimes with a long ring. Range: C5-C8 (an octave '
          'or two above the melody). Use: lullaby / dreamy intros, lo-fi toppers, cinematic wonder; layer over pads. '
          'Tweak: release 2 (longer ring), brightness -0.3 (softer). Sends: hall -6, echo -14 (the dotted-8th '
          'repeats sparkle). Measured -18.0 LUFS (audition phrase). Lush pass (v2): width 1.3 -> 1.8, + dimension '
          'mode 2 (~47 % wide, v1 10 %), + echo -14.',
    audition={'notes': 'phrase'}))

register(Patch(
    'gm/synth_strings',
    instrument=inst.sf2('Synth Strings 1', level=-1.3),
    fx=[fx.ensemble(mix=0.65), _hp(100), _dim(2)],
    sends={'hall': -7},
    notes='v2. GeneralUser GS "Synth Strings 1": 80s polysynth strings (Oberheim / Juno style), made wide by a '
          'Solina-style ensemble and a dimension side layer. Range: C3-C6 chords. Use: synthwave / 80s pop string '
          'pads, layered with gm/strings for a hybrid section. Tweak: attack 2 (slower), cutoff -12..+12, ensemble '
          'mix 0.3-0.8 (but_fx("ensemble", mix=...)). Sends: hall -7. Measured -18.0 LUFS (audition chords). Lush '
          'pass (v2): ensemble 0.5 -> 0.65, + dimension mode 2: ~48 % wide, v1 18 %.',
    audition={'notes': 'chord'}))

register(Patch(
    'gm/brass_section',
    instrument=inst.sf2('Brass Section', width=1.8, level=-0.8),
    fx=[_hp(80), _dim(2)],
    sends={'hall': -9},
    notes='v2. GeneralUser GS "Brass Section": trumpets + trombones with velocity-controlled brightness. Range: '
          'F2-C6; punchy chord stabs (1/8, 1/4) and swells (long notes, velocity 60-90). Use: funk / disco hits, 80s '
          'pop, cinematic fanfares. Tweak: velsens 0.6 (more even), cutoff -7 (mellow horns), attack 2 (swells), '
          'inst.sf2("Synth Brass 1") for the OB-X / "Jump" brass. Sends: hall -9. Measured -18.0 LUFS (audition '
          'stabs; peaks ~-3 dBFS). Lush pass (v2): width 1.3 -> 1.8, + dimension mode 2: ~51 % wide, v1 13 %: a '
          'section, not one horn.',
    audition={'notes': 'stab'}))
