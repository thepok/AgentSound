"""Taschenmonster - the background score for episode 4 of the Grandpa Konrad & Timo cartoon (German only,
D:/Projekte/cartoon/ep4_monster, a parody of monster-catching games; brief: ep4_monster/music_brief.md).

Laid out like songs/the-smog-monster-de: every scene / story beat is a section whose tempo is set so its first
downbeat lands exactly on its picture anchor; hits and stings are placed at absolute picture seconds; the melodic
lead plays loud only in the dialogue gaps (split_lead) and the bed stays thin under the voices (assemble.py also
side-chain ducks the music under the dialogue). The song ends at the timeline total (the episode tail included).

Sound world: the series palette (tuba / accordion oompah for Ronny, Konrad's ep2 theremin, harp + celesta for the
fabric softener, Rhodes for home) plus the game: two pulse leads (12.5 % and 50 % duty), a triangle bass, a noise
channel (snare / hats / sweeps), a triangle kick, fast arpeggio "chords", pitch-bend slides and a bitcrusher that
pixelates the vortex. All melodies are original: the Lintle motif (5-3-6-5 lullaby in a swung 6/8), our own
catch figure (1-5-4-5-8, dotted), our own battle sting (three RISING square stabs + a noise sweep, never a
descending chromatic run), a Dorian battle groove (no classic ostinato), a Mixolydian grass tiptoe, an original
victory flourish. Quotes: only the series' own themes - the Konrad hook (songs/grandpa-konrad-intro) re-voiced as
chiptune, and the Sock War theme (songs/sockenkrieg-theme-long, phrase A) for the Sock King.

Timing: every build reads ep4_monster/build/timeline.json (line spans, total), episode.json (line ids),
manifest.json (clip anchors line + offset, shake_at, bg_to, the game-UI overlays: text boxes, ball throws,
evolutions - parsed like ep4_monster/shots.py, the throw phases like clips/ui.py ui_ball_times) and measures the
burps / key words in voice/line_*.wav like animate.py burp_span (voiced runs). When a file is missing the snapshot
below is used. Overlays that start after their clip has been cut away are not on screen: their cues move to the
cut (see _ov). Re-sync after a timing change = just rebuild; the bar counts come from the target tempi (PLAN).

Build: python -m agentsound build songs/taschenmonster-de
Check: python songs/taschenmonster-de/check_anchors.py   (onsets / gates / length on out/mix.wav -> out/anchors.json)
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'Taschenmonster (Score, deutsche Fassung)', 'artist': 'AgentSound', 'genre': 'Soundtrack',
            'year': 2026, 'comment': 'cartoon score to picture, episode 4 (Grandpa Konrad & Timo), chiptune + '
                                     'series palette, ~315 s'}
ANALYSIS = {'profile': 'film'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'TASCHENMONSTER', 'subtitle': 'AgentSound', 'seed': 4}

# ------------------------------------------------------------------ picture timing (read at build time)
import json as _json
import math as _math
import re as _re
from pathlib import Path as _Path

EP = _Path('D:/Projekte/cartoon/ep4_monster')
# snapshot 2026-10-16 (timeline 5:15, total 315.1609) - only used when the files cannot be read
_SNAP_TOTAL = 315.1609
_SNAP = [[2.4, 4.342813], [7.342813, 9.459646], [17.102459, 4.234979], [22.177438, 5.208063], [27.685501, 9.075354],
         [37.060855, 6.93575], [44.716605, 7.264625], [53.42123, 2.088271], [55.869501, 3.890333],
         [62.519834, 4.596021], [67.415855, 9.918563], [79.494418, 3.232896], [83.447314, 9.583938],
         [93.391252, 7.294271], [100.985523, 6.365458], [110.710981, 6.056438], [119.407419, 5.651938],
         [126.379357, 4.215917], [131.555274, 0.465417], [132.320691, 5.418479], [138.09917, 10.570292],
         [148.969462, 3.541083], [155.870545, 6.022708], [165.853253, 1.6075], [168.180753, 3.622271],
         [172.103024, 5.368479], [179.391503, 6.616729], [186.488232, 9.583938], [196.43217, 2.003583],
         [199.395753, 3.239708], [203.235461, 3.716167], [208.631628, 6.3925], [218.264128, 5.73125],
         [224.355378, 5.620875], [230.936253, 5.886146], [239.342399, 5.481292], [247.583691, 3.181604],
         [252.565295, 6.419729], [259.585024, 4.081563], [264.146587, 7.368646], [271.995233, 7.495063],
         [279.850296, 2.072083], [284.322379, 6.659729], [294.222108, 1.754875], [298.136983, 4.694729],
         [303.311712, 1.885667], [305.497379, 4.663521]]
_SNAP_CLIPS = {'A1': {'t': 0.0}, 'A2': (1, -0.6), 'A3': (2, -0.5), 'A4': (4, -1.2), 'A5': (7, -0.8), 'B1': (8, -1.6),
               'C1': (10, -4.2), 'C2': (12, -3.2), 'C3': (13, -0.8), 'C4': (15, -0.3), 'C5': (16, -1.2),
               'C6': (17, -4.0), 'D1': (18, -1.8), 'D2': (19, -1.2), 'D3': (21, -0.4), 'D4': (23, -5.2),
               'D5': (24, -6.2), 'D6': (25, -0.8), 'E1': (27, -2.8), 'E2': (28, -0.6), 'E3': (29, -0.4),
               'E4': (31, -0.6), 'E5': (33, -0.6), 'E6': (35, -1.4), 'E7': (36, -1.4), 'F1': (38, -1.7),
               'F2': (39, -0.6), 'F3': (41, -0.4), 'F4': (42, -0.3), 'F5': (43, -1.0), 'G1': (44, -2.4),
               'G2': (45, -1.9), 'G3': (47, -0.3)}
# the burps / key words (s into the take) measured 2026-10-16
_SNAP_RUNS = {4: [(0.0, 0.3), (0.63, 1.1), (1.53, 2.2), (2.57, 3.53), (3.83, 4.57), (4.77, 5.13)],
              23: [(0.0, 0.4), (0.93, 1.37), (2.17, 2.43), (3.1, 3.53), (4.07, 4.43), (4.67, 5.07), (5.23, 5.97)],
              35: [(0.23, 1.43), (1.87, 5.87)], 38: [(0.63, 1.67), (1.83, 3.5), (3.93, 5.17), (5.3, 6.4)],
              43: [(0.03, 0.7), (1.53, 3.03), (3.77, 4.63), (5.4, 6.03), (6.2, 6.6)],
              47: [(0.0, 3.03), (3.47, 4.53)]}


def _load(path):
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


_tl = _load(EP / 'build' / 'timeline.json')
_ep = _load(EP / 'episode.json')
_man = _load(EP / 'manifest.json')
TIMING_SOURCE = 'timeline.json' if _tl else 'snapshot'
TOTAL = _tl['total'] if _tl else _SNAP_TOTAL
_spans = _tl['spans'] if _tl else _SNAP
_ids = [p['id'] for p in _ep['panels']] if _ep and len(_ep['panels']) == len(_spans) else list(range(1, len(_spans) + 1))
LINE_IDX = {lid: i for i, lid in enumerate(_ids)}            # dialogue id -> index into the spans / voice files
SPANS = {lid: tuple(_spans[i]) for lid, i in LINE_IDX.items()}
TEXT = {p['id']: p.get('text', '') for p in (_ep['panels'] if _ep else [])}
if _man:
    CLIPS = [c for ch in _man['episode']['chapters'] for c in ch['clips']]
else:
    CLIPS = [{'id': k, 'start': (v if isinstance(v, dict) else {'line': v[0], 'offset': v[1]})}
             for k, v in _SNAP_CLIPS.items()]
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


# ---- voiced runs of a take (animate.py _env / burp_span: 30 fps RMS / 90th percentile > 0.18, gaps >= 0.15 s)
def _runs(lid):
    try:
        import wave
        import numpy as np
        with wave.open(str(EP / 'voice' / f'line_{LINE_IDX[lid]:02d}.wav'), 'rb') as w:
            sr, ch = w.getframerate(), w.getnchannels()
            a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        a = a.reshape(-1, ch).mean(1)
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
        return [r for r in out if r[1] - r[0] > 0.25] or _SNAP_RUNS.get(lid, [])
    except Exception:
        return _SNAP_RUNS.get(lid, [])


RUNS = {lid: _runs(lid) for lid in _SNAP_RUNS}


def burp(lid):
    """(start, end) of the Ööörps in line lid: the voiced run nearest to where the text puts it (animate.py)."""
    txt = TEXT.get(lid, '')
    k = txt.find('Ööörps')
    d = SPANS[lid][1]
    guess = d * (k + 3) / len(txt) if k >= 0 and txt else d - 0.6
    r = RUNS.get(lid) or [(guess - 0.3, guess + 0.3)]
    b0, b1 = min(r, key=lambda q: abs((q[0] + q[1]) / 2 - guess))
    return L(lid) + b0, L(lid) + b1


def word(lid, k, frac):
    """Start of voiced run k of line lid (negative k from the end), or the text-fraction estimate."""
    r = RUNS.get(lid) or []
    try:
        return L(lid) + r[k][0]
    except IndexError:
        return L(lid) + SPANS[lid][1] * frac


# ---- the game UI overlays (shots.py overlay_t; clips/ui.py ui_ball_times / ui_type_end)
_AT_RE = _re.compile(r'^\s*(?:(line)\s+(\d+)\s+(start|end|mid)|(burp)\s+(start|end)|(clip)\s+(start|end))\s*'
                     r'(?:([+-])\s*([\d.]+))?\s*$')
UI_CPS = 28.0


def _ov_t(c, at):
    t0 = CLIP_T[c['id']]
    if isinstance(at, (int, float)):
        return t0 + at
    m = _AT_RE.match(str(at))
    if not m:
        return None
    off = (1 if m.group(8) == '+' else -1) * float(m.group(9)) if m.group(8) else 0.0
    if m.group(1):
        lid = int(m.group(2))
        base = {'start': L(lid), 'end': E(lid), 'mid': (L(lid) + E(lid)) / 2}[m.group(3)]
    elif m.group(4):
        lid = next((x for x in c.get('lines', []) if 'Ööörps' in TEXT.get(x, '')), None)
        if lid is None:
            return None
        b0, b1 = burp(lid)
        base = b0 if m.group(5) == 'start' else b1
    else:
        base = t0 if m.group(7) == 'start' else CLIP_END[c['id']]
    return base + off


def _ov(cid, kind, n=0, default=None, visible=True):
    """(t, overlay) of the n-th overlay of `kind` in clip cid. visible=True: an overlay that starts after its clip
    has been cut away is moved to the cut (minus 0.15 s) - the music follows what is on screen."""
    c = CLIP_BY_ID.get(cid, {})
    hits = sorted([(t, o) for o in c.get('overlays') or [] if o.get('kind') == kind
                   for t in [_ov_t(c, o.get('at', 0.0))] if t is not None], key=lambda e: e[0])
    if len(hits) <= n:
        return (default, {})
    t, o = hits[n]
    if visible and cid in CLIP_END and t > CLIP_END[cid] - 0.15:
        t = CLIP_END[cid] - 0.15
    return t, o


def type_end(t0, o):
    return t0 + len((o.get('de') or o.get('en') or '').replace('\n', '')) / UI_CPS


def ball_times(wobbles=3):
    T = {'fly': 0.0, 'open': 0.55, 'beam': 0.62, 'close': 1.35, 'drop': 1.45, 'land': 1.8}
    w = T['land'] + 0.35
    for i in range(wobbles):
        T[f'wobble_{i}'] = w
        w += 0.95
    T['click'] = w + 0.1
    return T


def shake(cid, default=0.0):
    return C(cid) + CLIP_BY_ID.get(cid, {}).get('shake_at', default)


# ------------------------------------------------------------------ the anchors
T_LVLUP = E(1)                                   # A2 "LEVEL UP! 32" on the handheld (line 1 end)
T_PROST = E(2) + 0.1                             # Ronny's "Prost."
T_BANG = shake('A4', 1.0)                        # A4 the door BANG (shake), Konrad bursts in
T_PRISON = word(4, -2, 0.75)                     # "Ein GEFÄNGNIS!"
BURP4 = burp(4)
T_WHO = E(6) - 0.15                              # "... WER?!"
T_RAY = C('A5')                                  # A5 the ray charges
T_ZAP = shake('A5', 4.5)                         # ZAP (shake)
T_VORTEX = C('B1')                               # B1 the pixel vortex
T_LAND = C('C1')                                 # C1 white-out cut: dead stop, plop-plop landing
T_TRANS = _ov('C1', 'battle_transition', default=T_LAND + 1.6)[0]
TB_C1 = _ov('C1', 'textbox', default=T_LAND + 2.4)            # "Ein wilder OPA erscheint!"
T_RONNY = C('C2')                                # C2 Ronny crashes down
T_BELLY = shake('C2', 0.6)
TB_C2 = _ov('C2', 'textbox', default=T_RONNY + 1.0)           # "Ein wilder RONNY erscheint!"
T_NPC = C('C3')                                  # C3 Mandy the NPC
T_CATCH = C('C4')                                # C4 Timo throws the ball at Konrad
TB_THROW = _ov('C4', 'textbox', 0, default=E(15) + 0.2)       # "TIMO wirft eine FANGKUGEL!"
T_THROW = _ov('C4', 'ball_throw', default=E(15) + 1.0, visible=False)[0]
T_FLAT = C('C5')                                 # C5 inside the ball: the cosy flat
T_KNAST = shake('C5', 4.6)                       # "TROTZDEM EIN KNAST, TIMO!"
T_FRIDGE = C('C6')                               # C6 the second throw (Ronny) -> the beer fridge
T_THROW2 = _ov('C6', 'ball_throw', default=T_FRIDGE + 0.4, visible=False)[0]
T_INSIDE2 = T_FRIDGE + (CLIP_BY_ID.get('C6', {}).get('bg_to') or {}).get('at', 2.6)
T_GRASS = C('D1')                                # D1 tall grass
T_RUSTLE = C('D2')                               # D2 the grass rustles ...
T_POP = L(19)                                    # ... POP: "Flusel!"
T_OPT = C('D3')                                  # D3 Konrad: "Opa OPTIMIERT"
T_NO = L(22)                                     # Timo's "Nein!"
T_EVO1 = C('D4')                                 # D4 evolution 1
_e1 = _ov('D4', 'evolution', default=T_EVO1 + 1.0)
T_PULSE1, T_FLASH1 = _e1[0], _e1[0] + _e1[1].get('dur', 2.6)
BURP23 = burp(23)
T_AGAIN = word(23, -1, 0.88)                     # "NOCHMAL!"
T_EVO2 = C('D5')                                 # D5 evolution 2
_e2 = _ov('D5', 'evolution', default=T_EVO2 + 0.8)
T_PULSE2, T_FLASH2 = _e2[0], _e2[0] + _e2[1].get('dur', 2.0)
T_GROSS = T_EVO2 + (CLIP_BY_ID.get('D5', {}).get('gross_up') or {}).get('offset', 2.9)   # the gross-up
T_SLIME = C('D6')                                # D6 the slurp, Konrad proud
T_GYM = C('E1')                                  # E1 the arena: pyro
T_NPC2 = C('E2')                                 # E2 Mandy in the stands: the SAME loop
T_BATTLE = C('E3')                               # E3 Kim throws: Swolepug
TB_E3 = _ov('E3', 'textbox', default=T_BATTLE + 0.8)
T_SWOLE = shake('E3', 2.4)                       # the ball opens with a flash
T_BATTLE2 = C('E4')                              # E4 Ronny is sent in
TB_COMPLAIN = _ov('E4', 'textbox', 0, default=L(32) - 1.6)   # "RONNY setzt MECKERN ein!"
TB_NOTEFF = _ov('E4', 'textbox', 1, default=E(32) + 0.3)     # "Das ist nicht sehr effektiv..."
TB_BENCH = _ov('E4', 'textbox', 2, default=E(32) + 1.8)      # "MUSKELMOPS setzt BANKDRÜCKEN ein!"
TB_FAINT = _ov('E4', 'textbox', 3, default=E(32) + 4.2, visible=False)   # "RONNY wurde besiegt!"
T_TAUNT = C('E5')                                # E5 Kim laughs
T_HERO = L(34)                                   # Timo's confident line: the hero key change
T_MENU = _ov('E5', 'menu', default=E(34) - 1.2)[0]
T_GRANDPA = C('E6')                              # E6 "Los, OPA!"
TB_GO = _ov('E6', 'textbox', 0, default=T_GRANDPA + 0.2)
BURP35 = burp(35)                                # the huge burp: the music is OFF
TB_SUPER = _ov('E6', 'textbox', 2, default=BURP35[1] + 1.4)  # "Das ist sehr effektiv!" (clamped to the cut)
T_SOFT = C('E7')                                 # E7 the fabric softener
TB_FAINT2 = _ov('E7', 'textbox', 0, default=E(36) + 1.4)     # "MUSKELMOPS wurde besiegt!"
TB_VICTORY = _ov('E7', 'textbox', 1, default=C('F1') - 0.8)  # "TIMO hat ARENALEITERIN KIM besiegt!"
T_SNOOP = C('E8') + 0.12 if 'E8' in CLIP_T else None   # E8 bridge: the lights flicker, Konrad sniffs out the power
T_KICK = shake('F1', 0.5)                        # F1 the door is kicked open: BallWorks
T_BATT = word(38, -1, 0.83)                      # "BATTERIEN!"
T_GLITCH = C('F3')                               # F3 Mandy's loop glitches ...
_npc3 = _ov('F3', 'npc_marker', default=T_GLITCH + 0.2)
T_BREAK = _ov_t(CLIP_BY_ID['F3'], _npc3[1]['pop_at']) if _npc3[1].get('pop_at') else (L(41) + E(41)) / 2
T_FREE = C('F4')                                 # F4 reverse polarity: every ball pops
T_KING = C('F5')                                 # F5 the legendary ball cracks: the Sock King
T_OHNO = word(43, 2, 0.57)                       # "Oh nein."
T_REVERSE = C('G1')                              # G1 the vortex in reverse
_bt = CLIP_BY_ID.get('G1', {}).get('bg_to') or {'at': 1.8, 'dur': 0.4}
T_HOME = T_REVERSE + _bt.get('at', 1.8) + _bt.get('dur', 0.4)   # the living room (evening)
T_TAG = C('G2')                                  # G2 "DREI STUNDEN SPÄTER..."
TB_CARD = _ov('G2', 'textbox', default=T_TAG + 0.2)
T_STOP = L(46)                                   # "Opa. Essen. Sofort."
T_PLEAD = C('G3')
BURP47 = burp(47)
T_ANT = _ov('G3', 'screen_insert', default=E(47) + 1.2)[0]   # "Eine wilde AMEISE erscheint!"
T_END = TOTAL

# (name, start, target bpm, meter): each section runs to the next one's start; bar counts from the target tempo
_PLAN = [('sunday', 0.0, 84, '4/4'), ('bang', T_BANG, 100, '4/4'), ('zap', T_RAY, 120, '4/4'),
         ('suck', T_ZAP, 150, '4/4'), ('vortex', T_VORTEX, 150, '7/8'), ('landing', T_LAND, 75, '4/4'),
         ('wild', T_TRANS, 168, '4/4'), ('ronny', T_RONNY, 168, '4/4'), ('npc', T_NPC, 120, '4/4'),
         ('catch', T_CATCH, 140, '4/4'), ('flat', T_FLAT, 96, '4/4'), ('fridge', T_FRIDGE, 126, '4/4'),
         ('grass', T_GRASS, 92, '6/8'), ('lintle', T_POP, 92, '6/8'), ('optimise', T_OPT, 110, '4/4'),
         ('evo1', T_EVO1, 120, '4/4'), ('lintroll', T_FLASH1, 100, '4/4'), ('evo2', T_EVO2, 120, '4/4'),
         ('gross', T_FLASH2, 60, '4/4'), ('slimed', T_SLIME, 96, '4/4'), ('gym', T_GYM, 138, '4/4'),
         ('npc2', T_NPC2, 120, '4/4'), ('battle', T_BATTLE, 152, '4/4'), ('battle2', T_BATTLE2, 152, '4/4'),
         ('polka', TB_COMPLAIN[0], 120, '4/4'), ('noteff', TB_NOTEFF[0], 90, '4/4'),
         ('bench', TB_BENCH[0], 120, '4/4'), ('taunt', T_TAUNT, 152, '4/4'), ('hero', T_HERO, 152, '4/4'),
         ('grandpa', T_GRANDPA, 152, '4/4'), ('burp', BURP35[0], 120, '4/4'), ('triumph', BURP35[1], 152, '4/4'),
         ('softener', T_SOFT, 70, '3/4'), ('fluffy', TB_FAINT2[0], 70, '3/4'), ('victory', TB_VICTORY[0], 150, '4/4'),
         *([('snoop', T_SNOOP, 100, '4/4')] if T_SNOOP else []),
         ('ballworks', T_KICK, 116, '4/4'), ('sour', T_BATT, 116, '4/4'), ('glitch', T_GLITCH, 116, '4/4'),
         ('liberation', T_FREE, 132, '4/4'), ('sockking', T_KING, 70, '4/4'), ('reverse', T_REVERSE, 150, '4/4'),
         ('home', T_HOME, 84, '4/4'), ('tag', T_TAG, 84, '4/4'), ('stop', T_STOP, 84, '4/4'),
         ('plead', T_PLEAD, 84, '4/4'), ('ant', T_ANT, 84, '4/4')]
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
    if _beats < 6.0:                                 # short beat: one bar of n quarter beats
        _nb = max(1, round(_beats))
        _p[3:] = [1, (_nb, 4), _nb]
    else:
        _p[3:] = [max(1, round(_beats / _bpb)), (_num, _den), _bpb]
PLAN = [tuple(p) for p in PLAN]                       # (name, start s, end s, bars, meter, beats per bar)

# the picture hits checked on the rendered mix (check_anchors.py: the onset nearest each target)
HITS = {'bang': T_BANG, 'prison': T_PRISON, 'zap': T_ZAP, 'vortex': T_VORTEX, 'transition': T_TRANS,
        'ronny_sting': T_RONNY, 'flat': T_FLAT, 'knast': T_KNAST, 'pop_lintle': T_POP, 'no_stop': T_NO,
        'flash1': T_FLASH1, 'again': T_AGAIN, 'flash2': T_FLASH2, 'pyro1': T_GYM, 'pyro2': T_GYM + 1.4,
        'battle': T_BATTLE, 'swole': T_SWOLE, 'polka': TB_COMPLAIN[0], 'not_effective': TB_NOTEFF[0],
        'bench': TB_BENCH[0], 'hero': T_HERO, 'super': BURP35[1] + 0.15, 'softener': T_SOFT, **({'snoop': T_SNOOP} if T_SNOOP else {}), 'kick': T_KICK,
        'batteries': T_BATT, 'liberation': T_FREE, 'king': T_KING, 'ohno': T_OHNO, 'home': T_HOME,
        'card': TB_CARD[0], 'ant': T_ANT}
def _gate(lid):
    """The burp of line lid, held shut up to the next word when that follows within 0.5 s."""
    b0, b1 = burp(lid)
    nxt = [L(lid) + a for a, _ in RUNS.get(lid) or [] if b1 < L(lid) + a < b1 + 0.5]
    return b0, (max(b1, min(nxt) - 0.13) if nxt else b1)


GATES = [_gate(4), _gate(23), _gate(35), _gate(47)]   # the music is silent under these burps


# ------------------------------------------------------------------ helpers
_PC = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}


def m(name):
    """'F#4' -> MIDI (C4 = 60)."""
    mm = _re.match(r'^([A-G])([#b]?)(-?\d)$', name)
    return 12 * (int(mm.group(3)) + 1) + _PC[mm.group(1)] + {'#': 1, 'b': -1, '': 0}[mm.group(2)]


def ch(*names):
    return [m(x) for x in names]


def mbar(section, n, beat=0.0):
    """Musical (1-based) bar n of a section: mbar(sec, 1) = its first downbeat."""
    return section.bar(n - 1, beat=beat)


def bpm_of(a, b, bars, bpb):
    return bars * bpb * 60.0 / (b - a)


# ------------------------------------------------------------------ the chip voices
def pulse(pw=0.125, level=-8.0, mono=True, vib=True, glide=0.0, release=0.05, sustain=0.75):
    """NES-style pulse: a bare square of duty pw, no filter, a delayed triangle vibrato."""
    mods = [vamod.lfo('triangle', hz=5.8, delay=0.22, fade=0.18, id='vib') >> ('pitch', 22)] if vib else []
    return inst.va(osc1__wave='square', osc1__pw=pw, osc2__level=0.0, drift__pitch=0, drift__cutoff=0,
                   filter__type='lp12', cutoff=16000, resonance=0.0, filter__env=0.0, filter__keytrack=0.0,
                   filter__velocity=0.0, osc__retrig='on', amp__attack=0.002, amp__decay=0.3,
                   amp__sustain=sustain, amp__release=release, amp__velocity=0.85,
                   mode='mono' if mono else 'poly', glide=glide, mods=mods, level=level)


def tri_bass(level=-4.0):
    """The triangle channel: a stepped-sounding, pure triangle bass."""
    return inst.va(osc1__wave='triangle', osc2__level=0.0, drift__pitch=0, drift__cutoff=0, filter__type='lp12',
                   cutoff=9000, resonance=0.0, filter__env=0.0, filter__velocity=0.0, osc__retrig='on',
                   amp__attack=0.002, amp__decay=0.2, amp__sustain=0.9, amp__release=0.03, amp__velocity=0.6,
                   mode='mono', glide=0.0, level=level)


def tri_kick(level=-4.0):
    """Triangle kick: a fast downward pitch sweep."""
    return inst.va(osc1__wave='triangle', osc2__level=0.0, drift__pitch=0, filter__type='lp12', cutoff=6000,
                   resonance=0.0, filter__env=0.0, osc__retrig='on', amp__attack=0.001, amp__decay=0.16,
                   amp__sustain=0.0, amp__release=0.05, amp__velocity=0.7,
                   mods=[vamod.env(0.0, 0.05, 0.0) >> ('pitch', 2400)], level=level)


def noise_ch(level=-10.0):
    """The noise channel: white noise through a key-tracked low-pass (the note picks the colour: 74 snare,
    90 hat, 60 thud), short decay; long notes + cutoff automation make sweeps."""
    return inst.va(osc1__level=0.0, osc2__level=0.0, noise__level=1.0, noise__color='white',
                   filter__type='lp12', cutoff=1600, resonance=0.1, filter__env=0.0, filter__keytrack=1.0,
                   filter__velocity=0.3, amp__attack=0.001, amp__decay=0.12, amp__sustain=0.0, amp__release=0.05,
                   amp__velocity=0.8, level=level)


def sweep_noise(level=-12.0):
    """Sustained noise for the zap / transition / vortex sweeps (cutoff automated)."""
    return inst.va(osc1__level=0.0, osc2__level=0.0, noise__level=1.0, noise__stereo=0.6, filter__type='bp12',
                   cutoff=1200, resonance=0.45, filter__env=0.0, filter__keytrack=1.0, amp__attack=0.02,
                   amp__decay=0.5, amp__sustain=0.9, amp__release=0.25, level=level)


def theremin():
    """Konrad's paranoia voice (the ep2 theremin)."""
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.9,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def whine():
    """The ray charging: a gliding detuned pulse pair (pitch climbs with the dial)."""
    return inst.va(osc1__wave='square', osc1__pw=0.25, osc2__wave='square', osc2__pw=0.4, osc2__level=0.7,
                   osc2__fine=18, mode='legato', glide=1.2, filter__type='lp12', cutoff=5000, resonance=0.2,
                   filter__env=0.0, amp__attack=0.2, amp__decay=0.5, amp__sustain=0.9, amp__release=0.3,
                   mods=[vamod.lfo('sine', hz=7.0, id='wob') >> ('pitch', 30)], level=-12.0)


