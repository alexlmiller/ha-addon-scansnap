#!/usr/bin/env python3
"""Apply Color / Gray / Lineart page rendering modes in-place."""

import sys
from pathlib import Path

from PIL import Image, ImageOps

JPEG_QUALITY = 72


def normalize_mode(raw: str) -> str:
    mode = raw.strip().lower().replace("-", "").replace("_", "")
    if mode in {"color", "colour"}:
        return "Color"
    if mode in {"gray", "grey", "grayscale", "greyscale"}:
        return "Gray"
    if mode in {"lineart", "line", "bw", "bilevel", "blackwhite"}:
        return "Lineart"
    return ""


def convert_gray(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    return ImageOps.autocontrast(gray, cutoff=1)


def convert_lineart(img: Image.Image) -> Image.Image:
    gray = convert_gray(img)
    try:
        import cv2
        import numpy as np
    except Exception:
        return gray.point(lambda p: 255 if p > 190 else 0, mode="L")

    arr = np.array(gray)
    blurred = cv2.GaussianBlur(arr, (5, 5), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return Image.fromarray(thresh)


def rewrite(path_str: str, mode: str) -> None:
    path = Path(path_str)
    with Image.open(path) as img:
        normalized = normalize_mode(mode)
        if normalized == "Color":
            return
        if normalized == "Gray":
            out = convert_gray(img)
        elif normalized == "Lineart":
            out = convert_lineart(img)
        else:
            raise ValueError(f"unsupported scan color mode: {mode}")
        out.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)


def main() -> int:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <Color|Gray|Lineart> <image> [image ...]", file=sys.stderr)
        return 1

    mode = normalize_mode(sys.argv[1])
    if not mode:
        print(f"Unsupported scan color mode: {sys.argv[1]}", file=sys.stderr)
        return 1

    for path in sys.argv[2:]:
        try:
            rewrite(path, mode)
            print(f"COLOR ({mode}):   {path}", file=sys.stderr)
        except Exception as exc:
            print(f"ERROR applying {mode} to {path}: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
