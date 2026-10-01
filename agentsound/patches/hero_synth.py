"""Hero synth leads: the synthwave / 80s hook lead that stands in front of the mix like on a hit record (The Midnight,
FM-84, Kavinsky, Timecop1983, Gunship, 80s pop leads).

  hero/synth_lead       the fat, singing saw lead (a two-saw voice + an octave-down square body + a supersaw halo)
  hero/synth_piano      the FM-84 / The Midnight hybrid: the bright melody piano's attack over a sustaining saw
  hero/darksynth_lead   the darker, grittier hero: a hard-sync saw over a driven saw body, tube drive

They are the 'synth', 'piano_synth' and 'darksynth' presets of the hero wrapper (agentsound.heroes; unified names
hero/synth, hero/piano_synth, hero/darksynth = the same sound + the 'air' stage): hero(s.track('lead',
'hero/synth_lead'), bed=[...], competitors=[...], genre='synthwave') applies the mix rules below in one logged call.

Why (recipes/HUMAN_FEEDBACK.md): thin, beepy synth hooks were the most common complaint ("piepsig", "lahm"); a
synth lead that stays needs body below 1 kHz, movement (vibrato, glide, filter), a doubling layer and real note
dynamics - and it must read in front of the bed. A hero patch is the sound AND its production chain AND the rules to
mix and play it:

  1. source: layered through the engine's 'stack' (inst.stack / Patch.layered): one voice leads, the others (an
     octave body, a halo, a sustain) sit 9-10 dB under it; layers of different waveforms / instruments, so they do not
     phase (an octave-down SQUARE has only odd harmonics: none lands on the lead's partials). Every synth layer has
     amp.velocity 1.0 and velocity -> cutoff (softer = quieter AND darker: ~8 dB from velocity 64 to 112 on one note),
     re-attacks every note (mono + 40 ms portamento: the singing slide), and ignores the sustain pedal;
  2. chain (after the layers are summed): EQ (-3 dB low-mid dip at 420 Hz, -3..-4.5 dB around 3.3-3.6 kHz so
     the hats and the snare keep their presence, +2.5 dB air shelf at 9.5 kHz), a slow RMS compressor (2:1, 25 ms
     attack: the attack speaks, the note blooms, only the loudest notes are touched - the note dynamics survive), 15 ips
     tape, Juno chorus I, a micro-pitch stereo double (smooth, +-9 ct: a ~34 % wide halo around a mono-solid centre);
     space on the sends: plate -12 (the vocal plate), the dotted-8th echo -11 (the repeats fill the gaps; throw a last
     note: automate send.echo to -4 on it), hall -14;
  3. mix rules (docs in each patch's notes): the hero sits about where a piano hook sat, +1..1.5 dB in sections with a
     thick bed, -0.5 dB where a single pad is the bed; the bed (pads, choir, strings) >= 2-3 dB under it (the report's
     'bed vs lead'); carve, do not push: key the bed to the
     hero (s.sidechain(pad, choir, strings, key=lead, threshold=-34, depth=2.5, attack=15, hold=60, release=260)) and
     dip competitors' presence (pads / arps -2 dB at 1-3 kHz) before raising the hero into the mid / presence limits;
     a hook below C5 puts the hero's fundamentals in the low mids: dip the pad / keys -2 dB at 400 Hz while it plays.
     Validated in songs/children-of-neon and songs/_bands/outrun (scratch copies; recipes/synthwave.md "Hero sounds");
  4. play it (perform() below): velocities from the line (humanize.touch arcs: lo 60-70, hi 105-118), slightly
     detached notes so every note re-attacks, long notes where the delayed vibrato should bloom, hooks C5-C6.

Level calibration: every patch at gain_db 0 lands at -18.0 LUFS integrated (track node, dry) playing its audition
phrase (python -m agentsound audition hero/<name>), like the rest of the library (LEVELS). hero/synth_piano needs the
Salamander pack (sampled/piano_lead: python -m agentsound samples fetch salamander-grand); the pure synth heroes always
work. Version: VERSION (bump it when a sound changes audibly).
"""

from __future__ import annotations

from .. import heroes
from ..vamod import env, lfo
from . import inst, layer
from . import sampled, synthwave_leads_fx  # noqa: F401  (the layers' source patches must be registered first)

