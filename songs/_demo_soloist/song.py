"""Soloist demo: one instrument-agnostic solo wrapper (agentsound.soloist), two players. The same 8-bar arc over the
same changes and the same motif, played by the hero sax (hornist.vocabulary: breath swells, pushes, air-coupled
vibrato, scoops / falls, a shake or growl at the climax) and then by the hero guitar (guitarist.vocabulary: bends,
up-only finger vibrato, legato, picking bursts, pinch harmonics, feedback, whammy, wah). Build one at a time:
    python -m agentsound build songs/_demo_soloist --section sax
    python -m agentsound build songs/_demo_soloist --section guitar

Sections (96 BPM, A minor, Am F C G two bars each):
  sax     8   layered/hero_sax: statement -> answer -> develop -> burst -> climax -> resolve (arc 'classic')
  guitar  8   layered/hero_guitar_heavy: the same arc, the same motif, the guitar's vocabulary
See docs/COMPOSE_API.md "The soloist".
"""
from agentsound import *
from agentsound import bands, guitarist as gtr, hornist, soloist

ANALYSIS = {'profile': 'rock'}

MOTIF = '1:1/8 3:1/8 5:1/4 6:1/4. 5:1/8 | 4:1/4 3:1/4 1:1/2'      # 2 bars, degree:value


def build() -> Song:
    s = Song('Soloist Demo', tempo=96, key='A minor', seed=11)
    sax_sec = s.section('sax', bars=8)
    gtr_sec = s.section('guitar', bars=8)
    prog = s.prog('Am F C G', bars=2)
    hook = s.motif(MOTIF).clip(octave=4)
    b = bands.rock_band(s, without=('lead', 'gtr_r'))          # drums, bass, a rhythm guitar, organ; space, master
    s.hall()                                                    # the heroes' hall send
    groove = drums({'kick': 'x.....x.x.......', 'snare': '....x.......x...', 'hat': 'x.x.x.x.x.x.x.x.'}, vel=96)
    for sec in (sax_sec, gtr_sec):
        b.drums.loop(groove, sec, vel=0.8).play(crash(), sec)
        b.bass.loop(prog.bass('pulse', rate='1/8', low='E1', vel=84), sec)
        b.keys.loop(prog.block(voicing='spread', register=('C3', 'C5'), vel=66), sec)
        b.gtr_l.loop(prog.block(voicing='close', register=('E3', 'E4'), rhythm='x..x..x.', vel=70)
                     .strum(ms=12, bpm=s.tempo), sec)
    sax = s.track('sax', 'layered/hero_sax', gain_db=1)
    lead = s.track('lead', 'layered/hero_guitar_heavy', gain_db=1)
    p1 = soloist.solo(s, sax, hornist.vocabulary('sax', style='hero'), at=sax_sec, prog=prog, motif=hook, seed=4)
    p2 = soloist.solo(s, lead, gtr.vocabulary('rock'), at=gtr_sec, prog=prog, motif=hook, seed=4)
    print('sax:', p1.summary())
    print('guitar:', p2.summary())
    return s
