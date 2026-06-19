#!/usr/bin/env python3
"""Content-review tests for Sovereign Stack, Volume 1.

This is the *review* gate. It is a companion to ``test_build.py`` (which guards
the build invariants: ASCII, no em/en dashes, no overfull boxes, page ceiling)
and it checks the things a careful human reviewer would otherwise have to read
the whole book to verify, every single iteration, by hand:

  * every acronym is spelled out in full near its first use,
  * the version tag in the corner of the page matches the folder name (the
    project's own convention: the folder is named after the iteration number,
    and build.sh derives the tag from it, so the two can never drift),
  * the build actually produced a PDF (the baseline definition of "it works"),
  * the structure is sound: contiguous Part numbering, well-formed section
    numbers, well-formed Pointer boxes, every referenced image present, every
    "Part N" cross-reference pointing at a Part that exists,
  * and the prose is clean: no placeholder text, no stray tabs or trailing
    whitespace, balanced code fences, no accidental ASCII drift.

It is deliberately deterministic and uses only the Python standard library: no
network, no running model, no nondeterministic output. (A local model such as
Ollama could be wired in for a softer, semantic review pass, but a test suite
should give the same verdict every time it runs, so the hard checks below ask
nothing of any service.)

Run from the project root (source checks always; the version, overfull and page
checks need a prior ``./build.sh``)::

    python3 src/tests/test_review.py

Exit code 0 means every hard check passed. This is the book practising its own
thesis from Part 9: functionality is a list of tests, and you own them.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MD = os.path.join(ROOT, "sovereign-stack-vol1.md")
PREAMBLE = os.path.join(ROOT, "src", "preamble.tex")
VERSION_TEX = os.path.join(ROOT, "src", "version.tex")
PDF = os.path.join(ROOT, "outputs", "sovereign-stack-vol1.pdf")
LOG = os.path.join(ROOT, "temp", "sovereign-stack-vol1.log")
ASSETS = os.path.join(ROOT, "assets")
CONFIG = os.path.join(ROOT, "config.toml")
TRACKER = os.path.join(ROOT, "tracker.json")

fails, warns = [], []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def warn(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'warn'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        warns.append(name)


def skip(name, why):
    print(f"[skip] {name}  ({why})")


# ----------------------------------------------------------------------------
# Load the manuscript and derive a few views of it.
# ----------------------------------------------------------------------------
raw = open(MD, encoding="utf-8").read()
lines = raw.split("\n")

# Lines split into prose / code, tracking fenced (```), raw-latex (```{=latex})
# blocks and heading lines. Headings are often ALL CAPS and are not prose.
prose_lines, fence_count, in_code = [], 0, False
prose_line_numbers = []
for n, l in enumerate(lines, 1):
    s = l.strip()
    if s.startswith("```"):
        fence_count += 1
        in_code = not in_code
        continue
    if in_code:
        continue
    if s.startswith("#"):
        continue
    prose_lines.append(l)
    prose_line_numbers.append(n)
prose_raw = "\n".join(prose_lines)

# Prose with inline code spans and emphasis markers removed, for word/acronym
# checks (so `127.0.0.1:PORT` and **LAN** do not distort the text).
prose = re.sub(r"`[^`]*`", " ", prose_raw)
prose = prose.replace("**", "").replace("*", "")


def collapse(s):
    return re.sub(r"\s+", " ", s).strip().lower()


print("=" * 70)
print("CONTENT REVIEW  ::  sovereign-stack-vol1.md")
print("=" * 70)

# ============================================================================
# 1. ACRONYMS: spelled out in full near first use.
# ============================================================================
WINDOW = 80
ACRONYMS = {
    "LAN": "Local Area Network",
    "WAN": "Wide Area Network",
    "NAT": "Network Address Translation",
    "CGNAT": "carrier-grade NAT",
    "DNS": "Domain Name System",
    "DDNS": "dynamic DNS",
    "IP": "Internet Protocol",
    "DHCP": "Dynamic Host Configuration Protocol",
    "SSH": "Secure Shell",
    "TLS": "Transport Layer Security",
    "HTTPS": "HyperText Transfer Protocol Secure",
    "HTTP": "HyperText Transfer Protocol",
    "API": "Application Programming Interface",
    "URL": "Uniform Resource Locator",
    "GPU": "Graphics Processing Unit",
    "CPU": "Central Processing Unit",
    "RAM": "Random Access Memory",
    "VRAM": "Video RAM",
    "SSD": "Solid State Drive",
    "UEFI": "Unified Extensible Firmware Interface",
    "BIOS": "Basic Input/Output System",
    "LLM": "Large Language Model",
    "RAG": "Retrieval-Augmented Generation",
    "PWA": "progressive web app",
    "LTS": "Long-Term Support",
    "UPS": "uninterruptible power supply",
    "WPA": "WiFi Protected Access",
    "HBM": "High Bandwidth Memory",
    "GDDR": "Graphics Double Data Rate",
    "DDR": "Double Data Rate",
    "HTML": "HyperText Markup Language",
    "CSS": "Cascading Style Sheets",
    "JS": "JavaScript",
    "JSON": "JavaScript Object Notation",
    "CSV": "Comma-Separated Values",
    "TOML": "Tom's Obvious Minimal Language",
    "PDF": "Portable Document Format",
    "GUI": "graphical user interface",
    "IT": "Information Technology",
    "EM": "electromagnetic",
    "VAT": "Value Added Tax",
}
acro_missing, acro_used = [], 0
# A few networking/ops terms are signposted in the chapter-preview bullets of
# "How to read this book" before being formally defined in their home section
# (LAN/WAN in 0.2, SSH in 2.5, NAT in 3.3, DNS in 3.8). Expanding them inside the
# compressed preview list would nest parentheses and weigh down a deliberately
# light list, so for these the rule relaxes to "defined somewhere in the book"
# rather than "at first occurrence". Every other acronym must be expanded at
# first use. (Remove a term from this set to enforce the strict rule on it.)
PREVIEW_INTRODUCED = {"LAN", "WAN", "NAT", "DNS", "SSH"}
for ac, exp in sorted(ACRONYMS.items()):
    m = re.search(r"\b" + re.escape(ac) + r"\b", prose)
    if not m:
        continue
    acro_used += 1
    i = m.start()
    if ac in PREVIEW_INTRODUCED:
        ok = collapse(exp) in collapse(prose)                       # anywhere
    else:
        ok = collapse(exp) in collapse(prose[max(0, i - WINDOW): i + len(ac) + WINDOW])
    if not ok:
        ctx = re.sub(r"\s+", " ", prose[max(0, i - 35): i + 35]).strip()
        acro_missing.append(f"{ac} -> {exp} | ...{ctx}...")
check(f"acronyms expanded in full ({acro_used} used, "
      f"{len(PREVIEW_INTRODUCED & set(ACRONYMS))} preview-introduced)",
      not acro_missing,
      ("missing: " + " ;; ".join(acro_missing)) if acro_missing else "")

# ============================================================================
# 2. VERSION TAG self-derives from the folder name and matches it.
# ============================================================================
# The preamble must reference \ssversion and \input the generated version file,
# so the tag is computed rather than hard-typed.
pre = open(PREAMBLE, encoding="utf-8").read()
wired = ("\\ssversion" in pre) and ("version.tex" in pre)
check("preamble uses the auto-derived \\ssversion tag", wired)

# After a build, the generated tag must match the folder name's number.
folder = os.path.basename(ROOT)
folder_num = (re.findall(r"\d+", folder) or [None])[-1]
if os.path.exists(VERSION_TEX):
    vt = open(VERSION_TEX, encoding="utf-8").read()
    m = re.search(r"v\d+v\d+i(\d+)", vt)
    tag_iter = m.group(1) if m else None
    check("version tag matches folder name",
          tag_iter is not None and folder_num is not None and tag_iter == folder_num,
          f"folder='{folder}' (n={folder_num}), tag i{tag_iter}")
else:
    skip("version tag matches folder name", "src/version.tex not built yet; run build.sh")

# ============================================================================
# 2b. CONFIG (config.toml) + TRACKER (tracker.json) + footer mechanism.
# ============================================================================
import json
folder = os.path.basename(ROOT)
folder_num = (re.findall(r"\d+", folder) or [None])[-1]

# config.toml parses and supplies an integer volume + version.
cfg_ok, cfg_detail = False, "config.toml missing"
if os.path.exists(CONFIG):
    try:
        import tomllib
        with open(CONFIG, "rb") as fh:
            cfg = tomllib.load(fh)
        v = cfg.get("version", {})
        cfg_ok = isinstance(v.get("volume"), int) and isinstance(v.get("version"), int)
        cfg_detail = f"volume={v.get('volume')}, version={v.get('version')}"
    except Exception as e:
        cfg_detail = f"parse error: {e}"
check("config.toml parses with integer volume and version", cfg_ok, cfg_detail)

# tracker.json is valid JSON, has a non-empty history, and its current
# iteration matches the folder name (build.sh keeps "current" in sync).
trk_ok, trk_detail = False, "tracker.json missing"
if os.path.exists(TRACKER):
    try:
        trk = json.load(open(TRACKER, encoding="utf-8"))
        hist = trk.get("history", [])
        cur_iter = str(trk.get("current", {}).get("iteration"))
        good_hist = isinstance(hist, list) and len(hist) > 0 and all(
            ("iteration" in h and "summary" in h) for h in hist)
        trk_ok = good_hist and (folder_num is None or cur_iter == folder_num)
        trk_detail = f"{len(hist)} entries, current i{cur_iter}, folder n={folder_num}"
    except Exception as e:
        trk_detail = f"parse error: {e}"
check("tracker.json valid, has history, current matches folder", trk_ok, trk_detail)

# the footer carries the total page count (page X / Y) via lastpage.
foot_ok = ("lastpage" in pre) and ("LastPage" in pre)
check("footer shows total page count (lastpage / \\pageref{LastPage})", foot_ok)

# ============================================================================
# 3. BASELINE: the build produced a PDF.
# ============================================================================
if os.path.exists(PDF):
    size = os.path.getsize(PDF)
    check("build produced a non-trivial PDF", size > 50_000, f"{size} bytes")
else:
    skip("build produced a PDF", "PDF not found; run build.sh first")

# ============================================================================
# 4. PART NUMBERING is contiguous 0..N with no gaps or duplicates.
# ============================================================================
parts = [int(x) for x in re.findall(r"(?m)^#\s+PART\s+(\d+):", raw)]
expected = list(range(0, len(parts)))
check("Part numbering is contiguous from 0",
      parts == expected,
      f"found PART {parts}" if parts != expected else f"PART 0..{parts[-1] if parts else '?'}")

# ============================================================================
# 5. SECTION NUMBERS within each Part run 1..M with no gaps or duplicates.
# ============================================================================
sec_problems = []
sections = re.findall(r"(?m)^##\s+(\d+)\.(\d+)\b", raw)
from collections import defaultdict
by_part = defaultdict(list)
for p, s in sections:
    by_part[int(p)].append(int(s))
for p in sorted(by_part):
    seq = by_part[p]
    if seq != list(range(1, len(seq) + 1)):
        sec_problems.append(f"Part {p}: {seq}")
check("section numbers within each Part are sequential",
      not sec_problems,
      "; ".join(sec_problems) if sec_problems else f"{len(sections)} sections OK")

# ============================================================================
# 6. POINTER boxes are well-formed: start with **Pointer.** and quote a prompt.
# ============================================================================
pointer_lines = [l for l in lines if l.lstrip().startswith(">") and "Pointer" in l]
ptr_bad = []
for l in pointer_lines:
    body = l.lstrip("> ").strip()
    if not body.startswith("**Pointer.**"):
        ptr_bad.append("not led by **Pointer.**: " + body[:50])
    elif body.count('"') < 2:
        ptr_bad.append("no quoted prompt: " + body[:50])
check(f"Pointer boxes well-formed ({len(pointer_lines)} found)",
      not ptr_bad and len(pointer_lines) > 0,
      "; ".join(ptr_bad) if ptr_bad else "")

# ============================================================================
# 7. ASSET references all exist on disk.
# ============================================================================
refs = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", raw))           # markdown images
refs |= set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", raw))  # latex
asset_missing = []
have = set(os.listdir(ASSETS)) if os.path.isdir(ASSETS) else set()
for r in sorted(refs):
    name = os.path.basename(r.strip())
    # try as given, and with common image extensions (graphicspath resolves these)
    cands = [name] + [name + ext for ext in (".png", ".pdf", ".jpg", ".jpeg")]
    if not any(c in have for c in cands):
        asset_missing.append(r)
check(f"referenced images exist in assets/ ({len(refs)} refs)",
      not asset_missing,
      "missing: " + ", ".join(asset_missing) if asset_missing else "")

# ============================================================================
# 8. NO PLACEHOLDER text left in the manuscript.
# ============================================================================
placeholders = ["TODO", "FIXME", "XXX", "TKTK", "TK TK", "lorem ipsum",
                "INSERT HERE", "WRITEME", "<<", ">>", "[ ]"]
found_ph = [p for p in placeholders if p.lower() in raw.lower()]
check("no placeholder markers in manuscript",
      not found_ph,
      "found: " + ", ".join(found_ph) if found_ph else "")

# ============================================================================
# 9. NO doubled words in prose (advisory: a few are legitimate English).
# ============================================================================
doubles = []
for m in re.finditer(r"\b([A-Za-z]{2,})\s+\1\b", prose):
    w = m.group(1).lower()
    if w in {"that", "had", "very"}:       # legitimately doublable
        continue
    ctx = re.sub(r"\s+", " ", prose[max(0, m.start() - 25): m.end() + 25]).strip()
    doubles.append(f"'{m.group(1)} {m.group(1)}' ...{ctx}...")
warn("no accidental doubled words", not doubles,
     "; ".join(doubles) if doubles else "")

# ============================================================================
# 10. NO tabs and no trailing whitespace in prose lines.
# ============================================================================
ws_bad = []
for n, l in zip(prose_line_numbers, prose_lines):
    if "\t" in l:
        ws_bad.append(f"tab on line {n}")
    if l != l.rstrip():
        ws_bad.append(f"trailing space on line {n}")
check("no tabs or trailing whitespace in prose",
      not ws_bad, "; ".join(ws_bad[:6]) + (" ..." if len(ws_bad) > 6 else ""))

# ============================================================================
# 11. CODE fences are balanced (every ``` opened is closed).
# ============================================================================
check("code fences are balanced", fence_count % 2 == 0,
      f"{fence_count} fence markers")

# ============================================================================
# 12. "Part N" cross-references point at a Part that exists.
# ============================================================================
maxpart = max(parts) if parts else 0
bad_refs = sorted({int(x) for x in re.findall(r"\bPart\s+(\d+)\b", prose)
                   if int(x) > maxpart})
check("every 'Part N' reference points at an existing Part",
      not bad_refs,
      f"dangling: Part {bad_refs}" if bad_refs else f"all within 0..{maxpart}")

# ============================================================================
# 13. ASCII-only and no em/en dashes (independent re-check of the build rule).
# ============================================================================
check("manuscript is ASCII-only", all(ord(c) < 128 for c in raw),
      "non-ASCII: " + " ".join(sorted({c for c in raw if ord(c) >= 128})))
check("no em-dash or en-dash", "\u2014" not in raw and "\u2013" not in raw)

# ============================================================================
# 14/15. POST-BUILD: overfull boxes and page ceiling.
# ============================================================================
if os.path.exists(LOG):
    log = open(LOG, encoding="utf-8", errors="ignore").read()
    n_over = log.count("Overfull \\hbox")
    check("no overfull hboxes in build log", n_over == 0, f"{n_over} found")
else:
    skip("overfull-hbox check", "build log not found; run build.sh first")

if os.path.exists(PDF):
    try:
        info = subprocess.run(["pdfinfo", PDF], capture_output=True, text=True).stdout
        pages = int(next(l.split()[1] for l in info.splitlines() if l.startswith("Pages")))
        check("page count within the 100-page ceiling", 1 <= pages <= 100, f"{pages} pages")
    except Exception as e:
        skip("page-count check", f"could not read PDF ({e})")
else:
    skip("page-count check", "PDF not found; run build.sh first")

# ============================================================================
# 16. MANIFEST.md must name every source file and folder (kept honest here, so
#     the manifest cannot silently drift out of date as files come and go).
# ============================================================================
MANIFEST = os.path.join(ROOT, "MANIFEST.md")
if os.path.exists(MANIFEST):
    man = open(MANIFEST, encoding="utf-8").read()
    expected = [e for e in os.listdir(ROOT)
                if e != "__pycache__" and not e.endswith(".zip")]
    for sub in ("src", os.path.join("src", "tests")):
        d = os.path.join(ROOT, sub)
        if os.path.isdir(d):
            expected += [e for e in os.listdir(d) if e != "__pycache__"]
    missing = sorted({e for e in expected if e not in man})
    check("MANIFEST.md names every source file and folder", not missing,
          "missing: " + ", ".join(missing) if missing
          else f"{len(set(expected))} entries covered")
else:
    check("MANIFEST.md present", False, "MANIFEST.md not found")

# ============================================================================
# 17. RECOVERY ARCHIVE present: the bundle must always carry a snapshot of
#     itself (the <folder>.zip that build.sh step 4 maintains), so the base
#     files are always recoverable from inside the tree. This encodes the
#     "always have an archive" rule as a test the project owns, rather than a
#     thing someone has to remember. Gated on a prior build, like the other
#     post-build checks (the archive is written at the end of build.sh).
# ============================================================================
ARCHIVE = os.path.join(ROOT, os.path.basename(ROOT) + ".zip")
if os.path.exists(PDF):
    if os.path.exists(ARCHIVE):
        asize = os.path.getsize(ARCHIVE)
        check("recovery archive present and non-trivial",
              asize > 50_000, f"{os.path.basename(ARCHIVE)}, {asize} bytes")
    else:
        check("recovery archive present and non-trivial", False,
              f"{os.path.basename(ARCHIVE)} not found; build.sh step 4 should create it")
else:
    skip("recovery archive present", "PDF not found; run build.sh first")

# ----------------------------------------------------------------------------
print()
if warns:
    print(f"{len(warns)} advisory warning(s): {', '.join(warns)}")
if fails:
    print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
    sys.exit(1)
print("all review checks passed")
