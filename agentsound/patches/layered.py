"""Layered leads and keys: several library sounds on one track through the engine's 'stack' instrument (inst.stack /
Patch.layered; docs/COMPOSE_API.md "Layered instruments"). One part, one set of notes, several instruments that each
do one job - the attack, the body, the sparkle, the swell - so a hook reads full and "produced" instead of a single
synth beeping (recipes/HUMAN_FEEDBACK.md: "no thin, beepy synth as the main hook").

  leads:     layered/piano_glass_lead layered/piano_saw_lead layered/brass_saw_lead layered/sax_synth_lead
             (the hero sax, layered/hero_sax, lives in patches/hero.py with its data HERO_SAX)
  keys:      layered/bell_piano layered/epiano_piano_split layered/piano_strings layered/piano_pad
             layered/pluck_piano layered/piano_organ
  orchestra: layered/strings_octaves layered/flute_clarinet layered/horn_trombone
  bass:      layered/synth_sub_bass

Every layer is a library patch (its instrument + its insert fx chain as the layer's fx; its gain_db folded into the
layer level), so a layer sounds exactly like the patch it names. Tweak one layer with patch.layer('<id>', level=-6)
or .but(**{'layers.<id>.<param>': v}) - a layer param (level, pan, transpose, fine, delay, keylo/keyhi, vello/velhi,
velfade ...), an effect of its chain ('layers.pad.fx.chorus.mix') or a param of its instrument ('layers.pad.cutoff');
automate them the same way ('instrument.layers.pad.level'). The sends are the whole stack's (the layers' own patch
sends are dropped: one reverb send per track).

Layers built on sampled/* patches need their sample packs (python -m agentsound samples fetch <id>), like those
patches; the pure synth stacks (synth_sub_bass) always work.

Level calibration: every patch at gain_db 0 lands at about -18 LUFS integrated (track node, dry) playing its audition
material, like the rest of the library; the measured value is in the notes. Version: see VERSION (bump it when a sound
changes audibly).
"""

from . import Patch, fx, inst, layer, register
# the libraries the layers come from (imported first: their patches must be registered before layer() reads them)
from . import sampled, sampled_synths, synthwave_drums_bass, synthwave_keys_pads, synthwave_leads_fx  # noqa: F401

VERSION = 2

# Stack patch levels (gain_db), audition-calibrated to -18.0 LUFS (python -m agentsound audition layered/<name>).
LEVELS = {
    'piano_glass_lead': -0.3, 'piano_saw_lead': 0.1, 'brass_saw_lead': -0.8, 'sax_synth_lead': 1.7, 'bell_piano': -0.5,
    'epiano_piano_split': -0.2, 'piano_strings': 1.2, 'piano_pad': 1.3, 'pluck_piano': -1.5, 'piano_organ': 1.2,
    'strings_octaves': -1.6, 'flute_clarinet': -1.2, 'horn_trombone': -1.1, 'synth_sub_bass': 1.6,
}


def _reg(name: str, *layers, notes: str, audition: str, sends: dict, fx_=(), **stack):
    register(Patch.layered(f'layered/{name}', *layers, fx=fx_, gain_db=LEVELS[name], sends=sends,
                           notes=f'v{VERSION}. {notes} Measured -18.0 LUFS (audition {audition}).',
                           audition={'notes': audition}, **stack))


# --------------------------------------------------------------------------------------------- leads

_reg('piano_glass_lead',
     layer('sampled/piano_lead', 'piano'),
     layer('synthwave/arp_glass', 'glass', transpose=12, level=-10, bend=False),
     layer('synthwave/warm_pad', 'pad', level=-11, delay=40, pedal=False),
     sends={'plate': -12, 'hall': -14},
     audition='phrase',
     notes='The 80s hook piano with a glass halo: sampled/piano_lead (the Salamander hook chain) + a DX glass layer '
           '(CELESTE, synthwave/arp_glass) an octave up at -10 dB (the FM sparkle over The Midnight / FM-84 piano '
           'hooks; it does not bend) + synthwave/warm_pad at -11 dB, 40 ms late, whose slow attack swells in under held '
           'notes (it ignores the sustain pedal, so it never smears chord changes). In the audition phrase the glass '
           'sits 12 LU and the pad 16 LU under the whole (they colour, the piano leads); layers uncorrelated (energy '
           'of the stack = the sum of the layers within 0.01 dB: no phasing). How to play: like sampled/piano_lead - '
           'the hook in C5-C7, octave-doubled right hand at ~80 %, velocities 85-115, re-struck notes and pedal steps; '
           'long notes bloom as the pad comes in. Tweak: .layer("glass", level=-6) (more sparkle), .layer("pad", '
           'level=-7) (a fuller sustain for slow ballad hooks), .layer("pad", mute=True) (a drier, punchier hook), '
           'instrument.pedal steps (piano + glass follow the pedal).')

