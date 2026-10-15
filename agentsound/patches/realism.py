"""Per-family sampler realism values (docs/SAMPLE_REALISM_PLAN.md): one data table, sampler params only. A patch
spreads its family into its sampler (`_sfz(path, level=..., **realism.FAMILY['nylon'])`); every param defaults to off
in the engine, so a patch that does not opt in renders bit-identically.

Lever 2, synthetic round robins (a sample pack with one recording per note and velocity plays the same waveform on
every repeat - a machine gun): `rrpitch` (+- ct, static per note), `rrtone` (+- dB high shelf), `rrattack` (enter the
transient a little late or soften it), `rrstart` (scripted legato entries start elsewhere past the attack), `rrlevel`
(+- dB), `rrborrow` (chance that a quick repeat plays the neighbouring key's sample, re-pitched, level-matched, only
when its attack is about as bright). Lever 3, velocity layers: `layers='blend'` crossfades the two layers a velocity
lies between in the attack (onset-aligned, settling on the nearer one after ~0.4 s), `veltone` darkens the bottom of
each layer as recorded at its top.

`restrike` (a re-struck key damps its ringing voices) rides along where a static per-note detune would otherwise beat
against the same key's ringing earlier notes: a plucked string re-plucked does not keep its old vibration.

Values are the A/B-checked starting points of the plan; the measured effect (report nodes[].realism on the audition
probes `repeat` / `sweep`) is in TODO.md "Sample realism".
"""

FAMILY = {
    # a plucked string with one recording per note (FreePats nylon): the most audible machine gun
    'nylon': {'rrpitch': 4, 'rrtone': 1.5, 'rrattack': 0.4, 'rrlevel': 0.8, 'rrborrow': 0.5, 'restrike': 12},
    # plucked packs that have their own round robins (Fiedler concert guitar 7 RR, Shinyguitar 5): a little on top
    'plucked': {'rrpitch': 2, 'rrtone': 1, 'rrattack': 0.2, 'rrlevel': 0.5, 'restrike': 12},
    # an acoustic piano with one recording per note and velocity layer. No rrborrow: on the Salamander (a sample every
    # 3 keys, 16 layers) a borrowed note stuck out by up to 20 dB of brightness in nocturne-etude despite the gate
    'piano': {'rrpitch': 1.5, 'rrtone': 1, 'rrattack': 0.25, 'rrlevel': 0.5},
    # saxophones / brass: the timbre changes too much across the registers to borrow
    'reed': {'rrpitch': 3, 'rrtone': 1, 'rrattack': 0.3, 'rrstart': 30},
    'brass': {'rrpitch': 3, 'rrtone': 1, 'rrattack': 0.3, 'rrstart': 30},
    # Rhodes / e-piano tines
    'rhodes': {'rrpitch': 2, 'rrtone': 0.5, 'rrattack': 0.2},   # rrborrow 0.3 in the plan: unchecked, left out
}

# pianos / guitars / mallets with 2-5 velocity layers: blend the neighbouring layers in the attack; many-layer packs
# (Salamander's 16) keep 'velocity' and take only VELTONE
BLEND = {'layers': 'blend', 'blendwidth': 0.4, 'veltone': 0.5}
VELTONE = {'veltone': 0.5}
