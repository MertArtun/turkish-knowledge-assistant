"""Test helpers that write corpus files into a temporary directory.

Invalid corpora are always built in tmp directories, so the real data/knowledge stays untouched.
"""

from datetime import date
from pathlib import Path

import yaml

KNOWLEDGE_DIR = Path(__file__).resolve().parents[3] / "data" / "knowledge"

# Pass as a metadata value to leave that field out of the frontmatter.
OMIT = object()
BASE_METADATA = {
    "doc_id": "D01",
    "procedure_id": "returns",
    "title": "İade Prosedürü",
    "version": "1.0",
    "valid_from": date(2026, 1, 1),
    "valid_to": None,
    "status": "approved",
    "scope": {"country": "TR", "customer_type": "B2B", "product": "MH-10"},
    "supersedes": None,
}
BASE_BODY = "## İade süresi {#sure}\nİade talebi teslimden itibaren 30 takvim günü içinde açılır.\n"


def write_doc(directory: Path, file_name: str, body: str = BASE_BODY, **metadata) -> Path:
    merged = {**BASE_METADATA, **metadata}
    frontmatter = {key: value for key, value in merged.items() if value is not OMIT}
    text = "---\n" + yaml.safe_dump(frontmatter, allow_unicode=True, sort_keys=False)
    path = directory / file_name
    path.write_text(text + "---\n" + body, encoding="utf-8")
    return path
