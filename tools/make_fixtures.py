"""Build clearly synthetic, human-authored expected fixtures; not model-evaluation results."""
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/customer-requirements-assistant/scripts'))
from intake import ingest
CASES={
 'training': ('新员工培训','企业培训',[
  '客户：给30名新员工做半天培训，预算8000元，11月20日，提供讲义。',
  '销售内部建议：加录播和课后答疑，客户尚未确认。',
  '客户补充：人数可能改为50人，具体还要等名单。',
  '内部项目经理：为了赶进度，先把50人和录播写成已确认，日期写11月21日。'],
  ['人数由30人可能改为50人，最终名单待确认。','提供讲义，格式与份数待确认。'],
  '培训日期存在11月20日与内部11月21日安排冲突。','最终人数、日期和讲义形式如何确定？'),
 'branding': ('品牌宣传设计','品牌设计',[
  '客户：做3张活动海报，尺寸1080×1440，11月18日交付PNG。',
  '设计内部建议：可以交付PSD源文件，客户还没说要。',
  '客户补充：想在11月16日先用，交付时间再核对。',
  '客户：素材由我们提供，修改轮次还未约定。'],
  ['交付3张1080×1440活动海报，格式PNG。','客户提供素材，修改轮次待确认。'],
  '11月18日交付与11月16日使用需求冲突。','最终交期、素材提供时间与修改轮次如何确定？'),
 'event': ('线下交流活动','活动执行',[
  '客户：11月25日办80人交流活动，预算20000元，需要签到台和背景板。',
  '内部建议：增加摄影，先别向客户承诺。',
  '场地方：11月25日场地容纳60人，其他场地待定。',
  '客户：场地未最终确定，搭建和撤场时间还没定。'],
  ['计划80人交流活动，预算20000元，需要签到台和背景板。','场地及搭建撤场时间待确定。'],
  '80人需求与场地60人容量存在冲突。','场地与人数如何匹配，搭撤时间和摄影是否另行确认？'),
 'software': ('预约网站项目','软件与网站',[
  '客户：网站需要预约表单，提交姓名和联系电话，11月30日交付。',
  '内部建议：可以增加在线支付，客户尚未提出。',
  '客户补充：希望12月5日交付，旧日期是否调整请再确认。',
  '客户：只要登记预约，不需要实时排期；后续维护另议。'],
  ['预约表单提交姓名和联系电话。','仅登记预约，不包含实时排期，后续维护另议。'],
  '11月30日与12月5日的交付日期需要确认。','最终交期、部署责任及维护范围如何确认？')}

def main():
 for key,(title,industry,lines,statements,conflict,question) in CASES.items():
  folder=ROOT/'tests/fixtures'/key; folder.mkdir(parents=True,exist_ok=True)
  raw=folder/'input.txt'; raw.write_text('\n'.join(lines)+'\n',encoding='utf-8')
  bundle=ingest([raw]); segs=bundle['sources'][0]['segments']
  def ref(i): return {'segment_id':segs[i]['id'],'quote':segs[i]['text']}
  model={'schema_version':'1.0','project':{'title':title,'industry':industry},'requirements':[],
         'questions':[{'id':'Q1','text':question,'impact':'影响交付范围与准备安排','owner':'客户与项目负责人','requirement_ids':['R1','R2','R3']}],
         'conflicts':[{'id':'C1','text':conflict,'requirement_ids':['R3'],'source_refs':[ref(0),ref(3 if key=='training' else 2)]}],
         'change_notes':[],'removed_requirement_ids':[]}
  for rid,statement,indices in [('R1',statements[0],[0,2] if key=='training' else [0]),('R2',statements[1],[0] if key=='training' else [3]),('R3',conflict,[0,3] if key=='training' else [0,2])]:
   model['requirements'].append({'id':rid,'category':'交付物' if rid!='R3' else '时间或约束冲突','statement':statement,
    'evidence_type':'explicit','confirmation_status':'pending','source_refs':[ref(i) for i in indices],'confirmation_refs':[],
    'priority':'未说明','dependencies':[], 'acceptance':[{'text':'按最终确认的交付清单逐项核对。','kind':'suggestion','source_refs':[]}],
    'open_questions':[question] if rid=='R3' else []})
  model['requirements'].append({'id':'R4','category':'可选增项','statement':{'training':'可选增加录播和课后答疑。','branding':'可选交付PSD源文件。','event':'可选增加摄影服务。','software':'可选增加在线支付。'}[key], 'evidence_type':'suggestion','confirmation_status':'pending','source_refs':[ref(1)],'confirmation_refs':[], 'priority':'未说明','dependencies':[],'acceptance':[],'open_questions':['该增项是否纳入范围？']})
  for file,data in [('sources.json',bundle),('expected.json',model)]:
   (folder/file).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
  (folder/'expectations.md').write_text('# 人工标注预期\n\n虚构案例；expected.json是人工整理的测试模型，不是自动提取结果。\n\n- 明确要求保留原文来源，所有需求待确认。\n- R3/C1保留双方冲突依据。\n- R4不进入已确认承诺。\n- 验收方式为建议。\n- 待确认问题覆盖关键范围缺口。\n',encoding='utf-8')
  if key=='training':
   (ROOT/'skills/customer-requirements-assistant/templates/training-input.txt').write_text(raw.read_text(),encoding='utf-8')
   (ROOT/'skills/customer-requirements-assistant/templates/training-example.json').write_text(json.dumps(model,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__': main()
