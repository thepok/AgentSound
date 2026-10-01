"""Hero sounds: ONE wrapper that makes any lead a hero - the instrument that sits in front of a record with everything
carved around it (the Baker Street sax, the Elton John piano, the Gilmour solo, The Midnight's synth hook, a film
violin theme, an 80s trumpet solo).

    from agentsound import hero                       # (also: from agentsound import *)
    lead = hero(s.track('lead', 'sampled/solo_violin'), family='strings', genre='film', bed=[pad, strings],
                competitors=[piano], sections=[chorus1, chorus2])          # the sound + the mix rules, on the track
    p = hero('sampled/trumpet', family='brass')       # a Patch: the trumpet through the brass hero chain
    p = hero(family='sax')                            # the family's own hero (= layered/hero_sax)
    hero.play(lead, line, verse)                      # = heroes.play: the family's player (velocity arcs, vibrato)

A hero is three things, and the wrapper does all of them from one table (PRESETS, one preset per family / variant):

1. THE SOUND - a source and the shared hero chain.
   source: the family's own (the sax: the Weresax alto + two MTG alto takes + a muted MTG tenor an octave down; the
   pianos: a key-split Salamander; the guitars: velocity-zoned DI through amps; the synths: layered va voices) or the
   sound you give (a patch name / Patch / Instrument). Extra layers go through inst.stack and are never a copy of the
   same samples (a copy detuned by a few cents comb-filters): double='takes' (other takes of the instrument from a
   different sample set, ~10 dB under, detuned +-8-9 ct, 17-26 ms late, panned apart), double='shift' (a micro-pitch
   double in the chain: width without a second sample set), octave=True / 'muted' (the family's octave-down layer).
   A single source stays a plain instrument (its keyswitch articulations and per-note glides keep working); extra
   layers make a stack.
   chain (after the layers are summed), in this order unless the preset says otherwise (ORDER):
       tone      eq: high-pass, mud / honk / box out (the family's own frequencies)
       catch     a fast peak compressor that only reaches the hardest hits (pianos)
       comp      the bloom: 2-3:1 with a 15-30 ms attack (note attacks and accents pass: the dynamics ear stays
                 quiet), 3-9 dB of gain reduction on a hook - the level nearly constant, long notes bloom
       deess     the de-esser (sung vocals: s / t / sh peaks down 4-8 dB above 6-8 kHz, after the compressor that
                 brought them up, before the presence boost)
       amp       family-specific fx (the clean guitar's amp)
       drive     saturator: harmonics = density and edge at the same loudness
       tape      15 ips tape: glue, rounded peaks
       presence  eq: bite (2.5-3.5 kHz) and air (an 8-10 kHz shelf) after the compressor
       exciter   the top octave
       chorus / double / width / dimension   width without phasing (Juno chorus, micro-pitch double, M/S width,
                 Dimension-D) - mono-compatible
       echo      the instrument's own stereo echo (guitars)
       air       LAST: the BREATH stage (a utility named 'air', 0 dB). Within-note expression - a wind player's
                 "mal kurz mehr, mal kurz weniger" air on a held note, a swell, an fp-crescendo - written on
                 'fx.air.gain' (heroes.air(track, points)) lands after all the compression and saturation: a 3 dB
                 push on a held note stays 3 dB at the output (AIR_TARGET)
   space: the sends (plate / hall / echo); in a song the family's plate bus (bus/hero_plate: big, bright,
   pre-delayed) and echo THROWS at the phrase ends instead of a constant echo.

2. THE MIX RULES - when hero() gets a Track (and so the song): the bed (pads, strings, choir) ducks under the hero
   (song.sidechain keyed by it) and steps out of its presence band while the hero plays (song.carve: a keyed dynamic
   EQ); competitors (keys, comping, rhythm guitars, arps) get a static presence dip (mixer.add_eq_dip: an eq named
   'hero_dip'); the hero is ridden up in the hook sections (a 'hero_ride' utility and its 'fx.hero_ride.gain' lane,
   the mixer's ride points); echo throws at every phrase end the track plays (articulation.throws, written when the
   song compiles, so notes placed after hero() count). The depths come from the preset; a genre (a mixer profile:
   bed_duck_db, lead_ride_db, dip_db) wins when given. Every move is logged (track.hero.log, heroes.log_lines(song),
   printed by `python -m agentsound build` / `check`) and every part can be switched off: chain=False (keep the
   sound), space=False, plate=False, echo=False, duck=False, carve=False, dips=False, ride=False, throws=False (a
   number instead of True/False sets the depth: duck=3, carve=2, dips=1.5, ride=2).

3. HOW TO PLAY IT - heroes.play(track, line, at) (= hero.play): the family's player - humanize.touch velocity arcs in
   the preset's range, then articulation.perform (legato, vibrato on the long notes, the instrument's articulations),
   the guitar's zone-locked play or the synth's detached re-attacks. The preset's 'play' entry says what else it
   needs (register, velocities, vibrato).

Generic vs family-specific: the stage vocabulary and ORDER, MIX_DEFAULTS, SPACE_DEFAULTS, the mix rules, the throw and
ride logic are shared; the frequencies, amounts, sources, sends and mix depths are per preset (PRESETS[name].chain /
.mix / .space). The four hero modules (patches/hero.py, hero_piano.py, hero_guitar.py, hero_synth.py) define their
presets with their measured numbers and build their library patches through build() - the old names stay registered
and render bit-identically (tests/python/test_hero.py pins their definitions); patches/hero_families.py adds strings,
brass, woodwind, voice, organ and generic. Every preset is also registered as hero/<preset>.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .theory import ComposeError

# ------------------------------------------------------------------------------------------------ the chain

STAGES = {'tone': 'eq', 'catch': 'compressor', 'comp': 'compressor', 'deess': 'deesser', 'amp': None,
          'drive': 'saturator',
          'tape': 'tape', 'air': 'utility', 'presence': 'eq', 'exciter': 'exciter', 'chorus': 'chorus',
          'double': 'microshift', 'width': 'width', 'dimension': 'dimension', 'echo': 'delay'}
"""Stage -> engine fx type (None: a list of fx given by the preset)."""
ORDER = ('tone', 'catch', 'comp', 'deess', 'amp', 'drive', 'tape', 'presence', 'exciter', 'chorus', 'double',
         'width', 'dimension', 'echo', 'air')
"""The shared hero chain in signal order (a preset may reorder: the darksynth drives before its eq; 'air' is always
last)."""
DYNAMIC_STAGES = ('catch', 'comp', 'amp', 'drive', 'tape')
"""The level-dependent stages (the 'air' stage comes after all of them)."""
AIR = 'air'
AIR_TARGET = 'fx.air.gain'
"""The breath / air-pressure stage: a utility named 'air' (gain 0 dB) at the end of the chain - after the compressor
and the saturation - in every hero built by the wrapper. A player writes the within-note expression of a wind
player or a bowed string (a swell, a short push, an fp-crescendo: "mal kurz mehr, mal kurz weniger" air on a held
note) as dB on
'fx.air.gain' (heroes.air(track, points)): it lands AFTER the 6-9 dB of hero compression, so a 3 dB push stays a
3 dB push at the output instead of being squashed flat. The timbre side of the same breath stays in front of the
chain: the sampler's 'dynamics' crossfade / 'expression' (instrument.dynamics, articulation.expression) change the
tone colour, the compressor evens their level, the air stage restores the level move on top."""

LAYER_ARGS = ('level', 'pan', 'mute', 'transpose', 'fine', 'delay', 'velcurve', 'velscale', 'keys', 'vel', 'keyfade',
              'velfade', 'pedal', 'bend', 'expression', 'dynamics', 'modwheel')
"""Keys of a source layer spec that go to layer() as they are ('hp' becomes a 24 dB/oct high-pass in its fx, 'fx'
more layer fx, 'params' instrument params)."""

DOUBLE_MODES = ('takes', 'shift', None)
OCTAVE_MODES = ('on', 'muted', 'off')
SHIFT = {'style': 'smooth', 'detune': 8, 'delay': 6, 'focus': 300, 'mix': 0.28}
"""double='shift' when the preset's chain has no 'double' stage: this micro-pitch double (the synth / guitar heroes'
H3000 idea: +-7-9 ct, 4-8 ms, above 300 Hz)."""

MIX_DEFAULTS = {'duck': 2.5, 'duck_threshold': -34.0, 'duck_attack': 15.0, 'duck_hold': 60.0, 'duck_release': 260.0,
                'carve_db': 3.0, 'carve_freq': 2500.0, 'carve_q': 0.7, 'ride_db': 1.0, 'dip_db': -2.0,
                'dip_freq': 2500.0, 'dip_q': 0.9, 'feature': ''}
"""Generic mix rules, from the four hero validations (bed duck 2.5 dB, attack 15 / release 260 ms; a 2.5 kHz presence
carve; the hero ridden 1-2 dB up in the hooks; competitors -2 dB in the presence band); presets override."""
SPACE_DEFAULTS = {'plate_bus': None, 'plate': -14.0, 'echo': -24.0, 'throw': -8.0, 'min_rest': 0.75, 'min_dur': 0.5}
"""Generic space: no own plate bus, an echo send at -24 dB thrown to -8 dB on phrase ends (a held note of 0.5+ beats
followed by 0.75+ beats of rest)."""


def stage_fx(stage: str, value, named: bool = False) -> list:
    """The fx of one chain stage: a params dict ('name' inside it names the effect; named=True names it after the
    stage), an FX, or a list of FX (the 'amp' stage)."""
    from .patches import FX
    if stage not in STAGES:
        raise ComposeError(f"hero chain: unknown stage {stage!r} (stages: {', '.join(ORDER)})")
    if value is None or value is False:
        return []
    if isinstance(value, FX):
        return [value.copy()]
    if isinstance(value, (list, tuple)):
        return [FX.coerce(f) for f in value]
    if not isinstance(value, dict):
        raise ComposeError(f"hero chain stage {stage!r}: a params dict, an FX or a list of FX, got {value!r}")
    if STAGES[stage] is None:
        raise ComposeError(f"hero chain stage {stage!r} takes a list of fx")
    params = dict(value)
    name = params.pop('name', stage if named else None)
    return [FX(STAGES[stage], params, name=name)] if name else [FX(STAGES[stage], params)]


def air_order(stages: dict, order=ORDER) -> tuple:
    """`order` with the 'air' stage last: after every level-dependent stage (DYNAMIC_STAGES: the compressors, amp,
    drive, tape) and after the linear colour / width / echo stages too - so adding it changes nothing else in the
    chain (the old heroes stay bit-identical at 0 dB: the fx before it keep their positions)."""
    return tuple([s for s in order if s != AIR] + [AIR])


def chain(stages: dict, order=ORDER, named: bool = False, air: bool = False) -> list:
    """The hero insert chain: the stages of `stages` in `order`. air=True adds the breath stage (a utility named
    'air' at 0 dB) at the end, after the compressor / saturation (air_order); air=False leaves it out."""
    stages = dict(stages)
    if air:
        stages[AIR] = {'name': AIR, 'gain': 0.0, **(stages.get(AIR) or {})}
        order = air_order(stages, order)
    else:
        stages.pop(AIR, None)
    extra = [k for k in stages if k not in order and stages[k] not in (None, False)]
    if extra:
        raise ComposeError(f"hero chain: stage(s) {', '.join(extra)} are not in the order {', '.join(order)}")
    out: list = []
    for st in order:
        if st in stages:
            out += stage_fx(st, stages[st], named)
    return out


def air(track, *points):
    """Breath / air pressure on a hero track: automate its 'air' stage ('fx.air.gain', dB, after the compressor) -
    points as for track.automate: heroes.air(sax, [(8, 0), (8.5, 3, 'smooth'), (9.2, -1, 'smooth'), (10, 0)]).
    Errors when the track has no 'air' stage (a hero built by heroes.build / hero() has one)."""
    if not any(f.name == AIR and f.type == 'utility' for f in getattr(track, 'fx', ())):
        raise ComposeError(f"track {getattr(track, 'id', track)!r} has no hero 'air' stage (a utility named 'air'): "
                           f"make it a hero with hero(track, family=...) or use a hero/<preset> patch")
    return track.automate(AIR_TARGET, *points)


# ------------------------------------------------------------------------------------------------ presets

@dataclass
class Preset:
    """One hero preset (a family or a variant of it); PRESETS holds them. See the module docstring."""
    name: str
    family: str
    chain: dict
    gain_db: float
    sends: dict
    sound: object = None           # the default source: a patch name / Patch / Instrument (generic sources)
    source: object = None          # a callable () -> Instrument | [Layer]: the family's own source (overrides sound)
    main: dict | None = None       # the main layer spec of a generic source ({'id', 'sound', 'hp', LAYER_ARGS ...})
    takes: list = field(default_factory=list)     # double='takes': other takes (layer specs)
    octave: dict | None = None     # the octave layer spec; its 'mode' ('on' | 'muted' | 'off') is the default use
    double: str | None = None      # the default double mode: 'takes', 'shift' or None
    order: tuple = ORDER
    named: bool = True             # the chain's fx named after their stages ('tone', 'comp', ...)
    user_gain_db: float | None = None   # gain_db around another -18 LUFS-calibrated sound (None: gain_db)
    space: dict = field(default_factory=dict)
    mix: dict = field(default_factory=dict)
    play: dict = field(default_factory=dict)
    notes: str = ''
    audition: dict | None = None
    patch: str | None = None       # the library name of the preset's own hero (legacy: layered/hero_sax ...)
    aliases: tuple = ()
    words: tuple = ()              # patch-name words that make infer() pick this preset
    measured: dict = field(default_factory=dict)  # the calibration / validation numbers (documentation)

    def mix_value(self, key: str):
        return self.mix.get(key, MIX_DEFAULTS[key])

    def space_value(self, key: str):
        return self.space.get(key, SPACE_DEFAULTS[key])

    @property
    def canonical(self) -> str:
        return f'hero/{self.name}'


PRESETS: dict[str, Preset] = {}
_ALIASES: dict[str, str] = {}


def define(name: str, **kw) -> Preset:
    """Add a hero preset (the hero modules do this at import). Returns it."""
    if name in PRESETS:
        raise ComposeError(f"hero preset {name!r} is already defined")
    p = Preset(name=name, **kw)
    if p.double not in DOUBLE_MODES:
        raise ComposeError(f"hero preset {name!r}: double must be one of {DOUBLE_MODES}, got {p.double!r}")
    for st in p.chain:
        if st not in STAGES:
            raise ComposeError(f"hero preset {name!r}: unknown chain stage {st!r}")
    PRESETS[name] = p
    for a in p.aliases:
        _ALIASES[a] = name
    return p


def register(name: str) -> None:
    """Register a preset's own hero in the patch library as hero/<preset> (the unified name, with the 'air' breath
    stage) and, for the heroes that existed before the wrapper, under their old library name (p.patch, e.g.
    layered/hero_sax) exactly as before (no 'air' stage: the old render JSON stays identical; the sound is the same)."""
    from . import patches
    p = PRESETS[name]
    new = build(p, name=p.canonical)
    if p.patch and p.patch != p.canonical:
        old = build(p, air=False)
        patches.register(old)
        new.notes = (f"= {p.patch} + the 'air' breath stage (hero preset {p.name!r}: hero(family={p.name!r})). "
                     + new.notes)
    patches.register(new)


def _load() -> None:
    from . import patches
    patches.load_library()


def presets() -> list[str]:
    """Names of the hero presets."""
    _load()
    return sorted(PRESETS)


def get_preset(name) -> Preset:
    """A preset by name, family or alias ('strings', 'violin', 'piano_pop', 'synth_lead' ...)."""
    if isinstance(name, Preset):
        return name
    _load()
    key = str(name).lower().strip()
    if key.startswith('hero/'):
        key = key[5:]
    if key in PRESETS:
        return PRESETS[key]
    if key in _ALIASES:
        return PRESETS[_ALIASES[key]]
    fam = [p for p in PRESETS.values() if p.family == key]
    if fam:
        return fam[0]
    import difflib
    names = sorted(set(PRESETS) | set(_ALIASES))
    close = difflib.get_close_matches(key, names, n=3, cutoff=0.5)
    raise ComposeError(f"no hero family / preset {name!r}" + (f" - did you mean {', '.join(close)}?" if close else '')
                       + f" (presets: {', '.join(sorted(PRESETS))})")


def infer(sound) -> Preset:
    """The preset for a sound: a registered hero patch -> its preset; else the words of its patch name ('violin' ->
    strings, 'trumpet' -> brass ...); a va / dx7 instrument -> synth; else generic."""
    _load()
    if getattr(sound, '_singer', None) and 'vocal' in PRESETS:     # a sung vocal track (agentsound.singer)
        return PRESETS['vocal']
    name = _sound_name(sound)
    if name:
        for p in PRESETS.values():
            if name in (p.patch, p.canonical):
                return p
        words = set(re.split(r'[/_\-.+ ]+', name.lower()))
        for p in PRESETS.values():
            if words & set(p.words):
                return p
    ins = _instrument_of(sound)
    if ins is not None and ins.type in ('va', 'dx7'):
        return PRESETS['synth']
    return PRESETS['generic']


def _sound_name(sound) -> str | None:
    from .patches import Patch
    if isinstance(sound, str):
        return sound
    if isinstance(sound, Patch):
        return sound.name
    p = getattr(sound, 'patch', None)          # a Track
    return p if isinstance(p, str) else None


def _instrument_of(sound):
    from . import patches
    if isinstance(sound, str):
        return patches.get(sound).instrument
    if isinstance(sound, patches.Instrument):
        return sound
    return getattr(sound, 'instrument', None)


# ------------------------------------------------------------------------------------------------ building

def _spec_layer(spec: dict, default_id: str):
    from .patches import fx as _fx
    from .patches import layer
    kw = {k: spec[k] for k in LAYER_ARGS if k in spec}
    kw.update(spec.get('params') or {})
    lfx = [_fx.eq({'hp.freq': spec['hp'], 'hp.slope': 24})] if spec.get('hp') else []
    lfx += [f.copy() for f in spec.get('fx', ())]
    return layer(spec['sound'], spec.get('id', default_id), fx=lfx, **kw)


def _mode(value, default, modes, what: str):
    if value is None:
        return default
    if value is True:
        return modes[0]
    if value is False:
        return None if what == 'double' else 'off'
    if value not in modes:
        raise ComposeError(f"hero: {what} must be one of {', '.join(str(m) for m in modes)} (or True / False), "
                           f"got {value!r}")
    return value


def _stages(p: Preset, overrides: dict) -> dict:
    st = {k: (dict(v) if isinstance(v, dict) else v) for k, v in p.chain.items()}
    for k, v in overrides.items():
        if k not in STAGES:
            raise ComposeError(f"hero: unknown chain stage {k!r} (stages: {', '.join(ORDER)})")
        if v is False or v is None:
            st.pop(k, None)
        elif isinstance(v, dict) and isinstance(st.get(k), dict):
            st[k] = {**st[k], **v}
        else:
            st[k] = v
    return st


def build(preset, sound=None, *, double=None, octave=None, air: bool = True, name: str | None = None,
          log: list | None = None, **stages):
    """The hero Patch of a preset: its own source (sound=None or the preset's default) or `sound` (a patch name,
    Patch or Instrument) through the preset's chain. double: 'takes' | 'shift' | False (None: the preset's default;
    'takes' are other takes of the preset's own instrument - with another sound they become 'shift' unless forced);
    octave: True / 'muted' / False (None: the preset's default). stages: chain overrides - comp={'threshold': -20}
    merges into the stage, drive=False drops it. air: the breath stage after the compressor (AIR; air=False: the
    chain as the preset lists it - the old library patches). name: the patch name (default: hero/<preset>, the old
    library name with air=False, or 'hero/<preset>+<sound>'). log: a list that receives what was built (one line per
    decision). A single source layer stays a plain instrument (its keyswitches, per-note glides and articulation
    marks keep working); extra layers make a stack."""
    from . import patches
    from .patches import Instrument, Patch
    p = get_preset(preset)
    lg = log if log is not None else []
    if isinstance(sound, str) and sound in (p.patch, p.canonical):
        sound = None
    own = sound is None or (isinstance(sound, str) and isinstance(p.sound, str) and sound == p.sound)
    dmode = _mode(double, p.double, DOUBLE_MODES, 'double')
    omode = _mode(octave, (p.octave or {}).get('mode', 'off'), OCTAVE_MODES, 'octave')
    st = _stages(p, stages)
    plain = None
    if own and p.source is not None:                       # the family's own source (piano / guitar / synth heroes)
        got = p.source()
        lg.append(f"source: the {p.name} hero's own ({_describe_source(got)})")
        if isinstance(got, Instrument):
            plain, layers = got, []
        else:
            layers = list(got)
        if double is not None or octave is not None:
            lg.append("double / octave: part of this family's own source (tweak its layers: patch.layer(id, ...))")
        dmode = None
    else:
        spec = dict(p.main or {}) if own else {'id': 'lead', 'sound': sound}
        if spec.get('sound') is None:
            spec['sound'] = p.sound
        if spec.get('sound') is None:
            raise ComposeError(f"hero preset {p.name!r} has no default sound; give one: "
                               f"hero('sampled/...', family={p.family!r})")
        if dmode == 'takes' and not own and double is None:
            lg.append("double: the preset's takes are other takes of ITS instrument -> 'shift' here "
                      "(double='takes' forces them)")
            dmode = 'shift'
        src = patches.get(spec['sound']) if isinstance(spec['sound'], str) else spec['sound']
        src_ins = src.instrument if isinstance(src, Patch) else src
        if isinstance(src_ins, Instrument) and src_ins.type == 'stack':
            # a layered sound (a stack: e.g. another hero) is wrapped whole: the chain goes after its own
            if dmode == 'takes' or octave in (True, 'on', 'muted'):
                raise ComposeError(f"hero: {_sound_label(spec['sound'])} is a stack - add takes / an octave as its "
                                   f"layers (patch.layer(...), inst.stack) instead of double= / octave=")
            lg.append(f"source: {_sound_label(spec['sound'])} (a stack: wrapped whole)")
            pre = [f.copy() for f in src.fx] if isinstance(src, Patch) else []
            gain = (src.gain_db if isinstance(src, Patch) else 0.0) + \
                (p.user_gain_db if p.user_gain_db is not None and not own else p.gain_db)
            if dmode == 'shift' and not st.get('double'):
                st['double'] = dict(SHIFT)
            ch = chain(st, p.order, p.named, air=air)
            lg.append('chain: ' + ' -> '.join(s for s in (air_order(st, p.order) if air else p.order)
                                              if st.get(s) or (air and s == AIR)))
            tail = _sound_label(spec['sound']).rsplit('/', 1)[-1].lower()
            nm = name or f"{p.canonical}+{re.sub(r'[^a-z0-9_.+-]+', '_', tail).strip('_') or 'sound'}"
            return Patch(nm, src_ins, fx=pre + ch, gain_db=round(gain, 4), sends=dict(p.sends),
                         notes=' '.join(x.rstrip('.') + '.' for x in lg) + ' ' + p.notes,
                         audition=src.audition if isinstance(src, Patch) else p.audition)
        layers = [_spec_layer(spec, 'lead')]
        lg.append(f"source: {_sound_label(spec['sound'])}" +
                  ('' if own else f" (the {p.name} preset is voiced on {_sound_label(p.sound or p.patch)})"))
        if dmode == 'takes':
            if not p.takes:
                lg.append(f"double: the {p.name} preset has no takes -> 'shift'")
                dmode = 'shift'
            else:
                layers += [_spec_layer(t, 'take') for t in p.takes]
                lg.append(f"double: {len(p.takes)} takes of another sample set ("
                          + ', '.join(f"{t.get('id')} {t.get('level', 0):+g} dB {t.get('fine', 0):+g} ct "
                                      f"{t.get('delay', 0):g} ms pan {t.get('pan', 0):+g}" for t in p.takes)
                          + "; uncorrelated: width without phasing)")
        if p.octave and omode in ('on', 'muted'):
            o = {k: v for k, v in p.octave.items() if k not in ('mode', 'mute')}
            if omode == 'muted':
                o['mute'] = True
            layers.append(_spec_layer(o, 'octave'))
            lg.append(f"octave: {_sound_label(o['sound'])} {o.get('transpose', -12):+d} st at {o.get('level', 0):+g}"
                      " dB" + (" (muted: automate instrument.layers.octave.mute to 0 in the big sections)"
                               if omode == 'muted' else ''))
    if dmode == 'shift':
        if not st.get('double'):
            st['double'] = dict(SHIFT)
        d = st['double']
        lg.append(f"double: micro-pitch double (microshift {d.get('style', 'smooth')}, +-{d.get('detune', 0):g} ct, "
                  f"mix {d.get('mix', 0):g})" if isinstance(d, dict) else "double: the chain's micro-pitch double")
    ch = chain(st, p.order, p.named, air=air)
    order = air_order(st, p.order) if air else p.order
    lg.append('chain: ' + (' -> '.join(s for s in order if st.get(s) or (air and s == AIR)) or 'none')
              + (f" ('air': breath automation on {AIR_TARGET} lands after the compression)" if air else ''))
    gain = p.gain_db if own else (p.user_gain_db if p.user_gain_db is not None else p.gain_db)
    if name is None:
        if own:
            name = p.canonical if air else (p.patch or p.canonical)
        else:
            tail = re.sub(r'[^a-z0-9_.+-]+', '_', _sound_label(sound).rsplit('/', 1)[-1].lower()).strip('_')
            name = f"{p.canonical}+{tail or 'sound'}"
    notes = p.notes if own else (f"hero({_sound_label(sound)!r}, family={p.name!r}): the {p.name} hero around this "
                                 f"sound (gain calibrated on the preset's own sound: audition it). "
                                 + ' '.join(x.rstrip('.') + '.' for x in lg) + ' ' + p.notes).strip()
    sends = dict(p.sends)
    if plain is not None:
        return Patch(name, plain, fx=ch, gain_db=gain, sends=sends, notes=notes, audition=p.audition)
    if len(layers) == 1 and set(layers[0].params) <= {'level', 'pan'}:
        lay = layers[0]
        src = patches.get(lay.source) if isinstance(lay.source, str) and patches.has(lay.source) else None
        aud = p.audition if (own and p.audition) else (src.audition if src is not None else p.audition)
        return Patch(name, lay.instrument, fx=[f.copy() for f in lay.fx] + ch,
                     gain_db=round(float(lay.params.get('level', 0.0)) + gain, 4),
                     pan=float(lay.params.get('pan', 0.0)), sends=sends, notes=notes, audition=aud)
    return Patch.layered(name, *layers, fx=ch, gain_db=gain, sends=sends, notes=notes, audition=p.audition)


def _sound_label(s) -> str:
    from .patches import Instrument, Patch
    if isinstance(s, str):
        return s
    if isinstance(s, Patch):
        return s.name
    if isinstance(s, Instrument):
        path = (s.lazy or {}).get('path') if s.lazy else None
        return f"inst.{s.type}({str(path).rsplit('/', 1)[-1]!r})" if path else f"inst.{s.type}(...)"
    return repr(s)


def _describe_source(got) -> str:
    from .patches import Instrument
    if isinstance(got, Instrument):
        return f"one {got.type}"
    return f"{len(got)} layers: " + ', '.join(x.id or '?' for x in got)


# ------------------------------------------------------------------------------------------------ the wrapper

@dataclass
class HeroInfo:
    """What hero() did to a track (track.hero). log: the moves made by hero() (sound, space, duck, carve, dips);
    compile_log: the moves written when the song compiles (rides, throws; rewritten by every compile)."""
    track: object
    preset: Preset
    genre: str | None
    options: dict
    log: list = field(default_factory=list)
    compile_log: list = field(default_factory=list)
    sections: object = None
    echo: str | None = None        # the echo bus id of the throws, 'fx.echo' (its own echo) or None
    echo_base: float | None = None
    throw_db: float | None = None
    ride_db: float = 0.0
    _lanes: list = field(default_factory=list)

    def lines(self) -> list[str]:
        head = f"{self.track.id!r} ({self.preset.name}{', ' + self.genre if self.genre else ''})"
        return [f"{head}: {x}" for x in self.log + self.compile_log]

    def describe(self) -> str:
        return '\n'.join(self.lines())

    def __str__(self) -> str:
        return self.describe()

    def _compile(self, song) -> None:
        """The moves that need the whole song (Song.compile runs this first; idempotent: the lanes of the last run
        are replaced)."""
        from .patterns import Clip
        t = self.track
        mine = {id(x) for x in self._lanes}
        t._auto = [x for x in t._auto if id(x) not in mine]
        self._lanes = []
        self.compile_log = []
        if self.ride_db:
            names = _hook_names(song, self.sections, self.preset.mix_value('feature'))
            if names:
                from . import mixer
                pts = mixer._ride_points(song, 0.0, {n: self.ride_db for n in names}, 1.0)
                t.automate('fx.hero_ride.gain', pts)
                self._lanes.append(t._auto[-1])
                self.compile_log.append(f"ride: {self.ride_db:+g} dB in {', '.join(names)} (fx.hero_ride.gain, "
                                        f"1-beat ramps)")
            else:
                self.compile_log.append("ride: no hook sections (name them chorus / drop / hook / refrain ... or "
                                        "pass sections=)")
        if not self.options.get('throws') or not self.echo:
            return
        notes = sorted(t._notes, key=lambda n: n.start)
        if getattr(t, '_singer', None):         # a sung vocal: its phrases as sung, not the takes' trigger notes
            from .singer import phrase_notes
            notes = phrase_notes(t)
        if not notes:
            self.compile_log.append("throws: the track plays nothing")
            return
        clip = Clip._raw(notes, max(song.length, max(n.start + n.dur for n in notes)))
        if self.echo == 'fx.echo':
            if any(tg == 'fx.echo.mix' for tg, _ in t._auto):
                self.compile_log.append("throws: the track already automates fx.echo.mix (kept; no throws written)")
                return
            from .patches import hero_guitar as _hg
            base = _hg._fx_param(t, 'echo', 'mix', 0.2)
            pts = _hg._throw_points(clip, 0.0, base)
            if pts:
                t.automate('fx.echo.mix', pts)
                self._lanes.append(t._auto[-1])
            self.compile_log.append(f"throws: {len(pts) // 4} phrase ends, its own echo's mix {base:g} -> "
                                    f"{base + 0.2:g} (fx.echo.mix)")
            return
        tgt = f'send.{self.echo}'
        if any(tg == tgt for tg, _ in t._auto):
            self.compile_log.append(f"throws: the track already automates {tgt} (kept; no throws written)")
            return
        from . import articulation as _art
        sp = self.preset
        n0 = len(t._auto)
        ends = _art.throws(t, clip, 0.0, bus=self.echo, base=self.echo_base, throw=self.throw_db,
                           min_rest=sp.space_value('min_rest'), min_dur=sp.space_value('min_dur'))
        if len(t._auto) > n0:
            self._lanes.append(t._auto[-1])
        self.compile_log.append(f"throws: {len(ends)} phrase ends, {tgt} {self.echo_base:g} -> {self.throw_db:g} dB "
                                f"(articulation.throws)")


def _hook_names(song, sections, feature: str = '') -> list[str]:
    """The sections a hero is ridden up in: `sections` when given, else the hook sections (chorus / drop / hook ...)
    plus the preset's own feature sections (its mix 'feature': a regex of section names - the guitar heroes: 'solo')."""
    from . import mixer
    if sections is not None:
        out = []
        for s in (sections if isinstance(sections, (list, tuple, set)) else [sections]):
            nm = s if isinstance(s, str) else getattr(s, 'name', None)
            song[nm]          # a missing section is an error (with the list of sections)
            out.append(nm)
        return out
    feat = re.compile(feature, re.I) if feature else None
    return [s.name for s in song.sections if mixer._HOOK_RE.search(s.name) or (feat and feat.search(s.name))]


def _nodes(nodes) -> list:
    if nodes is None:
        return []
    if not isinstance(nodes, (list, tuple, set)):
        nodes = [nodes]
    return list(nodes)


def _insert_air(track) -> str:
    """Add the 'air' stage at the end of a track chain that has none (after its compressors / saturation); returns
    the log text."""
    from .patches import FX
    if any(f.name == AIR and f.type == 'utility' for f in track.fx):
        return "; its 'air' stage is there"
    track.fx.append(FX('utility', {'gain': 0.0}, name=AIR))
    return f"; 'air' stage added at the end of its chain ({AIR_TARGET})"


def _names(nodes) -> str:
    return ', '.join(getattr(x, 'id', x) for x in nodes)


def _depth(opt, default: float) -> float:
    """A switch that may carry an amount: False -> 0 (off), True / None -> the default (the genre's or the preset's),
    a number -> that (as a magnitude, whatever the default)."""
    if opt is False:
        return 0.0
    if isinstance(opt, (int, float)) and not isinstance(opt, bool):
        return abs(float(opt))
    return abs(float(default))


def _echo_bus(song, echo):
    """The echo bus for the throws: the given one, the song's 'echo', any bus named *echo* / *delay*, else a new
    s.echo(). Returns (bus id, created)."""
    if echo is not None and echo is not True:
        bid = getattr(echo, 'id', echo)
        song.node(bid)
        return bid, False
    if 'echo' in song.buses:
        return 'echo', False
    for b in song.buses:
        if 'echo' in b or 'delay' in b:
            return b, False
    return song.echo().id, True


def hero(sound=None, family=None, *, genre=None, bed=(), competitors=(), sections=None, double=None, octave=None,
         chain=True, space=True, plate=None, echo=None, duck=True, carve=True, dips=True, ride=True, throws=True,
         air=True, **stages):
    """THE way to make a lead a hero (the module docstring explains what it does).

    hero(track, family=None, ...) -> the track: its sound replaced by the hero patch and the mix rules applied, all of
    it logged (track.hero, heroes.log_lines(song), printed at build). hero(sound=None | 'patch/name' | Patch |
    Instrument, family=...) -> a Patch.
    family: a preset / family / alias - 'sax', 'piano', 'piano_pop', 'piano_strings', 'guitar', 'guitar_clean',
    'guitar_heavy', 'synth', 'darksynth', 'piano_synth', 'strings' (violin), 'brass' (trumpet), 'woodwind' (flute),
    'voice' (choir), 'vocal' (a sung lead vocal: agentsound.singer), 'organ', 'generic'; None: inferred from the
    sound (heroes.infer).
    genre: a mixer profile ('pop', 'rock', 'film', 'synthwave', 'jazz', 'classical' ...): its bed duck, lead ride and
    dip depths win over the preset's. bed: tracks / buses that duck and get carved under the hero; competitors:
    tracks that get a static presence dip; sections: the hook sections the hero is ridden up in (None: the sections
    named chorus / drop / hook / refrain / lift / climax / finale / peak / head, plus the preset's feature sections:
    the guitar heroes' 'solo...').
    double / octave / air / **stages: as build() (air: the breath stage - 'fx.air.gain' after the compressor, for
    within-note expression; heroes.air(track, points)). Switches (False = off; a number = the depth in dB): chain
    (False keeps the track's sound; the 'air' stage is still added), space, plate (a bus / id / 'bus/<patch>' instead
    of the preset's), echo (a bus / id), duck, carve, dips, ride, throws."""
    from .song import Track
    if isinstance(sound, Track):
        return _wrap_track(sound, family, genre=genre, bed=bed, competitors=competitors, sections=sections,
                           double=double, octave=octave, chain=chain, space=space, plate=plate, echo=echo, duck=duck,
                           carve=carve, dips=dips, ride=ride, throws=throws, air=air, stages=stages)
    if bed or competitors or sections is not None or genre is not None:
        raise ComposeError("hero(): bed= / competitors= / sections= / genre= are mix rules and need the track: "
                           "hero(s.track('lead', ...), family=..., bed=[...])")
    if sound is None and family is None:
        raise ComposeError("hero() needs a sound or a family: hero('sampled/trumpet', family='brass'), "
                           "hero(family='sax')")
    p = get_preset(family) if family is not None else infer(sound)
    return build(p, sound, double=double, octave=octave, air=air, **stages)


def _wrap_track(track, family, *, genre, bed, competitors, sections, double, octave, chain, space, plate, echo, duck,
                carve, dips, ride, throws, stages, air=True):
    from . import mixer, patches
    from .patches import FX
    song = track._song
    if getattr(track, 'hero', None) is not None:
        raise ComposeError(f"track {track.id!r} is already a hero (call hero() once per track)")
    p = get_preset(family) if family is not None else infer(track)
    owner = next((q for q in PRESETS.values() if track.patch and track.patch in (q.patch, q.canonical)), None)
    if owner is not None and owner is not p and owner.family == p.family:
        p = owner                     # the track already holds a variant of that family (hero_piano_pop, ...)
    prof = mixer.get_profile(genre) if genre is not None else None
    info = HeroInfo(track, p, prof.name if prof else None, {'throws': bool(throws)}, sections=sections)
    lg = info.log
    if family is None:
        lg.append(f"family: {p.name} (inferred from {track.patch or track.instrument.type})")
    # 1. the sound
    already = track.patch is not None and track.patch in (p.patch, p.canonical)
    old = patches.get(track.patch) if track.patch and patches.has(track.patch) else None
    fits = old is not None and track.fx[:len(old.fx)] == old.fx
    if not chain or (already and not fits):
        why = "chain=False" if not chain else f"{track.patch} with its chain changed by the song"
        lg.append(f"sound: unchanged ({why})" + (_insert_air(track) if air else ''))
    else:
        blog: list = []
        if fits:
            extra = track.fx[len(old.fx):]         # the song's own inserts after the patch chain stay after the hero's
            new = build(p, None if already else track.patch, double=double, octave=octave, air=air, log=blog,
                        name=p.canonical if already and air else None, **stages)
            track.gain_db = track.gain_db - old.gain_db + new.gain_db
        else:                                      # an instrument (or a changed chain): all of it is the source
            src = patches.Patch('hero/source', track.instrument, fx=list(track.fx))
            extra = []
            new = build(p, src, double=double, octave=octave, air=air, log=blog,
                        name=f"{p.canonical}+{re.sub(r'[^a-z0-9_]+', '_', track.id.lower())}", **stages)
            track.gain_db = track.gain_db + new.gain_db
        track.instrument = new.instrument
        track.fx = [f.copy() for f in new.fx] + list(extra)
        track._patch_sends = dict(new.sends)
        track.patch = new.name
        lg.append(f"sound: {new.name}" + (f" (was {old.name})" if old is not None and old.name != new.name else '')
                  + f", gain {new.gain_db:+g} dB - " + '; '.join(blog))
    # 2. the space: the hero's plate, the echo for the throws
    own_echo = any(f.type == 'delay' and f.name == 'echo' for f in track.fx)
    if not space:
        lg.append("space: unchanged (space=False)")
    else:
        pb = p.space_value('plate_bus') if plate is None or plate is True else plate
        if pb:
            if isinstance(pb, str) and pb.startswith('bus/'):
                bid = 'hero_plate'
                made = bid not in song.buses
                bus = song.bus(bid, pb) if made else song.buses[bid]
            else:
                bus, made = song.node(getattr(pb, 'id', pb)), False
            lvl = track.sends.get(bus.id, p.space_value('plate'))        # a send the song set itself stays
            dropped = track._patch_sends.pop('plate', None)
            track.send(bus, lvl)
            lg.append(f"space: plate -> {bus.id!r} at {lvl:g} dB" + (f" (created from {pb})" if made else '')
                      + (f"; the patch's send to the band's 'plate' ({dropped:g} dB) moved there" if dropped is not None
                         else ''))
        if own_echo:
            info.echo = 'fx.echo'
            lg.append("space: its own echo (fx 'echo'); the throws raise fx.echo.mix")
        elif echo is not False and (throws or 'echo' in track._patch_sends):
            eid, made = _echo_bus(song, echo)
            base = track._patch_sends.pop('echo', None)
            if base is None:
                base = p.space_value('echo')
            base = track.sends.get(eid, base)
            track.send(eid, base)
            info.echo, info.echo_base, info.throw_db = eid, float(base), float(p.space_value('throw'))
            lg.append(f"space: echo -> {eid!r} at {base:g} dB" + (" (created: s.echo())" if made else ''))
        elif echo is False:
            track._patch_sends.pop('echo', None)
            lg.append("space: no echo (echo=False)")
    # 3. the bed: duck + carve
    bed_ids = _nodes(bed)
    if bed_ids:
        d = _depth(duck, prof.bed_duck_db if prof is not None else p.mix_value('duck'))
        if d:
            song.sidechain(*bed_ids, key=track, depth=d, threshold=p.mix_value('duck_threshold'),
                           attack=p.mix_value('duck_attack'), hold=p.mix_value('duck_hold'),
                           release=p.mix_value('duck_release'))
            lg.append(f"duck: {_names(bed_ids)} {d:g} dB under the hero (song.sidechain, attack "
                      f"{p.mix_value('duck_attack'):g} / release {p.mix_value('duck_release'):g} ms"
                      + (f"; {prof.name} profile" if prof is not None else '') + ')')
        else:
            lg.append("duck: off" + (" (duck=False)" if duck is False else f" (the {prof.name} profile ducks no bed)"))
        c = _depth(carve, p.mix_value('carve_db'))
        if c:
            song.carve(*bed_ids, key=track, freq=p.mix_value('carve_freq'), q=p.mix_value('carve_q'), depth=c)
            lg.append(f"carve: {_names(bed_ids)} up to -{c:g} dB at {p.mix_value('carve_freq'):g} Hz (Q "
                      f"{p.mix_value('carve_q'):g}) while the hero plays (song.carve)")
        else:
            lg.append("carve: off")
    # 4. competitors: static presence dips
    comp_ids = _nodes(competitors)
    if comp_ids:
        g = _depth(dips, prof.dip_db if prof is not None else p.mix_value('dip_db'))
        if g:
            bell = {'freq': p.mix_value('dip_freq'), 'gain': -g, 'q': p.mix_value('dip_q')}
            for c_ in comp_ids:
                mixer.add_eq_dip(song.node(getattr(c_, 'id', c_)), [bell], name='hero_dip')
            lg.append(f"dips: {_names(comp_ids)} {bell['gain']:g} dB at {bell['freq']:g} Hz (Q {bell['q']:g}, "
                      f"eq 'hero_dip')")
        else:
            lg.append("dips: off")
    # 5. rides (the lane is written at compile, when every section is known)
    r = _depth(ride, prof.lead_ride_db if prof is not None else p.mix_value('ride_db'))
    if r:
        info.ride_db = r
        track.add_fx(FX('utility', {'gain': 0.0}, name='hero_ride'))
        lg.append(f"ride: +{info.ride_db:g} dB in the hook sections (utility 'hero_ride'; the lane is written at "
                  f"compile)")
    else:
        lg.append("ride: off" + (" (ride=False)" if ride is False else
                                 f" (the {prof.name} profile rides no lead)" if prof is not None else ''))
    if not throws:
        lg.append("throws: off")
    elif info.echo:
        lg.append("throws: echo throws on the phrase ends (written at compile from the notes the track plays)")
    else:
        lg.append("throws: none (no echo)")
    track.hero = info
    song.add_compile_hook(info._compile)
    return track


def log_lines(song) -> list[str]:
    """Every hero's moves in a song (the static ones and those written by the last compile)."""
    out = []
    for t in song.tracks.values():
        info = getattr(t, 'hero', None)
        if info is not None:
            out += info.lines()
    return out


# ------------------------------------------------------------------------------------------------ playing

def play(track, line, at=0.0, *, lo=None, hi=None, **kw):
    """Play a written line on a hero track like the family's player: velocities from the line (humanize.touch in
    the preset's range, play['vel']; lo / hi override), then the guitar's zone-locked play (hero_guitar.play), the
    synth's perform (hero_synth.perform: detached re-attacks, ties), a plain play for the pianos (arrange them with
    pianist.arrange first) or articulation.perform (legato, vibrato on the long notes, the instrument's
    articulations). kw go to that player. Returns the clip as played."""
    from . import articulation as art
    from .humanize import touch
    from .patterns import as_clip
    info = getattr(track, 'hero', None)
    p = info.preset if info is not None else infer(track)
    v_lo, v_hi = p.play.get('vel', (62, 116))
    lo = v_lo if lo is None else lo
    hi = v_hi if hi is None else hi
    player = p.play.get('player', 'perform')
    if player == 'synth':
        from .patches import hero_synth
        c = hero_synth.perform(as_clip(line), lo=lo, hi=hi, **kw)
        track.play(c, at)
        return c
    c = touch(as_clip(line), lo, hi)
    if player == 'guitar':
        from .patches import hero_guitar
        kw.setdefault('vib', {'depth': 26})
        return hero_guitar.play(track, c, at, **kw)
    if player == 'piano':
        track.play(c, at)
        return c
    kw.setdefault('vib', p.play.get('vib', True))
    return art.perform(track, c, at, **kw)


hero.play = play
hero.build = build
hero.presets = presets
