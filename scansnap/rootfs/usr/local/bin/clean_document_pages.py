#!/usr/bin/env python3
"""Apply selected document cleanup profiles to scanned image pages in-place."""

import sys
from PIL import Image, ImageChops, ImageFilter, ImageOps

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


def soft_background_lift(gray: Image.Image, radius: int = 12, offset: int = 234) -> Image.Image:
    background = gray.filter(ImageFilter.GaussianBlur(radius=radius))
    lifted = ImageChops.add(gray, ImageChops.invert(background), scale=1.0, offset=offset)
    return ImageOps.autocontrast(lifted, cutoff=1)


def grayscale_base(img: Image.Image) -> Image.Image:
    gray = img.convert("L")
    return ImageOps.autocontrast(gray, cutoff=CONTRAST_CUTOFF)


def mild_text_boost(gray: Image.Image) -> Image.Image:
    return gray.filter(ImageFilter.UnsharpMask(radius=1.0, percent=75, threshold=3))


def opencv_restore(gray: Image.Image, mode: str) -> Image.Image:
    try:
        import cv2
        import numpy as np
    except Exception as exc:
        raise RuntimeError(f"OpenCV restoration mode unavailable: {exc}") from exc

    arr = np.array(gray)

    # Estimate the page illumination/background and normalize against it.
    background = cv2.GaussianBlur(arr, (0, 0), sigmaX=21, sigmaY=21)
    normalized = cv2.divide(arr, background, scale=255)

    if mode == "restore_gray":
        restored = cv2.fastNlMeansDenoising(normalized, None, h=10, templateWindowSize=7, searchWindowSize=21)
        restored = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8)).apply(restored)
        return Image.fromarray(restored)

    if mode == "restore_soft_bw":
        denoised = cv2.fastNlMeansDenoising(normalized, None, h=8, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            12,
        )
        # Keep text crisp, but soften the page image by blending slightly with normalized grayscale.
        blended = cv2.addWeighted(denoised, 0.28, thresh, 0.72, 0)
        return Image.fromarray(blended)

    if mode == "restore_soft_bw_cleaner":
        denoised = cv2.fastNlMeansDenoising(normalized, None, h=9, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            39,
            13,
        )
        blended = cv2.addWeighted(denoised, 0.20, thresh, 0.80, 0)
        return Image.fromarray(blended)

    if mode == "restore_clean_bw":
        denoised = cv2.fastNlMeansDenoising(normalized, None, h=10, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            41,
            15,
        )
        return Image.fromarray(thresh)

    if mode == "restore_text_mask":
        denoised = cv2.fastNlMeansDenoising(normalized, None, h=9, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            12,
        )
        # Force the page nearly white while preserving text as dark strokes.
        text = cv2.min(denoised, thresh)
        white_page = np.full_like(text, 248)
        mask = thresh < 245
        white_page[mask] = text[mask]
        return Image.fromarray(white_page)

    if mode == "restore_text_mask_soft":
        denoised = cv2.fastNlMeansDenoising(normalized, None, h=8, templateWindowSize=7, searchWindowSize=21)
        thresh = cv2.adaptiveThreshold(
            denoised,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            35,
            10,
        )
        text = cv2.min(denoised, thresh)
        white_page = np.full_like(text, 242)
        mask = thresh < 250
        white_page[mask] = cv2.addWeighted(text, 0.82, denoised, 0.18, 0)[mask]
        return Image.fromarray(white_page)

    raise ValueError(f"unknown OpenCV restoration mode: {mode}")


def clean_page(path: str, mode: str) -> None:
    with Image.open(path) as img:
        if mode == "baseline":
            return

        aliases = {
            "document_clean": "restore_soft_bw_cleaner",
            "document_texture": "gray_denoise",
            "document_texture_color": "color_denoise",
        }
        mode = aliases.get(mode, mode)

        if mode == "color_denoise":
            cleaned = img.convert("RGB").filter(ImageFilter.MedianFilter(size=3))
            cleaned = ImageOps.autocontrast(cleaned, cutoff=1)
            cleaned = cleaned.filter(ImageFilter.UnsharpMask(radius=0.8, percent=45, threshold=3))
            cleaned.save(path, format="JPEG", quality=JPEG_QUALITY, optimize=True)
            return

        cleaned = grayscale_base(img)

        if mode == "gray_light":
            pass
        elif mode == "gray_soft":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
        elif mode == "gray_denoise":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
            cleaned = ImageOps.autocontrast(cleaned, cutoff=1)
        elif mode == "gray_denoise_text":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
            cleaned = ImageOps.autocontrast(cleaned, cutoff=1)
            cleaned = mild_text_boost(cleaned)
        elif mode == "gray_denoise_text_strong":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
            cleaned = ImageOps.autocontrast(cleaned, cutoff=1)
            cleaned = cleaned.filter(ImageFilter.UnsharpMask(radius=1.2, percent=95, threshold=2))
        elif mode == "gray_text_boost":
            cleaned = cleaned.filter(ImageFilter.UnsharpMask(radius=1.5, percent=120, threshold=3))
        elif mode == "gray_light_text":
            cleaned = mild_text_boost(cleaned)
        elif mode == "gray_light_denoise_text":
            cleaned = cleaned.filter(ImageFilter.MedianFilter(size=3))
            cleaned = mild_text_boost(cleaned)
        elif mode == "restore_gray":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "restore_soft_bw":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "restore_soft_bw_cleaner":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "restore_clean_bw":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "restore_text_mask":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "restore_text_mask_soft":
            cleaned = opencv_restore(cleaned, mode)
        elif mode == "gray_bg_soft":
            cleaned = soft_background_lift(cleaned, radius=12, offset=236)
        elif mode == "gray_bg_soft_text":
            cleaned = soft_background_lift(cleaned, radius=10, offset=234)
            cleaned = cleaned.filter(ImageFilter.UnsharpMask(radius=1.3, percent=110, threshold=2))
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
