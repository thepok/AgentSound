"""The mix engineer: role-aware mix plans, a report-driven auto-mix and a mix engineer's findings.

    from agentsound import mixer
    p = mixer.plan(song, report='songs/x/out/report.json')   # roles, targets per genre, carving, rides, glue
    print(p.describe())                                       # + p.mix(): the moves as a MIX dict
    res = mixer.auto('songs/x', iterations=2)                 # render -> measure -> adjust faders / rides /
    print(res.describe())                                     #   sidechains / dips, bounded and logged
    res.mix                                                   # the MIX dict to paste into song.py
    for f in mixer.check('songs/x/out/report.json'):          # "lead not in front", "drums too loud for jazz",
        print(f)                                              #   masking, mud, harshness, width ... with fixes

    # song.py - the mix lives in code, never applied silently:
    MIX = {'trim': {'keys_lead': 1.5, 'pad': -2.0},           # dB, song-wide, per track / bus
           'ride': {'keys_lead': {'drop2': 1.0}},             # dB per section (on top of the trim)
           'duck': [{'targets': ['pad', 'choir'], 'key': 'keys_lead', 'depth': 2.5}],   # sidechains
           'eq': {'piano': [{'freq': 1400, 'gain': -2.0, 'q': 1.0}]}}                   # presence dips
    # the CLI applies a module-level MIX at build time (and prints it); or explicitly: s.mix(MIX) in build()

What MIX does to the song (agentsound.mixer.apply): trims and rides go to one `utility` insert named `mixer`
at the end of each node's chain (post-insert, pre-fader: the sends follow it; never in conflict with the
song's own gainDb lanes), a ride is an automation lane `fx.mixer.gain` that moves `ramp` beats (default 1)
before each section start, ducks are ordinary `song.sidechain()` duckers, eq dips one `eq` insert named
`mixer_eq` (up to three bells). The render JSON shows all of it.

Levels (how the mixer measures "3 dB under the lead"): per bar from the report (`nodes[].barsRmsDb`) plus each
node's K-weighting offset (its `lufs - rmsDb`), so the numbers read like the LUFS balances of the recipes and
band presets; compared per section on the bars where both parts play. The bed uses the report's own
`space.sections[].bedVsLeadDb` (K-weighted on the lead's ticks) when it has one.

Roles: lead (the part in front), bed (pads / strings / choir), rhythm (drums, percussion), low (bass), other
(keys, arps, comping, counter-lines), fx (risers, impacts: not balanced). Explicit arguments win over a band's
roles, which win over the report's analysis roles (`nodes[].role`), which win over the track ids.
"""

from __future__ import annotations

import copy
import difflib
import json
import math
import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

from .theory import ComposeError

ROLES = ('lead', 'bed', 'rhythm', 'low', 'other', 'fx')
GROUPS = ('rhythm', 'low', 'bed')          # balanced as groups against the lead (both bounds)
MIX_KEYS = ('profile', 'trim', 'ride', 'duck', 'eq', 'ramp', 'log')
DUCK_KEYS = ('targets', 'key', 'pitches', 'depth', 'threshold', 'attack', 'hold', 'release', 'curve')
EQ_KEYS = ('freq', 'gain', 'q')
FX_NAME, EQ_NAME = 'mixer', 'mixer_eq'
MAX_STEP = 6.0          # dB: the largest single move auto() makes per pass
MAX_TRIM = 12.0         # dB: the largest total trim auto() writes
MAX_RIDE = 6.0          # dB: the largest section ride auto() writes
TOL, MARGIN = 0.5, 0.5  # dB: a level this close outside its window needs no move; a move lands this far inside

_ANALYSIS_ROLE = {'lead': 'lead', 'bed': 'bed', 'drums': 'rhythm', 'bass': 'low', 'other': 'other', 'fx': 'fx'}
_WORDS = {
    'rhythm': ('drums', 'drum', 'kit', 'kick', 'snare', 'hat', 'hats', 'hihat', 'perc', 'percussion', 'rim', 'shaker',
               'clap', 'claps', 'toms', 'tom', 'cymbal', 'cymbals', 'ride', 'brushes', 'brush', 'tamb', 'tambourine',
               'conga', 'congas', 'bongo', 'timpani', 'cajon'),
    'low': ('bass', 'sub', '808', 'bassline', 'contrabass', 'upright', 'tuba'),
    'bed': ('pad', 'pads', 'strings', 'choir', 'bed', 'drone', 'atmos', 'texture', 'organ', 'swell', 'ensemble'),
    'lead': ('lead', 'hook', 'melody', 'vox', 'vocal', 'voice_lead', 'sax', 'trumpet', 'solo', 'flute', 'topline',
             'theme'),
    'fx': ('riser', 'impact', 'fx', 'sweep', 'downlifter', 'uplifter', 'noise', 'wind', 'rain', 'whoosh', 'crash_fx'),
}
_HOOK_RE = re.compile(r'chorus|drop|hook|refrain|lift|climax|finale|peak|head', re.I)


def role_from_id(node_id: str) -> str:
    """The role a track id suggests ('pad_hi' -> bed, 'sub_808' -> low, 'bass_drum' -> rhythm), else 'other'."""
    words = [w for w in re.split(r'[_\-\s]+', node_id.lower()) if w]
    if 'drum' in words or 'drums' in words:
        return 'rhythm'
    for role in ('fx', 'rhythm', 'low', 'lead', 'bed'):
        if any(w in _WORDS[role] for w in words):
            return role
    return 'other'


# ------------------------------------------------------------------------------------------------ profiles

@dataclass(frozen=True)
class MixProfile:
    """A genre's balance: where each role sits relative to the lead (dB, K-weighted-ish, on the bars both play) in
    the hook sections, and the mix engineer's habits for it."""
    name: str
    rhythm: tuple               # (lo, hi) dB vs the lead
    low: tuple
    bed: tuple
    other_max: float            # no other part (keys, arps, comping, a second lead) above this vs the lead
    lead_ride_db: float         # the lead sits this much further in front in the hook sections than in the verses
    bed_ride_db: float          # the bed sits this much lower in the verses (negative)
    bed_duck_db: float          # sidechain depth of the bed under the lead when the bed crowds it (0 = never)
    kick_bass_duck_db: float    # the bass ducks under the kick when they fight in the low end (0 = eq advice only)
    dip_db: float               # presence dip on a part that masks the lead (negative)
    glue: tuple = ()
    notes: str = ''

    def window(self, role: str, hook: bool = True) -> tuple:
        """(lo, hi) of a role vs the lead; outside the hooks the band may come lead_ride_db closer, the bed not."""
        lo, hi = {'rhythm': self.rhythm, 'low': self.low, 'bed': self.bed}.get(role, (-99.0, self.other_max))
        if hook:
            return (lo, hi)
        shift = self.lead_ride_db + (self.bed_ride_db if role == 'bed' else 0.0)
        return (lo + shift if lo > -99 else lo, hi + shift)


_SYNTH_GLUE = ('a drum bus (kick / snare / hats routed to one bus): compressor 2:1-4:1, attack 10-30 ms, 2-3 dB '
               'gain reduction on the hits, or parallel compression 20-30 % wet',
               "the master's glue compressor (master/synthwave): 1-2 dB on the drops, slow attack (30 ms), auto "
               "release - glue, not squash")
