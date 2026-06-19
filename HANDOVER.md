# HANDOVER -- Sovereign Stack, Volume 1: Home Node

Read this first. It is the single document needed to continue this project in a
fresh context. Unzip the bundle, read this, and you have everything.

---

## 1. What this is

A finished, 89-page A4 PDF field manual that teaches one person, starting from a
bare machine and with no prior technical background, to build a sovereign "home
node": a computer they own, running a local AI reachable securely over HTTPS from
anywhere, with the networking and security understanding behind every step. It is
scoped to home/personal use only and is the prerequisite foundation for a
sequential series (the multi-user "IT manager" scope is Volume 2). It ships with
two open-source companion apps (see section 6). The book is deliberately a
"cookbook" the reader finishes with their own model (cloud first, then local): it
teaches principles, not memorised commands.

The deliverable is the PDF. The rest of this bundle is how it is built and
maintained.

## 2. Current state and version

- **Version: v1v1i30** = volume 1 / version 1 / iteration 30. The tag is
  composed automatically: `src/mkversion.py` reads the volume and version from
  `config.toml` and takes the iteration from the name of the folder the project
  sits in (30). On each build, `build.sh` writes the result into
  `src/version.tex` (read by `src/preamble.tex`, with a `v1v1i00` fallback for a
  direct `latexmk`) and stamps it into `tracker.json`. Rename the folder,
  rebuild, and the tag follows; `test_review.py` asserts the tag, the folder
  name, and the tracker all agree. (i17 was skipped: the i16 bundle was unzipped
  into a folder named 17 and rebuilt, which the folder-driven tag turned into a
  v1v1i17 PDF with no separate content change; tracker.json records it.)
