"""Everything the making-of knows about a song, gathered from its own files: the render JSON (notes, tracks,
sections, tempo map, meter), report.json (loudness per section / bar, per-track levels, dynamics), the role files
(BRIEF / ARRANGEMENT / SOUND / MIX / MASTER / AR), credits.txt, cover.png and the players' logs (capture.py).
Nothing here is invented: every text and number the film shows comes from one of these."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from . import docs
from ..tempo import TempoMap

# --------------------------------------------------------------------------------------------- track families

FAMILIES = [  # (family, colour, id keywords) - first match wins
    ('drums', '#ff5f7e', ('kit', 'drum', 'hats', 'hat', 'snare', 'kick', 'cym', 'clap', 'tom')),
    ('fx', '#9aa3b5', ('riser', 'impact', 'down', 'sweep', 'fx', 'noise', 'whoosh')),
    ('bass', '#48f0a0', ('bass',)),
    ('piano', '#8fd8ff', ('piano', 'keys', 'rhodes', 'epiano', 'lead')),
    ('organ', '#7ea8ff', ('organ',)),
    ('guitar', '#ffa24a', ('gtr', 'guitar')),
    ('strings', '#c89bff', ('violin', 'viola', 'cello', 'string', 'harp')),
    ('winds', '#9ff0c8', ('flute', 'oboe', 'clarinet', 'bassoon', 'wind')),
    ('brass', '#ffd166', ('horn', 'trumpet', 'trombone', 'tuba', 'brass', 'sax')),
    ('timpani', '#ff8a5c', ('timpani', 'taiko', 'percussion', 'gong')),
    ('choir', '#6ff0e0', ('choir', 'voice', 'vox', 'chorus')),
    ('synth', '#ff6ad5', ('pad', 'arp', 'synth', 'glass', 'pluck', 'saw', 'shimmer', 'bell')),
]


def family(track_id: str) -> tuple[str, str]:
    t = track_id.lower()
    special = {'basses': ('strings', '#b48cff'), 'bassoons': ('winds', '#9ff0c8'), 'bassoon': ('winds', '#9ff0c8'),
               'contrabass': ('strings', '#b48cff')}
    if t in special:
        return special[t]
    for fam, col, words in FAMILIES:
        if any(w in t for w in words):
            return fam, col
    return 'other', '#c7cbd6'


PLAYER_COLORS = {'pianist': '#8fd8ff', 'drummer': '#ff5f7e', 'bassist': '#48f0a0', 'guitarist': '#ffa24a',
                 'hornist': '#ffd166'}

ROLE_COLORS = {'producer': '#f5c451', 'arranger': '#b69cff', 'sound-designer': '#3fe0f0', 'mix-engineer': '#ff6ad5',
               'mastering-engineer': '#9fc3ff', 'a-and-r': '#ff4d6a', **PLAYER_COLORS}

ROLE_TITLES = {'producer': 'Producer', 'arranger': 'Arranger', 'sound-designer': 'Sound designer',
               'mix-engineer': 'Mix engineer', 'mastering-engineer': 'Mastering engineer', 'a-and-r': 'A&R',
               'pianist': 'Pianist', 'drummer': 'Drummer', 'bassist': 'Bassist', 'guitarist': 'Guitarist',
               'hornist': 'Wind player'}

NOTE_NAMES = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


def note_name(p: int) -> str:
    return f"{NOTE_NAMES[p % 12]}{p // 12 - 1}"


def midi(name: str) -> int | None:
    m = re.fullmatch(r'([A-Ga-g])([#b]?)(-?\d)', name.strip())
    if not m:
        return None
    base = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}[m.group(1).upper()]
    return base + {'#': 1, 'b': -1, '': 0}[m.group(2)] + 12 * (int(m.group(3)) + 1)


# --------------------------------------------------------------------------------------------- helpers

def _load(p: Path):
    return json.loads(p.read_text(encoding='utf-8')) if p.is_file() else None


def fmt_time(sec: float) -> str:
    return f"{int(sec // 60)}:{int(round(sec % 60)) if round(sec % 60) < 60 else 59:02d}"


def credits(text: str) -> dict:
    """credits.txt -> {'packs': [{'name', 'id', 'license', 'by', 'source'}], 'attribution': [the packs whose license
    asks for a credit (CC-BY*, CC Sampling Plus)]}."""
    packs, cur = [], None
    for line in text.splitlines():
        m = re.match(r'^- (.+?) \[([^\]]+)\]\s*$', line)
        if m:
            cur = {'name': m.group(1), 'id': m.group(2), 'license': '', 'by': '', 'source': ''}
            packs.append(cur)
            continue
        m = re.match(r'^\s+(license|by|source):\s*(.+)$', line)
        if m and cur is not None:
            val = m.group(2).strip()
            cur[m.group(1)] = re.sub(r'\s*\(https?://[^)]*\)$', '', val) if m.group(1) == 'license' else val
    attrib = [p for p in packs if re.match(r'CC-BY|CC-Sampling', p['license'], flags=re.I)]
    return {'packs': packs, 'attribution': attrib}


# --------------------------------------------------------------------------------------------- the hook

def motif_from_text(*texts: str) -> list[int]:
    """The first run of >= 3 note names with octaves joined by ' - ' in the hook sections ('G4 - Eb5 - D5 - C5')."""
    for t in texts:
        for m in re.finditer(r'([A-G][#b]?\d(?:\s*-\s*[A-G][#b]?\d){2,})', t):
            ps = [midi(x) for x in re.split(r'\s*-\s*', m.group(1))]
            if all(p is not None for p in ps):
                return ps
    return []


def top_line(notes: list) -> list:
    """The melody on top (a skyline): the highest note of each onset (notes within 40 ms: rolled chords), and a lower
    note only once the note above it has ended (a left hand under a held melody note is not the tune)
    -> [(t, dur, pitch, vel)] in time order."""
    groups: list[list] = []
    for n in sorted(notes, key=lambda n: n[0]):
        if groups and n[0] - groups[-1][0][0] < 0.04:
            groups[-1].append(n)
        else:
            groups.append([n])
    out, top_end, top_p = [], -1.0, -1
    for g in groups:
        n = max(g, key=lambda x: x[2])
        t = g[0][0]
        if n[2] >= top_p or t >= top_end - 0.06:
            out.append((t, n[1], n[2], n[3]))
            top_end, top_p = n[0] + n[1], n[2]
    return out


def _intervals(ps):
    return [b - a for a, b in zip(ps, ps[1:])]


def find_hook(tracks: list[dict], motif: list[int], *, lead_ids=(), leap: bool = True) -> list[dict]:
    """Occurrences of a motif (its interval shape, any transposition; each interval may differ by one semitone in
    the same direction - a major / minor transformation - and the first leap must stay a leap) in the top lines of
    the melodic tracks -> [{'t', 'end', 'tracks', 'pitches'}] merged across doublings (starts within 0.35 s)."""
    shape = _intervals(motif)
    if len(shape) < 2:
        return []
    hits = []
    for tr in tracks:
        if tr['family'] in ('drums', 'fx', 'timpani', 'bass') or tr.get('mute'):
            continue
        line = top_line(tr['notes'])
        ps = [n[2] for n in line]
        k = len(shape)
        for i in range(len(line) - k):
            iv = _intervals(ps[i:i + k + 1])
            if all((a == 0) == (b == 0) and (a > 0) == (b > 0) and abs(a - b) <= 1 for a, b in zip(iv, shape)) \
                    and (abs(iv[0]) >= 4 or not leap):
                seg = line[i:i + k + 1]
                if seg[-1][0] - seg[0][0] > 6:         # too spread out to be the motif
                    continue
                hits.append({'t': seg[0][0], 'end': seg[-1][0] + seg[-1][1], 'track': tr['id'],
                             'pitches': [n[2] for n in seg], 'lead': tr['id'] in lead_ids})
    hits.sort(key=lambda h: h['t'])
    merged: list[dict] = []
    for h in hits:
        if merged and h['t'] - merged[-1]['t'] < 0.35:
            m = merged[-1]
            if h['track'] not in m['tracks']:
                m['tracks'].append(h['track'])
            m['end'] = max(m['end'], h['end'])
            continue
        merged.append({'t': h['t'], 'end': h['end'], 'tracks': [h['track']], 'pitches': h['pitches']})
    return merged


def common_motif(tracks: list[dict], lead_ids, sections: list[dict], n: int = 4) -> list[int]:
    """No motif written down: the interval shape of n+1 notes that recurs in the most different sections of the lead
    tracks' top lines (ties: the more often) -> an example of its pitches."""
    best, best_key = [], (0, 0)
    table: dict[tuple, dict] = {}
    for tr in tracks:
        if tr['id'] not in lead_ids:
            continue
        line = top_line(tr['notes'])
        ps = [x[2] for x in line]
        for i in range(len(line) - n):
            iv = tuple(_intervals(ps[i:i + n + 1]))
            if max(abs(x) for x in iv) == 0 or sum(1 for x in iv if x == 0) > 1:
                continue
            sec = next((s['name'] for s in sections if s['start'] <= line[i][0] < s['end']), '')
            e = table.setdefault(iv, {'secs': set(), 'n': 0, 'ex': ps[i:i + n + 1]})
            e['secs'].add(sec)
            e['n'] += 1
    for iv, e in table.items():
        key = (len(e['secs']), e['n'])
        if key > best_key:
            best, best_key = e['ex'], key
    return best if best_key[0] >= 2 else []


