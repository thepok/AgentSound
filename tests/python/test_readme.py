"""README.md is the central overview: everything user-facing must at least be named there.

Fails with 'document X in README.md' when an engine module type, a Python helper module, a band preset, a role
brief, an analysis profile, a CLI command, a recipe, a patch family or a hero preset exists but README.md does not
mention it. Names are matched as `code` (backticks), role and recipe files by their path.
"""

import re
import unittest
from pathlib import Path

from agentsound import bands, catalog, cli, heroes, patches

REPO = Path(__file__).resolve().parents[2]
README = REPO / 'README.md'


def readme() -> str:
    return README.read_text(encoding='utf-8')


def code_names(text: str) -> set[str]:
    """Every `code` span of the text, plus its words (so `samples fetch ID` counts for samples)."""
    out = set()
    for span in re.findall(r'`([^`\n]+)`', text):
        out.add(span.strip())
        out.update(re.findall(r'[A-Za-z0-9_.\-/]+', span))
    return out

def _tracked(path) -> bool:
    """True when git tracks the file (untracked work-in-progress files of other sessions are not part of the system)."""
    import subprocess
    try:
        r = subprocess.run(['git', 'ls-files', '--error-unmatch', str(path)], cwd=REPO, capture_output=True)
    except OSError:
        return True
    return r.returncode == 0



class ReadmeCoversTheSystem(unittest.TestCase):
    def setUp(self):
        self.assertTrue(README.is_file(), 'README.md is missing at the repo root')
        self.text = readme()
        self.code = code_names(self.text)

    def assert_named(self, names, what: str):
        missing = sorted(n for n in names if n not in self.code)
        self.assertFalse(missing, '\n'.join(f"document {what} `{n}` in README.md" for n in missing))

    def test_engine_modules(self):
        types = set(catalog.MODULES) | set(catalog.engine_modules())   # the engine's own list when it is built
        self.assert_named(types, 'the engine module')

    def test_helper_modules(self):
        self.assert_named(catalog.HELPER_MODULES, 'the helper module')

    def test_band_presets(self):
        library = [n for n in bands.list()                            # not presets other tests register
                   if getattr(bands.get(n).build, '__module__', '').startswith('agentsound.')]
        self.assertTrue(library, 'no band presets found')
        self.assert_named(library, 'the band preset')

    def test_analysis_profiles(self):
        self.assert_named(cli.ANALYSIS_PROFILES, 'the analysis profile')

    def test_cli_commands(self):
        sub = next(a for a in cli.build_parser()._actions if a.__class__.__name__ == '_SubParsersAction')
        self.assert_named(sub.choices, 'the CLI command (python -m agentsound ...)')

    def test_hero_presets(self):
        self.assert_named(heroes.presets(), 'the hero preset')

    def test_patch_families(self):
        source = ''.join(p.read_text(encoding='utf-8') for p in (REPO / 'agentsound' / 'patches').glob('*.py'))
        families = {n.split('/')[0] + '/' for n in patches.list('')}
        library = {f for f in families if re.search(rf"""['"]{re.escape(f)}""", source)}   # not test registrations
        self.assertTrue(library, 'no patch families found')
        self.assert_named(library, 'the patch family')

    def test_role_briefs(self):
        missing = [f"roles/{p.name}" for p in sorted((REPO / 'roles').glob('*.md'))
                   if f"roles/{p.name}" not in self.text]
        self.assertFalse(missing, '\n'.join(f"document the role {m} in README.md" for m in missing))

    def test_recipes(self):
        missing = [f"recipes/{p.name}" for p in sorted((REPO / 'recipes').glob('*.md')) if _tracked(p)
                   if f"recipes/{p.name}" not in self.text]
        self.assertFalse(missing, '\n'.join(f"document the recipe {m} in README.md" for m in missing))

    def test_reference_docs_are_linked(self):
        for doc in sorted((REPO / 'docs').glob('*.md')):
            self.assertIn(f"docs/{doc.name}", self.text, f"document docs/{doc.name} in README.md (link it)")

    def test_relative_links_resolve(self):
        for target in re.findall(r'\]\(([^)#\s]+)(?:#[^)]*)?\)', self.text):
            if '://' in target:
                continue
            self.assertTrue((REPO / target).exists(), f"README.md links to {target}, which does not exist")


if __name__ == '__main__':
    unittest.main()