- **Versioning rule (the project's own discipline, also taught in Part 7.10):**
  advance the *iteration* on every internal build by naming the folder; move the
  *version* only when shared or published, by editing the `[version]` block in
  `config.toml`. Version 1 means "not yet shared." The first approved external
  share becomes version 2 (i.e. `v1v2i...`).
- **Status: English edition is content-complete; Part 10, a toolchain section,
  and the project-as-its-own-example tooling are in.** 89 pages (printed footer
  shows page X / 88; the cover is unnumbered). i15 added Part 10 (eight-layer
  troubleshooting map); i16 added the toolchain section, the folder-driven tag,
  the `test_review.py` suite, and first-use expansion of every acronym; i18 added
  `config.toml` (TOML config read for the volume/version), `tracker.json` (the
  changelog), `src/mkversion.py`, and the total page count in the footer
  (page X / Y via `lastpage`); i19 renamed the byproducts folder `output/` to
  `generated/` and pinned Python 3.14 as the project target (in `config.toml`);
  i20 added two screenshots (a pacman system update in Part 2.4, a btop monitor
  in Part 8.7; assets now number eight) and made the release bundle self-backing;
  i21 split the byproducts folder into `temp/` (transient) and `outputs/` (the
  final PDF), renamed the recovery archive to match the version (e.g. `21.zip`)
  and made `build.sh` self-heal it each run, added `MANIFEST.md` (a full file
  inventory, checked for completeness by the review suite), and made the bundle
  extract flat (no wrapper folder); i22 added Part 8.8, the reboot drill (a
  scheduled reboot as a continuous recovery test, framed by the power-cut
  disaster, plus a scheduled security audit with Lynis as the hardening
  sibling); i23 redirected every LaTeX byproduct into `temp/` (via
  `latexmk -output-directory`) so the project root stays clean during a build,
  recorded the whole build to `temp/build.log`, kept those traces instead of
  deleting them, added a `./build.sh clean` subcommand that lists `temp/` by
  size before clearing it, and added a third companion-app screenshot
  (`shot_session`, the recorder in live multi-entry use) to the companion-app
  chapter; assets now number nine. i24 added an A5 edition built from the same
  manuscript (the paper is a build parameter, not a forked tree): `build.sh`
  takes `a4` (default), `a5`, or `both`, and writes the chosen geometry into a
  generated `src/paper.tex` (the same pattern as `src/version.tex`), so the A4
  build is unchanged (still 82 pages) and A5 reflows from the one source (132
  pages, expected on the smaller page, zero overfull boxes via the `\ssfit`
  diagram wrapper). i24 also added a clickable "Cover" line as the first Contents
  entry and PDF bookmark (jumping to page 1) in both editions, and a review check
  that fails if the recovery archive is missing after a build, so the bundle can
  never ship without its own self-backup inside it. i25 fixed an A5-only
  title-page overflow: the cover's fixed vertical spacing, tuned for A4's height,
  pushed the final strap line onto a second page on the shorter A5 page (an orphan
  that inherited the running header and the version tag), and it raised no
  overfull box, so the log checks never saw it; the title-page spacing is now
  elastic (natural sizes with a minus-shrink budget, the central `\vfill` taking
  positive slack), so A4 is unchanged and A5 compresses just enough to stay one
  page (now 131 pages), and `test_build.py` gained the check that would have
  caught it (the Contents must land on page 2, asserted for every edition's PDF).
  i26 made the closing colophon a deliberate page rather than an accidental
  orphan: the appendix fills its last text page, so the final italic line spilled
  onto its own page under the running header; it now forces its own page, drops
  the header and footer, and is centred with a thin rule (A4 unchanged at 82
  pages; A5 132). No test was added for i26 (the page break is explicit, so there
  is no silent failure mode, unlike the title page). i27 is the first large
  editorial revision since the structure settled, in five threads driven by the
  author. (a) The reference distribution switched from the Debian/Ubuntu LTS
  family to Arch across the whole book, framed as minimalism-as-security (every
  installed package is extra attack surface; no mainstream family ships as little
  as Arch), with the rolling-release tradeoff stated honestly and CachyOS and
  Manjaro named as Arch-derived, desktop-ready on-ramps (bare Arch from scratch
  for the determined). Every reader-facing command is now pacman; apt and dnf
  survive only as even-handed contrasts; the Part 2.4 update screenshot now
  illustrates the exact `pacman -Syu` in the text. (b) Over-claims were removed
  while keeping the sovereignty thesis: "no closed component" became "open source
  as high as the stack goes", and the firmware-floor honesty was deepened (a
  machine is dozens of chips, each with its own closed firmware/microcode; NVIDIA's
  largely proprietary GPU drivers named as an honest dependency; a full map is not
  obtainable in today's ecosystem; opening it is the standing goal for AI-native,
  privacy-first systems). (c) Token-speed claims were hedged: every tokens-per-
  second figure is flagged as an approximation, and the context-fill slowdown (a
  fuller window generates slower) is stated in 1.2 and cross-linked in 4.6; the
  4.8 GB derivation was corrected to about 0.6 bytes per parameter, consistently.
  (d) Volume 1 was rescoped to home/personal only and made the explicit
  prerequisite foundation of a sequential series; the multi-user "IT manager"
  scope was moved to Volume 2 (a school/building), and the "you are now the entire
  IT department" framing softened to running your own home IT plus a first map for
  going further. (e) Accessibility was sharpened: a front-matter passage states no
  prior technical background is needed (book + any basic LLM), that AI is assumed
  already available (cloud first, then local), and that the aim is to anchor that
  capability to ground you own so it cannot be taken away; the mid-2026 frontier
  claim was broadened (OpenAI and Anthropic most visibly, Google and open-weight
  models close behind). A4 grew from 82 to 86 pages (still well under the 100
  ceiling), A5 from 132 to 137; no new test was needed (all changes are prose, and
  the existing suites cover dashes, ASCII, acronyms, structure, and page limits).
  Zero em-dashes, zero
  en-dashes, ASCII-only, zero overfull boxes, every acronym expanded. i28 is a
  build/test change with no manuscript edits: a bare `./build.sh` now builds BOTH
  editions by default (the mode default went from `a4` to `both`), after it proved
  too easy to run the script and not notice the A5 was never produced. Two guards
  make a missing edition impossible to miss: build.sh now verifies each edition it
  built actually produced its PDF and fails the whole run loudly (non-zero exit,
  before the recovery archive is written) if one is absent; and test_build.py gained
  a check that both deliverables exist and are non-trivial (>50 KB), gated on a
  build having run so the standalone source pass still skips. The overfull check was
  generalised from the A4 log alone to every edition log (so an A5-only overfull
  would be caught); the page ceiling stays A4-only by design (A5 is legitimately
  ~137 pages). Both guards were verified negatively (removing the A5 PDF fails the
  suite; a missing-PDF guard aborts the build before the archive step). Pages
  unchanged (A4 86, A5 137). Verified by
  `src/tests/test_build.py` (now: the dash/ASCII/version source checks, a no-dash
  check on the LaTeX source, per-edition overfull checks, the A4 page ceiling, the
  both-editions-present check, and a one-page title-page check per edition built)
  and `src/tests/test_review.py` (22 checks). i29 is a polish pass toward a final
  version-1 manuscript, in three threads. (a) The series gained a cover subtitle,
  "A ground-up IT education for the age of AI", set in italic under the SOVEREIGN
  STACK title and above the rule in `src/frontmatter.tex`; the title-page spacing
  was re-tuned (a small clawback from the lower gaps) so both editions' covers
  still fit one page. The subtitle is on the cover only, not the body title block,
  to keep the acronym first-use ordering intact (the first expanded "Information
  Technology (IT)" must still precede any bare "IT" in the manuscript; putting the
  subtitle in the body broke this and was reverted). (b) A new front-matter
  section, "Why this book exists", was added after the tagline: the book's reason
  for being in the author's voice, keeping everything personal out except the
  professional experience (a pre-LLM-era IT specialist and programmer who held
  responsibility for keeping systems running, with no claim of managing people,
  dropped per the author; the earlier aphantasia note was also dropped). Its
  argument is that the language model (an adaptive tutor) plus cheap open hardware
  turn rented intelligence into owned sovereignty, framing the volume as an
  accessible, start-at-home, security-first foundation. (c) The appendix science
  gallery was expanded with three research-lab figures (two "Relational Reality"
  multi-lens diagnostic dashboards and a finite-size-scaling phase-transition
  study across system sizes up to four million nodes), plus an encouragement note:
  every figure was made by one person on ordinary hardware with a model as partner,
  so do not be afraid to do real science with the AI. Three images were added to
  `assets/` (lab_relational_a/b.png, lab_scaling.png) and to MANIFEST. A4 grew from
  86 to 89 pages, A5 from 137 to 140; zero overfull in both editions; recovery
  archive now 34 files; both suites green. Still version 1.
- **i30 (this iteration): over-claim and humility pass; still version 1.** At the
  author's direction, a pass to remove over-claims and add nuance, on the
  principle that a wrong assumption is the most expensive thing in troubleshooting
  (when stuck, the misleading belief is usually an unexamined certainty about
  where to look), so the book must not seed one. The iteration advanced (i29 to
  i30); the version was deliberately left at 1, because the bump to v1v2 is the
  author's own later step, not this pass (correcting the i29 note that had bundled
  the proofread and the version bump into i30). Four genuine over-claims were
  fixed and the rest of the manuscript was swept and found already disciplined.
  (a) The cover description in `src/frontmatter.tex` was the main outlier: "an AI
  agent you can reach over HTTPS from anywhere on Earth, with no cloud underneath
  it" read as if the reach itself were cloud-free, when worldwide reach always
  rides the internet, a shared, rented, cloud-like infrastructure. It now reads
  that the agent runs on the box you own, reached over the internet, with no cloud
  doing its thinking or holding its data, so the no-cloud claim is scoped to
  compute and storage and the internet dependency for reach is stated plainly. The
  cover strap and the thesis motto ("depending on nobody", already qualified in
  the honest-qualification paragraph) were kept. (b) The home-node definition in
  the body was scoped the same way (reachable from anywhere yet dependent on
  nobody for its thinking and data; the internet is the road you take to reach it,
  not something it runs on), making the operation-versus-reach distinction
  explicit. (c) A genuine internal contradiction in the Part 6.9 benefits list
  ("every layer is open ... the only entity that can alter your stack is you") was
  reconciled with the firmware floor the book names elsewhere: the bullet now
  scopes openness to the layers you can own, names the closed firmware floor as
  the one part you do not control while noting it cannot rewrite the software you
  run, and ends that everything above it is yours. (d) The closing line "one
  machine you can hold in your hands and understand completely" became "learn from
  the ground up", honest about the un-auditable floor and echoing the cover
  subtitle. The LLLM coinage (Local Large Language Model, three Ls) was checked and
  confirmed intentional, not a typo, and left as is. No files added or removed; A4
  stays 89 pages, A5 stays 140; zero overfull in both editions; both suites green;
  recovery archive 34 files. Still version 1.

