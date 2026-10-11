"""End to end tests over the generated samples.

These are the tests that matter. They run the real pipeline on real PDF bytes
and assert on the balance check, which can only pass if the dates, amounts,
directions and row order are all correct at the same time.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bsp.config import load_settings
from bsp.exporters import export_csv, export_excel
from bsp.pipeline import process_statement
from bsp.samplegen.generate import generate_all


@pytest.fixture(scope="session")
def samples(tmp_path_factory) -> dict[str, Path]:
    folder = tmp_path_factory.mktemp("samples")
    return {path.stem: path for path in generate_all(folder)}


@pytest.fixture(scope="session")
def settings() -> dict:
    return load_settings()


def test_samples_are_valid_pdfs(samples):
    assert len(samples) >= 3
    for path in samples.values():
        data = path.read_bytes()
        assert data.startswith(b"%PDF")
        assert data.rstrip().endswith(b"%%EOF")


@pytest.mark.parametrize(
    "name,min_rows",
    [
        ("sample_1_text_simple", 38),
        ("sample_2_wrapped", 22),
        ("sample_3_single_amount", 18),
    ],
)
def test_text_samples_extract_and_reconcile(samples, settings, name, min_rows):
    result = process_statement(samples[name], settings)
    assert len(result.transactions) >= min_rows
    assert result.validation.balance_checked >= min_rows - 2
    assert result.validation.balance_integrity >= 0.95
    assert result.coverage >= 0.90


def test_account_details_are_found(samples, settings):
    result = process_statement(samples["sample_1_text_simple"], settings)
    account = result.account
    assert account.account_holder == "RAJESH KUMAR SHARMA"
    assert account.account_number == "50100234567891"
    assert account.ifsc == "HDFC0000123"
    assert account.period_from is not None and account.period_to is not None


def test_masked_account_number_is_detected(samples, settings):
    result = process_statement(samples["sample_2_wrapped"], settings)
    assert result.account.account_number_masked is True


def test_single_amount_column_directions_are_recovered(samples, settings):
    result = process_statement(samples["sample_3_single_amount"], settings)
    assert all(t.direction in ("DR", "CR") for t in result.transactions)
    assert any(t.debit for t in result.transactions)
    assert any(t.credit for t in result.transactions)


def test_builtin_reader_matches_the_library_reader(samples, settings):
    """The dependency-free reader must find the same rows as pdfplumber."""
    from bsp.pdfio import backends

    path = str(samples["sample_1_text_simple"])
    builtin, name, _notes = backends.load_pages(path, prefer="builtin")
    assert name == "builtin"
    assert len(builtin) == 2
    assert sum(len(p["words"]) for p in builtin) > 200


def test_pdf_type_detection(samples, settings):
    text_result = process_statement(samples["sample_1_text_simple"], settings)
    assert text_result.pdf_kind == "text"
    if "sample_4_scanned" in samples:
        scanned = process_statement(samples["sample_4_scanned"], settings)
        assert scanned.pdf_kind == "image"


def test_exports_are_written_and_openable(samples, settings, tmp_path):
    result = process_statement(samples["sample_1_text_simple"], settings)

    csv_path = export_csv(result, tmp_path / "out.csv")
    body = csv_path.read_text(encoding="utf-8-sig")
    assert "Category" in body.splitlines()[0]
    assert len(body.splitlines()) == len(result.transactions) + 1

    xlsx_path = export_excel(result, tmp_path / "out.xlsx", settings)
    assert zipfile.is_zipfile(xlsx_path)
    with zipfile.ZipFile(xlsx_path) as zf:
        names = zf.namelist()
        assert "xl/workbook.xml" in names
        assert any(n.startswith("xl/worksheets/") for n in names)


def test_minimal_excel_writer_works_without_openpyxl(samples, settings, tmp_path, monkeypatch):
    import dataclasses

    from bsp.exporters import excel_export

    # Capabilities is frozen on purpose, so swap the whole object.
    monkeypatch.setattr(
        excel_export, "CAPS", dataclasses.replace(excel_export.CAPS, openpyxl=False)
    )
    result = process_statement(samples["sample_1_text_simple"], settings)
    path = excel_export.export_excel(result, tmp_path / "fallback.xlsx", settings)
    assert zipfile.is_zipfile(path)


def test_missing_file_is_reported_not_raised(settings, tmp_path):
    result = process_statement(tmp_path / "nope.pdf", settings)
    assert result.transactions == []
    assert any("not found" in w for w in result.warnings)


def test_audit_log_records_every_stage(samples, settings):
    result = process_statement(samples["sample_1_text_simple"], settings)
    joined = " ".join(result.audit)
    for expected in ("read", "document type", "date order", "classifier", "balance check"):
        assert expected in joined
    assert set(result.timings) >= {"read", "detect", "extract", "classify", "validate"}