PROFILES: dict[str, MixProfile] = {
    'synthwave': MixProfile('synthwave', rhythm=(-5.0, -2.0), low=(-5.0, -2.0), bed=(-5.5, -2.5), other_max=-3.0,
                            lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=2.5, kick_bass_duck_db=8.0, dip_db=-2.0,
                            glue=_SYNTH_GLUE,
                            notes='outrun / retrowave: kick / snare, bass and bed 2-6 dB under the hook in the drops, '
                                  'the bed >= 2.5 dB under it (user: "der Lead ist zu leise" at 0.4 dB)'),
    'dreamwave': MixProfile('dreamwave', rhythm=(-6.0, -2.0), low=(-6.0, -2.0), bed=(-4.5, -2.0), other_max=-3.0,
                            lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=2.0, kick_bass_duck_db=6.0, dip_db=-2.0,
                            glue=_SYNTH_GLUE, notes='lush beds close under a soft lead, the drums behind'),
    'darksynth': MixProfile('darksynth', rhythm=(-3.5, 0.5), low=(-3.5, 0.5), bed=(-6.0, -1.5), other_max=-2.0,
                            lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=2.0, kick_bass_duck_db=8.0, dip_db=-2.0,
                            glue=_SYNTH_GLUE, notes='the kick and the driven bass as loud as the lead'),
    'jazz': MixProfile('jazz', rhythm=(-16.0, -13.0), low=(-6.5, -3.0), bed=(-10.0, -4.0), other_max=-4.0,
                       lead_ride_db=0.0, bed_ride_db=0.0, bed_duck_db=1.5, kick_bass_duck_db=0.0, dip_db=-1.5,
                       glue=('no bus glue: a club trio breathes - at most a 1.5:1 master compressor catching 1 dB',),
                       notes='club trio record: brushes 13-16 dB under the piano / horn in every section (user: '
                             '"Drums etwas zu laut" at 10-12 dB), bass 3-6.5 dB under, comping 4+ dB under'),
    'classical': MixProfile('classical', rhythm=(-14.0, -4.0), low=(-9.0, -1.0), bed=(-8.0, -1.0), other_max=-1.0,
                            lead_ride_db=0.0, bed_ride_db=0.0, bed_duck_db=0.0, kick_bass_duck_db=0.0, dip_db=-1.5,
                            glue=('no glue: the hall and the players balance; keep the dynamics',),
                            notes='the solo line on top of the orchestra; percussion well behind'),
    'piano': MixProfile('piano', rhythm=(-14.0, -4.0), low=(-12.0, -2.0), bed=(-12.0, -2.0), other_max=-1.0,
                        lead_ride_db=0.0, bed_ride_db=0.0, bed_duck_db=0.0, kick_bass_duck_db=0.0, dip_db=0.0,
                        glue=('no glue: one instrument, the pianist balances the hands; keep the dynamics',),
                        notes='solo piano: the melody hand on top of the accompaniment (voicing, 3-12 dB), one room'),
    'film': MixProfile('film', rhythm=(-10.0, -2.0), low=(-8.0, -1.0), bed=(-7.0, -1.0), other_max=-1.5,
                       lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=1.5, kick_bass_duck_db=4.0, dip_db=-1.5,
                       glue=('a hybrid bus (low hits, braams, synth sub): compressor 2:1, 2 dB',),
                       notes='the theme on top, the hits big but under it'),
    'pop': MixProfile('pop', rhythm=(-4.0, -0.5), low=(-4.0, -0.5), bed=(-10.0, -4.0), other_max=-4.0,
                      lead_ride_db=1.5, bed_ride_db=-1.0, bed_duck_db=2.0, kick_bass_duck_db=6.0, dip_db=-2.0,
                      glue=('a drum bus compressor 4:1, 2-4 dB with 20-30 % parallel blend',
                            'the master glue 2:1, slow attack, 1-2 dB above -12 dB only'),
                      notes='lead -19, drums -19.5, bass -20, keys / pad / pluck -26..-27.5 LUFS (pop_band demo)'),
    'ballad': MixProfile('ballad', rhythm=(-9.0, -4.0), low=(-6.0, -2.0), bed=(-10.0, -4.0), other_max=-4.0,
                         lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=1.5, kick_bass_duck_db=3.0, dip_db=-1.5,
                         glue=('the master glue 1.5:1, slow attack, 1 dB at most: keep the swells',),
                         notes='a (pop / soul / jazz) ballad: the voice or lead close in front, a soft band well under, '
                               'the drums behind (hero(genre="ballad"): the vocal\'s intimate dry space)'),
    'rock': MixProfile('rock', rhythm=(-3.5, 0.0), low=(-5.0, -1.5), bed=(-10.0, -4.0), other_max=-2.0,
                       lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=0.0, kick_bass_duck_db=5.0, dip_db=-2.0,
                       glue=('drum bus: parallel compression (rock_band drum_bus)', 'master glue 2:1, 1-3 dB'),
                       notes='lead -19.5, drums -20.5, bass -22..-23, rhythm guitars -22.5..-23.5, keys -26 LUFS'),
    'default': MixProfile('default', rhythm=(-5.0, -1.0), low=(-5.0, -1.0), bed=(-7.0, -2.5), other_max=-3.0,
                          lead_ride_db=1.0, bed_ride_db=-1.0, bed_duck_db=2.0, kick_bass_duck_db=6.0, dip_db=-2.0,
                          glue=_SYNTH_GLUE, notes='generic modern mix: the lead in front, the band 1-5 dB under'),
}


def get_profile(name: str | MixProfile | None) -> MixProfile:
    """The mix profile for an analysis profile name (None / unknown-but-close -> error with the choices)."""
    if isinstance(name, MixProfile):
        return name
    if name is None:
        return PROFILES['default']
    if name not in PROFILES:
        close = difflib.get_close_matches(str(name), PROFILES, n=1)
        raise ComposeError(f"no mix profile {name!r}" + (f" - did you mean {close[0]!r}?" if close else '')
                           + f" (profiles: {', '.join(PROFILES)})")
    return PROFILES[name]


# ------------------------------------------------------------------------------------------------ report view

def _powmean(v) -> float | None:
    v = list(v)
    return 10.0 * math.log10(sum(10.0 ** (x / 10.0) for x in v) / len(v)) if v else None


def _powsum(v) -> float:
    return 10.0 * math.log10(sum(10.0 ** (x / 10.0) for x in v))


def load_report(report) -> dict:
    """A report dict from a dict, a report.json path or a song dir (its out/report.json)."""
    if isinstance(report, dict):
        return report
    p = Path(report)
    if p.is_dir():
        p = p / 'report.json' if (p / 'report.json').is_file() else p / 'out' / 'report.json'
    if not p.is_file():
        raise ComposeError(f"no report at {p}: build the song first (python -m agentsound build ...)")
    return json.loads(p.read_text(encoding='utf-8'))


class View:
    """Per-section, per-node levels from a report: bars where a part plays, its level there (bar RMS + the node's
    K-weighting offset), group levels on the bars they share with the lead."""

    ACTIVE_FLOOR, ACTIVE_RANGE = -60.0, 18.0

    def __init__(self, report: dict):
        self.r = report
        self.nodes = {n['id']: n for n in report.get('nodes', []) if not n.get('bus')}
        rows = (report.get('timeline') or {}).get('rows') or []
        self.bars = [row[0] if isinstance(row, (list, tuple)) else row.get('bar') for row in rows]
        self.sections = [s for s in report.get('sections', []) if 'startBar' in s]
        self.space = {s['section']: s for s in (report.get('space') or {}).get('sections', [])}
        loud = [s.get('lufs', -120.0) for s in self.sections]
        self.loudest = max(loud) if loud else -120.0
        self._k = {}
        for nid, n in self.nodes.items():
            lufs, rms = n.get('lufs', -120.0), n.get('rmsDb', -120.0)
            self._k[nid] = max(-8.0, min(8.0, lufs - rms)) if lufs > -70 and rms > -100 else 0.0

    def bar_index(self, sec: dict) -> list[int]:
        return [i for i, b in enumerate(self.bars) if b is not None and sec['startBar'] - 1e-6 <= b < sec['endBar'] - 1e-6]

    def bar_level(self, nid: str, i: int) -> float:
        return self.nodes[nid]['barsRmsDb'][i] + self._k[nid]

    def active(self, nid: str, idx: list[int]) -> list[int]:
        """The bars of `idx` where the node plays (above -60 dB and within 18 dB of its loudest bar there)."""
        n = self.nodes.get(nid)
        if n is None or not idx or len(n.get('barsRmsDb', [])) < max(idx) + 1:
            return []
        vals = [n['barsRmsDb'][i] for i in idx]
        top = max(vals)
        return [i for i in idx if n['barsRmsDb'][i] > self.ACTIVE_FLOOR and n['barsRmsDb'][i] >= top - self.ACTIVE_RANGE]

    def level(self, nid: str, bars: list[int]) -> float | None:
        return _powmean(self.bar_level(nid, i) for i in bars) if bars else None

    def group_level(self, ids, bars: list[int], idx: list[int]) -> tuple[float | None, list[int]]:
        """Summed level of several nodes on `bars` (each counted where it plays); the bars used."""
        act = {nid: set(self.active(nid, idx)) for nid in ids}
        used, per_bar = [], []
        for i in bars:
            vals = [self.bar_level(nid, i) for nid in ids if i in act[nid]]
            if vals:
                used.append(i)
                per_bar.append(_powsum(vals))
        return (_powmean(per_bar) if per_bar else None), used


# ------------------------------------------------------------------------------------------------ roles

