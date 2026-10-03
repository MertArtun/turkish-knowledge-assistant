import hashlib
import os
from datetime import date
from pathlib import Path

import pytest

from app.documents import CorpusError, load_corpus
from tests.corpus_files import BASE_BODY, BASE_METADATA, KNOWLEDGE_DIR, OMIT, write_doc

# doc_id -> (file name, procedure_id, section IDs the brief requires)
EXPECTED_CORPUS = {
    "D01": ("01-mh10-setup.md", "mh10-setup", {"baglanti"}),
    "D02": ("02-audio-troubleshooting.md", "audio-troubleshooting", {"ses-yok"}),
    "D03": ("03-returns-v1.md", "returns", {"sure", "kargo"}),
    "D04": ("04-returns-v2.md", "returns", {"sure", "kargo"}),
    "D05": ("05-refund-payment.md", "refund-payment", {"bedel"}),
    "D06": ("06-support-ticket.md", "support-ticket", {"alanlar"}),
    "D07": ("07-priority-sla.md", "priority-sla", {"p1"}),
    "D08": ("08-support-hours.md", "support-hours", {"saatler"}),
    "D09": ("09-account-access.md", "account-access", {"sifre"}),
    "D10": ("10-safe-support-sharing.md", "safe-support-sharing", {"paylasim"}),
}


def load_single(tmp_path: Path, body: str = BASE_BODY, **metadata):
    write_doc(tmp_path, "01-doc.md", body, **metadata)
    return load_corpus(tmp_path)


# --- The real corpus -------------------------------------------------------------------------


def test_real_corpus_contains_exactly_the_ten_expected_documents():
    corpus = load_corpus(KNOWLEDGE_DIR)

    assert sorted(path.name for path in KNOWLEDGE_DIR.glob("*.md")) == sorted(
        file_name for file_name, _, _ in EXPECTED_CORPUS.values()
    )
    assert [doc.metadata.doc_id for doc in corpus] == sorted(EXPECTED_CORPUS)
    for doc in corpus:
        file_name, procedure_id, required_sections = EXPECTED_CORPUS[doc.metadata.doc_id]
        assert doc.source_file == file_name
        assert doc.metadata.procedure_id == procedure_id
        assert required_sections <= {chunk.section_id for chunk in doc.chunks}


def test_real_corpus_returns_procedure_has_a_closed_old_and_an_open_current_version():
    by_id = {doc.metadata.doc_id: doc.metadata for doc in load_corpus(KNOWLEDGE_DIR)}

    old, current = by_id["D03"], by_id["D04"]
    assert (old.version, old.status, old.valid_from, old.valid_to, old.supersedes) == (
        "1.0",
        "approved",
        date(2026, 1, 1),
        date(2026, 7, 1),
        None,
    )
    assert (current.version, current.status, current.valid_from, current.valid_to) == (
        "2.0",
        "approved",
        date(2026, 7, 1),
        None,
    )
    assert current.supersedes == "D03"


def test_real_corpus_other_documents_are_open_ended_first_versions_in_the_fictional_scope():
    for doc in load_corpus(KNOWLEDGE_DIR):
        meta = doc.metadata
        assert meta.scope.model_dump() == BASE_METADATA["scope"]
        assert meta.status == "approved"
        if meta.doc_id not in ("D03", "D04"):
            assert (meta.version, meta.valid_from, meta.valid_to, meta.supersedes) == (
                "1.0",
                date(2026, 1, 1),
                None,
                None,
            )


# --- Sections ------------------------------------------------------------------------------


