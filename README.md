# Sovereign Press

A small workshop for building a whole shelf of books from plain text. Each book
is a folder of Markdown plus a little configuration; one command turns every
book into a finished PDF, and it only rebuilds the ones that actually changed.

The entire project lives at **https://github.com/Atyzze/sovereign-stack**: source,
build system, and manuscripts together. Clone it and you can rebuild every book
here yourself, or fork it and grow your own shelf. The books are open the same
way the stack they describe is: readable, buildable, and yours to change.

It currently holds the first two volumes of the series:

- **The Atlas, Volume 1: Home Node** (`src/books/atlas-home-node/`) the dense, complete
  map: bare hardware to a private AI, at speed, for a reader who can already walk a map
  alone. "The Atlas" is the name of the main, multi-volume series; Home Node is its
  first volume.
- **The Primer: First Contact** (`src/books/primer-first-contact/`) Volume 0, the
  on-ramp and a true workbook: the hundred small ideas the Atlas quietly assumes, one
  page each, every concept tried on all three kinds of machine and ticked off as you go,
  ending with the reader's own AI set up and the Atlas handed to it.

## Quick build

Prerequisites: Python 3.11+ (the build itself is standard-library only;
`pip install -r requirements.txt` adds `cairosvg` for figure rendering and
`Pillow` for the one-off cover regenerator), `pandoc`,
TeX Live (`xelatex` + `latexmk` + `lmodern`), and the fonts TeX Gyre Pagella,
TeX Gyre Heros, and DejaVu Sans Mono. On a full TeX Live install everything is
already present; on a minimal one, `lmodern` is the package most likely missing
(`pandoc`'s default LaTeX template loads it), so install it if a build stops with
a "lmodern.sty not found" error.

```
python3 build.py                 # build every enabled book that changed
python3 build.py atlas-home-node # build just one (or several) by name
python3 build.py --force         # rebuild everything, ignoring the cache
python3 build.py list            # show every book, its tag, and whether it is current
python3 build.py clean           # remove the temp/ working directory
python3 build.py bump <slug>     # increment a book's iteration number
python3 build.py snapshot        # refresh the recovery.zip without building

python3 src/tests/test_build.py      # build invariants, per book (dashes, ASCII, pages, ...)
python3 src/tests/test_review.py     # content review, per book (structure, acronyms, ...)
```

Finished PDFs land in `output/`, one per book (e.g. `output/atlas-home-node.pdf`).
Every transient artifact stays under `temp/<slug>/` (including `build.log`, the
full record of that book's last run). Each build run also refreshes
`recovery.zip`, a self-healing snapshot of every source file plus the built PDFs.

## How the incremental build works

This is the heart of the workshop. Building a book is slow, and most runs only
touch one of them, so `build.py` keeps a fingerprint of every book's inputs and
skips any book whose fingerprint has not moved.

The fingerprint (a SHA-256 hash) is taken over two things: the book's own files
(its `manuscript.md`, `book.toml`, `frontmatter.tex`, and everything in its
`assets/`), and the shared machinery every book depends on (the preamble, the
preprocess and version scripts, `press.toml`, and the shared assets). After each
successful build the fingerprint is stored in `output/.build-state.json`. On the
next run a book is rebuilt only if its fingerprint changed, or its PDF is missing
or implausibly small.

The practical consequences are worth knowing:

- Edit one book's manuscript and only that book rebuilds; the others are skipped
  in well under a second.
- Edit the shared preamble and every book rebuilds, because they all depend on
  it. (This is correct: a change to the shared styling can affect any of them.)
- There is a recipe version baked into the hash. Bump it in `build.py` (the
  `RECIPE_VERSION` constant) when you change the build commands themselves in a
  way that should force everything to rebuild.

`python3 build.py list` shows the state at a glance, and `--force` ignores it.

## Figures

Vector figures live as hand-authored, editable sources: `assets/fig_*.svg`,
the only form a figure exists in under `src/`. The renders the manuscript
embeds are build byproducts in `temp/<slug>/figures/`, produced by the first
step of every book build (see `src/shared/render_svgs.py`, also runnable on
its own). The workflow is simply: edit the `.svg`, run `python3 build.py`.

Freshness is decided by content, not timestamps: each source's SHA-256 is
kept beside the renders, and a figure is re-rendered exactly when its `.pdf`
is missing or its `.svg` bytes changed. Editing a label is always enough;
touched files, copied trees, and zips with scrambled timestamps never confuse
it, and deleting a `.pdf` is never necessary. Rendering needs `cairosvg`
(`pip install cairosvg`); a book with `.svg` figures cannot build without it.

## Layout

The top level holds exactly three folders, always the same three, plus the files
you run or read. Everything that is source, the build code and the manuscripts
alike, lives in `src/`; everything that can be thrown away and regenerated lives
in `temp/`; the finished books live in `output/`.

```
sovereign-press/
  build.py            the one orchestrator: discover, hash, build, snapshot
  press.toml          workshop-wide settings: the build order, shared defaults,
                      and the Primer-to-Atlas cross-map
  README.md           this file
  MANIFEST.md         a full inventory: every file, why it exists
  .gitignore          keeps temp/, the snapshot, and caches out of version control

  src/                all source code and manuscripts; nothing regenerable
    shared/           the machinery every book depends on
      preamble.tex    the series styling, plus the workbook tooling (see below)
      preprocess.py   Markdown clean-up, driven by each book's [preprocess]
      mkversion.py    composes the version tag from each book's [version]
      make_bg.py      regenerates the cover wash from its source art
      assets/         shared images: the cover wash and the art it derives from
    tests/
      _common.py      shared discovery used by both suites
      test_build.py   build invariants, run once per book
      test_review.py  content review, run once per book
    books/            one folder per book; any folder with a book.toml is a book
      atlas-home-node/
        book.toml     this book's title, version, preprocess, review, and
                      language-edition settings
        manuscript.md the source of truth for this book (English)
        manuscript-NL.md  the Dutch edition, a translation beside manuscript.md
        frontmatter.tex this book's title page and Contents (English)
        frontmatter-NL.tex the Dutch title page and Contents
        assets/       images embedded by this book only (shared by both editions)
      primer-first-contact/      ... same shape ...

  temp/<slug>/        transient working files per book; throw away any time
  output/<slug>.pdf   the finished books (plus output/<slug>-<CODE>.pdf per
                      translated edition) and .build-state.json (the hash cache)
  recovery.zip        a snapshot of all sources and PDFs, refreshed every build
```

The split is deliberate: `src/` is everything you write and keep, the build code
and the manuscripts together; `temp/` is what the build produces on the way and
you never need to look at; `output/` is what you hand to a reader. `python3
build.py clean` empties `temp/` and touches nothing else.


## Which files do you actually need?

- A book's **`manuscript.md`** is its source; keep and edit it.
- The generated **`.tex`** lives under `temp/<slug>/` and is rebuilt every time.
- A book's **`output/<slug>.pdf`** is the only file a reader needs. To share a book,
  share its PDF and nothing else.
- Everything under `temp/` is disposable; delete it any time with `clean`.
- `recovery.zip` is the safety net: delete a loose PDF and recover it from there.

## Adding a new book

A book is just a folder under `src/books/` with a `book.toml`. To add one:

1. Make the folder, e.g. `src/books/atlas-school/` (a future Atlas volume).
2. Write its `book.toml` (copy an existing one and adjust). The `[project]` block
   sets the title and the two running-header labels; `[version]` sets the tag;
   `[preprocess]` controls the Markdown clean-up; `[build]` can override any
   workshop default (for example a per-book `page_ceiling`); `[review]` (optional)
   turns on the structural checks that book should be held to.
3. Write its `manuscript.md` and `frontmatter.tex`, and drop any images in
   `assets/`.
4. Add its slug to `[order]` in `press.toml` so it builds in the right place
   (books not listed there still build, just alphabetically after the listed ones).
5. Run `python3 build.py <slug>`.

The version tag is `v{volume}v{version}i{iteration}`, composed from `[version]`
in `book.toml`. By convention `version = 1` means "not yet shared"; `iteration`
is bumped on every working revision (with `build.py bump <slug>`); `volume` is
the book's number in its series.

## Language editions

A book can carry translated editions without becoming a second book. Each is one
`[[language]]` block in the book's `book.toml`, pointing at a translated
manuscript that lives beside `manuscript.md` in the same folder:

```toml
[[language]]
code               = "NL"                       # -> output/<slug>-NL.pdf
manuscript         = "manuscript-NL.md"          # the translation, beside manuscript.md
frontmatter        = "frontmatter-NL.tex"        # a translated title page (optional)
lang               = "nl-NL"                      # pandoc: correct hyphenation
book_short         = "ATLAS / DEEL 1"            # running-header label for this edition
start_marker       = "## Waarom dit boek bestaat" # this edition's first body line
promote_to_chapter = ["## Waarom dit boek bestaat", "## Dit boek gebruiken"]
# review-suite helpers so the structure is checked in its own language:
part_word     = "DEEL"             # body uses "# DEEL N:"
pointer_lead  = "**Aanwijzing.**"  # Pointer boxes' lead phrase
cover_word    = "Omslag"           # title-page Contents entry
contents_word = "Inhoud"           # TOC heading word
```

`build.py` then produces `output/<slug>.pdf` (the default edition) and one
`output/<slug>-<CODE>.pdf` per language, from the same one command. A translation
**shares the English edition's version tag**, because it is the same version in
another language: editing a translation rebuilds only its own PDF and never bumps
`[version]`, while editing `manuscript.md` still drives the shared tag. Figures
are rendered once and shared. Both test suites check every edition too: the build
invariants (no dashes or smart quotes, an ASCII-plus-diacritics charset, a
one-page title page) and the content review in the edition's own language (its
`part_word`, `pointer_lead`, and so on). Add `manuscript-NL.md` and any
`frontmatter-NL.tex` to `MANIFEST.md` so the completeness check stays satisfied.

## The workbook format, and how to author it

The Primer is a workbook: every concept is one page with the same shape, so a
reader always knows where they are. The shared preamble carries the tools that
shape it, and the preprocessor lets you write those pages in clean Markdown.

The pieces, in the preamble:

- `\ssbox` a small, pen-tickable checkbox.
- the `tracks` box with `\tlinux \tmac \twin` (and `-n` "note" variants) for
  exact, platform-specific instructions on the three kinds of machine: CachyOS,
  macOS, Windows. Used only where the three genuinely differ.
- the `promptbox` panel for natural language destined for a search box or an AI
  chat: the same on every machine, set in italics, with CAPITALS as placeholders
  the reader replaces.
- the `doit` box, a task list whose every line is a checkbox.
- `\seeline{...}` the "You should see" line that tells the reader the step worked.
- `\concept{number}{title}` the per-page heading: it starts a fresh page, adds a
  Contents entry, and prints the number and title over a rule.

You do not write those by hand. With `workbook = true` in a book's `[preprocess]`,
the preprocessor turns this Markdown into the page above:

```
### 41. whoami: who am I

whoami prints the name of the user you are currently acting as.

::: tracks
linux: ls
mac: ls
win: dir
:::

::: doit
Type whoami and press Enter.
Read the name it prints: that is the user you are right now.
:::

::: see
your username printed on its own line.
:::
```

A `### N. Title` line becomes the page heading and a fresh page. A `::: tracks`
block becomes the three-OS box: each row is `key: value` (key is linux/mac/win;
anything else is a hard error), and a value beginning with `(note)` is shown as an
italic note instead of a typed command, for click-paths and per-OS facts. The box
is used only where the three OSes genuinely differ; identical commands live in the
step text instead. A `::: prompt` block becomes the prompt panel, for natural
language aimed at a search box or an AI chat, identical on every machine, with
CAPITALS as placeholders. A `::: doit` block becomes the ticked checklist (plain Markdown,
so bold and `code` work). A `::: see` block becomes the success line. Everything
between the heading and the first block is ordinary Markdown explanation. The
escaping of shell characters (so a `>` or a `|` in a command renders correctly) is
handled for you.

Per-concept artwork is a later production step: the pages are designed to read
well without an image, and a picture can be dropped in when the art exists. The
`src/books/primer-first-contact/` manuscript is the worked example, one hundred
concepts in this format.

## The shape of the series

Two volumes, one hand-off. The Primer (Volume 0) is the on-ramp: it assumes only
that the reader can use a search engine, sets them up with an AI of their own early,
and walks the hundred small ideas the Atlas quietly assumes. The Atlas is the map
itself, dense on purpose, read with that AI at hand, and Volume 1 (Home Node) is its
first and, so far, only volume. `press.toml` keeps a short `[crossmap]` note recording
the pairing. Whether later Atlas volumes (Volume 2 onward) ever exist is deliberately
left open and depends on whether these first two land well: nothing in the press
promises them, and nothing blocks them.
