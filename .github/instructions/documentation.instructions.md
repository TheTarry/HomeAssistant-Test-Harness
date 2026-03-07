---
applyTo: "documentation/**/*.md"
---

# Documentation Instructions

## Style

- **Line length**: ≤ 200 characters per line.
- Keep one blank line between each top-level section heading and its content.
- Use fenced code blocks with an explicit language tag (e.g., `python`, `yaml`, `bash`).
- Use relative links between documentation files (e.g., `[Fixtures](fixtures.md)`).

## Structure

Each topic lives in its own file under `documentation/`. Current files:

| File | Content |
|------|---------|
| `installation.md` | Installation instructions |
| `usage.md` | How to write tests, auto-discovery, persistent entities |
| `fixtures.md` | Complete fixture API reference |
| `troubleshooting.md` | Common issues and debugging |
| `development.md` | Development setup, release process |

New documentation files must be linked from `README.md`.

## Adding Documentation

When adding a new `.md` file to `documentation/`:

1. Follow the structure and heading style of existing files.
2. Add a link to the new file from `README.md`.
3. Cross-link from related existing files where useful.
4. Keep the file focused on one topic — split large topics rather than growing a single file.
