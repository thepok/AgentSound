"""Opt-in performance correction: replay stability, composition retained, analysis is not a gate."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from agentsound import endless
from agentsound.bandlib import orchestra as orch
from agentsound.endless import genres, symphony


class Switch(unittest.TestCase):
    def tearDown(self):
        genres.symphony_pumping(False)

    @unittest.skipUnless(orch.installed('sso') and orch.installed('vsco2-ce'), 'orchestral samples unavailable')
    def test_off_replay_and_composition(self):
        g = genres.get('orchestra-symphonic')
        genres.symphony_pumping(False)
        tune = endless.compose(g, 4242)
        before_song = endless.song(tune)
        before = before_song.compile()
        genres.symphony_pumping(True)
        after_song = endless.song(tune)
        after = after_song.compile()
        self.assertNotEqual(before, after)
        self.assertEqual(before['master'], after['master'])
        self.assertEqual(before['tempoMap'], after['tempoMap'])
        self.assertEqual(before_song.orch_score.to_dict(), after_song.orch_score.to_dict())
        self.assertEqual(before_song.orchestration.parts, after_song.orchestration.parts)
        self.assertEqual(after, endless.song(tune).compile())
        genres.symphony_pumping(False)
        self.assertEqual(before, endless.song(tune).compile())

    def test_film_is_unchanged(self):
        # The switch touches only the symphonic builder, including its genre configuration.
        import copy
        film = copy.deepcopy(genres.get('orchestra-film').band)
        genres.symphony_pumping(True)
        self.assertEqual(film, genres.get('orchestra-film').band)
        self.assertIsNot(symphony.PUMPING, symphony.PUMPING_ON)


try:
    import numpy as np
    import scipy
except ImportError:
    np = None


@unittest.skipIf(np is None, 'offline pumping diagnostic requires numpy/scipy')
class Analysis(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('pumping_diagnostic', ROOT / 'tools' / 'pumping.py')
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)

    def test_reversing_gain_is_detected_but_a_fade_and_silence_are_not(self):
        t = np.arange(300) * .1 + .2
        levels = -25 + 4 * np.sin(2 * np.pi * t / 3)
        m = self.tool.measure(t, levels)
        self.assertGreaterEqual(m['candidateCount'], 8)
        self.assertGreater(m['candidates'][0]['swingDb'], 7)
        for db in [np.full(len(t), -25), np.full(len(t), -150), np.linspace(-15, -50, len(t))]:
            self.assertEqual(self.tool.measure(t, db)['candidateCount'], 0)
        self.assertIn('Candidates only', m['interpretation'])

    def test_short_input_and_time_contract(self):
        self.assertEqual(self.tool.measure([], [])['candidateCount'], 0)
        with self.assertRaises(ValueError):
            self.tool.measure([0, .2], [-20, -20])
        with self.assertRaises(ValueError):
            self.tool.measure([0], [float('nan')])


if __name__ == '__main__':
    unittest.main()
