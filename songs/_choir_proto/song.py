"""Neural choir prototype (stage 1: vowel choir pack; stage 2: a choir that sings text) - A/B demos.

    python songs/_choir_proto/make_demos.py [variant ...]      # builds the variants -> out/<name>.mp3

Variants ($CHOIR_VARIANT):
  newpack   stage 1: a slow I-vi-IV-V(4-3)-I in F with a swell (hum -> "ah" -> "oh") on the NEW pack: 6 / 5
            virtual DiffSinger singers per part summed into each sample              -> out/stage1_newpack.mp3
  single    the same notes on the pack's 'solo' variant (one virtual singer a part)  -> out/stage1_single_layer.mp3
  copies    the same on 'copies' (ONE take x N with the section's onsets / pans: the comb-filter A/B)
                                                                                     -> out/stage1_copies.mp3
  oldchoir  the same notes on our sampled choirs (sampled/choir_mixed "ah", sampled/choir_oh "oh" / for the hum)
                                                                                     -> out/stage1_oldchoir.mp3
  pure      stage 2: an original two-line text, SATB homophonic, every part sung by 5 DiffSinger layers
            (singer.sing + singer.double)                                            -> out/stage2_pure.mp3
  hybrid    stage 2: 2 text layers a part over the stage-1 pack as the vowel body (vowel-matched, syllable-gated
            by orch.Choir)                                                           -> out/stage2_hybrid.mp3
  big       stage 3: the stage-1 notes on the BIG pack (14 S / 14 A / 12 T / 12 B singers, each placed in one hall:
            direct sound + early reflections + the stage's diffuse field to an ORTF pair + outriggers, varispeed
            detune / drift, breath; the bass's bottom layered with the SSO men's chorus) -> out/stage3_big.mp3
  big_nobass  the same without the old choir's bass bottom                          -> out/stage3_big_nobass.mp3
  vsold     the A/B: the stage-1 chords 4 x 8 bars - big, old, big, old              -> out/stage3_vs_old.mp3
  clones    the stage-1 notes on the CLONES pack: the stage-1 takes x 3, the clones changed mechanically (detune,
            LFO pitch, a moving pre-delay, all-pass decorrelation, timbre, level wobble, own seat) -> stage3_clones.mp3
  abc       blind blocks: clones / old / big, two each, 8 bars, in ABC's order          -> out/stage3_abc.mp3
  hybrid3   stage 2's text hybrid over the big pack                                  -> out/stage3_hybrid_text.mp3
  vocalset  stage 4: the stage-1 notes on the vocalset-choir pack (REAL singers: VocalSet, CC BY 4.0 - 9 women /
            10 men a part pool, every singer who covers the note, each on its own seat in the stage-3 hall; no hum
            in the set: the hum chords sing "oo")                                   -> out/stage4_vocalset.mp3
  abc4      blind blocks: vocalset / big / old, two each, 8 bars, in ABC4's order        -> out/stage4_abc.mp3
  hymn      an original SATB chorale on vowels (oo -> ah -> oh, p -> f -> p), the vocalset choir alone
                                                                                     -> out/stage4_hymn.mp3

The pack lives in D:/Repos/AgentSound/local/choir/pack (make_pack.py; LOCAL ONLY - voicebank licences, see choir.py). Voices:
Hanami (S, A) and TIGER (T, B) - TIGER is NON-COMMERCIAL; Hanami's vocoder CC BY-NC-SA: private / non-commercial.
"""
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from agentsound import *            # noqa: E402,F403
from agentsound import singer                 # noqa: E402
from agentsound.bandlib import scoring as orch   # noqa: E402

import choir as C                   # noqa: E402
C.setup_env()
import textchoir as T               # noqa: E402
import vocalset as VS               # noqa: E402

VARIANT = os.environ.get('CHOIR_VARIANT', 'newpack')
ANALYSIS = {'profile': 'classical'}
METADATA = {'artist': 'AgentSound', 'album': 'Prototypes', 'genre': 'Choral',
            'comment': 'Vocals: Hoshino Hanami ~AI\u2764dol~ (Lotte V) and TIGER (tigermeat) DiffSinger voicebanks - '
                       'non-commercial'}
LEAD = 1.0          # beats of silence before the first note (the choir starts early: lead_s, consonants)
PAN = {'S': -0.35, 'A': 0.35, 'T': -0.2, 'B': 0.2}
SATB = ('S', 'A', 'T', 'B')
ORDER = tuple(os.environ.get('CHOIR_PARTS', 'S,A,T,B').split(','))   # a subset while the pack renders

