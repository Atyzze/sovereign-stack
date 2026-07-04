#!/usr/bin/env python3
"""Sovereign Press - build orchestrator.

One command builds every book in the press, or just the ones you name, and it is
incremental: each book's PDF is rebuilt only when something that affects it has
actually changed. So editing one manuscript rebuilds one PDF; editing the shared
preamble rebuilds all of them; rerunning with nothing changed rebuilds nothing.

How "changed" is decided. For each book, build.py hashes every input that can
affect its PDF: the book's manuscript.md, its book.toml, its frontmatter.tex, and
every file in its assets/, plus the shared machinery (the preamble, the
preprocessor, the version composer, press.toml, and the shared cover art). That
combined hash is stored in output/.build-state.json next to the PDF. On the next
run, if the hash matches and the PDF is still present and non-trivial, the book is
skipped; otherwise it is rebuilt and the hash is updated. `--force` rebuilds
regardless.

Auto-iteration. A book's iteration number is bumped for you the moment its
manuscript.md changes. build.py keeps a separate hash of that one file in the
build state; when a rebuild finds the manuscript's bytes have moved since the
last successful build, it increments `iteration` in that book's book.toml before
composing the tag, so the version number tracks real edits with no manual step.
It is keyed on the manuscript alone, so editing an asset or the shared preamble
rebuilds a book without inflating its iteration; only its own manuscript does.
The first time a book is seen (no stored manuscript hash) is the baseline: its
hash is recorded, not bumped. `build.py bump` still works for a manual bump.

Pipeline per book (only when a rebuild is needed):
  0. version  : compose v{vol}v{ver}i{iter} from book.toml -> temp/<slug>/version.tex
  1. figures  : assets/*.svg -> temp/<slug>/figures/*.pdf (shared/render_svgs.py; content-hash fresh)
  2. preprocess: manuscript.md -> temp/<slug>/body.md (shared/preprocess.py)
  3. pandoc    : body.md -> temp/<slug>/<slug>.tex (shared preamble + this book's title page inlined)
  4. xelatex   : -> temp/<slug>/<slug>.pdf, then moved to output/<slug>.pdf
Every byproduct stays under temp/<slug>/ (with build.log, the run transcript).

Commands:
  python3 build.py                      build every enabled book (incremental)
  python3 build.py <slug> [<slug>...]   build only the named book(s) (incremental)
  python3 build.py --force [targets]    rebuild even if nothing changed
  python3 build.py list                 show every book: tag, enabled, up-to-date?
  python3 build.py clean                show temp/ by size, then remove it
  python3 build.py bump <slug>          increment that book's iteration by hand
                                        (a manuscript edit already bumps it for you)
  python3 build.py snapshot             refresh recovery.zip (all sources + PDFs)

Requires: python3 (stdlib only), pandoc, TeX Live (xelatex + latexmk), and the
fonts TeX Gyre Pagella, TeX Gyre Heros, DejaVu Sans Mono.
"""
import datetime as _dt
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
# The three top-level folders never change: src (all source code, including the
# books/ manuscripts), temp (regenerable build artifacts), output (finished PDFs).
SRC_DIR = os.path.join(ROOT, "src")
BOOKS_DIR = os.path.join(SRC_DIR, "books")
TEMP_DIR = os.path.join(ROOT, "temp")
OUTPUT_DIR = os.path.join(ROOT, "output")
SHARED = os.path.join(SRC_DIR, "shared")
TESTS_DIR = os.path.join(SRC_DIR, "tests")
STATE_PATH = os.path.join(OUTPUT_DIR, ".build-state.json")
ARCHIVE = os.path.join(ROOT, "recovery.zip")

# Bump when the *build recipe* (the pandoc/xelatex invocation below) changes in a
# way that should force every book to rebuild. Content/asset/preamble changes are
# detected automatically; this is only for changes to build.py's own logic.
RECIPE_VERSION = "4"   # 4: per-book language variants ([[language]]) each build a second PDF

sys.path.insert(0, SHARED)
import preprocess as _preprocess          # noqa: E402
import mkversion as _mkversion            # noqa: E402
import render_svgs as _render_svgs        # noqa: E402