def phrase_after(track: dict, t0: float, max_sec: float = 14.0) -> list:
    """The top-line notes of a track from t0 until a rest of more than 1.2 s (or max_sec) - the hook as written."""
    out = []
    for n in top_line(track['notes']):
        if n[0] < t0 - 0.01:
            continue
        if out and (n[0] - (out[-1][0] + out[-1][1]) > 1.2 or n[0] - t0 > max_sec):
            break
        out.append(n)
    return out


# --------------------------------------------------------------------------------------------- collect

def collect(song_dir, *, moves_log: list | None = None, song=None) -> dict:
    """All facts of a built song (out/ must exist: song.render.json, report.json, mix.wav)."""
    d = Path(song_dir)
    out_dir = d / 'out'
    rj = _load(out_dir / 'song.render.json')
    rep = _load(out_dir / 'report.json')
    if rj is None or rep is None or not (out_dir / 'mix.wav').is_file():
        raise FileNotFoundError(f"{d}: build the song first (python -m agentsound build {d.as_posix()}): "
                                f"needs out/song.render.json, out/report.json and out/mix.wav")
    md = docs.read(d)
    brief, arr, sound = md.get('BRIEF.md', ''), md.get('ARRANGEMENT.md', ''), md.get('SOUND.md', '')
    tmap = TempoMap(rj['tempoMap']) if 'tempoMap' in rj else TempoMap([[0, rj['tempo']]])
    sec = tmap.seconds_at

    meta = {}
    if song is not None and getattr(song, 'delivery_settings', None):
        meta = dict(song.delivery_settings.get('METADATA') or {})
    g = rep['global']
    genre_line = re.search(r'^- Genre:\s*(.+)$', brief, flags=re.M)
    facts: dict = {
        'slug': d.name,
        'title': meta.get('title') or rj.get('title') or d.name,
        'artist': meta.get('artist', 'AgentSound'),
        'album': meta.get('album', ''),
        'genre': meta.get('genre') or (docs.first_sentence(genre_line.group(1), 60) if genre_line else ''),
        'genre_text': docs.strip_md(genre_line.group(1)) if genre_line else '',
        'profile': (rj.get('analysis') or {}).get('profile', 'default'),
        'year': meta.get('year', ''), 'key': meta.get('key', ''), 'bpm': meta.get('bpm', ''),
        'duration': g['durationSec'],
        'lufs': g.get('lufsIntegrated'), 'truePeak': g.get('truePeakDbtp'), 'lra': g.get('loudnessRange'),
        'plr': g.get('plr'), 'width': rep.get('space', {}).get('widthAbove150HzPct'),
        'bars': (round(rep['sections'][-1]['endBar'] - rep['sections'][0]['startBar']) if rep.get('sections')
                 else g.get('bars')), 'bpmRange': g.get('bpmRange') or rep['render'].get('bpmRange'),
        'meters': sorted({f'{m[1]}/{m[2]}' for m in rj.get('meter', [[0, 4, 4]])}),
        'notesTotal': sum(len(t.get('notes', [])) for t in rj['tracks']),
        'clicks': len([c for c in rep.get('clicks', []) if c.get('inMix')]),
        'warnings': len([w for w in rep.get('warnings', []) if w.get('severity') == 'warning']),
    }

    # ---- sections (report timing + the arrangement's words + the parts table's key)
    form = {r.get('section', ''): r for r in docs.form_rows(arr)}
    parts = docs.part_rows(arr, brief)
    part_of: dict[str, dict] = {}
    for p in parts:
        for name in re.split(r'[,\s]+', p.get('sections', '')):
            if name:
                part_of[name] = p
    sections = []
    for i, s in enumerate(rep['sections']):
        f = form.get(s['name'], {})
        p = part_of.get(s['name'], {})
        key = re.split(r'[,(;]| -> ', p.get('key', ''))[0].strip() if p else ''
        sections.append({
            'name': s['name'], 'start': s['startSec'], 'end': s['endSec'], 'startBar': s['startBar'],
            'endBar': s['endBar'], 'lufs': s.get('lufs'), 'bpm': s.get('bpm'), 'bpmStart': s.get('bpmStart'),
            'bpmEnd': s.get('bpmEnd'), 'meter': s.get('meter', '4/4'), 'width': s.get('widthPct'),
            'part': docs.strip_md(p.get('part', '')), 'key': key, 'what': f.get('what happens', ''),
            'energy': f.get('energy', ''), 'harmony': f.get('harmony', ''), 'who': f.get('who plays', ''),
            'active': [a['id'] for a in s.get('active', []) if not a.get('bus')][:8],
        })
    facts['sections'] = sections
    facts['parts'] = [{'name': docs.strip_md(p.get('part', '')), 'key': p.get('key', ''), 'tempo': p.get('tempo', ''),
                       'meter': p.get('meter', ''), 'sections': p.get('sections', '')} for p in parts]
    lufs_vals = [s['lufs'] for s in sections if s['lufs'] is not None]
    lo, hi = (min(lufs_vals), max(lufs_vals)) if lufs_vals else (-30, -10)
    for s in sections:
        s['level'] = round((s['lufs'] - lo) / (hi - lo), 3) if s['lufs'] is not None and hi > lo else 0.5

    # ---- energy (per bar) and tempo curves
    rows = rep['timeline']['rows']
    cols = rep['timeline']['columns']
    ci = {c: i for i, c in enumerate(cols)}
    facts['energy'] = [[r[ci['sec']], r[ci['lufs']]] for r in rows]
    facts['barTimes'] = [r[ci['sec']] for r in rows]
    end_beat = rj['lengthBeats']
    tempo = []
    step = max(0.25, end_beat / 900)
    b = 0.0
    while b <= end_beat:
        tempo.append([round(sec(b), 3), round(tmap.bpm_at(b), 2)])
        b += step
    facts['tempo'] = tempo

    # ---- tracks and notes (seconds)
    nodes = {n['id']: n for n in rep.get('nodes', [])}
    lead_ids = [n['id'] for n in rep.get('nodes', []) if n.get('role') == 'lead']
    tracks = []
    for t in rj['tracks']:
        if t.get('mute') or not t.get('notes'):
            continue
        fam, col = family(t['id'])
        notes = []
        for st, du, p, v in t['notes']:
            a = sec(st)
            notes.append([round(a, 4), round(max(0.02, sec(st + du) - a), 4), int(p), int(v)])
        nd = nodes.get(t['id'], {})
        tracks.append({'id': t['id'], 'family': fam, 'color': col, 'type': t['instrument']['type'],
                       'role': nd.get('role', ''), 'lufs': nd.get('lufs'), 'notes': notes,
                       'dynamics': (nd.get('dynamics') or {}).get('dynamicsDb')})
    facts['leads'] = lead_ids

    # ---- players' moves (seconds)
    moves = []
    players_used: dict[str, set] = {}
    from .capture import POP_KINDS, absolute_moves
    for m in absolute_moves(moves_log or []):
        pl = m['player']
        players_used.setdefault(pl, set()).add(m['track'])
        if m['kind'] == 'dropped':
            continue
        t0, t1 = sec(m['beat']), sec(max(m['end'], m['beat']))
        moves.append({'t': round(t0, 4), 'end': round(t1, 4), 'player': pl, 'track': m['track'], 'kind': m['kind'],
                      'name': m['name'], 'pop': m['kind'] in POP_KINDS.get(pl, ())})
    for tr in tracks:
        tr['player'] = next((p for p, ts in players_used.items() if tr['id'] in ts), '')
        if tr['player'] and tr['family'] == 'other':
            tr['color'] = PLAYER_COLORS.get(tr['player'], tr['color'])
    facts['tracks'] = tracks
    facts['moves'] = moves
    facts['players'] = sorted(players_used, key=lambda p: list(PLAYER_COLORS).index(p) if p in PLAYER_COLORS else 9)

    # ---- the hook
    hook_text = docs.section(arr, 'hook') + '\n' + docs.section(brief, 'hook')
    motif = motif_from_text(hook_text)
    source = 'written' if motif else 'detected'
    if not motif:
        motif = common_motif(tracks, lead_ids or [t['id'] for t in tracks if t['family'] == 'piano'], sections)
    occ = find_hook(tracks, motif, lead_ids=lead_ids, leap=source == 'written') if motif else []
    phrase, phrase_track = [], ''
    if occ:
        first = occ[0]
        pref = [x for x in first['tracks'] if x in lead_ids] or first['tracks']
        tr = next(t for t in tracks if t['id'] == pref[0])
        phrase, phrase_track = phrase_after(tr, first['t']), tr['id']
    facts['hook'] = {'motif': motif, 'names': [note_name(p) for p in motif], 'source': source,
                     'occurrences': [{'t': round(o['t'], 3), 'end': round(o['end'], 3), 'tracks': o['tracks'],
                                      'section': next((s['name'] for s in sections if s['start'] <= o['t'] + 0.15 < s['end']),
                                                      '')} for o in occ],
                     'phrase': phrase, 'phraseTrack': phrase_track,
                     'text': docs.first_sentence(docs.section(arr, 'hook') or docs.section(brief, 'hook'), 200)}

    # ---- the story from the role files
    facts['wish'] = docs.wish(brief)
    facts['log'] = docs.log_entries(brief)
    facts['playersText'] = docs.players(arr)
    facts['soundRows'] = docs.sound_rows(sound)
    facts['soundMeasured'] = _measured_lines(sound)
    facts['verdict'] = docs.ar_verdict(md.get('AR.md', ''))
    facts['issues'] = docs.ar_issues(md.get('AR.md', ''))
    facts['revision'] = docs.ar_revision(md.get('AR.md', ''))
    facts['proposal'] = docs.ar_proposal(md.get('AR.md', ''))
    facts['mixPairs'] = _headline_pairs(md.get('MIX.md', ''))
    facts['masterPairs'] = _headline_pairs(md.get('MASTER.md', ''))
    facts['mixMoves'] = [docs.first_sentence(b, 150) for b in docs.bullets(docs.section(md.get('MIX.md', ''), 'moves'))][:6]
    facts['masterMoves'] = _master_moves(md.get('MASTER.md', ''))
    facts['files'] = sorted(md)
    cr = out_dir / 'credits.txt'
    facts['credits'] = credits(cr.read_text(encoding='utf-8')) if cr.is_file() else {'packs': [], 'attribution': []}
    facts['cover'] = 'cover.png' if (out_dir / 'cover.png').is_file() else ''
    facts['stemsDir'] = str(out_dir / 'stems')
    facts['items'] = track_items(facts, rj, rep, md.get('MIX.md', ''))
    return facts


