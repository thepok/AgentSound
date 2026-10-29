"""The ORCHESTRATOR: a polyphonic score of lines with musical FUNCTIONS (independent of instruments and of the
composer that wrote them) -> parts for the sections of an orchestra, by data tables - docs/ORCHESTRA_ENDLESS.md.

    from agentsound.bandlib import orchestra as orch
    sc = orch.OrchScore('Title', key='D major', meter=4, tempo=72)
    b = sc.block('A1', start=0, length=32, chart=[(0, 4, 'D'), (4, 4, 'Bm7'), ...], texture='solo_pad')
    b.add(orch.Line('melody', notes))                      # (start, dur, pitch) in song beats, a natural register
    b.add(orch.Line('harmony', h1, voice='h1')); ...       # real parts: h1 (top) .. hN
    plan = orch.orchestrate(sc, orch.role_table('film_orchestra'), pick=my_pick)   # -> Orchestration
    plan.parts                                             # [Part(role, block, function, notes, art, off, line)]

THE SCORE (OrchScore / Block / Line): blocks are sections (name, start, length, chord timeline, key, dynamics marks,
peak / frame flags, the texture), each with Lines - function (FUNCTIONS), notes with concrete pitches, a voice name
for real parts, `of` for a doubling. Any composer writes into it: the endless lead-sheet composer (endless/orchestra.py),
later a counterpoint / fugue / development composer (function 'voice').

THE ORCHESTRATION PLANS (TEXTURES): per texture type {function: slot}; a slot names the role(s) that carry the
function - 'pick' {role: weight} (one, drawn; weights x orch.ROLE_TRAITS[role]['functions'][function]) or 'voices'
(role, ...) top-down for the function's real parts (more voices than roles: the last role plays them divisi) - and
'n' (voices to write), 'art', 'off' (velocity offset over FUNCTIONS'), 'shift' (semitones before fitting), 'double'
{role: (interval, chance)}, 'chance' (the function is present at all), 'figure' (how the composer writes it). A
'colour' slot may be a list (harp arpeggios + a timpani roll ...). Texture keys: 'peak' (only on a peak block),
'size' ('full': needs the brass), 'light' (a thin texture: intros, codas).

THE RULES (RULES, budgets / distributions): ranges (a line moves by whole octaves toward the role's sweet spot; a
note still outside its range is folded and counted - metrics range_out), spacing (the harmony's adjacent upper voices
within `spacing` semitones, no third under `low_third`), doublings by register, a role carries one function per
block (a taken role gives its voice to a free partner), the colour change at boundaries (the melody's role differs
from the block before with `colour_change`), the tutti reserved for peak blocks (at most `tutti_blocks`), the coda
thin (a 'light' texture), the texture not twice running (`texture_change`).

metrics(score) measures any orch.Score (endless or hand-written): range faults, the melody's sweet-spot share,
spacing, low thirds, the melody's margin, colour changes, the tutti share, the coda's thinning, roles per bar,
doublings, the climax place and the loudness range (note energy).
"""
from __future__ import annotations

import math
import statistics as st
from dataclasses import dataclass, field

from ..theory import ComposeError, note as _note

__all__ = ['FUNCTIONS', 'TEXTURES', 'RULES', 'Line', 'Block', 'OrchScore', 'Part', 'Orchestration', 'plan_blocks',
           'orchestrate', 'metrics', 'needs']

_EPS = 1e-6

FUNCTIONS = {
    # off: the velocity offset under the dynamics map (the balance ranks: the melody on top); art: the default
    # articulation; line: written as a LINE (orch.Score's balance keeps the accompaniment under it)
    'melody': {'off': 4.0, 'art': 'sustain', 'line': True},
    'counter': {'off': -4.0, 'art': 'sustain', 'line': True},
    'voice': {'off': 0.0, 'art': 'sustain', 'line': True},
    'doubling': {'off': -4.0, 'art': None, 'line': True},
    'harmony': {'off': -10.0, 'art': 'sustain', 'line': False},
    'inner': {'off': -8.0, 'art': 'sustain', 'line': False},
    'bass': {'off': -5.0, 'art': 'sustain', 'line': False},
    'ostinato': {'off': -8.0, 'art': 'staccato', 'line': False},
    'colour': {'off': -8.0, 'art': 'sustain', 'line': False},
    'pedal': {'off': -10.0, 'art': 'sustain', 'line': False},
    'figuration': {'off': -5.0, 'art': 'sustain', 'line': False},
}
"""The musical functions a line can have (docs/ORCHESTRA_ENDLESS.md): melody, counter (a counter-melody), voice (an
equal contrapuntal voice: fugue / canon), doubling (of another line: `of`), harmony (sustained chord voices: the pad),
inner (moving inner voices), bass, ostinato (a rhythmic repeated figure), colour (figuration, sparkle, a roll),
pedal (a held pedal point), figuration (running figuration that carries the music: moto perpetuo, wave figures,
arpeggio streams - the symphonic composer's flutes / violins in 16ths, endless/symphony.py)."""
ORDER = ('melody', 'voice', 'counter', 'bass', 'figuration', 'harmony', 'inner', 'ostinato', 'colour', 'pedal')
"""The order the orchestrator seats the functions in (a role taken by an earlier one is not given to a later one)."""

_STR3 = ('violins2', 'violas', 'cellos')
TEXTURES = {
    # a hushed string pad; the melody (when the block has one) on the violins or a soft wind; a harp now and then
    'strings_pad': {
        'melody': {'pick': {'violins1': 1.0, 'clarinets': 0.6, 'flutes': 0.5, 'oboes': 0.4}},
        'harmony': {'voices': _STR3, 'n': 3},
        'bass': {'pick': {'basses': 1.0}, 'off': -4.0},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.35, 'figure': 'arp'}],
        'light': True},
    # a solo (oboe, flute, clarinet, horn, cello) over the strings' pad
    'solo_pad': {
        'melody': {'pick': {'oboes': 1.0, 'flutes': 0.9, 'clarinets': 0.8, 'horns': 0.6, 'cellos': 0.5}},
        'harmony': {'voices': ('violins2', 'violas', 'violas'), 'n': 3},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.6)}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.45, 'figure': 'arp'}],
        'light': True},
    # a solo over harp arpeggios, a soft horn / clarinet pad, the cellos' bass
    'harp_solo': {
        'melody': {'pick': {'flutes': 1.0, 'oboes': 0.8, 'clarinets': 0.7, 'violins1': 0.5}},
        'colour': [{'pick': {'harp': 1.0}, 'figure': 'arp'}],
        'harmony': {'voices': ('horns', 'horns'), 'n': 2, 'off': -4.0},
        'bass': {'pick': {'cellos': 1.0}, 'off': -2.0},
        'light': True},
    # the violins sing, violas / cellos hold the harmony, the basses under them; a counter-melody sometimes
    'strings_melody': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6), 'flutes': (12, 0.35),
                                                         'oboes': (0, 0.2)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'violas': 0.4}, 'chance': 0.4,
                    'double': {'bassoons': (0, 0.3)}},
        'harmony': {'voices': ('violins2', 'violas', 'cellos'), 'n': 3},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.4, 'figure': 'arp'}]},
    # the cellos' tenor theme under a high string pad
    'cello_theme': {
        'melody': {'pick': {'cellos': 1.0, 'horns': 0.5}, 'double': {'bassoons': (0, 0.35), 'horns': (0, 0.35),
                                                                    'violas': (0, 0.25)}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'off': -2.0},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.5, 'figure': 'arp'}]},
    # a woodwind choir: the tune on top, clarinets / oboes inside, the bassoon's bass
    'chorale_winds': {
        'melody': {'pick': {'flutes': 1.0, 'oboes': 0.9, 'clarinets': 0.5}, 'double': {'clarinets': (-12, 0.3)}},
        'harmony': {'voices': ('oboes', 'clarinets', 'clarinets'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'bassoons': 1.0}, 'double': {'basses': (-12, 0.4)}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.3, 'figure': 'arp'}],
        'light': True},
    # the theme with a counter-melody: violins / a wind above, cellos / horns answering
    'counter_strings': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.6, 'flutes': 0.6}, 'double': {'violins2': (-12, 0.4),
                                                                                      'flutes': (12, 0.3),
                                                                                      'clarinets': (0, 0.3)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.9, 'violas': 0.4}, 'double': {'bassoons': (0, 0.4)}},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2},
        'bass': {'pick': {'basses': 1.0}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.3, 'figure': 'arp'}]},
    # the strings drive in 8ths, the horns (or violins / cellos) carry the tune, a timpani roll into the next block
    'horn_ostinato': {
        'melody': {'pick': {'horns': 1.0, 'violins1': 0.7, 'cellos': 0.5}, 'double': {'cellos': (0, 0.25),
                                                                                       'violins1': (12, 0.4)}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'pulse8'},
        'harmony': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.8)}},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}]},
    # THE climax: violins in octaves, flutes on top, horns under, brass harmony, the basses' octaves, timpani, a crash
    'tutti': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.9), 'flutes': (12, 0.8),
                                                         'horns': (-12, 0.7), 'oboes': (0, 0.4)}},
        'harmony': {'voices': ('trumpets', 'trombones', 'trombones'), 'n': 3, 'off': -6.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.6), 'bassoons': (0, 0.6)}},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'}, {'pick': {'percussion': 1.0}, 'figure': 'crash'},
                   {'pick': {'choir': 1.0}, 'chance': 0.5, 'figure': 'aah'}],
        'peak': True, 'size': 'full'},
    # the lyrical climax: the strings' unison octaves, horns holding the harmony, woodwinds doubling, harp sweeps
    'tutti_lyrical': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.9), 'cellos': (-24, 0.5),
                                                         'flutes': (12, 0.8), 'oboes': (0, 0.4),
                                                         'clarinets': (-12, 0.4), 'trumpets': (0, 0.3)}},
        'counter': {'pick': {'horns': 1.0, 'cellos': 0.7}, 'chance': 0.6},   # (r2: four octaves of one line, no
        'harmony': {'voices': ('horns', 'horns', 'violas'), 'n': 3, 'off': -4.0},      # counter-line at the peak)
        'inner': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'bassoons': (12, 0.5)}},
        'colour': [{'pick': {'harp': 1.0}, 'figure': 'arp'}, {'pick': {'timpani': 1.0}, 'chance': 0.6,
                                                              'figure': 'roll_end'},
                   {'pick': {'choir': 1.0}, 'chance': 0.4, 'figure': 'aah'}],
        'peak': True},
}
"""The orchestration plans of the film / new-age vocabulary (the module docstring has the slot keys)."""