# --- stage 1: the chord progression (beats; F major, 60 BPM): (start, dur, vowel, vel, {part: pitch})
N = note
CHORDS = [
    (0, 4, 'mm', 52, {'S': 'A4', 'A': 'F4', 'T': 'C4', 'B': 'F3'}),       # I
    (4, 4, 'mm', 60, {'S': 'A4', 'A': 'F4', 'T': 'D4', 'B': 'D3'}),       # vi
    (8, 4, 'ah', 74, {'S': 'Bb4', 'A': 'F4', 'T': 'D4', 'B': 'Bb2'}),     # IV
    (12, 2, 'ah', 98, {'S': 'C5', 'A': 'F4', 'T': 'C4', 'B': 'C3'}),      # V sus4
    (14, 2, 'ah', 106, {'S': 'C5', 'A': 'E4', 'T': 'G3', 'B': 'C3'}),     # V (4-3 in the alto)
    (16, 6, 'oh', 70, {'S': 'A4', 'A': 'F4', 'T': 'C4', 'B': 'F3'}),      # I, the swell falling back
]

# --- stage 2: the text (original) and its SATB setting (F major, 52 BPM)
WORDS = [('Light', 1), ('the', 1), ('lamps', 1), ('a-long', 2), ('the', 1), ('shore,', 1),
         ('hold', 1), ('the', 1), ('mor-ning,', 2), ('sing', 1), ('once', 1), ('more.', 1)]
TEXT = 'Light the lamps along the shore, / hold the morning, sing once more.'
# (start, dur, vel, S, A, T, B); S may carry a melisma: a list of (dur, pitch)
SETTING = [
    (0.0, 1.0, 62, 'A4', 'F4', 'C4', 'F3'),            # Light       I
    (1.0, 0.5, 60, 'G4', 'E4', 'C4', 'E3'),            # the         V6
    (1.5, 1.5, 66, 'F4', 'D4', 'A3', 'D3'),            # lamps       vi
    (3.0, 1.0, 68, 'F4', 'D4', 'Bb3', 'D3'),           # a-          IV6
    (4.0, 2.0, 80, 'A4', 'F4', 'C4', 'C3'),            # long        I64
    (6.0, 1.0, 76, 'G4', 'E4', 'C4', 'C3'),            # the         V
    (7.0, 3.0, 72, [(1.5, 'A4'), (1.5, 'F4')], 'F4', 'C4', 'F3'),   # shore,  I (melisma in S)
    (11.0, 1.0, 74, 'Bb4', 'F4', 'D4', 'Bb2'),         # hold        IV
    (12.0, 0.5, 74, 'A4', 'F4', 'C4', 'F3'),           # the         I
    (12.5, 1.5, 84, 'G4', 'D4', 'Bb3', 'G3'),          # mor-        ii
    (14.0, 1.0, 88, 'G4', 'E4', 'C4', 'C3'),           # -ning       V
    (15.0, 2.0, 100, 'A4', 'F4', 'D4', 'D3'),          # sing        vi
    (17.0, 1.0, 92, 'G4', 'F4', 'C4', 'C3'),           # once        V7
    (18.0, 6.0, 70, [(2.0, 'A4'), (1.0, 'G4'), (3.0, 'F4')], 'F4', 'C4', 'F3'),   # more.  I (melisma in S)
]
# the nucleus vowel of each syllable -> the pack vowel of the hybrid's body
BODY_VOWEL = ['ah', 'ah', 'ah', 'ah', 'oh', 'ah', 'oh', 'oh', 'ah', 'oh', 'ah', 'ah', 'ah', 'oh']


def setting_notes(base: float = 0.0) -> dict:
    """{part: [(start, dur, pitch, vel)]} of the text setting (song beats from `base`)."""
    out = {p: [] for p in SATB}
    for st, du, v, *ps in SETTING:
        for p, x in zip(SATB, ps):
            if isinstance(x, list):
                t = st
                for d, q in x:
                    out[p].append((base + t, d, N(q), v))
                    t += d
            else:
                out[p].append((base + st, du, N(x), v))
    return out


