from .file_handler import read_docx_text, read_pdf_text, split_document
from .layout_editor import layout_converter_docx, set_page_size_docx
from .pdf_layout_editor import rotate_pdf_pages, resize_and_margin_pdf_content
from .design_editor_docx import (
    set_page_color_docx,
    set_text_color_docx,
    set_font_properties_docx,
    add_simple_page_numbers_docx,
    bold_keywords_docx
)
from .design_editor_pdf import (
    set_page_color_pdf,
    set_text_color_pdf,
    set_font_properties_pdf,
    add_page_numbers_pdf
)
from .content_analyzer import (
    correct_obvious_misspellings, 
    detect_potentially_awkward_phrases, 
    generate_placeholder_headings,
    list_keywords_pdf
)
from .orchestrator import process_docx_document, process_pdf_document # Added
