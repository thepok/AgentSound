"""Neural choir prototype, stage 2: a choir that sings TEXT - every SATB part sung N times by the DiffSinger singer
(agentsound.singer), the layers being the singer's own re-sung doubles (singer.double: another take with its own
timing, vibrato, drift and formant), consonants kept tight (each layer's lag <= LAG_MS, the style's jitter small),
summed per part on a bus with light ensemble processing and one shared hall.

    parts = textchoir.homophonic({'S': s_notes, 'A': ..., 'T': ..., 'B': ...}, WORDS)   # per-part lyrics strings
    voices = textchoir.sing_section(s, 'S', clip, lyrics, at=sec, layers=5, hall=hall)

Shared wrappers, not forks: the lyrics go through singer.sing (lyrics.align: syllables -> notes, '-' = melisma), the
layers are singer.double() takes; the hybrid body is the stage-1 pack on orch.Choir (syllable gate).
"""
from __future__ import annotations

import random

from agentsound import singer, fx

PART_VOICE = {
    # bank, transpose, formant (semitones of the singer's formant param; MEASURED: + = darker on these banks),
    # pan centre, per-layer formant spread (+-st)
    'S': dict(voice='hanami', formant=-0.4, pan=-0.7, spread=1.0),
    'A': dict(voice='hanami', formant=2.6, pan=0.7, spread=1.0),
    'T': dict(voice='tiger', formant=0.0, pan=-0.45, spread=0.35),
    'B': dict(voice='tiger', formant=0.6, pan=0.45, spread=0.3),
}
LAG_MS = (0.0, 18.0)
"""Each layer's lag range: with the style's jitter_ms (4) the consonant onsets of a part spread <= ~25 ms."""
CHOIR_STYLE = dict(late_ms=0.0, jitter_ms=4.0, vib_ct=14.0, peak_vib_ct=18.0, scoop_ct=28.0, fall=0.0, doit=0.0,
                   overshoot_ct=6.0, breath_db=-10.0, accent=0.06)
"""singer.sing overrides for a choir singer: on the beat, tight, a narrow vibrato, small scoops, no falls / doits,
quiet breaths (5 breathing layers would be a gust)."""


def homophonic(parts: dict, words: list) -> dict:
    """Per-part lyrics strings for a homophonic setting: `words` = [(word, n_syllables)] with each syllable's onset
    shared by every part; a part's note that starts on no new syllable onset (a melisma) sings '-'. parts: {name:
    [(start, dur, pitch, vel), ...]} sorted. Syllable onsets are taken from the part with the FEWEST notes (the
    plain rhythm); a part with more notes on the same syllable gets melismas (only on a word's last syllable:
    lyrics.align's rule)."""
    plain = min(parts.values(), key=len)
    onsets = [round(n[0], 4) for n in plain]
    nsyl = sum(k for _, k in words)
    if len(onsets) != nsyl:
        raise ValueError(f"homophonic: {nsyl} syllables but the plainest part has {len(onsets)} notes")
    # syllable index -> (word index, syllable in word)
    syl = []
    for wi, (w, k) in enumerate(words):
        syl += [(wi, j) for j in range(k)]
    out = {}
    for name, notes in parts.items():
        toks, si = [], -1
        for n in notes:
            st = round(n[0], 4)
            if si + 1 < len(onsets) and abs(st - onsets[si + 1]) < 1e-3:
                si += 1
                wi, j = syl[si]
                if j == 0:                       # the word (align gives a k-syllable word its k notes)
                    toks.append(words[wi][0])
            else:
                if si < 0:
                    raise ValueError(f"homophonic: part {name} starts before the first syllable")
                wi, j = syl[si]
                if j != words[wi][1] - 1:
                    raise ValueError(f"homophonic: part {name} has a melisma inside the word {words[wi][0]!r}")
                toks.append('-')
        out[name] = ' '.join(toks)
    return out


def sing_section(s, part: str, line, lyrics: str, *, at, layers: int = 5, hall=None, seed: int = 11,
                 gain_db: float = 0.0, transpose: int = 0, bus_id: str | None = None, memory=None,
                 track_prefix: str = 'choir') -> dict:
    """One choir part sung by `layers` virtual singers: layer 0 = singer.sing (the part), layers 1.. =
    singer.double of it (re-sung takes: own timing / vibrato / drift) with an own formant offset, a small lag
    (LAG_MS), its own pan inside the part's place; summed on a bus '<prefix>_<part>' (light ensemble eq + glue
    compression, one hall send). -> {'lead': Vocal, 'layers': [Vocal], 'bus': Bus}"""
    V = PART_VOICE[part]
    rng = random.Random(f'{part}-{seed}')
    bid = bus_id or f'{track_prefix}_{part.lower()}'
    bus = s.buses.get(bid) or s.bus(bid, fx=[
        fx.eq({'hp.freq': 90 if part in 'TB' else 160, 'peak1.freq': 420, 'peak1.gain': -2.5, 'peak1.q': 0.8,
               'peak2.freq': 3200, 'peak2.gain': -1.5, 'peak2.q': 0.7, 'high.freq': 9000, 'high.gain': -2.0}),
        fx.compressor(threshold=-22, ratio=1.8, knee=10, attack=25, release=300, detector='rms')],
        gain_db=gain_db)
    if hall is not None:
        bus.send(hall, -8)
    sp = V['spread']
    fms = [V['formant'] + (-sp + 2 * sp * i / (layers - 1) if layers > 1 else 0.0) for i in range(layers)]
    rng.shuffle(fms)
    pans = [max(-1.0, min(1.0, V['pan'] + (i - (layers - 1) / 2) * 0.25)) for i in range(layers)]
    rng.shuffle(pans)
    lead = singer.sing(s, line, lyrics, at=at, voice=V['voice'], style='pop', seed=seed, transpose=transpose,
                       formant=round(fms[0], 3), pan=round(pans[0], 3), track_id=f'{track_prefix}_{part.lower()}1',
                       memory=memory, back_phrase=False, ornament=False, messa_di_voce=False, emphasis=False,
                       mic_pull=False, vel=False, **CHOIR_STYLE)
    lead.track.to(bus)
    out = [lead]
    for i in range(1, layers):
        d = singer.double(lead, pan=round(pans[i], 3), offset_ms=round(rng.uniform(*LAG_MS), 1), gain_db=0.0,
                          formant=round(fms[i], 3), depth=1.0, track_id=f'{track_prefix}_{part.lower()}_dbl{i + 1}')
        d.track.to(bus)
        out.append(d)
    return {'lead': lead, 'layers': out, 'bus': bus}
