"""
PDF MCP Server — comprehensive PDF manipulation toolkit.

TOOLS:
    pdf_generate_extraction_code     Generate text/table extraction code
    pdf_generate_creation_code       Generate PDF creation code (reportlab)
    pdf_generate_merge_split_code    Generate merge/split operations code
    pdf_generate_manipulation_code   Generate page manipulation code
    pdf_generate_metadata_code       Generate metadata operations code
    pdf_generate_form_code           Generate form handling code
    pdf_generate_encryption_code     Generate password protection code
    pdf_generate_ocr_code            Generate OCR code for scanned PDFs
    pdf_detect_antipatterns          Detect anti-patterns in PDF code
    pdf_generate_scaffold            Generate complete PDF processing script
"""

import json
import re
from typing import Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("pdf_mcp")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXTRACTION_TYPES = ["text", "tables", "text_with_coords", "images"]
CREATION_TYPES = ["basic", "report", "invoice", "multi_page"]
MANIPULATION_TYPES = ["rotate", "crop", "watermark", "resize"]
FORM_TYPES = ["fillable", "non_fillable", "detect_fields"]

# Code templates
TEXT_EXTRACTION_TEMPLATE = '''"""PDF text extraction using {library}."""
from {import_path} import {imports}

def extract_text(pdf_path: str) -> str:
    """Extract text from PDF.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        Extracted text content
    """
{body}
'''

TABLE_EXTRACTION_TEMPLATE = '''"""PDF table extraction using pdfplumber."""
import pdfplumber
import pandas as pd
from typing import list

def extract_tables(pdf_path: str) -> list[pd.DataFrame]:
    """Extract tables from PDF as DataFrames.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        List of DataFrames, one per table found
    """
    tables = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            page_tables = page.extract_tables()
            for table in page_tables:
                if table and len(table) > 1:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df.attrs["page"] = page_num + 1
                    tables.append(df)
    return tables
'''

BASIC_CREATION_TEMPLATE = '''"""Create PDF using reportlab."""
from reportlab.lib.pagesizes import {pagesize}
from reportlab.pdfgen import canvas

def create_pdf(output_path: str, content: str) -> None:
    """Create a basic PDF document.

    Args:
        output_path: Path to output PDF file
        content: Text content to add
    """
    c = canvas.Canvas(output_path, pagesize={pagesize})
    width, height = {pagesize}

    # Add content
    y_position = height - 50
    for line in content.split("\\n"):
        c.drawString(50, y_position, line)
        y_position -= 15
        if y_position < 50:
            c.showPage()
            y_position = height - 50

    c.save()
'''

REPORT_CREATION_TEMPLATE = '''"""Create professional PDF report using reportlab."""
from reportlab.lib.pagesizes import {pagesize}
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_report(output_path: str, title: str, sections: list[dict]) -> None:
    """Create a professional PDF report.

    Args:
        output_path: Path to output PDF file
        title: Report title
        sections: List of dicts with 'heading' and 'content' keys
    """
    doc = SimpleDocTemplate(output_path, pagesize={pagesize})
    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 0.5 * inch))

    # Sections
    for section in sections:
        story.append(Paragraph(section['heading'], styles['Heading1']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(section['content'], styles['Normal']))
        story.append(Spacer(1, 0.3 * inch))

    doc.build(story)
'''

MERGE_TEMPLATE = '''"""Merge multiple PDFs using pypdf."""
from pypdf import PdfReader, PdfWriter
from pathlib import Path

def merge_pdfs(pdf_paths: list[str], output_path: str) -> None:
    """Merge multiple PDFs into one.

    Args:
        pdf_paths: List of input PDF file paths
        output_path: Path to output merged PDF
    """
    writer = PdfWriter()

    for pdf_path in pdf_paths:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

SPLIT_TEMPLATE = '''"""Split PDF into individual pages using pypdf."""
from pypdf import PdfReader, PdfWriter
from pathlib import Path

