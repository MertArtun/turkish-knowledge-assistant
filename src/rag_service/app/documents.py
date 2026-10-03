"""Load and validate the Markdown knowledge corpus.

The Markdown files are the single source of truth. Every problem found here stops startup with a
CorpusError that names the file (and line, for section syntax), because a silently skipped or
half-parsed document would make answers and version decisions wrong without any visible error.
The supported file and section syntax is specified in docs/project-spec.md §3.
"""

import hashlib
import re
from dataclasses import dataclass
from datetime import date
from itertools import combinations
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError, model_validator

from app.contracts import Scope

DocumentStatus = Literal["approved", "draft", "withdrawn"]

SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
DOCUMENT_FILE_NAME = re.compile(rf"\d{{2}}-{SLUG}\.md")
SECTION_ID = re.compile(SLUG)
# Any ATX heading CommonMark would render (up to three spaces of indentation).
ANY_HEADING = re.compile(r" {0,3}#{1,6}(?:\s|$)")
SECTION_HEADING = re.compile(r"## (?P<heading>\S.*?) \{#(?P<section_id>[^{}]+)\}")


class CorpusError(Exception):
    """The knowledge corpus is invalid; the service must not start with it."""


class DocumentMetadata(BaseModel):
    # strict: dates must be YAML dates and versions quoted strings. Lax parsing would turn an
    # unquoted `version: 2.10` into the float 2.1 and accept a date written as a plain string.
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    doc_id: Annotated[str, StringConstraints(pattern=r"^D\d{2}$")]
    procedure_id: Annotated[str, StringConstraints(pattern=rf"^{SLUG}$")]
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    version: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    valid_from: date
    # Required but nullable: an open-ended or "replaces nothing" document must say so explicitly.
    valid_to: date | None
    status: DocumentStatus
    scope: Scope
    supersedes: str | None

    @model_validator(mode="after")
    def _valid_to_after_valid_from(self) -> "DocumentMetadata":
        # valid_to is exclusive, so valid_to == valid_from would be a version that is never valid.
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


@dataclass(frozen=True)
class Chunk:
    """One section of a document; the unit that is embedded, retrieved and cited."""

    chunk_id: str
    doc_id: str
    section_id: str
    heading_path: tuple[str, ...]
    # Verbatim section text without its heading line; this is what sources quote.
    content: str
    content_hash: str


@dataclass(frozen=True)
class Document:
    metadata: DocumentMetadata
    source_file: str
    chunks: tuple[Chunk, ...]


def load_corpus(knowledge_dir: Path) -> list[Document]:
    """Parse and validate every document; returns them ordered by doc_id."""
    documents = [_parse_document(path) for path in _document_paths(knowledge_dir)]
    _validate_corpus(documents)
    return sorted(documents, key=lambda doc: doc.metadata.doc_id)


def _document_paths(knowledge_dir: Path) -> list[Path]:
    if not knowledge_dir.is_dir():
        raise CorpusError(f"knowledge directory {knowledge_dir} does not exist")
    paths = []
    # Only direct children are considered, and symlinks are refused, so nothing outside the
    # configured directory can be read. Non-Markdown files and subdirectories are never read.
    for path in sorted(knowledge_dir.iterdir()):
        if path.suffix.lower() != ".md":
            continue
        if path.is_symlink():
            raise CorpusError(f"{path.name}: symbolic links are not allowed in the corpus")
        if not path.is_file():
            raise CorpusError(f"{path.name}: not a regular file")
        if not DOCUMENT_FILE_NAME.fullmatch(path.name):
            # Refused rather than skipped: a misnamed document must not silently go missing,
            # and a README or notes file must not silently become a source.
            raise CorpusError(
                f"unexpected Markdown file '{path.name}'; corpus files are named like "
                "'04-returns-v2.md'"
            )
        paths.append(path)
    if not paths:
        raise CorpusError(f"knowledge directory {knowledge_dir} contains no documents")
    return paths


def _parse_document(path: Path) -> Document:
    name = path.name
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise CorpusError(f"{name}: not valid UTF-8") from None
    lines = text.split("\n")
    frontmatter, body_start = _split_frontmatter(lines, name)
    metadata = _parse_metadata(frontmatter, name)
    chunks = _parse_sections(lines, body_start, metadata, name)
    return Document(metadata=metadata, source_file=name, chunks=chunks)


def _split_frontmatter(lines: list[str], name: str) -> tuple[str, int]:
    """Returns the YAML text and the index of the first body line."""
    if lines[0].rstrip() != "---":
        raise CorpusError(f"{name}: document must start with a YAML frontmatter ('---')")
    for index in range(1, len(lines)):
        if lines[index].rstrip() == "---":
            return "\n".join(lines[1:index]), index + 1
    raise CorpusError(f"{name}: frontmatter is not closed with '---'")


def _parse_metadata(frontmatter: str, name: str) -> DocumentMetadata:
    try:
        # safe_load only builds plain data; YAML tags that construct Python objects are errors.
        raw = yaml.safe_load(frontmatter)
    except yaml.YAMLError as error:
        raise CorpusError(f"{name}: frontmatter is not valid YAML: {error}") from None
    if not isinstance(raw, dict):
        raise CorpusError(f"{name}: frontmatter must be a YAML mapping")
    try:
        return DocumentMetadata.model_validate(raw)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(part) for part in detail['loc']) or 'frontmatter'}: {detail['msg']}"
            for detail in error.errors(include_url=False)
        )
        raise CorpusError(f"{name}: invalid metadata: {problems}") from None


