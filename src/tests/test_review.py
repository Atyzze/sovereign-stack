#!/usr/bin/env python3
"""Content-review tests for Sovereign Press (all books).

This is the *review* gate, the companion to test_build.py (which guards the
build invariants). It checks the things a careful human reviewer would otherwise
have to read each whole book to verify, every iteration, by hand. It is
multi-book: it discovers every book and runs the universal checks on each, plus
the structural checks that book opts into via a [review] table in its book.toml
(Part numbering, section numbering, Pointer boxes, acronym expansion). A book
that declares none of those simply gets the universal checks.

Universal, every book:
  * ASCII-only, no em/en dashes (an independent re-check of the build rule),
  * no placeholder text, no stray tabs or trailing whitespace, balanced fences,
  * no accidental doubled words (advisory),
  * every referenced image exists, and the book's assets/ has no dead weight,
  * the build produced a non-trivial PDF.

Opt-in via [review] in book.toml:
  * expect_part_headings  -> "# PART N:" numbering is contiguous from 0,
  * expect_section_numbers-> "## N.M" numbers run 1..M within each Part,
  * require_pointers      -> Pointer boxes are present and well-formed,
  * expand_acronyms       -> every acronym is spelled out near first use,
      with acronyms_preview_ok / acronyms_described_ok as documented exceptions.

Press-wide:
  * MANIFEST.md names every source file and folder,
  * recovery.zip is present and non-trivial.

Deterministic, standard library only: same verdict every run. Run from the press
root (source checks always; the PDF checks need a prior build):

    python3 tests/test_review.py
    python3 tests/test_review.py atlas-home-node
"""
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as C  # noqa: E402

fails, warns = [], []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        fails.append(name)


def warn(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'warn'}] {name}" + (f"  ({detail})" if detail else ""))
    if not ok:
        warns.append(name)


def skip(name, why):
    print(f"  [skip] {name}  ({why})")


# A general IT glossary. A book only has an acronym checked if it both uses it
# and opts in via [review].expand_acronyms; otherwise this is inert.
ACRONYMS = {
    "LAN": "Local Area Network", "WAN": "Wide Area Network",
    "NAT": "Network Address Translation", "CGNAT": "carrier-grade NAT",
    "DNS": "Domain Name System", "DDNS": "dynamic DNS", "IP": "Internet Protocol",
    "DHCP": "Dynamic Host Configuration Protocol", "SSH": "Secure Shell",
    "VPN": "Virtual Private Network", "TLS": "Transport Layer Security",
    "HTTPS": "HyperText Transfer Protocol Secure",
    "HTTP": "HyperText Transfer Protocol",
    "API": "Application Programming Interface", "URL": "Uniform Resource Locator",
    "GPU": "Graphics Processing Unit", "CPU": "Central Processing Unit",
    "RAM": "Random Access Memory", "VRAM": "Video RAM", "SSD": "Solid State Drive",
    "UEFI": "Unified Extensible Firmware Interface", "BIOS": "Basic Input/Output System",
    "LLM": "Large Language Model", "RAG": "Retrieval-Augmented Generation",
    "PWA": "progressive web app", "LTS": "Long-Term Support",
    "UPS": "uninterruptible power supply", "WPA": "WiFi Protected Access",
    "HBM": "High Bandwidth Memory", "GDDR": "Graphics Double Data Rate",
    "DDR": "Double Data Rate", "HTML": "HyperText Markup Language",
    "CSS": "Cascading Style Sheets", "JS": "JavaScript",
    "JSON": "JavaScript Object Notation", "CSV": "Comma-Separated Values",
    "TOML": "Tom's Obvious Minimal Language", "PDF": "Portable Document Format",
    "GUI": "graphical user interface", "IT": "Information Technology",
    "EM": "electromagnetic", "VAT": "Value Added Tax",
}


