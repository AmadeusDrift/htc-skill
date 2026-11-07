import sys,unittest,json,tempfile,shutil,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
try:
 from scan_text import Scanner
except ImportError:
 Scanner=None

class ScannerTests(unittest.TestCase):
 def setUp(self):
  self.assertIsNotNone(Scanner,'扫描器实现尚未提供')
  self.s=Scanner()
 def test_snapshot_loaded(self):
  self.assertEqual(self.s.counts['terms'],32248)
  self.assertEqual(self.s.counts['ip'],2418)
 def test_feedback_overrides_generic_context(self):
  r=self.s.scan('Wrapped Framed Canvas Wall Art, Apple Harvest Home Decor')
  self.assertTrue(any(h['rule_source']=='platform_history' and h['term'].lower()=='apple' and h['action']=='rewrite' for h in r['hits']))
 def test_phrase_across_title_boundary(self):
  r=self.s.scan('Wrapped Framed Canvas Wall Art, Golden Ginkgo Home Decor')
  self.assertTrue(any(h['rule_source']=='platform_history' and h['term'].lower()=='ginkgo home' for h in r['hits']))
 def test_known_cases(self):
  for word in ['Alpine Pine','Tide Rocks','Wildflower Hill']:
   self.assertTrue(any(h['action']=='rewrite' for h in self.s.scan('Canvas Wall Art, '+word+' Home Decor')['hits']))
 def test_generic_art_is_contextual(self):
  r=self.s.scan('Wrapped Framed Canvas Wall Art, Fern Fronds Home Decor')
  self.assertFalse(any(h['term'].lower()=='art' and h['action']!='allow_context' for h in r['hits']))
 def test_word_boundaries(self):
  self.assertFalse(any(h['term'].lower()=='free' for h in self.s.scan('Freestyle Pattern')['hits']))
 def test_unicode_and_case(self):
  r=self.s.scan('Canvas Wall Art, ＡＰＰＬＥ Harvest Home Decor')
  self.assertTrue(any(h['rule_source']=='platform_history' for h in r['hits']))
 def test_real_character_not_auto_rename(self):
  r=self.s.scan('Mickey Mouse Canvas Wall Art')
  self.assertTrue(any(h['action']=='manual_review' and h['severity']=='high' for h in r['hits']))
 def test_fields_and_location(self):
  report=self.s.scan_records([{'sku':'SKU001','row':7,'column':'AD','field':'description','text':'Tide Rocks'}])
  self.assertEqual(report[0]['row'],7)
  self.assertEqual(report[0]['column'],'AD')
  self.assertEqual(report[0]['sku'],'SKU001')
 def test_no_false_safety_label(self):
  r=self.s.scan('')
  self.assertEqual(r['status'],'missing_text')
 def test_ruleset_tracks_history_revision(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
   assets=Path(folder)/'assets';shutil.copytree(self.s.assets,assets)
   before=Scanner(assets)
   file=assets/'platform_history.json';data=json.loads(file.read_text(encoding='utf-8'));data[0]['reason']='已验证的新运营理由';file.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
   manifest=assets/'dictionary_manifest.json';m=json.loads(manifest.read_text(encoding='utf-8'));m['sha256'][file.name]=hashlib.sha256(file.read_bytes()).hexdigest();manifest.write_text(json.dumps(m),encoding='utf-8')
   after=Scanner(assets)
   self.assertNotEqual(before.ruleset_sha256,after.ruleset_sha256)
   self.assertTrue(any(h['reason']=='已验证的新运营理由' for h in after.scan('Apple Harvest')['hits']))
 def test_corrupted_snapshot_rejected(self):
  with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
   assets=Path(folder)/'assets';shutil.copytree(self.s.assets,assets)
   with (assets/'supplement_terms.csv').open('a',encoding='utf-8') as f:f.write('\n')
   with self.assertRaises(ValueError):Scanner(assets)

if __name__=='__main__':unittest.main()