_SYM_BASS = {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}}
TEXTURES.update({
    # THE SYMPHONIC VOCABULARY (endless/symphony.py: a motto that drives and is developed, running figuration,
    # sudden contrasts - HUMAN_FEEDBACK 2026-10-16). Slot keys as above, plus 'enter' / 'leave' {role: fraction of
    # the block, or {fraction: weight} drawn} - the role (or the doubling) plays from / until that share of the block,
    # snapped to a bar (the texture's density changes inside the block: entries and drop-outs by phrase), and the
    # texture key 'theme': the function the block's theme line takes ('melody' default; 'bass': the motto in the low
    # strings). The composer reads a slot's 'figure' (how it writes the function).
    # the motto stated boldly in unison / octaves (no harmony): strings, winds and horns on one line, the bass under it
    'motto_unison': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (0, 1.0), 'violas': (-12, 0.9),
                                                         'flutes': (12, 0.7), 'oboes': (0, 0.5),
                                                         'clarinets': (-12, 0.6), 'horns': (-12, 0.7)}},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'bassoons': (0, 0.7), 'tuba': (-12, 0.4)},
                 'figure': 'theme'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.7, 'figure': 'motto_timp'}]},
    # the motto as a brass fanfare over string tremolo
    'motto_brass': {
        'melody': {'pick': {'trumpets': 1.0, 'horns': 0.8}, 'double': {'horns': (-12, 0.7), 'trumpets': (0, 0.4)}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo', 'off': -2.0},
        'inner': {'voices': ('trombones', 'trombones'), 'n': 2, 'off': -2.0},
        'bass': dict(_SYM_BASS, figure='pump'),
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash'}],
        'size': 'full'},
    # the theme with drive: the violins (a wind on top) over the strings' repeated 8ths, the winds' harmony entering
    'drive_strings': {
        'melody': {'pick': {'violins1': 1.0, 'flutes': 0.4, 'oboes': 0.3}, 'double': {'flutes': (12, 0.4),
                                                                                       'oboes': (0, 0.3)},
                   'enter': {'flutes': {0.5: 1.0, 0.0: 0.4}, 'oboes': {0.5: 1.0, 0.0: 0.4}}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive'},
        'harmony': {'voices': ('clarinets', 'bassoons', 'horns'), 'n': 3, 'off': -3.0,
                    'enter': {'horns': {0.5: 1.0, 0.0: 0.5}, 'clarinets': {0.25: 0.6, 0.0: 1.0}}},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato'),
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'hits'}]},
    # the theme in a wind / the horns over running strings (16ths / triplets)
    'running_strings': {
        'melody': {'pick': {'oboes': 1.0, 'flutes': 0.9, 'clarinets': 0.8, 'horns': 0.8},
                   'double': {'clarinets': (-12, 0.3), 'flutes': (12, 0.3)}},
        'figuration': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6)}, 'art': 'spiccato',
                       'figure': 'run', 'enter': {'violins2': {0.5: 1.0, 0.0: 0.6}}},
        'harmony': {'voices': ('violas', 'violas'), 'n': 2, 'off': -2.0},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato')},
    # the Moldau principle: two flutes in flowing figuration, the clarinets join, a plucked bass, the harp
    'river': {
        'melody': {'pick': {'horns': 1.0, 'oboes': 0.5}},
        # (round o6 - o5's judges: "flutes in 16th thirds for 12-16 bars": the flutes hand the stream to the
        # clarinets in a long block)
        'figuration': {'pick': {'flutes': 1.0}, 'double': {'clarinets': (-12, 1.0)}, 'figure': 'wave',
                       'enter': {'clarinets': {0.5: 1.0, 0.25: 0.5}}, 'leave': {'flutes': {0.75: 1.0, 0.625: 0.6}}},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'double': {'cellos': (12, 0.7)},
                 'enter': {'basses': {0.25: 1.0, 0.0: 0.5}, 'cellos': {0.5: 1.0, 0.75: 0.5}}, 'figure': 'pluck'},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.6, 'figure': 'arp'}],
        'light': True},
    # the theme grows out of the figuration: the strings take the stream, the violins sing over it
    'river_theme': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.4), 'oboes': (0, 0.3)},
                   'enter': {'flutes': {0.5: 1.0}, 'oboes': {0.5: 1.0}}},
        # (round o3: one stream under the theme, not the source's thirds again; round o10 - o9's judges, CKNM: "12 bars
        # of clarinet 16th scale runs, no theme": the stream under the tune and softer, the clarinets rarely on it)
        'figuration': {'pick': {'violins2': 1.0, 'violas': 0.5}, 'double': {'clarinets': (0, 0.15), 'violas': (-12, 0.5)},
                       'figure': 'wave1', 'off': -3.0},
        'harmony': {'voices': ('horns', 'horns'), 'n': 2, 'off': -4.0, 'enter': {'horns': {0.5: 1.0, 0.0: 0.4}}},
        'bass': dict(_SYM_BASS, figure='long'),
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.5, 'figure': 'arp'}]},
    # call and response: the strings call (the motto), the woodwinds / horns answer
    'dialogue': {
        # (round o12 - o11's judges, ARFK 44-59: "the motto buried in the cellos under harp and violin figures": the
        # call on top - the violins or a wind -, the drive entering from the block's middle: the argument first)
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.3, 'clarinets': 0.25}},
        'counter': {'pick': {'oboes': 1.0, 'flutes': 0.9, 'clarinets': 0.9, 'horns': 0.7, 'bassoons': 0.3},
                    'double': {'clarinets': (-12, 0.3)}},
        # (the drive goes on under the dialogue - round q1: a development of held notes stood still)
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive',
                     'enter': {'violins2': {0.5: 1.0, 0.25: 0.6}, 'violas': {0.5: 1.0, 0.25: 0.6}}},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato'),
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.4, 'figure': 'roll_end'}]},
    # the strings call, the brass answer
    'dialogue_brass': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6)}},
        'counter': {'pick': {'horns': 1.0, 'trumpets': 0.6}, 'double': {'trombones': (-12, 0.3)}},
        'ostinato': {'voices': ('violas', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive',
                     'enter': {'violas': {0.5: 1.0, 0.25: 0.6}}},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato'),
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'motto_timp'}],
        'size': 'full'},
    # a fugato: the motto as a subject entering voice by voice, low to high (the basses with the lowest voice)
    'fugato': {
        'voice': {'voices': ('violins1', 'violins2', 'violas', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        # (the fugato builds: the horns' pedal and the timpani roll from its second half - round q1)
        'pedal': {'pick': {'horns': 1.0}, 'enter': {'horns': {0.5: 1.0, 0.25: 0.5}}},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'roll_long', 'enter': {'timpani': {0.5: 1.0, 0.75: 0.6}}}]},
    # (round o19b, symphony.FUGUE) the fugato's four real voices over the choirs, top-down - an entry in every
    # register and colour; the basses double the bass voice from its entry (the 'bass' line the composer writes)
    'fugue_mixed': {
        'voice': {'voices': ('violins1', 'oboes', 'violas', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'}},
    'fugue_horn': {
        'voice': {'voices': ('violins1', 'clarinets', 'horns', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'}},
    'fugue_reeds': {
        'voice': {'voices': ('oboes', 'violins2', 'clarinets', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'}},
    # (round o21, symphony.FUGUE v2) the same choirs, the exposition never one voice alone: the entry's tonic held
    # under it until the bass voice enters ('pedal'), a soft string pad until the third entry (the composer trims
    # the 'harmony'), the counter-subject doubled in a colour of its own ('counter')
    'fugue2_mixed': {
        'voice': {'voices': ('violins1', 'oboes', 'violas', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'pedal': {'pick': {'horns': 1.0}},
        'harmony': {'voices': ('violins2', 'violins2'), 'n': 2, 'off': -2.0},
        'counter': {'pick': {'clarinets': 1.0, 'bassoons': 0.7}}},
    'fugue2_horn': {
        'voice': {'voices': ('violins1', 'clarinets', 'horns', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'pedal': {'pick': {'bassoons': 1.0}},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2, 'off': -2.0},
        'counter': {'pick': {'oboes': 1.0, 'flutes': 0.6}}},
    'fugue2_reeds': {
        'voice': {'voices': ('oboes', 'violins2', 'clarinets', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'pedal': {'pick': {'horns': 1.0}},
        'harmony': {'voices': ('violas', 'violas'), 'n': 2, 'off': -2.0},
        'counter': {'pick': {'bassoons': 1.0, 'violins1': 0.6}}},
    # (round o21) the fast feels' fugato over the dance's accompaniment: the strings' / winds' staccato chords on
    # under every entry
    'fugue2_dance': {
        'voice': {'voices': ('violins1', 'clarinets', 'bassoons', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive', 'off': 2.0},
        'pedal': {'pick': {'horns': 1.0}},
        'counter': {'pick': {'oboes': 1.0}}},
    'fugue2_dance_winds': {
        'voice': {'voices': ('flutes', 'oboes', 'clarinets', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive', 'off': 2.0},
        'pedal': {'pick': {'horns': 1.0}},
        'counter': {'pick': {'bassoons': 1.0}}},
    # the woodwinds' fugato over the strings' tremolo
    'fugato_winds': {
        'voice': {'voices': ('flutes', 'oboes', 'clarinets', 'bassoons'), 'n': 4},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'tremolo', 'off': -4.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.7)}, 'figure': 'low_voice'}},
    # the build: string tremolo over a pedal, the motto's fragments rising in the winds / horns, the brass entering
    'tremolo_build': {
        'melody': {'pick': {'horns': 1.0, 'clarinets': 0.8, 'oboes': 0.6, 'flutes': 0.6},
                   'double': {'flutes': (12, 0.5), 'trumpets': (0, 0.6), 'oboes': (0, 0.4)},
                   'enter': {'trumpets': {0.5: 1.0, 0.75: 0.6}, 'flutes': {0.25: 1.0, 0.5: 0.6}}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo'},
        'pedal': {'pick': {'basses': 1.0}, 'art': 'tremolo', 'double': {'cellos': (12, 0.8)}},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -3.0,
                  'enter': {'trombones': {0.5: 1.0, 0.75: 0.6}}},
        # (round o11 - the masterpiece panel: the retransition's head answered in imitation over the pedal)
        'counter': {'pick': {'clarinets': 1.0, 'oboes': 0.8, 'violas': 0.5}},
        # (round o3: the 12-32 beat timpani pedal under every build was the judges' first tell - a roll into the
        # climax's downbeat only, the cymbal swell now and then)
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'roll_end'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.3, 'figure': 'swell_cym'}]},
    # the lyrical theme: a woodwind (or horn, cello) solo over flowing strings, the harp
    'cantabile': {
        'melody': {'pick': {'oboes': 1.0, 'clarinets': 0.9, 'flutes': 0.8, 'horns': 0.5, 'cellos': 0.5}},
        # (round o5 - o4's judges: "thin middles: two- or three-voice stretches need a counter-line")
        'counter': {'pick': {'horns': 1.0, 'cellos': 0.8, 'bassoons': 0.6, 'violas': 0.5}, 'chance': 0.85},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'sustain', 'figure': 'arp'},
        'bass': {'pick': {'cellos': 1.0, 'basses': 0.4}, 'double': {'basses': (-12, 0.5)}, 'figure': 'long'},
        'harmony': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -4.0, 'chance': 0.6,
                    'enter': {'clarinets': {0.5: 1.0, 0.0: 0.5}, 'bassoons': {0.5: 1.0, 0.0: 0.5}}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.6, 'figure': 'arp'}],
        'light': True},
    # the lyrical theme sung by the violins, a counter-melody in the cellos / horns, flowing violas
    'cantabile_strings': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.3)}, 'enter': {'flutes': {0.5: 1.0}}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8}, 'double': {'bassoons': (0, 0.3)}},
        'ostinato': {'voices': ('violas', 'violins2'), 'n': 2, 'art': 'sustain', 'figure': 'arp'},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'long'},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.5, 'figure': 'arp'}]},
    # a non-peak tutti with drive: the theme in octaves, the strings' 8ths, horns and winds holding
    'tutti_drive': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.8), 'oboes': (0, 0.5),
                                                         'trumpets': (0, 0.3)}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive'},
        'harmony': {'voices': ('horns', 'horns'), 'n': 2, 'off': -2.0},
        'inner': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.4)}, 'figure': 'pump'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'}]},
    # the motto in the low strings, the violins' running figuration over it
    'motto_bass': {
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'bassoons': (0, 0.6), 'horns': (0, 0.4)},
                 'figure': 'theme'},
        'figuration': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6), 'flutes': (12, 0.3)},
                       'art': 'spiccato', 'figure': 'run'},
        'harmony': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -3.0},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'motto_timp'}],
        'theme': 'bass'},
    # the mysterious opening: hushed string tremolo, the motto in the low strings, a timpani roll
    'mist': {
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.8)}, 'figure': 'theme'},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo', 'off': -4.0},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.7, 'figure': 'roll_long'}],
        'theme': 'bass', 'light': True},
    # THE climax: the theme in octaves, brass harmony, a horn counter-line, the full bass, timpani, a crash
    'tutti_symphonic': {
        # (round o3: not the whole tutti on the tune - the oboes and trumpets mostly keep the inner parts; round o7 -
        # o6's judges: "the motto stacked in octaves of tutti unison": the line in two colours - the violins with the
        # flutes an octave over them, now and then the oboes -, the brass's harmony under it, the inner strings moving)
        # (round o8 - o7's judges: "the climax without the motto in the brass": the trumpets with the violins on it)
        # (the trumpets where the tune lies over their G4 floor, else the horns an octave under it)
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.5), 'oboes': (0, 0.2),
                                                         'trumpets': (0, 0.75), 'horns': (-12, 0.6),
                                                         'violins2': (-12, 0.25)}},
        'counter': {'pick': {'horns': 1.0, 'cellos': 0.5}, 'double': {'clarinets': (0, 0.3)}},
        'harmony': {'voices': ('trumpets', 'trombones', 'trombones'), 'n': 3, 'off': -4.0},
        'inner': {'voices': ('violins2', 'violas'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.8), 'bassoons': (0, 0.5)},
                 'figure': 'pump'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.5, 'figure': 'crash'}],
        'peak': True, 'size': 'full'},
    # a brass chorale (the motto augmented), the violins' figuration over it
    'chorale_brass': {
        'melody': {'pick': {'trumpets': 1.0, 'horns': 0.6}, 'double': {'horns': (-12, 0.6)}},
        # (round o9 - o8's judges: "the coda as violins1 16th broken chords over a brass chorale, the theme absent",
        # and "a coda thinned to tuba + basses + one violin": the violins sing the motto at its own speed over its
        # augmentation in the brass, the inner strings hold the chord, the 16ths now and then from the second half)
        'counter': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.35)}},
        'harmony': {'voices': ('horns', 'trombones', 'trombones'), 'n': 3, 'off': -2.0},
        'inner': {'voices': ('violins2', 'violas'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'tuba': 1.0, 'trombones': 0.3}, 'double': {'basses': (0, 0.8), 'cellos': (12, 0.6)},
                 'figure': 'long'},
        'figuration': {'pick': {'violins2': 1.0}, 'double': {'violas': (-12, 0.5)}, 'art': 'spiccato',
                       'figure': 'run', 'chance': 0.35, 'enter': {'violins2': {0.625: 1.0, 0.75: 0.5},
                                                                    'violas': {0.75: 1.0}}},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.4, 'figure': 'roll_long'}],   # (round o6: 0.7)
        'size': 'full'},
    # the closing strokes: tutti chords in the motto's rhythm, timpani, the crash on the last
    'hammer': {
        # (round o7: the tune in two colours, not five - o6's coda stacked it in flutes, oboes, violins and the bass)
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.7), 'oboes': (0, 0.3),
                                                         'trumpets': (0, 0.45), 'violins2': (-12, 0.3)}},
        'harmony': {'voices': ('horns', 'horns', 'violas'), 'n': 3, 'off': -2.0},
        'inner': {'voices': ('clarinets', 'trombones'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7),
                                                     'bassoons': (0, 0.6)}, 'figure': 'theme'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'}]},
    # the dissolving ending: a solo wind with the motto's last fragments over hushed strings
    'dissolve': {
        'melody': {'pick': {'clarinets': 1.0, 'oboes': 0.8, 'flutes': 0.7, 'horns': 0.6}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.7, 'bassoons': 0.5}, 'chance': 0.6},
        'harmony': {'voices': ('violins2', 'violas', 'cellos'), 'n': 3, 'off': -2.0},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'long'},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.4, 'figure': 'arp'},
                   {'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}],
        'light': True},
    # (round o2: the set's climax / build types - symphony.CLIMAXES / BUILDS; a set is not one brass climax after a
    # tremolo build in every piece)
    # the string apotheosis: the theme in three octaves of strings, the horns' harmony, harp sweeps, a timpani roll
    'apotheosis_strings': {
        # (round o5 - o4's orchestrators: "every instrument on the melody at the climax": the violas / cellos sing a
        # counter-line instead of the tune two octaves down)
        # (round o8: the horns an octave under the violins - the motto in the brass at the climax)
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.5), 'flutes': (12, 0.5),
                                                         'horns': (-12, 0.9)}},
        'counter': {'pick': {'cellos': 1.0, 'violas': 0.8}},
        'harmony': {'voices': ('horns', 'horns', 'clarinets'), 'n': 3, 'off': -3.0},
        'inner': {'voices': ('bassoons', 'bassoons'), 'n': 2, 'off': -4.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'cellos': (12, 0.4)}, 'figure': 'long'},
        # (round o6 - o5's judges, one plan in both codes: "the harp-arpeggio apotheosis": the harp now and then,
        # the inner strings running under the tune instead)
        # (round o9: the run rarer and only from the block's middle - "16ths over the chorale", the climax template)
        'figuration': {'pick': {'violas': 1.0, 'clarinets': 0.5}, 'art': 'spiccato', 'figure': 'run', 'chance': 0.3,
                       'enter': {'violas': {0.625: 1.0, 0.5: 0.4}, 'clarinets': {0.625: 1.0}}},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.3, 'figure': 'arp'},
                   {'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'roll_end'}],
        'peak': True},
    # the chorale climax: the theme over the choir and the brass choir's held harmony, the full bass
    'tutti_chorale': {
        'melody': {'pick': {'violins1': 1.0, 'trumpets': 0.6}, 'double': {'flutes': (12, 0.6), 'violins2': (-12, 0.3),
                                                                         'trumpets': (0, 0.6), 'horns': (-12, 0.7)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.7}, 'chance': 0.8},
        'harmony': {'voices': ('choir', 'trombones', 'trombones'), 'n': 3, 'off': -3.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'roll_long'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash'}],
        'peak': True, 'size': 'full'},
    # (round o8 - o7's judges, the stock build "a cymbal roll, a crash and the choir": the chorale climax without the
    # choir - the brass choir's harmony under the tune)
    'tutti_chorale_brass': {
        'melody': {'pick': {'violins1': 1.0, 'trumpets': 0.6}, 'double': {'flutes': (12, 0.6), 'violins2': (-12, 0.3),
                                                                         'trumpets': (0, 0.6), 'horns': (-12, 0.7)}},
        'counter': {'pick': {'cellos': 1.0, 'violas': 0.6}, 'chance': 0.8},
        'harmony': {'voices': ('horns', 'trombones', 'trombones'), 'n': 3, 'off': -3.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'roll_long'}],
        'peak': True, 'size': 'full'},
    # (round o24, symphony.SHAPE's 'dialogue' climax - o23's judges: "a unison tutti climax in every piece"): the tune
    # in the violins and the woodwinds against the brass choir's own line (the counter: the trumpets, the trombones an
    # octave under), the horns and clarinets holding the harmony, the inner strings moving, the full bass
    'apex_dialogue': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.6), 'oboes': (0, 0.4),
                                                         'violins2': (-12, 0.3)}},
        'counter': {'pick': {'trumpets': 1.0}, 'double': {'trombones': (-12, 0.7)}},
        'harmony': {'voices': ('horns', 'horns', 'clarinets'), 'n': 3, 'off': -4.0},
        'inner': {'voices': ('violas', 'violas'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.8), 'bassoons': (0, 0.5)},
                 'figure': 'pump'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash'}],
        'peak': True, 'size': 'full'},
    # (round o24b, SHAPE2's climax types - o24's set judges: "every climax a marcato tutti with the brass doubling the
    # violins in octaves"): the brass choir's chorale - the tune in the trumpets with the horns an octave under, the
    # trombones and tuba the chord and bass, the strings a tremolo shimmer around it, never on the tune
    'apex_chorale2': {
        'melody': {'pick': {'trumpets': 1.0}, 'double': {'horns': (-12, 0.9)}},
        'harmony': {'voices': ('trombones', 'trombones', 'horns'), 'n': 3, 'off': -2.0},
        'inner': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo', 'off': -5.0},
        'bass': {'pick': {'tuba': 1.0}, 'double': {'basses': (0, 0.9), 'cellos': (12, 0.6)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'roll_long'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash_dry'}],
        'peak': True, 'size': 'full'},
    # the tune low: the cellos, violas and horns sing it under the violins' running figuration, the trombones' chord,
    # the basses and tuba held
    'apex_low': {
        'melody': {'pick': {'cellos': 1.0}, 'double': {'horns': (0, 0.9), 'violas': (0, 0.7), 'bassoons': (0, 0.5)}},
        'figuration': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.8), 'flutes': (12, 0.3)},
                       'art': 'spiccato', 'figure': 'run'},
        'harmony': {'voices': ('trombones', 'trombones', 'clarinets'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'tuba': (0, 0.7)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash_dry'}],
        'peak': True, 'size': 'full'},
    # the dialogue without the pumping bass: the violins and woodwinds against the trumpets' own line, the bass held
    'apex_dialogue2': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.6), 'oboes': (0, 0.4),
                                                         'violins2': (-12, 0.3)}},
        'counter': {'pick': {'trumpets': 1.0}, 'double': {'trombones': (-12, 0.8), 'horns': (0, 0.5)}},
        'harmony': {'voices': ('horns', 'clarinets', 'clarinets'), 'n': 3, 'off': -4.0},
        'inner': {'voices': ('violas', 'violas'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.8)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash'}],
        'peak': True, 'size': 'full'},
    # (round o25, SHAPE3 - o24b's judges: "the chorale climax homorhythmic brass on stepwise lines"): the brass choir's
    # chorale with the strings hammering the motto's rhythm around it and a walking bass under it
    'apex_chorale3': {
        'melody': {'pick': {'trumpets': 1.0}, 'double': {'horns': (-12, 0.9), 'flutes': (12, 0.4)}},
        'harmony': {'voices': ('trombones', 'trombones', 'horns'), 'n': 3, 'off': -2.0},
        'ostinato': {'voices': ('violins1', 'violins2'), 'n': 2, 'figure': 'motto', 'off': -3.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -4.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.8)}, 'figure': 'walk'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash_dry'}],
        'peak': True, 'size': 'full'},
    # the cut ending's hammered chords in the motto's rhythm: the tune on top, the horns and trombones striking the
    # motto's rhythm, the bass with the tune's rhythm, the timpani on the motto
    'hammer_motto': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.6), 'trumpets': (0, 0.6),
                                                         'violins2': (-12, 0.4)}},
        'ostinato': {'voices': ('horns', 'trombones'), 'n': 2, 'figure': 'motto', 'off': -1.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7),
                                                     'bassoons': (0, 0.6)}, 'figure': 'theme'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.5, 'figure': 'crash'}]},
    # the quiet climax: the theme high in the violins and the flute over hushed tremolo, the harp
    'quiet_climax': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.7), 'violins2': (0, 0.6),
                                                         'horns': (-12, 0.7)}},
        # (round o5: the climax with a counter-line, not only the tune doubled)
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'clarinets': 0.6}, 'chance': 0.9},
        'harmony': {'voices': ('violas', 'cellos', 'violins2'), 'n': 3, 'art': 'tremolo', 'off': -4.0},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'long'},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.4, 'figure': 'arp'},       # (round o6: not always the harp)
                   {'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}],
        'peak': True, 'light': True},
    # the pulse build: the strings' repeated 8ths over a plucked pedal, the motto's fragments in the woodwinds, the
    # horns and the brass entering
    'pulse_build': {
        'melody': {'pick': {'oboes': 1.0, 'flutes': 0.8, 'clarinets': 0.7},
                   'double': {'violins1': (0, 0.7), 'horns': (-12, 0.5)},
                   'enter': {'violins1': {0.5: 1.0, 0.25: 0.5}, 'horns': {0.5: 1.0, 0.75: 0.6}}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive'},
        'pedal': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'double': {'cellos': (12, 0.6)}},
        'inner': {'voices': ('trumpets', 'trombones'), 'n': 2, 'off': -4.0,
                  'enter': {'trumpets': {0.75: 1.0}, 'trombones': {0.5: 1.0, 0.75: 0.6}}},
        # (round o11 - the masterpiece panel: the retransition's head answered in imitation over the pedal)
        'counter': {'pick': {'bassoons': 1.0, 'clarinets': 0.8, 'horns': 0.6}},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp', 'enter': {'timpani': {0.5: 1.0, 0.75: 0.6}}}]},
    # (round o3: the judges heard ONE recipe - the stock build (a timpani pedal, a rising oboe, a cymbal roll), a
    # development that never works the motto, the climax as the theme louder in octaves, the same flute thirds over
    # the harp and the same oboe over the harp. The rows below are the vocabulary each piece draws from: symphony.
    # DEV_TECH / BUILDS / APEX / T2_COLOURS / SOURCES / ENDINGS)
    # the development's polyphony: the motto against itself (stretto, inversion) or against the second theme - two
    # real lines, a sustained harmony under them, the bass; no ostinato (the counterpoint is the motion)
    'dev_poly': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.4, 'clarinets': 0.3}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'clarinets': 0.7, 'bassoons': 0.4, 'violas': 0.5}},
        'harmony': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -4.0, 'chance': 0.7},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'figure': 'pluck'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.3, 'figure': 'motto_timp',
                    'enter': {'timpani': {0.75: 1.0}}}]},
    # the motto in the bass (cellos, basses, bassoons; the trombones from the second half), a counter-line in the
    # winds above, the violins' tremolo
    'dev_bass': {
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'bassoons': (0, 0.7),
                                                     'trombones': (0, 0.5)},
                 'figure': 'theme', 'enter': {'trombones': {0.5: 1.0}}},
        'counter': {'pick': {'oboes': 1.0, 'clarinets': 0.9, 'flutes': 0.7, 'horns': 0.6}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo', 'off': -3.0},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'motto_timp'}],
        'theme': 'bass'},
    # round o17 (symphony.WALK2 - o16's judges: "sections shorter than 8 bars, each with a new colour, read as
    # channel-switching"): the development as one block whose colour GROWS at its middle (a phrase boundary) - the
    # dialogue with the call doubled by the flutes an octave up and the answer by the horns from there, the drive
    # entering by phrase
    'walk_dialogue': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.25}, 'double': {'flutes': (12, 1.0)},
                   'enter': {'flutes': {0.5: 1.0}}},
        'counter': {'pick': {'clarinets': 1.0, 'oboes': 0.9, 'bassoons': 0.3}, 'double': {'horns': (0, 1.0)},
                    'enter': {'horns': {0.5: 1.0}}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive',
                     'enter': {'violins2': {0.25: 1.0, 0.5: 0.5}, 'violas': {0.5: 1.0}}},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato'),
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}]},
    # round o18a (symphony.WALK3): walk_dialogue with the call doubled by the oboes in unison from the middle instead
    # of the flutes an octave up (o17's slot-11 rejects: a flute track too quiet over a low call at p)
    'walk_dialogue3': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.25}, 'double': {'oboes': (0, 1.0)},
                   'enter': {'oboes': {0.5: 1.0}}},
        'counter': {'pick': {'clarinets': 1.0, 'oboes': 0.9, 'bassoons': 0.3}, 'double': {'horns': (0, 1.0)},
                    'enter': {'horns': {0.5: 1.0}}},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'drive',
                     'enter': {'violins2': {0.25: 1.0, 0.5: 0.5}, 'violas': {0.5: 1.0}}},
        'bass': dict(_SYM_BASS, figure='pump', art='staccato'),
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}]},
    # the polyphony (two real lines over a held harmony) with the call doubled by the violins II an octave under and
    # the counter by the bassoons from the middle
    'walk_poly': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.35}, 'double': {'violins2': (-12, 1.0)},
                   'enter': {'violins2': {0.5: 1.0}}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'clarinets': 0.6}, 'double': {'bassoons': (0, 1.0)},
                    'enter': {'bassoons': {0.5: 1.0}}},
        'harmony': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -4.0, 'chance': 0.7},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'figure': 'pluck'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.4, 'figure': 'motto_timp',
                    'enter': {'timpani': {0.75: 1.0}}}]},
    # round o18a (symphony.WALK3 - o17's judges never named v2's two-line stretto): the development's stretto in four
    # real voices - the call in the violins I (the violins II in unison from the middle), the answer in the clarinets
    # / oboes (the horns with it from the middle), the tenor entries in the violas (the harmony's top voice: held
    # chords outside the stretto), the bass entries in the cellos with the basses (arco - the subject in the bass).
    # No flute doubling: a flute an octave over a low call at p was o17's silent track (silent_node / silent_notes)
    'walk_stretto': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.3}, 'double': {'violins2': (0, 1.0)},
                   'enter': {'violins2': {0.5: 1.0}}},
        'counter': {'pick': {'clarinets': 1.0, 'oboes': 0.8}, 'double': {'horns': (0, 0.7)},
                    'enter': {'horns': {0.5: 1.0}}},
        'harmony': {'voices': ('violas', 'bassoons'), 'n': 2, 'off': -1.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.4, 'figure': 'motto_timp',
                    'enter': {'timpani': {0.75: 1.0}}}]},
    # the builds into the climax (symphony.BUILDS), each from the piece's motto:
    # a stretto - the motto's entries closer and closer, strings against winds and horns, over a plucked pedal
    'stretto_build': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.6), 'flutes': (12, 0.4)},
                   'enter': {'violins2': {0.25: 1.0, 0.5: 0.5}, 'flutes': {0.5: 1.0, 0.75: 0.6}}},
        'counter': {'pick': {'horns': 1.0, 'clarinets': 0.8, 'oboes': 0.7}, 'double': {'bassoons': (-12, 0.5)}},
        'harmony': {'voices': ('violas', 'cellos'), 'n': 2, 'off': -4.0},
        'pedal': {'pick': {'basses': 1.0}, 'art': 'pizzicato'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'motto_timp',
                    'enter': {'timpani': {0.75: 1.0, 0.5: 0.5}}}]},
    # the brass calls: the horns call the motto's head, the trumpets / winds answer, closer and closer, over held
    # strings and the dominant in the low strings
    'calls_build': {
        'melody': {'pick': {'horns': 1.0}, 'double': {'trombones': (-12, 0.4)}, 'enter': {'trombones': {0.5: 1.0}}},
        'counter': {'pick': {'trumpets': 1.0, 'oboes': 0.6, 'clarinets': 0.5}, 'double': {'flutes': (12, 0.4)}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'off': -3.0},
        'pedal': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}}},
    # the motto in the bass climbing over a high dominant pedal (the horns), the violins running above
    'bass_build': {
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'bassoons': (0, 0.7), 'tuba': (-12, 0.3)},
                 'figure': 'theme'},
        'figuration': {'pick': {'violins1': 1.0}, 'double': {'violins2': (-12, 0.7)}, 'art': 'spiccato',
                       'figure': 'run', 'enter': {'violins2': {0.5: 1.0}}},
        'pedal': {'pick': {'horns': 1.0, 'clarinets': 0.5}},
        'harmony': {'voices': ('violas', 'oboes'), 'n': 2, 'off': -4.0, 'enter': {'oboes': {0.5: 1.0}}},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'motto_timp',
                    'enter': {'timpani': {0.5: 1.0}}}],
        'theme': 'bass'},
    # subito pianissimo, then the long crescendo: the strings alone, every choir entering in turn
    'subito_build': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'oboes': (0, 0.8), 'flutes': (12, 0.6), 'horns': (-12, 0.6),
                                                         'trumpets': (0, 0.4)},
                   'enter': {'oboes': {0.25: 1.0}, 'flutes': {0.5: 1.0}, 'horns': {0.5: 1.0, 0.75: 0.5},
                             'trumpets': {0.75: 1.0}}},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2, 'off': -2.0},
        'inner': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -3.0, 'enter': {'clarinets': {0.5: 1.0},
                                                                                      'bassoons': {0.5: 1.0}}},
        'pedal': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}},
        # (round o11 - the masterpiece panel: the retransition's head answered in imitation over the pedal)
        'counter': {'pick': {'horns': 1.0, 'trombones': 0.6, 'bassoons': 0.5}},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.5, 'figure': 'roll_end'}]},
    # a fugato that thickens into the climax: the strings' entries a bar apart, the winds doubling as they enter
    'fugato_build': {
        'voice': {'voices': ('violins1', 'violins2', 'violas', 'cellos'), 'n': 4},
        'bass': {'pick': {'basses': 1.0}, 'figure': 'low_voice'},
        'pedal': {'pick': {'horns': 1.0}, 'enter': {'horns': {0.5: 1.0}}},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp', 'enter': {'timpani': {0.75: 1.0}}}]},
    # the climaxes transformed (symphony.APEX): the motto augmented in the brass under the strings' running
    # figuration
    'apex_augment': {
        # (round o6: the trumpets carry the augmented line - a horn melody at F#3-E4 sat under the winds' harmony;
        # round o7 - o6's orchestrators: "the horns and trombones on the trumpets' pitches an octave under: voice the
        # brass as a chord" - the horns and trombones hold the harmony under the trumpets' line)
        'melody': {'pick': {'trumpets': 1.0, 'horns': 0.3}, 'double': {'oboes': (0, 0.3)}},
        # (round o6: the climax's counter-line - the motto / the first theme augmented now carries most climaxes;
        # round o9 - o8's judges, 5 of 8 new climaxes "violin 16th broken chords over a brass chorale, the theme
        # absent": the counter is the motto at its own speed in the violins over its augmentation in the brass
        # (symphony.Writer.apex), the 16ths in the violins II only from the block's middle - the theme heard first)
        'counter': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.4)}},
        'figuration': {'pick': {'violins2': 1.0}, 'double': {'violas': (-12, 0.5)}, 'art': 'spiccato',
                       'figure': 'run', 'enter': {'violins2': {0.625: 1.0, 0.75: 0.6}, 'violas': {0.75: 1.0}}},
        'harmony': {'voices': ('horns', 'horns', 'trombones'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7), 'bassoons': (0, 0.5)},
                 'figure': 'pump'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.5, 'figure': 'crash_dry'}],
        'peak': True, 'size': 'full'},
    # (the chamber orchestra's: the augmented motto in the violins, flutes and horns, the violins II running)
    'apex_augment_strings': {
        # (round o9: the motto at its own speed in the oboes / flutes over its augmentation, the run from the middle)
        'melody': {'pick': {'violins1': 1.0}, 'double': {'oboes': (0, 0.3), 'horns': (-12, 0.9)}},
        'counter': {'pick': {'oboes': 1.0, 'flutes': 0.8}},
        'figuration': {'pick': {'violins2': 1.0}, 'double': {'violas': (-12, 0.6)}, 'art': 'spiccato',
                       'figure': 'run', 'enter': {'violins2': {0.625: 1.0, 0.75: 0.6}, 'violas': {0.75: 1.0}}},
        'harmony': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}, 'figure': 'pump'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'}],
        'peak': True},
    # (round o9 - o8's judges: "the climax as 16ths over a brass chorale, the theme absent", the template shared by 5
    # of 8 pieces) the first theme augmented in the trumpets, the theme itself at its own speed over it in the violins
    # (a canon by augmentation, symphony.Writer.apex 'theme_aug'), the brass's chord, no running figuration
    'apex_theme': {
        'melody': {'pick': {'trumpets': 1.0, 'horns': 0.4}, 'double': {'horns': (-12, 0.5)}},
        'counter': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.45), 'violins2': (-12, 0.4)}},
        'harmony': {'voices': ('horns', 'trombones', 'trombones'), 'n': 3, 'off': -3.0},
        'inner': {'voices': ('violas', 'clarinets'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.6), 'bassoons': (0, 0.5)},
                 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash_dry'}],
        'peak': True, 'size': 'full'},
    # (the chamber orchestra's: the augmented theme in the violins with the horns an octave under, the theme at its
    # own speed over it in the flutes / oboes)
    'apex_theme_strings': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'horns': (-12, 0.9), 'violins2': (-12, 0.4)}},
        'counter': {'pick': {'flutes': 1.0, 'oboes': 0.9}, 'double': {'clarinets': (-12, 0.4)}},
        'harmony': {'voices': ('bassoons', 'bassoons'), 'n': 2, 'off': -3.0},
        'inner': {'voices': ('violas', 'violas'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'}],
        'peak': True},
    # the motto on top - the violins with the trumpets (the horns in a chamber orchestra) - against the second theme
    # in the cellos / horns under it (round o6 - o5's judges: "a new hymn at the climax": the motto transformed is the
    # tune, the second theme the counter-line; it was the second theme on top, the motto under it)
    'apex_combine': {
        # (round o7: the motto in one or two colours - the violins with the trumpets or the flutes -, the brass's
        # chord under it, the second theme's counter-line in the low strings)
        'melody': {'pick': {'violins1': 1.0}, 'double': {'trumpets': (0, 0.75), 'flutes': (12, 0.4),
                                                         'horns': (-12, 0.6)}},
        'counter': {'pick': {'cellos': 1.0, 'horns': 0.8, 'violas': 0.6}, 'double': {'violas': (0, 0.5),
                                                                                     'bassoons': (0, 0.4)}},
        'harmony': {'voices': ('horns', 'trombones', 'trombones'), 'n': 3, 'off': -4.0},
        'inner': {'voices': ('clarinets', 'bassoons'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'tuba': (0, 0.6)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'motto_timp'},
                   {'pick': {'percussion': 1.0}, 'chance': 0.4, 'figure': 'crash_dry'}],
        'peak': True},
    # the openings (symphony.INTRO_KINDS 'solo'): a solo voice states the motto over a held pedal
    'solo_call': {
        'melody': {'pick': {'horns': 1.0, 'clarinets': 0.9, 'oboes': 0.8, 'cellos': 0.7, 'bassoons': 0.4}},
        'pedal': {'pick': {'basses': 1.0, 'cellos': 0.5}},
        'harmony': {'voices': ('violas', 'violins2'), 'n': 2, 'off': -5.0, 'chance': 0.5},
        'light': True},
    # the source in other colours (symphony.SOURCES): one stream in the violins II over a plucked bass, the
    # clarinet's low stream with the bassoon, the violas' murmur under a high violin pedal
    'river_strings': {
        'melody': {'pick': {'clarinets': 1.0, 'horns': 0.7, 'oboes': 0.5}},
        'figuration': {'pick': {'violins2': 1.0}, 'figure': 'wave1'},
        'bass': {'pick': {'cellos': 1.0}, 'art': 'pizzicato', 'double': {'basses': (-12, 0.7)}, 'figure': 'pluck',
                 'enter': {'basses': {0.5: 1.0}}},
        'light': True},
    'river_low': {
        'melody': {'pick': {'flutes': 1.0, 'oboes': 0.8}},
        'figuration': {'pick': {'clarinets': 1.0}, 'double': {'bassoons': (-12, 0.5)}, 'figure': 'wave1',
                       'enter': {'bassoons': {0.5: 1.0}}},
        'harmony': {'voices': ('violins1', 'violins2'), 'n': 2, 'art': 'tremolo', 'off': -6.0, 'chance': 0.6},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'figure': 'pluck'},
        'light': True},
    'river_murmur': {
        'melody': {'pick': {'oboes': 1.0, 'horns': 0.8, 'clarinets': 0.6}},
        'figuration': {'pick': {'violas': 1.0}, 'double': {'cellos': (-12, 0.5)}, 'figure': 'wave1'},
        'pedal': {'pick': {'violins1': 1.0}},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'figure': 'pluck'},
        'light': True},
    # the second theme in other colours (symphony.T2_COLOURS): a horn solo over the strings' held divisi; the
    # cellos' tenor song under a high pad; a wind solo over syncopated strings; the woodwind choir over pizzicato
    # (round o8 - o7's judges: "a 16-bar horn solo over held strings": the inner strings move - broken chords in the
    # violins II / violas under the violins' held pad)
    'cantabile_horn': {
        'melody': {'pick': {'horns': 1.0}},
        'counter': {'pick': {'clarinets': 1.0, 'cellos': 0.7, 'oboes': 0.5}, 'chance': 0.85},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'sustain', 'figure': 'arp'},
        'harmony': {'voices': ('violins1', 'violins1'), 'n': 2, 'off': -6.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.6)}, 'figure': 'long'},
        'light': True},
    'cantabile_cello': {
        'melody': {'pick': {'cellos': 1.0}, 'double': {'bassoons': (0, 0.3)}},
        # (round o9 - o8's judges, TZKN: "a harp ostinato under held strings for 28 bars": a wind's counter-line over
        # the cellos' song; the held strings move - symphony.STATIC)
        'counter': {'pick': {'clarinets': 1.0, 'oboes': 0.8, 'flutes': 0.6}, 'chance': 0.85},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'basses': 1.0}, 'art': 'pizzicato', 'figure': 'pluck'},
        'colour': [{'pick': {'harp': 1.0}, 'chance': 0.25, 'figure': 'arp'}],
        'light': True},
    'cantabile_pulse': {
        'melody': {'pick': {'flutes': 1.0, 'clarinets': 0.9, 'violins1': 0.6}},
        'counter': {'pick': {'horns': 1.0, 'cellos': 0.8, 'bassoons': 0.6}, 'chance': 0.85},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'staccato', 'figure': 'sync'},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.6)}, 'art': 'pizzicato', 'figure': 'pluck'},
        'light': True},
    'cantabile_winds': {
        'melody': {'pick': {'oboes': 1.0, 'flutes': 0.9}},
        'counter': {'pick': {'horns': 1.0, 'violas': 0.8, 'cellos': 0.5}, 'chance': 0.85},
        'harmony': {'voices': ('clarinets', 'clarinets', 'bassoons'), 'n': 3, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.7)}, 'art': 'pizzicato', 'figure': 'pluck'},
        'light': True},
    # (round o23, symphony.TECHNIQUES 'pizz_choir' - only where the technique palette places it: the classic
    # pizzicato texture, a woodwind tune over the whole string choir plucked - the violins II / violas' broken chords,
    # the cellos / basses' plucked bass, the violins I on the beats an octave up: symphony._tech_pass)
    'pizz_choir': {
        'melody': {'pick': {'clarinets': 1.0, 'oboes': 0.9, 'flutes': 0.9}, 'double': {'bassoons': (-12, 0.2)}},
        'counter': {'pick': {'bassoons': 1.0, 'horns': 0.6}, 'chance': 0.5},
        'ostinato': {'voices': ('violins2', 'violas'), 'n': 2, 'art': 'pizzicato', 'figure': 'arp'},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.8)}, 'art': 'pizzicato', 'figure': 'pluck'},
        'light': True},
    # the endings (symphony.ENDINGS): the last chord held under a timpani roll (round o7 - o6's orchestrators: "the
    # tonic voiced upside-down, the bassoon over the clarinet, the trombones on top": the parts top-down in score
    # order, voiced by symphony.END_VOICING)
    'end_held': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.8), 'trumpets': (-12, 0.6)}},
        # (round o5: the held chord voiced - four parts and the violins II in it, not on the tune's octave)
        'harmony': {'voices': ('violins2', 'clarinets', 'violas', 'horns'), 'n': 4, 'off': -2.0},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.6)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.4, 'figure': 'roll_long'}]},    # (round o6: not always)
    # (round o5 - o4's judges: "a bare unison or a stop"; symphony.ENDINGS) the voiced final cadence: the tune on
    # top, four real parts of the chord in the strings / horns / clarinets, two more in the trombones / bassoons, the
    # bass - V7 then the tonic; the roll on the last chord
    'end_cadence': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.8), 'oboes': (0, 0.5), 'trumpets': (-12, 0.5)}},
        'harmony': {'voices': ('violins2', 'clarinets', 'violas', 'horns'), 'n': 4, 'off': -2.0},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -3.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.6)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'roll_end'}]},
    # the same cadence struck (the approach bar's chords cut into strokes), the timpani on the changes
    'end_strokes': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.8), 'oboes': (0, 0.6), 'trumpets': (-12, 0.7)}},
        'harmony': {'voices': ('violins2', 'clarinets', 'violas', 'horns'), 'n': 4, 'off': -1.0},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -2.0},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.7)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'figure': 'hits'}]},
    # the motto's head in unison over V7, the tonic chord voiced by the winds and horns entering on it
    'end_motto': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'violins2': (0, 1.0), 'violas': (-12, 0.8),
                                                         'flutes': (12, 0.6)}},
        'harmony': {'voices': ('oboes', 'clarinets', 'horns', 'bassoons'), 'n': 4, 'off': -2.0,
                    'enter': {'horns': 0.5, 'clarinets': 0.5, 'oboes': 0.5, 'bassoons': 0.5}},
        # (round o8 - o7's orchestrators: "the basses and the tuba both on D3": the cellos' root, the basses and the
        # tuba an octave under it)
        'inner': {'voices': ('trombones', 'trombones'), 'n': 2, 'off': -3.0, 'enter': {'trombones': 0.5}},
        'bass': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0), 'tuba': (-12, 0.5)}, 'figure': 'long'},
        'colour': [{'pick': {'timpani': 1.0}, 'chance': 0.6, 'figure': 'roll_end'}]},
    # round o18b (symphony.SET_PLAN - the judges' template flags: "a timpani dominant pedal before every climax"):
    # the long swell over a moving bass - the strings first, every choir entering in turn, no pedal, no timpani
    'swell_build': {
        'melody': {'pick': {'violins1': 1.0, 'oboes': 0.4}, 'double': {'flutes': (12, 0.7), 'horns': (-12, 0.6),
                                                                      'clarinets': (0, 0.4)},
                   'enter': {'flutes': {0.5: 1.0}, 'horns': {0.5: 1.0, 0.75: 0.6}, 'clarinets': {0.25: 1.0}}},
        'harmony': {'voices': ('violins2', 'violas'), 'n': 2, 'off': -2.0},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -3.0,
                  'enter': {'trombones': {0.75: 1.0, 0.5: 0.5}, 'bassoons': {0.25: 1.0}}},
        'pedal': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 1.0)}},
        'counter': {'pick': {'horns': 1.0, 'clarinets': 0.7, 'violas': 0.4}}},
    # the motto augmented in the trombones (the bass), the strings' tremolo over it, the basses on the frame
    'lowbrass_build': {
        'bass': {'pick': {'trombones': 1.0, 'cellos': 0.05}, 'double': {'tuba': (-12, 0.6), 'bassoons': (0, 0.7),
                                                                         'cellos': (0, 0.5)},
                 'figure': 'theme', 'enter': {'tuba': {0.5: 1.0}}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'art': 'tremolo', 'off': -3.0},
        'pedal': {'pick': {'basses': 1.0}},
        'counter': {'pick': {'horns': 1.0, 'clarinets': 0.7}, 'chance': 0.7},
        'theme': 'bass'},
    # the crisis's collapse: a wind's falling line over hushed strings, the bass falling - no harp, no timpani
    'collapse_build': {
        'melody': {'pick': {'clarinets': 1.0, 'oboes': 0.8, 'horns': 0.6, 'violins1': 0.5}},
        'harmony': {'voices': ('violins1', 'violins2', 'violas'), 'n': 3, 'off': -4.0},
        'pedal': {'pick': {'cellos': 1.0}, 'double': {'basses': (-12, 0.8)}},
        'counter': {'pick': {'bassoons': 1.0, 'cellos': 0.5, 'violas': 0.4}, 'chance': 0.8},
        'light': True},
    # the 'line' ending: end_held with a falling tenor line (the cellos / bassoons) under the held chord
    'end_line': {
        'melody': {'pick': {'violins1': 1.0}, 'double': {'flutes': (12, 0.6), 'oboes': (0, 0.4)}},
        'harmony': {'voices': ('violins2', 'clarinets', 'violas', 'horns'), 'n': 4, 'off': -2.0},
        'counter': {'pick': {'cellos': 1.0, 'bassoons': 0.6, 'horns': 0.3}},
        'inner': {'voices': ('trombones', 'bassoons'), 'n': 2, 'off': -4.0},
        'bass': {'pick': {'basses': 1.0}, 'double': {'tuba': (0, 0.4)}, 'figure': 'long'}},
})
SYMPHONIC = ('motto_unison', 'motto_brass', 'drive_strings', 'running_strings', 'river', 'river_theme', 'dialogue',
             'dialogue_brass', 'fugato', 'fugato_winds', 'tremolo_build', 'cantabile', 'cantabile_strings',
             'tutti_drive', 'motto_bass', 'mist', 'tutti_symphonic', 'chorale_brass', 'hammer', 'dissolve',
             'apotheosis_strings', 'tutti_chorale', 'tutti_chorale_brass', 'quiet_climax', 'pulse_build',
             'dev_poly', 'dev_bass', 'stretto_build', 'calls_build', 'bass_build', 'subito_build', 'fugato_build',
             'apex_augment', 'apex_augment_strings', 'apex_theme', 'apex_theme_strings', 'apex_combine', 'solo_call', 'river_strings', 'river_low', 'river_murmur',
             'cantabile_horn', 'cantabile_cello', 'cantabile_pulse', 'cantabile_winds', 'end_held', 'end_cadence',
             'end_strokes', 'end_motto', 'walk_dialogue', 'walk_poly', 'walk_stretto', 'walk_dialogue3',
             'swell_build', 'lowbrass_build', 'collapse_build', 'end_line', 'fugue_mixed', 'fugue_horn', 'fugue_reeds',
             'fugue2_mixed', 'fugue2_horn', 'fugue2_reeds', 'fugue2_dance', 'fugue2_dance_winds', 'apex_dialogue',
             'apex_chorale2', 'apex_low', 'apex_dialogue2', 'apex_chorale3', 'hammer_motto')
