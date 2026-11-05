"""Extract release into an unrelated path and execute all four synthetic fixtures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
archive=ROOT/'releases/0.1.0/customer-requirements-assistant-0.1.0.zip'
result={'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'cases':[]}
with tempfile.TemporaryDirectory(prefix='workbuddy skill smoke ') as td:
    root=Path(td)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for n in z.namelist(): assert '..' not in Path(n).parts and not n.startswith('/')
        z.extractall(root)
    cli=root/'customer-requirements-assistant/scripts/requirements_tool.py'
    for case in sorted((ROOT/'tests/fixtures').iterdir()):
        sources=root/(case.name+' sources.json')
        cmds=[['ingest',str(case/'input.txt'),'--out',str(sources)],
              ['validate','--model',str(case/'expected.json'),'--sources',str(sources)],
              ['render','--model',str(case/'expected.json'),'--sources',str(sources),'--out',str(root/'交付'),'--docx','auto']]
        runs=[]
        for args in cmds:
            p=subprocess.run([sys.executable,str(cli)]+args,cwd=root,capture_output=True,text=True)
            assert p.returncode==0,(args,p.stdout,p.stderr)
            runs.append(json.loads(p.stdout))
        out=Path(runs[-1]['directory'])
        assert (out/'需求确认书.md').is_file()
        result['cases'].append({'name':case.name,'commands':'ingest/validate/render','word':runs[-1]['word'],'files':len(list(out.iterdir()))})
(ROOT/'evidence/archive-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