# --------------------------------------------------------------------------------------------- meet the tracks

GROUP_NAMES = {'strings': 'Strings', 'winds': 'Woodwinds', 'brass': 'Brass', 'timpani': 'Percussion',
               'choir': 'Choirs', 'drums': 'Drums', 'bass': 'Bass', 'guitar': 'Guitars', 'organ': 'Organ',
               'synth': 'Synths', 'piano': 'Keys', 'other': 'More parts', 'fx': 'Effects'}
ORDER = {
    'orchestral': ['strings', 'winds', 'brass', 'timpani', 'choir', 'drums', 'bass', 'guitar', 'organ', 'synth',
                   'piano', 'other', 'fx'],
    'default': ['drums', 'bass', 'piano', 'organ', 'guitar', 'synth', 'strings', 'brass', 'winds', 'choir', 'timpani',
                'other', 'fx'],
}
SOLO_SEC, MIX_SEC = 4.2, 2.4


def _word_in(tid: str, text: str) -> bool:
    return re.search(rf'(?<![\w-]){re.escape(tid)}(?![\w-])', text) is not None


def sound_row_for(tid: str, rows: list[dict]) -> dict:
    for r in rows:
        head = r.get('role', '') or r.get('part', '') or r.get('track', '')
        if _word_in(tid, head) or _word_in(tid, r.get('sound', '')[:60]):
            return r
    return {}


