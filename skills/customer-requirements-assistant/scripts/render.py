"""Render validated records into an exclusive version directory."""
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path
import re
import shutil
import tempfile
from common import safe_text, skill_version
from validate import validate

EVIDENCE = {'explicit':'资料明确提出','inferred':'根据资料推断，待确认','suggestion':'建议项，未纳入承诺'}
STATUS = {'pending':'待客户确认','confirmed':'有客户确认依据，需核对'}


def md(value):
    value=safe_text(value).replace('\r','').replace('\n',' / ')
    value=value.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return re.sub(r'([\\`*_{}\[\]()#+.!|~-])',r'\\\1',value)


def csv_value(value):
    value=safe_text(value)
    return "'"+value if value.lstrip().startswith(('=','+','-','@','\t','\r','\n')) or value.startswith(('\t','\r','\n')) else value


def source_lookup(bundle):
    return {seg['id']:(src['filename'],seg['locator']) for src in bundle['sources'] for seg in src.get('segments',[])}


def ref_text(refs, lookup):
    return '；'.join(f'{r["segment_id"]} {lookup[r["segment_id"]][0]} {lookup[r["segment_id"]][1]}：{r["quote"]}' for r in refs) or '无原文依据，仅作建议或待补充'


def document_title(title):
    # Remove only trailing document labels; preserve words within the project name.
    title=safe_text(title).strip()
    suffix=r'需求确认(?:书|草稿)?\s*(?:[（(]\s*(?:待确认稿|草稿|待确认)\s*[）)])?\s*$'
    while re.search(suffix,title):
        title=re.sub(suffix,'',title).strip()
    return title+'需求确认书'


def blocks_for(model,bundle,result):
    title=document_title(model['project']['title'])
    blocks=[('title',title),('p','需求确认草稿'),
            ('p','请核对交付内容、范围和验收方式，并回复待确认事项。本稿用于沟通，未回复不视为默认同意；资料明确提出不等于客户已确认。'),
            ('small','行业或场景：'+model['project']['industry']),
            ('summary', [['需求记录','待客户确认','冲突事项','集中问题'],
                         [str(len(model['requirements'])),str(sum(r['confirmation_status']=='pending' for r in model['requirements'])),
                          str(len(model['conflicts'])),str(len(model['questions']))]]),
            ('h1','资料覆盖与限制')]
    read_count=sum(s['status']=='ok' for s in bundle['sources'])
    blocks.append(('p',f'已读取{read_count}份资料，未读取{len(bundle["sources"])-read_count}份；请核对资料覆盖范围。'))
    for src in bundle['sources']:
        for w in src.get('warnings',[]): blocks.append(('small',src['id']+'：'+w))
    def client_refs(refs):
        return '、'.join(dict.fromkeys(r['segment_id'] for r in refs)) or '无原文依据，仅作建议或待补充'
    blocks.append(('h1','需求与交付范围'))
    if not model['requirements']: blocks.append(('p','当前资料未提取到具体需求，请补充客户要求。'))
    for r in model['requirements']:
        blocks.extend([('h2',r['id']+' '+r['category']),('p',r['statement']),
                       ('small',EVIDENCE[r['evidence_type']]+'；'+STATUS[r['confirmation_status']]+'；优先级：'+r['priority']),
                       ('small','来源：'+client_refs(r['source_refs']))])
        if r['confirmation_refs']: blocks.append(('small','确认依据：'+client_refs(r['confirmation_refs'])))
        if r['dependencies']: blocks.append(('p','依赖与配合：'+'；'.join(r['dependencies'])))
        for a in r['acceptance']:
            blocks.append(('p',('原文验收要求：' if a['kind']=='source' else '建议验收方式，待确认：')+a['text']))
            if a['source_refs']: blocks.append(('small','验收依据：'+client_refs(a['source_refs'])))
        if not r['acceptance']: blocks.append(('p','验收方式：资料未约定，待补充。'))
        for q in r['open_questions']: blocks.append(('p','待确认：'+q))
    blocks.append(('h1','存在冲突的事项'))
    if not model['conflicts']: blocks.append(('p','本次整理未列出冲突，请仍核对原始资料；未列出不代表不存在。'))
    for c in model['conflicts']:
        blocks.extend([('h2',c['id']+' 待协调事项'),('p',c['text']),('small','关联需求：'+'、'.join(c['requirement_ids'])+'；冲突依据：'+client_refs(c['source_refs']))])
    blocks.append(('h1','请集中确认'))
    if not model['questions']: blocks.append(('p','当前没有单列问题，请核对各项范围与验收方式。'))
    for q in model['questions']:
        blocks.extend([('h2',q['id']+' 待确认问题'),('p',q['text']),('p','影响：'+q['impact']),('small','建议确认对象：'+q['owner']+'；关联需求：'+('、'.join(q['requirement_ids']) or '项目整体'))])
    if model['change_notes']:
        blocks.append(('h1','本次修订说明'))
        for c in model['change_notes']: blocks.append(('p',c))
    blocks.extend([('h1','确认说明'),('p','请逐项回复同意、修改意见或暂缓决定。建议项、未解决冲突和未约定的验收方式不构成已经确认的承诺。')])
    return blocks


