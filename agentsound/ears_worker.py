"""The ears worker: runs INSIDE the ears venv (torch + audiobox_aesthetics + fadtk, which brings laion_clap), never
imported by the main package. `agentsound.ears` writes a request JSON, runs

    <ears python> -I agentsound/ears_worker.py request.json response.json

and reads the response. Standalone on purpose (stdlib + the venv's packages only, no agentsound import), so the main
Python never needs torch.

Request:  {"files": [{"id", "path", "start", "end", "instrument"}], "refs": [{"path", "start", "end"}],
           "ffmpeg": path, "window": 10.0, "max_windows": 12, "device": "auto"|"cpu"|"cuda", "fad": bool}
Response: {"ok": true, "device", "models": {...}, "files": [{"id", "seconds", "windows", "aesthetics": {PQ,PC,CE,CU},
           "clap": {"instrument", "pReal", "pairs": [...]}, "refCos"}], "fad": float|null, "refs": [...]}
On failure: {"ok": false, "error": "..."} (the caller prints it).
"""

from __future__ import annotations

import json
import subprocess
import sys
import traceback

SR_CLAP = 48000
SR_AES = 16000
CLAP_REPO, CLAP_FILE = 'lukewys/laion_clap', 'music_audioset_epoch_15_esc_90.14.pt'   # LAION-AI/CLAP's host

# Zero-shot realism: each pair is (real, fake); P(real) = softmax over the pair, averaged over pairs and windows.
PROMPT_PAIRS = (
    ('a real recording of a {inst} played by a human musician',
     'a MIDI {inst} played by a computer'),
    ('an acoustic {inst} recorded with microphones in a room',
     'a synthesized {inst} sound from a cheap keyboard'),
    ('an expressive live {inst} performance',
     'a mechanical, quantized {inst} sequence with fixed velocities'),
    ('a professionally produced studio recording of a {inst}',
     'a low quality computer-generated {inst} demo'),
)


