"""Deterministic structure/evidence checks, not an entailment or legal verifier."""
import re

NUMBERS = re.compile(r'\d+(?:\.\d+)?')


def validate(model, bundle, previous=None):
    errors, warnings = [], []
    def err(message): errors.append(message)
    def text(value, label, empty=False):
        if not isinstance(value,str) or (not empty and not value.strip()):
            err(f'{label} 必须是非空文本。'); return ''
        if len(value) > 10000: err(f'{label} 超过一万字，请拆分。')
        return value
    def array(value,label):
        if not isinstance(value,list): err(f'{label} 必须是数组。'); return []
        return value
    if not isinstance(model,dict) or not isinstance(bundle,dict):
        return {'errors':['需求数据和来源索引必须是 JSON 对象。'], 'warnings':[]}
    if model.get('schema_version') != '1.0' or bundle.get('schema_version') != '1.0':
        err('schema_version 必须为 1.0。')
    project = model.get('project')
    if not isinstance(project,dict): err('project 必须是对象。')
    else:
        text(project.get('title'),'project.title'); text(project.get('industry'),'project.industry')
    segments = {}
    for source in array(bundle.get('sources'),'sources'):
        if not isinstance(source,dict): err('source 必须是对象。'); continue
        text(source.get('id'),'source.id'); text(source.get('filename'),'source.filename')
        if source.get('status') not in ('ok','error'): err('source.status 必须是 ok/error。')
        if source.get('status') != 'ok':
            warnings.append(f'未读取来源：{source.get("filename","未知")}；{source.get("error","未知原因")}')
        for w in array(source.get('warnings',[]),'source.warnings'): warnings.append(str(w))
        for seg in array(source.get('segments',[]),'source.segments'):
            if not isinstance(seg,dict) or not isinstance(seg.get('id'),str) or not isinstance(seg.get('text'),str):
                err('来源段落格式错误。'); continue
            text(seg.get('locator'),'segment.locator')
            if seg['id'] in segments: err(f'重复来源段落 ID：{seg["id"]}')
            segments[seg['id']] = seg['text']
    if not segments: err('没有可读来源，不能生成需求确认书。')

    def refs(value,label,required=False):
        values = array(value,label)
        if required and not values: err(f'{label} 缺少原文依据。')
        quotes = []
        for ref in values:
            if not isinstance(ref,dict): err(f'{label} 引用必须是对象。'); continue
            sid = ref.get('segment_id'); quote = text(ref.get('quote'),label+'.quote')
            if not isinstance(sid,str) or sid not in segments: err(f'{label} 来源段落不存在：{sid}'); continue
            if quote and quote not in segments[sid]: err(f'{label} 引文不是原文连续片段：{sid}')
            quotes.append(quote)
        return '\n'.join(quotes)

    def numbers(statement,quote,label):
        missing = set(NUMBERS.findall(statement.replace(',',''))) - set(NUMBERS.findall(quote.replace(',','')))
        if missing: err(f'{label} 出现原文未支持的数字：{", ".join(sorted(missing))}')

    requirements = array(model.get('requirements'),'requirements')
    if len(requirements)>200: err('单批最多 200 条需求，请分批。')
    ids = set(); record_map = {}
    for r in requirements:
        if not isinstance(r,dict): err('需求记录必须是对象。'); continue
        rid = text(r.get('id'),'requirement.id')
        if not re.fullmatch(r'R[1-9]\d*',rid): err(f'需求 ID 格式应为 R1、R2：{rid}')
        if rid in ids: err(f'重复需求 ID：{rid}')
        ids.add(rid); record_map[rid] = r
        text(r.get('category'),rid+'.category')
        statement = text(r.get('statement'),rid+'.statement')
        evidence = r.get('evidence_type'); status = r.get('confirmation_status')
        if evidence not in ('explicit','inferred','suggestion'): err(f'{rid} evidence_type 无效。')
        if status not in ('pending','confirmed'): err(f'{rid} confirmation_status 无效。')
        quote = refs(r.get('source_refs'),rid+'.source_refs', evidence != 'suggestion')
        if evidence == 'explicit': numbers(statement,quote,rid)
        confirm = refs(r.get('confirmation_refs'),rid+'.confirmation_refs', status == 'confirmed')
        if status == 'confirmed':
            if evidence != 'explicit': err(f'{rid} 推断或建议不能标为客户已确认。')
            warnings.append(f'{rid}：请人工核对确认引文确为客户针对本需求的明确确认，脚本无法判断身份与语义。')
        text(r.get('priority'),rid+'.priority')
        for key in ('dependencies','open_questions'):
            for value in array(r.get(key),rid+'.'+key): text(value,rid+'.'+key)
        for item in array(r.get('acceptance'),rid+'.acceptance'):
            if not isinstance(item,dict): err(f'{rid} acceptance 项必须是对象。'); continue
            value=text(item.get('text'),rid+'.acceptance.text')
            if item.get('kind') not in ('source','suggestion'): err(f'{rid} 验收 kind 无效。')
            q=refs(item.get('source_refs'),rid+'.acceptance.source_refs', item.get('kind')=='source')
            if item.get('kind') == 'source': numbers(value,q,rid+' 验收标准')
    for key,prefix in [('questions','Q'),('conflicts','C')]:
        seen=set()
        for item in array(model.get(key),key):
            if not isinstance(item,dict): err(f'{key} 项必须是对象。'); continue
            iid=text(item.get('id'),key+'.id')
            if not re.fullmatch(prefix+r'[1-9]\d*',iid) or iid in seen: err(f'{key} ID 无效或重复：{iid}')
            seen.add(iid); text(item.get('text'),iid+'.text')
            links=array(item.get('requirement_ids'),iid+'.requirement_ids')
            for rid in links:
                if not isinstance(rid,str) or rid not in ids: err(f'{iid} 引用了不存在的需求：{rid}')
            if key=='questions':
                text(item.get('impact'),iid+'.impact'); text(item.get('owner'),iid+'.owner')
            else:
                refs(item.get('source_refs'),iid+'.source_refs',True)
                conflict_refs = item.get('source_refs')
                distinct = {(str(r.get('segment_id')), str(r.get('quote'))) for r in conflict_refs if isinstance(r,dict)} if isinstance(conflict_refs,list) else set()
                if len(distinct) < 2: err(f'{iid} 冲突须保留至少两条不同的原文依据。')
                if not links: err(f'{iid} 冲突必须关联需求。')
                for rid in links:
                    if isinstance(rid,str) and record_map.get(rid,{}).get('confirmation_status')=='confirmed':
                        err(f'{iid} 未解决冲突关联的 {rid} 不能标为已确认。')
    changes=array(model.get('change_notes'), 'change_notes')
    for c in changes: text(c,'change_notes')
    removed=array(model.get('removed_requirement_ids'),'removed_requirement_ids')
    for rid in removed:
        if not isinstance(rid,str): err('removed_requirement_ids 项必须是文本。')
        elif rid in ids: err(f'删除清单中的 {rid} 仍在当前需求里。')
    if previous is not None:
        if not isinstance(previous,dict) or not isinstance(previous.get('requirements'),list):
            err('旧需求数据格式错误。')
        else:
            old={r['id']:r for r in previous['requirements'] if isinstance(r,dict) and isinstance(r.get('id'),str)}
            valid_removed={r for r in removed if isinstance(r,str)}
            if set(old)-ids != valid_removed: err('删除清单必须准确列出旧版中被移除的需求 ID。')
            revision_changed = any(previous.get(k)!=model.get(k) for k in ('project','requirements','questions','conflicts'))
            if revision_changed and not changes: err('修订项目、需求、问题或冲突时必须填写 change_notes。')
            for rid in set(old)&ids:
                old_refs = old[rid].get('source_refs',[])
                if any(ref not in record_map[rid].get('source_refs',[]) for ref in old_refs):
                    err(f'{rid} 修订丢失旧来源；请保留旧依据并补充新依据。')
    if not requirements: warnings.append('没有提取到具体需求；请检查资料并补充问题，不视为需求完整。')
    warnings.append('校验只验证结构、引文和数字匹配；来源真伪、说话人、中文数词及语义蕴含需复核。')
    return {'errors':errors,'warnings':list(dict.fromkeys(warnings))}
