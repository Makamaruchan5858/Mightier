from PyPDF2 import PdfReader, PdfWriter, Transformation
from PyPDF2.generic import RectangleObject # For page size

# Standard page sizes in points (1 inch = 72 points)
# Using points as it's native to PDF. 1 mm = 2.83465 points
MM_TO_POINTS = 2.83465
PAGE_SIZES_POINTS = {
    "A4": (210 * MM_TO_POINTS, 297 * MM_TO_POINTS),
    "B5": (182 * MM_TO_POINTS, 257 * MM_TO_POINTS),
    "LETTER": (215.9 * MM_TO_POINTS, 279.4 * MM_TO_POINTS),
    "LEGAL": (215.9 * MM_TO_POINTS, 355.6 * MM_TO_POINTS),
    "SHIROKUBAN": (127 * MM_TO_POINTS, 188 * MM_TO_POINTS),
    "BUNKO": (105 * MM_TO_POINTS, 148 * MM_TO_POINTS),
}

def rotate_pdf_pages(pdf_path: str, output_path: str, rotation_degrees: int = 90):
    """
    Rotates all pages in a PDF by the specified degrees (clockwise).
    Common values: 90, 180, 270.
    Saves the modified PDF to output_path.
    """
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        for page in reader.pages:
            # The rotate method rotates clockwise.
            page.rotate(rotation_degrees)
            writer.add_page(page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        print(f"PDF pages rotated by {rotation_degrees} degrees and saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error rotating PDF pages: {e}")
        return False

def resize_and_margin_pdf_content(pdf_path: str, output_path: str,
                                  target_size_identifier: str = None,
                                  custom_target_size_mm: tuple = None, # (width, height)
                                  margins_mm: dict = None): # {'top': 20, 'left': 30 ...}
    """
    Resizes PDF pages (by creating new pages of target_size) and applies margins
    by scaling and repositioning the content of original pages.
    'target_size_identifier' can be a key from PAGE_SIZES_POINTS (e.g., "A4").
    'custom_target_size_mm' is a (width, height) tuple in mm.
    'margins_mm' is a dict with 'top', 'bottom', 'left', 'right' keys in mm.
    Saves the modified PDF to output_path.
    """
    try:
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        target_width_pt, target_height_pt = None, None

        if target_size_identifier and target_size_identifier.upper() in PAGE_SIZES_POINTS:
            target_width_pt, target_height_pt = PAGE_SIZES_POINTS[target_size_identifier.upper()]
        elif custom_target_size_mm and len(custom_target_size_mm) == 2:
            target_width_pt = custom_target_size_mm[0] * MM_TO_POINTS
            target_height_pt = custom_target_size_mm[1] * MM_TO_POINTS
        
        if target_width_pt is None or target_height_pt is None:
            if not reader.pages:
                print("Error: PDF has no pages.")
                return False
            original_first_page = reader.pages[0]
            target_width_pt = original_first_page.mediabox.width
            target_height_pt = original_first_page.mediabox.height


        m_top_pt = margins_mm.get('top', 0) * MM_TO_POINTS if margins_mm else 0
        m_bottom_pt = margins_mm.get('bottom', 0) * MM_TO_POINTS if margins_mm else 0
        m_left_pt = margins_mm.get('left', 0) * MM_TO_POINTS if margins_mm else 0
        m_right_pt = margins_mm.get('right', 0) * MM_TO_POINTS if margins_mm else 0

        content_area_width = float(target_width_pt) - m_left_pt - m_right_pt
        content_area_height = float(target_height_pt) - m_top_pt - m_bottom_pt

        if content_area_width <= 0 or content_area_height <= 0:
            print("Error: Margins are too large for the target page size.")
            return False

        for original_page in reader.pages:
            new_page = writer.add_blank_page(width=target_width_pt, height=target_height_pt)

            orig_width = original_page.mediabox.width
            orig_height = original_page.mediabox.height
            
            if orig_width == 0 or orig_height == 0: # Skip if original page has no dimensions
                print(f"Skipping page {reader.pages.index(original_page)} due to zero dimensions.")
                continue

            scale_w = content_area_width / float(orig_width)
            scale_h = content_area_height / float(orig_height)
            scale_factor = min(scale_w, scale_h) 

            scaled_content_width = float(orig_width) * scale_factor
            scaled_content_height = float(orig_height) * scale_factor
            
            tx = m_left_pt
            # PDF Y-coordinate is from bottom-left. Content is placed starting from its bottom-left.
            # To align to top-left of margin box:
            # Top of content = target_height_pt - m_top_pt
            # Bottom of content = target_height_pt - m_top_pt - scaled_content_height
            ty = target_height_pt - m_top_pt - scaled_content_height
            
            # Centering (optional, uncomment to use)
            # tx = m_left_pt + (content_area_width - scaled_content_width) / 2
            # ty = m_bottom_pt + (content_area_height - scaled_content_height) / 2


            transformation = Transformation().scale(scale_factor).translate(tx, ty)
            try:
                new_page.merge_transformed_page(original_page, transformation)
            except AttributeError:
                # Fallback for older PyPDF2 versions
                original_page.add_transformation(transformation)
                new_page.merge_page(original_page)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        print(f"PDF content resized/margined and saved to {output_path}")
        return True
    except Exception as e:
        print(f"Error resizing/margining PDF content: {e}")
        import traceback
        traceback.print_exc()
        return False
