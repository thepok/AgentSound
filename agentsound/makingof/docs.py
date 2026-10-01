"""Reading the role files of a song (BRIEF.md, ARRANGEMENT.md, SOUND.md, MIX.md, MASTER.md, AR.md): sections,
tables, bullets, numbered items and the "before -> after" numbers in them. Plain text in, plain data out."""

from __future__ import annotations

import re

ROLE_FILES = ('BRIEF.md', 'ARRANGEMENT.md', 'SOUND.md', 'MIX.md', 'MASTER.md', 'AR.md')


def strip_md(text: str) -> str:
    """Markdown inline markup away: **bold**, `code`, [links](...), > quotes; whitespace collapsed."""
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text)
    t = t.replace('**', '').replace('__', '').replace('`', '')
    t = re.sub(r'(?<!\w)\*(?!\s)([^*]+)(?<!\s)\*(?!\w)', r'\1', t)
    t = re.sub(r'^\s*>\s?', '', t, flags=re.M)
    return re.sub(r'\s+', ' ', t).strip()


def title(md: str) -> str:
    m = re.search(r'^#\s+(.+)$', md, flags=re.M)
    return strip_md(m.group(1)) if m else ''


def sections(md: str, level: int = 2) -> dict[str, str]:
    """{heading text: body} of the headings of one level (the body runs to the next heading of that level or
    higher). Heading texts are kept as written (strip_md applied)."""
    out: dict[str, str] = {}
    marks = '#' * level
    pat = re.compile(rf'^{marks}\s+(.+)$', flags=re.M)
    hs = list(pat.finditer(md))
    for i, h in enumerate(hs):
        end = hs[i + 1].start() if i + 1 < len(hs) else len(md)
        body = md[h.end():end]
        nxt = re.search(rf'^#{{1,{level - 1}}}\s', body, flags=re.M) if level > 1 else None
        if nxt:
            body = body[:nxt.start()]
        out[strip_md(h.group(1))] = body.strip('\n')
    return out


def section(md: str, *words: str, level: int = 2) -> str:
    """The body of the first heading that starts with the first word and contains every word (case-insensitive),
    else of the first that contains every word; '' if none."""
    secs = sections(md, level)
    for h, body in secs.items():
        if h.lower().startswith(words[0].lower()) and all(w.lower() in h.lower() for w in words):
            return body
    for h, body in secs.items():
        if all(w.lower() in h.lower() for w in words):
            return body
    return ''


def tables(body: str) -> list[dict]:
    """Markdown tables -> [{'header': [...], 'rows': [[cell, ...], ...]}] (cells strip_md'ed)."""
    out, cur = [], []
    for line in body.splitlines() + ['']:
        s = line.strip()
        if s.startswith('|') and s.endswith('|') and len(s) > 1:
            cur.append(s)
            continue
        if len(cur) >= 2:
            cells = [[strip_md(c) for c in r.strip('|').split('|')] for r in cur]
            header, rows = cells[0], [r for r in cells[1:] if not all(re.fullmatch(r':?-{2,}:?', c or '-') for c in r)]
            out.append({'header': header, 'rows': rows})
        cur = []
    return out


def table_dicts(tbl: dict) -> list[dict]:
    """A table's rows as {lower-case header: cell}."""
    hs = [h.lower() for h in tbl['header']]
    return [{hs[i] if i < len(hs) else str(i): c for i, c in enumerate(r)} for r in tbl['rows']]


def bullets(body: str) -> list[str]:
    """Top-level '- ' items with their continuation lines (nested items included), strip_md'ed."""
    items, cur = [], None
    for line in body.splitlines():
        if re.match(r'^[-*]\s+', line):
            if cur is not None:
                items.append(cur)
            cur = re.sub(r'^[-*]\s+', '', line)
        elif cur is not None and (line.startswith(' ') or line.startswith('\t')) and line.strip():
            cur += ' ' + line.strip()
        elif cur is not None and not line.strip():
            items.append(cur)
            cur = None
        elif cur is not None:
            items.append(cur)
            cur = None
    if cur is not None:
        items.append(cur)
    return [strip_md(re.sub(r'(?m)^\s*[-*]\s+', '', i)) for i in items]