def choir_eq(part: str):
    """The same light eq on every choir track (new pack and old choir alike): low cut, box / honk / presence dips."""
    return fx.eq({'hp.freq': 70 if part in 'TB' else 140, 'peak1.freq': 400, 'peak1.gain': -2.5, 'peak1.q': 0.8,
                  'peak2.freq': 1100, 'peak2.gain': -2.5, 'peak2.q': 0.7, 'peak3.freq': 3500, 'peak3.gain': -2.5,
                  'peak3.q': 0.8})


VS_VOWEL = {'mm': 'oo'}
"""VocalSet has no hum: the stage-1 hum chords sing "oo" on the vocalset pack."""
VS_HUM_DB = 2.0
"""... 2 dB under the other vowels (a hum is softer: the first build's hum chords read 1.5 dB over the big pack's)."""


def pack_track(s, part: str, vowel: str, variant: str, hall, gain_db: float = 0.0, tag: str = ''):
    if variant == 'vocalset':
        sfz = VS.PACK / f'{part}_{VS_VOWEL.get(vowel, vowel)}.sfz'
        if not sfz.is_file():
            raise ComposeError(f"no {sfz}: run python -I songs/_choir_proto/vocalset.py package first")
    else:
        sfz = C.PACK / f'{part}_{vowel}{"" if variant == "section" else "_" + variant}.sfz'
    if not sfz.is_file():
        raise ComposeError(f"no {sfz}: run python songs/_choir_proto/make_pack.py all first")
    # the big / vocalset packs' samples carry each singer's place in the hall (room.py): no pan on top
    pan = 0.0 if variant.startswith('big') or variant in ('clones', 'vocalset') else PAN[part] * 0.6
    fxs = [choir_eq(part)] + ([fx.eq(dict(VS_DISTANCE))] if variant == 'vocalset' else [])
    return s.track(f'{tag}{part.lower()}_{vowel}', inst.sfz(str(sfz)), pan=pan, gain_db=gain_db,
                   sends={hall: -7}, fx=fxs)


BIG_DB = -7.7
VS_DB = -4.7
"""The vocalset pack's track level: BIG_DB + 3 dB (the first A/B build read its blocks -22.3 LUFS against the big /
old blocks' -19.7)."""
VS_DISTANCE = {'high.freq': 2200, 'high.gain': -3.5, 'peak1.freq': 3300, 'peak1.gain': -2.5, 'peak1.q': 0.9}
"""VocalSet was recorded close to each singer: its section samples read ~2 dB brighter than a choir heard from the
hall (sustain centroid SA 982 Hz vs the SSO chorus 795, TB 757 vs 603; measure: vocalset.py measure) - a high shelf
on its tracks as the distance."""
"""The big pack's track level (stage 1's -6 for the section pack; the A/B matches the old choir's loudness)."""


def stage1(s, hall, variant: str, at: float = 0.0, tag: str = '', section: str = 'chords', bars: int = 6):
    s.section(section, bars=bars)
    vowels = sorted({c[2] for c in CHORDS})
    if variant == 'oldchoir':
        # one sampled-choir track per part and vowel colour: "ah" = sampled/choir_mixed, "oh" and the hum (the
        # library has no hum) = sampled/choir_oh
        tr = {}
        for p in ORDER:
            for v in vowels:
                patch = 'sampled/choir_mixed' if v == 'ah' else 'sampled/choir_oh'
                tr[(p, v)] = s.track(f'{tag}{p.lower()}_{v}', patch, pan=PAN[p] * 0.6, gain_db=-2.0,
                                     sends={hall: -7}, fx=[choir_eq(p)])
    else:
        g = {'vocalset': VS_DB}.get(variant, BIG_DB if variant.startswith('big') or variant == 'clones' else -6.0)
        tr = {(p, v): pack_track(s, p, v, variant, hall, gain_db=g - (VS_HUM_DB if variant == 'vocalset' and v == 'mm'
                                                                  else 0.0), tag=tag) for p in ORDER for v in vowels}
    ch = orch.Choir(s, {f'{p}_{v}': t for (p, v), t in tr.items()}, lane='dynamics', speak=112, spread=0.15,
                    swell_s=3.5)
    for st, du, v, vel, ps in CHORDS:
        for p, q in ps.items():
            if p not in ORDER:
                continue
            ch.sing(f'{p}_{v}', [(at + LEAD + st, du, N(q), vel)])
    ch.perform()


