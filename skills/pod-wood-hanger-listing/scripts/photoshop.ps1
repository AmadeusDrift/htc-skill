param(
    [ValidateSet('Probe', 'Build', 'Inspect', 'TrialReplace')]
    [string]$Mode = 'Probe',
    [string]$SpecPath,
    [string]$DocumentPath
)
$ErrorActionPreference = 'Stop'

function Get-ExistingPath([string]$Value) {
    if (-not $Value -or -not (Test-Path -LiteralPath $Value -PathType Leaf)) {
        throw "Input file does not exist: $Value"
    }
    return (Resolve-Path -LiteralPath $Value).Path
}

function Get-NewPath([string]$Value, [string]$Extension) {
    if (-not $Value) { throw 'Output path is required' }
    $resolved = [IO.Path]::GetFullPath($Value)
    if ([IO.Path]::GetExtension($resolved).ToLowerInvariant() -ne $Extension) {
        throw "Output must use $Extension"
    }
    if (Test-Path -LiteralPath $resolved) { throw "Refusing to overwrite: $resolved" }
    if (-not (Test-Path -LiteralPath ([IO.Path]::GetDirectoryName($resolved)) -PathType Container)) {
        throw 'Output parent directory must already exist'
    }
    return $resolved
}

$settings = @{}
if ($Mode -eq 'Build' -or $Mode -eq 'TrialReplace') {
    $settings = Get-Content -LiteralPath (Get-ExistingPath $SpecPath) -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($Mode -eq 'Build') {
        $settings.base_path = Get-ExistingPath $settings.base_path
        $settings.artwork_path = Get-ExistingPath $settings.artwork_path
        $settings.output_path = Get-NewPath $settings.output_path '.psd'
        foreach ($field in @('x', 'y', 'width', 'height')) {
            $value = $settings.region.$field
            if ($null -eq $value -or $value -is [bool] -or $value -is [string] -or
                [double]::IsNaN([double]$value) -or [double]::IsInfinity([double]$value)) {
                throw "region.$field must be finite numeric pixels"
            }
        }
    } else {
        $settings.template_path = Get-ExistingPath $settings.template_path
        $settings.artwork_path = Get-ExistingPath $settings.artwork_path
        $settings.preview_path = Get-NewPath $settings.preview_path '.png'
    }
} elseif ($Mode -eq 'Inspect') {
    $settings = @{ document_path = Get-ExistingPath $DocumentPath }
}
$payload = $settings | ConvertTo-Json -Depth 20 -Compress
$modePayload = ConvertTo-Json -InputObject $Mode -Compress
$jsx = @'
function runPodJob(spec, mode) {
    function quote(s) {
        return '"' + String(s).replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\r/g, '\\r').replace(/\n/g, '\\n').replace(/\t/g, '\\t') + '"';
    }
    function encode(value) {
        if (value === null) return 'null';
        if (typeof value === 'string') return quote(value);
        if (typeof value === 'number' || typeof value === 'boolean') return String(value);
        var out = [], i;
        if (value instanceof Array) {
            for (i = 0; i < value.length; i++) out.push(encode(value[i]));
            return '[' + out.join(',') + ']';
        }
        for (i in value) if (value.hasOwnProperty(i)) out.push(quote(i) + ':' + encode(value[i]));
        return '{' + out.join(',') + '}';
    }
    if (mode === 'Probe') return encode({version: app.version, documents: app.documents.length});
    function file(path) {
        var f = new File(path);
        if (!f.exists) throw new Error('Missing input: ' + path);
        return f;
    }
    function newFile(path) {
        var f = new File(path);
        if (f.exists) throw new Error('Refusing to overwrite: ' + path);
        return f;
    }
    function place(path) {
        var desc = new ActionDescriptor();
        desc.putPath(charIDToTypeID('null'), file(path));
        executeAction(charIDToTypeID('Plc '), desc, DialogModes.NO);
        return app.activeDocument.activeLayer;
    }
    function bounds(layer) {
        var b = layer.bounds;
        return [b[0].as('px'), b[1].as('px'), b[2].as('px'), b[3].as('px')];
    }
    function openExisting(path) {
        var target = file(path).fsName.toLowerCase();
        for (var i = 0; i < app.documents.length; i++) {
            try {
                if (app.documents[i].fullName.fsName.toLowerCase() === target) return app.documents[i];
            } catch (untitled) {}
        }
        return null;
    }
    function copySource(path, merged) {
        var existing = openExisting(path);
        var source = existing || app.open(file(path));
        var copy = source.duplicate('POD working copy', merged);
        if (!existing) source.close(SaveOptions.DONOTSAVECHANGES);
        app.activeDocument = copy;
        return copy;
    }
    function findPrint(doc, name) {
        var result = doc.artLayers.getByName(name || 'PRINT_ARTWORK');
        if (result.kind !== LayerKind.SMARTOBJECT) throw new Error(result.name + ' is not a smart object');
        return result;
    }
    var oldDialogs = app.displayDialogs;
    var oldUnits = app.preferences.rulerUnits;
    var doc = null, temp = null;
    var previous = app.documents.length ? app.activeDocument : null;
    try {
        app.displayDialogs = DialogModes.NO;
        app.preferences.rulerUnits = Units.PIXELS;
        if (mode === 'Build') {
            // Duplicate the source: never save or close a pre-existing user document.
            doc = copySource(spec.base_path, true);
            app.activeDocument = doc;
            doc.activeLayer.name = 'FIXED_SCENE';
            var r = spec.region;
            if (r.x < 0 || r.y < 0 || r.width <= 0 || r.height <= 0 ||
                r.x + r.width > doc.width.as('px') || r.y + r.height > doc.height.as('px')) {
                throw new Error('Print region is outside the fixed canvas');
            }
            var layer = place(spec.artwork_path);
            layer.name = 'PRINT_ARTWORK';
            var b = bounds(layer), w = b[2] - b[0], h = b[3] - b[1];
            if (w <= 0 || h <= 0) throw new Error('Artwork has empty bounds');
            var scale = Math.min(r.width / w, r.height / h) * 100;
            layer.resize(scale, scale, AnchorPosition.MIDDLECENTER);
            b = bounds(layer);
            layer.translate(UnitValue(r.x + r.width / 2 - (b[0] + b[2]) / 2, 'px'),
                            UnitValue(r.y + r.height / 2 - (b[1] + b[3]) / 2, 'px'));
            var options = new PhotoshopSaveOptions(); options.layers = true;
            doc.saveAs(newFile(spec.output_path), options, false, Extension.LOWERCASE);
            return encode({status:'PSD_CREATED', path:spec.output_path, smartObject:layer.kind === LayerKind.SMARTOBJECT, bounds:bounds(layer)});
        }
        var sourcePath = mode === 'Inspect' ? spec.document_path : spec.template_path;
        doc = copySource(sourcePath, false);
        app.activeDocument = doc;
        var print = findPrint(doc);
        if (mode === 'Inspect') {
            var names = [], instances = [];
            for (var i = 0; i < doc.layers.length; i++) {
                names.push(doc.layers[i].name);
                if (/^PRINT_ARTWORK(?:_|$)/.test(doc.layers[i].name)) {
                    var item = findPrint(doc, doc.layers[i].name);
                    instances.push({name:item.name, smartObject:true, bounds:bounds(item)});
                }
            }
            return encode({status:'PSD_INSPECTED', layers:names, instances:instances, smartObject:true, width:doc.width.as('px'), height:doc.height.as('px'), bounds:bounds(print)});
        }
        // Reject mismatched source canvases instead of silently moving/scaling artwork.
        var existingArt = openExisting(spec.artwork_path);
        var candidate = existingArt || app.open(file(spec.artwork_path));
        var candidateWidth = candidate.width.as('px'), candidateHeight = candidate.height.as('px');
        if (!existingArt) candidate.close(SaveOptions.DONOTSAVECHANGES);
        var layerNames = spec.print_layer_names || ['PRINT_ARTWORK'];
        if (!(layerNames instanceof Array) || !layerNames.length) throw new Error('print_layer_names must be a nonempty array');
        var seen = {}, targets = [], replacements = [];
        for (var n = 0; n < layerNames.length; n++) {
            if (typeof layerNames[n] !== 'string' || !layerNames[n] || seen[layerNames[n]]) throw new Error('Print layer names must be unique nonempty strings');
            seen[layerNames[n]] = true;
            targets.push(findPrint(doc, layerNames[n]));
        }
        for (var n = 0; n < targets.length; n++) {
            print = targets[n];
            app.activeDocument = doc; doc.activeLayer = print;
            executeAction(stringIDToTypeID('placedLayerEditContents'), undefined, DialogModes.NO);
            temp = app.activeDocument;
            var originalWidth = temp.width.as('px'), originalHeight = temp.height.as('px');
            temp.close(SaveOptions.DONOTSAVECHANGES); temp = null;
            app.activeDocument = doc; doc.activeLayer = print;
            if (candidateWidth !== originalWidth || candidateHeight !== originalHeight) {
                throw new Error('Normalize replacement artwork to the same source canvas dimensions first');
            }
            var before = bounds(print);
            var replace = new ActionDescriptor();
            replace.putPath(charIDToTypeID('null'), file(spec.artwork_path));
            executeAction(stringIDToTypeID('placedLayerReplaceContents'), replace, DialogModes.NO);
            var after = bounds(print);
            replacements.push({name:print.name, before:before, after:after});
        }
        doc.saveAs(newFile(spec.preview_path), new PNGSaveOptions(), true, Extension.LOWERCASE);
        return encode({status:'TRIAL_PREVIEW_EXPORTED', path:spec.preview_path, before:replacements[0].before, after:replacements[0].after, replacements:replacements, templateUnchanged:true});
    } finally {
        if (temp) temp.close(SaveOptions.DONOTSAVECHANGES);
        if (doc) doc.close(SaveOptions.DONOTSAVECHANGES);
        app.displayDialogs = oldDialogs;
        app.preferences.rulerUnits = oldUnits;
        if (previous) { try { app.activeDocument = previous; } catch (ignore) {} }
    }
}
'@
$jsx += "`nrunPodJob($payload, $modePayload);"
$psApp = $null
try {
    $psApp = New-Object -ComObject Photoshop.Application
    $psApp.DoJavaScript($jsx)
} finally {
    if ($null -ne $psApp) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($psApp) }
}
