#!/usr/bin/env python3
"""Adapt a book's manuscript.md into LaTeX-friendly markdown for pandoc.

This is the generic successor to the old, vol1-specific preprocess.py. The
conventions pandoc alone would mangle are the same for every book, but the
*parameters* (where the body starts, which headings to promote) differ, so they
are read from the book's book.toml [preprocess] block rather than hardcoded:

    [preprocess]
    start_marker        = "## Why this book exists"   # first kept line; the
                                                       # title block above it is
                                                       # the frontmatter's job
    promote_to_chapter  = ["## Why this book exists",  # ## -> # so these become
                           "## How to read this book"] # real chapters
    drop_thematic_breaks = true                        # chapters give structure

If start_marker is empty or absent, nothing is dropped from the top. If
promote_to_chapter is empty, no headings are promoted. Inside code fences any
language hint is stripped (defensive), while raw-output fences (```{=latex}) are
preserved untouched, so the Atlas's TikZ blocks survive.

Usable two ways: imported (build.py calls run()) or standalone for one book:

    python3 shared/preprocess.py atlas-home-node
"""
import os
import re
import sys

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover  (Python < 3.11)
    tomllib = None


def _load_preprocess_cfg(book_dir):
    """Read the [preprocess] block from a book's book.toml, with safe defaults."""
    cfg = {"start_marker": "", "promote_to_chapter": [],
           "drop_thematic_breaks": True, "workbook": False}
    toml_path = os.path.join(book_dir, "book.toml")
    if not os.path.exists(toml_path):
        return cfg
    if tomllib is not None:
        with open(toml_path, "rb") as fh:
            data = tomllib.load(fh)
        pre = data.get("preprocess", {})
        cfg["start_marker"] = pre.get("start_marker", cfg["start_marker"])
        cfg["promote_to_chapter"] = pre.get("promote_to_chapter", cfg["promote_to_chapter"])
        cfg["drop_thematic_breaks"] = pre.get("drop_thematic_breaks", cfg["drop_thematic_breaks"])
        cfg["workbook"] = pre.get("workbook", cfg["workbook"])
    else:  # minimal fallback: regex the two fields we need
        txt = open(toml_path, encoding="utf-8").read()
        m = re.search(r'(?m)^\s*start_marker\s*=\s*"([^"]*)"', txt)
        if m:
            cfg["start_marker"] = m.group(1)
        cfg["workbook"] = bool(re.search(r'(?m)^\s*workbook\s*=\s*true', txt))
    return cfg


# --------------------------------------------------------------------------- #
# workbook mode: a tiny block syntax that becomes the one-concept-per-page layout
# --------------------------------------------------------------------------- #
# A concept is authored as a "### N. Title" heading, a plain-Markdown explanation,
# then up to three fenced blocks:
#
#   ::: tracks                ::: doit                     ::: see
#   linux: whoami             Open the terminal            your account name
#   mac: whoami               Type the word and Enter      :::
#   win: whoami               :::
#   :::
#
# tracks rows are "key: value" (key in linux/mac/win; any other key is a hard
# error). A value beginning with "(note)" becomes an italic note instead of a
# typed command. The tracks box is reserved for exact, platform-specific
# instructions (commands, keys, click-paths); when the thing to type is natural
# language for a search box or an AI chat, the same everywhere, use a
# "::: prompt" block instead, which renders one tinted prompt panel (CAPITALS
# inside it are placeholders the reader replaces). doit lines become a ticked
# checklist (plain Markdown, so they keep bold/code). see is the single
# "You should see" line. Everything else passes through untouched.

_SPECIAL = "&%$#_{}"


def _esc(s):
    """Escape text destined for raw LaTeX (titles, commands, note/see prose base)."""
    # Stash the backslash behind a sentinel first. Escaping it to
    # \textbackslash{} introduces braces, and the brace-escaping loop below
    # would otherwise re-escape those into \{\}, so a literal "\" would render
    # as "\{}" (visible in Windows paths like C:\Users inside a tracks box).
    # Restore it last, once the specials have been handled.
    s = s.replace("\\", "\x00bslash\x00")
    for ch in _SPECIAL:
        s = s.replace(ch, "\\" + ch)
    s = s.replace("~", r"\textasciitilde{}")
    s = s.replace("^", r"\textasciicircum{}")
    s = s.replace("\x00bslash\x00", r"\textbackslash{}")
    return s


def _inline(s):
    """Convert the light Markdown allowed in notes / see lines into LaTeX."""
    codes = []

    def stash(m):
        codes.append(_esc(m.group(1)))
        return f"\x00{len(codes) - 1}\x00"

    s = re.sub(r"`([^`]+)`", stash, s)          # protect code spans first
    s = _esc(s)                                  # escape the rest (keeps * and **)
    s = re.sub(r"\*\*([^*]+)\*\*", r"\\textbf{\1}", s)
    s = re.sub(r"\*([^*]+)\*", r"\\textit{\1}", s)
    s = re.sub("\x00(\\d+)\x00", lambda m: r"\texttt{" + codes[int(m.group(1))] + "}", s)
    return s


_TRACKCMD = {"linux": "tlinux", "mac": "tmac", "win": "twin"}


