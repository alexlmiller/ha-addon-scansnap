#!/usr/bin/env python3
"""Apply selected document cleanup profiles to scanned image pages in-place."""

import sys
from PIL import Image, ImageFilter, ImageOps

TEXT_THRESHOLD = 185
BACKGROUND_FLOOR = 236
CONTRAST_CUTOFF = 1
JPEG_QUALITY = 72


def flatten_background(gray: Image.Image) -> Image.Image:
    text_mask = gray.point(lambda p: 255 if p < TEXT_THRESHOLD else 0, mode="L")
    background = gray.point(
        lambda p: p if p < TEXT_THRESHOLD else max(BACKGROUND_FLOOR, p),
        mode="L",
    )
    return Image.composite(gray, background, text_mask)


def clean_page(path: str, mode: str) -> None:
    with Image.open(path) as img:
        if mode == "baseline":
            return

        gray = img.convert("L")
        cleaned = ImageOps.autocontrast(gray, cutoff=CONTRAST_CUTOFF)

        if mode == "gray_light":
            pass
        elif mode == "gray_soft":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
        elif mode == "gray_bg_flatten":
            cleaned = flatten_background(cleaned)
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
        else:
            raise ValueError(f"unknown cleanup mode: {mode}")

        cleaned.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <mode> <image> [image ...]", file=sys.stderr)
        return 1

    mode = sys.argv[1]
    for path in sys.argv[2:]:
        try:
            clean_page(path, mode)
            print(f"CLEAN ({mode}):   {path}", file=sys.stderr)
        except Exception as exc:
            print(f"ERROR cleaning {path}: {exc}", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
