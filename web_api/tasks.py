from .celery_app import celery_app
from document_processor.src.orchestrator import process_docx_document, process_pdf_document
import os
import tempfile
import shutil # For cleaning up directories

@celery_app.task(bind=True, name='process_docx_file_task')
def process_docx_file_task(self, input_file_path: str, operations: list[dict], original_filename: str = "processed.docx"):
    """
    Celery task to process a DOCX document.
    Manages a temporary file for the output.
    Returns the path to the processed file or raises an exception on failure.
    """
    temp_output_dir = None # Initialize to ensure it's defined for finally block
    try:
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Input file not found for task: {input_file_path}")

        temp_output_dir = tempfile.mkdtemp(prefix="celery_docx_out_")
        sanitized_filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in original_filename)
        if not sanitized_filename.lower().endswith(".docx"):
            sanitized_filename += ".docx"

        task_output_file_path = os.path.join(temp_output_dir, sanitized_filename)
        
        print(f"Celery task [{self.request.id}]: Processing DOCX '{input_file_path}' with ops: {operations}. Output to: {task_output_file_path}")
        success = process_docx_document(input_file_path, task_output_file_path, operations)

        if success and os.path.exists(task_output_file_path):
            print(f"Celery task [{self.request.id}]: DOCX processing successful. Result at {task_output_file_path}")
            # IMPORTANT: The caller (API endpoint) is now responsible for cleaning up temp_output_dir
            # once it has handled the result_path.
            return {
                "status": "completed",
                "result_path": task_output_file_path, # This is inside temp_output_dir
                "temp_dir_to_cleanup": temp_output_dir, # Pass the dir path for later cleanup by API
                "original_filename": original_filename,
                "message": "DOCX processing completed successfully."
            }
        else:
            print(f"Celery task [{self.request.id}]: DOCX processing reported failure or output file not found.")
            # No need to remove task_output_file_path specifically, as temp_output_dir will be removed.
            raise Exception("DOCX processing failed or output file was not created by orchestrator.")

    except Exception as e:
        print(f"Celery task [{self.request.id}]: Error during DOCX processing - {str(e)}")
        # If an exception occurs, clean up the temp_output_dir created by this task.
        if temp_output_dir and os.path.exists(temp_output_dir):
            try:
                shutil.rmtree(temp_output_dir)
                print(f"Celery task [{self.request.id}]: Cleaned up temporary directory {temp_output_dir} due to exception: {e}")
            except Exception as e_clean_exc:
                print(f"Celery task [{self.request.id}]: Error cleaning up temp directory {temp_output_dir} on exception: {e_clean_exc}")
        raise # Re-raise the exception to mark the task as failed in Celery


@celery_app.task(bind=True, name='process_pdf_file_task')
def process_pdf_file_task(self, input_file_path: str, operations: list[dict], original_filename: str = "processed.pdf"):
    """
    Celery task to process a PDF document.
    Manages a temporary file for the output.
    Returns the path to the processed file or raises an exception on failure.
    """
    temp_output_dir = None # Initialize
    try:
        if not os.path.exists(input_file_path):
            raise FileNotFoundError(f"Input file not found for task: {input_file_path}")

        temp_output_dir = tempfile.mkdtemp(prefix="celery_pdf_out_")
        sanitized_filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in original_filename)
        if not sanitized_filename.lower().endswith(".pdf"):
            sanitized_filename += ".pdf"
            
        task_output_file_path = os.path.join(temp_output_dir, sanitized_filename)

        print(f"Celery task [{self.request.id}]: Processing PDF '{input_file_path}' with ops: {operations}. Output to: {task_output_file_path}")
        success = process_pdf_document(input_file_path, task_output_file_path, operations)

        if success and os.path.exists(task_output_file_path):
            print(f"Celery task [{self.request.id}]: PDF processing successful. Result at {task_output_file_path}")
            # IMPORTANT: The caller (API endpoint) is now responsible for cleaning up temp_output_dir
            return {
                "status": "completed",
                "result_path": task_output_file_path, # This is inside temp_output_dir
                "temp_dir_to_cleanup": temp_output_dir, # Pass the dir path for later cleanup by API
                "original_filename": original_filename,
                "message": "PDF processing completed successfully."
            }
        else:
            print(f"Celery task [{self.request.id}]: PDF processing reported failure or output file not found.")
            raise Exception("PDF processing failed or output file was not created by orchestrator.")
    except Exception as e:
        print(f"Celery task [{self.request.id}]: Error during PDF processing - {str(e)}")
        if temp_output_dir and os.path.exists(temp_output_dir):
            try:
                shutil.rmtree(temp_output_dir)
                print(f"Celery task [{self.request.id}]: Cleaned up temporary directory {temp_output_dir} due to exception: {e}")
            except Exception as e_clean_exc:
                print(f"Celery task [{self.request.id}]: Error cleaning up temp directory {temp_output_dir} on exception: {e_clean_exc}")
        raise
