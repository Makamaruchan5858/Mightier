import os
import shutil
from .file_handler import read_docx_text, read_pdf_text # Assuming __init__.py makes these available
from .layout_editor import layout_converter_docx, set_page_size_docx
from .design_editor_docx import (
    set_page_color_docx,
    set_text_color_docx,
    set_font_properties_docx,
    add_simple_page_numbers_docx,
    bold_keywords_docx
)
from .content_analyzer import (
    correct_obvious_misspellings,
    detect_potentially_awkward_phrases, # For keyword extraction
    generate_placeholder_headings, # Not used in pipeline directly, but part of content_analyzer
    list_keywords_pdf # Not used in PDF modification pipeline directly
)
from .pdf_layout_editor import rotate_pdf_pages, resize_and_margin_pdf_content
from .design_editor_pdf import (
    set_page_color_pdf,
    add_page_numbers_pdf
    # set_text_color_pdf, set_font_properties_pdf are placeholders and not used in modification pipeline
)

def process_docx_document(input_path: str, output_path: str, operations: list[dict]):
    """
    Applies a series of operations to a DOCX document.

    Args:
        input_path (str): Path to the input DOCX file.
        output_path (str): Path to save the processed DOCX file.
        operations (list[dict]): A list of operation dictionaries. Each dict specifies
                                 the function to call and its parameters.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input DOCX file not found at {input_path}")
        return False

    base_dir = os.path.dirname(output_path)
    if not base_dir: # Handle cases where output_path is just a filename in current dir
        base_dir = "."
    temp_dir = os.path.join(base_dir, "temp_docx_processing")
    os.makedirs(temp_dir, exist_ok=True)
    
    current_path = os.path.join(temp_dir, "temp_initial_copy.docx")
    shutil.copy(input_path, current_path)
    
    processed_successfully = True # Tracks success of current operation

    extracted_keywords = [] # Store keywords if extracted

    for i, op in enumerate(operations):
        op_type = op.get("type")
        temp_output_path = os.path.join(temp_dir, f"temp_step_{i+1}_{op_type}.docx") # Retaining more descriptive name
        print(f"Applying DOCX operation: {op_type} (Input: {current_path}, Output: {temp_output_path})")

        if op_type == "layout_convert":
            processed_successfully = layout_converter_docx(
                current_path, temp_output_path,
                orientation_change=op.get("orientation_change", False),
                margins=op.get("margins")
            )
        elif op_type == "set_page_size":
            processed_successfully = set_page_size_docx(current_path, temp_output_path, op.get("size_identifier"))
        elif op_type == "set_page_color":
            processed_successfully = set_page_color_docx(current_path, temp_output_path, op.get("hex_color"))
        elif op_type == "set_text_color":
            processed_successfully = set_text_color_docx(current_path, temp_output_path, op.get("hex_color"))
        elif op_type == "set_font_properties":
            processed_successfully = set_font_properties_docx(
                current_path, temp_output_path,
                font_name=op.get("font_name"),
                font_size_pt=op.get("font_size_pt")
            )
        elif op_type == "add_page_numbers":
            processed_successfully = add_simple_page_numbers_docx(current_path, temp_output_path)
        elif op_type == "correct_misspellings":
            print(f"WARNING: correct_misspellings for DOCX is complex with current structure. "
                  f"This operation implies text extraction, correction, and then careful re-insertion "
                  f"into the DOCX structure, which is not fully implemented for direct DOCX modification. "
                  f"Copying file for now as a placeholder for this step.")
            # text_content = read_docx_text(current_path)
            # corrected_text = correct_obvious_misspellings(text_content, lang=op.get("lang", "ja"))
            # TODO: Need a function: apply_corrected_text_to_docx(current_path, temp_output_path, corrected_text_map_or_logic)
            shutil.copy(current_path, temp_output_path)
            processed_successfully = True # Placeholder
        
        elif op_type == "extract_keywords_for_bolding":
            if not extracted_keywords: # Only extract once or if forced
                text_content = read_docx_text(current_path)
                if text_content:
                    phrases_data = detect_potentially_awkward_phrases(
                        text_content, 
                        lang=op.get("lang", "ja"), 
                        top_n_keyterms=op.get("top_n", 20)
                    )
                    # Filter for keyterms identified by SGRank (score >= 0)
                    extracted_keywords = [item["phrase"] for item in phrases_data if item.get("score", -1.0) >= 0]
                    print(f"Extracted keywords for bolding: {extracted_keywords}")
                else:
                    print("Warning: Could not read DOCX text for keyword extraction.")
            shutil.copy(current_path, temp_output_path) # This operation doesn't modify the doc itself
            processed_successfully = True

        elif op_type == "bold_keywords":
            keywords_to_bold = op.get("keywords_list")
            if op.get("use_extracted", False) and extracted_keywords:
                print(f"Using {len(extracted_keywords)} extracted keywords for bolding.")
                keywords_to_bold = extracted_keywords
            
            if keywords_to_bold:
                processed_successfully = bold_keywords_docx(current_path, temp_output_path, keywords_to_bold)
            else:
                print("No keywords specified or extracted for bolding. Skipping DOCX bolding.")
                shutil.copy(current_path, temp_output_path)
                processed_successfully = True
        else:
            print(f"Unknown DOCX operation type: {op_type}. Skipping and copying file.")
            shutil.copy(current_path, temp_output_path)
            processed_successfully = False # Mark as not successfully processed by a known op

        if not processed_successfully:
            print(f"Operation {op_type} failed or was skipped. Output may not be as expected.")
            # If the operation function failed and didn't produce an output file,
            # we must ensure temp_output_path exists for the next step by copying the input of this failed step.
            if not os.path.exists(temp_output_path):
                 print(f"Operation {op_type} did not create an output file. Copying input {current_path} to {temp_output_path}.")
                 shutil.copy(current_path, temp_output_path)
        
        current_path = temp_output_path # Next operation reads from this output

    # Final step: copy the last processed file to the actual output_path
    shutil.copy(current_path, output_path)
    print(f"DOCX processing complete. Output saved to {output_path}")
    
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
    
    return True


def process_pdf_document(input_path: str, output_path: str, operations: list[dict]):
    """
    Applies a series of operations to a PDF document.
    Manages temporary files for sequential operations.
    """
    if not os.path.exists(input_path):
        print(f"Error: Input PDF file not found at {input_path}")
        return False

    base_dir = os.path.dirname(output_path)
    if not base_dir:
        base_dir = "."
    temp_dir = os.path.join(base_dir, "temp_pdf_processing")
    os.makedirs(temp_dir, exist_ok=True)
    
    current_path = os.path.join(temp_dir, "temp_initial_copy.pdf")
    shutil.copy(input_path, current_path)
    
    processed_successfully = True # Tracks success of current operation

    for i, op in enumerate(operations):
        op_type = op.get("type")
        temp_output_path = os.path.join(temp_dir, f"temp_step_{i+1}_{op_type}.pdf") # Retaining more descriptive name
        print(f"Applying PDF operation: {op_type} (Input: {current_path}, Output: {temp_output_path})")

        if op_type == "rotate_pages":
            processed_successfully = rotate_pdf_pages(
                current_path, temp_output_path, 
                rotation_degrees=op.get("rotation_degrees", 90)
            )
        elif op_type == "resize_and_margin":
            processed_successfully = resize_and_margin_pdf_content(
                current_path, temp_output_path,
                target_size_identifier=op.get("target_size_identifier"),
                custom_target_size_mm=op.get("custom_target_size_mm"),
                margins_mm=op.get("margins_mm")
            )
        elif op_type == "set_page_color":
            processed_successfully = set_page_color_pdf(current_path, temp_output_path, op.get("page_hex_color"))
        elif op_type == "add_page_numbers":
            processed_successfully = add_page_numbers_pdf(
                current_path, temp_output_path,
                font_name=op.get("font_name", "Helvetica"),
                font_size_pt=op.get("font_size_pt", 10),
                text_hex_color=op.get("text_hex_color", "000000"),
                position_bottom_mm=op.get("position_bottom_mm", 10),
                position_center_x=op.get("position_center_x", True),
                position_right_mm=op.get("position_right_mm")
            )
        # Note: Spell checking (correct_obvious_misspellings), keyword listing (list_keywords_pdf),
        # and awkward phrase detection (detect_potentially_awkward_phrases) for PDF are text analysis functions.
        # They operate on extracted text and do not modify the PDF structure itself.
        # Thus, they are not included as modification steps in this PDF pipeline.
        # Similarly, set_text_color_pdf and set_font_properties_pdf are placeholders and don't modify.
        else:
            print(f"Unknown PDF operation type: {op_type}. Skipping and copying file.")
            shutil.copy(current_path, temp_output_path)
            processed_successfully = False
        
        if not processed_successfully:
            print(f"Operation {op_type} failed or was skipped. Output may not be as expected.")
            if not os.path.exists(temp_output_path):
                print(f"Operation {op_type} did not create an output file. Copying input {current_path} to {temp_output_path}.")
                shutil.copy(current_path, temp_output_path)

        current_path = temp_output_path
    
    shutil.copy(current_path, output_path)
    print(f"PDF processing complete. Output saved to {output_path}")
    
    try:
        shutil.rmtree(temp_dir)
    except Exception as e:
        print(f"Warning: Could not remove temporary directory {temp_dir}: {e}")
    
    return True