def _parse_sections(
    lines: list[str], body_start: int, metadata: DocumentMetadata, name: str
) -> tuple[Chunk, ...]:
    sections: list[tuple[str, str, list[str]]] = []  # (section_id, heading, content lines)
    for index in range(body_start, len(lines)):
        line = lines[index].rstrip()
        location = f"{name}: line {index + 1}"
        if ANY_HEADING.match(line):
            match = SECTION_HEADING.fullmatch(line)
            if match is None:
                raise CorpusError(
                    f"{location}: unsupported heading {line!r}; "
                    "sections are written as '## Heading {#section-id}'"
                )
            section_id = match["section_id"]
            if not SECTION_ID.fullmatch(section_id):
                raise CorpusError(
                    f"{location}: invalid section id {section_id!r}; "
                    "use lowercase ASCII letters, digits and single hyphens"
                )
            if any(existing_id == section_id for existing_id, _, _ in sections):
                raise CorpusError(f"{location}: duplicate section id {section_id!r}")
            sections.append((section_id, match["heading"], []))
        elif sections:
            sections[-1][2].append(lines[index])
        elif line.strip():
            # Text outside a section would never be retrieved or cited, so it is refused.
            raise CorpusError(f"{location}: text before the first section heading")

    if not sections:
        raise CorpusError(f"{name}: document has no sections")
    chunks = []
    for section_id, heading, content_lines in sections:
        content = "\n".join(content_lines).strip()
        if not content:
            raise CorpusError(f"{name}: section {section_id!r} is empty")
        chunks.append(
            Chunk(
                chunk_id=f"{metadata.doc_id}#{section_id}",
                doc_id=metadata.doc_id,
                section_id=section_id,
                heading_path=(metadata.title, heading),
                content=content,
                content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
            )
        )
    return tuple(chunks)


def _validate_corpus(documents: list[Document]) -> None:
    """Rules that need more than one document. Each violation is a corpus error."""
    files_by_id: dict[str, str] = {}
    for doc in documents:
        doc_id = doc.metadata.doc_id
        if doc_id in files_by_id:
            raise CorpusError(
                f"duplicate doc_id {doc_id} in {files_by_id[doc_id]} and {doc.source_file}"
            )
        files_by_id[doc_id] = doc.source_file
    metadata = [doc.metadata for doc in documents]
    _check_unique_versions(metadata)
    _check_supersedes(metadata)
    _check_no_overlapping_approved_versions(metadata)


def _procedure_and_scope(meta: DocumentMetadata) -> tuple[str, str, str, str]:
    """Documents sharing this key are versions of one procedure in one scope."""
    scope = meta.scope
    return (meta.procedure_id, scope.country, scope.customer_type, scope.product)


def _check_unique_versions(metadata: list[DocumentMetadata]) -> None:
    seen: dict[tuple, str] = {}
    for meta in metadata:
        key = (_procedure_and_scope(meta), meta.version)
        if key in seen:
            raise CorpusError(
                f"{seen[key]} and {meta.doc_id} both declare version {meta.version} "
                f"of {meta.procedure_id} for the same scope"
            )
        seen[key] = meta.doc_id


def _check_supersedes(metadata: list[DocumentMetadata]) -> None:
    # supersedes only documents lineage; validity always comes from the dates and status.
    by_id = {meta.doc_id: meta for meta in metadata}
    for meta in metadata:
        target_id = meta.supersedes
        if target_id is None:
            continue
        target = by_id.get(target_id)
        if target is None:
            raise CorpusError(f"{meta.doc_id} supersedes unknown document {target_id}")
        if target.procedure_id != meta.procedure_id:
            raise CorpusError(f"{meta.doc_id} supersedes {target_id} of a different procedure")
        if target.scope != meta.scope:
            raise CorpusError(f"{meta.doc_id} supersedes {target_id} of a different scope")
    for meta in metadata:
        chain = [meta.doc_id]
        next_id = meta.supersedes
        while next_id is not None:
            chain.append(next_id)
            if next_id in chain[:-1]:
                raise CorpusError(f"supersedes cycle: {' -> '.join(chain)}")
            next_id = by_id[next_id].supersedes


def _check_no_overlapping_approved_versions(metadata: list[DocumentMetadata]) -> None:
    approved = [meta for meta in metadata if meta.status == "approved"]
    for first, second in combinations(approved, 2):
        same_procedure_and_scope = _procedure_and_scope(first) == _procedure_and_scope(second)
        if same_procedure_and_scope and _periods_overlap(first, second):
            raise CorpusError(
                f"approved versions {first.doc_id} and {second.doc_id} of "
                f"{first.procedure_id} overlap; close the older one with valid_to equal to "
                "the newer one's valid_from"
            )


def _periods_overlap(first: DocumentMetadata, second: DocumentMetadata) -> bool:
    # Periods are [valid_from, valid_to); a missing valid_to means open-ended.
    first_end = first.valid_to or date.max
    second_end = second.valid_to or date.max
    return first.valid_from < second_end and second.valid_from < first_end
