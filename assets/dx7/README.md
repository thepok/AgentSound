# DX7 ROM banks (not included)

The `dx7` instrument (the MSFA FM core in `third_party/msfa/`) plays the voices of the original Yamaha DX7
factory ROM cartridges by name (`inst.dx7('E.PIANO 1')`, `'rom1a:10'`, `'rom3a:E.PIANO 1'`). Those voice banks are
Yamaha's and are **not distributed with this repository**. Without them the DX7 voices are unavailable:

- `python -m agentsound dx7`, `catalog` and `find` say "no DX7 banks installed - see assets/dx7/README.md";
- a song, patch or audition that uses a DX7 voice (`inst.dx7(...)`, the DX7-based `synthwave/...` patches, a stack
  with a DX7 layer, the song template's keys) fails validation with that hint;
- the tests skip their DX7 checks (printed as `SKIP`).

Everything else (va, sf2, samplers, drums, effects, analysis) works without them.

## Installing

Place the 8 factory ROM cartridges as 32-voice bulk-dump SysEx files in this folder, named exactly:

| file | cartridge |
|---|---|
| `rom1a.syx` | ROM1A (voices 1-32: BRASS 1, ..., E.PIANO 1 at 11, ...) |
| `rom1b.syx` | ROM1B |
| `rom2a.syx` | ROM2A |
| `rom2b.syx` | ROM2B |
| `rom3a.syx` | ROM3A |
| `rom3b.syx` | ROM3B |
| `rom4a.syx` | ROM4A |
| `rom4b.syx` | ROM4B |

Each file is a standard DX7 32-voice bulk dump of exactly **4104 bytes** (`F0 43 0n 09 20 00`, 4096 bytes of packed
voice data, checksum, `F7`); the engine verifies framing and checksum on load. The bank name is the lower-case file
stem, so other cartridges work as well (any `*.syx` in this folder is loaded in file-name order; a bare voice name
resolves to the first bank that has it). The patches and songs of this repository expect the factory set above.

Check the installation with `python -m agentsound dx7` (256 voices) or `build/agentsound.exe dx7 piano`.

For reference, the SHA-256 of the files this project was developed with:

```
91416e81d0fad931f6c7b5dc5bcfd7b7c48f5340b3753b7d3bf99f439fdd104d  rom1a.syx
15c817360f56f7bd0e269575291cbfac91a45f0ee6125479abfdc4d69a560b4b  rom1b.syx
5254f04b674aa872e8f09a8b5828cc5454f79495e4aa5bbba8a3cac3c606a699  rom2a.syx
1efb00f24e28df03470ebca19cadd63cb98b5f099b5e7502dd6f232ddb23af54  rom2b.syx
157b71a53a9881c8209bb5de57f6d9519d5f43cb7cae591c4606e7fb52ff9d86  rom3a.syx
0f21e5f28f0b6c77ef5cef839bb244d8946b2ee2243e88e1ba19f46c4aa85e30  rom3b.syx
b34f01b5ee8690e5b45351a960eed3dea2fdd72318b419303d23f07d5e411fda  rom4a.syx
d4eae13570569e27894a21593a9c591a474a1b945c13c3a0a933c42dee684c0b  rom4b.syx
```

`*.syx` files in this folder are gitignored.
