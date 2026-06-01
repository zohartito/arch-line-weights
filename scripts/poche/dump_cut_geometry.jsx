#target illustrator

(function () {
    var TARGET = "<private-arch-202b-root>/DRAWING 4 SECTION [Converted] HIERARCHY.ai";
    var OUT = "/tmp/cut_geometry.json";
    var REPORT = "/tmp/cut_dump_report.txt";

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }

    function shouldDump(name) {
        var n = String(name).toUpperCase();
        if (n.indexOf("CLIPPINGPLANEINTERSECTIONS") === -1) return false;
        if (n.indexOf("GLASS") !== -1 || n.indexOf("IGU") !== -1) return false;
        return true;
    }

    function jsonEscape(s) {
        s = String(s); var out = '"';
        for (var i = 0; i < s.length; i++) {
            var c = s.charAt(i), code = s.charCodeAt(i);
            if (c === '\\') out += '\\\\';
            else if (c === '"') out += '\\"';
            else if (c === '\n') out += '\\n';
            else if (c === '\r') out += '\\r';
            else if (code < 0x20) out += '\\u' + ('0000' + code.toString(16)).slice(-4);
            else out += c;
        }
        return out + '"';
    }

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {
        try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
    }
    if (!doc) { writeFile(REPORT, "ERROR: not open"); return; }

    var leaves = [];
    function visit(layer, prefix) {
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        if (layer.layers.length > 0) {
            for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
        } else {
            leaves.push({layer: layer, fullName: fullName});
        }
    }
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    // For each cut layer, dump every path's anchor points
    var json = "{";
    var first = true;
    var totalPaths = 0;
    var totalAnchors = 0;
    for (var i = 0; i < leaves.length; i++) {
        var meta = leaves[i];
        if (!shouldDump(meta.fullName)) continue;

        if (!first) json += ",";
        first = false;
        json += "\n  " + jsonEscape(meta.fullName) + ": [";

        var paths = meta.layer.pathItems;
        for (var p = 0; p < paths.length; p++) {
            var pi = paths[p];
            var pts = pi.pathPoints;
            var pathArr = "[";
            for (var pp = 0; pp < pts.length; pp++) {
                if (pp > 0) pathArr += ",";
                var a = pts[pp].anchor;  // [x, y] in pt
                pathArr += "[" + a[0].toFixed(4) + "," + a[1].toFixed(4) + "]";
                totalAnchors++;
            }
            pathArr += "]";
            if (p > 0) json += ",";
            json += "\n    " + pathArr;
            totalPaths++;
        }
        json += "\n  ]";
    }
    json += "\n}";

    writeFile(OUT, json);
    writeFile(REPORT, "DUMP DONE\nlayers: " + leaves.length + "\npaths: " + totalPaths + "\nanchors: " + totalAnchors + "\nfile: " + OUT);
})();
