# PDF-Only Acceptance Notes

This note records technical tradeoffs for PDF-only output.

## Where PDF-Only Works

- Quick review files.
- Printed or rasterized output where Illustrator layer editing is not needed.
- Inputs that do not contain usable Illustrator native payload data.

## Where PDF-Only Is Not Enough

- Workflows where users expect to keep editing layer structure in Illustrator.
- Converted `.ai` files that need the Illustrator bridge for hierarchy edits.
- Native `.ai` files where preserving `/NumBlock` data is the key requirement.

## Current v1 Guidance

- Use `apply` for fast PDF-stream rewriting when layer preservation is not
  important.
- Use `apply-jsx` for PDF-only or converted `.ai` files that still need
  Illustrator layer preservation.
- Use `apply-saas` for native Illustrator `.ai` files with `/NumBlock`.
- For PDF-only/converted section files, run `apply-jsx` first, then
  `arch-lw poche`.