try:
    import tomllib
except ModuleNotFoundError:               # pragma: no cover
    tomllib = None


# --------------------------------------------------------------------------- #
# config + discovery
# --------------------------------------------------------------------------- #
def _load_toml(path):
    if tomllib is not None and os.path.exists(path):
        with open(path, "rb") as fh:
            return tomllib.load(fh)
    return {}


def load_press():
    return _load_toml(os.path.join(ROOT, "press.toml"))


def discover_books():
    """Every folder under src/books/ that has a book.toml, ordered by press.toml."""
    found = []
    if os.path.isdir(BOOKS_DIR):
        for name in os.listdir(BOOKS_DIR):
            if os.path.exists(os.path.join(BOOKS_DIR, name, "book.toml")):
                found.append(name)
    order = load_press().get("order", {}).get("books", [])
    ordered = [s for s in order if s in found]
    ordered += sorted(s for s in found if s not in order)
    return ordered


def book_meta(slug):
    """A book's merged settings: project + version + build defaults overlaid."""
    bdir = os.path.join(BOOKS_DIR, slug)
    data = _load_toml(os.path.join(bdir, "book.toml"))
    defaults = load_press().get("defaults", {})
    build = dict(defaults)
    build.update(data.get("build", {}))
    proj = data.get("project", {})
    return {
        "slug": slug,
        "dir": bdir,
        "title": proj.get("title", slug),
        "enabled": proj.get("enabled", True),
        "build": build,
    }


def book_languages(slug):
    """Extra language editions declared in a book's book.toml as [[language]].

    Each is a dict with at least ``code`` and ``manuscript``; optional keys are
    ``frontmatter``, ``lang`` (pandoc hyphenation, e.g. "nl-NL"), ``book_short``
    / ``series_short`` (running-header overrides), and the [preprocess]-shaped
    ``start_marker`` / ``promote_to_chapter`` for the translated source. Absent
    or empty => the book builds only its default manuscript, exactly as before.
    """
    data = _load_toml(os.path.join(BOOKS_DIR, slug, "book.toml"))
    langs = data.get("language", [])
    return [l for l in langs if l.get("code") and l.get("manuscript")]


def expected_pdfs(slug):
    """Every PDF a full build of this book should leave in output/: the default
    edition (<slug>.pdf) plus one per language variant (<slug>-<CODE>.pdf)."""
    pdfs = [f"{slug}.pdf"]
    pdfs += [f"{slug}-{l['code']}.pdf" for l in book_languages(slug)]
    return pdfs


# --------------------------------------------------------------------------- #
# hashing
# --------------------------------------------------------------------------- #
def _hash_files(paths):
    """Deterministic hash of a set of files by (relpath-to-ROOT, bytes)."""
    h = hashlib.sha256()
    for p in sorted(paths, key=lambda x: os.path.relpath(x, ROOT)):
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        with open(p, "rb") as fh:
            h.update(fh.read())
        h.update(b"\0")
    return h.hexdigest()


def _walk(dir_path):
    out = []
    for base, _dirs, files in os.walk(dir_path):
        if "__pycache__" in base:
            continue
        for f in files:
            if f == ".DS_Store":
                continue
            out.append(os.path.join(base, f))
    return out


def shared_inputs():
    paths = [
        os.path.join(SHARED, "preamble.tex"),
        os.path.join(SHARED, "preprocess.py"),
        os.path.join(SHARED, "mkversion.py"),
        os.path.join(SHARED, "render_svgs.py"),
        os.path.join(ROOT, "press.toml"),
    ]
    paths += _walk(os.path.join(SHARED, "assets"))
    return [p for p in paths if os.path.exists(p)]