def numbered(body: str) -> list[dict]:
    """Numbered items '1. **...** rest' with everything indented under them -> [{'n', 'head', 'text', 'raw'}]:
    head = the bold lead (strip_md), text = the whole item as plain text, raw = the item's markdown."""
    out = []
    ms = list(re.finditer(r'^(\d+)\.\s+', body, flags=re.M))
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(body)
        raw = body[m.end():end]
        stop = re.search(r'^\S', raw.split('\n', 1)[1] if '\n' in raw else '', flags=re.M)
        if stop and '\n' in raw:
            first, rest = raw.split('\n', 1)
            raw = first + '\n' + rest[:stop.start()]
        hm = re.match(r'\s*\*\*(.+?)\*\*', raw, flags=re.S)
        out.append({'n': int(m.group(1)), 'head': strip_md(hm.group(1)) if hm else strip_md(raw.split('\n')[0]),
                    'text': strip_md(raw), 'raw': raw.rstrip()})
    return out


def first_sentence(text: str, limit: int = 140) -> str:
    """The first sentence (to '. ', '; ' or ': ' past 30 chars), cut at a word boundary to `limit` chars."""
    t = strip_md(text)
    m = re.search(r'(?<=[a-z0-9)%\]])[.;](\s|$)', t[30:]) if len(t) > 30 else None
    if m:
        t = t[:30 + m.start()]
    t = t.rstrip(' .;:,')
    return clip(t, limit)


def clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    cut = text[:limit - 1]
    cut = cut[:cut.rfind(' ')] if ' ' in cut[limit // 2:] else cut
    return cut.rstrip(' ,;:(-') + '…'


# ------------------------------------------------------------------------------------------ before -> after

_NUM = r'[+\-−]?\d+(?:\.\d+)?'
_UNITS = r'dBTP|dBFS|dB|LUFS|LU|%|ms|kHz|Hz|BPM'
_SIDE = rf'({_NUM})((?:\s*(?:/|\.\.)\s*{_NUM})*)\s*({_UNITS})?'
_ARROW = re.compile(rf'{_SIDE}\s*(?:->|→)\s*\**\s*{_SIDE}\s*\**', flags=re.I)


def _num(s: str) -> float:
    return float(s.replace('−', '-'))


def arrow_pairs(text: str) -> list[dict]:
    """Every 'X -> Y' number change in a text: [{'label', 'before', 'after', 'unit', 'key', 'raw'}]. label = the words
    just before X in the same clause; unit = the unit after Y (or X, or the next unit in the clause); key = the
    after value was written in bold (the author's headline result)."""
    t = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', text).replace('`', '')
    t = re.sub(r'(?m)^\s*[-*]\s+', '', t)
    t = re.sub(r'\s+', ' ', t)
    out = []
    for m in _ARROW.finditer(t):
        b, a = _num(m.group(1)), _num(m.group(4))
        unit = m.group(6) or m.group(3) or ''
        if not unit:
            rest = t[m.end():m.end() + 70]
            stop = re.search(r'\.\s|;|\)', rest)
            um = re.search(rf'\b({_UNITS})', rest[:stop.start()] if stop else rest)
            unit = (um.group(1) or um.group(2)) if um else ''
        bold = '**' in t[m.start(4) - 3:m.start(4)] if m.start(4) >= 3 else False
        head = t[:m.start()].replace('**', '')
        cuts = [head.rfind('. '), head.rfind('; '), head.rfind(', ')]
        colon = head.rstrip().rstrip(':').rfind(': ')
        if not head.rstrip().endswith(':'):
            cuts.append(head.rfind(': '))
        opn = head.rfind('(')
        if opn > head.rfind(')'):
            cuts.append(opn)
        cut = max(cuts)
        label = head[cut + 1:].strip(' :,;(-') if cut >= 0 else head.strip(' :,;(-')
        if len(label) < 3:                     # "X: 1 -> 2" - the label is before the colon
            label = head.rstrip(' :')[max(0, colon + 1):].strip(' :,;(-')
        label = re.sub(r'^(and|the|from|was|were|is|now|it|to)\s+', '', label, flags=re.I)
        out.append({'label': clip(label, 60), 'before': b, 'after': a, 'unit': unit.replace('−', '-'), 'key': bold,
                    'raw': m.group(0).replace('*', '').strip(), '_end': m.end()})
    for i, p in enumerate(out):              # "a 1 -> 2, b 3 -> 4 LUFS": the first shares the second's unit
        if not p['unit'] and i + 1 < len(out) and out[i + 1]['unit'] and out[i + 1]['_end'] - p['_end'] < 60:
            p['unit'] = out[i + 1]['unit']
    for p in out:
        del p['_end']
    return out


def table_pairs(tbl: dict) -> list[dict]:
    """A 'before | after' table (or cells written 'X -> Y') -> [{'label', 'before', 'after', 'unit'}]."""
    hs = [h.lower() for h in tbl['header']]
    out = []
    if 'before' in hs and 'after' in hs:
        ib, ia = hs.index('before'), hs.index('after')
        for r in tbl['rows']:
            if max(ib, ia) >= len(r):
                continue
            mb, ma = re.search(_NUM, r[ib]), re.search(_NUM, r[ia])
            if not (mb and ma):
                continue
            um = re.search(rf'({_UNITS})', r[ia]) or re.search(rf'({_UNITS})', r[ib])
            lab = r[0] or (tbl['header'][0] if tbl['header'] else '')
            out.append({'label': clip(lab, 60), 'before': _num(mb.group(0)), 'after': _num(ma.group(0)),
                        'unit': um.group(1) if um else ''})
        return out
    for r in tbl['rows']:
        for i, c in enumerate(r[1:], 1):
            for p in arrow_pairs(c):
                p['label'] = clip(f"{r[0]} {tbl['header'][i] if i < len(tbl['header']) else ''}".strip(), 60)
                out.append(p)
    return out


def pairs(body: str) -> list[dict]:
    """All before -> after numbers of a markdown body: tables first, then the prose (tables removed)."""
    out = []
    for tbl in tables(body):
        out += table_pairs(tbl)
    prose = '\n'.join(l for l in body.splitlines() if not l.strip().startswith('|'))
    out += arrow_pairs(prose)
    return out


# ------------------------------------------------------------------------------------------ the role files

ROLE_NAMES = ('producer', 'arranger', 'sound-designer', 'mix-engineer', 'mastering-engineer', 'a-and-r')
_ROLE_ALIASES = {'mix': 'mix-engineer', 'mixing': 'mix-engineer', 'mastering': 'mastering-engineer',
                 'master': 'mastering-engineer', 'a&r': 'a-and-r', 'ar': 'a-and-r', 'sound designer': 'sound-designer',
                 'sound-design': 'sound-designer', 'mix engineer': 'mix-engineer',
                 'mastering engineer': 'mastering-engineer'}


def _roles_of(who: str) -> list[str]:
    who = who.lower().replace('a-and-r', 'a&r').replace('a and r', 'a&r')
    who = re.sub(r'\(.*?\)', '', who)
    out = []
    for part in re.split(r'\s*(?:\+|,|&(?!r)|\band\b)\s*', who):
        part = part.strip()
        r = part if part in ROLE_NAMES else _ROLE_ALIASES.get(part)
        if r and r not in out:
            out.append(r)
    return out


def log_entries(brief_md: str) -> list[dict]:
    """The '## Log' of BRIEF.md -> [{'who': [roles], 'text', 'revision': bool}] in order."""
    body = section(brief_md, 'Log')
    out = []
    for item in bullets(body):
        m = re.match(r'^([^:]{2,90}?):\s+(.*)$', item)
        if not m:
            continue
        who, text = m.group(1), m.group(2)
        roles = _roles_of(who)
        rev = 'revision' in who.lower() or text.lower().startswith('revision')
        if not roles and 'revision' in who.lower():
            roles = _roles_of(re.sub(r'.*\(|\).*', '', who)) or []
            inner = re.search(r'\(([^)]*)\)', who)
            if inner:
                roles = _roles_of(inner.group(1).split(';')[0])
        if not roles and rev:
            inner = re.match(r'\(?([^;)]*)', text)
            roles = _roles_of(inner.group(1)) if inner else []
        out.append({'who': roles, 'text': text, 'revision': rev, 'raw_who': who})
    return out


def wish(brief_md: str) -> dict:
    """{'quote': the user's words (the blockquote), 'summary': the first sentence of the brief's reading}."""
    body = section(brief_md, 'wish')
    quote = ' '.join(re.sub(r'^\s*>\s?', '', l) for l in body.splitlines() if l.strip().startswith('>'))
    rest = '\n'.join(l for l in body.splitlines() if not l.strip().startswith('>')).strip()
    q = strip_md(quote)
    return {'quote': q, 'summary': first_sentence(rest, 220) if rest else ''}


def players(arrangement_md: str) -> list[dict]:
    """ARRANGEMENT.md '## Players' -> [{'name', 'text'}] ('- **Piano** (hero piano): ...')."""
    body = section(arrangement_md, 'Players')
    out = []
    for line in re.findall(r'^[-*]\s+\*\*(.+?)\*\*(.*?)(?=^[-*]\s+\*\*|\Z)', body, flags=re.M | re.S):
        name, text = strip_md(line[0]), strip_md(line[1]).lstrip(' :')
        out.append({'name': name, 'text': text})
    return out


def form_rows(arrangement_md: str) -> list[dict]:
    """The form table of ARRANGEMENT.md (the first table with a 'section' column) as dicts."""
    body = section(arrangement_md, 'Form') or arrangement_md
    for tbl in tables(body):
        if any(h.lower().strip() == 'section' for h in tbl['header']):
            return table_dicts(tbl)
    return []


def part_rows(*mds: str) -> list[dict]:
    """The parts table (a table with 'part' and 'key' columns) of the first file that has one."""
    for md in mds:
        for tbl in tables(md):
            hs = [h.lower() for h in tbl['header']]
            if 'part' in hs and 'key' in hs:
                return table_dicts(tbl)
    return []


def sound_rows(sound_md: str) -> list[dict]:
    """SOUND.md's parts table (a table with a 'sound' column) as dicts."""
    for tbl in tables(sound_md):
        hs = [h.lower() for h in tbl['header']]
        if 'sound' in hs and ('role' in hs or 'part' in hs or 'track' in hs):
            return table_dicts(tbl)
    return []


def ar_verdict(ar_md: str) -> str:
    m = re.search(r'verdict:\s*\**\s*([a-z ]+)', ar_md, flags=re.I)
    return m.group(1).strip().lower() if m else ''


def ar_issues(ar_md: str) -> list[dict]:
    """AR.md '## Issues' -> [{'n', 'severity', 'title', 'owner', 'text'}]."""
    body = section(ar_md, 'Issues')
    out = []
    for it in numbered(body):
        head = it['head']
        m = re.match(r'\[(\w+)\]\s*(.*)', head)
        sev, ttl = (m.group(1).lower(), m.group(2)) if m else ('', head)
        om = re.search(r'Owner[s]?:\s*([^.]+)', it['text'])
        out.append({'n': it['n'], 'severity': sev, 'title': ttl.rstrip('.'), 'owner': om.group(1).strip() if om else '',
                    'text': it['text']})
    return out


def ar_revision(ar_md: str) -> list[dict]:
    """AR.md '## Revision' -> [{'n', 'head', 'status', 'pairs'}]: each numbered fix with its before -> after numbers
    (tables and prose) and its status word ('fixed', 'partly fixed', 'unchanged' ...) if the head names one."""
    body = section(ar_md, 'Revision')
    out = []
    for it in numbered(body):
        st = re.search(r'->\s*([a-z ]+?)(?:\s+for\b.*)?\.?$', it['head'])
        out.append({'n': it['n'], 'head': it['head'].rstrip('.'), 'status': st.group(1).strip() if st else '',
                    'pairs': pairs(it['raw'])})
    return out


def ar_proposal(ar_md: str) -> str:
    """The revision's closing verdict proposal ('ship candidate' ...) if the file has one."""
    m = re.search(r'Verdict proposal:\s*\**\s*([^*.\n]+)', ar_md, flags=re.I)
    return strip_md(m.group(1)).strip() if m else ''


def read(song_dir) -> dict:
    """{file name: markdown} of the role files present in a song folder."""
    from pathlib import Path
    d = Path(song_dir)
    out = {}
    for n in ROLE_FILES:
        p = d / n
        if p.is_file():
            out[n] = p.read_text(encoding='utf-8')
    return out
