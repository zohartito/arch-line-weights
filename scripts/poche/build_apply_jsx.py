#!/usr/bin/env python3
"""Build a JSX file with the polygons baked in and the apply logic."""
import json

with open("/tmp/poche_polygons.json") as f:
    polygons = json.load(f)

TARGET = "/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/DRAWING 4 SECTION [Converted] HIERARCHY.ai"
OUTPUT = "/Users/zohartito/SynologyDrive/USC/Spring 2026/ARCH 202B/DRAWING 4 SECTION [Converted] POCHE.ai"

def js_str(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'

def js_polys(polys):
    parts = []
    for poly in polys:
        coord_strs = [f"[{x:g},{y:g}]" for x, y in poly]
        parts.append("[" + ",".join(coord_strs) + "]")
    return "[" + ",".join(parts) + "]"

baked_lines = ["var POLYGONS = {"]
for i, (layer_name, polys) in enumerate(polygons.items()):
    sep = "," if i < len(polygons) - 1 else ""
    baked_lines.append(f"  {js_str(layer_name)}: {js_polys(polys)}{sep}")
baked_lines.append("};")
baked = "\n".join(baked_lines)

jsx = f"""#target illustrator

(function () {{
    var TARGET   = {js_str(TARGET)};
    var OUTPUT   = {js_str(OUTPUT)};
    var REPORT   = "/tmp/poche_apply_report.txt";

    try {{ app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; }} catch (e) {{}}

    function writeFile(p, s) {{ var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }}

{baked}

    var doc = null;
    for (var di = 0; di < app.documents.length; di++) {{
        try {{ if (app.documents[di].fullName.fsName === TARGET) {{ doc = app.documents[di]; break; }} }} catch (e) {{}}
    }}
    if (!doc) {{ writeFile(REPORT, "ERROR: target doc not open: " + TARGET); return; }}
    if (app.activeDocument !== doc) app.activeDocument = doc;

    var BLACK = new RGBColor(); BLACK.red = 0; BLACK.green = 0; BLACK.blue = 0;

    // Build layer name -> Layer object lookup
    var layerByName = {{}};
    function visit(layer, prefix) {{
        var fullName = prefix ? (prefix + "::" + layer.name) : layer.name;
        layerByName[fullName] = layer;
        for (var s = 0; s < layer.layers.length; s++) visit(layer.layers[s], fullName);
    }}
    for (var L = 0; L < doc.layers.length; L++) visit(doc.layers[L], "");

    var totalCreated = 0;
    var perLayer = [];
    for (var name in POLYGONS) {{
        var lyr = layerByName[name];
        if (!lyr) {{ perLayer.push(name + " :: NO MATCHING LAYER"); continue; }}
        var polys = POLYGONS[name];
        var created = 0;
        for (var pi = 0; pi < polys.length; pi++) {{
            try {{
                var coords = polys[pi];
                if (coords.length < 3) continue;
                // Drop trailing duplicate (closing) coord — Illustrator closes on its own
                var pts = coords;
                if (pts.length > 2 && pts[0][0] === pts[pts.length-1][0] && pts[0][1] === pts[pts.length-1][1]) {{
                    pts = pts.slice(0, pts.length - 1);
                }}
                var newPath = lyr.pathItems.add();
                newPath.setEntirePath(pts);
                newPath.closed = true;
                newPath.filled = true;
                newPath.fillColor = BLACK;
                newPath.stroked = false;
                created++;
            }} catch (e) {{ /* skip bad poly */ }}
        }}
        totalCreated += created;
        perLayer.push(name.split("::").pop() + "  +" + created);
    }}

    var saveFile = new File(OUTPUT);
    var saveOpts = new IllustratorSaveOptions();
    saveOpts.pdfCompatible = true;
    doc.saveAs(saveFile, saveOpts);

    var rep = "POCHE-SHAPELY DONE\\nnew filled polys created: " + totalCreated + "\\nper layer:\\n";
    for (var i = 0; i < perLayer.length; i++) rep += "  " + perLayer[i] + "\\n";
    rep += "saved as: " + OUTPUT + "\\n";
    writeFile(REPORT, rep);
}})();
"""

OUT = "/tmp/apply_poche_shapely.jsx"
with open(OUT, "w") as f:
    f.write(jsx)
print(f"wrote {OUT}, {len(jsx):,} bytes")