## 3. The queue (next steps, in order)

1. **Author's personal proofread, then lock / publish as v1v2.** The manuscript
   is at a near-final version-1 state through i30 (Arch reference, tightened
   claims, home-only rescope, the "Why this book exists" preface, the cover
   subtitle, the expanded appendix science gallery, and the i30 over-claim and
   humility pass are all in). The plan the author stated: read the whole thing
   through personally, then move to version 2 (set `version = 2` in the
   `[version]` block of `config.toml`, which makes the tag `v1v2i...` at the next
   iteration), rebuild, and begin sharing it with others. The version bump to v2
   is the author's own step and was deliberately not done in i30; this pass only
   advanced the iteration and left the version at 1. No content changes at lock
   time beyond what the proofread turns up. The review suite (`test_review.py`)
   automates the acronym, structure, and version-tag parts.
2. **ELI5 English edition.** Short and simple. **10 pages maximum. No index, no
   appendix, no intro.** Straight into a bedtime-story format. A separate, much
   gentler retelling of the same journey.
3. **Dutch edition** (full translation of the main book). Open question the
   author has not finally answered: keep technical terms in English (LAN, WAN,
   reverse proxy, embeddings, etc.) while translating the prose around them
   (**recommended**, and the text was written to translate this way), versus
   full localisation. The author will not verify the Dutch personally.
