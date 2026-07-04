#!/usr/bin/env python3
"""Build-invariant tests for Sovereign Press (all books).

Run from the press root, standalone for the source checks or after a build for
the full set:

    python3 tests/test_build.py            # every book
    python3 tests/test_build.py atlas-home-node primer-first-contact

These encode the constraints every book is held to, the same checks that were
run by hand on every iteration of the original single book, now applied once per
book the press discovers: no em or en dashes anywhere, an ASCII-only manuscript,
a version tag wired to its book.toml, and, once a build has run, no overfull
boxes in that book's log, a page count inside the configured ceiling, the right
version tag in the build state, and a title page that is exactly one page. Exit
code 0 means every check passed. This is the press practising the book's own
thesis: own the tests.
"""
import os
import sys
import shutil
import subprocess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def skip(name, why):
    print(f"  [skip] {name}  ({why})")


def check_manuscript_ascii_and_dashes(slug, p):
    md = open(p["manuscript"], encoding="utf-8").read()
    check("no em-dash (U+2014) in manuscript", "\u2014" not in md)
    check("no en-dash (U+2013) in manuscript", "\u2013" not in md)
    non_ascii = sorted({c for c in md if ord(c) > 127})
    check("manuscript is ASCII-only", not non_ascii,
          "found: " + " ".join(non_ascii) if non_ascii else "")


def check_tex_sources_no_dashes(slug, p):
    # The no-dash rule is "anywhere", not "manuscript only". The hand-written
    # LaTeX (this book's frontmatter, each language frontmatter, and the shared
    # preamble) is scanned for literal em/en dashes too. The .tex is intentionally
    # NOT held to ASCII-only: the preamble defines glyph fallbacks for a few
    # Unicode characters that must appear literally, and a translated title page
    # carries Latin diacritics. A real en/em dash in LaTeX is written -- / ---
    # (ASCII hyphens), so a literal U+2013 / U+2014 in the source is an accident.
    sources = [("frontmatter.tex", p["frontmatter"]),
               ("shared/preamble.tex", os.path.join(C.SHARED, "preamble.tex"))]
    for lang in C.book_languages(slug):
        lp = C.language_paths(slug, lang)
        if lp["frontmatter"] != p["frontmatter"]:
            sources.append((f"{os.path.basename(lp['frontmatter'])} ({lp['code']})",
                            lp["frontmatter"]))
    hits = []
    for label, path in sources:
        if os.path.exists(path):
            t = open(path, encoding="utf-8").read()
            if "\u2014" in t:
                hits.append(f"{label}: em-dash")
            if "\u2013" in t:
                hits.append(f"{label}: en-dash")
    check("no em/en dash in LaTeX source (frontmatter, shared preamble)",
          not hits, "; ".join(hits) if hits else "")


def check_version_wired(slug, p):
    # The shared preamble must reference \ssversion and read the generated
    # version.tex, so the tag is computed rather than hard-typed.
    pre = open(os.path.join(C.SHARED, "preamble.tex"), encoding="utf-8").read()
    wired = ("\\ssversion" in pre) and ("version.tex" in pre)
    check("shared preamble uses the auto-derived \\ssversion tag", wired)
    # After a build, the generated tag must equal the tag composed from book.toml.
    want = C.compose_tag(slug)
    if os.path.exists(p["version_tex"]):
        vt = open(p["version_tex"], encoding="utf-8").read()
        import re
        m = re.search(r"v\d+v\d+i\d+", vt)
        got = m.group(0) if m else None
        check("generated version.tex tag matches book.toml", got == want,
              f"book.toml={want}, version.tex={got}")
    else:
        skip("generated version.tex tag matches book.toml",
             "version.tex not built yet; run build.py")


def check_overfull(slug, p):
    # Overfull boxes are read from this book's per-run latexmk log (temp/<slug>/
    # <slug>.log), not the tee'd build.log, so warnings are not double-counted.
    if os.path.exists(p["latexmk_log"]):
        ltext = open(p["latexmk_log"], encoding="utf-8", errors="ignore").read()
        n_over = ltext.count("Overfull \\hbox")
        check("no overfull hboxes in build log", n_over == 0, f"{n_over} found")
    else:
        skip("overfull-hbox check", "build log not found; run build.py first")


def check_page_ceiling(slug, p):
    ceiling = C.page_ceiling(slug)
    if os.path.exists(p["pdf"]):
        pages = C.pdf_pages(p["pdf"])
        if pages is None:
            skip("page-count check", "could not read PDF")
        else:
            check(f"page count within the {ceiling}-page ceiling",
                  1 <= pages <= ceiling, f"{pages} pages")
    else:
        skip("page-count check", "PDF not found; run build.py first")


def check_deliverable(slug, p):
    # A complete build leaves a single, non-trivial PDF in output/. The 50 KB floor
    # distinguishes a real, rendered PDF from an empty or stub file.
    if not os.path.exists(p["pdf"]):
        skip("deliverable PDF present", "not built yet; run build.py first")
        return
    ok = os.path.getsize(p["pdf"]) > 50_000
    check("deliverable PDF present and non-trivial", ok,
          "" if ok else f"missing or too small: output/{slug}.pdf")


def check_title_one_page(slug, p):
    # A title page whose fixed spacing overflows its paper does NOT raise an
    # overfull box: \end{titlepage} silently flows the excess onto a second page,
    # which then inherits the running header (an orphan). The structural signal:
    # the cover is page 1, so the Contents heading must fall on page 2. If the
    # title page spills, page 2 is the orphan and Contents slides to page 3.
    if not os.path.exists(p["pdf"]):
        skip("title page is one page", "PDF not found; run build.py first")
        return
    if not shutil.which("pdftotext"):
        skip("title page is one page", "pdftotext not available")
        return
    try:
        p2 = subprocess.run(["pdftotext", "-f", "2", "-l", "2", p["pdf"], "-"],
                            capture_output=True, text=True).stdout
    except Exception as e:
        skip("title page is one page", f"pdftotext failed ({e})")
        return
    ok = ("Contents" in p2) and ("Cover" in p2)
    check("title page is one page; Contents on p2", ok,
          "" if ok else "page 2 is not the Contents page (title page overflowed)")


