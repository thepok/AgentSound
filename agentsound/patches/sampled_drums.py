"""Sampled drum kits and percussion, round two: multi-mic acoustic kits (rock, pop, jazz, metal, brushes and rods),
single hi-hats / snares / cymbals, hand percussion and the drum machines not yet in sampled_kits.py - all GM-mapped.

  acoustic:  sampled/virtuosity_kit (jazz club, sticks) sampled/naked_kit sampled/drs_kit sampled/salamander_kit
             sampled/muldjord_kit sampled/crocell_kit sampled/aasimonster_kit (metal) sampled/big_rusty_kit (80s arena)
             sampled/unruly_kit (dry garage) sampled/black_pearl_kit sampled/red_zeppelin_kit (70s)
             sampled/mf_natural_kit
             sampled/gogodze_kit (70s lo-fi) sampled/radio_ready_kit (produced pop) sampled/foley_kit (found sounds)
  soft:      sampled/big_rusty_brushes sampled/unruly_brushes sampled/pettinhouse_brushes sampled/hotrod_kit (rods)
             sampled/big_rusty_mallets (film tom rolls, cymbal swells)
  pieces:    sampled/phat_hat (a giant hi-hat, every opening live) sampled/frankensnare (15 snares, keyswitched)
             sampled/cymbals (hats, crashes, rides, rolls, scrapes)
  hand perc: sampled/world_percussion sampled/radio_ready_perc sampled/busk_kit (cajon kit) sampled/cajon
             sampled/bobobo; sampled/virtuosity_kit also carries the whole GM percussion range (54-84)
  machines:  sampled/tr606 sampled/tr626 sampled/tr505 sampled/tr727 (Latin) sampled/cr8000 sampled/rx21 sampled/rz1
             sampled/kpr77 sampled/dr110 sampled/sc_tom sampled/tr808_fischer (every 808 knob setting)

GM keys as in sampled_kits.py: 36 kick, 38 snare, 37 side stick, 40 rimshot / snare 2, 42 / 44 / 46 closed / pedal /
open hat (they choke each other), 41 43 45 47 48 50 toms low -> high, 49 / 57 crash, 51 / 59 ride, 53 bell, 52
china, 55 splash, 54 tambourine, 56 cowbell, 60+ hand percussion; each patch's notes list what it has and what sits
on the extra keys. Kits whose own layout is not GM are re-mapped with keymap= (inst.sfz / inst.kit): the GM keys
sound as expected (toms on 41-50, crash / ride / china on 49 51 52 57 59), the pack's extra articulations (chokes,
swishes, rim clicks) move to 88 and up. Every patch reads its samples only when a song renders it (lazy): importing
needs no samples, a missing pack fails at use with its fetch command; only the zones a track's notes can reach load.

Playing them like a drummer (recipes/HUMAN_FEEDBACK.md "realism"): velocities 20-127 across the layers (ghost notes
20-45 on the snare, backbeats 95-120, hats 50-90 with accents), round robins rotate by themselves, the hats choke
(42 closes a ringing 46), and the multi-mic kits carry close + overhead + room in one sampler; the notes name the
controller (cc=...) and microphone (mics=...) settings to change that balance in your own inst.sfz / inst.kit.

Level calibration: every patch at gain_db 0 lands at about -18 LUFS (track node, dry) playing its audition material
(`python -m agentsound audition <patch>`: the groove for kits; sampled/tr727, radio_ready_perc and world_percussion
are measured with a conga / bongo / shaker groove instead, see their notes). Licences (python -m agentsound samples
-v): CC0 (Karoryfer, Virtuosity, FreePats), CC-BY 4.0 (DrumGizmo kits, Naked Drums: credit), CC-BY-SA 3.0 (AVL kits,
Salamander: credit + share-alike), CC-BY-NC-SA with a music-production exception (MF Natural: check), MusicRadar
SampleRadar (royalty-free, no redistribution), Pettinhouse (freeware, no redistribution), hyperreal.org machines (no
formal licence: fine for sketches, check before releasing).
Version: see VERSION.
"""

from . import Patch, fx, inst, register

VERSION = 1

# Audition-calibrated levels (sampler 'level', dB): every patch at gain_db 0 -> about -18 LUFS on its material.
LEVELS = {
    'tr606': 3.7, 'tr626': 3.3, 'tr505': 1.4, 'tr727': 2.0, 'cr8000': 3.0, 'rx21': 0.8, 'rz1': 2.1, 'kpr77': 0.6,
    'dr110': 3.8, 'sc_tom': -1.2, 'tr808_fischer': 2.7,
    'virtuosity_kit': 0.1, 'naked_kit': 9.5, 'drs_kit': 9.4, 'salamander_kit': 3.8,
    'big_rusty_kit': 8.0, 'big_rusty_brushes': 9.9, 'big_rusty_mallets': 8.0, 'unruly_kit': 6.3,
    'unruly_brushes': 7.6, 'black_pearl_kit': -1.5, 'red_zeppelin_kit': 0.3, 'hotrod_kit': -3.4,
    'mf_natural_kit': 1.5, 'gogodze_kit': 4.4, 'busk_kit': 4.1, 'muldjord_kit': 2.8, 'aasimonster_kit': 3.9,
    'crocell_kit': 4.4, 'radio_ready_kit': -2.5, 'radio_ready_perc': -2.1, 'foley_kit': 0.4,
    'pettinhouse_brushes': -7.2, 'cymbals': -2.8, 'phat_hat': 8.3, 'frankensnare': 4.1, 'world_percussion': -2.0,
    'cajon': 10.3, 'bobobo': 13.5,
}


def _hp(freq: float = 25.0, slope: int = 24):
    """Clean-up high-pass: DC offset and subsonic rumble (old machine samples, room mics)."""
    return fx.eq({'hp.freq': freq, 'hp.slope': slope})


def _kit(name: str, source: str, **kw):
    return inst.kit(source, lazy=True, level=LEVELS[name], **kw)


def _sfz(name: str, path: str, **kw):
    return inst.sfz(path, lazy=True, level=LEVELS[name], **kw)


_HR_LICENSE = 'License unclear (hyperreal.org free download, no terms: fine for sketches, check before releasing).'

# --------------------------------------------------------------------------------------------- drum machines

