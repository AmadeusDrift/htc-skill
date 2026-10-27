"""Check declared complete scene sets and unchanged template hashes."""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image

def validate(report_path, before_path):
    data=json.loads(Path(report_path).read_text(encoding='utf-8-sig'))
    assert data['status']=='complete' and not data['failures'], 'Export did not complete'
    assert data['results'], 'No completed artwork sets'
    count=0
    for item in data['results']:
        files=[Path(p) for p in item['outputs']]
        inspection=item['inspection']
        expected=item.get('expected_scene_ids',[str(i) for i in range(1,inspection['scene_count']+1)])
        requested=item.get('requested_scene_ids',expected)
        assert requested==expected, 'Selected-scene rerun is not a complete set'
        assert len(files)==len(expected) and {p.stem for p in files}==set(expected), 'Incomplete scene set'
        assert inspection['scene_count']==len(expected) and inspection['instance_count']>0
        assert all(p['shared'] for p in inspection['instances'])
        for p in files:
            with Image.open(p) as im:
                assert im.format==('PNG' if data['format']=='png' else 'JPEG')
                im.verify()
        normalized=Path(item['layout']['output'])
        with Image.open(normalized) as im:
            assert list(im.size)==item['layout']['canvas']
        count+=len(files)
    hashes=json.loads(Path(before_path).read_text(encoding='utf-8-sig'))
    for item in hashes:
        assert hashlib.sha256(Path(item['Path']).read_bytes()).hexdigest().upper()==item['Hash'].upper(), 'Template changed: '+item['Path']
    return {'status':'pass','sets':len(data['results']),'images':count,'unchanged_templates':len(hashes),'scope':'native shared-object export, file completeness and hashes; visual review is separate'}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--report',required=True);parser.add_argument('--hashes-before',required=True)
    args=parser.parse_args();print(json.dumps(validate(args.report,args.hashes_before),ensure_ascii=False))