def _db_sum(vals: list[float]) -> float:
    p = sum(10 ** (v / 10) for v in vals if v > -119)
    return 10 * math.log10(p) if p > 0 else -120.0


def track_items(facts: dict, rj: dict, rep: dict, mix_md: str, max_items: int = 10) -> list[dict]:
    """'Meet the tracks': the song's parts one by one (a group per family for a big score, the hook / hero parts on
    their own at the end), each with the moment where it is loudest (a hook statement or its player's moves count
    too) and its facts from the files: sound + why (SOUND.md), player moves (logs), layers (render JSON), level /
    width / note dynamics (report), its mix treatment (MIX.md)."""
    from .timeline import genre_family
    tracks = {t['id']: t for t in facts['tracks']}
    rjt = {t['id']: t for t in rj['tracks']}
    nodes = {n['id']: n for n in rep.get('nodes', [])}
    rows = facts['soundRows']
    fam_of = {tid: t['family'] for tid, t in tracks.items()}
    hero = set()
    for tid in tracks:
        r = sound_row_for(tid, rows)
        if 'hero' in (r.get('sound', '') + ' ' + r.get('role', '')).lower() or tracks[tid].get('player') == 'hornist':
            hero.add(tid)
    order = ORDER['orchestral' if genre_family(facts) == 'orchestral' else 'default']
    groups: dict[str, list[str]] = {}
    for tid, t in tracks.items():
        if tid in hero or len(t['notes']) < 4:
            continue
        groups.setdefault(fam_of[tid], []).append(tid)
    items = []
    for fam in order:
        if fam in groups:
            ids = groups[fam]
            items.append({'name': GROUP_NAMES.get(fam, fam.title()) if len(ids) > 1 else ids[0], 'ids': ids,
                          'family': fam, 'lead': False})
    # the heroes: one item per sound family (a guitar orchestra is one item), the hook carriers last
    hgroups: dict[str, list[str]] = {}
    for tid in hero:
        hgroups.setdefault(fam_of[tid], []).append(tid)
    for fam, ids in sorted(hgroups.items(), key=lambda kv: min(tracks[i]['notes'][0][0] for i in kv[1])):
        ids.sort()
        items.append({'name': ids[0] if len(ids) == 1 else f"{GROUP_NAMES.get(fam, fam.title())} ({len(ids)} heroes)",
                      'ids': ids, 'family': fam, 'lead': True})
    # too many: drop the quietest non-lead groups
    def lufs_of(it):
        return _db_sum([nodes.get(i, {}).get('lufs', -120) or -120 for i in it['ids']])
    while len(items) > max_items:
        cand = [it for it in items if not it['lead']]
        if not cand:
            break
        items.remove(min(cand, key=lufs_of))
    bar_secs = facts['barTimes']
    for it in items:
        it.update(_item_facts(it, facts, tracks, rjt, nodes, rows, mix_md, bar_secs))
    return items


