# MANIFEST

Every file in the press, what it is, and what is lost if it goes missing. The
review suite (`src/tests/test_review.py`) checks that this list names every
source file and folder, so it cannot quietly fall out of date.

The top level holds exactly three folders, always the same three: **src** (all
source code, including the `books/` manuscripts), **temp** (regenerable build
artifacts), and **output** (the finished PDFs). Everything else at the top is a
file you run or read.

## Top-level files

- **build.py** the one orchestrator. Discovers books, fingerprints their inputs,
  rebuilds only what changed, moves finished PDFs to `output/`, and refreshes the
  recovery snapshot. Losing it loses the whole build; everything else is data.
- **press.toml** workshop-wide configuration: the build `[order]`, the shared
  `[defaults]` every book inherits (engine, fonts, paper, page ceiling), and the
  `[crossmap]` note pairing the Primer with the Atlas.
- **README.md** how to build, the layout, how the incremental build works, how to
  add a book, and how the workbook format is authored.
- **MANIFEST.md** this file.
- **.gitignore** keeps `temp/`, the recovery snapshot, and caches out of version
  control.

## src/  (all source code; nothing here is regenerable)

### src/shared/  (the machinery every book depends on)

- **src/shared/preamble.tex** the series styling, carried from the original book
  and generalized: the colours, fonts, code listings, tables, TikZ tooling, the
  running header and version tag, and the workbook tooling the Primer uses (the
  `\ssbox` checkbox, the three-track `tracks` box with `\tlinux`/`\tmac`/`\twin`,
  the `promptbox` panel, the `doit` task list, the `\seeline` success line, the `\concept`
  per-page heading, and the all-in-one `\workpage`). A change here re-fingerprints
  and rebuilds every book.
- **src/shared/preprocess.py** the Markdown clean-up step, generic and driven by
  each book's `[preprocess]` settings. Also holds the workbook block syntax
  (`### N. Title` plus `::: tracks`, `::: prompt`, `::: doit`, `::: see`) that the Primer is
  authored in, turned on by `workbook = true`.
- **src/shared/mkversion.py** composes a book's version tag,
  `v{volume}v{version}i{iteration}`, and its running-header label.
- **src/shared/render_svgs.py** renders each book's hand-authored figures:
  every `assets/*.svg` (the editable source) becomes a `.pdf` under
  `temp/<slug>/figures/`, where the build embeds it. Freshness is by content
  hash, so editing an .svg always re-renders and nothing else ever does. The
  build runs it first; it is also runnable standalone. Needs `cairosvg`
  (`pip install cairosvg`) whenever a book has .svg figures.
- **src/shared/make_bg.py** regenerates the cover wash image from its source art;
  run only when the cover art changes.
- **src/shared/assets/** images shared across books: **bg_titlepage.png** (the
  cover wash every title page uses) and **art_blob.png** (the source it derives
  from).

### src/tests/

- **src/tests/_common.py** the discovery and configuration shared by both suites:
  locating the tree, loading `press.toml` and each `book.toml`, composing the
  expected version tag, and listing a book's files.
- **src/tests/test_build.py** the build invariants, run once per book: no em/en
  dashes anywhere, an ASCII-only manuscript, a wired version tag that matches the
  book's config, and (after a build) no overfull boxes, a page count within the
  ceiling, a one-page title page, and a real PDF. Each translated edition is
  checked too (no dashes or smart quotes, an ASCII-plus-diacritics charset, and
  its own one-page title page). Plus the press-wide recovery-archive check.
- **src/tests/test_review.py** the content review, run once per book: the
  universal checks (ASCII and dashes, no placeholder markers, no stray
  whitespace, balanced fences, no doubled words, referenced images present, no
  dead-weight assets, a real PDF) and the opt-in structural checks a book turns on
  in its `[review]` table. Each translated edition is reviewed in its own language
  (charset, placeholders, whitespace, fences, images, and structural Part /
  section / Pointer checks using that edition's own words). Plus the press-wide
  MANIFEST-completeness and recovery checks.

### src/books/  (one folder per book; any folder with a book.toml is a book)

#### src/books/atlas-home-node/  (The Atlas, Volume 1: Home Node)

- **book.toml** this book's settings: `[project]` (title, header labels),
  `[version]` (the tag; Volume 1), `[preprocess]`, `[build]`, `[review]` (Part
  numbering, section numbering, Pointer boxes, and acronym expansion with its
  documented exception lists), and one `[[language]]` block per translated
  edition (the Dutch edition and its structural settings).
- **manuscript.md** the source of truth for the Atlas, in English. **Keep and
  edit this.**
- **manuscript-NL.md** the Dutch edition of the Atlas, a translation of
  manuscript.md living beside it. build.py builds it into
  `output/atlas-home-node-NL.pdf` alongside the English PDF; it shares the
  English edition's version tag. **Keep and edit this.**
- **frontmatter.tex** the Atlas title page and Contents (English).
- **frontmatter-NL.tex** the Dutch title page and Contents (Omslag / Inhoud),
  used by the Dutch edition; same elastic layout as frontmatter.tex.
- **assets/** images embedded by the Atlas only: **shot_main.png** (the companion
  app's main view) and **shot_update.png** (a system update in progress), plus the
  figure set: each **fig_*.svg** is a hand-authored diagram source, the only form
  a figure exists in under src/. The build renders each to a .pdf byproduct in
  `temp/<slug>/figures/` (also via `python3 src/shared/render_svgs.py`). The
  figures are shared by both editions.

#### src/books/primer-first-contact/  (The Primer: First Contact)

- **book.toml** the Primer's settings. Same shape as the Atlas's, plus
  `workbook = true` in `[preprocess]`, which turns the concept pages into the
  one-concept-per-page workbook layout.
- **manuscript.md** the source of truth for the Primer: one hundred concepts,
  each authored as a workbook page (explanation, the boxes it needs, a `::: doit`
  checklist, and a `::: see` success line). **Keep and edit this.**
- **frontmatter.tex** the Primer title page and Contents.
- **assets/** images embedded by this book (currently empty; the book builds
  without book-specific images, and per-concept artwork is a later production step).
- **sovereign-stack-first-contact.md** an earlier long-form draft of this book,
  kept beside the source for reference; not consumed by the build.

## Generated, not source (kept out of version control)

- **temp/<slug>/** per-book working files: the cleaned Markdown, the generated
  `.tex` and `version.tex`, xelatex's byproducts, and `build.log`. Disposable;
  clear with `python3 build.py clean`.
- **output/<slug>.pdf** the finished books, one per book, plus one
  `output/<slug>-<CODE>.pdf` per translated edition (e.g.
  `atlas-home-node-NL.pdf`). The only files a reader needs.
- **output/.build-state.json** the hash cache that drives the incremental build.
  Delete it to force a full rebuild on the next run.
- **recovery.zip** a self-healing snapshot of every source file plus the built
  PDFs, refreshed on every build run.
