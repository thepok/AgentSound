"""Strahlende Ferien - the background score for episode 5 of the Opa Konrad & Timo cartoon (German only,
D:/Projekte/cartoon/ep5_tschernobyl: the family on a Kaffeefahrt into the Chernobyl exclusion zone; brief:
ep5_tschernobyl/music_brief.md).

Laid out like songs/taschenmonster-de / songs/the-smog-monster-de: every scene / story beat is a section whose tempo
is set so its first downbeat lands exactly on its picture anchor; hits and stings sit at absolute picture seconds;
the melodic lead plays loud only in the dialogue gaps (split_lead) and the bed stays thin under the voices
(assemble.py also side-chain ducks the music under the dialogue). The song ends at the timeline total (tail incl.).

Sound world (the respect rule: no imitation of anyone's national / folk music, no anthems or marches, no mourning
music played for laughs - the comedy colour is German Kaffeefahrt kitsch): a cheesy home organ with its auto-rhythm,
vibraphone, the shopping-channel "99 Euro" sting (the same 3 notes every time: A6, B5, H3), decayed supermarket
muzak on warped tape, surf guitar in the empty pool, a Ballermann-style party Schlager in the reactor (original), an
ironic chorale for Ronny's love of the dome, monster-movie pastiche (style only) for the catfish, a wrestling-rock
fight for Oma, the series home sound. Around it the Geiger-tick groove: the counter's ticks are their own layer
(stem 'ticks') locked to the grid - one per bar (A), quarters (B), 8ths (B4, C, D, E), a 32nd buzz (F) - that stops
dead on "Ich kündige" (a bar without pulse), slows and dies in G1 and comes back as one last tick in the button.
All melodies are original: the Zone theme (a lonely 3/4 music-box tune in D Dorian, B1; warm in D major, H1-H2), the
99-Euro sting, the party hook, the selfie bounce, the muzak line, the surf riff, the whistled wolf line, the chase
ostinato, the chorale. Quotes: only the series' own material - the Konrad hook (songs/grandpa-konrad-intro) on
theremin (E2, F4) and solo clarinet (G8), Oma's tuba + timpani stomp (ep3 colour), the ep3 "RÜCKWÄRTS" stab (F7:
record-scratch + descending trombone), the ep4 softener lullaby (G5).

Timing: every build reads ep5_tschernobyl/build/timeline.json (line spans, total), episode.json (line ids, texts),
manifest.json (clip anchors line + offset, shake_at, gross_up) and sfx.json (the sounds' anchors, resolved exactly
like assemble.py), and measures the burps / key words in voice/line_*.wav (voiced runs like animate.py; a burp = the
low-centroid runs nearest to where the text puts it). When a file is missing the snapshot below is used.
Re-sync after a timing change = just rebuild; the bar counts come from the target tempi (PLAN).

Stems (group buses): lead, bass, drums, ticks, organ_kitsch, orchestra, stings (+ the hall / plate / echo returns).

Build: python -m agentsound build songs/strahlende-ferien
Check: python songs/strahlende-ferien/check_anchors.py   (onsets / gates / length on out/mix.wav -> out/anchors.json)
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Strahlende Ferien (Score)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'cartoon score to picture, episode 5 (Opa Konrad & Timo), Kaffeefahrt kitsch + '
                                     'Geiger-tick groove, ~599 s'}
ANALYSIS = {'profile': 'film'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'STRAHLENDE FERIEN', 'subtitle': 'AgentSound', 'seed': 5}

# ------------------------------------------------------------------ picture timing (read at build time)
import json as _json
import math as _math
import re as _re
from pathlib import Path as _Path

EP = _Path('D:/Projekte/cartoon/ep5_tschernobyl')
# snapshot 2026-10-17 (timeline 9:59.15, voice-based) - only used when the files cannot be read
_SNAP_TOTAL = 599.1454650000002
_SNAP_STARTS = [4.2, 10.88, 18.57, 25.25, 31.76, 35.11, 42.19, 47.34, 52.04, 59.1, 66.15, 74.56, 82.97, 93.79, 99.46,
                105.94, 108.73, 113.81, 120.31, 124.52, 128.46, 131.42, 140.75, 145.89, 150.52, 156.18, 162.62, 169.91,
                176.87, 181.27, 184.19, 194.09, 199.5, 205.28, 215.7, 224.63, 228.68, 232.88, 238.39, 245.64, 248.9,
                252.63, 261.87, 270.17, 273.95, 280.97, 286.18, 290.35, 293.31, 302.31, 310.14, 314.41, 324.4, 331.21,
                332.76, 338.23, 344.71, 353.28, 359.01, 364.37, 368.59, 377.33, 383.52, 393.27, 396.9, 402.74, 405.6,
                409.9, 417.83, 429.47, 436.33, 439.39, 445.35, 453.08, 459.03, 463.63, 468.9, 476.79, 481.85, 488.16,
                494.24, 500.56, 513.7, 521.04, 525.44, 527.75, 533.77, 543.07, 547.45, 552.18, 561.11, 569.16, 574.22,
                577.4, 582.14, 589.25]
_SNAP_DURS = [6.12, 7.35, 5.7, 6.2, 3.06, 6.66, 4.85, 3.72, 6.76, 6.63, 7.85, 3.51, 10.13, 5.1, 5.78, 2.37, 4.38, 6.2,
              3.91, 3.59, 1.84, 5.83, 4.84, 4.28, 2.15, 5.88, 5.47, 3.46, 4.11, 2.62, 5.7, 4.71, 5.36, 6.92, 7.8, 3.75,
              3.9, 4.95, 5.85, 1.02, 3.02, 7.57, 5.5, 1.68, 4.92, 4.37, 3.87, 2.66, 4.8, 7.12, 3.86, 9.43, 5.97, 1.2,
              5.17, 5.5, 6.61, 4.89, 3.96, 3.52, 7.63, 5.07, 6.25, 3.33, 4.44, 2.3, 3.95, 4.43, 11.34, 5.32, 2.76, 3.16,
              3.52, 4.84, 3.89, 4.93, 4.39, 4.63, 5.62, 3.0, 4.92, 8.24, 4.96, 3.84, 1.47, 2.52, 4.4, 3.82, 3.33, 4.73,
              7.7, 4.49, 2.35, 4.38, 6.69, 4.89]
_SNAP = [[a, d] for a, d in zip(_SNAP_STARTS, _SNAP_DURS)]
_SNAP_CLIPS = {'A1': {'t': 0.0}, 'A2': (2, -0.45), 'A3': (4, -1.0), 'A4': (7, -0.4), 'A5': (9, -0.8), 'A6': (11, -0.35),
               'B1': (13, -4.0), 'B2': (14, -0.6), 'B3': (17, -0.4), 'B4': (18, -0.3), 'B5': (22, -0.8),
               'C1': (23, -2.2), 'C2': (25, -0.3), 'C3': (26, -1.0), 'C4': (29, -2.6), 'C5': (31, 1.0, 4.28),
               'C6': (33, -0.6), 'D1': (35, -2.4), 'D2': (37, -0.15), 'D3': (40, -0.2), 'D4': (42, -0.6),
               'D5': (44, -1.6, 0.4), 'D6': (45, -2.0), 'D7': (46, -1.0), 'D8': (47, -0.5), 'E1': (50, -3.6),
               'E2': (51, -0.6), 'E3': (53, -0.4), 'E4': (55, -0.4), 'E5': (57, -0.6, 6.08), 'F1': (58, -2.6),
               'F2': (59, -0.4), 'F3': (61, -0.6), 'F4': (63, -0.8), 'F5': (66, -0.6), 'F6': (69, -2.4),
               'F7': (71, -0.6), 'F8': (73, -1.4, 1.0), 'G1': (74, -4.0, 3.0), 'G2': (75, -1.4), 'G3': (77, -0.3),
               'G4': (78, -1.2), 'G5': (80, -0.6), 'G6': (82, -1.6, 1.0), 'G7': (83, -6.0, 5.0), 'G8': (84, -0.8),
               'H1': (87, -3.0), 'H2': (88, -3.0), 'H3': (90, -1.4), 'H4': (91, -3.6), 'H5': (94, -0.8)}
# voiced runs (s into the take, spectral centroid Hz) measured 2026-10-17
_SNAP_RUNS = {6: [(0.3, 3.3, 5122), (4.1, 4.7, 756), (4.97, 5.63, 6654), (6.23, 6.63, 846)],
              12: [(0.0, 1.03, 3000), (2.0, 3.5, 3000)], 27: [(0.0, 1.03, 3000), (1.4, 3.4, 3000), (4.47, 5.43, 3000)],
              36: [(0.0, 0.27, 2000), (0.83, 1.1, 2000), (1.77, 2.23, 2000), (2.6, 3.6, 2000)],
              49: [(0.0, 1.63, 3269), (1.9, 2.73, 761), (2.9, 3.3, 439), (3.63, 4.13, 2467)],
              52: [(0.0, 2.83, 3000), (3.83, 5.57, 3000), (5.83, 7.33, 3000), (8.5, 9.13, 3000)],
              53: [(1.47, 2.8, 3000), (3.67, 4.17, 3000), (4.67, 5.83, 3000)],
              65: [(0.0, 1.43, 4470), (1.6, 3.0, 3195), (3.17, 4.3, 531)],
              68: [(0.4, 1.2, 3000), (1.63, 2.33, 3000), (2.57, 3.1, 3000), (3.4, 4.37, 3000)],
              72: [(0.1, 1.27, 3000), (2.1, 3.0, 3000)],
              82: [(0.0, 1.23, 900), (1.8, 2.6, 900), (3.07, 4.5, 900), (4.7, 5.53, 900), (6.13, 8.03, 900)],
              83: [(0.0, 1.93, 524), (2.17, 2.43, 537), (2.67, 2.93, 492), (3.27, 3.53, 514), (3.9, 4.2, 545)],
              95: [(0.0, 0.6, 1671), (0.73, 2.07, 3747), (2.3, 6.67, 477)]}


def _load(path):
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


_tl = _load(EP / 'build' / 'timeline.json')
_ep = _load(EP / 'episode.json')
_man = _load(EP / 'manifest.json')
_sfx = _load(EP / 'sfx.json') or []
TIMING_SOURCE = 'timeline.json' if _tl else 'snapshot'
TOTAL = _tl['total'] if _tl else _SNAP_TOTAL
_spans = _tl['spans'] if _tl else _SNAP
_ids = [p['id'] for p in _ep['panels']] if _ep and len(_ep['panels']) == len(_spans) else list(range(1, len(_spans) + 1))
LINE_IDX = {lid: i for i, lid in enumerate(_ids)}            # dialogue id -> index into the spans / voice files
SPANS = {lid: tuple(_spans[i]) for lid, i in LINE_IDX.items()}
TEXT = {p['id']: p.get('text', '') for p in (_ep['panels'] if _ep else [])}
if _man:
    CLIPS = [c for ch_ in _man['episode']['chapters'] for c in ch_['clips']]
else:
    CLIPS = []
    for k, v in _SNAP_CLIPS.items():
        c = {'id': k, 'start': v if isinstance(v, dict) else {'line': v[0], 'offset': v[1]}}
        if isinstance(v, tuple) and len(v) > 2:
            c['shake_at'] = v[2]
        CLIPS.append(c)
CLIP_BY_ID = {c['id']: c for c in CLIPS}


def L(i):
    """Start of line i (seconds)."""
    return SPANS[i][0]


def E(i):
    """End of line i (seconds)."""
    return SPANS[i][0] + SPANS[i][1]


def _anchor(a):
    return a['t'] if 't' in a else L(a['line']) + a.get('offset', 0.0)


CLIP_T = {c['id']: _anchor(c['start']) for c in CLIPS}
CLIP_END = {}
for _k, _c in enumerate(CLIPS):
    CLIP_END[_c['id']] = CLIP_T[CLIPS[_k + 1]['id']] if _k + 1 < len(CLIPS) else TOTAL


def C(cid):
    """Start of a manifest clip (seconds)."""
    return CLIP_T[cid]


def shake(cid, default=0.0):
    return C(cid) + CLIP_BY_ID.get(cid, {}).get('shake_at', default)


def _sfx_t(e):
    """Start of an sfx.json entry, resolved exactly like assemble.py."""
    if 'clip' in e:
        return CLIP_T[e['clip']] + e.get('offset', 0.0)
    if 't' in e:
        return e['t']
    lid = e['line_id'] if 'line_id' in e else _ids[e['line']]
    st = L(lid) + e.get('offset', 0.0)
    if e.get('from') == 'end':
        st += SPANS[lid][1]
    if 'frac' in e:
        st += e['frac'] * SPANS[lid][1]
    return st


def SFX(what, default, n=0):
    """Start of the n-th sfx.json sound whose 'what' contains `what` (the default when there is none)."""
    try:
        hits = sorted(_sfx_t(e) for e in _sfx if what.lower() in e.get('what', '').lower())
        return hits[n] if len(hits) > n else default
    except (KeyError, IndexError, TypeError):
        return default


def gross(cid, default):
    """(start, dur) of a clip's gross-up insert ('line N end + x')."""
    g = CLIP_BY_ID.get(cid, {}).get('gross_up') or {}
    mm = _re.match(r'^\s*line\s+(\d+)\s+(start|end)\s*(?:([+-])\s*([\d.]+))?\s*$', str(g.get('at', '')))
    if not mm:
        return default, g.get('dur', 2.4)
    lid = int(mm.group(1))
    base = L(lid) if mm.group(2) == 'start' else E(lid)
    off = (1 if mm.group(3) == '+' else -1) * float(mm.group(4)) if mm.group(3) else 0.0
    return base + off, g.get('dur', 2.4)


