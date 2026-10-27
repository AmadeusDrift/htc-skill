#target photoshop
(function(){
var _canvasProvidedJob=typeof MOCKUP_CURRENT_JOB==='undefined'?null:MOCKUP_CURRENT_JOB;
if(_canvasProvidedJob)MOCKUP_CURRENT_JOB=undefined;
var _canvasInteractive=!_canvasProvidedJob;
var _canvasReplaceTools=new File($.fileName).parent.fsName;
$.evalFile(new File(_canvasReplaceTools+'/mockup-geometry.js'));
$.evalFile(new File(_canvasReplaceTools+'/mockup-core.js'));
var _canvasPreview=null;
function canvasReplaceCurrent(job){
    var C=MockupCore,doc=null,keep=false;
    try{
        if(job.template)doc=C.openCopy(job.template,'换图预览-'+new File(job.input).name);
        else{
            if(!app.documents.length)throw Error('请先打开联动PSD，返回主文档后运行本脚本，不需要进入母稿内部。');
            C.mother(app.activeDocument,'母稿');doc=app.activeDocument.duplicate('换图预览-'+new File(job.input).name,false);app.activeDocument=doc;
        }
        var check=C.inspect(doc,'母稿'),size=check.source_size;
        var profile={canvas:size,ppi:check.source_ppi,mode:job.mode||'canvas',fit:job.fit||(job.mode==='alpha'?'contain':'cover')};if(job.target)profile.target=job.target;
        var output=job.output||Folder.temp.fsName+'/canvas-replace-'+new Date().getTime()+'-'+Math.round(Math.random()*1000000);
        if(new Folder(output).exists)throw Error('换图输出目录已存在，请使用新目录。');C.mkdir(output);
        var layout=C.normalize(job.input,output+'/normalized.png',profile);
        app.activeDocument=doc;var mother=C.mother(doc,'母稿');doc.activeLayer=mother;
        var d=new ActionDescriptor();d.putPath(charIDToTypeID('null'),C.file(output+'/normalized.png'));executeAction(stringIDToTypeID('placedLayerReplaceContents'),d,DialogModes.NO);mother.visible=false;
        var after=C.inspect(doc,'母稿');if(after.instance_count!==check.instance_count)throw Error('换图后共享实例数量异常');
        var files=[];if(job.scenes){var gs=C.groups(doc);for(var i=0;i<job.scenes.length;i++){var n=String(job.scenes[i]),exists=false;for(var z=0;z<check.scene_ids.length;z++)if(check.scene_ids[z]===n)exists=true;if(!exists)throw Error('场景编号不在此模板中');C.only(gs,n);var path=output+'/'+n+'.png';C.saveImage(doc,path,'png');files.push(path);}}
        var result={status:'replaced_in_copy',layout:layout,inspection:after,outputs:files};C.write(output+'/replacement-report.json',result);
        if(!job.closeAfter){keep=true;_canvasPreview=doc;}
        return result;
    }finally{if(doc&&!keep)doc.close(SaveOptions.DONOTSAVECHANGES);}
}
var _canvasReplaceResult;
try{
    if(_canvasInteractive){
        var _canvasPick=File.openDialog('选择新印花：自动等比铺满，替换母稿并联动更新');
        if(_canvasPick)_canvasReplaceResult=MockupCore.run(function(){return canvasReplaceCurrent({input:_canvasPick.fsName});});
    }else _canvasReplaceResult=MockupCore.run(function(){return canvasReplaceCurrent(_canvasProvidedJob);});
    if(_canvasPreview)app.activeDocument=_canvasPreview;
}catch(_canvasReplaceError){if(_canvasInteractive)alert('换图未完成：\n'+_canvasReplaceError.message);else throw _canvasReplaceError;}
return _canvasReplaceResult;
})();