def infer_roles(song=None, report=None, *, band=None, roles=None, lead=None, bed=None, rhythm=None, low=None,
                other=None, fx=None) -> tuple[dict, dict]:
    """(id -> role, id -> why) for every track (and the report's non-bus nodes). Explicit > band > report > id."""
    out: dict[str, str] = {}
    why: dict[str, str] = {}
    ids: list[str] = []
    ghosts = set(getattr(song, '_ghosts', {}) or {})
    if song is not None:
        ids += [t for t, tr in song.tracks.items() if not tr.mute and t not in ghosts]
    rep = load_report(report) if report is not None else None
    rnodes = {n['id']: n for n in (rep or {}).get('nodes', []) if not n.get('bus')}
    ids += [i for i in rnodes if i not in ids and not i.endswith('-key')]
    for nid in ids:
        rr = (rnodes.get(nid) or {}).get('role')
        if rr in _ANALYSIS_ROLE:
            out[nid], why[nid] = _ANALYSIS_ROLE[rr], f"report role {rr}"
        else:
            out[nid], why[nid] = role_from_id(nid), 'track id'
    for nid, tr in (getattr(song, 'tracks', None) or {}).items():   # a hero (agentsound.heroes.hero) leads
        if getattr(tr, 'hero', None) is not None and nid in out:
            out[nid], why[nid] = 'lead', 'hero()'
    if not any(r == 'lead' for r in out.values()):   # no lead role: the report's melodic lead (dynamics kind)
        cands = [n for n in rnodes.values() if (n.get('dynamics') or {}).get('kind') == 'lead']
        for n in sorted(cands, key=lambda n: -n.get('lufs', -120))[:2]:
            out[n['id']], why[n['id']] = 'lead', 'report: the melodic lead (nodes[].dynamics.kind)'
    if band is not None:
        jazz = False
        try:
            from . import bands as _bands
            jazz = _bands.get(band.preset).genre == 'jazz'
        except Exception:   # a hand-made Band
            pass
        for role_name, tr in band.roles.items():
            tid = getattr(tr, 'id', None)
            if tid is None:
                continue
            r = 'lead' if jazz and role_name in ('piano', 'sax') else role_from_id(role_name)
            if role_name in ('comp', 'keys', 'gtr', 'gtr_l', 'gtr_r', 'horns', 'pluck', 'arp'):
                r = 'other'
            out[tid], why[tid] = r, f"band {band.preset} role {role_name!r}"
    for role, arg in (('lead', lead), ('bed', bed), ('rhythm', rhythm), ('low', low), ('other', other), ('fx', fx)):
        for nid in _ids(arg):
            out[nid], why[nid] = role, 'explicit'
    for nid, role in (roles or {}).items():
        if role not in ROLES:
            raise ComposeError(f"mixer roles: {nid!r} -> {role!r} is not a role ({', '.join(ROLES)})")
        out[_ids(nid)[0]], why[_ids(nid)[0]] = role, 'explicit'
    return out, why


def _ids(x) -> list[str]:
    if x is None:
        return []
    if isinstance(x, (list, tuple, set)):
        return [i for y in x for i in _ids(y)]
    return [x if isinstance(x, str) else getattr(x, 'id')]


# ------------------------------------------------------------------------------------------------ measuring

@dataclass
class SectionBalance:
    """One section as the mixer hears it."""
    name: str
    hook: bool
    judged: bool
    lead: str | None = None
    lead_level: float | None = None
    rel: dict = field(default_factory=dict)          # group / other node -> dB vs the lead
    members: dict = field(default_factory=dict)      # group -> node ids playing
    bed_from: str = ''                               # 'space' (report bedVsLeadDb) or 'bars'
    why: str = ''

    def line(self, prof: MixProfile | None = None) -> str:
        if not self.judged:
            return f"{self.name:<12} not judged ({self.why})"
        parts = []
        for g in GROUPS:
            if g in self.rel:
                w = f" [{prof.window(g, self.hook)[0]:+g}..{prof.window(g, self.hook)[1]:+g}]" if prof else ''
                parts.append(f"{g} {self.rel[g]:+.1f}{w}")
        loud = [(k, v) for k, v in self.rel.items() if k not in GROUPS]
        if loud:
            k, v = max(loud, key=lambda kv: kv[1])
            parts.append(f"top other {k} {v:+.1f}")
        return f"{self.name:<12} {'HOOK ' if self.hook else '     '}lead {self.lead} | " + ', '.join(parts)


def hook_sections(view: View, names=None) -> set[str]:
    """Sections the lead has to own: names like chorus / drop / hook / lift / head, else the loudest full ones."""
    if names is not None:
        return set(_ids(names)) if not isinstance(names, str) else {names}
    hooks = {s['name'] for s in view.sections if _HOOK_RE.search(s['name'])}
    if hooks:
        return hooks
    return {s['name'] for s in view.sections if s.get('lufs', -120) >= view.loudest - 1.5}


def features(song) -> dict:
    """{section name: track id} of the song's featured tracks (track.feature(section): a bass solo, a drum break) -
    the featured track is the lead of that section."""
    out: dict = {}
    for tid, tr in (getattr(song, 'tracks', None) or {}).items():
        for name in getattr(tr, 'featured', ()) or ():
            out[name] = tid
    return out


def measure(report, roles: dict, prof: MixProfile, hooks=None, featured=None) -> list[SectionBalance]:
    """Every section's balance vs its lead: the loudest lead-role part that plays in at least half its bars - or the
    track featured in that section (featured={section: id}, mixer.features(song): track.feature(bass_solo) makes the
    bass the lead of the bass solo and takes it out of its group there)."""
    view = report if isinstance(report, View) else View(load_report(report))
    hook_names = hook_sections(view, hooks)
    leads = [n for n, r in roles.items() if r == 'lead' and n in view.nodes]
    featured = featured or {}
    out = []
    for sec in view.sections:
        name = sec['name']
        idx = view.bar_index(sec)
        sb = SectionBalance(name, name in hook_names, False)
        out.append(sb)
        if len(idx) < 2:
            sb.why = 'shorter than 2 bars'
            continue
        if sec.get('lufs', -120) < view.loudest - 12:
            sb.why = f"quiet ({sec.get('lufs', -120):.1f} LUFS)"
            continue
        f = featured.get(name)
        cands = [f] if f in view.nodes else leads
        playing = {n: view.active(n, idx) for n in cands}
        playing = {n: a for n, a in playing.items() if len(a) >= max(2, 0.5 * len(idx))}
        if not playing:
            sb.why = 'no lead plays in half its bars'
            continue
        lead = max(playing, key=lambda n: view.level(n, playing[n]))
        la = playing[lead]
        sb.judged, sb.lead, sb.lead_level = True, lead, view.level(lead, la)
        for g in GROUPS:
            ids = [n for n, r in roles.items() if r == g and n != lead and n in view.nodes and view.active(n, idx)]
            if not ids:
                continue
            lvl, used = view.group_level(ids, la, idx)
            if lvl is None or len(used) < max(2, 0.25 * len(la)):
                continue
            sb.rel[g] = round(lvl - view.level(lead, used), 2)
            sb.members[g] = ids
        sp = view.space.get(name) or {}
        if 'bed' in sb.rel and sp.get('bedVsLeadDb') is not None and sp.get('lead') == lead:
            sb.rel['bed'], sb.bed_from = float(sp['bedVsLeadDb']), 'space'
        elif 'bed' in sb.rel:
            sb.bed_from = 'bars'
        for n, r in roles.items():   # every other part (and a second lead) on its own
            if n == lead or n not in view.nodes or r not in ('other', 'lead'):
                continue
            act = set(view.active(n, idx))
            used = [i for i in la if i in act]
            if len(used) >= max(2, 0.25 * len(la)):
                sb.rel[n] = round(view.level(n, used) - view.level(lead, used), 2)
    return out


# ------------------------------------------------------------------------------------------------ moves

@dataclass
class Move:
    """One mix move: kind trim | ride | duck | eq, on node(s), with the reason."""
    kind: str
    node: str
    db: float = 0.0
    section: str | None = None
    why: str = ''
    params: dict = field(default_factory=dict)

    def __str__(self) -> str:
        if self.kind == 'trim':
            return f"trim {self.node} {self.db:+.1f} dB - {self.why}"
        if self.kind == 'ride':
            return f"ride {self.node} {self.db:+.1f} dB in {self.section} - {self.why}"
        if self.kind == 'duck':
            p = self.params
            return (f"duck {', '.join(p['targets'])} under {p['key']}" + (f" ({p['pitches']})" if p.get('pitches') else '')
                    + f" by {p['depth']:g} dB - {self.why}")
        if self.kind == 'eq':
            p = self.params
            return f"eq {self.node} {p['gain']:+.1f} dB at {p['freq']:g} Hz (q {p['q']:g}) - {self.why}"
        return f"{self.kind} {self.node} - {self.why}"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _r1(x: float) -> float:
    return round(x * 2.0) / 2.0 if abs(x) >= 1.0 else round(x, 1)   # half-dB steps above 1 dB


def _err(rel: float, window: tuple) -> float:
    """> 0: louder than the window allows (vs the lead), < 0: quieter, 0: inside."""
    lo, hi = window
    return rel - hi if rel > hi else rel - lo if rel < lo else 0.0


def _has_duck(song, target: str, key: str) -> bool:
    if song is None:
        return False
    try:
        node = song.node(target)
    except ComposeError:
        return False
    keys = {key} | {g for g, (k, _) in getattr(song, '_ghosts', {}).items() if k == key}
    return any(f.type in ('ducker', 'compressor') and f.sidechain in keys for f in node.fx)


def _kick_pitches(song, nid: str) -> list[int]:
    t = getattr(song, 'tracks', {}).get(nid) if song is not None else None
    if t is None:
        return []
    return sorted({n.pitch for n in t.notes if n.pitch in (35, 36)})


_BAND_HZ = {'sub': 45.0, 'bass': 120.0, 'lowmid': 450.0, 'mid': 1400.0, 'presence': 3300.0, 'brilliance': 7000.0,
            'air': 12000.0}


def _bounds(prof: MixProfile, g: str, hook: bool) -> tuple:
    """The judged window of a group in a section: outside the hooks drums and bass are only judged for being too
    loud (a softer verse is the arrangement's business), the bed on both sides."""
    lo, hi = prof.window(g, hook)
    return (lo if hook or g == 'bed' else -math.inf, hi)