def stage3_vs_old(s, hall):
    """The A/B: the stage-1 chords four times, 8 bars each - big pack, old choir, big pack, old choir."""
    for i, v in enumerate(('big', 'oldchoir', 'big', 'oldchoir')):
        stage1(s, hall, v, at=32.0 * i, tag=f'{"ab"[i % 2]}{i // 2 + 1}_', section=f'part{i + 1}', bars=8)


ABC = ('big', 'clones', 'clones', 'oldchoir', 'big', 'oldchoir')
"""stage3_abc's block order (8 bars each). random.Random(19).shuffle of ['big', 'big', 'clones', 'clones', 'oldchoir', 'oldchoir']; the order is
in the commit / report, never printed in the song."""


def stage3_abc(s, hall):
    for i, v in enumerate(ABC):
        stage1(s, hall, v, at=32.0 * i, tag=f'x{i + 1}_', section=f'block{i + 1}', bars=8)


ABC4 = ('big', 'vocalset', 'oldchoir', 'vocalset', 'oldchoir', 'big')
"""stage4_abc's block order (8 bars each): random.Random(40).shuffle of ['vocalset', 'vocalset', 'big', 'big', 'oldchoir',
'oldchoir'] (the first seed >= 40 without two equal blocks in a row) - in the report only, never printed in the song."""


def stage4_abc(s, hall):
    for i, v in enumerate(ABC4):
        stage1(s, hall, v, at=32.0 * i, tag=f'y{i + 1}_', section=f'block{i + 1}', bars=8)


# --- stage 4: the hymn (original; D major, 60 BPM, half notes): (dur beats, vowel, vel, S, A, T, B)
HYMN = [
    (2, 'oo', 50, 'F#4', 'D4', 'A3', 'D3'), (2, 'oo', 52, 'E4', 'C#4', 'A3', 'C#3'),
    (2, 'oo', 54, 'D4', 'B3', 'F#3', 'B2'), (2, 'oo', 56, 'E4', 'B3', 'G3', 'E3'),
    (2, 'oo', 60, 'F#4', 'D4', 'A3', 'D3'), (2, 'oo', 64, 'G4', 'D4', 'B3', 'G3'),
    (4, 'oo', 66, 'A4', 'E4', 'C#4', 'A3'),
    (2, 'ah', 72, 'B4', 'F#4', 'D4', 'B2'), (2, 'ah', 80, 'C#5', 'F#4', 'C#4', 'A3'),
    (2, 'ah', 88, 'D5', 'G4', 'B3', 'G3'), (2, 'ah', 98, 'E5', 'G4', 'C#4', 'A3'),
    (4, 'ah', 112, 'F#5', 'A4', 'D4', 'D3'), (2, 'ah', 100, 'E5', 'A4', 'E4', 'C#3'),
    (2, 'oh', 86, 'D5', 'F#4', 'D4', 'B2'), (2, 'oh', 74, 'B4', 'G4', 'D4', 'G3'),
    (2, 'oh', 64, 'A4', 'F#4', 'D4', 'A3'), (2, 'oh', 56, 'G4', 'E4', 'C#4', 'A3'),
    (5, 'oh', 46, 'F#4', 'D4', 'A3', 'D3'),
]


def stage4_hymn(s, hall):
    s.section('hymn', bars=11)
    vowels = sorted({h[1] for h in HYMN})
    tr = {(p, v): pack_track(s, p, v, 'vocalset', hall, gain_db=VS_DB) for p in SATB for v in vowels}
    ch = orch.Choir(s, {f'{p}_{v}': t for (p, v), t in tr.items()}, lane='dynamics', speak=112, spread=0.15,
                    swell_s=3.5)
    t = LEAD
    for du, v, vel, *ps in HYMN:
        for p, q in zip(SATB, ps):
            ch.sing(f'{p}_{v}', [(t, du * 0.97, N(q), vel)])
        t += du
    ch.perform()


BUS_DB = {'S': -7.0, 'A': -4.0, 'T': -9.5, 'B': -7.0}
"""Each part's bus level (the sung takes are level-matched per voice: Hanami's alto register reads ~4 dB under her
soprano, TIGER's tenor ~3 dB over)."""


def arc(notes, depth: float = 0.22) -> list:
    """The written dynamics as the bus level (dB around `base`): the takes are level-matched, so the phrase's
    crescendo to 'sing' and the soft close are ridden on the part's bus (dB on its fader), syllable to syllable."""
    pts = []
    for st, d, q, v in notes:
        pts.append((max(0.0, st - 0.15), round((v - 78) * depth, 2), 'smooth'))
    st, d, q, v = notes[-1]
    pts.append((st + d, round((v - 78) * depth - 3.0, 2), 'smooth'))
    return pts


