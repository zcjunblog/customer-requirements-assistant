"""Extract both current release profiles and run every synthetic fixture independently."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile
from distribution import ROOT, SOURCE, NAME

version = (SOURCE / 'VERSION').read_text().strip()
release = ROOT / 'releases' / version
manifest = json.loads((release / 'manifest.json').read_text())
results = {'version': version, 'packages': []}
with tempfile.TemporaryDirectory(prefix='agent skill smoke ') as td:
    for package in manifest['packages']:
        archive = release / package['archive']
        assert hashlib.sha256(archive.read_bytes()).hexdigest() == package['sha256']
        root = Path(td) / package['profile']
        root.mkdir()
        with zipfile.ZipFile(archive) as z:
            assert z.testzip() is None
            for n in z.namelist():
                assert '..' not in Path(n).parts and n.startswith(NAME + '/')
            z.extractall(root)
        cli = root / NAME / 'scripts/requirements_tool.py'
        record = {'profile': package['profile'], 'sha256': package['sha256'], 'cases': []}
        for case in sorted((ROOT / 'tests/fixtures').iterdir()):
            sources = root / (case.name + ' sources.json')
            commands = [
                ['ingest', str(case / 'input.txt'), '--out', str(sources)],
                ['validate', '--model', str(case / 'expected.json'), '--sources', str(sources)],
                ['render', '--model', str(case / 'expected.json'), '--sources', str(sources), '--out', str(root / '交付'), '--docx', 'auto'],
            ]
            runs = []
            for args in commands:
                p = subprocess.run([sys.executable, str(cli)] + args, cwd=root, capture_output=True, text=True)
                assert p.returncode == 0, (args, p.stdout, p.stderr)
                runs.append(json.loads(p.stdout))
            assert runs[-1]['skill_version'] == version
            assert (Path(runs[-1]['directory']) / '需求确认书.md').is_file()
            record['cases'].append({'name': case.name, 'commands': 'ingest/validate/render', 'word': runs[-1]['word']})
        results['packages'].append(record)
folder = ROOT / 'evidence' / version
folder.mkdir(exist_ok=True)
(folder / 'archive-smoke.json').write_text(json.dumps(results, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(results, ensure_ascii=False, indent=2))
