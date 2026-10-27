var MockupGeometry = (function () {
    function rect(r) {
        if (!r || r.length !== 4) throw Error('Invalid bounds');
        for (var i=0;i<4;i++) if (typeof r[i] !== 'number' || !isFinite(r[i])) throw Error('Invalid bounds');
        if (r[2]<=r[0] || r[3]<=r[1]) throw Error('Empty bounds');
        return r;
    }
    function fit(bounds, target, mode, anchor) {
        rect(bounds); rect(target);
        if (mode !== 'contain' && mode !== 'cover') throw Error('Unsupported fit');
        if (anchor !== 'center') throw Error('Unsupported anchor');
        var w=bounds[2]-bounds[0],h=bounds[3]-bounds[1];
        var sx=(target[2]-target[0])/w,sy=(target[3]-target[1])/h;
        var scale=mode==='cover'?Math.max(sx,sy):Math.min(sx,sy);
        return {scale:scale,width:w*scale,height:h*scale,x:target[0]+((target[2]-target[0])-w*scale)/2,y:target[1]+((target[3]-target[1])-h*scale)/2};
    }
    function profile(p) {
        if (!p || !p.canvas || p.canvas.length!==2) throw Error('Missing canvas');
        var w=p.canvas[0],h=p.canvas[1];rect([0,0,w,h]);
        if (w!==Math.floor(w)||h!==Math.floor(h)) throw Error('Canvas must use integer pixels');
        if (p.mode!=='canvas' && p.mode!=='alpha') throw Error('Explicit mode canvas or alpha required');
        var target=p.target || [0,0,w,h];rect(target);
        if (target[0]<0 || target[1]<0 || target[2]>w || target[3]>h) throw Error('Invalid target outside canvas');
        var f=p.fit || 'contain';if(f!=='contain'&&f!=='cover')throw Error('Unsupported fit');
        if(p.mode==='alpha'&&f==='cover')throw Error('alpha cutouts require contain; use canvas cover for approved full artwork');
        var ppi=p.ppi===undefined?72:p.ppi;if(typeof ppi!=='number'||!isFinite(ppi)||ppi<=0)throw Error('Invalid source PPI');
        return {canvas:[w,h],target:target,mode:p.mode,fit:f,anchor:'center',ppi:ppi};
    }
    function sceneIds(n){if(typeof n!=='number'||n<1||Math.floor(n)!==n)throw Error('Invalid scene count');var a=[];for(var i=1;i<=n;i++)a.push(String(i));return a;}
    function checkScenes(actual,expected){if(actual.length!==expected.length)throw Error('Scene count mismatch');for(var i=0;i<actual.length;i++)if(actual[i]!==String(expected[i]))throw Error('Scene identifiers mismatch');}
    function safeSegment(value){if(typeof value!=='string'||!value||/[<>:"\/\\|?*\x00-\x1f]/.test(value)||/[. ]$/.test(value)||value==='.'||value==='..'||/^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?$/i.test(value))throw Error('Unsafe output folder');return value;}
    return {fit:fit,profile:profile,rect:rect,sceneIds:sceneIds,checkScenes:checkScenes,safeSegment:safeSegment};
})();