VERSION = 2  # v2: hero/darksynth_lead's sync layer without the patch's own micro-pitch double (it sat before the tube
#              drive, which then ground the doubled voices together; the chain's 'double' after the drive is the width)

# Stack patch levels (gain_db), audition-calibrated to -18.0 LUFS.
LEVELS = {'synth_lead': 1.9, 'synth_piano': -1.5, 'darksynth_lead': 4.6}


def _voice(**kw):
    """The hero voice: two saws 7 ct apart, 3-voice unison (thick, not a smeared supersaw),
    oscillators restarted per note (every attack alike: the dynamics come from velocity), a driven ladder whose
    cutoff follows velocity (1.6 oct darker at velocity 0) and only gently the key (high notes do not turn shrill), a
    sung attack (filter swell + a -22 ct pitch scoop over 70 ms), mono with a 40 ms glide and a delayed vibrato
    (5.3 Hz, 16 ct, after 0.32 s: only long notes sing)."""
    p = dict(osc1__wave='saw', osc2__wave='saw', osc2__level=0.85, osc2__fine=7, sub__level=0.0,
             unison=3, unison__detune=0.22, unison__spread=0.35, drift__pitch=3,
             filter__type='ladder', cutoff=1900, resonance=0.18, filter__drive=0.35, filter__keytrack=0.3,
             filter__env=1.3, filter__velocity=1.6, fenv__attack=0.03, fenv__decay=0.8, fenv__sustain=0.5,
             fenv__release=0.35,
             amp__attack=0.006, amp__decay=0.9, amp__sustain=0.88, amp__release=0.32, amp__velocity=1.0,
             mode='mono', glide=0.04, hpf=80, osc__retrig='on',
             mods=[lfo('sine', hz=5.3, delay=0.32, fade=0.55, id='vib') >> ('pitch', 16),
                   env(a=0.0, d=0.07, id='scoop') >> ('pitch', -22)])
    p.update(kw)
    return inst.va(**p)


def _sync_dry():
    """synthwave/sync_lead without its micro-pitch double: the darksynth hero drives the layers (tube drive, before
    its eq) and doubles after that - a doubler in front of the drive would be ground into it."""
    from . import get
    p = get('synthwave/sync_lead')
    return p.with_fx(*[f for f in p.fx if f.type != 'microshift'], replace=True)


def _octave(**kw):
    """The body an octave down: a square (odd harmonics only, none on the lead's partials: no phasing) through a warm
    ladder, mono with the same glide, full velocity response."""
    p = dict(osc1__wave='square', osc1__pw=0.5, osc2__level=0.0, sub__level=0.0, drift__pitch=2,
             filter__type='ladder', cutoff=950, resonance=0.1, filter__drive=0.3, filter__keytrack=0.4,
             filter__env=0.8, filter__velocity=1.0, fenv__attack=0.03, fenv__decay=0.6, fenv__sustain=0.5,
             amp__attack=0.01, amp__decay=0.8, amp__sustain=0.9, amp__release=0.3, amp__velocity=1.0,
             mode='mono', glide=0.04, hpf=60)
    p.update(kw)
    return inst.va(**p)