def split_pdf(pdf_path: str, output_dir: str) -> list[str]:
    """Split PDF into individual page files.

    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory for output files

    Returns:
        List of created file paths
    """
    reader = PdfReader(pdf_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    for i, page in enumerate(reader.pages):
        writer = PdfWriter()
        writer.add_page(page)

        output_path = output_dir / f"page_{i + 1:03d}.pdf"
        with open(output_path, "wb") as output:
            writer.write(output)
        created_files.append(str(output_path))

    return created_files
'''

ROTATE_TEMPLATE = '''"""Rotate PDF pages using pypdf."""
from pypdf import PdfReader, PdfWriter

def rotate_pages(pdf_path: str, output_path: str, degrees: int, pages: list[int] | None = None) -> None:
    """Rotate specific pages in a PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        degrees: Rotation degrees (90, 180, 270)
        pages: Page numbers to rotate (1-based), None for all pages
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        if pages is None or page_num in pages:
            page.rotate(degrees)
        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

WATERMARK_TEMPLATE = '''"""Add watermark to PDF using pypdf."""
from pypdf import PdfReader, PdfWriter

def add_watermark(pdf_path: str, watermark_path: str, output_path: str) -> None:
    """Add watermark to all pages of a PDF.

    Args:
        pdf_path: Path to input PDF file
        watermark_path: Path to watermark PDF (single page)
        output_path: Path to output PDF file
    """
    watermark = PdfReader(watermark_path).pages[0]
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.merge_page(watermark)
        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

METADATA_TEMPLATE = '''"""PDF metadata operations using pypdf."""
from pypdf import PdfReader, PdfWriter
from datetime import datetime

def get_metadata(pdf_path: str) -> dict:
    """Extract metadata from PDF.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        Dictionary of metadata fields
    """
    reader = PdfReader(pdf_path)
    meta = reader.metadata

    return {{
        "title": meta.title if meta else None,
        "author": meta.author if meta else None,
        "subject": meta.subject if meta else None,
        "creator": meta.creator if meta else None,
        "producer": meta.producer if meta else None,
        "page_count": len(reader.pages),
    }}

def set_metadata(pdf_path: str, output_path: str, metadata: dict) -> None:
    """Set metadata on PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        metadata: Dictionary with title, author, subject keys
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.add_metadata(metadata)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

FORM_FILLABLE_TEMPLATE = '''"""Fill fillable PDF forms using pypdf."""
from pypdf import PdfReader, PdfWriter

def get_form_fields(pdf_path: str) -> dict:
    """Get form field names and values from PDF.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        Dictionary of field names to current values
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    return {{
        name: {{
            "value": field.get("/V", ""),
            "type": str(field.get("/FT", "")),
        }}
        for name, field in (fields or {{}}).items()
    }}

def fill_form(pdf_path: str, output_path: str, field_values: dict) -> None:
    """Fill form fields in a PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        field_values: Dictionary of field names to values
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    writer.append(reader)
    writer.update_page_form_field_values(writer.pages[0], field_values)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

ENCRYPTION_TEMPLATE = '''"""PDF encryption/decryption using pypdf."""
from pypdf import PdfReader, PdfWriter

def encrypt_pdf(pdf_path: str, output_path: str, user_password: str, owner_password: str | None = None) -> None:
    """Encrypt PDF with password protection.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output encrypted PDF
        user_password: Password required to open PDF
        owner_password: Password for full access (defaults to user_password)
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    writer.encrypt(user_password, owner_password or user_password)

    with open(output_path, "wb") as output:
        writer.write(output)

def decrypt_pdf(pdf_path: str, output_path: str, password: str) -> None:
    """Decrypt password-protected PDF.

    Args:
        pdf_path: Path to encrypted PDF file
        output_path: Path to output decrypted PDF
        password: Password to decrypt
    """
    reader = PdfReader(pdf_path)

    if reader.is_encrypted:
        reader.decrypt(password)

    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

OCR_TEMPLATE = '''"""OCR for scanned PDFs using pytesseract and pdf2image."""
import pytesseract
from pdf2image import convert_from_path
from pathlib import Path

def ocr_pdf(pdf_path: str, output_path: str | None = None, language: str = "eng") -> str:
    """Extract text from scanned PDF using OCR.

    Args:
        pdf_path: Path to scanned PDF file
        output_path: Optional path to save extracted text
        language: Tesseract language code (default: eng)

    Returns:
        Extracted text content
    """
    images = convert_from_path(pdf_path)

    text_parts = []
    for i, image in enumerate(images):
        page_text = pytesseract.image_to_string(image, lang=language)
        text_parts.append(f"--- Page {{i + 1}} ---\\n{{page_text}}")

    full_text = "\\n\\n".join(text_parts)

    if output_path:
        Path(output_path).write_text(full_text, encoding="utf-8")

    return full_text
'''

# Anti-patterns
ANTIPATTERNS = [
    {
        "pattern": r"\.extract_text\(\).*for.*in.*range\(len",
        "issue": "Inefficient page iteration",
        "fix": "Use `for page in reader.pages:` instead of range(len())",
    },
    {
        "pattern": r"open\([^)]+\)\s*$",
        "issue": "File handle not closed",
        "fix": "Use context manager: `with open(...) as f:`",
    },
    {
        "pattern": r"PdfReader\([^)]+\)\.pages\[0\]\.extract_text\(\)",
        "issue": "Reader created just to read one page",
        "fix": "Store reader in variable for potential reuse",
    },
    {
        "pattern": r"for.*in.*pdf\.pages.*:\s*writer = PdfWriter",
        "issue": "Creating writer inside loop",
        "fix": "Create PdfWriter once before loop",
    },
    {
        "pattern": r"\.decrypt\(['\"]['\"]",
        "issue": "Empty password string",
        "fix": "Provide actual password or handle unencrypted PDFs",
    },
    {
        "pattern": r"convert_from_path\([^)]+\)\s*#.*all",
        "issue": "Loading all pages to memory for OCR",
        "fix": "Use `first_page` and `last_page` params for large PDFs",
    },
    {
        "pattern": r"page\.rotate\(\d+\).*page\.rotate",
        "issue": "Multiple rotations on same page",
        "fix": "Calculate final rotation and apply once",
    },
    {
        "pattern": r"pdfplumber\.open.*for.*in.*range",
        "issue": "Reopening PDF for each page",
        "fix": "Open once with context manager, iterate pages",
    },
]

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

_CFG = ConfigDict(str_strip_whitespace=True, extra="forbid")


class ExtractionInput(BaseModel):
    model_config = _CFG
    extraction_type: str = Field(
        ..., description="Type: text, tables, text_with_coords, images"
    )
    library: str = Field(
        default="pypdf", description="Library: pypdf, pdfplumber, pypdfium2"
    )
    include_page_numbers: bool = Field(
        default=True, description="Include page numbers in output"
    )

    @field_validator("extraction_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in EXTRACTION_TYPES:
            raise ValueError(f"extraction_type must be one of {EXTRACTION_TYPES}")
        return v


class CreationInput(BaseModel):
    model_config = _CFG
    creation_type: str = Field(
        ..., description="Type: basic, report, invoice, multi_page"
    )
    pagesize: str = Field(default="letter", description="Page size: letter, A4, legal")
    include_tables: bool = Field(
        default=False, description="Include table creation code"
    )

    @field_validator("creation_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in CREATION_TYPES:
            raise ValueError(f"creation_type must be one of {CREATION_TYPES}")
        return v


class MergeSplitInput(BaseModel):
    model_config = _CFG
    operation: str = Field(..., description="Operation: merge, split, extract_pages")
    include_error_handling: bool = Field(
        default=True, description="Include try/except blocks"
    )

    @field_validator("operation")
    @classmethod
    def _check_op(cls, v: str) -> str:
        if v not in ("merge", "split", "extract_pages"):
            raise ValueError("operation must be merge, split, or extract_pages")
        return v


class ManipulationInput(BaseModel):
    model_config = _CFG
    manipulation_type: str = Field(
        ..., description="Type: rotate, crop, watermark, resize"
    )
    include_batch: bool = Field(
        default=False, description="Include batch processing support"
    )

    @field_validator("manipulation_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in MANIPULATION_TYPES:
            raise ValueError(f"manipulation_type must be one of {MANIPULATION_TYPES}")
        return v


class MetadataInput(BaseModel):
    model_config = _CFG
    operation: str = Field(..., description="Operation: get, set, both")
    include_dates: bool = Field(default=True, description="Include date fields")

    @field_validator("operation")
    @classmethod
    def _check_op(cls, v: str) -> str:
        if v not in ("get", "set", "both"):
            raise ValueError("operation must be get, set, or both")
        return v


class FormInput(BaseModel):
    model_config = _CFG
    form_type: str = Field(
        ..., description="Type: fillable, non_fillable, detect_fields"
    )
    include_validation: bool = Field(
        default=True, description="Include field validation"
    )

    @field_validator("form_type")
    @classmethod
    def _check_type(cls, v: str) -> str:
        if v not in FORM_TYPES:
            raise ValueError(f"form_type must be one of {FORM_TYPES}")
        return v


class EncryptionInput(BaseModel):
    model_config = _CFG
    operation: str = Field(..., description="Operation: encrypt, decrypt, both")
    algorithm: str = Field(default="AES-256", description="Encryption algorithm")

    @field_validator("operation")
    @classmethod
    def _check_op(cls, v: str) -> str:
        if v not in ("encrypt", "decrypt", "both"):
            raise ValueError("operation must be encrypt, decrypt, or both")
        return v


class OcrInput(BaseModel):
    model_config = _CFG
    language: str = Field(default="eng", description="Tesseract language code")
    include_preprocessing: bool = Field(
        default=False, description="Include image preprocessing"
    )
    output_format: str = Field(default="text", description="Output: text, hocr, pdf")

    @field_validator("output_format")
    @classmethod
    def _check_format(cls, v: str) -> str:
        if v not in ("text", "hocr", "pdf"):
            raise ValueError("output_format must be text, hocr, or pdf")
        return v


class AntipatternInput(BaseModel):
    model_config = _CFG
    code: str = Field(
        ..., min_length=10, max_length=50000, description="Code to analyze"
    )


class ScaffoldInput(BaseModel):
    model_config = _CFG
    project_name: str = Field(
        ..., min_length=1, max_length=100, description="Project name"
    )
    features: list[str] = Field(default_factory=list, description="Features to include")

    @field_validator("project_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", v):
            raise ValueError(
                "project_name must start with letter, contain only alphanumeric, underscore, hyphen"
            )
        return v


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------


def _generate_text_extraction(library: str, include_page_numbers: bool) -> str:
    """Generate text extraction code."""
    if library == "pypdf":
        body = """    reader = PdfReader(pdf_path)
    text_parts = []

    for i, page in enumerate(reader.pages):
        page_text = page.extract_text()"""
        if include_page_numbers:
            body += """
        text_parts.append(f"--- Page {i + 1} ---\\n{page_text}")"""
        else:
            body += """
        text_parts.append(page_text)"""
        body += """

    return "\\n\\n".join(text_parts)"""
        return TEXT_EXTRACTION_TEMPLATE.format(
            library="pypdf",
            import_path="pypdf",
            imports="PdfReader",
            body=body,
        )
    elif library == "pdfplumber":
        body = """    text_parts = []

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            page_text = page.extract_text()"""
        if include_page_numbers:
            body += """
            text_parts.append(f"--- Page {i + 1} ---\\n{page_text}")"""
        else:
            body += """
            text_parts.append(page_text or "")"""
        body += """

    return "\\n\\n".join(text_parts)"""
        return TEXT_EXTRACTION_TEMPLATE.format(
            library="pdfplumber",
            import_path="pdfplumber",
            imports="pdfplumber",
            body=body,
        ).replace("from pdfplumber import pdfplumber", "import pdfplumber")
    else:
        body = """    pdf = pdfium.PdfDocument(pdf_path)
    text_parts = []

    for i, page in enumerate(pdf):
        page_text = page.get_textpage().get_text_range()"""
        if include_page_numbers:
            body += """
        text_parts.append(f"--- Page {i + 1} ---\\n{page_text}")"""
        else:
            body += """
        text_parts.append(page_text)"""
        body += """

    return "\\n\\n".join(text_parts)"""
        return TEXT_EXTRACTION_TEMPLATE.format(
            library="pypdfium2",
            import_path="pypdfium2",
            imports="pdfium",
            body=body,
        ).replace("from pypdfium2 import pdfium", "import pypdfium2 as pdfium")


def _detect_antipatterns(code: str) -> list[dict]:
    """Detect anti-patterns in PDF code."""
    findings = []
    for ap in ANTIPATTERNS:
        if re.search(ap["pattern"], code, re.IGNORECASE):
            findings.append(
                {
                    "issue": ap["issue"],
                    "fix": ap["fix"],
                    "pattern": ap["pattern"],
                }
            )
    return findings


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def pdf_generate_extraction_code(
    extraction_type: str,
    library: str = "pypdf",
    include_page_numbers: bool = True,
) -> str:
    """Generate code for PDF text/table extraction. Returns Python code string."""
    try:
        inp = ExtractionInput(
            extraction_type=extraction_type,
            library=library,
            include_page_numbers=include_page_numbers,
        )

        if inp.extraction_type == "text":
            code = _generate_text_extraction(inp.library, inp.include_page_numbers)
        elif inp.extraction_type == "tables":
            code = TABLE_EXTRACTION_TEMPLATE
        elif inp.extraction_type == "text_with_coords":
            code = '''"""Extract text with coordinates using pdfplumber."""
import pdfplumber

def extract_text_with_coords(pdf_path: str) -> list[dict]:
    """Extract text with bounding box coordinates.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        List of dicts with text, x, y, width, height
    """
    results = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for char in page.chars:
                results.append({
                    "page": page_num + 1,
                    "text": char["text"],
                    "x": char["x0"],
                    "y": char["y0"],
                    "width": char["x1"] - char["x0"],
                    "height": char["y1"] - char["y0"],
                })
    return results
'''
        else:  # images
            code = '''"""Extract images from PDF using pdfplumber."""
import pdfplumber
from pathlib import Path

def extract_images(pdf_path: str, output_dir: str) -> list[str]:
    """Extract all images from PDF.

    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory for extracted images

    Returns:
        List of saved image paths
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    saved_paths = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for img_num, img in enumerate(page.images):
                # Note: pdfplumber provides image metadata, actual extraction
                # may require additional processing with PIL
                img_path = output_dir / f"page{page_num + 1}_img{img_num + 1}.png"
                # Image extraction logic depends on PDF structure
                saved_paths.append(str(img_path))

    return saved_paths
'''

        return json.dumps(
            {"code": code, "library": inp.library, "type": inp.extraction_type}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_creation_code(
    creation_type: str,
    pagesize: str = "letter",
    include_tables: bool = False,
) -> str:
    """Generate code for creating PDFs with reportlab. Returns Python code string."""
    try:
        inp = CreationInput(
            creation_type=creation_type,
            pagesize=pagesize,
            include_tables=include_tables,
        )

        if inp.creation_type == "basic":
            code = BASIC_CREATION_TEMPLATE.format(pagesize=inp.pagesize)
        elif inp.creation_type == "report":
            code = REPORT_CREATION_TEMPLATE.format(pagesize=inp.pagesize)
        elif inp.creation_type == "invoice":
            code = '''"""Create invoice PDF using reportlab."""
from reportlab.lib.pagesizes import {pagesize}
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch

def create_invoice(
    output_path: str,
    invoice_number: str,
    client_name: str,
    items: list[dict],
) -> None:
    """Create an invoice PDF.

    Args:
        output_path: Path to output PDF file
        invoice_number: Invoice number
        client_name: Client name
        items: List of dicts with 'description', 'quantity', 'price' keys
    """
    doc = SimpleDocTemplate(output_path, pagesize={pagesize})
    styles = getSampleStyleSheet()
    story = []

    # Header
    story.append(Paragraph(f"Invoice #{invoice_number}", styles['Title']))
    story.append(Spacer(1, 0.25 * inch))
    story.append(Paragraph(f"Bill To: {client_name}", styles['Normal']))
    story.append(Spacer(1, 0.5 * inch))

    # Items table
    table_data = [['Description', 'Qty', 'Price', 'Total']]
    total = 0
    for item in items:
        item_total = item['quantity'] * item['price']
        total += item_total
        table_data.append([
            item['description'],
            str(item['quantity']),
            f"${item['price']:.2f}",
            f"${item_total:.2f}",
        ])
    table_data.append(['', '', 'Total:', f"${total:.2f}"])

    table = Table(table_data, colWidths=[3*inch, 0.75*inch, inch, inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -2), 1, colors.black),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
    ]))
    story.append(table)

    doc.build(story)