_reg('piano_saw_lead',
     layer('sampled/piano_lead', 'piano'),
     layer('synthwave/supersaw_lead', 'saw', level=-8, pedal=False, **{'amp.attack': 0.03, 'cutoff': 3000},
           fx=[fx.eq({'peak3.freq': 3300, 'peak3.gain': -3.0, 'peak3.q': 0.9})]),
     sends={'plate': -12, 'hall': -12, 'echo': -16},
     audition='phrase',
     notes='The piano attack in front, a fat detuned supersaw sustaining under it (The Midnight "Sunset" / FM-84 '
           'hooks): sampled/piano_lead + synthwave/supersaw_lead at -8 dB with a softer attack (30 ms, so the hammer '
           'speaks first), the filter at 3 kHz and a -3 dB dip at 3.3 kHz (room for hats and snare: in a full mix the '
           'saw\'s presence otherwise masks the drums); the saw sits ~8.5 LU under the stack. The piano gives each note '
           'its edge and decay, the saw keeps long notes singing where a piano would die away. The saw follows the keys, '
           'not the sustain pedal (pedal steps ring the piano on; a pedalled saw would pile every hook note of a chord '
           'into a sustained cluster: +1.7 LU and flat note dynamics on the children-of-neon hook). How to play: '
           'melodies C5-C6 (the saw gets harsh above C7), velocities 90-115; unlike a plain piano, held notes and '
           'legato phrases work (the saw sustains). Tweak: .layer("saw", level=-5) (more synth), .but(**{"layers.saw.cutoff": 5000}) '
           '(brighter), automate instrument.layers.saw.level to push the saw in the last chorus.')

_reg('brass_saw_lead',
     layer('synthwave/brass_lead', 'brass'),
     layer('synthwave/dx_brass', 'fm', level=-7),
     layer('sampled/french_horns', 'horns', level=-7, delay=12),
     sends={'hall': -12},
     audition='phrase',
     notes='An 80s synth-brass lead with a real brass body: synthwave/brass_lead (VA saws with the filter swell) + '
           'synthwave/dx_brass (the FM BRASS 1 bite) at -7 dB + the sampled French horn section at -7 dB, 12 ms late '
           '(a section that breathes behind the synth attack: width and air, no audible flam); FM and horns each sit '
           '~11 LU under the stack. Heroic hooks and fanfares (Kavinsky, Carpenter Brut breaks, Stranger Things cues). '
           'Range: C4-C6. Velocity opens the brass; accent the downbeats. Tweak: .layer("horns", level=-3) (more '
           'orchestral), .layer("fm", level=-12) (smoother), .layer("horns", mute=True) (pure synth; the horn samples '
           'still load).')

_reg('sax_synth_lead',
     layer('sampled/tenor_sax', 'sax'),
     layer(inst.va(osc1__wave='square', osc1__pw=0.5, osc2__level=0.0, sub__level=0.0, filter__type='ladder',
                   cutoff=850, resonance=0.1, filter__drive=0.3, filter__keytrack=0.4, filter__env=0.6,
                   fenv__attack=0.05, fenv__decay=0.6, fenv__sustain=0.5, amp__attack=0.04, amp__decay=0.5,
                   amp__sustain=0.9, amp__release=0.2, amp__velocity=0.3, mode='legato', glide=0.05, hpf=45,
                   level=-16.0),
           'synth', transpose=-12, fx=[fx.chorus(mode='I', mix=0.3)]),
     sends={'hall': -12, 'echo': -18},
     audition='phrase',
     notes='The 80s sax solo glued into a synth mix: the sampled MTG tenor (legato player) + a soft mono synth an '
           'octave below, ~10 LU under the stack (a Juno-chorused square through an 850 Hz ladder, 40 ms attack, 50 ms '
           'glide: a body under the reed, not a second voice). A square, not a saw: an octave-down square has only odd '
           'harmonics (f/2, 3f/2, 5f/2 ...), none of them on the sax\'s partials, so the layers cannot phase against '
           'each other (measured correlation 0.000). Sax breaks in synthwave / retro pop (Timecop1983, "Careless '
           'Whisper" moods). Range: the sax\'s D#3-E5 (sounding); legato phrases (overlapping notes = legato '
           'transitions on both layers); vibrato on long notes: automate instrument.layers.sax.vibrato (the '
           'articulation helpers that write instrument.vibrato need a plain sampled/tenor_sax track). Tweak: '
           '.layer("synth", level=4) (more synth), .but(**{"layers.synth.cutoff": 1500}) (a brighter body).')

