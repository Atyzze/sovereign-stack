# MANIFEST: what every file is, and what deleting it costs

This is the full inventory of "Sovereign Stack, Volume 1." Three things make up
the project: the **manuscript** (the single source of truth), the **machinery**
that turns it into a PDF, and the **records** that track it. Everything else is
either an input to those or a regenerable output of them. Rule of thumb: the
manuscript and the contents of `src/` and `assets/` are precious; everything
else can be rebuilt from them.

## The source of truth

- **`sovereign-stack-vol1.md`** -- the entire book in one markdown file: every
  part, the front and back matter, the appendix, and the raw-LaTeX blocks for
  the figures and the layer diagram. This is the one file you actually write in.
  Deleting it loses the book; nothing else can regenerate it. Treat it as the
  master copy.

## The machinery (in `src/`)

- **`src/`** -- the build machinery: the LaTeX preamble, the title page, the
  Python that drives the pipeline, and the test suites. Deleting the folder
  leaves the manuscript intact but unbuildable until it is restored.
- **`src/preamble.tex`** -- the LaTeX preamble: page geometry (A4 by default,
  A5 when `src/paper.tex` selects it), colours, fonts, the TikZ setup for the
  layer diagram, the `\ssfit` figure-fit helper, the footer ("page X / Y"), and
  the `\input` of the version tag. Pandoc injects it into every build via `-H`.
  Delete it and the book still compiles but loses all styling, the footer, and
  the version stamp, coming out as plain unstyled LaTeX.
- **`src/frontmatter.tex`** -- the title page and the material before the first
  chapter, inserted by pandoc's `--include-before-body`. Deleting it drops the
  cover and front matter; the body still builds.
- **`src/preprocess.py`** -- the markdown pre-pass that runs before pandoc and
  writes `temp/vol1_latex.md`, handling the conventions pandoc alone would
  mangle. Delete it and the build breaks at step 1.
- **`src/mkversion.py`** -- composes the version tag from `config.toml` (volume
  and version) and the folder name (iteration). Delete it and the build cannot
  stamp a version; the tag falls back to the placeholder baked into the
  preamble.
- **`src/make_bg.py`** -- regenerates the cover background wash
  (`assets/bg_titlepage.png`) with Pillow. It is a one-off generator, not part
  of the normal build. Deleting it only means that one image can no longer be
  regenerated; the existing PNG still works.
- **`src/version.tex`** -- the generated tag file (`\def\ssversion{...}`),
  rewritten by `build.sh` on every run. It is a build product, not a source.
  Deleting it is harmless; the next build recreates it.
- **`src/paper.tex`** -- the generated paper-selection file, written by
  `build.sh` for whichever edition it is building (the same generated-file
  pattern as `version.tex`). It sets the paper class, the matching `\geometry`
  call, the version-tag corner coordinates, and the `\sspaperclass` flag the
  preamble reads to fit the wide diagrams. A build product, not a source:
  deleting it is harmless, and if it is absent the preamble falls back to A4 so
  any `.tex` still compiles standalone.
- **`src/tests/`** -- the two test suites that hold the book to its rules.
  Deleting them removes the safety net; the book still builds, but nothing
  checks it.
- **`src/tests/test_build.py`** -- the build-invariant checks: no em or en
  dashes, an ASCII-only manuscript, a version tag present, and (after a build)
  zero overfull boxes, a page count within the ceiling, and that each edition's
  title page is exactly one page (the Contents heading lands on page 2, which
  catches a cover whose spacing has silently overflowed onto a second page).
- **`src/tests/test_review.py`** -- the content-review checks: acronyms expanded
  on first use, contiguous part and section numbering, well-formed Pointer
  boxes, referenced images present, the version and tracker agreeing with the
  folder name, the recovery archive present after a build, and this manifest
  naming every file.

## The records (project root)