register(Patch(
    'sampled/tr606',
    instrument=_kit('tr606', 'samples/hyperreal-tr606', gains={'hats': -4, 'cymbals': -4}),
    fx=[_hp(28)],
    sends={'plate': -24},
    notes='v1. Roland TR-606 Drumatix (hyperreal.org, 8 hits): the thin, ticking little analogue box of early '
          'electro, acid (with a TB-303) and indie-electronica. Keys: 36 kick, 38 snare, 42 / 46 hats (44 = closed), '
          '88 the half-open hat, 45 / 48 toms (41 43 47 50 retuned copies), 49 cymbal. No clap, no rim: add sampled/'
          'tr808 or sampled/cr8000 for those. Hats: 16ths at velocities 60-100 with accents; the kick is short and '
          'clicky (layer a sub or sampled/tr808_fischer 36 under it for weight). ' + _HR_LICENSE + ' Sends: plate -24. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr626',
    instrument=_kit('tr626', 'samples/hyperreal-tr626', gains={'hats': -3, 'cymbals': -5, 'shaker': -6}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Roland TR-626 (hyperreal.org, 30 hits): the late-80s 12-bit PCM machine - brighter and more complete '
          'than the 707 (house, freestyle, new jack swing, lo-fi). Keys: 36 / 35 kicks, 38 / 40 snares (88 a third), '
          '37 rimshot, 39 clap, 42 / 46 hats (44 = closed), 41 43 45 47 48 50 toms, 49 crash, 51 ride, 53 cup, 52 '
          'china, 54 tambourine, 56 cowbell, 62 / 63 / 64 congas (mute hi, open hi, low), 65 / 66 timbales, 67 / 68 '
          'agogos, 75 claves, 82 shaker. ' + _HR_LICENSE + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr505',
    instrument=_kit('tr505', 'samples/hyperreal-tr505', gains={'hats': -3, 'cymbals': -4}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Roland TR-505 (hyperreal.org, 16 hits): the cheap 1986 PCM box of lo-fi house, early techno and '
          'bedroom synth-pop; short, gritty samples. Keys: 36 kick, 38 snare, 37 rimshot, 39 clap, 42 / 46 hats, 41 '
          '45 48 toms (43 47 50 retuned copies), 49 crash, 51 ride, 56 high cowbell (88 low cowbell), 63 / 64 congas, '
          '65 timbale. ' + _HR_LICENSE + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/cr8000',
    instrument=_kit('cr8000', 'samples/hyperreal-cr8000', gains={'hats': -3, 'cymbals': -4, 'cowbell': -4}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Roland CompuRhythm CR-8000 (hyperreal.org, 13 hits): the soft, round analogue preset box of early-80s '
          'pop and new wave (softer than the 808, a famous clap). Keys: 36 kick, 38 snare, 37 rim, 39 clap, 42 / 46 '
          'hats, 45 / 48 toms (41 43 47 50 retuned copies), 49 cymbal, 56 cowbell, 63 / 64 congas, 75 claves. '
          + _HR_LICENSE + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/tr727',
    instrument=_kit('tr727', 'samples/hyperreal-tr727', extras=False, map={
        'open_hat': None, 'conga_mute': '727 HM CONGA', 'conga_hi': '727 HO CONGA', 'conga_lo': '727 LO CONGA',
        'whistle_short': '727 S.WHISTL', 'whistle_long': '727 L.WHISTL'}),
    fx=[_hp(40)],
    sends={'plate': -20},
    notes='v1. Roland TR-727 (hyperreal.org, 13 hits): the Latin-percussion twin of the TR-707 (Italo, freestyle, '
          'Detroit techno, 80s pop percussion tracks). Keys (GM hand percussion): 60 / 61 bongos (high / low), 62 / 63 '
          '/ 64 congas (high mute, high open, low), 65 / 66 timbales, 69 cabasa, 70 maracas, 71 / 72 whistles (short / '
          'long), 58 quijada (vibraslap), 84 star chime (bell tree). Fixed mapping: the pack names the open high conga '
          '"HO" (the kit builder read it as an open hi-hat) and the long whistle "L." (read as short). No kick or '
          'snare: '
          'pair it with sampled/tr707 on its own track. Play congas in 16th patterns, velocities 60-110 (open tones '
          'accented), maracas / cabasa as 8ths or 16ths at 50-80. ' + _HR_LICENSE + ' Sends: plate -20. Measured -18.0 '
          'LUFS (percussion groove: congas, bongos, timbale, maracas; the audition groove plays drum keys it lacks).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/rx21',
    instrument=_kit('rx21', 'samples/hyperreal-rx21', extras=False, map={
        'kick': 'KIRX21', 'clap': 'CLRX21', 'hat': 'HCRX21', 'pedal_hat': 'HCRX21', 'open_hat': 'HORX21',
        'crash': 'CCRX21'}, gains={'hats': -3, 'cymbals': -4}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. Yamaha RX21 (hyperreal.org, 9 hits): the budget 1985 digital machine - hard, dry 12-bit samples '
          '(synth-pop demos, lo-fi, EBM). Keys: 36 kick, 38 snare, 39 clap, 42 / 46 hats (44 = closed), 41 45 48 toms '
          '(43 47 50 retuned copies), 49 crash. The file names (KI, CL, HC, HO, CC) are mapped by hand. '
          + _HR_LICENSE + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/rz1',
    instrument=_kit('rz1', 'samples/hyperreal-rz1', extras=False, map={
        'kick': 'KIRZ', 'rim': 'RSRZ', 'clap': 'CLRZ', 'hat': 'HCRZ', 'pedal_hat': 'HCRZ', 'open_hat': 'HORZ',
        'crash': 'CCRZ', 'ride': 'CRRZ', 'cowbell': 'CBRZ'}, gains={'hats': -3, 'cymbals': -3, 'cowbell': -4}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. Casio RZ-1 (hyperreal.org, 12 hits): the crunchy 1986 sampling drum machine (early hip-hop, '
          'industrial, 80s indie) - lo-fi, punchy, a little noisy. Keys: 36 kick, 38 snare, 37 rimshot, 39 clap, 42 / '
          '46 hats (44 = closed), 41 45 48 toms (43 47 50 retuned copies), 49 crash, 51 ride, 56 cowbell. The '
          'two-letter '
          'file names are mapped by hand (CC crash, CR ride: quieter and duller, as measured). ' + _HR_LICENSE +
          ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/kpr77',
    instrument=_kit('kpr77', 'samples/hyperreal-kpr77', gains={'hats': -4, 'cymbals': -5}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Korg KPR-77 (hyperreal.org, 8 hits): the analogue 1983 Korg - a soft, boomy kick, papery snare and '
          'clap, long open hat (minimal wave, electro, early techno). Keys: 36 kick, 38 snare, 39 clap, 42 / 46 hats '
          '(44 = closed), 45 / 48 toms (41 43 47 50 retuned copies), 49 cymbal. ' + _HR_LICENSE + ' Sends: plate -22. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/dr110',
    instrument=_kit('dr110', 'samples/hyperreal-dr110', gains={'hats': -4, 'cymbals': -6}),
    fx=[_hp(28)],
    sends={'plate': -22},
    notes='v1. Boss DR-110 Dr. Rhythm Graphic (hyperreal.org, 6 hits): the tiny analogue box with the famous '
          'clap and the sizzling hats (lo-fi, electro, minimal synth). Keys: 36 kick, 38 snare, 39 clap, 42 / 46 hats '
          '(44 = closed), 49 cymbal - no toms (the audition fill falls silent). ' + _HR_LICENSE + ' Sends: plate -22. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/sc_tom',
    instrument=_kit('sc_tom', 'samples/hyperreal-sequential-tom', map={'hat': 'closehat', 'pedal_hat': 'closehat'},
                    gains={'hats': -3, 'cymbals': -4}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. Sequential Circuits TOM (hyperreal.org, 8 hits): the 1985 sister of the Drumtraks - fat, bright 8-bit '
          'digital drums (synth-pop, new wave). Keys: 36 kick, 38 snare, 39 clap, 42 / 46 hats (44 = closed), 45 / 48 '
          'toms (41 43 47 50 retuned copies), 49 crash. The kick is very short (80 ms): layer a sub for weight. '
          + _HR_LICENSE + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_F808 = 'samples/hyperreal-tr808-fischer'

register(Patch(
    'sampled/tr808_fischer',
    instrument=_kit('tr808_fischer', _F808, extras=False, map={
        'kick': 'BD5075.WAV', 'kick2': 'BD2525.WAV', 88: 'BD0010.WAV', 89: 'BD1050.WAV', 90: 'BD5000.WAV',
        'snare': 'SD5050.WAV', 'snare2': 'SD1010.WAV', 91: 'SD0000.WAV',
        'rim': 'RS.WAV', 'clap': 'CP.WAV', 'hat': 'CH.WAV', 'pedal_hat': {'files': ['CH.WAV'], 'gain': -4},
        'open_hat': 'OH50.WAV', 92: {'files': ['OH10.WAV'], 'choke': 1, 'gain': -5},
        'tom_lo': 'LT00.WAV', 'tom_floor_hi': 'LT50.WAV', 'tom_mid': 'MT00.WAV', 'tom_lowmid': 'MT50.WAV',
        'tom_hi': 'HT00.WAV', 'tom_high': 'HT50.WAV',
        'crash': 'CY5075.WAV', 'crash2': 'CY2550.WAV', 'cowbell': 'CB.WAV',
        'conga_mute': 'HC75.WAV', 'conga_hi': 'MC50.WAV', 'conga_lo': 'LC50.WAV',
        'maracas': 'MA.WAV', 'claves': 'CL.WAV'},
        gains={'hats': -5, 'cymbals': -6, 'clap': -2, 'cowbell': -5, 'conga': -3, 'maracas': -6, 'claves': -5,
               'rim': -4}),
    fx=[_hp(20)],
    sends={'plate': -24},
    notes='v1. Roland TR-808, the complete Michael Fischer set (1994, 116 hits from a real 808, every knob at 5 '
          'positions, 44.1 kHz, individual outputs): the most faithful 808 here. Chosen settings: 36 kick BD5075 (tone '
          '5, decay 7.5: ~1.3 s boom), 35 BD2525 (short and punchy), 88 BD0010 (dark, 3 s sub boom: trap / hip-hop '
          '808 bass - play it pitched with instrument.tune or note bends), 89 BD1050 (brightest tone), 90 BD5000 '
          '(shortest click); 38 snare SD5050, 40 SD1010 (max tone and snappy: bright, noisy), 91 SD0000 (dull); 37 '
          'rimshot, 39 clap, 42 closed hat (44 the same, 4 dB softer), 46 open hat OH50 (92 OH10: longest); toms '
          '41 43 45 47 48 50 = low / mid / high tom at tuning 0 and 5; 49 cymbal CY5075 (57 CY2550 shorter, darker); '
          '56 cowbell, 62 / 63 / 64 high / mid / low conga, 70 maracas, 75 claves. File names: <sound><knob 1><knob 2> '
          'at 00 25 50 75 10 (= min .. max), e.g. inst.kit("' + _F808 + '", map={"kick": "BD0075.WAV"}). No velocity '
          'layers (one sample per setting, velocity scales the level): accent with velocity 110-127 against 80-95. '
          'Licence: freeware from the author ("absolutely free", no formal licence: check before releasing). Compared '
          'with sampled/tr808 (SampleRadar, 23 hits): longer, cleaner kicks and every tuning. Sends: plate -24. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- acoustic kits (SFZ)

_VIRT = 'samples/virtuosity-drums/Programs/02-full-kit.sfz'

register(Patch(
    'sampled/virtuosity_kit',
    instrument=_sfz('virtuosity_kit', _VIRT, cc={109: 80},
                    keymap={37: 88, 99: 37, 45: 50, 47: 48, 97: 45, 98: 47}),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v1. Virtuosity Drums (sfzinstruments, CC0): a small jazz-club kit played with sticks, 6 microphones, deep '
          'velocity layers (up to 36) with round robins - the most detailed acoustic kit here, very good for ghost '
          'notes. Default mix: kick + snare close mics and overheads (the file\'s default) plus the room mic at 63 % '
          '(cc 109 = 80); mid (cc 107) and vintage lo-fi (cc 111) mics off. Keys: 36 kick (35 kick with loose snare '
          'wires), 38 snare centre, 39 snare off-centre (no clap), 40 rimshot, 37 cross-stick (88 too; 99 the stick '
          'shot), toms: 41 / 43 low tom centre / off-centre, 48 / 50 high tom centre / off-centre (47 = 48, 45 = 50 so '
          'the GM tom keys all sound: two toms), 97 / 98 low-tom rimshot / cross-stick; 42 / 44 / 46 hats (90 half, 94 '
          'three-quarter open, 92 foot splash), 49 crash, 57 crash sizzle, 51 ride, 53 bell, 59 flat ride, 55 '
          'flat-ride '
          'crash; 85-96 snare extras (86 muted, 87 half-open, 93 buzz, 95 flam, 96 roll: hold the key); GM percussion '
          '54-84 (tambourine, cowbell, bongos, congas, timbales, agogo, cabasa, shaker, whistles, guiro, claves, '
          'woodblocks, cuica, triangle, jingle bells, bell tree) - the kit doubles as a percussion rack. How to play: '
          'snare ghosts at 15-40 and backbeats 90-115 (the layers change the tone, not just the level), ride at 60-95 '
          'with a softer "skip" note, hat foot on 2 and 4. Tweak (own inst.sfz of the file): cc={109: 0} (dry close '
          'mics), {107: 90} (mid pair), {111: 100} (vintage lo-fi mic), {113: 100} ("epic" octave-down layer), {21: '
          '127} (snares off), {71: 100} (dampened kick). CC0 (credit welcome: sfzinstruments / Virtuosity Drums). '
          'Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_NAKED = 'samples/naked-drums/Wilkinson Audio/Naked Drums/Stereo/Naked Drums.sfz'

register(Patch(
    'sampled/naked_kit',
    instrument=_sfz('naked_kit', _NAKED, keymap={
        46: 49, 88: 46, 89: 39, 39: None, 49: 55, 55: 54, 54: None, 50: 48, 52: 50, 90: 52, 91: 56, 56: None,
        92: 58, 58: None, 93: 59, 59: 51}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. Wilkinson Audio Naked Drums (SFZ by kinwie, CC-BY 4.0): a Yamaha Recording Custom kit through Neve / '
          'API preamps, 10 round robins, up to 5 velocity layers, direct + overhead + close-room + far-room + mid-side '
          'microphones all in (the file\'s balance): a big, natural rock / pop kit. Keys (re-mapped to GM): 36 kick, '
          '38 / 40 snares (Ayotte 14", Pearl 13"), 37 side stick, 42 / 44 / 46 hats (88 half-open, 89 tight), toms 48 '
          '(10"; 50 the same) 47 45 43 41 (16"), 49 / 57 crashes (92 / 93 their bells), 51 ride, 53 bell, 59 = 51, 52 '
          'china (90 second china), 55 splash (91 second splash); 60-66 choke the ride, crashes, splashes and chinas '
          '(hit after the cymbal). Variable hats (pedal CC 4): keyswitch C#0 (clip.articulate on key 13). Play: '
          'kick 80-120, snare 30-120 (ghosts at 30-50), toms 70-120. Tweak (own inst.sfz of the file): cc={41: 90} '
          '(more direct mics), {43: 30, 44: 30} (less room), {45: 0} (no mid-side), {46: 60} (wide China OH). '
          'CC-BY 4.0: credit "Wilkinson Audio (Naked Drums)". Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_DRS = 'samples/drumgizmo-drskit-sfz/DrumGizmo/DRSKit/Stereo/DrumGizmo DRSKit.sfz'

register(Patch(
    'sampled/drs_kit',
    instrument=_sfz('drs_kit', _DRS, keymap={48: 47, 50: 47, 45: 43, 88: 48, 89: 50, 90: 52, 52: None}),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v1. DRSKit (DrumGizmo, SFZ port by kinwie, CC-BY 4.0): a Danish rehearsal-room kit (Paiste cymbals) "for '
          'everything from jazz to rock", 8 velocity layers x up to 9 round robins, close + overhead + ambience mics '
          'mixed to stereo. Keys: 36 kick (35 no-contact kick), 38 snare, 40 snare rest, 37 rimshot, 42 / 44 / 46 '
          'hats (56 closed tip, 58 open, 61 open tip), toms 47 / 48 / 50 (high), 45 = 43 (mid), 41 (floor), 49 / 54 '
          'left crash / its tip, 57 / 55 right crash / tip, 51 ride, 53 bell, 63-73 ride variants; 88 / 89 / 90 choke '
          'the left crash / right crash / ride; 60-76 whisker (wire brush) hits of the same kit - recorded far '
          'softer than the sticks (25-35 dB under the kick) and the snare whisker has a velocity gap near 45, so they '
          'are no separate brush patch. Play: velocities 20-127, ghost notes below 45. Tweak (own inst.sfz): '
          'cc={90: 90} (more close mics), {92: 30} (less ambience), {91: 90} (more overheads). CC-BY 4.0: credit '
          '"Drum samples provided by DrumGizmo.org (DRSKit)". Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_SAL = 'samples/salamander-drumkit/ALL.sfz'

register(Patch(
    'sampled/salamander_kit',
    instrument=_sfz('salamander_kit', _SAL, keymap={
        35: None, 37: 41, 88: 37, 89: 39, 39: None, 41: 43, 47: 45, 48: 45, 50: 45, 56: 47, 51: 52, 59: 48, 52: 59,
        49: 55,
        55: 63, 84: 64, 90: 62, 91: 60, 92: 50, 93: 49, 94: 54, 95: 56, 96: 58, 97: 51, 98: 61,
        54: None, 58: None, 60: None, 61: None, 62: None, 63: None, 64: None}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. Salamander Drumkit (Alexander Holm, CC-BY-SA 3.0): a birch kit recorded from the overheads, 3-4 '
          'velocity layers with many random round robins (up to 20 on the hats): an open, roomy, natural indie / pop '
          '/ rock sound. Keys (re-mapped to GM): 36 kick (the pack\'s first kick on 35 is left out: one of its soft '
          'samples, kick_OH_P_1.wav, is 44 s long and silent - a ghost kick would sound 44 s late), 38 snare 2 (40 '
          'snare 1), 37 stick on the snare, 88 / '
          '89 the two snares with the wires off; 42 / 44 / 46 hats (44 above velocity 100: foot stomp), 43 / 45 low / '
          'high tom (41 = 43; 47 48 50 = 45: two toms), 49 / 57 crashes, 51 ride (53 bell), 59 second ride, 52 china, '
          '55 splash, 56 cowbell, 84 bell chime; 90 third crash, 91 second china, 92 / 93 ride-2 crash / bell; 94-98 '
          'chokes (crash 1, crash 2, china, ride 2, china 2). Semi-open hats (the file\'s CC 64 layers on key 42) are '
          'off. Play: snare ghosts below 30 (own layer), 60-100 normal, 101+ accents. Credit: Alexander Holm, CC-BY-SA '
          '3.0 (share-alike). Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_RUSTY = 'samples/big-rusty-drums/Programs/01-full.sfz'
# the Big Rusty keymap -> GM: toms 41 43 45 47 (22" 18" 15" 14") + copies on 48 / 50; crash choke 50 -> 88, ride
# choke 55 -> 89, china choke 59 -> 90; 52 china (57), 57 sizzle crash (65), 59 sizzle ride (60), 55 stack (71)
_RUSTY_MAP = {48: 47, 50: 47, 88: 50, 89: 55, 90: 59, 91: 52, 52: 57, 57: 65, 59: 60, 55: 71}
_RUSTY_MICS = {'oh': -2.0, 'top': 0.0, 'btm': -4.0}

register(Patch(
    'sampled/big_rusty_kit',
    instrument=_sfz('big_rusty_kit', _RUSTY, mics=_RUSTY_MICS, dyn_cc=4, keymap=_RUSTY_MAP),
    fx=[_hp(28)],
    sends={'plate': -20},
    notes='v1. Karoryfer Big Rusty Drums (CC0), played with sticks: a big 80s kit (24" kick, 22" / 18" / 15" / 14" '
          'toms), 14 velocity layers x 4 round robins, close + overhead mics (snare bottom -4 dB, overheads -2 dB): '
          'the full low end for rock, arena pop and power ballads (the rock band presets use it). Keys: 36 kick (35 '
          'no-damp), 38 snare, 37 side stick, 39 edge, 40 rimshot, 42 closed hat, 44 foot, 46 variable hat (its '
          'opening is the live "dynamics" param: 1 = open (default), 0.5 half, 0.2 nearly closed - automate '
          'instrument.dynamics in steps or .but(dynamics=0.5)), 54 / 56 / 58 closed shank / foot splash / variable '
          'shank, toms 41 43 45 47 (48 / 50 = 47), 49 crash, 51 ride, 53 bell, 52 china, 57 sizzle crash, 59 sizzle '
          'ride, 55 stack; 88 / 89 / 90 choke crash / ride / china, 91 ride crash; 83-96 rim clicks, 24-32 pedal '
          'noises. Play: ghost notes 20-45, backbeat 100-127 (the top layers crack), toms 80-120. Tweak (own inst.sfz '
          'of the file): mics={"oh": -8} (tighter), cc={85: 100} (snare "epic" layer), {74: 100} (kick punch), {49: '
          '100} (deadened toms). CC0. Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/big_rusty_brushes',
    instrument=_sfz('big_rusty_brushes', _RUSTY, mics=_RUSTY_MICS, dyn_cc=4, keymap=_RUSTY_MAP,
                    cc={25: 80, 26: 80, 27: 80, 28: 80}),
    fx=[_hp(30)],
    sends={'plate': -18},
    notes='v1. Karoryfer Big Rusty Drums (CC0) played with brushes (sticking CC 25-28 = 80): the same big kit for '
          'ballads, country, jazz-pop and brushed rock. Keys as sampled/big_rusty_kit, plus the brush techniques: 73 / '
          '74 long / short snare stir (a swell: start one every beat or half bar for the continuous "shhh"), 75 '
          'flutter, 76 dig, 77 stops the stir; 78-81 the same on the 18" tom. Brush taps are soft by nature: snare '
          '40-100, ride 50-90, and keep stirs under the taps. Hi-hat 46: live opening via instrument.dynamics. CC0. '
          'Sends: plate -18. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/big_rusty_mallets',
    instrument=_sfz('big_rusty_mallets', _RUSTY, mics=_RUSTY_MICS, dyn_cc=4, keymap=_RUSTY_MAP,
                    cc={25: 110, 26: 110, 28: 110}),
    fx=[_hp(28)],
    sends={'hall': -14},
    notes='v1. Karoryfer Big Rusty Drums (CC0) played with soft mallets (sticking CC 25 / 26 / 28 = 110; the hi-hat '
          'stays on sticks): rolling tom thunder, mallet snare and cymbal swells for film, orchestral pop and '
          'post-rock builds. Keys as sampled/big_rusty_kit: toms 41 43 45 47 (48 / 50 = 47), 38 snare, 49 / 57 '
          'crashes, 51 ride, 52 china. How to play a cymbal swell: 16th or 32nd notes on 49 or 51 with velocity '
          'rising 30 -> 110 over 1-2 bars, then a choke (88) or let it ring; tom rolls: alternate 41 / 43 in 16ths, '
          'velocity waves 50-110. CC0. Sends: hall -14. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_UNRULY = 'samples/karoryfer-unruly-drums/Programs/'
# Unruly -> GM: toms 41 (22" as floor) 45 47 (+48 / 50 = 47); crash / ride chokes -> 88 / 89; crash bow on 57 -> 90;
# 57 / 59 = second crash / ride copies; woodblocks 59 / 60 -> 77 / 76
_UNRULY_MAP = {48: 47, 50: 47, 88: 50, 89: 52, 52: None, 90: 57, 57: 49, 59: 51, 76: 60, 77: 59, 60: None}

register(Patch(
    'sampled/unruly_kit',
    instrument=_sfz('unruly_kit', _UNRULY + '01-kit-sticks.sfz', dyn_cc=4, keymap=_UNRULY_MAP),
    fx=[_hp(40)],
    sends={'plate': -20},
    notes='v1. Karoryfer Unruly Drums (CC0), sticks: a small, dry garage kit - a 20" kick with snare wires, three '
          'snares (14", 13", 22" deep), 22" / 14" / 13" toms, up to 9 velocity layers x 4 round robins, close + '
          'overhead mics. Indie, garage rock, lo-fi pop, funk. Thin below 60 Hz by design (layer a sub kick for '
          'weight). Keys: 36 kick (35 dirty, 34 dirtiest), 38 snare 14" (39 edge, 40 rimshot, 37 side stick), 62-64 '
          'snare 13" (centre / edge / rimshot), 26-28 snare 22"; 42 / 44 / 46 hats (46: live opening = the '
          '"dynamics" param, 1 open), 54 / 58 hat shank; toms 41 / 43 (22" centre / edge), 45 (14"), 47 = 48 = 50 '
          '(13"); 49 = 57 crash (90 crash bow), 51 = 59 ride, 53 bell, 55 ride edge; 88 / 89 choke crash / ride; '
          '76 / 77 woodblocks; 65-72 rim clicks, 74-83 pedal and stool noises. Tweak (own inst.sfz): cc={72: 10, 32: '
          '60, 42: 60, 52: 60} (less overheads: a tighter, centred kit, as the rock presets do). CC0. Sends: plate '
          '-20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/unruly_brushes',
    instrument=_sfz('unruly_brushes', _UNRULY + '02-kit-brushes.sfz', dyn_cc=4, keymap=_UNRULY_MAP),
    fx=[_hp(40)],
    sends={'plate': -18},
    notes='v1. Karoryfer Unruly Drums (CC0) played with brushes: the small dry kit of sampled/unruly_kit with brush '
          'taps (8 velocity layers x 4 round robins) and stirs - 29-33 snare stirs (29 / 30 / 31 / 32 start, '
          'ongoing, accent, flutter; 33 mutes: hold a stir key for a sweep, start a new one each beat or half bar). '
          'Keys otherwise as sampled/unruly_kit (38 snare, 42 / 44 / 46 hats, 51 ride, 49 crash, toms 41 45 47). A '
          'drier, closer alternative to sampled/brush_kit (Swirly) for folk, singer-songwriter and quiet jazz-pop. '
          'Play taps at 40-100. CC0. Sends: plate -18. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# AVL drumkits (Glen MacArthur): 41 / 43 floor tom centre / edge, 45 / 47 rack tom centre / edge, 48 hat swish,
# 50 / 52 / 58 crash / ride / crash-2 chokes, 59 ride shank, 60 extra crash (china on 62) -> GM
_AVL_MAP = {48: 45, 50: 45, 88: 48, 89: 50, 90: 52, 91: 58, 52: 62, 58: None}
_AVL_CREDIT = 'CC-BY-SA 3.0: credit "AVL Drumkits by Glen MacArthur (AV Linux)", share-alike.'

register(Patch(
    'sampled/black_pearl_kit',
    instrument=_sfz('black_pearl_kit', 'samples/avl-black-pearl/Black_Pearl_2023_repack.sfz', keymap=_AVL_MAP),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v1. AVL Drumkits "Black Pearl" (Glen MacArthur): a Pearl rock kit (22" kick, 14" snare, 12" / 16" toms, '
          'Sabian cymbals), 5 velocity layers, no round robins (vary the velocity of repeated hits a little: '
          'humanize), stereo overhead image. Classic rock and pop. Keys: 36 kick, 38 snare (40 edge), 37 side stick, '
          '35 stick click, 39 clap; 42 / 44 / 46 hats (88 hat swish), 45 / 47 rack tom centre / edge (48 / 50 = 45), '
          '41 / 43 floor tom centre / edge, 49 16" crash, 57 17" crash, 60 22" crash, 51 ride, 59 ride shank, 53 '
          'bell, 52 china, 55 splash, 54 tambourine, 56 cowbell, 61 maraca; 89 / 90 / 91 choke crash / ride / crash '
          '2. ' + _AVL_CREDIT + ' Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/red_zeppelin_kit',
    instrument=_sfz('red_zeppelin_kit', 'samples/avl-red-zeppelin/Red_Zeppelin_2023_repack.sfz', keymap=_AVL_MAP),
    fx=[_hp(25)],
    sends={'plate': -18},
    notes='v1. AVL Drumkits "Red Zeppelin" (Glen MacArthur): a big Ludwig (26" kick, 14" snare, 14" / 16" toms, '
          'Zildjian 20" crash, 24" ride) for the 70s hard-rock sound - huge, open, boomy. 5 velocity layers, no round '
          'robins. Keys as sampled/black_pearl_kit: 36 kick, 38 snare (40 edge), 37 side stick, 42 / 44 / 46 hats (88 '
          'swish), 45 / 47 rack tom, 41 / 43 floor tom (48 / 50 = 45), 49 / 57 / 60 crashes, 51 ride (59 shank, 53 '
          'bell), 52 china, 55 splash, 54 tambourine, 56 cowbell, 61 maraca; 89-91 chokes. Play big: kick 90-127, '
          'snare 100-127, crash on the ones. ' + _AVL_CREDIT + ' Sends: plate -18. Measured -18.0 LUFS (audition '
          'groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/hotrod_kit',
    instrument=_sfz('hotrod_kit', 'samples/avl-blonde-bop-hotrod/BLONDE_BOP_HR.sfz',
                    keymap={48: 45, 50: 45, 88: 48, 89: 50, 90: 52, 91: 58, 52: 60, 58: None, 60: None, 82: 61,
                            61: None}),
    fx=[_hp(30)],
    sends={'plate': -16},
    notes='v1. AVL Drumkits "Blonde Bop Hot Rods" (Glen MacArthur): the small TAMA bebop kit of sampled/jazz_kit '
          'played with rods (bundled dowels): between sticks and brushes - soft, woody, dry; unplugged pop, '
          'singer-songwriter, acoustic jazz, cafe sets. 5 velocity layers. Keys: 36 kick 18", 38 snare (40 edge), 37 '
          'side stick, 35 rod click, 39 clap; 42 / 44 / 46 hats (88 swish), 45 / 47 10" tom (48 / 50 = 45), 41 / 43 '
          '14" floor tom, 49 crash, 57 crash 2, 51 ride tip, 59 shank, 53 bell, 52 china, 55 splash, 54 tambourine, '
          '56 cowbell, 82 shakers; 89-91 chokes. Play 40-110 (rods do not bark). ' + _AVL_CREDIT + ' Sends: plate '
          '-16. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_MF = 'samples/fiedler-mf-natural-drumset/mf-drumset-complete-ogg.sfz'

register(Patch(
    'sampled/mf_natural_kit',
    instrument=_sfz('mf_natural_kit', _MF, keymap={51: 59, 59: 51, 88: 56, 56: None, 89: 54, 54: None}),
    fx=[_hp(30)],
    sends={'plate': -20},
    notes='v1. MF Natural Drumset (Markus Fiedler, 2011): a natural Sonor kit, kick with 14 velocity layers, drums '
          '6-7 layers x 2 round robins, cymbals 4 x 4, recorded left and right hand separately - no machine gun. Keys: '
          '36 kick (35 second kick), 38 / 40 snare left / right hand (alternate them for 16ths and rolls), 37 side '
          'stick, 39 rimshot; 42 / 44 / 46 hats (30 rattle, 32 closed bell, 34 open rattle), 41 / 43 low tom L / R, '
          '45 / 47 tom L / R (48 / 50 the same), 49 16" crash, 57 18" crash (88 its left-hand hits), 51 ride, 59 '
          '18" crash-ride, 53 bell (89 right hand), 52 china, 55 splash, 58 choke, 65 / 66 snare as timbale; brushes '
          'on the snare: 25 / 27 hits L / R, 26 swish, 28 roll; 24 / 31 pressed rolls. License CC-BY-NC-SA 3.0 with '
          'the author\'s exception: free to use in (also commercial) music productions, NOT in sample libraries - '
          'check before releasing. Credit: Markus Fiedler (fiedler-audio.de). Sends: plate -20. Measured -18.0 LUFS '
          '(audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/gogodze_kit',
    instrument=_sfz('gogodze_kit', 'samples/karoryfer-gogodze-phu-vol-ii/Programs/Kit.sfz',
                    keymap={48: 45, 50: 45, 47: 43}),
    fx=[_hp(35)],
    sends={'plate': -18},
    notes='v1. Karoryfer Gogodze Phu Vol II (CC0): a small, dry, "variable-fidelity" 70s kit (after Kim Jung Mi\'s '
          '"Now", 1973): kick, snare, three toms and a hi-hat, 4-6 velocity layers x 4 round robins, 7 mics mixed '
          '(CC 105 mic mix = 80). Psych-folk, 70s soul, lo-fi and vintage pop. Keys: 36 kick, 38 snare (40 edge, 37 '
          'side stick), 42 / 44 / 46 hats, 41 low, 43 mid (47 the same), 45 high tom (48 / 50 the same). No '
          'cymbals: add sampled/cymbals or a ride from another kit. Tweak (own inst.sfz): cc={110: 20} (lower '
          'fidelity), {111: 60} (cleaner kick), {112: 100} (fat snare), {113: 80} (trashy hat). CC0. Sends: plate -18. '
          'Measured -18.0 LUFS (audition groove; the fill\'s crash is silent).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/busk_kit',
    instrument=_sfz('busk_kit', 'samples/avl-buskmans-holiday/Buskmans_Holiday.sfz'),
    fx=[_hp(35)],
    sends={'plate': -18},
    notes='v1. AVL "Buskmans Holiday" (Glen MacArthur): an unplugged busker\'s kit laid out like a drum kit, 10 '
          'velocity layers per sound - plays any GM drum groove as cajon + shakers: 36 cajon thump (kick), 38 / 40 '
          'cajon slap left / right hand (snare), 37 finger snaps, 39 hand claps, 42 triple shaker (closed hat), 44 '
          'shake tambourine, 46 bump tambourine (open hat), 41 / 43 large conga left / right, 45 / 47 small conga '
          'left / right, 48 claves, 49 Paiste 16" cymbal, 50 its bell, 51 LP cowbell, 52 foot stomp, 53 20 l '
          'bucket, 54 / 55 bell tree down / up, 35 stick click. For acoustic pop, folk, campfire and unplugged '
          'sets: alternate 38 / 40 for fast slaps, shaker 16ths at 50-80. ' + _AVL_CREDIT + ' Sends: plate -18. '
          'Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# ------------------------------------------------------------------------------------------ DrumGizmo kits (inst.kit)

_DG_CREDIT = 'CC-BY 4.0: credit "Drum samples provided by DrumGizmo.org ({})".'

register(Patch(
    'sampled/muldjord_kit',
    instrument=_kit('muldjord_kit', 'samples/drumgizmo-muldjordkit', mics={'Trigger': None, 'room': -3.0},
                    keymap={88: 37, 37: None, 89: 55, 55: None}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. MuldjordKit 3 (DrumGizmo, Lars Muldjord): a Tama Superstar metal / rock kit recorded with 16 '
          'microphones (close kick / snare / toms / hat / rides, overheads, ambience), mixed here to stereo: all close '
          'mics + overheads at 0 dB, the ambience pair -3 dB, the DDrum trigger channel muted. 4-11 velocity layers x '
          '5-13 round robins. Keys: 36 / 35 right / left kick (double bass drum: alternate them for 16ths), 38 '
          'snare (88 the snare resting sound), 42 / 46 hats (44 = closed), toms 48 (Tom1) 47 (Tom2) 45 = 43 (Tom3) '
          '41 (floor, Tom4), 50 = 48, 49 / 57 left / right crash, 51 / 59 right / left ride, 53 bell (89 left-ride '
          'bell), 52 china. The FreePats SFZ build of this kit (pack muldjordkit) is the same recording as a fixed '
          'stereo mix on non-GM keys: use this one. Tweak (own inst.kit): mics={"room": -12} (drier), {"overheads": '
          '-6, "close": 2} (punchier), {"Trigger": 0} (the trigger click for metal kick definition). '
          + _DG_CREDIT.format('MuldjordKit') + ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/aasimonster_kit',
    instrument=_kit('aasimonster_kit', 'samples/drumgizmo-aasimonster', kit='aasimonster',
                    mics={'Trigger': None, 'Snare_trigger': None},
                    keymap={94: 50, 95: 58, 50: 48, 58: None}),
    fx=[_hp(30)],
    sends={'plate': -24},
    notes='v1. The Aasimonster 2.1 (DrumGizmo, the full kit file): a death-metal kit with 16 microphones mixed to '
          'stereo (close + overheads + ambience at 0 dB, both trigger channels muted), 7-11 velocity layers x up to '
          '16 round robins: tight double kick, cracking snare, many chinas - metal, hardcore, heavy rock. Keys: 36 / '
          '35 left / right kick (alternate for double-bass 16ths), 38 snare (93 off-centre), 37 rimshot, 42 / 46 hats '
          '(44 = closed; 89 / 91 two more closed hats), toms 48 (= 50) 47 45 43 (= 41), 49 / 57 crashes (94 / 95 '
          'their chokes), 51 = 59 ride, 53 bell (92 second bell), 52 18" china (88 10", 90 8"), 55 bell cymbal. '
          'Play: kicks 90-120 even (the samples carry the attack), blast beats alternate 36 / 35. Tweak (own '
          'inst.kit): mics={"room": -9} (tighter), {"Trigger": -12} (trigger click on the kick). '
          + _DG_CREDIT.format('The Aasimonster') + ' Sends: plate -24. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/crocell_kit',
    instrument=_kit('crocell_kit', 'samples/drumgizmo-crocellkit-stereo-mix', keymap={
        88: 54, 89: 56, 90: 58, 91: 75, 92: 80, 93: 78, 94: 73, 59: 51,
        54: None, 56: None, 58: None, 73: None, 75: None, 78: None, 80: None}),
    fx=[_hp(30)],
    sends={'plate': -22},
    notes='v1. CrocellKit (DrumGizmo, stereo mix): a big modern rock / metal kit with double pedal, 4 toms, chinas '
          'and splashes, already mixed to stereo by its author, 5-12 velocity layers x up to 24 round robins (the '
          'snare): very natural repetitions. Keys: 36 / 35 right / left kick, 38 snare, 37 rim click, 40 rimshot, 39 '
          'snare rest; 42 / 44 / 46 hats (92 semi-open, 93 closed without pedal, 94 pedal hit), toms 48 = 50 (Tom1) '
          '47 = 45 (Tom2) 43 (floor 1) 41 (floor 2), 49 / 57 left / right crash (89 / 91 stopped, 55 / 90 splashes), '
          '51 = 59 ride, 53 bell, 52 right china (88 left china). ' + _DG_CREDIT.format('CrocellKit') +
          ' Sends: plate -22. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- SampleRadar / one-shots

_RR = 'samples/sampleradar-radio-ready-drums/Kits/'
_MR_LICENSE = 'MusicRadar licence: royalty-free for music, no redistribution of the samples.'

register(Patch(
    'sampled/radio_ready_kit',
    instrument=_kit('radio_ready_kit', _RR + 'Kit B/Wide', gains={'hats': -4, 'cymbals': -5, 'shaker': -8},
                    map={'pedal_hat': 'ClHat2'}),
    fx=[_hp(30)],
    sends={'plate': -24},
    notes='v1. SampleRadar "Radio-ready drums", kit B, wide version: a mixed and compressed modern pop / rock kit - '
          'already produced (EQ, compression, stereo room), drops straight into a dense mix. Keys: 36 / 35 kicks, 38 / '
          '40 snares, 39 clap (89 second clap), 42 / 44 / 46 hats (88 second closed, 90 half-open), toms 48 (= 50) 45 '
          '41 (+ copies), 49 / 57 cymbals, 82 shaker (3 layers). Other versions of every kit A-E: Clean, Crunch '
          '(saturated), Wide, XtraComp (squashed): inst.kit("' + _RR + 'Kit D/Crunch", level=...). One sample per '
          'hit (no layers): vary velocity (80-120) for movement. ' + _MR_LICENSE + ' Sends: plate -24. Measured -18.0 '
          'LUFS (audition groove).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/radio_ready_perc',
    instrument=_kit('radio_ready_perc', _RR + 'Kit E/Clean', gains={'shaker': -4, 'cabasa': -4, 'guiro': -3}),
    fx=[_hp(40)],
    sends={'plate': -20},
    notes='v1. SampleRadar "Radio-ready drums", kit E (clean): produced pop / Latin percussion with velocity layers '
          'and round robins - 60 bongo (7 layers x 3 round robins), 63 conga (7 layers), 65 timbale (3 x 3), 56 '
          'cowbell (88 second), 69 cabasa, 73 / 74 guiro short / long, 82 shaker (3 layers), 91 cajon (4 layers); '
          'plus its own small kit: 36 kick, 38 snare (2 layers x 3), toms 41 45 48 50 (89 / 90 two more). '
          'Layer it on its own track over a kit: shaker / cabasa 16ths at 50-90 with accents, bongo and conga '
          'patterns at 60-110. ' + _MR_LICENSE + ' Sends: plate -20. Measured -18.0 LUFS (percussion groove: congas, '
          'bongos, shaker, timbale; the audition groove plays drum keys it lacks).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/foley_kit',
    instrument=_kit('foley_kit', 'samples/sampleradar-realworld-drums/Drum hits',
                    gains={'hats': -3, 'perc': -3}),
    fx=[_hp(35)],
    sends={'plate': -20},
    notes='v1. SampleRadar "Real-world drums": a found-sound kit - kicks from car doors, bins and footfalls, snares '
          'from doors, paper and tins, hats from coins, foil and frying pans, claps from carrier bags and water, '
          'percussion from pots, keys and coins (145 one-shots). For lo-fi, indie-electronica, film trailers and '
          'playful pop: the kit builder puts one sound per role on the GM keys (36 kick, 38 snare, 42 / 46 hats, 39 '
          'clap, 37 side stick) and every other hit on 88 and up (python -m agentsound kit "samples/'
          'sampleradar-realworld-drums/Drum hits" lists them); pick others with map={"kick": "Car_Door_Kick01"}. '
          + _MR_LICENSE + ' Sends: plate -20. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_PH = 'samples/pettinhouse-brush-kit/Brush Rock Samples'

register(Patch(
    'sampled/pettinhouse_brushes',
    instrument=_kit('pettinhouse_brushes', _PH, map={
        'tom_lo': {'files': ['tom brush basso 2', 'Tom brush Basso 1', 'tom brush Basso 3'], 'layers': 'rr'},
        'tom_floor_hi': {'files': ['tom brush basso 2', 'Tom brush Basso 1', 'tom brush Basso 3'], 'layers': 'rr'},
        'tom_mid': {'files': ['tom brush medio 1', 'tom brush medio 2', 'tom brush medio 3'], 'layers': 'rr'},
        'tom_lowmid': {'files': ['tom brush medio 1', 'tom brush medio 2', 'tom brush medio 3'], 'layers': 'rr'},
        'tom_hi': {'files': ['Tom Brush alto1', 'tom brush alto2', 'tom brush alto3', 'tom brush alto4'],
                   'layers': 'rr'},
        'tom_high': {'files': ['Tom Brush alto1', 'tom brush alto2', 'tom brush alto3', 'tom brush alto4'],
                     'layers': 'rr'}},
        extras=True, gains={'hats': -3, 'cymbals': -3}),
    fx=[_hp(35)],
    sends={'plate': -16},
    notes='v1. Pettinhouse Brush Kit, "Brush Rock" set: an acoustic kit played with brushes throughout - brushed '
          'snare with 4 velocity layers x 3 round robins, brushed toms, cymbals and ride (3 layers), hats: for brushed '
          'pop / rock ballads, country and unplugged sets (a fuller, rockier brush sound than the jazz kits). Keys: 36 '
          '/ 35 kicks (89 third), 38 snare, 40 second snare (4 round robins; 88 a fifth hit), 42 / 44 / 46 hats (90 / '
          '91 second closed / open), toms 41 = 43 low, 45 = 47 mid, 48 = 50 high (3-4 round robins each), 49 crash '
          '(3 layers), 51 ride (3 layers x 2), 53 ride cup. No stirs / sweeps: layer sampled/brush_kit keys 60 / 64 '
          'for '
          'the "shhh". Play 40-110. Other sets in the pack: "Brush jazz", "Brush country jazz", "Brush country rock '
          '2", "brush jazz stick" (inst.kit("samples/pettinhouse-brush-kit/<set> Samples")). License: Pettinhouse '
          'freeware - free to use in music productions, NO redistribution of the samples. Sends: plate -16. Measured '
          '-18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))

_CYM = 'samples/sampleradar-hats-cymbals-gongs/'
_CA, _HA = 'Cymbals/Accoustic/', 'Hats/Accoustic/'

register(Patch(
    'sampled/cymbals',
    instrument=_kit('cymbals', 'samples/sampleradar-hats-cymbals-gongs', extras=False, fill=False, map={
        'hat': {'files': [_HA + 'Closed hat *'], 'layers': 'auto'},
        'pedal_hat': [_HA + 'Hi Hat Foot *'],
        'open_hat': [_HA + 'Open hat 01', _HA + 'Open hat 02', _HA + 'Open hat 03'],
        'crash': {'files': [_CA + 'Crash 01', _CA + 'Crash 02', _CA + 'Crash 03'], 'layers': 'rr'},
        'crash2': {'files': [_CA + 'Crash 05', _CA + 'Crash 06'], 'layers': 'rr'},
        'ride': {'files': [_CA + 'Ride 01', _CA + 'Ride 02', _CA + 'Ride 03'], 'layers': 'rr'},
        'ride2': {'files': [_CA + 'Ride 05', _CA + 'Ride 06'], 'layers': 'rr'},
        'ride_bell': {'files': [_CA + 'Cymbal Bell 01', _CA + 'Cymbal Bell 02'],
                      'layers': 'rr'},
        'china': {'files': [_CA + 'China 01', _CA + 'China 02'], 'layers': 'rr'},
        'splash': {'files': [_CA + 'Splash 01', _CA + 'Splash 02'], 'layers': 'rr'},
        'cowbell': None,
        88: [_CA + 'Cymbal Roll 01'], 89: [_CA + 'Cymbal Roll 02'],
        90: [_CA + 'Cymbal Scrape 01'], 91: [_CA + 'Cymbal Scrape 02'],
        92: [_CA + 'Cymbal Choke 01'], 93: [_CA + 'Cymbal Choke 02'],
        94: [_CA + 'Cymbal and Plug Chain sizzler 01'],
        95: {'files': [_HA + 'Closing Hat 01'], 'choke': 1},
        96: {'files': [_HA + 'Closing Hat 02'], 'choke': 1}}),
    fx=[_hp(120, 12)],
    sends={'plate': -20},
    notes='v1. SampleRadar "Hats, cymbals and gongs", the acoustic sets: a cymbal rack to add to kits that have none '
          '(sampled/gogodze_kit, sampled/studio_kit, drum machines) or for orchestral / film cymbal work. Keys: 42 '
          'closed hat (25 hits sorted into velocity layers), 44 foot, 46 open (3 round robins), 49 / 57 crashes, 51 / '
          '59 rides, 53 bell, 52 china, 55 splash (each 2-3 round robins of different cymbals), 88 / 89 cymbal rolls '
          '(swells: start them 2-4 beats before the downbeat), 90 / 91 scrapes, 92 / 93 chokes, 94 chain sizzler, 95 / '
          '96 closing hats (open-to-closed "tss-t"). High-passed at 120 Hz (no kick bleed): it sits on top of a kit. '
          'Many more (20 crashes, 15 rides, 10 splashes, machine and processed cymbals) in the pack: map={"crash": '
          '"Crash 12"}. ' + _MR_LICENSE + ' Sends: plate -20. Measured -18.0 LUFS (audition groove: hats and crash '
          'only).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- single pieces

register(Patch(
    'sampled/phat_hat',
    instrument=_sfz('phat_hat', 'samples/karoryfer-hat-with-the-phat/Programs/01-complete.sfz', dyn_cc=4),
    fx=[_hp(150, 12)],
    sends={'plate': -22},
    notes='v1. Karoryfer "The Hat With The Phat" (CC0): an oversized hi-hat made of two 20" ride cymbals - dark, '
          'washy, huge; every opening sampled: 5 velocity layers x 4 round robins per position. Keys: 42 squashed '
          '(closed) bow, 44 pedal chik, 46 variable bow hit - its opening is the live "dynamics" param (0 tightly '
          'closed, 0.2 / 0.4 / 0.6 / 0.8 the four half-open positions, 1 fully open: .but(dynamics=0.4) or automate '
          'instrument.dynamics in steps between hits), 54 / 58 squashed / variable edge, 66 / 70 squashed / variable '
          'bell, 56 pedal splash, 68 pedal return, 78 / 80 clutch drop / raise. Opens choke when a closed hit or the '
          'pedal follows. For trip-hop, neo-soul, jazz-funk and slow rock hats; play it on its own track beside a kit '
          'without hats. Tweak (own inst.sfz): cc={81: 60} (an octave-down copy: even bigger), {96: 80} (drier opens), '
          '{98: 80} (tighter closed). CC0. Sends: plate -22. Measured -18.0 LUFS (audition groove: hats only).',
    audition={'notes': 'drums'}))

_FS = 'samples/karoryfer-frankensnare/Programs/'

register(Patch(
    'sampled/frankensnare',
    instrument=inst.sfz_multi({
        'maple': _FS + '06-14x5maple.sfz', 'maple_deep': _FS + '07-14x65maple.sfz',
        'maple_muted': _FS + '08-14x65maplemute.sfz', 'aluminium': _FS + '09-14x8al.sfz',
        'birch': _FS + '11-14x8birch.sfz', 'birch_13': _FS + '18-13x9birch.sfz', 'steel': _FS + '04-12x5steel.sfz',
        'ash': _FS + '03-10x6ash.sfz', 'sapele': _FS + '22-16x7sapele.sfz', 'mahogany': _FS + '26-22x5mah.sfz',
        'alder': _FS + '23-20x12alder.sfz', 'poplar': _FS + '14-20x6poplar.sfz', 'vintage_80s': _FS + '16-80ssymp.sfz',
        'vintage_60s': _FS + '17-60ssymp.sfz', 'brush': _FS + '05-14x5maplebrush.sfz'},
        default='maple', lazy=True, level=LEVELS['frankensnare']),
    fx=[_hp(60)],
    sends={'plate': -18},
    notes='v1. Karoryfer Frankensnare (CC0): a snare collection - 15 real snare drums (5-11 velocity layers x 4 round '
          'robins each) as keyswitched articulations of one instrument, played on 38 (39 / 40 the same drum, 37 side '
          'stick where sampled): maple 14x5 (default), maple_deep 14x6.5, maple_muted, aluminium 14x8, birch 14x8, '
          'birch_13 13x9, steel 12x5, ash 10x6 (popcorn), sapele 16x7, mahogany 22x5, alder 20x12 (a huge "bass '
          'drum" snare), poplar 20x6, vintage_80s / vintage_60s (sympathetic snare buzz from a kit), brush (maple '
          'with brushes; stirs on 24 / 28, 26 stops them). Pick one per clip with clip.articulate("birch") (keyswitch '
          'notes C-1 up; python -m agentsound sfz <file> for each), unmarked notes play maple. Layer it over a kit\'s '
          'snare (a second track on 38) or use it as the kit\'s snare with a kit that lacks one. Play ghost notes '
          '15-40, '
          'backbeats 95-120. CC0. Sends: plate -18. Measured -18.0 LUFS (audition groove: snare only).',
    audition={'notes': 'drums'}))

# --------------------------------------------------------------------------------------------- hand percussion

_WP = 'samples/freepats-world-percussion/WorldPercussion 20200905.sfz'

register(Patch(
    'sampled/world_percussion',
    instrument=_sfz('world_percussion', _WP, keymap={
        36: 50, 38: 48, 40: 49, 39: 59, 54: 57, 60: 52, 61: 53, 62: 65, 63: 64, 64: 63, 69: 56, 70: 67, 75: 60,
        82: 54, 85: 61, 88: 55, 89: 58, 90: 51, 91: 62, 92: 66, 93: 68, 94: 69, 95: 70, 96: 71,
        48: None, 49: None, 50: None, 51: None, 52: None, 53: None, 55: None, 56: None, 57: None, 58: None,
        59: None, 65: None, 66: None, 67: None, 68: None, 71: None}),
    fx=[_hp(40)],
    sends={'plate': -18},
    notes='v1. FreePats World Percussion (CC0; recorded from Xavimart\'s instrument collection, conga and claves from '
          'VSCO 2): re-mapped to the GM keys - 36 / 38 / 40 cajon (bass, slap, a third stroke), 60 / 61 bongo high / '
          'low, 62 / 63 / 64 conga muted / high / low, 54 tambourine, 70 maracas, 82 egg shaker, 69 soft shaker '
          '(cabasa key), 75 claves, 85 castanets, 39 hand clap; extras: 88 fast shaker, 89 fast tambourine, 90 muted '
          'bongo, 91 middle conga, 92 muted low conga, 93 maracas backwards stroke, 94 / 95 / 96 darbuka doom / tak / '
          'pa. Random round robins (2-17 per sound), single velocity layer: vary velocity 60-115 and keep accents on '
          'open tones. The jazz band presets use this pack for bossa percussion. CC0. Sends: plate -18. Measured -18.0 '
          'LUFS (percussion groove: congas, bongos, shaker, tambourine, claves).',
    audition={'notes': 'drums'}))

_GP1 = 'samples/karoryfer-gogodze-phu-vol-i/Programs/'

register(Patch(
    'sampled/cajon',
    instrument=_sfz('cajon', _GP1 + 'Cajon.sfz', keymap={36: 49, 38: 51, 40: 50}),
    fx=[_hp(35)],
    sends={'plate': -18},
    notes='v1. Karoryfer Gogodze Phu Vol I cajon (CC0): a Polish cajon, rear + front mics, 4 velocity layers x 6 '
          'random round robins per stroke, release tails. Keys: 48-52 the five strike locations (49 the deepest '
          'bass, up to 52 the brightest edge slap), 53 / 54 side hits, 55 / 56 two strokes with the snares removed '
          '(round, conga-like), 57 finger roll (hold the key: the roll lasts as long as the note; cc 11 = its level) - '
          'and for GM grooves 36 = 49 (bass), 38 = 51 and 40 = 50 (slaps). Unplugged pop, flamenco-pop, acoustic '
          'sets: bass on 1 and the "and" of 2, slaps on 2 and 4, ghost taps (velocity 25-45) on the 16ths between. '
          'Tweak (own inst.sfz): cc={70: 60} (less rear mic: less boom), {73: 80} (contrast), {72: 50} (lower '
          'tuning). CC0. Sends: plate -18. Measured -18.0 LUFS (audition groove: kick and snare keys).',
    audition={'notes': 'drums'}))

register(Patch(
    'sampled/bobobo',
    instrument=_sfz('bobobo', _GP1 + 'Bobobo.sfz'),
    fx=[_hp(40)],
    sends={'plate': -18},
    notes='v1. Karoryfer Gogodze Phu Vol I bobobo drums (CC0): five Ghanaian drums (bass, two tenors, two trebles) - '
          'deep, round hand-drum tones for world, afro-pop, film and ambient percussion, 4 velocity layers x 4 '
          'round robins. Keys (the pack\'s own layout, near GM drums): 36 bass, 38 / 39 large tenor (open / second '
          'stroke), 40 / 41 small tenor, 43 / 44 large treble, 45 / 46 small treble; the drums are panned across the '
          'stage. Play interlocking parts: bass on the downbeats, tenors on off-beats, trebles in 16th figures, '
          'velocities 50-115. CC0. Sends: plate -18. Measured -18.0 LUFS (audition groove).',
    audition={'notes': 'drums'}))