def perform(line, *, lo: float = 64, hi: float = 112, tie: str = 'none', leap: int = 4, overlap: float = 0.03,
            gate: float = 0.9, double=None, double_vel: float = 0.72):
    """Play a melody on a hero synth like a keyboard soloist (the matching player; a Clip in, a Clip out):

      - velocities from the line (humanize.touch: an arc to each phrase's goal note, the summit loudest, passing notes
        and short releases lighter) - the hero patches turn velocity into level AND brightness, so this is the whole
        expression (lo 55-70 / hi 100-118; a first statement softer, the last chorus hottest);
      - notes followed closely by the next are played slightly detached (x gate): the mono hero voices re-attack
        every note (so every velocity speaks) and glide into it (40 ms portamento: the singing slide), and the delayed
        vibrato blooms only on the long notes. tie='leaps': notes leaping `leap`+ semitones into the next are held
        into it, tie='all': held through each phrase - for hero/synth_piano, whose poly saw then sustains from note
        to note (a legato hook), and for slow ballad lines;
      - double=12 / -12 / [12, -12] adds octave copies at double_vel (for hero/synth_piano: a pianist's octaves; the
        mono hero leads carry their own octave layer, leave it None there).
    """
    from ..humanize import touch
    from ..patterns import Clip
    if tie not in ('leaps', 'all', 'none'):
        raise ValueError(f"perform: tie must be 'leaps', 'all' or 'none', got {tie!r}")
    c = touch(line, lo, hi)
    notes = sorted(c, key=lambda n: (n.start, -n.pitch))
    out = []
    for i, n in enumerate(notes):
        nxt = next((m for m in notes[i + 1:] if m.start > n.start + 1e-6), None)
        near = nxt is not None and nxt.start - (n.start + n.dur) < 0.25 + 1e-6
        if near and tie != 'none' and (tie == 'all' or abs(nxt.pitch - n.pitch) >= leap):
            n = n._replace(dur=nxt.start - n.start + overlap)
        elif near:
            n = n._replace(dur=max(0.05, n.dur * gate))
        out.append(n)
    c = Clip._raw(out, c.length)
    if double is not None:
        c = c.octave_double(double, vel=double_vel)
    return c


def _loose(piano):
    """The melody piano's compressor loosened (-13 dB 3:1 -> -10 dB 2:1, attack 4 -> 10 ms): the patch's own setting
    takes 4-5 dB off every attack and flattens the accents (children-of-neon: note dynamics 2.6 -> 3.7 dB per phrase)."""
    for k, v in (('threshold', -10), ('ratio', 2.0), ('attack', 10)):
        piano.set(f'fx.compressor.{k}', v)
    return piano


# the synth heroes' mix / space / playing rules for heroes.hero() (validated in children-of-neon / _bands/outrun)
_SYNTH_MIX = {'duck': 2.5, 'duck_threshold': -34.0, 'duck_attack': 15.0, 'duck_hold': 60.0, 'duck_release': 260.0,
              'carve_db': 2.0, 'carve_freq': 1800.0, 'carve_q': 0.6, 'ride_db': 1.0, 'dip_db': -2.0,
              'dip_freq': 1800.0, 'dip_q': 0.7}


def _reg(name, *layers, notes, audition='phrase', sends, stages, preset, family='synth', order=None, play=None,
         **kw):
    """A synth hero as a heroes preset (the layers are its own source) and its library patch hero/<name>."""
    heroes.define(preset, family=family, source=lambda: [x.copy() for x in layers], chain=stages,
                  order=order or heroes.ORDER, named=False, gain_db=LEVELS[name], sends=sends,
                  notes=f'v{VERSION}. {notes} Measured -18.0 LUFS (audition {audition}).',
                  audition={'notes': audition}, patch=f'hero/{name}', mix=dict(_SYNTH_MIX),
                  space={'echo': sends['echo'], 'throw': -4.0}, play=play or {'player': 'synth', 'vel': (64, 112)},
                  **kw)
    heroes.register(preset)


_MIX = ('Mix: about as loud as a piano hook would sit, +1..1.5 dB in the sections with a thick bed (choir, strings), '
        '-0.5 dB where one pad is the whole bed (more than 6 dB over it reads thin_bed); the bed >= 2-3 dB under it '
        '(report: "bed vs lead") - carve first: s.sidechain(<bed tracks>, key=<hero>, threshold=-34, '
        'depth=2.5, attack=15, hold=60, release=260), pads / arps -2 dB at 1-3 kHz; then the fader. Echo throws: '
        'automate send.echo to -4 on the last note of a phrase. Below C5 the hero fundamentals fill the low mids: in a '
        'mix already near the low-mid limit take -2 dB at 400 Hz off the pad (while the hero plays) and the keys. ')