def test_sections_keep_explicit_ids_heading_path_and_verbatim_content(tmp_path):
    body = (
        "## Bağlantı ve aygıt seçimi {#baglanti}\n"
        "\n"
        "MH-10'u USB ile bağlayın.\n"
        "\n"
        "- Giriş aygıtı: MH-10\n"
        "- Çıkış aygıtı: MH-10\n"
        "\n"
        "## Ses gelmiyorsa {#ses-yok}  \n"
        "Test çağrısı başlatın; ğüşıöç İĞÜŞÖÇ korunur.\n"
    )

    (doc,) = load_single(tmp_path, body, doc_id="D07", title="MH-10 Kurulumu")

    assert [chunk.chunk_id for chunk in doc.chunks] == ["D07#baglanti", "D07#ses-yok"]
    first, second = doc.chunks
    assert first.doc_id == "D07"
    assert first.section_id == "baglanti"
    assert first.heading_path == ("MH-10 Kurulumu", "Bağlantı ve aygıt seçimi")
    assert first.content == (
        "MH-10'u USB ile bağlayın.\n\n- Giriş aygıtı: MH-10\n- Çıkış aygıtı: MH-10"
    )
    assert second.heading_path == ("MH-10 Kurulumu", "Ses gelmiyorsa")
    assert second.content == "Test çağrısı başlatın; ğüşıöç İĞÜŞÖÇ korunur."


def test_content_hash_is_the_sha256_of_the_section_content(tmp_path):
    (doc,) = load_single(tmp_path)
    chunk = doc.chunks[0]

    assert chunk.content_hash == hashlib.sha256(chunk.content.encode("utf-8")).hexdigest()


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("## İade süresi\nMetin.\n", "unsupported heading"),
        ("## İade süresi {#sure}x\nMetin.\n", "unsupported heading"),
        ("## {#sure}\nMetin.\n", "unsupported heading"),
        ("# MH-10 İade\n## İade süresi {#sure}\nMetin.\n", "unsupported heading"),
        ("## A {#a}\nMetin.\n### Alt başlık {#alt}\nMetin.\n", "unsupported heading"),
        ("## A {#a}\nMetin.\n   ## B {#b}\nMetin.\n", "unsupported heading"),
        ("## İade süresi {#süre}\nMetin.\n", "invalid section id"),
        ("## İade süresi {#Sure}\nMetin.\n", "invalid section id"),
        ("## İade süresi {#iade--suresi}\nMetin.\n", "invalid section id"),
        ("Giriş paragrafı.\n## İade süresi {#sure}\nMetin.\n", "text before the first section"),
        ("## A {#a}\nMetin.\n## B {#a}\nMetin.\n", "duplicate section id 'a'"),
        ("## A {#a}\n\n   \n## B {#b}\nMetin.\n", "section 'a' is empty"),
        ("\n\n", "has no sections"),
    ],
)
def test_unsupported_section_syntax_is_rejected(tmp_path, body, message):
    with pytest.raises(CorpusError, match=message):
        load_single(tmp_path, body)


def test_section_errors_name_the_file_and_line(tmp_path):
    path = write_doc(tmp_path, "01-doc.md", "## A {#a}\nMetin.\n### Alt\n")
    line_number = path.read_text(encoding="utf-8").split("\n").index("### Alt") + 1

    with pytest.raises(CorpusError, match=rf"01-doc\.md: line {line_number}: unsupported heading"):
        load_corpus(tmp_path)


# --- Frontmatter and metadata --------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("## A {#a}\nMetin.\n", "must start with a YAML frontmatter"),
        ("---\ndoc_id: D01\n## A {#a}\nMetin.\n", "frontmatter is not closed"),
        ("---\ndoc_id: [D01\n---\n## A {#a}\nMetin.\n", "frontmatter is not valid YAML"),
        ("---\n- D01\n- D02\n---\n## A {#a}\nMetin.\n", "frontmatter must be a YAML mapping"),
    ],
)
def test_malformed_frontmatter_is_rejected(tmp_path, text, message):
    (tmp_path / "01-doc.md").write_text(text, encoding="utf-8")

    with pytest.raises(CorpusError, match=message):
        load_corpus(tmp_path)


def test_frontmatter_is_parsed_with_the_safe_yaml_loader(tmp_path):
    marker = tmp_path / "executed"
    text = f"---\ndoc_id: !!python/object/apply:os.system ['touch {marker}']\n---\n" + BASE_BODY
    (tmp_path / "01-doc.md").write_text(text, encoding="utf-8")

    with pytest.raises(CorpusError, match="frontmatter is not valid YAML"):
        load_corpus(tmp_path)
    assert not marker.exists()


