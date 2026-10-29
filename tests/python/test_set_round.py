"""songs/_blind/set_round.py's two-pass set judging (round p-div4): every judge twice, the second pass relabelled and
in the other reading order; a judge's choice counts only when both passes keep the same code."""
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parents[2] / 'songs' / '_blind'
sys.path.insert(0, str(HERE))

import set_round as sr  # noqa: E402


class TwoPass(unittest.TestCase):
    def test_second_pass_swaps_labels_and_order(self):
        for asg in ({'X': 'on', 'Y': 'off', 'first': 'X'}, {'X': 'off', 'Y': 'on', 'first': 'X'},
                    {'X': 'on', 'Y': 'off', 'first': 'Y'}):
            a2 = sr.second_pass(asg)
            self.assertEqual({a2['X'], a2['Y']}, {'on', 'off'})
            self.assertEqual(a2['X'], asg['Y'])                       # (relabelled)
            self.assertNotEqual(a2[a2['first']], asg[asg['first']])   # (the other code read first)

    def test_deal_judge_writes_both_passes(self):
        sets = {'on': [{'text': 'on piece'}], 'off': [{'text': 'off piece'}]}
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            kp = {'judges': {}}
            sr.deal_judge(kp, root, 'A', 'j1', sets, {'X': 'on', 'Y': 'off', 'first': 'X'}, 'BRIEF', 'LENS',
                          cleanse=True, two_pass=True)
            self.assertEqual(set(kp['judges']), {'j1', 'j1' + sr.P2})
            p2 = root / 'A' / ('j1' + sr.P2)
            self.assertEqual((p2 / 'set_X' / '01.txt').read_text(encoding='utf-8'), 'off piece')
            self.assertIn('notes_', (p2 / 'JUDGE.md').read_text(encoding='utf-8'))
            self.assertIn('A_j1__p2.md', (p2 / 'prompt.txt').read_text(encoding='utf-8'))

    def test_two_pass_lines_count_only_agreement(self):
        rows = [{'pair': 'A', 'judge': 'j1', 'keep': 'on', 'first_code': 'off'},
                {'pair': 'A', 'judge': 'j1' + sr.P2, 'keep': 'on', 'first_code': 'on'},     # (agrees: on)
                {'pair': 'A', 'judge': 'j2', 'keep': 'on', 'first_code': 'off'},
                {'pair': 'A', 'judge': 'j2' + sr.P2, 'keep': 'off', 'first_code': 'on'}]   # (the second read: no)
        txt = sr.two_pass_lines(rows, 'on')
        self.assertIn('agreement: 1 of 2', txt)
        self.assertIn('AGREED: on kept by 1 of 1', txt)


if __name__ == '__main__':
    unittest.main()