"""The symphonic textures (endless/symphony.py's vocabulary), in TEXTURES after the film / new-age ones."""

RULES = {
    'fit_octaves': (-2, -1, 0, 1, 2),   # a line moves by these octaves (as a whole, per block) toward the sweet spot
    'spacing': 12,                      # the harmony's adjacent upper voices within an octave (close in the treble)
    'low_third': 48,                    # no third (or second) between the two lowest voices under C3 (wide in the bass)
    'colour_change': 0.85,              # the melody's role differs from the block before's (a colour change)
    'texture_change': 0.75,             # the texture differs from the block before's
    'tutti_blocks': 1,                  # tutti textures: peak blocks only, at most this many per piece
    'coda_light': True,                 # the last block (and an intro) plays a 'light' texture
    'doubling_floor': 'C3',             # a doubling of a line never under this (a melody doubled into the bass)
    'bass_floor': True,                 # ... the bass's and the pedal's doublings too (False: the basses' octave
                                        # under the cellos sounds - the symphonic plans; film keeps True, TODO.md)
    'dyn_peak': 1,                      # a tutti block's marks a step louder (mf -> f): the full stack's weight;
    'dyn_light': 0,                     # a light texture's (-1: p -> pp - under p the sections' samples barely move
                                        # in level: a solo's hairpins went flat, the r1 gate's flat_dynamics)
    'power_db': 6.0,                    # a powerful section (ROLE_TRAITS power > 1: brass) under the line plays
                                        # softer: off -= power_db x log2(power) (horns 1.6: -4 dB) - it never covers
    'power_line': 0.0,                  # ... and on a LINE (a melody, its doubling) by this x log2(power): the brass
                                        # a dynamic under the strings (the symphonic plans, round o2: trumpets
                                        # doubling an ff tune sat at velocity 127 - no phrase left, flat_dynamics)
    'idiom': False,                     # the instrument table's idiom (ROLE_TRAITS 'top' / 'run'): a role's range
                                        # ends at its 'top', a line with runs faster than its 'run' goes to another
                                        # role of the slot (the symphonic plans; film keeps the plain ranges)
    'reserve': False,                   # the top register kept for the climax: nothing before the first peak block
                                        # reaches its highest note (_reserve; the symphonic plans, round o3); a
                                        # number: that many semitones under it (round o11: 3 - one summit)
    'reserve_after': False,             # ... and nothing after the last peak block reaches it either (round o11)
    'reserve_lines': None,              # the lines' own margin (round o12: 1 - a tune keeps its register, the
                                        # accompaniment moves under the summit; None: 'reserve')
}
"""The orchestration rules as budgets / distributions (see the module docstring)."""


