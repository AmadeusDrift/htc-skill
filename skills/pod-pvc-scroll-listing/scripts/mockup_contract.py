"""Portable template manifest and batch-plan contract; no Photoshop dependency."""
import argparse, copy, hashlib, json, math, re
from pathlib import Path

SCHEMA='pod-mockup/1'
EXTENSIONS={'.png','.jpg','.jpeg','.tif','.tiff','.psd','.psb','.bmp'}

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def folder_name(value):
    text=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',str(value)).strip().rstrip('. ')
    if not text:text='未命名'
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?',text):text='_'+text
    if text.casefold() in {'_work','export-report.json','progress.jsonl','cancel.request'}:text+='__art'
    return text[:100].rstrip('. ') or '未命名'
def positive(value):return isinstance(value,(int,float)) and not isinstance(value,bool) and math.isfinite(value) and value>0

def validate_manifest(data,base=None):
    m=copy.deepcopy(data);base=Path(base or '.').resolve()
    if m.get('schema_version')!=SCHEMA:raise ValueError('Unsupported template schema')
    ident=m.get('template_id','')
    if not re.fullmatch(r'[A-Za-z0-9_-]+',ident):raise ValueError('Invalid template_id')
    scenes=m.get('scene_ids');n=len(scenes) if isinstance(scenes,list) else 0
    if not n or scenes!=[str(i) for i in range(1,n+1)]:raise ValueError('scene_ids must be ordered 1..N')
    counts=m.get('expected_instances_by_scene',{})
    if set(counts)!=set(scenes) or any(not isinstance(v,int) or isinstance(v,bool) or v<0 for v in counts.values()) or sum(counts.values())<1:raise ValueError('Declare all scene instance counts, including fixed scenes')
    if not isinstance(m.get('mother'),str) or not m['mother'].strip():raise ValueError('Mother name required')
    p=m.get('profile',{});canvas=p.get('canvas',[])
    if len(canvas)!=2 or any(not positive(v) or int(v)!=v for v in canvas):raise ValueError('Invalid source canvas')
    p.setdefault('ppi',72)
    if not positive(p['ppi']):raise ValueError('Invalid source PPI')
    if p.get('mode') not in ('canvas','alpha') or p.get('fit') not in ('cover','contain'):raise ValueError('Explicit source mode and fit required')
    if p['mode']=='alpha' and p['fit']!='contain':raise ValueError('Alpha cutout must preserve complete content')
    target=p.get('target',[0,0,*canvas])
    if len(target)!=4 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in target) or not (0<=target[0]<target[2]<=canvas[0] and 0<=target[1]<target[3]<=canvas[1]):raise ValueError('Invalid target rectangle')
    psd=Path(m['psd']);psd=psd if psd.is_absolute() else base/psd;psd=psd.resolve()
    if psd.suffix.lower()!='.psd' or not psd.is_file():raise ValueError('Saved PSD required')
    if not re.fullmatch('[a-fA-F0-9]{64}',m.get('sha256','')) or sha(psd).lower()!=m['sha256'].lower():raise ValueError('Template hash mismatch')
    m['psd']=str(psd);m['folder']=folder_name(m.get('name',ident));return m

def natural(path):
    return [(1,int(s)) if s.isdigit() else (0,s.casefold()) for s in re.split(r'(\d+)',path.name)]

def plan_batch(manifests,input_dir,output_root,format='png',base=None):
    if format not in ('png','jpg'):raise ValueError('Unsupported output format')
    if Path(output_root).exists():raise ValueError('Output directory must be new')
    templates=[validate_manifest(m,base) for m in manifests]
    if not templates or len({m['template_id'] for m in templates})!=len(templates):raise ValueError('Unique template IDs required')
    if len({m['folder'].casefold() for m in templates})!=len(templates):raise ValueError('Template display folders collide')
    files=sorted((p for p in Path(input_dir).iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS and not p.name.startswith('.')),key=natural)
    if not files:raise ValueError('No supported artwork files')
    inputs=[];used=set()
    for index,p in enumerate(files,1):
        name=folder_name(p.stem);candidate=name;serial=2
        while candidate.casefold() in used:candidate=f'{name}__{serial:03d}';serial+=1
        used.add(candidate.casefold());inputs.append({'id':f'art{index:04d}','name':p.stem,'folder':candidate,'path':str(p.resolve())})
    jobs=[]
    for m in templates:
        jobs.append({'id':m['template_id'],'folder':m['folder'],'template':m['psd'],'template_sha256':m['sha256'],'mother':m['mother'],'expected_scene_ids':m['scene_ids'],'expected_instances':sum(m['expected_instances_by_scene'].values()),'expected_instances_by_scene':m['expected_instances_by_scene'],'profile':m['profile'],'inputs':copy.deepcopy(inputs),'quality_status':m.get('quality_status','candidate')})
    return {'schema_version':SCHEMA,'format':format,'output':str(Path(output_root).resolve()),'output_layout':'artwork' if len(jobs)==1 else 'artwork-template','planned_images':sum(len(m['scene_ids']) for m in templates)*len(inputs),'jobs':jobs}

def register(inspection,psd,ident,product_type,fit='contain',mode='canvas'):
    data=inspection.get('inspection',inspection);source=Path(psd).resolve()
    counts={s:0 for s in data['scene_ids']}
    for item in data['instances']:counts[item['scene']]+=1
    return validate_manifest({'schema_version':SCHEMA,'template_id':ident,'product_type':product_type,'name':ident,'psd':str(source),'sha256':sha(source),'mother':inspection.get('mother','母稿'),'scene_ids':data['scene_ids'],'profile':{'canvas':data['source_size'],'ppi':data['source_ppi'],'mode':mode,'fit':fit},'expected_instances_by_scene':counts,'quality_status':'candidate','qa_evidence':[]})

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('plan');p.add_argument('--manifest',action='append',required=True);p.add_argument('--input-dir',required=True);p.add_argument('--output-root',required=True);p.add_argument('--format',choices=['png','jpg'],default='png');p.add_argument('--config',required=True)
    p=sub.add_parser('register');p.add_argument('--inspection',required=True);p.add_argument('--psd',required=True);p.add_argument('--id',required=True);p.add_argument('--product-type',required=True);p.add_argument('--fit',choices=['contain','cover'],required=True);p.add_argument('--mode',choices=['canvas','alpha'],default='canvas');p.add_argument('--manifest',required=True)
    p=sub.add_parser('validate');p.add_argument('--manifest',required=True)
    args=parser.parse_args()
    if args.command=='validate':
        m=validate_manifest(read(args.manifest),Path(args.manifest).parent);print(json.dumps({'status':'valid','template_id':m['template_id']},ensure_ascii=True));return
    if args.command=='plan':
        manifests=[validate_manifest(read(p),Path(p).parent) for p in args.manifest];data=plan_batch(manifests,args.input_dir,args.output_root,args.format);out=Path(args.config)
    else:data=register(read(args.inspection),args.psd,args.id,args.product_type,args.fit,args.mode);out=Path(args.manifest)
    if out.exists():raise ValueError('Refusing to overwrite configuration or manifest')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'status':'written','path':str(out.resolve()),'planned_images':data.get('planned_images')},ensure_ascii=True))

if __name__=='__main__':main()