def test_versions_and_dates_must_use_their_yaml_types(tmp_path):
    # An unquoted 2.10 would silently become the float 2.1; a quoted date is a plain string.
    text = (
        "---\ndoc_id: D01\nprocedure_id: returns\ntitle: İade\nversion: 2.10\n"
        "valid_from: '2026-01-01'\nvalid_to: null\nstatus: approved\n"
        "scope: {country: TR, customer_type: B2B, product: MH-10}\nsupersedes: null\n---\n"
    )
    (tmp_path / "01-doc.md").write_text(text + BASE_BODY, encoding="utf-8")

    with pytest.raises(CorpusError) as error:
        load_corpus(tmp_path)
    assert "version: Input should be a valid string" in str(error.value)
    assert "valid_from: Input should be a valid date" in str(error.value)


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"valid_to": OMIT}, "valid_to: Field required"),
        ({"supersedes": OMIT}, "supersedes: Field required"),
        ({"scope": {"country": "TR", "customer_type": "B2B"}}, "scope.product: Field required"),
        ({"status": "archived"}, "status: Input should be 'approved', 'draft' or 'withdrawn'"),
        ({"owner": "destek"}, "owner: Extra inputs are not permitted"),
        ({"title": ""}, "title: String should have at least 1 character"),
        ({"doc_id": "D01#x"}, "doc_id: String should match pattern"),
        ({"procedure_id": "İade"}, "procedure_id: String should match pattern"),
        ({"valid_to": date(2026, 1, 1)}, "valid_to must be after valid_from"),
        ({"valid_to": date(2025, 12, 31)}, "valid_to must be after valid_from"),
    ],
)
def test_missing_or_contradictory_metadata_is_rejected(tmp_path, metadata, message):
    with pytest.raises(CorpusError, match=f"01-doc.md: invalid metadata: .*{message}"):
        load_single(tmp_path, **metadata)


# --- Which files are read ------------------------------------------------------------------


