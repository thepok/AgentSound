"""Automatic theme accents must not become a full attack in every doubling."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from agentsound.bandlib import orchestration as orc
from agentsound.endless import symphony


class ThemeAccents(unittest.TestCase):
    def fixture(self, peak=False, bass_theme=False, count=6):
        score = orc.OrchScore()
        b = score.block('theme', 0, 8, peak=peak)
        fn = 'bass' if bass_theme else 'melody'
        notes = [(0, 1, 60), (2, 1, 62), (4, 1, 64)]
        b.add(orc.Line(fn, notes, meta={'sf': [0, 2]}))
        parts = [orc.Part('leader', b.name, fn, '', notes, 'sustain', 0, True, sf=(0, 2))]
        parts += [orc.Part(f'double{i}', b.name, 'doubling', fn, notes, 'sustain', 0, True,
                           sf=(0, 2)) for i in range(count)]
        parts += [orc.Part('support', b.name, 'pedal', '', notes, 'sustain', 0, False, sf=(0, 2, 4))]
        return score, orc.Orchestration(parts)

    def test_leader_support_budget_and_explicit_accent(self):
        for count in (1, 3, 8):
            for bass_theme in (False, True):
                score, plan = self.fixture(count=count, bass_theme=bass_theme)
                before = copy.deepcopy(plan)
                boosts = symphony._theme_accents(plan, score)
                self.assertEqual(plan.parts[0].sf, (0, 2))
                self.assertTrue(all(not p.sf for p in plan.parts[1:-1]))
                self.assertEqual(plan.parts[-1].sf, (4,))
                self.assertLessEqual(sum(b[0] for b in boosts.values()), 8)
                self.assertTrue(all(0 < b[0] <= 4 for b in boosts.values()))
                self.assertEqual([p.notes for p in plan.parts], [p.notes for p in before.parts])
                self.assertEqual([p.art for p in plan.parts], [p.art for p in before.parts])

    def test_peak_keeps_one_tutti_not_a_whole_pumping_phrase(self):
        score, plan = self.fixture(peak=True)
        symphony._theme_accents(plan, score)
        self.assertTrue(all(0 in p.sf for p in plan.parts))
        self.assertEqual(sum(2 in p.sf for p in plan.parts), 1)

    def test_without_automatic_marks_authored_accents_are_untouched(self):
        score, plan = self.fixture()
        score.blocks[0].lines[0].meta.clear()
        before = copy.deepcopy(plan)
        self.assertEqual(symphony._theme_accents(plan, score), {})
        self.assertEqual(plan, before)


class ExposedAnswers(unittest.TestCase):
    def part(self, role, fn, notes, block='dialogue'):
        return orc.Part(role, block, fn, '', notes, 'sustain', 0, True)

    def test_answer_takes_foreground_only_in_melody_rests(self):
        plan = orc.Orchestration([
            self.part('violins1', 'melody', [(0, 1, 72), (2, 1, 74)]),
            self.part('oboe_solo', 'counter', [(0, .5, 67), (1, 1, 69), (3, 1, 71)]),
            self.part('horns', 'doubling', [(1, 1, 69)]),
        ])
        self.assertEqual(symphony._exposed_answers(plan), {1: {1, 3}})

    def test_partial_overlap_or_another_melody_keeps_counter_balance(self):
        plan = orc.Orchestration([
            self.part('violins1', 'melody', [(0, 1, 72), (2, 1, 74)]),
            self.part('flutes', 'melody', [(1, .5, 76)]),
            self.part('oboe_solo', 'counter', [(.5, 1, 67), (1, 1, 69), (3, 1, 71)]),
        ])
        self.assertEqual(symphony._exposed_answers(plan), {2: {3}})

    def test_other_blocks_and_unrelated_counterparts_do_not_trigger(self):
        plan = orc.Orchestration([
            self.part('violins1', 'melody', [(0, 1, 72)], block='other'),
            self.part('clarinet_solo', 'counter', [(1, 1, 67)]),
        ])
        self.assertEqual(symphony._exposed_answers(plan), {})


if __name__ == '__main__':
    unittest.main()
