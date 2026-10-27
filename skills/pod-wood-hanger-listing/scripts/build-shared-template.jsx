#target photoshop
if(typeof MOCKUP_JOB==='undefined'||typeof MOCKUP_TOOLS==='undefined')throw Error('Use run-mockup.ps1 -Mode Build -ConfigPath <json>');
$.evalFile(new File(MOCKUP_TOOLS+'/mockup-geometry.js'));
$.evalFile(new File(MOCKUP_TOOLS+'/mockup-core.js'));
MockupCore.run(function(){
    var C=MockupCore,job=MOCKUP_JOB,results=[],i,s,phase='preflight';
    for(i=0;i<job.templates.length;i++){var p=job.templates[i];C.fresh(p.output);if(!p.scenes||!p.scenes.length)throw Error('Scene declarations required');var ids=[];for(s=0;s<p.scenes.length;s++){ids.push(String(p.scenes[s].number));C.file(p.scenes[s].base);}MockupGeometry.checkScenes(ids,p.expected_scene_ids||MockupGeometry.sceneIds(p.scenes.length));}
    for(i=0;i<job.templates.length;i++){
        var p=job.templates[i],source=null,doc=null;
        try{
            C.mkdir(new File(p.output).parent.fsName);C.mkdir(new File(p.source).parent.fsName);
            if(!new File(p.source).exists){source=app.documents.add(p.canvas[0],p.canvas[1],p.ppi||72,'标准印花母稿',NewDocumentMode.RGB,DocumentFill.WHITE);source.activeLayer.name='替换印花，保留画布尺寸';C.savePSD(source,p.source);source.close(SaveOptions.DONOTSAVECHANGES);source=null;}
            doc=app.documents.add(p.document[0],p.document[1],72,p.id+'-'+p.scenes.length+'图联动母版',NewDocumentMode.RGB,DocumentFill.TRANSPARENT);
            var mother=C.placed(p.source);mother.name='母稿';mother.visible=false;
            for(s=0;s<p.scenes.length;s++){
                var scene=p.scenes[s],g=doc.layerSets.add();g.name=String(scene.number);g.visible=true;doc.activeLayer=g;doc.activeChannels=doc.componentChannels;phase=p.id+'/scene-'+scene.number+'/base';
                var base=C.placed(scene.base);base.name='FIXED_SCENE';base.move(g,ElementPlacement.INSIDE);
                if(base.bounds[0].as('px')!==0||base.bounds[1].as('px')!==0||Math.round(base.bounds[2].as('px'))!==p.document[0]||Math.round(base.bounds[3].as('px'))!==p.document[1])throw Error('Scene size mismatch: '+scene.base);
                for(var k=0;k<(scene.prints||[]).length;k++){
                    phase=p.id+'/scene-'+scene.number+'/print-'+k;var map=scene.prints[k],l=mother.duplicate(g,ElementPlacement.INSIDE);l.name='PRINT_'+(k+1);l.visible=true;doc.activeLayer=l;l.blendMode=BlendMode.MULTIPLY;
                    C.quad(l,map.quad);C.mask(doc,map.mask||map.quad);
                }
                g.visible=scene.number===1;
            }
            mother.move(doc,ElementPlacement.PLACEATBEGINNING);doc.activeLayer=mother;mother.visible=false;
            phase=p.id+'/inspect';var report=C.inspect(doc,'母稿');if(report.source_size[0]!==p.canvas[0]||report.source_size[1]!==p.canvas[1])throw Error('Canonical source mismatch');
            C.savePSD(doc,p.output);results.push({id:p.id,path:p.output,inspection:report});
        }catch(e){throw Error(phase+': '+e.message+' (line '+e.line+')');}finally{if(source)source.close(SaveOptions.DONOTSAVECHANGES);if(doc)doc.close(SaveOptions.DONOTSAVECHANGES);}
    }
    C.write(job.report,{status:'built',templates:results});return {status:'built',templates:results};
});
