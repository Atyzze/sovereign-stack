#!/usr/bin/env python3
"""Compose the version tag for the book.

The tag is ``v{volume}v{version}i{iteration}``, where the volume and version come
from ``config.toml`` and the iteration is the number in the name of the folder
the project sits in. build.sh runs this and writes the printed tag into
``src/version.tex``, which the preamble reads, so the tag on every page follows
the folder with no manual edit.

Standard library only. Uses ``tomllib`` (Python 3.11+) when available and falls
back to a tiny regex read of the two integers otherwise, so it works anywhere.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # project root


def iteration_from_folder():
    nums = re.findall(r"\d+", os.path.basename(ROOT))
    return nums[-1] if nums else "0"


def volume_version_from_config():
    vol, ver = "1", "1"
    cfg = os.path.join(ROOT, "config.toml")
    if not os.path.exists(cfg):
        return vol, ver
    try:
        import tomllib
        with open(cfg, "rb") as fh:
            data = tomllib.load(fh)
        v = data.get("version", {})
        vol = str(v.get("volume", vol))
        ver = str(v.get("version", ver))
    except Exception:
        txt = open(cfg, encoding="utf-8").read()
        a = re.search(r"(?m)^\s*volume\s*=\s*(\d+)", txt)
        b = re.search(r"(?m)^\s*version\s*=\s*(\d+)", txt)
        if a:
            vol = a.group(1)
        if b:
            ver = b.group(1)
    return vol, ver


def tag():
    vol, ver = volume_version_from_config()
    return f"v{vol}v{ver}i{iteration_from_folder()}"


if __name__ == "__main__":
    print(tag())
