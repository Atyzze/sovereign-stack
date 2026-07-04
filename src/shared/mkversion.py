#!/usr/bin/env python3
"""Compose the version tag (and running-header label) for a book.

The tag is ``v{volume}v{version}i{iteration}``. In the old single-book press all
three numbers were inferred from the name of the one project folder; that cannot
work once several books live side by side, so each book now owns its three
numbers explicitly in book.toml:

    [version]
    volume    = 1   # which volume of this book's line (fixed for the book)
    version   = 1   # 1 = "not yet shared"; bump on an external share
    iteration = 48  # working iteration; bump on a real edit (or: build.py bump)

build.py reads this, writes the tag into temp/<slug>/version.tex (which the
shared preamble \\input's), and stamps it into the build state. The build itself
never edits book.toml, so a build is pure and repeatable; bumping the iteration
is a one-line edit, or `python3 build.py bump <slug>`.

Standard library only (tomllib on 3.11+, with a tiny regex fallback otherwise).
"""
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


def _read_book_toml(book_dir):
    path = os.path.join(book_dir, "book.toml")
    if tomllib is not None and os.path.exists(path):
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    # fallback: pull the few integers/strings we need by regex
    data = {"version": {}, "project": {}}
    if os.path.exists(path):
        txt = open(path, encoding="utf-8").read()
        for key in ("volume", "version", "iteration"):
            m = re.search(rf"(?m)^\s*{key}\s*=\s*(\d+)", txt)
            if m:
                data["version"][key] = int(m.group(1))
        for key in ("series_short", "book_short"):
            m = re.search(rf'(?m)^\s*{key}\s*=\s*"([^"]*)"', txt)
            if m:
                data["project"][key] = m.group(1)
    return data


def compose(book_dir, series_short=None, book_short=None):
    """Return (tag, runhead_latex) for the book in book_dir.

    The tag is always the book's own ``v{vol}v{ver}i{iter}`` from book.toml, so
    a language variant carries the *same* version as the edition it is a
    translation of. Only the running-header labels may be overridden per
    variant (e.g. "ATLAS / DEEL 1" in place of "ATLAS / VOL 1"); pass
    ``series_short`` / ``book_short`` to do so, or leave them None to use the
    book.toml [project] values.
    """
    data = _read_book_toml(book_dir)
    v = data.get("version", {})
    vol = int(v.get("volume", 1))
    ver = int(v.get("version", 1))
    it = int(v.get("iteration", 0))
    tag = f"v{vol}v{ver}i{it}"

    proj = data.get("project", {})
    series = series_short if series_short is not None else proj.get("series_short", "SOVEREIGN STACK")
    short = book_short if book_short is not None else proj.get("book_short", "")
    # ASCII-only running header (the no-Unicode rule applies to generated .tex too).
    if short:
        runhead = (r"\color{accent}\textbf{%s}\;\color{rulegray}\textbar\;"
                   r"\color{accentlt}\textbf{%s}" % (series, short))
    else:
        runhead = r"\color{accent}\textbf{%s}" % series
    return tag, runhead


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 src/shared/mkversion.py <book-slug>")
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bdir = os.path.join(root, "src", "books", sys.argv[1])
    tag, _ = compose(bdir)
    print(tag)
