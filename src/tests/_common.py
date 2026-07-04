#!/usr/bin/env python3
"""Shared helpers for the Sovereign Press test suite.

Both test_build.py and test_review.py are multi-book: they discover every book
under src/books/ (any folder with a book.toml), exactly the way build.py does, and
run their checks once per book. This module holds the small amount of logic they
share: locating the tree, loading press.toml and each book.toml, listing a
book's files, and composing the version tag a book should carry. Keeping it here
means the two suites cannot drift apart on what counts as a book or how a tag is
spelled.
"""
import os
import re

try:
    import tomllib
except ModuleNotFoundError:                       # pragma: no cover
    tomllib = None

# This file lives at src/tests/_common.py, so the press root is two levels up.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BOOKS_DIR = os.path.join(ROOT, "src", "books")
SHARED = os.path.join(ROOT, "src", "shared")
OUTPUT_DIR = os.path.join(ROOT, "output")
TEMP_DIR = os.path.join(ROOT, "temp")

# Characters a *translated* manuscript may use beyond ASCII: the accented Latin
# letters Western-European languages need. Both suites hold the default English
# manuscript to strict ASCII, but hold a language variant to "ASCII + this set"
# instead, so Dutch keeps its diacritics while stray smart quotes, dashes, and
# other exotic codepoints are still caught (they fall outside the set).
LATIN_DIACRITICS = set(
    "àáâãäåæçèéêëìíîïñòóôõöøùúûüýÿ"
    "ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÑÒÓÔÕÖØÙÚÛÜÝ"
    "\u0133\u0132"  # ij / IJ digraph, if a source ever uses the single-char form
)


def load_toml(path):
    if tomllib is not None and os.path.exists(path):
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    return {}


def press():
    return load_toml(os.path.join(ROOT, "press.toml"))


def defaults():
    return press().get("defaults", {})


def discover_books():
    """Every folder under src/books/ with a book.toml, ordered by press.toml [order]."""
    found = []
    if os.path.isdir(BOOKS_DIR):
        for name in sorted(os.listdir(BOOKS_DIR)):
            if os.path.exists(os.path.join(BOOKS_DIR, name, "book.toml")):
                found.append(name)
    order = press().get("order", {}).get("books", [])
    ordered = [s for s in order if s in found]
    ordered += [s for s in found if s not in order]
    return ordered


def book_toml(slug):
    return load_toml(os.path.join(BOOKS_DIR, slug, "book.toml"))


def compose_tag(slug):
    """The version tag a book should carry: v{volume}v{version}i{iteration}."""
    v = book_toml(slug).get("version", {})
    vol = v.get("volume", 0)
    ver = v.get("version", 0)
    it = v.get("iteration", 0)
    return f"v{vol}v{ver}i{it}"


def book_paths(slug):
    """The conventional files for a book (those that exist)."""
    bdir = os.path.join(BOOKS_DIR, slug)
    p = {
        "dir": bdir,
        "manuscript": os.path.join(bdir, "manuscript.md"),
        "frontmatter": os.path.join(bdir, "frontmatter.tex"),
        "book_toml": os.path.join(bdir, "book.toml"),
        "assets": os.path.join(bdir, "assets"),
        "pdf": os.path.join(OUTPUT_DIR, f"{slug}.pdf"),
        "latexmk_log": os.path.join(TEMP_DIR, slug, f"{slug}.log"),
        "version_tex": os.path.join(TEMP_DIR, slug, "version.tex"),
    }
    return p


def page_ceiling(slug):
    """Universal ceiling from press.toml [defaults], overridable per book."""
    base = defaults().get("page_ceiling", 400)
    return book_toml(slug).get("build", {}).get("page_ceiling", base)


def book_languages(slug):
    """The [[language]] editions declared in a book's book.toml (may be empty).

    Each is a dict with at least ``code`` and ``manuscript``; both suites check
    every one alongside the default edition. Mirrors build.book_languages so the
    tests and the build agree on what a language edition is.
    """
    langs = book_toml(slug).get("language", [])
    return [l for l in langs if l.get("code") and l.get("manuscript")]


def language_paths(slug, lang):
    """The source files, output PDF, and log for one language edition."""
    bdir = os.path.join(BOOKS_DIR, slug)
    code = lang["code"]
    fm = lang.get("frontmatter")
    return {
        "code": code,
        "manuscript": os.path.join(bdir, lang["manuscript"]),
        "frontmatter": os.path.join(bdir, fm) if fm else os.path.join(bdir, "frontmatter.tex"),
        "pdf": os.path.join(OUTPUT_DIR, f"{slug}-{code}.pdf"),
        "latexmk_log": os.path.join(TEMP_DIR, slug, f"{slug}-{code}.log"),
    }


def list_assets(slug):
    a = book_paths(slug)["assets"]
    return sorted(os.listdir(a)) if os.path.isdir(a) else []


def pdf_pages(pdf_path):
    """Page count via pdfinfo, or None if it cannot be read."""
    import subprocess
    try:
        info = subprocess.run(["pdfinfo", pdf_path],
                              capture_output=True, text=True).stdout
        return int(next(l.split()[1] for l in info.splitlines()
                        if l.startswith("Pages")))
    except Exception:
        return None