def input_hash(slug):
    """The combined hash that decides whether a book needs rebuilding."""
    bdir = os.path.join(BOOKS_DIR, slug)
    book_files = [
        os.path.join(bdir, "manuscript.md"),
        os.path.join(bdir, "book.toml"),
        os.path.join(bdir, "frontmatter.tex"),
    ]
    # Language variants: their translated manuscript and (optional) title page
    # are inputs too, so editing a translation re-fingerprints and rebuilds its
    # PDF, while leaving the default edition's hash unchanged.
    for lang in book_languages(slug):
        book_files.append(os.path.join(bdir, lang["manuscript"]))
        if lang.get("frontmatter"):
            book_files.append(os.path.join(bdir, lang["frontmatter"]))
    book_files += _walk(os.path.join(bdir, "assets"))
    book_files = [p for p in book_files if os.path.exists(p)]
    combined = RECIPE_VERSION + "|" + _hash_files(shared_inputs()) + "|" + _hash_files(book_files)
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def manuscript_hash(slug):
    """SHA-256 of a book's manuscript.md alone, or None if it is missing.

    This is deliberately narrower than input_hash: it tracks only the one file
    whose change should bump the iteration, so editing an asset or the shared
    preamble (which input_hash covers) never inflates a book's iteration.
    """
    p = os.path.join(BOOKS_DIR, slug, "manuscript.md")
    if not os.path.exists(p):
        return None
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def bump_iteration_file(toml_path):
    """Increment the `iteration = N` line in a book.toml in place.

    Returns the new integer, or None if the file has no such line. Shared by the
    manual `bump` command and the automatic manuscript-changed bump, so both
    spell the edit exactly the same way.
    """
    if not os.path.exists(toml_path):
        return None
    txt = open(toml_path, encoding="utf-8").read()
    m = re.search(r"(?m)^(\s*iteration\s*=\s*)(\d+)", txt)
    if not m:
        return None
    new = int(m.group(2)) + 1
    txt = txt[:m.start()] + m.group(1) + str(new) + txt[m.end():]
    with open(toml_path, "w", encoding="utf-8") as fh:
        fh.write(txt)
    return new


# --------------------------------------------------------------------------- #
# state
# --------------------------------------------------------------------------- #
def load_state():
    if os.path.exists(STATE_PATH):
        try:
            return json.load(open(STATE_PATH, encoding="utf-8"))
        except Exception:
            pass
    return {"recipe": RECIPE_VERSION, "books": {}}


def save_state(state):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")


def is_up_to_date(slug, state):
    rec = state.get("books", {}).get(slug)
    if not rec:
        return False
    # Every edition this book should produce must be present and non-trivial;
    # a missing language PDF alone forces a rebuild.
    for name in expected_pdfs(slug):
        pdf = os.path.join(OUTPUT_DIR, name)
        if not (os.path.exists(pdf) and os.path.getsize(pdf) > 50_000):
            return False
    return rec.get("input_hash") == input_hash(slug)


# --------------------------------------------------------------------------- #
# build one book
# --------------------------------------------------------------------------- #
def _run(cmd, log, cwd=ROOT, env=None):
    """Run a command, streaming to stdout and appending to the log file."""
    with open(log, "a", encoding="utf-8") as lf:
        lf.write("\n$ " + " ".join(cmd) + "\n")
        lf.flush()
        proc = subprocess.run(cmd, cwd=cwd, env=env,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True)
        sys.stdout.write(proc.stdout)
        lf.write(proc.stdout)
    return proc.returncode