def to_markdown(blocks):
    lines=[]
    for kind,value in blocks:
        if kind=='summary':
            rows=[value[0],['---']*len(value[0])]+value[1:]
            lines.append('\n'.join('| '+' | '.join(md(cell) if i!=1 else cell for cell in row)+' |' for i,row in enumerate(rows)))
        else:
            lines.append({'title':'# ','h1':'## ','h2':'### '}.get(kind,'')+md(value))
    return '\n\n'.join(lines)+'\n'


def write_docx(blocks,path):
    from docx import Document
    from docx.shared import Cm, Pt, RGBColor
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
    doc=Document()
    sec=doc.sections[0]; sec.page_width=Cm(21); sec.page_height=Cm(29.7)
    sec.top_margin=sec.bottom_margin=Cm(2); sec.left_margin=sec.right_margin=Cm(2.2)
    cjk_font=os.environ.get('CRA_CJK_FONT') or ('Heiti SC' if sys.platform=='darwin' else 'Microsoft YaHei' if sys.platform=='win32' else 'Noto Sans CJK SC')
    for style in doc.styles:
        for element in list(style.element.iter()):
            if element.tag==qn('w:pBdr'): element.getparent().remove(element)
            if element.tag==qn('w:rFonts'):
                for key in list(element.attrib):
                    if 'theme' in key.lower(): del element.attrib[key]
    for name,size in [('Normal',11),('Title',21),('Heading 1',14),('Heading 2',11)]:
        style=doc.styles[name]; style.font.name='Arial'; style.font.size=Pt(size); style.font.color.rgb=RGBColor(0,0,0)
        style.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),cjk_font)
        style.paragraph_format.space_after=Pt(5)
        style.paragraph_format.line_spacing=1.2
    doc.styles['Normal'].paragraph_format.widow_control=True
    for name in ('Heading 1','Heading 2'):
        doc.styles[name].paragraph_format.space_before=Pt(12 if name=='Heading 1' else 8)
        doc.styles[name].font.bold=True
    # Keep short records together; long records retain natural pagination.
    grouped=set()
    for start,(kind,_) in enumerate(blocks):
        if kind!='h2': continue
        end=start+1
        while end<len(blocks) and blocks[end][0] not in ('h1','h2','title','summary'): end+=1
        if sum(len(value) for _,value in blocks[start:end])<=650:
            grouped.update(range(start,end-1))
    for i,(kind,value) in enumerate(blocks):
        if kind=='summary':
            table=doc.add_table(rows=len(value),cols=len(value[0]))
            table.autofit=False
            props=table._tbl.tblPr
            borders=OxmlElement('w:tblBorders')
            for edge in ('top','left','bottom','right','insideH','insideV'):
                border=OxmlElement('w:'+edge)
                for key,val in [('val','single'),('sz','4'),('color','D9D9D9')]: border.set(qn('w:'+key),val)
                borders.append(border)
            props.append(borders)
            margins=OxmlElement('w:tblCellMar')
            for edge in ('top','left','bottom','right'):
                margin=OxmlElement('w:'+edge); margin.set(qn('w:w'),'100'); margin.set(qn('w:type'),'dxa'); margins.append(margin)
            props.append(margins)
            for rowno,row in enumerate(table.rows):
                row._tr.get_or_add_trPr().append(OxmlElement('w:cantSplit'))
                if rowno==0: row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
                for colno,cell in enumerate(row.cells):
                    cell.width=Cm(4.15); cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
                    shade=OxmlElement('w:shd'); shade.set(qn('w:fill'),'EAF2FA' if rowno==0 else 'FFFFFF'); cell._tc.get_or_add_tcPr().append(shade)
                    p=cell.paragraphs[0]; p.alignment=WD_ALIGN_PARAGRAPH.CENTER
                    p.paragraph_format.space_after=Pt(0); p.paragraph_format.keep_with_next=rowno==0
                    run=p.add_run(safe_text(value[rowno][colno])); run.font.size=Pt(10 if rowno==0 else 12)
                    run.bold=rowno!=0
            continue
        value=safe_text(value)
        p=doc.add_paragraph(value, style={'title':'Title','h1':'Heading 1','h2':'Heading 2'}.get(kind,'Normal'))
        p.paragraph_format.keep_together=True
        if kind in ('title','h1','h2') or i in grouped: p.paragraph_format.keep_with_next=True
        if kind=='small':
            p.paragraph_format.space_after=Pt(3)
            for run in p.runs: run.font.size=Pt(9); run.font.color.rgb=RGBColor(80,80,80)
    footer=sec.footer.paragraphs[0]
    footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('需求确认草稿  ·  ')
    field=OxmlElement('w:fldSimple'); field.set(qn('w:instr'),'PAGE'); footer._p.append(field)
    footer.add_run(' / ')
    total=OxmlElement('w:fldSimple'); total.set(qn('w:instr'),'NUMPAGES'); footer._p.append(total)
    for run in footer.runs: run.font.size=Pt(9)
    doc.core_properties.author=''; doc.core_properties.last_modified_by=''
    doc.core_properties.title=blocks[0][1]
    doc.core_properties.subject='需求确认草稿'
    doc.save(str(path))


