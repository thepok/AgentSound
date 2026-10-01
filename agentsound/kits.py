"""Kit builder: GM-mapped 'sampler' drum kits from any one-shot collection, Hydrogen and DrumGizmo kits, and
note-named multisample folders.

    inst.kit('samples/hyperreal-linndrum')                                    # a folder of one-shots, any names
    inst.kit('samples/sampleradar-80s-pop-drums/Drum Kits/Kit A', map={'snare': 'Snare03'})
    inst.kit('samples/hydrogen-forzee-stereo')                                 # Hydrogen drumkit.xml
    inst.kit('samples/drumgizmo-drskit', mics={'room': -6, 'overheads': -2})  # DrumGizmo multichannel kit
    inst.multisample('samples/sampleradar-80s-synths/Jupiter Pad')            # files named by note
    kits.build(path) -> (zones, info); kits.describe(path); python -m agentsound kit DIR [--json]

One-shot folders (recursive): every audio file is classified by its name (and its folder names): kick / bd / bass
drum, snare / sd, rim / sidestick, clap, closed / pedal / open / half-open hat, toms (floor, low, mid, high, or
measured pitch), crash, ride, ride bell, china, splash, cowbell, tambourine, shaker, conga, bongo, timbale, agogo,
cabasa, maracas, claves, woodblock, triangle, ... Velocity layers come from the names (v1..v16, pp/p/mp/mf/f/ff,
soft/medium/hard, ghost/accent) and round robins from rr1/take1 markers; numbered files of one sound ('Kick-01'..
'Kick-08') are measured (pitch, decay, loudness): the same drum hit at different strengths becomes velocity layers
(ordered by loudness) with round robins inside a layer, different sounds ('TR 808 Kick 01/02/03') become variants
on the role's other keys (kick 36 then 35, snare 38 then 40, crash 49 then 57, ride 51 then 59) and spare keys.
Hats choke each other; every zone is a one-shot with pitchKeytrack 0. Files no rule recognizes land on spare keys
(88 and up) and are listed; loops / beats / fills are skipped and listed: nothing is dropped silently.

map= overrides / extends the mapping: {'snare': 'Snare03', 40: ['Gated*'], 'clap': None, 'perc': 'Scratch'}: keys by
GM name, MIDI number or note name; values: a file (name, substring, glob, or a list of them: layers / round robins
of one sound), None (nothing on that key), or a dict {'files': ..., 'gain': dB, 'tune': cents, 'pan': -1..1,
'choke': group, 'layers': 'auto'|'velocity'|'rr'|'random'}.
"""

from __future__ import annotations

import array
import fnmatch
import math
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from .theory import ComposeError

__all__ = ['build', 'describe', 'multisample', 'analyze', 'classify', 'GM_NAMES', 'format_info', 'velocity_map']

AUDIO_EXT = ('.wav',)
_CONVERTIBLE = ('.flac', '.aif', '.aiff', '.ogg')   # the downloader converts these to .wav

# --------------------------------------------------------------------------------------------- GM key names

GM_NAMES = {
    35: 'kick2', 36: 'kick', 37: 'rim', 38: 'snare', 39: 'clap', 40: 'snare2', 41: 'tom_lo', 42: 'hat',
    43: 'tom_floor_hi', 44: 'pedal_hat', 45: 'tom_mid', 46: 'open_hat', 47: 'tom_lowmid', 48: 'tom_hi', 49: 'crash',
    50: 'tom_high', 51: 'ride', 52: 'china', 53: 'ride_bell', 54: 'tamb', 55: 'splash', 56: 'cowbell', 57: 'crash2',
    58: 'vibraslap', 59: 'ride2', 60: 'bongo_hi', 61: 'bongo_lo', 62: 'conga_mute', 63: 'conga_hi', 64: 'conga_lo',
    65: 'timbale_hi', 66: 'timbale_lo', 67: 'agogo_hi', 68: 'agogo_lo', 69: 'cabasa', 70: 'maracas',
    71: 'whistle_short', 72: 'whistle_long', 73: 'guiro_short', 74: 'guiro_long', 75: 'claves', 76: 'block_hi',
    77: 'block_lo', 78: 'cuica_mute', 79: 'cuica_open', 80: 'triangle_mute', 81: 'triangle', 82: 'shaker',
    83: 'jingle', 84: 'belltree', 85: 'castanets', 86: 'surdo_mute', 87: 'surdo',
}
_NAME_KEYS = {v: k for k, v in GM_NAMES.items()}
_NAME_KEYS.update({'bd': 36, 'sd': 38, 'rimshot': 37, 'sidestick': 37, 'closed_hat': 42, 'hihat': 42, 'hh': 42,
                   'ohh': 46, 'oh': 46, 'pedal': 44, 'tom_low': 41, 'tom_floor': 41, 'tom_high2': 50,
                   'tambourine': 54, 'cb': 56, 'cp': 39, 'ch': 42, 'lt': 41, 'mt': 45, 'ht': 48, 'cr': 49, 'rd': 51})

# role -> GM keys (tom / bongo / conga ...: in pitch order, see _PITCHED)
ROLE_KEYS = {
    'kick': [36, 35], 'rim': [37], 'snare': [38, 40], 'clap': [39], 'hat_closed': [42], 'hat_pedal': [44],
    'hat_open': [46], 'hat_half': [], 'tom': [41, 43, 45, 47, 48, 50], 'crash': [49, 57], 'ride': [51, 59],
    'ride_bell': [53], 'china': [52], 'splash': [55], 'tambourine': [54], 'cowbell': [56], 'vibraslap': [58],
    'bongo': [60, 61], 'conga': [62, 63, 64], 'timbale': [65, 66], 'agogo': [67, 68], 'cabasa': [69],
    'maracas': [70], 'whistle': [71, 72], 'guiro': [73, 74], 'claves': [75], 'woodblock': [76, 77],
    'cuica': [78, 79], 'triangle': [80, 81], 'shaker': [82], 'jingle': [83], 'belltree': [84], 'castanets': [85],
    'surdo': [86, 87], 'perc': [], 'fx': [],
}
# Pitched roles: keys are filled low -> high ('up') or high -> low ('down') after sorting the sounds by pitch.
_PITCHED = {'tom': 'up', 'bongo': 'down', 'conga': 'down', 'timbale': 'down', 'agogo': 'down', 'woodblock': 'down'}
# Articulation pairs: (first key word, second key word)
_ARTIC = {'whistle': ('short', 'long'), 'guiro': ('short', 'long'), 'cuica': ('mute', 'open'),
          'triangle': ('mute', 'open'), 'surdo': ('mute', 'open')}
HAT_KEYS = (42, 44, 46)
SPARE_KEYS = list(range(88, 128)) + list(range(34, 26, -1)) + list(range(26, -1, -1))

# Drummer's-perspective pans for mono one-shots (scaled by spread=).
_ROLE_PAN = {'hat_closed': -0.45, 'hat_pedal': -0.45, 'hat_open': -0.45, 'hat_half': -0.45, 'crash': -0.35,
             'ride': 0.45, 'ride_bell': 0.45, 'china': 0.55, 'splash': -0.2, 'tambourine': 0.3, 'shaker': -0.3,
             'cowbell': 0.25, 'conga': 0.35, 'bongo': -0.3, 'timbale': 0.3, 'agogo': -0.25, 'cabasa': 0.35,
             'maracas': -0.35, 'claves': 0.2, 'woodblock': -0.2, 'triangle': 0.4, 'jingle': 0.3, 'belltree': -0.4}
_TOM_PANS = {41: 0.45, 43: 0.35, 45: 0.1, 47: -0.05, 48: -0.2, 50: -0.3}

# --------------------------------------------------------------------------------------------- name analysis

_SKIP_WORDS = {'loop', 'loops', 'beat', 'beats', 'bpm', 'fill', 'fills', 'groove', 'grooves', 'break', 'pattern',
               'phrase', 'song', 'demo', 'full', 'mix'}
_DYN = {'ppp': 1, 'pp': 2, 'p': 3, 'mp': 4, 'mf': 5, 'f': 6, 'ff': 7, 'fff': 8, 'ghost': 1, 'soft': 2, 'light': 2,
        'medium': 5, 'hard': 7, 'loud': 7, 'heavy': 7, 'accent': 8, 'acc': 8, 'hardest': 8, 'softest': 1}
_ITALIAN = [('pianissimo', 2), ('mezzo[-_ ]?piano', 4), ('mezzo[-_ ]?forte', 5), ('fortissimo', 7), ('forte', 6),
            ('piano', 3)]
_VEL_RE = re.compile(r'(?:^|[^a-z])(?:v|vl|vel|velo|velocity|dyn|layer|lyr)[ _\-.]?(\d{1,3})(?![0-9])', re.I)
_RR_RE = re.compile(r'(?:^|[^a-z])(?:rr|roundrobin|round[ _-]robin|robin|take|tk|seq|hit)[ _\-.]?(\d{1,3})(?![0-9])', re.I)
_NUM_TAIL = re.compile(r'[ _\-.(\[]*(\d{1,3})[)\]]?$')
_NUM_HEAD = re.compile(r'^(\d{1,3})[ _\-.)]+(?=[A-Za-z])')     # '1-Snare', '12_Kick' (hit index first)
# the snare wires' state ('snares on / off') says nothing about which drum it is ('rack tom - snares off')
_WIRES_RE = re.compile(r'(?i)(?<![a-z])snares?[ _\-]*(?:on|off)(?![a-z])')

HAT = {'hat', 'hats', 'hh', 'hihat', 'hihats', 'hhat', 'hht', 'chh', 'ohh', 'phh', 'hhc', 'hho', 'hhp', 'hhcd',
       'hhod', 'chat', 'ohat', 'cht', 'oht', 'clhh', 'ophh', 'mhat', 'hatc', 'hato', 'hatp', 'clhat', 'ophat',
       'pdhat', 'hfhat', 'hc', 'ho', 'hhclosed', 'hhopen', 'hhpedal', 'oh', 'ph'}
HAT_OPEN = {'open', 'op', 'opn', 'ohh', 'oh', 'hho', 'ohat', 'oht', 'ophh', 'hhod', 'loose', 'hato', 'ophat', 'ho',
            'hhopen', 'opened', 'sizzle'}
HAT_PEDAL = {'pedal', 'pd', 'ped', 'foot', 'ft', 'ph', 'phh', 'fhh', 'hhp', 'chick', 'hatp', 'pdhat', 'stomp',
             'hhpedal', 'splashhat'}
HAT_HALF = {'half', 'hf', 'semi', 'halfopen', 'hfhat', 'mhat', 'semiopen', 'halfopened'}
KICK = {'kick', 'kik', 'kck', 'kic', 'bd', 'bassdrum', 'bdrum', 'kd', 'kickdrum', 'bombo', 'bdr', 'kicks', 'kdrum',
        'bassd', 'bdm'}
SNARE = {'snare', 'snr', 'sn', 'sd', 'sdr', 'snar', 'snares', 'sdrum', 'snaredrum', 'snre', 'snd', 'sna'}
RIM = {'rim', 'rimshot', 'rs', 'rimsh', 'sidestick', 'sdst', 'sst', 'ssth', 'sstl', 'xstick', 'crossstick',
       'rimclick', 'sidestk', 'cross', 'rimsnare', 'side', 'rims'}
_SIDE = {'side', 'sidestick', 'sdst', 'xstick', 'cross', 'crossstick', 'sst', 'ssth', 'sstl', 'rimclick', 'sidestk'}
CLAP = {'clap', 'clp', 'cp', 'handclap', 'claps', 'handclp', 'clapping', 'hands'}
TOM = {'tom', 'toms', 'tm', 'tomtom', 'lt', 'mt', 'ht', 'hitom', 'lotom', 'midtom', 'lowtom', 'hightom', 'rack',
       'racktom', 'floortom', 'lotm', 'hitm', 'mdtm', 'tomh', 'toml', 'tomm', 'tomhh', 'tomll', 'tmrx', 'simmons'}
