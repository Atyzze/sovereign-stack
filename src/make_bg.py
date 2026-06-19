#!/usr/bin/env python3
# Regenerate the faded title-page background: 25% opacity of assets/art_blob.png
# over white. Run from the project root: python3 src/make_bg.py  (needs Pillow).
from PIL import Image
im = Image.open("assets/art_blob.png").convert("RGB")
white = Image.new("RGB", im.size, (255, 255, 255))
Image.blend(white, im, 0.25).save("assets/bg_titlepage.png")
print("wrote assets/bg_titlepage.png")
