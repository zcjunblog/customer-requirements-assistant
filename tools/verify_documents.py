"""Render fixture DOCX files using the caller-supplied document runtime."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skill/customer-requirements-assistant/scripts'))
from intake import ingest
from render import render
p=argparse.ArgumentParser(); p.add_argument('--renderer',required=True); p.add_argument('--fontconfig')
a=p.parse_args(); env=os.environ.copy()
if a.fontconfig: env['FONTCONFIG_FILE']=a.fontconfig
results=[]
for folder in sorted((ROOT/'tests/fixtures').iterdir()):
    result=render(json.loads((folder/'expected.json').read_text()),json.loads((folder/'sources.json').read_text()),ROOT/'outputs/verified-examples'/folder.name,'required')
    dest=ROOT/'outputs/verified-pages'/folder.name
    run=subprocess.run([sys.executable,a.renderer,str(Path(result['directory'])/'需求确认书.docx'),'--output_dir',str(dest),'--emit_pdf'],env=env,capture_output=True,text=True)
    dest.mkdir(parents=True,exist_ok=True); (dest/'render.log').write_text(run.stdout+'\n'+run.stderr)
    if run.returncode: raise RuntimeError(run.stdout+run.stderr)
    bundle=ingest([dest/'需求确认书.pdf'])
    assert bundle['sources'][0]['status']=='ok'
    assert any('需求确认' in s['text'] for s in bundle['sources'][0]['segments']), 'PDF中文文本回读失败'
    results.append({'case':folder.name,'docx_directory':str(Path(result['directory']).relative_to(ROOT)),
                    'pages':len(list(dest.glob('page-*.png'))),'pdf_text_intake':'passed','visual_review':'pending'})
    print(folder.name,'render and PDF text passed',flush=True)
(ROOT/'evidence/document-renders.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
