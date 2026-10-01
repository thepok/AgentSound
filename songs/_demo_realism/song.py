"""Realism demo: 'Played, not triggered' - the same material twice: played (legato transitions, live dynamics,
keyswitched articulations, portamento, delayed vibrato, expression shapes) and triggered the old way (every note
re-attacked from the velocity layer its velocity picks, one articulation, dynamics frozen at the note-on). Build:
    python -m agentsound build songs/_demo_realism

Sections (80 BPM, D minor, 40 bars, ~2:00), each pair loudness-matched:
  violin      8   sampled/solo_violin (VSCO 2 sustain-vibrato, spiccato, pizzicato, tremolo in one instrument:
                  inst.sfz_multi): a legato line whose held notes crescendo, swell and fade (layers='dynamics': the p and
                  f recordings crossfade while a note sounds), a spiccato passage in the same track (keyswitches inserted
                  at compile), a portamento into the opening leap A4-D5, delayed vibrato, a player's timing
  violin_old  8   the same notes triggered: poly, velocity layers, the sustain samples for the short notes too
  sax         8   sampled/tenor_sax (MTG tenor, mono='legato'): a ballad phrase with legato transitions, scoops into
                  the phrase entries, a portamento into the big leap, swells and a delayed vibrato on the long notes
  sax_old     8   the same notes triggered: every note re-attacked, straight tone, flat dynamics
  swell       4   string section chord (sampled/violin_section, viola_section, cello_section) p -> f -> p over four
                  bars: one set of notes, the velocity layers crossfaded live by 'dynamics' and the tone opening
  swell_old   4   the same chord at one velocity, swelled with the expression (volume) control only
See docs/COMPOSE_API.md "Realistic performance".

Measured (dry stems, each pair at -20.0 LUFS; 0 clicks):
  violin  the previous pitch 150-300 ms into the next note: -35 dB played (handed over in 70 ms) vs -16 dB triggered
          (the old note's release rings under the new attack); level around the 11 legato transitions (160 ms RMS):
          largest deviation median 1.2 / max 2.1 dB vs 1.8 / 3.4 dB; the spiccato bars fall -23 dB within each 8th
          vs +2 dB with the sustain samples (a legato smear)
  sax     24 transitions: level deviation median 0.6 dB vs 1.6 dB; previous pitch -32 vs -28 dB
  swell   brightness (share above 2.5 kHz) -15.5 dB at pp -> -12.0 dB at ff (the layers and the tone open with the
          dynamics) vs -11.7 -> -12.0 dB triggered (only the volume moves); level range 13.7 vs 16.2 dB
"""
from agentsound import *
from agentsound import articulation as art
from agentsound import jazz
from agentsound.patches import sampled

ANALYSIS = {'profile': 'classical'}

VSCO = 'samples/vsco2-ce/'

# Track gains (dB): each pair (played / triggered) loudness-matched, the whole piece around -20 LUFS
GAIN = {'violin': 6.9, 'violin_old': 1.2, 'sax': 5.3, 'sax_old': 1.4, 'swell': -2.4, 'swell_old': -2.9}

# The violin line, D minor, one list per bar: (beat, beats, pitch, velocity)
VIOLIN = [
    [(0, 2, 'A4', 70), (2, 1, 'D5', 78), (3, 1, 'E5', 82)],
    [(0, 3, 'F5', 88), (3, 1, 'E5', 80)],
    [(0, 2, 'D5', 78), (2, 1, 'C#5', 76), (3, 1, 'D5', 80)],
    [(0, 4, 'E5', 84)],
    [(0, 0.5, 'A5', 96), (0.5, 0.5, 'G5', 88), (1, 0.5, 'F5', 90), (1.5, 0.5, 'E5', 86),
     (2, 0.5, 'D5', 92), (2.5, 0.5, 'E5', 86), (3, 0.5, 'F5', 90), (3.5, 0.5, 'G5', 88)],
    [(0, 0.5, 'A5', 100), (0.5, 0.5, 'F5', 88), (1, 0.5, 'D5', 90), (1.5, 0.5, 'F5', 88), (2, 1, 'A5', 104)],
    [(0, 2, 'D6', 96), (2, 1, 'C6', 86), (3, 1, 'Bb5', 84)],
    [(0, 4, 'A5', 80)],
]
# expression per note (index in time order; the others flat): a crescendo into the line, swells on the long notes,
# a sforzando on the high D, a long diminuendo at the end
VIOLIN_SHAPES = {0: 'cresc', 3: 'swell', 8: 'swell', 22: 'sfz', 25: 'dim'}

# Tenor sax ballad phrase, concert pitch (bars of 4 beats)
SAX = [
    [(0.5, 0.5, 'A3', 72), (1, 0.5, 'D4', 80), (1.5, 2.5, 'F4', 88)],
    [(0, 0.5, 'E4', 78), (0.5, 0.5, 'D4', 76), (1, 1, 'C#4', 80), (2, 2, 'A3', 74)],
    [(0.5, 0.5, 'Bb3', 74), (1, 0.5, 'D4', 80), (1.5, 0.5, 'G4', 86), (2, 2, 'Bb4', 92)],
    [(0, 1, 'A4', 86), (1, 0.5, 'G4', 80), (1.5, 0.5, 'F4', 78), (2, 2, 'E4', 82)],
    [(0.5, 0.5, 'F4', 80), (1, 0.5, 'G4', 84), (1.5, 2.5, 'A4', 94)],
    [(0, 0.5, 'C5', 96), (0.5, 0.5, 'Bb4', 90), (1, 1, 'A4', 86), (2, 1, 'G4', 82), (3, 1, 'E4', 80)],
    [(0, 3, 'F4', 84), (3, 0.5, 'E4', 76), (3.5, 0.5, 'C#4', 74)],
    [(0, 4, 'D4', 78)],
]
# The chord: Dm(add9) spread over the section (violins take the top, violas the middle, celli the bass)
CHORD = {'violins': ['A4', 'E5', 'F5'], 'violas': ['D4', 'A4'], 'celli': ['D2', 'D3']}


