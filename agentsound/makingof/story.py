"""The making-of's words: narration lines and the default story built from the song's facts (facts.py) - the
material the draft film.py (draft.py) is written from - plus the helpers every film uses (speakable numbers and
note names, move labels, excerpt picking, the team cards).

Every line is a caption on screen and, with a TTS backend, the narration. Lines only restate what the song's files
say (the wish, the log, the form, the measured numbers, the A&R verdict); the wording around the numbers is fixed
English templates."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .docs import clip, first_sentence, strip_md
from .facts import ROLE_TITLES, fmt_time

CHAPTERS = [  # (id, title) in film order
    ('cold', 'The wish'),
    ('team', 'The team'),
    ('blueprint', 'The blueprint'),
    ('tracks', 'Meet the tracks'),
    ('performance', 'The performance'),
    ('crisis', 'The verdict'),
    ('song', 'The song'),
    ('end', 'Credits'),
]
CHAPTER_IDS = [c for c, _ in CHAPTERS]

VOICES = ('narrator', 'ar')
DIRECTIONS = {
    'cold': 'Warm, intrigued, unhurried.',
    'team': 'Warm and lively, a little proud.',
    'blueprint': 'Clear, curious and measured.',
    'tracks': 'Close, attentive and precise.',
    'performance': 'Lively and observant.',
    'crisis': 'Low, serious, a little tense.',
    'crisis-ar': 'Firm, clipped and uncompromising.',
    'crisis-fix': 'Determined, then quietly relieved.',
    'song': 'Hushed anticipation, uplifting.',
    'end': 'Warm and grateful.',
}
MAX_LINE = 260          # characters per narrated chunk (Breeze: one to three sentences, <= ~260)


@dataclass
class Line:
    text: str
    voice: str = 'narrator'
    direction: str = ''
    pause_ms: int = 360

    def md(self) -> str:
        d = f" | {self.direction}" if self.direction else ''
        return f"- [{self.voice}{d}] {self.text}"


@dataclass
class Excerpt:
    start: float
    end: float
    label: str = ''
    lines: list = field(default_factory=list)


@dataclass
class TrackItem:
    name: str
    ids: list
    at: float                     # song time where its solo starts
    lines: list = field(default_factory=list)


@dataclass
class Chapter:
    id: str
    title: str
    lines: list = field(default_factory=list)
    excerpts: list = field(default_factory=list)      # performance only
    items: list = field(default_factory=list)         # tracks only: TrackItem
    episodes: list = field(default_factory=list)      # tried only: film.Episode
    kind: str = ''                                    # the component that renders it (default: the id)
    opts: dict = field(default_factory=dict)          # the component's options

    def __post_init__(self):
        self.kind = self.kind or self.id


# ------------------------------------------------------------------------------------------------ helpers

def _num(x: float, nd: int = 1) -> str:
    s = f"{x:.{nd}f}"
    return s.rstrip('0').rstrip('.') if '.' in s else s


def _join(words: list[str]) -> str:
    words = [w for w in words if w]
    if len(words) <= 1:
        return ''.join(words)
    return ', '.join(words[:-1]) + ' and ' + words[-1]


def pretty(name: str) -> str:
    """A section id the way it is said: 'chorus3' -> 'chorus 3', 'pre_2' -> 'pre 2'."""
    return re.sub(r'(?<=[a-z])(?=\d)', ' ', name.replace('_', ' '))


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _low(s: str) -> str:
    return s[:1].lower() + s[1:] if s[:2] != s[:2].upper() else s


def _minutes(sec: float) -> str:
    m, s = int(sec // 60), int(round(sec % 60))
    if s == 60:
        m, s = m + 1, 0
    return f"{m}:{s:02d}"


MOVE_WORDS = {
    ('pianist', 'ornament'): {'trill': 'a trill', 'turn': 'a turn', 'mordent': 'a mordent', 'roll': 'a rolled chord',
                              'restrike': 'a restrike', 'crush': 'a grace note'},
    ('pianist', 'fill'): {'run': 'a run', 'gliss': 'a glissando', 'answer': 'an answering fill',
                          'arpeggio': 'an arpeggio', 'stabs': 'chord stabs', 'pentatonic': 'a pentatonic fill',
                          'fourths': 'a fill in fourths'},
    ('drummer', 'crash'): {'crash': 'a crash', 'ride_crash': 'a ride crash'},
    ('drummer', 'fill'): {'toms': 'a tom fill', 'snare': 'a snare fill', 'triplets': 'a triplet fill',
                          'flams': 'a flam fill', 'pickup': 'a pickup', 'linear': 'a linear fill'},
    ('drummer', 'build'): {'build': 'a build'},
    ('drummer', 'stop'): {'break': 'a stop', 'bar': 'a stop bar'},
    ('drummer', 'ending'): {'hit': 'the final hit', 'roll': 'a closing roll'},
    ('bassist', 'fill'): {'run_down': 'a run down', 'run_up': 'a run up', 'octave': 'an octave fill',
                          'triplet': 'a triplet fill'},
    ('bassist', 'move'): {'slide': 'a slide', 'hammer_on': 'a hammer-on', 'octave_pop': 'an octave pop',
                          'pull_off': 'a pull-off'},
    ('guitarist', 'move'): {'bend': 'a bend', 'slide': 'a slide', 'hammer_on': 'a hammer-on', 'pull_off': 'a pull-off',
                            'rake': 'a rake', 'double_stop': 'a double stop'},
    ('guitarist', 'ornament'): {'slide_chord': 'slid chords', 'choke': 'a choke', 'grace': 'a grace note',
                                'trill': 'a trill', 'harmonic': 'a harmonic'},
    ('guitarist', 'technique'): {'chug': 'palm-muted chugs'},
    ('hornist', 'air'): {'push': 'an air push', 'swell': 'a swell', 'bloom': 'a bloom', 'accents': 'accents',
                         'taper': 'a taper', 'breath_release': 'a breath release'},
    ('hornist', 'pitch'): {'scoop': 'a scoop', 'vibrato': 'vibrato', 'shake': 'a shake', 'fall': 'a fall',
                           'bend': 'a bend'},
    ('hornist', 'mic'): {'lean_in': 'a lean into the mic'},
}


def move_label(m: dict) -> str:
    """Short on-screen label of a move ('trill', 'tom fill', 'bend')."""
    w = MOVE_WORDS.get((m['player'], m['kind']), {}).get(m['name'])
    if w:
        return re.sub(r'^(a|an|the)\s+', '', w)
    return m['name'].replace('_', ' ')


def move_phrase(m: dict) -> str:
    return MOVE_WORDS.get((m['player'], m['kind']), {}).get(m['name']) or m['name'].replace('_', ' ')


def speakable(text: str) -> str:
    """The narration text for a voice: numbers, units and note names the way they are said."""
    t = text
    t = t.replace('A&R', 'A and R').replace('->', 'to').replace('→', 'to').replace('…', '...')
    t = re.sub(r'(\d)\.\.(-?\d)', r'\1 to \2', t)
    t = re.sub(r'(?<![\w.])-(\d)', r'minus \1', t)
    t = re.sub(r'\+(\d)', r'plus \1', t)
    t = re.sub(r'(\d)\s*%', r'\1 percent', t)
    t = re.sub(r'(\d)\s*dBTP\b', r'\1 dB true peak', t)
    t = re.sub(r'(\d)\s*kHz\b', r'\1 kilohertz', t)
    t = re.sub(r'(\d)\s*Hz\b', r'\1 hertz', t)
    t = re.sub(r'(\d)\s*ms\b', r'\1 milliseconds', t)
    t = re.sub(r'\bdB\b', 'decibels', t)
    t = re.sub(r'\bLUFS\b', 'LUFS', t)
    t = re.sub(r'(\d)\s*LU\b', r'\1 L U', t)
    t = re.sub(r'\bBPM\b', 'beats per minute', t)
    t = re.sub(r'\b(\d+)/4\b', lambda m: {'3': 'three-four', '4': 'four-four', '2': 'two-four',
                                          '6': 'six-four'}.get(m.group(1), m.group(0)), t)
    t = re.sub(r'\b(\d+):(\d\d)\b', lambda m: f"{int(m.group(1))} minutes {int(m.group(2))}", t)

    def note(m):
        n = m.group(1) + {'b': ' flat', '#': ' sharp', '': ''}[m.group(2)]
        return n
    t = re.sub(r'\b([A-G])(b|#|)\d\b', note, t)
    t = re.sub(r'\b([A-G])b\b', r'\1 flat', t)
    t = re.sub(r'\b([A-G])#', r'\1 sharp', t)
    return re.sub(r'\s+', ' ', t).strip()


# ------------------------------------------------------------------------------------------------ excerpts

def pick_excerpts(facts: dict, n: int = 3, length: float = 11.0) -> list[Excerpt]:
    """n windows (length s, on bar lines) with the most player moves on screen: distinct players count double, a
    hook statement helps, windows in different sections, spread over the song -> in song order."""
    pops = [m for m in facts['moves'] if m['pop']]
    bars = facts.get('barTimes') or []
    hooks = facts['hook']['occurrences']
    dur = facts['duration']
    cands = []
    for b in bars:
        if b + length > dur - 2:
            break
        ms = [m for m in pops if b + 0.3 <= m['t'] < b + length - 1.0]
        if not ms:
            continue
        players = {m['player'] for m in ms}
        kinds = {(m['player'], m['kind'], m['name']) for m in ms}
        score = 3 * len(players) + min(len(kinds), 8) + (2 if any(b <= h['t'] < b + length - 2 for h in hooks) else 0)
        sec = next((s for s in facts['sections'] if s['start'] <= b + length / 2 < s['end']), None)
        score += 2 * (sec['level'] if sec else 0)
        cands.append((score, b, sec['name'] if sec else ''))
    cands.sort(key=lambda c: -c[0])
    chosen = []
    for score, b, sname in cands:
        if any(abs(b - c[1]) < length + 20 for c in chosen) or any(sname == c[2] for c in chosen):
            continue
        chosen.append((score, b, sname))
        if len(chosen) == n:
            break
    chosen.sort(key=lambda c: c[1])
    return [Excerpt(round(b, 3), round(b + length, 3), sname) for _, b, sname in chosen]


def excerpt_line(facts: dict, ex: Excerpt) -> str:
    """'The solo, 3:52: the guitarist plays a bend and a slide; the drummer a crash.' from the moves inside."""
    ms = [m for m in facts['moves'] if m['pop'] and ex.start <= m['t'] < ex.end]
    by: dict[str, list] = {}
    for m in ms:
        ph = move_phrase(m)
        lst = by.setdefault(m['player'], [])
        if ph not in lst:
            lst.append(ph)
    parts = []
    for pl in facts['players']:
        if pl in by:
            parts.append(f"the {ROLE_TITLES.get(pl, pl).lower()} plays {_join(by[pl][:3])}")
    head = f"{_cap(pretty(ex.label))}, at {_minutes(ex.start)}" if ex.label else f"At {_minutes(ex.start)}"
    if not parts:
        return head + '.'
    s = f"{head}: {parts[0]}" + ''.join(f"; {p}" for p in parts[1:3]) + '.'
    return s


# ------------------------------------------------------------------------------------------------ the script

def _role_line(facts: dict, role: str) -> str:
    """What a role did in this song: the first of its log entries (not the revision), first sentence."""
    for e in facts['log']:
        if role in e['who'] and not e['revision']:
            txt = re.sub(r'^[A-Z]+\.md(\s*\+\s*[\w.]+)?\s*-\s*', '', e['text'])
            return first_sentence(txt, 120)
    return ''


def team_cards(facts: dict) -> list[dict]:
    """The cast: the six roles + the players who played (from the players' logs), each with one line from the
    song's own files."""
    cards = []
    order = ['producer', 'arranger'] + facts['players'] + ['sound-designer', 'mix-engineer', 'mastering-engineer',
                                                             'a-and-r']
    from .capture import counts
    mv_counts = counts([{'player': m['player'], 'kind': m['kind'], 'name': m['name']} for m in facts['moves']])
    for r in order:
        line = _role_line(facts, r)
        if r in facts['players']:
            c = mv_counts.get(r, {})
            top = [(k, v) for k, v in c.items() if k.split(':')[0] not in ('groove', 'device', 'shape', 'pattern',
                                                                            'anticipation', 'dropped', 'space')][:3]
            words = [f"{v} × {move_label({'player': r, 'kind': k.split(':')[0], 'name': k.split(':', 1)[1]})}"
                     for k, v in top]
            tracks = sorted({m['track'] for m in facts['moves'] if m['player'] == r})
            line = f"played {', '.join(tracks)}" + (f": {', '.join(words)}" if words else '')
        if r == 'a-and-r' and facts['verdict']:
            line = f"verdict: {facts['verdict']}" + (f", {len(facts['issues'])} ranked issues" if facts['issues']
                                                      else '')
        if not line:
            continue
        cards.append({'role': r, 'title': ROLE_TITLES.get(r, r), 'line': clip(line, 120)})
    return cards


def hero_names(facts: dict) -> list[str]:
    """The hero sounds named in SOUND.md's parts table ('sampled/hero_piano' -> 'hero piano')."""
    heroes = []
    for r in facts['soundRows']:
        for m in re.finditer(r'\b(?:hero|layered|sampled)/(\w+)', r.get('sound', '')):
            if 'hero' not in m.group(0):
                continue
            nm = m.group(1).replace('_', ' ')
            if nm not in heroes:
                heroes.append(nm)
    return heroes


def build(facts: dict, n_excerpts: int = 3) -> list[Chapter]:
    """The default script of a song."""
    D = DIRECTIONS
    title = facts['title']
    secs = facts['sections']
    parts = [p for p in facts['parts'] if p['name']]
    chs = {cid: Chapter(cid, t) for cid, t in CHAPTERS}

    # 1 cold open
    c = chs['cold']
    c.lines.append(Line("It started with a wish, typed into a chat.", 'narrator', D['cold']))
    summ = facts['wish'].get('summary') or ''
    if ': ' in summ and summ.index(': ') > 40:
        summ = summ[:summ.index(': ')]
    summ = re.sub(r'\b[A-Z]{4,}\b', lambda m: m.group(0).lower(), summ).rstrip('.…')
    if summ:
        c.lines.append(Line(f"The brief made it this: {clip(_low(summ), 200)}.", 'narrator', D['cold']))
    genre = facts['genre'].lower() if facts['genre'] else 'an instrumental'
    c.lines.append(Line(f"This is how {title} was made: {genre}, {_minutes(facts['duration'])} long.", 'narrator',
                        D['cold'], 650))

    # 2 the team
    c = chs['team']
    cards = team_cards(facts)
    roles = [x for x in cards if x['role'] not in facts['players']]
    pls = [ROLE_TITLES[p].lower() for p in facts['players']]
    c.lines.append(Line(f"{len(roles)} roles and {len(pls)} players made it, one after the other.", 'narrator',
                        D['team']))
    c.lines.append(Line(f"The producer wrote the brief, the arranger the form, and the {_join(pls)} performed the "
                        f"parts: every move they made is in their logs.", 'narrator', D['team']))
    c.lines.append(Line("Then came sound design, the mix, the master, and the critic: the A&R.", 'narrator',
                        D['team'], 650))

    # 3 the blueprint
    c = chs['blueprint']
    nparts = f" in {len(parts)} parts" if len(parts) > 1 else ''
    c.lines.append(Line(f"The blueprint: {len(secs)} sections{nparts}, {int(round(facts['bars'] or 0))} bars.",
                        'narrator', D['blueprint']))
    keys = []
    for s in secs:
        if s['key'] and (not keys or keys[-1] != s['key']):
            keys.append(s['key'])
    bpms = [s['bpm'] for s in secs if s.get('bpm')] or [x for x in (facts.get('bpmRange') or []) if x]
    if not keys and facts.get('key'):
        keys = [facts['key']]
    if bpms:
        lo, hi = min(bpms), max(bpms)
        tempo = f"the tempo moves between {lo:.0f} and {hi:.0f} BPM" if hi - lo > 3 else f"{hi:.0f} BPM"
        meters = f" in {' and '.join(facts['meters'])} time" if len(facts['meters']) > 1 else ''
        keyp = f", through {_join(keys)}" if len(keys) > 1 else (f", in {keys[0]}" if keys else '')
        c.lines.append(Line(f"Section by section {tempo}{meters}{keyp}.", 'narrator', D['blueprint']))
    h = facts['hook']
    if h['motif']:
        k = len(h['occurrences'])
        c.lines.append(Line(f"The hook: {', '.join(h['names'])}. It returns {k} times, handed from part to part.",
                            'narrator', D['blueprint']))
    if secs:
        quiet = min(secs, key=lambda s: s['lufs'] if s['lufs'] is not None else 0)
        loud = max(secs, key=lambda s: s['lufs'] if s['lufs'] is not None else -99)
        c.lines.append(Line(f"The energy climbs from {quiet['lufs']:.1f} LUFS in the {pretty(quiet['name'])} to "
                            f"{loud['lufs']:.1f} in the {pretty(loud['name'])}.", 'narrator', D['blueprint'], 650))

    # 4 sound design
    c = chs['tracks']
    rows = facts['soundRows']
    heroes = hero_names(facts)
    c.lines.append(Line(f"Sound design: {len(rows) or 'every'} parts, each with its own sound and space.", 'narrator',
                        D['tracks']))
    if heroes:
        c.lines.append(Line(f"The hooks ride on hero sounds: {_join(heroes[:4])}.", 'narrator', D['tracks']))
    ranked = sorted(facts['soundMeasured'], key=lambda x: 0 if re.search(r'\bwon\b|\bchosen\b|\bchose\b', x) else
                    1 if x.startswith('Result') else 2)
    if ranked:
        c.lines.append(Line(f"Measured, not guessed. {clip(_clean_sentence(ranked[0]), 200)}",
                            'narrator', D['tracks'], 650))
    for it in facts.get('items', []):
        c.items.append(TrackItem(it['name'], list(it['ids']), it['at']))

    # 5 the performance
    c = chs['performance']
    c.lines.append(Line("The players, caught in the act: every label is a move from their logs, on the frame it was "
                        "played.", 'narrator', D['performance']))
    for ex in pick_excerpts(facts, n_excerpts):
        ex.lines.append(Line(excerpt_line(facts, ex), 'narrator', D['performance'], 240))
        c.excerpts.append(ex)

    # 6 the crisis
    c = chs['crisis']
    iss = facts['issues']
    if facts['verdict']:
        c.lines.append(Line(f"Verdict: {facts['verdict']}.", 'ar', D['crisis-ar'], 650))
        if iss:
            sev: dict[str, int] = {}
            for i in iss:
                sev[i['severity']] = sev.get(i['severity'], 0) + 1
            count = _join([f"{v} {k}{'s' if v > 1 else ''}" for k, v in sev.items() if k])
            c.lines.append(Line(f"{count}. First: {clip(_low(iss[0]['title'].rstrip('.')), 150)}.", 'ar', D['crisis-ar']))
        if iss:
            c.lines.append(Line("Every issue went back to the role that owns its cause.", 'narrator', D['crisis']))
        for r in facts['revision'][:3]:
            good = [p for p in r['pairs'] if len(p['label']) <= 45 and ' / ' not in p['label']
                    and '(' not in p['label'] and p['label'][:1].isalpha()]
            key = [p for p in good if p.get('key')] or good
            head = re.sub(r'^\[\w+\]\s*', '', r['head'])
            head = re.sub(r'\s*->.*$', '', head)
            head = re.sub(r'\s*\(.*?\)\s*$', '', head)
            if key:
                p = key[0]
                u = f" {p['unit']}" if p['unit'] else ''
                c.lines.append(Line(f"{head}: {_low(p['label'])}, {_num(p['before'])} to {_num(p['after'])}{u}.",
                                    'narrator', D['crisis-fix']))
        if facts['proposal']:
            c.lines.append(Line(f"After the revision, the verdict proposal: {facts['proposal']}.", 'narrator',
                                D['crisis-fix'], 650))
    else:
        c.lines.append(Line("No A&R verdict is on file for this song.", 'narrator', D['crisis'], 650))

    # 7 the song, 8 credits
    chs['song'].lines.append(Line(f"And now, {title}.", 'narrator', D['song'], 900))
    chs['end'].lines.append(Line(f"{title}. Made with AgentSound.", 'narrator', D['end'], 900))
    return [chs[cid] for cid in CHAPTER_IDS]


def _clean_sentence(s: str) -> str:
    s = strip_md(s).strip()
    s = re.sub(r'^-\s*', '', s)
    s = s[0].upper() + s[1:] if s else s
    return s if s.endswith(('.', '!', '?')) else s + '.'


# ------------------------------------------------------------------------------------------------ times

def _ts(sec: float) -> str:
    """M:SS.ss (the making-of.md review copy, the draft's comments)."""
    return f"{int(sec // 60)}:{sec % 60:05.2f}"
