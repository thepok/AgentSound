# Singing voicebanks

The licensed DiffSinger voicebanks `agentsound.singer` sings with. Only `manifest.json` (and this file) are in git:
the banks themselves are downloaded by hand from their official sources and never committed - their licences forbid
redistribution. `python -m agentsound voicebanks` lists them, says which are installed and shows their licences;
`--check` loads each one in the WSL backend.

| id | voice | official source | licence (short) |
|---|---|---|---|
| `hanami` | Hoshino Hanami ~AI❤dol~ v1.0 by Lotte V - female pop soprano | the download link on https://diffsinger.miraheze.org/wiki/Hanami_Hoshino (MediaFire) | voicebank: commercial use allowed, credit Lotte V, no reupload, no political / hateful use; its AI❤dolGAN vocoder CC BY-NC-SA 4.0 |
| `tiger` | TIGER for DiffSinger v106 by tigermeat - male pop / rock | https://github.com/spicytigermeat/tiger_diffsinger/releases (v106) | non-commercial (CC BY-NC-ND 4.0 + Commons Clause; a commercial licence is sold by the rights holder); never modify or redistribute |

**Install** a bank so that `assets/voices/<id>/dsconfig.yaml` exists:

- hanami: unpack the zip and move the contents of its folder `Hoshino Hanami ~AIdol~ for DiffSinger v1.0/` into
  `assets/voices/hanami/`.
- tiger: unpack the release zip, then unpack `Voice Library/TIGER_DS_v106.zip` into `assets/voices/tiger/`.

`$AGENTSOUND_VOICES` points the system at another folder (one copy for every git worktree). A song sung with a bank
caches its takes in `songs/<slug>/samples/vocals/<id>/` with a `SOURCE.json` (url, licence, attribution): the build's
`out/credits.txt` names the voice and its terms, and NC voices are flagged like NC sample packs.

**The consent rule**: no cloning of real singers. A manifest entry says what gives the right to synthesise the voice
(`consent`: `licensed`, `synthetic` or `own` - the user's own voice); anything else is refused. The backend (WSL venv,
onnxruntime) is described in docs/COMPOSE_API.md "Vocals".
