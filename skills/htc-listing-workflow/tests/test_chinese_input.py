import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
 from chinese_input import review_form,FORM_TEMPLATE
except ImportError:
 review_form=None;FORM_TEMPLATE=''

def form(**values):
 lines=['使用 htc上架工作流','','【HTC上架工作流输入】']
 fields={'图片目录':'D:/产品图片','本批起始SKU':'SKU001','商品模式':'普通单品','标题模板':'Canvas Wall Art, {关键词} Home Decor','云图链接表':'','上架表':'','上架样板位置':'自动识别','其他商品信息':'','分组方式（父子体时填）':'','父图（父子体时填）':'','子图及SKU后缀（父子体时填）':'','售卖方式（父子体时填）':'','输出位置':'图片目录同级新文件夹','特殊要求':''}
 fields.update(values)
 return '\n'.join(lines+[k+'：'+v for k,v in fields.items()])

class ChineseInputTests(unittest.TestCase):
 def setUp(self):self.assertIsNotNone(review_form,'尚未实现中文表单检查')
 def test_one_merged_template(self):
  self.assertIn('父图（父子体时填）',FORM_TEMPLATE)
  self.assertNotIn('schema_version',FORM_TEMPLATE)
 def test_single_blank_optionals_allowed(self):
  r=review_form(form())
  self.assertTrue(r['valid'],r)
  self.assertIsNone(r['request']['listing_workbook'])
  self.assertIsNone(r['request']['cloud_links_workbook'])
  self.assertIsNone(r['request']['grouping'])
 def test_missing_title_preserves_all_other_values(self):
  raw=form(标题模板='',本批起始SKU='HUC.TEST-00052',其他商品信息='重量0.2 Pounds；材质帆布')
  r=review_form(raw)
  self.assertFalse(r['valid'])
  self.assertIn('标题模板：【待补',r['response_form'])
  for line in raw.splitlines():
   if line and not line.startswith('标题模板：'):self.assertIn(line,r['response_form'])
  self.assertEqual(r['response_form'].count('【待补'),1)
 def test_complete_parent_child(self):
  r=review_form(form(**{'商品模式':'父子体','分组方式（父子体时填）':'每个编号文件夹一组','父图（父子体时填）':'90x40.png','子图及SKU后缀（父子体时填）':'左.png对应-A，中.png对应-B，右.png对应-C','售卖方式（父子体时填）':'子体单幅售卖，父体仅展示关联'}))
  self.assertTrue(r['valid'],r)
  self.assertEqual([c['suffix'] for c in r['request']['grouping']['children']],['-A','-B','-C'])
 def test_parent_missing_only_marks_missing_group_fields(self):
  r=review_form(form(商品模式='父子体'))
  self.assertFalse(r['valid'])
  self.assertEqual(r['response_form'].count('【待补'),4)
  self.assertIn('本批起始SKU：SKU001',r['response_form'])
 def test_no_form_marker_requests_chinese_form(self):
  r=review_form('帮我处理D:/图案，从SKU001开始')
  self.assertFalse(r['valid'])
  self.assertIn('【HTC上架工作流输入】',r['response_form'])
  self.assertNotIn('schema_version',r['response_form'])
 def test_conflict_keeps_filled_text(self):
  r=review_form(form(**{'商品模式':'普通单品','父图（父子体时填）':'90x40.png'}))
  self.assertFalse(r['valid'])
  self.assertIn('商品模式：普通单品【需确认',r['response_form'])
  self.assertIn('父图（父子体时填）：90x40.png',r['response_form'])
 def test_known_title_can_resolve_explicit_reuse(self):
  r=review_form(form(标题模板='沿用该产品已确认模板'),known={'title_template':'Canvas Wall Art, {关键词} Home Decor'})
  self.assertTrue(r['valid'],r)
 def test_unresolved_reuse_is_not_guessed(self):
  r=review_form(form(标题模板='沿用该产品已确认模板'))
  self.assertFalse(r['valid'])
  self.assertIn('标题模板：沿用该产品已确认模板【需确认',r['response_form'])
 def test_duplicate_field_is_not_silently_overwritten(self):
  r=review_form(form()+'\n本批起始SKU：SKU999')
  self.assertFalse(r['valid'])
  self.assertIn('SKU001',r['response_form']);self.assertIn('SKU999',r['response_form'])
 def test_listing_sample_auto_does_not_require_json(self):
  r=review_form(form(上架表='D:/模板.xlsm',上架样板位置='模板工作表第7～10行'))
  self.assertTrue(r['valid'],r)
  self.assertEqual(r['request']['template_rows'],{'sheet':'模板','first_row':7,'last_row':10})
 def test_no_listing_ignores_sample_note(self):
  r=review_form(form(上架样板位置='第7行，暂未提供上架表'))
  self.assertTrue(r['valid'],r)
  self.assertIsNone(r['request']['template_rows'])
 def test_partial_parent_only_marks_actual_missing_fields(self):
  r=review_form(form(**{'商品模式':'父子体','分组方式（父子体时填）':'每个编号文件夹一组','父图（父子体时填）':'90x40.png'}))
  self.assertFalse(r['valid'])
  self.assertEqual(set(r['missing']),{'子图及SKU后缀','售卖方式'})
  self.assertNotIn('商品模式：父子体【',r['response_form'])
 def test_filled_reply_does_not_use_system_marker_as_title(self):
  r=review_form(form(标题模板='Canvas Wall Art, {关键词} Home Decor【待补：请补标题模板】'))
  self.assertTrue(r['valid'],r)
  self.assertEqual(r['request']['title_template'],'Canvas Wall Art, {关键词} Home Decor')
 def test_still_missing_marker_does_not_duplicate(self):
  r=review_form(form(标题模板='【待补：请补标题模板】'))
  self.assertFalse(r['valid'])
  self.assertEqual(r['response_form'].count('【待补'),1)
 def test_independent_note_does_not_pollute_title(self):
  raw=form().replace('标题模板：Canvas Wall Art, {关键词} Home Decor','标题模板：Canvas Wall Art, {关键词} Home Decor\n备注：赶时间，请保留空格')
  r=review_form(raw)
  self.assertTrue(r['valid'],r)
  self.assertEqual(r['request']['title_template'],'Canvas Wall Art, {关键词} Home Decor')
  self.assertIn('备注：赶时间，请保留空格',r['response_form'])

if __name__=='__main__':unittest.main()