# ------------------------------------------------------------------------------------------------ the score

@dataclass
class Line:
    """One musical line: function (FUNCTIONS), notes [(start, dur, pitch)] in song beats (concrete pitches; a chord
    stream may hold simultaneous notes), voice (a real part's name: 'h1' .. 'hN' top-down), of (a doubling: the line
    it doubles), art (an articulation wish), meta (the composer's notes: figure, register ...)."""
    function: str
    notes: list
    voice: str = ''
    of: str | None = None
    art: str | None = None
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.function not in FUNCTIONS:
            raise ComposeError(f"Line: function {self.function!r} unknown ({', '.join(FUNCTIONS)})")
        self.notes = sorted((float(a), float(d), int(p)) for a, d, p in self.notes)


@dataclass
class Block:
    """A section of the score: name, start / length (beats), chart [(start, beats, symbol)] in song beats, key, marks
    (dynamics: (beat, level[, 'step'])), peak / frame flags, the texture (TEXTURES), its lines, meta (the drawn
    decisions: lead, counter, colour ...)."""
    name: str
    start: float
    length: float
    chart: list = field(default_factory=list)
    key: str = ''
    marks: list = field(default_factory=list)
    peak: bool = False
    frame: str | None = None
    texture: str | None = None
    lines: list = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def end(self) -> float:
        return self.start + self.length

    def add(self, line: Line) -> Line:
        self.lines.append(line)
        return line

    def get(self, function: str) -> list:
        return [x for x in self.lines if x.function == function]