# ---- voiced runs of a take (animate.py _env / burp_span: 30 fps RMS / 90th percentile > 0.18, gaps >= 0.15 s),
# each with its spectral centroid (a burp is the low, dark run)
def _runs(lid):
    try:
        import wave
        import numpy as np
        with wave.open(str(EP / 'voice' / f'line_{LINE_IDX[lid]:02d}.wav'), 'rb') as w:
            sr, ch_ = w.getframerate(), w.getnchannels()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        a = a.reshape(-1, ch_).mean(1)
        hop = sr // 30
        n = len(a) // hop
        rms = np.sqrt((a[:n * hop].reshape(n, hop) ** 2).mean(1) + 1e-9)
        on = rms / (np.percentile(rms, 90) + 1e-6) > 0.18
        out, s0, gap = [], None, 0
        for j, v in enumerate(list(on) + [False] * 8):
            if v:
                if s0 is None:
                    s0 = j
                gap = 0
            elif s0 is not None:
                gap += 1
                if gap >= 4:
                    out.append((s0 / 30, (j - gap + 1) / 30))
                    s0 = None
        res = []
        for r0, r1 in out:
            if r1 - r0 <= 0.25:
                continue
            seg = a[int(r0 * sr):int(r1 * sr)]
            sp = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
            f = np.fft.rfftfreq(len(seg), 1 / sr)
            res.append((r0, r1, float((sp * f).sum() / (sp.sum() + 1e-9))))
        return res or _SNAP_RUNS.get(lid, [])
    except Exception:
        return _SNAP_RUNS.get(lid, [])


RUNS = {lid: _runs(lid) for lid in _SNAP_RUNS if lid in SPANS}


def burp(lid):
    """(start, end) of the Ööörps in line lid: the dark (low-centroid) runs around the one nearest to where the text
    puts it; a line that is only a burp is gated whole."""
    txt = TEXT.get(lid, '')
    d = SPANS[lid][1]
    if _re.sub(r'[^A-Za-zÄÖÜäöüß]', '', txt.replace('Ööörps', '')) == '':
        return L(lid), E(lid)
    k = txt.find('Ööörps')
    guess = d * (k + 3) / len(txt) if k >= 0 and txt else d - 0.6
    r = RUNS.get(lid) or [(guess - 0.3, guess + 0.3, 500)]
    dark = [q for q in r if q[2] < 1200] or r
    i = min(range(len(r)), key=lambda j: (r[j] not in dark, abs((r[j][0] + r[j][1]) / 2 - guess)))
    j0 = j1 = i
    while j0 > 0 and r[j0 - 1][2] < 1200 and r[j0][0] - r[j0 - 1][1] < 0.4:
        j0 -= 1
    while j1 + 1 < len(r) and r[j1 + 1][2] < 1200 and r[j1 + 1][0] - r[j1][1] < 0.4:
        j1 += 1
    return L(lid) + r[j0][0], L(lid) + r[j1][1]


def word(lid, k, frac):
    """Start of voiced run k of line lid (negative k from the end), or the text-fraction estimate."""
    r = RUNS.get(lid) or []
    try:
        return L(lid) + r[k][0]
    except IndexError:
        return L(lid) + SPANS[lid][1] * frac


def word_end(lid, k, frac):
    r = RUNS.get(lid) or []
    try:
        return L(lid) + r[k][1]
    except IndexError:
        return L(lid) + SPANS[lid][1] * frac


# ------------------------------------------------------------------ the anchors
T_WELCOME = L(1)                                  # "Herzlich willkommen" (organ glissando under it)
T_CREAK = SFX('barrier creak 1', 2.85)            # A1 the barrier creaks: a cymbal swell ...
T_BACKFIRE = SFX('BACKFIRE', 4.6)                 # ... up to the coach's backfire
T_SELFIE = SFX('phone shutter', E(3) - 0.15)      # Mandy's selfie (line 3): glow-up sparkle
T_FOIL0, T_FOIL1 = C('A4'), C('A5')               # A4 Konrad's foil: the crinkle doubles the hi-hat
T_EURO1 = E(11) + 0.05                            # "... neunundneunzig Euro!": the 99-Euro sting
T_CASH = word_end(12, 0, 0.3) + 0.05              # Oma "Ich nehm drei.": the cash register
T_PARK = C('B1')
T_SERIOUS = C('B2')
T_DRY16 = L(16) - 0.6                             # the full stop before "Doch. Da ist 'n Riesenrad."
T_SELFIE2 = C('B3')                               # ... then the cheesy organ chord as if nothing happened
T_TICK8 = C('B4')
T_FWEET = SFX('ear whistle 1', E(21) - 0.2)       # Konrad "DU nicht.": the ear whistle
T_SOUV = C('B5')
T_MOUSTACHE = SFX('moustache glow', L(22) + 3.2)  # Ronny's moustache lights up
T_EURO2 = E(22) + 0.05                            # the 99-Euro sting again (souvenir pitch)
T_MARKET = C('C1')
T_CHOMP, D_CHOMP = gross('C2', E(25) + 0.3)       # CHOMP + the gross-up (Oma bites the can)
T_GLOW = C('C3')
T_OMAGLOW = L(26)                                 # "Die OMA leuchtet!"
T_STARK = word(27, -1, 0.82)                      # "Und STARK."
T_SWOON = SFX('swoon (Konrad', L(28) - 0.2)       # harp swoon for Konrad
T_POOL = C('C4')
T_FALL = SFX('falling whistle', L(31) + 3.2)      # the cannonball: whistle fall ...
T_SPLAT = shake('C5', 4.28)                       # ... goo SPLAT
T_LOUNGE = C('C6')
T_SAX = E(34) + 0.03                              # Detlef's whisper: the sleazy sax lick
T_MUTANT = C('D1')
T_WURST = L(40)                                   # "WURST!"
T_GROSS_D, D_GROSS_D = gross('D3', E(40) + 0.5)
T_WOLVES = C('D4')
T_CHASE = C('D5')
T_STREAM = C('D6')
T_COACH = C('D7')
T_SOUR = E(46) + 0.05                             # "Tschüssi!": the sting slowed down and sour
T_RUN = C('D8')
T_HYMN = C('E1')                                  # the chase ends on a hit at the cut
T_GATE = SFX('slams the fence gate', T_HYMN + 2.65)
T_SCHEME = C('E2')
T_UNFOLD = SFX('unfolding clack 1', L(52))
T_REVEAL = word_end(52, 0, 0.3) + 0.04            # "Der Sauber-O-Mat Sechstausend!": the reveal fanfare
T_LIEB = word(53, -1, 0.75)                       # "... ich hab dich immer lieb gehabt": schmaltz
T_QUIT = SFX('switches itself off', L(54) + 0.9)  # "Ich kündige." - the ticks stop dead
T_PERSONAL = C('E5')
T_KICK = shake('E5', 6.08)                        # the door KICK
T_TICKS_BACK = SFX('frantic ticks', T_KICK + 0.22)
T_MALLE = E(58) + 0.05                            # after the dry scream: the party
T_PROST = SFX('Prost! can up', L(61) + 4.65)
T_SPROUTS = [SFX('sprout pop', L(62) + 1.68 + 0.17 * k, k) for k in range(3)] + \
            [SFX('leaves pop', L(62) + 3.53 + 0.1 * k, k) for k in range(4)]
T_VAC = C('F4')
T_NOZZLE = SFX('nozzle kicks on', L(63) + 1.0)
T_BAG = [SFX('bag swells (creak 1)', L(63) + 2.22), SFX('bag swells (creak 2)', E(63) + 0.8),
         SFX('bag balloons', L(64) + 2.35)]       # each bag stage pushes the key up a semitone
T_GLOWUP = C('F5')
T_GLOWHUM = SFX('glow hum swell (Mandy', L(66) + 0.5)
T_GROSS_F, D_GROSS_F = gross('F5', E(67) + 0.2)
T_GLOWUP2 = L(68)                                 # "GLOW-UP!": the hook back, louder
T_LICK = C('F6')
T_LICKSLURP = SFX('lick slurp', T_LICK + 1.7)
T_ACH = SFX('harp swoon (Ach.)', L(70) + 2.6)
T_LEVER = C('F7')
T_RUECK = word(72, -1, 0.7)                       # "Das ist RÜCKWÄRTS!"
T_BURSTCUT = C('F8')
T_CLUNK = SFX('lever CLUNK', T_BURSTCUT + 0.32)
T_BURST = SFX('bag BURST', T_BURSTCUT + 1.0)
T_PIPE = C('G1')
T_LANDS = sorted(SFX(f'lands on the bridge ({w})', T_PIPE + d) for w, d in
                 (('Ronny', 0.95), ('Konrad', 1.4), ('Timo', 1.8), ('Mandy', 2.15), ('Finn', 2.5)))
T_OMALAND = SFX('OMA lands', T_PIPE + 3.0)
T_DEATH = L(74)                                   # "Dafür... gibt es keine Zahl mehr."
T_KAIJU = C('G2')
T_BLUBB = L(75)                                   # "BLUUUBB."
T_CHARGE = L(77)                                  # Ronny's charge
T_GULP, D_GULP = gross('G3', E(77) + 0.4)
T_INSIDE = C('G4')
T_BUBBLE = C('G5')
T_SOFTENER = SFX('softener ray fires', E(80) - 0.6)
T_PURR = SFX('catfish purrs', E(80) + 0.4)
T_WORDS = word(82, 0, 0.0)                        # Oma's first word: hard cut into the fight
WORD_HITS = [L(82) + r[0] for r in (RUNS.get(82) or [])][:5] or [L(82), L(82) + 1.8, L(82) + 3.07]
T_FIGHT = E(82) + 0.1
BURP83 = burp(83)                                 # the mega-burp gates everything
T_TRIUMPH = BURP83[1] + 0.05
T_MAEDCHEN = C('G8')
T_WHEEL = C('H1')
T_BULBS = [SFX('bulbs ping on', E(87) + 0.2), SFX('bulbs ping on (2)', E(87) + 0.45)]
T_TURN = SFX('big rusty creak', E(87) + 0.5)      # the wheel starts: the Zone theme in full
T_GONDOLA = C('H2')
T_REPRISE = C('H3')
T_EURO3 = E(90) + 0.05
T_HOME = C('H4')
T_TAG = C('H5')
T_ENDCHORD = SFX('end sting (freeze)', E(96) + 0.25)
T_END = TOTAL

# (name, start, target bpm, meter): each section runs to the next one's start; bar counts from the target tempo
_PLAN = [('kaffee', 0.0, 108, '4/4'), ('bus', C('A2'), 108, '4/4'), ('foil', T_FOIL0, 108, '4/4'),
         ('finn', T_FOIL1, 108, '4/4'), ('pitch', C('A6'), 108, '4/4'),
         ('park', T_PARK, 76, '3/4'), ('serious', T_SERIOUS, 76, '3/4'), ('drystop', T_DRY16, 76, '3/4'),
         ('selfie', T_SELFIE2, 112, '4/4'), ('ticks8', T_TICK8, 112, '4/4'), ('souvenir', T_SOUV, 112, '4/4'),
         ('market', T_MARKET, 92, '4/4'), ('chomp', T_CHOMP, 60, '4/4'), ('glow', T_GLOW, 92, '4/4'),
         ('pool', T_POOL, 150, '4/4'), ('goo', T_SPLAT, 80, '4/4'), ('lounge', T_LOUNGE, 96, '4/4'),
         ('mutants', T_MUTANT, 84, '4/4'), ('wurst', T_WURST, 120, '4/4'), ('wolves', T_WOLVES, 84, '4/4'),
         ('chase', T_CHASE, 176, '2/4'), ('stream', T_STREAM, 176, '2/4'), ('coach', T_COACH, 176, '2/4'),
         ('run', T_RUN, 176, '2/4'), ('hymn', T_HYMN, 60, '4/4'), ('scheme', T_SCHEME, 100, '4/4'),
         ('quit', T_QUIT, 100, '4/4'), ('personal', T_PERSONAL, 100, '4/4'), ('reactor', T_KICK, 128, '4/4'),
         ('malle', T_MALLE, 128, '4/4'), ('vacuum', T_VAC, 128, '4/4'), ('glowup', T_GLOWUP, 128, '4/4'),
         ('lick', T_LICK, 128, '4/4'), ('lever', T_LEVER, 128, '4/4'), ('burst', T_BURSTCUT, 128, '4/4'),
         ('pipe', T_PIPE, 90, '4/4'), ('kaiju', T_KAIJU, 66, '4/4'), ('gulp', T_GULP, 66, '4/4'),
         ('inside', T_INSIDE, 66, '4/4'), ('bubble', T_BUBBLE, 70, '3/4'), ('words', T_WORDS, 92, '4/4'),
         ('fight', T_FIGHT, 140, '4/4'), ('megaburp', BURP83[0], 140, '4/4'), ('triumph', T_TRIUMPH, 140, '4/4'),
         ('maedchen', T_MAEDCHEN, 70, '4/4'), ('wheel', T_WHEEL, 72, '3/4'), ('gondola', T_GONDOLA, 72, '3/4'),
         ('reprise', T_REPRISE, 108, '4/4'), ('home', T_HOME, 84, '4/4'), ('tag', T_TAG, 84, '4/4')]
# a section whose anchor no longer comes after the previous one (a timing change) is dropped: its music still
# plays at its absolute times, only the tempo grid skips it
PLAN = []
for _n, _a, _bpm, _m in _PLAN:
    if PLAN and _a <= PLAN[-1][1] + 0.3:
        continue
    PLAN.append([_n, _a, None, _bpm, _m])
for _k, _p in enumerate(PLAN):
    _p[2] = PLAN[_k + 1][1] if _k + 1 < len(PLAN) else T_END
for _p in PLAN:
    _n, _a, _b, _bpm, _m = _p
    _num, _den = (int(x) for x in _m.split('/'))
    _bpb = _num * 4.0 / _den
    _beats = (_b - _a) * _bpm / 60.0
    if _beats < max(6.0, 2 * _bpb):                  # short beat: one bar of n quarter beats
        _nb = max(1, round(_beats))
        _p[3:] = [1, (_nb, 4), _nb]
    else:
        _p[3:] = [max(1, round(_beats / _bpb)), (_num, _den), _bpb]
PLAN = [tuple(p) for p in PLAN]                       # (name, start s, end s, bars, meter, beats per bar)


def _gate(lid):
    """The burp of line lid, held shut up to the next word when that follows within 0.5 s."""
    b0, b1 = burp(lid)
    nxt = [L(lid) + r[0] for r in RUNS.get(lid) or [] if b1 < L(lid) + r[0] < b1 + 0.5]
    return b0, (max(b1, min(nxt) - 0.13) if nxt else b1)


