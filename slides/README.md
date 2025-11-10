# MAS-FRO Defense Slides

## Overview
This directory contains the Beamer slide deck for the MAS-FRO thesis defense. The deck is authored in LaTeX (`masfro-defense.tex`) and targets a 45-minute presentation aligned with Q1-compliant research standards. The content mirrors the master `README.md` while adding live code listings, TikZ architecture diagrams, Agreement Form compliance analysis, and backup technical material for deep-dive questions.

## File Layout
- `masfro-defense.tex`: Primary Beamer source with 50 main frames and 12 appendix/backup frames.
- `README.md`: Compilation and structure guide (this file).

## Prerequisites
Compile with a TeX distribution that includes the following packages (TeX Live 2023+ or MikTeX with auto-install is recommended):

| Package      | Purpose                                |
|--------------|----------------------------------------|
| `beamer`     | Presentation framework (Singapore theme)|
| `tikz` (+ `arrows`, `positioning`, `shapes`, `calc`, `backgrounds`) | Diagrams and flowcharts |
| `listings`   | Syntax-highlighted code listings        |
| `amsmath`, `amssymb` | Mathematical notation and proofs |
| `booktabs`   | Professional tables                     |
| `graphicx`   | Image inclusion (space reserved for figures)|
| `xcolor`     | Custom color definitions                |
| `hyperref`   | In-slide hyperlinks                     |

No external images are required; all diagrams are drawn with TikZ placeholders that may be replaced with actual figures later.

## Compilation Options
The document is compatible with both PDFLaTeX and LuaLaTeX. Choose the toolchain that best fits your environment.

### One-Off Compilation
```powershell
pdflatex -interaction=nonstopmode -halt-on-error masfro-defense.tex
pdflatex -interaction=nonstopmode -halt-on-error masfro-defense.tex
```
Run twice to resolve references. On macOS/Linux replace `pdflatex` with the corresponding binary path as needed.

### LuaLaTeX
LuaLaTeX handles Unicode input more gracefully if Filipino or accented text is introduced:
```powershell
lualatex -interaction=nonstopmode masfro-defense.tex
lualatex -interaction=nonstopmode masfro-defense.tex
```

### latexmk (Automatic Rebuild)
```powershell
latexmk -pdf -interaction=nonstopmode masfro-defense.tex
```
Use `latexmk -c` to clean auxiliary files (`.aux`, `.log`, `.nav`, `.snm`, `.toc`).

### Troubleshooting
- **Missing TikZ libraries**: Install/update `pgf`/`tikz` packages in your TeX distribution.
- **Listings package warnings**: Ensure `listings` is present; MikTeX may prompt for installation.
- **Color or hyperref errors**: Confirm `xcolor` and `hyperref` are available; they ship with standard distributions.

## Deck Structure
The frames follow the approved defense narrative:

| Section | Frames | Highlights |
|---------|--------|------------|
| Title & Scope | 1 | Prototype disclaimer |
| Problem & Motivation | 2–7 | Ondoy context, Marikina constraints |
| Theory | 8–11 | MAS foundations, A*, risk formulation, data fusion |
| Related Work | 12–14 | Literature gap positioning |
| System Architecture | 15–24 | Agent topology, FIPA-ACL messages, risk-aware A* pseudocode |
| Agreement Form Compliance | 25–32 | Item-by-item status with gaps |
| Implementation Highlights | 33–37 | Data ingestion, GeoTIFF workflow, WebSocket design, dependencies |
| Performance | 38–40 | Preliminary metrics (n≈20), operational stats |
| Critical Assessment | 41–45 | Limitations, publication gaps, roadmap, lessons learned |
| Future Work & Conclusion | 46–49 | Qualified contributions, expansion roadmap, summary |
| Q&A | 50 | Prompt + note on backup slides |
| Backup Appendix | A1–A12 | Proof sketches, code listings, architecture deep dives |

Each major section begins with self-contained context so individual frames can stand alone during questioning.

## Editing Guidance
- Maintain the Singapore theme (`\usetheme{Singapore}`) for consistency and readability.
- Use TikZ for diagrams; keep placeholder drawings until real figures are available.
- Code snippets should use the existing `listings` configuration to preserve styling.
- Update both the main narrative and appendix when modifying features or Agreement Form status.

## Distribution
Compiled PDFs should be committed separately (e.g., `masfro-defense.pdf`) or exported through a release asset to keep version control clean. Always regenerate the PDF after significant code or data updates in the backend/frontend to ensure slides stay aligned with the implementation.

## Verification Checklist
- [ ] TeX compilation succeeds without warnings/errors.
- [ ] Agenda aligns with the master `README.md` and Agreement Form breakdown.
- [ ] Backup slides cover anticipated technical questions.
- [ ] Auxiliary files cleaned (`latexmk -c`) before committing, unless build artifacts are required.

The slides are presentation-ready once all boxes above are checked and the latest research gaps/metrics are incorporated.

