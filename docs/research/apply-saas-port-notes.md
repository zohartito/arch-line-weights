# `apply-saas` Port Notes

`apply-saas` is the historical CLI command name for the local native
Illustrator payload rewrite path. The name does not indicate a hosted product.

## What The Port Does

- Opens a native Illustrator `.ai` file that contains `/NumBlock` data.
- Decompresses the Illustrator private payload.
- Rewrites stroke-weight operators for the selected hierarchy.
- Recompresses the payload and writes a new `.ai` file.

## Poché Constraint

`apply-saas --poche` needs native `/NumBlock`. If a file is PDF-only or
converted, use:

```bash
arch-lw apply-jsx path/to/file.ai
arch-lw poche path/to/file-HIERARCHY.ai
```

## Known Input Classes

- Native Illustrator `.ai`: use `apply-saas`.
- Converted `.ai`: use `apply-jsx`, then `arch-lw poche` if poché is needed.
- Plain PDF: use `apply` for stroke weights.
- Legacy Rhino PostScript `.ai`: open and re-save/convert before current v1
  processing.