4. **Dutch ELI5.**

## 4. Hard constraints and voice (must be preserved)

- **No em-dashes and no en-dashes anywhere.** Use commas, colons, parentheses,
  or hyphens. This applies to the book *and* to assistant chat replies. It is
  checked by the test suite; keep it green.
- **ASCII-only manuscript.**
- **Voice:** warm, philosophical, technically deep, and epistemically honest.
  Flag approximations as approximations. Admit trust floors (firmware/microcode)
  rather than overclaiming. The author has confirmed the voice is exactly theirs.
- **Scope discipline:** 100 pages is an internal *upper limit*, not a target;
  staying well under is better. The author has repeatedly asked the assistant to
  be the voice of restraint against scope creep. Add only what clearly earns its
  place.
- **Formatting:** prose over bullets and headers. Minimal formatting. The
  "Pointer" boxes are the one recurring structured element (styled via tcolorbox
  in the preamble).
- **No citations / no bibliography.** Figures are given as honest 2026
  approximations in the prose, on purpose.

## 5. How to build

Prerequisites: `pandoc`, a TeX Live install with `xelatex` and `latexmk`, and
the fonts TeX Gyre Pagella, TeX Gyre Heros, and DejaVu Sans Mono (all standard
in TeX Live). The project targets Python 3.14 (declared in `config.toml`); the
scripts (`preprocess.py`, `mkversion.py`, the tests) use only the standard
library, including `tomllib`, so they run on 3.11+. `make_bg.py` needs Pillow.

```
./build.sh                       # full build, BOTH editions (default): markdown -> LaTeX -> PDF
./build.sh a4                    # A4 only
./build.sh a5                    # A5 only (same manuscript, narrower page)
python3 src/tests/test_build.py  # build invariants (run after build.sh; asserts both editions exist)
python3 src/tests/test_review.py # content review: acronyms, version, structure
```

`build.sh` runs four steps: `src/preprocess.py` (manuscript ->
`temp/vol1_latex.md`, once), then for each requested edition `pandoc` (-> the
`.tex` in `temp/`, with the preamble and title page inlined) and
`latexmk -xelatex -output-directory=temp` (-> the PDF), and finally a self-heal
of the recovery archive. The paper is selected by a generated `src/paper.tex`
that `build.sh` writes per edition (both editions by default; `a4` or `a5` builds
just one); the A4 edition keeps the base name and the A5 edition gets a `-a5`
suffix, so the two never collide and the A4 test suite keeps measuring the A4
book. Each requested edition is verified to have produced its PDF before the run
finishes (a missing PDF fails the build loudly, rather than passing silently).
Each final PDF is moved to `outputs/`; every other artifact (the `.tex` and all
xelatex byproducts) stays in `temp/`, and the whole run is also written to
`temp/build.log`. Those traces are kept for review, not deleted; `./build.sh
clean` lists `temp/` by size and then clears it.

Quick recompile without editing (skips pandoc), from the project root:

```
latexmk -xelatex -output-directory=temp temp/sovereign-stack-vol1.tex
```

