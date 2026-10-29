"""The Smog Monster - the 215.4-second background score for episode 3 of the Grandpa Konrad & Timo cartoon.

Laid out like songs/operation-no-wifi-3min (episode 2): every scene / story beat is a section whose tempo is set so
its first downbeat lands exactly on the picture anchor, the hits sit on the story beats, the melodic lead plays
loud only in the dialogue gaps (split_lead: notes under a line move to a softer voice / velocity) and the bed stays
thin under the voices (assemble.py also side-chain ducks the music under the dialogue). The song ends at the
episode length (tail 0).

Timing: song.py reads ep3_grill/build/timeline.json, manifest.json (clip anchors) and sfx.json at every build
(snapshot fallback inside) and measures Timo's last cough in voice/line_35.wav. The table below is the layout at
the first composition (timeline 21:46, total 215.366; built again against the 21:57 timeline, total 217.177, where
line 35/36 moved +1.8 s so evening / button shift):

  garden     0.000 -  28.783  14 bars ~116.7 F major  A  oompah garden party, wheezy accordion + harmonica on the
                                                        coughs (Ronny's cough gross-up 11.6-14.6), "Prost!" button
  fence     28.783 -  51.890   9 bars ~93.5  D minor  B1 western standoff over the hedge: clip-clop, twang, whistle
                                                        calls in the gaps, showdown flourish after line 8
  entrance  51.890 -  57.572   2 bars ~84.5  F minor  C1 Oma's entrance: two heavy stomps, elephant tuba, chair groan
  croon     57.572 -  70.471   4 bars ~74.4  Bb major C2 Konrad the crooner: harp gliss, schmaltzy strings + violin
  serious   70.471 -  79.193   3 bars ~61.9  D minor  C3 Timo coughs, Konrad gets serious: low strings, horn motif
  machine   79.193 -  93.538   7 bars ~117.1 C minor  D1 mad-science reveal + build, stop-time on "Does it work?"
  pastoral  93.538 - 100.907   3 bars ~97.7  D major  D3 FWOOM -> clean blue sky: birdsong, flute, harp, strings
  panic    100.907 - 114.925   8 bars ~137   D minor  D4 the parents panic: the idyll sours, agitated strings
  reverse  114.925 - 123.575   4 bars ~111   C minor  D5 lever slam: record scratch + descending, then the suction
  rise     123.575 - 127.970   2 bars ~109.2 C minor  E2 the black cloud rises (ember eyes): roar hit, low brass
  monster  127.970 - 156.165  16 bars ~136.2 C minor  E3 monster action (brass, drums), stings in every line gap
  oma      156.165 - 172.733   5 bars ~72.4  F minor  F1 fork down, earth-shake, deadly calm suspense, build
  inhale   172.733 - 178.236   2 bars ~87.2           F3 the INHALE: everything rises ... CUT at the F4 cut
  burp     178.236 - 184.283   2 bars        silence  F4 the burp (line 30, 178.636 - 183.784): music gated out
  fanfare  184.283 - 188.725   2 bars ~108   F major     triumphant fanfare + applause, soft under "...That's my girl."
  evening  188.725 - 209.840  11 bars 3/4 ~93.8 F     G1 warm sentimental waltz (the garden theme), the proposal
  button   209.840 - 215.366   2 bars ~86.9  F major  G3 Timo's cough (line 36 + 3.65): comic button, the ep2
                                                        theremin wink for the tin-foil-hat ant, final chord

Re-sync when the timeline changes: just rebuild (python -m agentsound build songs/the-smog-monster); every anchor
is derived from the live files, the bar counts come from the target tempi (PLAN), the gap stings sit at absolute
seconds, the length = timeline total. Only a changed clip id / meaning in the manifest needs an edit here (CLIPS).

Build: python -m agentsound build songs/the-smog-monster
"""
from agentsound import *
from agentsound import vamod

METADATA = {'title': 'The Smog Monster (Score)', 'artist': 'AgentSound', 'genre': 'Soundtrack', 'year': 2026,
            'comment': 'cartoon score to picture, episode 3 (Grandpa Konrad & Timo), F major / C minor, 215.4 s'}
ANALYSIS = {'profile': 'film'}
COVER = {'style': 'synthwave', 'palette': 'midnight', 'title': 'THE SMOG MONSTER', 'subtitle': 'AgentSound',
         'seed': 3}

# ------------------------------------------------------------------ picture timing (read at build time)
# The score follows the episode files live: every build reads ep3_grill/build/timeline.json (line spans, total),
# ep3_grill/manifest.json (clip start anchors: line + offset) and ep3_grill/sfx.json (sfx offsets inside a clip),
# and measures Timo's final cough in voice/line_35.wav. When a file is missing the snapshot below (2026-10-13
# 21:46 / 21:51, total 215.365918) is used. Re-sync after a timeline change = just rebuild.
import json as _json
from pathlib import Path as _Path

EP = _Path('D:/Projekte/cartoon/ep3_grill')
_SNAP_TOTAL = 215.365918
_SNAP = [[5.0, 9.707313], [15.907313, 3.162521], [20.269834, 3.032979], [23.702813, 4.480313],
         [29.783126, 6.119542], [36.402668, 6.122792], [43.02546, 3.504417], [46.929877, 4.56],
         [53.289877, 4.081979], [57.871856, 5.661708], [64.133564, 5.837771], [71.471335, 3.021688],
         [75.293023, 3.699521], [80.192544, 6.860021], [87.452565, 1.177104], [89.029669, 4.30875],
         [95.938419, 4.568292], [101.306711, 4.865167], [106.471878, 3.652854], [110.524732, 4.464167],
         [117.788899, 5.185875], [125.374774, 2.395375], [131.570149, 6.012375], [139.182524, 4.224958],
         [145.007482, 5.105583], [151.513065, 4.4515], [158.564565, 6.24575], [166.410315, 2.622646],
         [169.632961, 3.002875], [178.635836, 5.147083], [187.182919, 0.941854], [190.724773, 4.338854],
         [195.863627, 2.877833], [200.34146, 2.930271], [204.071731, 0.317354], [206.189085, 4.176833]]
# clip anchors (line id, offset) and sfx offsets as of the 21:51 manifest / sfx.json
_SNAP_CLIPS = {'A2': (1, -0.6), 'B1': (5, -1.0), 'C1': (9, -1.4), 'C2': (10, -0.3), 'C3': (12, -1.0),
               'D1': (14, -1.0), 'D2': (16, -0.3), 'D3': (17, -2.4), 'D4': (18, -0.4), 'D5': (20, -0.3),
               'E2': (22, -1.8), 'E3': (23, -3.6), 'F1': (27, -2.4), 'F3': (29, 3.1), 'F4': (30, -0.4),
               'G1': (32, -2.0)}
_SNAP_SFX = {'D2': 4.2, 'D5': 4.7, 'F1': 0.6}


def _load(path):
    try:
        return _json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


_tl = _load(EP / 'build' / 'timeline.json')
TIMING_SOURCE = 'timeline.json' if _tl else 'snapshot'
TOTAL = _tl['total'] if _tl else _SNAP_TOTAL
SPANS = {i + 1: (a, d) for i, (a, d) in enumerate(_tl['spans'] if _tl else _SNAP)}
CLIPS = dict(_SNAP_CLIPS)
_man = _load(EP / 'manifest.json')
if _man:
    for _ch in _man['episode']['chapters']:
        for _c in _ch['clips']:
            _st = _c.get('start') or {}
            if _c['id'] in CLIPS and 'line' in _st:
                CLIPS[_c['id']] = (_st['line'], _st.get('offset', 0.0))