def _best_shift(items) -> tuple[float, float]:
    """items: ((full lo, hi), (inner lo, hi), weight, _) = the shifts that put a section inside its window / its inner
    half. The shift that puts the most weight inside (the smallest one on ties), moved into the inner half of every
    window it satisfies (as close to 0 as that allows). Returns (shift, covered weight)."""
    def cover(x: float) -> float:
        return sum(w for (a, z), _, w, _ in items if a - 1e-9 <= x <= z + 1e-9)
    if all(a - 1e-9 <= 0.0 <= z + 1e-9 for (a, z), _, _, _ in items):
        return 0.0, cover(0.0)
    cands = {0.0} | {v for (a, z), _, _, _ in items for v in (a, z) if math.isfinite(v)}
    best = max(cover(x) for x in cands)
    x0 = min((x for x in cands if cover(x) >= best - 1e-9), key=lambda x: (abs(x), x))
    inside = [it for it in items if it[0][0] - 1e-9 <= x0 <= it[0][1] + 1e-9]
    ia, iz = max(it[1][0] for it in inside), min(it[1][1] for it in inside)
    if ia > iz:
        ia, iz = max(it[0][0] for it in inside), min(it[0][1] for it in inside)
    return _clamp(0.0, ia, iz), best


def propose(report, roles: dict, prof: MixProfile, *, song=None, mix=None, hooks=None, max_step: float = MAX_STEP,
            balances=None) -> tuple[list[Move], list[SectionBalance]]:
    """The moves that bring the measured balance to the profile's targets (deterministic, bounded)."""
    rep = load_report(report)
    view = View(rep)
    bal = balances if balances is not None else measure(view, roles, prof, hooks, features(song))
    mix = normalize(mix or {})
    judged = [b for b in bal if b.judged]
    moves: list[Move] = []
    if not judged:
        return moves, bal
    # 1) per section: how far each group sits outside its window; the part all bounded groups share is the lead's
    corr: dict[str, float] = {}
    for b in judged:
        errs = {g: _err(b.rel[g], _bounds(prof, g, b.hook)) for g in GROUPS if g in b.rel}
        c = 0.0
        if len(errs) >= 2:
            if all(e > 0 for e in errs.values()):
                c = min(errs.values())
            elif all(e < 0 for e in errs.values()):
                c = max(errs.values())
        corr[b.name] = c
    use = [b for b in judged if b.hook] or judged
    # the lead: trim = the median over the hooks, rides where a section differs; its peak (pre-master) stays under
    # -0.5 dBFS - what the lead cannot rise, the band comes down instead
    leads = sorted({b.lead for b in judged})
    shift: dict[str, float] = {}          # section -> how far the lead moves there (trim + ride)
    for lead in leads:
        mine = [b for b in use if b.lead == lead] or [b for b in judged if b.lead == lead]
        t0 = statistics.median(corr[b.name] for b in mine)
        peak = view.nodes.get(lead, {}).get('peakDb', -120.0)
        trim = min(t0, max(0.0, -0.5 - peak)) if t0 > 0 else t0
        trim = _clamp(trim, -max_step, max_step)
        if abs(trim) < 0.3:
            trim = 0.0
        else:
            secs = ', '.join(f"{b.name} {corr[b.name]:+.1f}" for b in mine)
            moves.append(Move('trim', lead, _r1(trim), why=f"the band sits above its window around the lead in the "
                                                          f"hooks ({secs}; lead peak {peak:+.1f} dBFS)"
                              if trim > 0 else f"the band sits under its window around the lead in the hooks ({secs})"))
        for b in judged:
            if b.lead != lead:
                continue
            ride = _clamp(corr[b.name] - t0, -3.0, 3.0)
            cur = mix['ride'].get(lead, {}).get(b.name, 0.0)
            if abs(ride) < 0.5 or abs(cur + ride) > MAX_RIDE or (ride > 0 and trim + ride > max(0.0, -0.5 - peak)):
                ride = 0.0
            else:
                moves.append(Move('ride', lead, _r1(ride), b.name,
                                  why=f"{'hook' if b.hook else 'verse'}: the band sits {corr[b.name]:+.1f} dB off its "
                                      f"window around the lead here ({t0:+.1f} in the hooks)"))
            shift[b.name] = trim + ride
    # 2) the groups, after the lead's move: the song-wide trim that puts the most sections (hooks count double) inside
    #    the window, into its inner half; the bed also rides the sections that stay outside
    for g in GROUPS:
        sec = [b for b in judged if g in b.rel]
        if not sec:
            continue
        members = sorted({m for b in sec for m in b.members.get(g, [])})
        rel = {b.name: b.rel[g] - shift.get(b.name, 0.0) for b in sec}
        lo, hi = prof.window(g, True)

        def items(off: float = 0.0):
            out = []
            for b in sec:   # coverage: the window + TOL; a move lands MARGIN inside it
                a, z = _bounds(prof, g, b.hook)
                r = rel[b.name] + off
                out.append(((a - TOL - r, z + TOL - r), (a + MARGIN - r, z - MARGIN - r), 2.0 if b.hook else 1.0, b))
            return out
        x, _ = _best_shift(items())
        detail = ', '.join(f"{b.name} {b.rel[g]:+.1f}" for b in sec)
        duck_off = 0.0
        hook_down = [b for b in sec if b.hook and _err(rel[b.name], _bounds(prof, g, True)) > 1.0]
        if g == 'bed' and prof.bed_duck_db > 0 and leads and (x < -1.0 or len(hook_down) * 2 > len([b for b in sec if b.hook])):
            lead = max(leads, key=lambda L: sum(1 for b in sec if b.lead == L))
            targets = [m for m in members if not _has_duck(song, m, lead) and not _mix_has_duck(mix, m, lead)]
            if targets:
                lvl = view.nodes.get(lead, {}).get('rmsDb', -30.0)
                moves.append(Move('duck', targets[0], prof.bed_duck_db, why=(
                    f"the bed crowds the lead ({detail}, want {lo:+g}..{hi:+g}): carve before pushing the lead - "
                    f"the bed dips while {lead} plays"), params={
                    'targets': targets, 'key': lead, 'depth': prof.bed_duck_db,
                    'threshold': float(round(_clamp(lvl - 12.0, -45.0, -18.0))), 'attack': 15.0, 'hold': 60.0,
                    'release': 260.0}))
                duck_off = -0.6 * prof.bed_duck_db   # about what the duck takes off on the bars the lead plays
                x, _ = _best_shift(items(duck_off))
        trim = _clamp(x, -max_step, max_step)
        if abs(trim) >= 0.5:
            for m in members:
                moves.append(Move('trim', m, _r1(trim), why=f"{g} vs the lead ({detail}; want {lo:+g}..{hi:+g} "
                                                            f"in the hooks)"))
        else:
            trim = 0.0
        if g != 'bed':
            continue
        for (fa, fz), (ia, iz), _, b in items(duck_off):
            if fa - 1e-9 <= trim <= fz + 1e-9:
                continue
            ride = _clamp(_clamp(trim, ia, iz) - trim, -4.0, 4.0)
            if abs(ride) < 0.5:
                continue
            for m in b.members.get(g, []):
                if abs(mix['ride'].get(m, {}).get(b.name, 0.0) + ride) <= MAX_RIDE:
                    moves.append(Move('ride', m, _r1(ride), b.name, why=f"bed {b.rel[g]:+.1f} dB vs the lead in {b.name}"))
    # 3) other parts louder than the lead allows
    others = sorted({k for b in judged for k in b.rel if k not in GROUPS})
    for n in others:
        over = [(b.name, b.rel[n] - shift.get(b.name, 0.0) - prof.window('other', b.hook)[1]) for b in judged
                if n in b.rel]
        over = [(s, d) for s, d in over if d > TOL]
        if not over:
            continue
        worst = max(d for _, d in over)
        moves.append(Move('trim', n, _r1(-_clamp(worst + MARGIN, 0, max_step)), why=(
            f"{roles.get(n, 'other')} part above the lead's limit ({', '.join(f'{s} +{d:.1f}' for s, d in over)} "
            f"over {prof.other_max:+g} dB in the hooks)")))
    # 4) masking: a part that shares the lead's band gets a dip; kick vs bass low-end ownership
    lead_ids = {b.lead for b in judged}
    for w in rep.get('warnings', []):
        if w.get('code') != 'masking' or len(w.get('nodes') or []) != 2:
            continue
        a, c = w['nodes']
        m = re.search(r'of the (\w+) band', w.get('message', ''))
        band = m.group(1) if m else None
        if band in ('lowmid', 'mid', 'presence') and (a in lead_ids) != (c in lead_ids):
            other_n = c if a in lead_ids else a
            if roles.get(other_n) in ('fx',) or other_n in mix['eq']:
                continue
            moves.append(Move('eq', other_n, prof.dip_db, why=f"masks the lead in the {band} band ({w.get('message', '')[:90]}...)",
                              params={'freq': _BAND_HZ[band], 'gain': prof.dip_db, 'q': 1.0}))
        elif band in ('sub', 'bass') and prof.kick_bass_duck_db > 0:
            ra, rc = roles.get(a), roles.get(c)
            if {ra, rc} != {'rhythm', 'low'} or 'alternate' in w.get('message', ''):
                continue
            kit, bass = (a, c) if ra == 'rhythm' else (c, a)
            if _has_duck(song, bass, kit) or _mix_has_duck(mix, bass, kit):
                continue
            kicks = _kick_pitches(song, kit)
            if song is not None and not kicks and kit not in getattr(song, 'tracks', {}):
                continue
            moves.append(Move('duck', bass, prof.kick_bass_duck_db, why=(
                f"kick and bass fight in the {band} band (little ducking between them): the kick owns the attack"),
                params={'targets': [bass], 'key': kit, 'pitches': 'kick' if kicks else None,
                        'depth': prof.kick_bass_duck_db, 'attack': 2.0, 'hold': 10.0, 'release': 120.0}))
    return _dedupe(moves), bal


