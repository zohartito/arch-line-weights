# Designer Console Prototype

The designer console is a local browser UI around the existing `arch-lw`
engine. It is meant for a designer sitting at a workstation, not for public
posting clearance, app-store packaging, or a hosted service.

## Open The Console

From a source checkout with the console extra installed:

```bash
python -m pip install -e ".[console]"
arch-lw designer-console
```

The command starts a local server and opens:

```text
http://127.0.0.1:8765
```

If you do not want it to open a browser automatically:

```bash
arch-lw designer-console --no-browser
```

Use `--storage-root /path/to/local/runs` when you want console uploads,
outputs, and raw local reports to land in a specific local folder.

## What It Can Do

- Choose or drag a Rhino / Illustrator / PDF export.
- Choose a workflow type: Section, Plan, Detail, or Synthetic proof / demo.
- Run five explicit actions: Inspect File, Run Layout, Apply Line Weights,
  Generate Poché, and Export Proof Packet.
- Show each stage as `not run`, `running`, `passed`, `needs review`, `failed`,
  or `no-go`.
- Show a readable report with what changed, what skipped, what failed, why,
  and the next step.
- Keep raw local reports in the console run folder while the proof packet only
  contains public-safe summaries.

The pipeline uses the existing engine paths:

- `inspect_file` for inspection.
- `layout_via_jsx` for sheet/layout normalization.
- `apply_via_jsx` plus `validate_apply_jsx_result` for hierarchy output.
- `apply_poche` plus structured poché reports for cut-fill review.

## What It Cannot Claim

These guardrails are shown in the console and apply to every proof packet:

- Posting/public proof is NO-GO unless W5/W7 explicitly accepts it.
- Synthetic proof does not close #30.
- Private USC regression stays private.

The console does not close #29 or #30. It does not mean public launch is
ready. It does not mean App Store, Microsoft Store, or Windows desktop support
is ready. Windows remains future work until it is packaged and tested on
Windows.

## Proof Packets

Export Proof Packet creates a local `.zip` with:

- `public-summary.json`
- `designer-console-report.txt`
- `README-NOT-PUBLIC-CLEARANCE.txt`

The packet deliberately excludes raw drawings and raw local reports. If a
public summary would include a local/private path, the proof-packet stage is
marked `no-go` and the packet is not exported.

## Desktop Roadmap

1. Local web prototype: keep improving the one-command console around the
   existing Python engine and report contracts.
2. Signed Mac desktop beta: package the same local console/engine with signing,
   notarization, update notes, and a tested local-file permission story.
3. Windows desktop beta: package and test the workflow on Windows before making
   any Windows support claim.
4. Rhino plugin / Illustrator panel: later, wrap the same stages inside native
   design-tool surfaces once the local console proves the workflow.
