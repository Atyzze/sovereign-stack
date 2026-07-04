#!/usr/bin/env python3
"""render_svgs.py -- render hand-authored figure sources to embeddable PDFs.

Each book keeps vector figures in its assets/ directory as .svg files: the
only figure files under src/, the hand-authored, editable sources. The
renders the manuscript embeds (\\includegraphics{fig_x.pdf}) are build
byproducts and live under temp/<slug>/figures/, where xelatex finds them via
TEXINPUTS; they are never committed and never enter a zip.

Freshness is decided by content, not clocks: a SHA-256 of each .svg is kept
in temp/<slug>/figures/.hashes.json, and a figure is (re)rendered exactly
when its .pdf is missing or its source bytes changed. Editing an .svg is
therefore always enough; touching a file, or extracting a zip with scrambled
timestamps, never triggers or suppresses anything. A render whose source was
deleted is pruned.

Rendering needs cairosvg (``pip install cairosvg``); a book with .svg assets
cannot build without it. Used by build.py as the first step of every book
build; also runnable standalone:

    python3 src/shared/render_svgs.py                 # every book
    python3 src/shared/render_svgs.py atlas-home-node # one book
"""

import argparse
import glob
import hashlib
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_BOOKS = os.path.join(_ROOT, "src", "books")
_TEMP = os.path.join(_ROOT, "temp")


def _cairosvg():
    """Import cairosvg lazily; return the module or None."""
    try:
        import cairosvg  # noqa: PLC0415 (deliberate lazy import)
        return cairosvg
    except ImportError:
        return None


def run(assets_dir, out_dir, log=print):
    """Bring out_dir's .pdf renders in step with assets_dir's .svg sources.

    Returns {"rendered": n, "fresh": n, "stale_kept": n, "pruned": n,
    "errors": [msg, ...]}. Errors are reported, not raised; the caller
    decides whether they are fatal.
    """
    res = {"rendered": 0, "fresh": 0, "stale_kept": 0, "pruned": 0, "errors": []}
    svgs = sorted(glob.glob(os.path.join(assets_dir, "*.svg")))
    state_path = os.path.join(out_dir, ".hashes.json")
    state = {}
    if os.path.exists(state_path):
        try:
            state = json.load(open(state_path, encoding="utf-8"))
        except (ValueError, OSError):
            state = {}
    if not svgs:
        return res
    os.makedirs(out_dir, exist_ok=True)

    svg2pdf = _cairosvg()
    dirty = False
    names = set()
    for svg in svgs:
        name = os.path.basename(svg)[:-4]
        names.add(name)
        pdf = os.path.join(out_dir, name + ".pdf")
        digest = hashlib.sha256(open(svg, "rb").read()).hexdigest()
        have = os.path.exists(pdf)

        if have and state.get(name) == digest:
            res["fresh"] += 1
            continue

        if svg2pdf is None:
            if have:  # source changed but a usable render exists: warn, keep
                res["stale_kept"] += 1
                log(f"WARNING: {name}.svg changed but cairosvg is not "
                    f"installed; building with the previous render")
            else:
                res["errors"].append(
                    f"{name}.svg has no render and cairosvg is not installed "
                    f"(pip install cairosvg)")
            continue

        try:
            svg2pdf.svg2pdf(url=svg, write_to=pdf)
            state[name] = digest
            dirty = True
            res["rendered"] += 1
        except Exception as exc:  # a broken SVG should name itself clearly
            res["errors"].append(f"{name}.svg failed to render: {exc}")

    # prune renders whose source is gone
    for pdf in glob.glob(os.path.join(out_dir, "*.pdf")):
        name = os.path.basename(pdf)[:-4]
        if name not in names:
            os.remove(pdf)
            state.pop(name, None)
            dirty = True
            res["pruned"] += 1

    if dirty:
        with open(state_path, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1, sort_keys=True)
    return res


def book_dirs(slug):
    return (os.path.join(_BOOKS, slug, "assets"),
            os.path.join(_TEMP, slug, "figures"))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Render figure .svg sources to their temp/ .pdf renders.")
    ap.add_argument("slugs", nargs="*",
                    help="book slugs (default: every book under src/books)")
    args = ap.parse_args(argv)

    slugs = args.slugs or sorted(
        d for d in os.listdir(_BOOKS)
        if os.path.isdir(os.path.join(_BOOKS, d, "assets")))
    failed = False
    for slug in slugs:
        assets, out = book_dirs(slug)
        if not os.path.isdir(assets):
            print(f"[skip] {slug}: no assets directory")
            continue
        res = run(assets, out, log=lambda m: print("  " + m))
        total = res["rendered"] + res["fresh"] + res["stale_kept"]
        if total or res["errors"] or res["pruned"]:
            note = f"{res['rendered']} rendered, {res['fresh']} fresh"
            if res["stale_kept"]:
                note += f", {res['stale_kept']} stale kept"
            if res["pruned"]:
                note += f", {res['pruned']} pruned"
            print(f"[{slug}] {note} -> {out}")
        for e in res["errors"]:
            print("  ERROR: " + e)
            failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