def _mix_has_duck(mix: dict, target: str, key: str) -> bool:
    return any(d['key'] == key and target in d['targets'] for d in mix.get('duck', []))


def _dedupe(moves: list[Move]) -> list[Move]:
    out, seen = [], set()
    for m in moves:
        k = (m.kind, m.node, m.section)
        if m.kind in ('trim', 'ride') and k in seen:
            continue
        seen.add(k)
        out.append(m)
    return out


# ------------------------------------------------------------------------------------------------ MIX dicts

def normalize(mix: dict | None) -> dict:
    """A validated deep copy of a MIX dict with every key present (strict: unknown keys are errors)."""
    mix = copy.deepcopy(mix or {})
    if not isinstance(mix, dict):
        raise ComposeError(f"MIX must be a dict like {{'trim': {{'lead': 1.5}}}}, got {type(mix).__name__}")
    bad = [k for k in mix if k not in MIX_KEYS]
    if bad:
        raise ComposeError(f"MIX: unknown key(s) {', '.join(map(repr, bad))} (allowed: {', '.join(MIX_KEYS)})")
    out = {'trim': {}, 'ride': {}, 'duck': [], 'eq': {}}
    if 'profile' in mix:
        out['profile'] = str(mix['profile'])
    out['ramp'] = _db(mix.get('ramp', 1.0), 'MIX ramp (beats)', 0.0, 16.0)
    for nid, db in (mix.get('trim') or {}).items():
        out['trim'][nid] = _db(db, f"MIX trim {nid!r}", -48, 24)
    for nid, secs in (mix.get('ride') or {}).items():
        if not isinstance(secs, dict):
            raise ComposeError(f"MIX ride {nid!r} must be {{section: dB}}, got {secs!r}")
        out['ride'][nid] = {s: _db(v, f"MIX ride {nid!r} {s!r}", -24, 24) for s, v in secs.items()}
    for i, d in enumerate(mix.get('duck') or []):
        if not isinstance(d, dict) or 'targets' not in d or 'key' not in d:
            raise ComposeError(f"MIX duck #{i} must be {{'targets': [...], 'key': id, 'depth': dB, ...}}, got {d!r}")
        extra = [k for k in d if k not in DUCK_KEYS]
        if extra:
            raise ComposeError(f"MIX duck #{i}: unknown key(s) {extra} (allowed: {', '.join(DUCK_KEYS)})")
        e = {k: v for k, v in d.items() if v is not None}
        e['targets'] = _ids(d['targets'])
        e['key'] = _ids(d['key'])[0]
        out['duck'].append(e)
    for nid, bells in (mix.get('eq') or {}).items():
        bells = [bells] if isinstance(bells, dict) else list(bells)
        if not 1 <= len(bells) <= 3:
            raise ComposeError(f"MIX eq {nid!r}: 1-3 bells ({{'freq', 'gain', 'q'}}), got {len(bells)}")
        clean = []
        for b in bells:
            extra = [k for k in b if k not in EQ_KEYS]
            if extra or 'freq' not in b or 'gain' not in b:
                raise ComposeError(f"MIX eq {nid!r}: a bell is {{'freq': Hz, 'gain': dB, 'q': 1.0}}, got {b!r}")
            clean.append({'freq': _db(b['freq'], f"MIX eq {nid!r} freq", 20, 20000),
                          'gain': _db(b['gain'], f"MIX eq {nid!r} gain", -24, 24),
                          'q': _db(b.get('q', 1.0), f"MIX eq {nid!r} q", 0.1, 20)})
        out['eq'][nid] = clean
    if 'log' in mix:
        out['log'] = [str(x) for x in mix['log']]
    return out


def _db(x, what: str, lo: float, hi: float) -> float:
    if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or not lo <= x <= hi:
        raise ComposeError(f"{what} must be a number in {lo:g}..{hi:g}, got {x!r}")
    return float(x)


def merge(mix: dict, moves: list[Move]) -> dict:
    """MIX + moves (trims and rides add up, clamped; ducks and dips append)."""
    out = normalize(mix)
    for m in moves:
        if m.kind == 'trim':
            out['trim'][m.node] = round(_clamp(out['trim'].get(m.node, 0.0) + m.db, -MAX_TRIM, MAX_TRIM), 2)
        elif m.kind == 'ride':
            r = out['ride'].setdefault(m.node, {})
            r[m.section] = round(_clamp(r.get(m.section, 0.0) + m.db, -MAX_RIDE, MAX_RIDE), 2)
        elif m.kind == 'duck':
            out['duck'].append({k: v for k, v in m.params.items() if v is not None})
        elif m.kind == 'eq':
            bells = out['eq'].setdefault(m.node, [])
            if len(bells) < 3:
                bells.append(dict(m.params))
    out['trim'] = {k: v for k, v in out['trim'].items() if abs(v) >= 0.05}
    out['ride'] = {k: {s: v for s, v in r.items() if abs(v) >= 0.05} for k, r in out['ride'].items()}
    out['ride'] = {k: r for k, r in out['ride'].items() if r}
    return out


def apply(song, mix: dict | None):
    """Write a MIX dict into the song (see the module docstring); returns the song. Unknown nodes / sections are
    errors; applying twice is an error (the song records the MIX it got as song.applied_mix)."""
    from .patches import FX
    m = normalize(mix)
    if getattr(song, 'applied_mix', None) is not None:
        raise ComposeError("this song already has a MIX applied (s.mix() / the CLI's module-level MIX): merge them "
                           "into one dict")
    names = [s.name for s in song.sections]

    def node(nid: str, what: str):
        try:
            return song.node(nid)
        except ComposeError:
            close = difflib.get_close_matches(nid, list(song.tracks) + list(song.buses), n=2)
            raise ComposeError(f"MIX {what}: no track or bus {nid!r}" + (f" - did you mean {' / '.join(close)}?"
                                                                       if close else '')) from None

    for nid, bells in m['eq'].items():
        add_eq_dip(node(nid, 'eq'), bells, EQ_NAME)
    for d in m['duck']:
        for t in d['targets']:
            node(t, 'duck target')
        node(d['key'], 'duck key')
        params = {k: v for k, v in d.items() if k not in ('targets', 'key', 'pitches')}
        song.sidechain(*d['targets'], key=d['key'], pitches=d.get('pitches'), **params)
    for nid in sorted(set(m['trim']) | set(m['ride'])):
        n = node(nid, 'trim / ride')
        if n.kind == 'master':
            raise ComposeError("MIX trim / ride: the master is the mastering engineer's (master.gain_db / limiter)")
        trim = m['trim'].get(nid, 0.0)
        n.add_fx(FX('utility', {'gain': round(trim, 3)}, name=FX_NAME))
        rides = m['ride'].get(nid, {})
        for s in rides:
            if s not in names:
                close = difflib.get_close_matches(s, names, n=1)
                raise ComposeError(f"MIX ride {nid!r}: no section {s!r}" + (f" - did you mean {close[0]!r}?" if close else '')
                                   + f" (sections: {', '.join(names)})")
        if rides:
            n.automate(f'fx.{FX_NAME}.gain', _ride_points(song, trim, rides, m['ramp']))
    song.applied_mix = m
    return song


def add_eq_dip(node, bells, name: str = EQ_NAME):
    """Append one eq insert named `name` with 1-3 bells ({'freq', 'gain', 'q'}: presence dips, mud cuts) to a track /
    bus - what a MIX 'eq' entry writes (and the hero wrapper's competitor dips, name 'hero_dip')."""
    from .patches import FX
    bells = [bells] if isinstance(bells, dict) else list(bells)
    if not 1 <= len(bells) <= 3:
        raise ComposeError(f"eq dip on {getattr(node, 'id', node)!r}: 1-3 bells, got {len(bells)}")
    params = {}
    for k, b in enumerate(bells, start=1):
        params.update({f'peak{k}.freq': b['freq'], f'peak{k}.gain': b['gain'], f'peak{k}.q': b.get('q', 1.0)})
    node.add_fx(FX('eq', params, name=name))
    return node


