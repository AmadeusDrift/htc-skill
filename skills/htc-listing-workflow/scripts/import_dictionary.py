"""Validate/import only JSON dictionary data from an authorized snapshot; never eval worker code."""
import argparse,json,hashlib
from pathlib import Path

def extract_multipart(text):
 boundary=text.split('\n',1)[0].rstrip('\r')
 for part in text.split(boundary):
  if 'name="index.js.map"' not in part:continue
  sep='\r\n\r\n' if '\r\n\r\n' in part else '\n\n'
  sm=json.loads(part.split(sep,1)[1].strip())
  for path,content in zip(sm['sources'],sm['sourcesContent']):
   if path.replace('\\','/').endswith('/title-audit/dictionary.json'):return json.loads(content)
 raise ValueError('Expected title-audit/dictionary.json source content not found')

def validate(d):
 if not isinstance(d,dict) or not all(isinstance(d.get(k),list) and d[k] for k in ['terms','ip']):raise ValueError('Missing or empty terms/ip arrays')
 if not all(isinstance(r,list) and len(r)>=2 and all(isinstance(x,str) for x in r[:2]) for r in d['terms']):raise ValueError('Invalid terms rows')
 if not all(isinstance(r,list) and len(r)>=4 and all(isinstance(x,str) for x in r[:4]) for r in d['ip']):raise ValueError('Invalid ip rows')
 return d

def main():
 ap=argparse.ArgumentParser(description=__doc__);g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--multipart');g.add_argument('--dictionary');ap.add_argument('--output-directory',required=True);a=ap.parse_args()
 d=validate(extract_multipart(Path(a.multipart).read_text(encoding='utf-8')) if a.multipart else json.loads(Path(a.dictionary).read_text(encoding='utf-8-sig')))
 out=Path(a.output_directory);out.mkdir(parents=True,exist_ok=True);f=out/'htcerp_dictionary.json'
 if f.exists():raise FileExistsError('Use a fresh staging directory; do not overwrite an accepted snapshot')
 raw=json.dumps(d,ensure_ascii=False,separators=(',',':')).encode('utf-8');f.write_bytes(raw)
 print(json.dumps({'terms':len(d['terms']),'ip':len(d['ip']),'sha256':hashlib.sha256(raw).hexdigest()},ensure_ascii=False))
if __name__=='__main__':main()