def _item_facts(it, facts, tracks, rjt, nodes, rows, mix_md, bar_secs) -> dict:
    ids = it['ids']
    # the moment: the loudest bar of the group (+3 dB for a hook statement, +0.5 dB per pop move), not in the tail
    n_bars = min(len(nodes.get(i, {}).get('barsRmsDb', [])) for i in ids) if all(i in nodes for i in ids) else 0
    best, best_score = 0.0, -1e9
    hooks = [o for o in facts['hook']['occurrences'] if set(o['tracks']) & set(ids)]
    pops = [m for m in facts['moves'] if m['pop'] and m['track'] in ids]
    for b in range(min(n_bars, len(bar_secs))):
        t0 = bar_secs[b]
        if t0 + SOLO_SEC + MIX_SEC > facts['duration'] - 1:
            break
        lvl = _db_sum([nodes[i]['barsRmsDb'][b] for i in ids])
        if lvl < -80:
            continue
        # the bar and the next (the solo runs ~4 s) - both loud
        lvl2 = _db_sum([nodes[i]['barsRmsDb'][b + 1] for i in ids]) if b + 1 < n_bars else lvl
        score = min(lvl, lvl2 + 3)
        score += 3 * sum(1 for o in hooks if t0 - 0.2 <= o['t'] < t0 + SOLO_SEC)
        score += 0.5 * sum(1 for m in pops if t0 <= m['t'] < t0 + SOLO_SEC)
        if score > best_score:
            best, best_score = t0, score
    notes = sum(len(tracks[i]['notes']) for i in ids)
    lines = []
    row = next((r for r in (sound_row_for(i, rows) for i in ids) if r), {})
    if row:
        snd = re.sub(r'\s+', ' ', row.get('sound', ''))
        lines.append(('sound', docs.clip(snd, 96)))
        why = row.get('why', '')
        if why:
            lines.append(('why', docs.clip(why, 110)))
    players = sorted({tracks[i].get('player') for i in ids if tracks[i].get('player')})
    for pl in players:
        cnt: dict[str, int] = {}
        for m in facts['moves']:
            if m['player'] == pl and m['track'] in ids and m['kind'] not in ('groove', 'device', 'shape', 'pattern',
                                                                              'anticipation', 'space'):
                k = f"{m['kind']}:{m['name']}"
                cnt[k] = cnt.get(k, 0) + 1
        top = sorted(cnt.items(), key=lambda kv: -kv[1])[:4]
        if top:
            from .story import move_label
            lines.append(('player', f"{ROLE_TITLES.get(pl, pl).lower()}: " + ', '.join(
                f"{v} {move_label({'player': pl, 'kind': k.split(':')[0], 'name': k.split(':', 1)[1]})}"
                for k, v in top)))
    layers = []
    for i in ids:
        ins = rjt.get(i, {}).get('instrument', {})
        if ins.get('type') == 'stack':
            layers += [str(l.get('id')) for l in ins.get('params', {}).get('layers', []) if isinstance(l, dict)]
    uniq = list(dict.fromkeys(layers))
    if uniq:
        per = f" per part x {len(ids)}" if len(layers) > len(uniq) else ''
        lines.append(('layers', f"{len(uniq)} layers{per}: {', '.join(uniq[:6])}"))
    lv = [nodes[i]['lufs'] for i in ids if i in nodes and nodes[i].get('lufs') is not None]
    wd = [nodes[i].get('widthPct') for i in ids if i in nodes and nodes[i].get('widthPct') is not None]
    dy = [nodes[i]['dynamics'] for i in ids if i in nodes and isinstance(nodes[i].get('dynamics'), dict)]
    stat = []
    if lv:
        stat.append(f"{_db_sum(lv):.1f} LUFS")
    if wd:
        stat.append(f"width {max(wd):.0f} %")
    if dy:
        d = max(dy, key=lambda x: x.get('dynamicsDb') or 0)
        v = d.get('velocity') or {}
        if d.get('dynamicsDb') is not None:
            stat.append(f"note dynamics {d['dynamicsDb']:.1f} dB" + (f" (velocity {v['min']}-{v['max']})" if v else ''))
    stat.append(f"{notes} notes")
    lines.append(('stats', ' · '.join(stat)))
    mixline = _mix_line(ids, mix_md)
    if mixline:
        lines.append(('mix', mixline))
    return {'at': round(best, 3), 'solo': SOLO_SEC, 'mix': MIX_SEC, 'lines': lines, 'players': players,
            'color': tracks[ids[0]]['color'], 'lufs': round(_db_sum(lv), 1) if lv else None}


