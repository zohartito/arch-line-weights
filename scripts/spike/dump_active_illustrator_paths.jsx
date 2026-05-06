#target illustrator

(function () {
    var outPath = "/tmp/arch_lw_active_paths.json";
    var doc = app.activeDocument;
    var f = new File(outPath);
    f.encoding = "UTF-8";
    f.open("w");

    function esc(s) {
        return String(s).replace(/\\/g, "\\\\").replace(/"/g, '\\"');
    }

    function colorObj(c) {
        try {
            if (!c) return "null";
            if (c.typename === "RGBColor") return "[" + c.red + "," + c.green + "," + c.blue + "]";
            if (c.typename === "CMYKColor") {
                return "[" + c.cyan + "," + c.magenta + "," + c.yellow + "," + c.black + "]";
            }
            if (c.typename === "GrayColor") return "[" + c.gray + "]";
        } catch (e) {}
        return "null";
    }

    f.write('{"doc":"' + esc(doc.name) + '","paths":[');
    for (var i = 0; i < doc.pathItems.length; i++) {
        var p = doc.pathItems[i];
        if (i > 0) f.write(",");
        var pts = [];
        for (var j = 0; j < p.pathPoints.length; j++) {
            var a = p.pathPoints[j].anchor;
            pts.push("[" + a[0] + "," + a[1] + "]");
        }
        f.write(
            '{"i":' + i
                + ',"layer":"' + esc(p.layer.name) + '"'
                + ',"closed":' + p.closed
                + ',"stroked":' + p.stroked
                + ',"filled":' + p.filled
                + ',"strokeWidth":' + p.strokeWidth
                + ',"strokeColor":' + colorObj(p.strokeColor)
                + ',"points":[' + pts.join(",") + "]}"
        );
    }
    f.write("]}");
    f.close();
})();