def check_language_variant(slug, lang):
    """Build invariants for one translated edition. The no-dash rule still holds
    and the charset is ASCII plus known Latin diacritics (so a stray smart quote
    or exotic codepoint is caught); once built, the PDF is real, within the page
    ceiling, free of overfull boxes, and keeps its title page to one page,
    verified with this edition's own words for Cover and Contents.
    """
    lp = C.language_paths(slug, lang)
    code = lp["code"]
    t = f"[{code}] "
    if not os.path.exists(lp["manuscript"]):
        check(t + "manuscript present", False,
              f"missing: {os.path.basename(lp['manuscript'])}")
        return
    md = open(lp["manuscript"], encoding="utf-8").read()
    check(t + "no em-dash (U+2014) in manuscript", "\u2014" not in md)
    check(t + "no en-dash (U+2013) in manuscript", "\u2013" not in md)
    smart = sorted({c for c in md if c in "\u2018\u2019\u201c\u201d"})
    check(t + "no curly/smart quotes in manuscript", not smart,
          "found: " + " ".join(smart) if smart else "")
    exotic = sorted({c for c in md if ord(c) > 127 and c not in C.LATIN_DIACRITICS})
    check(t + "manuscript is ASCII + known diacritics only", not exotic,
          "unexpected: " + " ".join(exotic) if exotic else "")

    # Overfull boxes from this edition's own latexmk log.
    if os.path.exists(lp["latexmk_log"]):
        ltext = open(lp["latexmk_log"], encoding="utf-8", errors="ignore").read()
        n_over = ltext.count("Overfull \\hbox")
        check(t + "no overfull hboxes in build log", n_over == 0, f"{n_over} found")
    else:
        skip(t + "overfull-hbox check", "build log not found; run build.py first")

    if not os.path.exists(lp["pdf"]):
        skip(t + "PDF checks", "not built yet; run build.py first")
        return
    ok = os.path.getsize(lp["pdf"]) > 50_000
    check(t + "deliverable PDF present and non-trivial", ok,
          "" if ok else f"missing or too small: output/{slug}-{code}.pdf")
    ceiling = C.page_ceiling(slug)
    pages = C.pdf_pages(lp["pdf"])
    if pages is None:
        skip(t + "page-count check", "could not read PDF")
    else:
        check(t + f"page count within the {ceiling}-page ceiling",
              1 <= pages <= ceiling, f"{pages} pages")

    # Title page is one page, checked with this edition's Cover/Contents words.
    cover_word = lang.get("cover_word", "Cover")
    contents_word = lang.get("contents_word", "Contents")
    if not shutil.which("pdftotext"):
        skip(t + "title page is one page", "pdftotext not available")
        return
    try:
        p2 = subprocess.run(["pdftotext", "-f", "2", "-l", "2", lp["pdf"], "-"],
                            capture_output=True, text=True).stdout
    except Exception as e:
        skip(t + "title page is one page", f"pdftotext failed ({e})")
        return
    ok = (contents_word in p2) and (cover_word in p2)
    check(t + f"title page is one page; {contents_word} on p2", ok,
          "" if ok else f"page 2 lacks '{contents_word}'/'{cover_word}' (title page overflowed?)")


def check_recovery_archive():
    # The bundle must always carry a snapshot of itself (recovery.zip), so the
    # base files are always recoverable from inside the tree. Gated on at least
    # one PDF existing, like the other post-build checks.
    archive = os.path.join(C.ROOT, "recovery.zip")
    any_pdf = any(os.path.exists(C.book_paths(s)["pdf"]) for s in C.discover_books())
    if not any_pdf:
        skip("recovery archive present", "no PDFs yet; run build.py first")
        return
    if os.path.exists(archive):
        asize = os.path.getsize(archive)
        check("recovery archive present and non-trivial", asize > 50_000,
              f"recovery.zip, {asize:,} bytes")
    else:
        check("recovery archive present and non-trivial", False,
              "recovery.zip not found; build.py should maintain it")


def main():
    wanted = sys.argv[1:]
    books = C.discover_books()
    if wanted:
        unknown = [s for s in wanted if s not in books]
        if unknown:
            print("unknown book(s): " + ", ".join(unknown))
            print("available: " + ", ".join(books))
            sys.exit(2)
        books = wanted

    if not books:
        print("no books found under books/*/book.toml")
        sys.exit(2)

    print("=" * 70)
    print("BUILD INVARIANTS  ::  " + ", ".join(books))
    print("=" * 70)

    for slug in books:
        p = C.book_paths(slug)
        print(f"\n[{slug}]  (tag {C.compose_tag(slug)})")
        if not os.path.exists(p["manuscript"]):
            check("manuscript.md present", False, f"missing: books/{slug}/manuscript.md")
            continue
        check_manuscript_ascii_and_dashes(slug, p)
        check_tex_sources_no_dashes(slug, p)
        check_version_wired(slug, p)
        check_overfull(slug, p)
        check_page_ceiling(slug, p)
        check_deliverable(slug, p)
        check_title_one_page(slug, p)
        for lang in C.book_languages(slug):
            check_language_variant(slug, lang)

    print("\n[press]")
    check_recovery_archive()

    print()
    if fails:
        print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
        sys.exit(1)
    print("all build-invariant checks passed")


if __name__ == "__main__":
    main()