class OrchScore:
    """A whole piece as blocks of lines (the module docstring): composer-independent, instrument-independent."""

    def __init__(self, title: str = '', key: str = 'C major', meter: int = 4, tempo: float = 80):
        self.title, self.key, self.meter, self.tempo = title, key, int(meter), float(tempo)
        self.blocks: list[Block] = []

    def block(self, name: str, start: float, length: float, chart=(), key: str | None = None, **kw) -> Block:
        if any(b.name == name for b in self.blocks):
            raise ComposeError(f"OrchScore: block {name!r} twice")
        b = Block(name, float(start), float(length), list(chart), key or self.key, **kw)
        self.blocks.append(b)
        return b

    def lines(self, function: str | None = None):
        for b in self.blocks:
            for x in b.lines:
                if function is None or x.function == function:
                    yield b, x

    def to_dict(self) -> dict:
        """A compact summary (tune.json): per block its texture, decisions and lines (function, voice, notes)."""
        return {'key': self.key, 'meter': self.meter, 'blocks': [
            {'name': b.name, 'start': round(b.start, 3), 'length': round(b.length, 3), 'texture': b.texture,
             'peak': b.peak, 'meta': {k: v for k, v in b.meta.items() if isinstance(v, (str, int, float, bool))},
             'lines': [[x.function, x.voice, len(x.notes)] for x in b.lines]} for b in self.blocks]}


