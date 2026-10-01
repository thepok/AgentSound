import json
import pathlib
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from agentsound import cli, delivery
from agentsound.theory import Key


def render_with(tracks=(), buses=(), master=None):
    return {'format': 'agentsound.render', 'version': 1, 'tempo': 120, 'lengthBeats': 4, 'tracks': list(tracks),
            'buses': list(buses), 'master': master or {'fx': []}}


class Settings(unittest.TestCase):
    def test_metadata_strict(self):
        self.assertEqual(delivery.check_metadata({'artist': ' X ', 'year': 2026}), {'artist': 'X', 'year': 2026})
        with self.assertRaisesRegex(delivery.DeliveryError, "unknown key"):
            delivery.check_metadata({'artsit': 'X'})
        with self.assertRaises(delivery.DeliveryError):
            delivery.check_metadata({'year': '2026'})
        with self.assertRaises(delivery.DeliveryError):
            delivery.check_metadata({'title': ''})

    def test_cover_strict(self):
        self.assertIsNone(delivery.check_cover(False))
        self.assertEqual(delivery.check_cover(None), {})
        self.assertEqual(delivery.check_cover({'palette': ['ff0000', '#00ff00']})['palette'], '#ff0000,#00ff00')
        with self.assertRaisesRegex(delivery.DeliveryError, 'unknown style'):
            delivery.check_cover({'style': 'baroque'})
        with self.assertRaises(delivery.DeliveryError):
            delivery.check_cover({'stlye': 'jazz'})
        with self.assertRaises(delivery.DeliveryError):
            delivery.check_cover({'palette': ['#12']})
        with self.assertRaises(delivery.DeliveryError):
            delivery.check_cover({'size': 50})
        with self.assertRaisesRegex(delivery.DeliveryError, 'generated cover'):
            delivery.check_cover({'file': 'art.jpg', 'palette': 'ember'})
        self.assertEqual(delivery.check_cover({'file': 'art.jpg', 'style': 'jazz'})['style'], 'jazz')

    def test_id3_key(self):
        self.assertEqual(delivery.id3_key(Key('A minor')), 'Am')
        self.assertEqual(delivery.id3_key(Key('F# dorian')), 'F#m')
        self.assertEqual(delivery.id3_key(Key('Eb major')), 'Eb')
        self.assertEqual(delivery.id3_key('C lydian'), 'C')
        self.assertEqual(delivery.id3_key('Dm'), 'Dm')

    def test_cover_spec_defaults(self):
        spec = delivery.cover_spec('Night Drive', 7, {}, {}, 'darksynth')
        self.assertEqual((spec['style'], spec['title'], spec['subtitle'], spec['seed']), ('darksynth', 'Night Drive', 'AgentSound', 7))
        self.assertEqual(delivery.cover_spec('T', 1, {'genre': 'Cool Jazz'}, {}, 'default')['style'], 'jazz')
        self.assertEqual(delivery.cover_spec('T', 1, {}, {}, None)['style'], 'synthwave')
        own = delivery.cover_spec('T', 1, {'artist': 'Me'}, {'style': 'pop', 'title': 'X', 'seed': 3}, None)
        self.assertEqual((own['style'], own['title'], own['subtitle'], own['seed']), ('pop', 'X', 'Me', 3))

    def test_profile_defaults(self):
        self.assertEqual(delivery.default_style({}, 'jazz'), 'jazz')
        self.assertEqual(delivery.default_style({}, 'film'), 'classical')
        self.assertEqual(delivery.default_style({'genre': 'Indie Rock'}, 'default'), 'rock')
        # An own cover file still picks the genre tag from the profile, not 'synthwave'.
        self.assertEqual(delivery.cover_spec('T', 1, {}, {'file': 'x.jpg'}, 'classical')['style'], 'classical')
        self.assertEqual(delivery.tags('T', 80, 'C', {}, 'classical', profile='film')['genre'], 'Soundtrack')

    def test_tags(self):
        t = delivery.tags('Night Drive', 104.4, Key('D minor'), {'album': 'A', 'comment': 'hi'}, 'outrun', 'Sounds: x')
        self.assertEqual(t['title'], 'Night Drive')
        self.assertEqual(t['artist'], 'AgentSound')
        self.assertEqual(t['genre'], 'Synthwave')
        self.assertEqual(t['TBPM'], '104')
        self.assertEqual(t['TKEY'], 'Dm')
        self.assertEqual(t['comment'], 'hi | Sounds: x')
        self.assertEqual(delivery.tags('T', 90, Key('C'), {'genre': 'Lo-fi'}, 'jazz')['genre'], 'Lo-fi')


