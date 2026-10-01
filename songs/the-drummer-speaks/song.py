"""The Drummer Speaks - classic hard rock with an organ, built around a 40-bar drum solo (116 BPM, E minor, straight).

The showcase of the drummer's solo layer (docs/COMPOSE_API.md "The drum solo"): a two-bar unison riff whose rhythm
(3 + 3 + 4 + 2 16ths) is the solo's motif; the band frames it (cymbal swell, the drummer alone on the toms, the riff,
the head on the hero guitar, a chorus, the riff with band hits) and drops out; the drummer keeps time while the band's
chord rings away, then soloist.solo (the instrument-agnostic solo wrapper) plays the drummer's vocabulary along the
classic arc on the riff's rhythm: the motif stated softly on the snare, answered (the hi-hat as a voice, snare / tom
call and response, a tom melody), developed (rudiments around the kit, flams down the toms), a burst (a single-stroke
speed burst, hand-hand-foot triplets, double bass), the climax (the 80s gated tom break, a press roll from a whisper),
a quiet resolution - and the finish (unison hits on the riff's accents, a run around the kit) cues the band back in;
the head returns, the riff ends it, the final hit choked. Plan: BRIEF.md, ARRANGEMENT.md, SOUND.md, MIX.md, MASTER.md,
AR.md.
"""
from agentsound import *
from agentsound import bands, bassist, drummer, mastering, patches, soloist
from agentsound.humanize import touch
from agentsound.patches import hero_guitar as hg

ANALYSIS = {'profile': 'rock'}
METADATA = {'title': 'The Drummer Speaks', 'artist': 'AgentSound', 'album': 'Players', 'genre': 'Rock', 'year': 2026}
COVER = {'style': 'rock'}

# the mix engineer's moves (MIX.md): the drums and bass up to the rock window in the hooks, the drums ridden up in the
# solo (they are the whole band there: the climax lands near the band's level), the bass ducked deeper under the kick,
# less sub on the kit, the lead's presence peak tamed
MIX = {
    'trim': {'drums': 2.0, 'bass': 1.5},
    'ride': {'lead': {'B2': -1.5}, 'drums': {'solo': 3.5}},
    'duck': [{'targets': ['bass'], 'key': 'drums', 'pitches': 'kick', 'depth': 4, 'attack': 2, 'release': 110}],
    'eq': {'drums': [{'freq': 42, 'gain': -2.5, 'q': 0.8}], 'lead': [{'freq': 3300, 'gain': -2.0, 'q': 1.0}]},
}

BPM = 116
HANDS = 'master'                        # one drummer through the song: an even weak hand, consistent heights, fast
RIFF_CELL = 'x..x..x...x.x...'          # the riff's rhythm = the drum solo's motif

# the drum solo (40 bars): the drummer keeps time while the band's chord rings away (4 bars, by hand), then
# soloist.solo plays the body (34 bars, the 'classic' arc: statement -> answer -> develop -> burst -> climax ->
# resolve) from the drummer's vocabulary on the riff's rhythm as the motif, then the finish cues the band back in
# (2 bars, by hand: unison hits on the motif's accents and a run around the kit into B2's 1)
SOLO_IN = ('time', 4, 0.6, {'crash': True})
SOLO_BODY = 34
SOLO_OUT = ('finish', 2, 1.0, {'motif': True})
SOLO_ARC = 'classic'
SOLO_SEED = 11


def riff_notes(octave_shift: int = 0, vel: float = 100) -> Clip:
    """The two-bar riff (bass register: E1 = the low string); +12 for the guitars' power-chord roots."""
    r = [(0.0, 0.5, 'E1'), (0.75, 0.25, 'E1'), (1.5, 0.75, 'G1'), (2.5, 0.5, 'A1'), (3.0, 0.25, 'G1'),
         (3.25, 0.5, 'E1'),
         (4.0, 0.5, 'D2'), (4.75, 0.5, 'B1'), (5.5, 0.5, 'A1'), (6.5, 0.25, 'E1'), (7.0, 0.25, 'G1'),
         (7.25, 0.25, 'A#1'), (7.5, 0.5, 'B1')]
    # the riff's accents (the 1s, the long notes) dig in, the short pickups are lighter
    acc = {0.0: 1.0, 1.5: 0.9, 2.5: 0.86, 4.0: 1.0, 5.5: 0.88, 7.5: 0.95}
    return Clip([(t, d, note(n) + octave_shift, min(127, vel * acc.get(t, 0.7))) for t, d, n in r], length=8)


