#target photoshop

/*
 * Photoshop 智能对象批量套图脚本
 * 多场景输出：B/001/1.jpg、B/001/2.jpg……
 *              B/002/1.jpg、B/002/2.jpg……
 * 脚本会把 PSD 顶层中名称为纯数字的图层组（如 1、2、3）识别为场景。
 * V3：自动定位顶层“母稿”；先匹配母稿像素画布/PPI，再替换；检查 PRINT_ 联动。
 */

(function () {
    app.bringToFront();

    // 可自行修改的设置
    var START_NUMBER = 1;
    var NUMBER_DIGITS = 3;
    var JPEG_QUALITY = 12;

    var oldRulerUnits = app.preferences.rulerUnits;
    var oldDialogs = app.displayDialogs;
    var templateDoc = null;
    var targetLayer = null;
    var cfg = typeof PSBatchConfig !== "undefined" ? PSBatchConfig : null;
    var logFile = null;
    var normalizedFolder = null;
    var fitMode = cfg && cfg.fitMode ? cfg.fitMode : "canvas";
    var progress = null;

    try {
        var templateFile = cfg && cfg.templatePath ? new File(cfg.templatePath) : File.openDialog("请选择本次套图的 PSD 模板（本套请选：印区修复版.psd）", "模板:*.psd;*.psb");
        if (!templateFile) return;
        templateDoc = openSelectedTemplate(templateFile);
        targetLayer = findMother(templateDoc);
        var templateState = inspectPrints(templateDoc, targetLayer);
        checkPrintCoverage(templateState);

        if (!targetLayer || targetLayer.typename !== "ArtLayer" || targetLayer.kind !== LayerKind.SMARTOBJECT) {
            alert("请先在图层面板中选中要替换的智能对象图层，然后再运行脚本。", "批量套图");
            return;
        }

        var inputFolder = cfg ? new Folder(cfg.input) : Folder.selectDialog("请选择 A 文件夹（存放待套图片）");
        if (!inputFolder) {
            return;
        }

        var outputFolder = cfg ? new Folder(cfg.output) : Folder.selectDialog("请选择 B 文件夹（存放套图成品）");
        if (!outputFolder) {
            return;
        }

        if (sameFolder(inputFolder, outputFolder)) {
            alert("A 文件夹和 B 文件夹不能是同一个文件夹。", "批量套图");
            return;
        }

        var inputFiles = getSupportedImages(inputFolder);
        if (inputFiles.length === 0) {
            alert("A 文件夹中没有找到可处理的图片。\n\n支持：JPG、JPEG、PNG、TIF、TIFF、PSD、PSB、BMP。", "批量套图");
            return;
        }

        inputFiles.sort(naturalFileCompare);
        if (!cfg) {
            var fitDialog = new Window("dialog", "印花适配方式");
            fitDialog.orientation = "column";
            fitDialog.add("statictext", undefined, "所有素材均等比例完整放入母稿画布，不拉伸、不裁图。");
            var modes = fitDialog.add("dropdownlist", undefined, ["保留原图留白（默认，适合已排版印花）", "去掉外围透明留白（按可见图案适配）"]);
            modes.selection = 0;
            var buttons = fitDialog.add("group");
            buttons.add("button", undefined, "开始", {name:"ok"});
            buttons.add("button", undefined, "取消", {name:"cancel"});
            if (fitDialog.show() !== 1) return;
            fitMode = modes.selection.index === 1 ? "alpha" : "canvas";
        }
        if (fitMode !== "canvas" && fitMode !== "alpha") throw Error("未知适配方式");

        // 顶层纯数字图层组作为需要分别导出的场景。
        var sceneNames = getNumberedSceneNames(templateDoc);
        if (sceneNames.length === 0) {
            alert("没有找到顶层编号图层组。\n\n请把需要分别导出的图层组命名为 1、2、3……，并确保它们位于 PSD 的最外层。", "批量套图");
            return;
        }

        var runName = "套图_" + new Date().getTime();
        outputFolder = new Folder(outputFolder.fsName + "/" + runName);
        if (!outputFolder.create()) throw Error("无法创建本次输出目录");
        normalizedFolder = new Folder(outputFolder.fsName + "/标准化母稿");
        if (!normalizedFolder.create()) throw Error("无法创建标准化目录");
        logFile = new File(outputFolder.fsName + "/运行记录.txt");
        log("模板完整路径：" + templateDoc.fullName.fsName);
        log("模板：" + templateDoc.name + "；源画布：" + templateState.size + "；PPI：" + templateState.ppi);
        log("联动印花实例：" + templateState.prints.length + "；输入：" + inputFiles.length + "；场景：" + sceneNames.join(","));
        var existingCount = countExistingOutputs(outputFolder, inputFiles.length, sceneNames, START_NUMBER, NUMBER_DIGITS);
        if (existingCount > 0) {
            var overwrite = confirm(
                "B 文件夹中已有 " + existingCount + " 个同名 JPG 成品。\n\n继续会覆盖这些 JPG，但不会删除编号文件夹内的其他文件。是否继续？",
                true,
                "确认覆盖"
            );
            if (!overwrite) {
                return;
            }
        }

        app.preferences.rulerUnits = Units.PIXELS;
        app.displayDialogs = DialogModes.NO;

        var totalOutputCount = inputFiles.length * sceneNames.length;
        progress = createProgressWindow(totalOutputCount);
        var successCount = 0;
        var failedItems = [];
        var cancelled = false;
        var processedCount = 0;

        for (var i = 0; i < inputFiles.length; i++) {
            progress.window.update();
            if (progress.cancelled()) {
                cancelled = true;
                break;
            }

            var numberText = padNumber(START_NUMBER + i, NUMBER_DIGITS);
            progress.label.text = "正在套入素材 " + (i + 1) + "/" + inputFiles.length + "：" + inputFiles[i].name;
            progress.bar.value = processedCount;
            progress.window.update();

            var workingDoc = null;
            try {
                app.activeDocument = templateDoc;
                selectWithoutReveal(templateDoc, targetLayer);

                // 每次复制模板再处理，确保原始 PSD 不被修改。
                workingDoc = templateDoc.duplicate("批量套图_" + numberText, false);

                if (!workingDoc.activeLayer || workingDoc.activeLayer.kind !== LayerKind.SMARTOBJECT) {
                    throw new Error("复制模板后未能定位智能对象图层");
                }

                var before = inspectPrints(workingDoc, workingDoc.activeLayer);
                var normalized = normalizeArtwork(inputFiles[i], before, numberText);
                app.activeDocument = workingDoc;
                replaceSmartObjectContents(normalized);
                verifyReplacement(before, inspectPrints(workingDoc, workingDoc.activeLayer));
                log(numberText + " <- " + decodeSafe(inputFiles[i].name) + "；尺寸、联动、透视检查通过");

                var numberedFolder = new Folder(outputFolder.fsName + "/" + numberText);
                if (!numberedFolder.exists && !numberedFolder.create()) {
                    throw new Error("无法创建输出文件夹：" + numberedFolder.fsName);
                }

                var workingScenes = getNumberedSceneGroups(workingDoc);
                if (workingScenes.length !== sceneNames.length) {
                    throw new Error("复制模板后的编号场景组数量发生变化");
                }

                // 同一张素材依次导出每个编号场景组。
                for (var sceneIndex = 0; sceneIndex < workingScenes.length; sceneIndex++) {
                    progress.window.update();
                    if (progress.cancelled()) {
                        cancelled = true;
                        break;
                    }

                    setOnlySceneVisible(workingScenes, sceneIndex);

                    var sceneName = workingScenes[sceneIndex].name.replace(/^\s+|\s+$/g, "");
                    progress.label.text = "素材 " + numberText + "：正在导出场景 " + sceneName + "（" + (sceneIndex + 1) + "/" + workingScenes.length + "）";
                    progress.bar.value = processedCount;
                    progress.window.update();

                    var outputFile = new File(numberedFolder.fsName + "/" + sceneName + ".jpg");
                    var exportDoc = null;
                    try {
                        // 单独复制当前场景后再拼合，避免破坏后续场景所需图层。
                        exportDoc = workingDoc.duplicate("导出_" + numberText + "_" + sceneName, false);
                        saveDocumentAsJpeg(exportDoc, outputFile, JPEG_QUALITY);
                        successCount++;
                        log("已导出：" + numberText + "/" + sceneName + ".jpg");
                    } catch (sceneError) {
                        failedItems.push(numberText + "/" + sceneName + ".jpg：" + cleanError(sceneError));
                    } finally {
                        if (exportDoc) {
                            try {
                                exportDoc.close(SaveOptions.DONOTSAVECHANGES);
                            } catch (exportCloseError) {
                                // 关闭失败不打断后续任务。
                            }
                        }
                    }

                    processedCount++;
                    progress.bar.value = processedCount;
                    progress.window.update();
                }
            } catch (itemError) {
                failedItems.push(numberText + "  <-  " + inputFiles[i].name + "：" + cleanError(itemError));
                log("失败：" + failedItems[failedItems.length - 1]);
            } finally {
                if (workingDoc) {
                    try {
                        workingDoc.close(SaveOptions.DONOTSAVECHANGES);
                    } catch (closeError) {
                        // 关闭失败不打断后续任务。
                    }
                }
            }

            if (cancelled) {
                break;
            }
        }

        progress.bar.value = processedCount;
        progress.window.update();
        progress.window.close();

        app.activeDocument = templateDoc;
        selectWithoutReveal(templateDoc, targetLayer);

        var summary = "批量套图完成。\n\n识别素材：" + inputFiles.length + " 张\n识别场景：" + sceneNames.length + " 个\n成功导出：" + successCount + " 张";
        if (failedItems.length > 0) {
            summary += "\n失败：" + failedItems.length + " 张\n\n失败明细：\n" + failedItems.join("\n");
        }
        if (cancelled) {
            summary += "\n\n任务已由用户中途取消。";
        }
        summary += "\n\n输出位置：\n" + outputFolder.fsName;
        log(summary);
        if (cfg) { cfg.result = {success:successCount, failures:failedItems, output:outputFolder.fsName}; } else alert(summary, "批量套图 V3");
    } catch (error) {
        if (cfg) throw error;
        alert("脚本未能完成：\n" + cleanError(error), "批量套图 V3");
    } finally {
        if (progress) { try { progress.window.close(); } catch (ignored) {} }
        app.preferences.rulerUnits = oldRulerUnits;
        app.displayDialogs = oldDialogs;
        if (templateDoc) {
            try {
                app.activeDocument = templateDoc;
                if (targetLayer) {
                    selectWithoutReveal(templateDoc, targetLayer);
                }
            } catch (restoreError) {
                // 模板可能已由用户关闭。
            }
        }
    }


    function openSelectedTemplate(file) {
        if(!file.exists) throw Error("模板不存在："+file.fsName);
        for(var i=0;i<app.documents.length;i++) {
            var d=app.documents[i], path="";
            try { path=d.fullName.fsName; } catch(e) {}
            if(normalizePath(path)===normalizePath(file.fsName)) {
                if(!d.saved) throw Error("所选模板有未保存修改，请先另存确认，或选择已交付的印区修复版。\n"+path);
                app.activeDocument=d;return d;
            }
        }
        return app.open(file);
    }
    // Conservative preflight for complete-print mockups. This is not an automatic mask repair.
    function checkPrintCoverage(state) {
        for(var i=0;i<state.prints.length;i++) {
            var p=state.prints[i],q=p.transform,b=p.visibleBounds;
            var xs=[q[0],q[2],q[4],q[6]],ys=[q[1],q[3],q[5],q[7]];
            var w=Math.max.apply(Math,xs)-Math.min.apply(Math,xs),h=Math.max.apply(Math,ys)-Math.min.apply(Math,ys);
            var vw=b[2]-b[0],vh=b[3]-b[1];
            if(vw<=0||vh<=0) throw Error("印花实例没有可见区域："+p.path);
            if(w/vw>2.5 && h/vh>2.5) throw Error("印区预检未通过："+p.path+" 的变形范围约为可见区域的 "+(w/vw).toFixed(2)+" × "+(h/vh).toFixed(2)+" 倍，疑似会只显示图案局部。\n本套请使用“男款圣诞T恤-七图联动样机-印区修复版.psd”。\n其他模板如故意局部裁切或有大量透明留白，请先人工核对印区；脚本不会猜测或自动缩放模板。 ");
        }
    }

    function selectWithoutReveal(doc, layer) {
        app.activeDocument=doc;
        var visible=layer.visible;
        doc.activeLayer=layer;
        layer.visible=visible;
    }
    function log(text) {
        if (!logFile) return;
        logFile.encoding = "UTF8";
        if (!logFile.open("a")) throw Error("无法写入运行日志");
        try { logFile.writeln(text); } finally { logFile.close(); }
    }
    function findMother(doc) {
        var found = [];
        for (var i=0;i<doc.artLayers.length;i++) if (doc.artLayers[i].name === "母稿") found.push(doc.artLayers[i]);
        if (found.length !== 1 || found[0].kind !== LayerKind.SMARTOBJECT) throw Error("需要唯一的顶层智能对象图层“母稿”。请勿选择 FIXED_SCENE 背景层。");
        if (found[0].visible) throw Error("顶层母稿必须隐藏，避免遮挡成品。");
        return found[0];
    }
    function meta(layer) {
        var r=new ActionReference();r.putIdentifier(charIDToTypeID("Lyr "),layer.id);
        var d=executeActionGet(r), so=d.getObjectValue(stringIDToTypeID("smartObjectMore"));
        var basic=d.getObjectValue(stringIDToTypeID("smartObject"));
        if (basic.hasKey(stringIDToTypeID("linked")) && basic.getBoolean(stringIDToTypeID("linked"))) throw Error("此版本仅处理嵌入式母稿，请先将链接母稿嵌入。");
        var size=so.getObjectValue(stringIDToTypeID("size"));
        function n(obj,key) {key=stringIDToTypeID(key);return obj.getType(key)===DescValueType.UNITDOUBLE?obj.getUnitDoubleValue(key):obj.getDouble(key);}
        var t=so.getList(stringIDToTypeID("transform")), a=[];
        for(var i=0;i<t.count;i++) a.push(t.getDouble(i));
        if(so.hasKey(stringIDToTypeID("nonAffineTransform"))) { var nt=so.getList(stringIDToTypeID("nonAffineTransform"));for(var j=0;j<nt.count;j++) a.push(nt.getDouble(j)); }
        return {id:so.getString(stringIDToTypeID("ID")),size:[n(size,"width"),n(size,"height")],ppi:n(so,"resolution"),transform:a};
    }
    function inspectPrints(doc,mother) {
        app.activeDocument=doc;
        var m=meta(mother), prints=[], groups=getNumberedSceneGroups(doc), names={};
        function walk(parent,path) {
            for(var i=0;i<parent.layers.length;i++) {
                var l=parent.layers[i], p=path+"/"+l.name;
                if(l.typename==="LayerSet") walk(l,p);
                else if(l.name.indexOf("PRINT_")===0) {
                    if(l.kind!==LayerKind.SMARTOBJECT) throw Error("印花层不是智能对象："+p);
                    var info=meta(l);
                    if(info.id!==m.id) throw Error("印花层未与母稿联动："+p);
                    var lb=l.bounds; info.visibleBounds=[lb[0].as("px"),lb[1].as("px"),lb[2].as("px"),lb[3].as("px")];
                    info.path=p;prints.push(info);
                }
            }
        }
        for(var i=0;i<groups.length;i++) {
            var name=groups[i].name.replace(/^\s+|\s+$/g,"");
            if(names[name]) throw Error("场景编号重复："+name);
            names[name]=true;walk(groups[i],name);
        }
        if(!prints.length) throw Error("未找到与母稿联动的 PRINT_ 印花实例。");
        m.prints=prints;return m;
    }
    function verifyReplacement(a,b) {
        function near(x,y){return Math.abs(x-y)<0.02;}
        if(!near(a.size[0],b.size[0])||!near(a.size[1],b.size[1])||!near(a.ppi,b.ppi)) throw Error("替换后源画布或 PPI 变化，已停止该素材导出。");
        if(a.prints.length!==b.prints.length) throw Error("联动数量发生变化");
        for(var i=0;i<a.prints.length;i++) {
            var x=a.prints[i],y=b.prints[i];
            if(x.path!==y.path || !near(x.size[0],y.size[0]) || !near(x.size[1],y.size[1])) throw Error("实例尺寸发生变化："+x.path);
            for(var j=0;j<x.transform.length;j++) if(!near(x.transform[j],y.transform[j])) throw Error("实例透视坐标发生变化："+x.path);
        }
    }
    function normalizeArtwork(file, target, number) {
        var source=null, merged=null, dest=null, prior=null;
        try {
            for(var i=0;i<app.documents.length;i++) {try{if(normalizePath(app.documents[i].fullName.fsName)===normalizePath(file.fsName)) prior=app.documents[i];}catch(e){}}
            if(prior && !prior.saved) throw Error("素材存在未保存编辑，请先保存："+file.name);
            source=prior || app.open(file);
            merged=source.duplicate("素材标准化_"+number,true);
            if(!prior) source.close(SaveOptions.DONOTSAVECHANGES);
            source=null;
            app.activeDocument=merged;
            if(merged.mode!==DocumentMode.RGB) merged.changeMode(ChangeMode.RGB);
            merged.bitsPerChannel=BitsPerChannelType.EIGHT;
            var originalW=merged.width.as("px"),originalH=merged.height.as("px");
            if(fitMode === "alpha" && !merged.activeLayer.isBackgroundLayer) merged.trim(TrimType.TRANSPARENT,true,true,true,true);
            var w=merged.width.as("px"),h=merged.height.as("px"),oldPpi=merged.resolution;
            var scale=Math.min(target.size[0]/w,target.size[1]/h);
            var nw=Math.max(1,Math.round(w*scale)),nh=Math.max(1,Math.round(h*scale));
            merged.resizeImage(UnitValue(nw,"px"),UnitValue(nh,"px"),target.ppi,ResampleMethod.BICUBIC);
            var src=merged.activeLayer, sb=src.bounds;
            var left=sb[0].as("px"),top=sb[1].as("px");
            if(sb[2].as("px")<=left || sb[3].as("px")<=top) throw Error("印花为空白或全透明");
            dest=app.documents.add(UnitValue(target.size[0],"px"),UnitValue(target.size[1],"px"),target.ppi,"标准化母稿",NewDocumentMode.RGB,DocumentFill.TRANSPARENT);
            app.activeDocument=merged;
            var layer=src.duplicate(dest,ElementPlacement.PLACEATBEGINNING);
            app.activeDocument=dest;
            var db=layer.bounds;
            layer.translate(UnitValue(Math.floor((target.size[0]-nw)/2)+left-db[0].as("px"),"px"),UnitValue(Math.floor((target.size[1]-nh)/2)+top-db[1].as("px"),"px"));
            var output=new File(normalizedFolder.fsName+"/"+number+".psd");
            if(output.exists) throw Error("标准化文件已存在，拒绝覆盖");
            var options=new PhotoshopSaveOptions();options.layers=true;options.embedColorProfile=true;
            dest.saveAs(output,options,true,Extension.LOWERCASE);
            log(number+" 模式="+fitMode+"；原图="+originalW+"x"+originalH+"；适配区域="+w+"x"+h+" @"+oldPpi+"；标准化="+target.size+" @"+target.ppi+"；等比缩放="+scale);
            return output;
        } finally {
            if(source && !prior) source.close(SaveOptions.DONOTSAVECHANGES);
            if(merged) merged.close(SaveOptions.DONOTSAVECHANGES);
            if(dest) dest.close(SaveOptions.DONOTSAVECHANGES);
        }
    }

    function getSupportedImages(folder) {
        var extensionPattern = /\.(jpg|jpeg|png|tif|tiff|psd|psb|bmp)$/i;
        return folder.getFiles(function (entry) {
            return entry instanceof File && extensionPattern.test(entry.name) && entry.name.charAt(0) !== ".";
        });
    }

    function getNumberedSceneNames(documentRef) {
        var groups = getNumberedSceneGroups(documentRef);
        var names = [];
        for (var i = 0; i < groups.length; i++) {
            names.push(groups[i].name.replace(/^\s+|\s+$/g, ""));
        }
        return names;
    }

    function getNumberedSceneGroups(documentRef) {
        var groups = [];
        for (var i = 0; i < documentRef.layerSets.length; i++) {
            var group = documentRef.layerSets[i];
            if (/^\s*\d+\s*$/.test(group.name)) {
                groups.push(group);
            }
        }
        groups.sort(function (groupA, groupB) {
            return naturalTextCompare(groupA.name, groupB.name);
        });
        return groups;
    }

    function setOnlySceneVisible(sceneGroups, visibleIndex) {
        for (var i = 0; i < sceneGroups.length; i++) {
            sceneGroups[i].visible = (i === visibleIndex);
        }
    }

    function naturalFileCompare(fileA, fileB) {
        return naturalTextCompare(decodeSafe(fileA.name), decodeSafe(fileB.name));
    }

    function naturalTextCompare(textA, textB) {
        var a = String(textA).toLowerCase();
        var b = String(textB).toLowerCase();
        var aParts = splitNatural(a);
        var bParts = splitNatural(b);
        var length = Math.min(aParts.length, bParts.length);

        for (var i = 0; i < length; i++) {
            if (aParts[i] === bParts[i]) {
                continue;
            }

            var aIsNumber = /^\d+$/.test(aParts[i]);
            var bIsNumber = /^\d+$/.test(bParts[i]);
            if (aIsNumber && bIsNumber) {
                var aNumber = parseInt(aParts[i], 10);
                var bNumber = parseInt(bParts[i], 10);
                if (aNumber !== bNumber) {
                    return aNumber - bNumber;
                }
            }
            return aParts[i] < bParts[i] ? -1 : 1;
        }

        if (aParts.length !== bParts.length) {
            return aParts.length - bParts.length;
        }
        return a < b ? -1 : (a > b ? 1 : 0);
    }

    function splitNatural(text) {
        var parts = text.match(/\d+|\D+/g);
        return parts || [text];
    }

    function replaceSmartObjectContents(imageFile) {
        var descriptor = new ActionDescriptor();
        descriptor.putPath(charIDToTypeID("null"), imageFile);
        executeAction(stringIDToTypeID("placedLayerReplaceContents"), descriptor, DialogModes.NO);
    }

    function saveDocumentAsJpeg(documentToSave, outputFile, quality) {
        app.activeDocument = documentToSave;
        documentToSave.flatten();

        if (documentToSave.mode !== DocumentMode.RGB) {
            documentToSave.changeMode(ChangeMode.RGB);
        }

        if (documentToSave.bitsPerChannel !== BitsPerChannelType.EIGHT) {
            documentToSave.bitsPerChannel = BitsPerChannelType.EIGHT;
        }

        if (outputFile.exists && !outputFile.remove()) {
            throw new Error("无法覆盖已有文件：" + outputFile.fsName);
        }

        var jpegOptions = new JPEGSaveOptions();
        jpegOptions.quality = quality;
        jpegOptions.embedColorProfile = true;
        jpegOptions.formatOptions = FormatOptions.STANDARDBASELINE;
        jpegOptions.matte = MatteType.NONE;

        documentToSave.saveAs(outputFile, jpegOptions, true, Extension.LOWERCASE);
    }

    function countExistingOutputs(rootFolder, itemCount, sceneNames, startNumber, digits) {
        var count = 0;
        for (var i = 0; i < itemCount; i++) {
            var numberText = padNumber(startNumber + i, digits);
            for (var sceneIndex = 0; sceneIndex < sceneNames.length; sceneIndex++) {
                var outputFile = new File(rootFolder.fsName + "/" + numberText + "/" + sceneNames[sceneIndex] + ".jpg");
                if (outputFile.exists) {
                    count++;
                }
            }
        }
        return count;
    }

    function createProgressWindow(total) {
        var state = { isCancelled: false };
        var windowRef = new Window("palette", "智能对象批量套图");
        windowRef.orientation = "column";
        windowRef.alignChildren = ["fill", "top"];
        windowRef.margins = 16;

        var label = windowRef.add("statictext", undefined, "准备处理 " + total + " 张图片……");
        label.preferredSize.width = 420;

        var bar = windowRef.add("progressbar", undefined, 0, total);
        bar.preferredSize = [420, 18];

        var cancelButton = windowRef.add("button", undefined, "取消");
        cancelButton.alignment = "right";
        cancelButton.onClick = function () {
            state.isCancelled = true;
            cancelButton.enabled = false;
            cancelButton.text = "正在停止……";
        };

        windowRef.center();
        windowRef.show();

        return {
            window: windowRef,
            label: label,
            bar: bar,
            cancelled: function () {
                return state.isCancelled;
            }
        };
    }

    function padNumber(numberValue, digits) {
        var text = String(numberValue);
        while (text.length < digits) {
            text = "0" + text;
        }
        return text;
    }

    function sameFolder(folderA, folderB) {
        return normalizePath(folderA.fsName) === normalizePath(folderB.fsName);
    }

    function normalizePath(pathText) {
        return String(pathText).replace(/\\/g, "/").replace(/\/$/, "").toLowerCase();
    }

    function decodeSafe(text) {
        try {
            return decodeURI(text);
        } catch (error) {
            return text;
        }
    }

    function cleanError(error) {
        if (!error) {
            return "未知错误";
        }
        var message = error.message ? error.message : String(error);
        return message.replace(/^Error:\s*/i, "");
    }
}());