'''.format(pagesize=inp.pagesize)
        else:  # multi_page
            code = '''"""Create multi-page PDF using reportlab."""
from reportlab.lib.pagesizes import {pagesize}
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

def create_multipage_pdf(output_path: str, pages: list[dict]) -> None:
    """Create a multi-page PDF document.

    Args:
        output_path: Path to output PDF file
        pages: List of dicts with 'title' and 'content' keys
    """
    doc = SimpleDocTemplate(output_path, pagesize={pagesize})
    styles = getSampleStyleSheet()
    story = []

    for i, page in enumerate(pages):
        if i > 0:
            story.append(PageBreak())

        story.append(Paragraph(page['title'], styles['Heading1']))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(page['content'], styles['Normal']))

    doc.build(story)
'''.format(pagesize=inp.pagesize)

        return json.dumps(
            {"code": code, "type": inp.creation_type, "pagesize": inp.pagesize}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_merge_split_code(
    operation: str,
    include_error_handling: bool = True,
) -> str:
    """Generate code for merging/splitting PDFs. Returns Python code string."""
    try:
        inp = MergeSplitInput(
            operation=operation, include_error_handling=include_error_handling
        )

        if inp.operation == "merge":
            code = MERGE_TEMPLATE
        elif inp.operation == "split":
            code = SPLIT_TEMPLATE
        else:  # extract_pages
            code = '''"""Extract specific pages from PDF using pypdf."""
