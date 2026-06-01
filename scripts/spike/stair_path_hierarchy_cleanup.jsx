#target illustrator

(function () {
    var doc = app.activeDocument;
    var sourcePath = doc.fullName.fsName;
    var outPath = sourcePath.replace(/v[0-9]+-stair(?:-path-clean)?\.ai$/i, "sample-stair-path-clean.ai");
    if (outPath === sourcePath) outPath = sourcePath.replace(/\.ai$/i, " path-clean.ai");

    var reportPath = "/tmp/arch_lw_stair_cleanup_report.txt";
    var report = new File(reportPath);
    report.encoding = "UTF-8";
    report.open("w");

    function dist(a, b) {
        var dx = a[0] - b[0];
        var dy = a[1] - b[1];
        return Math.sqrt(dx * dx + dy * dy);
    }

    function pathLength(p) {
        var len = 0;
        for (var i = 1; i < p.pathPoints.length; i++) {
            len += dist(p.pathPoints[i - 1].anchor, p.pathPoints[i].anchor);
        }
        if (p.closed && p.pathPoints.length > 1) {
            len += dist(p.pathPoints[p.pathPoints.length - 1].anchor, p.pathPoints[0].anchor);
        }
        return len;
    }

    function blackColor() {
        try {
            if (doc.documentColorSpace === DocumentColorSpace.RGB) {
                var rgb = new RGBColor();
                rgb.red = 0;
                rgb.green = 0;
                rgb.blue = 0;
                return rgb;
            }
        } catch (e) {}
        var cmyk = new CMYKColor();
        cmyk.cyan = 0;
        cmyk.magenta = 0;
        cmyk.yellow = 0;
        cmyk.black = 100;
        return cmyk;
    }

    var black = blackColor();
    var deleted = 0;
    var light = 0;
    var medium = 0;
    var heavy = 0;

    for (var i = doc.pathItems.length - 1; i >= 0; i--) {
        var p = doc.pathItems[i];
        if (!p.stroked) continue;
        var len = pathLength(p);

        // Rhino Make2D often emits dust-length line fragments at joins.
        // They print as dark burrs and do not carry architectural information.
        if (len < 1.0) {
            p.remove();
            deleted++;
            continue;
        }

        p.strokeColor = black;
        if (len < 28.0) {
            p.strokeWidth = 0.18;
            light++;
        } else if (len < 85.0) {
            p.strokeWidth = 0.25;
            medium++;
        } else {
            p.strokeWidth = 0.5;
            heavy++;
        }
    }

    var opts = new IllustratorSaveOptions();
    opts.pdfCompatible = true;
    doc.saveAs(new File(outPath), opts);

    report.write(
        "source: " + sourcePath + "\n"
            + "saved as: " + outPath + "\n"
            + "deleted <1pt debris: " + deleted + "\n"
            + "0.18pt short/detail paths: " + light + "\n"
            + "0.25pt medium paths: " + medium + "\n"
            + "0.5pt long/profile paths: " + heavy + "\n"
    );
    report.close();
})();
