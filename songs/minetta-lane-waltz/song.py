"""Minetta Lane Waltz - an original straight-8th jazz waltz for piano trio (D minor, 3/4, 152 BPM, ~3:40).
Build: python -m agentsound build songs/minetta-lane-waltz

New York bar jazz without swing, in three: a grand piano, an upright bass and brushes in a small Village room, a
bittersweet minor waltz with a major bridge, every 8th even (straight Feel, ratio 0.5, small lay-backs). The tune is a
32-bar AABA, one chord per bar (3 beats):

  A1   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Dm9 | G13     | Em7b5    | A7b9
  A2   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Gm9 | A7alt   | DmMaj9   | F13          (-> the bridge in Bb)
  B    Bbmaj9   | Eb9#11    | Am7 | D7b9  | Gm9 | C13     | Bb7#11   | A7alt
  A3   Dm9      | Bbmaj7#11 | Gm9 | A7b13 | Gm9 | A7b9    | DmMaj9   | A7alt        (turnaround)
  head-out bridge reharmonized: Gm9 | Eb9#11 | Fmaj7#11 | Ab13 | Ebmaj9 | D9 | Bb7#11 | Eb7#11 (tritone home)

The hook: a pickup (A C) into a three-step rise D-E-F that leaps a third up to a held A (the Bbmaj7's 7th), sighs
back down F-E-D and lands on the C# of the A7 - repeated, then answered brighter (B natural over G13), and in A2 turned
into a climb (C# E G -> Bb) that ends on the bittersweet D over D minor-major. The bridge sings the same shape in
major (A held over Bbmaj9, G over Eb9#11, C over Am7), climbs through D7b9 to the high E over C13 and falls back in
one long line into the hook's pickup.

  intro       8   4 bars piano alone, rubato (the hook's tail over Bbmaj7#11 A7b9 Gm9 A7sus4, tenths in the left
                  hand), then 4 bars in tempo: bass and brushes enter, the hook foreshadowed, the pickup into the head
  head       32   the melody harmonized by the pianist (pianist.arrange), left hand shells with waltz answers on
                  2 / the & of 2; bass in one / two, brushes stir in 3 with taps on 2 and 3
  solo_1     32   the piano solo builds: the motif in fragments (A1), an improvised line (A2), a line in the bridge,
                  the motif in 6ths (A3); bass starts walking in three
  solo_2     32   the climax chorus: a line with runs, octaves, locked hands in the bridge, the hook an octave up in
                  octaves (A3), then it winds down; ride in three
  bass_solo  32   the Meatbass quotes the hook and sings a chorus; the piano whispers shells; brushes only stir
  head_out   32   A1 with a tritone sub, A2 lush, the bridge reharmonized (Gm9 Eb9#11 Fmaj7#11 Ab13 ...), the last A
                  quietly
  tag         8   Gm9 A7alt Dm9 Bbmaj7#11 | Gm9 Eb7#11 Dm9 A7alt, the hook's tail twice, ritardando
  end         3   DmMaj9 rolled from the left hand up into the pedal, fermata, the room rings
"""
from agentsound import *
from agentsound import bands, jazz, pianist
from agentsound.bandlib import jazz as jazzband
import random

ANALYSIS = {'profile': 'jazz'}
METADATA = {'title': 'Minetta Lane Waltz', 'artist': 'AgentSound', 'album': 'Blue Hour Sessions',
            'genre': 'Jazz', 'year': 2026}
COVER = {'style': 'jazz', 'palette': ['#6b2e3a', '#d8b26a'], 'title': 'minetta lane waltz',
         'subtitle': 'AgentSound - Blue Hour Sessions', 'seed': 12}

TEMPO = 152
INTRO_BPM = 112
BPB = 3.0
ARRANGED = {}          # section:part -> pianist.Arrangement (filled by build(); inspect what the pianist played)
MASTER_DRIVE = 6.9
PIANO_TRIM = -3.0

# spice budget (user: too many fast trills / tremolos in perry-street-rain v3): the arranger's ornaments lean on
# turns, mordents, crushes, re-struck voicings and rolls; a trill or tremolo is rare
ORN = {'turn': 1.2, 'mordent': 1.0, 'inverted_mordent': 0.6, 'crush': 1.0, 'restrike': 1.6, 'roll': 1.0,
       'trill': 0.25, 'tremolo': 0.2}