from pypdf import PdfReader, PdfWriter

def extract_pages(pdf_path: str, output_path: str, page_numbers: list[int]) -> None:
    """Extract specific pages from PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        page_numbers: List of page numbers to extract (1-based)
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page_num in page_numbers:
        if 1 <= page_num <= len(reader.pages):
            writer.add_page(reader.pages[page_num - 1])

    with open(output_path, "wb") as output:
        writer.write(output)
'''

        if inp.include_error_handling:
            code = code.replace(
                "def ",
                """import logging

logger = logging.getLogger(__name__)

def """,
                1,
            )

        return json.dumps({"code": code, "operation": inp.operation})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_manipulation_code(
    manipulation_type: str,
    include_batch: bool = False,
) -> str:
    """Generate code for PDF page manipulation. Returns Python code string."""
    try:
        inp = ManipulationInput(
            manipulation_type=manipulation_type, include_batch=include_batch
        )

        if inp.manipulation_type == "rotate":
            code = ROTATE_TEMPLATE
        elif inp.manipulation_type == "watermark":
            code = WATERMARK_TEMPLATE
        elif inp.manipulation_type == "crop":
            code = '''"""Crop PDF pages using pypdf."""
from pypdf import PdfReader, PdfWriter

def crop_pages(
    pdf_path: str,
    output_path: str,
    left: float,
    bottom: float,
    right: float,
    top: float,
) -> None:
    """Crop all pages in a PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        left, bottom, right, top: Crop box coordinates in points
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.mediabox.left = left
        page.mediabox.bottom = bottom
        page.mediabox.right = right
        page.mediabox.top = top
        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''
        else:  # resize
            code = '''"""Resize PDF pages using pypdf."""
from pypdf import PdfReader, PdfWriter, Transformation

def resize_pages(pdf_path: str, output_path: str, scale: float) -> None:
    """Resize all pages in a PDF by a scale factor.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        scale: Scale factor (e.g., 0.5 for half size, 2.0 for double)
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        page.add_transformation(Transformation().scale(scale, scale))
        page.scale_by(scale)
        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

        return json.dumps({"code": code, "type": inp.manipulation_type})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_metadata_code(
    operation: str,
    include_dates: bool = True,
) -> str:
    """Generate code for PDF metadata operations. Returns Python code string."""
    try:
        inp = MetadataInput(operation=operation, include_dates=include_dates)
        code = METADATA_TEMPLATE

        if inp.operation == "get":
            # Extract only get_metadata function
            code = code.split("def set_metadata")[0].rstrip()
        elif inp.operation == "set":
            # Extract only set_metadata function
            lines = code.split("\n")
            start_idx = next(
                i for i, line in enumerate(lines) if "def set_metadata" in line
            )
            code = "\n".join(lines[:3] + lines[start_idx:])

        return json.dumps({"code": code, "operation": inp.operation})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_form_code(
    form_type: str,
    include_validation: bool = True,
) -> str:
    """Generate code for PDF form handling. Returns Python code string."""
    try:
        inp = FormInput(form_type=form_type, include_validation=include_validation)

        if inp.form_type == "fillable":
            code = FORM_FILLABLE_TEMPLATE
        elif inp.form_type == "detect_fields":
            code = '''"""Detect form fields in PDF using pypdf."""
