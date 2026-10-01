"""The production role briefs in roles/: every file has the header block, the names are unique and match the file,
and docs/ROLES.md / CLAUDE.md point to each of them."""

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ROLES = REPO / 'roles'
HEADER = ('Role', 'When to use', 'Inputs', 'Deliverable')
EXPECTED = {'producer', 'arranger', 'sound-designer', 'mix-engineer', 'mastering-engineer', 'a-and-r'}


def role_files():
    return sorted(ROLES.glob('*.md'))


class RoleFiles(unittest.TestCase):
    def test_the_expected_roles_exist(self):
        self.assertTrue(EXPECTED <= {p.stem for p in role_files()}, [p.stem for p in role_files()])

    def test_header_block(self):
        for p in role_files():
            lines = p.read_text(encoding='utf-8').splitlines()
            self.assertTrue(lines and lines[0].startswith('# '), f"{p.name}: starts with a '# Title'")
            head = '\n'.join(lines[:25])
            positions = []
            for key in HEADER:
                m = re.search(rf'^> \*\*{re.escape(key)}:\*\* \S', head, re.M)
                self.assertIsNotNone(m, f"{p.name}: header line '> **{key}:** ...' missing in the first lines")
                positions.append(m.start())
            self.assertEqual(positions, sorted(positions), f"{p.name}: header order is {', '.join(HEADER)}")

    def test_names_unique_and_match_the_file(self):
        names = []
        for p in role_files():
            m = re.search(r'^> \*\*Role:\*\* ([a-z0-9-]+)', p.read_text(encoding='utf-8'), re.M)
            self.assertIsNotNone(m, p.name)
            self.assertEqual(m.group(1), p.stem, f"{p.name}: the Role name is the file name")
            names.append(m.group(1))
        self.assertEqual(len(names), len(set(names)))

    def test_every_role_has_must_not_and_checklist(self):
        for p in role_files():
            text = p.read_text(encoding='utf-8')
            self.assertIn('## Must not', text, p.name)
            self.assertIn('HUMAN_FEEDBACK', text, p.name)

    def test_overview_and_claude_md_point_to_every_role(self):
        overview = (REPO / 'docs' / 'ROLES.md').read_text(encoding='utf-8')
        for p in role_files():
            self.assertIn(f'roles/{p.name}', overview, f"docs/ROLES.md does not list {p.name}")
        claude = (REPO / 'CLAUDE.md').read_text(encoding='utf-8')
        self.assertIn('roles/producer.md', claude)
        self.assertIn('docs/ROLES.md', claude)


if __name__ == '__main__':
    unittest.main()
