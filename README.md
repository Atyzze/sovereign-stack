# Sovereign Stack, Volume 1: Home Node

The complete, reproducible source for the book. For full project context,
the queue, the constraints, and the companion apps, read **HANDOVER.md** first.

## Quick build

Prerequisites: Python 3.14 (the project target; the scripts are standard-library
only and run on 3.11+), `pandoc`, TeX Live (`xelatex` + `latexmk`), and the fonts
TeX Gyre Pagella, TeX Gyre Heros, DejaVu Sans Mono.

```
./build.sh                       # markdown -> LaTeX -> PDF, both editions (the default)
./build.sh a4                    # A4 only
./build.sh a5                    # A5 only, same book, narrower page
python3 src/tests/test_build.py  # build invariants (dashes, ASCII, overfull, pages, cover is one page, both editions present)
python3 src/tests/test_review.py # content review (acronyms, version, structure)
```

Output: `outputs/sovereign-stack-vol1.pdf` (A4) and
`outputs/sovereign-stack-vol1-a5.pdf` (A5), both produced by a bare `./build.sh`.
The A4 and A5 editions are the same
manuscript built at two page sizes, not two copies of the tree: the paper is a
build parameter (`build.sh` writes `src/paper.tex`, the same generated-file
pattern as `src/version.tex`), so there is one source of truth and nothing to
drift. The A5 page count is naturally higher; that is expected. Every transient
artifact goes to `temp/` (and the whole run is logged to `temp/build.log`); the
traces are kept for review, and `./build.sh clean` lists `temp/` by size and then
clears it. Each build also refreshes a self-healing recovery snapshot named after
the version (e.g. `26.zip`).

Quick recompile without editing (skips pandoc), from the root:

```
latexmk -xelatex -output-directory=temp temp/sovereign-stack-vol1.tex
```

## Layout

- `sovereign-stack-vol1.md` -- the manuscript. **This is the source of truth.**
- `config.toml` -- project config (title, and the volume/version the tag uses).
- `tracker.json` -- the version changelog: a current pointer plus per-iteration history.
- `MANIFEST.md` -- a full inventory: every file, why it exists, what deleting it costs.
- `src/` -- build code: `preprocess.py`, `mkversion.py` (composes the version
  tag), `preamble.tex`, `frontmatter.tex`, `make_bg.py`, `version.tex` and
  `paper.tex` (both generated each build), and `tests/test_build.py` plus
  `tests/test_review.py`.
- `assets/` -- the twelve images used by the book (the three companion-app shots,
  the three appendix art pieces, three research-lab figures for the expanded
  appendix gallery, the cover wash, and the system-update and node-monitor
  screenshots).
- `outputs/` -- the final PDFs: `sovereign-stack-vol1.pdf` (A4) and
  `sovereign-stack-vol1-a5.pdf` (A5), both produced by default.
- `temp/` -- transient build artifacts (the intermediate markdown, the generated
  `.tex`, xelatex's byproducts, and `build.log`, the full record of the last
  run); kept for review and cleared with `./build.sh clean`.
- `<version>.zip` (e.g. `26.zip`) -- a self-healing snapshot of every source plus
  the built PDF(s), refreshed on each build; delete the loose PDF and recover it here.

## Which files do you actually need?

- The **`.md`** is the source; keep and edit it.
- The **`.tex`** (now under `temp/`) is regenerated from the `.md` on each build.
- The **`.pdf`** is the only file a reader needs. To share the book, share the
  PDF and nothing else.

## Versioning

The tag in the top-right corner of every page (e.g. `v1v1i23`) is **composed
automatically**: `src/mkversion.py` reads the volume and version from
`config.toml` and takes the iteration from the name of the folder the project
sits in (`22`, `23`, ...). On each build, `build.sh` writes the result into
`src/version.tex` (which the preamble reads) and stamps it into `tracker.json`.
So the tag can never silently fall out of step: rename the folder, rebuild, and
the number follows; `test_review.py` enforces that the tag, the folder name, and
the tracker all agree.

The tag reads volume / version / iteration: advance the iteration by naming the
folder, and move the version only when you share or publish, by editing the
`[version]` block in `config.toml`. Compiling the `.tex` directly without
`build.sh` falls back to the placeholder `v1v1i00` in `src/preamble.tex`.

`tracker.json` is the changelog: a `current` pointer (kept in sync by the build)
and a `history` of what each iteration changed, so the project carries its own
record forward across edits and context resets.