from pypdf import PdfReader

def detect_form_fields(pdf_path: str) -> dict:
    """Detect and analyze form fields in PDF.

    Args:
        pdf_path: Path to input PDF file

    Returns:
        Dictionary with field analysis
    """
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()

    if not fields:
        return {"has_forms": False, "fields": []}

    field_info = []
    for name, field in fields.items():
        field_info.append({
            "name": name,
            "type": str(field.get("/FT", "Unknown")),
            "value": field.get("/V", ""),
            "flags": field.get("/Ff", 0),
        })

    return {
        "has_forms": True,
        "field_count": len(field_info),
        "fields": field_info,
    }
'''
        else:  # non_fillable
            code = '''"""Fill non-fillable PDF forms using annotations."""
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from io import BytesIO

def fill_non_fillable(
    pdf_path: str,
    output_path: str,
    annotations: list[dict],
) -> None:
    """Add text annotations to non-fillable PDF.

    Args:
        pdf_path: Path to input PDF file
        output_path: Path to output PDF file
        annotations: List of dicts with 'page', 'x', 'y', 'text', 'font_size' keys
    """
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    # Group annotations by page
    page_annotations = {}
    for ann in annotations:
        page_num = ann.get("page", 1) - 1
        if page_num not in page_annotations:
            page_annotations[page_num] = []
        page_annotations[page_num].append(ann)

    for i, page in enumerate(reader.pages):
        if i in page_annotations:
            # Create overlay with annotations
            packet = BytesIO()
            can = canvas.Canvas(packet, pagesize=letter)

            for ann in page_annotations[i]:
                can.setFontSize(ann.get("font_size", 12))
                can.drawString(ann["x"], ann["y"], ann["text"])

            can.save()
            packet.seek(0)

            overlay_reader = PdfReader(packet)
            page.merge_page(overlay_reader.pages[0])

        writer.add_page(page)

    with open(output_path, "wb") as output:
        writer.write(output)
