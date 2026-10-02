#!/usr/bin/env python3
"""Content Linter for Nexus Pre-Sales Bot.

Scans content files (markdown, text, yaml) in tenants/ to detect hardcoded
currency figures ($500, ₹1000, 75 USD, etc.) that could contradict the dynamic
pricing engine (pricing.yaml).
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

# Matches currency symbols and codes followed or preceded by numbers:
# e.g., $5,000, $500, ₹50,000, 75 USD, 6000 INR, USD 500, etc.
CURRENCY_PATTERNS = [
    re.compile(r"\$[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?(?:k|K|m|M)?"),
    re.compile(r"₹[0-9]+(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?(?:k|K|lakh|crore)?"),
    re.compile(r"\b[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?\s*(?:USD|INR|dollars|rupees)\b", re.IGNORECASE),
    re.compile(r"\b(?:USD|INR)\s*[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{1,2})?\b", re.IGNORECASE),
]

IGNORE_FILENAMES = {"pricing.yaml"}
CHECKED_EXTENSIONS = {".md", ".txt", ".yaml", ".yml"}


@dataclass
class LintIssue:
    file: str
    line_number: int
    matched_text: str
    line_content: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line_number}: [CURRENCY_WARNING] Found '{self.matched_text}' in line: '{self.line_content.strip()}'"


def lint_content(target_path: str | Path, strict: bool = False) -> list[LintIssue]:
    path = Path(target_path)
    if not path.exists():
        return []

    issues: list[LintIssue] = []

    if path.is_file():
        files_to_check = [path]
    else:
        files_to_check = [
            f for f in path.rglob("*")
            if f.is_file() and f.suffix.lower() in CHECKED_EXTENSIONS and f.name not in IGNORE_FILENAMES
        ]

    for file_path in files_to_check:
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        for line_idx, line in enumerate(content.splitlines(), start=1):
            # Check for each currency pattern
            for pattern in CURRENCY_PATTERNS:
                for match in pattern.finditer(line):
                    issues.append(
                        LintIssue(
                            file=str(file_path),
                            line_number=line_idx,
                            matched_text=match.group(0),
                            line_content=line,
                        )
                    )

    return issues


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lint content files for hardcoded currency figures.")
    parser.add_argument("--path", default="tenants", help="Path to content directory or file (default: tenants)")
    parser.add_argument("--strict", action="store_true", help="Exit with non-zero status if issues are found")
    args = parser.parse_args(argv)

    issues = lint_content(args.path, strict=args.strict)
    if not issues:
        print(f"Content lint passed: 0 currency issues found in '{args.path}'.")
        return 0

    print(f"Content lint failed: {len(issues)} currency issue(s) found in '{args.path}':")
    for issue in issues:
        print(f"  {issue}")

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
