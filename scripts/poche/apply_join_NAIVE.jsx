#target illustrator

(function () {
    var TARGET   = "<private-arch-202b-root>/DRAWING 4 SECTION [Converted] HIERARCHY.ai";
    var OUTPUT   = "<private-arch-202b-root>/DRAWING 4 SECTION [Converted] POCHE.ai";
    var PROGRESS = "/tmp/poche_progress.txt";
    var REPORT   = "/tmp/poche_report.txt";

    try { app.userInteractionLevel = UserInteractionLevel.DONTDISPLAYALERTS; } catch (e) {}

    function writeFile(p, s) { var f = new File(p); f.encoding = "UTF-8"; f.open("w"); f.write(s); f.close(); }
    function progress(s) { writeFile(PROGRESS, new Date().toString() + "\n" + s); }

    function shouldPoche(name) {
        var n = String(name).toUpperCase();
        if (n.indexOf("CLIPPINGPLANEINTERSECTIONS") === -1) return false;
        if (n.indexOf("GLASS") !== -1 || n.indexOf("IGU") !== -1) return false;
        return true;
    }

    var savedUndo = null;
    var undoKeys = ["maximumUndoDepth", "Undo/UndoCount", "Undo/MaximumUndoCount"];

    try {
        progress("starting");

        var doc = null;
        for (var di = 0; di < app.documents.length; di++) {
            try { if (app.documents[di].fullName.fsName === TARGET) { doc = app.documents[di]; break; } } catch (e) {}
        }
        if (!doc) { writeFile(REPORT, "ERROR: target doc not open: " + TARGET); return; }
        if (app.activeDocument !== doc) app.activeDocument = doc;

        for (var uk = 0; uk < undoKeys.length; uk++) {
            try {
                savedUndo = app.preferences.getIntegerPreference(undoKeys[uk]);
                app.preferences.setIntegerPreference(undoKeys[uk], 1);
                break;
            } catch (e) {}
        }

        var BLACK = new RGBColor(); BLACK.red = 0; BLACK.green = 0; BLACK.blue = 0;

        // Walk leaf layers
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
        progress("found " + leaves.length + " leaf layers");

        var perLayer = {};
        var grandTotal = 0;
        var t0 = (new Date()).getTime();

        for (var i = 0; i < leaves.length; i++) {
            var meta = leaves[i];
            if (!shouldPoche(meta.fullName)) continue;

            var layer = meta.layer;
            var beforeCount = layer.pathItems.length;

            // Unlock every other layer to be safe and lock all others so Join only operates on this one
            // Actually simpler: deselect all, then select only this layer's contents.
            try { doc.selection = null; } catch (e) {}
            layer.hasSelectedArtwork = true;
            var selBefore = doc.selection.length;

            // Repeated Join — Illustrator's join chains pairs of coincident endpoints.
            // For N micro-segments forming one closed loop, ~log(N) join calls should suffice
            // because each join roughly halves the number of paths if endpoints are well-paired.
            var joinIterations = 0;
            for (var j = 0; j < 25; j++) {
                var lenBefore = doc.selection ? doc.selection.length : 0;
                try { app.executeMenuCommand("join"); } catch (e) { break; }
                joinIterations++;
                var lenAfter = doc.selection ? doc.selection.length : 0;
                if (lenAfter >= lenBefore || lenAfter === 0) break;
            }

            // Now fill every path in the layer black (closed or not)
            var afterCount = layer.pathItems.length;
            var filled = 0, closed = 0;
            for (var p = 0; p < layer.pathItems.length; p++) {
                try {
                    var pi = layer.pathItems[p];
                    if (!pi.closed) { pi.closed = true; }
                    else { closed++; }
                    pi.filled = true;
                    pi.fillColor = BLACK;
                    filled++;
                } catch (e) {}
            }

            try { doc.selection = null; } catch (e) {}

            perLayer[meta.fullName] = {
                paths_before: beforeCount,
                paths_after: afterCount,
                join_iterations: joinIterations,
                closed_after_join: closed,
                filled: filled,
            };
            grandTotal += filled;
            var elapsed = ((new Date()).getTime() - t0) / 1000;
            progress("layer " + (i+1) + "/" + leaves.length
                + "  paths " + beforeCount + "->" + afterCount
                + "  join_iters=" + joinIterations
                + "  filled=" + filled
                + "  elapsed=" + elapsed.toFixed(1) + "s");
        }

        var totalElapsed = ((new Date()).getTime() - t0) / 1000;
        progress("done in " + totalElapsed.toFixed(1) + "s");

        try { app.executeMenuCommand("preview"); } catch (e) {}
        if (savedUndo !== null) {
            for (var uk2 = 0; uk2 < undoKeys.length; uk2++) {
                try { app.preferences.setIntegerPreference(undoKeys[uk2], savedUndo); break; } catch (e) {}
            }
        }

        var saveFile = new File(OUTPUT);
        var saveOpts = new IllustratorSaveOptions();
        saveOpts.pdfCompatible = true;
        progress("saveAs " + OUTPUT);
        doc.saveAs(saveFile, saveOpts);

        var rep = "POCHE-JOIN DONE\nelapsed: " + totalElapsed.toFixed(1) + "s\ntotal filled: " + grandTotal + "\nper layer:\n";
        for (var k in perLayer) {
            var pl = perLayer[k];
            rep += "  " + k
                + "  before=" + pl.paths_before
                + "  after=" + pl.paths_after
                + "  joins=" + pl.join_iterations
                + "  closed=" + pl.closed_after_join
                + "  filled=" + pl.filled + "\n";
        }
        rep += "saved as: " + OUTPUT + "\n";
        writeFile(REPORT, rep);
        progress("complete");
    } catch (e) {
        try { app.executeMenuCommand("preview"); } catch (e2) {}
        writeFile(REPORT, "EXCEPTION: " + e.toString() + (e.line ? " line " + e.line : ""));
        progress("exception: " + e.toString());
    }
})();