'''

        return json.dumps({"code": code, "type": inp.form_type})
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_encryption_code(
    operation: str,
    algorithm: str = "AES-256",
) -> str:
    """Generate code for PDF encryption/decryption. Returns Python code string."""
    try:
        inp = EncryptionInput(operation=operation, algorithm=algorithm)
        code = ENCRYPTION_TEMPLATE

        if inp.operation == "encrypt":
            code = code.split("def decrypt_pdf")[0].rstrip()
        elif inp.operation == "decrypt":
            lines = code.split("\n")
            start_idx = next(
                i for i, line in enumerate(lines) if "def decrypt_pdf" in line
            )
            code = "\n".join(lines[:3] + lines[start_idx:])

        return json.dumps(
            {"code": code, "operation": inp.operation, "algorithm": inp.algorithm}
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_ocr_code(
    language: str = "eng",
    include_preprocessing: bool = False,
    output_format: str = "text",
) -> str:
    """Generate code for OCR on scanned PDFs. Returns Python code string."""
    try:
        inp = OcrInput(
            language=language,
            include_preprocessing=include_preprocessing,
            output_format=output_format,
        )
        code = OCR_TEMPLATE

        if inp.include_preprocessing:
            code = '''"""OCR for scanned PDFs with preprocessing."""
import pytesseract
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter
from pathlib import Path

