import argparse
import json
import os
import sys

# Ensure the parent directory of `document_processor` is in PYTHONPATH if running script directly
# For `python -m document_processor.main`, this is handled automatically.
# For direct execution `python document_processor/main.py`, this might be needed if `document_processor`
# parent is not in sys.path.
# One way to ensure relative imports work when script is run directly:
# if __package__ is None and not hasattr(sys, "frozen"):
#     # direct execution (not via -m)
#     parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     if parent_dir not in sys.path:
#         sys.path.insert(0, parent_dir)

# Assuming execution via `python -m document_processor.main` or parent in PYTHONPATH
from .src.orchestrator import process_docx_document, process_pdf_document

def main():
    parser = argparse.ArgumentParser(description="Process DOCX and PDF documents.")
    parser.add_argument("input_file", help="Path to the input document (DOCX or PDF).")
    parser.add_argument("output_file", help="Path to save the processed document.")
    parser.add_argument("operations_file", help="Path to a JSON file defining the operations to perform.")
    
    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        return

    if not os.path.exists(args.operations_file):
        print(f"Error: Operations JSON file not found: {args.operations_file}")
        return

    try:
        with open(args.operations_file, 'r', encoding='utf-8') as f:
            operations_config = json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from operations file: {args.operations_file}")
        return
    except Exception as e:
        print(f"Error reading operations file: {e}")
        return
    
    operations_list = []
    if isinstance(operations_config, list):
        operations_list = operations_config
    elif isinstance(operations_config, dict) and "operations" in operations_config:
        # This handles cases where the JSON might be a dict with an "operations" key
        # as discussed in the prompt, though the example JSON is a direct list.
        operations_list = operations_config["operations"]
    else:
        print("Error: Operations JSON must be a list of operations or a dictionary with an 'operations' key that holds a list.")
        return

    if not operations_list:
        print("No operations defined in the JSON file.")
        # Optionally, copy input to output if no operations
        # shutil.copy(args.input_file, args.output_file)
        return

    file_extension = os.path.splitext(args.input_file)[1].lower()

    print(f"Processing file: {args.input_file} -> {args.output_file}")
    if file_extension == ".docx":
        success = process_docx_document(args.input_file, args.output_file, operations_list)
    elif file_extension == ".pdf":
        success = process_pdf_document(args.input_file, args.output_file, operations_list)
    else:
        print(f"Error: Unsupported file type: {file_extension}. Only .docx and .pdf are supported.")
        return
    
    if success:
        print(f"Processing finished. Output saved to {args.output_file}")
    else:
        print(f"Processing encountered errors. Output might be incomplete or at {args.output_file}")

if __name__ == "__main__":
    # This allows the script to be run directly, e.g., python document_processor/main.py
    # For relative imports like `.src.orchestrator` to work consistently when running
    # as `python document_processor/main.py`, the Python interpreter needs to know that
    # `document_processor` is a package. This usually means the directory *containing*
    # `document_processor` must be in `sys.path`.
    # If you run `python -m document_processor.main`, Python handles this correctly.
    # The sys.path manipulation at the top is a common pattern for direct script execution,
    # but it's often better to rely on proper PYTHONPATH setup or `-m` execution.
    # For this project, we'll assume `python -m document_processor.main` or that PYTHONPATH is correctly set.
    main()