def _ride_points(song, trim: float, rides: dict, ramp: float) -> list:
    pts, prev = [], None
    for sec in song.sections:
        v = round(trim + rides.get(sec.name, 0.0), 3)
        if prev is None:
            pts.append((0.0, v))
        elif v != prev:
            r = min(ramp, 0.5 * sec.length, max(0.0, sec.start - pts[-1][0] - 1e-3))
            if r > 0:
                pts.append((sec.start - r, prev))
                pts.append((sec.start, v))
            else:
                pts.append((sec.start, v, 'step'))
        prev = v
    return pts


def describe_mix(mix: dict) -> str:
    """One line: what a MIX does."""
    m = normalize(mix)
    n_r = sum(len(r) for r in m['ride'].values())
    return (f"{len(m['trim'])} trim{'s' * (len(m['trim']) != 1)}, {n_r} ride{'s' * (n_r != 1)}, "
            f"{len(m['duck'])} duck{'s' * (len(m['duck']) != 1)}, {len(m['eq'])} eq dip{'s' * (len(m['eq']) != 1)}")


def to_code(mix: dict, log=(), name: str = 'MIX') -> str:
    """Python source of a MIX dict (pasteable into song.py), the log as comments above it."""
    m = normalize(mix)
    m.pop('log', None)
    if m.get('ramp') == 1.0:
        m.pop('ramp')
    for k in ('trim', 'ride', 'duck', 'eq'):
        if not m[k]:
            m.pop(k)
    lines = [f"# {x}" for x in log]
    lines.append(f"{name} = {{")
    for k, v in m.items():
        if k in ('duck', 'ride', 'eq') and len(v) > 1:
            op, cl = ('[', ']') if k == 'duck' else ('{', '}')
            lines.append(f"    {k!r}: {op}")
            lines += [f"        {x!r}," for x in v] if k == 'duck' else [f"        {n!r}: {x!r}," for n, x in v.items()]
            lines.append(f"    {cl},")
        else:
            lines.append(f"    {k!r}: {v!r},")
    lines.append('}')
    return '\n'.join(lines) + '\n'


# ------------------------------------------------------------------------------------------------ plan

@dataclass
class MixPlan:
    """What the mix engineer intends: roles, the genre's targets, the measured balance (with a report), the moves."""
    profile: MixProfile
    roles: dict
    why: dict
    hooks: set
    balances: list = field(default_factory=list)
    moves: list = field(default_factory=list)
    glue: tuple = ()
    base: dict = field(default_factory=dict)

    def mix(self) -> dict:
        """The plan's moves on top of the MIX it started from."""
        return merge(self.base, self.moves)

    def describe(self) -> str:
        p = self.profile
        lines = [f"mix plan ({p.name}): {p.notes}"]
        by = {}
        for n, r in self.roles.items():
            by.setdefault(r, []).append(n)
        lines.append('  roles: ' + '; '.join(f"{r} {', '.join(sorted(by[r]))}" for r in ROLES if r in by))
        lines.append(f"  targets vs the lead (hooks): rhythm {p.rhythm[0]:+g}..{p.rhythm[1]:+g}, low {p.low[0]:+g}.."
                     f"{p.low[1]:+g}, bed {p.bed[0]:+g}..{p.bed[1]:+g}, others <= {p.other_max:+g} dB; the lead "
                     f"{p.lead_ride_db:+g} dB further in front in the hooks, the bed {p.bed_ride_db:+g} dB in the verses")
        lines.append(f"  hook sections: {', '.join(sorted(self.hooks)) or '-'}")
        if self.balances:
            lines.append('  measured (dB vs the section lead):')
            lines += ['    ' + b.line(p) for b in self.balances]
        if self.moves:
            lines.append('  moves:')
            lines += ['    ' + str(m) for m in self.moves]
        else:
            lines.append('  moves: none - the balance is inside the targets' if self.balances else '  moves: -')
        for g in self.glue:
            lines.append(f"  glue: {g}")
        return '\n'.join(lines)

    def __str__(self) -> str:
        return self.describe()


def plan(song=None, report=None, *, profile=None, lead=None, bed=None, rhythm=None, low=None, other=None,
         roles=None, band=None, hooks=None, base=None, max_step: float = MAX_STEP) -> MixPlan:
    """The mix plan for a song (and its report, when there is one).

    Without a report: the static carve plan of the genre - the bed sidechained a little under the lead (profiles that
    do it), the bass under the kick, the lead ridden up in the hook sections and the bed down in the verses.
    With a report (a dict, a report.json path or a song dir): the measured balance per section and the moves that
    bring it to the targets (what auto() applies per pass).
    profile: an analysis profile name (default: the report's, then 'default')."""
    rep = load_report(report) if report is not None else None
    pname = profile or ((rep or {}).get('reference') or {}).get('profile') or \
        (getattr(song, 'analysis_profile', None)) or 'default'
    prof = get_profile(pname)
    rl, why = infer_roles(song, rep, band=band, roles=roles, lead=lead, bed=bed, rhythm=rhythm, low=low, other=other)
    base = normalize(base if base is not None else getattr(song, 'applied_mix', None) or {})
    if rep is not None:
        view = View(rep)
        hk = hook_sections(view, hooks)
        moves, bal = propose(rep, rl, prof, song=song, mix=base, hooks=hook_sections(view, hooks), max_step=max_step)
        return MixPlan(prof, rl, why, hk, bal, moves, prof.glue, base)
    if song is None:
        raise ComposeError("mixer.plan needs a song or a report")
    names = [s.name for s in song.sections]
    hk = set(_ids(hooks)) if hooks is not None else {n for n in names if _HOOK_RE.search(n)}
    moves = []
    leads = [n for n, r in rl.items() if r == 'lead']
    beds = [n for n, r in rl.items() if r == 'bed']
    if leads and beds and prof.bed_duck_db > 0:
        L = leads[0]
        tg = [b for b in beds if not _has_duck(song, b, L)]
        if tg:
            moves.append(Move('duck', tg[0], prof.bed_duck_db, why=f"carving: the bed dips while {L} plays", params={
                'targets': tg, 'key': L, 'depth': prof.bed_duck_db, 'threshold': -34.0, 'attack': 15.0, 'hold': 60.0,
                'release': 260.0}))
    kits = [n for n, r in rl.items() if r == 'rhythm' and _kick_pitches(song, n)]
    if kits and prof.kick_bass_duck_db > 0:
        for b in (n for n, r in rl.items() if r == 'low'):
            if not _has_duck(song, b, kits[0]):
                moves.append(Move('duck', b, prof.kick_bass_duck_db, why='low-end ownership: the kick owns the attack',
                                  params={'targets': [b], 'key': kits[0], 'pitches': 'kick', 'depth': prof.kick_bass_duck_db,
                                          'attack': 2.0, 'hold': 10.0, 'release': 120.0}))
    verses = [n for n in names if n not in hk]
    if hk and verses:
        for L in leads[:1]:
            if prof.lead_ride_db:
                for s in names:
                    if s in hk:
                        moves.append(Move('ride', L, prof.lead_ride_db, s, why='the lead up in the hook sections'))
        if prof.bed_ride_db:
            for b in beds:
                for s in verses:
                    moves.append(Move('ride', b, prof.bed_ride_db, s, why='the bed down in the verses'))
    return MixPlan(prof, rl, why, hk, [], moves, prof.glue, base)


# ------------------------------------------------------------------------------------------------ check

@dataclass
class Finding:
    """One note of the mix engineer: code, severity (warn / info), what, the concrete fix (and a MIX snippet)."""
    code: str
    severity: str
    message: str
    fix: str = ''
    mix: dict | None = None
    nodes: list = field(default_factory=list)
    sections: list = field(default_factory=list)

    def __str__(self) -> str:
        s = f"[{self.severity}] {self.code}: {self.message}"
        if self.fix:
            s += f"\n    fix: {self.fix}"
        if self.mix:
            s += f"\n    MIX: {json.dumps(self.mix)}"
        return s


def _third(rep: dict, lo: float, hi: float) -> float | None:
    t = (rep.get('global') or {}).get('thirdOctave') or {}
    v = [d for hz, d in zip(t.get('hz', []), t.get('vsRefDb', [])) if lo <= hz <= hi]
    return sum(v) / len(v) if v else None


def _top(rep: dict, band: str, exclude=(), n: int = 2) -> list[tuple[str, float]]:
    rows = [(x['id'], (x.get('mixSharePct') or {}).get(band, 0.0)) for x in rep.get('nodes', [])
            if not x.get('bus') and x['id'] not in exclude]
    return [r for r in sorted(rows, key=lambda r: -r[1]) if r[1] >= 15.0][:n]


