#!/usr/bin/env python3
"""Regenerate the faded title-page background used by the series cover.

It blends shared/assets/art_blob.png to 25% opacity over white, producing
shared/assets/bg_titlepage.png. This is a one-off generator, not part of a normal
build; the PNG it makes is committed and reused. Run from the workshop root:

    python3 src/shared/make_bg.py     (needs Pillow)
"""
import os
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src", "shared", "assets", "art_blob.png")
OUT = os.path.join(ROOT, "src", "shared", "assets", "bg_titlepage.png")

im = Image.open(SRC).convert("RGB")
white = Image.new("RGB", im.size, (255, 255, 255))
Image.blend(white, im, 0.25).save(OUT)
print("wrote", OUT)