# --------------------------------------------------------------------------------------------- keys

_reg('bell_piano',
     layer('sampled/grand_piano', 'piano'),
     layer('synthwave/dx_bells', 'bell', level=-12, bend=False),
     sends={'plate': -12, 'hall': -14},
     audition='chord',
     notes='The DX "bell piano" of 80s ballads: the Salamander grand + the DX7 TUB BELLS (synthwave/dx_bells) in '
           'unison at -12 dB, ~10 LU under the stack: the bell partials ring on over the piano\'s decay. Chords C3-C5, '
           'arpeggios and bell-like melodies C4-C6. The bell layer does not bend. Tweak: .layer("bell", transpose=12, '
           'level=-15) (a higher, glassier shimmer), .layer("bell", level=-8) (more bell), instrument.pedal steps.')

_reg('epiano_piano_split',
     layer('sampled/rhodes', 'rhodes', vel=(1, 95), velfade=35, level=3),
     layer('sampled/grand_piano', 'grand', vel=(60, 127), velfade=35),
     sends={'plate': -14, 'hall': -16},
     audition='chord',
     notes='A velocity-crossfaded keyboard: soft playing is a Rhodes (jRhodes3d), hard playing a grand piano (the '
           'Salamander), with an equal-power crossfade over velocities 60-95 (both layers at -3 dB at 78); the Rhodes '
           'is raised 3 dB so both instruments meet at the same level inside the fade (a velocity sweep on C4 rises '
           'from -47 dB at velocity 20 to -11 dB at 127 without a jump at the crossfade; two sampled keyboards on one '
           'key keep a fixed phase relation, so single notes inside the fade vary about +-1.5 dB - like the '
           'Salamander\'s own velocity-layer steps). Ballad comping that blooms from a warm e-piano into piano bark on '
           'the accents, neo-soul, lo-fi. Velocities 40-65 play the Rhodes, 95-120 the grand, the range between blends '
           'them. Range: A0-C8. Tweak: .but(**{"layers.grand.vello": 75, "layers.rhodes.velhi": 110}) (move the '
           'crossfade up), pedal steps. License: the Rhodes pack is CC-BY-NC (non-commercial); a free version swaps the '
           'soft layer: .but(layers=[layer("synthwave/epiano", "rhodes", vel=(1, 95), velfade=35), '
           'layer("sampled/grand_piano", "grand", vel=(60, 127), velfade=35)]).')

_reg('piano_strings',
     layer('sampled/grand_piano', 'piano'),
     layer('sampled/strings', 'strings', level=-9, delay=60, pedal=False),
     sends={'hall': -10},
     audition='chord',
     notes='Piano with a string section behind it (power ballads, film cues, pop-piano choruses): the Salamander '
           'grand + the full VPO string section at -9 dB (~8 LU under the stack), 60 ms late so the hammer leads and '
           'the strings swell in under it; the strings ignore the sustain pedal (they follow the keys while the piano '
           'rings on). Chords C3-C5 with a melody on top; the strings sound as long as the keys are held, so hold chords '
           'through the bar. Tweak: .layer("strings", level=-5) (a lusher bed), .layer("strings", keylo=60) (strings '
           'only on the right hand), automate instrument.layers.strings.level to bring the section in for the last '
           'chorus.')

_reg('piano_pad',
     layer('sampled/grand_piano', 'piano'),
     layer('synthwave/dream_pad', 'pad', level=-10, pedal=False),
     sends={'hall': -10},
     audition='chord',
     notes='Piano over a slow dreamy pad (dreamwave / chillsynth ballads, ambient intros): the Salamander grand + '
           'synthwave/dream_pad at -10 dB, ~9 LU under the stack (its 1.8 s attack blooms under held chords, the '
           'breathing filter keeps it moving). Chords C3-C5, held a bar or two; the pad ignores the pedal. Tweak: '
           '.layer("pad", level=-6) (more pad), .layer("pad", transpose=12) (a higher halo), '
           '.but(**{"layers.pad.cutoff": 3000}) (brighter).')