GATES = [_gate(lid) for lid in (6, 49, 65, 83, 95) if lid in SPANS]   # the music is silent under the burps
DRY = [(T_DRY16, E(16) - 0.02),                       # B2: the full stop, Ronny's line lands dry
       (E(25) + 0.02, T_CHOMP - 0.02),                # C2: the chomp (the sting enters on it)
       (L(32) - 0.1, E(32) + 0.05),                   # C5: "Ich bin ein Messgerät. Kein Babysitter." dry
       (L(58) - 0.05, E(58) + 0.02),                  # F1: the counter's scream dry
       (L(74) - 0.05, E(74) + 0.05),                  # G1: the counter's death line in silence
       (L(96) - 0.05, E(96) + 0.05)]                  # H5: the last scream dry
# the picture hits checked on the rendered mix (check_anchors.py: the onset nearest each target)
HITS = {'backfire': T_BACKFIRE, 'euro1': T_EURO1, 'cash': T_CASH, 'riesenrad_organ': T_SELFIE2, 'euro2': T_EURO2,
        'chomp_sting': T_CHOMP, 'stark': T_STARK, 'splat': T_SPLAT, 'wurst': T_WURST, 'chase': T_CHASE,
        'sour99': T_SOUR, 'chase_end': T_HYMN, 'reveal': T_REVEAL, 'kick': T_KICK, 'prost': T_PROST,
        'glowup': T_GLOWUP2, 'rueckwaerts': T_RUECK, 'burst': T_BURST, 'oma_lands': T_OMALAND, 'blubb': T_BLUBB,
        'gulp': T_GULP, **{f'word{k + 1}': t for k, t in enumerate(WORD_HITS[:3])}, 'triumph': T_TRIUMPH,
        'bulbs': T_BULBS[0], 'euro3': T_EURO3, 'end_chord': T_ENDCHORD}

# ------------------------------------------------------------------ helpers
_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(name):
    """'F#4' -> MIDI (C4 = 60)."""
    if isinstance(name, int):
        return name
    mm = _re.match(r'^([A-G])([#b]?)(-?\d)$', name)
    return 12 * (int(mm.group(3)) + 1) + _PC[mm.group(1)] + {'#': 1, 'b': -1, '': 0}[mm.group(2)]


def ch(*names):
    return [m(x) for x in names]


def mbar(section, n, beat=0.0):
    """Musical (1-based) bar n of a section: mbar(sec, 1) = its first downbeat."""
    return section.bar(n - 1, beat=beat)


def bpm_of(a, b, bars, bpb):
    return bars * bpb * 60.0 / (b - a)


# ------------------------------------------------------------------ synth voices
def geiger_voice():
    """The counter's tick: a 4 ms burst of bright noise (high-passed), no pitch."""
    return inst.va(osc1__level=0.0, osc2__level=0.0, noise__level=1.0, noise__color='white', filter__type='hp12',
                   cutoff=2600, resonance=0.25, filter__env=0.0, filter__keytrack=0.0, filter__velocity=0.4,
                   amp__attack=0.001, amp__decay=0.01, amp__sustain=0.0, amp__release=0.006, amp__velocity=0.9,
                   level=-2.0)


def crinkle_voice():
    """Konrad's tin foil: short band-passed noise rustles."""
    return inst.va(osc1__level=0.0, osc2__level=0.0, noise__level=1.0, noise__stereo=0.5, filter__type='bp12',
                   cutoff=5200, resonance=0.35, filter__env=1.0, fenv__decay=0.03, filter__keytrack=0.6,
                   amp__attack=0.001, amp__decay=0.045, amp__sustain=0.0, amp__release=0.03, amp__velocity=0.9,
                   level=-8.0)


def glow_voice():
    """The glow colour: a buzzing, slightly sour shimmer - FM 'ring' partials (osc2 a detuned tritone up),
    a fast vibrato, a bright pad envelope."""
    return inst.va(osc1__wave='sine', osc2__wave='sine', osc2__level=0.6, osc2__semi=6, osc2__fine=23, fm=2.2,
                   drift__pitch=6, filter__type='lp12', cutoff=9000, resonance=0.1, filter__env=0.0,
                   amp__attack=0.35, amp__decay=1.0, amp__sustain=0.85, amp__release=0.8, amp__velocity=0.6,
                   unison=3, unison__detune=0.35, unison__spread=0.9, hpf=500,
                   mods=[vamod.lfo('sine', hz=13.0, id='buzz') >> ('pitch', 18)], level=-12.0)


def stab_voice():
    """The shopping-channel synth stab: bright detuned saws with a snappy filter envelope."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.7, osc2__fine=9, unison=3,
                   unison__detune=0.3, filter__type='lp12', cutoff=1800, resonance=0.2, filter__env=3.2,
                   fenv__decay=0.25, fenv__sustain=0.3, amp__attack=0.003, amp__decay=0.4, amp__sustain=0.6,
                   amp__release=0.25, amp__velocity=0.8, level=-8.0)


def theremin():
    """Konrad's scheme voice (the ep2 theremin)."""
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11, filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.9,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def sweep_noise(level=-12.0):
    """Sustained noise for risers / whooshes / the vacuum roar (cutoff automated)."""
    return inst.va(osc1__level=0.0, osc2__level=0.0, noise__level=1.0, noise__stereo=0.6, filter__type='bp12',
                   cutoff=1200, resonance=0.45, filter__env=0.0, filter__keytrack=0.0, amp__attack=0.05,
                   amp__decay=0.5, amp__sustain=0.9, amp__release=0.3, level=level)


def roar_voice():
    """The Sauber-O-Mat: a gritty saw drone that climbs (legato glide)."""
    return inst.va(osc1__wave='saw', osc2__wave='saw', osc2__level=0.8, osc2__fine=-17, sub__level=0.4,
                   noise__level=0.25, mode='legato', glide=1.5, filter__type='ladder', cutoff=900, resonance=0.3,
                   filter__drive=0.6, filter__env=0.0, amp__attack=0.3, amp__decay=0.5, amp__sustain=0.9,
                   amp__release=0.4, mods=[vamod.lfo('sine', hz=6.5, id='wob') >> ('pitch', 20)], level=-14.0)


def hum_voice():
    """The reactor hall's hum: a low, beating sine/square drone."""
    return inst.va(osc1__wave='sine', osc2__wave='square', osc2__level=0.25, osc2__fine=7, sub__level=0.3,
                   filter__type='lp12', cutoff=500, resonance=0.1, filter__env=0.0, amp__attack=0.8,
                   amp__decay=1.0, amp__sustain=1.0, amp__release=1.2, level=-6.0)


def slide_voice():
    """The cartoon slide whistle (fweet / the falling whistle): a sine with a wide glide."""
    return inst.va(osc1__wave='sine', osc2__level=0.0, noise__level=0.04, mode='legato', glide=0.0,
                   filter__type='lp12', cutoff=9000, filter__env=0.0, amp__attack=0.01, amp__decay=0.2,
                   amp__sustain=0.9, amp__release=0.08,
                   mods=[vamod.lfo('sine', hz=6.0, id='vib') >> ('pitch', 25)], level=-10.0)


# ------------------------------------------------------------------ the themes (all original)
# the 99-Euro sting: the SAME three notes every time (short-short-long), over an F 6/9 sparkle
STING99 = [(0.0, 0.11, 'F5', 0.86), (0.13, 0.11, 'C6', 0.94), (0.28, 0.62, 'A5', 1.06)]
STING99_PAD = ('F4', 'A4', 'D5', 'G5')
# the Zone theme: a lonely 3/4 tune, D Dorian (B natural); in H it comes back warm in D major (F# / C#)
ZONE = 'A4/4 D5/4 E5/4 | F5/4. G5/8 E5/4 | D5/4 B4/4 C5/4 | A4/2. | G4/4 A4/4 C5/4 | B4/4. D5/8 F5/4 | ' \
       'E5/4 C5/4 B4/8 C5/8 | D5/2.'
ZONE_MAJ = 'A4/4 D5/4 E5/4 | F#5/4. G5/8 E5/4 | D5/4 B4/4 C#5/4 | A4/2. | G4/4 A4/4 C#5/4 | B4/4. D5/8 F#5/4 | ' \
           'E5/4 C#5/4 B4/8 C#5/8 | D5/2.'
ZONE_CHORDS_DOR = [('Dm', ch('D3', 'F3', 'A3')), ('C', ch('C3', 'E3', 'G3')), ('G', ch('B2', 'D3', 'G3')),
                   ('Am', ch('A2', 'C3', 'E3')), ('C', ch('C3', 'E3', 'G3')), ('G', ch('B2', 'D3', 'G3')),
                   ('Am', ch('A2', 'C3', 'E3')), ('Dm', ch('D3', 'F3', 'A3'))]
ZONE_CHORDS_MAJ = [('D', ch('D3', 'F#3', 'A3')), ('A', ch('C#3', 'E3', 'A3')), ('G', ch('B2', 'D3', 'G3')),
                   ('D', ch('A2', 'D3', 'F#3')), ('A', ch('C#3', 'E3', 'A3')), ('G', ch('B2', 'D3', 'G3')),
                   ('A7', ch('C#3', 'G3', 'A3')), ('D', ch('D3', 'F#3', 'A3'))]
# the Konrad hook (series intro, songs/grandpa-konrad-intro), D minor
KONRAD = 'D5/4 F5/8 E5/8 D5/8 A5/4.'
# Oma's stomp (ep3 colour): low tuba + timpani, (beat, dur, semitones over the root, timpani?)
OMA = [(0.0, 0.5, 0, True), (1.0, 0.4, -5, False), (1.5, 0.35, -4, False), (2.0, 0.9, 0, True)]
# the party hook (Ballermann style, original), A major: 4 bars
PARTY = 'E5/8 E5/8 A5/4 G#5/8 F#5/8 E5/4 | F#5/8 D5/8 F#5/8 A5/8 G#5/2 | E5/8 E5/8 B5/4 A5/8 G#5/8 F#5/4 | ' \
        'E5/8 C#5/8 D5/8 B4/8 A4/2'


def _dump_anchors():
    """out/anchors_build.json: the anchors this build was made with (check_anchors.py compares them)."""
    try:
        out = _Path(__file__).resolve().parent / 'out'
        out.mkdir(exist_ok=True)
        (out / 'anchors_build.json').write_text(_json.dumps(
            {'timing': TIMING_SOURCE, 'total': TOTAL, 'hits': HITS, 'gates': GATES, 'dry': DRY,
             'plan': [[p[0], p[1], p[2], p[3], list(p[4])] for p in PLAN]}, indent=1), encoding='utf-8')
    except Exception:
        pass


