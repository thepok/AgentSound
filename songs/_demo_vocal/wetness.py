"""How wet is a sung vocal? (recipes/HUMAN_FEEDBACK.md "Vocals": "der Gesang hat immer viel Hall und/oder Reverb")

    python songs/_demo_vocal/wetness.py songs/<slug> [--from-beat X --to-beat Y] [--json out.json]

Renders the song with every non-vocal track muted (a muted track feeds no send either), so each return bus carries
only what the sung tracks send into it, and writes the stems. Measured (numpy; BS.1770 K-weighting):
  dry_lufs / wet_lufs   the sung tracks (+ their grit buses: distortion of the dry voice, not space) vs the sum of
                        every return bus, over the same gated 400 ms blocks; wet_lu = wet - dry (LU: how far the
                        reverb / echo sits under the voice), per bus in `buses`
  tail                  at every phrase end with >= 1 s of rest: the returns 250 / 500 ms after the voice stopped
                        (dB vs the phrase's last 400 ms of dry voice) and the decay time to -30 dB of voice + returns
                        (median over the phrase ends)
  take_tail_db          the raw DiffSinger takes (the cached phrase WAVs): 30-250 ms after the last phoneme vs the
                        last vowel (a dry take falls to the noise floor: < -45 dB)
  singing               the lead part's moves (plan: scoops / vibrato / falls / doits) and what the rendered curves
                        did: scooped onsets (> 25 ct under the note in the vowel's first 150 ms, at phrase openers
                        and after a note at or above it) and their depth, the time every note takes to settle
                        (within 25 ct for 60 ms, from the vowel onset),
                        the vibrato's extent (+- ct) and rate on held notes, the voice-mode blend (soft / power share
                        of the vowels), the dynamics (the takes' gain lane and the dry stem's per-note levels, p10-p90),
                        the sibilance (s / z / sh / ch at 5-12 kHz vs the neighbouring vowel, dry stem) and the
                        word-final consonants at 2-8 kHz vs the 120 ms of vowel before them (codas)
Used by songs/jane-street-bossa/dry_ab.py and songs/_demo_vocal_rock/grit_rock_dry.py.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(HERE))
import grit_ab as G      # noqa: E402  (the shared wav / K-weighting helpers)

FR = 512 / 44100


def load(song_py: Path, env: dict | None = None, before=None):
    """The song of a song file (build()), with env vars set while it builds and before(module) called first (to
    change module constants for a variant). The module MIX is applied like the CLI does."""
    from agentsound import cli
    old = dict(os.environ)
    os.environ.update(env or {})
    try:
        name = 'wet_song_' + re.sub(r'\W', '_', song_py.parent.name)
        spec = importlib.util.spec_from_file_location(name, song_py)
        mod = importlib.util.module_from_spec(spec)
        sys.path.insert(0, str(song_py.parent))
        spec.loader.exec_module(mod)
        if before is not None:
            before(mod)
        song = mod.build()
        song.delivery_settings = {'METADATA': getattr(mod, 'METADATA', None), 'COVER': getattr(mod, 'COVER', None),
                                  'dir': song_py.parent}
        song.module_mix = getattr(mod, 'MIX', None)
        cli.apply_module_mix(song)
        return song
    finally:
        os.environ.clear()
        os.environ.update(old)


def _sung(song) -> list:
    return [t for t in song.tracks.values() if getattr(t, '_singer', None)]


def render_vocal_only(song, out: Path, from_beat=None, to_beat=None) -> dict:
    """Render with every non-vocal track muted, stems on, into `out` (returns the render dict)."""
    from agentsound import cli
    render = song.compile()
    vids = {t.id for t in _sung(song)}
    for t in render['tracks']:
        if t['id'] not in vids:
            t['mute'] = True
    render.setdefault('export', {})['stems'] = True
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True, exist_ok=True)
    rj = cli.write_render(render, out / 'vocal_only.render.json')
    cmd = [str(cli.find_engine()), 'render', str(rj), '--out', str(out), '--no-analysis', '--no-png', '--quiet']
    if from_beat is not None:
        cmd += ['--from-beat', f'{from_beat:g}']
    if to_beat is not None:
        cmd += ['--to-beat', f'{to_beat:g}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(f"engine failed: {r.stderr or r.stdout}")
    return render


def _kw(x, fs):
    return G._sos(x, [G._rbj('shelf', 1681.97, fs, 0.7072, 3.9998), G._rbj('hp', 38.13, fs, 0.5003)], fs)


def _lvl(y, fs, a, b) -> float:
    import numpy as np
    i0, i1 = max(0, int(a * fs)), min(len(y), int(b * fs))
    if i1 - i0 < 16:
        return -120.0
    return float(-0.691 + 10 * np.log10(np.mean(y[i0:i1] ** 2, axis=0).sum() + 1e-20))


def wetness(song, out: Path, from_beat=None, to_beat=None) -> dict:
    """The dry / wet numbers of a song's sung tracks (see the module docstring)."""
    import numpy as np
    render = render_vocal_only(song, out, from_beat, to_beat)
    vids = [t.id for t in _sung(song)]
    st = out / 'stems'
    dry, fs = None, 44100
    for vid in vids + [f'{v}_grit' for v in vids]:
        p = st / f'{vid}.wav'
        if p.is_file():
            x, fs = G._read(p)
            dry = x if dry is None else dry + x
    grit_ids = {f'{v}_grit' for v in vids}
    buses = {}
    for b in render['buses']:
        if b['id'] in grit_ids:
            continue
        p = st / f"{b['id']}.wav"
        if p.is_file():
            x, _ = G._read(p)
            if float(np.max(np.abs(x))) > 1e-6:
                buses[b['id']] = x
    n = len(dry)
    wet = np.zeros_like(dry)
    for x in buses.values():
        wet[:min(n, len(x))] += x[:n]
    kd, kwt = _kw(dry, fs), _kw(wet, fs)
    kb = {k: _kw(x[:n], fs) for k, x in buses.items()}
    blk, hop = int(0.4 * fs), int(0.1 * fs)
    idx = range(0, n - blk, hop)

    def ms(y):
        return np.array([np.mean(y[i:i + blk] ** 2, axis=0).sum() for i in idx])
    md, mw = ms(kd), ms(kwt)
    tot = md + mw
    lk = -0.691 + 10 * np.log10(tot + 1e-20)
    g = lk > -70
    rel = -0.691 + 10 * np.log10(tot[g].mean()) - 10
    g = g & (lk > rel)

    def lu(m):
        return round(float(-0.691 + 10 * np.log10(m[g].mean() + 1e-20)), 2)
    res = {'dry_lufs': lu(md), 'wet_lufs': lu(mw)}
    res['wet_lu'] = round(res['wet_lufs'] - res['dry_lufs'], 2)
    res['buses'] = {k: round(lu(ms(y)) - res['dry_lufs'], 2) for k, y in kb.items()}
    # the phrase ends
    t_off = song.seconds(from_beat) if from_beat is not None else 0.0
    lead = song.tracks[vids[0]]
    ends = []
    for vo in lead._singer['parts']:
        for k, ph in enumerate(vo.phrases):
            z = vo.notes[ph[-1]]
            te = song.seconds(z.start + z.dur) + vo.offset_ms / 1000.0 - t_off
            nxt = (song.seconds(vo.notes[vo.phrases[k + 1][0]].start) - t_off) if k + 1 < len(vo.phrases) else te + 4
            ends.append((te, nxt))
    ends.sort()
    allstarts = sorted(song.seconds(vo.notes[ph[0]].start) - t_off for t in _sung(song)
                       for vo in t._singer['parts'] for ph in vo.phrases)
    kt = kd + kwt
    tails = []
    for te, nxt in ends:
        nxt = min([nxt] + [s for s in allstarts if s > te + 0.05])
        if nxt - te < 1.0 or te < 0.5 or te + 0.6 > n / fs:
            continue
        lp = _lvl(kd, fs, te - 0.4, te)
        if lp < -60:
            continue
        # where the voice really stops (codas / releases run to the note end and a little past it)
        t = te - 0.3
        stop = te
        while t < te + 0.5:
            if _lvl(kd, fs, t, t + 0.01) > lp - 25:
                stop = t + 0.01
            t += 0.01
        lim = nxt - 0.45                 # before the next phrase's breath
        if stop + 0.55 > lim:
            continue
        w250 = _lvl(kwt, fs, stop + 0.225, stop + 0.275) - lp
        w500 = _lvl(kwt, fs, stop + 0.475, stop + 0.525) - lp
        d250 = _lvl(kd, fs, stop + 0.225, stop + 0.275) - lp
        dec = None
        t = stop
        while t < lim:
            if _lvl(kt, fs, t, t + 0.05) < lp - 30:
                dec = round(t - stop, 3)
                break
            t += 0.01
        tails.append({'at': round(stop + t_off, 2), 'wet_250': round(w250, 1), 'wet_500': round(w500, 1),
                      'dry_250': round(d250, 1), 'decay30_s': dec if dec is not None else f'>{lim - stop:.2f}'})

    def med(v):
        v = sorted(v)
        return round(v[len(v) // 2], 1) if v else None
    res['tail'] = {'phrase_ends': len(tails), 'wet_250_db': med([x['wet_250'] for x in tails]),
                   'wet_500_db': med([x['wet_500'] for x in tails]),
                   'dry_250_db': med([x['dry_250'] for x in tails]),
                   'decay30_s': med([x['decay30_s'] if isinstance(x['decay30_s'], float) else
                                     float(x['decay30_s'][1:]) for x in tails]),
                   'decay30_capped': sum(isinstance(x['decay30_s'], str) for x in tails)}
    res['tails'] = tails
    return res


def take_tails(song) -> dict:
    """The raw takes: level 30-250 ms after the last phoneme vs the last vowel (dB), median / worst."""
    import numpy as np
    from agentsound.lyrics import VOWELS
    vals = []
    for t in _sung(song):
        for vo in t._singer['parts']:
            for r in getattr(vo, 'rendered', []) or []:
                p = Path(r['path'])
                tl = json.loads(p.with_suffix('.json').read_text(encoding='utf-8'))['timeline']
                x, fs = G._read(p)
                m = x.mean(axis=1)
                o = tl['offset_s']
                toks = [tk for tk in tl['tokens'] if tk[0] not in ('SP', 'AP')]
                vow = [tk for tk in toks if tk[0] in VOWELS]
                if not toks or not vow:
                    continue
                end = toks[-1][2] - o
                va, vb = vow[-1][1] - o, vow[-1][2] - o
                if end + 0.25 > len(m) / fs:
                    continue
                lv = G._db(m[int(va * fs):int(vb * fs)])
                lt = G._db(m[int((end + 0.03) * fs):int((end + 0.25) * fs)])
                vals.append(round(lt - lv, 1))
    vals.sort()
    return {'takes': len(vals), 'median_db': vals[len(vals) // 2] if vals else None,
            'worst_db': vals[-1] if vals else None}


def singing(song, track_id: str = 'vocal', stem: Path | None = None, t_off: float = 0.0, span=None) -> dict:
    """The lead's moves (planned) and what its rendered curves did (see the module docstring). span: (from, to)
    song seconds to count (None: the whole part)."""
    import numpy as np
    from agentsound.lyrics import VOWELS
    t = song.tracks[track_id]
    plan = {'notes': 0, 'scoop': [], 'vibrato': [], 'vib_hz': [], 'fall': 0, 'doit': 0}
    onsets, vib_ext, vib_rate, soft, power, gains, nlev, settle = [], [], [], [], [], [], [], []
    dry = None
    sib, coda = [], []
    if stem is not None and stem.is_file():
        x, fs = G._read(stem)
        dry = _kw(x, fs)
        mono = x.mean(axis=1, keepdims=True)
        hi = G._sos(mono, [G._rbj('hp', 5000, fs), G._rbj('hp', 5000, fs), G._rbj('lp', 12000, fs)], fs)
        mid = G._sos(mono, [G._rbj('hp', 2000, fs), G._rbj('hp', 2000, fs), G._rbj('lp', 8000, fs),
                            G._rbj('lp', 8000, fs)], fs)
    for vo in t._singer['parts']:
        for r in getattr(vo, 'rendered', []) or []:
            ph = vo.phrases[r['phrase']]
            t0 = song.seconds(vo.notes[ph[0]].start) + vo.offset_ms / 1000.0
            if span is not None and not (span[0] - 0.01 <= t0 < span[1]):
                continue
            d = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))
            tl, sp = d['timeline'], d['spec']
            midi = np.array(tl['midi'])
            o = tl['offset_s']
            nf = len(midi)
            groups_v = tl['vowels']
            gi = 0
            for j, nt in enumerate(sp['notes']):
                plan['notes'] += 1
                pl = nt['plan']
                if 'scoop' in pl:
                    plan['scoop'].append(-float(pl['scoop']['cents']))
                if 'vibrato' in pl:
                    plan['vibrato'].append(float(pl['vibrato']['depth']))
                    plan['vib_hz'].append(float(pl['vibrato']['hz']))
                plan['fall'] += 'fall' in pl
                plan['doit'] += 'doit' in pl
                if nt['k'] == 'syllable':
                    st = groups_v[gi] if gi < len(groups_v) else nt['t']
                    gi += 1
                else:
                    st = nt['t']
                f0 = int(round((st - o) / FR))
                prev = sp['notes'][j - 1] if j else None
                if nt['d'] >= 0.2 and nt['k'] == 'syllable':
                    w = midi[max(0, f0):min(nf, f0 + int(0.15 / FR))]
                    # a scoop: under the note at a phrase opener / after a note at or above it (a note approached
                    # from below glides up through that range: its time to settle counts instead)
                    if len(w) and (prev is None or prev['m'] >= nt['m']):
                        onsets.append(float((w.min() - nt['m']) * 100.0))
                    # settle: from the vowel onset until the pitch stays within 25 ct of the note for 60 ms
                    end_f = min(nf, int(round((nt['t'] + nt['d'] - o) / FR)))
                    hold_n = max(1, int(0.06 / FR))
                    for f in range(max(0, f0 - int(0.05 / FR)), max(0, end_f - hold_n)):
                        if np.all(np.abs(midi[f:f + hold_n] - nt['m']) < 0.25):
                            settle.append(max(0.0, (f - f0) * FR * 1000.0))
                            break
                if nt['d'] >= 0.6:
                    a, b = f0 + int(0.3 / FR), min(nf, int(round((nt['t'] + nt['d'] - o) / FR)) - int(0.08 / FR))
                    if b - a >= int(0.25 / FR):
                        seg = midi[a:b] * 100.0
                        k = max(1, int(0.2 / FR) // 2)
                        sm = np.convolve(np.pad(seg, k, mode='edge'), np.ones(2 * k + 1) / (2 * k + 1), 'valid')
                        dev = seg - sm[:len(seg)]
                        vib_ext.append(float(np.percentile(np.abs(dev), 90)))
                        zc = np.sum(np.diff(np.sign(dev)) != 0)
                        vib_rate.append(zc / 2.0 / ((b - a) * FR))
                if dry is not None and nt['k'] == 'syllable':
                    a = t0 - t_off + nt['t'] + 0.04
                    nlev.append(_lvl(dry, fs, a, a + min(nt['d'], 0.35)))
            if dry is not None:
                toks = tl['tokens']
                for i, (p_, a, b) in enumerate(toks):
                    # sibilance: an s / z / sh / ch at 5-12 kHz vs its neighbouring vowel (full band), dB
                    if p_ in ('s', 'z', 'sh', 'zh', 'ch', 'jh') and b - a >= 0.03:
                        vw = [tk for tk in toks[max(0, i - 3):i + 4] if tk[0] in VOWELS]
                        if vw:
                            v = max(vw, key=lambda tk: tk[2] - tk[1])
                            ls = _lvl(hi, fs, t0 - t_off + a, t0 - t_off + b)
                            lv = _lvl(mono, fs, t0 - t_off + v[1], t0 - t_off + v[2])
                            if lv > -60:
                                sib.append(ls - lv)
                for c in tl.get('diction', []):
                    # a word-final consonant at 2-8 kHz vs the 120 ms of vowel before it (grit_ab's measure)
                    if c['cls'] == 'release':
                        continue
                    a, b = t0 - t_off + c['a'], t0 - t_off + c['b']
                    if b - a >= 0.02 and a > 0.13:
                        coda.append((round(_lvl(mid, fs, a, b) - _lvl(mid, fs, a - 0.12, a), 2), c['word'], c['ph']))
            mix = tl['mix']
            names = list(mix)
            ws = {k: (np.array(v) if isinstance(v, list) else np.full(nf, float(v))) for k, v in mix.items()}
            vf = np.zeros(nf, bool)
            for p_, a, b in tl['tokens']:
                if p_ in VOWELS:
                    vf[max(0, int((a - o) / FR)):min(nf, int((b - o) / FR) + 1)] = True
            tot = sum(ws.values())
            if vf.any():
                zero = np.zeros(nf)
                soft.append(float(np.mean(ws.get(vo.bank.mode('soft'), zero)[vf] / tot[vf])))
                power.append(float(np.mean(ws.get(vo.bank.mode('power'), zero)[vf] / tot[vf])))
            gains += list(np.array(tl['gain'])[vf])

    def pct(v, q):
        return round(float(np.percentile(v, q)), 1) if len(v) else None
    sc = [x for x in onsets if x < -25]
    nl = [x for x in nlev if x > -70]
    return {
        'notes': plan['notes'],
        'plan': {'scoops': len(plan['scoop']), 'scoop_ct_mean': round(float(np.mean(plan['scoop'])), 1)
                 if plan['scoop'] else 0.0, 'vibratos': len(plan['vibrato']),
                 'vib_ct_mean': round(float(np.mean(plan['vibrato'])), 1) if plan['vibrato'] else 0.0,
                 'vib_hz_mean': round(float(np.mean(plan['vib_hz'])), 2) if plan['vib_hz'] else 0.0,
                 'falls': plan['fall'], 'doits': plan['doit']},
        'scooped_onsets': len(sc), 'onsets': len(onsets), 'scooped_pct': round(100.0 * len(sc) / max(1, len(onsets))),
        'scoop_depth_ct_median': pct(sc, 50), 'scoop_depth_ct_p10': pct(sc, 10),
        'settle_ms_median': pct(settle, 50), 'settle_ms_p90': pct(settle, 90),
        'vibrato_ext_ct_median': pct(vib_ext, 50), 'vibrato_ext_ct_p90': pct(vib_ext, 90),
        'vibrato_rate_hz_median': pct(vib_rate, 50), 'held_notes': len(vib_ext),
        'mode_soft_share': round(float(np.mean(soft)), 3) if soft else None,
        'mode_power_share': round(float(np.mean(power)), 3) if power else None,
        'gain_lane_p10_p90_db': (pct(gains, 10), pct(gains, 90)),
        'note_level_p10_p90_db': round(pct(nl, 90) - pct(nl, 10), 1) if nl else None,
        'sibilance_db_median': pct(sib, 50), 'sibilance_db_p90': pct(sib, 90), 'sibilants': len(sib),
        'codas': coda,
    }


# ------------------------------------------------------------------------------------------------ delivery
# "die Jazz-Stimme ist immer noch sehr aufgeregt" / "sie klingt gerusht": what the takes deliver (brightness, energy
# contour, onset sharpness), the timing against the grid, and what the line asks for (register, density, leaps)

def _parts(song, track_id='vocal', span=None):
    """(Vocal, rendered phrase, its JSON, t0 song seconds) of a track's takes (span: (from, to) song seconds)."""
    t = song.tracks[track_id]
    for vo in t._singer['parts']:
        for r in getattr(vo, 'rendered', []) or []:
            ph = vo.phrases[r['phrase']]
            t0 = song.seconds(vo.notes[ph[0]].start) + vo.offset_ms / 1000.0
            if span is not None and not (span[0] - 0.01 <= t0 < span[1]):
                continue
            d = json.loads(Path(r['path']).with_suffix('.json').read_text(encoding='utf-8'))
            yield vo, r, d, t0, ph


def _med(v, q=50):
    import numpy as np
    return round(float(np.percentile(v, q)), 2) if len(v) else None


def take_character(song, track_id='vocal', span=None) -> dict:
    """The raw takes (before the chain and the make-up): loudness, brightness (spectral centroid of the vowels, tilt =
    2-5 kHz vs 0.2-1 kHz), the energy contour (the level wobble inside a vowel, 20 ms frames; the vowel-to-vowel level
    spread p10-p90) and the onset sharpness (the steepest 10 ms level rise around each syllable's start, dB)."""
    import numpy as np
    from agentsound.lyrics import VOWELS
    cent, tilt, wob, vlev, rise, chunks = [], [], [], [], [], []
    fs = 44100
    for vo, r, d, t0, ph in _parts(song, track_id, span):
        x, fs = G._read(Path(r['path']))
        m = x.mean(axis=1)
        chunks.append(m)
        o = d['timeline']['offset_s']
        toks = d['timeline']['tokens']
        for i, (p_, a, b) in enumerate(toks):
            if p_ not in VOWELS or b - a < 0.08:
                continue
            i0, i1 = int((a - o) * fs), int((b - o) * fs)
            seg = m[i0:i1]
            if len(seg) < 1024 or np.sqrt(np.mean(seg ** 2)) < 1e-4:
                continue
            spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
            fr = np.fft.rfftfreq(len(seg), 1 / fs)
            cent.append(float((spec * fr).sum() / (spec.sum() + 1e-12)))
            hi = (spec[(fr >= 2000) & (fr < 5000)] ** 2).sum()
            lo = (spec[(fr >= 200) & (fr < 1000)] ** 2).sum()
            tilt.append(float(10 * np.log10((hi + 1e-12) / (lo + 1e-12))))
            n20 = int(0.02 * fs)
            core = m[i0 + int(0.03 * fs):i1 - int(0.03 * fs)]
            fr_db = [10 * np.log10(np.mean(core[k:k + n20] ** 2) + 1e-12) for k in range(0, len(core) - n20, n20)]
            if len(fr_db) >= 3:
                wob.append(float(np.std(fr_db)))
            vlev.append(float(10 * np.log10(np.mean(seg ** 2) + 1e-12)))
        sp = d['spec']
        vows = d['timeline']['vowels']
        n10 = int(0.01 * fs)
        for g_i, V in enumerate(vows):
            a = int((V - o - 0.09) * fs)
            b = int((V - o + 0.06) * fs)
            if a < n10 or b > len(m):
                continue
            lv = [10 * np.log10(np.mean(m[k:k + n10] ** 2) + 1e-10) for k in range(a, b, n10)]
            rise.append(float(max(np.diff(lv)))) if len(lv) > 2 else None
    allx = np.concatenate(chunks)[:, None] if chunks else np.zeros((fs, 1))
    return {'takes_lufs': round(G.lufs(allx, fs), 2), 'centroid_hz': _med(cent), 'tilt_db': _med(tilt),
            'vowel_wobble_db': _med(wob), 'vowel_level_p10_p90_db': (round(_med(vlev, 90) - _med(vlev, 10), 2)
                                                                        if vlev else None),
            'onset_rise_db_per_10ms': _med(rise), 'onset_rise_p90': _med(rise, 90), 'vowels': len(cent)}


def timing(song, track_id='vocal', span=None) -> dict:
    """The micro-timing against the grid: every syllable's vowel onset vs its note (ms, + = behind the beat), the
    phrase openers', the consonants' lead before the vowel and the P-centre (vowel onset - half the onset consonants:
    roughly where a listener hears the syllable land), syllables per second inside the phrases, the rests between."""
    from agentsound.lyrics import VOWELS
    vow, first, lead, pc, rates, gaps, ioi = [], [], [], [], [], [], []
    prev_end = None
    for vo, r, d, t0, ph in sorted(_parts(song, track_id, span), key=lambda x: x[3]):
        tl, sp = d['timeline'], d['spec']
        syl = [n for n in sp['notes'] if n['k'] == 'syllable']
        toks = tl['tokens']
        for k, (n, V) in enumerate(zip(syl, tl['vowels'])):
            off = (V - n['t']) * 1000.0
            vow.append(off)
            if k == 0:
                first.append(off)
            j = next((i for i, tk in enumerate(toks) if tk[0] in VOWELS and abs(tk[1] - V) < 0.02), None)
            c0 = V
            if j is not None:
                i = j - 1
                while i >= 0 and toks[i][0] not in VOWELS and toks[i][0] not in ('SP', 'AP') and \
                        V - toks[i][1] < 0.25 and i >= j - max(1, len(n['on'])):
                    c0 = toks[i][1]
                    i -= 1
            lead.append((V - c0) * 1000.0)
            pc.append(off - (V - c0) * 500.0)
        ns = sp['notes']
        ioi += [(b['t'] - a['t']) * 1000.0 for a, b in zip(syl, syl[1:])]
        dur = ns[-1]['t'] + ns[-1]['d'] - ns[0]['t']
        if dur > 0.5:
            rates.append(len(syl) / dur)
        if prev_end is not None:
            gaps.append(t0 + ns[0]['t'] - prev_end)
        prev_end = t0 + ns[-1]['t'] + ns[-1]['d']
    return {'vowel_ms_median': _med(vow), 'vowel_ms_p10': _med(vow, 10), 'vowel_ms_p90': _med(vow, 90),
            'vowel_early_pct': round(100.0 * sum(v < 0 for v in vow) / max(1, len(vow))),
            'phrase_start_vowel_ms': _med(first), 'consonant_lead_ms': _med(lead), 'p_centre_ms': _med(pc),
            'syllables_per_s': _med(rates), 'syllable_ioi_ms_median': _med(ioi),
            'ioi_8th_or_less_pct': round(100.0 * sum(x <= 260 for x in ioi) / max(1, len(ioi))), 'rest_between_phrases_s': _med(gaps), 'syllables': len(vow)}


def line_shape(song, track_id='vocal', span=None) -> dict:
    """What the line asks for: the share of sung time at / above D5 (74), notes at / above G5 (79), the leaps of a
    4th+ inside phrases, the mean interval, the velocities' p10-p90, and the pitch wobble on short notes (0.3-0.9 s:
    a vibrato there sounds nervous)."""
    import numpy as np
    hi_t = tot = 0.0
    g5 = 0
    iv, vels, short = [], [], []
    for vo, r, d, t0, ph in _parts(song, track_id, span):
        sp, tl = d['spec'], d['timeline']
        ns = sp['notes']
        midi = np.array(tl['midi'])
        o = tl['offset_s']
        for j, n in enumerate(ns):
            tot += n['d']
            hi_t += n['d'] if n['m'] >= 74 else 0.0
            g5 += n['m'] >= 79
            vels.append(n['v'])
            if j:
                iv.append(abs(n['m'] - ns[j - 1]['m']))
            if 0.3 <= n['d'] < 0.9:
                a, b = int((n['t'] + 0.12 - o) / FR), int((n['t'] + n['d'] - 0.05 - o) / FR)
                if b - a >= 8:
                    seg = (midi[a:b] - n['m']) * 100.0
                    short.append(float(np.percentile(np.abs(seg - np.median(seg)), 90)))
    return {'time_at_or_above_D5_pct': round(100.0 * hi_t / max(tot, 1e-9), 1), 'notes_at_or_above_G5': g5,
            'leaps_4th_plus': sum(x >= 5 for x in iv), 'intervals': len(iv),
            'mean_interval_st': round(float(np.mean(iv)), 2) if iv else None,
            'vel_p10_p90': (_med(vels, 10), _med(vels, 90)), 'short_note_wobble_ct': _med(short)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('song')
    ap.add_argument('--from-beat', type=float)
    ap.add_argument('--to-beat', type=float)
    ap.add_argument('--json')
    ap.add_argument('--out', help='render folder (default <song>/out/wetness)')
    ap.add_argument('--singing', action='store_true', help='only the singing numbers (no render)')
    a = ap.parse_args(argv)
    sd = Path(a.song).resolve()
    song = load(sd / 'song.py')
    out = Path(a.out) if a.out else sd / 'out' / 'wetness'
    if a.singing:
        song.compile()
        res = {}
    else:
        res = wetness(song, out, a.from_beat, a.to_beat)
        res['take_tail'] = take_tails(song)
    span = None
    if a.from_beat is not None:
        span = (song.seconds(a.from_beat), song.seconds(a.to_beat) if a.to_beat is not None else 1e9)
    res['singing'] = singing(song, stem=out / 'stems' / 'vocal.wav',
                             t_off=song.seconds(a.from_beat) if a.from_beat is not None else 0.0, span=span)
    txt = json.dumps({k: v for k, v in res.items() if k != 'tails'}, indent=1)
    print(txt)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