def needs(texture: str) -> dict:
    """{function: [slot, ...]} a texture asks the composer to write (a colour slot list kept as a list)."""
    T = TEXTURES[texture]
    return {f: (v if isinstance(v, list) else [v]) for f, v in T.items() if f in FUNCTIONS}


# ------------------------------------------------------------------------------------------------ planning

def _avail(slot: dict, roles) -> dict:
    return {r: w for r, w in (slot.get('pick') or {}).items() if r in roles and w > 0}


def plan_blocks(score: OrchScore, weights: dict, roles, pick, rules: dict | None = None, change=()) -> None:
    """Draw each block's texture and its roles' picks (block.texture, block.meta['lead' / 'counter' / 'colour'])
    under the RULES' budgets: weights {block name: {texture: weight}}; roles: the roles the piece's band has (a
    size); pick(block, key, {choice: weight}) -> a choice (the caller's dice: endless.arrangement.Dice); change: the
    blocks that never take the texture of the block before where they have another (the symphony's joins inside a
    merged section - round o22)."""
    change = set(change or ())
    R = dict(RULES, **(rules or {}))
    roles = set(roles)
    prev_tex = prev_lead = None
    tutti = 0
    last = score.blocks[-1].name if score.blocks else None
    for b in score.blocks:
        w = dict(weights.get(b.name) or {'strings_pad': 1.0})
        for t in list(w):
            T = TEXTURES.get(t)
            if T is None:
                raise ComposeError(f"orchestration: texture {t!r} unknown ({', '.join(TEXTURES)})")
            if (T.get('peak') and (not b.peak or tutti >= R['tutti_blocks'])) or \
                    (T.get('size') == 'full' and not {'trumpets', 'trombones'} <= roles) or \
                    not _avail(needs(t).get('melody', [{}])[0], roles) and 'melody' in T:
                w.pop(t)
            elif R['coda_light'] and b.name == last and not T.get('light'):
                w.pop(t)
        if not w:
            w = {'strings_pad': 1.0}
        if prev_tex in w and len(w) > 1:
            if b.name in change:
                w.pop(prev_tex)
            else:
                w[prev_tex] *= (1.0 - R['texture_change'])
        tex = pick(b.name, 'texture', w)
        b.texture = tex
        if TEXTURES[tex].get('peak'):
            tutti += 1
        T = TEXTURES[tex]
        if 'melody' in T:
            from .orchestra import ROLE_TRAITS
            lw = {r: x * ROLE_TRAITS.get(r, {}).get('functions', {}).get('melody', 0.5)
                  for r, x in _avail(T['melody'], roles).items()}
            if prev_lead in lw and len(lw) > 1:
                lw[prev_lead] *= (1.0 - R['colour_change'])
            b.meta['lead'] = pick(b.name, 'lead', lw)
            prev_lead = b.meta['lead']
        if 'counter' in T:
            s = T['counter']
            cw = {r: x for r, x in _avail(s, roles).items() if r != b.meta.get('lead')}
            on = cw and _chance(pick, b.name, 'counter_on', s.get('chance', 1.0))
            b.meta['counter'] = pick(b.name, 'counter', cw) if on else 'none'
        for i, s in enumerate(needs(tex).get('colour', ())):
            on = _avail(s, roles) and _chance(pick, b.name, f'colour{i}', s.get('chance', 1.0))
            b.meta[f'colour{i}'] = pick(b.name, f'colour{i}_role', _avail(s, roles)) if on else 'none'
        step = R['dyn_peak'] if T.get('peak') else R['dyn_light'] if T.get('light') else 0
        if step:
            b.marks = [(m[0], _step_mark(m[1], step)) + tuple(m[2:]) for m in b.marks]
        prev_tex = tex


_MARKS = ('ppp', 'pp', 'p', 'mp', 'mf', 'f', 'ff', 'fff')


def _step_mark(m, step: int):
    """A dynamic mark `step` marks louder (negative: softer); louder never past f (a mark already over it stays: an
    ff tutti saturates the velocities - the phrase arcs flatten, the r1 gate's flat_dynamics), softer never under ppp;
    anything else (a number) unchanged."""
    if m not in _MARKS:
        return m
    i = _MARKS.index(m)
    return _MARKS[min(i + step, max(i, _MARKS.index('f'))) if step > 0 else max(0, i + step)]


def _chance(pick, block, key, p: float) -> bool:
    if p >= 1.0:
        return True
    if p <= 0.0:
        return False
    return bool(pick(block, key, {1: p, 0: 1.0 - p}))


# ------------------------------------------------------------------------------------------------ orchestrating

@dataclass
class Part:
    """One role's share of one line in one block: notes [(start, dur, pitch)] as fitted, articulation, velocity offset,
    LINE or accompaniment."""
    role: str
    block: str
    function: str
    voice: str
    notes: list
    art: str
    off: float
    line: bool
    shift: int = 0
    sf: tuple = ()                        # beats of sforzandi (the line's meta['sf'] inside the part's notes)


@dataclass
class Orchestration:
    parts: list = field(default_factory=list)
    folded: int = 0                       # notes still outside their role's range after the octave fit (folded)
    notes: int = 0

    def roles(self) -> list:
        seen = []
        for p in self.parts:
            if p.role not in seen:
                seen.append(p.role)
        return seen

    def by_block(self, block: str) -> list:
        return [p for p in self.parts if p.block == block]


def _n(x) -> int:
    return x if isinstance(x, int) else _note(x)


def _fit(notes, rng_: tuple, sweet: tuple, octaves) -> int:
    """The octave shift (semitones) that puts a line best into a role: no note outside the range first, then the most
    notes in the sweet spot, then the smallest move."""
    lo, hi = _n(rng_[0]), _n(rng_[1])
    slo, shi = _n(sweet[0]), _n(sweet[1])
    best = None
    for k in octaves:
        s = 12 * k
        out = sum(1 for _, _, p in notes if not lo <= p + s <= hi)
        swt = sum(1 for _, _, p in notes if slo <= p + s <= shi)
        cost = (out, -swt, abs(k))
        if best is None or cost < best[0]:
            best = (cost, s)
    return best[1] if best else 0


def _free_partner(role: str, function: str, taken: set, roles) -> str | None:
    from .orchestra import ROLE_TRAITS
    for r in ROLE_TRAITS.get(role, {}).get('partners', ()):
        if r in roles and r not in taken and ROLE_TRAITS.get(r, {}).get('functions', {}).get(function):
            return r
    return None