# ------------------------------------------------------------------ the themes (all original)
# the Lintle motif: 5-3-6-5 lullaby in a swung 6/8 (one 6/8 bar = 3 quarter beats): (beat, dur, degree step)
LINTLE = [(0.0, 0.5, 7), (0.5, 1.0, 4), (1.5, 0.5, 9), (2.0, 1.0, 7)]     # semitones over the tonic: 5 3 6 5
# our catch figure 1-5-4-5-8, dotted
CATCH = [(0.0, 0.25, 0), (0.25, 0.75, 7), (1.0, 0.25, 5), (1.25, 0.75, 7), (2.0, 1.0, 12)]
# the Konrad hook (series intro) and the Sock War phrase A (series theme), D minor
KONRAD = 'D5/4 F5/8 E5/8 D5/8 A5/4.'
SOCKWAR = 'D5/2 F5/4 E5/8 D5/8 | A5/2. r/4 | Bb5/4 A5/4 G5/4 Bb5/4 | A5/1'
# the NPC jingle: a 2-bar C major music-box loop at 120 BPM, in SECONDS (identical audio every time it plays)
NPC_LOOP = [(0.0, 0.25, 'E6'), (0.25, 0.25, 'G6'), (0.5, 0.5, 'C7'), (1.0, 0.25, 'B6'), (1.25, 0.25, 'G6'),
            (1.5, 0.5, 'A6'), (2.0, 0.25, 'F6'), (2.25, 0.25, 'A6'), (2.5, 0.5, 'D7'), (3.0, 0.25, 'C7'),
            (3.25, 0.25, 'B6'), (3.5, 0.5, 'G6')]