def bars(rows, length=None) -> Clip:
    notes = [(i * 4 + t, d, p, v) for i, bar in enumerate(rows) for t, d, p, v in bar]
    return Clip(notes, length=length or len(rows) * 4)


def old_way(path: str, level: float, **kw):
    """The same samples triggered the old way: velocity picks the layer, every note re-attacks, one articulation."""
    return inst.sfz(path, level=level, keyswitches='static', dyn_cc=None, **kw)


def build() -> Song:
    s = Song('Played, not triggered', tempo=80, key='D minor', seed=11)
    violin = s.section('violin', bars=8)
    violin_old = s.section('violin_old', bars=8)
    sax = s.section('sax', bars=8)
    sax_old = s.section('sax_old', bars=8)
    swell = s.section('swell', bars=4)
    swell_old = s.section('swell_old', bars=4)
    hall = s.hall()
    s.master.add(fx.limiter())

    # ------------------------------------------------------------------ (a) solo violin
    line = bars(VIOLIN)
    vln = s.track('violin', 'sampled/solo_violin', pan=-0.1, gain_db=GAIN['violin'])
    played = line.articulate('spiccato', span=(16, 23))                      # bars 5-6: spiccato, same track
    played = art.legato(played, overlap=0.04)                                # tie the phrases -> legato transitions
    played = played.glide(160, span=(2, 3))                                  # portamento into the leap A4-D5
    played = art.humanize_starts(played, s.tempo, ms=7, seed=3)
    vln.play(played, violin)
    art.expression(vln, played, violin, VIOLIN_SHAPES, lo=0.25)
    art.vibrato(vln, played, violin, depth=22, rate=5.4, delay=0.35, grow=0.7, seed=5)

    vln_old = s.track('violin_old', old_way(VSCO + 'SViolinVib.sfz', sampled.LEVELS['solo_violin']), pan=-0.1,
                      fx=[fx.eq({'hp.freq': 180, 'hp.slope': 24})], sends={hall: -10}, gain_db=GAIN['violin_old'])
    vln_old.play(line, violin_old)

    # ------------------------------------------------------------------ (b) tenor sax ballad
    phrase = bars(SAX)
    sx = s.track('sax', 'sampled/tenor_sax', pan=0.1, gain_db=GAIN['sax'])
    sp = art.legato(phrase, overlap=0.03)
    sp = sp.glide(90, where=art.leaps(7))                                    # portamento into the leap to Bb4
    sp = art.humanize_starts(sp, s.tempo, ms=9, late_ms=18, seed=8)
    sx.play(sp, sax)
    art.expression(sx, sp, sax, 'auto', lo=0.35, long=1.5)
    art.vibrato(sx, sp, sax, depth=16, rate=5.0, delay=0.4, grow=0.6, seed=2)
    starts = [n.start for n in sp]
    bend = [(sax.start, 0.0)]
    for b in (starts[2], starts[9], starts[16]):                            # scoops (the sampler's pitch bend)
        bend += jazz.scoop(sax.start + b, cents=-70, length=0.2)
    sx.automate('instrument.pitchbend', bend)

    sx_old = s.track('sax_old', old_way('samples/mtg-solo-sax/MTG Solo Saxophones/MTG Tenor Sax.sfz', 11.8),
                     pan=0.1, fx=[fx.eq({'hp.freq': 70, 'hp.slope': 24})], sends={hall: -12}, gain_db=GAIN['sax_old'])
    sx_old.play(phrase, sax_old)

    # ------------------------------------------------------------------ (c) string section chord swell
    L = swell.length
    files = {'violins': 'ViolinEnsSusVib.sfz', 'violas': 'ViolaEnsSusVib.sfz', 'celli': 'CelloEnsSusVib.sfz'}
    patch = {'violins': 'violin_section', 'violas': 'viola_section', 'celli': 'cello_section'}
    pans = {'violins': -0.35, 'violas': 0.15, 'celli': 0.35}
    for name, pitches in CHORD.items():
        chord = Clip([(0, L - 0.25, p, 90) for p in pitches], length=L)
        t = s.track(name, f"sampled/{patch[name]}", pan=pans[name], gain_db=GAIN['swell'])
        t.play(chord, swell)
        t.automate('instrument.dynamics', [(swell.start, 0.08), (swell.start + L * 0.55, 1.0, 'smooth'),
                                           (swell.end - 0.5, 0.1, 'smooth')])
        o = s.track(name + '_old', old_way(VSCO + files[name], sampled.LEVELS[patch[name]]), pan=pans[name],
                    sends={hall: -8}, gain_db=GAIN['swell_old'])
        o.play(chord, swell_old)
        o.automate('instrument.expression', [(swell_old.start, 0.35), (swell_old.start + L * 0.55, 1.0, 'smooth'),
                                             (swell_old.end - 0.5, 0.35, 'smooth')])
    return s