def _mix_line(ids: list[str], mix_md: str) -> str:
    """The sentence of MIX.md (prose or bullet) that best says what the mix did to these tracks: it names one of them
    early, carries a number and a mix move (ride, duck, carve, dip, trim, pan, fader); tool suggestions that were
    not taken ('suggested', 'proposed', 'flagged') and notes for other roles are left out."""
    prose = '\n'.join(l for l in mix_md.splitlines() if not l.strip().startswith('|'))
    best, best_score = '', 2
    for item in docs.bullets(prose) + [docs.strip_md(x) for x in re.split(r'\n\s*\n', prose)]:
        for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z(])|;\s+|\s+-\s+(?=[A-Z])', item):
            sent = sent.strip(' -')
            if len(sent) < 20 or not any(_word_in(i, sent) for i in ids):
                continue
            if re.search(r'\b(suggest\w*|propos\w*|flagged|inferred)\b', sent) or re.match(r'For the ', sent):
                continue
            first = min(m.start() for i in ids for m in [re.search(rf'(?<![\w-]){re.escape(i)}(?![\w-])', sent)]
                        if m)
            score = (2 if first < 40 else 0) + (1 if re.search(r'[+\-−]?\d+(?:\.\d+)?\s*dB', sent) else 0) + \
                (1 if re.search(r'\b(rid\w*|duck\w*|carv\w*|dip\w*|trim\w*|fader|pan\w*|boost\w*|cut)\b', sent) else 0)
            if score > best_score:
                best, best_score = sent, score
    return docs.clip(best, 120) if best else ''