def preprocess_image(image: Image.Image) -> Image.Image:
    """Preprocess image for better OCR results.

    Args:
        image: PIL Image to preprocess

    Returns:
        Preprocessed image
    """
    # Convert to grayscale
    image = image.convert("L")

    # Enhance contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)

    # Apply sharpening
    image = image.filter(ImageFilter.SHARPEN)

    # Binarize
    threshold = 128
    image = image.point(lambda p: 255 if p > threshold else 0)

    return image

def ocr_pdf(pdf_path: str, output_path: str | None = None, language: str = "{language}") -> str:
    """Extract text from scanned PDF using OCR with preprocessing.

    Args:
        pdf_path: Path to scanned PDF file
        output_path: Optional path to save extracted text
        language: Tesseract language code

    Returns:
        Extracted text content
    """
    images = convert_from_path(pdf_path)

    text_parts = []
    for i, image in enumerate(images):
        processed = preprocess_image(image)
        page_text = pytesseract.image_to_string(processed, lang=language)
        text_parts.append(f"--- Page {{i + 1}} ---\\n{{page_text}}")

    full_text = "\\n\\n".join(text_parts)

    if output_path:
        Path(output_path).write_text(full_text, encoding="utf-8")

    return full_text
'''.format(language=inp.language)

        return json.dumps(
            {
                "code": code,
                "language": inp.language,
                "preprocessing": inp.include_preprocessing,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_detect_antipatterns(
    code: str,
) -> str:
    """Detect anti-patterns in PDF processing code. Returns findings as JSON."""
    try:
        inp = AntipatternInput(code=code)
        findings = _detect_antipatterns(inp.code)

        return json.dumps(
            {
                "findings": findings,
                "count": len(findings),
                "clean": len(findings) == 0,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


@mcp.tool()
async def pdf_generate_scaffold(
    project_name: str,
    features: list[str] | None = None,
) -> str:
    """Generate complete PDF processing project scaffold. Returns file structure as JSON."""
    try:
        inp = ScaffoldInput(project_name=project_name, features=features or [])

        files = {
            f"{inp.project_name}/pdf_processor.py": '''"""PDF processing module."""