CRASH = {'crash', 'cr', 'crsh', 'crashcym', 'crashcymbal', 'cc', 'csh', 'cshd', 'crashes', 'trash'}
RIDE = {'ride', 'rd', 'rde', 'ridecym', 'ridecymbal', 'rided', 'rides', 'rdcym'}
CYMBAL = {'cymbal', 'cym', 'cymb', 'cy', 'cymbals', 'cymbl'}
SIMPLE = [
    ('china', {'china', 'chna', 'chinese', 'chinacymbal'}),
    ('splash', {'splash', 'spl', 'splsh'}),
    ('cowbell', {'cowbell', 'cowb', 'cb', 'cow', 'cowbel', 'cowbl', 'bell'}),
    ('tambourine', {'tambourine', 'tamb', 'tamborine', 'tambo', 'tb', 'tambourin', 'tamborin', 'tamburine',
                    'pandeiro'}),
    ('shaker', {'shaker', 'shake', 'shk', 'egg', 'sh', 'shkr', 'shakers', 'eggshaker', 'caxixi', 'ganza'}),
    ('maracas', {'maracas', 'maraca', 'marcas', 'mrc', 'maracs'}),
    ('cabasa', {'cabasa', 'afuche', 'cabassa', 'cab'}),
    ('conga', {'conga', 'congas', 'cng', 'cong', 'tumba', 'quinto', 'lcng', 'mcng', 'hcng', 'congah', 'congahh',
               'congal', 'congall', 'congalll'}),
    ('bongo', {'bongo', 'bongos', 'bong', 'bonga', 'bng'}),
    ('timbale', {'timbale', 'timbales', 'timbal', 'timba', 'timb', 'tmbl', 'timbali'}),
    ('agogo', {'agogo', 'agg', 'agogobell'}),
    ('claves', {'clave', 'claves', 'clv', 'clav', 'klave'}),
    ('woodblock', {'woodblock', 'block', 'wb', 'wood', 'blk', 'woodblk', 'temple'}),
    ('triangle', {'triangle', 'tri', 'trngl', 'trian', 'triang'}),
    ('guiro', {'guiro', 'gro', 'guiros', 'scraper'}),
    ('whistle', {'whistle', 'whistl', 'whstl'}),
    ('vibraslap', {'vibraslap', 'vibra', 'quijada', 'jawbone'}),
    ('cuica', {'cuica'}),
    ('castanets', {'castanet', 'castanets', 'cast'}),
    ('jingle', {'jingle', 'sleigh', 'sleighbells', 'jingles'}),
    ('belltree', {'belltree', 'chimes', 'chime', 'starchim', 'marktree', 'windchime', 'barchimes'}),
    ('surdo', {'surdo'}),
]
PERC = {'perc', 'percussion', 'prc', 'hit', 'knock', 'snap', 'click', 'tick', 'zap', 'blip', 'pop', 'metal', 'tin'}
FX = {'fx', 'sfx', 'noise', 'scratch', 'laser', 'riser', 'sweep', 'impact', 'boom', 'reverse', 'rev', 'vox', 'voice'}

# compact spellings inside run-together names ('CR8KBASS', 'KPRCLHH', 'DR110CHT', 'chhl', 'congall')
_COMPACT = [
    ('hat_open', ('openhat', 'openhh', 'ophat', 'ohat', 'ohh', 'oht', 'hhod', 'hhopen', 'opnhat', 'kprophh')),
    ('hat_pedal', ('pedalhat', 'pdhat', 'pedhat', 'foothat', 'phh', 'hhpedal', 'hhfoot')),
    ('hat_half', ('halfhat', 'hfhat', 'halfopen')),
    ('hat_closed', ('closedhat', 'clhat', 'chat', 'clhh', 'chh', 'cht', 'hhcd', 'hhclosed', 'hihat')),
    ('ride_bell', ('ridebell', 'bellride', 'ridecup', 'cupcym')),
    ('ride', ('ride',)),
    ('china', ('china',)),
    ('splash', ('splash',)),
    ('crash', ('crash', 'cshd', 'crsh', 'cymb', 'cym')),
    ('rim', ('rimshot', 'sidestick', 'rim', 'sdst', 'sst')),
    ('clap', ('handclp', 'clap', 'clp')),
    ('snare', ('snare', 'snar', 'snr', 'sdh', 'sdl')),
    ('kick', ('kick', 'kik', 'bassdrum', 'bass', 'bd')),
    ('conga', ('conga', 'cng')),
    ('bongo', ('bongo',)),
    ('tom', ('tom', 'lotm', 'hitm', 'tm')),
    ('cowbell', ('cowb', 'cowbell')),
    ('tambourine', ('tamb',)),
    ('cabasa', ('cabasa',)),
    ('claves', ('clave', 'clav')),
    ('shaker', ('shaker',)),
    ('maracas', ('maraca',)),
    ('timbale', ('timba',)),
    ('agogo', ('agogo',)),
]

_PITCH_WORDS = {'floor': -3, 'fl': -3, 'ft': -3, 'lowlow': -2, 'll': -2, 'lll': -3, 'lowest': -3, 'low': -1,
                'lo': -1, 'l': -1, 'lt': -1, 'mid': 0, 'med': 0, 'm': 0, 'mt': 0, 'middle': 0, 'high': 1, 'hi': 1,
                'h': 1, 'ht': 1, 'highhigh': 2, 'hh': 2, 'hihi': 2, 'highest': 2, 'top': 2}


def _tokens(text: str) -> list[str]:
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', text)
    text = re.sub(r'([A-Za-z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([A-Za-z])', r'\1 \2', text)
    return [t for t in re.split(r'[^A-Za-z0-9]+', text.lower()) if t]


def _hat_state(toks: set[str], compact: str) -> str:
    if toks & {'opcl', 'clop'} or 'opcl' in compact or 'clop' in compact:
        return 'hat_fx'
    if toks & HAT_PEDAL:
        return 'hat_pedal'
    if toks & HAT_HALF:
        return 'hat_half'
    if toks & HAT_OPEN or 'o' in toks or re.search(r'(open|ohh|ophh|hhod|ohat)', compact):
        return 'hat_open'
    return 'hat_closed'


def classify(name: str, folders: tuple[str, ...] = ()) -> tuple[str | None, int | None, str]:
    """(role, pitch hint, reason) of a file stem, falling back on its folder names (nearest first). The pitch hint
    orders toms / congas / bongos (-3 floor .. +2 highest; None: unknown)."""
    for level, text in enumerate((name, *folders)):
        role, hint = _classify_text(text)
        if role:
            return role, hint, 'name' if level == 0 else f"folder '{text}'"
    return None, None, ''


def _classify_text(text: str) -> tuple[str | None, int | None]:
    bare = _WIRES_RE.sub(' ', text)
    if _tokens(bare):
        text = bare
    toks_list = _tokens(text)
    toks = set(toks_list)
    compact = re.sub(r'[^a-z]', '', text.lower())
    hint = _pitch_hint(toks_list)
    if toks & {'hi', 'high'} and toks & {'hat', 'hats'}:     # 'Hi Hat', 'High Hat'
        return _hat_state(toks - {'hi', 'high'}, compact), None
    if toks & HAT:
        return _hat_state(toks, compact), None
    if toks & {'ride'} and toks & {'bell', 'cup', 'bel'}:
        return 'ride_bell', None
    if toks & {'cup'} and toks & CYMBAL:
        return 'ride_bell', None
    for role, words in (('china', {'china', 'chna', 'chinese'}), ('splash', {'splash', 'spl', 'splsh'})):
        if toks & words:
            return role, None
    if toks & RIDE:
        return 'ride', None
    core = {t for t in toks if not t.isdigit()}
    if toks & (CRASH - {'cr', 'cc'}) or (core and core <= {'cr', 'cc'}):   # 'cr' alone (tidal folders), not 'CR8K...'
        return 'crash', None
    if toks & KICK or ({'bass', 'drum'} <= toks) or ('bass' in toks and not toks - {'bass'} - _generic(toks_list)):
        return 'kick', None
    if toks & SNARE or toks & {'gated'}:
        if _rim_kind(toks):             # 'Snare Rimshot', 'SD Stick', 'Snare X-Stick'
            return 'rim', None
        return 'snare', None
    if toks & RIM or _rim_kind(toks):
        return 'rim', None
    if toks & {'stick', 'sticks'}:      # sticks clicked together (count-in), not a side stick
        return 'perc', None
    if toks & CLAP:
        return 'clap', None
    if toks & TOM or toks & {'floor'}:
        return 'tom', hint
    for role, words in SIMPLE:
        if toks & words:
            if role == 'cowbell' and 'bell' in toks and toks & {'ride', 'tree', 'jingle', 'sleigh', 'tubular'}:
                continue
            return role, (hint if role in _PITCHED else None)
    if toks & CYMBAL:
        return 'crash', None
    if toks & {'flam', 'flams', 'roll', 'drag', 'ruff', 'buzz'}:    # snare rudiments of acoustic kits
        return 'snare', None
    if toks & PERC:
        return 'perc', None
    if toks & FX:
        return 'fx', None
    # run-together names: substring search (longest spellings first within each role)
    for role, subs in _COMPACT:
        for s in subs:
            if s in compact:
                if role == 'kick' and s == 'bass' and ('guitar' in compact or 'synth' in compact):
                    continue
                if role == 'tom':
                    return role, _compact_pitch(compact)
                if role == 'conga':
                    return role, _compact_pitch(compact)
                return role, None
    return None, None


def _rim_kind(toks: set[str]) -> str | None:
    """'side' (side stick / cross stick / rim click: GM 37), 'shot' (rimshot) or None."""
    if toks & _SIDE or {'rim', 'click'} <= toks or {'sd', 'st'} <= toks or ('stick' in toks and toks & ({'x'} | SNARE)):
        return 'side'
    if toks & {'rimshot', 'rimshots', 'rimsh'} or {'rim', 'shot'} <= toks or ('rim' in toks and toks & SNARE):
        return 'shot'
    return None


def _generic(toks: list[str]) -> set[str]:
    return {t for t in toks if t.isdigit() or len(t) <= 2}


def _pitch_hint(toks: list[str]) -> int | None:
    for t in toks:
        if t in _PITCH_WORDS and t not in ('h', 'l', 'm') or (t in ('h', 'l', 'm') and len(toks) > 1):
            return _PITCH_WORDS[t]
    for t in toks:   # 'tomh', 'tomll', 'congahh'
        m = re.fullmatch(r'(?:tom|tm|conga|cng|bongo|timba)(h{1,2}|l{1,3}|m)', t)
        if m:
            s = m.group(1)
            return {'h': 1, 'hh': 2, 'l': -1, 'll': -2, 'lll': -3, 'm': 0}[s]
    return None


def _compact_pitch(compact: str) -> int | None:
    m = re.search(r'(?:tom|tm|conga|cng)(hh|h|lll|ll|l|m)?', compact)
    if m and m.group(1):
        return {'h': 1, 'hh': 2, 'l': -1, 'll': -2, 'lll': -3, 'm': 0}[m.group(1)]
    for w, v in (('hi', 1), ('lo', -1), ('mid', 0), ('floor', -3)):
        if w in compact:
            return v
    return None


def _markers(stem: str) -> tuple[int | None, int | None, str]:
    """(velocity layer marker, round-robin marker, stem without them)."""
    vel = rr = None
    rest = stem
    m = _RR_RE.search(rest)
    if m:
        rr = int(m.group(1))
        rest = rest[:m.start(1)].rstrip(' _-.') + rest[m.end(1):]
        rest = re.sub(r'(?i)(rr|roundrobin|round[ _-]robin|robin|take|tk|seq|hit)$', '', rest.rstrip(' _-.')) or rest
    m = _VEL_RE.search(rest)
    if m:
        vel = int(m.group(1))
        rest = (rest[:m.start()] + rest[m.end():]).strip(' _-.')
    else:
        toks = _tokens(rest)
        dyn = [t for t in toks if t in _DYN]
        ital = next(((w, v) for w, v in _ITALIAN if re.search(r'(?i)(?<![a-z])' + w + r'(?![a-z])', rest)), None)
        if ital and len(toks) > 1:      # Philharmonia-style names: 'flute_A4_025_mezzo-forte_normal'
            vel = ital[1] * 16
            rest = re.sub(r'(?i)(?<![a-z])' + ital[0] + r'(?![a-z])', '', rest).strip(' _-.')
        # a lone 'p'/'f' is a dynamic only next to other words (not 'F' as a note, not a single-letter name)
        elif dyn and (len(dyn[-1]) > 1 or len(toks) > 1):
            vel = _DYN[dyn[-1]] * 16
            rest = re.sub(r'(?i)(?<![a-z])' + re.escape(dyn[-1]) + r'(?![a-z])', '', rest).strip(' _-.')
    return vel, rr, rest


# --------------------------------------------------------------------------------------------- WAV reading

_ANALYSIS: dict[tuple, dict] = {}


