#!/usr/bin/env python3
"""Build a deterministic WorkBuddy skill archive; exclude repo/test/client data."""
import hashlib
import json
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NAME='customer-requirements-assistant'


def build():
    source=ROOT/'skill'/NAME
    text=(source/'SKILL.md').read_text(encoding='utf-8')
    assert text.startswith('---\n') and '\n---\n' in text[4:], 'Missing YAML frontmatter'
    front=text.split('---\n',2)[1]
    fields={m.group(1):m.group(2).strip() for m in re.finditer(r'^([a-z_]+):[ \t]*(.+)$',front,re.M)}
    for key in ('name','display_name','display_name_en','description','description_zh','description_en','version','author'):
        assert fields.get(key), 'Missing '+key
    assert fields['name']==NAME
    version=fields['version']; assert re.fullmatch(r'\d+\.\d+\.\d+',version)
    files=sorted(p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for p in files:
        assert not p.is_symlink(), 'Symlink forbidden'
        rel=p.relative_to(source)
        assert rel.parts[0] in ('SKILL.md','requirements-optional.txt','scripts','references','templates'),rel
        assert p.stat().st_size < 1024*1024
        if p.suffix=='.md':
            for link in re.findall(r'\]\(([^)]+)\)',p.read_text()):
                if not link.startswith(('https:','http:','#')): assert (p.parent/link).is_file(),link
    dest=ROOT/'releases'/version; dest.mkdir(parents=True,exist_ok=True)
    archive=dest/f'{NAME}-{version}.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in files:
            name=NAME+'/'+p.relative_to(source).as_posix()
            info=zipfile.ZipInfo(name,(2026,11,5,0,0,0)); info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644 << 16
            z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(n.startswith(NAME+'/') and '..' not in Path(n).parts for n in z.namelist())
    digest=hashlib.sha256(archive.read_bytes()).hexdigest()
    (dest/'SHA256SUMS').write_text(f'{digest}  {archive.name}\n')
    metadata={'version':version,'archive':archive.name,'sha256':digest,'bytes':archive.stat().st_size,
              'files':[{'path':str(p.relative_to(source)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
    (dest/'manifest.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'archive':str(archive),'bytes':metadata['bytes'],'files':len(files),'sha256':digest}))
    return archive
if __name__=='__main__': build()
