var MockupCore = (function () {
    function json(v) {
        if(v===null)return 'null';
        if(typeof v==='string')return '"'+v.replace(/\\/g,'\\\\').replace(/"/g,'\\"').replace(/\r/g,'\\r').replace(/\n/g,'\\n').replace(/\t/g,'\\t')+'"';
        if(typeof v==='number'||typeof v==='boolean')return String(v);
        var a=[],k;if(v instanceof Array){for(k=0;k<v.length;k++)a.push(json(v[k]));return '['+a.join(',')+']';}
        for(k in v)if(v.hasOwnProperty(k))a.push(json(k)+':'+json(v[k]));return '{'+a.join(',')+'}';
    }
    function file(p){var f=new File(p);if(!f.exists)throw Error('Missing file: '+p);return f;}
    function fresh(p){var f=new File(p);if(f.exists)throw Error('Refusing to overwrite: '+p);return f;}
    function mkdir(p){var f=new Folder(p);if(!f.exists){if(!f.parent.exists)mkdir(f.parent.fsName);if(!f.create())throw Error('Cannot create '+p);}return f;}
    function write(p,v){var f=fresh(p);mkdir(f.parent.fsName);f.encoding='UTF8';if(!f.open('w'))throw Error('Cannot write '+p);try{f.write(json(v));}finally{f.close();}}
    function findOpen(f){for(var i=0;i<app.documents.length;i++){try{if(app.documents[i].fullName.fsName.toLowerCase()===f.fsName.toLowerCase())return app.documents[i];}catch(e){}}return null;}
    function openCopy(p,label){var f=file(p),prior=findOpen(f),src=prior||app.open(f),copy;try{if(prior&&!src.saved)throw Error('Saved input has unsaved edits open; save a separate version first: '+p);copy=src.duplicate(label,false);}finally{if(!prior)src.close(SaveOptions.DONOTSAVECHANGES);}app.activeDocument=copy;return copy;}
    function placed(path){var d=new ActionDescriptor();d.putPath(charIDToTypeID('null'),file(path));executeAction(charIDToTypeID('Plc '),d,DialogModes.NO);return app.activeDocument.activeLayer;}
    function bounds(l){var b=l.bounds;return [b[0].as('px'),b[1].as('px'),b[2].as('px'),b[3].as('px')];}
    function layerDesc(l){var r=new ActionReference();r.putIdentifier(charIDToTypeID('Lyr '),l.id);return executeActionGet(r);}
    function id(l){return layerDesc(l).getObjectValue(stringIDToTypeID('smartObjectMore')).getString(stringIDToTypeID('ID'));}
    function sourceSize(l){var d=layerDesc(l).getObjectValue(stringIDToTypeID('smartObjectMore')).getObjectValue(stringIDToTypeID('size'));function n(k){k=stringIDToTypeID(k);return d.getType(k)===DescValueType.UNITDOUBLE?d.getUnitDoubleValue(k):d.getDouble(k);}return [n('width'),n('height')];}
    function sourcePpi(l){var d=layerDesc(l).getObjectValue(stringIDToTypeID('smartObjectMore'));return d.getUnitDoubleValue(stringIDToTypeID('resolution'));}
    function event(path,data){var f=new File(path);f.encoding='UTF8';if(!f.open('a'))throw Error('Cannot append progress');try{f.writeln(json(data));}finally{f.close();}}
    function quad(l,q){
        if(!q||q.length!==8)throw Error('Four-corner mapping required');
        var a=new ActionDescriptor(),r=new ActionReference();r.putEnumerated(charIDToTypeID('Lyr '),charIDToTypeID('Ordn'),charIDToTypeID('Trgt'));a.putReference(charIDToTypeID('null'),r);
        var b=bounds(l),v=new ActionList(),i;for(i=0;i<4;i++)v.putDouble(b[i]);a.putList(stringIDToTypeID('rectangle'),v);
        v=new ActionList();for(i=0;i<8;i++){if(typeof q[i]!=='number'||!isFinite(q[i]))throw Error('Invalid mapping');v.putDouble(q[i]);}a.putList(stringIDToTypeID('quadrilateral'),v);executeAction(charIDToTypeID('Trnf'),a,DialogModes.NO);
    }
    function mask(doc,q){if(!q||q.length<6||q.length%2)throw Error('Mask must contain polygon point pairs');var points=[];for(var i=0;i<q.length;i+=2)points.push([q[i],q[i+1]]);doc.selection.select(points);var d=new ActionDescriptor();d.putClass(charIDToTypeID('Nw  '),charIDToTypeID('Chnl'));var r=new ActionReference();r.putEnumerated(charIDToTypeID('Chnl'),charIDToTypeID('Chnl'),charIDToTypeID('Msk '));d.putReference(charIDToTypeID('At  '),r);d.putEnumerated(charIDToTypeID('Usng'),charIDToTypeID('UsrM'),charIDToTypeID('RvlS'));executeAction(charIDToTypeID('Mk  '),d,DialogModes.NO);doc.selection.deselect();}
    function savePSD(doc,p){var o=new PhotoshopSaveOptions();o.layers=true;o.embedColorProfile=true;doc.saveAs(fresh(p),o,true,Extension.LOWERCASE);}
    function saveImage(doc,p,format){if(format==='png'){doc.saveAs(fresh(p),new PNGSaveOptions(),true,Extension.LOWERCASE);}else if(format==='jpg'){var temp=doc.duplicate('MOCKUP_JPEG_EXPORT',false);try{temp.flatten();if(temp.mode!==DocumentMode.RGB)temp.changeMode(ChangeMode.RGB);temp.bitsPerChannel=BitsPerChannelType.EIGHT;var o=new JPEGSaveOptions();o.quality=12;o.embedColorProfile=true;temp.saveAs(fresh(p),o,true,Extension.LOWERCASE);}finally{temp.close(SaveOptions.DONOTSAVECHANGES);}}else throw Error('Unsupported format');}
    function groups(doc){var a=[];for(var i=0;i<doc.layerSets.length;i++)if(/^\d+$/.test(doc.layerSets[i].name))a.push(doc.layerSets[i]);a.sort(function(x,y){return Number(x.name)-Number(y.name);});return a;}
    function only(gs,n){for(var i=0;i<gs.length;i++)gs[i].visible=gs[i].name===String(n);}
    function mother(doc,name){var a=[];for(var i=0;i<doc.artLayers.length;i++)if(doc.artLayers[i].name===name)a.push(doc.artLayers[i]);if(a.length!==1||a[0].kind!==LayerKind.SMARTOBJECT)throw Error('Exactly one root smart-object mother required: '+name);return a[0];}
    function inspect(doc,name){
        var m=mother(doc,name),mid=id(m),gs=groups(doc),seen={},instances=[];
        if(m.visible)throw Error('Mother must be hidden at root');
        function walk(c,scene){for(var i=0;i<c.layers.length;i++){var l=c.layers[i];if(l.typename==='LayerSet')walk(l,scene);else if(l.kind===LayerKind.SMARTOBJECT){var linked=id(l)===mid;if(l.name.indexOf('PRINT_')===0&&!linked)throw Error('Unlinked print instance: '+scene+'/'+l.name);if(linked){var d=layerDesc(l);instances.push({scene:scene,name:l.name,shared:true,user_mask:d.hasKey(stringIDToTypeID('hasUserMask'))&&d.getBoolean(stringIDToTypeID('hasUserMask')),vector_mask:d.hasKey(stringIDToTypeID('hasVectorMask'))&&d.getBoolean(stringIDToTypeID('hasVectorMask'))});}}}}
        for(var i=0;i<gs.length;i++){if(seen[gs[i].name])throw Error('Duplicate scene number');seen[gs[i].name]=true;walk(gs[i],gs[i].name);}
        if(!gs.length||!instances.length)throw Error('No numbered scenes or shared print instances');
        var scene_ids=[],counts={};for(var i=0;i<gs.length;i++){scene_ids.push(gs[i].name);counts[gs[i].name]=0;}for(var i=0;i<instances.length;i++)counts[instances[i].scene]++;
        return {scene_count:gs.length,scene_ids:scene_ids,instance_count:instances.length,instances_by_scene:counts,source_size:sourceSize(m),source_ppi:sourcePpi(m),instances:instances};
    }
    function normalize(input,output,p){
        p=MockupGeometry.profile(p);var src=null,merged=null,dest=null;
        try{
            src=openCopy(input,'MOCKUP_INPUT_COPY');merged=src.duplicate('MOCKUP_INPUT_MERGED',true);src.close(SaveOptions.DONOTSAVECHANGES);src=null;app.activeDocument=merged;
            if(merged.mode!==DocumentMode.RGB)merged.changeMode(ChangeMode.RGB);merged.bitsPerChannel=BitsPerChannelType.EIGHT;
            var original=[merged.width.as('px'),merged.height.as('px')],originalPpi=merged.resolution;
            merged.resizeImage(undefined,undefined,p.ppi,ResampleMethod.NONE);
            var l=merged.activeLayer,b=p.mode==='alpha'?bounds(l):[0,0,original[0],original[1]];
            MockupGeometry.rect(b);var layout=MockupGeometry.fit(b,p.target,p.fit,p.anchor);
            if(p.mode==='alpha')merged.crop([UnitValue(b[0],'px'),UnitValue(b[1],'px'),UnitValue(b[2],'px'),UnitValue(b[3],'px')]);
            var nw=Math.max(1,Math.round(layout.width)),nh=Math.max(1,Math.round(layout.height));
            merged.resizeImage(UnitValue(nw,'px'),UnitValue(nh,'px'),p.ppi,ResampleMethod.BICUBIC);
            dest=app.documents.add(p.canvas[0],p.canvas[1],p.ppi,'NORMALIZED_ARTWORK',NewDocumentMode.RGB,DocumentFill.TRANSPARENT);
            app.activeDocument=merged;var sourceBounds=bounds(merged.activeLayer);l=merged.activeLayer.duplicate(dest,ElementPlacement.PLACEATBEGINNING);app.activeDocument=dest;var destBounds=bounds(l);
            // Align canvas origin, not visible layer bounds: intentional whitespace is retained.
            l.translate(Math.round(layout.x)+sourceBounds[0]-destBounds[0],Math.round(layout.y)+sourceBounds[1]-destBounds[1]);
            saveImage(dest,output,'png');
            return {input:input,output:output,mode:p.mode,fit:p.fit,original_canvas:original,original_ppi:originalPpi,source_ppi:p.ppi,content_bounds:b,layout:layout,canvas:p.canvas,upscaled:layout.scale>1,cropped:p.fit==='cover'&&(layout.width>p.canvas[0]+0.5||layout.height>p.canvas[1]+0.5)};
        }finally{if(src)src.close(SaveOptions.DONOTSAVECHANGES);if(merged)merged.close(SaveOptions.DONOTSAVECHANGES);if(dest)dest.close(SaveOptions.DONOTSAVECHANGES);}
    }
    function run(fn){var units=app.preferences.rulerUnits,dialogs=app.displayDialogs,active=app.documents.length?app.activeDocument:null;app.preferences.rulerUnits=Units.PIXELS;app.displayDialogs=DialogModes.NO;try{return json(fn());}finally{app.preferences.rulerUnits=units;app.displayDialogs=dialogs;if(active){try{app.activeDocument=active;}catch(e){}}}}
    return {json:json,file:file,fresh:fresh,mkdir:mkdir,write:write,event:event,openCopy:openCopy,placed:placed,bounds:bounds,id:id,sourceSize:sourceSize,sourcePpi:sourcePpi,quad:quad,mask:mask,savePSD:savePSD,saveImage:saveImage,groups:groups,only:only,mother:mother,inspect:inspect,normalize:normalize,run:run};
})();
