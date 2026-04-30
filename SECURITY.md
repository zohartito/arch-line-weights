# Security policy

## Supported versions

Pre-1.0, only the latest minor version receives fixes. Once 1.0 ships,
the latest two minor versions will be supported.

| Version | Supported |
|---|---|
| 0.5.x | ✅ |
| 0.4.x | ⚠️  fixes for severe bugs only |
| < 0.4 | ❌ |

## Reporting a vulnerability

**Do not open a public GitHub issue for security reports.**

Email security reports to **zohartito96@gmail.com** with subject
`arch-line-weights security`. You'll get an acknowledgement within 5
business days.

For the kinds of bugs likely to matter:
- malicious `.ai`/`.pdf` input that crashes / hangs / OOMs the tool
- malicious `mapping.json` / `overrides.json` that triggers code execution
  (we use `json.loads`, not `eval`, so this should be impossible — but
  report if you find a path)
- escape-the-sandbox bugs in the JSX runner (we shell out to osascript;
  any way to inject arbitrary code through the file path or content is
  in scope)