def orchestrate(score: OrchScore, table: dict, pick, rules: dict | None = None) -> Orchestration:
    """The parts of every block's lines (each block's texture and picks drawn: plan_blocks): table = the band's role
    table {role: {'range', 'sweet', ...}} (orch.role_table(preset) or band.info's); pick(block, key, weights) the
    dice for the doublings. Lines move by whole octaves into their role (RULES fit_octaves: the range first, then the
    sweet spot); a role carries one function per block (a voice whose role is taken goes to a free partner, else to
    the voice above's role as divisi); doublings by the slot's 'double' {role: (interval, chance)} on free roles, never
    under RULES doubling_floor."""
    R = dict(RULES, **(rules or {}))
    table = _idiom_table(table, R)
    roles = set(table)
    out = Orchestration()
    floor = _n(R['doubling_floor'])
    tempo = score.tempo
    for b in score.blocks:
        if b.texture is None:
            continue
        taken: set = set()
        for fn in ORDER:
            slots = needs(b.texture).get(fn)
            if not slots:
                continue
            lines = b.get(fn)
            if fn == 'colour':
                for i, s in enumerate(slots):
                    role = b.meta.get(f'colour{i}', 'none')
                    mine = [x for x in lines if x.meta.get('slot') == i]
                    if role == 'none' or role not in roles or not mine:
                        continue
                    for x in mine:
                        _place(out, b, x, role, s, table, R, fit=s.get('figure') not in ('hits', 'roll_end', 'crash'),
                               window=_window(pick, b, s, role, score.meter))
                    taken.add(role)
                continue
            slot = slots[0]
            if not lines:
                continue
            if 'pick' in slot and 'voices' not in slot:
                role = b.meta.get('lead') if fn == 'melody' else b.meta.get('counter') if fn == 'counter' else None
                if role is None:
                    av = {r: w for r, w in _avail(slot, roles).items() if r not in taken}
                    if not av and fn == 'bass':           # (the bass's roles all busy - the cellos sing: the
                        av = {r: _fn_weight(r, fn) for r in sorted(roles)       # free role best at it)
                              if r not in taken and _fn_weight(r, fn) >= 0.8}
                    role = pick(b.name, f'{fn}_role', av) if av else None
                if role in (None, 'none') or role not in roles:
                    continue
                if not _runs_ok(role, [n for x in lines for n in x.notes], tempo, R):
                    # (the idiom: runs too fast for the role - another of the slot's roles takes the line)
                    av = {r: w for r, w in _avail(slot, roles).items() if r not in taken and r != role
                          and _runs_ok(r, [n for x in lines for n in x.notes], tempo, R)}
                    if av:
                        role = pick(b.name, f'{fn}_idiom', av)
                        if fn == 'melody' and b.meta.get('lead'):
                            b.meta['lead'] = role
                        elif fn == 'counter' and b.meta.get('counter'):
                            b.meta['counter'] = role
                    elif fn != 'melody':                     # (no role of the slot plays it: left out - the
                        continue                             # melody is always played)
                if fn in ('melody', 'counter') and not _tune_ok(role, [n for x in lines for n in x.notes], table, R):
                    # (round o5, the idiom: a tune under the role's 'tune' floor - trumpets at Bb3-Eb4 - goes to
                    # another of the slot's roles that plays it in its singing register)
                    av = {r: w for r, w in _avail(slot, roles).items() if r not in taken and r != role
                          and _tune_ok(r, [n for x in lines for n in x.notes], table, R)
                          and _runs_ok(r, [n for x in lines for n in x.notes], tempo, R)}
                    if av:
                        role = pick(b.name, f'{fn}_tune', av)
                        if fn == 'melody' and b.meta.get('lead'):
                            b.meta['lead'] = role
                        elif fn == 'counter' and b.meta.get('counter'):
                            b.meta['counter'] = role
                placed = []
                # (round o5: the melody's own role plays the whole block - a slot's 'enter' for a role it may also
                # double, the flutes of drive_strings, left a scherzo's tune out for half its first theme)
                win = None if fn == 'melody' else _window(pick, b, slot, role, score.meter)
                for x in lines:
                    placed.append(_place(out, b, x, role, slot, table, R, window=win))
                taken.add(role)
                for dr, (iv, ch) in sorted((slot.get('double') or {}).items()):
                    if dr not in roles or dr in taken or not _chance(pick, b.name, f'{fn}_dbl_{dr}', ch):
                        continue
                    for x, sh in zip(lines, placed):          # (the interval from the line as its role plays it:
                        ns = [(a, d, p + sh + iv) for a, d, p in x.notes]   # r1 - 2nd violins over the 1st)
                        if ns and min(p for _, _, p in ns) < floor and (R['bass_floor'] or fn not in ('bass', 'pedal')):
                            continue
                        lo, hi = (_n(v) for v in table[dr]['range'])
                        if R.get('idiom') and fn in ('bass', 'pedal') and 'full' in table[dr]:
                            # (the idiom's floor, round o3: the basses' octave under the cellos jumps up where it
                            # would go under E1 - as a bass player reads it - instead of the doubling dropped)
                            ns = [(a, d, p + 12 if p < lo <= p + 12 else p) for a, d, p in ns]
                        if any(not lo <= p <= hi for _, _, p in ns):      # (a doubling is never folded)
                            continue
                        if not _runs_ok(dr, ns, tempo, R):                 # (nor doubled in runs it cannot play)
                            continue
                        if fn in ('melody', 'counter') and not _tune_ok(dr, ns, table, R, fit=False):
                            continue                                       # (nor under its tune floor)
                        dbl = Line('doubling', ns, voice=x.voice or fn, of=fn, art=x.art, meta=x.meta)
                        _place(out, b, dbl, dr, {'off': slot.get('off', 0.0)}, table, R, fit=False,
                               base=fn, window=_window(pick, b, slot, dr, score.meter))
                    taken.add(dr)
                continue
            # real parts: voices top-down onto the slot's roles
            vroles = []
            for r in slot['voices']:
                if r not in roles or r in taken:
                    r2 = _free_partner(r, fn, taken | set(vroles), roles)
                    r = r2 if r2 is not None else (vroles[-1] if vroles else None)
                vroles.append(r)
            ordered = sorted(lines, key=lambda x: x.voice)
            used: list = []
            for i, x in enumerate(ordered):
                r = vroles[min(i, len(vroles) - 1)] if vroles else None
                if r is not None and not _covers(table[r], x.notes):
                    # the voice lies outside the role: another free role of the function that holds it (a
                    # partner first), else divisi on a role already playing this slot that holds it
                    alts = [q for q in _partners(r) + sorted(roles)
                            if q in roles and q not in taken and q not in vroles and q not in used
                            and _fn_weight(q, fn) and _covers(table[q], x.notes)]
                    alts += [q for q in used if _covers(table[q], x.notes)]
                    r = alts[0] if alts else r
                if r is None:
                    continue
                used.append(r)
                _place(out, b, x, r, slot, table, R, fit=False, window=_window(pick, b, slot, r, score.meter))
            taken.update(r for r in vroles + used if r)
        out.notes = sum(len(p.notes) for p in out.parts)
    if R.get('reserve'):
        _reserve(out, score, table, margin=1 if R['reserve'] is True else int(R['reserve']),
                 after=bool(R.get('reserve_after')), lines=R.get('reserve_lines'))
        out.notes = sum(len(p.notes) for p in out.parts)
    return out


_UNPITCHED = ('percussion', 'timpani')


def _reserve(out: Orchestration, score: OrchScore, table: dict, margin: int = 1, after: bool = False,
             lines: int | None = None) -> None:
    """RULES 'reserve' (round o3's judges: the top register spent before the climax): no part of a block before the
    first peak block reaches the peak blocks' highest note (margin: stays that many semitones under it - round o11,
    the masterpiece panel: "no hierarchy of climaxes", one summit; after: the blocks after the last peak block too, at
    one semitone). A line (melody, counter, voice) that would moves down an octave with its doublings, when it fits its
    role (a doubling that then does not is left out); a doubling of a line that stays is left out; any other part's
    notes that reach it move down an octave. lines (round o12 - o11's judges: "the summit margin lowered the tunes",
    folds 0.79 -> 1.54): the lines' own margin (None: `margin`) - the accompaniment keeps the wide one."""
    peaks = [b.name for b in score.blocks if b.peak]
    if not peaks:
        return
    top = max((p_ for x in out.parts if x.block in peaks and x.role not in _UNPITCHED for _, _, p_ in x.notes),
              default=None)
    if top is None:
        return
    before = set()
    for b in score.blocks:
        if b.name == peaks[0]:
            break
        before.add(b.name)
    lim = {n_: top - max(0, margin - 1) for n_ in before}
    lim_l = {n_: top - max(0, (margin if lines is None else lines) - 1) for n_ in before}
    if after:
        names = [b.name for b in score.blocks]
        for n_ in names[names.index(peaks[-1]) + 1:]:
            lim[n_] = lim_l[n_] = top
    before = set(lim)

    def lo_of(x):
        return _n(table[x.role]['range'][0]) if x.role in table else 0

    def lim_of(x):
        fn_ = x.voice if x.function == 'doubling' else x.function
        return (lim_l if fn_ in ('melody', 'counter', 'voice') else lim)[x.block]

    def high(x):
        return x.block in before and x.role not in _UNPITCHED and x.notes and \
            max(p_ for _, _, p_ in x.notes) >= lim_of(x)
    down = set()                                         # (block, line function) moved down an octave
    for x in out.parts:
        if high(x) and x.function in ('melody', 'counter', 'voice') and \
                min(p_ for _, _, p_ in x.notes) - 12 >= lo_of(x):
            down.add((x.block, x.function))
    keep = []
    for x in out.parts:
        fn = x.voice if x.function == 'doubling' else x.function
        if x.notes and (x.block, fn) in down:
            if min(p_ for _, _, p_ in x.notes) - 12 < lo_of(x):
                if x.function == 'doubling':
                    continue
            else:
                x.notes = [(a, d, p_ - 12) for a, d, p_ in x.notes]
                x.shift -= 12
        if not high(x):
            keep.append(x)
            continue
        if x.function == 'doubling':
            continue
        lo = lo_of(x)                    # (a line that cannot move as a whole: the notes that reach it turn under
        pcs = {p_ % 12 for _, _, p_ in x.notes}       # the top - round o4: folded an octave, a run broke)
        top_ = lim_of(x)
        if margin > 1 and min(p_ for _, _, p_ in x.notes) - 12 >= lo:
            # (round o11: under a wider margin a figure whose few top notes turned broke into octave folds - the
            # whole part down an octave where it fits)
            x.notes = [(a, d, p_ - 12) for a, d, p_ in x.notes]
            x.shift -= 12
            keep.append(x)
            continue

        def turn(p_, lo=lo, pcs=pcs, top_=top_):
            m = 2 * (top_ - 1) - p_
            c = [q for q in range(m - 3, top_) if q % 12 in pcs and q >= lo]
            return min(c, key=lambda q: (abs(q - m), q)) if c else (p_ - 12 if p_ - 12 >= lo else p_)
        x.notes = [(a, d, turn(p_) if p_ >= top_ else p_) for a, d, p_ in x.notes]
        keep.append(x)
    out.parts[:] = keep


def _idiom_table(table: dict, R: dict) -> dict:
    """The role table under RULES 'idiom': a role's range (and sweet spot) ends at its ROLE_TRAITS 'top' (trombones
    Bb4, bassoons C5 - round q1); without the rule the table as given."""
    if not R.get('idiom'):
        return table
    from .orchestra import ROLE_TRAITS
    out = {}
    for r, t in table.items():
        top = ROLE_TRAITS.get(r, {}).get('top')
        if top is not None and _n(top) < _n(t['range'][1]):
            hi = _n(top)
            t = dict(t, range=(t['range'][0], hi), sweet=(t['sweet'][0], min(_n(t['sweet'][1]), hi)),
                     full=t['range'])      # (an octave down under the idiom's top is no range error: not 'folded')
        bot = ROLE_TRAITS.get(r, {}).get('bottom')         # (round o3: the floor - basses E1, flutes G4)
        if bot is not None and _n(bot) > _n(t['range'][0]):
            lo = _n(bot)
            t = dict(t, range=(lo, t['range'][1]), sweet=(max(_n(t['sweet'][0]), lo), t['sweet'][1]),
                     full=t.get('full', t['range']))
        out[r] = t
    return out


def _runs_ok(role: str, notes, tempo: float, R: dict) -> bool:
    """RULES 'idiom': no three onsets in a row closer than the role's ROLE_TRAITS 'run' (seconds at the score's
    tempo; the horns' 0.2 s - no running 16ths)."""
    if not R.get('idiom'):
        return True
    from .orchestra import ROLE_TRAITS
    run = ROLE_TRAITS.get(role, {}).get('run')
    if not run or len(notes) < 4:
        return True
    on = sorted({round(a, 4) for a, _, _ in notes})
    lim = run * tempo / 60.0                         # (in beats)
    fast = [b - a < lim - 1e-6 for a, b in zip(on, on[1:])]
    return not any(fast[i] and fast[i + 1] for i in range(len(fast) - 1))