_reg('synth_lead',
     layer(_voice(), 'voice', pedal=False),
     layer(_octave(), 'octave', transpose=-12, level=-9, pedal=False, keys=('G#4', 'C8'), keyfade=5),
     layer('synthwave/supersaw_lead', 'halo', level=-10, pedal=False,
           **{'amp.attack': 0.02, 'cutoff': 2500, 'amp.velocity': 1.0, 'osc2.level': 0.0}),
     stages={'tone': {'hp.freq': 110, 'peak1.freq': 420, 'peak1.gain': -3.0, 'peak1.q': 0.8,
                      'peak3.freq': 3600, 'peak3.gain': -4.5, 'peak3.q': 0.6, 'high.freq': 9500, 'high.gain': 2.5},
             'comp': {'threshold': -16, 'ratio': 2, 'attack': 25, 'release': 250, 'knee': 8, 'detector': 'rms'},
             'tape': {'speed': '15', 'drive': 5, 'wow': 0.05, 'flutter': 0.05, 'bump': 1},
             'chorus': {'mode': 'I', 'mix': 0.2},
             'double': {'style': 'smooth', 'detune': 9, 'mix': 0.42}},
     preset='synth', aliases=('synth_lead', 'synthwave'), user_gain_db=2.1,
     words=('synth', 'saw', 'supersaw', 'sync', 'moog', 'juno', 'jupiter', 'obx', 'va'),
     measured={'lufs': -18.0, 'vel64_112_db': 8.0, 'width_pct': 34, 'correlation': 0.5},
     sends={'plate': -12, 'echo': -11, 'hall': -14},
     notes='THE synthwave hook lead, fat and singing instead of beepy (The Midnight, FM-84, Gunship, Kavinsky '
           'choruses). Layers: "voice" (two saws 7 ct apart, 3-voice unison, driven ladder, velocity -> level '
           '(amp.velocity 1) and brightness (1.6 oct), a -22 ct scoop into every note, 40 ms glide, delayed vibrato '
           '5.3 Hz / 16 ct after 0.32 s) + "octave" (a square an octave down at -9 dB: the body below 1 kHz, only on '
           'notes from G#4 up, faded in over 5 semitones - lower lines would pile up low mids) + "halo" '
           '(synthwave/supersaw_lead at -10 dB, filtered to 2.5 kHz, 20 ms attack: the shimmer and width around the '
           'centre). Chain: EQ -3 dB 420 Hz / -4.5 dB 3.6 kHz (broad: the hats and snare keep their presence) / +2.5 dB air, RMS compressor 2:1 '
           '(25 ms attack: notes bloom, dynamics stay: ~8 dB from velocity 64 to 112), 15 ips tape, Juno chorus I, '
           'micro-pitch double (~34 % wide, correlation ~0.5: a solid mono centre). Mono: one line, every note '
           're-attacks and glides 40 ms from the last. How to play: hooks C5-C6 (the octave body then sounds '
           'C4-C5), velocities 60-118 in phrase arcs (hero_synth.perform(line, lo=64, hi=112): humanize.touch + '
           'detached notes), long notes on the phrase peaks so the vibrato blooms, a pickup glide into the chorus; no '
           'octave doubling in the notes (the patch carries it). ' + _MIX +
           'Tweak: .layer("octave", level=-6) (fatter; watch the low mids), .layer("halo", level=-6) (a wider, '
           'brighter supersaw sheen), .but(**{"layers.voice.glide": 0.08}) (more portamento), '
           '.but(**{"layers.voice.mod.vib.amount": 25}) (a deeper vibrato; automate instrument.layers.voice.mod.vib.'
           'amount for swells), .but(**{"layers.voice.cutoff": 2600}) or .but_fx("eq", **{"peak3.gain": -2}) (brighter: '
           'it is voiced darker than synthwave/supersaw_lead so a presence-heavy mix keeps its limits; in a lean mix '
           'give it the presence back), .but_fx("microshift", mix=0.6) (wider).')