def _render_edition(slug, meta, bld, log, *, manuscript, frontmatter, cfg,
                    out_basename, tag, runhead, lang=None):
    """Steps 0/2/3/4 for one edition: write its version.tex, clean its source,
    run pandoc then xelatex, and move the finished PDF to output/<out_basename>.pdf.

    Returns (ok, size_bytes). Figures (step 1) are rendered once by build_book
    before any edition and shared by all of them. Each edition writes version.tex
    fresh (so its running-header label is this edition's), and uses its own body
    and .tex filenames under temp/<slug>/, so the default and the translations
    never clobber one another.
    """
    bdir = meta["dir"]
    b = meta["build"]

    # 0. version.tex (shared tag; this edition's running-header label)
    with open(os.path.join(bld, "version.tex"), "w", encoding="utf-8") as fh:
        fh.write("%% generated by build.py; do not edit by hand\n")
        fh.write("\\def\\ssversion{%s}\n" % tag)
        fh.write("\\def\\ssrunhead{%s}\n" % runhead)

    # 2. preprocess this edition's manuscript
    body = os.path.join(bld, f"{out_basename}.body.md")
    stats = _preprocess.run(bdir, body, manuscript=manuscript, cfg=cfg)
    print(f"  [2/4] preprocess ({manuscript}) -> {os.path.basename(body)} "
          f"({stats['lines']} lines, {stats['chapters']} chapters)")
    if stats["dash"]:
        print("  WARNING: an em/en dash survived preprocessing")

    # 3. pandoc -> .tex
    tex = os.path.join(bld, f"{out_basename}.tex")
    preamble = os.path.join(SHARED, "preamble.tex")
    pandoc_cmd = [
        "pandoc", body,
        "-f", "markdown+autolink_bare_uris", "-t", "latex", "-s",
        "--top-level-division=" + b.get("toplevel", "chapter"), "--listings",
        "-V", "documentclass=report", "-V", "classoption=oneside",
        "-V", "classoption=11pt", "-V", "classoption=" + b.get("paper", "a4paper"),
        "-V", "mainfont=" + b.get("mainfont", "TeX Gyre Pagella"),
        "-V", "sansfont=" + b.get("sansfont", "TeX Gyre Heros"),
        "-V", "monofont=" + b.get("monofont", "DejaVu Sans Mono"),
        "-V", "colorlinks=true", "-V", "linkcolor=black",
        "-V", "urlcolor=blue", "-V", "toccolor=black",
        "-H", preamble,
    ]
    if lang:                                   # Dutch hyphenation, etc.
        pandoc_cmd += ["-V", "lang=" + lang]
    if frontmatter and os.path.exists(frontmatter):
        pandoc_cmd += ["--include-before-body=" + frontmatter]
    pandoc_cmd += ["-o", tex]
    print("  [3/4] pandoc -> %s.tex" % out_basename)
    if _run(pandoc_cmd, log) != 0:
        print(f"  ERROR: pandoc failed for {out_basename}; see {log}")
        return (False, 0)

    # 4. xelatex -> .pdf. version.tex and images are found via TEXINPUTS.
    texinputs = ":".join([
        bld + "//",
        os.path.join(bdir, "assets") + "//",
        os.path.join(SHARED, "assets") + "//",
        "",                                   # trailing empty => append defaults
    ])
    env = dict(os.environ, TEXINPUTS=texinputs)
    print("  [4/4] xelatex -> %s.pdf" % out_basename)
    rc = _run(["latexmk", "-xelatex", "-gg", "-interaction=nonstopmode",
               "-halt-on-error", "-output-directory=" + bld, tex], log, env=env)
    built = os.path.join(bld, f"{out_basename}.pdf")
    if rc != 0 or not os.path.exists(built):
        print(f"  ERROR: xelatex failed for {out_basename}; tail of {log}:")
        _print_log_tail(log)
        return (False, 0)

    out_pdf = os.path.join(OUTPUT_DIR, f"{out_basename}.pdf")
    shutil.move(built, out_pdf)
    size = os.path.getsize(out_pdf)
    if size < 50_000:
        print(f"  ERROR: {out_basename}.pdf is implausibly small ({size} bytes)")
        return (False, 0)
    print(f"  -> output/{out_basename}.pdf  ({size:,} bytes)")
    return (True, size)


