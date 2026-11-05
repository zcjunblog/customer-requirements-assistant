#!/usr/bin/env python3
"""Portable CLI entrypoint; model extraction is performed by WorkBuddy, not here."""
import argparse
import importlib.util
import json
import sys
from common import load_json, save_json_new
from intake import ingest
from validate import validate
from render import render


def main():
    parser=argparse.ArgumentParser(description='客户需求整理助手：读取、校验和交付工具（Python 3.9+）。')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='检查运行时和可选依赖')
    p=sub.add_parser('ingest',help='只读提取资料，保存带来源位置的文本快照')
    p.add_argument('files',nargs='+'); p.add_argument('--out',required=True); p.add_argument('--previous')
    for name in ('validate','render'):
        p=sub.add_parser(name)
        p.add_argument('--model',required=True); p.add_argument('--sources',required=True); p.add_argument('--previous')
        if name=='render':
            p.add_argument('--out',required=True); p.add_argument('--docx',choices=['auto','off','required'],default='auto')
    args=parser.parse_args()
    try:
        if args.command=='doctor':
            result={'python':sys.version.split()[0],'core_ready':sys.version_info>=(3,9),
                    'word_export':importlib.util.find_spec('docx') is not None,'pdf_import':importlib.util.find_spec('pypdf') is not None,
                    'network':'本工具不联网，不需要模型API密钥。'}
        elif args.command=='ingest':
            result=ingest(args.files,load_json(args.previous) if args.previous else None)
            save_json_new(args.out,result)
            print(json.dumps({'output':args.out,'read':sum(s['status']=='ok' for s in result['sources']),
                              'failed':[{'name':s['filename'],'error':s.get('error')} for s in result['sources'] if s['status']!='ok']},ensure_ascii=False))
            return 0 if any(s['status']=='ok' for s in result['sources']) else 2
        else:
            model=load_json(args.model); bundle=load_json(args.sources)
            previous=load_json(args.previous) if args.previous else None
            if args.command=='validate':
                result=validate(model,bundle,previous)
                print(json.dumps(result,ensure_ascii=False,indent=2)); return 2 if result['errors'] else 0
            result=render(model,bundle,args.out,args.docx,previous)
        print(json.dumps(result,ensure_ascii=False,indent=2)); return 0
    except Exception as exc:
        print(json.dumps({'error':f'{type(exc).__name__}: {exc}','hint':'没有改写输入；检查路径、数据格式和依赖。已有来源索引不会覆盖，请换新文件名。'},ensure_ascii=False),file=sys.stderr)
        return 2

if __name__=='__main__': sys.exit(main())
