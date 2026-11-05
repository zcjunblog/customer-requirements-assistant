import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skill/customer-requirements-assistant/scripts'
sys.path.insert(0, str(SCRIPTS))
from intake import ingest
from validate import validate
from render import render


def model_for(bundle):
    sid = bundle['sources'][0]['segments'][0]['id']
    ref = {'segment_id': sid, 'quote': '客户：培训30人，预算8000元，提供讲义。'}
    return {'schema_version': '1.0', 'project': {'title': '新员工培训', 'industry': '企业培训'},
            'requirements': [{'id': 'R1', 'category': '交付物', 'statement': '培训30人，预算8000元，提供讲义。',
                'evidence_type': 'explicit', 'confirmation_status': 'pending', 'source_refs': [ref],
                'confirmation_refs': [], 'priority': '未说明', 'dependencies': [],
                'acceptance': [{'text': '提供讲义。', 'kind': 'source', 'source_refs': [ref]}], 'open_questions': ['讲义格式？']}],
            'questions': [{'id': 'Q1', 'text': '讲义格式？', 'impact': '影响文件准备', 'owner': '客户', 'requirement_ids': ['R1']}],
            'conflicts': [], 'change_notes': [], 'removed_requirement_ids': []}


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.input = self.root / '客户 聊天.txt'
        self.input.write_text('客户：培训30人，预算8000元，提供讲义。\n', encoding='utf-8')
        self.bundle = ingest([self.input])
        self.model = model_for(self.bundle)

    def tearDown(self):
        self.tmp.cleanup()

    def test_sources_and_partial_failure(self):
        b = ingest([self.input, self.root / 'missing.pdf'])
        self.assertEqual(b['sources'][0]['segments'][0]['locator'], '行1')
        self.assertEqual(b['sources'][1]['status'], 'error')
        self.assertEqual(self.input.read_text(), '客户：培训30人，预算8000元，提供讲义。\n')

    def test_empty_and_oversize(self):
        with self.assertRaises(ValueError): ingest([])
        huge = self.root / 'big.txt'; huge.write_text('a' * 200001)
        self.assertEqual(ingest([huge])['sources'][0]['status'], 'error')

    def test_valid_and_false_quote(self):
        self.assertEqual(validate(self.model, self.bundle)['errors'], [])
        self.model['requirements'][0]['source_refs'][0]['quote'] = '客户确认100人'
        self.assertTrue(validate(self.model, self.bundle)['errors'])

    def test_new_number_rejected(self):
        self.model['requirements'][0]['statement'] = '培训300人。'
        self.assertTrue(validate(self.model, self.bundle)['errors'])

    def test_confirmation_needs_evidence_and_suggestion_cannot_be_confirmed(self):
        r = self.model['requirements'][0]; r['confirmation_status'] = 'confirmed'
        self.assertTrue(validate(self.model, self.bundle)['errors'])
        r['confirmation_refs'] = copy.deepcopy(r['source_refs'])
        r['evidence_type'] = 'suggestion'
        self.assertTrue(validate(self.model, self.bundle)['errors'])

    def test_duplicate_and_wrong_type(self):
        self.model['requirements'].append(copy.deepcopy(self.model['requirements'][0]))
        self.assertTrue(validate(self.model, self.bundle)['errors'])
        self.assertTrue(validate([], self.bundle)['errors'])
        self.model['requirements'] = 'broken'
        self.assertTrue(validate(self.model, self.bundle)['errors'])

    def test_revision_removal_and_source_retention(self):
        new = copy.deepcopy(self.model); new['requirements'] = []; new['questions'] = []
        self.assertTrue(validate(new, self.bundle, self.model)['errors'])
        new['removed_requirement_ids'] = ['R1']; new['change_notes'] = ['应用户要求删除R1，保留原稿。']
        self.assertEqual(validate(new, self.bundle, self.model)['errors'], [])

    def test_reingest_stable_ids(self):
        other = self.root / '补充.txt'; other.write_text('客户：另需练习。')
        b = ingest([self.input, other], previous=self.bundle)
        self.assertEqual(len(b['sources']), 2)
        self.assertEqual(b['sources'][0]['id'], self.bundle['sources'][0]['id'])

    def test_render_nonoverwriting_and_csv_safe(self):
        r = self.model['requirements'][0]
        r['statement'] = '=HYPERLINK("example")'; r['evidence_type'] = 'suggestion'
        a = render(self.model, self.bundle, self.root / 'out', 'off')
        b = render(self.model, self.bundle, self.root / 'out', 'off')
        self.assertNotEqual(a['directory'], b['directory'])
        dest = Path(a['directory'])
        import csv
        with (dest/'需求追溯表.csv').open(encoding='utf-8-sig') as f:
            rows = list(csv.reader(f))
        self.assertTrue(rows[1][2].startswith("'="))
        self.assertIn('需求确认草稿', (dest/'需求确认书.md').read_text())
        self.assertTrue((dest/'来源索引.md').exists())

    def test_render_blocks_invalid(self):
        self.model['requirements'][0]['source_refs'] = []
        with self.assertRaises(ValueError): render(self.model, self.bundle, self.root/'out', 'off')
        self.assertFalse((self.root/'out').exists())

    def test_four_industry_fixtures(self):
        for folder in sorted((Path(__file__).parent/'fixtures').iterdir()):
            with self.subTest(industry=folder.name):
                b=ingest([folder/'input.txt'])
                m=json.loads((folder/'expected.json').read_text())
                self.assertEqual(validate(m,b)['errors'], [])
                output=render(m,b,self.root/folder.name,'off')
                text=(Path(output['directory'])/'需求确认书.md').read_text()
                self.assertIn(m['project']['industry'],text)
                self.assertIn('待客户确认',text)

    def test_malformed_conflict_refs(self):
        self.model['conflicts']=[{'id':'C1','text':'冲突','requirement_ids':['R1'],'source_refs':None}]
        self.assertTrue(validate(self.model,self.bundle)['errors'])

    def test_explicit_source_acceptance_needs_quote(self):
        self.model['requirements'][0]['acceptance']=[{'text':'满意度99%','kind':'source','source_refs':[]}]
        self.assertTrue(validate(self.model,self.bundle)['errors'])

    def test_revision_keeps_old_refs(self):
        new=copy.deepcopy(self.model)
        new['requirements'][0]['source_refs']=[{'segment_id':self.bundle['sources'][0]['segments'][0]['id'],'quote':'培训30人'}]
        new['change_notes']=['缩短引文']
        self.assertTrue(validate(new,self.bundle,self.model)['errors'])

    def test_unresolved_conflict_blocks_confirmation(self):
        r=self.model['requirements'][0]; r['confirmation_status']='confirmed'; r['confirmation_refs']=copy.deepcopy(r['source_refs'])
        self.model['conflicts']=[{'id':'C1','text':'人数冲突','requirement_ids':['R1'],'source_refs':r['source_refs']*2}]
        self.assertTrue(validate(self.model,self.bundle)['errors'])

    def test_confirmation_can_reference_previous_message(self):
        path=self.root/'补充.txt'; path.write_text('客户：确认，按上一条安排执行。')
        b=ingest([path],previous=self.bundle)
        r=self.model['requirements'][0]; r['confirmation_status']='confirmed'
        r['confirmation_refs']=[{'segment_id':b['sources'][-1]['segments'][0]['id'],'quote':'客户：确认，按上一条安排执行。'}]
        self.assertEqual(validate(self.model,b)['errors'],[])

    def test_question_changes_need_revision_note(self):
        changed=copy.deepcopy(self.model); changed['questions']=[]
        self.assertTrue(validate(changed,self.bundle,self.model)['errors'])
        changed['change_notes']=['客户另行确认了讲义格式。']
        self.assertEqual(validate(changed,self.bundle,self.model)['errors'],[])
        output=render(changed,self.bundle,self.root/'out','off',self.model)
        self.assertIn('questions',(Path(output['directory'])/'版本变化.md').read_text())

    def test_source_required_fields(self):
        for field in ('id','filename'):
            b=copy.deepcopy(self.bundle); del b['sources'][0][field]
            self.assertTrue(validate(self.model,b)['errors'])
        b=copy.deepcopy(self.bundle); del b['sources'][0]['segments'][0]['locator']
        self.assertTrue(validate(self.model,b)['errors'])

    def test_customer_draft_omits_full_source_quotes(self):
        a=render(self.model,self.bundle,self.root/'out','off')
        draft=(Path(a['directory'])/'需求确认书.md').read_text()
        self.assertNotIn('客户：培训',draft)
        self.assertIn('S001',draft)
        self.assertIn('客户：培训',(Path(a['directory'])/'来源索引.md').read_text())

    def test_title_not_duplicated(self):
        self.model['project']['title']='培训需求确认草稿'
        a=render(self.model,self.bundle,self.root/'out','off')
        self.assertEqual((Path(a['directory'])/'需求确认书.md').read_text().splitlines()[0],'# 培训需求确认书')

    @unittest.skipUnless(importlib.util.find_spec('pypdf'),'optional pypdf unavailable')
    def test_scanned_pdf_reported(self):
        from pypdf import PdfWriter
        writer=PdfWriter(); writer.add_blank_page(width=600,height=800)
        path=self.root/'scan.pdf'
        with path.open('wb') as f: writer.write(f)
        b=ingest([self.input,path])
        self.assertEqual(b['sources'][1]['status'],'error')
        self.assertTrue(any('第1页' in w for w in b['sources'][1]['warnings']))

    def test_missing_optional_word_is_explicit(self):
        from unittest.mock import patch
        with patch('render.importlib.util.find_spec',return_value=None):
            a=render(self.model,self.bundle,self.root/'out','auto')
            self.assertEqual(a['word'],'missing_dependency')
            self.assertFalse((Path(a['directory'])/'需求确认书.docx').exists())
            with self.assertRaises(ValueError): render(self.model,self.bundle,self.root/'must-fail','required')
            self.assertFalse((self.root/'must-fail').exists())

    def test_ingest_output_never_overwrites(self):
        from common import save_json_new
        path=self.root/'sources.json'; save_json_new(path,self.bundle)
        before=path.read_bytes()
        with self.assertRaises(FileExistsError): save_json_new(path,{})
        self.assertEqual(before,path.read_bytes())

    @unittest.skipUnless(importlib.util.find_spec('docx'), 'optional python-docx unavailable')
    def test_docx_round_trip(self):
        from docx import Document
        a = render(self.model, self.bundle, self.root/'out', 'required')
        doc = Path(a['directory'])/'需求确认书.docx'
        text = '\n'.join(p.text for p in Document(doc).paragraphs)
        self.assertIn('8000', text); self.assertIn('需求确认草稿', text)
        self.assertNotIn('pBdr', Document(doc).styles['Title'].element.xml)
        self.assertNotIn('eastAsiaTheme', Document(doc).styles['Title'].element.xml)
        b = ingest([doc])
        self.assertEqual(b['sources'][0]['status'], 'ok')
        self.assertTrue(any('8000' in s['text'] for s in b['sources'][0]['segments']))

if __name__ == '__main__': unittest.main()