def build() -> Song:
    _dump_anchors()
    s = Song('Strahlende Ferien (Score)', tempo=bpm_of(PLAN[0][1], PLAN[0][2], PLAN[0][3], PLAN[0][5]),
             key='Bb major', seed=5, tail=0.0)
    sec = {}
    for name, a, b, bars, meter, bpb in PLAN:
        sec[name] = s.section(name, bars=bars, meter=None if meter == (4, 4) else meter)
    for name, a, b, bars, meter, bpb in PLAN[1:]:
        s.set_tempo(sec[name], bpm_of(a, b, bars, bpb))
    g = sec.get
    T_SEC = {name: (a, b) for name, a, b, *_ in PLAN}
    BPB = {name: bpb for name, a, b, bars, meter, bpb in PLAN}

    def at(t):
        """The beat at an absolute picture time (seconds)."""
        return s.beat_at(max(0.0, min(t, T_END)))

    def talking(t, pad=0.06):
        return any(a - pad <= t <= a + d + pad for a, d in SPANS.values())

    stops = []                                       # (t0, t1): stop-time windows (gates, dry lines)
    lanes = {}                                       # (track id, target) -> [track, points]: merged at the end

    def auto(track, target, pts):
        lanes.setdefault((track.id, target), [track, []])[1].extend(pts)

    def stopped(t):
        return any(a <= t < b for a, b in stops)

    def pl(track, clip, pos, vel=1.0, until=None, after=None):
        """Play a groove clip, dropping the notes in a stop window (and before `after` / from `until` s)."""
        keep = []
        for n in clip:
            t = s.seconds(pos + n.start)
            if stopped(t) or (until is not None and t >= until) or (after is not None and t < after):
                continue
            keep.append((n.start, n.dur, n.pitch, max(1, min(127, int(n.vel * vel)))))
        if keep:
            track.play(Clip(keep, length=max(k[0] + k[1] for k in keep) + 0.01), pos)

    def ps(track, ev, t0, vel=1.0):
        """Events (offset s, dur s, pitch name|midi, vel) placed in SECONDS from t0 - independent of the tempo."""
        b0 = at(t0)
        out = []
        for t, d, p, v in ev:
            a, e = at(t0 + t), at(t0 + t + d)
            out.append((a - b0, max(0.02, e - a), m(p), max(1, min(127, int(v * vel)))))
        if out:
            track.play(Clip(out, length=max(o[0] + o[1] for o in out) + 0.01), b0)

    def split_lead(clip, pos, loud, soft=None, under=0.6, until=None, after=None):
        """Ducking-friendly lead: notes in the dialogue gaps play on `loud`, notes under a line on `soft` (or
        `loud`) at `under` x velocity; notes in a stop window, before `after` or from `until` (s) are left out."""
        lo, so = [], []
        for n in clip:
            t = s.seconds(pos + n.start)
            if stopped(t) or (until is not None and t >= until) or (after is not None and t < after):
                continue
            if talking(t):
                so.append((n.start, n.dur, n.pitch, max(1, int(n.vel * under))))
            else:
                lo.append((n.start, n.dur, n.pitch, n.vel))
        if lo:
            loud.play(Clip(lo, length=clip.length), pos)
        if so:
            (soft or loud).play(Clip(so, length=clip.length), pos)

    def bars(name):
        x = g(name)
        return [(b, mbar(x, b + 1)) for b in range(int(x.bars))] if x else []

    def sec_end(name):
        return T_SEC.get(name, (0, T_END))[1]

    for b0, b1 in GATES + DRY:
        stops.append((b0 - 0.05, b1 + 0.06))
    for th in (T_PROST, T_SOUR, T_BACKFIRE, T_GLOWUP2):    # a breath before these hits, so they land clean
        stops.append((th - 0.18, th - 0.005))

    # ------------------------------------------------------------------ buses (the stems) and returns
    returns = [s.hall(), s.plate(), s.echo()]
    STEMS = ('lead', 'bass', 'drums', 'ticks', 'organ_kitsch', 'orchestra', 'stings')
    stem_bus = {sid: s.bus(sid, [fx.filter(mode='lp', cutoff=20000)]) for sid in STEMS}     # the lp: the "inside the fish" muffle (G4)
    s.master.use('master/synthwave')
    s.master.automate('fx.limiter.gain', [(0, 9.0)])     # the earlier scores sit around -18 LUFS

    def T(id_, sound, out, **kw):
        return s.track(id_, sound, output=out, **kw)

    # lead
    vibes = T('vibes', inst.sf2('Vibraphone'), 'lead', gain_db=-6, pan=0.2, sends={'hall': -8, 'echo': -18})
    mbox = T('musicbox', inst.sf2('Music Box', {'tune': -14}), 'lead', gain_db=-5, pan=0.12, sends={'hall': -3})
    ther = T('theremin', theremin(), 'lead', gain_db=-7, pan=0.1, sends={'hall': -5, 'echo': -12},
             fx=[fx.chorus(mode='II', mix=0.4)])
    whistle = T('whistle', inst.sf2('Whistle'), 'lead', gain_db=-10, pan=0.25, sends={'hall': -3, 'echo': -9})
    sax = T('sax', inst.sf2('Tenor Sax'), 'lead', gain_db=-6, pan=0.15, sends={'hall': -8, 'plate': -12})
    clar = T('clarinet', inst.sf2('Clarinet'), 'lead', gain_db=-5, pan=0.1, sends={'hall': -5})
    tpt = T('trumpet', inst.sf2('Trumpet'), 'lead', gain_db=-6, pan=0.3, sends={'hall': -9},
            fx=[fx.eq({'peak2.freq': 2400, 'peak2.gain': -3.0, 'peak2.q': 0.7})])
    surf = T('surf', inst.sf2('Clean Guitar'), 'lead', gain_db=-6, pan=-0.3, sends={'hall': -2, 'echo': -10},
             fx=[fx.tremolo(rate=6.5, depth=0.35), fx.chorus(mode='I', mix=0.4)])
    # bass
    tuba = T('tuba', inst.sf2('Tuba'), 'bass', gain_db=-2, pan=-0.15, sends={'hall': -11})
    obass = T('organ_bass', inst.sf2('Tonewheel Organ'), 'bass', gain_db=-9, fx=[fx.filter(mode='lp', cutoff=900)])
    fbass = T('finger_bass', inst.sf2('Finger Bass'), 'bass', gain_db=-5)
    dbass = T('upright', inst.sf2('Acoustic Bass'), 'bass', gain_db=-4, sends={'hall': -14})
    sbass = T('synth_bass', inst.sf2('Synth Bass 1'), 'bass', gain_db=-9, fx=[fx.filter(mode='lp', cutoff=1800)])
    cello = T('cello', inst.sf2('Cello'), 'bass', gain_db=-10, pan=-0.2, sends={'hall': -6})
    # drums
    kit = T('kit', inst.sf2('Standard 1 Kit'), 'drums', gain_db=-10, sends={'hall': -12},
            fx=[fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 0.7})]).humanize(3, 5)
    rhythm = T('autorhythm', inst.sf2('Standard 1 Kit'), 'drums', gain_db=-15, pan=0.1,
               fx=[fx.filter(mode='lp', cutoff=6000), fx.eq({'low.freq': 120, 'low.gain': -4})])
    brush = T('brushes', inst.sf2('Brush Kit'), 'drums', gain_db=-11, sends={'hall': -14}).humanize(3, 5)
    block = T('woodblock', inst.sf2('Wood Block'), 'drums', gain_db=-13, pan=0.35, sends={'hall': -11})
    crink = T('foil', crinkle_voice(), 'drums', gain_db=-10, pan=-0.3)
    # ticks (the counter)
    geig = T('geiger', geiger_voice(), 'ticks', gain_db=7, pan=-0.05, sends={'plate': -24})
    # organ_kitsch
    horgan = T('home_organ', inst.sf2('Percussive Organ'), 'organ_kitsch', gain_db=-10, pan=-0.2, sends={'hall': -12},
               fx=[fx.eq({'low.freq': 220, 'low.gain': -10}), fx.tremolo(rate=6.2, depth=0.18, stereo=90)])
    acc = T('accordion', inst.sf2('Accordion'), 'organ_kitsch', gain_db=-9, pan=-0.25, sends={'hall': -9},
            fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.6})])
    keys = T('rhodes', 'gm/epiano', 'organ_kitsch', gain_db=-9, pan=-0.2, fx=[fx.eq({'low.freq': 160, 'low.gain': -8})])
    muzak = T('muzak_keys', 'gm/epiano', 'organ_kitsch', gain_db=-10, pan=0.15,
              pre=[fx.tape(speed='cassette', wow=0.9, flutter=0.5, hiss=0.3)], fx=[fx.filter(mode='lp', cutoff=3500)])
    muzvib = T('muzak_vibes', inst.sf2('Vibraphone'), 'organ_kitsch', gain_db=-9, pan=-0.15, sends={'hall': -10},
               fx=[fx.tape(speed='cassette', wow=1.0, flutter=0.6), fx.filter(mode='lp', cutoff=3000)])
    # orchestra
    strings = T('strings', inst.sf2('Slow Strings'), 'orchestra', gain_db=-8, sends={'hall': -3},
                fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7}), fx.chorus(mode='II', mix=0.4)])
    trem = T('tremolo', inst.sf2('Tremolo Strings'), 'orchestra', gain_db=-8, pan=-0.1, sends={'hall': -5},
             fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    pizz = T('pizz', inst.sf2('Pizzicato Strings'), 'orchestra', gain_db=-5, pan=-0.15, sends={'hall': -7})
    harp = T('harp', inst.sf2('Orchestral Harp'), 'orchestra', gain_db=-6, pan=-0.35, sends={'hall': -3})
    cele = T('celesta', inst.sf2('Celeste'), 'orchestra', gain_db=-8, pan=0.25, sends={'hall': -2})
    glock = T('glock', inst.sf2('Glockenspiel'), 'orchestra', gain_db=-12, pan=0.3, sends={'hall': -4})
    brass = T('brass', inst.sf2('Brass Section'), 'orchestra', gain_db=-9, pan=0.05, sends={'hall': -5},
              fx=[fx.eq({'peak2.freq': 1800, 'peak2.gain': -3.0, 'peak2.q': 0.7})])
    bone = T('trombone', inst.sf2('Trombone'), 'orchestra', gain_db=-5, pan=-0.35, sends={'hall': -7})
    horns = T('horns', inst.sf2('French Horns'), 'orchestra', gain_db=-7, pan=-0.25, sends={'hall': -4})
    timp = T('timpani', inst.sf2('Timpani'), 'orchestra', gain_db=-6, sends={'hall': -4})
    choir = T('choir', inst.sf2('Concert Choir'), 'orchestra', gain_db=-9, sends={'hall': -1},
              fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    corgan = T('church_organ', inst.sf2('Pipe Organ'), 'orchestra', gain_db=-12, pan=-0.2, sends={'hall': -3},
               fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -5.0, 'peak2.q': 0.6})])
    bsn = T('bass_clarinet', inst.sf2('Clarinet', {'transpose': -12}), 'orchestra', gain_db=-5, pan=0.1, sends={'hall': -8})
    gtr = T('rock_guitar', inst.sf2('Distortion Guitar'), 'orchestra', gain_db=-14, pan=-0.3, sends={'hall': -12},
            fx=[fx.eq({'peak2.freq': 2000, 'peak2.gain': -4.0, 'peak2.q': 0.7, 'low.freq': 120, 'low.gain': -6})])
    # stings
    ohit = T('ohit', 'gm/orchestra_hit', 'stings', gain_db=-10, sends={'hall': -7})
    boom = T('boom', 'synthwave/impact', 'stings', gain_db=-12)
    revcym = T('revcym', inst.sf2('Reverse Cymbal'), 'stings', gain_db=-5, sends={'hall': -7})
    stab = T('stab99', stab_voice(), 'stings', gain_db=-4, pan=0.05, sends={'plate': -10, 'echo': -16})
    sbrass = T('synth_brass', inst.sf2('Synth Brass 1'), 'stings', gain_db=-9, pan=-0.05, sends={'plate': -12})
    glow = T('glow', glow_voice(), 'stings', gain_db=-6, pan=0.0, sends={'hall': -4},
             fx=[fx.tremolo(rate=11, depth=0.35, stereo=120)])
    sweep = T('sweep', sweep_noise(), 'stings', gain_db=-10, sends={'hall': -8})
    roar = T('roar', roar_voice(), 'stings', gain_db=-8, sends={'hall': -10})
    hum = T('hum', hum_voice(), 'stings', gain_db=-6)
    slide = T('slide_whistle', slide_voice(), 'stings', gain_db=-6, pan=0.2, sends={'hall': -9})

    party_tracks = []                                # the party groove (the tape-stop in F8 bends them all)

    # ------------------------------------------------------------------ shared figures
    def hit(t, pitches=(38, 50, 57, 62), vel=112, ring=1.2, crash=True, stab_=True):
        """The episode hit at picture time t: orchestra hit + impact + timpani (+ brass, crash)."""
        ps(ohit, [(0, ring, p, vel) for p in pitches], t)
        ps(boom, [(0, max(1.5, ring), 38, min(127, vel + 4))], t)
        ps(timp, [(0, 1.0, pitches[0] + 12 if pitches[0] < 40 else pitches[0], vel)], t)
        if stab_:
            ps(brass, [(0, min(ring, 0.8), p, vel - 12) for p in pitches[1:]], t)
        if crash:
            ps(kit, [(0, 1.0, 49, vel - 10), (0, 0.3, 36, vel - 6)], t)

    def sting99(t, slow=1.0, sour=False, vel=112):
        """The shopping-channel sting: the same three notes every time (sour = slowed, sagging, out of tune)."""
        ev = [(a * slow, d * slow, p, min(127, int(vel * w))) for a, d, p, w in STING99]
        ps(stab, ev, t)
        ps(sbrass, [(a, d, p, vel - 14) for a, d, p, _ in ev], t)
        last = STING99[-1][0] * slow
        ps(stab, [(last, 0.62 * slow, p, vel - 26) for p in STING99_PAD], t)
        ps(glock, [(last, 0.5, p, 70 if sour else 92) for p in ('A6', 'D7')], t)
        if not sour:
            ps(glock, [(last + 0.05 + i * 0.045, 0.2, p, 60) for i, p in enumerate(('C7', 'F7', 'A7', 'C8'))], t)
            ps(kit, [(last, 0.6, 55, 70)], t)                      # splash
        else:                                                     # the sag: the tail bends down a whole tone
            auto(stab, 'instrument.pitchbend', [(at(t) - 0.001, 0.0, 'step'), (at(t + last), 0.0),
                                                (at(t + last + 0.6 * slow), -2.5, 'smooth'),
                                                (at(t + last + 0.65 * slow + 0.15), 0.0, 'step')])
            ps(bone, [(last, 0.6 * slow, 'A2', 80)], t)

    def glow_shimmer(t, dur, root='D6', vel=80, swell=True):
        """The glow colour: a buzzing sour shimmer (not a melody) - two notes a 4th apart + a high harmonic."""
        r = m(root)
        ps(glow, [(0, dur, r, vel), (0.05, dur - 0.05, r + 5, vel - 12), (0.1, dur - 0.1, r + 12, vel - 22)], t)
        if swell:
            ps(cele, [(0.02 + i * 0.05, 0.3, r + p, 48) for i, p in enumerate((0, 5, 12, 17))], t)

    def gross_sting(t, dur, root='Bb1'):
        """The gross-up: a wet brass blat sagging down + a held horror chord."""
        r = m(root)
        ps(bone, [(0, 0.45, r, 118), (0.5, max(0.6, dur - 0.9), r - 1, 106)], t)
        auto(bone, 'instrument.pitchbend', [(at(t) - 0.001, 0.0, 'step'), (at(t + 0.5), 0.0),
                                            (at(t + dur - 0.3), -2.0, 'smooth'), (at(t + dur - 0.2), 0.0, 'step')])
        ps(trem, [(0, dur, p, 72) for p in (r + 26, r + 32, r + 37, r + 43)], t)
        ps(corgan, [(0, dur, p, 66) for p in (r + 26, r + 27, r + 33)], t)
        ps(ohit, [(0, 0.6, p, 100) for p in (r + 12, r + 18, r + 24)], t)
        ps(timp, [(0, 0.8, r + 24 if r + 24 > 40 else 41, 104)], t)

    def oma_stomp(t, root='C2', vel=104, spb=0.5):
        """Oma's motif: the tuba + timpani stomp (spb = seconds per beat)."""
        r = m(root)
        ps(tuba, [(b * spb, d * spb, r + st, vel - (0 if tp else 14)) for b, d, st, tp in OMA], t)
        ps(timp, [(b * spb, 0.6, r + 12 if r + 12 >= 41 else 41, vel) for b, d, st, tp in OMA if tp], t)

    def ticks(name, per_beat, vel=46, until=None, after=None, accent=10, jitter=True):
        """The Geiger-tick groove locked to the grid: per_beat ticks per quarter beat (0 = one per bar)."""
        x = g(name)
        if not x:
            return
        bpb = BPB[name]
        for b, pos in bars(name):
            if per_beat == 0:
                ev = [(0.0, 0.03, 84, vel + accent)]
            else:
                n = int(round(bpb * per_beat))
                step = 1.0 / per_beat
                ev = [(k * step, min(0.03, step * 0.5), 84 + (k * 7 + b) % 5,
                       max(8, vel + (accent if k % int(max(1, per_beat)) == 0 else 0) -
                           ((k * 37 + b * 11) % 9 if jitter else 0))) for k in range(n)]
            pl(geig, Clip(ev, length=bpb), pos, until=until, after=after)

    def zone_theme(start_pos, track, src=ZONE, vel=72, transpose=0, under=0.6, until=None):
        split_lead(notes(f'vel={vel} meter=3/4 {src}', transpose=transpose).arch(4, 0.45, beats_per_bar=3),
                   start_pos, track, None, under=under, until=until)

    # ================================================================== 1 kaffeefahrt: home organ, Bb major
    KPROG = [('Bb', 'Bb1', ch('D4', 'F4', 'Bb4')), ('Gm', 'G1', ch('D4', 'G4', 'Bb4')),
             ('Eb', 'Eb2', ch('Eb4', 'G4', 'Bb4')), ('F', 'F1', ch('C4', 'F4', 'A4'))]

    def organ_bars(name, thin=False, vel=1.0, until=None, after=None, rhythm_on=True):
        """The Heimorgel auto-rhythm "Beat 2": pedal bass on 1 and 3, the chord on 2 and 4 (+ the and of 4), the
        drum box (rim, shaker, a soft kick) - thinned to a held organ pad under the dialogue."""
        for b, pos in bars(name):
            sym, r, v = KPROG[b % 4]
            r = m(r)
            under = talking(s.seconds(pos + 0.2)) or thin
            if under:
                pl(horgan, Clip([(0, 3.9, p, int(52 * vel)) for p in v], length=4), pos, until=until, after=after)
                pl(obass, Clip([(0, 1.8, r + 12, int(54 * vel)), (2, 1.8, r + 19, int(48 * vel))], length=4), pos,
                   until=until, after=after)
            else:
                pl(horgan, Clip([(t, 0.35, p, int(66 * vel)) for t in (1, 3, 3.5) for p in v], length=4), pos,
                   until=until, after=after)
                pl(obass, Clip([(0, 0.8, r + 12, int(76 * vel)), (2, 0.8, r + 19, int(68 * vel))], length=4), pos,
                   until=until, after=after)
                if rhythm_on:
                    pl(rhythm, drums({'kick': 'x.......x.......', 'rim': '....x.......x...', 70: 'x.xxx.xxx.xxx.xx'},
                                     vel=58 * vel), pos, until=until, after=after)

    organ_bars('kaffee')
    # the barrier creaks: a suspended-cymbal swell up to the backfire, a tiny bump on the bang
    ps(revcym, [(0, max(0.5, T_BACKFIRE - T_CREAK), 60, 80)], T_CREAK)
    ps(kit, [(0, 0.4, 41, 96), (0, 0.3, 36, 104), (0, 0.6, 55, 80)], T_BACKFIRE)
    ps(ohit, [(0, 0.3, p, 70) for p in (46, 53, 58)], T_BACKFIRE)
    # the organ glissando under "Herzlich willkommen" (a Bb major run up into the downbeat of the line)
    run = ['Bb3', 'C4', 'D4', 'Eb4', 'F4', 'G4', 'A4', 'Bb4', 'C5', 'D5', 'F5', 'Bb5']
    ps(horgan, [(i * 0.03, 0.12 if i < len(run) - 1 else 0.9, p, 60 + i * 3) for i, p in enumerate(run)],
       T_WELCOME - 0.36)
    ps(vibes, [(0, 0.9, p, 70) for p in ('D5', 'F5', 'Bb5')], T_WELCOME - 0.03)
    ticks('kaffee', 0, vel=52)
    # the bus banter: organ pad under the lines, the auto-rhythm + vibes only in the gaps
    for nm in ('bus', 'foil', 'finn', 'pitch'):
        organ_bars(nm, vel=0.95)
        ticks(nm, 0, vel=50 if nm != 'pitch' else 56)
    vline = notes('vel=82 F5/8 D5/8 Bb4/8 D5/8 F5/4 G5/8 F5/8 | Eb5/4. D5/8 C5/2 | D5/8 Eb5/8 F5/8 Bb5/8 A5/4 G5/8 '
                  'F5/8 | Eb5/2 D5/4 r/4').arch(4, 0.5)
    for nm in ('kaffee', 'bus', 'foil', 'finn'):
        for b, pos in bars(nm)[::4]:
            split_lead(vline, pos, vibes, None, under=0.0)       # under the lines: left out (the pad only)
    # Mandy's selfie: a tiny glow-up sparkle
    glow_shimmer(T_SELFIE, 0.9, 'F6', vel=62)
    ps(glock, [(i * 0.05, 0.25, p, 66) for i, p in enumerate(('F6', 'A6', 'C7', 'F7'))], T_SELFIE)
    # A4 Konrad's foil: the crinkle doubles the hi-hat (16ths, accents on the 8ths)
    if g('foil'):
        for b, pos in bars('foil'):
            pl(crink, Clip([(k * 0.25, 0.05, 88 + (k * 5) % 9, 70 if k % 2 == 0 else 46 + (k * 13) % 18)
                            for k in range(16)], length=4), pos)
    # A6 the sales pitch: the 99-Euro sting, then Oma's cash register
    sting99(T_EURO1)
    ps(glock, [(0, 0.5, 'E7', 96), (0.02, 0.6, 'B6', 80)], T_CASH)            # ka-
    ps(kit, [(0.0, 0.2, 75, 90), (0.12, 0.3, 54, 84)], T_CASH)                   # -tsching (claves + tambourine)
    ps(rhythm, [(0.12, 0.25, 81, 90)], T_CASH)                                   # the drawer bell

    # ================================================================== 3 the park: D Dorian 3/4, the Zone theme
    if g('park'):
        for b, pos in bars('park'):
            sym, v = ZONE_CHORDS_DOR[b % 8]
            pl(strings, Clip([(0, 2.9, p, 34) for p in v], length=3), pos)
            pl(cello, Clip([(0, 2.9, v[0] - 12, 40)], length=3), pos)
            if b % 2 == 0:                                         # the gondola creak as percussion (a guiro)
                pl(kit, Clip([(0, 0.6, 74, 40)], length=3), pos)
        ticks('park', 1, vel=38)
        zone_theme(mbar(g('park'), 2), mbox, vel=70, under=0.55)
    if g('serious'):
        for b, pos in bars('serious'):
            sym, v = ZONE_CHORDS_DOR[(b + 4) % 8]
            pl(strings, Clip([(0, 2.9, p, 30) for p in v], length=3), pos, until=T_DRY16)
            pl(harp, Clip([(0, 0.8, v[0], 34), (1, 0.6, v[1] + 12, 30), (2, 0.6, v[2] + 12, 30)], length=3), pos,
               until=T_DRY16)
        ticks('serious', 1, vel=34, until=T_DRY16)
        split_lead(notes('vel=60 meter=3/4 G4/4 A4/4 C5/4 | B4/4. D5/8 F5/4 | E5/4 C5/4 B4/8 C5/8 | D5/2.')
                   .arch(4, 0.4, beats_per_bar=3), mbar(g('serious'), 1), mbox, None, under=0.5, until=T_DRY16)
    # B3: the cheesy organ chord as if nothing happened, the selfie pop-bounce starts
    ps(horgan, [(0, 0.9, p, 96) for p in ('F4', 'A4', 'C5', 'F5')], T_SELFIE2)
    ps(obass, [(0, 0.9, 'F2', 90)], T_SELFIE2)
    ps(horgan, [(i * 0.025, 0.1, p, 70) for i, p in enumerate(('C5', 'D5', 'E5', 'F5', 'G5', 'A5', 'C6'))],
       T_SELFIE2 - 0.2)

    # ================================================================== 4 tourist trap: selfie pop-bounce, F major
    SPROG = [('F', 'F1', ch('A4', 'C5', 'F5')), ('Dm', 'D2', ch('A4', 'D5', 'F5')),
             ('Bb', 'Bb1', ch('Bb4', 'D5', 'F5')), ('C', 'C2', ch('G4', 'C5', 'E5'))]
    for nm in ('selfie', 'ticks8', 'souvenir'):
        for b, pos in bars(nm):
            sym, r, v = SPROG[b % 4]
            r = m(r)
            under = talking(s.seconds(pos + 0.2))
            pl(fbass, Clip([(0, 0.4, r + 12, 92), (0.75, 0.2, r + 24, 70), (1.5, 0.4, r + 12, 84), (2.5, 0.3, r + 19, 80),
                            (3.0, 0.4, r + 12, 86), (3.5, 0.3, r + 24, 70)], length=4), pos, vel=0.8 if under else 1.0)
            pl(kit, drums({'kick': 'x.....x...x.....', 'clap': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                          vel=46 if under else 70), pos)
            if not under:
                pl(glock, Clip([(t, 0.2, p, 52) for t in (0.5, 2.5) for p in v[1:]], length=4), pos)
                pl(keys, Clip([(t, 0.3, p - 12, 56) for t in (1, 3) for p in v], length=4), pos)
        ticks(nm, 1 if nm == 'selfie' else 2, vel=40)
        hook = notes('vel=90 C5/8 F5/8 A5/8 C6/4 A5/8 G5/8 F5/8 | G5/4 E5/8 C5/8 D5/2 | Bb4/8 D5/8 F5/8 Bb5/4 A5/8 '
                     'G5/8 F5/8 | E5/4 G5/8 E5/8 C5/2').arch(4, 0.5)
        for b, pos in bars(nm)[::4]:
            split_lead(hook, pos, vibes, glock, under=0.35, until=sec_end(nm))
    # "DU nicht.": the ear-whistle fweet (a slide whistle up)
    ps(slide, [(0, 0.35, 'C6', 90)], T_FWEET)
    auto(slide, 'instrument.pitchbend', [(at(T_FWEET) - 0.01, -12.0, 'step'), (at(T_FWEET + 0.3), 7.0, 'smooth'),
                                         (at(T_FWEET + 0.4), 0.0, 'step')])
    # the souvenir pitch: the moustache glows, the 99-Euro sting again
    glow_shimmer(T_MOUSTACHE, 1.6, 'C6', vel=76)
    sting99(T_EURO2)

    # ================================================================== 5 supermarket: decayed muzak, Eb major
    MPROG = [('Eb', 'Eb2', ch('G3', 'Bb3', 'D4')), ('Cm', 'C2', ch('G3', 'Bb3', 'Eb4')),
             ('Fm', 'F2', ch('Ab3', 'C4', 'Eb4')), ('Bb', 'Bb1', ch('Ab3', 'D4', 'F4'))]
    if g('market'):
        for b, pos in bars('market'):
            sym, r, v = MPROG[b % 4]
            r = m(r)
            under = talking(s.seconds(pos + 0.2))
            pl(muzak, Clip([(0, 1.4, p, 50) for p in v] + [(2.5, 1.2, p, 42) for p in v], length=4), pos)
            pl(dbass, Clip([(0, 0.9, r, 70), (1.5, 0.4, r + 7, 56), (2, 0.9, r + 7, 62), (3.5, 0.4, r, 54)], length=4), pos)
            pl(brush, drums({42: 'x.xx.xx.x.xx.xx.', 37: '...x.....x......'}, vel=30 if under else 40), pos)
            if b % 4 == 2 and b > 0:                              # Oma's tuba motif sneaking in, under the bed
                oma_stomp(s.seconds(pos), root='Eb2', vel=62, spb=60 / 92)
        ticks('market', 2, vel=36)
        split_lead(notes('vel=74 G5/4. F5/8 Eb5/4 Bb4/4 | C5/2 r/4 D5/8 Eb5/8 | F5/4. Eb5/8 D5/4 Ab4/4 | Bb4/2 r/2 | '
                         'G5/4. Ab5/8 Bb5/4 G5/4 | F5/2 Eb5/4 D5/4 | C5/4 D5/4 Eb5/4 F5/4 | Eb5/1').arch(4, 0.45),
                   mbar(g('market'), 1), muzvib, None, under=0.5, until=T_CHOMP)
    # C2: the chomp - the music cuts, then the gross-up sting on the bite (2.6 s)
    gross_sting(T_CHOMP, min(D_CHOMP, max(1.0, T_GLOW - T_CHOMP)), root='Bb1')
    # C3: the counter shrieks, Oma glows: the first glow shimmer; "STARK": the stomp; Konrad's harp swoon
    if g('glow'):
        glow_shimmer(T_OMAGLOW, 3.0, 'D6', vel=78)
        for b, pos in bars('glow'):
            sym, r, v = MPROG[b % 4]
            pl(trem, Clip([(0, 3.9, p, 36) for p in v], length=4), pos, until=T_STARK - 0.1)
            pl(tuba, Clip([(0, 1.5, m(r), 46)], length=4), pos, until=T_STARK - 0.1)
        ticks('glow', 2, vel=42)
        oma_stomp(T_STARK, root='C2', vel=118, spb=0.42)
        hit(T_STARK, pitches=(36, 48, 55, 60, 63), vel=108, ring=0.8, crash=False)
        glow_shimmer(T_STARK + 0.1, 2.2, 'G6', vel=70, swell=False)
        ps(harp, [(i * 0.04, 1.4, p, 60 + i) for i, p in enumerate(ch('Eb4', 'G4', 'Bb4', 'D5', 'Eb5', 'G5', 'Bb5', 'D6',
                                                                       'Eb6', 'G6'))], T_SWOON)
        ps(strings, [(0.3, 2.6, p, 46) for p in ('Eb4', 'G4', 'Bb4', 'D5')], T_SWOON)
        ps(vibes, [(0.4, 1.6, p, 58) for p in ('G5', 'Bb5', 'D6')], T_SWOON)

    # ================================================================== 6 the pool: surf rock, A minor
    if g('pool'):
        PPROG = [('Am', 'A1'), ('G', 'G1'), ('F', 'F1'), ('E', 'E1')]
        for b, pos in bars('pool'):
            sym, r = PPROG[b % 4]
            r = m(r)
            under = talking(s.seconds(pos + 0.2))
            pl(fbass, Clip([(0, 0.4, r + 12, 96), (0.5, 0.3, r + 12, 70), (1, 0.4, r + 19, 86), (1.5, 0.3, r + 12, 70),
                            (2, 0.4, r + 22 if sym == 'Am' else r + 24, 86), (3, 0.4, r + 19, 84), (3.5, 0.3, r + 12, 70)],
                           length=4), pos, vel=0.85 if under else 1.0, until=T_FALL)
            pat = {'kick': 'x..x..x.x..x..x.', 'snare': '....x.......x...', 'ride': 'x.x.x.x.x.x.x.x.'}
            if b % 4 == 3:
                pat['tom_lo'] = '............xxxx'
            pl(kit, drums(pat, vel=48 if under else 72), pos, until=T_FALL)
        ticks('pool', 2, vel=40, until=T_FALL)
        riff = notes('vel=96 A4/16 A4/16 A4/16 A4/16 C5/8 E5/8 G5/8 E5/8 D5/8 C5/8 | B4/16 B4/16 B4/16 B4/16 D5/8 G5/8 '
                     'B5/4 A5/8 G5/8 | A5/16 A5/16 A5/16 A5/16 F5/8 C5/8 A4/8 C5/8 F5/8 A5/8 | G#5/4. E5/8 B4/2').arch(4, 0.5)
        for b, pos in bars('pool')[::4]:
            split_lead(riff, pos, surf, None, under=0.45, until=T_FALL)
        # Ronny climbs the tower: a rising chromatic tremolo from the ladder to the fall
        t_climb = SFX('ladder clank 1', T_POOL + 0.3)
        n = max(4, int((T_FALL - t_climb) / 0.5))
        step = (T_FALL - t_climb) / n
        ps(trem, [(k * step, step * 0.98, m('A3') + k, 44 + int(40 * k / n)) for k in range(n)], t_climb)
        ps(trem, [(k * step, step * 0.98, m('E4') + k, 40 + int(36 * k / n)) for k in range(n)], t_climb)
    # the cannonball: the whistle falls, the goo SPLAT, the music stops (the counter's line dry)
    dfall = max(0.4, T_SPLAT - T_FALL - 0.05)
    ps(slide, [(0, dfall, 'C7', 96)], T_FALL)
    auto(slide, 'instrument.pitchbend', [(at(T_FALL) - 0.01, 0.0, 'step'), (at(T_FALL + dfall), -19.0, 'smooth'),
                                         (at(T_FALL + dfall + 0.05), 0.0, 'step')])
    hit(T_SPLAT, pitches=(33, 45, 52, 57, 60), vel=118, ring=1.1, stab_=False)
    ps(tuba, [(0, 0.6, 'F1', 118), (0.0, 0.6, 'C2', 90)], T_SPLAT)
    auto(tuba, 'instrument.pitchbend', [(at(T_SPLAT) - 0.001, 0.0, 'step'), (at(T_SPLAT + 0.6), -3.0, 'smooth'),
                                        (at(T_SPLAT + 0.75), 0.0, 'step')])
    # C6: Detlef's sleazy lounge (brushes, upright, Rhodes), the sax lick on his whisper
    if g('lounge'):
        LPROG = [('Dm7', 'D2', ch('C4', 'F4', 'A4')), ('G7', 'G1', ch('B3', 'F4', 'A4')),
                 ('Cmaj7', 'C2', ch('B3', 'E4', 'G4')), ('A7', 'A1', ch('C#4', 'G4', 'Bb4'))]
        t_in = E(32) + 0.4
        for b, pos in bars('lounge'):
            sym, r, v = LPROG[b % 4]
            r = m(r)
            pl(dbass, Clip([(0, 0.9, r, 70), (1, 0.9, r + 7, 60), (2, 0.9, r + 12, 64), (3, 0.9, r + 10, 58)], length=4),
               pos, after=t_in)
            pl(keys, Clip([(0.5, 1.2, p, 44) for p in v] + [(2.5, 1.2, p, 40) for p in v], length=4), pos, after=t_in)
            pl(brush, drums({42: 'x..x..x.x..x..x.', 37: '....x.......x...'}, vel=30), pos, after=t_in)
        ticks('lounge', 2, vel=34, after=t_in)
        ps(sax, [(0, 0.18, 'A4', 84), (0.2, 0.14, 'C5', 80), (0.36, 0.5, 'E5', 92), (0.9, 0.12, 'D5', 72),
                 (1.04, 0.5, 'C#5', 86)], T_SAX)
        auto(sax, 'instrument.pitchbend', [(at(T_SAX + 0.36) - 0.001, -1.0, 'step'), (at(T_SAX + 0.5), 0.0, 'smooth')])

    # ================================================================== 7 mutants: sneaky pizz, E minor
    if g('mutants'):
        UPROG = [('Em', 'E2', ch('E3', 'G3', 'B3')), ('Em', 'E2', ch('E3', 'G3', 'B3')),
                 ('C', 'C2', ch('E3', 'G3', 'C4')), ('B7', 'B1', ch('D#3', 'F#3', 'A3'))]
        for b, pos in bars('mutants'):
            sym, r, v = UPROG[b % 4]
            under = talking(s.seconds(pos + 0.1))
            pl(pizz, Clip([(i * 0.5, 0.3, (v + [v[1] + 12])[i % 4], 64 - 14 * under) for i in range(8)], length=4), pos)
            pl(bsn, Clip([(0, 0.45, m(r) + 12, 76), (1.5, 0.3, m(r) + 19, 60), (2, 0.45, m(r) + 15, 68),
                          (3.5, 0.3, m(r) + 12, 56)], length=4), pos, vel=0.8 if under else 1.0)
        ticks('mutants', 2, vel=42)
        # Hasso's three words: three bark-shaped stabs (low brass + pizz) on the word onsets
        r36 = RUNS.get(36) or []
        barks = [L(36) + q[0] for q in ([r36[0], r36[1], r36[-1]] if len(r36) >= 3 else r36)] or \
                [L(36), L(36) + 0.9, L(36) + 2.6]
        for k, tb in enumerate(barks):
            ps(bone, [(0, 0.16, p, 96 + 6 * k) for p in (('E2', 'B2') if k < 2 else ('G2', 'D3'))], tb)
            ps(pizz, [(0, 0.2, p, 96) for p in ('E3', 'B3')], tb)
        if len(barks) == 3:
            auto(bone, 'instrument.pitchbend', [(at(barks[2]) - 0.001, 0.0, 'step'), (at(barks[2] + 0.15), 2.0, 'smooth'),
                                                (at(barks[2] + 0.3), 0.0, 'step')])
        split_lead(notes('vel=74 B4/8 r/8 C5/8 B4/8 A#4/4 B4/4 | E5/8 r/8 D5/8 B4/8 G4/2 | A4/8 r/8 B4/8 A4/8 G#4/4 A4/4 | '
                         'F#4/2 D#4/2').arch(4, 0.4), mbar(g('mutants'), 1), clar, None, under=0.5, until=T_WURST)
    # "WURST!": a happy oompah blast, then the gross-up (D3)
    ps(tuba, [(0, 0.25, 'C2', 116), (0.3, 0.25, 'G1', 104), (0.6, 0.5, 'C2', 112)], T_WURST)
    ps(acc, [(t, 0.22, p, 88) for t in (0.3, 0.6) for p in ('E4', 'G4', 'C5')], T_WURST)
    ps(tpt, [(0, 0.2, 'G5', 108), (0.3, 0.2, 'E5', 100), (0.6, 0.55, 'C6', 112)], T_WURST)
    ps(kit, [(0, 0.3, 36, 104), (0, 0.6, 55, 90), (0.6, 0.6, 49, 96)], T_WURST)
    gross_sting(T_GROSS_D, D_GROSS_D, root='B1')
    # D4 the wolves: a low string cluster, a creepy whistled line (original), echo throws
    if g('wolves'):
        for b, pos in bars('wolves'):
            pl(trem, Clip([(0, 3.9, p, 44 + b * 4) for p in ch('E2', 'F2', 'B2', 'C3')], length=4), pos)
            pl(timp, Clip([(0, 1.0, 40, 50 + b * 5), (2.5, 0.8, 40, 40 + b * 5)], length=4), pos)
        ticks('wolves', 2, vel=46)
        split_lead(notes('vel=96 B4/2 E5/8 F#5/8 G5/4 | F#5/4. E5/8 B4/2 | C5/2 B4/8 A4/8 G4/4 | B4/1').arch(2, 1.0),
                   mbar(g('wolves'), 1), whistle, None, under=0.55)
        ps(revcym, [(0, 2.0, 60, 86)], T_CHASE - 2.0)

    # ================================================================== 8 the chase: 176, 2/4, E minor -> G
    CPROG_E = ['E1', 'E1', 'G1', 'F#1', 'E1', 'E1', 'C2', 'B1']
    CPROG_G = ['G1', 'G1', 'E1', 'E1', 'C2', 'C2', 'D2', 'D2']
    hit(T_CHASE, pitches=(28, 40, 47, 52, 55), vel=118, ring=0.8)
    for nm in ('chase', 'stream', 'coach', 'run'):
        prog = CPROG_G if nm == 'run' else CPROG_E
        t_stream0, t_stream1 = L(45) - 0.05, E(45) + 0.05
        for b, pos in bars(nm):
            r = m(prog[b % len(prog)])
            t0 = s.seconds(pos)
            if nm == 'stream' and t_stream0 <= t0 < t_stream1:      # Mandy's stream: stop-time, only the downbeat
                pl(kit, drums({'kick': 'x.......', 'crash': 'x.......' if b % 2 == 0 else '........'}, vel=70,
                              beats_per_bar=2), pos)
                pl(tuba, Clip([(0, 0.3, r + 12, 90)], length=2), pos)
                pl(brass, Clip([(0, 0.25, p, 84) for p in (r + 24, r + 31, r + 36)], length=2), pos)
                continue
            under = talking(t0 + 0.1)
            pl(kit, drums({'kick': 'x...x...', 'snare': '..x...x.' if b % 4 != 3 else '..x.xxxx', 'hat': 'xxxxxxxx'},
                          vel=56 if under else 82, beats_per_bar=2), pos)
            pl(tuba, Clip([(0, 0.25, r + 12, 96), (0.5, 0.25, r + 12, 80), (1.0, 0.25, r + 19, 90), (1.5, 0.25, r + 15, 82)],
                          length=2), pos, vel=0.85 if under else 1.0)
            pl(bone, Clip([(0, 0.2, r + 24, 72), (1.0, 0.2, r + 31, 66)], length=2), pos, vel=0.7 if under else 1.0)
            if not under:
                pl(surf, Clip([(k * 0.125, 0.11, r + 36 + (7 if k >= 8 else 0), 58) for k in range(16)], length=2), pos)
        ticks(nm, 2, vel=46)
        if nm != 'stream':
            line = notes('vel=96 meter=2/4 E5/8 G5/8 B5/8 A5/8 | G5/8 F#5/8 E5/4 | D5/8 E5/8 G5/8 B5/8 | D6/4 B5/4 | '
                         'C6/8 B5/8 A5/8 G5/8 | F#5/8 G5/8 A5/4 | B5/8 A5/8 G5/8 F#5/8 | E5/2',
                         transpose=3 if nm == 'run' else 0).arch(4, 0.9, beats_per_bar=2)
            for b, pos in bars(nm)[::8]:
                split_lead(line, pos, tpt, horns, under=0.45, until=sec_end(nm))
    # the howl as a riser into the chase (strings glissando up)
    ps(strings, [(0, 1.6, p, 70) for p in ('E3', 'B3')], T_CHASE - 1.6)
    auto(strings, 'instrument.pitchbend', [(at(T_CHASE - 1.6) - 0.001, -7.0, 'step'), (at(T_CHASE), 0.0, 'smooth')])
    # D7 the coach leaves: the 99-Euro sting slowed down and sour
    sting99(T_SOUR, slow=2.2, sour=True, vel=100)
    # the chase ends on a hit at the cut to E1
    hit(T_HYMN, pitches=(31, 43, 50, 55, 59), vel=120, ring=1.0)
    ps(kit, [(0, 0.5, 55, 80)], T_GATE)                                        # the gate clang

    # ================================================================== 9 the plant hymn: ironic chorale, C major
    if g('hymn'):
        t_h0 = max(T_GATE + 0.5, L(50) - 0.6)
        t_h1 = E(50) + 0.05
        hymn = [(0.0, 'C3', ('E4', 'G4', 'C5')), (1.0, 'F2', ('F4', 'A4', 'C5')), (2.0, 'A2', ('E4', 'A4', 'C5')),
                (3.0, 'G2', ('D4', 'G4', 'B4')), (4.0, 'C3', ('E4', 'G4', 'C5')), (5.0, 'F2', ('F4', 'A4', 'D5')),
                (6.0, 'G2', ('D4', 'G4', 'B4')), (7.0, 'C3', ('E4', 'G4', 'C5'))]
        spb = (t_h1 - t_h0) / 8.0
        ps(corgan, [(a * spb, spb * 0.98, p, 70) for a, r, v in hymn for p in v] +
           [(a * spb, spb * 0.98, r, 64) for a, r, v in hymn], t_h0)
        ps(choir, [(a * spb, spb * 0.98, p, 62) for a, r, v in hymn for p in v], t_h0)
        ps(timp, [(0, 0.8, 'C3', 70), (7 * spb, 0.8, 'C3', 80)], t_h0)
        ticks('hymn', 2, vel=34, after=T_HYMN + 1.0, until=t_h1)

    # ================================================================== 10 the scheme: Konrad's theremin, D minor
    if g('scheme'):
        SPR = [('Dm', 'D2', ch('D4', 'F4', 'A4')), ('Dm', 'D2', ch('D4', 'F4', 'A4')),
               ('Bb', 'Bb1', ch('D4', 'F4', 'Bb4')), ('A7', 'A1', ch('C#4', 'E4', 'G4'))]
        for b, pos in bars('scheme'):
            sym, r, v = SPR[b % 4]
            under = talking(s.seconds(pos + 0.1))
            pl(pizz, Clip([(i * 0.5, 0.3, (v + [v[1] + 12])[i % 4], 60 - 12 * under) for i in range(8)], length=4), pos,
               until=T_LIEB)
            pl(dbass, Clip([(0, 0.4, m(r), 82), (1.5, 0.4, m(r), 64), (2, 0.4, m(r) + 7, 72), (3.5, 0.3, m(r) + 12, 60)],
                           length=4), pos, until=T_LIEB)
            if s.seconds(pos) >= T_UNFOLD - 0.1:                   # the unfolding machine: mechanical clacks
                pl(block, Clip([(k * 0.25, 0.08, 76 + (k % 3 == 0), 40 + 16 * (k % 4 == 0)) for k in range(16)],
                               length=4), pos, until=T_LIEB)
        ticks('scheme', 2, vel=42, until=T_QUIT)
        split_lead(notes(f'vel=100 {KONRAD} | D5/4 F5/8 G5/8 Ab5/2 | A5/1').arch(1, 0.9), mbar(g('scheme'), 1, 0.5), ther,
                   None, under=0.6, until=T_UNFOLD)
        ps(kit, [(0, 0.1, 75, 90), (0.1, 0.1, 75, 84)], T_UNFOLD)
        # "Der Sauber-O-Mat Sechstausend!": the reveal fanfare
        ps(brass, [(0, 0.14, p, 104) for p in ('D4', 'F4', 'A4')] + [(0.16, 0.14, p, 106) for p in ('D4', 'F4', 'A4')] +
           [(0.32, 1.1, p, 114) for p in ('F4', 'A4', 'D5')], T_REVEAL)
        ps(tpt, [(0, 0.14, 'A5', 104), (0.16, 0.14, 'A5', 104), (0.32, 1.1, 'D6', 116)], T_REVEAL)
        ps(timp, [(0, 0.12, 'D3', 96), (0.16, 0.12, 'D3', 96), (0.32, 0.8, 'A2', 112)], T_REVEAL)
        ps(kit, [(0.32, 1.0, 49, 100)], T_REVEAL)
        split_lead(notes(f'vel=96 {KONRAD}').arch(1, 0.9), at(T_REVEAL + 1.6), ther, None, under=0.55, until=L(53))
        # "Konrad, ich hab dich immer lieb gehabt": schmaltzy strings
        ps(strings, [(0, max(1.0, E(53) - T_LIEB + 0.4), p, 66) for p in ('F3', 'A3', 'C4', 'F4')], T_LIEB - 0.1)
        ps(strings, [(0.0, 0.5, 'A5', 74), (0.5, 0.5, 'C6', 78), (1.0, max(0.5, E(53) - T_LIEB - 0.6), 'F6', 82)],
           T_LIEB - 0.1)
        ps(harp, [(i * 0.05, 1.0, p, 54) for i, p in enumerate(('F4', 'A4', 'C5', 'F5', 'A5', 'C6'))], T_LIEB - 0.1)
    # "Ich kündige.": the ticks stop dead - one bar without any pulse (a held chord), then the argument
    if g('quit'):
        ps(trem, [(0, 2.4, p, 40) for p in ('D3', 'A3', 'F4')], T_QUIT)
        t_pulse = T_QUIT + 4 * 60 / 100 + 0.05
        for b, pos in bars('quit'):
            pl(dbass, Clip([(0, 0.6, m('D2'), 64), (2, 0.6, m('A1'), 56)], length=4), pos, after=t_pulse)
            pl(pizz, Clip([(1, 0.3, p, 44) for p in ch('D3', 'F3')] + [(3, 0.3, p, 40) for p in ch('C#3', 'E3')], length=4),
               pos, after=t_pulse)
    # E5 "Ich BIN Personal!": a snare build into the door KICK, then the hall's hum
    if g('personal'):
        for b, pos in bars('personal'):
            pl(dbass, Clip([(i * 0.5, 0.4, m('D2') + (i % 2) * 7, 60 + i * 3) for i in range(8)], length=4), pos,
               until=T_KICK)
        n = int(max(1, (T_KICK - (T_KICK - 2.4)) / 0.1))
        ps(kit, [(k * 0.1, 0.08, 38, 30 + int(80 * k / n)) for k in range(n)], T_KICK - 2.4)
        ps(revcym, [(0, 2.0, 60, 90)], T_KICK - 2.0)
    hit(T_KICK, pitches=(26, 38, 45, 50, 53), vel=124, ring=1.6)
    ps(hum, [(0.4, max(1.0, L(58) - T_KICK - 0.4), 'C2', 90)], T_KICK)
    ps(hum, [(0.4, max(1.0, L(58) - T_KICK - 0.4), 'G2', 70)], T_KICK)

    # ================================================================== 11/12 reactor Malle: party Schlager, A major
    PARTY_PROG = [('A', 'A1', ch('C#4', 'E4', 'A4')), ('D', 'D2', ch('D4', 'F#4', 'A4')),
                  ('E', 'E2', ch('B3', 'E4', 'G#4')), ('A', 'A1', ch('C#4', 'E4', 'A4'))]
    party_tracks.extend([fbass, kit, acc, horgan, brass, tpt, whistle, glock, geig, keys])

    def key_at(t):
        """The vacuum: each bag stage pushes the key up a semitone (F4), the glow-up stays up."""
        if t < T_VAC:
            return 0
        return sum(1 for tb in T_BAG if t >= tb - 0.05)

    def party_bars(name, vel=1.0, until=None, after=None, hook=True, hook_vel=100):
        for b, pos in bars(name):
            t0 = s.seconds(pos)
            k = key_at(t0)
            sym, r, v = PARTY_PROG[b % 4]
            r = m(r) + k
            v = [p + k for p in v]
            under = talking(t0 + 0.2)
            w = (0.75 if under else 1.0) * vel
            pl(kit, drums({'kick': 'x...x...x...x...', 'clap': '....x.......x...', 'ohh': '..x...x...x...x.',
                           'hat': 'x.x.x.x.x.x.x.x.'}, vel=int(80 * w)), pos, until=until, after=after)
            pl(fbass, Clip([(0, 0.4, r + 12, 96), (0.5, 0.3, r + 24, 80), (1, 0.4, r + 19, 88), (1.5, 0.3, r + 24, 80),
                            (2, 0.4, r + 12, 94), (2.5, 0.3, r + 24, 80), (3, 0.4, r + 19, 88), (3.5, 0.3, r + 24, 80)],
                           length=4), pos, vel=w, until=until, after=after)
            pl(acc, Clip([(t, 0.22, p, int(60 * w)) for t in (0.5, 1.5, 2.5, 3.5) for p in v], length=4), pos,
               until=until, after=after)
            if not under:
                pl(horgan, Clip([(t, 0.2, p + 12, 54) for t in (0.5, 1.5, 2.5, 3.5) for p in v], length=4), pos,
                   until=until, after=after)
            # the counter's 32nd-note buzz on top
            pl(geig, Clip([(j * 0.125, 0.02, 84 + j % 4, 30 + (12 if j % 8 == 0 else 0) + (j * 7) % 6) for j in range(32)],
                          length=4), pos, until=until, after=after)
        if hook:
            for b, pos in bars(name)[::4]:
                k = key_at(s.seconds(pos))
                split_lead(notes(f'vel={hook_vel} {PARTY}', transpose=k).arch(4, 0.9), pos, tpt, brass, under=0.4,
                           until=until or sec_end(name), after=after)
                # the Malle whistles: two short blasts on the last bar of each hook
                tw = s.seconds(pos + 14.5)
                if tw < (until or sec_end(name)) - 0.3 and (after is None or tw >= after) and not stopped(tw):
                    ps(whistle, [(0, 0.12, 'B6', 84), (0.2, 0.12, 'B6', 84)], tw)

    if g('malle'):
        hit(T_MALLE, pitches=(33, 45, 52, 57, 61), vel=110, ring=0.6, crash=True, stab_=False)
        party_bars('malle')
        ps(brass, [(0, 0.35, p, 118) for p in ('A3', 'E4', 'A4', 'C#5')], T_PROST)    # "Prost!"
        ps(tpt, [(0, 0.35, 'A5', 118)], T_PROST)
        ps(kit, [(0, 0.8, 49, 110)], T_PROST)
        for k, tp in enumerate(T_SPROUTS):                                           # Finn sprouts: a pizz pop per leaf
            ps(pizz, [(0, 0.2, m('E5') + (k * 5) % 12, 96)], tp)
    # F4 the vacuum: the roar rises under the party groove, each bag stage up a semitone
    if g('vacuum'):
        party_bars('vacuum', vel=0.9, hook=False)
        t_r0 = T_NOZZLE
        t_r1 = sec_end('vacuum')
        ps(roar, [(0, (T_BAG[0] - t_r0), 'A1', 80), (T_BAG[0] - t_r0, T_BAG[1] - T_BAG[0], 'Bb1', 86),
                  (T_BAG[1] - t_r0, T_BAG[2] - T_BAG[1], 'B1', 92), (T_BAG[2] - t_r0, max(0.5, t_r1 - T_BAG[2]), 'C2', 98)],
           t_r0)
        auto(roar, 'instrument.cutoff', [(at(t_r0) - 0.01, 400.0, 'step'), (at(t_r1), 4000.0, 'exp')])
        for tb in T_BAG:
            ps(ohit, [(0, 0.3, p, 90) for p in (45, 52, 57)], tb)
        split_lead(notes(f'vel=100 {KONRAD} | D5/4 F5/8 G5/8 A5/2').arch(1, 0.9), mbar(g('vacuum'), 1, 1.0), ther, None,
                   under=0.55, until=T_BAG[0])
    # F5 Mandy's glow-up: the shimmer swells, the gross-up, then the hook back louder on "GLOW-UP!"
    if g('glowup'):
        party_bars('glowup', vel=0.7, hook=False, until=T_GLOWUP2)
        glow_shimmer(T_GLOWHUM, max(1.5, T_GROSS_F - T_GLOWHUM), 'C#6', vel=86)
        gross_sting(T_GROSS_F, D_GROSS_F, root='C2')
        hit(T_GLOWUP2, pitches=(36, 48, 55, 60, 64), vel=118, ring=0.6, stab_=False)
        party_bars('glowup', vel=1.1, hook=True, hook_vel=112, after=T_GLOWUP2)
    # F6 Oma licks the lump: tuba + harp swoon (the party thinner under her long line)
    if g('lick'):
        party_bars('lick', vel=0.6, hook=False)
        oma_stomp(T_LICKSLURP, root='C2', vel=100, spb=0.4)
        glow_shimmer(T_LICKSLURP + 0.45, 2.0, 'G6', vel=74, swell=False)
        ps(harp, [(i * 0.04, 1.4, p, 62) for i, p in enumerate(ch('C4', 'E4', 'G4', 'C5', 'E5', 'G5', 'C6', 'E6', 'G6'))],
           T_ACH)
        ps(strings, [(0.2, 2.2, p, 50) for p in ('C4', 'E4', 'G4', 'C5')], T_ACH)
    # F7 the lever: "Das ist RÜCKWÄRTS!" - the ep3 stab (record scratch + descending trombone + timpani)
    if g('lever'):
        party_bars('lever', vel=0.8, hook=True, hook_vel=96, until=T_RUECK - 0.05)
        ps(kit, [(0, 0.07, 84, 112), (0.07, 0.1, 62, 104), (0.17, 0.08, 81, 108)], T_RUECK)
        ps(kit, [(0, 0.3, 38, 104), (0, 0.3, 36, 100)], T_RUECK)
        desc = [72, 71, 70, 69, 68, 67, 66, 65]
        ps(bone, [(0.25 + i * 0.13, 0.15, p - 12, 100 - i * 3) for i, p in enumerate(desc)], T_RUECK)
        ps(tuba, [(0.25 + i * 0.26, 0.24, p - 36, 92 - i * 3) for i, p in enumerate(desc[::2])], T_RUECK)
        ps(timp, [(0.3, 0.4, 45, 96), (0.7, 0.4, 43, 90), (1.1, 0.5, 41, 86)], T_RUECK)
        party_bars('lever', vel=0.8, hook=False, after=T_RUECK + 1.4)
    # F8: the reverse cymbal + the tape-stop of the whole party groove, the BURST, a whoosh into silence
    if g('burst'):
        party_bars('burst', vel=0.9, hook=False, until=T_BURST - 0.02)
        ps(revcym, [(0, max(0.3, T_BURST - T_CLUNK), 60, 100)], T_CLUNK)
        for trk in party_tracks:
            if trk is geig:
                continue
            auto(trk, 'instrument.pitchbend', [(at(T_CLUNK) - 0.002, 0.0, 'step'), (at(T_CLUNK), 0.0),
                                               (at(T_BURST - 0.03), -24.0, 'smooth'), (at(T_BURST), 0.0, 'step')])
        hit(T_BURST, pitches=(26, 38, 45, 50, 57), vel=126, ring=1.8)
        dwh = max(1.0, L(73) + 0.6 - T_BURST)
        ps(sweep, [(0, dwh, 72, 110)], T_BURST)
        auto(sweep, 'instrument.cutoff', [(at(T_BURST) - 0.01, 9000.0, 'step'), (at(T_BURST + dwh), 300.0, 'exp')])

    # ================================================================== 13 out of the pipe: plop thuds, the last tick
    if g('pipe'):
        for k, tl in enumerate(T_LANDS):
            ps(kit, [(0, 0.2, 45 + (k % 3) * 2, 96), (0, 0.15, 36, 90)], tl)
            ps(pizz, [(0, 0.2, m('A2') + k * 2, 80)], tl)
        hit(T_OMALAND, pitches=(24, 36, 43, 48), vel=118, ring=1.2, crash=False, stab_=False)
        ps(tuba, [(0, 0.9, 'C1', 120)], T_OMALAND)
        # the counter's last, slowing ticks (its death line then in silence)
        t, gap, ev = T_OMALAND + 0.4, 0.22, []
        while t < T_DEATH - 0.35:
            ev.append(t)
            t += gap
            gap *= 1.35
        for k, tk in enumerate(ev):
            ps(geig, [(0, 0.03, 84, max(30, 70 - k * 5))], tk)

    # ================================================================== 14 kaiju catfish: monster-movie pastiche, F minor
    if g('kaiju'):
        t_k0 = E(74) + 0.1
        for b, pos in bars('kaiju'):
            pl(timp, Clip([(0, 1.0, 41, 70), (2.5, 0.4, 41, 56), (3.0, 0.8, 41, 64)], length=4), pos, after=t_k0)
            pl(trem, Clip([(0, 3.9, p, 44) for p in ch('F2', 'C3', 'Db3')], length=4), pos, after=t_k0, until=T_CHARGE)
        # "BLUUUBB": the foghorn bass note
        dfog = SPANS[75][1]
        ps(tuba, [(0, dfog, 'F1', 110)], T_BLUBB)
        ps(bone, [(0, dfog, 'C2', 96), (0, dfog, 'F2', 92)], T_BLUBB)
        ps(sbass, [(0, dfog, 'F1', 96)], T_BLUBB)
        ps(boom, [(0, 2.0, 38, 110)], T_BLUBB)
        ps(timp, [(0, 1.0, 41, 110)], T_BLUBB)
        # the monster theme (brass + horns, original): in the gap after Timo's line, before Ronny's charge
        split_lead(notes('vel=100 F3/4. Gb3/8 F3/2 | Ab3/4 G3/8 Gb3/8 F3/2').arch(2, 0.4), at(E(75) + 0.15), horns, None,
                   under=0.6, until=T_CHARGE)
        split_lead(notes('vel=96 F2/4. Gb2/8 F2/2 | Ab2/4 G2/8 Gb2/8 F2/2'), at(E(75) + 0.15), bone, None, under=0.6,
                   until=T_CHARGE)
        # Ronny's charge: a short heroic oompah
        oom = [(0, 0.2, 'F1', 104), (0.25, 0.2, 'C2', 96), (0.5, 0.2, 'F1', 104), (0.75, 0.2, 'C2', 96)]
        ps(tuba, [(a + k * 1.0, d, p, v) for k in range(int(max(1, (SPANS[77][1]) // 1))) for a, d, p, v in oom], T_CHARGE)
        ps(acc, [(a + k * 1.0, 0.18, p, 70) for k in range(int(max(1, SPANS[77][1] // 1))) for a in (0.25, 0.75)
                 for p in ('A3', 'C4', 'F4')], T_CHARGE)
        ps(tpt, [(0, 0.2, 'C5', 96), (0.25, 0.2, 'F5', 100), (0.5, 0.6, 'A5', 106)], E(77) - 0.9)
    # G3: the GULP + gross-up
    gross_sting(T_GULP, D_GULP, root='Db2')
    # G4: inside the fish - everything muffled (the stem buses' low-pass), a slow heartbeat
    if g('inside'):
        for b, pos in bars('inside'):
            pl(timp, Clip([(0, 0.4, 41, 70), (0.6, 0.4, 41, 54)], length=4), pos)
            pl(cello, Clip([(0, 3.9, m('F2'), 50)], length=4), pos)
            pl(trem, Clip([(0, 3.9, p, 40) for p in ch('Ab3', 'C4')], length=4), pos)
        t_m0, t_m1 = T_INSIDE, E(78) + 0.25
        for bus in stem_bus.values():
            bus.automate('fx.filter.cutoff', [(0, 20000.0), (at(t_m0) - 0.01, 20000.0, 'step'), (at(t_m0), 520.0, 'step'),
                                              (at(t_m1), 520.0), (at(t_m1 + 0.4), 20000.0, 'exp')])

    # ================================================================== 15 the bubble bath: harp + celesta, D major 3/4
    if g('bubble'):
        ps(harp, [(i * 0.035, 1.2, p, 64 + i) for i, p in enumerate(ch('D3', 'F#3', 'A3', 'D4', 'F#4', 'A4', 'D5', 'F#5',
                                                                         'A5', 'D6', 'F#6', 'A6'))], T_SOFTENER)
        ps(glock, [(0, 0.6, 'A6', 90), (0, 0.6, 'D7', 84)], T_SOFTENER)
        ps(cello, [(0, max(1.0, T_WORDS - T_PURR - 0.05), 'D2', 64)], T_PURR)
        sprog = [ch('D4', 'F#4', 'A4'), ch('B3', 'D4', 'F#4'), ch('G3', 'B3', 'D4'), ch('A3', 'C#4', 'E4')]
        for b, pos in bars('bubble'):
            v = sprog[b % 4]
            pl(harp, Clip([(0, 1.0, v[0] - 12, 50), (1, 0.6, v[1], 42), (2, 0.6, v[2], 42)], length=3), pos, until=T_WORDS)
            pl(strings, Clip([(0, 2.9, p, 36) for p in v], length=3), pos, until=T_WORDS)
        split_lead(notes('vel=70 meter=3/4 A5/2 F#5/4 | D6/2. | B5/4 A5/4 F#5/4 | A5/2. | G5/2 E5/4 | B5/2 A5/4 | '
                         'F#5/4 E5/4 C#5/4 | D5/2.').arch(4, 0.4, beats_per_bar=3), mbar(g('bubble'), 1), cele, None,
                   under=0.6, until=T_WORDS)

    # ================================================================== 16 Oma's fight: words, wrestling rock, C minor
    for k, tw in enumerate(WORD_HITS):
        ps(kit, [(0, 0.3, 36, 120), (0, 0.4, 38, 100 + 4 * k)], tw)
        ps(timp, [(0, 0.6, 'C3', 108 + 3 * k)], tw)
        ps(tuba, [(0, 0.4, 'C1' if k % 2 else 'C2', 110)], tw)
        if k == len(WORD_HITS) - 1:
            ps(brass, [(0, 0.4, p, 112) for p in ('C3', 'G3', 'C4', 'Eb4')], tw)
    if g('fight'):
        FPROG = ['C2', 'C2', 'Ab1', 'Bb1']
        for b, pos in bars('fight'):
            r = m(FPROG[b % 4])
            under = talking(s.seconds(pos + 0.2))
            pl(gtr, Clip([(i * 0.5, 0.3, p, 76 if i % 4 == 0 else 60) for i in range(8) for p in (r + 24, r + 31)],
                         length=4), pos, vel=0.75 if under else 1.0)
            pl(kit, drums({'kick': 'x.x...x.x.x...x.', 'snare': '....x.......x...', 'crash': 'x...............',
                           'hat': 'x.x.x.x.x.x.x.x.'}, vel=62 if under else 86), pos)
            pl(fbass, Clip([(i * 0.5, 0.4, r + 12, 90) for i in range(8)], length=4), pos)
            if b % 2 == 0:
                oma_stomp(s.seconds(pos), root=FPROG[b % 4], vel=100, spb=60 / 140)
        ps(revcym, [(0, 1.2, 60, 80)], BURP83[0] - 1.2)
    # the mega-burp gates everything (DRY / GATES), then the triumphant brass chord
    hit(T_TRIUMPH, pitches=(36, 48, 55, 60, 64), vel=124, ring=1.6)
    ps(brass, [(0, max(1.2, T_MAEDCHEN - T_TRIUMPH - 0.1), p, 112) for p in ('C3', 'G3', 'C4', 'E4', 'G4')], T_TRIUMPH)
    ps(horns, [(0, max(1.2, T_MAEDCHEN - T_TRIUMPH - 0.1), p, 100) for p in ('E3', 'G3', 'C4')], T_TRIUMPH)
    ps(tpt, [(0, 0.15, 'G5', 110), (0.18, 0.15, 'C6', 112), (0.36, 1.0, 'E6', 118)], T_TRIUMPH)
    # G8: Ronny slimed, the catfish sinks (a sad tuba), "Das ist mein Mädchen": the Konrad motif on solo clarinet
    if g('maedchen'):
        ps(strings, [(0, max(1.0, L(86) - T_MAEDCHEN), p, 40) for p in ('C4', 'E4', 'G4')], T_MAEDCHEN + 0.3)
        ps(tuba, [(0, 0.5, 'C2', 70), (0.6, 1.0, 'G1', 62)], E(85) + 0.2)
        auto(tuba, 'instrument.pitchbend', [(at(E(85) + 0.8) - 0.001, 0.0, 'step'), (at(E(85) + 1.6), -1.0, 'smooth'),
                                            (at(E(85) + 1.7), 0.0, 'step')])
        t_cl = E(85) + 0.2
        spb = min(0.75, max(0.45, (T_WHEEL - 0.2 - t_cl) / 5.0))
        line = notes(f'vel=86 {KONRAD}')
        ps(clar, [(n_.start * spb, n_.dur * spb * 0.97, n_.pitch, n_.vel - (14 if k_ in (1, 2, 3) else 0))
                  for k_, n_ in enumerate(line)], t_cl)
        ps(harp, [(0, 1.0, p, 44) for p in ('D3', 'A3', 'F4')], t_cl)
        ps(strings, [(0, max(1.0, T_WHEEL - t_cl - 0.1), p, 42) for p in ('D3', 'A3', 'F4')], t_cl)

    # ================================================================== 17 the wheel turns: the Zone theme in full, D major
    if g('wheel'):
        for k, tb in enumerate(T_BULBS):
            ps(cele, [(i * 0.06, 0.4, p, 70) for i, p in enumerate(ch(*(('D5', 'F#5', 'A5', 'D6') if k == 0 else
                                                                         ('F#5', 'A5', 'D6', 'F#6'))))], tb)
        t_z = T_TURN + 0.3
        ps(strings, [(0, max(0.5, t_z - (E(87) - 0.3)), p, 40) for p in ('A3', 'D4')], E(87) - 0.3)
        for nm in ('wheel', 'gondola'):
            for b, pos in bars(nm):
                if s.seconds(pos + 2.9) < t_z:
                    continue
                kk = b if nm == 'wheel' else b + len(bars('wheel'))
                sym, v = ZONE_CHORDS_MAJ[kk % 8]
                pl(strings, Clip([(0, 2.9, p + 12, 52) for p in v], length=3), pos, after=t_z - 0.05)
                pl(cello, Clip([(0, 1.0, v[0] - 12, 60)], length=3), pos, after=t_z - 0.05)
                pl(harp, Clip([(1, 0.6, p + 12, 42) for p in v[1:]] + [(2, 0.6, p + 12, 40) for p in v[1:]], length=3),
                   pos, after=t_z - 0.05)
                pl(horns, Clip([(0, 2.9, v[1], 38)], length=3), pos, after=t_z - 0.05)
        # the theme: the music box first, then the strings take it (warm), the music box an octave up with them
        x = g('wheel')
        first = next((pos for b, pos in bars('wheel') if s.seconds(pos) >= t_z - 0.05), None)
        if first is not None:
            zone_theme(first, mbox, src=ZONE_MAJ, vel=74, under=0.6, until=sec_end('gondola'))
            zone_theme(first + 24, strings, src=ZONE_MAJ, vel=80, under=0.7, until=sec_end('gondola'))
            zone_theme(first + 24, mbox, src=ZONE_MAJ, vel=58, transpose=12, under=0.6, until=sec_end('gondola'))

    # ================================================================== 18 the 99-euro reprise: the home organ is back
    if g('reprise'):
        organ_bars('reprise', vel=0.95, until=T_EURO3 + 0.9)
        sting99(T_EURO3)
        ps(horgan, [(0, 0.5, p, 90) for p in ('F4', 'A4', 'C5', 'F5')], T_EURO3 + 0.95)     # the button
        ps(obass, [(0, 0.5, 'F2', 90)], T_EURO3 + 0.95)
        ps(kit, [(0, 0.3, 36, 90), (0, 0.6, 55, 80)], T_EURO3 + 0.95)

    # ================================================================== 19 the home tag: Rhodes + brushes, F major
    HPROG = [ch('F3', 'A3', 'C4', 'E4'), ch('D3', 'F3', 'A3', 'C4'), ch('Bb2', 'D3', 'F3', 'A3'), ch('C3', 'E3', 'G3', 'Bb3')]
    for nm in ('home', 'tag'):
        for b, pos in bars(nm):
            v = HPROG[b % 4]
            under = talking(s.seconds(pos + 0.2))
            pl(keys, Clip([(0, 1.8, p, 50) for p in v] + [(2.5, 1.3, p, 42) for p in v[1:]], length=4), pos,
               until=L(96) - 0.1)
            pl(brush, drums({42: 'x.x.x.x.x.x.x.x.', 38: '....o.......o...'}, vel=30 if under else 38), pos,
               until=L(96) - 0.1)
            pl(dbass, Clip([(0, 0.9, v[0] - 12, 62), (2, 0.9, v[2] - 12, 54)], length=4), pos, until=L(96) - 0.1)
        hl = notes('vel=74 A4/4 C5/8 F5/8 E5/4 C5/4 | D5/4. C5/8 A4/2 | Bb4/4 D5/8 F5/8 A5/4 G5/8 F5/8 | E5/2 G5/2')
        for b, pos in bars(nm)[::4]:
            split_lead(hl.arch(4, 0.4), pos, vibes, None, under=0.4, until=L(96) - 0.1)
    if g('home'):
        glow_shimmer(T_HOME + 0.5, 6.0, 'A5', vel=44, swell=False)               # the glow as a soft pad
        glow_shimmer(SFX('burp glow fills', E(95) - 0.9), 1.8, 'C6', vel=54, swell=False)
    # the final button: one Geiger tick + the series end chord
    ps(geig, [(0, 0.03, 84, 90)], T_ENDCHORD - 0.2)
    ps(keys, [(0, 3.0, p, 64) for p in ('F3', 'C4', 'G4', 'A4')], T_ENDCHORD)
    ps(vibes, [(0, 2.5, p, 70) for p in ('F5', 'A5', 'C6')], T_ENDCHORD)
    ps(glock, [(0, 1.2, 'F6', 70)], T_ENDCHORD)
    ps(dbass, [(0, 2.0, 'F1', 80)], T_ENDCHORD)
    ps(brush, [(0, 0.8, 49, 50)], T_ENDCHORD)

    for (tid, target), (trk, pts_) in lanes.items():
        trk.automate(target, _mono(pts_))
    # ------------------------------------------------------------------ master: the gates, the end
    pts = [(0, 0.0)]
    for b0, b1 in sorted(GATES + DRY):
        pts += [(at(b0 - 0.04), 0.0), (at(b0), -80.0), (at(b1 + 0.05), -80.0), (at(b1 + 0.12), 0.0)]
    end_fade = at(min(T_ENDCHORD + 2.8, T_END - 0.4))
    pts += [(end_fade, 0.0), (at(T_END) - 0.001, -50.0, 'smooth')]
    s.master.automate('gainDb', _mono(pts))
    return s


def _mono(points):
    """Automation points sorted, later duplicates of a beat dropped (re-synced timings may make them touch)."""
    out = []
    for p in sorted(points, key=lambda q: q[0]):
        if not out or p[0] > out[-1][0] + 1e-6:
            out.append(p)
    return out