def decode(ffmpeg: str, path: str, sr: int, start=None, end=None):
    import numpy as np
    cmd = [ffmpeg, '-v', 'error', '-nostdin']
    if start:
        cmd += ['-ss', f'{float(start):.3f}']
    if end is not None:
        cmd += ['-t', f'{float(end) - float(start or 0):.3f}']
    cmd += ['-i', path, '-ac', '1', '-ar', str(sr), '-f', 'f32le', '-']
    p = subprocess.run(cmd, capture_output=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg could not decode {path}: {p.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(p.stdout, dtype=np.float32).copy()


def windows(x, sr: int, win_s: float, max_n: int):
    """Up to max_n non-overlapping windows of win_s seconds spread evenly over x (skipping near-silent ones)."""
    import numpy as np
    w = int(win_s * sr)
    if len(x) <= w:
        return [x]
    n_all = len(x) // w
    idx = np.linspace(0, n_all - 1, num=min(max_n, n_all)).round().astype(int)
    out = [x[i * w:(i + 1) * w] for i in sorted(set(idx.tolist()))]
    loud = [c for c in out if float(np.sqrt(np.mean(c ** 2))) > 1e-3]   # -60 dBFS: not a silent gap
    return loud or out


class Ears:
    def __init__(self, device: str):
        import torch
        if device == 'auto':
            device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.device = device
        self._clap = None
        self._aes = None
        self.models = {'torch': torch.__version__, 'device': device}

    # ------------------------------------------- LAION-CLAP music (laion_clap package, checkpoint CC0-1.0)
    # The transformers port laion/larger_clap_music gives near-zero audio-text similarity (equal zero-shot outputs,
    # see its HF discussion #2), so the original checkpoint runs through the laion_clap package (as fadtk does).
    def clap(self):
        if self._clap is None:
            import laion_clap
            from huggingface_hub import hf_hub_download
            ckpt = hf_hub_download(CLAP_REPO, CLAP_FILE)
            model = laion_clap.CLAP_Module(enable_fusion=False, amodel='HTSAT-base', device=self.device)
            model.load_ckpt(ckpt, verbose=False)
            self._clap = model
            self.models['clap'] = f'{CLAP_REPO}/{CLAP_FILE}'
        return self._clap

    def clap_audio(self, chunks):
        import torch
        model = self.clap()
        embs = []
        for i in range(0, len(chunks), 8):
            with torch.no_grad():
                e = model.get_audio_embedding_from_data(chunks[i:i + 8], use_tensor=False)
            embs.append(torch.nn.functional.normalize(torch.from_numpy(e).float(), dim=-1))
        return torch.cat(embs)

    def clap_text(self, texts):
        import torch
        model = self.clap()
        with torch.no_grad():
            e = model.get_text_embedding(list(texts), use_tensor=False)
        return torch.nn.functional.normalize(torch.from_numpy(e).float(), dim=-1)

    def realism(self, audio_emb, inst: str):
        import torch
        scale = float(self.clap().model.logit_scale_a.exp().detach())
        pairs = []
        for real, fake in PROMPT_PAIRS:
            t = self.clap_text([real.format(inst=inst), fake.format(inst=inst)])
            logits = scale * audio_emb @ t.T                       # windows x 2
            p = torch.softmax(logits, dim=-1)[:, 0]
            pairs.append({'real': real.format(inst=inst), 'fake': fake.format(inst=inst),
                          'pReal': round(float(p.mean()), 4)})
        return {'instrument': inst, 'pReal': round(sum(q['pReal'] for q in pairs) / len(pairs), 4), 'pairs': pairs}

    # ---------------------------------------------------------- Audiobox Aesthetics (CC-BY-4.0, facebook/...)
    def aesthetics(self, chunks):
        import torch
        if self._aes is None:
            from audiobox_aesthetics.infer import initialize_predictor
            self._aes = initialize_predictor()
            self.models['audiobox'] = 'facebook/audiobox-aesthetics'
        batch = [{'path': torch.from_numpy(c).unsqueeze(0), 'sample_rate': SR_AES} for c in chunks]
        rows = self._aes.forward(batch)
        keys = ('PQ', 'PC', 'CE', 'CU')
        return {k: round(sum(float(r[k]) for r in rows) / len(rows), 3) for k in keys}


def frechet(a, b) -> float:
    """Frechet distance between two embedding sets (rows = embeddings); fadtk's implementation when present."""
    import numpy as np
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mu1, mu2 = a.mean(0), b.mean(0)
    s1, s2 = np.cov(a, rowvar=False), np.cov(b, rowvar=False)
    try:
        from fadtk.fad import calc_frechet_distance
        return float(calc_frechet_distance(mu1, s1, mu2, s2))
    except ImportError:
        from scipy import linalg
        covmean, _ = linalg.sqrtm(s1.dot(s2), disp=False)
        if np.iscomplexobj(covmean):
            covmean = covmean.real
        d = mu1 - mu2
        return float(d.dot(d) + np.trace(s1) + np.trace(s2) - 2 * np.trace(covmean))


def run(req: dict) -> dict:
    ears = Ears(req.get('device', 'auto'))
    ff = req['ffmpeg']
    win, max_n = float(req.get('window', 10.0)), int(req.get('max_windows', 12))
    ref_embs = []
    refs_out = []
    for r in req.get('refs', []):
        x = decode(ff, r['path'], SR_CLAP, r.get('start'), r.get('end'))
        e = ears.clap_audio(windows(x, SR_CLAP, win, max_n))
        ref_embs.append(e)
        refs_out.append({'path': r['path'], 'windows': int(e.shape[0])})
    files_out = []
    all_embs = []
    for f in req['files']:
        x48 = decode(ff, f['path'], SR_CLAP, f.get('start'), f.get('end'))
        ch48 = windows(x48, SR_CLAP, win, max_n)
        emb = ears.clap_audio(ch48)
        all_embs.append(emb)
        x16 = decode(ff, f['path'], SR_AES, f.get('start'), f.get('end'))
        row = {'id': f['id'], 'path': f['path'], 'seconds': round(len(x48) / SR_CLAP, 2), 'windows': len(ch48),
               'aesthetics': ears.aesthetics(windows(x16, SR_AES, win, max_n)),
               'clap': ears.realism(emb, f.get('instrument') or 'music')}
        if ref_embs:
            import torch
            m = torch.nn.functional.normalize(emb.mean(0), dim=-1)
            r = torch.nn.functional.normalize(torch.cat(ref_embs).mean(0), dim=-1)
            row['refCos'] = round(float(m @ r), 4)
        files_out.append(row)
    fad = None
    if req.get('fad') and ref_embs:
        import torch
        a, b = torch.cat(all_embs).numpy(), torch.cat(ref_embs).numpy()
        if min(len(a), len(b)) >= 8:
            fad = round(frechet(a, b), 4)
    return {'ok': True, 'device': ears.device, 'models': ears.models, 'files': files_out, 'refs': refs_out,
            'fad': fad}


def main(argv) -> int:
    req_path, resp_path = argv[1], argv[2]
    with open(req_path, encoding='utf-8') as fh:
        req = json.load(fh)
    try:
        resp = run(req)
    except Exception as e:   # the caller reports it; the traceback goes to stderr
        traceback.print_exc()
        resp = {'ok': False, 'error': f"{type(e).__name__}: {e}"}
    with open(resp_path, 'w', encoding='utf-8') as fh:
        json.dump(resp, fh, indent=1)
    return 0 if resp.get('ok') else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
