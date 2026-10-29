"""AgentSound endless music in the browser (Pyodide): the native endless set loop (agentsound.endless.run.cmd_endless)
without audio - set plans, best-of-N candidates - for the piano styles (on the Splendid grand) and the symphonic
orchestra (orchestra-symphonic: SSO / VPO / VSCO 2 samples, as on master).

The repo mirror (agentsound/ + the text assets, prod/mirror2.py) is unpacked at /repo. Runs unchanged under CPython
for checks and for the bank:  AGENTSOUND_WEB_REPO=<mirror> python compose_web.py
"""
import copy, json, math, os, random, sys, time, types

REPO = os.environ.get('AGENTSOUND_WEB_REPO', '/repo')
sys.dont_write_bytecode = True
sys.path.insert(0, REPO)

# 1. 32-bit Pyodide: random.Random(<float>) must seed like 64-bit CPython (hash(float) is taken modulo 2**61-1
#    there, 2**31-1 here). Without it the composer draws other numbers from the first float seed on.
_P = (1 << 61) - 1


def _hash64(x: float) -> int:
    if math.isinf(x):
        return 314159 if x > 0 else -314159
    n, d = x.as_integer_ratio()
    h = (abs(n) % _P) * pow(d, _P - 2, _P) % _P
    h = -h if n < 0 else h
    return -2 if h == -1 else h


_seed0 = random.Random.seed


def _seed(self, a=None, version=2):
    return _seed0(self, _hash64(a) if isinstance(a, float) else a, version)


random.Random.seed = _seed

# 2. the composer's reads of sample AUDIO come from tables (the mirror has no audio; prod/orch_tables.py made them
#    natively from the real files): sfz.wav_info (frames / rate / channels: loop / offset / end clamps) and the
#    orchestra's zone levelling (bandlib.orchestra._sample_level). A miss is counted (MISSING) and falls back to the
#    placeholder file (no info / no level) - the bank build and the checks fail on any miss.
from agentsound import sfz as _sfz           # noqa: E402
from agentsound.bandlib import orchestra as _orch   # noqa: E402
from agentsound.patches import inst          # noqa: E402

with open(os.path.join(REPO, 'agentsound_web_tables.json'), encoding='utf-8') as _fh:
    TABLES = json.load(_fh)
MISSING = set()


def _rel(p):
    p = str(p).replace(chr(92), '/')
    return p.split('/assets/', 1)[1] if '/assets/' in p else p


_wav_info0, _level0 = _sfz.wav_info, _orch._sample_level


def _wav_info(path):
    r = _rel(path)
    if r in TABLES['wav_info']:
        return TABLES['wav_info'][r]
    MISSING.add('wav_info ' + r)
    return _wav_info0(path)


def _sample_level(path, offset=0, seconds=1.5):
    k = f'{_rel(path)}|{int(offset)}'
    if seconds == 1.5 and k in TABLES['level']:
        return TABLES['level'][k]
    MISSING.add('level ' + k)
    return _level0(path, offset, seconds)


_sfz.wav_info, _orch._sample_level = _wav_info, _sample_level

# (the pipe organs: organ.sample_info reads WAV headers - frames / rate / channels / loop / cue - from the tables too)
from agentsound import organ as _organ       # noqa: E402
_organ_info0 = _organ.sample_info


def _organ_info(path):
    r = _rel(path)
    t = TABLES.get('organ_info', {})
    if r in t:
        v = t[r]
        return None if v is None else dict(v, loop=tuple(v['loop']) if v.get('loop') is not None else None)
    MISSING.add('organ_info ' + r)
    return _organ_info0(path)


_organ.sample_info = _organ_info

# 3. the web piano: the solo-piano Salamander (1.9 GB) -> the Splendid Grand (public domain); 'spar' plays the mini
#    cut: 3 of the 5 velocity layers, every 2nd sampled key (pitch-shifted between)
SAL = 'samples/salamander-grand/SalamanderGrandPianoV3Retuned.sfz'
WEB = 'samples/splendid-grand-piano/Splendid Grand Piano.sfz'
MODE = {'piano': 'beste'}
_cls = type(inst)
_sfz_method = _cls.sfz


def _inst_sfz(self, path, **kw):
    return _sfz_method(self, WEB if str(path) == SAL else path, **kw)


_cls.sfz = _inst_sfz


