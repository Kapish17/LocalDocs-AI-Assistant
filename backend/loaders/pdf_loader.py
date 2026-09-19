import logging

from langchain_core.documents import Document
from pypdf import PdfReader

from core.ocr import needs_ocr, ocr_pdf_page

logger = logging.getLogger(__name__)


def load_pdf(file_path):
    """
    Reads a PDF file and extracts text, one Document per page.

    Returning a Document per page (rather than one Document for the whole
    PDF) is what makes page-level source citations ("Page 4") possible —
    metadata is preserved through chunking (LangChain's text splitter
    propagates each source Document's metadata onto its resulting chunks),
    so every chunk retains which page it came from.

    document_id is the same as `source` (the filename) for now — this
    project has no database, so filename is the closest thing to a stable
    identifier — but it's set explicitly and used everywhere downstream so
    retrieval/filtering code never has to fall back to implicitly reading
    `source` and guessing it means "document identity".

    Per-page OCR fallback: if a page's native pypdf extraction yields too
    little text to be usable (needs_ocr), that single page is rasterized
    and OCR'd rather than running OCR over the whole PDF unconditionally —
    text-based pages are never OCR'd, and a mixed scanned/native PDF gets
    the right treatment per page.
    """

    reader = PdfReader(file_path)

    pages = []
    for page_num, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        ocr_used = False

        if needs_ocr(page_text):
            ocr_text = ocr_pdf_page(file_path, page_num - 1)
            if ocr_text:
                page_text = ocr_text
                ocr_used = True
                logger.info("OCR used for %s page %d", file_path.name, page_num)

        pages.append(
            Document(
                page_content=page_text,
                metadata={
                    "source": file_path.name,
                    "file_type": "pdf",
                    "document_id": file_path.name,
                    "page": page_num,
                    "ocr": ocr_used,
                },
            )
        )

    return pages
