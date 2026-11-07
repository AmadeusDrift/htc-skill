"""Offline text screening adapter. Findings are review signals, not legal decisions."""
import argparse,csv,json,re,unicodedata,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def norm(s):return unicodedata.normalize('NFKC',str(s)).lower()
def tokens(s):return list(re.finditer(r'[^\W_]+|[+#&@%]',s,re.UNICODE))

class Scanner:
 def __init__(self,assets=None):
  self.assets=Path(assets) if assets else ROOT/'assets'
  manifest=json.loads((self.assets/'dictionary_manifest.json').read_text(encoding='utf-8'))
  sources=['htcerp_dictionary.json','supplement_terms.csv','platform_history.json']
  fingerprints={name:hashlib.sha256((self.assets/name).read_bytes()).hexdigest() for name in sources}
  if any(fingerprints[name]!=manifest['sha256'].get(name) for name in sources):raise ValueError('Dictionary snapshot hash mismatch; review/update manifest before use')
  fingerprints['scan_text.py']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
  self.ruleset_sha256=hashlib.sha256(json.dumps(fingerprints,sort_keys=True).encode()).hexdigest()
  raw=(self.assets/'htcerp_dictionary.json').read_bytes();d=json.loads(raw)
  if not isinstance(d.get('terms'),list) or not isinstance(d.get('ip'),list):raise ValueError('Invalid htcerp dictionary')
  self.counts={'terms':len(d['terms']),'ip':len(d['ip'])};self.snapshot_sha256=hashlib.sha256(raw).hexdigest();self.index={};self.longest=1
  def add(term,source,severity,reason,**extra):
   key=tuple(m.group() for m in tokens(norm(term)))
   if not key:return
   self.longest=max(self.longest,len(key))
   self.index.setdefault(key,[]).append({'source_term':term,'rule_source':source,'severity':severity,'reason':reason,**extra})
  for term,serial,*_ in d['terms']:add(term,'htcerp_terms','review','商标名称记录命中，需结合商品及用途复核',serial=serial)
  for alias,name,family,policy,*url in d['ip']:
   add(alias,'htcerp_ip','high' if policy=='重点核权' else 'review','品牌/IP名称或别名命中，需核对图像及来源',name=name,family=family,policy=policy)
  with (self.assets/'supplement_terms.csv').open(encoding='utf-8-sig',newline='') as f:
   for r in csv.DictReader(f):
    if r['term'].strip():add(r['term'],'scanner_csv',r.get('severity','review'),r.get('note',''),category=r.get('category',''))
  for r in json.loads((self.assets/'platform_history.json').read_text(encoding='utf-8')):
   add(r['term'],'platform_history','rewrite',r['reason'],action='rewrite',scope=r['scope'])
  self.motifs=set('cat ghost daisy coastal fern angel blossom iris tiger eagle lemon reef canyon swan bison bluebird goat owl zebra harvest raven crescent phoenix poppy calf husky hummingbird dove calico retriever crane rocky seashell wave mosaic silhouette willow giraffe bulldog boathouse pumpkin deer jellyfish goldfish'.split())
  self.descriptions=[re.compile(x,re.I) for x in [r'\b(?:wall|canvas|diamond|nail|line|metal|abstract|resin) art\b',r'\bart (?:prints?|paintings?|posters?|decor|supplies|sets?)\b',r'\bstill life\b|\bsea life\b|\bsmooth surface\b|\bhome or office\b',r'\b\d+(?:\.\d+)?\s*[x×]\s*\d+(?:\.\d+)?(?:\s*[x×]\s*\d+(?:\.\d+)?)?(?:\s*(?:inches|inch|cm|mm|ft))?\b']]
 def scan(self,text,scope='generic_pod'):
  text=str(text or '');normalized=norm(text);parts=tokens(normalized);words=[m.group() for m in parts];hits=[];seen=set()
  decorative=bool(re.search(r'\b(decor|pattern|printed|canvas|poster|posters|wall art|ornament|sticker|stickers|tapestry)\b',normalized))
  spans=[(m.start(),m.end()) for pattern in self.descriptions for m in pattern.finditer(normalized)]
  for i in range(len(words)):
   for end in range(min(len(words),i+self.longest),i,-1):
    rules=self.index.get(tuple(words[i:end]),[])
    if not rules:continue
    start=parts[i].start();stop=parts[end-1].end();phrase=normalized[start:stop]
    before=normalized[:start];after=normalized[stop:]
    source_claim=bool(re.search(r'\b(?:official|licensed|genuine|authentic|by|brand|from)\s*[:=-]?\s*$',before) or re.match(r'\s*[®™]',after))
    for rule in rules:
     if rule['rule_source']=='platform_history' and scope not in ['generic_pod',rule.get('scope')]:continue
     key=(start,stop,rule['rule_source'],rule['source_term'])
     if key in seen:continue
     seen.add(key)
     action='manual_review';severity=rule['severity']
     if rule['rule_source']=='platform_history':action='rewrite'
     elif source_claim:severity='high'
     elif severity=='high':action='manual_review'
     elif severity=='medium':action='rewrite_suggested'
     elif rule['rule_source'] in ['htcerp_terms','htcerp_ip']:
      descriptive=any(a<=start and stop<=b for a,b in spans)
      motif=phrase in self.motifs and decorative
      model_code=bool(re.fullmatch(r'[a-z]{1,3}',phrase) and re.match(r'[-_](?:jit[-_])?\d',after))
      if descriptive or motif or model_code:action='allow_context'
     hits.append({'term':text[start:stop] if len(text)==len(normalized) else normalized[start:stop],'normalized_term':phrase,'normalized_start':start,'normalized_end':stop,'action':action,**rule,'severity':severity})
  active=[h for h in hits if h['action']!='allow_context']
  if not text.strip():status='missing_text'
  elif any(h['severity']=='high' for h in active):status='manual_review'
  elif any(h['action']=='rewrite' for h in active):status='rewrite'
  elif active:status='review'
  else:status='no_rule_hit'
  return {'status':status,'hits':hits,'snapshot_sha256':self.snapshot_sha256,'ruleset_sha256':self.ruleset_sha256,'scope':scope}
 def scan_records(self,records):
  return [{**r,**self.scan(r.get('text',''),r.get('scope','generic_pod'))} for r in records]

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);ap.add_argument('--assets');a=ap.parse_args()
 records=json.loads(Path(a.input).read_text(encoding='utf-8-sig'))
 if not isinstance(records,list):raise ValueError('Expected JSON array of {sku,row,column,field,text}')
 scanner=Scanner(a.assets);report=scanner.scan_records(records)
 Path(a.output).write_text(json.dumps({'dictionary_counts':scanner.counts,'snapshot_sha256':scanner.snapshot_sha256,'ruleset_sha256':scanner.ruleset_sha256,'records':report},ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps({'records':len(report),'counts':{status:sum(r['status']==status for r in report) for status in sorted(set(r['status'] for r in report))}},ensure_ascii=False))
if __name__=='__main__':main()