def stage2_pure(s, hall, layers: int = 5):
    s.section('text', bars=7)
    parts = setting_notes(0.0)
    lyr = T.homophonic(parts, WORDS)
    mem = singer.Memory()
    out = {}
    for p in ORDER:
        clip = Clip([(st, d, q, v) for st, d, q, v in parts[p]], length=24)
        out[p] = T.sing_section(s, p, clip, lyr[p], at=LEAD, layers=layers, hall=hall, memory=mem,
                                gain_db=BUS_DB[p])
        out[p]['bus'].automate('gainDb', arc([(st + LEAD, d, q, v) for st, d, q, v in parts[p]]))
    import json                         # the layers' lag / formant / pan, for measure_text.py
    (HERE / 'out').mkdir(exist_ok=True)
    (HERE / 'out' / 'choir_layers.json').write_text(json.dumps(
        {v.track.id: {'part': p, 'voice': v.bank.id, 'offset_ms': v.offset_ms, 'formant': v.formant, 'take': v.take,
                      'lyrics': lyr[p]} for p, d in out.items() for v in d['layers']}, indent=1), encoding='utf-8')
    return out


def stage2_hybrid(s, hall, body: str = 'section'):
    out = stage2_pure(s, hall, layers=2)
    parts = setting_notes(LEAD)
    g = -4.5 if body == 'section' else BIG_DB + 1.5
    tr = {(p, v): pack_track(s, p, v, body, hall, gain_db=g) for p in ORDER for v in ('ah', 'oh')}
    ch = orch.Choir(s, {f'{p}_{v}': t for (p, v), t in tr.items()}, lane='dynamics', speak=112, spread=0.15,
                    gate=(LEAD, LEAD + 24.0), lead_s=(0.03, 0.02))
    plain = parts['A']                      # the syllable rhythm (no melismas)
    for p in ORDER:
        for st, d, q, v in parts[p]:
            k = max(i for i, n in enumerate(plain) if n[0] <= st + 1e-6)
            ch.sing(f'{p}_{BODY_VOWEL[k]}', [(st, d, q, v)])
    ch.perform()
    return out


def build() -> Song:
    title = {'newpack': 'Choir proto - new pack', 'single': 'Choir proto - single layer', 'copies':
             'Choir proto - one take x N', 'oldchoir': 'Choir proto - sampled choir', 'pure': 'Choir proto - text',
             'hybrid': 'Choir proto - text hybrid', 'big': 'Choir proto - big section', 'big_nobass':
             'Choir proto - big section (no old bass)', 'vsold': 'Choir proto - A/B', 'hybrid3':
             'Choir proto - text hybrid (big body)', 'clones': 'Choir proto - clones', 'abc':
             'Choir proto - blind blocks', 'vocalset': 'Choir proto - VocalSet choir', 'abc4':
             'Choir proto - blind blocks 4', 'hymn': 'Choir proto - VocalSet hymn'}[VARIANT]
    stage1_v = {'newpack': 'section', 'single': 'solo', 'copies': 'copies', 'oldchoir': 'oldchoir', 'big': 'big',
                'big_nobass': 'big_nobass', 'clones': 'clones', 'vocalset': 'vocalset'}
    s = Song(title, tempo=60 if VARIANT in stage1_v or VARIANT in ('vsold', 'abc', 'abc4', 'hymn') else 52, key='F major', seed=5, tail=5)
    hall = s.hall(decay=2.8)
    s.master.add(fx.limiter(gain=0.0, ceiling=-1.5))
    if VARIANT in stage1_v:
        stage1(s, hall, stage1_v[VARIANT])
    elif VARIANT == 'pure':
        stage2_pure(s, hall)
    elif VARIANT == 'hybrid':
        stage2_hybrid(s, hall)
    elif VARIANT == 'hybrid3':
        stage2_hybrid(s, hall, body='big')
    elif VARIANT == 'vsold':
        stage3_vs_old(s, hall)
    elif VARIANT == 'abc':
        stage3_abc(s, hall)
    elif VARIANT == 'abc4':
        stage4_abc(s, hall)
    elif VARIANT == 'hymn':
        stage4_hymn(s, hall)
    else:
        raise ComposeError(f"CHOIR_VARIANT {VARIANT!r}?")
    return s
