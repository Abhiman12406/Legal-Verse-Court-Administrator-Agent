from __future__ import annotations

import io
import os
import re
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Literal, Optional, Tuple
from pydantic import BaseModel, Field


from lexis_ops.schemas.state import CaptionLayoutDescriptor


class ExtractedDocumentMetadata(BaseModel):
    page_count: int = 1
    detected_title: Optional[str] = None
    has_signature: bool = False
    has_certificate_of_service: bool = False
    has_fee_receipt: bool = False
    ada_accommodations: List[str] = Field(default_factory=list)
    confidence_score: float = 1.0
    ingestion_mode: Literal["DIGITAL_SHORT_CIRCUIT", "NEURAL_OCR_DOCLING"] = "DIGITAL_SHORT_CIRCUIT"
    ocr_latency_ms: float = 0.0
    has_embedded_text_layer: bool = True
    caption_layout: Optional[CaptionLayoutDescriptor] = None


class IngressFilingPayload(BaseModel):
    case_number: Optional[str] = None
    document_title: str
    filing_party: Optional[str] = None
    document_raw_text: str
    source_format: Literal["PDF", "XML", "PLAINTEXT"]
    metadata: ExtractedDocumentMetadata
    is_sealed: bool = False
    emergency_motion: bool = False


class DocketXMLPayload(BaseModel):
    case_number: str
    court_id: str
    filing_date: str
    filing_attorney: Optional[str] = None
    docket_entries: List[Dict[str, Any]] = Field(default_factory=list)
    xml_raw: str


class DocketXMLParser:
    """
    Parses statutory court docket XML / ECF records into typed Pydantic payloads.
    """

    @staticmethod
    def parse(xml_content: str | bytes) -> IngressFilingPayload:
        if isinstance(xml_content, bytes):
            xml_str = xml_content.decode("utf-8", errors="replace")
        else:
            xml_str = xml_content

        root = ET.fromstring(xml_str)

        def _find_elem(tags: List[str]) -> Optional[ET.Element]:
            for t in tags:
                el = root.find(f".//{t}")
                if el is not None:
                    return el
            return None

        # Extract standard ECF docket XML fields
        case_num_elem = _find_elem(["CaseNumber", "case_number", "Case"])
        case_number = case_num_elem.text.strip() if case_num_elem is not None and case_num_elem.text else None

        title_elem = _find_elem(["DocumentTitle", "Title", "document_title"])
        document_title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Notice of Motion"

        party_elem = _find_elem(["FilingParty", "Party", "filing_party"])
        filing_party = party_elem.text.strip() if party_elem is not None and party_elem.text else None

        # Extract body/text
        text_elem = _find_elem(["DocumentText", "Body", "Content"])
        raw_text = text_elem.text.strip() if text_elem is not None and text_elem.text else xml_str

        # Check signature & certificate flags
        sig_elem = _find_elem(["SignatureBlock", "Signature"])
        has_signature = sig_elem is not None or bool(re.search(r"/s/\s+[A-Za-z]+", raw_text, re.IGNORECASE))

        svc_elem = _find_elem(["CertificateOfService"])
        has_svc = svc_elem is not None or "certificate of service" in raw_text.lower()

        fee_elem = _find_elem(["FeeReceipt"])
        has_fee = fee_elem is not None or "fee receipt" in raw_text.lower()

        is_emergency = "emergency" in document_title.lower() or "ex parte" in document_title.lower()
        is_sealed = "sealed" in document_title.lower() or "in camera" in document_title.lower()

        # Check ADA/ASL requirements
        ada_accommodations = []
        if "asl interpreter" in raw_text.lower() or "american sign language" in raw_text.lower():
            ada_accommodations.append("ASL_INTERPRETER")
        if "spanish interpreter" in raw_text.lower():
            ada_accommodations.append("SPANISH_INTERPRETER")
        if "wheelchair" in raw_text.lower() or "ada accessible" in raw_text.lower():
            ada_accommodations.append("WHEELCHAIR_ACCESSIBLE")

        metadata = ExtractedDocumentMetadata(
            page_count=1,
            detected_title=document_title,
            has_signature=has_signature,
            has_certificate_of_service=has_svc,
            has_fee_receipt=has_fee,
            ada_accommodations=ada_accommodations,
            confidence_score=1.0,
            ingestion_mode="DIGITAL_SHORT_CIRCUIT",
            ocr_latency_ms=0.5,
            has_embedded_text_layer=True,
        )

        return IngressFilingPayload(
            case_number=case_number,
            document_title=document_title,
            filing_party=filing_party,
            document_raw_text=raw_text,
            source_format="XML",
            metadata=metadata,
            is_sealed=is_sealed,
            emergency_motion=is_emergency,
        )