_reg('synth_piano',
     _loose(layer('sampled/piano_lead', 'piano')),
     layer(_voice(mode='poly', polyphony=8, glide=0.0, **{'amp.attack': 0.03, 'cutoff': 1500}), 'saw', level=-6,
           pedal=False, velcurve=1.6),
     stages={'tone': {'peak3.freq': 3300, 'peak3.gain': -1.5, 'peak3.q': 1.0, 'high.freq': 9500, 'high.gain': 1.5},
             'tape': {'speed': '15', 'drive': 2, 'wow': 0.04, 'flutter': 0.04, 'bump': 1},
             'double': {'style': 'smooth', 'detune': 7, 'mix': 0.25}},
     preset='piano_synth', family='piano_synth', aliases=('synth_piano', 'hybrid'), user_gain_db=0.2,
     play={'player': 'synth', 'vel': (60, 116)},
     measured={'lufs': -18.0, 'children_of_neon_note_dynamics_db': 3.7},
     sends={'plate': -12, 'echo': -12, 'hall': -14},
     notes='The FM-84 / The Midnight hook: the bright melody piano (sampled/piano_lead, its own compressed, chorused '
           'Salamander chain) gives every note its hammer and decay, the hero saw voice (poly, 30 ms attack, 1.5 kHz, '
           'vibrato after 0.32 s) at -6 dB sustains under it so long notes sing where a piano dies away. The saw '
           'answers velocity with a steeper curve (velcurve 1.6: soft notes are piano, hard ones bring the synth in) '
           'and ignores the sustain pedal (a pedalled saw would pile every hook note of a chord into a held cluster). '
           'Chain: -1.5 dB at 3.3 kHz, +1.5 dB air, light 15 ips tape, a micro-pitch double. How to play: like the '
           'piano hook - C5-C7, octave-doubled right hand (hero_synth.perform(line, double=-12) or the pianist moves: '
           'pianist.arrange / octave_double(-12, vel=0.7)), velocities 60-116 with accents, re-struck notes; unlike a '
           'plain piano, held notes and legato (perform(..., tie="all")) work. Pedal steps at chord changes ring the '
           'piano only. ' + _MIX +
           'Tweak: .layer("saw", level=-3) (more synth), .layer("saw", velcurve=1.0) (the saw on every note), '
           '.but(**{"layers.saw.cutoff": 2400}) (a brighter saw), automate instrument.layers.saw.level to push the '
           'saw into the last chorus.')

_reg('darksynth_lead',
     layer(_sync_dry(), 'sync', pedal=False, **{'amp.velocity': 1.0, 'filter.velocity': 1.2, 'cutoff': 2600}),
     layer(_octave(osc1__wave='saw', cutoff=700, filter__drive=0.6), 'octave', transpose=-12, level=-11, pedal=False,
           keys=('G#4', 'C8'), keyfade=5),
     stages={'drive': {'mode': 'tube', 'drive': 8, 'tone': -1},
             'tone': {'hp.freq': 120, 'peak1.freq': 420, 'peak1.gain': -3.0, 'peak1.q': 0.8,
                      'peak3.freq': 3300, 'peak3.gain': -3.0, 'peak3.q': 0.8, 'high.freq': 9000, 'high.gain': 1.5},
             'comp': {'threshold': -20, 'ratio': 2, 'attack': 15, 'release': 180, 'knee': 8, 'detector': 'rms'},
             'double': {'style': 'classic', 'detune': 10, 'mix': 0.3}},
     order=('drive', 'tone', 'comp', 'double'),      # family-specific: the drive before the eq
     preset='darksynth', aliases=('darksynth_lead',), user_gain_db=1.6, words=('darksynth',),
     play={'player': 'synth', 'vel': (66, 112)},
     measured={'lufs': -18.0, 'width_pct': 42},
     sends={'plate': -14, 'echo': -12, 'hall': -16},
     notes='The darker hero (Kavinsky, Perturbator, Carpenter Brut, darker outrun): synthwave/sync_lead (a hard-synced '
           'saw swept down on every attack, mono 20 ms glide, vibrato) with full velocity response (level + 1.2 oct '
           'brightness) + a driven saw an octave down at -11 dB (grit and body, from G#4 up, faded in over 5 semitones), '
           'through a tube drive (8 dB), EQ (-3 dB 420 Hz, -3 dB 3.3 kHz, +1.5 dB air), an RMS compressor 2:1 and an '
           'H910-style double (grainy, ~42 % wide). How to play: riffs and hooks A4-A5 in 8ths and quarters (each '
           'attack gets the sync sweep), hero_synth.perform(line, lo=66, hi=112), long notes with vibrato at the phrase '
           'ends, octave jumps. ' + _MIX +
           'Tweak: .but(**{"layers.sync.mod.sync.amount": 2400}) (a wider sweep), .but_fx("saturator", drive=14) '
           '(dirtier), .layer("octave", level=-6) (heavier), .but(**{"layers.sync.cutoff": 3500}) (brighter).')
