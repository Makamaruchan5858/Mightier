# Needs: pip install python-docx
import docx

def read_docx_text(file_path: str) -> str:
    """Reads text content from a .docx file."""
    try:
        doc = docx.Document(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        return '\n'.join(full_text)
    except Exception as e:
        print(f"Error reading DOCX file {file_path}: {e}")
        return ""

# Needs: pip install PyPDF2
from PyPDF2 import PdfReader

def read_pdf_text(file_path: str) -> str:
    """Reads text content from a .pdf file."""
    text = ""
    try:
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() if page.extract_text() else ""
        return text
    except Exception as e:
        print(f"Error reading PDF file {file_path}: {e}")
        return ""

def split_document(text: str, max_length: int = 300000) -> list[str]:
    """Splits a document into chunks of specified maximum length."""
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]