def _tune_ok(role: str, notes, table: dict, R: dict, fit: bool = True) -> bool:
    """RULES 'idiom' (round o5): a tune (a melody, a counter-line, their doublings) on a role with a ROLE_TRAITS
    'tune' floor stays at or over it - as the line is fitted to the role (fit) or as given; and it fits the role's
    range whole (a melody folded an octave in the middle of a phrase: another role sings it)."""
    if not R.get('idiom') or not notes or role not in table:
        return True
    from .orchestra import ROLE_TRAITS
    lo = ROLE_TRAITS.get(role, {}).get('tune')
    k = _fit(notes, table[role]['range'], table[role]['sweet'], R['fit_octaves']) if fit else 0
    if fit:
        flo, fhi = (_n(v) for v in table[role].get('full', table[role]['range']))
        if not all(flo <= p + k <= fhi for _, _, p in notes):
            return False
    return lo is None or min(p for _, _, p in notes) + k >= _n(lo)


def _covers(t: dict, notes) -> bool:
    lo, hi = (_n(v) for v in t['range'])
    return all(lo <= p <= hi for _, _, p in notes)


def _partners(role) -> list:
    from .orchestra import ROLE_TRAITS
    return list(ROLE_TRAITS.get(role, {}).get('partners', ()))


def _fn_weight(role, fn) -> float:
    from .orchestra import ROLE_TRAITS
    return ROLE_TRAITS.get(role, {}).get('functions', {}).get(fn, 0.0)


def _window(pick, b: Block, slot: dict, role: str, meter: int):
    """The span (start, end) in song beats a role plays of a slot in block b: the slot's 'enter' / 'leave' {role:
    fraction of the block, or {fraction: weight} drawn through pick} snapped to a bar - None: the whole block."""
    span = []
    for k, dflt in (('enter', 0.0), ('leave', 1.0)):
        w = (slot.get(k) or {}).get(role)
        if w is None:
            span.append(dflt)
            continue
        span.append(float(pick(b.name, f'{k}_{role}', w) if isinstance(w, dict) else w))
    if span == [0.0, 1.0]:
        return None
    bars = max(1, int(round(b.length / max(1, meter))))
    a, z = (b.start + round(f * bars) * meter for f in span)
    return a, z


def _place(out: Orchestration, b: Block, x: Line, role: str, slot: dict, table: dict, R: dict, fit: bool = True,
           base: str | None = None, window=None) -> int:
    """A line on a role: shifted (slot 'shift'), fitted by octaves (fit: the whole line), folded where still outside
    the range; window (start, end): only its notes starting inside it (none: nothing placed). -> the shift."""
    t = table[role]
    sh = int(slot.get('shift', 0))
    ns = [(a, d, p + sh) for a, d, p in x.notes]
    if fit and ns:
        k = _fit(ns, t['range'], t['sweet'], R['fit_octaves'])
        ns = [(a, d, p + k) for a, d, p in ns]
        sh += k
    if window is not None:
        ns = [n for n in ns if window[0] - _EPS <= n[0] < window[1] - _EPS]
        if not ns:
            return sh
    lo, hi = (_n(v) for v in t['range'])
    flo, fhi = (_n(v) for v in t.get('full', t['range']))
    folded = []
    for a, d, p in ns:
        q = p
        while q > hi:
            q -= 12
        while q < lo:
            q += 12
        if q != p and not flo <= p <= fhi:
            out.folded += 1
        folded.append((a, d, q))
    F = FUNCTIONS[x.function]
    fn = base or x.function
    art = slot.get('art') or x.art or F['art'] or FUNCTIONS[fn]['art'] or 'sustain'
    if not t.get('arts'):                         # (a role without articulations - harp, percussion, choir: none)
        art = None
    elif art not in t['arts'] and art in ('hit', 'roll'):
        art = None
    line = F['line'] and FUNCTIONS[fn]['line']   # (a doubled bass / harmony stays accompaniment, 2 dB under it)
    off = (F['off'] if line or fn == x.function else FUNCTIONS[fn]['off'] - 2.0) + float(slot.get('off', 0.0))
    if not line or R.get('power_line'):
        from .orchestra import ROLE_TRAITS
        off -= R.get('power_db' if not line else 'power_line', 0.0) * \
            max(0.0, math.log2(ROLE_TRAITS.get(role, {}).get('power', 1.0)))
    sf = tuple(t_ for t_ in x.meta.get('sf', ()) if any(abs(a - t_) < 1e-3 for a, _, _ in folded))
    out.parts.append(Part(role, b.name, x.function, x.voice, folded, art, off, line, sh, sf))
    return sh


# ------------------------------------------------------------------------------------------------ metrics

def _db(v: float) -> float:
    from .ensemble import db_of
    return db_of(max(1, v) / 127.0)


def metrics(sc, sections=None) -> dict:
    """The orchestration measures of an orch.Score (its written parts sc.parts and lines sc.lines, the band's
    ranges; any hand-written piece through orch.Score or an endless one) - {name: number}:
      range_out   notes outside their role's range per 100 notes (before the Score folds them)
      sweet_mel   share of the LINE notes inside their role's sweet spot
      gap_hi      share of beats whose sounding pitches above C4 leave a gap of more than an octave between
                  neighbours (close in the treble)
      low_thirds  share of beats whose two lowest sounding pitches (both under C3) are a 3rd or closer (wide in the bass)
      mel_db      median margin (dB, the lane's scale) of a line note over the loudest accompaniment note sounding with it
      colour_chg  share of section boundaries where the roles carrying the lines change
      tutti       share of bars where 75 %+ of the piece's roles sound
      coda_thin   roles in the last section / the most roles in any section
      roles_bar   mean roles sounding per bar; roles_sd its spread over the bars
      dbl_share   share of line notes doubled (unison / octave) by another role at the same onset
      dbl_low     share of those doublings under C3 (a melody doubled into the bass register)
      peak_x      the loudest 4-bar window's centre (0..1 of the piece, note energy)
      dyn_rng     note-energy range over 2-bar windows (p95 - p10, dB)
      textures    distinct role sets over the sections"""
    info = sc.band.info
    song = sc.song
    secs = list(sections if sections is not None else song.sections)
    meter = float(song.beats_per_bar)
    allp = [(role, n) for role, ns in sc.parts.items() for n in ns]
    if not allp:
        return {}
    total = len(allp)
    rng_ = {r: tuple(_n(x) for x in info.get('range', {}).get(r, ('C0', 'C9'))) for r in sc.parts}
    swt = {r: tuple(_n(x) for x in info.get('sweet', {}).get(r, info.get('range', {}).get(r, ('C0', 'C9'))))
           for r in sc.parts}
    out_n = sum(1 for r, n in allp if not rng_[r][0] <= n[2] <= rng_[r][1])
    lines = {r: s for r, s in sc.lines.items() if s}
    line_notes = [(r, n) for r, n in allp if (round(n[0], 4), n[2]) in lines.get(r, ())]
    sweet = [1 if swt[r][0] <= n[2] <= swt[r][1] else 0 for r, n in line_notes]
    end = max(n[0] + n[1] for _, n in allp)
    # sounding pitches on the beat grid (sustained notes; shorts count on their beat)
    by_beat: dict = {}
    for r, n in allp:
        a, d, p = n[0], max(n[1], 0.25), n[2]
        t = math.ceil(a - _EPS)
        while t < a + d - _EPS:
            by_beat.setdefault(t, set()).add(p)
            t += 1
    gap_hi = low3 = nb = 0
    for t, ps in by_beat.items():
        ps = sorted(ps)
        if len(ps) < 2:
            continue
        nb += 1
        hi_ = [p for p in ps if p >= 60]
        if any(b_ - a_ > 12 for a_, b_ in zip(hi_, hi_[1:])):
            gap_hi += 1
        if ps[0] < 48 and ps[1] < 48 and ps[1] - ps[0] <= 4:
            low3 += 1
    # the melody's margin
    acc = [(n[0], n[0] + n[1], n[3], r) for r, n in allp if (round(n[0], 4), n[2]) not in lines.get(r, ())
           and n[4] not in ('staccato', 'spiccato', 'pizzicato', 'marcato')
           and info.get('kind', {}).get(r, 'sustain') == 'sustain']
    acc.sort()
    margins = []
    import bisect
    starts = [x[0] for x in acc]
    longest = max((e - a for a, e, _, _ in acc), default=0.0)
    for r, n in line_notes:
        k = bisect.bisect_right(starts, n[0] + _EPS)
        vs = [v for a, e, v, r2 in acc[bisect.bisect_left(starts, n[0] - longest - _EPS):k]
              if r2 != r and a <= n[0] + _EPS < e]
        if vs:
            margins.append(_db(n[3]) - _db(max(vs)))
    # roles per section / bar
    def roles_in(a, z):
        return {r for r, n in allp if n[0] < z - _EPS and n[0] + n[1] > a + _EPS}
    sec_roles = [(s.name, roles_in(s.start, s.end), {r for r, n in line_notes if s.start - _EPS <= n[0] < s.end - _EPS})
                 for s in secs if s.length > 0]
    chg = [1 if a[2] and b_[2] and a[2] != b_[2] else 0 for a, b_ in zip(sec_roles, sec_roles[1:])
           if a[2] and b_[2]]
    used = {r for r, _ in allp}
    nbar = max(1, int(math.ceil(end / meter - _EPS)))
    per_bar = [len(roles_in(i * meter, (i + 1) * meter)) for i in range(nbar)]
    sounding = [x for x in per_bar if x]
    tutti = sum(1 for x in sounding if x >= 0.75 * len(used)) / max(1, len(sounding))
    maxr = max((len(x[1]) for x in sec_roles), default=1)
    coda = len(sec_roles[-1][1]) / max(1, maxr) if sec_roles else 1.0
    # doublings
    onset = {}
    for r, n in allp:
        onset.setdefault(round(n[0], 2), []).append((r, n[2]))
    dbl = dlow = 0
    for r, n in line_notes:
        others = [(r2, p) for r2, p in onset.get(round(n[0], 2), ()) if r2 != r and p % 12 == n[2] % 12]
        if others:
            dbl += 1
            if min(p for _, p in others) < 48:
                dlow += 1
    # energy: the climax place and the range
    e_bar = [0.0] * nbar
    for r, n in allp:
        i = min(nbar - 1, int(n[0] // meter))
        e_bar[i] += (n[3] / 127.0) ** 2.5
    db_bar = [10 * math.log10(max(e, 1e-4)) for e in e_bar]
    w4 = [(sum(e_bar[i:i + 4]), i) for i in range(max(1, nbar - 3))]
    peak_i = max(w4)[1] if w4 else 0
    w2 = sorted(10 * math.log10(max(1e-4, sum(e_bar[i:i + 2]) / 2)) for i in range(0, max(1, nbar - 1), 2))
    rngdb = w2[min(len(w2) - 1, int(0.95 * len(w2)))] - w2[int(0.1 * len(w2))] if w2 else 0.0
    sets = {frozenset(x[1]) for x in sec_roles}
    return {
        'range_out': round(100.0 * out_n / total, 2),
        'sweet_mel': round(sum(sweet) / len(sweet), 3) if sweet else None,
        'gap_hi': round(gap_hi / max(1, nb), 3),
        'low_thirds': round(low3 / max(1, nb), 3),
        'mel_db': round(st.median(margins), 2) if margins else None,
        'colour_chg': round(sum(chg) / len(chg), 3) if chg else None,
        'tutti': round(tutti, 3),
        'coda_thin': round(coda, 3),
        'roles_bar': round(st.mean(sounding), 2) if sounding else 0.0,
        'roles_sd': round(st.pstdev(sounding), 2) if len(sounding) > 1 else 0.0,
        'dbl_share': round(dbl / max(1, len(line_notes)), 3),
        'dbl_low': round(dlow / max(1, dbl), 3),
        'peak_x': round((peak_i * meter + 2 * meter) / max(meter, end), 3),
        'dyn_rng': round(rngdb, 1),
        'textures': len(sets),
        'roles_used': len(used),
        'db_bar_sd': round(st.pstdev(db_bar), 2) if len(db_bar) > 1 else 0.0,
    }