class PDFIngressInspector:
    """
    Ingress Stream Inspector:
    Inspects PDF byte streams to determine whether an extractable digital text
    layer is present (short-circuit path) or whether the document is an image-only
    raster scan requiring neural OCR (Docling fallback path).
    """

    @staticmethod
    def inspect(file_input: str | bytes) -> Tuple[bool, int, str]:
        """
        Inspects input and returns (has_embedded_text_layer, page_count, extracted_text).
        """
        if isinstance(file_input, str):
            if not os.path.exists(file_input):
                # Simulated plain text or in-memory string representation
                text = file_input.strip()
                return (len(text) >= 20, 1, text)
            # File on disk
            try:
                with open(file_input, "rb") as f:
                    content_bytes = f.read()
            except Exception:
                return (False, 1, "")
        else:
            content_bytes = file_input

        # Check if byte stream resembles PDF
        if not content_bytes.startswith(b"%PDF") and b"%PDF-" not in content_bytes[:1024]:
            # Non-PDF or plain text bytes
            try:
                text = content_bytes.decode("utf-8", errors="ignore").strip()
                if len(text) >= 20:
                    return (True, 1, text)
            except Exception:
                pass
            return (False, 1, "")

        # Fast PyMuPDF (fitz) inspection
        try:
            import fitz
            doc = fitz.open(stream=content_bytes, filetype="pdf")
            page_count = len(doc)
            extracted_pages = []
            for page in doc:
                txt = page.get_text()
                if txt:
                    extracted_pages.append(txt)
            doc.close()
            joined = "\n".join(extracted_pages).strip()
            # If joined digital text has substantial character and word content
            if len(joined) >= 30 and len(joined.split()) >= 4:
                return (True, max(1, page_count), joined)
            return (False, max(1, page_count), joined)
        except Exception:
            pass

        # Fast pypdf fallback inspection
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(content_bytes))
            page_count = len(reader.pages)
            extracted_pages = []
            for p in reader.pages:
                txt = p.extract_text() or ""
                if txt:
                    extracted_pages.append(txt)
            joined = "\n".join(extracted_pages).strip()
            if len(joined) >= 30 and len(joined.split()) >= 4:
                return (True, max(1, page_count), joined)
            return (False, max(1, page_count), joined)
        except Exception:
            pass

        return (False, 1, "")