def riff_drums(bars: int = 2, *, stop: bool = False) -> list[str]:
    """The drummer doubling the riff: snare + kick on its accents (crash on the 1s), the hat 8ths between."""
    toks = []
    onsets = {0, 3, 6, 10, 12, 13}
    onsets2 = {0, 3, 6, 10, 12, 13, 14}
    for b in range(bars):
        on = onsets if b % 2 == 0 else onsets2
        for st in range(16):
            parts = []
            if st in on:
                if st == 0:
                    parts.append('>R@crash' if b % 2 == 0 else '>R@china')
                    parts.append('K')
                else:
                    parts.append('>L+K' if st in (6, 12) else 'L+K' if st != 13 else 'l')
            elif st % 2 == 0:
                parts.append('R@hat')
            toks.append('+'.join(parts) or '-')
    if stop:                                    # the last beat: a flam into the solo's 1, then nothing
        toks[-4:] = ['f>L@tom1+K', 'R@tom2', 'L@floor', 'R@floor']
    return toks


def lead_line(s: Song, spec: str, lo: float, hi: float) -> Clip:
    c = s.motif(spec).clip(octave=4)
    c = touch(c, lo, hi)                      # phrase arcs: the goal note sings, passing notes lighter
    return c


def build() -> Song:
    s = Song('The Drummer Speaks', tempo=BPM, key='E minor', seed=11)
    intro = s.section('intro', bars=4)
    a = s.section('A', bars=16)
    b_ = s.section('B', bars=8)
    riff = s.section('riff', bars=4)
    solo = s.section('solo', bars=SOLO_IN[1] + SOLO_BODY + SOLO_OUT[1])
    b2 = s.section('B2', bars=8)
    a3 = s.section('A3', bars=8)
    end = s.section('end', bars=4)

    kit_sound = patches.get('sampled/big_rusty_kit').but(level=1.0, restrike=6.0)
    b = bands.rock_band(s, without=('lead',), sounds={'drums': kit_sound})
    kit = b.drums
    drum_bus = kit.output
    # a peak catcher at the end of the drum bus: the hardest crash / kick accents (+2 dBFS on the bus) would otherwise
    # drive the master limiter and flatten the whole song; only the top transients above -9 dBFS are touched
    s.node(drum_bus).add_fx(fx.compressor(threshold=-9, ratio=8, attack=0.3, release=60, knee=3, detector='peak'))
    mallets = s.track('mallets', 'sampled/big_rusty_mallets', gain_db=-4, sends={'room': -8})
    mallets.to(drum_bus)
    s.hall()
    gated = s.bus('gated', 'bus/gated')
    kit.send(gated, -60)
    lead = hero(s.track('lead', 'layered/hero_guitar', sends={'echo': -12}), bed=[b.keys], competitors=[b.gtr_l, b.gtr_r], genre='rock',
                sections=[a, b_, b2, a3])

    # ------------------------------------------------------------------ the riff (bass + two guitars in unison)
    rb = riff_notes()
    rg = riff_notes(12, vel=112).chordify('power').articulate('palm', where=lambda n: n.dur < 0.5)
    riff_spans = [(intro.bar(2), 1), (a.bar(0), 2), (a.bar(8), 2), (riff.start, 2), (a3.bar(0), 2), (end.start, 1)]
    for at, times in riff_spans:
        b.bass.play(rb.articulate('staccato', where=lambda n: n.dur < 0.5), at, times=times)
        for gtr, ms in ((b.gtr_l, 9), (b.gtr_r, 12)):
            gtr.play(rg.strum(ms=ms, bpm=BPM, direction='alternate'), at, times=times)

    # ------------------------------------------------------------------ harmony outside the riff
    prog_a = s.prog('C D Em B7')                  # A bars 5-8 (and 13-16)
    prog_b = s.prog('C D Em Em C D B7 B7')
    for at in (a.bar(4), a.bar(12), a3.bar(4)):
        bassist.arrange(prog_a, bpm=BPM, key=s.key, style='rock', part='verse', kick='x.....x.x.......',
                        seed=3).place(b.bass, at)
    for sec, part in ((b_, 'chorus'), (b2, 'chorus')):
        bassist.arrange(prog_b, bpm=BPM, key=s.key, style='rock', part=part, kick='x.....x.x.......',
                        seed=5 if sec is b_ else 6).place(b.bass, sec)

    def open_chords(roots, rhythm, vel):
        notes = []
        for bar, r in enumerate(roots):
            i = 0
            while i < len(rhythm):
                if rhythm[i] == 'x':
                    j = i + 1
                    while j < len(rhythm) and rhythm[j] == '_':
                        j += 1
                    notes.append((bar * 4 + i * 0.5, (j - i) * 0.5 - 0.06, note(r), vel))
                    i = j
                else:
                    i += 1
        return Clip(notes, length=len(roots) * 4).chordify('power')

    turn = open_chords(['C3', 'D3', 'E2', 'B2'], 'x___x_x_', 96)
    chorus = open_chords(['C3', 'D3', 'E2', 'E2', 'C3', 'D3', 'B2', 'B2'], 'x___x_x_', 106)
    for gtr, ms in ((b.gtr_l, 11), (b.gtr_r, 14)):
        for at in (a.bar(4), a.bar(12), a3.bar(4)):
            gtr.play(turn.strum(ms=ms, bpm=BPM, direction='alternate'), at)
        gtr.play(chorus.strum(ms=ms, bpm=BPM, direction='alternate'), b_)
        gtr.play(chorus.strum(ms=ms + 2, bpm=BPM, direction='alternate'), b2)
        gtr.play(open_chords(['E2'], 'x_______', 112).strum(ms=ms + 14, bpm=BPM), solo.start)      # rings away
        gtr.play(open_chords(['B2'], 'x_______', 108).strum(ms=ms + 6, bpm=BPM), end.bar(2))
        gtr.play(open_chords(['E2'], 'x_', 116).strum(ms=ms + 4, bpm=BPM), end.bar(3))
        # loud-quiet: the riff under the head sits back, the choruses open up
        gtr.automate('gainDb', per_section({intro: -2, a: -6, b_: -1, riff: 0, solo: -2, b2: 0, a3: -4, end: 0},
                                           glide=0.5))

    # the bass: the solo's first chord rings, the ending
    b.bass.note('E1', solo.start, 7.5, 108)
    b.bass.note('B1', end.bar(2), 3.8, 104)
    b.bass.note('E1', end.bar(3), 0.9, 116)

    # ------------------------------------------------------------------ organ
    org = b.keys
    org.play(s.prog('Em7').block(voicing='spread', register=('E3', 'E5'), vel=62).stretch(2), intro.bar(1))
    for at in (a.bar(0), a.bar(8)):
        org.play(s.prog('Em7 Em7').block(voicing='spread', register=('E3', 'E5'), vel=68), at, times=2)
    for at in (a.bar(4), a.bar(12), a3.bar(4)):
        org.play(prog_a.block(voicing='drop2', register=('G3', 'G5'), rhythm='x...x.x.', vel=80), at)
    org.play(prog_b.block(voicing='drop2', register=('G3', 'G5'), rhythm='x..x..x.', vel=88), b_)
    org.play(prog_b.block(voicing='drop2', register=('G3', 'G5'), rhythm='x..x..x.', vel=96), b2)
    org.play(s.prog('Em7 Em7').block(voicing='spread', register=('E3', 'E5'), vel=74), a3.bar(0), times=2)
    org.play(s.prog('Em').block(register=('E3', 'B4'), vel=84).stretch(2), solo.start)
    org.automate('gainDb', ramp(solo.start, solo.bar(2), 0, -24), hold(solo.bar(2), b2.start, -60),
                 hold(b2.start, end.end, 0))
    org.play(s.prog('B7').block(register=('F#3', 'A4'), vel=90), end.bar(2))
    org.play(s.prog('Em').block(register=('E3', 'B4'), vel=100).slice(0, 1), end.bar(3))
    # the swell pedal (an organ has no touch: its dynamics are the expression pedal): pads breathe in and out over
    # two bars, the pushes lean into the changes, the chorus opens, the solo's chord dies away with the pedal
    swell = []
    for at in (intro.bar(1), a.bar(0), a.bar(2), a.bar(8), a.bar(10), a3.bar(0), a3.bar(2)):
        t0 = s._at(at)
        swell += [(t0, 0.62), (t0 + 3.0, 0.92, 'smooth'), (t0 + 6.5, 0.74, 'smooth')]
    for at in (a.bar(4), a.bar(12), a3.bar(4)):
        t0 = s._at(at)
        swell += [(t0, 0.78), (t0 + 6.0, 0.9, 'smooth'), (t0 + 11.0, 0.8, 'smooth'), (t0 + 15.5, 0.95, 'smooth')]
    for sec in (b_, b2):
        t0 = s._at(sec)
        swell += [(t0, 0.86), (t0 + 10.0, 1.0, 'smooth'), (t0 + 16.0, 0.88, 'smooth'), (t0 + 24.0, 1.0, 'smooth'),
                  (t0 + 31.5, 0.92, 'smooth')]
    t0 = s._at(solo)
    swell += [(t0, 0.95), (t0 + 7.5, 0.35, 'smooth')]
    t0 = s._at(end)
    swell += [(t0, 0.9), (t0 + 12.0, 1.0, 'smooth')]
    org.automate('instrument.expression', sorted(swell, key=lambda p: p[0]))
    org.automate('fx.tremolo.rate', hold(intro.start, a.start, 0.8), hold(a.start, b_.start, 0.9),
                 ramp(b_.start, b_.bar(1), 0.9, 6.4), hold(b_.bar(1), solo.start, 6.4),
                 ramp(solo.start, solo.bar(2), 6.4, 0.6), hold(solo.bar(2), b2.start, 0.6),
                 hold(b2.start, end.end, 6.4))

    # ------------------------------------------------------------------ the head (hero guitar)
    p1 = '5:1.5 4:0.5 3:1 5:1 | 8:2 7:1 5:1 | 6:1.5 5:0.5 4:1 3:1 | 5:3 r:1'
    p2 = '6:1.5 5:0.5 6:1 8:1 | 7:2 5:1 7:1 | 8:1 10:1 9:1 8:1 | 5:3 r:1'
    p2b = '6:1.5 5:0.5 6:1 8:1 | 9:2 8:1 7:1 | 8:1 10:1 12:1 10:1 | 9:3 r:1'
    chorus_line = ('10:2 9:1 8:1 | 9:2 8:1 7:1 | 8:1.5 7:0.5 5:2 | r:2 5:0.5 7:0.5 8:1 | 10:2 9:1 8:1 | '
                   '9:2 10:1 11:1 | 12:4 | 11:2 r:2')
    head1 = lead_line(s, p1 + ' | ' + p2, 66, 104)
    head2 = lead_line(s, p1 + ' | ' + p2b, 70, 112)
    ch1 = lead_line(s, chorus_line, 76, 116)
    ch2 = lead_line(s, chorus_line, 84, 124)
    hg.play(lead, head1, a.bar(0), vib=True)
    hg.play(lead, head2, a.bar(8), vib=True, throws=True)
    hg.play(lead, ch1, b_, vib=True, throws=True)
    hg.play(lead, ch2, b2, vib=True, throws=True)
    hg.play(lead, head2, a3, vib=True, throws=True)

    # ------------------------------------------------------------------ drums
    motif = drummer.DrumMotif.make(seed=4, cell=RIFF_CELL, density=0.45)
    # the opening cymbal swell (soft mallets), then the drummer alone on the toms: the motif
    mallets.play(drummer.swell(4, BPM, kit=mallets, energy=0.75, seed=2), intro.start)
    mallets.humanize(0, 0)
    drummer.perform([{'move': 'develop', 'bars': 1, 'energy': 0.66, 'variations': ['orchestrate'], 'feet': 'four'}],
                    bpm=BPM, kit=kit, at=intro.bar(1), motif=motif, seed=3, hands=HANDS).play(kit)
    mem = drummer.Memory()
    drummer.arrange([('intro', 2), ('verse', 16), ('chorus', 8)], bpm=BPM, style='rock', density=0.55, seed=21,
                    kit=kit, at=intro.bar(2), memory=mem, lock=b.bass, hands=HANDS,
                    plan={'intro': {'energy': 0.62, 'crash': True}, 'verse': {'energy': 0.55, 'time': 'hat8'},
                          'chorus': {'energy': 0.88, 'time': 'ride'}}).play(kit)
    kit.play(drummer.pattern(riff_drums(4, stop=True), BPM, kit=kit, energy=0.86, seed=8, hands=HANDS), riff)
    drummer.perform([SOLO_IN], bpm=BPM, kit=kit, at=solo.start, motif=motif, seed=7, hands=HANDS).play(kit)
    body = (s._at(solo.bar(SOLO_IN[1])), SOLO_BODY)
    vocab = drummer.vocabulary(kit, hands=HANDS, moves=[m for m in drummer.SOLO_ROLES
                                                        if m not in ('time', 'finish', 'hit_choke')])
    part = soloist.solo(s, kit, vocab, at=body, motif=motif.to_clip(kit), arc=SOLO_ARC, seed=SOLO_SEED)
    drummer.perform([SOLO_OUT], bpm=BPM, kit=kit, at=solo.bar(SOLO_IN[1] + SOLO_BODY), motif=motif, seed=9,
                    hands=HANDS).play(kit)
    gated_at = [(a0, a1) for a0, a1, _, name in part.moves if name == 'gated_toms']
    if gated_at:                                      # the 80s tom break through the gated room
        pts = [(0.0, -60, 'step')]
        for a0, a1 in gated_at:
            pts += [(a0 - 0.05, -60, 'step'), (a0, -4, 'step'), (a1 + 0.5, -60, 'step')]
        kit.automate('send.gated', pts)
    # the solo's longest rest: its last strokes ring into it (a plate throw)
    ns = sorted(part.clip, key=lambda n: n.start)
    gaps = [(b_.start - a_.start, part.start + a_.start, part.start + b_.start) for a_, b_ in zip(ns, ns[1:])]
    _, g0, g1 = max(gaps)
    hit = s._at(end.bar(3))
    kit.automate('send.plate', hold(0, g0 - 1.0, -20), ramp(g0 - 1.0, g0, -20, -5), hold(g0, g1 - 0.5, -5),
                 ramp(g1 - 0.5, g1, -5, -20), hold(g1, hit - 0.5, -20), ramp(hit - 0.5, hit, -20, -6),
                 hold(hit, end.end, -6))
    for gtr in (b.gtr_l, b.gtr_r):                  # the final hit rings into the room
        gtr.automate('send.room', hold(0, hit - 0.5, -13), ramp(hit - 0.5, hit, -13, -6), hold(hit, end.end, -6))
    drummer.arrange([('chorus2', 8), ('verse3', 8)], bpm=BPM, style='rock', density=0.6, seed=22, kit=kit,
                    at=b2.start, memory=mem, lock=b.bass, hands=HANDS,
                    plan={'chorus2': {'energy': 0.95, 'time': 'ride'}, 'verse3': {'energy': 0.82, 'time': 'hat8'}}
                    ).play(kit)
    kit.play(drummer.pattern(riff_drums(2), BPM, kit=kit, energy=0.9, seed=9, hands=HANDS), end.start)
    drummer.perform([('finish', 1, 1.0), ('hit_choke', 1, 1.0)], bpm=BPM, kit=kit, at=end.bar(2), motif=motif,
                    seed=12, hands=HANDS).play(kit)

    # the master (MASTER.md: `python -m agentsound master` against the rock profile, platform auto)
    mastering.apply(s, eq={'low.freq': 60, 'low.gain': -0.8, 'low.q': 0.7071, 'peak1.freq': 400, 'peak1.gain': 2.0,
                           'peak1.q': 1.0}, limiter={'ceiling': -1.2, 'release': 120.0}, loudness_change=+3.5)
    s.solo_part = part                                # the solo's log (moves, plan) for the notes
    return s