def wav_header(path: str) -> dict | None:
    """{'format', 'channels', 'rate', 'bits', 'align', 'data', 'size', 'frames', 'loop', 'cue', 'unity'} of a PCM /
    float WAV; None if it is not one."""
    try:
        with open(path, 'rb') as f:
            head = f.read(12)
            if len(head) < 12 or head[:4] not in (b'RIFF', b'RF64') or head[8:12] != b'WAVE':
                return None
            out: dict = {'loop': None, 'cue': None, 'unity': None}
            total = os.path.getsize(path)
            while True:
                h = f.read(8)
                if len(h) < 8:
                    break
                cid, size = h[:4], struct.unpack('<I', h[4:])[0]
                if cid == b'fmt ':
                    b = f.read(size + (size & 1))
                    fmt, ch, rate = struct.unpack('<HHI', b[:8])
                    align, bits = struct.unpack('<HH', b[12:16])
                    if fmt == 0xFFFE and len(b) >= 26:
                        fmt = struct.unpack('<H', b[24:26])[0]
                    out.update(format=fmt, channels=ch, rate=rate, bits=bits, align=align)
                    continue
                if cid == b'data':
                    pos = f.tell()
                    if size in (0, 0xFFFFFFFF) or pos + size > total:
                        size = total - pos
                    out.update(data=pos, size=size)
                    f.seek(size + (size & 1), 1)
                    continue
                if cid == b'smpl':
                    b = f.read(size + (size & 1))
                    _parse_smpl(b, out)
                    continue
                if cid == b'cue ':
                    b = f.read(size + (size & 1))
                    _parse_cue(b, out)
                    continue
                f.seek(size + (size & 1), 1)
            if 'data' not in out or 'format' not in out or not out.get('align'):
                return None
            out['frames'] = out['size'] // out['align']
            return out
    except (OSError, struct.error):
        return None


def _parse_smpl(b: bytes, out: dict) -> None:
    if len(b) >= 36:
        note, frac = struct.unpack('<II', b[12:20])
        loops = struct.unpack('<I', b[28:32])[0]
        if note <= 127:
            out['unity'] = note + frac / 4294967296.0
        if loops >= 1 and len(b) >= 60:
            _, typ, start, end = struct.unpack('<IIII', b[36:52])
            if end >= start:
                out['loop'] = (start, end + 1, typ)


def _parse_cue(b: bytes, out: dict) -> None:
    """The first cue point's frame: its dwSampleOffset (GrandOrgue's release marker), else its dwPosition."""
    if len(b) >= 4:
        n = struct.unpack('<I', b[:4])[0]
        cues = []
        for i in range(n):
            if 4 + 24 * i + 24 <= len(b):
                _, position, _, _, _, offset = struct.unpack('<II4sIII', b[4 + 24 * i:4 + 24 * i + 24])
                cues.append(offset or position)
        cues = [c for c in cues if c > 0]
        if cues:
            out['cue'] = min(cues)


def read_mono(path: str, seconds: float = 1.5, head: dict | None = None) -> tuple[list[float], int]:
    """The first `seconds` of a WAV as mono floats (channels averaged) and its rate; ([], 0) if unreadable."""
    head = head or wav_header(path)
    if not head or head['format'] not in (1, 3) or head['channels'] < 1:
        return [], 0
    ch, bits, align, rate = head['channels'], head['bits'], head['align'], head['rate']
    frames = min(head['frames'], int(seconds * rate))
    with open(path, 'rb') as f:
        f.seek(head['data'])
        data = f.read(frames * align)
    frames = len(data) // align
    data = data[:frames * align]
    if head['format'] == 3 and bits == 32:
        a = array.array('f')
        a.frombytes(data)
        scale = 1.0
    elif bits == 16:
        a = array.array('h')
        a.frombytes(data)
        scale = 1.0 / 32768.0
    elif bits == 24:
        b16 = bytearray(frames * ch * 2)
        b16[0::2] = data[1::3]
        b16[1::2] = data[2::3]
        a = array.array('h')
        a.frombytes(bytes(b16))
        scale = 1.0 / 32768.0
    elif bits == 32 and head['format'] == 1:
        a = array.array('i')
        a.frombytes(data)
        scale = 1.0 / 2147483648.0
    elif bits == 8:
        a = array.array('B')
        a.frombytes(data)
        return [(v - 128) / 128.0 for v in a[0::ch]], rate
    else:
        return [], 0
    if sys.byteorder != 'little':
        a.byteswap()
    if ch == 1:
        return [v * scale for v in a], rate
    left, right = a[0::ch], a[1::ch]
    s = scale * 0.5
    return [(x + y) * s for x, y in zip(left, right)], rate


