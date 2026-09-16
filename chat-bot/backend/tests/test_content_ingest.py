from pathlib import Path

import pytest
from sqlalchemy import select

from backend.app.config_loader.loader import load_config
from backend.app.core.settings import ROOT
from backend.app.models.db import SessionLocal
from backend.app.models.entities import RagChunkRow
from backend.app.rag.content import CONTENT_SOURCE, scan_content
from backend.app.rag.ingest import ingest, main

CASE = """---
title: Acme — field service scheduling
case_id: acme-field
service: mobile_app
industry: logistics
platforms: [ios, android]
stacks: [Flutter, Firebase]
tags: [scheduling, offline]
outcome: Cut dispatch time in half.
nda_only: false
updated: 2026-03-01
---

## The problem

Dispatchers were scheduling by phone and losing jobs.

## What we shipped

An offline-capable scheduling app for field engineers.
"""


def write(root: Path, relative: str, body: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


@pytest.fixture(autouse=True)
def _clean_content_chunks():
    """Content indexed by these tests must not leak into the retrieval tests."""
    yield
    with SessionLocal() as db:
        for row in db.scalars(select(RagChunkRow).where(RagChunkRow.source == CONTENT_SOURCE)).all():
            db.delete(row)
        db.commit()


def findings(scan, level: str) -> str:
    return "\n".join(f.message for f in scan.findings if f.level == level)


def test_front_matter_becomes_searchable_metadata(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/acme-field-service.md", CASE)
    scan = scan_content(tmp_path)
    assert scan.files == 1 and scan.indexed == 1
    assert not scan.errors and not scan.warnings
    document = scan.documents[0]
    assert document.doc_id == "content:case-studies/acme-field-service#0"
    assert document.source == CONTENT_SOURCE
    assert document.source_id == "case-studies/acme-field-service"
    assert document.title.startswith("Acme — field service scheduling")
    assert document.metadata["case_id"] == "acme-field"
    assert document.metadata["service"] == "mobile_app"
    assert document.metadata["platforms"] == ["ios", "android"]
    assert document.metadata["nda_only"] is False


def test_folder_decides_the_kind_of_document(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/one.md", "---\ntitle: One\n---\n\nBody text.\n")
    write(tmp_path, "faq/two.md", "---\ntitle: Two\n---\n\nBody text.\n")
    write(tmp_path, "trust/three.md", "---\ntitle: Three\n---\n\nBody text.\n")
    write(tmp_path, "loose.md", "---\ntitle: Loose\n---\n\nBody text.\n")
    kinds = {d.source_id: d.metadata["kind"] for d in scan_content(tmp_path).documents}
    assert kinds == {"case-studies/one": "case_study", "faq/two": "faq", "trust/three": "trust", "loose": "document"}


def test_draft_documents_are_never_indexed(tmp_path: Path) -> None:
    write(tmp_path, "faq/wip.md", "---\ntitle: Work in progress\nstatus: draft\n---\n\nNot ready yet.\n")
    scan = scan_content(tmp_path)
    assert scan.documents == []
    assert scan.files == 1 and scan.indexed == 0 and scan.skipped == 1
    assert not scan.errors
    assert "not indexed" in "\n".join(f.message for f in scan.findings)


def test_a_missing_title_is_an_error(tmp_path: Path) -> None:
    write(tmp_path, "faq/untitled.md", "---\nservice: web_app\n---\n\nAn answer with no title.\n")
    scan = scan_content(tmp_path)
    assert "missing 'title'" in findings(scan, "error")
    # Still indexed, with the title inferred, so one omission does not lose the content.
    assert scan.documents[0].title == "Untitled"


def test_a_typo_in_a_front_matter_key_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/typo.md", "---\ntitle: Typo\nindusty: fintech\n---\n\nBody text.\n")
    scan = scan_content(tmp_path)
    assert "unknown front matter key 'industy'" in findings(scan, "warning")
    assert not scan.errors


def test_a_service_outside_the_catalogue_is_reported(tmp_path: Path) -> None:
    write(tmp_path, "capabilities/blockchain.md", "---\ntitle: Blockchain\nservice: blockchain\n---\n\nBody.\n")
    scan = scan_content(tmp_path, set(load_config().services.in_scope))
    assert "not a key in services.yaml" in findings(scan, "warning")


def test_broken_front_matter_stops_the_document(tmp_path: Path) -> None:
    # An unquoted colon is the most common authoring mistake. It must not fall back to
    # the defaults, because the defaults publish the file and clear nda_only.
    write(tmp_path, "case-studies/broken.md", "---\ntitle: Broken\nsummary: A case study: with a colon\nnda_only: true\n---\n\nSecret.\n")
    scan = scan_content(tmp_path)
    assert "not valid YAML" in findings(scan, "error")
    assert scan.documents == []


def test_a_long_document_splits_into_stable_chunks(tmp_path: Path) -> None:
    sections = "\n\n".join(
        f"## Section {index}\n\n" + f"Sentence {index} about scheduling and dispatch logistics. " * 40
        for index in range(6)
    )
    write(tmp_path, "process/long.md", f"---\ntitle: Long\n---\n\n{sections}\n")
    first = scan_content(tmp_path).documents
    assert len(first) > 6
    assert [d.doc_id for d in first] == [f"content:process/long#{i}" for i in range(len(first))]
    # Every chunk carries the heading it came from, so a chunk still reads in isolation.
    assert all(d.metadata["heading"] for d in first)
    assert first[0].content.startswith("Section 0")
    # Re-reading the same tree produces byte-identical documents, which is what makes
    # ingest idempotent.
    assert [d.content for d in scan_content(tmp_path).documents] == [d.content for d in first]


def test_headings_split_faq_answers_apart(tmp_path: Path) -> None:
    body = "## Can we start with a prototype?\n\nYes, and it is often the cheapest useful step.\n\n## Do you sign NDAs?\n\nYes, and we work from your template.\n"
    write(tmp_path, "faq/questions.md", f"---\ntitle: FAQ\n---\n\n{body}")
    documents = scan_content(tmp_path).documents
    assert len(documents) == 2
    assert "prototype" in documents[0].content and "prototype" not in documents[1].content
    assert documents[1].title.endswith("Do you sign NDAs?")


def test_authoring_scaffolding_is_not_indexed(tmp_path: Path) -> None:
    write(tmp_path, "README.md", "# How to write content\n")
    write(tmp_path, "_template.md", "---\ntitle: Template\n---\n\nCopy me.\n")
    write(tmp_path, "_drafts/idea.md", "---\ntitle: Idea\n---\n\nNot yet.\n")
    write(tmp_path, "faq/real.md", "---\ntitle: Real\n---\n\nIndexed.\n")
    scan = scan_content(tmp_path)
    assert [d.source_id for d in scan.documents] == ["faq/real"]
    assert scan.files == 1


def test_unsupported_and_empty_files_are_reported(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/deck.pptx", "not really a deck")
    write(tmp_path, "faq/blank.md", "---\ntitle: Blank\n---\n\n")
    scan = scan_content(tmp_path)
    assert "unsupported file type .pptx" in findings(scan, "warning")
    assert "no readable text extracted" in findings(scan, "error")
    assert scan.documents == []


def test_every_file_is_either_indexed_or_skipped(tmp_path: Path) -> None:
    """The counts in the CLI report have to add up, or they cannot be trusted."""
    write(tmp_path, "case-studies/good.md", CASE)
    write(tmp_path, "faq/draft.md", "---\ntitle: Draft\nstatus: draft\n---\n\nLater.\n")
    write(tmp_path, "faq/empty.md", "---\ntitle: Empty\n---\n\n")
    write(tmp_path, "trust/deck.pptx", "wrong format")
    write(tmp_path, "trust/broken.md", "---\ntitle: Broken\nsummary: has a: colon\n---\n\nBody.\n")
    scan = scan_content(tmp_path)
    assert scan.files == 5
    assert scan.indexed == 1
    assert scan.indexed + scan.skipped == scan.files


def test_two_files_with_one_id_are_reported(tmp_path: Path) -> None:
    write(tmp_path, "faq/pricing.md", "---\ntitle: Pricing markdown\n---\n\nBody.\n")
    write(tmp_path, "faq/pricing.txt", "---\ntitle: Pricing text\n---\n\nBody.\n")
    scan = scan_content(tmp_path)
    assert "collides with" in findings(scan, "error")
    assert len(scan.documents) == 1


def test_the_shipped_library_is_valid() -> None:
    """The samples under content/ are the authoring example, so they must be clean."""
    scan = scan_content(ROOT / "content", set(load_config().services.in_scope))
    assert scan.files >= 18
    assert scan.indexed == scan.files
    assert scan.errors == [], "\n".join(str(f) for f in scan.errors)
    assert scan.warnings == [], "\n".join(str(f) for f in scan.warnings)
    # The one hard rule for authors: no figure from pricing.yaml is restated in prose.
    corpus = "\n".join(document.content for document in scan.documents)
    pricing = load_config().pricing
    for base in pricing.bases.values():
        assert str(base) not in corpus
    for phrase in load_config().agency.never_say:
        assert phrase not in corpus


def test_renaming_a_file_replaces_its_chunks(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/before.md", CASE)
    with SessionLocal() as db:
        ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        assert _ids(db) == {"content:case-studies/before#0", "content:case-studies/before#1"}
        (tmp_path / "case-studies/before.md").rename(tmp_path / "case-studies/after.md")
        result = ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        assert result["removed"] == 2
        assert _ids(db) == {"content:case-studies/after#0", "content:case-studies/after#1"}


def test_deleting_a_file_prunes_it_unless_pruning_is_off(tmp_path: Path) -> None:
    write(tmp_path, "faq/keep.md", "---\ntitle: Keep\n---\n\nStays put.\n")
    write(tmp_path, "faq/remove.md", "---\ntitle: Remove\n---\n\nGoes away.\n")
    with SessionLocal() as db:
        ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        (tmp_path / "faq/remove.md").unlink()
        ingest(db, only=CONTENT_SOURCE, prune=False, content_override=tmp_path)
        db.commit()
        assert "content:faq/remove#0" in _ids(db), "--no-prune must leave the orphan alone"
        ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        assert _ids(db) == {"content:faq/keep#0"}


def test_content_ingest_is_idempotent(tmp_path: Path) -> None:
    write(tmp_path, "case-studies/acme.md", CASE)
    with SessionLocal() as db:
        first = ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        assert first["written"] == len(first["scan"].documents) > 0
        second = ingest(db, only=CONTENT_SOURCE, content_override=tmp_path)
        db.commit()
        assert second["written"] == 0 and second["removed"] == 0


def test_dry_run_validates_without_writing(tmp_path: Path, capsys) -> None:
    write(tmp_path, "case-studies/acme.md", CASE)
    write(tmp_path, "faq/untitled.md", "---\nservice: web_app\n---\n\nNo title here.\n")
    with SessionLocal() as db:
        before = _ids(db)
    exit_code = main(["--dry-run", "--only", CONTENT_SOURCE, "--content-dir", str(tmp_path), "--verbose"])
    output = capsys.readouterr().out
    assert exit_code == 1, "an error-level finding must fail the command so it can gate CI"
    assert "nothing written" in output
    assert "missing 'title'" in output
    assert "1 error(s)" in output
    with SessionLocal() as db:
        assert _ids(db) == before


def test_dry_run_succeeds_on_the_shipped_library(capsys) -> None:
    assert main(["--dry-run"]) == 0
    assert "0 error(s)" in capsys.readouterr().out


def test_admin_reindex_reports_the_content_library(client) -> None:
    response = client.post("/api/v1/admin/rag/reindex", auth=("admin", "test-admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["content"]["indexed"] >= 18
    assert body["content"]["errors"] == []
    # The scan object itself must not leak into the response; it is not serialisable.
    assert "scan" not in body


def test_admin_knowledge_base_page_lists_content_chunks(client) -> None:
    client.post("/api/v1/admin/rag/reindex", auth=("admin", "test-admin"))
    response = client.get("/admin/rag", auth=("admin", "test-admin"))
    assert response.status_code == 200
    assert CONTENT_SOURCE in response.text


def _ids(db) -> set[str]:
    return set(db.scalars(select(RagChunkRow.doc_id).where(RagChunkRow.source == CONTENT_SOURCE)).all())