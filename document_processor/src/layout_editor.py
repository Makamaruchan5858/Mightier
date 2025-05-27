from docx import Document
from docx.shared import Mm
from docx.enum.section import WD_ORIENT

def change_orientation_docx(doc: Document):
    """Swaps the page orientation of a DOCX document (Portrait <-> Landscape)."""
    for section in doc.sections:
        current_width = section.page_width
        current_height = section.page_height
        section.orientation = WD_ORIENT.LANDSCAPE if current_width < current_height else WD_ORIENT.PORTRAIT
        # Important: After changing orientation, page_width and page_height are automatically swapped by python-docx
        # So, if you want to manually set them after orientation change, do it here.
        # However, for a simple swap, changing section.orientation might be enough if it also swaps them.
        # If not, we explicitly set them:
        section.page_width = current_height
        section.page_height = current_width


def set_margins_docx(doc: Document, top_mm: float, bottom_mm: float, left_mm: float, right_mm: float):
    """Sets the page margins for a DOCX document in millimeters."""
    for section in doc.sections:
        section.top_margin = Mm(top_mm)
        section.bottom_margin = Mm(bottom_mm)
        section.left_margin = Mm(left_mm)
        section.right_margin = Mm(right_mm)

def layout_converter_docx(doc_path: str, output_path: str, orientation_change: bool = False, margins: dict = None):
    """
    Applies layout conversions to a DOCX document.
    Currently supports orientation change and margin setting.
    'margins' should be a dict like {'top': 20, 'bottom': 20, 'left': 30, 'right': 30} in mm.
    Saves the modified document to output_path.
    """
    try:
        doc = Document(doc_path)

        if orientation_change:
            change_orientation_docx(doc)

        if margins:
            set_margins_docx(doc,
                             margins.get('top', 20),    # Default if not provided
                             margins.get('bottom', 20),
                             margins.get('left', 30),
                             margins.get('right', 30))
        
        doc.save(output_path)
        print(f"DOCX layout conversion applied and saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error in layout_converter_docx: {e}")
        return False

# Common page sizes in mm (Width, Height)
PAGE_SIZES_MM = {
    "A4": (210, 297),
    "B5": (182, 257),
    "A3": (297, 420),
    "A5": (148, 210),
    "LETTER": (215.9, 279.4),
    "LEGAL": (215.9, 355.6),
    # Add more JIS sizes as needed: https://www.w3.org/TR/css-page-3/#typedef-page-size-page-size
    # For example, 'JIS-B4': (257, 364), 'JIS-B5': (182, 257) - B5 is already there
    "SHIROKUBAN": (127, 188), # 四六判 approx
    "BUNKO": (105, 148),      # 文庫判 approx
}

def set_page_size_docx(doc_path: str, output_path: str, size_identifier):
    """
    Sets the page size for a DOCX document.
    'size_identifier' can be a string key from PAGE_SIZES_MM (e.g., "A4", "B5")
    or a tuple (width_mm, height_mm).
    Saves the modified document to output_path.
    """
    try:
        doc = Document(doc_path)
        
        new_width_mm, new_height_mm = None, None

        if isinstance(size_identifier, str) and size_identifier.upper() in PAGE_SIZES_MM:
            new_width_mm, new_height_mm = PAGE_SIZES_MM[size_identifier.upper()]
        elif isinstance(size_identifier, tuple) and len(size_identifier) == 2:
            new_width_mm, new_height_mm = size_identifier
        else:
            print(f"Invalid size_identifier: {size_identifier}. Provide a known key or (width, height) tuple in mm.")
            return False

        if new_width_mm is not None and new_height_mm is not None:
            for section in doc.sections:
                # Check current orientation to apply new dimensions correctly
                is_landscape = section.orientation == WD_ORIENT.LANDSCAPE # or section.page_width > section.page_height
                
                if is_landscape: # If landscape, the user expects width_mm to be the larger dimension on page
                    section.page_height = Mm(min(new_width_mm, new_height_mm))
                    section.page_width = Mm(max(new_width_mm, new_height_mm))
                else: # If portrait
                    section.page_width = Mm(min(new_width_mm, new_height_mm))
                    section.page_height = Mm(max(new_width_mm, new_height_mm))
                
                # If a specific orientation is desired with the new size, it should be set explicitly.
                # For now, we maintain the existing orientation and apply the new dimensions.

        doc.save(output_path)
        print(f"DOCX page size set to {size_identifier} and saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error in set_page_size_docx: {e}")
        return False