def mini_cut(zones):
    """3 velocity layers (the softest, the middle, the loudest; the ranges meet halfway) and every 2nd sampled key
    per layer (each covering the keys halfway to its neighbours)."""
    zones = copy.deepcopy(zones)
    layers = sorted({(z.get('vello', 0), z.get('velhi', 127)) for z in zones})
    kept = [layers[0], layers[len(layers) // 2], layers[-1]] if len(layers) > 3 else layers
    cent = [(a + b) / 2 for a, b in kept]
    out = []
    for i, lay in enumerate(kept):
        lo_v = 0 if i == 0 else int((cent[i - 1] + cent[i]) // 2) + 1
        hi_v = 127 if i == len(kept) - 1 else int((cent[i] + cent[i + 1]) // 2)
        zl = sorted([z for z in zones if (z.get('vello', 0), z.get('velhi', 127)) == lay], key=lambda z: z['root'])
        lo_k, hi_k = min(z['lo'] for z in zl), max(z['hi'] for z in zl)
        zl = zl[::2]
        for j, z in enumerate(zl):
            z['lo'] = lo_k if j == 0 else (zl[j - 1]['root'] + z['root']) // 2 + 1
            z['hi'] = hi_k if j == len(zl) - 1 else (z['root'] + zl[j + 1]['root']) // 2
            if len(kept) < len(layers):
                z['vello'], z['velhi'] = lo_v, hi_v
            out.append(z)
    return out


_load0 = _sfz.load


def _load(path, *a, **k):
    zones, info = _load0(path, *a, **k)
    if MODE['piano'] == 'spar' and str(path) == WEB:
        zones = mini_cut(zones)
    return zones, info


_sfz.load = _load

# 4. speed (the same numbers): symphony.activity converts every attack of the score to seconds through
#    song.seconds(), which builds the tempo map anew each time (~4 s of a candidate's score natively, ~4x that in
#    Pyodide); here the map is built once per call - the identical function of the identical points.
from agentsound.endless import symphony as _sym                  # noqa: E402


def _activity(song) -> dict:
    scs = getattr(song, 'orch_scores', None) or []
    on = sorted({round(n[0], 3) for sc in scs for ns in sc.parts.values() for n in ns})
    if not on:
        return {}
    secs = song.seconds(song.length)
    if song._tempo_plan.empty():
        ts = [song.seconds(x) for x in on]
    else:
        tm = song.tempo_map()
        ts = [tm.seconds_at(song._at(x)) for x in on]
    return {'nps': round(len(on) / max(1.0, secs), 2),
            'run_share': round(sum(1 for a, b_ in zip(ts, ts[1:]) if b_ - a <= 0.3) / max(1, len(ts) - 1), 3)}


_sym.activity = _activity

from agentsound import cli                                       # noqa: E402
from agentsound.endless import run as R                          # noqa: E402
from agentsound.endless.composer import set_plan                 # noqa: E402
from agentsound.endless.genres import get                        # noqa: E402
from agentsound.song import dumps                                # noqa: E402
from agentsound.theory import ComposeError                       # noqa: E402

# page genre -> (AgentSound genre, the feel a set keeps, candidates per piece: first, next)
GENRES = {'new-age': ('new-age-piano', None, 8, 8), 'klassik': ('classical-piano', None, 8, 8),
          'walzer': ('classical-piano', 'waltz', 8, 8), 'orchester': ('orchestra-symphonic', None, 4, 4)}
ORCHESTRA = ('orchester',)
VERSION = 'web7-925b025c26'           # the page's code version (AgentSound master commit): recipes of another say so
_GENRE_CACHE = {}


def _genre(key):
    if key not in _GENRE_CACHE:
        _GENRE_CACHE[key] = get(GENRES[key][0]).validate()
    return _GENRE_CACHE[key]


def _args():
    return types.SimpleNamespace(mood=None, swing=None, engine=None, keep=True, tries=5)


def _output(genre_key, piano, tune, song, seed, slot, extra):
    """The browser's piece: the render JSON, the display info, the recipe that reproduces it, its hash."""
    import hashlib
    genre = _genre(genre_key)
    old, MODE['piano'] = MODE['piano'], piano
    try:
        render = song.compile()
    finally:
        MODE['piano'] = old
    cli.apply_analysis(render, {'profile': genre.band.get('profile', 'jazz')})
    for t in render['tracks']:                    # (organ zones carry OS paths: '/' everywhere, the hash is portable)
        for z in t['instrument'].get('params', {}).get('samples', []) or []:
            if isinstance(z.get('file'), str):
                z['file'] = z['file'].replace(chr(92), '/')
    text = dumps(render).replace(REPO.rstrip('/') + '/assets/', '')     # sample paths relative: the hash is portable
    secs = [{'name': s.name, 'start': round(song.seconds(s.start), 3), 'end': round(song.seconds(s.end), 3)}
            for s in song.sections]
    info = {'title': tune.title, 'key': tune.key, 'tempo': tune.tempo, 'meter': f'{tune.meter}/4',
            'feel': tune.feel, 'mood': tune.mood, 'form': tune.form, 'genre': genre_key, 'piano': piano,
            'seconds': round(song.seconds(song.length), 2), 'sections': secs, **extra}
    if genre_key in ORCHESTRA:
        info['meter'] = getattr(tune, 'meter_text', info['meter'])
        info['roles'] = [t['id'] for t in render['tracks']]
    if MISSING:
        info['web_missing'] = sorted(MISSING)[:20]
    recipe = {'v': VERSION, 'g': genre_key, 'p': piano, 's': int(seed), 'slot': slot}
    return {'info': info, 'recipe': recipe, 'hash': hashlib.sha1(text.encode('utf-8')).hexdigest()[:16],
            'tune': tune.to_dict(), 'render': text}


class Session:
    """One endless stream: cmd_endless's loop (a set plan, the best of N candidates per slot), one tune at a time.
    The piano genres' and the symphony's perform ignore the tune before (build_piano / build_symphony take no prev),
    so every piece is reproduced by its recipe alone: the winning candidate's seed + its set slot (compose_recipe)."""

    def __init__(self, genre='new-age', seed=1, piano='beste', first_candidates=None, candidates=None):
        self.key, self.feel = genre, GENRES[genre][1]
        self.genre = _genre(genre)
        self.piano = piano if genre not in ORCHESTRA else 'beste'
        self.set_seed = self.seed = int(seed)
        self.n_first = int(first_candidates or GENRES[genre][2])
        self.n = int(candidates or GENRES[genre][3])
        self.args = _args()
        self.set_n = self.genre.arc['set']['tunes']
        self.plan, self.set_k, self.prev, self.prev_key = [], 0, None, None
        self.index, self.log = 0, []

    def _slot(self):
        if self.set_k >= len(self.plan):                    # a new set: its plan, from the key the last one ended in
            self.prev = None
            if self.feel:                                   # 'walzer': the set's waltz slots only
                pool = set_plan(self.genre, 3 * self.set_n, self.seed, mood=None, prev_key=self.prev_key)
                self.plan = [s for s in pool if s.get('feel') == self.feel][:self.set_n]
            else:
                self.plan = set_plan(self.genre, self.set_n, self.seed, mood=None, prev_key=self.prev_key)
            self.set_k = 0
        return self.plan[self.set_k]

    def _accept(self, tune, song):
        self.prev, self.prev_key = song, tune.key
        self.set_k, self.index = self.set_k + 1, self.index + 1

    def next(self):
        t0 = time.perf_counter()
        slot = self._slot()
        n = self.n_first if self.index == 0 else self.n
        got = None
        if n > 1:
            ranked = R.candidates(self.genre, self.seed, n, self.args, self.log.append, plan=slot, prev=self.prev)
            self.seed += R.seeds_for(self.genre, n)
            if ranked:
                got = (ranked[0]['tune'], ranked[0]['song'], ranked[0]['seed'])
        else:
            for _ in range(5):
                sd = self.seed
                self.seed += 1
                try:
                    made = R.prepare(self.genre, sd, self.args, self.log.append, plan=slot, prev=self.prev)
                except ComposeError as e:
                    self.log.append(f'seed {sd}: compose error ({e})')
                    made = None
                if made:
                    got = (made[0], made[1], sd)
                    break
        if got is None:
            raise ComposeError('no candidate passed the checks')
        tune, song, sd = got
        extra = {'index': self.index + 1, 'set_seed': self.set_seed, 'set_slot': self.set_k + 1,
                 'set_size': len(self.plan), 'candidates': n}
        self._accept(tune, song)
        out = _output(self.key, self.piano, tune, song, sd, slot, extra)
        out['info']['compose_s'] = round(time.perf_counter() - t0, 2)
        return out

    def skip_first(self, key):
        """Continue a set whose first piece came from the bank (composed natively by the same code, best of
        n_first): the state after it, without composing it."""
        assert self.index == 0
        self._slot()
        self.seed += R.seeds_for(self.genre, self.n_first) if self.n_first > 1 else 1
        self.prev_key = key
        self.set_k, self.index = self.set_k + 1, self.index + 1


def compose_recipe(recipe):
    """Re-make one piece from its recipe (history, share links). The same render JSON as when it was first made;
    a recipe of another page version is made with this code (info['other_version']: it may sound different)."""
    import gc
    t0 = time.perf_counter()
    if recipe.get('g') not in GENRES:
        raise ComposeError(f"unknown genre {recipe.get('g')!r}")
    genre = _genre(recipe['g'])
    made = R.prepare(genre, int(recipe['s']), _args(), lambda m: None, plan=recipe['slot'])
    if not made:
        raise ComposeError('the recipe no longer composes')
    tune, song = made
    piano = recipe.get('p', 'beste') if recipe['g'] not in ORCHESTRA else 'beste'
    out = _output(recipe['g'], piano, tune, song, recipe['s'], recipe['slot'], {'index': 0, 'candidates': 0})
    if recipe.get('v') != VERSION:
        out['info']['other_version'] = recipe.get('v')
    out['info']['compose_s'] = round(time.perf_counter() - t0, 2)
    gc.collect()
    return out


SESSION = {}


def start(genre, seed, piano='beste', first_candidates=None, candidates=None, after_bank_key=None):
    MODE['piano'] = piano if genre not in ORCHESTRA else 'beste'
    SESSION['s'] = Session(genre, seed, piano, first_candidates, candidates)
    if after_bank_key:
        SESSION['s'].skip_first(after_bank_key)
    return 'ok'


def next_piece():
    import gc
    out = json.dumps(SESSION['s'].next(), ensure_ascii=False)
    gc.collect()
    return out


def recipe_piece(recipe_json):
    return json.dumps(compose_recipe(json.loads(recipe_json)), ensure_ascii=False)