def _measured_lines(sound_md: str) -> list[str]:
    """Sentences of SOUND.md's prose that carry a measured reason: a number and '->' / 'won' / 'chosen' /
    'measured' / 'Result' (tables left out)."""
    out = []
    prose = '\n'.join(l for l in sound_md.splitlines() if not l.strip().startswith('|'))
    for item in docs.bullets(prose) + [docs.strip_md(x) for x in re.split(r'\n\s*\n', prose)]:
        for sent in re.split(r'(?<=[.!?])\s+(?=[A-Z(])|;\s+', item):
            sent = sent.strip(' -')
            if re.search(r'\d', sent) and re.search(r'->|\bwon\b|\bchosen\b|\bchose\b|\bmeasured\b|\bResult\b', sent):
                if 25 < len(sent) < 230 and sent not in out:
                    out.append(sent)
    return out[:10]


def _headline_pairs(md: str) -> list[dict]:
    """The 'whole song' / before-after numbers of MIX.md / MASTER.md (LUFS-I, true peak, LRA, PLR, mid ...)."""
    out = []
    for tbl in docs.tables(md):
        hs = [h.lower() for h in tbl['header']]
        if 'before' in hs and 'after' in hs:
            out += docs.table_pairs(tbl)
    seen, res = set(), []
    for p in out:
        k = p['label'].lower()
        if k in seen:
            continue
        seen.add(k)
        res.append(p)
    return res[:10]


def _master_moves(md: str) -> list[str]:
    body = docs.section(md, 'Decisions') or docs.section(md, 'plan')
    return [docs.first_sentence(b, 150) for b in docs.bullets(body)][:6]