- **`build.sh`** -- the build pipeline and entry point: it stamps the version,
  runs `src/preprocess.py`, `pandoc`, and `latexmk` (writing every byproduct into
  `temp/` and logging the whole run to `temp/build.log`), moves the finished PDF
  to `outputs/`, and refreshes the recovery archive. It takes a paper target,
  `./build.sh` (A4, the default), `./build.sh a5`, or `./build.sh both`, and one
  housekeeping subcommand, `./build.sh clean`, which lists `temp/` by size and
  then clears it. Deleting it does not touch the book, but you would have to run
  those steps by hand to rebuild.
- **`config.toml`** -- project configuration: title and slug, the volume and
  version numbers (the half of the tag the folder does not supply), the build
  settings mirrored for reference, and the targeted Python version. Delete it
  and `mkversion.py` falls back to defaults; the volume and version are lost.
- **`tracker.json`** -- the changelog: a `current` pointer (stamped
  automatically by the build) and a curated `history` of every iteration.
  Delete it and the recorded history is lost; the build still runs and recreates
  the `current` stub.
- **`README.md`** -- the short orientation: how to build, the prerequisites, and
  what each top-level item is. Reference only; deleting it costs nothing at
  build time.
- **`HANDOVER.md`** -- the continuity document, written to survive a context
  reset: the version mechanism, the single-source decision, the recovery bundle,
  the file layout, and the work queue. The most important doc to keep if a
  person or a model has to pick this up cold.
- **`MANIFEST.md`** -- this file. Deleting it only loses the inventory; a review
  check will flag its absence.

## The images (in `assets/`)

- **`assets/`** -- every image the book embeds. Deleting the folder makes the
  build fail at the figures. The twelve files are: `shot_main.png`,
  `shot_settings.png`, and `shot_session.png` (the companion app, the last in a
  live multi-entry session), `shot_update.png` (a pacman system update) and
  `shot_monitor.png` (the btop dashboard), `art_spectral.png`, `art_blob.png`,
  and `art_flow.png` (the appendix art), `lab_relational_a.png`,
  `lab_relational_b.png`, and `lab_scaling.png` (the expanded appendix science
  gallery: two multi-lens diagnostic dashboards and a finite-size-scaling study),
  and `bg_titlepage.png` (the cover wash, itself regenerable via `make_bg.py`).

## The working folders (regenerable; safe to delete)

- **`temp/`** -- transient build artifacts: the intermediate `vol1_latex.md`,
  the generated `.tex`, xelatex's `.aux`, `.log`, `.toc`, `.fls`,
  `.fdb_latexmk`, and `.xdv`, and `build.log` (the full record of the last run).
  `latexmk` writes these straight here via `-output-directory`, so the project
  root stays clean during a build, and nothing is deleted at the end: the traces
  are kept for review. Clearing them is one overseeable operation,
  `./build.sh clean`, which prints the folder by size first and then removes only
  it; the next build recreates it. (This is the folder once called `output/`,
  then `generated/`; `temp/` is the honest name, because its entire job is to be
  thrown away.)
- **`outputs/`** -- the final deliverables: `sovereign-stack-vol1.pdf` (the A4
  edition) and, when the A5 variant has been built, `sovereign-stack-vol1-a5.pdf`
  beside it. The plural name earns its keep here: the folder holds one edition or
  both, or none if a build has not run yet. Deleting a PDF is safe: the next
  build remakes it, or you recover it from the archive below.

## The recovery archive

- **`<version>.zip`** (for example `26.zip`) -- a self-healing snapshot of every
  source plus the built PDF(s), named after the version folder and refreshed by
  `build.sh` on every run (step 4 of the build). It excludes `temp/` and itself.
  This is the belt to the manuscript's braces: delete the loose PDF and recover
  it from here, or, if a rebuild ever fails on some future machine, extract both
  the PDF and the exact generating code from this one file. A review check
  confirms it is present after a build, so the bundle never ships without its own
  archive inside it. It is itself regenerable, but it is the thing that lets
  everything else be deleted safely.
