# Scan Formats

This file records the document-processing profiles that were tested locally against archived raw ScanSnap iX500 page JPEGs, along with the current conclusions.

The goal was not just "searchable OCR", but:

- clean, readable pages
- suppressed bleed-through and paper texture
- preserved document readability and OCR quality
- reasonable file size

## Current Profiles

### `document_clean`

Intended use:
- letters
- notices
- invoices
- receipts
- anything you mainly want to read, search, or feed to an LLM

Behavior:
- restoration-oriented cleanup
- brighter page background
- reduced paper texture / show-through
- keeps OCR quality strong

Current implementation:
- alias for the internal `restore_soft_bw_cleaner` profile

Why it won:
- best visual tradeoff for "clean paper" output
- still kept good OCR and naming quality
- looked cleaner than the grayscale-preservation profiles

### `document_texture`

Intended use:
- documents where the paper itself matters
- forms or stationery where preserving some original character is useful
- scans where you want a lighter-touch cleanup

Behavior:
- grayscale denoise
- keeps more of the original paper texture and tonal variation
- still trims some scanner noise

Current implementation:
- alias for the internal `gray_denoise` profile

Why it stayed:
- good "preserve fidelity" companion to `document_clean`
- lower-risk, lighter-touch look

## Local Experiment Summary

These profiles were tested locally from the same raw scan set in `~/Desktop/tests`.

### Early Mild Cleanup Profiles

- `baseline`
  - useful control
  - preserved raw appearance
  - not visually clean enough

- `gray_light`
  - decent first default candidate
  - stable OCR
  - differences from baseline were modest

- `gray_soft`
  - slightly smaller files
  - not a large enough visual improvement to matter

- `gray_denoise`
  - best of the mild grayscale family
  - worth keeping as the texture-preserving profile

- `gray_text_boost`
  - increased text emphasis
  - tended to increase file size
  - not a compelling default

### Failed / Rejected Cleanup Profiles

- `gray_bg_soft`
- `gray_bg_soft_text`

Why rejected:
- destroyed OCR
- produced tiny junk outputs

- `gray_bg_flatten`

Why rejected:
- reduced size well
- but too synthetic / destructive visually

- `gray_light_text`

Why rejected:
- caused OCR/name degradation

### Restoration-Oriented Profiles

- `restore_gray`
  - improved OCR confidence
  - but still left too much bleed-through

- `restore_soft_bw`
  - strong candidate
  - good OCR
  - cleaner page background

- `restore_text_mask`
  - stronger "clean paper" look
  - more aggressive visually

- `restore_clean_bw`
  - usable OCR
  - but naming degraded
  - too aggressive

### Final Round

Final narrowed comparison:

- `restore_soft_bw`
- `restore_soft_bw_cleaner`
- `restore_text_mask`
- `restore_text_mask_soft`

Outcome:

- `restore_text_mask_soft`
  - strongest OCR metric
  - slightly cooler / bluer page tone

- `restore_soft_bw_cleaner`
  - preferred visual result
  - whiter, cleaner page look
  - still good OCR

Final decision:

- use `restore_soft_bw_cleaner` as the default analysis/document profile
- keep `gray_denoise` as the texture-preserving profile

## How To Re-Test Later

1. Enable raw scan archiving in the add-on
2. Scan once
3. Replay locally with:

```bash
./scripts/replay_raw_scan.sh \
  /path/to/raw-scan-dir \
  /tmp/scansnap-replay \
  document_clean document_texture baseline
```

For deeper experimentation, internal profile names can still be replayed locally as long as they remain implemented in the scripts.
