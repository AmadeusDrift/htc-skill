"""Read the operator's single Chinese form; preserve supplied text in missing-field replies."""
import argparse,json,re
from pathlib import Path
from input_gate import validate_request

FIELDS=['图片目录','本批起始SKU','商品模式','标题模板','云图链接表','上架表','上架样板位置','其他商品信息','分组方式（父子体时填）','父图（父子体时填）','子图及SKU后缀（父子体时填）','售卖方式（父子体时填）','输出位置','特殊要求']
FORM_TEMPLATE='使用 htc上架工作流\n\n【HTC上架工作流输入】\n'+ '\n'.join(k+'：'+{'商品模式':'普通单品','上架样板位置':'自动识别','输出位置':'图片目录同级新文件夹'}.get(k,'') for k in FIELDS)
def canonical(label):return re.sub(r'[（(][^）)]*[）)]','',label).strip()
def strip_markers(value):return re.sub(r'【(?:待补|需确认)[：:][^】]*】','',value)
DISPLAY={canonical(k):k for k in FIELDS}
EMPTY={'','未提供','无','不适用'}

def review_form(text,check_paths=False,known=None):
 """Syntax/path review only; listing sample completeness and business facts need model review."""
 known=known or {};issues={};lines=str(text).splitlines();values={};indices={};duplicates=set();notes=[]
 if '【HTC上架工作流输入】' not in text and not re.search(r'^\s*HTC上架工作流输入\s*$',text,re.M):
  return {'valid':False,'syntaxOnly':True,'missing':['中文结构化表单'],'errors':['请使用合并的中文表单填写后再开始。'],'request':None,'response_form':FORM_TEMPLATE}
 previous=None
 for i,line in enumerate(lines):
  match=re.match(r'^\s*([^：:]+)[：:](.*)$',line)
  key=canonical(match[1]) if match else None
  if key in DISPLAY:
   if key in values:duplicates.add(key)
   else:values[key]=strip_markers(match[2]).strip();indices[key]=i
   previous=key
  elif line.strip() and not line.strip().startswith(('【','使用 ')):
   if previous in ['其他商品信息','特殊要求'] and not match:values[previous]+='\n'+strip_markers(line)
   else:notes.append(line);previous=None
 def get(k,default=''):return values.get(k,default)
 def issue(k,message):issues.setdefault(k,('待补' if get(k).strip() in EMPTY else '需确认',message))
 for key in ['图片目录','本批起始SKU','标题模板']:
  if not get(key).strip():issue(key,'请提供含{关键词}的具体英文标题模板' if key=='标题模板' else '请补充本批'+key)
 for key in duplicates:issue(key,'同一字段重复填写，请确认唯一值')
 mode_text=get('商品模式');has_group=any(get(k).strip() not in EMPTY for k in ['分组方式','父图','子图及SKU后缀','售卖方式'])
 mode={'普通单品':'single','单品':'single','single':'single','父子体':'parent-child','父子变体':'parent-child','parent-child':'parent-child'}.get(mode_text)
 if not mode_text:mode='parent-child' if has_group else 'single'
 if mode is None:issue('商品模式','请选择普通单品或父子体')
 if mode=='single' and has_group:issue('商品模式','已填写父子分组信息，请确认是否为父子体；原填写内容已保留')
 title=get('标题模板')
 if '沿用' in title:
  if isinstance(known.get('title_template'),str) and '{关键词}' in known['title_template']:title=known['title_template'];issues.pop('标题模板',None)
  else:issue('标题模板','当前没有可读取的已确认模板，请补充具体英文模板并保留{关键词}')
 def optional(k):return None if get(k).strip() in EMPTY else get(k)
 output=get('输出位置')
 if output in EMPTY or output in ['图片目录同级新文件夹','同级新目录']:output='同级新目录'
 rows=None;sample=get('上架样板位置')
 if optional('上架表') is not None and sample not in EMPTY and sample!='自动识别':
  m=re.fullmatch(r'\s*(.*?)\s*(?:工作表)?第?\s*(\d+)\s*[～~—–\-至到]\s*(\d+)\s*行\s*',sample)
  if m:
   sheet=re.sub(r'工作表$','',m[1]).strip() or '模板';rows={'sheet':sheet,'first_row':int(m[2]),'last_row':int(m[3])}
  else:issue('上架样板位置','请写“模板工作表第7～10行”，或填自动识别')
 grouping=None
 if mode=='parent-child':
  for key in ['分组方式','父图','子图及SKU后缀','售卖方式']:
   if get(key).strip() in EMPTY:issue(key,'父子体需补充'+key)
  children=[];child_text=get('子图及SKU后缀')
  if child_text.strip() not in EMPTY:
   for item in re.split(r'[，,；;]\s*',child_text):
    m=re.fullmatch(r'\s*(.+?)\s*(?:对应|→|=>|=)\s*(\S+)\s*',item)
    if not m:issue('子图及SKU后缀','请写“左.png对应-A，中.png对应-B，右.png对应-C”');break
    children.append({'file':m[1].strip(),'suffix':m[2]})
  grouping={'unit':get('分组方式'),'parent_file':get('父图'),'children':children,'sale_mode':get('售卖方式')}
 request={'schema_version':'htc-listing-v1','source_dir':get('图片目录'),'start_sku':get('本批起始SKU'),'mode':mode,'grouping':grouping,'cloud_links_workbook':optional('云图链接表'),'listing_workbook':optional('上架表'),'template_rows':rows,'title_template':title,'title_limit':100,'keyword_limit':15,'product_info':{} if get('其他商品信息') in EMPTY else {'说明':get('其他商品信息')},'output_dir':output,'zip':False,'special_requirements':get('特殊要求'),'additional_notes':notes}
 validation=validate_request(request,check_paths=check_paths)
 # Internal diagnostics are mapped back to human field labels, never an English JSON request.
 mapping={'source_dir':'图片目录','start':'本批起始SKU','mode':'商品模式','title_template':'标题模板','output_dir':'输出位置','listing_workbook':'上架表','cloud_links_workbook':'云图链接表','template_rows':'上架样板位置','parent_file':'父图','sale_mode':'售卖方式','suffix':'子图及SKU后缀','child':'子图及SKU后缀','grouping':'分组方式'}
 for err in validation['errors']+validation['missing']:
  if mode=='parent-child' and all(get(k).strip() in EMPTY for k in ['分组方式','父图','子图及SKU后缀','售卖方式']):continue
  label=next((mapping[k] for k in sorted(mapping,key=len,reverse=True) if k in err),'商品模式')
  if 'grouping.children' in err:label='子图及SKU后缀'
  issue(label,{'图片目录':'请确认绝对路径、目录存在且不是占位说明','本批起始SKU':'请填写末尾带数字的完整首SKU，例如SKU001','标题模板':'请填写具体英文标题模板并保留{关键词}','输出位置':'请填写未占用的新目录，或使用图片目录同级新文件夹','上架表':'请确认文件绝对路径及文件存在，未提供可留空','云图链接表':'请确认文件绝对路径及文件存在，未提供可留空','分组方式':'请确认每组目录、文件名及分组方式','父图':'请确认父图相对文件名且与子图不同','售卖方式':'请说明父体和子体分别如何售卖','子图及SKU后缀':'请检查图名与后缀对应关系、唯一性及合法字符','上架样板位置':'请确认工作表和起止行号'}.get(label,'请确认填写内容'))
 response=lines[:]
 for key,(kind,reason) in issues.items():
  marker='【'+kind+'：'+reason+'】'
  if key in indices:response[indices[key]]=strip_markers(response[indices[key]])+marker
  else:response.append(DISPLAY[key]+'：'+marker)
 return {'valid':not issues and validation['valid'],'syntaxOnly':True,'missing':list(issues),'errors':[DISPLAY[k]+'：'+v[1] for k,v in issues.items()],'request':request,'response_form':'\n'.join(response)}

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--form',required=True);ap.add_argument('--check-paths',action='store_true');ap.add_argument('--output');a=ap.parse_args()
 result=review_form(Path(a.form).read_text(encoding='utf-8-sig'),a.check_paths)
 if a.output:Path(a.output).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 if result['valid']:print('中文表单格式检查通过；仍需核对样板及业务必填资料。')
 else:print('本批尚有资料需要补充或确认。请补齐下面中文表单中标注的位置后再开始。\n\n'+result['response_form'])
 return 0 if result['valid'] else 1
if __name__=='__main__':raise SystemExit(main())
