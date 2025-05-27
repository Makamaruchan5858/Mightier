from PyPDF2 import PdfReader, PdfWriter
from PyPDF2.generic import RectangleObject
# from PyPDF2.Transformation import Transformation # Not explicitly used in the final provided code

# For set_page_color_pdf and add_page_numbers_pdf, ReportLab components are imported within the function
# to handle potential ImportError more gracefully if ReportLab is not installed.

def hex_to_rgb_float(hex_color):
    """Converts a 6-digit hex color to a tuple of (r, g, b) floats between 0 and 1."""
    if len(hex_color) == 7 and hex_color.startswith('#'):
        hex_color = hex_color[1:]
    if len(hex_color) != 6:
        raise ValueError("Hex color must be 6 digits (e.g., RRGGBB or #RRGGBB)")
    try:
        r = int(hex_color[0:2], 16) / 255.0
        g = int(hex_color[2:4], 16) / 255.0
        b = int(hex_color[4:6], 16) / 255.0
        return r, g, b
    except ValueError:
        raise ValueError(f"Invalid character in hex color string: {hex_color}")


def set_page_color_pdf(pdf_path: str, output_path: str, page_hex_color: str):
    """
    Sets the page background color for a PDF.
    It creates a new page with the specified background color using ReportLab,
    and then merges the original page content on top of this colored background.
    Saves the modified PDF to output_path.
    """
    try:
        from reportlab.pdfgen import canvas
        # from reportlab.lib.pagesizes import A4 # Not needed directly as we use original page dimensions
        from reportlab.lib.colors import Color as ReportLabColor # Renamed to avoid conflict
        import io

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        
        r_float, g_float, b_float = hex_to_rgb_float(page_hex_color)

        for original_page in reader.pages:
            media_box = original_page.mediabox
            page_width = float(media_box.width)
            page_height = float(media_box.height)

            # Create a colored page using ReportLab
            packet = io.BytesIO()
            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            can.setFillColorRGB(r_float, g_float, b_float)
            can.rect(0, 0, page_width, page_height, fill=1, stroke=0)
            can.save()
            packet.seek(0)
            
            color_pdf_reader = PdfReader(packet)
            color_page = color_pdf_reader.pages[0]
            
            # Create a new blank page in the writer with the correct dimensions
            # This will be our "final" page for this iteration
            final_page_for_writer = PdfWriter().add_blank_page(width=page_width, height=page_height)
            
            # Merge the colored page (as background) onto our new blank page
            final_page_for_writer.merge_page(color_page)
            # Then, merge the original page's content on top of the colored background
            final_page_for_writer.merge_page(original_page) 
            
            writer.add_page(final_page_for_writer)

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        print(f"PDF page color set using ReportLab for background and saved to {output_path}")
        return True

    except ImportError:
        print("ReportLab is not installed. Page color setting for PDF requires ReportLab.")
        print("Please run: pip install reportlab")
        return False
    except Exception as e:
        print(f"Error setting PDF page color: {e}")
        # import traceback
        # traceback.print_exc()
        return False

def set_text_color_pdf(pdf_path: str, output_path: str, hex_color: str):
    print("INFO: Setting text color for existing arbitrary PDF content is a highly complex operation "
          "and not reliably achievable with PyPDF2 or ReportLab. "
          "This would require specialized PDF parsing and rewriting libraries (e.g., PyMuPDF/fitz or commercial SDKs). "
          "This function is a placeholder and will not modify text colors.")
    import shutil
    try:
        shutil.copy(pdf_path, output_path)
        return False # Indicates no operation was truly performed
    except Exception as e:
        print(f"Error copying file in set_text_color_pdf: {e}")
        return False


def set_font_properties_pdf(pdf_path: str, output_path: str, font_name: str = None, font_size_pt: float = None):
    print("INFO: Changing font properties (name, size) for existing arbitrary PDF content is a "
          "highly complex operation and not reliably achievable with PyPDF2 or ReportLab. "
          "This would require specialized PDF parsing, font handling, and rewriting libraries. "
          "This function is a placeholder and will not modify fonts.")
    import shutil
    try:
        shutil.copy(pdf_path, output_path)
        return False # Indicates no operation was truly performed
    except Exception as e:
        print(f"Error copying file in set_font_properties_pdf: {e}")
        return False


def add_page_numbers_pdf(pdf_path: str, output_path: str,
                         font_name: str = "Helvetica", font_size_pt: int = 10,
                         text_hex_color: str = "000000",
                         position_bottom_mm: float = 10, position_center_x: bool = True, position_right_mm: float = None):
    """
    Adds page numbers to each page of a PDF document using ReportLab to create overlays.
    Saves the modified PDF to output_path.
    If position_center_x is True, numbers are centered. Otherwise, position_right_mm from right edge is used.
    """
    try:
        from reportlab.pdfgen import canvas
        # from reportlab.lib.pagesizes import A4 # Not needed as we use actual page size
        from reportlab.lib.units import mm
        from reportlab.lib.colors import HexColor as ReportLabHexColor # Renamed
        import io

        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        num_pages = len(reader.pages)

        if num_pages == 0:
            print("Warning: PDF has no pages. No page numbers will be added.")
            # Copy original to output if no pages
            import shutil
            shutil.copy(pdf_path, output_path)
            return True


        for i, page in enumerate(reader.pages):
            packet = io.BytesIO()
            media_box = page.mediabox # Get mediabox from the page object itself
            page_width = float(media_box.width)  # in points
            page_height = float(media_box.height) # in points

            can = canvas.Canvas(packet, pagesize=(page_width, page_height))
            
            # Validate and set text color
            if not (len(text_hex_color) == 6 and all(c in '0123456789abcdefABCDEF' for c in text_hex_color)):
                print(f"Warning: Invalid text_hex_color '{text_hex_color}'. Defaulting to black.")
                valid_text_hex_color = "000000"
            else:
                valid_text_hex_color = text_hex_color
            can.setFillColor(ReportLabHexColor(f"#{valid_text_hex_color}"))

            can.setFont(font_name, font_size_pt)
            
            page_number_text = f"{i + 1}" # Simple page number, add / num_pages for "Page X of Y"
            # Example for "Page X of Y":
            # page_number_text = f"Page {i + 1} of {num_pages}"


            text_width = can.stringWidth(page_number_text, font_name, font_size_pt)
            
            y_position = position_bottom_mm * mm # From bottom of the page

            if position_center_x:
                x_position = (page_width - text_width) / 2
            elif position_right_mm is not None:
                x_position = page_width - (position_right_mm * mm) - text_width
            else: # Default to a sensible left margin if neither center nor right is specified
                x_position = 10 * mm # Default left margin for page number, e.g., ~35 points

            can.drawString(x_position, y_position, page_number_text)
            can.save()
            packet.seek(0)
            
            watermark_pdf_reader = PdfReader(packet)
            watermark_page = watermark_pdf_reader.pages[0]
            
            # Merge the watermark (page number) onto the original page
            page.merge_page(watermark_page) # Overlay watermark_page onto original page
            writer.add_page(page) # Add the modified page to the writer

        with open(output_path, "wb") as f_out:
            writer.write(f_out)
        print(f"PDF page numbers added and saved to {output_path}")
        return True
    except ImportError:
        print("ReportLab is not installed. Page numbering for PDF requires ReportLab.")
        print("Please run: pip install reportlab")
        return False
    except Exception as e:
        print(f"Error adding PDF page numbers: {e}")
        # import traceback
        # traceback.print_exc()
        return False