def _emit_tracks(rows):
    """rows: list of (key, value). Returns one raw-LaTeX fence with a tracks box."""
    out = []
    for key, val in rows:
        cmd = _TRACKCMD.get(key)
        if not cmd:
            raise SystemExit(f"preprocess: unknown track row {key!r} "
                             "(tracks are linux/mac/win only)")
        note = False
        v = val.strip()
        if v.lower().startswith("(note)"):
            note = True
            v = v[len("(note)"):].strip()
        if note:
            out.append(f"\\{cmd}n{{{_inline(v)}}}")
        else:
            out.append(f"\\{cmd}{{{_esc(v)}}}")
    return ["```{=latex}", "\\begin{tracks}" + "".join(out) + "\\end{tracks}", "```"]


def _workbook_transform(lines):
    """Turn the workbook block syntax into pandoc-ready Markdown + LaTeX fences."""
    out, i, n = [], 0, len(lines)
    heading = re.compile(r"^###\s+(\d+)\.\s+(.*)$")
    fence = re.compile(r"^:::\s*(tracks|doit|see|prompt)\s*$")
    closer = re.compile(r"^:::\s*$")
    while i < n:
        line = lines[i]
        m = heading.match(line.strip())
        if m:
            num, title = m.group(1), m.group(2).strip()
            out += ["```{=latex}", f"\\concept{{{_esc(num)}}}{{{_esc(title)}}}", "```", ""]
            i += 1
            continue
        fm = fence.match(line.strip())
        if fm:
            kind = fm.group(1)
            i += 1
            block = []
            while i < n and not closer.match(lines[i].strip()):
                block.append(lines[i])
                i += 1
            i += 1  # skip the closing :::
            content = [b for b in block if b.strip()]
            if kind == "tracks":
                rows = []
                for b in content:
                    if ":" in b:
                        k, v = b.split(":", 1)
                        rows.append((k.strip().lower(), v.strip()))
                out += _emit_tracks(rows)
            elif kind == "doit":
                out += ["```{=latex}", "\\begin{doit}", "```", ""]
                for b in content:
                    b = b.strip()
                    out.append(b if b.startswith("- ") else "- " + b)
                out += ["", "```{=latex}", "\\end{doit}", "```", ""]
            elif kind == "prompt":
                body = "\\par ".join(_inline(b.strip()) for b in content)
                out += ["```{=latex}",
                        "\\begin{promptbox}" + body + "\\end{promptbox}", "```"]
            elif kind == "see":
                joined = " ".join(b.strip() for b in content)
                out += ["```{=latex}", f"\\seeline{{{_inline(joined)}}}", "```", ""]
            continue
        out.append(line)
        i += 1
    return out


def run(book_dir, out_path, manuscript="manuscript.md", cfg=None):
    """Transform book_dir/<manuscript> -> out_path. Returns a small stats dict.

    By default this reads ``manuscript.md`` and the ``[preprocess]`` block from
    the book's book.toml. A language variant passes an alternate ``manuscript``
    filename and an explicit ``cfg`` dict (its own start_marker / headings to
    promote), so the same cleanup runs over a translated source without needing a
    second book folder. ``cfg`` keys mirror ``_load_preprocess_cfg`` output:
    start_marker, promote_to_chapter, drop_thematic_breaks, workbook.
    """
    if cfg is None:
        cfg = _load_preprocess_cfg(book_dir)
    src_path = os.path.join(book_dir, manuscript)
    lines = open(src_path, encoding="utf-8").read().split("\n")

    # Begin at the start marker if one is set, dropping the title block above it
    # (the frontmatter supplies that). If no marker, keep everything.
    start = 0
    if cfg["start_marker"]:
        marker = cfg["start_marker"].strip()
        idx = next((i for i, l in enumerate(lines) if l.strip() == marker), None)
        if idx is None:
            raise SystemExit(
                f"preprocess: start_marker {marker!r} not found in {src_path}")
        start = idx
    body = lines[start:]

    promote = {h.strip() for h in cfg["promote_to_chapter"]}
    drop_breaks = cfg["drop_thematic_breaks"]

    out, in_code = [], False
    for l in body:
        s = l.strip()
        if s.startswith("```"):
            if s.startswith("```{="):
                out.append(l.rstrip())     # preserve raw-output fence (```{=latex})
            else:
                out.append("```")          # strip language hint on normal fences
            in_code = not in_code
            continue
        if in_code:
            out.append(l)
            continue
        # --- prose ---
        if drop_breaks and s == "---":
            continue                       # drop thematic breaks
        if s in promote and s.startswith("## "):
            out.append("# " + s[3:])       # ## Heading -> # Heading
            continue
        out.append(l)

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    if cfg["workbook"]:
        out = _workbook_transform(out)
    open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")
    txt = "\n".join(out)
    return {
        "out": out_path,
        "lines": len(out),
        "chapters": sum(1 for l in out if re.match(r"^# ", l)),
        "sections": sum(1 for l in out if re.match(r"^## ", l)),
        "dash": ("\u2014" in txt) or ("\u2013" in txt),
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 shared/preprocess.py <book-slug>")
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    slug = sys.argv[1]
    bdir = os.path.join(root, "src", "books", slug)
    outp = os.path.join(root, "temp", slug, "body.md")
    stats = run(bdir, outp)
    print("wrote", stats["out"], "lines:", stats["lines"],
          "chapters:", stats["chapters"], "sections:", stats["sections"],
          "any em/en dash:", stats["dash"])
