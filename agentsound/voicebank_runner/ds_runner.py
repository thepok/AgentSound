"""DiffSinger ONNX runner (runs INSIDE WSL in ~/services/singing/.venv - numpy + onnxruntime; NOT imported by
agentsound, which is stdlib only).

The voicebanks we use are packaged for OpenUtau: ONNX exports of DiffSinger's acoustic model, a linguistic encoder +
duration predictor (dsdur/), a linguistic encoder + pitch predictor (dspitch/), optionally a variance predictor
(dsvariance/) and their own vocoder (dsvocoder/). DiffSinger's own inference scripts load PyTorch checkpoints, not
these exports, so this small runner drives the ONNX graphs directly, the way OpenUtau's DiffSinger renderer does.

    python ds_runner.py request.json response.json

request.json: {"bank": "/mnt/d/.../assets/voices/hanami", "provider": "cuda" | "cpu", "jobs": [job, ...]}
Jobs (all lengths in frames of hop_size / sample_rate, e.g. 512 / 44100 = 11.6 ms):
  {"op": "info"}
      -> {"phonemes": [...], "speakers": [...], "sample_rate", "hop_size", "acoustic": {...flags}, "has": {...}}
  {"op": "duration", "phonemes": [...], "word_div": [...], "word_dur": [...], "ph_midi": [...],
   "speaker": {"Root": 1.0}}
      -> {"ph_dur": [float frames per phoneme]}
  {"op": "pitch", "phonemes": [...], "ph_dur": [...], "note_midi": [...], "note_rest": [...], "note_dur": [...],
   "pitch": [midi per frame], "expr": [0..1 per frame] | number, "retake": [bool per frame] | true,
   "speaker": {...} | {"Root": [w per frame], ...}, "steps": 10}
      -> {"pitch": [midi per frame]}
  {"op": "sing", "phonemes": [...], "durations": [frames], "f0": [Hz per frame],
   "gender": [per frame] | number, "velocity": [per frame] | number, "speaker": {...}, "depth": 0.6,
   "steps": 20, "out": "/mnt/.../x.wav", "gain_db": 0 | [dB per frame], "seed": n (optional)}
      -> {"samples": n, "sample_rate": sr, "peak": float, "out": path}
A "speaker" mix is {name: weight} (constant) or {name: [weight per frame]} (a per-frame blend of the bank's
speaker / voice-mode embeddings, normalised to sum 1 per frame).
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
import wave

import numpy as np
import onnxruntime as ort
import yaml


def _yaml(path):
    with open(path, encoding='utf-8') as f:
        return yaml.safe_load(f)


class Bank:
    def __init__(self, root: str, provider: str = 'cuda'):
        self.root = root.rstrip('/')
        self.cfg = _yaml(f'{self.root}/dsconfig.yaml')
        self.providers = ['CPUExecutionProvider']
        if provider == 'cuda' and 'CUDAExecutionProvider' in ort.get_available_providers():
            try:                     # the CUDA / cuDNN libraries of the nvidia-* wheels in this venv
                if hasattr(ort, 'preload_dlls'):
                    ort.preload_dlls()
                self.providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            except Exception:  # noqa: BLE001 - no usable CUDA: the CPU does it (slower)
                pass
        self.phonemes = self._phonemes(f"{self.root}/{self.cfg['phonemes']}")
        self.sr = int(self.cfg.get('sample_rate', 44100))
        self.hop = int(self.cfg.get('hop_size', 512))
        self.hidden = int(self.cfg.get('hidden_size', 256))
        self._sessions: dict = {}
        self.speakers = self._embeds(self.cfg.get('speakers') or [], self.root)
        self.dur_cfg = self._sub('dsdur')
        self.pitch_cfg = self._sub('dspitch')
        voc_dir = f'{self.root}/dsvocoder'
        self.voc_cfg = _yaml(f'{voc_dir}/vocoder.yaml') if os.path.isfile(f'{voc_dir}/vocoder.yaml') else None

    @staticmethod
    def _phonemes(path):
        if path.endswith('.json'):
            with open(path, encoding='utf-8') as f:
                m = json.load(f)
            return dict(m)
        with open(path, encoding='utf-8') as f:
            names = [ln.strip() for ln in f if ln.strip()]
        return {n: i for i, n in enumerate(names)}

    @staticmethod
    def _embeds(paths, base):
        out = {}
        for p in paths:
            name = p.rstrip('/').split('/')[-1]
            out[name] = np.fromfile(f'{base}/{p}.emb', dtype=np.float32)
        return out

    def _sub(self, folder):
        p = f'{self.root}/{folder}/dsconfig.yaml'
        if not os.path.isfile(p):
            return None
        c = _yaml(p)
        c['_dir'] = f'{self.root}/{folder}'
        c['_speakers'] = self._embeds(c.get('speakers') or [], c['_dir'])
        return c

    def session(self, path):
        s = self._sessions.get(path)
        if s is None:
            so = ort.SessionOptions()
            so.log_severity_level = 3
            s = ort.InferenceSession(path, sess_options=so, providers=self.providers)
            self._sessions[path] = s
        return s

    def tokens(self, phonemes):
        bad = [p for p in phonemes if p not in self.phonemes]
        if bad:
            raise ValueError(f"phonemes not in this bank: {sorted(set(bad))}")
        return np.array([[self.phonemes[p] for p in phonemes]], dtype=np.int64)

    # ---- speaker mixes
    def spk(self, mix, n, table):
        """[1, n, hidden] from {name: weight | [weights]}; missing -> the first speaker."""
        if not table:
            return None
        if not mix:
            mix = {next(iter(table)): 1.0}
        acc = np.zeros((n, self.hidden), dtype=np.float32)
        wsum = np.zeros((n, 1), dtype=np.float32)
        for name, w in mix.items():
            if name not in table:
                raise ValueError(f"unknown speaker {name!r}; this bank has {list(table)}")
            w = np.asarray(w, dtype=np.float32)
            w = np.full((n,), float(w)) if w.ndim == 0 else _fit(w, n)
            acc += w[:, None] * table[name][None, :]
            wsum += w[:, None]
        wsum[wsum <= 1e-6] = 1.0
        return (acc / wsum)[None].astype(np.float32)

    # ---- ops
    def info(self, job):
        ac = self.session(f"{self.root}/{self.cfg['acoustic']}")
        return {'phonemes': list(self.phonemes), 'speakers': list(self.speakers), 'sample_rate': self.sr,
                'hop_size': self.hop,
                'acoustic_inputs': [i.name for i in ac.get_inputs()],
                'has': {'duration': self.dur_cfg is not None, 'pitch': self.pitch_cfg is not None,
                        'vocoder': self.voc_cfg is not None},
                'augmentation': self.cfg.get('augmentation_args'), 'max_depth': self.cfg.get('max_depth')}

    def duration(self, job):
        c = self.dur_cfg
        if c is None:
            raise ValueError('this bank has no duration model (dsdur/)')
        toks = self.tokens(job['phonemes'])
        n = toks.shape[1]
        ling = self.session(f"{c['_dir']}/{c['linguistic']}")
        feeds = {'tokens': toks, 'word_div': np.array([job['word_div']], dtype=np.int64),
                 'word_dur': np.array([job['word_dur']], dtype=np.int64)}
        enc, mask = ling.run(None, _only(ling, feeds))
        dur = self.session(f"{c['_dir']}/{c['dur']}")
        feeds = {'encoder_out': enc, 'x_masks': mask, 'ph_midi': np.array([job['ph_midi']], dtype=np.int64)}
        sp = self.spk(job.get('speaker'), n, c['_speakers'])
        if sp is not None:
            feeds['spk_embed'] = sp
        out = dur.run(None, _only(dur, feeds))[0]
        return {'ph_dur': [float(x) for x in out[0]]}

    def pitch(self, job):
        c = self.pitch_cfg
        if c is None:
            raise ValueError('this bank has no pitch model (dspitch/)')
        toks = self.tokens(job['phonemes'])
        ph_dur = np.array([job['ph_dur']], dtype=np.int64)
        nf = int(ph_dur.sum())
        ling = self.session(f"{c['_dir']}/{c['linguistic']}")
        enc, mask = ling.run(None, _only(ling, {'tokens': toks, 'ph_dur': ph_dur}))
        sess = self.session(f"{c['_dir']}/{c['pitch']}")
        _seed(job)
        expr = job.get('expr', 1.0)
        retake = job.get('retake', True)
        feeds = {'encoder_out': enc, 'ph_dur': ph_dur,
                 'note_midi': np.array([job['note_midi']], dtype=np.float32),
                 'note_rest': np.array([job['note_rest']], dtype=bool),
                 'note_dur': np.array([job['note_dur']], dtype=np.int64),
                 'pitch': _fit(np.asarray(job['pitch'], dtype=np.float32), nf)[None],
                 'expr': (np.full((1, nf), float(expr), np.float32) if np.ndim(expr) == 0
                          else _fit(np.asarray(expr, np.float32), nf)[None]),
                 'retake': (np.full((1, nf), bool(retake)) if np.ndim(retake) == 0
                            else _fit(np.asarray(retake, np.float32), nf)[None] > 0.5),
                 'steps': np.array(int(job.get('steps', 10)), dtype=np.int64)}
        sp = self.spk(job.get('speaker'), nf, c['_speakers'])
        if sp is not None:
            feeds['spk_embed'] = sp
        out = sess.run(None, _only(sess, feeds))[0]
        return {'pitch': [round(float(x), 4) for x in out[0]]}

    def sing(self, job):
        _seed(job)
        toks = self.tokens(job['phonemes'])
        durs = np.array([job['durations']], dtype=np.int64)
        nf = int(durs.sum())
        f0 = _fit(np.asarray(job['f0'], dtype=np.float32), nf)
        ac = self.session(f"{self.root}/{self.cfg['acoustic']}")
        names = {i.name for i in ac.get_inputs()}
        feeds = {'tokens': toks, 'durations': durs, 'f0': f0[None]}
        if 'gender' in names:
            g = job.get('gender', 0.0)
            feeds['gender'] = (np.full((1, nf), float(g), np.float32) if np.ndim(g) == 0
                               else _fit(np.asarray(g, np.float32), nf)[None])
        if 'velocity' in names:
            v = job.get('velocity', 1.0)
            feeds['velocity'] = (np.full((1, nf), float(v), np.float32) if np.ndim(v) == 0
                                 else _fit(np.asarray(v, np.float32), nf)[None])
        for k in ('energy', 'breathiness', 'voicing', 'tension'):
            if k in names:
                v = job.get(k, 0.0)
                feeds[k] = (np.full((1, nf), float(v), np.float32) if np.ndim(v) == 0
                            else _fit(np.asarray(v, np.float32), nf)[None])
        if 'spk_embed' in names:
            feeds['spk_embed'] = self.spk(job.get('speaker'), nf, self.speakers)
        if 'depth' in names:
            feeds['depth'] = np.array(float(job.get('depth', self.cfg.get('max_depth', 1.0))), dtype=np.float32)
        if 'steps' in names:
            feeds['steps'] = np.array(int(job.get('steps', 20)), dtype=np.int64)
        if 'speedup' in names:
            steps = int(job.get('steps', 20))
            sp = max(1, 1000 // steps)
            while 1000 % sp and sp > 1:
                sp -= 1
            feeds['speedup'] = np.array(sp, dtype=np.int64)
        missing = names - set(feeds)
        if missing:
            raise ValueError(f"acoustic model needs inputs this runner does not know: {sorted(missing)}")
        mel = ac.run(None, feeds)[0]
        voc = self.session(f"{self.root}/dsvocoder/{self.voc_cfg['model']}")
        wav = voc.run(None, _only(voc, {'mel': mel.astype(np.float32), 'f0': f0[None]}))[0][0]
        g = job.get('gain_db', 0.0)
        if np.ndim(g) == 0:
            wav = wav * 10 ** (float(g) / 20)
        else:                                   # dB per frame -> per sample (linear between frame centres)
            gd = _fit(np.asarray(g, np.float64), nf)
            hop = wav.size / max(nf, 1)
            xs = (np.arange(nf) + 0.5) * hop
            wav = wav * 10 ** (np.interp(np.arange(wav.size), xs, gd) / 20)
        peak = float(np.max(np.abs(wav))) if wav.size else 0.0
        out = job['out']
        _write_wav(out, wav, int(self.voc_cfg.get('sample_rate', self.sr)))
        return {'samples': int(wav.size), 'sample_rate': int(self.voc_cfg.get('sample_rate', self.sr)),
                'peak': peak, 'out': out}


def _seed(job) -> None:
    """The diffusion samplers draw random noise inside the ONNX graphs: seed onnxruntime per job (the job's 'seed',
    else a hash of the job) so the same job gives the same take on the same machine and provider."""
    if not hasattr(ort, 'set_seed'):
        return
    s = job.get('seed')
    if s is None:
        import hashlib
        s = int(hashlib.sha1(json.dumps({k: v for k, v in job.items() if k != 'out'}, sort_keys=True)
                             .encode('utf-8')).hexdigest()[:8], 16)
    ort.set_seed(int(s) % (2 ** 31 - 1))


def _fit(a, n):
    a = np.asarray(a).reshape(-1)
    if a.size == n:
        return a
    if a.size == 0:
        return np.zeros(n, dtype=np.float32)
    if a.size > n:
        return a[:n]
    return np.concatenate([a, np.full(n - a.size, a[-1], dtype=a.dtype)])


def _only(sess, feeds):
    names = {i.name for i in sess.get_inputs()}
    return {k: v for k, v in feeds.items() if k in names}


def _write_wav(path, x, sr):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    y = np.clip(np.asarray(x, dtype=np.float64), -1.0, 1.0)
    pcm = (y * 32767.0).round().astype('<i2')
    tmp = path + '.part'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    os.replace(tmp, path)


def main(argv):
    if len(argv) != 3:
        print(__doc__)
        return 2
    with open(argv[1], encoding='utf-8') as f:
        req = json.load(f)
    t0 = time.time()
    bank = Bank(req['bank'], req.get('provider', 'cuda'))
    results = []
    for job in req['jobs']:
        op = job.get('op')
        fn = {'info': bank.info, 'duration': bank.duration, 'pitch': bank.pitch, 'sing': bank.sing}.get(op)
        try:
            if fn is None:
                raise ValueError(f"unknown op {op!r}")
            results.append({'ok': True, **fn(job)})
        except Exception as e:  # noqa: BLE001 - every job reports its own error
            results.append({'ok': False, 'error': f"{type(e).__name__}: {e}"})
    providers = sorted({p for s in bank._sessions.values() for p in s.get_providers()[:1]})
    with open(argv[2], 'w', encoding='utf-8') as f:
        json.dump({'results': results, 'seconds': round(time.time() - t0, 2), 'providers': providers}, f)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
