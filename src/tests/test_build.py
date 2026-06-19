#!/usr/bin/env python3
"""Build-invariant tests for Sovereign Stack, Volume 1.

Run from the project root (standalone for the source checks, or after build.sh
for the full set):

    python3 src/tests/test_build.py

These encode the constraints the book is held to, the same checks that were run
by hand on every iteration: no em or en dashes anywhere, an ASCII-only
manuscript, a version tag present, and, once the build has run, no overfull
boxes in either edition's log, a page count inside the deliberate ceiling, and
both editions (A4 and A5) actually produced, since a bare build now makes both.
Exit code 0 means every check passed. This is the book practising its own
thesis: own the tests.
"""
import os
import re
import sys
import glob
import shutil
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MD = os.path.join(ROOT, "sovereign-stack-vol1.md")
PREAMBLE = os.path.join(ROOT, "src", "preamble.tex")
PDF = os.path.join(ROOT, "outputs", "sovereign-stack-vol1.pdf")
LOG = os.path.join(ROOT, "temp", "sovereign-stack-vol1.log")

fails = []


def check(name, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def skip(name, why):
    print(f"[skip] {name}  ({why})")


# ---- source checks (always available) ----
md = open(MD, encoding="utf-8").read()
check("no em-dash (U+2014) in manuscript", "\u2014" not in md)
check("no en-dash (U+2013) in manuscript", "\u2013" not in md)
non_ascii = sorted({c for c in md if ord(c) > 127})
check("manuscript is ASCII-only", not non_ascii,
      "found: " + " ".join(non_ascii) if non_ascii else "")

pre = open(PREAMBLE, encoding="utf-8").read()
m = re.search(r"v\d+v\d+i\d+", pre)
check("version tag present in preamble.tex", bool(m), m.group(0) if m else "none")

# The no-dash rule is "anywhere", not "in the manuscript only". The hand-written
# LaTeX source is checked for literal em/en dashes too (a real em-dash once sat in
# a preamble comment and went unseen because only the .md was scanned). The .tex
# is intentionally not held to ASCII-only: the preamble defines glyph fallbacks
# for a few Unicode characters, which must appear literally. A genuine en/em dash
# in LaTeX is written "--" / "---" (ASCII hyphens), so a literal U+2013 or U+2014
# in the source is always an accident.
TEX_SOURCES = [("preamble.tex", PREAMBLE),
               ("frontmatter.tex", os.path.join(ROOT, "src", "frontmatter.tex"))]
dash_hits = []
for label, path in TEX_SOURCES:
    if os.path.exists(path):
        t = open(path, encoding="utf-8").read()
        if "\u2014" in t:
            dash_hits.append(f"{label}: em-dash")
        if "\u2013" in t:
            dash_hits.append(f"{label}: en-dash")
check("no em/en dash in LaTeX source (preamble, frontmatter)", not dash_hits,
      "; ".join(dash_hits) if dash_hits else "")

# ---- build-output checks (after build.sh) ----
# Overfull boxes are checked on EVERY edition's latexmk log, not just A4's: the A5
# edition reflows on a smaller page, so an overfull box can appear there alone. The
# per-edition logs are temp/sovereign-stack-vol1.log (A4) and ...-a5.log (A5); the
# tee'd temp/build.log is intentionally excluded so latexmk warnings are not
# double-counted.
edition_logs = sorted(glob.glob(os.path.join(ROOT, "temp", "sovereign-stack-vol1*.log")))
if edition_logs:
    for lg in edition_logs:
        lname = os.path.basename(lg)
        ltext = open(lg, encoding="utf-8", errors="ignore").read()
        n_over = ltext.count("Overfull \\hbox")
        check(f"no overfull hboxes in build log ({lname})", n_over == 0, f"{n_over} found")
else:
    skip("overfull-hbox check", "build log not found; run build.sh first")

if os.path.exists(PDF):
    try:
        info = subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout
        pages = int(next(l.split()[1] for l in info.splitlines()
                         if l.startswith("Pages")))
        check("page count within the 100-page ceiling", 1 <= pages <= 100,
              f"{pages} pages")
    except Exception as e:  # pdfinfo missing or unreadable
        skip("page-count check", f"could not read PDF ({e})")
else:
    skip("page-count check", "PDF not found; run build.sh first")

# ---- both editions must be produced on every standard build ----
# A bare ./build.sh now builds BOTH editions, so a complete build is A4 + A5. This
# asserts both deliverables exist and are non-trivial in size, so a silently missing
# edition (the A5 was once skipped when A4 was the default) fails the suite instead
# of passing unnoticed. It is gated on a build having actually run: on a fresh
# checkout with no build artifacts it skips, exactly like the other build-output
# checks, so the standalone source-only run is unaffected. The 50 KB floor
# distinguishes a real, rendered PDF from an empty or stub file.
EDITIONS = {
    "A4 (sovereign-stack-vol1.pdf)": os.path.join(ROOT, "outputs", "sovereign-stack-vol1.pdf"),
    "A5 (sovereign-stack-vol1-a5.pdf)": os.path.join(ROOT, "outputs", "sovereign-stack-vol1-a5.pdf"),
}
build_ran = (os.path.exists(os.path.join(ROOT, "temp", "build.log"))
             or any(os.path.exists(p) for p in EDITIONS.values()))
if not build_ran:
    skip("both editions present (A4 + A5)", "no build artifacts; run build.sh first")
else:
    missing = [label for label, p in EDITIONS.items()
               if not (os.path.exists(p) and os.path.getsize(p) > 50_000)]
    check("both editions present and non-trivial (A4 + A5)", not missing,
          "" if not missing else "missing or too small: " + "; ".join(missing))

# ---- title page must be exactly one page (checked per edition) ----
# A title page whose fixed spacing overflows its paper does NOT raise an overfull
# box: \end{titlepage} silently flows the excess onto a second page, which then
# inherits the running header and the version tag (an orphan page). Nothing in the
# log flags it. The signal that actually catches it is structural: the cover is
# page 1, so the Contents heading must fall on page 2. If the title page spills,
# page 2 is the orphan and the Contents slides to page 3, so the marker is absent.
# This runs over EVERY PDF in outputs/ (A4 and A5 alike): the A5 edition has less
# vertical room, so an edition-specific overflow must be checked on the edition
# itself, not only on the A4 PDF the other build checks read.
pdfs = sorted(glob.glob(os.path.join(ROOT, "outputs", "*.pdf")))
if not pdfs:
    skip("title page is one page", "no PDFs in outputs/; run build.sh first")
elif not shutil.which("pdftotext"):
    skip("title page is one page", "pdftotext not available")
else:
    for pdf in pdfs:
        name = os.path.basename(pdf)
        try:
            p2 = subprocess.run(["pdftotext", "-f", "2", "-l", "2", pdf, "-"],
                                capture_output=True, text=True).stdout
        except Exception as e:
            skip(f"title page is one page ({name})", f"pdftotext failed ({e})")
            continue
        # page 2 of a healthy build is the Contents page: it carries the heading
        # "Contents" and the first TOC entry "Cover". The orphan overflow page has
        # neither (it holds the strap line and the running header).
        ok = ("Contents" in p2) and ("Cover" in p2)
        check(f"title page is one page; Contents on p2 ({name})", ok,
              "" if ok else "page 2 is not the Contents page (title page overflowed)")

print()
if fails:
    print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all checks passed")