def analyze(path: str) -> dict:
    """Features of a one-shot (cached per file): peak / loudness (dB, loudest 50 ms), decay (s to -30 dB after the
    peak, first 1.5 s), pitch (Hz of the low-passed body: tom / kick tuning), brightness (Hz), length (s)."""
    try:
        st = os.stat(path)
    except OSError:
        return {}
    key = (path, st.st_mtime_ns, st.st_size)
    if key in _ANALYSIS:
        return _ANALYSIS[key]
    head = wav_header(path)
    x, rate = read_mono(path, 1.5, head)
    out = {'length': head['frames'] / head['rate'] if head and head.get('rate') else 0.0}
    if not x or rate <= 0:
        out.update(peak=-120.0, loud=-120.0, decay=0.0, pitch=0.0, bright=0.0)
        _ANALYSIS[key] = out
        return out
    peak = max(max(x), -min(x))
    hop = max(1, rate // 200)                       # 5 ms frames
    energies = []
    for i in range(0, len(x) - hop + 1, hop):
        seg = x[i:i + hop]
        energies.append(sum(v * v for v in seg) / hop)
    loud = 0.0
    for i in range(len(energies)):
        w = energies[i:i + 10]
        loud = max(loud, sum(w) / len(w))
    pk = max(range(len(energies)), key=energies.__getitem__) if energies else 0
    floor = energies[pk] * 1e-3 if energies else 0.0   # -30 dB
    end = pk
    while end + 1 < len(energies) and energies[end + 1] > floor:
        end += 1
    decay = (end - pk + 1) * hop / rate
    # body pitch: zero crossings of a 1-pole low-pass (~700 Hz) from 10 ms to 150 ms after the peak
    a = 1.0 - math.exp(-2.0 * math.pi * 700.0 / rate)
    y = 0.0
    start = pk * hop + rate // 100
    stop = min(len(x), pk * hop + int(0.15 * rate))
    thr = peak * 0.003
    crossings, sign, first, last = 0, 0, None, None
    for i in range(max(0, pk * hop), stop):
        y += a * (x[i] - y)
        if i < start:
            continue
        s = 1 if y > thr else (-1 if y < -thr else 0)
        if s and s != sign:
            if sign:
                crossings += 1
                last = i
                if first is None:
                    first = i
            sign = s
    pitch = (crossings - 1) / 2.0 * rate / (last - first) if crossings > 2 and last > first else 0.0
    # brightness: RMS of the first difference / RMS (first 100 ms from the peak)
    seg = x[pk * hop:pk * hop + rate // 10]
    num = sum((seg[i] - seg[i - 1]) ** 2 for i in range(1, len(seg)))
    den = sum(v * v for v in seg) or 1e-20
    bright = math.sqrt(num / den) * rate / (2.0 * math.pi)
    out.update(peak=20.0 * math.log10(max(peak, 1e-6)), loud=10.0 * math.log10(max(loud, 1e-12)), decay=decay,
               pitch=pitch, bright=bright)
    _ANALYSIS[key] = out
    return out


def _alike(a: dict, b: dict) -> bool:
    """Two takes of the same hit: pitch within 5 %, decay within 30 %, level within 2 dB, brightness within 12 %
    and file length within 10 % (drum machine variants differ in tuning, decay or length)."""
    if not a or not b:
        return False
    pa, pb = a.get('pitch', 0.0), b.get('pitch', 0.0)
    if (pa > 20) != (pb > 20) or (pa > 20 and abs(math.log2(pa / pb)) > 0.07):
        return False
    da, db = max(a.get('decay', 0.0), 0.01), max(b.get('decay', 0.0), 0.01)
    ba, bb = max(a.get('bright', 0.0), 1.0), max(b.get('bright', 0.0), 1.0)
    la, lb = max(a.get('length', 0.0), 1e-3), max(b.get('length', 0.0), 1e-3)
    return (abs(math.log2(da / db)) < 0.38 and abs(a.get('loud', 0.0) - b.get('loud', 0.0)) < 2.0
            and abs(math.log2(ba / bb)) < 0.17 and abs(math.log2(la / lb)) < 0.14)


def _alike_take(a: dict, b: dict) -> bool:
    """Two hits of the same acoustic drum at any strength: body pitch within 12 % where it is a clear low body
    (< 250 Hz: kicks, toms), decay and brightness within a factor 2 (both change with the strength of the hit)."""
    if not a or not b:
        return False
    pa, pb = a.get('pitch', 0.0), b.get('pitch', 0.0)
    if 20 < pa < 250 or 20 < pb < 250:
        if not (pa > 20 and pb > 20) or abs(math.log2(pa / pb)) > 0.165:
            return False
    da, db = max(a.get('decay', 0.0), 0.01), max(b.get('decay', 0.0), 0.01)
    ba, bb = max(a.get('bright', 0.0), 1.0), max(b.get('bright', 0.0), 1.0)
    return abs(math.log2(da / db)) <= 1.0 and abs(math.log2(ba / bb)) <= 1.0


# --------------------------------------------------------------------------------------------- paths

def _samples_dir() -> Path:
    from .library import SAMPLES
    return SAMPLES


def resolve(source, caller_file: str | None = None, what: str = 'kit') -> Path:
    """A folder or file: 'samples/<pack>/...' in the sample library, './' / '../' next to the song, absolute, or
    relative to assets/. ComposeError (with the fetch hint for a missing pack) when it does not exist."""
    if isinstance(source, os.PathLike):
        source = os.fspath(source)
    if not isinstance(source, str) or not source.strip():
        raise ComposeError(f"{what}: the path must be a non-empty string, got {source!r}")
    from .sfz import ASSETS
    text = source.strip().replace('\\', '/').rstrip('/')
    cands: list[Path] = []
    if text.startswith(('./', '../')):
        if not caller_file:
            raise ComposeError(f"{what}: {text!r} is relative to the song file, but the caller has no __file__")
        cands.append(Path(os.path.dirname(os.path.abspath(caller_file))) / text)
    elif os.path.isabs(text):
        cands.append(Path(text))
    elif text.startswith('samples/'):
        cands += [_samples_dir() / text[len('samples/'):], ASSETS / text]
    else:
        cands += [ASSETS / text, _samples_dir() / text]
    for c in cands:
        if c.exists():
            return Path(os.path.normpath(c))
    hint = ''
    if text.startswith('samples/'):
        parts = text.split('/')
        pack = parts[1] if len(parts) > 1 else ''
        pdir = _samples_dir() / pack
        if pack and not (pdir / 'SOURCE.json').is_file():
            hint = f"; pack {pack!r} is not installed: python -m agentsound samples fetch {pack}"
        elif pack:
            # the nearest existing folder and what it holds
            here = pdir
            for p in parts[2:]:
                nxt = next((c for c in here.iterdir() if c.name.lower() == p.lower()), None) if here.is_dir() else None
                if nxt is None:
                    break
                here = nxt
            subs = sorted(c.name for c in here.iterdir() if c.is_dir())[:15] if here.is_dir() else []
            hint = f"; {here.relative_to(_samples_dir()).as_posix()}/ has: {', '.join(subs) or 'no folders'}"
    raise ComposeError(f"{what}: {text!r} not found (looked at {', '.join(str(c) for c in cands)}){hint}")


def _find_file(base: Path, rel: str) -> str | None:
    from .sfz import _FINDER
    return _FINDER.find(os.path.normpath(os.path.join(str(base), rel.replace('\\', '/'))))


def _audio_files(root: Path) -> list[Path]:
    out = []
    for dirpath, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            if f.lower().endswith(AUDIO_EXT):
                out.append(Path(dirpath) / f)
    return out


# --------------------------------------------------------------------------------------------- sounds

class _Sound:
    """One drum sound: its files as velocity layers (soft -> loud) of round robins, and where it goes."""

    def __init__(self, role: str | None, label: str, layers: list[list[dict]], hint: int | None = None):
        self.role = role
        self.label = label
        self.layers = layers                      # [[{'file', 'gain', 'tune', 'channels', 'vello', 'velhi'}, ...]]
        self.hint = hint
        self.key: int | None = None
        self.gain = 0.0
        self.tune = 0.0
        self.pan: float | None = None
        self.choke = 0
        self.filled_from: int | None = None
        self.velranges: list[tuple[int, int]] | None = None   # explicit (Hydrogen / DrumGizmo)
        self.rr_mode = 'cycle'
        self.source = ''

    def files(self) -> list[str]:
        return [f['file'] for layer in self.layers for f in layer]

    def feature(self, name: str) -> float:
        vals = [analyze(f).get(name, 0.0) for f in self.files()[:3]]
        vals = [v for v in vals if v]
        return sorted(vals)[len(vals) // 2] if vals else 0.0


def _order_layers(entries: list[dict], mode: str) -> list[list[dict]]:
    """Velocity layers (soft -> loud) of one sound's files: by velocity markers, else by measured loudness; round
    robins inside a layer by rr markers or near-equal loudness. mode: 'auto' | 'velocity' | 'rr' | 'random'."""
    if len(entries) == 1:
        return [entries]
    if mode in ('rr', 'random'):
        return [sorted(entries, key=lambda e: (e.get('rr') or 0, e['file']))]
    if mode == 'auto' and any(e.get('vel') is not None for e in entries):
        groups: dict[int, list[dict]] = {}
        for e in entries:
            groups.setdefault(e.get('vel') if e.get('vel') is not None else -1, []).append(e)
        if -1 in groups and len(groups) > 1:       # unmarked files join by loudness later: put them in the middle
            loose = groups.pop(-1)
            mid = sorted(groups)[len(groups) // 2]
            groups[mid] += loose
        return [sorted(groups[k], key=lambda e: (e.get('rr') or 0, e['file'])) for k in sorted(groups)]
    if mode == 'auto' and all(e.get('rr') is not None for e in entries):
        return [sorted(entries, key=lambda e: e['rr'])]
    loud = sorted(entries, key=lambda e: (analyze(e['file']).get('loud', -120.0), e['file']))
    levels = [analyze(e['file']).get('loud', -120.0) for e in loud]
    if mode == 'auto' and levels[-1] - levels[0] < 4.0:
        return [sorted(entries, key=lambda e: e['file'])]       # all about equally loud: round robins
    layers: list[list[dict]] = [[loud[0]]]
    base = levels[0]
    for e, lv in zip(loud[1:], levels[1:]):
        if mode == 'auto' and lv - base < 1.5:
            layers[-1].append(e)
        else:
            layers.append([e])
            base = lv
    while len(layers) > 12:                       # merge the two closest neighbours
        gaps = [analyze(layers[i + 1][0]['file']).get('loud', 0) - analyze(layers[i][-1]['file']).get('loud', 0)
                for i in range(len(layers) - 1)]
        i = gaps.index(min(gaps))
        layers[i] = layers[i] + layers.pop(i + 1)
    return layers


def _cluster(entries: list[dict], loose: bool = False) -> list[list[dict]]:
    """Numbered files of one name: near-identical takes (same pitch, decay and level) are round robins of one
    sound, anything else is a different sound (drum machine collections: 'Kick 01', 'Kick 02'). loose: takes of an
    acoustic drum (natural levels): the same body pitch (kicks / toms), decay and brightness within a factor 2 are
    one drum at any level and length."""
    clusters: list[list[dict]] = []
    alike = _alike_take if loose else _alike
    for e in sorted(entries, key=lambda e: e['file']):
        fa = analyze(e['file'])
        for c in clusters:
            if alike(analyze(c[0]['file']), fa):
                c.append(e)
                break
        else:
            clusters.append([e])
    return clusters


# --------------------------------------------------------------------------------------------- one-shot folders

def _oneshot_sounds(files: list[Path], root: Path, numbered: str, skipped: list, unmapped: list) -> list[_Sound]:
    # tokens every file of a folder shares ('80PD_KitA-...', 'CYCdh_K1close_...', 'TR 808 ...') name the kit, not
    # the drum: they are left out of the classification (unless nothing is left)
    by_dir: dict[str, list[set[str]]] = {}
    for f in files:
        by_dir.setdefault(f.parent.as_posix(), []).append(set(_tokens(f.stem)))
    common = {d: (set.intersection(*ts) if len(ts) >= 3 else set()) for d, ts in by_dir.items()}
    # hit indices in front ('1-Snare' .. '56-Snare': DrumGizmo exports, MuldjordKit): a run of 3+ files of one name
    # numbered from 1 or 2 is one drum's hits (not '808 Kick', '909 Kick': machine names)
    heads: dict[tuple[str, str], list[int]] = {}
    for f in files:
        m = _NUM_HEAD.match(f.stem)
        if m and not _NUM_TAIL.search(f.stem[m.end():]):
            heads.setdefault((f.parent.as_posix(), f.stem[m.end():].lower()), []).append(int(m.group(1)))
    runs = {k for k, v in heads.items() if len(v) >= 3 and min(v) <= 2 and max(v) <= 2 * len(v) + 8}
    fams: dict[tuple, list[dict]] = {}
    order: list[tuple] = []
    for f in files:
        rel = f.relative_to(root)
        stem = f.stem
        head = _NUM_HEAD.match(stem)
        if head and (f.parent.as_posix(), stem[head.end():].lower()) in runs:
            stem = stem[head.end():] + ' ' + head.group(1)        # '12-Snare' -> 'Snare 12'
        folders = tuple(reversed(rel.parts[:-1]))
        toks = set(_tokens(stem)) | {t for p in rel.parts[:-1] for t in _tokens(p)}
        if toks & _SKIP_WORDS or re.search(r'\d{2,3} ?bpm|\[\d{2,3}\]', rel.as_posix(), re.I):
            skipped.append((rel.as_posix(), 'loop / beat / fill'))
            continue
        vel, rr, rest = _markers(stem)
        m = _NUM_TAIL.search(rest)
        num = int(m.group(1)) if m and m.start() > 0 else None
        base = rest[:m.start()].rstrip(' _-.([') if num is not None else rest
        shared = common.get(f.parent.as_posix(), set())
        role = hint = None
        why = ''
        own = ' '.join(t for t in _tokens(base or stem) if t not in shared) if shared else ''
        if own:     # the file's own words decide; the shared kit-name words only when the own words are all shared
            role, hint, why = classify(own, folders)
        else:
            role, hint, why = classify(base or stem, folders)
            if role is None:
                role, hint, why = classify(stem, folders)
        e = {'file': str(f), 'rel': rel.as_posix(), 'vel': vel, 'rr': rr, 'num': num, 'hint': hint, 'why': why}
        fam = (role, rel.parent.as_posix(), base.lower() if base else stem.lower())
        if fam not in fams:
            fams[fam] = []
            order.append(fam)
        fams[fam].append(e)
    sounds: list[_Sound] = []
    for fam in order:
        role = fam[0]
        entries = fams[fam]
        marked = any(e['vel'] is not None or e['rr'] is not None for e in entries)
        numbered_only = not marked and len(entries) > 1
        if numbered_only and numbered == 'auto':
            # Hits of one drum recorded at several strengths keep their natural levels (a wide loudness and peak
            # spread): velocity layers. Normalized collections ('Kick 01'..'Kick 03' of a drum machine, peaks all
            # near 0 dBFS) are different sounds, unless two are near-identical takes (round robin).
            # Takes of an acoustic drum at one strength keep natural, uneven peaks: near-alike ones (body pitch,
            # decay, brightness) are one drum (round robins / layers), whatever their exact level and length.
            feats = [analyze(e['file']) for e in entries]
            loud = [f.get('loud', -120.0) for f in feats]
            peak = [f.get('peak', -120.0) for f in feats]
            dynamic = max(loud) - min(loud) >= 6.0 and max(peak) - min(peak) >= 4.0
            # normalized: most peaks at the same level (a collection's gain-matched variants)
            normalized = sum(p >= max(peak) - 0.2 for p in peak) >= max(2.0, len(peak) / 2.0)
            takes = not normalized and len(entries) >= 4
            if dynamic:
                groups = [entries]
            elif role == 'tom' and all(e['hint'] is None for e in entries) and not takes:
                groups = [[e] for e in entries]            # 'Tom 01', 'Tom 02': different drums
            else:
                groups = _cluster(entries, loose=takes)
        elif numbered_only:
            groups = [[e] for e in entries] if numbered == 'variants' else [entries]
        else:
            groups = [entries]
        for g in groups:
            mode = numbered if numbered in ('layers', 'rr', 'random') else 'auto'
            if mode == 'layers':
                mode = 'velocity'
            label = os.path.basename(g[0]['rel']) if len(g) == 1 else f"{g[0]['rel']} (+{len(g) - 1})"
            s = _Sound(role, label, _order_layers([dict(e) for e in g], mode), g[0]['hint'])
            s.rr_mode = 'random' if numbered == 'random' else 'cycle'
            s.source = g[0]['why']
            if role is None:
                unmapped.append(label)
            sounds.append(s)
    return sounds


# --------------------------------------------------------------------------------------------- Hydrogen

def _xml(path: Path) -> ET.Element:
    try:
        root = ET.parse(str(path)).getroot()
    except ET.ParseError as e:
        raise ComposeError(f"kit: {path}: not valid XML ({e})") from None
    for el in root.iter():
        if isinstance(el.tag, str) and '}' in el.tag:
            el.tag = el.tag.split('}', 1)[1]
    return root


def _num(el: ET.Element | None, tag: str, default: float) -> float:
    if el is None:
        return default
    c = el.find(tag)
    try:
        return float(c.text) if c is not None and c.text and c.text.strip() else default
    except ValueError:
        return default


def _text(el: ET.Element | None, tag: str, default: str = '') -> str:
    c = el.find(tag) if el is not None else None
    return c.text.strip() if c is not None and c.text else default


def _hydrogen_sounds(xml: Path, skipped: list, unmapped: list, info: dict) -> list[_Sound]:
    root = _xml(xml)
    info['name'] = _text(root, 'name', xml.parent.name)
    info['license'] = _text(root, 'license')
    info['author'] = _text(root, 'author')
    base = xml.parent
    sounds = []
    ilist = root.find('instrumentList')
    for ins in (ilist if ilist is not None else []):
        if ins.tag != 'instrument':
            continue
        name = _text(ins, 'name', 'instrument')
        layers = list(ins.iter('layer'))
        if not layers:
            continue
        gain = _num(ins, 'gain', 1.0) * _num(ins, 'volume', 1.0)
        entries = []
        missing = []
        for ly in layers:
            fn = _text(ly, 'filename')
            path = _find_file(base, fn) if fn else None
            if not path:
                missing.append(fn)
                continue
            lo, hi = _num(ly, 'min', 0.0), _num(ly, 'max', 1.0)
            g = _num(ly, 'gain', 1.0) * gain
            entries.append({'file': path, 'lo': lo, 'hi': hi, 'gain': 20.0 * math.log10(max(g, 1e-6)),
                            'tune': _num(ly, 'pitch', 0.0) * 100.0})
        if missing:
            skipped.append((f"{name}: " + ', '.join(missing[:4]), 'file not found'))
        if not entries:
            continue
        # layers with the same velocity range play in turn (round robin), otherwise by range
        by_range: dict[tuple, list[dict]] = {}
        for e in entries:
            by_range.setdefault((round(e['lo'], 4), round(e['hi'], 4)), []).append(e)
        ranges = sorted(by_range)
        s = _Sound(None, name, [by_range[r] for r in ranges])
        vr = []
        for lo, hi in ranges:
            vlo = max(0, math.ceil(lo * 127 - 1e-9))
            vhi = 127 if hi >= 1.0 - 1e-9 else max(vlo, math.ceil(hi * 127 - 1e-9) - 1)
            vr.append((vlo, vhi))
        s.velranges = vr
        role, hint, _ = classify(name)
        s.role, s.hint = role, hint
        s.source = 'Hydrogen'
        mg = int(_num(ins, 'muteGroup', -1))
        if mg >= 0:
            s.choke = 20 + mg
        if ins.find('pan') is not None:
            s.pan = max(-1.0, min(1.0, _num(ins, 'pan', 0.0)))
        else:
            pl, pr = _num(ins, 'pan_L', 1.0), _num(ins, 'pan_R', 1.0)
            if max(pl, pr) > 0 and abs(pl - pr) > 1e-6:
                s.pan = max(-1.0, min(1.0, (pr - pl) / max(pl, pr)))
        note = ins.find('midiOutNote')
        s.midi = int(float(note.text)) if note is not None and note.text and note.text.strip() else None
        s.index = len(sounds)
        if role is None:
            unmapped.append(name)
        sounds.append(s)
    return sounds


# --------------------------------------------------------------------------------------------- DrumGizmo

def _mic_kind(name: str) -> tuple[str, str]:
    """(category, side) of a DrumGizmo channel name: category room / overheads / kick / snare / hihat / toms /
    ride / cymbals / other; side 'L', 'R' or ''."""
    n = name.lower()
    c = re.sub(r'[^a-z0-9]', '', n)
    side = ''
    for s_, word in (('L', 'left'), ('R', 'right')):
        if (c.endswith(word) or re.search(r'(^|[^A-Za-z]|[a-z])' + s_ + r'$', name)
                or (len(name) >= 3 and name.isupper() and name.endswith(s_))
                or re.search(r'(^|[^a-z])' + s_.lower() + r'$', n)):
            side = s_
            break
    if 'amb' in c or 'room' in c:
        return 'room', side
    if c.startswith('oh') or 'overhead' in c or c.startswith('over'):
        return 'overheads', side
    if re.search(r'kick|kdrum|bassdrum|^bd|^kd', c):
        return 'kick', side
    if re.search(r'snare|^sn|^sd', c):
        return 'snare', side
    if re.search(r'hihat|^hh|hat', c):
        return 'hihat', side
    if re.search(r'tom|floor', c):
        return 'toms', side
    if 'ride' in c:
        return 'ride', side
    if re.search(r'crash|cym|china|splash', c):
        return 'cymbals', side
    return 'other', side


_CLOSE = ('kick', 'snare', 'hihat', 'toms', 'ride', 'cymbals', 'other')
_CLOSE_PAN = {'kick': 0.0, 'snare': -0.05, 'hihat': -0.45, 'ride': 0.45, 'cymbals': -0.3, 'other': 0.0}


def _mic_mix(channels: list[str], mics: dict | None, where: str) -> dict[str, tuple[float, float] | None]:
    """Left / right gains per kit channel (None: muted). mics: {name: dB or None}: a channel name, a category
    (close, overheads, room, kick, snare, hihat, toms, ride, cymbals) or 'all'."""
    kinds = {ch: _mic_kind(ch) for ch in channels}
    toms = sorted((ch for ch in channels if kinds[ch][0] == 'toms'), key=lambda c: [int(d) for d in re.findall(r'\d+', c)] or [0])
    tom_pan = {ch: (-0.3 + 0.75 * i / max(1, len(toms) - 1)) if len(toms) > 1 else 0.1 for i, ch in enumerate(toms)}
    mics = dict(mics or {})
    names = {'all', 'close', 'overheads', 'room', *_CLOSE, *channels}
    lower = {n.lower(): n for n in names}
    for k in list(mics):
        if k not in names:
            if isinstance(k, str) and k.lower() in lower:
                mics[lower[k.lower()]] = mics.pop(k)
            else:
                raise ComposeError(f"{where}: unknown microphone {k!r}; this kit has channels {', '.join(channels)} "
                                   f"and the groups all, close, overheads, room, kick, snare, hihat, toms, ride, cymbals")
    for k, v in mics.items():
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float)) or not -60 <= v <= 24):
            raise ComposeError(f"{where}: mics[{k!r}] must be a gain in dB (-60..24) or None (muted), got {v!r}")
    out: dict[str, tuple[float, float] | None] = {}
    for ch in channels:
        kind, side = kinds[ch]
        group = 'close' if kind in _CLOSE else kind
        db = 0.0
        muted = False
        for key in ('all', group, kind, ch):     # most specific wins
            if key in mics:
                if mics[key] is None:
                    muted = True
                else:
                    muted = False
                    db = float(mics[key])
        if muted:
            out[ch] = None
            continue
        g = 10.0 ** (db / 20.0)
        if kind in ('room', 'overheads') or (kind in ('ride', 'cymbals') and side):
            pan = -1.0 if side == 'L' else (1.0 if side == 'R' else 0.0)
        else:
            pan = tom_pan.get(ch, _CLOSE_PAN.get(kind, 0.0))
        th = (pan + 1.0) * math.pi / 4.0
        out[ch] = (g * math.cos(th), g * math.sin(th))
    return out


def _dg_kits(folder: Path) -> list[Path]:
    out = []
    for p in sorted(folder.glob('*.xml')):
        try:
            with open(p, 'rb') as f:
                head = f.read(600).decode('utf-8', 'replace')
        except OSError:
            continue
        if re.search(r'<drumkit[\s>]', head):
            out.append(p)
    return out


def _dg_sounds(xml: Path, mics: dict | None, skipped: list, unmapped: list, info: dict) -> list[_Sound]:
    root = _xml(xml)
    base = xml.parent
    info['name'] = root.get('name', xml.stem)
    chans = [c.get('name') for c in root.iter('channel') if c.get('name')]
    info['channels'] = chans
    mix = _mic_mix(chans, mics, f"kit {xml.name}")
    info['mix'] = {ch: (None if g is None else [round(g[0], 4), round(g[1], 4)]) for ch, g in mix.items()}
    # the kit's MIDI map (Midimap*.xml next to the kit; the one named like the kit first)
    maps = sorted(base.glob('[Mm]idimap*.xml'))
    suffix = xml.stem.split('_', 1)[1].lower() if '_' in xml.stem else ''
    mapfile = next((m for m in maps if suffix and suffix in m.stem.lower()), maps[0] if maps else None)
    notes: dict[str, list[int]] = {}
    if mapfile is not None:
        for m in _xml(mapfile).iter('map'):
            try:
                notes.setdefault(m.get('instr', ''), []).append(int(m.get('note', '')))
            except ValueError:
                pass
        info['midimap'] = mapfile.name
    sounds = []
    groups: dict[str, int] = {}
    for ins in root.iter('instrument'):
        name, rel = ins.get('name', ''), ins.get('file', '')
        if not rel:
            continue
        ipath = _find_file(base, rel)
        if not ipath:
            skipped.append((name, f"instrument file {rel} not found"))
            continue
        cmap = {c.get('in'): c.get('out') for c in ins.iter('channelmap') if c.get('in')}
        iroot = _xml(Path(ipath))
        samples = []
        for smp in iroot.iter('sample'):
            try:
                power = float(smp.get('power', '0'))
            except ValueError:
                power = 0.0
            per_file: dict[str, list] = {}
            for af in smp.iter('audiofile'):
                ch = cmap.get(af.get('channel'), af.get('channel'))
                g = mix.get(ch)
                f = af.get('file')
                if g is None or not f:
                    continue
                path = _find_file(Path(ipath).parent, f)
                if not path:
                    skipped.append((f"{name}/{smp.get('name')}", f"{f} not found"))
                    continue
                try:
                    fc = int(af.get('filechannel', '1')) - 1
                except ValueError:
                    fc = 0
                per_file.setdefault(path, []).append([fc, round(g[0], 5), round(g[1], 5)])
            if per_file:
                samples.append((power, smp.get('name', ''), per_file))
        if not samples:
            skipped.append((name, 'no playable samples (all its microphones muted?)'))
            continue
        samples.sort(key=lambda s: (s[0], s[1]))
        layers = _power_layers(samples)
        s = _Sound(None, name, [[{'file': p, 'channels': sorted(chs), 'group': sname}
                                 for (_, sname, files) in layer for p, chs in files.items()] for layer in layers])
        # zones of one hit (one file per mic group) share a round-robin slot: remember the hit count per layer
        s.hits = [len(layer) for layer in layers]
        s.velranges = _even_ranges(len(layers))
        role, hint, _ = classify(name)
        s.role, s.hint = role, hint
        s.dg_notes = notes.get(name, [])
        s.source = 'DrumGizmo'
        grp = ins.get('group')
        if grp:
            s.choke = groups.setdefault(grp, 40 + len(groups))
        if role is None and not s.dg_notes:
            unmapped.append(name)
        sounds.append(s)
    return sounds


def _power_layers(samples: list) -> list[list]:
    """DrumGizmo hits (sorted by power) -> velocity layers of round robins: bands ~2.5 dB wide in power."""
    db = [10.0 * math.log10(max(p, 1e-12)) for p, _, _ in samples]
    lo, hi = db[0], db[-1]
    n = max(1, min(16, int(round((hi - lo) / 2.5)) + 1, len(samples)))
    bands: list[list] = [[] for _ in range(n)]
    for s, d in zip(samples, db):
        i = 0 if hi - lo < 1e-9 else min(n - 1, int((d - lo) / (hi - lo) * n))
        bands[i].append(s)
    return [b for b in bands if b]


def _even_ranges(n: int) -> list[tuple[int, int]]:
    return [(0 if i == 0 else round(128 * i / n), 127 if i == n - 1 else round(128 * (i + 1) / n) - 1) for i in range(n)]


# --------------------------------------------------------------------------------------------- key assignment

def _assign(sounds: list[_Sound], fill: bool, notes: list[str], extras: bool = True,
            unused: list | None = None) -> dict[int, list[_Sound]]:
    keys: dict[int, list[_Sound]] = {}
    by_role: dict[str, list[_Sound]] = {}
    for s in sounds:
        if s.key is not None:
            keys.setdefault(s.key, []).append(s)
        elif s.role in ROLE_KEYS:
            by_role.setdefault(s.role, []).append(s)
    spare = [k for k in SPARE_KEYS]
    leftovers: list[_Sound] = []
    # an acoustic kit with a side stick and a rimshot: the side stick on 37, the rimshot on 40 (snare 2)
    rims = _prefer_main(by_role.get('rim', []), 'rim')
    shot = None
    if len(rims) > 1 and 40 not in keys:
        shots = [r for r in rims[1:] if _rim_kind(set(_tokens(r.label))) == 'shot']
        if shots:
            shot = shots[0]
        elif _rim_kind(set(_tokens(rims[0].label))) == 'side':
            shot = rims[1]
    if shot is not None:
        shot.key = 40
        keys.setdefault(40, []).append(shot)
        by_role['rim'] = [r for r in by_role['rim'] if r is not shot]
    for role, group in by_role.items():
        slots = [k for k in ROLE_KEYS[role] if k not in keys]
        if role in _PITCHED:
            group = _sort_pitched(group, _PITCHED[role])
            if role == 'tom' and len(group) < len(slots):
                floor = group[0].hint is not None and group[0].hint <= -2      # the lowest is a floor tom
                pick = {1: [45], 2: [41, 48] if floor else [45, 48], 3: [41, 45, 48], 4: [41, 45, 48, 50],
                        5: [41, 43, 45, 48, 50]}[len(group)]
                slots = [k for k in pick if k in slots] or slots
            elif role == 'conga' and len(group) < len(slots):
                slots = [k for k in (63, 64) if k in slots][:len(group)] or slots   # open high, low (62 = muted)
        elif role in _ARTIC:
            a, b = _ARTIC[role]
            group = sorted(group, key=lambda s: (0 if a in s.label.lower() else 1 if b in s.label.lower() else 2))
            if len(group) == 1 and b in ('open', 'long') and len(slots) == 2:
                slots = slots[1:]                       # a lone triangle / surdo is the open one
        elif role in ('crash', 'ride', 'kick', 'snare', 'rim'):
            group = _prefer_main(group, role)
        for s, k in zip(group, slots):
            s.key = k
            keys.setdefault(k, []).append(s)
        leftovers += group[len(slots):]
    for s in sounds:
        if s.key is None and s not in leftovers:
            leftovers.append(s)
    for s in leftovers:
        if not extras:
            if unused is not None and s.label != '(reserved)':
                unused.append(s.label)
            continue
        while spare and spare[0] in keys:
            spare.pop(0)
        if not spare:
            notes.append(f"no free key left for {s.label}")
            continue
        s.key = spare.pop(0)
        keys.setdefault(s.key, []).append(s)
    if fill:
        _fill(keys)
    return keys


def _prefer_main(group: list[_Sound], role: str) -> list[_Sound]:
    """The main sound of a role first: plain names before rimshots / flams / 'snares off' / 'ghost' variants; for
    the rim key (GM side stick) side-stick names before rimshots."""
    odd = {'flam', 'flams', 'roll', 'off', 'rim', 'ghost', 'brush', 'edge', 'choke', 'fx', 'rev', 'drag', 'buzz',
           'swirl', 'mute', 'grab', 'stop', 'ruff'}

    def rank(s: _Sound) -> tuple:
        toks = set(_tokens(s.label))
        if role == 'rim':
            return ({'side': 0, None: 1, 'shot': 2}[_rim_kind(toks)], -len(s.files()))
        return (1 if toks & odd else 0, -len(s.files()))
    return sorted(group, key=rank)


def _sort_pitched(group: list[_Sound], direction: str) -> list[_Sound]:
    """Low -> high ('up') or high -> low: by the names' pitch words (an unqualified one counts as 'mid'), ties and
    unnamed ones by measured body pitch."""
    if any(s.hint is not None for s in group):
        out = sorted(group, key=lambda s: (s.hint if s.hint is not None else 0, s.feature('pitch') or 0.0, s.label))
    else:
        out = sorted(group, key=lambda s: (s.feature('pitch') or 0.0, s.label))
    return out if direction == 'up' else list(reversed(out))


def _fill(keys: dict[int, list[_Sound]]) -> None:
    """Empty GM keys a song commonly uses, from their nearest relative: toms (retuned), kick2, pedal hat, crash2,
    ride2."""
    toms = [41, 43, 45, 47, 48, 50]
    have = [k for k in toms if k in keys and keys[k][0].filled_from is None]
    if have:
        for k in toms:
            if k in keys:
                continue
            src = min(have, key=lambda h: (abs(toms.index(h) - toms.index(k)), -h))
            steps = toms.index(k) - toms.index(src)
            keys[k] = [_filled(s, k, src, tune=max(-450.0, min(450.0, 150.0 * steps))) for s in keys[src]]
    for k, src, gain, tune in ((35, 36, 0.0, 0.0), (44, 42, -4.0, 0.0), (57, 49, -1.0, 80.0), (59, 51, 0.0, 0.0)):
        if k not in keys and src in keys and keys[src][0].filled_from is None:
            keys[k] = [_filled(s, k, src, gain=gain, tune=tune) for s in keys[src]]


def _filled(s: _Sound, key: int, src: int, gain: float = 0.0, tune: float = 0.0) -> _Sound:
    c = _Sound(s.role, s.label, s.layers, s.hint)
    c.__dict__.update({k: v for k, v in s.__dict__.items() if k not in ('key', 'filled_from', 'gain', 'tune')})
    c.key, c.filled_from, c.gain, c.tune = key, src, s.gain + gain, s.tune + tune
    if key in _TOM_PANS and s.pan is not None and s.role == 'tom':
        c.pan = s.pan
    return c


# --------------------------------------------------------------------------------------------- map= overrides

def _key_of(k, where: str) -> int:
    if isinstance(k, bool):
        raise ComposeError(f"{where}: bad key {k!r}")
    if isinstance(k, int):
        if 0 <= k <= 127:
            return k
        raise ComposeError(f"{where}: key {k} is outside 0..127")
    if isinstance(k, str):
        t = k.strip().lower()
        if t in _NAME_KEYS:
            return _NAME_KEYS[t]
        from .patterns import DRUMS
        if t in DRUMS:
            return DRUMS[t]
        try:
            from .theory import note
            return note(k)
        except ComposeError:
            pass
        names = sorted(set(GM_NAMES.values()))
        raise ComposeError(f"{where}: unknown key {k!r}; use a MIDI number, a note name or a drum name: "
                           f"{', '.join(names)}")
    raise ComposeError(f"{where}: bad key {k!r}")


def _match(pattern: str, files: list[Path], root: Path) -> list[Path]:
    p = pattern.replace('\\', '/').lower()
    rels = [(f, f.relative_to(root).as_posix().lower()) for f in files]
    exact = [f for f, r in rels if r == p or os.path.basename(r) == p or os.path.splitext(os.path.basename(r))[0] == p]
    if exact:
        return exact
    if any(c in p for c in '*?['):
        return [f for f, r in rels if fnmatch.fnmatch(r, p) or fnmatch.fnmatch(os.path.basename(r), p)
                or fnmatch.fnmatch(os.path.splitext(os.path.basename(r))[0], p)]
    return [f for f, r in rels if p in r]


def _rel(f: Path, root: Path) -> str:
    try:
        return f.relative_to(root).as_posix()
    except ValueError:
        return f.name


def _apply_map(mapping: dict, files: list[Path], root: Path, where: str,
               caller_file: str | None = None) -> tuple[list[_Sound], set[int], set[str]]:
    """Sounds forced by map= (with their keys), keys map= leaves empty, files map= used. A value that is a path
    ('samples/<pack>/...', './x.wav', absolute) takes that file (or every WAV of that folder) from anywhere."""
    if not isinstance(mapping, dict):
        raise ComposeError(f"{where}: map= must be a dict like {{'snare': 'Snare03', 40: ['Gated*'], 'clap': None}}")
    sounds, empty, used = [], set(), set()
    for k, v in mapping.items():
        key = _key_of(k, f"{where} map key")
        if v is None:
            empty.add(key)
            continue
        opts = {}
        if isinstance(v, dict):
            unknown = set(v) - {'files', 'gain', 'tune', 'pan', 'choke', 'layers'}
            if unknown or 'files' not in v:
                raise ComposeError(f"{where}: map[{k!r}] dict needs 'files' and may have gain, tune, pan, choke, layers "
                                   f"(unknown: {sorted(unknown)})")
            opts = v
            v = v['files']
        pats = [v] if isinstance(v, (str, os.PathLike)) else v
        if not isinstance(pats, (list, tuple)) or not pats or not all(isinstance(p, (str, os.PathLike)) for p in pats):
            raise ComposeError(f"{where}: map[{k!r}] must be a file name / pattern, a list of them, a dict or None")
        hits: list[Path] = []
        for p in pats:
            text = os.fspath(p).replace(chr(92), '/')
            if text.startswith(('samples/', './', '../')) or os.path.isabs(text):
                found = resolve(text, caller_file, f"{where} map[{k!r}]")
                got = _audio_files(found) if found.is_dir() else [found]
            else:
                got = _match(text, files, root)
            if not got:
                import difflib
                names = [f.relative_to(root).as_posix() for f in files]
                close = difflib.get_close_matches(os.fspath(p), names, n=5, cutoff=0.3)
                raise ComposeError(f"{where}: map[{k!r}]: no file matches {os.fspath(p)!r}"
                                   + (f"; close: {', '.join(close)}" if close else f" ({len(files)} files in {root})"))
            hits += [g for g in got if g not in hits]
        mode = opts.get('layers', 'auto')
        if mode not in ('auto', 'velocity', 'rr', 'random'):
            raise ComposeError(f"{where}: map[{k!r}]['layers'] must be 'auto', 'velocity', 'rr' or 'random'")
        entries = []
        for h in hits:
            vel, rr, _ = _markers(h.stem)
            entries.append({'file': str(h), 'rel': _rel(h, root), 'vel': vel, 'rr': rr})
            used.add(str(h))
        role = None
        for r, ks in ROLE_KEYS.items():
            if key in ks:
                role = r
        if key in HAT_KEYS:
            role = {42: 'hat_closed', 44: 'hat_pedal', 46: 'hat_open'}[key]
        label = os.path.basename(entries[0]['rel']) + (f" (+{len(entries) - 1})" if len(entries) > 1 else '')
        s = _Sound(role, label, _order_layers(entries, mode))
        s.rr_mode = 'random' if mode == 'random' else 'cycle'
        s.key = key
        s.source = 'map'
        for opt, attr in (('gain', 'gain'), ('tune', 'tune'), ('pan', 'pan'), ('choke', 'choke')):
            if opt in opts:
                val = opts[opt]
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    raise ComposeError(f"{where}: map[{k!r}][{opt!r}] must be a number")
                setattr(s, attr, float(val) if opt != 'choke' else int(val))
        sounds.append(s)
    return sounds, empty, used


# --------------------------------------------------------------------------------------------- zones

def _zones(keys: dict[int, list[_Sound]], humanize: bool | None, spread: float, gains: dict | None) -> list[dict]:
    zones = []
    role_gain = {}
    for k, v in (gains or {}).items():
        role_gain[k] = v
    for key in sorted(keys):
        for s in keys[key]:
            nl = len(s.layers)
            ranges = s.velranges or _even_ranges(nl)
            multi = nl > 1 or any(len(layer) > 1 for layer in s.layers)
            human = multi if humanize is None else bool(humanize)
            gain = s.gain + _role_gain(role_gain, s, key)
            hits = getattr(s, 'hits', None)
            for li, layer in enumerate(s.layers):
                vlo, vhi = ranges[li]
                # DrumGizmo: one hit may be several files (mic groups): they share the round-robin slot
                slots = _slots(layer, hits[li] if hits else None)
                n = len(slots)
                for pos, group in enumerate(slots):
                    for f in group:
                        z = {'file': f['file'], 'lo': key, 'hi': key, 'loop': 'oneshot', 'pitchKeytrack': 0}
                        if vlo > 0 or vhi < 127:
                            z['vello'], z['velhi'] = vlo, vhi
                        if n > 1:
                            if s.rr_mode == 'random':
                                z['lorand'], z['hirand'] = round(pos / n, 6), round((pos + 1) / n, 6)
                            else:
                                z['seqLength'], z['seqPosition'] = min(n, 128), min(pos + 1, 128)
                        g = gain + f.get('gain', 0.0)
                        if abs(g) > 1e-6:
                            z['gain'] = round(max(-144.0, min(48.0, g)), 3)
                        t = s.tune + f.get('tune', 0.0)
                        if abs(t) > 1e-6:
                            z['tune'] = round(t, 3)
                        if f.get('channels'):
                            z['channels'] = f['channels']
                        pan = s.pan
                        if pan is None and not f.get('channels') and _mono(f['file']):
                            # mono one-shots only: a stereo file carries its own placement
                            pan = (_TOM_PANS.get(key) if s.role == 'tom' else _ROLE_PAN.get(s.role or '', None))
                            pan = None if pan is None else pan * spread
                        if pan:
                            z['pan'] = round(max(-1.0, min(1.0, pan)), 3)
                        choke = s.choke or (1 if key in HAT_KEYS or s.role in ('hat_closed', 'hat_open', 'hat_pedal',
                                                                              'hat_half') else 0)
                        if choke:
                            z['choke'] = choke
                        if nl > 1:
                            z['ampVeltrack'] = 0.45
                        if human:
                            z['ampRandom'] = 0.8
                            z['pitchRandom'] = 4
                        cut = cut_end(f['file'])
                        if cut:     # the file stops mid-waveform: fade its last 12 ms (at the fastest playback)
                            ratio = 2.0 ** ((abs(t) + (4 if human else 0)) / 1200.0)
                            z['hold'] = round(max(0.0, cut / ratio - 0.014), 4)
                            z['decay'] = 0.012
                            z['sustain'] = 0.0
                        zones.append(z)
    return zones


_TAILS: dict[tuple, float | None] = {}


_MONO: dict[tuple, bool] = {}


def _mono(path: str) -> bool:
    """True for a mono one-shot: a mono WAV, or a stereo one whose channels are (nearly) the same (dual mono, the
    side signal 40 dB under the mid). The spread= placement applies to these only: a real stereo recording carries
    its own placement."""
    try:
        st = os.stat(path)
    except OSError:
        return False
    key = (path, st.st_mtime_ns, st.st_size)
    if key in _MONO:
        return _MONO[key]
    head = wav_header(path)
    out = False
    if head and head.get('channels') == 1:
        out = True
    elif head and head.get('channels', 0) >= 2 and head['format'] in (1, 3):
        frames = min(head['frames'], int(0.5 * head['rate']))
        bps = head['bits'] // 8
        with open(path, 'rb') as f:
            f.seek(head['data'])
            data = f.read(frames * head['align'])
        frames = len(data) // head['align']
        if frames and bps in (2, 3, 4) and not (head['format'] == 3 and bps != 4):
            def chan(c: int) -> list[float]:
                vals = []
                for i in range(0, frames, 4):          # every 4th frame is plenty for an energy ratio
                    o = i * head['align'] + c * bps
                    b = data[o:o + bps]
                    if head['format'] == 3:
                        vals.append(struct.unpack('<f', b)[0])
                    else:
                        vals.append(int.from_bytes(b, 'little', signed=True) / float(1 << (8 * bps - 1)))
                return vals
            lch, rch = chan(0), chan(1)
            mid = sum((a + b) ** 2 for a, b in zip(lch, rch))
            side = sum((a - b) ** 2 for a, b in zip(lch, rch))
            out = mid > 0 and side < mid * 1e-4
    _MONO[key] = out
    return out


def cut_end(path: str) -> float | None:
    """The length (s) of a WAV that ends abruptly (its last 2 ms still above -60 dBFS: a click when it stops), else
    None."""
    try:
        st = os.stat(path)
    except OSError:
        return None
    key = (path, st.st_mtime_ns, st.st_size)
    if key in _TAILS:
        return _TAILS[key]
    out = None
    head = wav_header(path)
    if head and head['format'] in (1, 3) and head['frames'] > 0 and head['rate'] > 0:
        n = min(head['frames'], max(8, head['rate'] // 500))
        tail = dict(head)
        tail['data'] = head['data'] + (head['frames'] - n) * head['align']
        tail['frames'] = n
        x, _ = read_mono(path, n / head['rate'] + 1.0, tail)
        if x:
            level = math.sqrt(sum(v * v for v in x) / len(x))
            if level > 1e-3:
                out = head['frames'] / head['rate']
    _TAILS[key] = out
    return out


def _slots(layer: list[dict], hits: int | None) -> list[list[dict]]:
    if not hits or hits == len(layer):
        return [[f] for f in layer]
    groups: dict[str, list[dict]] = {}
    for f in layer:
        groups.setdefault(f.get('group', f['file']), []).append(f)
    return list(groups.values())


def _role_gain(gains: dict, s: _Sound, key: int) -> float:
    total = 0.0
    fam = {'hat_closed': 'hats', 'hat_open': 'hats', 'hat_pedal': 'hats', 'hat_half': 'hats', 'crash': 'cymbals',
           'ride': 'cymbals', 'ride_bell': 'cymbals', 'china': 'cymbals', 'splash': 'cymbals', 'tom': 'toms'}
    for name in (fam.get(s.role or ''), s.role, GM_NAMES.get(key), key):
        if name is not None and name in gains:
            total = float(gains[name])
    return total


# --------------------------------------------------------------------------------------------- public

def _kind(path: Path) -> tuple[str, Path]:
    if path.is_file():
        if path.suffix.lower() == '.xml':
            root = _xml(path)
            if root.tag == 'drumkit_info':
                return 'hydrogen', path
            if root.tag == 'drumkit':
                return 'drumgizmo', path
            raise ComposeError(f"kit: {path} is neither a Hydrogen (drumkit_info) nor a DrumGizmo (drumkit) kit file")
        if path.suffix.lower() == '.h2drumkit':
            raise ComposeError(f"kit: {path} is a packed Hydrogen kit (tar.gz); the kit builder reads unpacked kits "
                               f"(a folder with drumkit.xml)")
        raise ComposeError(f"kit: {path} is a file; give a folder of one-shots, a Hydrogen / DrumGizmo kit folder or "
                           f"its .xml, or a list of files")
    h2 = sorted(path.glob('drumkit.xml')) or sorted(path.glob('*/drumkit.xml'))
    for x in h2:
        if _xml(x).tag == 'drumkit_info':
            return 'hydrogen', x
    dg = _dg_kits(path) or [p for sub in sorted(path.iterdir()) if sub.is_dir() for p in _dg_kits(sub)]
    if dg:
        return 'drumgizmo', dg[0]
    return 'oneshots', path


def build(source, map: dict | None = None, *, numbered: str = 'auto', fill: bool = True, humanize: bool | None = None,
          mics: dict | None = None, gains: dict | None = None, spread: float = 0.5, kit: str | None = None,
          extras: bool = True, caller_file: str | None = None) -> tuple[list[dict], dict]:
    """(zones for the 'sampler', info) of a kit. source: a folder (one-shots, a Hydrogen kit with drumkit.xml, a
    DrumGizmo kit), a kit .xml, or a list of WAV files. map: key overrides (module docstring). numbered: how numbered
    files of one name are read: 'auto' (measured), 'variants' (different sounds), 'layers' (velocity layers by
    loudness), 'rr' (round robins), 'random' (random picks). fill: put retuned toms / kick2 / pedal hat / crash2 / ride2
    on empty GM keys. humanize: tiny per-hit level / pitch variation (None: for multi-sample sounds only). mics:
    DrumGizmo microphone gains {name or group: dB or None}. gains: dB per role, family (hats, cymbals, toms) or key.
    spread: stereo spread of mono one-shots (drummer's perspective, 0 = all centred). kit: which DrumGizmo kit file
    of a folder with several (name substring). extras=False leaves files that are neither recognized nor on a GM
    key of their role off the keyboard (listed in info['unused']) instead of on spare keys 88+."""
    if numbered not in ('auto', 'variants', 'layers', 'rr', 'random'):
        raise ComposeError(f"kit: numbered= must be 'auto', 'variants', 'layers', 'rr' or 'random', got {numbered!r}")
    if isinstance(spread, bool) or not isinstance(spread, (int, float)) or not 0 <= spread <= 1:
        raise ComposeError(f"kit: spread= must be 0..1, got {spread!r}")
    if gains is not None:
        if not isinstance(gains, dict) or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in gains.values()):
            raise ComposeError(f"kit: gains= must be a dict {{role / family / key: dB}}, got {gains!r}")
        gains = _check_gains(gains)
    if kit is not None and not isinstance(kit, str):
        raise ComposeError(f"kit: kit= must be a kit file name (text), got {kit!r}")
    skipped: list[tuple[str, str]] = []
    unmapped: list[str] = []
    notes: list[str] = []
    unused: list[str] = []
    info: dict = {}
    if isinstance(source, (list, tuple)):
        paths = [resolve(p, caller_file) for p in source]
        if not paths:
            raise ComposeError("kit: the file list is empty")
        root = Path(os.path.commonpath([str(p.parent) for p in paths]))
        files = paths
        kind, where = 'oneshots', root
    else:
        root = resolve(source, caller_file)
        kind, where = _kind(root)
        if kind == 'drumgizmo' and kit is not None:
            cands = _dg_kits(where.parent)
            # an exact file name / stem first ('aasimonster' must not pick 'aasimonster-minimal'), then a substring
            pick = ([c for c in cands if kit.lower() in (c.name.lower(), c.stem.lower())]
                    or [c for c in cands if kit.lower() in c.stem.lower()])
            if not pick:
                raise ComposeError(f"kit: no DrumGizmo kit file matching {kit!r} in {where.parent} "
                                   f"(kits: {', '.join(c.name for c in cands)})")
            where = pick[0]
        files = _audio_files(root) if kind == 'oneshots' else []
        if kit is not None and kind != 'drumgizmo':
            raise ComposeError(f"kit: kit= picks one kit file of a DrumGizmo folder; {root} is a {kind} kit")
    info.update(kind=kind, path=str(where))
    if kind == 'oneshots':
        if not files:
            conv = [p for p in root.rglob('*') if p.suffix.lower() in _CONVERTIBLE] if root.is_dir() else []
            raise ComposeError(f"kit: no .wav files in {root}" + (f" ({len(conv)} unconverted {conv[0].suffix} files: "
                               f"the sample downloader converts them)" if conv else ''))
        forced, empty, used = _apply_map(map, files, root, 'kit', caller_file) if map else ([], set(), set())
        rest = [f for f in files if str(f) not in used]
        sounds = forced + _oneshot_sounds(rest, root, numbered, skipped, unmapped)
        # forced keys are reserved: automatic sounds of that role move on to the role's other keys / spare keys
        keys = _assign_with_reserved(sounds, {s.key for s in forced} | empty, fill, notes, extras, unused)
        for k in empty:
            keys.pop(k, None)
    else:
        if map:
            raise ComposeError(f"kit: map= is for one-shot folders; a {kind} kit maps its instruments itself "
                               f"(use gains= / mics=, or build a one-shot kit from its files)")
        if kind == 'hydrogen':
            sounds = _hydrogen_sounds(where, skipped, unmapped, info)
        else:
            sounds = _dg_sounds(where, mics, skipped, unmapped, info)
            info['kits'] = [c.name for c in _dg_kits(where.parent)]
        keys = _assign_structured(sounds, kind, fill, notes)
    if mics and kind != 'drumgizmo':
        raise ComposeError("kit: mics= is for DrumGizmo kits (multichannel files); SFZ multi-mic kits: inst.sfz(..., mics=)")
    zones = _zones(keys, humanize, float(spread), gains)
    if not zones:
        raise ComposeError(f"kit: nothing playable in {where}"
                           + (f" ({len(skipped)} files skipped: loops / beats / fills, e.g. {skipped[0][0]})"
                              if skipped else ''))
    if kind == 'oneshots' and root.is_dir():
        # a pack that ships an .sfz maps its own velocity layers / round robins / microphones: say so
        pack = root
        for p in [root, *root.parents]:
            if (p / 'SOURCE.json').is_file():
                pack = p
                break
        sfz = sorted(pack.glob('*.sfz')) + sorted(pack.glob('*/*.sfz'))
        if sfz:
            try:
                shown = 'samples/' + sfz[0].relative_to(_samples_dir()).as_posix()
            except ValueError:
                shown = sfz[0].as_posix()
            notes.append(f"this pack has its own mapping: inst.sfz('{shown}') ({len(sfz)} .sfz files) - "
                         f"multi-microphone packs map better that way")
    info['keys'] = {}
    for k in sorted(keys):
        ss = keys[k]
        s = ss[0]
        info['keys'][k] = {'name': GM_NAMES.get(k, f"extra_{k}"), 'role': s.role or 'unknown', 'sound': s.label,
                           'layers': len(s.layers),
                           'rr': max(len(_slots(layer, (getattr(s, 'hits', None) or [None] * len(s.layers))[i]))
                                     for i, layer in enumerate(s.layers)),
                           'files': len({f for x in ss for f in x.files()}),
                           **({'filledFrom': s.filled_from} if s.filled_from is not None else {}),
                           **({'source': s.source} if s.source else {})}
    info['names'] = {GM_NAMES.get(k, f"extra_{k}"): k for k in sorted(keys)}
    info['unmapped'] = [u for u in unmapped if u not in unused]
    info['unused'] = unused
    info['skipped'] = [f"{a} ({b})" for a, b in skipped]
    info['notes'] = notes
    info['zones'] = len(zones)
    return zones, info


_FAMILIES = ('hats', 'cymbals', 'toms')


def _check_gains(gains: dict) -> dict:
    """gains= keys: a family (hats, cymbals, toms), a role (kick, snare, hat_open, tambourine ...), a GM key name
    ('open_hat', 'crash2'), an alias ('bd', 'ohh') or a MIDI key. Unknown names are errors, never ignored."""
    roles = set(ROLE_KEYS) | {'hat_closed', 'hat_open', 'hat_pedal', 'hat_half'}
    out: dict = {}
    for k, v in gains.items():
        if isinstance(k, bool):
            raise ComposeError(f"kit: gains= key {k!r} is not a role, family or key")
        if isinstance(k, int):
            if not 0 <= k <= 127:
                raise ComposeError(f"kit: gains= key {k} is outside 0..127")
            out[k] = v
        elif isinstance(k, str) and (k in _FAMILIES or k in roles or k in _NAME_KEYS):
            out[k if (k in _FAMILIES or k in roles or k in GM_NAMES.values()) else _NAME_KEYS[k]] = v
        else:
            raise ComposeError(f"kit: gains= key {k!r} is not a family ({', '.join(_FAMILIES)}), a role "
                               f"({', '.join(sorted(roles))}) or a key name / MIDI number")
    return out


def _assign_with_reserved(sounds: list[_Sound], reserved: set[int], fill: bool, notes: list[str], extras: bool = True,
                          unused: list | None = None) -> dict[int, list[_Sound]]:
    """_assign() with keys held free (map= keys, map= None keys): placeholders take them during the assignment."""
    fake = []
    for k in reserved:
        if not any(s.key == k for s in sounds):
            p = _Sound(None, '(reserved)', [[]])
            p.key = k
            fake.append(p)
    keys = _assign(sounds + fake, fill, notes, extras, unused)
    for k in list(keys):
        keys[k] = [s for s in keys[k] if s.label != '(reserved)']
        if not keys[k]:
            del keys[k]
    return keys


def _assign_structured(sounds: list[_Sound], kind: str, fill: bool, notes: list[str]) -> dict[int, list[_Sound]]:
    """Hydrogen / DrumGizmo: the kit's own MIDI map where it has one (DrumGizmo midimap), else the role of each
    instrument's name, else the kit's note / Hydrogen's default (36 + index)."""
    keys: dict[int, list[_Sound]] = {}
    extra: list[_Sound] = []
    for s in sounds:
        dg = getattr(s, 'dg_notes', None)
        if dg:
            s.key = dg[0]
            keys.setdefault(dg[0], []).append(s)
            for n in dg[1:]:
                c = _filled(s, n, dg[0])
                c.filled_from = None
                keys.setdefault(n, []).append(c)
    rest = [s for s in sounds if s.key is None]
    if rest:
        auto = _assign([s for s in rest if s.role], False, notes)
        for k, ss in auto.items():
            if k in keys:   # the midimap already has this key: the extra instrument goes to a spare key
                extra += ss
            else:
                keys[k] = ss
        for s in rest:
            if s.role is None:
                midi = getattr(s, 'midi', None)
                k = midi if midi is not None and midi not in keys else None
                if k is None and kind == 'hydrogen' and 36 + getattr(s, 'index', 0) not in keys:
                    k = 36 + getattr(s, 'index', 0)
                if k is None:
                    extra.append(s)
                else:
                    s.key = k
                    keys[k] = [s]
    for s in extra:
        k = next((k for k in SPARE_KEYS if k not in keys), None)
        if k is None:
            notes.append(f"no free key left for {s.label}")
            continue
        s.key = k
        keys[k] = [s]
    if fill:
        _fill(keys)
    return keys


def describe(source, map: dict | None = None, caller_file: str | None = None, **kw) -> dict:
    """The mapping build() would make (info only)."""
    _, info = build(source, map, caller_file=caller_file, **kw)
    return info


def format_info(info: dict) -> str:
    """Human-readable mapping (python -m agentsound kit DIR)."""
    out = [f"{info.get('kind')} kit: {info.get('path')}" + (f" ({info['name']})" if info.get('name') else '')]
    if info.get('channels'):
        mix = info.get('mix', {})
        out.append('  microphones: ' + ', '.join(f"{c}{'' if mix.get(c) else ' (muted)'}" for c in info['channels']))
    if info.get('kits') and len(info['kits']) > 1:
        out.append('  kit files: ' + ', '.join(info['kits']) + " (choose with kit='name')")
    out.append(f"  {info.get('zones')} zones on {len(info.get('keys', {}))} keys:")
    for k, v in info.get('keys', {}).items():
        from .theory import note_name
        extra = []
        if v['layers'] > 1:
            extra.append(f"{v['layers']} velocity layers")
        if v['rr'] > 1:
            extra.append(f"{v['rr']} round robins")
        if 'filledFrom' in v:
            extra.append(f"filled from key {v['filledFrom']}")
        out.append(f"    {k:3d} {note_name(k):4s} {v['name']:14s} {v['role']:11s} {v['sound']}"
                   + (f"  [{', '.join(extra)}]" if extra else ''))
    if info.get('unmapped'):
        out.append(f"  not recognized (on spare keys, listed above as role 'unknown'): {', '.join(info['unmapped'])}")
    if info.get('unused'):
        out.append(f"  not on the keyboard (extras=False): {len(info['unused'])} sounds, e.g. "
                   + ', '.join(info['unused'][:12]) + (' ...' if len(info['unused']) > 12 else ''))
    if info.get('skipped'):
        out.append(f"  skipped: {', '.join(info['skipped'][:20])}" + (' ...' if len(info['skipped']) > 20 else ''))
    for n in info.get('notes', []):
        out.append(f"  note: {n}")
    return '\n'.join(out)


# --------------------------------------------------------------------------------------------- multisamples

_NOTE_RE = re.compile(r'(?<![A-Za-z])([A-Ga-g])(#|s|b)?(-?\d)(?![0-9])')
_MIDI_RE = re.compile(r'(?:^|[^0-9])(\d{2,3})(?:[^0-9]|$)')


def note_of(stem: str) -> int | None:
    """MIDI note of a sample name: the last note name in it ('Pad C3', 'Str_F#2', 'Bb1'), else a MIDI number
    ('036-C', 'pad_60')."""
    return _note_parse(stem)[0]


def _note_parse(stem: str) -> tuple[int | None, bool]:
    """(MIDI note, True if it came from a note name - octave= shifts those - or False for a MIDI number)."""
    ms = list(_NOTE_RE.finditer(stem))
    for m in reversed(ms):
        pc = {'c': 0, 'd': 2, 'e': 4, 'f': 5, 'g': 7, 'a': 9, 'b': 11}[m.group(1).lower()]
        pc += {'#': 1, 's': 1, 'b': -1}.get(m.group(2) or '', 0)
        k = 12 * (int(m.group(3)) + 1) + pc
        if 0 <= k <= 127:
            return k, True
    for m in reversed(list(_MIDI_RE.finditer(stem))):
        v = int(m.group(1))
        if 12 <= v <= 120:
            return v, False
    return None, False


def multisample(source, *, octave: int = 0, loop: str | None = 'auto', keys: tuple | None = None, root=None,
                loop_start: int | None = None, loop_end: int | None = None, match=None,
                caller_file: str | None = None) -> tuple[list[dict], dict]:
    """(zones, info) of a folder (or list) of note-named samples: each file on its root key, spread to the keys
    between its neighbours; velocity layers / round robins from the names (v1, pp..ff, rr1). octave: shift every
    parsed note (packs that call middle C 'C3': octave=1). root: the key of files whose names carry no note (one
    sample stretched over the keyboard, e.g. a Fairlight voice recorded at A3: root='A3'). loop: 'auto' (the files'
    smpl loops), 'none', 'forward', 'pingpong', 'sustain'; loop_start / loop_end: loop frames for every zone.
    keys: (lo, hi) range the lowest / highest samples stretch to (default: the whole keyboard). match: only files
    whose path contains this text (or matches this glob); a list: every entry must match (one articulation / length
    of a folder that mixes them: match=['_1_', 'arco-normal'])."""
    if loop not in ('auto', 'none', 'forward', 'pingpong', 'sustain', None):
        raise ComposeError(f"multisample: loop= must be 'auto', 'none', 'forward', 'pingpong' or 'sustain', got {loop!r}")
    if (loop_start is not None or loop_end is not None) and loop not in ('forward', 'pingpong', 'sustain'):
        raise ComposeError("multisample: loop_start / loop_end need loop='forward', 'pingpong' or 'sustain'")
    if isinstance(octave, bool) or not isinstance(octave, int) or not -4 <= octave <= 4:
        raise ComposeError(f"multisample: octave= must be a whole number -4..4, got {octave!r}")
    if keys is not None and not (isinstance(keys, (list, tuple)) and len(keys) == 2
                                 and all(isinstance(k, int) and not isinstance(k, bool) and 0 <= k <= 127 for k in keys)
                                 and keys[0] <= keys[1]):
        raise ComposeError(f"multisample: keys= must be (lowest, highest) MIDI keys 0..127, got {keys!r}")
    fixed_root = None
    if root is not None:
        from .theory import note
        fixed_root = note(root) if isinstance(root, str) else root
        if isinstance(fixed_root, bool) or not isinstance(fixed_root, (int, float)) or not 0 <= fixed_root <= 127:
            raise ComposeError(f"multisample: root= must be a key 0..127 or a note name, got {root!r}")
    if isinstance(source, (list, tuple)):
        files = [resolve(p, caller_file, 'multisample') for p in source]
        base = Path(os.path.commonpath([str(p.parent) for p in files]))
    else:
        base = resolve(source, caller_file, 'multisample')
        files = _audio_files(base) if base.is_dir() else [base]
    if match is not None:
        pats = [match] if isinstance(match, str) else list(match)
        if not pats or not all(isinstance(m, str) and m for m in pats):
            raise ComposeError(f"multisample: match= must be a text / glob or a list of them, got {match!r}")
        before = len(files)
        files = [f for f in files if all(_match(m, [f], base) for m in pats)]
        if not files:
            raise ComposeError(f"multisample: no file of {base} matches {match!r} ({before} files)")
    notes: dict[float, list[dict]] = {}
    unmapped = []
    for f in files:
        vel, rr, rest = _markers(f.stem)
        k, named = _note_parse(rest) if rest else (None, False)
        if k is None:
            k, named = _note_parse(f.stem)
        if k is None:
            if fixed_root is None:
                unmapped.append(f.name)
                continue
            k = fixed_root
        elif named:     # octave= renames note names ('C3' = middle C); MIDI numbers are absolute
            k += 12 * int(octave)
        if not 0 <= k <= 127:
            unmapped.append(f"{f.name} (key {k} out of range)")
            continue
        notes.setdefault(k, []).append({'file': str(f), 'vel': vel, 'rr': rr, 'rel': _rel(f, base)})
    if not notes:
        raise ComposeError(f"multisample: no file in {base} has a note name (C3, F#2, Bb1) or MIDI number in its name"
                           + (f"; e.g. {', '.join(unmapped[:5])} (root= gives unnamed files a key)" if unmapped else ''))
    roots = sorted(notes)
    lo_all, hi_all = keys if keys else (0, 127)
    zones = []
    for i, r in enumerate(roots):
        lo = min(lo_all, int(r)) if i == 0 else int(roots[i - 1] + r) // 2 + 1
        hi = max(hi_all, int(math.ceil(r))) if i == len(roots) - 1 else int(r + roots[i + 1]) // 2
        layers = _order_layers(notes[r], 'auto') if len(notes[r]) > 1 else [notes[r]]
        ranges = _even_ranges(len(layers))
        for li, layer in enumerate(layers):
            for pos, e in enumerate(layer):
                z = {'file': e['file'], 'root': r, 'lo': lo, 'hi': hi}
                if loop and loop != 'none':
                    z['loop'] = loop
                if loop_start is not None:
                    z['loopStart'] = int(loop_start)
                if loop_end is not None:
                    z['loopEnd'] = int(loop_end)
                if len(layers) > 1:
                    z['vello'], z['velhi'] = ranges[li]
                if len(layer) > 1:
                    z['seqLength'], z['seqPosition'] = len(layer), pos + 1
                zones.append(z)
    info = {'kind': 'multisample', 'path': str(base), 'roots': roots, 'zones': len(zones), 'unmapped': unmapped,
            'layers': max(len(_order_layers(v, 'auto')) if len(v) > 1 else 1 for v in notes.values())}
    return zones, info


# --------------------------------------------------------------------------------------------- level calibration

def _interp(pts, v: float) -> float:
    if v <= pts[0][0]:
        return pts[0][1]
    for (v0, d0), (v1, d1) in zip(pts, pts[1:]):
        if v <= v1:
            return d0 + (d1 - d0) * (v - v0) / (v1 - v0) if v1 > v0 else d1
    return pts[-1][1]


def velocity_map(ins, maps: dict):
    """Re-level a sampled kit's velocity layers per key (in place; returns ins): maps = {key: [(velocity, dB), ...]}
    - the level correction at those velocities (measured: a key whose recorded layers sit at one level, a tom ~6 dB
    louder than the snare at the same velocity). Each single-key zone of a mapped key gets the correction at its own
    layer edges: its gain moves by the correction at its velhi, its velcurve's points by the difference to it (the
    layer's own ramp is bent along the curve); a zone without a velcurve takes the mean of its two edges. Measure
    first (each round robin at each layer's edges), then map the measured levels onto the curve you want
    (agentsound/patches/sampled_drums.py BIG_RUSTY_VELOCITY: snare and toms on the kick's natural curve)."""
    zones = ins.params.get('samples') if hasattr(ins, 'params') else None
    if zones is None:
        raise ComposeError("velocity_map: needs an expanded sampler instrument (its zones)")
    table = {}
    for k, pts in maps.items():
        ps = sorted((float(v), float(d)) for v, d in pts)
        if not ps or any(not 0 <= v <= 127 or abs(d) > 24 for v, d in ps):
            raise ComposeError(f"velocity_map[{k!r}]: points must be (velocity 0..127, dB -24..24), got {pts!r}")
        table[int(k)] = ps
    for z in zones:
        k = z.get('lo')
        if k is None or k != z.get('hi') or k not in table:
            continue
        ps = table[k]
        lo, hi = max(1, z.get('vello', 0)), z.get('velhi', 127)
        c_hi = _interp(ps, hi)
        vc = z.get('velcurve')
        if vc:
            z['velcurve'] = [[p[0], round(p[1] * 10.0 ** ((_interp(ps, p[0]) - c_hi) / 20.0), 6)] for p in vc]
            z['gain'] = round(z.get('gain', 0.0) + c_hi, 4)
        else:
            z['gain'] = round(z.get('gain', 0.0) + 0.5 * (_interp(ps, lo) + c_hi), 4)
    return ins