class DoclingPDFParser:
    """
    Ingress & OCR Gate: parses PDF filings using an automated digital-text short-circuit
    and Docling DocumentConverter neural OCR fallback.
    Converts unstructured legal scans into typed Pydantic models.
    """

    @staticmethod
    def parse_pdf(
        file_input: str | bytes,
        filename: str = "filing.pdf",
        force_ocr: bool = False,
    ) -> IngressFilingPayload:
        t0 = time.perf_counter()

        has_embedded_text = False
        page_count = 1
        raw_text = ""

        if not force_ocr:
            has_embedded_text, page_count, raw_text = PDFIngressInspector.inspect(file_input)

        if has_embedded_text and not force_ocr:
            # Digital short-circuit: < 50ms latency (typically 2-8ms)
            ingestion_mode: Literal["DIGITAL_SHORT_CIRCUIT", "NEURAL_OCR_DOCLING"] = "DIGITAL_SHORT_CIRCUIT"
            confidence_score = 0.99
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
        else:
            # Scanned physical raster scan: route through Docling DocumentConverter
            ingestion_mode = "NEURAL_OCR_DOCLING"
            confidence_score = 0.95
            try:
                from docling.document_converter import DocumentConverter

                converter = DocumentConverter()
                if isinstance(file_input, bytes):
                    import tempfile
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(file_input)
                        tmp_path = tmp.name
                    try:
                        conv_result = converter.convert(tmp_path)
                    finally:
                        try:
                            os.unlink(tmp_path)
                        except OSError:
                            pass
                else:
                    conv_result = converter.convert(file_input)

                doc = conv_result.document
                raw_text = doc.export_to_markdown()
                if callable(getattr(doc, "num_pages", None)):
                    page_count = int(doc.num_pages())
                elif hasattr(doc, "pages"):
                    page_count = int(len(doc.pages))
                else:
                    val = getattr(doc, "num_pages", 1)
                    page_count = int(val) if isinstance(val, (int, float)) else 1
            except Exception:
                # High-reliability fallback if Docling native model weights are still downloading or input format is unusual
                if isinstance(file_input, bytes):
                    try:
                        raw_text = file_input.decode("utf-8", errors="ignore")
                    except Exception:
                        raw_text = str(file_input)
                else:
                    try:
                        with open(file_input, "r", encoding="utf-8", errors="ignore") as f:
                            raw_text = f.read()
                    except Exception:
                        raw_text = str(file_input)
                confidence_score = 0.70

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

        # Structured caption layout evaluation (encapsulated Pydantic model)
        caption_descriptor = CaptionLayoutDescriptor.from_raw_text(raw_text, filename=filename)
        case_number = caption_descriptor.case_number
        detected_title = caption_descriptor.document_title
        confidence_score = min(confidence_score, caption_descriptor.confidence_score)

        # Check signature block: /s/ Name or signed by
        has_signature = bool(
            re.search(
                r"(/s/\s+[A-Za-z]+|respectfully submitted|counsel for defendant|counsel for plaintiff|attorney for)",
                raw_text,
                re.IGNORECASE,
            )
        )
        has_svc = bool(
            re.search(
                r"(certificate of service|served upon counsel|i hereby certify|certificate of transmission)",
                raw_text,
                re.IGNORECASE,
            )
        )
        has_fee = bool(re.search(r"(receipt\s+no|filing\s+fee\s+paid|fee\s+exempt)", raw_text, re.IGNORECASE))

        is_emergency = bool(
            re.search(
                r"\b(?:emergency\s+motion|emergency\s+ex\s+parte|ex\s+parte|temporary\s+restraining\s+order|\btro\b)\b",
                raw_text,
                re.IGNORECASE,
            )
        )
        is_sealed = any(
            kw in raw_text.lower() for kw in ["under seal", "filed under seal", "confidential filing", "in camera"]
        )

        # Detect ADA accommodations
        ada_accommodations = []
        if "asl interpreter" in raw_text.lower() or "sign language" in raw_text.lower():
            ada_accommodations.append("ASL_INTERPRETER")
        if "spanish interpreter" in raw_text.lower():
            ada_accommodations.append("SPANISH_INTERPRETER")
        if "wheelchair" in raw_text.lower() or "ada accessible" in raw_text.lower():
            ada_accommodations.append("WHEELCHAIR_ACCESSIBLE")

        metadata = ExtractedDocumentMetadata(
            page_count=page_count,
            detected_title=detected_title,
            has_signature=has_signature,
            has_certificate_of_service=has_svc,
            has_fee_receipt=has_fee,
            ada_accommodations=ada_accommodations,
            confidence_score=confidence_score,
            ingestion_mode=ingestion_mode,
            ocr_latency_ms=round(elapsed_ms, 2),
            has_embedded_text_layer=has_embedded_text,
            caption_layout=caption_descriptor,
        )

        return IngressFilingPayload(
            case_number=case_number,
            document_title=detected_title,
            filing_party="Filing Counsel",
            document_raw_text=raw_text,
            source_format="PDF",
            metadata=metadata,
            is_sealed=is_sealed,
            emergency_motion=is_emergency,
        )


def ingest_filing(
    content: str | bytes,
    filename: str = "filing.pdf",
    format_type: Optional[Literal["PDF", "XML", "PLAINTEXT"]] = None,
    force_ocr: bool = False,
) -> IngressFilingPayload:
    """
    Unified Ingress Gateway: Converts incoming PDF scans, docket XMLs, or legal filings
    into typed Pydantic IngressFilingPayload.
    """
    if format_type == "XML" or filename.lower().endswith(".xml") or (isinstance(content, str) and content.strip().startswith("<")):
        return DocketXMLParser.parse(content)
    elif format_type == "PDF" or filename.lower().endswith(".pdf") or isinstance(content, bytes):
        return DoclingPDFParser.parse_pdf(content, filename=filename, force_ocr=force_ocr)
    else:
        # Plaintext fallback
        return DoclingPDFParser.parse_pdf(content, filename=filename, force_ocr=force_ocr)

