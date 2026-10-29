"""Endless page: the content hashes of the samples.

Run after any change under music/endless/samples/: writes samples/index.json {set: {file: sha1[:8]}} for the sets
beste / spar / orch / ir (the orchestra's index.json included) and patches `const SV = '...'` in app.js with the hash
of that index. The page fetches samples/<set>/<file>?h=<hash> cache-first (Cache Storage "endless-samples"), so an
update fetches only the files whose content changed; entries no index names any more are pruned by the page.
"""
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path(__file__).resolve().parents[2] / 'web'
S = ROOT / 'samples'
SETS = ('beste', 'spar', 'orch', 'ir')

for old in (S / 'beste' / 'index.json', S / 'spar' / 'index.json'):   # (the name lists of the first offline version)
    if old.exists():
        old.unlink()
index = {}
for st in SETS:
    index[st] = {p.name: hashlib.sha1(p.read_bytes()).hexdigest()[:8]
                 for p in sorted((S / st).iterdir()) if p.is_file() and p.suffix in ('.opus', '.wav', '.json')}
text = json.dumps(index, separators=(',', ':'), sort_keys=True)
(S / 'index.json').write_text(text, encoding='utf-8')
sv = hashlib.sha1(text.encode()).hexdigest()[:10]

app = ROOT / 'app.js'
src = app.read_text(encoding='utf-8')
new, n = re.subn(r"const SV = '[0-9a-f]*';", f"const SV = '{sv}';", src)
if n != 1:
    sys.exit('app.js: no `const SV = ...;` line')
if new != src:
    app.write_text(new, encoding='utf-8')
print(f'SV={sv}', {st: len(v) for st, v in index.items()}, f'index {len(text) / 1e3:.0f} KB')