class Credits(unittest.TestCase):
    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_credits_'))
        self.samples = self.dir / 'samples'
        self.assets = self.dir / 'assets'
        (self.assets / 'soundfonts').mkdir(parents=True)
        for pid, lic, attr in (('cc0kit', 'CC0-1.0', 'Someone'), ('bykit', 'CC-BY-4.0', 'Jane Doe'),
                               ('sakeys', 'CC-BY-SA-3.0', 'Glen'), ('nckit', 'CC-BY-NC-4.0', 'Nc Person'),
                               ('noredist', 'Royalty-free-no-redistribution', ''), ('huh', 'Unclear-free-download', '')):
            (self.samples / pid).mkdir(parents=True)
            src = {'id': pid, 'title': pid.upper(), 'license': lic, 'licenseUrl': 'https://example.org/' + pid}
            if attr:
                src['attribution'] = attr
            (self.samples / pid / 'SOURCE.json').write_text(json.dumps(src), encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def collect(self, render):
        return delivery.collect_credits(render, samples=self.samples, assets=self.assets, manifest={'mani': {'title': 'Manifest Pack', 'license': 'CC0-1.0'}})

    def test_classes(self):
        self.assertEqual(delivery.license_class('CC0-1.0'), 'free')
        self.assertEqual(delivery.license_class('CC-BY-4.0'), 'attribution')
        self.assertEqual(delivery.license_class('CC-BY-SA-3.0'), 'sharealike')
        self.assertEqual(delivery.license_class('CC-BY-NC-SA-3.0-music-ok'), 'nc')
        self.assertEqual(delivery.license_class('Freeware-no-redistribution'), 'noredist')
        self.assertEqual(delivery.license_class('Unclear-free-download'), 'unclear')
        self.assertEqual(delivery.license_class('CC-BY-SA-unverified'), 'unclear')
        self.assertEqual(delivery.license_class('GPL-3.0-with-FreePats-exception'), 'free')
        self.assertEqual(delivery.license_class('Royalty-free'), 'free')

    def test_every_reference_kind(self):
        abs_pack = str(self.samples / 'nckit' / 'Kick.wav')
        render = render_with(
            tracks=[
                {'id': 'a', 'instrument': {'type': 'sampler', 'params': {'samples': {'dir': 'samples/cc0kit/kit'}}}},
                {'id': 'b', 'instrument': {'type': 'sampler', 'params': {'samples': [
                    {'file': 'samples/bykit/C4.wav', 'root': 60}, {'file': abs_pack}]}}},
                {'id': 'c', 'instrument': {'type': 'sf2', 'params': {'preset': 'Grand Piano'}}},
                {'id': 'd', 'instrument': {'type': 'sf2', 'params': {'file': 'samples/sakeys/Keys.sf2', 'preset': '0:0'}}},
                {'id': 'e', 'instrument': {'type': 'dx7', 'params': {'voice': 'BRASS 1/2'}},
                 'fx': [{'type': 'convolver', 'params': {'ir': 'samples/noredist/hall.wav', 'mix': 0.3}}]},
                {'id': 'f', 'instrument': {'type': 'sampler', 'params': {'samples': {'file': 'samples/mani/x.wav'}}}},
            ],
            buses=[{'id': 'hall', 'fx': [{'type': 'convolver', 'params': {'ir': 'samples/huh/room.wav'}}]}])
        cr = self.collect(render)
        ids = [s['id'] for s in cr['sources']]
        for pid in ('cc0kit', 'bykit', 'nckit', 'sakeys', 'noredist', 'huh', 'mani', 'GeneralUser-GS.sf2'):
            self.assertIn(pid, ids)
        self.assertNotIn('BRASS 1/2', ids)             # a DX7 voice name is not a path
        self.assertEqual(len(ids), 8)
        warned = ' '.join(cr['warnings'])
        for pid in ('nckit', 'noredist', 'huh'):
            self.assertIn(pid, warned)
        self.assertNotIn('cc0kit', warned)
        attr = ' '.join(cr['attributions'])
        self.assertIn('Jane Doe', attr)
        self.assertIn('share-alike', attr)
        self.assertIn('Nc Person', attr)
        self.assertNotIn('Someone', attr)
        self.assertIn('GeneralUser GS', cr['comment'])
        text = delivery.credits_text(cr, 'Song', 'Me')
        self.assertIn('Required attributions', text)
        self.assertIn('Check before publishing', text)

    def test_every_cc_by_license_needs_attribution(self):
        for lic, cls in (('CC BY-SA 3.0', 'sharealike'), ('Creative Commons Attribution-ShareAlike 4.0', 'sharealike'),
                         ('cc_by_4.0', 'attribution'), ('BY-SA 4.0', 'sharealike'),
                         ('Creative Commons Attribution-NonCommercial 4.0', 'nc'), ('CC0 1.0', 'free')):
            self.assertEqual(delivery.license_class(lic), cls, lic)
        # every CC-BY* pack of the manifest (the AVL Buskman's Holiday percussion: CC-BY-SA, Glen MacArthur / AV
        # Linux) lands in the required attributions when a render uses it - through its SOURCE.json or the manifest
        from agentsound import library
        packs = [p for p in library.load_manifest() if 'cc-by' in p.get('license', '').lower()]
        self.assertTrue(any(p['id'] == 'avl-buskmans-holiday' for p in packs))
        render = render_with(tracks=[{'id': f't{i}', 'instrument': {'type': 'sampler', 'params': {
            'samples': [{'file': f"samples/{p['id']}/x.wav"}]}}} for i, p in enumerate(packs)])
        cr = delivery.collect_credits(render, samples=self.dir / 'none', assets=self.assets,
                                      manifest={p['id']: p for p in packs})
        self.assertEqual(len(cr['attributions']), len(packs))
        busk = next(a for a in cr['attributions'] if 'Buskman' in a)
        self.assertIn('Glen MacArthur', busk)
        self.assertIn('share-alike', busk)

    def test_busk_kit_patch_is_credited(self):
        from agentsound import Song, library
        if not (library.SAMPLES / 'avl-buskmans-holiday' / 'SOURCE.json').is_file():
            self.skipTest('avl-buskmans-holiday not installed')
        s = Song('t', tempo=100)
        s.section('a', bars=1)
        s.track('perc', 'sampled/busk_kit').note(42, 0, 0.5)
        cr = delivery.collect_credits(s.compile())
        self.assertTrue(any('Glen MacArthur' in a and 'CC-BY-SA' in a for a in cr['attributions']), cr['attributions'])

    def test_loose_file_in_samples_is_no_pack(self):
        cr = self.collect(render_with(tracks=[{'id': 'a', 'instrument': {'type': 'sampler', 'params': {
            'samples': [{'file': 'samples/pad.wav'}, {'file': str(self.samples / 'riser.wav')}]}}}]))
        self.assertEqual(sorted(s['kind'] for s in cr['sources']), ['file', 'file'])
        self.assertEqual(sorted(s['title'] for s in cr['sources']), ['pad.wav', 'riser.wav'])

    def test_sfz_generators_are_no_files(self):
        """'*silence' (Swirly Drums' stir mute zones), '*sine', '*noise' are sfz generators, not an unknown file."""
        cr = self.collect(render_with(tracks=[{'id': 'a', 'instrument': {'type': 'sampler', 'params': {
            'samples': [{'file': '*silence'}, {'file': '*sine'}, {'file': 'samples/pad.wav'}]}}}]))
        self.assertEqual([s['title'] for s in cr['sources']], ['pad.wav'])

    def test_synth_only_and_unknown(self):
        cr = self.collect(render_with(tracks=[{'id': 'a', 'instrument': {'type': 'va', 'params': {}}}]))
        self.assertEqual(cr['sources'], [])
        self.assertIn('synthesised only', delivery.credits_text(cr, 'S', 'A'))
        cr = self.collect(render_with(tracks=[{'id': 'a', 'instrument': {'type': 'sampler', 'params': {
            'samples': {'dir': 'samples/notinstalled/x'}}}}]))
        self.assertEqual(cr['sources'][0]['class'], 'unclear')
        self.assertTrue(cr['warnings'])


class BuildDelivery(unittest.TestCase):
    """End to end: build writes credits.txt, cover.png and a tagged mp3 (needs the engine and ffmpeg)."""

    SONG = '''
from agentsound import *

METADATA = {'title': 'Delivery Übung', 'artist': 'Test Artist', 'year': 2025}
COVER = {'style': 'jazz', 'size': 256}

def build():
    s = Song('Delivery Test', tempo=96, key='G minor', seed=4)
    a = s.section('a', bars=1)
    s.track('keys', inst.va()).play(s.prog('i').block(), a)
    s.master.add(fx.limiter())
    return s
'''

    def setUp(self):
        try:
            self.engine = cli.find_engine()
        except cli.CliError:
            self.skipTest('engine not built')
        self.ff = cli.find_ffmpeg()
        self.probe = delivery.find_ffprobe(self.ff)
        if not self.ff or not self.probe:
            self.skipTest('ffmpeg/ffprobe not found')
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix='agentsound_delivery_'))
        (self.dir / 'song.py').write_text(self.SONG, encoding='utf-8')

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_build_tags_cover_credits(self):
        import contextlib
        import io
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            code = cli.main(['build', str(self.dir)])
        self.assertEqual(code, 0, out.getvalue())
        o = self.dir / 'out'
        self.assertTrue((o / 'credits.txt').is_file())
        self.assertTrue((o / 'cover.png').is_file())
        info = delivery.probe_tags(self.probe, o / 'mix.mp3')
        t = info['tags']
        self.assertEqual(t['title'], 'Delivery Übung')
        self.assertEqual(t['artist'], 'Test Artist')
        self.assertEqual(t['genre'], 'Jazz')
        self.assertEqual(t['tbpm'], '96')
        self.assertEqual(t['tkey'], 'Gm')
        self.assertTrue(t['date'].startswith('2025'))
        self.assertTrue(info['cover'])
        # The cover is reused when nothing changed.
        stamp = (o / 'cover.png').stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            cli.main(['build', str(self.dir), '--no-mp3'])
        self.assertEqual((o / 'cover.png').stat().st_mtime_ns, stamp)

    def test_preview_title_and_no_cover(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['build', str(self.dir), '--no-mp3']), 0)
        o = self.dir / 'out'
        self.assertTrue((o / 'cover.png').is_file())
        # COVER = False: no picture in the mp3 and no stale cover.png of the earlier build; a section preview keeps
        # METADATA's title and says which section it is.
        (self.dir / 'song.py').write_text(self.SONG.replace("COVER = {'style': 'jazz', 'size': 256}", 'COVER = False'),
                                          encoding='utf-8')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(cli.main(['build', str(self.dir), '--section', 'a']), 0, out.getvalue())
        self.assertFalse((o / 'cover.png').exists())
        mp3 = next(o.glob('**/a/mix.mp3'))
        info = delivery.probe_tags(self.probe, mp3)
        self.assertEqual(info['tags']['title'], 'Delivery Übung (a)')
        self.assertFalse(info['cover'])

    def test_bad_metadata_rejected_before_render(self):
        (self.dir / 'song.py').write_text(self.SONG.replace("'year': 2025", "'yaer': 2025"), encoding='utf-8')
        import contextlib
        import io
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            code = cli.main(['check', str(self.dir), '--engine', str(self.dir / 'missing.exe')])
        self.assertEqual(code, 1)
        self.assertIn('yaer', err.getvalue())


if __name__ == '__main__':
    unittest.main()