def render(model,bundle,out,docx_mode='auto',previous=None):
    result=validate(model,bundle,previous)
    if result['errors']: raise ValueError('校验失败：\n'+'\n'.join(result['errors']))
    if docx_mode not in ('auto','off','required'): raise ValueError('docx 模式应为 auto/off/required。')
    has_docx=importlib.util.find_spec('docx') is not None
    if docx_mode=='required' and not has_docx: raise ValueError('缺少 python-docx，无法生成要求的 Word 文件。')
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    # Reserve an empty unique directory, render elsewhere, then atomically publish each file.
    dest=Path(tempfile.mkdtemp(prefix='需求整理-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-',dir=str(out)))
    work=Path(tempfile.mkdtemp(prefix='.render-',dir=str(out)))
    try:
        blocks=blocks_for(model,bundle,result); lookup=source_lookup(bundle)
        (work/'需求确认书.md').write_text(to_markdown(blocks),encoding='utf-8')
        qs=[('title','待确认问题'),('p','以下问题按整理时确定的影响顺序排列，优先询问前3至5项。')]
        for q in model['questions']:
            qs.extend([('h2',q['id']+' 待确认问题'),('p',q['text']),('p','影响：'+q['impact']),('small','建议确认对象：'+q['owner']+'；关联需求：'+('、'.join(q['requirement_ids']) or '项目整体'))])
        for r in model['requirements']:
            for q in r['open_questions']: qs.append(('p',r['id']+' 待确认：'+q))
        (work/'待确认问题.md').write_text(to_markdown(qs),encoding='utf-8')
        headers=['需求ID','分类','内容','依据类型','确认状态','优先级','来源','确认依据','依赖','验收方式','待确认问题']
        with (work/'需求追溯表.csv').open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.writer(f); writer.writerow(headers)
            for r in model['requirements']:
                writer.writerow([csv_value(v) for v in [r['id'],r['category'],r['statement'],EVIDENCE[r['evidence_type']],STATUS[r['confirmation_status']],r['priority'],ref_text(r['source_refs'],lookup),ref_text(r['confirmation_refs'],lookup),'；'.join(r['dependencies']),'；'.join(('原文要求：' if a['kind']=='source' else '建议待确认：')+a['text'] for a in r['acceptance']),'；'.join(r['open_questions'])]])
        srcblocks=[('title','来源索引'),('p','工作资料，包含原文摘录；对外发送前请检查授权与敏感信息。')]
        for s in bundle['sources']:
            srcblocks.extend([('h1',s['id']+' '+s['filename']),('p','状态：'+s['status']+'；SHA256：'+str(s.get('sha256')))])
            if s.get('error'): srcblocks.append(('p',s['error']))
            for w in s.get('warnings',[]): srcblocks.append(('p',w))
            for seg in s.get('segments',[]): srcblocks.extend([('h2',seg['id']+' '+seg['locator']),('p',seg['text'])])
        (work/'来源索引.md').write_text(to_markdown(srcblocks),encoding='utf-8')
        changes=[('title','版本变化'),('p','首次生成。' if previous is None else '与提供的上一版需求数据比较。')]
        if previous is not None:
            old={r['id']:r for r in previous['requirements']}; new={r['id']:r for r in model['requirements']}
            for rid in sorted(set(old)|set(new)):
                if rid not in old: label='新增'
                elif rid not in new: label='移除（旧版数据随包保留）'
                elif old[rid]!=new[rid]: label='修改'
                else: continue
                changes.append(('p',rid+'：'+label))
            for key in ('project','questions','conflicts'):
                if previous.get(key) != model.get(key): changes.append(('p',key+'：内容发生变化，请对照上一版需求数据与本次说明。'))
            (work/'上一版需求数据.json').write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for c in model['change_notes']: changes.append(('p',c))
        (work/'版本变化.md').write_text(to_markdown(changes),encoding='utf-8')
        word='disabled'
        if docx_mode!='off':
            if has_docx:
                try: write_docx(blocks,work/'需求确认书.docx'); word='generated'
                except Exception as exc:
                    if docx_mode=='required': raise
                    (work/'需求确认书.docx').unlink(missing_ok=True)
                    word='failed'; result['warnings'].append('Word导出失败：'+str(exc))
            else:
                word='missing_dependency'; result['warnings'].append('未生成 Word：缺少 python-docx；Markdown和CSV已生成。')
        for filename,data in [('需求数据.json',model),('来源数据.json',bundle),('校验报告.json',result)]:
            (work/filename).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        manifest={'skill_version':skill_version(),'created_at':datetime.now(timezone.utc).isoformat(),'status':'draft','word':word,
                  'files':[{ 'name':p.name, 'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(work.iterdir())],
                  'notes':['需求追溯表CSV、来源数据、需求数据、来源索引和上一版数据是内部工作资料，含完整原文；对外文件也须人工复核。','结构校验不等于事实或客户确认核验。']}
        (work/'交付清单.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        for p in work.iterdir(): p.replace(dest/p.name)
        return {**manifest,'directory':str(dest.resolve()),'warnings':result['warnings']}
    except Exception:
        shutil.rmtree(dest)
        raise
    finally:
        shutil.rmtree(work)