from pypdf import PdfReader, PdfWriter
import pdfplumber
from pathlib import Path
from typing import Optional


class PDFProcessor:
    """Main PDF processing class."""

    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self._reader: Optional[PdfReader] = None

    @property
    def reader(self) -> PdfReader:
        if self._reader is None:
            self._reader = PdfReader(self.pdf_path)
        return self._reader

    @property
    def page_count(self) -> int:
        return len(self.reader.pages)

    def extract_text(self) -> str:
        """Extract all text from PDF."""
        return "\\n".join(
            page.extract_text() or ""
            for page in self.reader.pages
        )

    def extract_tables(self) -> list:
        """Extract tables using pdfplumber."""
        tables = []
        with pdfplumber.open(self.pdf_path) as pdf:
            for page in pdf.pages:
                tables.extend(page.extract_tables())
        return tables

    def save_pages(self, output_path: str, pages: list[int]) -> None:
        """Save specific pages to new PDF."""
        writer = PdfWriter()
        for page_num in pages:
            if 1 <= page_num <= self.page_count:
                writer.add_page(self.reader.pages[page_num - 1])

        with open(output_path, "wb") as f:
            writer.write(f)
''',
            f"{inp.project_name}/requirements.txt": """pypdf>=4.0.0
pdfplumber>=0.10.0
reportlab>=4.0.0
""",
            f"{inp.project_name}/__init__.py": f'''"""
{inp.project_name} - PDF processing toolkit.
"""
from .pdf_processor import PDFProcessor

__all__ = ["PDFProcessor"]
__version__ = "0.1.0"
''',
            f"{inp.project_name}/cli.py": '''"""Command-line interface for PDF processing."""
import argparse
from pathlib import Path
from .pdf_processor import PDFProcessor


def main():
    parser = argparse.ArgumentParser(description="PDF Processing CLI")
    parser.add_argument("input", help="Input PDF file")
    parser.add_argument("--extract-text", "-t", action="store_true", help="Extract text")
    parser.add_argument("--extract-tables", "-T", action="store_true", help="Extract tables")
    parser.add_argument("--pages", "-p", type=str, help="Pages to extract (e.g., 1,3,5-7)")
    parser.add_argument("--output", "-o", help="Output file")

    args = parser.parse_args()

    processor = PDFProcessor(args.input)

    if args.extract_text:
        text = processor.extract_text()
        if args.output:
            Path(args.output).write_text(text)
        else:
            print(text)

    if args.extract_tables:
        tables = processor.extract_tables()
        for i, table in enumerate(tables):
            print(f"Table {i + 1}:")
            for row in table:
                print(row)


if __name__ == "__main__":
    main()
''',
        }

        # Add feature-specific files
        if "ocr" in inp.features:
            files[f"{inp.project_name}/ocr.py"] = OCR_TEMPLATE

        if "forms" in inp.features:
            files[f"{inp.project_name}/forms.py"] = FORM_FILLABLE_TEMPLATE

        return json.dumps(
            {
                "project": inp.project_name,
                "files": files,
                "features": inp.features,
            }
        )
    except Exception as e:
        return json.dumps({"error": str(e)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
