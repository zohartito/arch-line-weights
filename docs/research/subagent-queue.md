# Engineering Spike Queue

This public version keeps only technical spike prompts. Business research and
deleted planning-document references were removed.

## Completed Spikes

- Native Illustrator payload inspection: confirm `/AIPrivateData` streams can
  be decompressed, edited, recompressed, and reopened by Illustrator.
- Converted-file bridge path: confirm `apply-jsx` works on `[Converted]`
  drawings that do not expose native `/NumBlock`.
- Poché bridge path: confirm `arch-lw poche` can consume bridge output and
  write conservative black cut fills.

## Open Technical Spikes

1. Improve missing-`/NumBlock` diagnostics.
2. Add a fixture matrix for native `.ai`, converted `.ai`, PDF-only `.ai`,
   plain PDF, and legacy Rhino PostScript `.ai`.
3. Improve low-confidence poché reports so ambiguous layers are easy to fix by
   hand.
4. Validate Bluebeam output on Windows before making any Bluebeam claim.
5. Expand Make2D layer-name examples from real projects.