def check(report, *, profile=None, song=None, roles=None, lead=None, hooks=None, band=None) -> list[Finding]:
    """A mix engineer's findings on a report (dict / report.json / song dir), most important first: the lead not in
    front, bed / drums / bass off their genre window, parts louder than the lead, masking, low-end fights, flat
    dynamics, mud (200-400 Hz), harshness (2-5 kHz), width, headroom, loudness, clicks - each with a concrete fix."""
    rep = load_report(report)
    pname = profile or (rep.get('reference') or {}).get('profile') or 'default'
    prof = get_profile(pname)
    rl, _ = infer_roles(song, rep, band=band, roles=roles, lead=lead)
    view = View(rep)
    bal = measure(view, rl, prof, hooks, features(song))
    judged = [b for b in bal if b.judged]
    out: list[Finding] = []
    if not any(r == 'lead' for r in rl.values()):
        out.append(Finding('no_lead', 'warn', 'no part is a lead (no role lead, no melodic lead in the report)',
                           "name the melody track lead / hook / melody, or pass lead='<id>' to mixer.check / plan"))
    names = {'rhythm': 'drums', 'low': 'bass', 'bed': 'bed'}
    for g in GROUPS:
        hot = [(b, b.rel[g]) for b in judged if g in b.rel and _err(b.rel[g], _bounds(prof, g, b.hook)) > 0.75]
        cold = [(b, b.rel[g]) for b in judged if g in b.rel and _err(b.rel[g], _bounds(prof, g, b.hook)) < -0.75]
        for lst, word, sign in ((hot, 'too loud', 1), (cold, 'too quiet', -1)):
            if not lst:
                continue
            members = sorted({m for b, _ in lst for m in b.members.get(g, [])})
            worst = max((sign * _err(v, _bounds(prof, g, b.hook)) for b, v in lst))
            lo, hi = prof.window(g, True)
            where = ', '.join(f"{b.name} {v:+.1f}" for b, v in lst)
            fix = {('bed', 1): f"carve first: sidechain the bed to the lead ~{max(prof.bed_duck_db, 2):g} dB (duck), "
                               f"then trim it; a presence dip on the lead where it masks",
                   ('rhythm', 1): 'pull the drums down (their peaks too: transients read louder than their RMS)'
                   + (' - jazz drums sit clearly behind the piano' if prof.name == 'jazz' else ''),
                   ('low', 1): 'trim the bass; if kick and bass fight, duck the bass under the kick',
                   ('bed', -1): 'raise the bed (thin under the lead) or add a sustained layer',
                   ('rhythm', -1): 'raise the drums (or their transients) - the groove must carry',
                   ('low', -1): 'raise the bass: the walking / root line must stay followable'}[(g, sign)]
            code = f"{names[g]}_{'too_loud' if sign > 0 else 'too_quiet'}"
            if prof.name == 'jazz' and g == 'rhythm' and sign > 0:
                code = 'drums_too_loud_for_jazz'
            out.append(Finding(code, 'warn' if worst >= 1.5 or g == 'bed' else 'info',
                               f"{names[g]} {word} vs the lead in {where} (want {lo:+g}..{hi:+g} dB in the hooks)",
                               fix, {'trim': {m: _r1(-sign * worst) for m in members}}, members, [b.name for b, _ in lst]))
    # the lead not in front: every bounded group too loud at once (or a part above the lead)
    buried = [b for b in judged if len([g for g in GROUPS if g in b.rel]) >= 2 and
              all(_err(b.rel[g], _bounds(prof, g, b.hook)) > 0 for g in GROUPS if g in b.rel)]
    if buried:
        c = statistics.median(min(_err(b.rel[g], _bounds(prof, g, b.hook)) for g in GROUPS if g in b.rel) for b in buried)
        leads = sorted({b.lead for b in buried})
        out.insert(0, Finding('lead_not_in_front', 'warn', f"the lead ({', '.join(leads)}) is not in front in "
                              f"{', '.join(b.name for b in buried)}: every group sits above its window (by >= "
                              f"{c:.1f} dB, median)", 'raise the lead (headroom: its peak) or pull the band down; carve '
                              'the bed with a duck keyed by the lead', {'trim': {L: _r1(c) for L in leads}}, leads,
                              [b.name for b in buried]))
    for b in judged:
        for k, v in b.rel.items():
            if k not in GROUPS and v > prof.window('other', b.hook)[1] + 0.75:
                out.append(Finding('part_over_lead', 'warn' if v > 0 else 'info',
                                   f"'{k}' ({rl.get(k)}) sits {v:+.1f} dB vs the lead {b.lead} in {b.name} (limit "
                                   f"{prof.other_max:+g})", f"trim '{k}' or give it a dip where the lead lives",
                                   {'trim': {k: _r1(prof.other_max - v)}}, [k], [b.name]))
    # the report's own findings, as the mix engineer reads them
    lead_ids = {b.lead for b in judged}
    for w in rep.get('warnings', []):
        code, msg, nodes = w.get('code'), w.get('message', ''), w.get('nodes') or []
        if code == 'masking' and len(nodes) == 2:
            m = re.search(r'of the (\w+) band', msg)
            band = m.group(1) if m else ''
            if band in ('sub', 'bass'):
                if 'alternate' in msg:
                    continue
                a, c = nodes
                bass = c if rl.get(c) == 'low' else a
                kit = a if bass == c else c
                out.append(Finding('low_end_fight', 'warn', msg, f"duck '{bass}' under the kick ({prof.kick_bass_duck_db or 6:g}"
                                   f" dB, attack 2 ms, release ~120 ms) or eq: the kick owns 50-60 Hz, the bass 80-120 Hz",
                                   {'duck': [{'targets': [bass], 'key': kit, 'pitches': 'kick',
                                              'depth': prof.kick_bass_duck_db or 6.0, 'attack': 2.0, 'release': 120.0}]},
                                   nodes, w.get('sections') or []))
            elif band in ('lowmid', 'mid', 'presence'):
                other_n = next((n for n in nodes if n not in lead_ids), nodes[1])
                out.append(Finding('masking', 'warn' if set(nodes) & lead_ids else 'info', msg,
                                   f"a {abs(prof.dip_db):g} dB dip on '{other_n}' at {_BAND_HZ[band]:g} Hz (the band the "
                                   f"{'lead' if set(nodes) & lead_ids else 'other part'} lives in), or move it an octave",
                                   {'eq': {other_n: [{'freq': _BAND_HZ[band], 'gain': prof.dip_db, 'q': 1.0}]}},
                                   nodes, w.get('sections') or []))
        elif code == 'flat_dynamics':
            out.append(Finding('flat_dynamics', w.get('severity', 'warn'), msg.split(' - ')[0],
                               'velocity arcs over each phrase (55-118), a velocity-sensitive sound, a gentler track '
                               'compressor (the composer / player fixes this, not the fader)', None, nodes,
                               w.get('sections') or []))
        elif code in ('node_hot',):
            out.append(Finding('headroom', 'info', msg, 'trim the node (its peak before the master)',
                               None, nodes))
        elif code in ('clicks',) and w.get('severity') == 'warn':
            out.append(Finding('clicks', 'warn', msg, 'see report.clicks and clicks/click_NN.png', None, nodes))
    # tone: mud 200-400 Hz, harshness 2-5 kHz (vs the profile's reference balance)
    mud = _third(rep, 200, 400)
    if mud is not None and mud > 2.5:
        tops = _top(rep, 'lowmid', exclude=lead_ids)
        out.append(Finding('mud', 'warn' if mud > 4 else 'info', f"200-400 Hz {mud:+.1f} dB over the {prof.name} "
                           f"reference (boxy / muddy)" + (f"; most of the low mids: {', '.join(f'{n} {p:.0f} %' for n, p in tops)}"
                                                         if tops else ''),
                           'dip the biggest low-mid contributors (not the lead) 2-3 dB at ~300 Hz (q 1), high-pass pads / '
                           'keys at 120-200 Hz', {'eq': {n: [{'freq': 300.0, 'gain': -2.5, 'q': 1.0}] for n, _ in tops}}
                           if tops else None, [n for n, _ in tops]))
    harsh = _third(rep, 2000, 5000)
    if harsh is not None and harsh > 2.5:
        tops = _top(rep, 'presence')
        out.append(Finding('harsh', 'warn' if harsh > 4 else 'info', f"2-5 kHz {harsh:+.1f} dB over the {prof.name} "
                           f"reference (harsh / glassy)" + (f"; most of the presence: {', '.join(f'{n} {p:.0f} %' for n, p in tops)}"
                                                           if tops else ''),
                           'a 2-3 dB dip at ~3.3 kHz on the biggest contributors (on the lead a presence dip lets its '
                           'fader come up: louder, not harsher); air above 10 kHz instead of presence',
                           {'eq': {n: [{'freq': 3300.0, 'gain': -2.0, 'q': 1.0}] for n, _ in tops}} if tops else None,
                           [n for n, _ in tops]))
    # width and space
    space = rep.get('space') or {}
    for issue in space.get('issues') or []:
        code = issue if isinstance(issue, str) else issue.get('code', str(issue))
        if code in ('narrow', 'over_wide', 'phasey'):
            ops = ', '.join(f"{o.get('id')} ({o.get('widener', '?')})" for o in space.get('opportunities', [])[:3])
            out.append(Finding(f"width_{code}", 'warn', f"space: {code} (width above 150 Hz "
                               f"{space.get('widthAbove150HzPct', '?')} %, correlation {space.get('correlationAbove150Hz', '?')})",
                               ('widen the music parts: ' + ops) if code == 'narrow' and ops else
                               'back off the wideners (chorus mix, width > 1.2) on the parts that go anti-phase'))
    lowc = [s['name'] for s in rep.get('sections', []) if s.get('lowEndCorrelation', 1.0) < 0.8 and s.get('lufs', -120) > view.loudest - 12]
    if lowc:
        out.append(Finding('low_end_wide', 'warn', f"the low end is not mono in {', '.join(lowc)} (correlation < 0.8 "
                           f"below 150 Hz)", 'mono the lows: the master width with monobass, or eq width off the bass '
                           '/ kick layers; no chorus on the bass', None, [], lowc))
    g = rep.get('global') or {}
    tgt = (rep.get('reference') or {}).get('lufsTarget')
    if tgt and g.get('lufsIntegrated') is not None and not tgt[0] - 0.5 <= g['lufsIntegrated'] <= tgt[1] + 0.5:
        out.append(Finding('loudness', 'info', f"{g['lufsIntegrated']:.1f} LUFS vs the {prof.name} target "
                           f"{tgt[0]:g}..{tgt[1]:g} (the mastering stage: limiter drive)", 'master.gain / limiter gain; '
                           'the mix balance does not depend on it'))
    order = {'warn': 0, 'info': 1}
    return sorted(out, key=lambda f: (order.get(f.severity, 2), f.code != 'lead_not_in_front'))