SFX = dict(_SNAP_SFX)
for _x in (_load(EP / 'sfx.json') or []):
    if _x.get('clip') in SFX:
        SFX[_x['clip']] = _x['offset']


def L(i):
    """Start of line i (seconds)."""
    return SPANS[i][0]


def E(i):
    """End of line i (seconds)."""
    return SPANS[i][0] + SPANS[i][1]


def C(cid):
    """Start of a manifest clip (seconds)."""
    line, off = CLIPS[cid]
    return L(line) + off


def _last_burst(path, default):
    """Onset (s into the take) of the last sound burst in a voice line (Timo's final cough), or `default`."""
    try:
        import wave
        import numpy as np
        w = wave.open(str(path))
        sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype={2: np.int16, 4: np.int32}[sw]).astype(float)
        x = x.reshape(-1, ch).mean(1)
        hop = int(sr * 0.05)
        e = np.array([np.sqrt(np.mean(x[k * hop:(k + 1) * hop] ** 2)) + 1e-9 for k in range(len(x) // hop)])
        act = 20 * np.log10(e) > 20 * np.log10(e.max()) - 30
        k = len(act) - 1
        while k > 0 and not act[k]:
            k -= 1
        gap = 0
        while k > 0 and gap < 4:                 # walk back to the silence (>= 0.2 s) before the last burst
            gap = gap + 1 if not act[k] else 0
            k -= 1
        t = (k + gap + 1) * 0.05
        return t if 0.3 < t < len(x) / sr else default
    except Exception:
        return default


COUGH_IN_36 = _last_burst(EP / 'voice' / 'line_35.wav', 3.65)

T_B = C('B1')                    # B1 Finn over the hedge
T_C = C('C1')                    # C1 Oma sits down (chair groans)
T_CROON = C('C2')                # C2 Konrad melts
T_SERIOUS = C('C3')              # C3 Timo can't stop coughing
T_D = C('D1')                    # D1 the tarp comes off: the Clean-O-Matic
T_FWOOM_SFX = C('D2') + SFX['D2']  # sfx "machine FWOOM"
T_FWOOM = C('D3')                # D3 the clean-air dome: blue sky, birds (the music's FWOOM hit)
T_PANIC = C('D4')                # D4 the parents can't breathe
T_REV = C('D5') + SFX['D5']      # sfx "lever slams to REVERSE": record scratch
T_RISE = C('E2')                 # E2 the black cloud rises, roar
T_MONSTER = C('E3')              # E3 it eats the party (gross-up of the grill-grate mouth +0.2)
T_OMA = C('F1')                  # F1 Oma puts down her fork
T_SHAKE = T_OMA + SFX['F1']      # earth-shake sfx
T_INHALE = C('F3')               # F3 the INHALE (gross-up of her cheeks +1.1 .. +4.1)
T_BURP = C('F4')                 # F4 cut to the burp: music OFF
T_FANFARE = E(30) + 0.5          # after the burp + a beat of silence: fanfare + applause
T_EVENING = C('G1')              # G1 evening, the proposal
T_COUGH = L(36) + COUGH_IN_36    # Timo's final cough (measured in voice/line_35.wav)
T_RONNY_COUGH = C('A2') + 7.2    # Ronny's cough gross-up (3 s)
T_END = TOTAL

# (name, start, end, target bpm, beats per bar, bars or None = from the target tempo)
_PLAN = [('garden', 0.0, T_B, 116, 4, None), ('fence', T_B, T_C, 92, 4, None),
         ('entrance', T_C, T_CROON, 84, 4, 2), ('croon', T_CROON, T_SERIOUS, 72, 4, None),
         ('serious', T_SERIOUS, T_D, 62, 4, 3), ('machine', T_D, T_FWOOM, 120, 4, None),
         ('pastoral', T_FWOOM, T_PANIC, 92, 4, 3), ('panic', T_PANIC, T_REV, 136, 4, None),
         ('reverse', T_REV, T_RISE, 108, 4, 4), ('rise', T_RISE, T_MONSTER, 108, 4, 2),
         ('monster', T_MONSTER, T_OMA, 138, 4, None), ('oma', T_OMA, T_INHALE, 72, 4, 5),
         ('inhale', T_INHALE, T_BURP, 88, 4, 2), ('burp', T_BURP, T_FANFARE, 80, 4, 2),
         ('fanfare', T_FANFARE, T_EVENING, 108, 4, 2), ('evening', T_EVENING, T_COUGH, 96, 3, None),
         ('button', T_COUGH, T_END, 86, 4, 2)]
PLAN = []
for _n, _a, _b, _bpm, _bpb, _bars in _PLAN:
    _bars = _bars or max(1, round((_b - _a) * _bpm / 60.0 / _bpb))
    PLAN.append((_n, _a, _b, _bars, _bpb))

HITS = {'prost': E(4) + 0.15, 'fence': T_B, 'oma_stomp': T_C, 'croon': T_CROON, 'machine': T_D,
        'fwoom': T_FWOOM, 'reverse': T_REV, 'rise': T_RISE, 'monster': T_MONSTER, 'shake': T_SHAKE,
        'burp_cut': T_BURP, 'fanfare': T_FANFARE, 'cough': T_COUGH}


def _mono(points):
    """Automation points sorted, later duplicates of a beat dropped (re-synced timings may make them touch)."""
    out = []
    for p in sorted(points, key=lambda q: q[0]):
        if not out or p[0] > out[-1][0] + 1e-6:
            out.append(p)
    return out


def bpm_of(a, b, bars, bpb):
    return bars * bpb * 60.0 / (b - a)


def mbar(section, n, beat=0.0):
    """Musical (1-based) bar n of a section: mbar(sec, 1) = its first downbeat."""
    return section.bar(n - 1, beat=beat)


def root(sym, lo=29):
    """The chord root as a tuba / bass note in [lo, lo + 11]."""
    r = chord(sym).notes(2)[0]
    while r < lo:
        r += 12
    while r >= lo + 12:
        r -= 12
    return r


def triad(sym, lo=53, n=3):
    """The chord's first n tones folded into [lo, lo + 12)."""
    out = []
    for t in chord(sym).notes(4)[:n]:
        while t < lo:
            t += 12
        while t >= lo + 12:
            t -= 12
        out.append(t)
    return sorted(out)


# the garden theme (cheesy Schlager, F major) - A over F | C7 | C7 | F, B over F | Bb | C7 | F
THEME_A = 'C5/4 A4/8 C5/8 F5/4 A5/4 | G5/4. E5/8 C5/4 E5/4 | G5/4 Bb5/8 G5/8 E5/4 C5/4 | F5/2 r/2'
THEME_B = 'A5/4 C6/8 A5/8 F5/4 A5/4 | Bb5/4 D6/8 Bb5/8 F5/2 | G5/4 A5/8 G5/8 E5/4 C5/4 | F5/2. r/4'
PROG_A = ['F', 'C7', 'C7', 'F']
PROG_B = ['F', 'Bb', 'C7', 'F']
# the same theme as the evening waltz (3/4): F F C7 C7 Gm C7 F F | Bb C7 F
WALTZ = ('C5/2 A4/4 | F5/2 A5/4 | G5/2. | E5/2 C5/4 | D5/2 Bb4/4 | G5/2 Bb5/4 | A5/2. | r/2 C5/4 | '
         'D5/2 F5/4 | E5/2 G5/4 | F5/2.')
PROG_W = ['F', 'F', 'C7', 'C7', 'Gm', 'C7', 'F', 'F', 'Bb', 'C7', 'F']


def theremin():
    """Konrad's mad-science voice (the ep2 theremin)."""
    return inst.va(osc1__wave='sine', osc2__wave='triangle', osc2__level=0.35, osc2__fine=14,
                   drift__pitch=14, mode='mono', glide=0.11,
                   filter__type='lp12', cutoff=3200, resonance=0.05,
                   amp__attack=0.06, amp__decay=0.3, amp__sustain=0.95, amp__release=0.35, amp__velocity=0.9,
                   mods=[vamod.lfo('sine', hz=5.6, delay=0.15, fade=0.35, id='vib') >> ('pitch', 32)],
                   hpf=200, level=-5.0)


def scratch_synth():
    """Record scratch / zip: a resonant saw + square with a very fast glide (notes jumping = the scratch)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__semi=7, mode='mono', glide=0.05,
                   filter__type='lp12', cutoff=4200, resonance=0.5, filter__env=0.8, fenv__decay=0.3,
                   amp__attack=0.002, amp__decay=0.4, amp__sustain=0.7, amp__release=0.08, level=-8.0)


def suck_synth():
    """The suction / inhale sweep: a slow-gliding resonant saw (glide up = sucking in)."""
    return inst.va(osc1__wave='saw', osc2__wave='square', osc2__level=0.6, osc2__semi=7, mode='mono', glide=1.6,
                   filter__type='lp12', cutoff=2600, resonance=0.6, filter__env=0.6, fenv__decay=2.0,
                   amp__attack=0.4, amp__decay=1.5, amp__sustain=0.8, amp__release=0.3, level=-10.0)


def build() -> Song:
    s = Song('The Smog Monster (Score)', tempo=bpm_of(*PLAN[0][1:]), key='F major', seed=3, tail=0.0)
    sec = {}
    for name, a, b, bars, bpb in PLAN:
        sec[name] = s.section(name, bars=bars, meter=(3, 4) if bpb == 3 else None)
    for name, a, b, bars, bpb in PLAN[1:]:
        s.set_tempo(sec[name], bpm_of(a, b, bars, bpb))
    garden, fence, entrance, croon, serious = (sec[k] for k in ('garden', 'fence', 'entrance', 'croon', 'serious'))
    machine, pastoral, panic, reverse, rise = (sec[k] for k in ('machine', 'pastoral', 'panic', 'reverse', 'rise'))
    monster, oma, inhale, burp, fanfare = (sec[k] for k in ('monster', 'oma', 'inhale', 'burp', 'fanfare'))
    evening, button = sec['evening'], sec['button']

    def at(t):
        """The beat at an absolute picture time (seconds)."""
        return s.beat_at(t)

    def talking(t, pad=0.06):
        return any(a - pad <= t <= a + d + pad for a, d in SPANS.values())

    def split_lead(clip, pos, loud, soft=None, under=0.62):
        """Ducking-friendly lead: notes in the dialogue gaps play on `loud`, notes under a line on `soft` (or on
        `loud`) at `under` x velocity."""
        lo, so = [], []
        for n in clip:
            if talking(s.seconds(pos + n.start)):
                so.append((n.start, n.dur, n.pitch, max(1, int(n.vel * under))))
            else:
                lo.append((n.start, n.dur, n.pitch, n.vel))
        if lo:
            loud.play(Clip(lo, length=clip.length), pos)
        if so:
            (soft or loud).play(Clip(so, length=clip.length), pos)

    s.hall(), s.plate(), s.echo()
    s.master.use('master/synthwave')

    # ------------------------------------------------------------------ the band (mids kept open for dialogue)
    kit = s.track('drums', inst.sf2('Standard 1 Kit'), gain_db=-5, sends={'hall': -13},
                  fx=[fx.eq({'peak2.freq': 1200, 'peak2.gain': -3.0, 'peak2.q': 0.7, 'high.freq': 7000, 'high.gain': -5.0})]).humanize(3, 5)
    tuba = s.track('tuba', inst.sf2('Tuba'), gain_db=1.5, sends={'hall': -11})
    acc = s.track('accordion', inst.sf2('Accordion'), gain_db=0, pan=-0.2, sends={'hall': -9},
                  fx=[fx.chorus(mode='II', mix=0.35),
                      fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.6})])
    tpt = s.track('trumpet', inst.sf2('Trumpet'), gain_db=-6, pan=0.15, sends={'hall': -5})
    clar = s.track('clarinet', inst.sf2('Clarinet'), gain_db=-5, pan=0.1, sends={'hall': -5})
    harmo = s.track('harmonica', inst.sf2('Harmonica'), gain_db=-12, pan=-0.3, sends={'hall': -7})
    glock = s.track('glock', inst.sf2('Glockenspiel'), gain_db=-13, pan=0.3, sends={'hall': -3})
    block = s.track('woodblock', inst.sf2('Wood Block'), gain_db=-12, pan=0.35, sends={'hall': -11})
    gtr = s.track('twang', inst.sf2('Steel Guitar'), gain_db=-2, pan=-0.25, sends={'hall': -5, 'echo': -10})
    whistle = s.track('whistle', inst.sf2('Whistle'), gain_db=-9, pan=0.2, sends={'hall': -1, 'echo': -14})
    strings = s.track('strings', inst.sf2('Slow Strings'), gain_db=-4, sends={'hall': -3},
                      fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7}),
                          fx.chorus(mode='II', mix=0.5)])
    trem = s.track('tremolo', inst.sf2('Tremolo Strings'), gain_db=-5, pan=-0.1, sends={'hall': -5},
                   fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    pizz = s.track('pizz', inst.sf2('Pizzicato Strings'), gain_db=-2, pan=-0.15, sends={'hall': -7})
    violin = s.track('violin', inst.sf2('Violin'), gain_db=-5, pan=0.2, sends={'hall': -2})
    cbass = s.track('contrabass', inst.sf2('Double Bass'), gain_db=-2, sends={'hall': -11})
    harp = s.track('harp', inst.sf2('Orchestral Harp'), gain_db=-4, pan=-0.35, fx=[fx.chorus(mode='I', mix=0.4)], sends={'hall': -3})
    flute = s.track('flute', inst.sf2('Flute'), gain_db=-7, pan=0.25, sends={'hall': -3})
    birds = s.track('birds', inst.sf2('Birds'), gain_db=-16, pan=0.4, sends={'hall': -5})
    horns = s.track('horns', inst.sf2('French Horns'), gain_db=-8, pan=-0.1, sends={'hall': -3})
    brass = s.track('brass', inst.sf2('Brass Section'), gain_db=-8, pan=0.05, sends={'hall': -5},
                    fx=[fx.eq({'peak2.freq': 1800, 'peak2.gain': -3.0, 'peak2.q': 0.7})])
    bone = s.track('trombone', inst.sf2('Trombone'), gain_db=-6, pan=0.2, sends={'hall': -7})
    mute = s.track('mutetpt', inst.sf2('Muted Trumpet'), gain_db=-8, pan=0.25, sends={'hall': -7})
    harpsi = s.track('harpsichord', inst.sf2('Harpsichord'), gain_db=-9, pan=0.3, sends={'hall': -6})
    organ = s.track('organ', inst.sf2('Pipe Organ'), gain_db=-14, pan=-0.2, sends={'hall': -5},
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -5.0, 'peak2.q': 0.6})])
    lead = s.track('theremin', theremin(), gain_db=-6, pan=0.1, sends={'hall': -4, 'echo': -12},
                   fx=[fx.chorus(mode='II', mix=0.4)])
    celesta = s.track('celesta', inst.sf2('Celeste'), gain_db=-9, pan=0.2, sends={'hall': -1})
    vibes = s.track('vibes', inst.sf2('Vibraphone'), gain_db=-11, pan=-0.2, sends={'hall': -3})
    choir = s.track('choir', inst.sf2('Concert Choir'), gain_db=-11, sends={'hall': -1},
                    fx=[fx.eq({'peak2.freq': 1500, 'peak2.gain': -4.0, 'peak2.q': 0.7})])
    timp = s.track('timpani', inst.sf2('Timpani'), gain_db=-5, sends={'hall': -4})
    ohit = s.track('ohit', 'gm/orchestra_hit', gain_db=-9, sends={'hall': -7})
    boom = s.track('boom', 'synthwave/impact', gain_db=-11)
    revcym = s.track('revcym', inst.sf2('Reverse Cymbal'), gain_db=-12, sends={'hall': -7})
    applause = s.track('applause', inst.sf2('Applause'), gain_db=-12, sends={'hall': -9})
    zip_ = s.track('scratch', scratch_synth(), gain_db=-12, pan=-0.1)
    suck = s.track('suck', suck_synth(), gain_db=-14, sends={'hall': -5})

    def big_hit(pos, pitches=(29, 41, 53, 57, 60), ring=1.5, vel=118, crash=True, stab=True):
        """The episode hit: orchestra hit + impact + timpani + brass (+ kick and crash)."""
        ohit.play(Clip([(0, ring, p, vel) for p in pitches], length=4), pos)
        boom.play(Clip([(0, max(2.0, ring), 38, min(127, vel + 4))], length=4), pos)
        timp.play(Clip([(0, 1.5, pitches[0] + 12 if pitches[0] < 40 else pitches[0], min(127, vel))], length=4), pos)
        if stab:
            brass.play(Clip([(0, min(ring, 1.2), p, vel - 10) for p in pitches[2:]], length=4), pos)
        kit.play(drums({'kick': 'X', 'crash': 'X' if crash else '.'}, bars=1), pos)

    def oompah(sym, pos, vel=1.0, beats=4, acc_on=True, tuba_on=True, drums_on=True, lo=53):
        """Oom-pah: tuba root / fifth on the strong beats, accordion chord on the off beats, kick + snare."""
        r = root(sym)
        if beats == 4:
            if tuba_on:
                tuba.play(Clip([(0, 0.6, r, int(92 * vel)), (2, 0.6, r - 5 if r - 5 >= 26 else r + 7, int(84 * vel))],
                               length=4), pos)
            if acc_on:
                acc.play(Clip([(b, 0.35, p, int(70 * vel)) for b in (1, 3) for p in triad(sym, lo)], length=4), pos)
            if drums_on:
                kit.play(drums({'kick': 'x.......x.......', 'snare': '....o.......o...', 'hat': '....o.......o...'},
                               vel=int(50 * vel)), pos)
        else:
            if tuba_on:
                tuba.play(Clip([(0, 0.6, r, int(80 * vel))], length=3), pos)
            if acc_on:
                acc.play(Clip([(b, 0.4, p, int(58 * vel)) for b in (1, 2) for p in triad(sym, lo)], length=3), pos)

    # ================================================================== A: birthday in the soot (oompah)
    gb = int(garden.bars)
    for b in range(gb - 1):
        sym = (PROG_A + PROG_B + PROG_A + ['F'])[b % 13]
        intro = b < 2
        oompah(sym, mbar(garden, b + 1), vel=1.0 if intro else 0.8)
    for k, th in enumerate((THEME_A, THEME_B, THEME_A)):
        if 4 * k + 4 > gb - 1:
            break
        line = notes(f'vel=86 {th}').arch(4, 0.4)
        if k == 2:
            line = line.transpose(-12)
        split_lead(line, mbar(garden, 4 * k + 1), tpt, clar, under=0.72)
    # bar 13: a run-up on the clarinet (under line 4)
    if gb >= 14:
        clar.play(notes('vel=60 C5/8 D5/8 E5/8 F5/8 G5/8 A5/8 Bb5/8 C6/8'), mbar(garden, gb - 1))
    # wheeze: harmonica breaths and a sagging accordion on the coughs (Ronny's cough gross-up 11.6 - 14.6,
    # Mandy's "Cough. Cough." at the end of line 2)
    rc, mc = T_RONNY_COUGH, E(2) - 1.2
    for t, ch_ in ((rc + 0.1, (65, 69, 72)), (rc + 0.9, (64, 67, 70)), (rc + 1.8, (65, 69, 72)),
                   (mc, (64, 67, 70)), (mc + 0.6, (65, 68, 72))):
        harmo.play(Clip([(0, 0.55, p, 64) for p in ch_], length=1), at(t))
    acc.automate('instrument.pitchbend', _mono([(0, 0.0), (at(rc - 0.1), 0.0), (at(rc + 1.0), -0.7, 'smooth'),
                                          (at(rc + 3.0), 0.0, 'smooth'), (at(mc - 0.1), 0.0),
                                          (at(mc + 0.7), -0.5, 'smooth'), (at(mc + 1.4), 0.0, 'smooth')]))
    # "Prost!" (end of line 4): glasses clink, a ta-da on the band, a whistle pickup into the fence
    t_prost = E(4) + 0.1
    glock.play(Clip([(0, 0.3, 96, 80), (0.15, 0.4, 100, 74)], length=1), at(t_prost))
    pb = at(t_prost + 0.3)
    tuba.play(Clip([(0, 0.4, 29, 100), (0.5, 0.9, 41, 96)], length=2), pb)
    acc.play(Clip([(0, 0.3, p, 84) for p in (65, 69, 72)] + [(0.5, 0.9, p, 88) for p in (65, 69, 72, 77)],
                  length=2), pb)
    tpt.play(Clip([(0.5, 0.9, 77, 92)], length=2), pb)
    kit.play(drums({'kick': 'x.x.', 'crash': '..x.'}, step='1/8', vel=80), pb)

    # ================================================================== B: over the fence (western standoff)
    fb = int(fence.bars)
    fprog = ['Dm', 'Dm', 'Gm', 'Dm', 'Bb', 'A7', 'Dm', 'A7', 'Dm', 'Dm', 'A7', 'Dm']
    for b in range(fb):
        pos = mbar(fence, b + 1)
        sym = fprog[b % len(fprog)]
        r = root(sym, lo=38)
        last = b == fb - 1
        # clip-clop (a slow trot), the twang on the downbeat, a low tremolo pedal
        block.play(drums({76: 'x..x..x.x..x..x.' if not last else 'x..x..x.........'}, vel=48 + b * 2), pos)
        gtr.play(Clip([(0, 2.5, r - 12, 82), (2.5, 1.0, r - 5, 62)] if not last else [(0, 1.5, r - 12, 80)],
                      length=4), pos)
        trem.play(Clip([(0, 3.9, p, 44 + b * 3) for p in triad(sym, lo=50)], length=4), pos)
        kit.play(drums({'kick': 'x.......x.......'}, vel=40 + b * 3), pos)
    # the hedge: Finn's head pops up (a soft 'boing' + a flute 'om')
    glock.play(Clip([(0, 0.3, 86, 70), (0.25, 0.4, 93, 60)], length=1), fence.start)
    # whistle calls in the gaps between the lines (35.90-36.40, 42.53-43.03, 46.53-46.93)
    for t in (E(5) + 0.04, E(6) + 0.04, E(7) + 0.02):
        whistle.play(Clip([(0, 0.3, 74, 76), (0.33, 0.55, 81, 82)], length=1), at(t))
    # the duel: Ronny vs Finn, a tuba grunt before Ronny's lines, a flute 'om' before Finn's
    tuba.play(Clip([(0, 0.5, 26, 80)], length=1), at(L(6) - 0.42))
    flute.play(Clip([(0, 0.4, 74, 56)], length=1), at(L(7) - 0.42))
    # line 8 (Mandy shrieks): snare tremolo grows, then the showdown flourish in the gap before Oma
    kit.play(drums({'snare': '1122334455667788'}, vel=60), at(L(8) + 2.0))
    t_show = E(8) + 0.05
    tpt.play(notes('vel=96 A4/16 D5/16 F5/16 A5/16 D6/4'), at(t_show))
    gtr.play(Clip([(0, 1.0, 26, 92)], length=2), at(t_show))
    timp.play(Clip([(0, 0.5, 38, 90), (0.5, 0.5, 33, 96)], length=2), at(t_show))

    # ================================================================== C1: Oma's grand entrance
    # two heavy stomps (the chair groans), then the elephant walk on the tuba under "KONRAD!"
    for k, (t, v) in enumerate(((0.0, 120), (0.75, 108))):
        tuba.play(Clip([(0, 0.6, 29, v)], length=1), entrance.start + t)
        timp.play(Clip([(0, 0.8, 41, v)], length=1), entrance.start + t)
        boom.play(Clip([(0, 1.0, 38, v - 10)], length=1), entrance.start + t)
        cbass.play(Clip([(0, 0.6, 29, v - 20)], length=1), entrance.start + t)
    brass.play(Clip([(0, 0.7, p, 104) for p in (41, 48, 53, 56)], length=1), entrance.start)
    kit.play(drums({'kick': 'X..x', 'crash': 'x...'}, step='1/8', vel=90), entrance.start)
    walk = [(2.0, 0.8, 29, 74), (3.0, 0.8, 36, 66), (4.0, 0.8, 37, 70), (5.0, 0.8, 36, 64)]
    tuba.play(Clip(walk, length=8), entrance.start)
    pizz.play(Clip([(t, 0.3, p, 56) for t, p in ((2.0, 41), (3.0, 48), (4.0, 49), (5.0, 48))], length=8),
              entrance.start)
    # the chair groans (bar 2, beats 2.5-4): a trombone sagging down
    bone.play(Clip([(2.5, 1.4, 46, 76)], length=4), mbar(entrance, 2))
    bone.automate('instrument.pitchbend', [(0, 0.0), (mbar(entrance, 2, 2.6), 0.0),
                                           (mbar(entrance, 2, 3.9), -2.0), (croon.start, 0.0, 'step')])

    # ================================================================== C2: Konrad the crooner (schmaltz)
    harp.play(Clip([(i * 0.0625, 0.8, p, 60 + i) for i, p in
                    enumerate((46, 50, 53, 57, 58, 62, 65, 69, 70, 74, 77, 81, 82, 86))], length=4), croon.start)
    vibes.play(Clip([(0.9, 2.5, p, 66) for p in (70, 74, 77, 81)], length=4), croon.start)
    glock.play(Clip([(1.0, 0.4, 93, 54), (1.25, 0.4, 98, 50)], length=4), croon.start)
    cprog = [('Bb', (58, 62, 65, 69)), ('Gm', (58, 62, 65, 67)), ('Cm', (58, 63, 67, 70)), ('Bb', (58, 62, 65, 69))]
    for b in range(int(croon.bars)):
        sym, v = cprog[b % 4]
        pos = mbar(croon, b + 1)
        strings.play(Clip([(0, 3.9, p, 62 + (6 if b == 1 else 0)) for p in v], length=4), pos)
        cbass.play(Clip([(0, 1.8, root(sym, lo=34), 64), (2, 1.8, root(sym, lo=34) + 7, 56)], length=4), pos)
        harp.play(Clip([(i * 0.5 + 0.5 * (i // 4), 0.6, p, 52) for i, p in enumerate(v)], length=4), pos)
        kit.play(drums({'hat': '..o...o...o...o.', 'rim': '....o.......o...'}, vel=36), pos)
    # the solo violin sobs along (soft under the lines, out in the gaps)
    split_lead(notes('vel=78 F5/2 D6/4 C6/8 Bb5/8 | A5/2. G5/4 | Bb5/4 A5/4 G5/4 Eb5/4 | D5/1').arch(4, 0.5),
               mbar(croon, 1, 1.0), violin, under=0.7)
    # his small happy burp (end of line 10): a tuba blip
    tuba.play(Clip([(0, 0.25, 34, 72), (0.3, 0.3, 46, 60)], length=1), at(E(10) + 0.04))

    # ================================================================== C3: serious (Timo coughs)
    for b in range(int(serious.bars)):
        pos = mbar(serious, b + 1)
        strings.play(Clip([(0, 3.9, p, 50) for p in ((50, 57, 62) if b < 2 else (50, 58, 62))], length=4), pos)
        cbass.play(Clip([(0, 3.9, 26 if b < 2 else 34, 58)], length=4), pos)
        pizz.play(Clip([(0, 0.3, 38, 52), (0.5, 0.3, 38, 40)], length=4), pos)            # heartbeat
    celesta.play(Clip([(0, 0.5, 74, 52), (0.5, 0.5, 72, 48), (1.0, 1.0, 69, 46)], length=2), at(E(12) + 0.05))
    # Konrad decides: a low horn call, then a timpani roll into the machine
    horns.play(notes('vel=70 D3/4 F3/4 A3/2'), mbar(serious, 3, 0.5))
    timp.play(Clip([(i * 0.125, 0.125, 43, 44 + i * 4) for i in range(8)], length=1), at(E(13) + 0.02))
    revcym.play(Clip([(0, 3.0, 60, 80)], length=4), s.beat_at(2.0, before=machine.start))

    # ================================================================== D1/D2: the Clean-O-Matic (mad science)
    mprog = ['Cm', 'Cm', 'Ab', 'Fm', 'G7', 'Ab', 'G7', 'G7']
    mb = int(machine.bars)
    big_hit(machine.start, pitches=(36, 48, 55, 60, 63), ring=1.2, vel=112)
    for b in range(mb):
        pos = mbar(machine, b + 1)
        sym = mprog[b % len(mprog)]
        tones = triad(sym, lo=60)
        arp = tones + [tones[0] + 12] + tones[::-1]
        stopq = b == 4 and mb >= 7                 # "Does it work?" stop-time
        last = b == mb - 1
        grow = b / max(1, mb - 1)
        if stopq:
            block.play(Clip([(0, 0.2, 77, 60), (1, 0.2, 76, 56)], length=4), pos)
            glock.play(Clip([(1.6, 0.4, 79, 56), (1.9, 0.6, 83, 60)], length=4), pos)
            harpsi.play(Clip([(2.5 + i * 0.25, 0.22, arp[i % 7], 60 + i * 3) for i in range(6)], length=4), pos)
            continue
        harpsi.play(Clip([(i * 0.5, 0.45, arp[i % 7], int(62 + grow * 20)) for i in range(8)], length=4), pos)
        organ.play(Clip([(0, 3.9, t - 12, int(56 + grow * 20)) for t in tones], length=4), pos)
        pizz.play(Clip([(i * 0.5, 0.3, root(sym, lo=36), int(64 + grow * 20)) for i in range(8)], length=4), pos)
        if not last:
            kit.play(drums({'kick': 'x.......x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'},
                           vel=int(46 + grow * 26)), pos)
            timp.play(Clip([(0, 1, root(sym, lo=36), int(56 + grow * 30))], length=4), pos)
    lastm = mbar(machine, mb)
    kit.play(drums({'snare': '1122334455667788', 'kick': 'x...x...x.x.x.x.'}, vel=74), lastm)
    timp.play(Clip([(i * 0.25, 0.25, 43, 50 + i * 4) for i in range(16)], length=4), lastm)
    trem.play(Clip([(0, 3.9, p, 70) for p in (55, 59, 62, 65)], length=4), lastm)
    suck.play(Clip([(0, 0.05, 43, 50), (0.05, 3.8, 79, 64)], length=4), lastm)
    # Konrad's theremin motif (mad scientist), soft under line 14, out in the gaps
    split_lead(notes('vel=80 C5/4 Eb5/8 G5/8 C6/2 | B5/4 Ab5/4 G5/2 | Ab5/4 C6/8 Ab5/8 F5/4 Ab5/4 | '
                     'G5/2 B4/2').arch(4, 0.4), mbar(machine, 1, 1.0), lead, under=0.6)
    if mb >= 7:
        lead.play(notes('vel=86 G5/8 Ab5/8 B5/8 C6/8 D6/8 Eb6/8 F6/8 G6/8'), mbar(machine, mb - 1))

    # ================================================================== D3: FWOOM -> clean blue sky (pastoral)
    big_hit(pastoral.start, pitches=(38, 50, 54, 57, 62, 66), ring=2.0, vel=116)
    harp.play(Clip([(i * 0.0625, 1.2, p, 64 + i) for i, p in
                    enumerate((62, 66, 69, 74, 78, 81, 86, 90, 93))], length=4), pastoral.start)
    glock.play(notes('vel=76 D7/16 F#7/16 A7/16 D8/8'), pastoral.start + 0.25)
    pprog = [('D', (62, 66, 69, 74)), ('G', (62, 67, 71, 74)), ('A', (61, 64, 69, 73))]
    for b in range(int(pastoral.bars)):
        sym, v = pprog[b % 3]
        pos = mbar(pastoral, b + 1)
        strings.play(Clip([(0, 3.9, p, 64) for p in v], length=4), pos)
        cbass.play(Clip([(0, 3.9, root(sym, lo=38), 56)], length=4), pos)
        harp.play(Clip([(i * 0.5, 0.7, (v + tuple(p + 12 for p in v))[i], 54 + (i % 4 == 0) * 8)
                        for i in range(8)], length=4), pos)
    # birdsong (the dome): little chirps everywhere
    chirps = [(0.6, 88), (0.9, 91), (1.7, 86), (2.3, 93), (2.5, 90), (3.4, 88), (4.1, 95), (4.6, 91), (5.5, 89),
              (6.2, 94), (6.4, 91), (7.3, 87), (8.1, 92), (8.8, 90), (9.6, 94), (10.3, 89), (11.0, 92)]
    birds.play(Clip([(t, 0.25, p, 70) for t, p in chirps if t < pastoral.bars * 4 + 2.0], length=16),
               pastoral.start)
    split_lead(notes('vel=82 F#5/4 A5/8 B5/8 A5/2 | D6/4 C#6/8 B5/8 A5/4 F#5/4 | G5/4 F#5/8 E5/8 D5/2')
               .arch(3, 0.4), mbar(pastoral, 1, 1.0), flute, under=0.65)

    # ================================================================== D4: the parents panic, the idyll sours
    pb_ = int(panic.bars)
    # bar 1: the flute sours (bends flat), the birds stop with a squawk, strings slide into D minor
    flute.play(Clip([(0, 2.0, 74, 70)], length=4), panic.start)
    flute.automate('instrument.pitchbend', [(0, 0.0), (panic.start + 0.2, 0.0), (panic.start + 2.0, -1.0),
                                            (mbar(panic, 2), 0.0, 'step')])
    birds.play(Clip([(0, 0.2, 76, 90)], length=1), panic.start + 0.3)
    strings.play(Clip([(0, 3.9, p, 58) for p in (62, 65, 69)], length=4), panic.start)
    kprog = ['Dm', 'Dm', 'Bb', 'Gm', 'A7', 'Dm', 'Bb', 'A7', 'A7', 'A7']
    for b in range(1, pb_):
        sym = kprog[b % len(kprog)]
        pos = mbar(panic, b + 1)
        grow = b / max(1, pb_ - 1)
        tones = triad(sym, lo=57)
        pizz.play(Clip([(i * 0.5, 0.25, (tones + [tones[0] + 12])[i % 4], int(60 + grow * 26)) for i in range(8)],
                       length=4), pos)
        trem.play(Clip([(0, 3.9, p, int(48 + grow * 30)) for p in triad(sym, lo=50)], length=4), pos)
        cbass.play(Clip([(i, 0.4, root(sym, lo=38), int(64 + grow * 24)) for i in range(4)], length=4), pos)
        kit.play(drums({'kick': 'x.......x.......', 'snare': '....o.......o.oo', 'hat': 'x.x.x.x.x.x.x.x.'},
                       vel=int(44 + grow * 30)), pos)
    # brass stabs in the gaps (106.17-106.47 between lines 18/19, 110.13-110.52 between 19/20)
    for t in (E(18) + 0.04, E(19) + 0.06):
        brass.play(Clip([(0, 0.25, p, 100) for p in (50, 57, 62, 65)], length=1), at(t))
        timp.play(Clip([(0, 0.4, 38, 96)], length=1), at(t))
    # the last bar: snare roll + chromatic climb into the lever
    lp = mbar(panic, pb_)
    kit.play(drums({'snare': '2233445566778899', 'kick': 'x...x...x.x.x.x.'}, vel=70), lp)
    cbass.play(Clip([(i * 0.5, 0.35, 38 + i, 76 + i * 4) for i in range(8)], length=4), lp)

    # ================================================================== D5/E1: REVERSE - scratch, descend, suck
    # the lever slam (sfx 114.925): record scratch + choke, then everything slides down
    zip_.play(Clip([(0, 0.07, 84, 112), (0.07, 0.1, 62, 104), (0.17, 0.08, 81, 108), (0.25, 0.5, 40, 100)],
                   length=4), reverse.start)
    kit.play(drums({'snare': 'X', 'kick': 'X'}, bars=1, vel=90), reverse.start)
    desc = [72, 71, 70, 69, 68, 67, 66, 65, 64, 63, 62, 61]
    bone.play(Clip([(0.75 + i * 0.27, 0.3, p - 12, 92 - i * 3) for i, p in enumerate(desc)], length=4),
              reverse.start)
    tuba.play(Clip([(0.75 + i * 0.54, 0.5, p - 36, 88 - i * 3) for i, p in enumerate(desc[::2])], length=4),
              reverse.start)
    timp.play(Clip([(1.0, 0.6, 45, 90), (1.8, 0.6, 43, 84), (2.6, 0.6, 41, 80), (3.4, 0.6, 36, 84)], length=4),
              reverse.start)
    # bars 2-4: the suction - a low C drone, a whirling chromatic swirl, a rising choir, the sweep growing
    for b in range(1, int(reverse.bars)):
        pos = mbar(reverse, b + 1)
        g = b / max(1, reverse.bars - 1)
        cbass.play(Clip([(0, 3.9, 24, int(60 + g * 20))], length=4), pos)
        tuba.play(Clip([(0, 3.9, 24, int(50 + g * 20))], length=4), pos)
        trem.play(Clip([(0, 3.9, p, int(46 + g * 26)) for p in (48, 49 + b)], length=4), pos)
        celesta.play(Clip([(i * 0.25, 0.22, 72 + (i * 5 + b) % 13, int(40 + g * 20)) for i in range(16)],
                          length=4), pos)
        choir.play(Clip([(0, 3.9, p, int(46 + g * 24)) for p in (48, 51 + b)], length=4), pos)
        timp.play(Clip([(0, 1.0, 36, int(52 + g * 30)), (2.5, 1.0, 36, int(44 + g * 30))], length=4), pos)
    suck.play(Clip([(0, 0.05, 36, 60), (0.05, 11.8, 72, 76)], length=12), mbar(reverse, 2))
    # the gap after line 21 (122.97 -): the swirl swells (flute run up) into the rise
    flute.play(notes('vel=70 C5/16 D5/16 Eb5/16 F5/16 G5/16 Ab5/16 B5/16 C6/16'), at(E(21) + 0.05))
    revcym.play(Clip([(0, 3.0, 60, 84)], length=4), s.beat_at(1.6, before=rise.start))

    # ================================================================== E2: the cloud rises (ember eyes)
    big_hit(rise.start, pitches=(24, 36, 48, 55, 60, 63), ring=2.4, vel=120)
    choir.play(Clip([(0, 7.6, p, 70) for p in (48, 55, 60, 63)], length=8), rise.start)
    horns.play(Clip([(0.5, 3.0, 48, 72), (0.5, 3.0, 55, 68), (4.0, 3.6, 49, 72), (4.0, 3.6, 56, 68)], length=8),
               rise.start)
    cbass.play(Clip([(0, 7.6, 24, 76)], length=8), rise.start)
    timp.play(Clip([(4.0 + i * 0.25, 0.25, 36, 50 + i * 4) for i in range(16)], length=8), rise.start)

    # ================================================================== E3-E5: the Smog Monster eats the party
    mon = int(monster.bars)
    stomp = [(0, 0.4, 36), (1.0, 0.4, 36), (1.5, 0.4, 39), (2.0, 0.4, 36), (2.5, 0.4, 42), (3.0, 0.4, 43),
             (3.5, 0.4, 31)]
    mprog2 = ['Cm', 'Cm', 'Ab', 'G7']
    beat_m = drums({'kick': 'x.....x.x.......', 'snare': '....X.......X...', 'hat': 'x.x.x.x.x.x.x.x.',
                    'tom_lo': '..............x.'}, vel=70)
    beat_m2 = drums({'kick': 'x.....x.x.x.....', 'snare': '....X.......X.xx', 'hat': 'x.x.x.x.x.x.x.x.',
                     'tom_mid': '............x...', 'tom_lo': '.............xx.'}, vel=74)
    for b in range(mon):
        pos = mbar(monster, b + 1)
        sym = mprog2[b % 4]
        shift = {'Cm': 0, 'Ab': -4, 'G7': -5}[sym]
        under_line = talking(s.seconds(pos + 0.1)) and talking(s.seconds(pos + 3.5))
        v = 0.8 if under_line else 1.0
        tuba.play(Clip([(t, d, p + shift, int(96 * v)) for t, d, p in stomp], length=4), pos)
        cbass.play(Clip([(t, d, p + shift, int(80 * v)) for t, d, p in stomp], length=4), pos)
        kit.play((beat_m2 if b % 4 == 3 else beat_m).velocity(v), pos)
        if not under_line:
            brass.play(Clip([(0.5, 0.25, p, 96) for p in triad(sym, lo=55)] +
                            [(2.5, 0.25, p, 100) for p in triad(sym, lo=55)], length=4), pos)
        else:
            horns.play(Clip([(0, 3.8, p, 58) for p in triad(sym, lo=48)], length=4), pos)
    # the monster theme on the trumpet (gaps) / horns (under the lines)
    mtheme = notes('vel=94 C5/8 C5/8 Eb5/8 C5/8 F#5/4 G5/4 | Ab5/8 G5/8 F#5/8 Eb5/8 C5/2 | '
                   'C5/8 C5/8 Eb5/8 C5/8 F#5/4 G5/4 | B4/4 D5/4 G5/2')
    for k in range(0, mon - 3, 8):
        split_lead(mtheme, mbar(monster, k + 1), tpt, horns, under=0.6)
    # E3 the monster starts eating: a kick-off hit, then the grill-grate mouth bites (chomp sfx +0.2): a 'gulp'
    big_hit(monster.start, pitches=(24, 36, 48, 51, 55), ring=0.8, vel=108, stab=False)
    bone.play(Clip([(0, 0.3, 36, 104), (0.35, 0.6, 31, 100)], length=2), at(T_MONSTER + 0.25))
    # gap after line 23 (beer cans, 137.58-139.18): clang clang clonk, a gulp
    for i, (dt, p) in enumerate(((0.05, 96), (0.35, 91), (0.7, 84))):
        glock.play(Clip([(0, 0.3, p, 90)], length=1), at(E(23) + dt))
        kit.play(Clip([(0, 0.2, 56, 84)], length=1), at(E(23) + dt))
    tuba.play(Clip([(0, 0.3, 31, 100), (0.4, 0.5, 26, 96)], length=1), at(E(23) + 1.05))
    # gap after line 24 (Finn's non-violent communication fails, 143.41-145.01): sad trombone
    st = at(E(24) + 0.05)
    mute.play(Clip([(0, 0.3, 67, 90), (0.4, 0.3, 66, 86), (0.8, 0.3, 65, 84), (1.2, 1.4, 64, 82)], length=4), st)
    # gap after line 25 (Mandy's stream, 150.11-151.51): CHOMP - the phone goes in
    big_hit(at(E(25) + 0.05), pitches=(24, 36, 48, 51, 55), ring=0.8, vel=116, crash=False)
    tuba.play(Clip([(0.5, 0.6, 26, 96)], length=2), at(E(25) + 0.05))
    # line 26 (the machine is fried, nothing can stop it): build, a last stab on the end of the line
    lm = mbar(monster, mon)
    kit.play(drums({'snare': '1122334455667788', 'kick': 'x...x...x...x...'}, vel=66), lm)
    trem.play(Clip([(0, 3.9, p, 70) for p in (55, 59, 62, 65)], length=4), lm)
    stopit = at(E(26) + 0.02)
    brass.play(Clip([(0, 0.3, p, 108) for p in (43, 50, 55, 59, 62)], length=1), stopit)
    timp.play(Clip([(0, 0.5, 43, 110)], length=1), stopit)

    # ================================================================== F1/F2: Oma (deadly calm, suspense)
    # fork down (a tiny 'ting'), the earth-shake (sfx +0.6) doubled low, then a dark drone with a heartbeat
    glock.play(Clip([(0, 0.3, 91, 62)], length=1), at(T_OMA + 0.2))
    for t, v in ((T_SHAKE, 124), (T_SHAKE + 0.75, 108)):
        timp.play(Clip([(0, 1.0, 41, v)], length=1), at(t))
        tuba.play(Clip([(0, 0.8, 29, v - 6)], length=1), at(t))
        cbass.play(Clip([(0, 0.8, 29, v - 20)], length=1), at(t))
    boom.play(Clip([(0, 2.0, 38, 112)], length=2), at(T_SHAKE))
    ob = int(oma.bars)
    for b in range(ob):
        pos = mbar(oma, b + 1)
        g = b / max(1, ob - 1)
        if b > 0:
            cbass.play(Clip([(0, 3.9, 29, int(56 + g * 20))], length=4), pos)
            trem.play(Clip([(0, 3.9, p, int(40 + g * 34)) for p in (41, 44 + (b >= 3))], length=4), pos)
            beats_ = (0, 2) if b < 3 else (0, 1, 2, 3)
            timp.play(Clip([(x, 0.3, 29 + 12, int(50 + g * 30)) for x in beats_] +
                           [(x + 0.35, 0.3, 41, int(40 + g * 30)) for x in beats_], length=4), pos)
        if b >= 2:
            choir.play(Clip([(0, 3.9, p, int(44 + g * 26)) for p in (53, 56 + (b - 2))], length=4), pos)
    # the elephant walk again, slow and soft under "Nobody. Eats. At MY birthday."
    tuba.play(Clip([(0, 1.6, 29, 62), (2, 1.6, 36, 56), (4, 1.6, 37, 60), (6, 1.6, 36, 54)], length=8),
              mbar(oma, 2))
    # the gap after line 27 (164.81-166.41): horns 'dun-dun'
    horns.play(Clip([(0, 0.6, 41, 82), (0.75, 1.2, 40, 84)], length=2), at(E(27) + 0.08))
    celesta.play(Clip([(0, 0.4, 77, 50), (0.4, 0.6, 80, 52)], length=1), at(E(28) + 0.05))

    # ================================================================== F3: the INHALE (everything rises)
    ib = int(inhale.bars)
    for b in range(ib):
        pos = mbar(inhale, b + 1)
        base = 41 + b * 4
        trem.play(Clip([(i, 1.0, base + i, 70 + b * 12 + i * 3) for i in range(4)] +
                       [(i, 1.0, base + 7 + i, 66 + b * 12 + i * 3) for i in range(4)], length=4), pos)
        brass.play(Clip([(i, 1.0, base + 12 + i, 60 + b * 16 + i * 4) for i in range(4)], length=4), pos)
        choir.play(Clip([(0, 3.95, p, 70 + b * 14) for p in (base + 12, base + 16, base + 19)], length=4), pos)
        cbass.play(Clip([(0, 3.95, 29 + b * 2, 80)], length=4), pos)
        kit.play(drums({'snare': '1122334455667788' if b == 0 else '5566778899999999'}, vel=60 + b * 16), pos)
        timp.play(Clip([(i * 0.25, 0.25, 41, 50 + b * 30 + i * 2) for i in range(16)], length=4), pos)
    suck.play(Clip([(0, 0.05, 41, 70), (0.05, ib * 4 - 0.2, 89, 96)], length=ib * 4), inhale.start)
    revcym.play(Clip([(0, 3.0, 60, 96)], length=4), s.beat_at(2.6, before=burp.start))

    # ================================================================== F4: the burp - silence (master gate)
    gate_out, gate_in = at(T_BURP - 0.03), at(E(30) + 0.08)
    # a tiny white cloud floats out after the burp
    celesta.play(Clip([(0, 0.6, 84, 60), (0.3, 0.9, 91, 54)], length=2), at(E(30) + 0.15))

    # ================================================================== the fanfare + applause
    big_hit(fanfare.start, pitches=(29, 41, 53, 57, 60, 65), ring=1.6, vel=120)
    tpt.play(notes('vel=100 C5/8. C5/16 F5/8 A5/8 C6/4 A5/8 C6/8 | F6/2').arch(2, 0.3), fanfare.start)
    brass.play(Clip([(0, 0.4, p, 96) for p in (53, 57, 60)] + [(0.75, 0.25, p, 86) for p in (53, 57, 60)] +
                    [(1.0, 0.8, p, 92) for p in (53, 58, 62)] + [(2.0, 1.6, p, 98) for p in (53, 57, 60, 65)],
                    length=4), fanfare.start)
    timp.play(Clip([(0, 0.5, 41, 104), (1, 0.5, 36, 92), (2, 0.5, 41, 100), (3, 0.25, 36, 88),
                    (3.5, 0.25, 36, 92)], length=4), fanfare.start)
    kit.play(drums({'snare': 'x..xx.x.x..xx.x.', 'kick': 'x.......x.......'}, vel=66), fanfare.start)
    applause.play(Clip([(0.5, 6.5, 60, 96)], length=8), fanfare.start)
    applause.automate('gainDb', [(0, 0.0), (mbar(fanfare, 2), 0.0), (fanfare.end, -10.0, 'smooth')])
    # bar 2: soft and warm under "...That's my girl." (whispered)
    f2 = mbar(fanfare, 2)
    strings.play(Clip([(0, 3.9, p, 56) for p in (53, 57, 60, 65)], length=4), f2)
    harp.play(Clip([(i * 0.125, 1.0, p, 50) for i, p in enumerate((89, 84, 81, 77, 72, 69, 65, 60))], length=4), f2)
    cbass.play(Clip([(0, 3.9, 29, 54)], length=4), f2)

    # ================================================================== G: evening, the proposal (warm waltz)
    eb = int(evening.bars)
    for b in range(eb):
        pos = mbar(evening, b + 1)
        sym = PROG_W[b] if b < len(PROG_W) else 'F'
        oompah(sym, pos, vel=0.75, beats=3, lo=55)
        strings.play(Clip([(0, 2.9, p, 50) for p in triad(sym, lo=57)], length=3), pos)
        harp.play(Clip([(i * 0.5, 0.6, p, 46) for i, p in enumerate(triad(sym, lo=65) + [triad(sym, lo=65)[0] + 12])],
                       length=3), pos)
    wl = notes(f'vel=80 meter=3/4 {WALTZ}').arch(4, 0.4)
    wl = Clip([n for n in wl if n.start < eb * 3 - 0.25], length=eb * 3)       # never past the cough
    split_lead(wl, evening.start, violin, under=0.66)
    # glock twinkle in the gap between lines 33 and 34 (198.74-200.34)
    glock.play(notes('vel=60 F6/8 A6/8 C7/8 F7/4'), at(E(33) + 0.1))

    # ================================================================== the cough: comic button + the ant
    tuba.play(Clip([(0, 0.35, 29, 110), (0.5, 0.3, 24, 96)], length=1), button.start)
    pizz.play(Clip([(0.5, 0.3, p, 84) for p in (53, 57, 60, 65)], length=1), button.start)
    kit.play(drums({'rim': 'x.x.', 'kick': 'x...'}, step='1/8', vel=84), button.start)
    # the tin-foil-hat ant (ep2 cameo): the series theremin wink, then the final chord
    lead.play(notes('vel=72 D5/8 F5/8 E5/8 D5/8 A5/2').arch(1, 0.5), mbar(button, 1, 1.0))
    pizz.play(Clip([(1.0, 0.25, 50, 56), (2.0, 0.25, 45, 52), (3.0, 0.25, 50, 56)], length=4), button.start)
    fin = mbar(button, 2)
    strings.play(Clip([(0, 4.0, p, 64) for p in (53, 57, 60, 65)], length=4), fin)
    acc.play(Clip([(0, 3.0, p, 60) for p in (65, 69, 72)], length=4), fin)
    tuba.play(Clip([(0, 2.0, 29, 80)], length=4), fin)
    harp.play(Clip([(i * 0.0625, 2.0, p, 58) for i, p in enumerate((53, 57, 60, 65, 69, 72, 77))], length=4), fin)
    glock.play(Clip([(0.5, 1.0, 89, 54)], length=4), fin)

    # ------------------------------------------------------------------ master: the burp gate, the end fade
    end_fade = mbar(button, 2, 1.5)
    s.master.automate('gainDb', [(0, 0.0), (gate_out, 0.0), (burp.start, -90.0), (gate_in - 0.02, -90.0),
                                 (gate_in, 0.0), (end_fade, 0.0), (button.end, -40.0, 'smooth')])
    return s