def collapse(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def split_prose(lines):
    """Lines outside code fences and not headings, with their 1-based numbers."""
    prose_lines, prose_nums, fence_count, in_code = [], [], 0, False
    for n, l in enumerate(lines, 1):
        s = l.strip()
        if s.startswith("```"):
            fence_count += 1
            in_code = not in_code
            continue
        if in_code or s.startswith("#"):
            continue
        prose_lines.append(l)
        prose_nums.append(n)
    return prose_lines, prose_nums, fence_count


def review_book(slug):
    p = C.book_paths(slug)
    rev = C.book_toml(slug).get("review", {})
    print(f"\n[{slug}]  (tag {C.compose_tag(slug)})")

    if not os.path.exists(p["manuscript"]):
        check("manuscript.md present", False, f"missing: books/{slug}/manuscript.md")
        return

    raw = open(p["manuscript"], encoding="utf-8").read()
    lines = raw.split("\n")
    prose_lines, prose_nums, fence_count = split_prose(lines)
    prose_raw = "\n".join(prose_lines)
    prose = re.sub(r"`[^`]*`", " ", prose_raw).replace("**", "").replace("*", "")

    # ---- universal: ASCII + dashes (independent re-check) ----
    check("manuscript is ASCII-only", all(ord(c) < 128 for c in raw),
          "non-ASCII: " + " ".join(sorted({c for c in raw if ord(c) >= 128})))
    check("no em-dash or en-dash", "\u2014" not in raw and "\u2013" not in raw)

    # ---- universal: no placeholder text ----
    # Placeholder markers are matched the way they are actually written, not as
    # loose substrings, so a book may legitimately contain them as content. The
    # SHOUTED markers (TODO, FIXME, ...) are matched case-sensitively as whole
    # words: a lowercase filename like `todo.txt`, or a sentence about a to-do
    # list, is not a left-behind marker, but "TODO" in caps is. "lorem ipsum" is
    # distinctive enough to match case-insensitively. Angle-bracket placeholders
    # are matched only as <<UPPERCASE>> tokens, so a shell append operator (>>),
    # a heredoc (<<), or a redirect taught in the text never trips this. (This is
    # why the original bare "<<" / ">>" / "[ ]" markers were dropped: a workbook
    # that teaches the shell uses them as real content.)
    shouted = ["TODO", "FIXME", "XXX", "TKTK", "TK TK", "INSERT HERE", "WRITEME"]
    found_ph = [ph for ph in shouted if re.search(r"\b" + re.escape(ph) + r"\b", raw)]
    if re.search(r"lorem ipsum", raw, re.IGNORECASE):
        found_ph.append("lorem ipsum")
    if re.search(r"<<[A-Z_][A-Z0-9_ ]*>>", raw):
        found_ph.append("<<PLACEHOLDER>>")
    check("no placeholder markers in manuscript", not found_ph,
          "found: " + ", ".join(found_ph) if found_ph else "")

    # ---- universal: no tabs / trailing whitespace in prose ----
    ws_bad = []
    for n, l in zip(prose_nums, prose_lines):
        if "\t" in l:
            ws_bad.append(f"tab on line {n}")
        if l != l.rstrip():
            ws_bad.append(f"trailing space on line {n}")
    check("no tabs or trailing whitespace in prose", not ws_bad,
          "; ".join(ws_bad[:6]) + (" ..." if len(ws_bad) > 6 else ""))

    # ---- universal: balanced code fences ----
    check("code fences are balanced", fence_count % 2 == 0,
          f"{fence_count} fence markers")

    # ---- universal: no doubled words (advisory) ----
    doubles = []
    for m in re.finditer(r"\b([A-Za-z]{2,})\s+\1\b", prose):
        if m.group(1).lower() in {"that", "had", "very"}:
            continue
        ctx = re.sub(r"\s+", " ", prose[max(0, m.start() - 25): m.end() + 25]).strip()
        doubles.append(f"'{m.group(1)} {m.group(1)}' ...{ctx}...")
    warn("no accidental doubled words", not doubles,
         "; ".join(doubles) if doubles else "")

    # ---- universal: referenced images exist; assets/ has no dead weight ----
    refs = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", raw))
    refs |= set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", raw))
    fm_text = ""
    if os.path.exists(p["frontmatter"]):
        fm_text = open(p["frontmatter"], encoding="utf-8").read()
        refs |= set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", fm_text))
    have = set(C.list_assets(slug))
    shared_assets = set(os.listdir(os.path.join(C.SHARED, "assets"))) \
        if os.path.isdir(os.path.join(C.SHARED, "assets")) else set()
    asset_missing = []
    for r in sorted(refs):
        name = os.path.basename(r.strip())
        cands = [name] + [name + ext for ext in (".png", ".pdf", ".jpg", ".jpeg")]
        # an image is satisfied by this book's assets/ or the shared assets/;
        # a .pdf reference is also satisfied by its .svg source, because the
        # build's figures step renders assets/x.svg to temp/<slug>/figures/x.pdf
        stem = name[:-4] if name.lower().endswith(".pdf") else name
        cands.append(stem + ".svg")
        if not any(c in have or c in shared_assets for c in cands):
            asset_missing.append(r)
    check(f"referenced images exist ({len(refs)} refs)", not asset_missing,
          "missing: " + ", ".join(asset_missing) if asset_missing else "")

    # every file in this book's assets/ is referenced by its manuscript or
    # frontmatter (a file nothing uses is dead weight)
    ref_text = raw + "\n" + fm_text
    unreferenced = [f for f in have if f not in ref_text]
    check("every file in this book's assets/ is referenced", not unreferenced,
          "dead weight: " + ", ".join(unreferenced) if unreferenced else
          f"{len(have)} asset(s), all referenced")

    # ---- universal: build produced a PDF ----
    if os.path.exists(p["pdf"]):
        size = os.path.getsize(p["pdf"])
        check("build produced a non-trivial PDF", size > 50_000, f"{size:,} bytes")
    else:
        skip("build produced a PDF", "PDF not found; run build.py first")

    # ---- opt-in: chapter tails fill their final page ----
    # A chapter that spills a line or two onto an otherwise empty page (the
    # next chapter opens fresh overleaf) reads as a mistake in print. This
    # measures every page's body text, with the running header, footer, and
    # version tag stripped, and fails on near-empty pages, so a spill is
    # caught the moment an edit creates one and cured by trimming that
    # chapter a little. Opt in with check_page_fill = true (threshold 500
    # body characters) or set an integer to choose the threshold. The title
    # page is exempt by design.
    if rev.get("check_page_fill"):
        threshold = rev["check_page_fill"]
        if threshold is True:
            threshold = 500
        if not os.path.exists(p["pdf"]):
            skip("no near-empty pages", "PDF not found; run build.py first")
        elif not shutil.which("pdftotext"):
            skip("no near-empty pages", "pdftotext not available")
        else:
            txt = subprocess.run(["pdftotext", p["pdf"], "-"],
                                 capture_output=True, text=True).stdout
            thin, emptiest = [], None
            for num, page in enumerate(txt.split("\f"), start=1):
                if num == 1 or not page.strip():
                    continue
                kept = []
                for ln in page.splitlines():
                    t = ln.strip()
                    if not t or "SOVEREIGN STACK" in t:
                        continue
                    if re.fullmatch(r"v\d+v\d+i\d+", t):
                        continue
                    if re.fullmatch(r"\d+\s*/\s*\d+", t):
                        continue
                    kept.append(t)
                body = " ".join(kept)
                if emptiest is None or len(body) < emptiest[1]:
                    emptiest = (num, len(body))
                if len(body) < threshold:
                    thin.append(f'p{num} ({len(body)} chars: "{body[:60]}...")')
            check("no near-empty pages (chapter tails fill their final page)",
                  not thin,
                  "; ".join(thin) if thin else
                  f"emptiest content page is p{emptiest[0]} at {emptiest[1]} chars"
                  f" (threshold {threshold})")

    # ---- opt-in: Part numbering contiguous from 0 ----
    parts = [int(x) for x in re.findall(r"(?m)^#\s+PART\s+(\d+):", raw)]
    if rev.get("expect_part_headings"):
        expected = list(range(0, len(parts)))
        check("Part numbering is contiguous from 0", parts == expected,
              f"found PART {parts}" if parts != expected
              else f"PART 0..{parts[-1] if parts else '?'}")
        # cross-references "Part N" must point at a Part that exists
        maxpart = max(parts) if parts else 0
        bad_refs = sorted({int(x) for x in re.findall(r"\bPart\s+(\d+)\b", prose)
                           if int(x) > maxpart})
        check("every 'Part N' reference points at an existing Part", not bad_refs,
              f"dangling: Part {bad_refs}" if bad_refs else f"all within 0..{maxpart}")

    # ---- opt-in: section numbers run 1..M within each Part ----
    if rev.get("expect_section_numbers"):
        sections = re.findall(r"(?m)^##\s+(\d+)\.(\d+)\b", raw)
        by_part = defaultdict(list)
        for pt, s in sections:
            by_part[int(pt)].append(int(s))
        sec_problems = []
        for pt in sorted(by_part):
            seq = by_part[pt]
            if seq != list(range(1, len(seq) + 1)):
                sec_problems.append(f"Part {pt}: {seq}")
        check("section numbers within each Part are sequential", not sec_problems,
              "; ".join(sec_problems) if sec_problems else f"{len(sections)} sections OK")

    # ---- opt-in: Pointer boxes present and well-formed ----
    pointer_lines = [l for l in lines if l.lstrip().startswith(">") and "Pointer" in l]
    if rev.get("require_pointers") or pointer_lines:
        ptr_bad = []
        for l in pointer_lines:
            body = l.lstrip("> ").strip()
            if not body.startswith("**Pointer.**"):
                ptr_bad.append("not led by **Pointer.**: " + body[:50])
            elif body.count('"') < 2:
                ptr_bad.append("no quoted prompt: " + body[:50])
        need_present = bool(rev.get("require_pointers"))
        ok = not ptr_bad and (len(pointer_lines) > 0 or not need_present)
        check(f"Pointer boxes well-formed ({len(pointer_lines)} found)", ok,
              "; ".join(ptr_bad) if ptr_bad else
              ("none found but required" if need_present and not pointer_lines else ""))

    # ---- opt-in: acronyms expanded in full near first use ----
    if rev.get("expand_acronyms"):
        WINDOW = 80
        preview_ok = set(rev.get("acronyms_preview_ok", []))
        described_ok = set(rev.get("acronyms_described_ok", []))
        # Acronyms so common (or self-evident in context) that the book
        # intentionally never spells them out, e.g. IT, PDF, URL. A documented
        # editorial choice, listed in the book's own [review], not a gap. The
        # check still enforces expansion on every other acronym.
        common_ok = set(rev.get("acronyms_common_ok", []))
        exempt = described_ok | common_ok
        acro_missing, acro_used = [], 0
        for ac, exp in sorted(ACRONYMS.items()):
            m = re.search(r"\b" + re.escape(ac) + r"\b", prose)
            if not m:
                continue
            acro_used += 1
            if ac in exempt:
                continue
            i = m.start()
            if ac in preview_ok:
                ok = collapse(exp) in collapse(prose)
            else:
                ok = collapse(exp) in collapse(prose[max(0, i - WINDOW): i + len(ac) + WINDOW])
            if not ok:
                ctx = re.sub(r"\s+", " ", prose[max(0, i - 35): i + 35]).strip()
                acro_missing.append(f"{ac} -> {exp} | ...{ctx}...")
        check(f"acronyms expanded in full ({acro_used} used, "
              f"{len(preview_ok)} preview-ok, {len(described_ok)} described-ok, "
              f"{len(common_ok)} common-ok)",
              not acro_missing,
              ("missing: " + " ;; ".join(acro_missing)) if acro_missing else "")

    # ---- each declared language edition, reviewed in its own language ----
    for lang in C.book_languages(slug):
        review_language_variant(slug, lang)


def review_language_variant(slug, lang):
    """Content review for one translated edition, run alongside the default one.

    The universal checks are re-run in the variant's own charset (ASCII plus the
    Latin diacritics, no dashes, no smart quotes), together with the placeholder,
    whitespace, fence, and image-reference checks. The structural checks are the
    same shape as the default's but expressed in the edition's language, read from
    its [[language]] entry: Part numbering uses its part_word ("DEEL"), Pointer
    boxes its pointer_lead ("**Aanwijzing.**"); section numbers are language-
    agnostic. Acronym expansion is deliberately NOT run on a variant: the acronyms
    are universal, but rendering their expansions is the translator's job, and a
    second-language glossary is a later pass, not a build gate.
    """
    lp = C.language_paths(slug, lang)
    code = lp["code"]
    t = f"[{code}] "
    if not os.path.exists(lp["manuscript"]):
        check(t + "manuscript present", False,
              f"missing: {os.path.basename(lp['manuscript'])}")
        return
    raw = open(lp["manuscript"], encoding="utf-8").read()
    lines = raw.split("\n")
    prose_lines, prose_nums, fence_count = split_prose(lines)

    # charset: ASCII + known Latin diacritics, no dashes, no smart quotes
    exotic = sorted({c for c in raw if ord(c) > 127 and c not in C.LATIN_DIACRITICS})
    check(t + "charset is ASCII + known diacritics", not exotic,
          "unexpected: " + " ".join(exotic) if exotic else "")
    check(t + "no em-dash or en-dash", "\u2014" not in raw and "\u2013" not in raw)
    smart = sorted({c for c in raw if c in "\u2018\u2019\u201c\u201d"})
    check(t + "no curly/smart quotes", not smart,
          "found: " + " ".join(smart) if smart else "")

    # placeholder markers (same rules as the default edition)
    shouted = ["TODO", "FIXME", "XXX", "TKTK", "TK TK", "INSERT HERE", "WRITEME"]
    found_ph = [ph for ph in shouted if re.search(r"\b" + re.escape(ph) + r"\b", raw)]
    if re.search(r"lorem ipsum", raw, re.IGNORECASE):
        found_ph.append("lorem ipsum")
    if re.search(r"<<[A-Z_][A-Z0-9_ ]*>>", raw):
        found_ph.append("<<PLACEHOLDER>>")
    check(t + "no placeholder markers", not found_ph,
          "found: " + ", ".join(found_ph) if found_ph else "")

    # tabs / trailing whitespace in prose
    ws_bad = []
    for n, l in zip(prose_nums, prose_lines):
        if "\t" in l:
            ws_bad.append(f"tab on line {n}")
        if l != l.rstrip():
            ws_bad.append(f"trailing space on line {n}")
    check(t + "no tabs or trailing whitespace", not ws_bad,
          "; ".join(ws_bad[:6]) + (" ..." if len(ws_bad) > 6 else ""))

    # balanced code fences
    check(t + "code fences are balanced", fence_count % 2 == 0,
          f"{fence_count} fence markers")

    # referenced images exist (shared assets + this book's assets; .pdf <- .svg)
    refs = set(re.findall(r"!\[[^\]]*\]\(([^)]+)\)", raw))
    refs |= set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", raw))
    if os.path.exists(lp["frontmatter"]):
        fm_text = open(lp["frontmatter"], encoding="utf-8").read()
        refs |= set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", fm_text))
    have = set(C.list_assets(slug))
    shared_assets = set(os.listdir(os.path.join(C.SHARED, "assets"))) \
        if os.path.isdir(os.path.join(C.SHARED, "assets")) else set()
    asset_missing = []
    for r in sorted(refs):
        name = os.path.basename(r.strip())
        cands = [name] + [name + ext for ext in (".png", ".pdf", ".jpg", ".jpeg")]
        stem = name[:-4] if name.lower().endswith(".pdf") else name
        cands.append(stem + ".svg")
        if not any(c in have or c in shared_assets for c in cands):
            asset_missing.append(r)
    check(t + f"referenced images exist ({len(refs)} refs)", not asset_missing,
          "missing: " + ", ".join(asset_missing) if asset_missing else "")

    # structural: Part numbering in this language ("# DEEL N:")
    part_word = lang.get("part_word", "PART")
    parts = [int(x) for x in
             re.findall(r"(?m)^#\s+" + re.escape(part_word) + r"\s+(\d+):", raw)]
    expected = list(range(0, len(parts)))
    check(t + f"{part_word} numbering is contiguous from 0", parts == expected,
          f"found {part_word} {parts}" if parts != expected
          else f"{part_word} 0..{parts[-1] if parts else '?'}")

    # structural: section numbers 1..M within each Part (language-agnostic "## N.M")
    sections = re.findall(r"(?m)^##\s+(\d+)\.(\d+)\b", raw)
    by_part = defaultdict(list)
    for pt, s in sections:
        by_part[int(pt)].append(int(s))
    sec_problems = []
    for pt in sorted(by_part):
        seq = by_part[pt]
        if seq != list(range(1, len(seq) + 1)):
            sec_problems.append(f"Part {pt}: {seq}")
    check(t + "section numbers within each Part are sequential", not sec_problems,
          "; ".join(sec_problems) if sec_problems else f"{len(sections)} sections OK")

    # structural: Pointer boxes in this language ("**Aanwijzing.**")
    pointer_lead = lang.get("pointer_lead", "**Pointer.**")
    key = pointer_lead.replace("*", "").rstrip(".")   # e.g. "Aanwijzing"
    pointer_lines = [l for l in lines if l.lstrip().startswith(">") and key in l]
    ptr_bad = []
    for l in pointer_lines:
        body = l.lstrip("> ").strip()
        if not body.startswith(pointer_lead):
            ptr_bad.append(f"not led by {pointer_lead}: " + body[:50])
        elif body.count('"') < 2:
            ptr_bad.append("no quoted prompt: " + body[:50])
    check(t + f"Pointer boxes well-formed ({len(pointer_lines)} found)", not ptr_bad,
          "; ".join(ptr_bad) if ptr_bad else "")


def review_press():
    print("\n[press]")
    # MANIFEST.md names every source file and folder, so it cannot silently drift.
    manifest = os.path.join(C.ROOT, "MANIFEST.md")
    if os.path.exists(manifest):
        man = open(manifest, encoding="utf-8").read()
        expected = set()
        # top level (skip generated/transient folders and the snapshot archive)
        for e in os.listdir(C.ROOT):
            if e in {"__pycache__", "temp", "output", ".git"} or e.endswith(".zip"):
                continue
            expected.add(e)
        # src/shared, src/tests, and every book folder's files
        for sub in (os.path.join("src", "shared"), os.path.join("src", "tests")):
            d = os.path.join(C.ROOT, sub)
            if os.path.isdir(d):
                expected |= {e for e in os.listdir(d) if e != "__pycache__"}
        for slug in C.discover_books():
            expected.add(slug)
            bdir = os.path.join(C.BOOKS_DIR, slug)
            expected |= {e for e in os.listdir(bdir) if e != "__pycache__"}
        missing = sorted({e for e in expected if e not in man})
        check("MANIFEST.md names every source file and folder", not missing,
              "missing: " + ", ".join(missing) if missing
              else f"{len(expected)} entries covered")
    else:
        check("MANIFEST.md present", False, "MANIFEST.md not found")

    # recovery archive present and non-trivial (gated on a build having run)
    archive = os.path.join(C.ROOT, "recovery.zip")
    any_pdf = any(os.path.exists(C.book_paths(s)["pdf"]) for s in C.discover_books())
    if not any_pdf:
        skip("recovery archive present", "no PDFs yet; run build.py first")
    elif os.path.exists(archive):
        check("recovery archive present and non-trivial",
              os.path.getsize(archive) > 50_000, f"{os.path.getsize(archive):,} bytes")
    else:
        check("recovery archive present and non-trivial", False, "recovery.zip not found")


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
    print("CONTENT REVIEW  ::  " + ", ".join(books))
    print("=" * 70)

    for slug in books:
        review_book(slug)
    if not wanted:
        review_press()

    print()
    if warns:
        print(f"{len(warns)} advisory warning(s): {', '.join(warns)}")
    if fails:
        print(f"{len(fails)} check(s) FAILED: {', '.join(fails)}")
        sys.exit(1)
    print("all review checks passed")


if __name__ == "__main__":
    main()
