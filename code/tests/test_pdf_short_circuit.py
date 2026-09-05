import time
import fitz  # PyMuPDF
import pytest
from lexis_ops.ingestion.ocr_parser import (
    DoclingPDFParser,
    ExtractedDocumentMetadata,
    IngressFilingPayload,
    PDFIngressInspector,
    ingest_filing,
)


def create_sample_digital_pdf(
    case_number: str = "2026-CV-009941",
    document_title: str = "MOTION FOR PROTECTIVE ORDER",
    signer: str = "Robert Vance, Esq.",
    has_cert: bool = True,
    ada_req: str = "SPANISH INTERPRETER REQUIRED",
) -> bytes:
    """Helper creating an in-memory digital PDF with native text vectors."""
    doc = fitz.open()
    page = doc.new_page()
    text = f"""IN THE TRIAL COURT OF THE FIRST JUDICIAL DISTRICT
COUNTY OF METROPOLIS

CASE NO: {case_number}
DIVISION: CIVIL COMMERCIAL

ACME CORPORATION, Plaintiff,
v.
GLOBAL DYNAMICS LLC, Defendant.

{document_title}

Defendant Global Dynamics LLC moves for a protective order under seal.
Special Accommodation: {ada_req}.

Respectfully submitted,
/s/ {signer}
Counsel for Defendant
"""
    if has_cert:
        text += """
CERTIFICATE OF SERVICE
I hereby certify that a true and correct copy was served upon counsel.
"""
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def create_sample_raster_pdf() -> bytes:
    """Helper creating an in-memory image-only scanned raster PDF (no embedded text)."""
    doc = fitz.open()
    page = doc.new_page()
    pix = fitz.Pixmap(fitz.csRGB, (0, 0, 200, 200), 1)
    pix.clear_with(245)  # Light grey background simulating scanned paper
    page.insert_image(fitz.Rect(50, 50, 300, 300), pixmap=pix)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


def test_pdf_inspector_distinguishes_digital_vs_raster():
    """Verify stream inspector flags digital text layer vs image raster scan."""
    digital_pdf = create_sample_digital_pdf()
    raster_pdf = create_sample_raster_pdf()

    has_text_dig, pages_dig, extracted_dig = PDFIngressInspector.inspect(digital_pdf)
    assert has_text_dig is True
    assert pages_dig >= 1
    assert "2026-CV-009941" in extracted_dig
    assert "MOTION FOR PROTECTIVE ORDER" in extracted_dig

    has_text_rast, pages_rast, extracted_rast = PDFIngressInspector.inspect(raster_pdf)
    assert has_text_rast is False
    assert pages_rast >= 1
    assert len(extracted_rast.strip()) == 0


def test_digital_pdf_short_circuit_sub_50ms_latency():
    """Verify digital-native filings extract in <50ms with DIGITAL_SHORT_CIRCUIT mode."""
    digital_pdf = create_sample_digital_pdf()

    t0 = time.perf_counter()
    payload = DoclingPDFParser.parse_pdf(digital_pdf, filename="Motion_Protective_Order.pdf")
    total_elapsed_ms = (time.perf_counter() - t0) * 1000.0

    # Invariant: Sub-50ms ingestion latency
    assert total_elapsed_ms < 50.0, f"Ingestion took {total_elapsed_ms:.2f}ms, expected <50ms"
    assert payload.metadata.ocr_latency_ms < 50.0
    assert payload.metadata.ingestion_mode == "DIGITAL_SHORT_CIRCUIT"
    assert payload.metadata.has_embedded_text_layer is True
    assert payload.metadata.confidence_score >= 0.98

    # Field extraction fidelity
    assert payload.case_number == "2026-CV-009941"
    assert "motion" in payload.document_title.lower()
    assert payload.metadata.has_signature is True
    assert payload.metadata.has_certificate_of_service is True
    assert "SPANISH_INTERPRETER" in payload.metadata.ada_accommodations
    assert payload.is_sealed is True


def test_scanned_raster_pdf_routes_to_ocr_fallback():
    """Verify scanned bitmap PDFs fall back to neural OCR pathway."""
    raster_pdf = create_sample_raster_pdf()

    payload = DoclingPDFParser.parse_pdf(raster_pdf, filename="Scanned_Filing_001.pdf")

    assert isinstance(payload, IngressFilingPayload)
    assert payload.metadata.ingestion_mode == "NEURAL_OCR_DOCLING"
    assert payload.metadata.has_embedded_text_layer is False
    assert payload.source_format == "PDF"


def test_unified_data_contract_consistency_across_pathways():
    """Verify both digital short-circuit and OCR fallback output identical typed schema."""
    digital_pdf = create_sample_digital_pdf()
    raster_pdf = create_sample_raster_pdf()

    payload_digital = ingest_filing(digital_pdf, filename="digital.pdf")
    payload_raster = ingest_filing(raster_pdf, filename="scanned.pdf")

    assert type(payload_digital) is IngressFilingPayload
    assert type(payload_raster) is IngressFilingPayload
    assert type(payload_digital.metadata) is ExtractedDocumentMetadata
    assert type(payload_raster.metadata) is ExtractedDocumentMetadata

    assert hasattr(payload_digital.metadata, "ingestion_mode")
    assert hasattr(payload_raster.metadata, "ingestion_mode")
    assert hasattr(payload_digital.metadata, "ocr_latency_ms")
    assert hasattr(payload_raster.metadata, "ocr_latency_ms")


def test_benchmark_speedup_greater_than_10x():
    """
    Automated benchmark proving digital-native short-circuit is >10x faster
    than forcing neural OCR initialization.
    """
    digital_pdf = create_sample_digital_pdf()

    # Measure digital short-circuit latency (multiple runs)
    digital_latencies = []
    for _ in range(5):
        t0 = time.perf_counter()
        p = DoclingPDFParser.parse_pdf(digital_pdf, force_ocr=False)
        digital_latencies.append((time.perf_counter() - t0) * 1000.0)
    avg_digital_ms = sum(digital_latencies) / len(digital_latencies)

    # Measure fallback latency (force_ocr=True)
    ocr_latencies = []
    for _ in range(3):
        t0 = time.perf_counter()
        p = DoclingPDFParser.parse_pdf(digital_pdf, force_ocr=True)
        ocr_latencies.append((time.perf_counter() - t0) * 1000.0)
    avg_ocr_ms = sum(ocr_latencies) / len(ocr_latencies)

    speedup_factor = avg_ocr_ms / max(0.001, avg_digital_ms)
    print(f"\n[BENCHMARK] Digital Short-Circuit: {avg_digital_ms:.2f}ms | Fallback: {avg_ocr_ms:.2f}ms | Speedup: {speedup_factor:.1f}x")

    assert speedup_factor > 10.0, f"Expected >10x speedup, got {speedup_factor:.1f}x"