def build_book(slug, state, force=False):
    meta = book_meta(slug)
    bdir = meta["dir"]

    if not force and is_up_to_date(slug, state):
        print(f"[skip] {slug}: up to date ({state['books'][slug]['tag']})")
        return "skip"

    bld = os.path.join(TEMP_DIR, slug)
    os.makedirs(bld, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    log = os.path.join(bld, "build.log")
    open(log, "w").close()  # fresh log per build

    # Auto-iteration: bump before composing the tag, so the version number this
    # build stamps reflects the edit that triggered it. Fire only when this
    # book's manuscript.md has actually changed since its last successful build
    # (a stored hash exists and differs). It is keyed on manuscript.md alone, so
    # editing a *translation* rebuilds that language's PDF (via input_hash)
    # without inflating the shared version number. The first sighting seeds the
    # hash without bumping.
    mhash = manuscript_hash(slug)
    prev_mhash = state.get("books", {}).get(slug, {}).get("manuscript_hash")
    if prev_mhash and mhash and prev_mhash != mhash:
        newit = bump_iteration_file(os.path.join(bdir, "book.toml"))
        if newit is not None:
            print(f"  manuscript changed since last build; iteration -> {newit}")

    tag, runhead = _mkversion.compose(bdir)
    langs = book_languages(slug)
    extra = f" (+{len(langs)} language edition{'s' if len(langs) != 1 else ''})" if langs else ""
    print(f"[build] {slug}  tag {tag}{extra}")

    # 1. figures: rendered once, shared by every edition of this book
    figs = _render_svgs.run(os.path.join(bdir, "assets"),
                            os.path.join(bld, "figures"),
                            log=lambda m: print("        " + m))
    fig_note = f"{figs['rendered']} rendered, {figs['fresh']} fresh"
    if figs["stale_kept"]:
        fig_note += f", {figs['stale_kept']} stale kept"
    if figs["pruned"]:
        fig_note += f", {figs['pruned']} pruned"
    print(f"  [1/4] figures    -> {fig_note}")
    for e in figs["errors"]:
        print("  ERROR: " + e)
    if figs["errors"]:
        return "fail"

    pdfs = {}

    # default edition: manuscript.md, [preprocess], frontmatter.tex, no lang tag
    print(f"  edition: default -> {slug}.pdf")
    ok, size = _render_edition(
        slug, meta, bld, log,
        manuscript="manuscript.md",
        frontmatter=os.path.join(bdir, "frontmatter.tex"),
        cfg=None,                       # None => preprocess reads [preprocess]
        out_basename=slug, tag=tag, runhead=runhead, lang=None)
    if not ok:
        return "fail"
    pdfs[f"{slug}.pdf"] = size

    # one further edition per [[language]] entry
    for lc in langs:
        code = lc["code"]
        out_basename = f"{slug}-{code}"
        print(f"  edition: {code} -> {out_basename}.pdf")
        _t, lang_runhead = _mkversion.compose(
            bdir, series_short=lc.get("series_short"), book_short=lc.get("book_short"))
        fm = lc.get("frontmatter")
        fm_path = os.path.join(bdir, fm) if fm else os.path.join(bdir, "frontmatter.tex")
        pre_cfg = {
            "start_marker": lc.get("start_marker", ""),
            "promote_to_chapter": lc.get("promote_to_chapter", []),
            "drop_thematic_breaks": lc.get("drop_thematic_breaks", True),
            "workbook": lc.get("workbook", False),
        }
        ok, size = _render_edition(
            slug, meta, bld, log,
            manuscript=lc["manuscript"], frontmatter=fm_path, cfg=pre_cfg,
            out_basename=out_basename, tag=tag, runhead=lang_runhead,
            lang=lc.get("lang"))
        if not ok:
            return "fail"
        pdfs[f"{out_basename}.pdf"] = size

    state.setdefault("books", {})[slug] = {
        "input_hash": input_hash(slug),
        "manuscript_hash": mhash,       # baseline for the next auto-iteration check
        "tag": tag,
        "built_at": _dt.datetime.now().isoformat(timespec="seconds"),
        "pdfs": pdfs,                   # {filename: bytes} for every edition built
    }
    return "built"


def _print_log_tail(log, n=25):
    try:
        lines = open(log, encoding="utf-8").read().splitlines()
        for l in lines[-n:]:
            print("    " + l)
    except OSError:
        pass


# --------------------------------------------------------------------------- #
# recovery snapshot
# --------------------------------------------------------------------------- #
def refresh_snapshot():
    """Refresh recovery.zip: every source plus every built PDF, in one file.

    Uses `zip -FS` (file-sync): adds new files, refreshes changed ones, drops
    entries whose files are gone, so the archive is brought into agreement on
    every call. Excludes temp/ and the archive itself.
    """
    if shutil.which("zip") is None:
        print("  (zip not found; skipping recovery snapshot)")
        return
    items = ["press.toml", "build.py", "README.md", "MANIFEST.md", ".gitignore",
             "src"]
    items = [i for i in items if os.path.exists(os.path.join(ROOT, i))]
    # include the finished PDFs (the state file's churn is harmless to include)
    if os.path.isdir(OUTPUT_DIR):
        items.append("output")
    cmd = ["zip", "-FS", "-r", "-q", ARCHIVE, *items,
           "-x", "*/__pycache__/*", "-x", "*/.DS_Store", "-x", "temp/*"]
    subprocess.run(cmd, cwd=ROOT, check=False)
    if os.path.exists(ARCHIVE):
        n = subprocess.run(["unzip", "-l", ARCHIVE], cwd=ROOT,
                          capture_output=True, text=True).stdout.splitlines()
        total = n[-1].split()[1] if n else "?"
        print(f"  recovery.zip refreshed ({total} files; temp/ excluded)")


# --------------------------------------------------------------------------- #
# subcommands
# --------------------------------------------------------------------------- #
def cmd_build(targets, force):
    state = load_state()
    state["recipe"] = RECIPE_VERSION
    if targets:
        slugs = targets
    else:
        slugs = [s for s in discover_books() if book_meta(s)["enabled"]]
    if not slugs:
        print("No books to build.")
        return 0

    results = {}
    for slug in slugs:
        if not os.path.exists(os.path.join(BOOKS_DIR, slug, "book.toml")):
            print(f"[error] no such book: {slug}")
            results[slug] = "fail"
            continue
        results[slug] = build_book(slug, state, force=force)
        save_state(state)

    print("\nSummary:")
    for slug in slugs:
        print(f"  {results.get(slug, '?'):>5}  {slug}")
    refresh_snapshot()
    fails = [s for s, r in results.items() if r == "fail"]
    if fails:
        print(f"\n{len(fails)} book(s) FAILED: {', '.join(fails)}")
        return 1
    print("\nDone. Verify with: python3 src/tests/test_build.py")
    return 0


def cmd_list():
    state = load_state()
    print(f"{'book':32} {'tag':12} {'enabled':8} status")
    print("-" * 64)
    for slug in discover_books():
        meta = book_meta(slug)
        tag, _ = _mkversion.compose(meta["dir"])
        en = "yes" if meta["enabled"] else "no"
        if is_up_to_date(slug, state):
            status = "up to date"
        elif slug in state.get("books", {}):
            status = "STALE (will rebuild)"
        else:
            status = "not built yet"
        print(f"{slug:32} {tag:12} {en:8} {status}")
    return 0


def cmd_clean():
    if os.path.isdir(TEMP_DIR) and os.listdir(TEMP_DIR):
        print("temp/ currently holds (largest first):")
        subprocess.run("du -ah temp | sort -rh", cwd=ROOT, shell=True)
        shutil.rmtree(TEMP_DIR)
        print("Cleared temp/ (recreated on the next build).")
    else:
        print("temp/ is empty or absent; nothing to clear.")
    return 0


def cmd_bump(slug):
    path = os.path.join(BOOKS_DIR, slug, "book.toml")
    if not os.path.exists(path):
        print(f"no such book: {slug}")
        return 2
    new = bump_iteration_file(path)
    if new is None:
        print("could not find an 'iteration = N' line in book.toml")
        return 2
    print(f"{slug}: iteration -> {new}")
    return 0


def main(argv):
    args = argv[1:]
    force = False
    if "--force" in args:
        force = True
        args.remove("--force")
    if "-f" in args:
        force = True
        args.remove("-f")

    if not args:
        return cmd_build([], force)
    cmd = args[0]
    if cmd == "build":
        return cmd_build(args[1:], force)
    if cmd == "list":
        return cmd_list()
    if cmd == "clean":
        return cmd_clean()
    if cmd == "bump":
        if len(args) != 2:
            print("usage: python3 build.py bump <slug>")
            return 2
        return cmd_bump(args[1])
    if cmd == "snapshot":
        refresh_snapshot()
        return 0
    # otherwise treat all args as book slugs to build
    return cmd_build(args, force)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