NPC_BASS = [(0.0, 0.45, 'C5'), (0.5, 0.45, 'G5'), (1.0, 0.45, 'E5'), (1.5, 0.45, 'G5'), (2.0, 0.45, 'F5'),
            (2.5, 0.45, 'A5'), (3.0, 0.45, 'G5'), (3.5, 0.45, 'B4')]
NPC_LEN = 4.0
NPC_PRE = 0.5                                     # the loop starts this long before Mandy's line


def _dump_anchors():
    """out/anchors_build.json: the anchors this build was made with (check_anchors.py compares them)."""
    try:
        out = _Path(__file__).resolve().parent / 'out'
        out.mkdir(exist_ok=True)
        (out / 'anchors_build.json').write_text(_json.dumps(
            {'timing': TIMING_SOURCE, 'total': TOTAL, 'hits': HITS, 'gates': GATES,
             'plan': [[p[0], p[1], p[2], p[3], list(p[4])] for p in PLAN]}, indent=1), encoding='utf-8')
    except Exception:
        pass


def build() -> Song:
    _dump_anchors()
    s = Song('Taschenmonster (Score)', tempo=bpm_of(PLAN[0][1], PLAN[0][2], PLAN[0][3], PLAN[0][5]),
             key='F major', seed=4, tail=0.0)
    sec = {}
    for name, a, b, bars, meter, bpb in PLAN:
        sec[name] = s.section(name, bars=bars, meter=None if meter == (4, 4) else meter)
    for name, a, b, bars, meter, bpb in PLAN[1:]:
        s.set_tempo(sec[name], bpm_of(a, b, bars, bpb))
    g = sec.get
    T_SEC = {name: (a, b) for name, a, b, *_ in PLAN}

    def at(t):
        """The beat at an absolute picture time (seconds)."""
        return s.beat_at(max(0.0, min(t, T_END)))

    def talking(t, pad=0.06):
        return any(a - pad <= t <= a + d + pad for a, d in SPANS.values())

    stops = []                                       # (t0, t1): stop-time windows (text boxes, gates)
    lanes = {}                                       # (track id, target) -> [track, points]: merged at the end

    def auto(track, target, pts):
        lanes.setdefault((track.id, target), [track, []])[1].extend(pts)

    def stopped(t):
        return any(a <= t < b for a, b in stops)

    def pl(track, clip, pos, vel=1.0, until=None, after=None):
        """Play a groove clip, dropping the notes in a stop-time window (and before `after` / from `until` s)."""
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
            out.append((a - b0, max(0.02, e - a), m(p) if isinstance(p, str) else p, max(1, min(127, int(v * vel)))))
        if out:
            track.play(Clip(out, length=max(o[0] + o[1] for o in out) + 0.01), b0)

    def split_lead(clip, pos, loud, soft=None, under=0.6, until=None):
        """Ducking-friendly lead: notes in the dialogue gaps play on `loud`, notes under a line on `soft` (or
        `loud`) at `under` x velocity; notes in a stop window or from `until` (s) are left out."""
        lo, so = [], []
        for n in clip:
            t = s.seconds(pos + n.start)
            if stopped(t) or (until is not None and t >= until):
                continue
            if talking(t):
                so.append((n.start, n.dur, n.pitch, max(1, int(n.vel * under))))
            else:
                lo.append((n.start, n.dur, n.pitch, n.vel))
        if lo:
            loud.play(Clip(lo, length=clip.length), pos)
        if so:
            (soft or loud).play(Clip(so, length=clip.length), pos)

    def bars_of(name):
        x = g(name)
        return int(x.bars) if x else 0

    returns = [s.hall(), s.plate(), s.echo()]
    s.master.use('master/synthwave')
    s.master.automate('fx.limiter.gain', [(0, 8.0)])     # the earlier scores sit around -18 LUFS

    # ------------------------------------------------------------------ the chip band
    lead = s.track('lead_chip', pulse(0.125, -7), gain_db=-7, pan=0.08, sends={'echo': -16, 'hall': -14},
                   fx=[fx.bitcrush(bits=8, downsample=1, mix=1.0)])
    lead2 = s.track('lead_soft', pulse(0.25, -9, release=0.08), gain_db=-12, pan=0.12, sends={'hall': -12})
    sq = s.track('square', pulse(0.5, -10, mono=False, vib=False, release=0.04), gain_db=-12, pan=-0.18,
                 sends={'hall': -14}, fx=[fx.bitcrush(bits=8, downsample=1, mix=1.0)])
    arp = s.track('arp_chip', pulse(0.25, -10, mono=False, vib=False, release=0.03, sustain=0.5), gain_db=-15,
                  pan=0.22, sends={'echo': -14}, fx=[fx.bitcrush(bits=7, downsample=1, mix=1.0)])
    tri = s.track('bass_chip', tri_bass(), gain_db=-4, fx=[fx.bitcrush(bits=9, downsample=1, mix=0.6)])
    kick = s.track('kick_chip', tri_kick(), gain_db=-6)
    nz = s.track('drums_noise', noise_ch(-2.0), gain_db=-15, pan=0.05, fx=[fx.bitcrush(bits=10, downsample=2, mix=1.0)])
    sweep = s.track('sweep', sweep_noise(), gain_db=-10, sends={'hall': -8})
    wh = s.track('whine', whine(), gain_db=-10, sends={'hall': -10})
    bleep = s.track('handheld', pulse(0.125, 0.0, vib=False, release=0.02, sustain=0.4), gain_db=-24, pan=-0.45,
                    fx=[fx.bitcrush(bits=8, downsample=3, mix=1.0), fx.eq({'low.freq': 400, 'low.gain': -12})])
    # ------------------------------------------------------------------ the series' acoustic colours
    keys = s.track('rhodes', 'gm/epiano', gain_db=-9, pan=-0.2, fx=[fx.eq({'low.freq': 160, 'low.gain': -8})])
    brush = s.track('brushes', inst.sf2('Brush Kit'), gain_db=-12, sends={'hall': -14}).humanize(3, 5)
    kit = s.track('kit', inst.sf2('Standard 1 Kit'), gain_db=-10, sends={'hall': -12},
                  fx=[fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 0.7})]).humanize(3, 5)
    tuba = s.track('tuba', inst.sf2('Tuba'), gain_db=-1, sends={'hall': -11})
    acc = s.track('accordion', inst.sf2('Accordion'), gain_db=-6, pan=-0.2, sends={'hall': -9},
                  fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.6})])
    ther = s.track('theremin', theremin(), gain_db=-7, pan=0.1, sends={'hall': -5, 'echo': -12},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    harp = s.track('harp', inst.sf2('Orchestral Harp'), gain_db=-6, pan=-0.35, sends={'hall': -3})
    cele = s.track('celesta', inst.sf2('Celeste'), gain_db=-9, pan=0.25, sends={'hall': -2})
    glock = s.track('glock', inst.sf2('Glockenspiel'), gain_db=-12, pan=0.3, sends={'hall': -4})
    mbox = s.track('musicbox', inst.sf2('Music Box'), gain_db=-6, pan=0.15)          # dry: the NPC loop
    mbass = s.track('npc_bass', pulse(0.5, -4, vib=False, release=0.03, sustain=0.3), gain_db=-14, pan=-0.1)
    bsn = s.track('bassoon', inst.sf2('Bassoon'), gain_db=-4, pan=0.1, sends={'hall': -8})
    vibes = s.track('vibes', inst.sf2('Vibraphone'), gain_db=-9, pan=0.2, sends={'hall': -6},
                    fx=[fx.filter(mode='lp', cutoff=2400)])
    nylon = s.track('nylon', inst.sf2('Nylon Guitar'), gain_db=-7, pan=-0.25, sends={'hall': -8},
                    fx=[fx.filter(mode='lp', cutoff=2400)])
    pizz = s.track('pizz', inst.sf2('Pizzicato Strings'), gain_db=-5, pan=-0.15, sends={'hall': -7})
    strings = s.track('strings', inst.sf2('Slow Strings'), gain_db=-8, sends={'hall': -3},
                      fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7}), fx.chorus(mode='II', mix=0.4)])
    trem = s.track('tremolo', inst.sf2('Tremolo Strings'), gain_db=-8, pan=-0.1, sends={'hall': -5},
                   fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    bone = s.track('trombone', inst.sf2('Trombone'), gain_db=-5, pan=0.2, sends={'hall': -7})
    mute = s.track('mutetpt', inst.sf2('Muted Trumpet'), gain_db=-6, pan=0.25, sends={'hall': -7})
    brass = s.track('brass', inst.sf2('Brass Section'), gain_db=-9, pan=0.05, sends={'hall': -5},
                    fx=[fx.eq({'peak2.freq': 1800, 'peak2.gain': -3.0, 'peak2.q': 0.7})])
    timp = s.track('timpani', inst.sf2('Timpani'), gain_db=-6, sends={'hall': -4})
    choir = s.track('choir', inst.sf2('Concert Choir'), gain_db=-10, sends={'hall': -1},
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    organ = s.track('organ', inst.sf2('Pipe Organ'), gain_db=-13, pan=-0.2, sends={'hall': -4},
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -5.0, 'peak2.q': 0.6})])
    gtr = s.track('guitar', inst.sf2('Distortion Guitar'), gain_db=-14, pan=-0.3, sends={'hall': -12},
                  fx=[fx.eq({'peak2.freq': 2000, 'peak2.gain': -4.0, 'peak2.q': 0.7, 'low.freq': 120, 'low.gain': -6})])
    whistle = s.track('whistle', inst.sf2('Whistle'), gain_db=-11, pan=0.2, sends={'hall': -3, 'echo': -14})
    uke = s.track('ukulele', inst.sf2('Ukulele'), gain_db=-8, pan=-0.25, sends={'hall': -8})
    block = s.track('woodblock', inst.sf2('Wood Block'), gain_db=-13, pan=0.35, sends={'hall': -11})
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-10, sends={'hall': -7})
    boom = s.track('boom', 'synthwave/impact', gain_db=-12)
    revcym = s.track('revcym', inst.sf2('Reverse Cymbal'), gain_db=-13, sends={'hall': -7})
    crowd = s.track('crowd', inst.sf2('Applause'), gain_db=-16, sends={'hall': -9})

    def hit(t, pitches=(38, 50, 57, 62), vel=112, ring=1.2, crash=True, stab=True, chip=True):
        """The episode hit at picture time t: orchestra hit + impact + timpani (+ brass, crash, a chip stab)."""
        ps(ohit, [(0, ring, p, vel) for p in pitches], t)
        ps(boom, [(0, max(1.5, ring), 38, min(127, vel + 4))], t)
        ps(timp, [(0, 1.0, pitches[0] + 12 if pitches[0] < 40 else pitches[0], vel)], t)
        if stab:
            ps(brass, [(0, min(ring, 0.8), p, vel - 12) for p in pitches[1:]], t)
        if crash:
            ps(kit, [(0, 1.0, 49, vel - 10), (0, 0.3, 36, vel - 6)], t)
        if chip:
            ps(sq, [(0, 0.25, p + 24, 100) for p in pitches[1:4]], t)

    def chip_stabs(t, roots, step=0.11, vel=104):
        """Our battle sting: rising square-chord stabs + a noise sweep up (never a descending run)."""
        for k, r in enumerate(roots):
            ps(sq, [(k * step, step * 0.8, p, vel) for p in (r, r + 3, r + 7)], t)
            ps(lead, [(k * step, step * 0.8, r + 12, vel)], t)
            ps(kick, [(k * step, 0.1, 40, 100)], t)
        ps(kit, [(0, 0.8, 49, 100)], t)
        n = len(roots) * step
        ps(sweep, [(0, n + 0.25, 72, 96)], t)
        auto(sweep, 'instrument.cutoff', [(at(t - 0.02), 600), (at(t), 600, 'step'), (at(t + n + 0.2), 9000, 'exp')])

    def catch_jingle(t, root, vel=100, short=False):
        fig = CATCH[:3] + [(1.25 - 0.25, 1.0, 12)] if short else CATCH
        sc = 0.16 if short else 0.2                    # seconds per quarter (fast, 300-375 BPM feel)
        ps(lead, [(b * sc, d * sc * 0.95, root + st, vel) for b, d, st in fig], t)
        ps(tri, [(b * sc, d * sc * 0.9, root - 24 + (0 if st in (0, 12) else 7 if st == 7 else 5), 96)
                 for b, d, st in fig], t)
        ps(sq, [(fig[-1][0] * sc, 0.6, p, 80) for p in (root, root + 4, root + 7)], t)
        ps(nz, [(fig[-1][0] * sc, 0.1, 90, 90)], t)

    def wobble_tick(t, vel=96):
        ps(nz, [(0, 0.05, 92, vel), (0.08, 0.05, 86, vel - 20)], t)
        ps(block, [(0, 0.1, 76, vel - 10)], t)

    def lintle(t, root, track, vel=82, scale=1.0, octave=0, motif=LINTLE, bars=1, spb=None):
        """The Lintle motif at picture time t (spb = seconds per quarter beat; default the local tempo)."""
        if spb is None:
            spb = 60.0 / s.tempo_at(at(t))
        ev = []
        for k in range(bars):
            for b, d, st in motif:
                ev.append(((k * 3 + b) * spb * scale, d * spb * scale * 0.95, root + st + 12 * octave, vel))
        ps(track, ev, t)

    def gate(t0, t1):
        stops.append((t0 - 0.05, t1 + 0.08))

    for b0, b1 in GATES:
        gate(b0, b1)

    def box_pop(t0, vel=84):
        """The game's text box opens: a tiny square blip."""
        ps(lead, [(0, 0.05, 'E6', vel), (0.055, 0.07, 'B6', vel)], t0)
        ps(sq, [(0, 0.05, 'E5', vel), (0.055, 0.07, 'B5', vel)], t0)
        ps(nz, [(0, 0.03, 100, vel)], t0)

    def textstop(tb, extra=0.25, pop=True):
        t0, o = tb
        if t0 is not None:
            stops.append((t0 - 0.04, type_end(t0, o) + extra))
            if pop:
                box_pop(t0)

    # ================================================================== 1 sunday: rainy living room, F major
    sun = g('sunday')
    if sun:
        prog = [('F', ch('F3', 'A3', 'C4', 'E4')), ('Dm', ch('D3', 'F3', 'A3', 'C4', 'E4')),
                ('Bb', ch('Bb2', 'D3', 'F3', 'A3')), ('C', ch('C3', 'G3', 'Bb3', 'D4'))]
        nb = int(sun.bars)
        for b in range(nb):
            pos = mbar(sun, b + 1)
            sym, v = prog[b % 4]
            keys.play(Clip([(0, 1.9, p, 54 + (b % 2) * 4) for p in v] + [(2.5, 1.4, p, 46) for p in v[1:]], length=4), pos)
            # rain on the window: soft brushed ticks (straight 8ths, a ghost here and there)
            brush.play(drums({42: 'x.x.x.x.x.x.x.x.', 38: '........o.......' if b % 2 else '................'},
                             vel=34 + (b % 3) * 3), pos)
            if s.seconds(pos) >= L(2) - 0.6:          # Ronny's tuba walks in under line 2
                r = {'F': 'F1', 'Dm': 'D2', 'Bb': 'Bb1', 'C': 'C2'}[sym]
                tuba.play(Clip([(0, 0.7, m(r), 66), (1, 0.6, m(r) + 7, 56), (2, 0.7, m(r) + 12 if m(r) < 36 else m(r), 62),
                                (3, 0.6, m(r) + 4, 54)], length=4), pos)
        # the handheld bleeps (diegetic, tiny, left = Timo) while he plays, until the level up
        ev = []
        t = 0.6
        k = 0
        pat = ['C6', 'E6', 'G6', 'E6', 'D6', 'F6', 'A6', 'F6']
        while t < T_LVLUP - 0.2:
            ev.append((t - 0.6, 0.06, pat[k % 8], 70 if k % 4 == 0 else 52))
            t += 0.18 if (k // 8) % 2 == 0 else 0.27
            k += 1
        ps(bleep, ev, 0.6)
        # LEVEL UP sparkle (original: an upward broken F major sixth + a trill)
        ps(bleep, [(i * 0.06, 0.08, p, 92) for i, p in enumerate(('F6', 'A6', 'C7', 'D7', 'F7'))] +
           [(0.3 + i * 0.045, 0.04, 'F7' if i % 2 else 'G7', 70) for i in range(6)], T_LVLUP)
        ps(glock, [(0.3, 0.6, 'F7', 50)], T_LVLUP)
        # "Prost." clink + a tiny oompah ta-da
        ps(glock, [(0, 0.3, 'A6', 74), (0.12, 0.4, 'C7', 66)], T_PROST)
        ps(tuba, [(0.35, 0.25, 'F1', 92), (0.65, 0.6, 'F2', 88)], T_PROST)
        ps(acc, [(0.65, 0.6, p, 76) for p in ('F4', 'A4', 'C5')], T_PROST)

    # ================================================================== 2 bang: Konrad's conspiracy rant, D minor
    bg_ = g('bang')
    if bg_:
        hit(T_BANG, pitches=(38, 50, 57, 62, 65), vel=118, ring=0.9)
        nb = int(bg_.bars)
        dprog = [('Dm', 'D2'), ('Dm', 'D2'), ('Bb', 'Bb1'), ('A7', 'A1')]
        for b in range(nb):
            pos = mbar(bg_, b + 1)
            sym, r = dprog[b % 4]
            tones = {'Dm': ch('D4', 'F4', 'A4'), 'Bb': ch('D4', 'F4', 'Bb4'), 'A7': ch('C#4', 'E4', 'G4')}[sym]
            under = talking(s.seconds(pos + 0.1))
            # sneaky pizzicato (the paranoid tiptoe), thin under the lines
            pl(pizz, Clip([(i * 0.5, 0.3, (tones + [tones[1] + 12])[i % 4], 64 - 12 * under) for i in range(8)], length=4), pos)
            pl(tri, Clip([(0, 0.4, m(r), 92), (1.5, 0.4, m(r), 70), (2, 0.4, m(r) + 7, 80), (3.5, 0.3, m(r) + 12, 66)],
                         length=4), pos, vel=0.8 if under else 1.0)
            pl(nz, drums({90: 'x.x.x.x.x.x.x.x.', 74: '....x.......x...'}, vel=40 if under else 60), pos)
        # Konrad's tin-foil theremin (the ep2 colour): loud in the gaps, soft under the lines
        tline = notes('vel=84 D5/4 F5/8 G5/8 Ab5/2 | G5/4 F5/8 E5/8 D5/2 | F5/4 A5/8 Bb5/8 C#6/4 Bb5/4 | A5/1')
        for k in range(0, max(1, nb - 1), 4):
            split_lead(tline.arch(4, 0.4), mbar(bg_, k + 1, 1.0), ther, under=0.55)
        # stab on "GEFÄNGNIS!", the burp gated (stop window), the shrill cluster on "WER?!"
        ps(brass, [(0, 0.35, p, 108) for p in ('D3', 'A3', 'D4', 'F4')], T_PRISON)
        ps(ohit, [(0, 0.5, p, 100) for p in (50, 57, 62)], T_PRISON)
        ps(timp, [(0, 0.6, 'D3', 104)], T_PRISON)
        ps(trem, [(0, 0.9, p, 104) for p in ('D6', 'Eb6', 'E6', 'F6')], T_WHO)
        ps(sq, [(i * 0.04, 0.6, p, 92) for i, p in enumerate(('C#7', 'D7', 'Eb7'))], T_WHO)
        ps(kit, [(0, 1.0, 49, 96)], T_WHO)

    # ================================================================== 3 zap: the ray charges (rising whine)
    zp = g('zap')
    if zp:
        t0, t1 = T_RAY, T_ZAP
        # the whine climbs with the dial (legato glide), softener bubbles (harp + chip arps) speed up
        ps(wh, [(0.0, (t1 - t0) * 0.5, 'D4', 70), ((t1 - t0) * 0.45, (t1 - t0) * 0.35, 'A4', 80),
                ((t1 - t0) * 0.75, (t1 - t0) * 0.27, 'E5', 92)], t0)
        nb = int(zp.bars)
        for b in range(nb):
            pos = mbar(zp, b + 1)
            gr = (b + 1) / nb
            rate = 0.5 if b < nb / 2 else 0.25
            n = int(4 / rate)
            tones = ch('D5', 'F#5', 'A5', 'D6') if b % 2 == 0 else ch('E5', 'G5', 'B5', 'E6')
            arp.play(Clip([(i * rate, rate * 0.8, tones[i % 4] + 12 * (b >= nb - 1), int(50 + 40 * gr)) for i in range(n)],
                          length=4), pos)
            harp.play(Clip([(i * 0.5, 0.6, tones[(i * 3) % 4] - 12, int(40 + 30 * gr)) for i in range(8)], length=4), pos)
            nz.play(drums({90: 'x...x...x...x...' if b < nb - 1 else 'xxxxxxxxxxxxxxxx'}, vel=int(36 + 40 * gr)), pos)
        cele.play(Clip([(i * 0.25, 0.3, 86 + (i % 5) * 2, 44) for i in range(8)], length=2), mbar(zp, 1, 1.0))
        revcym.play(Clip([(0, 3.0, 60, 90)], length=4), s.beat_at(2.2, before=at(T_ZAP)))

    # ================================================================== 4 the ZAP + the suck into the screen
    sk = g('suck')
    if sk:
        hit(T_ZAP, pitches=(26, 38, 50, 57, 62), vel=120, ring=1.4)
        ps(sweep, [(0, 1.0, 96, 120)], T_ZAP)                      # white-noise burst
        auto(sweep, 'instrument.cutoff', [(at(T_ZAP - 0.05), 9000), (at(T_ZAP), 12000, 'step'),
                                             (at(T_ZAP + 0.9), 2000, 'exp')])
        n = int(sk.bars)
        for b in range(n):
            pos = mbar(sk, b + 1)
            arp.play(Clip([(i * 0.125, 0.11, ch('E5', 'B5', 'G5', 'D6', 'F#6', 'A5')[i % 6] + (i // 8) * 2, 70 + i)
                           for i in range(32)], length=4), pos)
            tri.play(Clip([(i * 0.5, 0.45, m('E2') + (i % 2) * 12, 90) for i in range(8)], length=4), pos)
            nz.play(drums({74: '1122334455667788'}, vel=70), pos)
        ps(sweep, [(0.9, T_VORTEX - T_ZAP - 0.9, 60, 80)], T_ZAP)
        ps(revcym, [(0, 2.0, 60, 90)], T_VORTEX - 2.0)

    # ================================================================== 5 the pixel vortex, 7/8, E Dorian
    vx = g('vortex')
    if vx:
        ps(kit, [(0, 1.2, 49, 104), (0, 0.3, 36, 100)], T_VORTEX)
        ps(boom, [(0, 1.5, 38, 104)], T_VORTEX)
        nb = int(vx.bars)
        vchords = [ch('E4', 'G4', 'B4', 'D5'), ch('A4', 'C#5', 'E5', 'F#5'), ch('E4', 'G4', 'B4', 'D5'), ch('D4', 'F#4', 'A4', 'C#5')]
        vroots = ['E2', 'A1', 'E2', 'D2']
        for b in range(nb):
            pos = mbar(vx, b + 1)
            v = vchords[b % 4]
            # 7/8 = 3.5 beats: arpeggio chords in 1/16 (2-2-3 grouping on the bass)
            arp.play(Clip([(i * 0.25, 0.22, (v + [v[0] + 12, v[2] + 12])[i % 6], 72 + (i in (0, 4, 8)) * 20)
                           for i in range(14)], length=3.5), pos)
            r = m(vroots[b % 4])
            tri.play(Clip([(0, 0.9, r, 100), (1.0, 0.9, r + 12, 86), (2.0, 0.4, r, 92), (2.5, 0.4, r + 7, 84),
                           (3.0, 0.4, r + 12, 88)], length=3.5), pos)
            kick.play(Clip([(0, 0.2, 40, 110), (1.0, 0.2, 40, 96), (2.0, 0.2, 40, 104)], length=3.5), pos)
            nz.play(Clip([(t, 0.1, 90, 70) for t in (0.5, 1.5, 2.5, 3.0)] + [(1.0, 0.15, 74, 96), (3.0, 0.15, 74, 90)],
                         length=3.5), pos)
        # the spinning lead with pitch bends (dives), loud only in the gaps
        vl = notes('vel=94 meter=7/8 B5/8 E6/8 D6/8 B5/8 A5/8. G5/16 A5/8 | B5/4 D6/8 E6/8 F#6/4. | '
                   'G6/8 F#6/8 E6/8 D6/8 B5/8 A5/8 B5/8 | E6/2..')
        split_lead(vl, vx.start, lead, lead2, under=0.6)
        auto(lead, 'instrument.pitchbend', _mono([(0, 0.0), (mbar(vx, 2, 2.4), 0.0), (mbar(vx, 2, 3.4), -2.0, 'smooth'),
                                                     (mbar(vx, 3), 0.0, 'step'), (mbar(vx, 4, 2.0), 0.0),
                                                     (mbar(vx, 4, 3.4), -12.0, 'smooth'), (vx.end, 0.0, 'step')]))
        # the bitcrusher: everything pixelates as they spiral in
        for trk in (arp, sq, lead):
            auto(trk, 'fx.bitcrush.downsample', [(0, 1.0), (vx.start, 1.0), (vx.end - 0.05, 22.0, 'exp'),
                                                    (vx.end, 1.0, 'step')])
        auto(nz, 'fx.bitcrush.downsample', [(0, 2.0), (vx.start, 2.0), (vx.end - 0.05, 20.0, 'exp'),
                                               (vx.end, 2.0, 'step')])

    # ================================================================== 6 landing: dead stop, plop-plop
    for k, (dt, p) in enumerate(((0.55, 'G3'), (0.95, 'D3'))):
        ps(tri, [(0, 0.12, p, 110), (0.12, 0.1, m(p) - 12, 90)], T_LAND + dt)
        ps(kick, [(0, 0.15, 40, 100)], T_LAND + dt)

    # ================================================================== 7/8 wild encounter: B minor (Dorian)
    textstop(TB_C1)
    textstop(TB_C2)
    stops.append((T_RONNY - 0.02, T_RONNY + 0.9))         # the second sting + Ronny's landing
    chip_stabs(T_TRANS, [m('B3'), m('D4'), m('F#4')])
    for name in ('wild', 'ronny'):
        x = g(name)
        if not x:
            continue
        nb = int(x.bars)
        wprog = [('Bm', 'B1'), ('Bm', 'B1'), ('E', 'E2'), ('A', 'A1')] if name == 'wild' else \
                [('Bm', 'B1'), ('G', 'G1'), ('E', 'E2'), ('F#', 'F#1')]
        for b in range(nb):
            pos = mbar(x, b + 1)
            sym, r = wprog[b % 4]
            r = m(r)
            under = talking(s.seconds(pos + 0.2))
            # surf bass in 3-3-2 on the triangle
            pl(tri, Clip([(0, 1.3, r, 100), (1.5, 1.3, r, 92), (3.0, 0.4, r + 7, 90), (3.5, 0.4, r + 12, 86)], length=4),
               pos, vel=0.85 if under else 1.0)
            pl(kick, Clip([(0, 0.2, 40, 100), (1.5, 0.2, 40, 90), (3.0, 0.2, 40, 94)], length=4), pos,
               vel=0.75 if under else 1.0)
            pl(nz, drums({90: 'x.xxx.xxx.xxx.xx', 74: '....x.......x..x'}, vel=44 if under else 66), pos)
            if not under:
                tones = {'Bm': ch('B4', 'D5', 'F#5'), 'E': ch('G#4', 'B4', 'E5'), 'A': ch('A4', 'C#5', 'E5'),
                         'G': ch('G4', 'B4', 'D5'), 'F#': ch('A#4', 'C#5', 'F#5')}[sym]
                pl(sq, Clip([(t, 0.2, p, 70) for t in (0.5, 2.0, 3.5) for p in tones], length=4), pos)
            if name == 'ronny':                       # Ronny's oompah touch
                pl(tuba, Clip([(0, 0.5, r - 12 if r >= 40 else r, 70), (2, 0.5, r + 7 - 12 if r >= 40 else r + 7, 62)],
                              length=4), pos)
        riff = notes('vel=96 F#5/8 F#5/16 A5/16 B5/8 r/8 D6/16 C#6/16 B5/8 A5/8 G#5/8 | F#5/4 r/8 E5/16 F#5/16 '
                     'A5/4 B5/4 | D6/8 C#6/8 B5/8 G#5/8 E5/8 G#5/8 B5/8 C#6/8 | A5/4 G#5/8 E5/8 F#5/2')
        for k in range(0, nb, 4):
            split_lead(riff.arch(4, 0.5), mbar(x, k + 1), lead, lead2, under=0.5, until=x_end(T_SEC, name))
    # C2: the second, shorter sting and the tuba "bwomp" for the belly landing
    chip_stabs(T_RONNY, [m('D4'), m('F#4')], step=0.1)
    ps(tuba, [(0, 0.5, 'F1', 118), (0.0, 0.5, 'C2', 90)], T_BELLY)
    ps(tuba, [(0, 0.6, 'E1', 110)], T_BELLY)
    auto(tuba, 'instrument.pitchbend', _mono([(0, 0.0), (at(T_BELLY), 0.0), (at(T_BELLY + 0.5), -3.0, 'smooth'),
                                                 (at(T_BELLY + 0.7), 0.0, 'step')]))
    ps(kick, [(0, 0.3, 36, 120)], T_BELLY)

    # ================================================================== 9 the NPC loop (identical audio) + line 14
    D13 = SPANS[13][1]
    npc_until = min(D13 + 0.25, L(14) - L(13) - 0.05, C('E3') - L(28) - 0.05 if 'E3' in CLIP_T else 99.0)

    def npc_loop(tl, until=npc_until, glitch_at=None, break_at=None):
        """Mandy's NPC music-box loop from tl (= her line start - NPC_PRE), the same notes in seconds every time.
        glitch_at / break_at (s after tl): stutter from there, tape-stop and break off at break_at."""
        ev, bev = [], []
        reps = int(_math.ceil((until + NPC_PRE) / NPC_LEN))
        for k in range(reps):
            for t, d, p in NPC_LOOP:
                tt = k * NPC_LEN + t
                if tt < until + NPC_PRE and (glitch_at is None or tt < glitch_at):
                    ev.append((tt, d * 0.95, p, 78 if t in (0.0, 2.0) else 64))
            for t, d, p in NPC_BASS:
                tt = k * NPC_LEN + t
                if tt < until + NPC_PRE and (glitch_at is None or tt < glitch_at):
                    bev.append((tt, d, p, 70))
        if glitch_at is not None:                 # the glitch: the same 1/8 fragment stuttering, faster
            frag = [x for x in NPC_LOOP if 1.0 <= x[0] < 1.5]
            t = glitch_at
            step = 0.25
            while t < break_at - 0.05:
                for k, (_, d, p) in enumerate(frag):
                    ev.append((t + k * step / 2, step / 2 * 0.9, p, 70))
                bev.append((t, step * 0.9, 'C5', 60))
                t += step
                step = max(0.07, step * 0.88)
        ps(mbox, ev, tl)
        ps(mbass, bev, tl)

    npc_loop(L(13) - NPC_PRE)
    # both loops must sound the same: the reverb returns are cut just before each loop (the previous scene's
    # tails would colour the first second) and come back after it
    rp = [(0, 0.0)]
    for lid in (13, 28):
        tl = L(lid) - NPC_PRE
        rp += [(at(tl - 0.12), 0.0), (at(tl - 0.01), -70.0), (at(L(lid) + npc_until), -70.0),
               (at(L(lid) + npc_until + 0.15), 0.0)]
    for bus in returns:
        bus.automate('gainDb', _mono(rp))
    # line 14 (Timo deadpan): a thin pulse of the wild riff's bass, then his decision ("muss ich dich fangen")
    if g('npc'):
        x = g('npc')
        t_after = L(13) + npc_until + 0.3
        for b in range(int(x.bars)):
            pos = mbar(x, b + 1)
            if s.seconds(pos) < t_after:
                continue
            pl(tri, Clip([(0, 0.4, m('B1'), 70), (1.5, 0.4, m('B1'), 60), (3, 0.4, m('F#2'), 60)], length=4), pos)
            pl(nz, drums({90: '..x...x...x...x.'}, vel=34), pos)
        ps(sq, [(0, 0.15, 'B4', 60), (0.16, 0.3, 'F#5', 66)], E(14) + 0.05)

    # ================================================================== 10 catch: Konrad backs away, the throw
    ct = g('catch')
    if ct:
        nb = int(ct.bars)
        for b in range(nb):
            pos = mbar(ct, b + 1)
            gr = (b + 1) / nb
            pl(trem, Clip([(0, 3.9, p, int(40 + 30 * gr)) for p in ch('F#3', 'C4')], length=4), pos, until=T_THROW)
            pl(pizz, Clip([(i, 0.3, m('F#2') + (i % 2) * 6, int(50 + 30 * gr)) for i in range(4)], length=4), pos,
               until=T_THROW)
            pl(nz, drums({90: 'x...x...x...x...'}, vel=int(30 + 30 * gr)), pos, until=T_THROW)
        ps(sq, [(0, 0.08, 'C6', 70), (0.1, 0.08, 'G6', 70)], TB_THROW[0])
        # the throw: whoosh up; the wobble ticks (growing silence) + our catch figure on the click
        ps(sweep, [(0, 0.5, 80, 90)], T_THROW)
        auto(sweep, 'instrument.cutoff', [(at(T_THROW - 0.02), 1200), (at(T_THROW), 800, 'step'),
                                             (at(T_THROW + 0.5), 6000, 'exp')])
        T = ball_times(3)
        click = T_THROW + T['click']
        if click <= T_FLAT - 0.2:                 # the whole throw is on screen: its own wobbles and the click
            for i in range(3):
                wobble_tick(T_THROW + T[f'wobble_{i}'], 96 - i * 6)
            catch_jingle(click, m('C5'))
        else:                                      # the cut (C5) comes before the click: the drawn wobbles that
            for i in range(3):                     # are still on screen, the click + catch figure on the cut
                tk = T_THROW + T[f'wobble_{i}']
                if tk < T_FLAT - 0.03:
                    wobble_tick(tk, 96 - i * 6)
            catch_jingle(T_FLAT - 0.02, m('C5'))

    # ================================================================== 11 the ball flat: tinny bossa, Eb major
    fl = g('flat')
    if fl:
        bprog = [ch('Eb3', 'G3', 'Bb3', 'D4'), ch('C3', 'Eb3', 'G3', 'Bb3'), ch('F3', 'Ab3', 'C4', 'Eb4'), ch('Bb2', 'D3', 'F3', 'Ab3')]
        broots = ['Eb2', 'C2', 'F2', 'Bb1']
        for b in range(int(fl.bars)):
            pos = mbar(fl, b + 1)
            v = bprog[b % 4]
            pl(nylon, Clip([(0, 0.4, v[0] - 12 if v[0] > 50 else v[0], 64)] + [(t, 0.3, p, 54) for t in (0.5, 1.5, 2.0, 3.0) for p in v[1:]],
                           length=4), pos, until=T_KNAST)
            pl(vibes, Clip([(0, 1.8, p + 12, 48) for p in v[1:]], length=4), pos, until=T_KNAST)
            pl(tuba, Clip([(0, 0.8, m(broots[b % 4]), 54), (2, 0.8, m(broots[b % 4]) + 7, 48)], length=4), pos,
               until=T_KNAST)
            pl(brush, drums({42: 'x.xx.xx.x.xx.xx.', 37: '...x.....x......'}, vel=36), pos, until=T_KNAST)
        split_lead(notes('vel=70 G5/4. Bb5/8 r/8 Ab5/8 G5/8 F5/8 | Eb5/2 r/2 | C6/4. Bb5/8 r/8 G5/8 Ab5/8 F5/8 | D5/2 r/2'),
                   mbar(fl, 1), vibes, under=0.65, until=T_KNAST)
        # the hard cut: "TROTZDEM EIN KNAST, TIMO!"
        ps(brass, [(0, 0.5, p, 112) for p in ('Eb3', 'A3', 'D4', 'G4')], T_KNAST)
        ps(timp, [(0, 0.5, 'D3', 108)], T_KNAST)
        ps(kit, [(0, 0.8, 49, 96)], T_KNAST)

    # ================================================================== 12 the beer fridge: throw 2 + chip oompah
    fr = g('fridge')
    if fr:
        T = ball_times(1)
        ps(sweep, [(0, 0.5, 80, 86)], T_THROW2)
        auto(sweep, 'instrument.cutoff', [(at(T_THROW2 - 0.02), 1200), (at(T_THROW2), 800, 'step'),
                                             (at(T_THROW2 + 0.5), 6000, 'exp')])
        click2 = min(T_THROW2 + T['click'], CLIP_END.get('C6', T_GRASS) - 0.3)
        wobble_tick(min(T_THROW2 + T['wobble_0'], click2 - 0.4), 92)
        catch_jingle(click2, m('F5'), short=True)
        t_oom = click2 + 0.7
        for b in range(int(fr.bars)):
            pos = mbar(fr, b + 1)
            if s.seconds(pos + 3.9) < t_oom:
                continue
            sym = ['F', 'C', 'C', 'F', 'Bb', 'F', 'C', 'F'][b % 8]
            r = {'F': m('F1'), 'C': m('C2'), 'Bb': m('Bb1')}[sym]
            tones = {'F': ch('F4', 'A4', 'C5'), 'C': ch('E4', 'G4', 'C5'), 'Bb': ch('F4', 'Bb4', 'D5')}[sym]
            pl(tri, Clip([(0, 0.4, r + 12, 96), (2, 0.4, r + 19, 88)], length=4), pos, after=t_oom)
            pl(sq, Clip([(bt, 0.25, p, 62) for bt in (1, 3) for p in tones], length=4), pos, after=t_oom)
            pl(kick, Clip([(0, 0.2, 40, 90), (2, 0.2, 40, 84)], length=4), pos, after=t_oom)
            pl(nz, drums({74: '....x.......x...'}, vel=50), pos, after=t_oom)
            pl(glock, Clip([(1.5, 0.2, 93, 50), (3.5, 0.2, 96, 44)], length=4), pos, after=t_oom)   # bottle clinks
        split_lead(notes('vel=86 C5/4 A4/8 C5/8 F5/4 A5/4 | G5/4. E5/8 C5/4 E5/4 | F5/8 G5/8 A5/8 Bb5/8 C6/4 A5/4 | '
                         'G5/2 r/2'), next((mbar(fr, b + 1) for b in range(int(fr.bars))
                                            if s.seconds(mbar(fr, b + 1)) >= t_oom - 0.05), fr.end), lead, lead2,
                   under=0.45, until=T_GRASS)

    # ================================================================== 13/14 tall grass (6/8, G Mixolydian) + Lintle
    gr_ = g('grass')
    if gr_:
        nb = int(gr_.bars)
        for b in range(nb):
            pos = mbar(gr_, b + 1)
            sym = ['G', 'F', 'G', 'C'][b % 4]
            r = {'G': m('G2'), 'F': m('F2'), 'C': m('C3')}[sym]
            tones = {'G': ch('G3', 'B3', 'D4'), 'F': ch('F3', 'A3', 'C4'), 'C': ch('C4', 'E4', 'G4')}[sym]
            # tiptoe: pizz + muted square plucks on the dotted beats, cricket hats
            pizz.play(Clip([(0, 0.4, r, 60), (1.5, 0.4, r + 7, 54)], length=3), pos)
            sq.play(Clip([(1.0, 0.12, tones[0] + 12, 46), (2.5, 0.12, tones[2] + 12, 42)], length=3), pos)
            nz.play(Clip([(i * 0.5, 0.05, 100, 26 + 8 * (i % 3 == 0)) for i in range(6)], length=3), pos)
        # the rustle builds over D2 into the POP
        ps(kit, [(i * 0.12, 0.1, 70, int(30 + i * 5)) for i in range(int(max(1, (T_POP - T_RUSTLE) / 0.12)))], T_RUSTLE)
        split_lead(notes('vel=64 meter=6/8 D5/8 r/8 E5/8 F5/4 E5/8 | D5/4. r/4. | B4/8 r/8 C5/8 D5/4 F5/8 | E5/4. D5/4.'),
                   mbar(gr_, 2), sq, under=0.5, until=T_RUSTLE)
    if g('lintle'):
        ps(nz, [(0, 0.06, 96, 110)], T_POP)
        ps(glock, [(0, 0.3, 'G6', 70)], T_POP)
        lintle(T_POP + 0.5, m('G5'), glock, vel=86, octave=1)              # first statement, sweet
        lintle(T_POP + 0.5, m('G5'), cele, vel=60)
        x = g('lintle')
        for b in range(int(x.bars)):
            pos = mbar(x, b + 1)
            sym = ['G', 'C', 'G', 'D'][b % 4]
            v = {'G': ch('G3', 'B3', 'D4'), 'C': ch('G3', 'C4', 'E4'), 'D': ch('F#3', 'A3', 'D4')}[sym]
            harp.play(Clip([(i * 0.5, 0.6, (v + [v[0] + 12, v[1] + 12, v[2] + 12])[i], 44) for i in range(6)], length=3), pos)
            strings.play(Clip([(0, 2.9, p, 40) for p in v], length=3), pos)
        lintle(E(20) + 0.02, m('G5'), cele, vel=58, octave=0)

    # ================================================================== 15 optimise: mad-scientist purr, G minor
    op = g('optimise')
    if op:
        nb = int(op.bars)
        gprog = [('Gm', 'G1'), ('Eb', 'Eb2'), ('Cm', 'C2'), ('D7', 'D2')]
        for b in range(nb):
            pos = mbar(op, b + 1)
            sym, r = gprog[b % 4]
            v = {'Gm': ch('G3', 'Bb3', 'D4'), 'Eb': ch('G3', 'Bb3', 'Eb4'), 'Cm': ch('G3', 'C4', 'Eb4'), 'D7': ch('F#3', 'C4', 'D4')}[sym]
            pl(strings, Clip([(0, 3.9, p - 12, 52) for p in v], length=4), pos, until=T_NO)
            pl(tuba, Clip([(0, 1.8, m(r), 56)], length=4), pos, until=T_NO)
            pl(block, Clip([(i, 0.1, 76 if i % 2 else 77, 44) for i in range(4)], length=4), pos, until=T_NO)   # dial clicks
        split_lead(notes('vel=80 G4/4 Bb4/8 D5/8 Gb5/2 | F5/4 Eb5/8 D5/8 C#5/2 | D5/4 G5/8 Bb5/8 A5/4 F#5/4 | G5/1')
                   .arch(4, 0.4), mbar(op, 1, 1.0), ther, under=0.5, until=T_NO)
        # "Nein!": a stop - one pizz + cymbal choke, then the riser into the first evolution
        ps(pizz, [(0, 0.3, p, 90) for p in ('G2', 'D3', 'Bb3')], T_NO)
        ps(revcym, [(0, T_EVO1 - T_NO, 60, 80)], T_NO + 0.1)
        ps(trem, [(0, T_EVO1 - T_NO - 0.2, p, 60) for p in ('G3', 'Db4')], T_NO + 0.3)

    # ================================================================== 16-19 evolutions (the Lintle riser)
    def evo_riser(t0, t1, root, track, base_vel=60, dirty=False):
        """The Lintle motif repeated, faster and higher each time, from t0 to the flash at t1."""
        t, spb, k = t0, 0.32, 0
        while t < t1 - 0.12:
            spb_k = max(0.045, spb * (0.82 ** k))
            dur = 3 * spb_k
            if t + dur > t1:
                break
            lintle(t, root + min(12, k), track, vel=min(122, base_vel + 8 * k), spb=spb_k)
            lintle(t, root + min(12, k) - 12, arp, vel=min(110, 50 + 8 * k), spb=spb_k)
            if dirty:
                lintle(t, root + min(12, k) - 24, gtr, vel=min(110, 60 + 6 * k), spb=spb_k)
            t += dur
            k += 1
        ps(sweep, [(0, t1 - t0, 72, 90)], t0)
        auto(sweep, 'instrument.cutoff', [(at(t0 - 0.02), 1200), (at(t0), 500, 'step'), (at(t1), 12000, 'exp'),
                                             (at(t1 + 0.05), 1200, 'step')])
        ps(trem, [(0, t1 - t0, p, 70) for p in (root - 12, root - 6)], t0)
        ps(kit, [(i * 0.1, 0.1, 38, int(40 + 70 * i * 0.1 / (t1 - t0))) for i in range(int((t1 - t0) / 0.1))], t0)

    if g('evo1'):
        textstop(_ov('D4', 'textbox', 0, default=T_EVO1 + 0.6), extra=0.0)
        evo_riser(T_PULSE1, T_FLASH1, m('G5'), glock)
        ps(cele, [(i * 0.07, 0.2, 86 + i, 50) for i in range(6)], T_EVO1 + 0.2)
    if g('lintroll'):
        hit(T_FLASH1, pitches=(31, 43, 50, 55, 59), vel=114, ring=1.0)
        # the motif on bassoon, stumbling (a late note, a cracked one)
        spb = 0.36
        ps(bsn, [(0.6, 0.18, 'D4', 84), (0.85, 0.34, 'B3', 80), (1.45, 0.16, 'E4', 86), (1.7, 0.1, 'Eb4', 70),
                 (1.82, 0.5, 'D4', 82)], T_FLASH1)
        ps(tuba, [(0.6, 0.3, 'G1', 70), (1.45, 0.3, 'D2', 64)], T_FLASH1)
        # under Konrad's line 23: low pedal, bassoon grumbles in the gaps, the small burp gated
        x = g('lintroll')
        for b in range(1, int(x.bars)):
            pl(strings, Clip([(0, 3.9, p, 44) for p in ch('G2', 'D3', 'Bb3')], length=4), mbar(x, b + 1))
        ps(brass, [(0, 0.3, p, 112) for p in ('G3', 'D4', 'G4', 'Bb4')], T_AGAIN)    # "NOCHMAL!"
        ps(timp, [(0, 0.4, 'G2', 110)], T_AGAIN)
    if g('evo2'):
        textstop(_ov('D5', 'textbox', 0, default=T_EVO2 + 0.4), extra=0.0)
        evo_riser(max(T_PULSE2, BURP23[1] + 0.1), T_FLASH2, m('G4'), bsn, base_vel=80, dirty=True)
    if g('gross'):
        hit(T_FLASH2, pitches=(24, 30, 36, 42, 47), vel=120, ring=2.2)
        ps(brass, [(0, 2.5, p, 100) for p in ('C2', 'F#2', 'C3', 'Db3')], T_FLASH2)
        # the gross-up: a wet trombone blat sagging down + a sustained horror chord
        ps(bone, [(0, 0.5, 'Bb1', 118), (0.55, 1.6, 'A1', 108)], T_GROSS)
        auto(bone, 'instrument.pitchbend', _mono([(0, 0.0), (at(T_GROSS + 0.55), 0.0), (at(T_GROSS + 2.1), -2.0, 'smooth'),
                                                     (at(T_GROSS + 2.3), 0.0, 'step')]))
        ps(trem, [(0, 3.0, p, 70) for p in ('C3', 'F#3', 'B3', 'F4')], T_GROSS)
        ps(organ, [(0, 3.0, p, 70) for p in ('C3', 'Db3', 'G3')], T_GROSS)
        # "Flusel?": the motif on solo tuba, tender
        lintle(L(24) - 0.05, m('G2'), tuba, vel=78, spb=0.42)
        ps(strings, [(0, 3.2, p, 40) for p in ('G3', 'B3', 'D4')], L(24) - 0.05)
    # D6 the slurp (sfx: space), Timo slimed, Konrad proud: tender Rhodes + strings
    sl = g('slimed')
    if sl:
        for b in range(int(sl.bars)):
            pos = mbar(sl, b + 1)
            if s.seconds(pos) < T_SLIME + 0.8:
                continue
            v = [ch('G3', 'B3', 'D4', 'F#4'), ch('E3', 'G3', 'B3', 'D4'), ch('C3', 'E3', 'G3', 'B3'), ch('D3', 'F#3', 'A3', 'C4')][b % 4]
            keys.play(Clip([(0, 3.8, p, 46) for p in v], length=4), pos)
            strings.play(Clip([(0, 3.9, p, 36) for p in v[1:]], length=4), pos)
        lintle(E(25) + 0.05, m('G4'), bsn, vel=60, spb=0.33)
        ps(glock, [(0, 0.4, 'B6', 50), (0.3, 0.6, 'D7', 46)], E(26) - 0.6)

    # ================================================================== 20 the gym: wrestling entrance, E minor
    gy = g('gym')
    if gy:
        hit(T_GYM, pitches=(28, 40, 47, 52, 55), vel=120, ring=0.9)
        hit(T_GYM + 1.4, pitches=(28, 40, 47, 52, 55), vel=112, ring=0.9, chip=False)
        ps(crowd, [(0, T_NPC2 - T_GYM, 60, 80)], T_GYM)
        crowd.automate('gainDb', [(0, 0.0), (at(T_GYM + 1.5), 0.0), (at(L(27)), -10.0, 'smooth'), (at(T_NPC2), -40.0, 'smooth')])
        nb = int(gy.bars)
        for b in range(nb):
            pos = mbar(gy, b + 1)
            r = m(['E2', 'E2', 'C2', 'D2'][b % 4])
            under = talking(s.seconds(pos + 0.2))
            # palm-muted power chords in 8ths (root + fifth), chant claps on 2 and 4, a triangle bass
            if s.seconds(pos + 3.9) < T_GYM + 1.5:
                continue                                  # the two pyro blasts first, then the riff
            pl(gtr, Clip([(i * 0.5, 0.3, p, 70 if i % 4 == 0 else 54) for i in range(8) for p in (r + 12, r + 19)], length=4),
               pos, vel=0.7 if under else 1.0, until=T_NPC2 - 0.05)
            pl(tri, Clip([(i * 0.5, 0.4, r, 86) for i in range(8)], length=4), pos, until=T_NPC2 - 0.05)
            pl(kit, drums({'kick': 'x.......x.x.....', 'clap': '....x.......x...'}, vel=60 if under else 80), pos,
               until=T_NPC2 - 0.05)
        # Kim's theme: a cocky 2-bar riff with a big bend (gaps loud)
        kim = notes('vel=100 E5/8 G5/8 A5/8 B5/4 r/8 D6/8 B5/8 | E6/2. r/4')
        for k in range(0, nb - 1, 2):
            split_lead(kim.arch(2, 0.5), mbar(gy, k + 1), lead, lead2, under=0.5, until=T_NPC2 - 0.05)
            auto(lead, 'instrument.pitchbend', _mono([(mbar(gy, k + 2) - 0.01, 0.0, 'step'), (mbar(gy, k + 2, 0.4), 0.0),
                                                         (mbar(gy, k + 2, 1.4), 2.0, 'smooth'),
                                                         (mbar(gy, k + 2, 3.0), 0.0, 'step')]))
        ps(brass, [(0, 0.25, p, 110) for p in ('E3', 'B3', 'E4', 'G4')], T_NPC2 - 0.05)   # the stop on "Würde"
    # ================================================================== 21 E2: the SAME NPC loop
    npc_loop(L(28) - NPC_PRE)

    # ================================================================== 22-30 the battle, A Dorian (stop-time)
    textstop(TB_E3)
    textstop(TB_COMPLAIN)
    stops.append((T_SWOLE - 0.02, T_SWOLE + 0.5))
    for tb in (TB_NOTEFF, TB_BENCH):
        stops.append((tb[0] - 0.04, type_end(*tb) + 0.1))

    def battle_bars(name, prog, vel=1.0, hero=0, lead_line=True):
        x = g(name)
        if not x:
            return
        nb = int(x.bars)
        for b in range(nb):
            pos = mbar(x, b + 1)
            sym, r = prog[b % len(prog)]
            r = m(r) + hero
            under = talking(s.seconds(pos + 0.2))
            v = 0.8 * vel if under else vel
            # the driving triangle: 8ths with octave pushes and a syncopated anticipation (not a classic ostinato)
            pl(tri, Clip([(0, 0.4, r, 100), (0.5, 0.3, r + 12, 80), (1.0, 0.4, r, 92), (1.5, 0.4, r + 10, 84),
                          (2.0, 0.3, r + 12, 86), (2.5, 0.4, r, 90), (3.0, 0.3, r + 7, 84), (3.5, 0.4, r + 12, 82)],
                         length=4), pos, vel=v)
            pl(kick, Clip([(0, 0.2, 40, 110), (1.5, 0.2, 40, 90), (2.5, 0.2, 40, 100)], length=4), pos, vel=v)
            pl(nz, drums({90: 'x.x.x.x.x.x.x.x.', 74: '....x.......x...', 96: '...............x'}, vel=int(70 * v)), pos)
            tones = {'Am': ch('A4', 'C5', 'E5'), 'D': ch('F#4', 'A4', 'D5'), 'G': ch('G4', 'B4', 'D5'),
                     'Em': ch('G4', 'B4', 'E5'), 'F': ch('F4', 'A4', 'C5')}[sym]
            if not under:
                pl(arp, Clip([(i * 0.25, 0.2, (tones + [tones[0] + 12])[i % 4] + hero, 64) for i in range(16)], length=4), pos)
            else:
                pl(sq, Clip([(t, 0.18, p + hero, 52) for t in (0.5, 2.5) for p in tones], length=4), pos)
        if lead_line:
            hook = notes('vel=98 E5/8 A5/8 r/8 B5/8 C6/4 B5/8 G5/8 | A5/4. E5/8 D5/4 E5/4 | G5/8 A5/8 r/8 C6/8 D6/4 '
                         'C6/8 A5/8 | B5/2 E5/2', transpose=hero)
            for k in range(0, nb, 4):
                split_lead(hook.arch(4, 0.5), mbar(x, k + 1), lead, lead2, under=0.45, until=x_end(T_SEC, name))

    BPROG = [('Am', 'A1'), ('D', 'D2'), ('Am', 'A1'), ('G', 'G1')]
    if g('battle'):
        ps(sq, [(0, 0.1, 'A4', 80), (0.1, 0.1, 'E5', 80)], T_BATTLE)
        hit(T_SWOLE, pitches=(33, 45, 52, 57, 60), vel=122, ring=1.4)          # the ball opens: SWOLE!
        hit(L(30), pitches=(33, 45, 52, 57, 64), vel=112, ring=0.8, crash=False)   # "MUSKELMOPS!"
        battle_bars('battle', BPROG)
    battle_bars('battle2', BPROG, vel=0.85)
    # "RONNY setzt MECKERN ein!": a sad oompah polka under his rant (A minor, accordion + tuba)
    pk = g('polka')
    if pk:
        for b in range(int(pk.bars)):
            pos = mbar(pk, b + 1)
            sym = ['Am', 'E7', 'E7', 'Am'][b % 4]
            r = m('A1') if sym == 'Am' else m('E1')
            tones = ch('A3', 'C4', 'E4') if sym == 'Am' else ch('G#3', 'B3', 'D4')
            pl(tuba, Clip([(0, 0.5, r, 76), (1, 0.5, r + 7, 64), (2, 0.5, r, 72), (3, 0.5, r + 7, 62)], length=4), pos,
               after=TB_COMPLAIN[0] + 0.6)
            pl(acc, Clip([(bt, 0.3, p, 54) for bt in (0.5, 1.5, 2.5, 3.5) for p in tones], length=4), pos,
               after=TB_COMPLAIN[0] + 0.6)
        auto(acc, 'instrument.pitchbend', _mono([(0, 0.0), (at(E(32) - 1.2), 0.0), (at(E(32)), -1.0, 'smooth'),
                                                    (at(E(32) + 0.2), 0.0, 'step')]))
    # "Das ist nicht sehr effektiv...": wah-wah trombone
    t = TB_NOTEFF[0]
    box_pop(t, 70)
    ps(mute, [(0, 0.3, 'Bb3', 92), (0.32, 0.3, 'A3', 88), (0.64, 0.3, 'Ab3', 86), (0.96, 0.5, 'G3', 84)], t)
    auto(mute, 'instrument.pitchbend', _mono([(0, 0.0), (at(t + 0.96), 0.0), (at(t + 1.4), -0.8, 'smooth'),
                                                 (at(t + 1.5), 0.0, 'step')]))
    # "BANKDRÜCKEN": three grunt hits
    for k in range(3):
        tk = TB_BENCH[0] + k * 0.26
        if tk < T_TAUNT - 0.05:
            ps(brass, [(0, 0.18, p, 100 + 6 * k) for p in ('A2', 'E3', 'A3')], tk)
            ps(timp, [(0, 0.3, 'A2', 100 + 6 * k)], tk)
            ps(kick, [(0, 0.2, 40, 110)], tk)
    # "RONNY wurde besiegt!" (on screen only if before the cut): the descending 3-note chip figure, then the snore
    tf = TB_FAINT[0] if TB_FAINT[0] and TB_FAINT[0] < CLIP_END.get('E4', T_TAUNT) - 0.3 else T_TAUNT + 0.05
    ps(lead, [(0, 0.12, 'E5', 90), (0.14, 0.12, 'C5', 86), (0.28, 0.4, 'A4', 82)], tf)
    ps(tuba, [(0.8, 0.9, 'E1', 50)], tf)
    stops.append((tf, L(33) + 0.1))
    battle_bars('taunt', [('Am', 'A1'), ('F', 'F1'), ('Am', 'A1'), ('Em', 'E1')], vel=0.75, lead_line=False)
    # the hero key change (up a 4th: D Dorian) on Timo's line 34
    hit(T_HERO, pitches=(38, 50, 57, 62, 66), vel=104, ring=0.6, crash=True, stab=False)
    battle_bars('hero', BPROG, vel=0.9, hero=5)
    ps(sq, [(0, 0.06, 'D6', 80), (0.07, 0.06, 'A6', 80)], T_MENU)
    # E6 "Los, OPA!": Konrad pops out - the Konrad hook as chiptune, then "Mit Vergnügen" ... BURP: OFF
    gp = g('grandpa')
    if gp:
        textstop(TB_GO, extra=0.0)
        hit(T_GRANDPA, pitches=(38, 50, 57, 62, 65), vel=110, ring=0.6, stab=False)
        kl = notes(f'vel=104 {KONRAD}')
        split_lead(kl, at(type_end(*TB_GO) + 0.05), lead, lead2, under=0.6, until=BURP35[0])
        split_lead(kl.transpose(-12), at(type_end(*TB_GO) + 0.05), sq, None, under=0.6, until=BURP35[0])
        for b in range(int(gp.bars)):
            pos = mbar(gp, b + 1)
            pl(tri, Clip([(i * 0.5, 0.4, m('D2') + (12 if i % 2 else 0), 80) for i in range(8)], length=4), pos,
               until=BURP35[0] - 0.05)
            pl(nz, drums({90: 'x.x.x.x.x.x.x.x.'}, vel=40), pos, until=BURP35[0] - 0.05)
        ps(revcym, [(0, 1.0, 60, 70)], BURP35[0] - 1.0)
    # burp end: "OPA setzt RÜLPSER ein!" -> "sehr effektiv!" the super-effective sting: crash + upward arpeggio
    t_sup = BURP35[1] + 0.15
    hit(t_sup, pitches=(38, 50, 57, 62, 66), vel=124, ring=1.0)
    ps(lead, [(i * 0.05, 0.08, p, 100) for i, p in enumerate(('D5', 'F#5', 'A5', 'D6', 'F#6', 'A6', 'D7'))], t_sup)
    ps(arp, [(i * 0.05, 0.08, p, 90) for i, p in enumerate(('A4', 'D5', 'F#5', 'A5', 'D6', 'F#6', 'A6'))], t_sup)
    if g('triumph'):
        x = g('triumph')
        for b in range(int(x.bars)):
            pos = mbar(x, b + 1)
            pl(tri, Clip([(i * 0.5, 0.4, m('D2') + (12 if i % 2 else 0), 96) for i in range(8)], length=4), pos,
               after=t_sup + 0.4, until=T_SOFT)
            pl(kick, Clip([(0, 0.2, 40, 110), (2, 0.2, 40, 100)], length=4), pos, after=t_sup + 0.4, until=T_SOFT)

    # ================================================================== 31 the softener: harp + celesta, 3/4 D major
    so = g('softener')
    if so:
        ps(glock, [(0, 0.6, 'A6', 100), (0, 0.6, 'D7', 92)], T_SOFT)
        ps(cele, [(0, 0.8, 'D6', 96), (0, 0.8, 'A6', 90)], T_SOFT)
        ps(kit, [(0, 1.2, 81, 70)], T_SOFT)                                      # triangle ding
        ps(harp, [(i * 0.035, 1.2, p, 64 + i) for i, p in enumerate(ch('D3', 'F#3', 'A3', 'D4', 'F#4', 'A4', 'D5', 'F#5',
                                                                          'A5', 'D6', 'F#6', 'A6'))], T_SOFT)
        nb = int(so.bars)
        sprog = [ch('D4', 'F#4', 'A4'), ch('B3', 'D4', 'F#4'), ch('G3', 'B3', 'D4'), ch('A3', 'C#4', 'E4')]
        for b in range(nb):
            pos = mbar(so, b + 1)
            v = sprog[b % 4]
            harp.play(Clip([(0, 1.0, v[0] - 12, 52), (1, 0.6, v[1], 44), (2, 0.6, v[2], 44)], length=3), pos)
            strings.play(Clip([(0, 2.9, p, 40) for p in v], length=3), pos)
        split_lead(notes('vel=70 meter=3/4 A5/2 F#5/4 | D6/2. | B5/4 A5/4 F#5/4 | A5/2. | G5/2 E5/4 | B5/2 A5/4 | '
                         'F#5/4 E5/4 C#5/4 | D5/2.'), mbar(so, 1), cele, under=0.6)
        # Swolepug goes fluffy (the hp drains): little chime poofs
        for i in range(4):
            ps(cele, [(0, 0.3, m('A6') + i * 2, 50)], E(36) + 0.4 + i * 0.25)
    if g('fluffy'):
        ps(lead, [(0, 0.12, 'A5', 80), (0.14, 0.12, 'F#5', 76), (0.28, 0.5, 'D5', 72)], TB_FAINT2[0])
        ps(strings, [(0, TB_VICTORY[0] - TB_FAINT2[0] + 0.3, p, 46) for p in ('D4', 'F#4', 'A4', 'D5')], TB_FAINT2[0] + 0.3)
        ps(choir, [(0, TB_VICTORY[0] - TB_FAINT2[0], p, 40) for p in ('A3', 'D4', 'F#4')], TB_FAINT2[0] + 0.5)
    # the victory flourish (original, compressed to the time left before the door kick)
    tv = TB_VICTORY[0]
    room = max(0.6, (T_SNOOP or T_KICK) - tv - 0.1)
    sc = min(0.22, room / 6.0)
    ps(lead, [(0, sc, 'D5', 96), (sc, sc, 'A5', 96), (2 * sc, sc, 'G5', 92), (3 * sc, sc, 'B5', 96),
              (4 * sc, 2 * sc, 'D6', 104)], tv)
    ps(sq, [(4 * sc, 2 * sc, p, 80) for p in ('D5', 'F#5', 'A5')], tv)
    ps(tri, [(0, 2 * sc, 'D3', 90), (2 * sc, 2 * sc, 'G2', 90), (4 * sc, 2 * sc, 'D2', 96)], tv)

    # ================================================================== 31b the bridge (E8): why + where
    # the lights flicker (a power-down drop), then Konrad's paranoid tiptoe from the living room (pizz + tri bass +
    # his theremin in the gaps) as he follows the hum to the STAFF-ONLY door; a dead stop on Kim's "Halt!", the
    # tiptoe sneaks on from "...Nur für Personal!"; thinned to a held tremolo under "Natürlich." up to the kick
    sn = g('snoop')
    if sn:
        t_halt, t_go, t_nat = L(49), L(49) + 1.7, L(50) + 3.3
        ps(sweep, [(0, 0.9, 'C5', 70)], T_SNOOP)
        auto(sweep, 'instrument.cutoff', [(at(T_SNOOP), 3000), (at(T_SNOOP + 0.9), 300, 'exp')])
        ps(tri, [(0.35, 0.6, 'D2', 96), (0.35, 0.6, 'A1', 70)], T_SNOOP)          # the brown-out: the power sags
        ps(ohit, [(0.0, 0.4, p, 84) for p in (38, 45, 50)], T_SNOOP)              # the lights stutter: a stab
        ps(pizz, [(0.0, 0.3, p, 90) for p in ('D3', 'A3', 'D4')], T_SNOOP)
        dprog = [('Dm', 'D2'), ('Dm', 'D2'), ('Bb', 'Bb1'), ('A7', 'A1')]
        t_in = T_SNOOP + 1.1
        for b in range(int(sn.bars)):
            pos = mbar(sn, b + 1)
            sym, r = dprog[b % 4]
            tones = {'Dm': ch('D4', 'F4', 'A4'), 'Bb': ch('D4', 'F4', 'Bb4'), 'A7': ch('C#4', 'E4', 'G4')}[sym]
            under = talking(s.seconds(pos + 0.1))
            tip = Clip([(i * 0.5, 0.3, (tones + [tones[1] + 12])[i % 4], 60 - 14 * under) for i in range(8)], length=4)
            bas = Clip([(0, 0.4, m(r), 84), (1.5, 0.4, m(r), 64), (2, 0.4, m(r) + 7, 72), (3.5, 0.3, m(r) + 12, 60)],
                       length=4)
            hat = drums({90: 'x...x...x...x...'}, vel=30 if under else 44)
            for tr, c in ((pizz, tip), (tri, bas), (nz, hat)):
                pl(tr, c, pos, vel=0.8 if under else 1.0, after=t_in, until=t_halt - 0.05)
                pl(tr, c, pos, vel=0.8 if under else 1.0, after=t_go, until=t_nat)
        ps(pizz, [(0, 0.3, p, 96) for p in ('D3', 'A3', 'D4', 'F4')], t_halt)        # "Halt!": the freeze
        ps(kit, [(0, 0.3, 55, 60)], t_halt)
        tline = notes('vel=80 D5/4 F5/8 G5/8 Ab5/2 | G5/4 F5/8 E5/8 D5/2 | F5/4 A5/8 Bb5/8 C#6/4 Bb5/4 | A5/1')
        split_lead(tline.arch(4, 0.4), mbar(sn, 1, 2.0), ther, under=0.5, until=t_halt - 0.05)
        # "Natürlich.": the room goes quiet, one held low tremolo + the theremin's knowing slide, into the kick
        ps(trem, [(0, max(0.4, T_KICK - t_nat - 0.05), p, 50) for p in ('D3', 'A3')], t_nat)
        ps(ther, [(0.0, 0.5, 'A4', 70), (0.5, max(0.3, T_KICK - t_nat - 0.6), 'D5', 76)], t_nat)

    # ================================================================== 32 BallWorks: corporate jingle -> sour
    bw = g('ballworks')
    if bw:
        hit(T_KICK, pitches=(36, 48, 55, 60, 64), vel=118, ring=0.7, chip=False)
        for b in range(int(bw.bars)):
            pos = mbar(bw, b + 1)
            sym = ['C', 'F', 'G', 'C'][b % 4]
            v = {'C': ch('C4', 'E4', 'G4'), 'F': ch('C4', 'F4', 'A4'), 'G': ch('B3', 'D4', 'G4')}[sym]
            pl(uke, Clip([(t, 0.25, p, 62) for t in (0, 0.5, 1.5, 2, 2.5, 3.5) for p in v], length=4), pos)
            pl(tri, Clip([(0, 0.4, v[0] - 24, 80), (2, 0.4, v[2] - 24, 72)], length=4), pos)
            # the machine: wheel squeaks + conveyor clanks
            pl(block, Clip([(i * 0.5, 0.1, 76 + (i % 2), 46) for i in range(8)], length=4), pos)
            pl(nz, drums({60: 'x.......x.......', 84: '..x...x...x...x.'}, vel=52), pos)
        split_lead(notes('vel=80 E5/8 G5/8 C6/4 B5/8 A5/8 G5/4 | A5/8 F5/8 A5/8 C6/8 B5/2 | G5/8 F5/8 E5/8 D5/8 '
                         'G5/4 B4/4 | C5/2 r/2'), mbar(bw, 1, 0.5), whistle, glock, under=0.6)
    sr_ = g('sour')
    if sr_:
        # "BATTERIEN!": the jingle turns minor, slows into the hum of the wheels
        hit(T_BATT, pitches=(36, 48, 55, 60, 63), vel=104, ring=1.0, crash=False, chip=False)
        nb = int(sr_.bars)
        for b in range(nb):
            pos = mbar(sr_, b + 1)
            sym = ['Cm', 'Fm', 'G7', 'Cm'][b % 4]
            v = {'Cm': ch('C4', 'Eb4', 'G4'), 'Fm': ch('C4', 'F4', 'Ab4'), 'G7': ch('B3', 'D4', 'F4')}[sym]
            pl(uke, Clip([(t, 0.25, p, 46) for t in (0, 1.5, 2.5) for p in v], length=4), pos, until=T_GLITCH)
            pl(strings, Clip([(0, 3.9, p - 12, 40) for p in v], length=4), pos, until=T_GLITCH)
            pl(block, Clip([(i, 0.1, 76, 36) for i in range(4)], length=4), pos, until=T_GLITCH)
            pl(tri, Clip([(0, 1.8, v[0] - 24, 64)], length=4), pos, until=T_GLITCH)
        split_lead(notes('vel=66 Eb5/8 G5/8 C6/4 B5/8 Ab5/8 G5/4 | Ab5/8 F5/8 Ab5/8 C6/8 B5/2 | G5/4 F5/4 Eb5/4 D5/4 | '
                         'C5/1'), mbar(sr_, 2), mute, None, under=0.55, until=T_GLITCH)
    # F3: the NPC loop glitches (stutter from the end of her first phrase, tape-stop, break at line 41 mid)
    r41 = RUNS.get(41) or []
    g_at = (r41[0][1] if r41 else 1.87) + NPC_PRE
    npc_loop(L(41) - NPC_PRE, until=T_BREAK - L(41), glitch_at=g_at, break_at=T_BREAK - L(41) + NPC_PRE)
    auto(mbox, 'instrument.pitchbend', _mono([(0, 0.0), (at(T_BREAK - 0.35), 0.0), (at(T_BREAK), -12.0, 'smooth'),
                                                 (at(T_BREAK + 0.05), 0.0, 'step')]))
    auto(mbass, 'instrument.pitchbend', _mono([(0, 0.0), (at(T_BREAK - 0.35), 0.0), (at(T_BREAK), -12.0, 'smooth'),
                                                  (at(T_BREAK + 0.05), 0.0, 'step')]))
    ps(nz, [(0, 0.08, 96, 110), (0.1, 0.06, 80, 90)], T_BREAK)
    # "Alles GELOGEN!": anger rising into the liberation
    ps(trem, [(0, T_FREE - T_BREAK - 0.3, p, 64) for p in ('C3', 'F#3', 'C4')], T_BREAK + 0.3)
    ps(kit, [(i * 0.125, 0.1, 38, int(36 + 4 * i)) for i in range(int(max(1, (T_FREE - T_BREAK - 1.0) / 0.125)))],
       T_BREAK + 1.0)

    # ================================================================== 33 the liberation: the anthem, D major
    lb = g('liberation')
    if lb:
        hit(T_FREE, pitches=(38, 50, 57, 62, 66), vel=116, ring=0.8)
        dt = T_KING - T_FREE
        n, t, step = 0, 0.0, 0.22                   # the chain of ball pops: accelerating 8ths
        while t < dt - 0.05:
            ps(nz, [(0, 0.05, 94 + (n % 3) * 3, 80 + min(40, n * 2))], T_FREE + t)
            ps(sq, [(0, 0.05, m('D6') + (n * 7) % 12, 60)], T_FREE + t)
            t += step
            step = max(0.06, step * 0.93)
            n += 1
        ps(strings, [(0, dt, p, 70) for p in ('D4', 'F#4', 'A4', 'D5')], T_FREE)
        ps(choir, [(0, dt, p, 60) for p in ('A3', 'D4', 'F#4')], T_FREE + 0.1)
        ps(tri, [(i * dt / 8, dt / 8 * 0.9, 'D2' if i % 2 == 0 else 'D3', 96) for i in range(8)], T_FREE)
        ps(lead, [(0, 0.2, 'F#5', 96), (0.25, 0.2, 'A5', 96), (0.5, 0.45, 'D6', 104), (1.0, 0.2, 'E6', 100),
                  (1.25, 0.2, 'F#6', 104), (1.5, dt - 1.55, 'A6', 110)], T_FREE)

    # ================================================================== 34 the Sock King: choir + organ, Sock War
    kg = g('sockking')
    if kg:
        hit(T_KING, pitches=(26, 38, 50, 57, 62), vel=120, ring=2.0, chip=False)     # the banner falls / it cracks
        hold = max(1.0, T_OHNO - T_KING - 0.2)          # everything grand stops before "Oh nein."
        ps(organ, [(0, hold, p, 84) for p in ('D3', 'A3', 'D4', 'F4')], T_KING + 0.1)
        ps(choir, [(0, hold / 2, p, 74) for p in ('D4', 'F4', 'A4')] +
           [(hold / 2, hold / 2 - 0.2, p, 78) for p in ('Eb4', 'G4', 'Bb4')], T_KING + 0.1)
        # the Sock War theme (phrase A) as a grand cadence on choir + brass, compressed to fit before "Oh nein."
        room = max(1.5, T_OHNO - (T_KING + 0.6) - 0.1)
        line = notes(f'vel=96 {SOCKWAR}')
        if room / line.length < 0.33:                  # too little room: phrase A's first half + the cadence
            line = notes('vel=96 D5/2 F5/4 E5/8 D5/8 | A5/2. r/4')
        spb = min(0.5, room / line.length)
        ps(brass, [(n.start * spb, n.dur * spb * 0.95, n.pitch - 12, n.vel) for n in line], T_KING + 0.6)
        ps(choir, [(n.start * spb, n.dur * spb * 0.95, n.pitch, n.vel - 20) for n in line], T_KING + 0.6)
        ps(timp, [(spb * k, 0.5, p, 100) for k, p in ((0, 'D3'), (4, 'A2'), (8, 'D3'), (12, 'A2')) if k < line.length],
           T_KING + 0.6)
        # "Oh nein. IHR schon wieder.": everything deflates on a trombone slide; the lid clang as the button
        ps(bone, [(0, 1.2, 'A2', 104)], T_OHNO)
        ps(pizz, [(0, 0.3, p, 96) for p in ('D2', 'A2', 'D3')], T_OHNO)
        ps(timp, [(0, 0.5, 'A2', 90)], T_OHNO)
        auto(bone, 'instrument.pitchbend', _mono([(0, 0.0), (at(T_OHNO + 0.1), 0.0), (at(T_OHNO + 1.2), -7.0, 'smooth'),
                                                     (at(T_OHNO + 1.3), 0.0, 'step')]))
        ps(tuba, [(0.2, 1.0, 'D2', 70)], T_OHNO)
        t_clang = min(E(43) + 0.08, T_REVERSE - 0.3)
        ps(glock, [(0, 0.5, 'C#6', 100), (0, 0.5, 'G6', 90)], t_clang)
        ps(kit, [(0, 0.6, 55, 96)], t_clang)

    # ================================================================== 35 the vortex in reverse -> home
    rv = g('reverse')
    if rv:
        nb = int(rv.bars)
        for b in range(nb):
            pos = mbar(rv, b + 1)
            arp.play(Clip([(i * 0.125, 0.11, ch('A6', 'F#6', 'D6', 'B5', 'G5', 'E5')[i % 6] - (i // 8) * 2, 90 - i)
                           for i in range(32)], length=4), pos)
            tri.play(Clip([(i * 0.5, 0.45, m('E3') - i, 80) for i in range(8)], length=4), pos)
        for trk in (arp,):
            auto(trk, 'fx.bitcrush.downsample', [(rv.start - 0.01, 1.0, 'step'), (rv.start, 22.0, 'step'),
                                                    (rv.end - 0.1, 1.0, 'exp')])
        ps(sweep, [(0, T_HOME - T_REVERSE, 90, 90)], T_REVERSE)
        auto(sweep, 'instrument.cutoff', [(at(T_REVERSE - 0.02), 1200), (at(T_REVERSE), 12000, 'step'),
                                             (at(T_HOME), 500, 'exp')])
    hm = g('home')
    if hm:
        ps(keys, [(0, 2.5, p, 58) for p in ('F3', 'A3', 'C4', 'E4')], T_HOME)
        ps(harp, [(i * 0.05, 1.0, p, 50) for i, p in enumerate(('F4', 'A4', 'C5', 'F5', 'A5'))], T_HOME)
        lintle(L(44) - 0.05, m('C3'), tuba, vel=80, spb=0.36)
        lintle(L(44) - 0.05, m('C5'), keys, vel=56, spb=0.36)
        ps(tuba, [(0, 0.5, 'F1', 110)], E(44) + 0.05)                                   # squash!
        auto(tuba, 'instrument.pitchbend', _mono([(0, 0.0), (at(E(44) + 0.1), 0.0), (at(E(44) + 0.5), -2.0, 'smooth'),
                                                     (at(E(44) + 0.6), 0.0, 'step')]))
    # ================================================================== 36 tag: three hours later
    tg = g('tag')
    if tg:
        ps(sq, [(0, 0.08, 'C5', 104), (0.1, 0.08, 'G5', 100), (0.2, 0.08, 'E5', 100), (0.3, 0.3, 'C6', 110)], TB_CARD[0])
        ps(lead, [(0, 0.08, 'C6', 100), (0.3, 0.3, 'G6', 104)], TB_CARD[0])
        ps(tri, [(0, 0.1, 'C3', 100), (0.3, 0.3, 'C3', 96)], TB_CARD[0])
        ps(kick, [(0, 0.15, 40, 110)], TB_CARD[0])
    # the handheld bleep loop (diegetic: Konrad playing) from the card to the end, under the stop too
    t0 = TB_CARD[0] + 1.0
    ev, k = [], 0
    pat = ['E6', 'G6', 'C7', 'G6', 'F6', 'A6', 'D7', 'B6']
    t = t0
    while t < T_ANT - 0.1:
        ev.append((t - t0, 0.06, pat[k % 8], 66 if k % 4 == 0 else 50))
        t += 0.2
        k += 1
    ps(bleep, ev, t0)
    for name in ('tag', 'plead'):
        x = g(name)
        if not x:
            continue
        for b in range(int(x.bars)):
            pos = mbar(x, b + 1)
            if s.seconds(pos) < TB_CARD[0] + 0.8 and name == 'tag':
                continue
            v = [ch('F3', 'A3', 'C4', 'E4'), ch('D3', 'F3', 'A3', 'C4'), ch('Bb2', 'D3', 'F3', 'A3'), ch('C3', 'E3', 'G3', 'Bb3')][b % 4]
            pl(keys, Clip([(0, 3.6, p, 44) for p in v], length=4), pos)
    ps(pizz, [(0, 0.3, 'C3', 70)], T_STOP)                                             # "Opa. Essen. Sofort." stop
    # the ant: the ep2 theremin wink + a final 8-bit chord
    box_pop(T_ANT, 96)
    ps(ther, [(0.0, 0.2, 'D5', 74), (0.22, 0.2, 'F5', 72), (0.44, 0.2, 'E5', 70), (0.66, 0.2, 'D5', 70),
              (0.88, 1.0, 'A5', 76)], T_ANT + 0.15)
    ps(pizz, [(0.0, 0.25, 'D3', 70), (0.44, 0.25, 'A2', 52), (0.88, 0.25, 'D3', 56)], T_ANT)
    t_fin = T_ANT + 2.1
    ps(sq, [(0, 1.4, p, 84) for p in ('F4', 'A4', 'C5')], t_fin)
    ps(lead, [(0, 1.4, 'F5', 90)], t_fin)
    ps(tri, [(0, 1.4, 'F2', 100)], t_fin)
    ps(keys, [(0, 1.8, p, 52) for p in ('F3', 'C4', 'A4')], t_fin)
    ps(nz, [(0, 0.1, 90, 90)], t_fin)

    for (tid, target), (trk, pts_) in lanes.items():
        trk.automate(target, _mono(pts_))
    # ------------------------------------------------------------------ master: the burp gates, the end
    pts = [(0, 0.0)]
    for b0, b1 in sorted(GATES):
        pts += [(at(b0 - 0.04), 0.0), (at(b0), -80.0), (at(b1 + 0.05), -80.0), (at(b1 + 0.12), 0.0)]
    end_fade = at(min(t_fin + 1.2, T_END - 0.5))
    pts += [(end_fade, 0.0), (at(T_END) - 0.001, -50.0, 'smooth')]
    s.master.automate('gainDb', _mono(pts))
    return s


def x_end(T_SEC, name):
    return T_SEC.get(name, (0, T_END))[1]


def _mono(points):
    """Automation points sorted, later duplicates of a beat dropped (re-synced timings may make them touch)."""
    out = []
    for p in sorted(points, key=lambda q: q[0]):
        if not out or p[0] > out[-1][0] + 1e-6:
            out.append(p)
    return out
