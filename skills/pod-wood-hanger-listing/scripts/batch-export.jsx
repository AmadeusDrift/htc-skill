#target photoshop
if(typeof MOCKUP_JOB==='undefined'||typeof MOCKUP_TOOLS==='undefined')throw Error('Use run-mockup.ps1 -Mode Export -ConfigPath <json>');
$.evalFile(new File(MOCKUP_TOOLS+'/mockup-geometry.js'));$.evalFile(new File(MOCKUP_TOOLS+'/mockup-core.js'));
MockupCore.run(function(){
 var C=MockupCore,G=MockupGeometry,job=MOCKUP_JOB,format=job.format||'png',results=[],failures=[],seen={},cancelled=false,completed=0,total=0,i,k;
 if(format!=='png'&&format!=='jpg')throw Error('Format must be png or jpg');
 if(!job.jobs||!job.jobs.length)throw Error('At least one export job required');
 if(new Folder(job.output).exists||new File(job.output).exists)throw Error('Output must be a NEW directory: '+job.output);
 var layout=job.output_layout||'template-artwork';if(layout!=='template-artwork'&&layout!=='artwork-template'&&layout!=='artwork')throw Error('Invalid output layout');
 if(layout==='artwork'&&job.jobs.length!==1)throw Error('Single-template layout requires exactly one job');
 function cancelledNow(){return new File(job.cancel_file||job.output+'/cancel.request').exists;}
 function emit(type,data){data.event=type;data.completed_images=completed;data.planned_images=total;C.event(job.output+'/progress.jsonl',data);}
 for(i=0;i<job.jobs.length;i++){
  var j=job.jobs[i];C.file(j.template);G.profile(j.profile);if(!j.inputs||!j.inputs.length)throw Error('At least one artwork input required');
  if(!/^[A-Za-z0-9_-]+$/.test(j.id)||seen[j.id])throw Error('Invalid or duplicate job id');seen[j.id]=true;G.safeSegment(j.folder||j.id);
  var expected=j.expected_scene_ids||G.sceneIds(j.scene_count||7);G.checkScenes(expected,G.sceneIds(expected.length));
  var requested=j.scenes||expected,sceneSeen={};
  for(var n=0;n<requested.length;n++){var s=String(requested[n]),found=false;for(var z=0;z<expected.length;z++)if(expected[z]===s)found=true;if(!found||sceneSeen[s])throw Error('Invalid or duplicate selected scene');sceneSeen[s]=true;}
  if(!requested.length)throw Error('At least one scene required');total+=j.inputs.length*requested.length;
  var ids={},folders={};for(k=0;k<j.inputs.length;k++){var input=j.inputs[k];C.file(input.path);if(!/^[A-Za-z0-9_-]+$/.test(input.id)||ids[input.id])throw Error('Invalid or duplicate artwork id');ids[input.id]=true;var folder=G.safeSegment(input.folder||input.id).toLowerCase();if(folders[folder])throw Error('Duplicate artwork folder');folders[folder]=true;}
 }
 C.mkdir(job.output);emit('batch_started',{status:'running'});
 for(i=0;i<job.jobs.length&&!cancelled;i++){
  var j=job.jobs[i];
  for(k=0;k<j.inputs.length;k++){
   if(cancelledNow()){cancelled=true;break;}
   var input=j.inputs[k],doc=null,outputs=[],artFolder=input.folder||input.id,templateFolder=j.folder||j.id;
   var dir;if(layout==='artwork')dir=job.output+'/'+artFolder;else if(layout==='artwork-template')dir=job.output+'/'+artFolder+'/'+templateFolder;else dir=job.output+'/'+templateFolder+'/'+artFolder;
   var internalDir=job.schema_version==='pod-mockup/1'?job.output+'/_work/'+j.id+'/'+input.id:dir;
   try{
    emit('artwork_started',{template:j.id,artwork:input.id,name:input.name||artFolder});
    C.mkdir(dir);C.mkdir(internalDir);var normalized=internalDir+'/normalized.png',adapted=C.normalize(input.path,normalized,j.profile);
    doc=C.openCopy(j.template,'MOCKUP_WORKING_'+j.id+'_'+input.id);var before=C.inspect(doc,j.mother||'母稿'),expected=j.expected_scene_ids||G.sceneIds(j.scene_count||7);
    G.checkScenes(before.scene_ids,expected);
    if(before.source_size[0]!==j.profile.canvas[0]||before.source_size[1]!==j.profile.canvas[1]||Math.abs(before.source_ppi-(j.profile.ppi||72))>0.1)throw Error('Profile differs from embedded mother pixel dimensions or PPI');
    if(j.expected_instances!==undefined&&before.instance_count!==j.expected_instances)throw Error('Print instance count mismatch');
    if(j.expected_instances_by_scene)for(var s in j.expected_instances_by_scene)if(j.expected_instances_by_scene.hasOwnProperty(s)&&before.instances_by_scene[s]!==j.expected_instances_by_scene[s])throw Error('Scene '+s+' print instance count mismatch');
    var mother=C.mother(doc,j.mother||'母稿');doc.activeLayer=mother;var d=new ActionDescriptor();d.putPath(charIDToTypeID('null'),C.file(normalized));executeAction(stringIDToTypeID('placedLayerReplaceContents'),d,DialogModes.NO);mother.visible=false;
    var after=C.inspect(doc,j.mother||'母稿');if(after.instance_count!==before.instance_count)throw Error('Shared instances changed after replacement');
    var requested=j.scenes||expected,gs=C.groups(doc);
    for(var n=0;n<requested.length;n++){if(cancelledNow()){cancelled=true;break;}var s=String(requested[n]);C.only(gs,s);var out=dir+'/'+s+'.'+format;C.saveImage(doc,out,format);outputs.push(out);completed++;emit('image_exported',{template:j.id,artwork:input.id,scene:s,path:out});}
    C.write(internalDir+'/layout.json',adapted);results.push({template:j.id,artwork:input.id,name:input.name||artFolder,status:cancelled?'cancelled':'complete',expected_scene_ids:expected,requested_scene_ids:requested,outputs:outputs,layout:adapted,inspection:after});if(cancelled)break;
   }catch(e){var failure={template:j.id,artwork:input.id,error:String(e.message||e),outputs:outputs};failures.push(failure);emit('artwork_failed',failure);}
   finally{if(doc)doc.close(SaveOptions.DONOTSAVECHANGES);}
  }
 }
 var status='complete';if(cancelled)status='cancelled';else if(failures.length)status='partial_failure';
 var result={schema_version:'pod-mockup/1',status:status,format:format,planned_images:total,completed_images:completed,results:results,failures:failures};C.write(job.output+'/export-report.json',result);emit('batch_finished',{status:result.status});return result;
});
