#!/usr/bin/env python3
"""Regenerate synthetic AURORA-101 protocol PDFs from editable JSON sources."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from protocol215.fixtures import (  # noqa: E402
    PDF_ADVERSARIAL,
    PDF_V1,
    PDF_V2,
    SOURCE_ADVERSARIAL,
    SOURCE_V1,
    SOURCE_V2,
)
from protocol215.fixtures.protocol_pdf import (  # noqa: E402
    load_protocol_source,
    render_protocol_pdf,
)


def main() -> int:
    jobs = [
        (SOURCE_V1, PDF_V1),
        (SOURCE_V2, PDF_V2),
        (SOURCE_ADVERSARIAL, PDF_ADVERSARIAL),
    ]
    for source_path, pdf_path in jobs:
        if not source_path.is_file():
            print(f"Missing source: {source_path}", file=sys.stderr)
            return 1
        source = load_protocol_source(source_path)
        pages = render_protocol_pdf(source, pdf_path)
        print(f"Wrote {pdf_path} ({pages} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
