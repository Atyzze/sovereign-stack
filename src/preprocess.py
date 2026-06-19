#!/usr/bin/env python3
"""Adapt sovereign-stack-vol1.md into LaTeX-friendly markdown for pandoc.

The manuscript is pure ASCII (verified: zero em/en dashes, no arrows, no tildes),
so the transforms are structural only:

- Drop the leading title block (series title / volume / tagline) -> custom title page.
- Promote the three front-matter headings ("A note before you start",
  "How to read this book", "The thesis…") to chapters (#), so they become proper
  chapters rather than floating sections before PART 0.
- Drop standalone `---` thematic breaks (chapters already provide structure).
- Inside code fences: strip any language hint (defensive; none are present).
"""
import re

src_path = "sovereign-stack-vol1.md"
out_path = "temp/vol1_latex.md"

lines = open(src_path, encoding="utf-8").read().split("\n")

# Begin at the first real section, dropping the title block above it.
start = next(i for i, l in enumerate(lines)
             if l.strip() == "### A note before you start")
body = lines[start:]

out = []
in_code = False
for l in body:
    s = l.strip()
    if s.startswith("```"):
        if s.startswith("```{="):
            out.append(l.rstrip())     # preserve raw-output fence (e.g. ```{=latex})
        else:
            out.append("```")          # strip language hint on normal fences
        in_code = not in_code
        continue
    if in_code:
        out.append(l)
        continue
    # --- prose ---
    if s == "---":
        continue                   # drop thematic breaks
    if s == "### A note before you start":
        out.append("# A note before you start"); continue
    if s == "## How to read this book":
        out.append("# How to read this book"); continue
    if s.startswith("## The thesis"):
        out.append("# The thesis: own your ground"); continue
    out.append(l)

open(out_path, "w", encoding="utf-8").write("\n".join(out) + "\n")

txt = "\n".join(out)
print("wrote", out_path, "lines:", len(out))
print("chapters (# ):", sum(1 for l in out if re.match(r"^# ", l)))
print("sections (## ):", sum(1 for l in out if re.match(r"^## ", l)))
print("any em/en dash left:", ("\u2014" in txt) or ("\u2013" in txt))