_reg('pluck_piano',
     layer('synthwave/arp_pluck', 'pluck'),
     layer('sampled/grand_piano', 'piano', level=-7, cutoff=9000),
     sends={'echo': -12, 'hall': -14},
     audition='arp',
     notes='A pop / future-bass pluck with a real piano under it: synthwave/arp_pluck (the filter-snap saw) + the '
           'Salamander grand at -7 dB (~5 LU under the stack; the piano adds a hammer transient and the natural decay '
           'the synth pluck lacks). 16th arpeggios, offbeat chords and top-line hooks C4-C6. Tweak: .layer("piano", '
           'level=-3) (more piano), .but(**{"layers.pluck.cutoff": 900}) (a brighter snap), .but(pedal=1) (a ringing '
           'piano under the pluck).')

_reg('piano_organ',
     layer('sampled/grand_piano', 'piano'),
     layer('synthwave/organ', 'organ', level=-10, pedal=False),
     sends={'plate': -12, 'hall': -16},
     audition='chord',
     notes='Rock / gospel keys: the Salamander grand doubled by a drawbar organ (synthwave/organ: 8\' + fifth + sub, '
           'tremolo) at -10 dB, ~9 LU under the stack - the piano hits, the organ holds the chord (the "piano + B3" of '
           'rock ballads, heartland rock, gospel pop). Chords C3-C5; the organ ignores the pedal (it stops with the '
           'keys). Tweak: .layer("organ", level=-6) (more organ), .layer("organ", keylo=55) (organ only on the right '
           'hand).')

# --------------------------------------------------------------------------------------------- orchestra

_reg('strings_octaves',
     layer('sampled/violins', 'violins'),
     layer('sampled/cellos', 'cellos', transpose=-12),
     sends={'hall': -8},
     audition='phrase',
     notes='The orchestral octave doubling: the first violins on the melody + the cello section an octave below '
           '(both at their calibrated level; the cellos read ~7 LU under the stack because loudness weighting hears '
           'less of the low octave) - the film-score line: warmth under the violins\' shine, one track, one set of '
           'notes. Melodies G4-E6 (the cellos then sound G3-E5). Tweak: .layer("cellos", level=3) (a darker, heavier '
           'line), .layer("cellos", transpose=-24) (two octaves down: a bass under the tune).')

_reg('flute_clarinet',
     layer('sampled/flute', 'flute'),
     layer('sampled/clarinet', 'clarinet', level=-4),
     sends={'hall': -10},
     audition='phrase',
     notes='The classic woodwind unison blend: solo flute + solo clarinet at -4 dB (~5.5 LU under the stack) on the '
           'same line - the flute\'s air on top, the clarinet\'s hollow body under it: a rounder, more singing line than '
           'either alone. Melodies F4-C6 (both in range). Tweak: .layer("clarinet", transpose=-12) (the clarinet an '
           'octave below), .layer("clarinet", level=0) (clarinet-led).')

_reg('horn_trombone',
     layer('sampled/french_horns', 'horns'),
     layer('sampled/trombones', 'trombones', level=-5),
     sends={'hall': -8},
     audition='chord',
     notes='A brass section blend: the French horn section + trombones at -5 dB in unison (~6 LU under the stack; '
           'horns round and noble, trombones add edge and weight). Chorales, pads and heroic unisons B2-F5. Tweak: '
           '.layer("trombones", transpose=-12) (trombones an octave below: a heavier bottom), .layer("trombones", '
           'level=0) (more bite).')

# --------------------------------------------------------------------------------------------- bass

_reg('synth_sub_bass',
     layer('synthwave/moog_bass', 'bass', fx=[fx.eq({'hp.freq': 90, 'hp.slope': 24})]),
     layer('synthwave/sub_bass', 'sub', level=-2, cutoff=120),
     sends={},
     audition='bass',
     notes='A bass with a separate, clean sub: synthwave/moog_bass (ladder growl) high-passed at 90 Hz (24 dB/oct) + '
           'a sine sub (synthwave/sub_bass, low-passed at 120 Hz) at -2 dB on the same notes: the growl stays in the '
           'mids, the sub stays solid and mono underneath, and the crossover keeps the two fundamentals apart (layer '
           'correlation -0.06: no audible phase fight). Both layers are mono legato. Lines E1-E3. Tweak: .layer("sub", '
           'level=2) (more weight), .but(**{"layers.bass.cutoff": 900}) (a brighter growl), .layer("sub", '
           'transpose=-12) (an octave-down sub under high lines).')