# ------------------------------------------------------------------------------------------------ auto

@dataclass
class Pass:
    index: int
    report: str
    balances: list
    moves: list
    mix: dict


@dataclass
class AutoResult:
    """What auto() did: the final MIX, the log, the balance before / after each pass, the renders."""
    mix: dict
    passes: list
    profile: MixProfile
    log: list = field(default_factory=list)
    out: Path | None = None

    @property
    def before(self) -> list:
        return self.passes[0].balances if self.passes else []

    @property
    def after(self) -> list:
        return self.passes[-1].balances if self.passes else []

    def table(self) -> str:
        """Per judged section: the groups vs the lead, first pass -> last pass."""
        a = {b.name: b for b in self.before}
        z = {b.name: b for b in self.after}
        lines = [f"{'section':<12} {'lead':<12} " + ' '.join(f"{g:>15}" for g in GROUPS) + '   top other']
        for name, b0 in a.items():
            b1 = z.get(name)
            if not b0.judged and not (b1 and b1.judged):
                continue
            cells = []
            for g in GROUPS:
                x0, x1 = b0.rel.get(g), (b1.rel.get(g) if b1 else None)
                cells.append(f"{_f(x0):>6} -> {_f(x1):<6}" if x0 is not None or x1 is not None else f"{'-':>15}")
            o0 = [(k, v) for k, v in b0.rel.items() if k not in GROUPS]
            top = ''
            if o0:
                k, v = max(o0, key=lambda kv: kv[1])
                top = f"{k} {v:+.1f} -> {_f(b1.rel.get(k) if b1 else None)}"
            lines.append(f"{name:<12} {str(b0.lead or (b1.lead if b1 else '-')):<12} " + ' '.join(cells) + '   ' + top)
        return '\n'.join(lines)

    def describe(self) -> str:
        lines = [f"auto mix ({self.profile.name}): {len(self.passes)} render{'s' * (len(self.passes) != 1)}, "
                 f"MIX = {describe_mix(self.mix)}"]
        lines += ['  ' + x for x in self.log]
        lines.append('  balance vs the lead (first -> last render):')
        lines += ['    ' + x for x in self.table().splitlines()]
        return '\n'.join(lines)

    def code(self) -> str:
        return to_code(self.mix, self.log)


def _f(x) -> str:
    return '-' if x is None else f"{x:+.1f}"


def _song_source(song):
    """(loader returning (Song, ANALYSIS, module MIX), song dir) for a song path / dir, or a Song object."""
    from .song import Song
    if isinstance(song, Song):
        snap = copy.deepcopy(song)
        return (lambda: (copy.deepcopy(snap), None, None)), None
    from . import cli
    song_py = cli.resolve_song(str(song))

    def load():
        s, analysis = cli._load_song(song_py)
        return s, analysis, getattr(s, 'module_mix', None)
    return load, song_py.parent


def render(song, mix=None, *, out, profile=None, from_beat=None, to_beat=None, engine=None) -> Path:
    """Render a song (path / dir / Song) with a MIX applied into `out`; returns the report.json path."""
    from . import cli
    load, _ = _song_source(song)
    s, analysis, _mod_mix = load()
    if getattr(s, 'applied_mix', None) is not None:
        raise ComposeError("the song's build() applies a MIX itself (s.mix(...)); mixer.auto manages the MIX: move it to "
                           "a module-level MIX = {...} (the CLI applies it at build time)")
    apply(s, mix or {})
    rj = cli.compile_song(s)
    cli.apply_analysis(rj, analysis, profile)
    out = Path(out)
    path = cli.write_render(rj, out / 'song.render.json')
    cli.run_engine(cli.find_engine(engine), path, out, from_beat, to_beat, rj)
    return out / 'report.json'


def auto(song, report=None, *, profile=None, iterations: int = 2, start=None, out=None, sections=None,
         span=None, lead=None, bed=None, rhythm=None, low=None, other=None, roles=None, hooks=None, engine=None,
         max_step: float = MAX_STEP, renderer=None, verbose: bool = False) -> AutoResult:
    """Render -> read the report -> move faders / rides / sidechains / dips toward the genre targets, `iterations`
    times, then render once more to verify. Every move is bounded (max_step dB per pass), logged and ends up in the
    returned MIX (paste it into song.py; nothing is written into the song file).

    song: songs/<slug>, a song.py, or a Song object. report: the current render's report (skips the first render;
    it must match `start`). start: the MIX to start from (default: the song file's module-level MIX). out: where
    the passes render (default <song dir>/out/mixer, or a temp folder for a Song object). sections / span: render
    only these sections / (from_beat, to_beat) - a preview; the targets are judged on what it contains.
    renderer(song, mix, out, pass_index) -> report: replaces the engine (tests)."""
    import tempfile
    load, sdir = _song_source(song)
    s0, analysis, mod_mix = load()
    mix = normalize(start if start is not None else (mod_mix or {}))
    base_out = Path(out) if out is not None else (sdir / 'out' / 'mixer' if sdir is not None else
                                                  Path(tempfile.mkdtemp(prefix='agentsound-mixer-')))
    fb, tb = (span or (None, None))
    if sections:
        secs = [s0[n] for n in _ids(sections)]
        fb, tb = min(x.start for x in secs), max(x.end for x in secs)
    pname = profile or (analysis or {}).get('profile')
    passes: list[Pass] = []
    log: list[str] = []
    prof = None

    def do_render(i: int, m: dict):
        if renderer is not None:
            return renderer(song, m, base_out / f"pass_{i}", i)
        return render(song, m, out=base_out / f"pass_{i}", profile=pname, from_beat=fb, to_beat=tb, engine=engine)

    rep_src = report
    for i in range(iterations + 1):
        if i > 0 or rep_src is None:
            rep_src = do_render(i, mix)
        rep = load_report(rep_src)
        pl = plan(s0, rep, profile=pname, lead=lead, bed=bed, rhythm=rhythm, low=low, other=other, roles=roles,
                  hooks=hooks, base=mix, max_step=max_step)
        prof = pl.profile
        passes.append(Pass(i, str(rep_src) if not isinstance(rep_src, dict) else '<dict>', pl.balances, pl.moves, mix))
        if i == iterations:
            if pl.moves:
                log.append(f"after pass {i}: {len(pl.moves)} move(s) would still help (not applied): "
                           + '; '.join(str(m) for m in pl.moves[:6]))
            else:
                log.append(f"after pass {i}: inside the targets")
            break
        if not pl.moves:
            log.append(f"pass {i + 1}: inside the targets - nothing to move")
            break
        for m in pl.moves:
            log.append(f"pass {i + 1}: {m}")
        mix = merge(mix, pl.moves)
        if verbose:
            print('\n'.join(log[-len(pl.moves):]))
    lufs = [((load_report(x.report) if x.report != '<dict>' else {}).get('global') or {}).get('lufsIntegrated')
            for x in (passes[0], passes[-1])] if len(passes) > 1 else [None, None]
    if None not in lufs and abs(lufs[1] - lufs[0]) >= 0.3:
        log.append(f"the mix moved the master's input: {lufs[0]:.1f} -> {lufs[1]:.1f} LUFS integrated - the mastering "
                   f"stage re-sets the limiter drive ({lufs[0] - lufs[1]:+.1f} dB) if the loudness target needs it")
    mix['profile'] = prof.name if prof else (pname or 'default')
    res = AutoResult(mix, passes, prof or get_profile(pname), log, base_out)
    try:
        base_out.mkdir(parents=True, exist_ok=True)
        (base_out / 'MIX.py').write_text(res.code(), encoding='utf-8')
        (base_out / 'log.txt').write_text(res.describe() + '\n', encoding='utf-8')
    except OSError:
        pass
    return res