def test_only_numbered_markdown_files_directly_under_the_directory_are_read(tmp_path):
    write_doc(tmp_path, "01-doc.md")
    (tmp_path / ".env").write_text("APP_MODE=evidence_only\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("not a document\n", encoding="utf-8")
    (tmp_path / "archive").mkdir()
    write_doc(tmp_path / "archive", "02-old.md", doc_id="D02")

    corpus = load_corpus(tmp_path)

    assert [doc.source_file for doc in corpus] == ["01-doc.md"]


@pytest.mark.parametrize(
    "file_name", ["README.md", "1-doc.md", "01_doc.md", "02-Doc.md", "01-x.MD"]
)
def test_unexpected_markdown_file_names_are_rejected(tmp_path, file_name):
    write_doc(tmp_path, "01-doc.md")
    write_doc(tmp_path, file_name, doc_id="D02")

    with pytest.raises(CorpusError, match=f"unexpected Markdown file '{file_name}'"):
        load_corpus(tmp_path)


def test_symlink_pointing_outside_the_directory_is_rejected(tmp_path):
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    outside = write_doc(tmp_path, "secret.md")
    os.symlink(outside, knowledge / "01-doc.md")

    with pytest.raises(CorpusError, match="01-doc.md: symbolic links are not allowed"):
        load_corpus(knowledge)


def test_symlink_pointing_inside_the_directory_is_rejected(tmp_path):
    write_doc(tmp_path, "01-doc.md")
    os.symlink(tmp_path / "01-doc.md", tmp_path / "02-copy.md")

    with pytest.raises(CorpusError, match="02-copy.md: symbolic links are not allowed"):
        load_corpus(tmp_path)


def test_markdown_named_directory_is_rejected(tmp_path):
    (tmp_path / "01-doc.md").mkdir()

    with pytest.raises(CorpusError, match="01-doc.md: not a regular file"):
        load_corpus(tmp_path)


def test_missing_or_empty_knowledge_directory_is_rejected(tmp_path):
    with pytest.raises(CorpusError, match="does not exist"):
        load_corpus(tmp_path / "missing")
    with pytest.raises(CorpusError, match="no documents"):
        load_corpus(tmp_path)


def test_non_utf8_document_is_rejected(tmp_path):
    (tmp_path / "01-doc.md").write_bytes("---\ntitle: İade\n---\n".encode("iso-8859-9"))

    with pytest.raises(CorpusError, match="01-doc.md: not valid UTF-8"):
        load_corpus(tmp_path)


# --- Rules across documents ----------------------------------------------------------------


def test_duplicate_doc_id_is_rejected(tmp_path):
    write_doc(tmp_path, "01-a.md", doc_id="D01")
    write_doc(tmp_path, "02-b.md", doc_id="D01", procedure_id="other")

    with pytest.raises(CorpusError, match="duplicate doc_id D01 in 01-a.md and 02-b.md"):
        load_corpus(tmp_path)


def test_same_version_twice_for_one_procedure_and_scope_is_rejected(tmp_path):
    write_doc(tmp_path, "01-a.md", doc_id="D01", valid_to=date(2026, 7, 1))
    write_doc(tmp_path, "02-b.md", doc_id="D02", valid_from=date(2026, 7, 1))

    with pytest.raises(CorpusError, match="D01 and D02 both declare version 1.0 of returns"):
        load_corpus(tmp_path)


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ({"doc_id": "D09"}, "D02 supersedes unknown document D01"),
        ({"procedure_id": "refund-payment"}, "D02 supersedes D01 of a different procedure"),
        (
            {"scope": {"country": "DE", "customer_type": "B2B", "product": "MH-10"}},
            "D02 supersedes D01 of a different scope",
        ),
    ],
)
def test_broken_supersedes_is_rejected(tmp_path, target, message):
    write_doc(tmp_path, "01-old.md", **{"valid_to": date(2026, 7, 1), **target})
    write_doc(
        tmp_path,
        "02-new.md",
        doc_id="D02",
        version="2.0",
        valid_from=date(2026, 7, 1),
        supersedes="D01",
    )

    with pytest.raises(CorpusError, match=message):
        load_corpus(tmp_path)


def test_cyclic_supersedes_chain_is_rejected(tmp_path):
    write_doc(tmp_path, "01-a.md", doc_id="D01", status="draft", supersedes="D02")
    write_doc(tmp_path, "02-b.md", doc_id="D02", version="2.0", status="draft", supersedes="D01")

    with pytest.raises(CorpusError, match="supersedes cycle: D01 -> D02 -> D01"):
        load_corpus(tmp_path)


def test_document_superseding_itself_is_rejected(tmp_path):
    with pytest.raises(CorpusError, match="supersedes cycle: D01 -> D01"):
        load_single(tmp_path, supersedes="D01")


def test_overlapping_approved_versions_are_rejected(tmp_path):
    write_doc(tmp_path, "01-v1.md", doc_id="D01", valid_to=date(2026, 8, 1))
    write_doc(tmp_path, "02-v2.md", doc_id="D02", version="2.0", valid_from=date(2026, 7, 1))

    with pytest.raises(CorpusError, match="approved versions D01 and D02 of returns overlap"):
        load_corpus(tmp_path)


def test_adjacent_versions_draft_overlaps_and_other_scopes_are_accepted(tmp_path):
    # valid_to is exclusive, so a version may start on the day the previous one ends.
    write_doc(tmp_path, "01-v1.md", doc_id="D01", valid_to=date(2026, 7, 1))
    write_doc(tmp_path, "02-v2.md", doc_id="D02", version="2.0", valid_from=date(2026, 7, 1))
    write_doc(tmp_path, "03-v3.md", doc_id="D03", version="3.0", status="draft")
    write_doc(
        tmp_path,
        "04-de.md",
        doc_id="D04",
        scope={"country": "DE", "customer_type": "B2B", "product": "MH-10"},
    )

    assert [doc.metadata.doc_id for doc in load_corpus(tmp_path)] == ["D01", "D02", "D03", "D04"]