The generated `.tex` now lives in `temp/` (along with every other byproduct);
it is self-contained except for the images, which it finds in `assets/` via the
`\graphicspath` line in the preamble.

## 6. The two companion apps (referenced by the book; separate projects)

The node ships with two open-source AI-native apps. The book teaches the first
in full and points at the second as the horizon.

- **App 1, the voice transcriber.** A vanilla-JS progressive web app: records in
  the browser with a live waveform and timer, replays while still recording,
  transcribes on-device with timestamps, and lets the local model reply so a
  voice note becomes a conversation. On-device by default, remote optional per
  step. It has its own test suite (the "own the tests" example used in Part 9).
  Delivered separately by the author as `MyAI-updated.zip`. Its UI appears in the
  book via `assets/shot_main.png`, `assets/shot_settings.png`, and
  `assets/shot_session.png` (the last a live multi-entry session).
- **App 2, "relational-reality."** Exploratory computational-physics research
  code (public domain). It grows graphs from a simple rule (a two-star ERGM plus
  a locality bias) with no coordinate system programmed in, and measures the
  spectral dimension of the geometry that emerges, asking where it looks
  four-dimensional. The rule it ships with does not produce 4D, which was never
  the point. Its real significance in the book is the "auto-science bot": wire it
  to an agent that reads each result, proposes the next rule, reruns, and
  compares, and a home node becomes a primitive automated scientist. The author
  holds the source separately (`Archive.zip`). Its shapes appear in the appendix
  gallery (`assets/art_*.png`) and as the faded wash behind the cover
  (`assets/bg_titlepage.png`, baked from `assets/art_blob.png`).

## 7. Book structure (orientation for editing)

21 top-level chapters. The cover (`src/frontmatter.tex`) carries the series
subtitle "A ground-up IT education for the age of AI" under the title. Front
matter: a "Why this book exists" mission note (author's professional experience
only, the model-plus-open-hardware-equals-sovereignty argument); a style/scope
note; "How to read this book"
(the cookbook method); "The Map" (a skills-and-principles roadmap with a TikZ
"temple" diagram, plus the trust-floor honesty and the isolation/cross-monitoring
security philosophy); "The thesis: own your ground"; and the companion-app
chapter (with the three screenshots and the "two apps, and a pattern" framing).
Then Parts 0-10: 0 the map of concepts; 1 hardware (the memory-bandwidth lens,
key formula tok/s ~ bandwidth GB/s / model-GB, with ~0.6 bytes/param, flagged as
an approximation that also slows as the context window fills); 2 Linux (pacman on
Arch as the reference base, framed as minimalism-as-security, with apt and dnf as
even-handed contrasts and CachyOS/Manjaro as desktop-ready Arch derivatives); 3 networking (LAN/WAN, NAT,
reverse proxy groundwork); 4 local AI; 5 retrieval up to offline Wikipedia; 6
reachable safely (reverse proxy, HTTPS, DDNS, port-forward); 7 cybersecurity
(firewall, logs, bans, backups, and 7.10 versioning incl. git push/pull and the
iteration-vs-version idea); 8 a society of agents; 9 the method (describe and
verify, own the tests); 10 troubleshooting (the eight-layer map from hardware to
intent, the zoom-in-vs-zoom-out decision, and steering an AI that cannot see
your machine; pays off the "which layer is lying to me?" thread from 0.1). Then
"The Build Path" (the ordered execution), "How This Book Was Made" (now also carrying a toolchain
group: why LaTeX, why PDF, a format for each job, and the Arch pacman packages),
the closing (the economic argument: this is a complete, practical IT foundation
at one scale, running the information technology of your own home plus a solid
first map for going further; the multi-user "IT manager" scope is deferred to
Volume 2, and the series is sequential with Volume 1 as prerequisite; the chain
to Volume 2 = a mansion or school, Volume 3 = a university, then a city), and the
appendix ("the spicy bit": open-source trust, the cross-monitoring-web view of
trustworthy intelligence, math-in-motion, the auto-science crescendo, a musing
on structure that falls out of nothing, and an expanded image gallery of the
research lab: the three art images plus two multi-lens diagnostic dashboards and
a finite-size-scaling phase-transition study, with a note encouraging readers to
do real science with an AI partner).

## 8. Build internals (gotchas)