# ------------------------------------------------------------------------------------------------ changes
A1 = 'Dm9 Bbmaj7#11 Gm9 A7b13 | Dm9 G13 Em7b5 A7b9'
A2 = 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7alt DmMaj9 F13'
BR = 'Bbmaj9 Eb9#11 Am7 D7b9 | Gm9 C13 Bb7#11 A7alt'
A3 = 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7b9 DmMaj9 A7alt'
A1R = 'Dm9 Bbmaj7#11 Gm9 Eb7#11 | Dm9 G13 Em7b5 A7b9'          # head out: tritone sub in bar 4
BRR = 'Gm9 Eb9#11 Fmaj7#11 Ab13 | Ebmaj9 D9 Bb7#11 Eb7#11'     # the reharmonized bridge
A3E = 'Dm9 Bbmaj7#11 Gm9 A7b13 | Gm9 A7b9 DmMaj9 Eb7#11'       # the last A: into the tag
INTRO = 'Bbmaj7#11 A7b9 Gm9 A7sus4 | Dm9 Bbmaj7#11 Dm9 A7b13'
TAG = 'Gm9 A7alt Dm9 Bbmaj7#11 | Gm9 Eb7#11 Dm9 A7alt'
END = 'DmMaj9'


# ------------------------------------------------------------------------------------------------ notation
def ph(spec: str, vel: float = 90) -> Clip:
    """A written line in 3/4: tokens PITCH[/len][!|?] separated by spaces, 'r' = rest; len in 8ths (default 1 = an
    8th, '/3' = dotted quarter, '/6' = a whole bar); '!' accent, '?' ghost; 'g:PITCH' = a crushed grace note just
    before the next note; '|' checks the bar line (6 8ths). Notes are held to the next onset (finger legato)."""
    t, mark, grace, notes = 0.0, 0.0, None, []
    for tok in spec.replace('|', ' | ').split():
        if tok == '|':
            nb = mark + BPB
            if abs(t - nb) > 1e-6:
                raise ValueError(f"bar ending at beat {nb} holds {t - mark:.3f} beats in {spec[:70]!r}")
            mark = nb
            continue
        if tok.startswith('g:'):
            grace = tok[2:]
            continue
        acc = 1.1 ** tok.count('!') * 0.72 ** tok.count('?')
        tok = tok.replace('!', '').replace('?', '')
        p, _, d = tok.partition('/')
        dur = 0.5 * (float(d) if d else 1.0)
        if p != 'r':
            if grace:
                g = 0.1
                if notes and notes[-1][0] + notes[-1][1] > t - g:
                    notes[-1][1] = max(0.08, t - g - notes[-1][0])
                notes.append([t - g, g, grace, vel * 0.72])
            notes.append([t, dur, p, vel * acc])
        grace = None
        t += dur
    length = max(BPB, -(-t // BPB) * BPB)
    return Clip([(a, d, p, max(1, min(127, int(round(v))))) for a, d, p, v in notes], length=length)


def waltz_bass(prog, seed: int, vel: int = 84, style: str = 'two') -> Clip:
    """A straight-8th jazz-waltz bass line with real dynamics: 'one' = the root held through the bar (sometimes the
    fifth on 3), 'two' = root (half) + fifth / tenth / an approach (quarter) on 3, 'walk' = three quarters (root,
    a chord tone, an approach into the next root; now and then two 8ths on 3). Velocity: the downbeat leans, 2 is
    light, the approach on 3 leads; a 4-bar arch over it and a little seeded play."""
    rng = random.Random(seed)
    chords = [(st, d, c) for st, d, c in prog if c is not None]
    out = []

    def near(pc, ref, lo=28, hi=45):                    # E1 .. A2 for roots, closest to the previous one
        cands = [p for p in range(lo, hi + 1) if p % 12 == pc]
        return min(cands, key=lambda p: (abs(p - ref), p))

    prev = 38
    arch = (0.9, 1.0, 1.08, 0.92)
    for i, (st, d, c) in enumerate(chords):
        root = near(c.root, prev)
        nxt = chords[i + 1][2].root if i + 1 < len(chords) else chords[0][2].root
        nroot = near(nxt, root)
        ivs = {(p - c.root) % 12 for p in c.pcs}
        third = root + (3 if 3 in ivs and 4 not in ivs else 4)
        fifth = root + (6 if 6 in ivs and 7 not in ivs else 7)
        seventh = root + (10 if 10 in ivs else 11 if 11 in ivs else 9)
        ap = rng.choice((nroot + 1, nroot - 1, nroot - 1, nroot + 7 if nroot + 7 <= 50 else nroot - 5))
        ph_ = arch[int(round(st / BPB)) % 4]

        def v(x):
            return max(1, min(127, int(round(vel * x * ph_ * (1 + (rng.random() - 0.5) * 0.1)))))
        if style == 'one':
            if rng.random() < 0.3:
                out += [(st, 1.9, root, v(1.0)), (st + 2.0, 0.9, rng.choice((fifth, ap)), v(0.84))]
            else:
                out += [(st, 2.85, root, v(1.0))]
        elif style == 'two':
            mid = rng.choice((fifth, fifth, ap, ap, third + 12 if third + 12 <= 52 else fifth))
            out += [(st, 1.9, root, v(1.04)), (st + 2.0, 0.9, mid, v(0.8))]
        else:   # walk
            a = rng.choice((third, fifth, fifth, seventh, root + 12 if root + 12 <= 50 else fifth))
            if rng.random() < 0.18:
                out += [(st, 0.92, root, v(1.02)), (st + 1.0, 0.92, a, v(0.8)), (st + 2.0, 0.45, fifth, v(0.84)),
                        (st + 2.5, 0.45, ap, v(0.88))]
            else:
                out += [(st, 0.92, root, v(1.06)), (st + 1.0, 0.92, a, v(0.74)), (st + 2.0, 0.92, ap, v(0.88))]
        prev = root
    return Clip(sorted(out), length=prog.length)


def waltz_brushes(band, bars: int, seed: int, vel: float = 1.0, ghosts: float = 0.0, kick: bool = False,
                  ride: float = 0.0, fills: bool = True, taps: bool = True) -> Clip:
    """Brushes in three: the preset's stir once per bar (a Swirly stir about every second: one per bar at 152) +
    taps and hat foot on 2 and 3, plus colour: ghost taps on the &s (ghosts = probability), a feathered kick on 1
    (and softly the & of 2), or the ride in three (1, 2, & of 2, 3 - ride = level) with brush digs on 2."""
    kit = band.info['kit']
    base = jazzband.brushes(band, bars, style='medium', kick=None, fills=fills, fill='eighths', vel=vel,
                            taps=taps and ride == 0.0, seed=seed, beats_per_bar=BPB)
    rng = random.Random(seed)
    extra = []
    for b in range(bars):
        t0 = BPB * b
        fill_bar = fills and b % 8 == 7
        for k in range(6):
            t = t0 + 0.5 * k
            if fill_bar and t >= t0 + 1.5:
                continue
            if ghosts and k % 2 == 1 and rng.random() < ghosts:
                extra.append((t, 0.2, kit['tap'], int(22 * vel + rng.randint(0, 6))))
            if ride and k in (0, 2, 3, 4):
                extra.append((t, 0.4, kit['ride'], int((56 if k in (0, 3) else 44) * ride + rng.randint(-3, 3))))
        if kick:
            extra.append((t0, 0.3, kit['kick'], int(38 * vel + rng.randint(0, 4))))
            if rng.random() < 0.3 and not fill_bar:
                extra.append((t0 + 1.5, 0.3, kit['kick'], int(27 * vel + rng.randint(0, 4))))
        if ride and not fill_bar:
            extra.append((t0 + 1.0, 0.25, kit['dig'], int(36 * vel + rng.randint(0, 5))))
    return base | Clip([(a, d, p, max(1, min(127, v))) for a, d, p, v in extra], length=BPB * bars)


def rolled(clip: Clip, lo: float = 8, hi: float = 22, rng=None, direction='up') -> Clip:
    ms = (rng or random).uniform(lo, hi)
    return clip.strum(ms=ms, direction=direction, bpm=TEMPO)


# ------------------------------------------------------------------------------------------------ the head
HEAD_A1 = ph("""
 D5/3 E5 F5/2 | A5/4 G5/2 | F5/3 E5 D5/2 | C#5/4 A4 C5 |
 D5/3 E5 F5/2 | B5/4 A5/2 | G5/3 F5 E5 D5 | E5/2 C#5/2 A4 C5""", 70)
HEAD_A2 = ph("""
 D5/3 E5 F5/2 | A5/4 G5/2 | F5/3 E5 D5/2 | C#5/4 E5 G5 |
 Bb5/3 A5 G5/2 | F5/3 Eb5 C#5/2 | D5/6 | r/3 C5 D5 F5""", 78)
HEAD_B = ph("""
 A5/4 F5 D5 | G5/4 F5 Db5 | C6/3 B5 A5/2 | F#5/3 A5 C6 Eb6 |
 D6/4 C6 Bb5 | E6/3 D6 C6 A5 | Ab5/3 G5 F5/2 | G5 F5 Eb5 C#5 A4 C5""", 86)
HEAD_A3 = ph("""
 D5/3 E5 F5/2 | A5/4 G5/2 | F5/3 E5 D5/2 | C#5/4 E5 G5 |
 Bb5/3 C6 D6/2 | C#6/3 Bb5 G5 E5 | D5/6 | r/4 A4 C5""", 80)
HEAD_A3_END = ph("""
 D5/3 E5 F5/2 | A5/4 G5/2 | F5/3 E5 D5/2 | C#5/4 E5 G5 |
 Bb5/3 C6 D6/2 | C#6/3 Bb5 G5 E5 | D5/6 | r/2 Db5/2 C5 Bb4""", 70)

# ------------------------------------------------------------------------------------------------ piano solo
SOLO1_A1 = ph("""
 r/2 D5 E5 F5/2 | A5/3 r/3 | r/2 F5 G5 A5/2 | C#6/3 r/3 |
 r/2 A5 C6 D6 C6 | B5/2 A5 F5 D5 B4 | D5/2 E5 G5 Bb5 D6 | C#6/3 Bb5 G5 E5""", 80)
SOLO2_B = ph("""
 D6/3 C6 A5/2 | G5/3 A5 Bb5/2 | C6/3 E6 D6/2 | C6/3 A5 F#5/2 |
 Bb5/3 D6 F6/2 | E6/3 G6 A6/2 | Ab6/3 F6 D6/2 | C#6/2 Bb5 G5 A5 C6""", 100)
SOLO2_A3 = ph("""
 D6/3 E6 F6/2 | A6/4 G6/2 | F6/3 E6 D6/2 | C#6/4 E6 G6 |
 Bb6/3 A6 G6/2 | F6/3 Eb6 C#6/2 | D6/3 A5 F5 D5 | r/6""", 104)
SOLO1_A3 = ph("""
 D5/3 E5 F5/2 | A5/4 G5 A5 | Bb5/3 A5 G5/2 | E5/4 r/2 |
 r F5 G5 A5 Bb5 D6 | C#6/3 Bb5 G5 E5 | F5/3 E5 D5 A4 | r/4 A4 C5""", 88)

# ------------------------------------------------------------------------------------------------ bass solo
BASS_SOLO = ph("""
 r/2 D3 E3 F3/2 | A3/4 G3/2 | F3/3 E3 D3/2 | C#3/4 A2 C3 |
 D3/2 F3 A3 C4/2 | B3/3 A3 F3 D3 | E3/2 G3 Bb3 A3 G3 | E3/2 C#3/2 A2 C3 |
 D3/3 E3 F3 A3 | D3/2 C3 A2 F2/2 | G2/2 Bb2 D3 F3/2 | E3/2 C#3/2 E3 G3 |
 Bb3/3 A3 G3/2 | F3/3 Eb3 C#3/2 | D3/4 E3 F3 | A3/2 G3 F3 Eb3 C3 |
 A3/4 F3 D3 | G3/4 F3 Db3 | C3/3 E3 G3/2 | F#3/3 A3 C4 A3 |
 Bb3/2 A3 G3 F3 D3 | E3/2 C3 D3 E3 G3 | Ab3/3 G3 F3 D3 | C#3/2 Eb3 F3 G3 A3 |
 A3/3 G3 F3 D3 | E3/2 D3 C3 A2/2 | Bb2/2 D3/2 F3/2 | E3/3 F3 C#3/2 |
 D3/2 Bb2 G2 A2 Bb2 | C#3/3 Bb2 G2/2 | D2/4 r/2 | A2/4 r/2""", 94)
BASS_SLIDES = [(1, 0.0, -2.0), (5, 0.0, -1.0), (16, 0.0, -2.0), (20, 0.0, -1.0), (24, 0.0, -2.0)]

# ------------------------------------------------------------------------------------------------ intro / tag / end
INTRO_RUB = ph("F5/3 E5 D5/2 | C#5/4 E5 G5 | Bb5/3 A5 G5/2 | E5/6", 70)
INTRO_TEMPO = ph("r/2 D5 E5 F5/2 | A5/6 | r/2 D5 E5 F5/2 | E5/2 C#5/2 A4 C5", 66)
TAG_RH = ph("""
 Bb5/3 A5 G5/2 | F5/3 Eb5 C#5/2 | D5/6 | r/2 D5 E5 F5/2 |
 Bb5/3 A5 G5/2 | F5/3 Eb5 Db5/2 | D5/6 | r/3 C#5 F5 G5""", 66)
END_LH = Clip([(0, 8.9, p, v) for p, v in (('E3', 46), ('A3', 50))], length=9)    # the bass has the low D
END_RH = Clip([(0, 8.6, p, v) for p, v in (('F4', 64), ('A4', 66), ('C#5', 72), ('E5', 78), ('A5', 96))],
              length=9)


def build() -> Song:
    s = Song('Minetta Lane Waltz', tempo=TEMPO, key='D minor', seed=12, tail=6, meter=(3, 4))
    secs = [('intro', 8), ('head', 32), ('solo_1', 32), ('solo_2', 32), ('bass_solo', 32), ('head_out', 32),
            ('tag', 8), ('end', 3)]
    intro, head, solo1, solo2, bsolo, hout, tag, end = (s.section(n, bars=b) for n, b in secs)
    feel = jazz.Feel(TEMPO, ratio=0.5, layback={'piano': 8, 'comp': 4, 'bass': -2, 'drums': 0}, beats_per_bar=BPB)
    b = bands.make('jazz_trio', s, feel=feel, master_gain=MASTER_DRIVE)
    b.piano.gain_db += PIANO_TRIM
    b.drums.gain_db -= 1.5        # brushes 14-16 dB (RMS) under the piano in every section
    b.bass.gain_db -= 1.0         # the piano leads: the bass sits a little under it
    kit = b.info['kit']
    # air, not bite: the preset's jazz_grand keeps the loud layers warm (HUMAN_FEEDBACK: "es klingt hart")
    b.piano.add_fx(fx.eq({'high.freq': 9000, 'high.gain': 1.5}))
    s.master.add_fx(fx.eq({'high.freq': 8000, 'high.gain': 2.0}), first=True)   # air (the room IR is dark)
    P = {k: s.prog(v) for k, v in (('A1', A1), ('A2', A2), ('B', BR), ('A3', A3), ('A1r', A1R), ('Br', BRR),
                                   ('A3e', A3E), ('intro', INTRO), ('tag', TAG), ('end', END))}
    rng = random.Random(9)
    mem = pianist.Memory()        # one pianist for the whole song: the ornament budget counts song-wide
    mem.save(solo2.bar(29))       # the fast figure is saved for the climax (the hook an octave up)

    def hands(sec, part, bar, mel, *, pedal_rh=True, lh='guide', lh_vel=54, bpm=TEMPO, busy=0.5, answers=True,
              **kw):
        """The pianist plays `mel` over P[part]: the right hand harmonized, decorated and filled, the left hand on
        the comping track (in 3/4 it answers on 2 / the & of 2 / 3 where the right hand leaves room: `busy` = how
        often); the pedal follows the harmony and lifts for runs and trills."""
        kw.setdefault('ornaments', ORN)
        at = sec.bar(bar)
        arr = pianist.arrange(mel, P[part], bpm=bpm, key=s.key, lh=lh, lh_vel=lh_vel, memory=mem, at=at,
                              lh_answers=busy if answers else 0.0, **kw)
        b.piano.play(arr.rh, at)
        if len(arr.lh):
            b.comp.play(arr.lh, at)
        if pedal_rh:
            b.piano.automate('instrument.pedal', arr.pedal(P[part], at))
        ARRANGED[f"{sec.name}:{part}:{bar}"] = arr
        return arr

    def bass(sec, part, bar, seed, vel, style='two'):
        # a bassist's touch on the line (jazz.bass_touch): 4-bar arcs (12 beats) around `vel`, the root on 1
        # leading, 2 light, 3 answering; the evened upright plays the velocity as its level
        line = jazz.bass_touch(waltz_bass(P[part], seed, vel, style), vel * 0.84, vel * 1.22, accent='1-3',
                               phrase=4 * BPB, beats_per_bar=BPB, seed=seed)
        b.bass.play(line, sec.bar(bar))

    # ============================================================== intro
    # 4 bars rubato, piano alone (tenths in the left hand, ballad voicings), then in tempo: bass + brushes enter,
    # the hook foreshadowed, the pickup (A C) into the head
    intro_p = s.prog(INTRO)
    P['intro_a'] = s.prog('Bbmaj7#11 A7b9 Gm9 A7sus4')
    P['intro_b'] = s.prog('Dm9 Bbmaj7#11 Dm9 A7b13')
    hands(intro, 'intro_a', 0, jazz.touch(INTRO_RUB, 50, 84), style='ballad', density=0.5, seed=101, lh='tenths',
          lh_vel=54, pedal_rh=True, answers=False, bpm=INTRO_BPM, roll=(30, 55),
          ornaments={'roll': 2.0, 'restrike': 1.0, 'turn': 1.0}, fills={'arpeggio': 3.0, 'answer': 1.0})
    hands(intro, 'intro_b', 4, jazz.touch(INTRO_TEMPO, 46, 80), style='sparse', density=0.5, seed=102,
          lh_vel=50, busy=0.8, section_end=False)
    jazzband.pedal([b.comp], intro_p, intro)
    bass(intro, 'intro_b', 4, 11, 78, 'one')
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(14, 44)), intro.bar(3))
    b.drums.play(waltz_brushes(b, 4, 21, vel=0.5, fills=False), intro.bar(4))

    # ============================================================== head
    heads = {'A1': jazz.touch(HEAD_A1, 42, 82), 'A2': jazz.touch(HEAD_A2, 48, 94),
             'B': jazz.touch(HEAD_B, 54, 104),
             'A3': jazz.touch(jazz.paraphrase(HEAD_A3, seed=3, anticipate=0.0, delay=0.0, embellish=0.12,
                                              key=s.key), 50, 96)}
    hands(head, 'A1', 0, heads['A1'], style='straight', density=0.45, seed=201, lh_vel=52, inner=0.76, busy=0.55)
    hands(head, 'A2', 8, heads['A2'], style='straight', density=0.6, seed=202, lead_in=True, lh_vel=55,
          inner=0.76, busy=0.6)
    hands(head, 'B', 16, heads['B'], style='straight', density=0.8, seed=203, lead_in=True, lh='rootless',
          lh_vel=58, busy=0.65, devices={'drop2': 2.5, 'sixths': 1.5, 'quartal': 1.5, 'close': 1.0, 'guide': 1.0},
          fills={'run': 2.0, 'fourths': 1.5, 'arpeggio': 2.0, 'answer': 1.0},
          ornaments={'trill': 1.5, 'turn': 1.0, 'restrike': 1.0, 'crush': 1.0})
    hands(head, 'A3', 24, heads['A3'], style='lush', density=0.6, seed=204, lead_in=True, lh='rootless',
          lh_vel=54, busy=0.55)
    jazzband.pedal([b.comp], P['A1'] + P['A2'] + P['B'] + P['A3'], head)
    bass(head, 'A1', 0, 31, 81, 'one')
    bass(head, 'A2', 8, 32, 85, 'two')
    bass(head, 'B', 16, 33, 89, 'two')
    bass(head, 'A3', 24, 34, 89, 'two')
    b.drums.play(waltz_brushes(b, 8, 41, vel=0.5), head)
    b.drums.play(waltz_brushes(b, 8, 42, vel=0.62, ghosts=0.35, kick=True), head.bar(8))
    b.drums.play(waltz_brushes(b, 16, 43, vel=0.72, ghosts=0.5, kick=True), head.bar(16))

    # ============================================================== solo chorus 1: it builds
    motif = HEAD_A1.slice(0, 6)
    line_a2 = jazz.solo_line(P['A2'], key=s.key, register=('A4', 'D6'), density=0.62, intensity=0.55, seed=14,
                             motif=motif, motif_prob=0.5, phrase_bars=(2, 3), triplets=0.1, length=24)
    line_b1 = jazz.solo_line(P['B'], key=s.key, register=('C5', 'Eb6'), density=0.7, intensity=0.65, seed=15,
                             motif=HEAD_B.slice(0, 6), motif_prob=0.4, phrase_bars=(2, 3), triplets=0.1, length=24)
    hands(solo1, 'A1', 0, jazz.touch(SOLO1_A1, 54, 100), style='sparse', density=0.55, seed=301, lead_in=True,
          pedal_rh=False, lh_vel=56, busy=0.6, fills={'answer': 2.0, 'run': 1.0, 'pentatonic': 1.0})
    hands(solo1, 'A2', 8, jazz.touch(line_a2, 58, 104), style='straight', density=0.55, seed=302, lead_in=True,
          pedal_rh=False, lh_vel=58, busy=0.6, devices={'single': 3.0, 'guide': 2.0, 'thirds': 1.0},
          fills={'run': 2.0, 'chromatic': 1.5, 'fourths': 1.5, 'pentatonic': 1.0})
    hands(solo1, 'B', 16, jazz.touch(line_b1, 62, 106), style='straight', density=0.6, seed=303, lead_in=True,
          pedal_rh=False, lh='rootless', lh_vel=60, busy=0.65,
          devices={'single': 2.0, 'guide': 2.0, 'sixths': 1.5, 'thirds': 1.5},
          fills={'run': 1.5, 'fourths': 1.5, 'chromatic': 1.0, 'arpeggio': 1.0})
    hands(solo1, 'A3', 24, jazz.touch(SOLO1_A3, 62, 106), style='straight', density=0.7, seed=304, lead_in=True,
          lh='rootless', lh_vel=60, busy=0.65, devices={'sixths': 3.0, 'thirds': 1.5, 'drop2': 1.0})
    bass(solo1, 'A1', 0, 61, 89, 'two')
    bass(solo1, 'A2', 8, 62, 91, 'walk')
    bass(solo1, 'B', 16, 63, 93, 'walk')
    bass(solo1, 'A3', 24, 64, 93, 'walk')
    b.drums.play(waltz_brushes(b, 16, 71, vel=0.72, ghosts=0.4, kick=True), solo1)
    b.drums.play(waltz_brushes(b, 16, 72, vel=0.8, ghosts=0.5, kick=True), solo1.bar(16))

    # ============================================================== solo chorus 2: the climax, then it winds down
    line_a1 = jazz.solo_line(P['A1'], key=s.key, register=('C5', 'F6'), density=0.75, intensity=0.75, seed=16,
                             motif=motif, motif_prob=0.4, phrase_bars=(2, 4), triplets=0.12, length=24)
    line_a2b = jazz.solo_line(P['A2'], key=s.key, register=('D5', 'G6'), density=0.8, intensity=0.8, seed=17,
                              motif=motif, motif_prob=0.5, phrase_bars=(2, 4), triplets=0.1, length=24)
    hands(solo2, 'A1', 0, jazz.touch(line_a1, 64, 108), style='straight', density=0.65, seed=311, lead_in=True,
          pedal_rh=False, lh='rootless', lh_vel=60, busy=0.7, devices={'single': 2.0, 'guide': 2.0, 'thirds': 1.5,
                                                                      'sixths': 1.0},
          fills={'run': 2.0, 'chromatic': 1.5, 'pentatonic': 1.5, 'fourths': 1.0})
    hands(solo2, 'A2', 8, jazz.touch(line_a2b, 66, 110), style='bar', density=0.7, seed=312, lead_in=True,
          pedal_rh=False, lh='rootless', lh_vel=62, busy=0.7, quick=0.2,
          ornaments={'crush': 1.5, 'blues_crush': 1.5, 'slip': 1.0, 'mordent': 1.0, 'turn': 0.8, 'repeated': 0.6,
                     'trill': 0.2},
          fills={'chromatic': 2.0, 'run': 1.5, 'octave_run': 1.0, 'stabs': 1.0, 'hands': 0.8})
    hands(solo2, 'B', 16, jazz.touch(SOLO2_B, 74, 114), style='lush', density=0.8, seed=313, lead_in=True,
          lh='rootless', lh_vel=64, busy=0.6, voices=3, devices={'locked': 3.0, 'drop2': 2.0, 'octave': 1.0},
          ornaments={'restrike': 1.5, 'roll': 0.8, 'turn': 0.8, 'tremolo': 1.2},
          fills={'hands': 2.0, 'arpeggio': 1.0, 'fourths': 1.0})
    hands(solo2, 'A3', 24, jazz.touch(SOLO2_A3, 72, 116), style='bar', climax=True, density=0.85, seed=314,
          lead_in=True, pedal_rh=False, lh='rootless', lh_vel=64, busy=0.6, quick=0.15, section_end=False,
          ornaments={'blues_crush': 1.5, 'crush': 1.0, 'slip': 1.0, 'repeated': 1.0, 'shake': 1.0, 'trill': 0.3},
          fills={'octave_run': 1.5, 'chromatic': 1.0, 'hands': 1.0})
    bass(solo2, 'A1', 0, 81, 93, 'walk')
    bass(solo2, 'A2', 8, 82, 95, 'walk')
    bass(solo2, 'B', 16, 83, 96, 'walk')
    bass(solo2, 'A3', 24, 84, 96, 'walk')
    b.drums.play(waltz_brushes(b, 16, 91, vel=0.88, ghosts=0.4, kick=True), solo2)
    b.drums.play(waltz_brushes(b, 16, 92, vel=0.95, kick=True, ride=0.9), solo2.bar(16))
    b.drums.play(Clip([(0, 2, kit['crash'], 40)], length=3), solo2.bar(16))

    # ============================================================== bass solo: the hook in the bass, piano whispers
    b.bass.play(jazz.touch(BASS_SOLO, 68, 98), bsolo)     # the solo sung like a melody
    bend = []
    for bar, beat, frm in BASS_SLIDES:
        t = bsolo.bar(bar) + beat
        bend += [(t - 0.03, 0.0, 'step'), (t - 0.01, frm, 'step'), (t + 0.2, 0.0, 'smooth')]
    b.bass.automate('instrument.pitchbend', bend)
    # +2 dB for the solo ('gainDb' lanes are dB on the track's gain_db)
    b.bass.automate('gainDb', [(0, 0.0), (bsolo.start - 1, 0.0), (bsolo.start, 2.0, 'smooth'),
                               (hout.start - 1, 2.0), (hout.start, 0.0, 'smooth')])

    for i, part in enumerate(('A1', 'A2', 'B', 'A3')):
        c = jazz.comp(P[part], style='waltz', voicing='shell', density=0.3, intensity=0.22, seed=131 + i,
                      register=('C3', 'A4'), answer=BASS_SOLO.slice(24 * i, 24 * i + 24), vel=50 + 2 * i, length=24)
        b.comp.play(rolled(c, 20, 40, rng), bsolo.bar(8 * i))
    jazzband.pedal([b.comp], P['A1'] + P['A2'] + P['B'] + P['A3'], bsolo)
    b.piano.play(pianist.sweep('A7alt', 1.4, TEMPO, low='C#4', high='C5', direction='up', ring=False,
                               vel=(40, 70), seed=13), bsolo.beat(-1.5))
    b.drums.play(waltz_brushes(b, 32, 141, vel=0.55, fills=False), bsolo)
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(22, 54)), bsolo.beat(-3))

    # ============================================================== head out: A1 re-harmonized, A2, the new bridge,
    # the last A quiet
    hands(hout, 'A1r', 0, jazz.touch(jazz.paraphrase(HEAD_A1, seed=5, anticipate=0.2, delay=0.0, embellish=0.1,
                                                      key=s.key), 50, 92),
          style='straight', density=0.55, seed=401, lead_in=True, lh='rootless', lh_vel=56, busy=0.6)
    hands(hout, 'A2', 8, jazz.touch(HEAD_A2, 54, 98), style='lush', density=0.65, seed=406, lead_in=True,
          lh='rootless', lh_vel=58, busy=0.6, ornaments=dict(ORN, trill=3.0))   # the one trill: the held D
    hands(hout, 'Br', 16, jazz.touch(HEAD_B, 62, 108), style='lush', density=0.8, seed=403, lead_in=True,
          lh='rootless', lh_vel=60, busy=0.6, devices={'drop2': 3.0, 'close': 1.5, 'ust': 1.0, 'locked': 1.0},
          fills={'arpeggio': 2.0, 'fourths': 1.0, 'run': 1.0})
    hands(hout, 'A3e', 24, jazz.touch(HEAD_A3_END, 42, 80), style='sparse', density=0.45, seed=404, lead_in=True,
          lh_vel=50, busy=0.5)
    jazzband.pedal([b.comp], P['A1r'] + P['A2'] + P['Br'] + P['A3e'], hout)
    bass(hout, 'A1r', 0, 161, 89, 'two')
    bass(hout, 'A2', 8, 162, 91, 'walk')
    bass(hout, 'Br', 16, 163, 93, 'walk')
    bass(hout, 'A3e', 24, 164, 81, 'two')
    b.drums.play(waltz_brushes(b, 16, 171, vel=0.75, ghosts=0.4, kick=True), hout)
    b.drums.play(waltz_brushes(b, 8, 172, vel=0.82, ghosts=0.5, kick=True), hout.bar(16))
    b.drums.play(waltz_brushes(b, 8, 173, vel=0.58, ghosts=0.15), hout.bar(24))

    # ============================================================== tag + ending
    tag_arr = hands(tag, 'tag', 0, jazz.touch(TAG_RH, 46, 84), style='ballad', density=0.5, seed=501, lead_in=True,
                    pedal_rh=False, lh='rootless', lh_vel=48, bpm=TEMPO * 0.85, busy=0.45, section_end=False)
    b.piano.automate('instrument.pedal', tag_arr.pedal(P['tag'], tag, end=end.start - 0.1))
    jazzband.pedal([b.comp], P['tag'], tag, end=end.start - 0.1)
    bass(tag, 'tag', 0, 191, 80, 'one')
    b.drums.play(waltz_brushes(b, 7, 201, vel=0.5, fills=False), tag)
    b.drums.play(jazz.brush_fill('swell', 3, kit=kit, vel=(12, 42)), tag.beat(-3))
    b.comp.play(END_LH.strum(ms=70, bpm=TEMPO * 0.7), end)
    b.piano.play(END_RH.strum(ms=85, bpm=TEMPO * 0.7).shift(0.25), end)
    for t in (b.piano, b.comp):
        t.automate('instrument.pedal', [(end.start - 0.05, 0.0, 'step'), (end.start + 0.02, 1.0, 'step')])
    b.bass.note('D2', end, dur=8, vel=82)
    b.drums.play(Clip([(0, 9, kit['crash'], 26), (0, 0.5, kit['kick'], 28), (0, 3, kit['sweep'], 54),
                       (3, 3, kit['sweep'], 42), (6, 3, kit['sweep'], 30)], length=9), end)

    # ============================================================== time
    s.set_tempo(intro, INTRO_BPM)                                  # the rubato bars: slower and free
    s.rubato((intro.start, intro.bar(4)), depth=0.07, phrase='lean')
    s.set_tempo(intro.bar(4), TEMPO)
    s.ritardando((tag.bar(4), end.start), to=0.72, a_tempo=False)
    s.fermata(end.start, hold=2, length=3)
    for t in (b.piano, b.comp):
        t.automate('send.room', ramp(end.start, end.end, -13, -8))
    return s
