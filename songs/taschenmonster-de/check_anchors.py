"""Measure the rendered score against the picture: python songs/taschenmonster-de/check_anchors.py

Reads song.py's anchors (HITS, GATES, TOTAL - live from the episode files, the same as the build) and out/mix.wav:
  - hits: the onset (5 ms frames, energy jump >= 6 dB: 30 ms after vs the 20 ms before) nearest each anchor within
    +-150 ms (or the strongest jump there) -> its offset in ms and the jump in dB (ok: |offset| <= 30 ms and jump >= 6 dB)
  - gates: the music level under each burp (ok: below -60 dBFS)
  - npc: the two NPC loops (lines 13 and 28) compared sample by sample (ok: the difference is >= 30 dB down)
  - length: the mix length vs the timeline total
Writes out/anchors.json and prints a table.
"""
import importlib.util
import json
import sys
import wave
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent


def load_song():
    sys.path.insert(0, str(HERE.parents[1]))
    spec = importlib.util.spec_from_file_location('taschenmonster_song', HERE / 'song.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_wav(path):
    with wave.open(str(path), 'rb') as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        v = np.where(v >= 1 << 23, v - (1 << 24), v)
        x = v.astype(np.float64) / (1 << 23)
    else:
        x = np.frombuffer(raw, dtype=np.int32).astype(np.float64) / 2 ** 31
    return sr, x.reshape(-1, ch).mean(1)


def main():
    mod = load_song()
    sr, x = read_wav(HERE / 'out' / 'mix.wav')
    hop = int(sr * 0.005)
    nfr = len(x) // hop
    e = (x[:nfr * hop].reshape(nfr, hop) ** 2).mean(1) + 1e-12

    def db(v):
        return 10 * np.log10(v)

    def jump(k):
        a = e[max(0, k - 4):k].mean() if k > 0 else 1e-12          # the 20 ms before (a cut-then-hit counts)
        b = e[k:k + 6].mean()
        return db(b) - db(a)

    hits = []
    for name, t in sorted(mod.HITS.items(), key=lambda kv: kv[1]):
        k0 = int(round(t / 0.005))
        rng = range(max(1, k0 - 30), min(nfr - 6, k0 + 31))
        strong = [k for k in rng if jump(k) >= 6.0 and jump(k) >= jump(k - 1) and jump(k) >= jump(k + 1)]
        best = min(strong, key=lambda k: abs(k - k0)) if strong else max(rng, key=jump)   # the onset nearest the cue
        off = (best - k0) * 5.0
        j = jump(best)
        hits.append({'cue': name, 't': round(t, 3), 'offsetMs': off, 'jumpDb': round(float(j), 1),
                     'ok': bool(abs(off) <= 30 and j >= 6.0)})
    gates = []
    for b0, b1 in mod.GATES:
        seg = x[int((b0 + 0.02) * sr):int((b1 + 0.02) * sr)]
        lvl = 20 * np.log10(np.sqrt((seg ** 2).mean()) + 1e-12) if len(seg) else -999
        gates.append({'burp': [round(b0, 3), round(b1, 3)], 'rmsDbfs': round(float(lvl), 1), 'ok': bool(lvl < -60)})
    # the NPC loop: identical audio twice?
    # (from 1 s in: before that the previous scene's reverb tails still ring)
    a0, a1 = mod.L(13) - mod.NPC_PRE + 1.0, mod.L(28) - mod.NPC_PRE + 1.0
    dur = min(mod.SPANS[13][1] - 1.0, 8.0)
    s0, s1 = x[int(a0 * sr):int((a0 + dur) * sr)], x[int(a1 * sr):int((a1 + dur) * sr)]
    nn = min(len(s0), len(s1))
    best = None
    for lag in range(-48, 49):                       # +-1 ms (sample rounding of the two positions)
        d = s0[max(0, lag):nn + min(0, lag)] - s1[max(0, -lag):nn - max(0, lag)]
        r = 10 * np.log10(((d ** 2).mean() + 1e-15) / ((s0 ** 2).mean() + 1e-15))
        if best is None or r < best[1]:
            best = (lag, r)
    npc = {'line13': round(a0, 3), 'line28': round(a1, 3), 'compared_s': dur, 'lagSamples': best[0],
           'differenceDb': round(float(best[1]), 1), 'ok': bool(best[1] <= -30)}
    out = {'timing': mod.TIMING_SOURCE, 'total': mod.TOTAL, 'mixSeconds': round(len(x) / sr, 3),
           'lengthOk': bool(abs(len(x) / sr - mod.TOTAL) < 0.1), 'hits': hits, 'gates': gates, 'npcLoop': npc,
           'sections': [{'name': p[0], 'start': round(p[1], 3), 'end': round(p[2], 3), 'bars': p[3],
                         'meter': '%d/%d' % p[4], 'bpm': round(mod.bpm_of(p[1], p[2], p[3], p[5]), 2)} for p in mod.PLAN]}
    (HERE / 'out' / 'anchors.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    used = json.loads((HERE / 'out' / 'anchors_build.json').read_text(encoding='utf-8'))         if (HERE / 'out' / 'anchors_build.json').is_file() else None
    moved = {k: round(mod.HITS[k] - v, 3) for k, v in (used or {}).get('hits', {}).items()
             if k in mod.HITS and abs(mod.HITS[k] - v) > 0.005}
    for p, q in zip(mod.PLAN, (used or {}).get('plan', [])):
        if p[0] != q[0] or abs(p[1] - q[1]) > 0.005:
            moved['section ' + p[0]] = round(p[1] - q[1], 3)
    if used and len(mod.PLAN) != len(used.get('plan', [])):
        moved['sections'] = f"{len(used['plan'])} -> {len(mod.PLAN)}"
    if moved:
        print(f"STALE: anchors moved since the build (s): {moved} - rebuild")
    out['movedSinceBuild'] = moved
    mix_t = (HERE / 'out' / 'mix.wav').stat().st_mtime
    newer = [f for f in ('build/timeline.json', 'manifest.json', 'episode.json')
             if (mod.EP / f).is_file() and (mod.EP / f).stat().st_mtime > mix_t]
    if newer and not moved:
        print(f"note: {', '.join(newer)} changed after the render, but no anchor the score uses moved")
    elif newer:
        print(f"STALE: {', '.join(newer)} changed after out/mix.wav was rendered - rebuild first")
    out['staleFiles'] = newer
    (HERE / 'out' / 'anchors.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(f"length {out['mixSeconds']} s vs total {mod.TOTAL:.3f} ({'ok' if out['lengthOk'] else 'MISMATCH'}), timing: {out['timing']}")
    for h in hits:
        print(f"  {'ok ' if h['ok'] else '-- '} {h['cue']:<14} {h['t']:8.3f}  {h['offsetMs']:+6.0f} ms  {h['jumpDb']:+5.1f} dB")
    for g in gates:
        print(f"  {'ok ' if g['ok'] else '-- '} burp {g['burp'][0]:.2f}-{g['burp'][1]:.2f}  {g['rmsDbfs']} dBFS")
    print(f"  {'ok ' if npc['ok'] else '-- '} NPC loop line 13 vs 28: difference {npc['differenceDb']} dB (lag {npc['lagSamples']})")


if __name__ == '__main__':
    main()