- `src/preprocess.py` drops the manuscript's title block (the custom title page
  in `frontmatter.tex` replaces it), promotes the three front-matter headings to
  chapters, drops standalone `---`, strips ordinary code-fence language hints,
  and **preserves raw-LaTeX fences (```{=latex})** which carry the TikZ roadmap
  diagram and the `\includegraphics` blocks. Do not let those raw fences get
  flattened.
- Images are referenced by bare filename in the manuscript and frontmatter; they
  resolve because the preamble sets `\graphicspath{{assets/}{./}}`.
- `bg_titlepage.png` is a derived asset (25% opacity of `art_blob.png` over
  white). Regenerate with `python3 src/make_bg.py` if the opacity or source
  changes.
- After editing, always rebuild and run both test suites before calling an
  iteration done. The iteration tag advances automatically from the folder name
  (via `src/mkversion.py` + `config.toml`); you do not edit it by hand. To make a
  new iteration, work in, or rename to, a folder named after the new number.
- **Single source, on purpose.** The whole book is one `.md` and compiles to one
  `.tex`; do not split it into per-chapter files. At this size (about 1,400 lines,
  80 pages) a single source is easier to grep, sed, diff, and cross-reference, and
  LaTeX computes all pagination and section numbering at build time, so editing
  never touches page numbers. Splitting would only pay off at multi-volume scale,
  and even then the clean way is per-chapter source files concatenated from a
  manifest, still producing one `.tex`.
- **A5 is a build parameter, not a forked tree (same single-source rule).** The
  A4 and A5 editions are the one manuscript built at two page sizes. `build.sh`
  writes the chosen geometry into a generated `src/paper.tex` (mirroring
  `src/version.tex`): it sets the paper class, the `\geometry` call, the
  version-tag corner coordinates (`\sstagx`/`\sstagy`), and the `\sspaperclass`
  flag. `src/preamble.tex` `\input`s it, and if it is absent falls back to A4, so
  any `.tex` still compiles standalone. The A4 path reproduces the original
  geometry exactly, so the A4 book is unchanged. The two wide TikZ diagrams are
  wrapped in `\ssfit{...}`, a helper that is a no-op on A4 and scales-down-only on
  A5, so A5 fits with zero overfull boxes (it does not enlarge anything, so A4 is
  provably untouched). Do not hard-code a paper size back into the preamble or the
  pandoc call; keep it flowing through `paper.tex`.
- **The Contents opens with a clickable "Cover" line.** `src/frontmatter.tex`
  adds `\phantomsection` + `\addcontentsline{toc}{chapter}{Cover}` on the title
  page, which (via hyperref) creates both the first Contents entry and a PDF
  bookmark, both jumping to page 1. It is one visible line, by request. Present in
  both editions.
- **The title page is sized to fit both papers, and a test guards it.** The cover
  is one `titlepage`, and its spacing is elastic: each gap keeps its natural size
  but carries a `minus` shrink component, with the central `\vfill` absorbing
  positive slack. On A4 (ample height) the `\vfill` takes the slack so every gap
  is at natural size and the page is unchanged; on A5 (less height) the same fixed
  spacing would overflow, so TeX shrinks the `minus` glue just enough to keep it
  one page. The trap this avoids: a title page that overflows does NOT raise an
  overfull box, because `\end{titlepage}` silently flows the excess onto a second
  page (which then inherits the running header and the tag, an orphan). Nothing in
  the log flags it. The check that catches it is structural, in `test_build.py`:
  the cover is page 1, so the Contents heading must land on page 2, asserted for
  every PDF in `outputs/` (A4 and A5 both, since A5 has less vertical room and is
  otherwise exempt from the A4-only build checks). If you add lines to the cover
  and an edition spills, that check fails; widen the `minus` budget on the
  title-page gaps rather than hand-tuning per paper.
- **The book ends on a deliberate colophon page.** The last lines of the
  manuscript are a raw-LaTeX block that issues `\clearpage`, sets
  `\thispagestyle{empty}` (no running header, no page number), and centres the
  colophon with a thin rule. This is intentional: the appendix fills its final
  text page, so the colophon would otherwise orphan onto a near-empty page under
  the running header and read as an accident. Forcing the break and stripping the
  chrome makes it a closing, not a spill. Only the version tag remains (it is
  drawn on every page by `\AddToShipoutPictureFG`, independent of page style).
  There is deliberately no test for this: the page break is explicit in the
  source, so there is no silent failure mode to guard (contrast the title page,
  which overflowed without warning), and "a page looks too empty" is an aesthetic
  call that does not reduce to a crisp assertion. If you edit the ending, just
  rebuild and look at the last page.
- **Build artifacts are written straight into `temp/`, and kept.** `pandoc`
  writes the `.tex` into `temp/`, and `latexmk` runs with
  `-output-directory=temp`, so the project root never fills with `.aux`, `.log`,
  `.fls`, `.fdb_latexmk`, `.toc`, or `.xdv` files mid-build; only the finished
  PDF is moved out, to `outputs/`. The whole run is teed to `temp/build.log`.
  Nothing in `temp/` is deleted at the end of a build: the traces are left for
  review. `temp/` is the one folder dedicated to that disk churn, and clearing it
  is a single overseeable operation: `./build.sh clean` first prints `temp/`
  sorted largest-first (`du -ah`), then removes the folder (and only that folder,
  via a guarded `rm`). The next build recreates it.
- **The release bundle is self-backing, and extracts flat.** The delivered zip
  is named after the version and unzips directly to the working tree (no wrapper
  folder of the same name), so you extract it into a folder you have named after
  the iteration. Inside that tree sits `<version>.zip` (e.g. `26.zip`): a
  self-healing snapshot of every source plus the built PDF(s), excluding `temp/`
  and itself. `build.sh` refreshes it on every run with `zip -FS` (file-sync: adds
  new, refreshes changed, drops removed), so it never drifts. A review check
  (`test_review.py`, section 17) fails if that inner archive is missing after a
  build, so the bundle can never ship without its own self-backup. The loose PDF
  in `outputs/` is therefore deletable (the build remakes it, or you fetch it from
  the archive), and if a rebuild ever fails you recover both the PDF and the exact
  generating code from that one file. To cut a release: build (which refreshes the
  archive), then zip the tree's contents (minus `temp/`) so it extracts flat,
  keeping the inner `<version>.zip` in place.

## 9. File layout

```
sovereign-stack-vol1/
  HANDOVER.md                 this file
  README.md                   build instructions and file roles
  build.sh                    the build pipeline
  config.toml                 project config; build.sh reads volume/version here
  tracker.json                version changelog (current pointer + history)
  sovereign-stack-vol1.md     THE MANUSCRIPT (source of truth; edit this)
  (the generated book PDF lives in outputs/, the standalone .tex in temp/; see below)
  src/
    preprocess.py             manuscript markdown -> LaTeX-friendly markdown
    mkversion.py              composes the tag from config.toml + the folder name
    preamble.tex              geometry (A4 default, A5 via paper.tex), colours, fonts, TikZ, \ssfit, version tag, graphicspath
    frontmatter.tex           custom title page (cover wash) + clickable "Cover" line + table of contents
    version.tex               generated each build (the \def\ssversion line)
    paper.tex                 generated each build (paper class, geometry, tag coords, \sspaperclass)
    make_bg.py                regenerate the faded cover background (needs Pillow)
    tests/
      test_build.py           build-invariant tests (dashes, ASCII, overfull, pages)
      test_review.py          content-review tests (acronyms, version, structure)
  assets/
    bg_titlepage.png          faded cover background (derived from art_blob.png)
    art_blob.png              appendix gallery + cover source
    art_spectral.png          appendix gallery: three spectral layouts
    art_flow.png              appendix gallery: final flow dashboard
    shot_main.png             companion-app chapter: main view
    shot_settings.png         companion-app chapter: settings
    shot_session.png          companion-app chapter: live multi-entry session
    shot_monitor.png          Part 8.7: node monitor (btop)
    shot_update.png           Part 2.4: system update (pacman)
  outputs/                     the final PDFs (A4 always; A5 when built)
    sovereign-stack-vol1.pdf      (A4)
    sovereign-stack-vol1-a5.pdf   (A5, present after ./build.sh a5 or both)
  temp/                        transient artifacts; kept for review, cleared via ./build.sh clean
    build.log                 full record of the last build (stdout and stderr)
    vol1_latex.md             intermediate (from preprocess.py)
    sovereign-stack-vol1.tex  generated LaTeX (from pandoc)
    (xelatex byproducts: .aux .log .toc .fls .fdb_latexmk .xdv etc.)
  <version>.zip                self-healing recovery snapshot (sources + PDF)
```
