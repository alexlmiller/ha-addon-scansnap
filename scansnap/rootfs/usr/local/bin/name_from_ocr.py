#!/usr/bin/env python3
"""
Generate a smart filename from OCR text using regex + heuristics.
Pure Python stdlib — no external APIs, no models.

Reads OCR text from stdin, prints a filename to stdout.

Output format: YYYY-MM-DD - OrgName DocType.pdf
Fallback:      YYYY-MM-DD - Scan.pdf
"""

import re
import sys
from datetime import date


# ── Date extraction ──────────────────────────────────────────────────────────

MONTH_NAMES = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "jun": "06", "jul": "07", "aug": "08", "sep": "09",
    "oct": "10", "nov": "11", "dec": "12",
}
MONTH_PATTERN = "|".join(MONTH_NAMES.keys())


def extract_date(text: str) -> str:
    """Return YYYY-MM-DD from text, or today's date as fallback."""
    # MM/DD/YYYY or MM-DD-YYYY
    m = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](20\d{2})\b", text)
    if m:
        return f"{m.group(3)}-{m.group(1).zfill(2)}-{m.group(2).zfill(2)}"

    # Month DD, YYYY  (e.g. "March 7, 2026" or "March 7 2026")
    m = re.search(
        rf"\b({MONTH_PATTERN})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b",
        text, re.IGNORECASE,
    )
    if m:
        mon = MONTH_NAMES[m.group(1).lower()]
        return f"{m.group(3)}-{mon}-{m.group(2).zfill(2)}"

    # DD Month YYYY  (e.g. "7 March 2026")
    m = re.search(
        rf"\b(\d{{1,2}})\s+({MONTH_PATTERN})\s+(20\d{{2}})\b",
        text, re.IGNORECASE,
    )
    if m:
        mon = MONTH_NAMES[m.group(2).lower()]
        return f"{m.group(3)}-{mon}-{m.group(1).zfill(2)}"

    return date.today().strftime("%Y-%m-%d")


# ── Organization extraction ──────────────────────────────────────────────────

ORG_SUFFIX_RE = re.compile(
    r"\b(LLC|Inc\.?|Corp\.?|Ltd\.?|Bank|Insurance|Credit Union|"
    r"Hospital|Medical|Health|Associates|Partners|Financial|Services)\b",
    re.IGNORECASE,
)

GOVERNMENT_RE = re.compile(
    r"\b("
    r"Department|Court|County|State|City|Town|Agency|Office|Commission|"
    r"Administration|Revenue|Treasury|Water|District|Authority|Board"
    r")\b",
    re.IGNORECASE,
)

NOISE_RE = re.compile(
    r"\b("
    r"letter date|letter id|dear |dated this|page \d+|geocode|contact information|"
    r"governor|director|telephone|zoom|www\.|http|https"
    r")\b",
    re.IGNORECASE,
)


def clean_org_candidate(line: str) -> str:
    line = re.sub(r"[^\w\s&.,'\-]", "", line)
    line = re.sub(r"\s+", " ", line).strip(" -,:")
    return line[:60].strip()


def looks_like_garbage_org(line: str) -> bool:
    compact = re.sub(r"[^A-Za-z]", "", line)
    if len(compact) < 4:
        return True
    if len(compact) >= 7 and compact.isupper() and " " not in line:
        return True
    vowels = sum(1 for c in compact.lower() if c in "aeiou")
    if vowels == 0:
        return True
    if len(compact) >= 6 and vowels / len(compact) < 0.18:
        return True
    return False


def extract_org(lines: list[str]) -> str | None:
    """Scan first 15 lines for a likely organization name."""
    for line in lines[:15]:
        line = line.strip()
        if not line or len(line) > 60:
            continue
        if NOISE_RE.search(line):
            continue

        # Line contains a recognized org suffix (LLC, Bank, Inc, etc.)
        if ORG_SUFFIX_RE.search(line):
            # Strip noise, keep first ~40 chars
            org = clean_org_candidate(line)
            if org:
                return org

        # Government / agency letterheads in title case or uppercase
        if GOVERNMENT_RE.search(line) and len(line.split()) <= 6:
            org = clean_org_candidate(line)
            if org and not looks_like_garbage_org(org):
                return org

        # Short ALL-CAPS line = letterhead (e.g. "AT&T", "CHASE BANK")
        words = line.split()
        if (
            line.isupper()
            and 1 <= len(words) <= 5
            and 3 < len(line) < 40
        ):
            org = clean_org_candidate(line)
            if org and not looks_like_garbage_org(org):
                return org

    return None


# ── Document type extraction ─────────────────────────────────────────────────

DOC_TYPES = [
    (r"\binvoice\b", "Invoice"),
    (r"\bstatement\b", "Statement"),
    (r"\breceipt\b", "Receipt"),
    (r"\bbill\b", "Bill"),
    (r"\bletter\b", "Letter"),
    (r"\bexplanation of benefits\b", "Explanation of Benefits"),
    (r"\beob\b", "Explanation of Benefits"),
    (r"\binsurance\b", "Insurance"),
    (r"\bw-?2\b", "W-2"),
    (r"\b1099\b", "1099"),
    (r"\bprescription\b", "Prescription"),
    (r"\blease\b", "Lease"),
    (r"\bnotice\b", "Notice"),
    (r"\bform\b", "Form"),
    (r"\bagreement\b", "Agreement"),
    (r"\bcontract\b", "Contract"),
    (r"\bwater court\b", "Notice"),
    (r"\bdepartment of revenue\b", "Notice"),
]


def extract_type(text: str) -> str | None:
    text_lower = text.lower()
    for pattern, label in DOC_TYPES:
        if re.search(pattern, text_lower):
            return label
    if "dear " in text_lower:
        return "Letter"
    return None


# ── Filename sanitization ────────────────────────────────────────────────────

def sanitize(s: str) -> str:
    """Remove characters that are unsafe in filenames."""
    return re.sub(r"[^\w\s\-.]", "", s).strip()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    text = sys.stdin.read()
    lines = text.splitlines()

    doc_date = extract_date(text)
    org = extract_org(lines)
    doc_type = extract_type(text)

    if org and doc_type:
        name = f"{doc_date} - {sanitize(org)} {doc_type}.pdf"
    elif org:
        name = f"{doc_date} - {sanitize(org)}.pdf"
    elif doc_type:
        name = f"{doc_date} - {doc_type}.pdf"
    else:
        name = f"{doc_date} - Scan.pdf"

    print(name)


if __name__ == "__main__":
    main()
