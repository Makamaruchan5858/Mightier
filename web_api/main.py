import uvicorn # For type hinting and direct execution if needed, though uvicorn command is preferred
import os
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, List

from fastapi import FastAPI, File, UploadFile, HTTPException, Path, Body
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.background import BackgroundTask

from pydantic import BaseModel, Field

# Import Celery tasks
from .tasks import process_docx_file_task, process_pdf_file_task
from celery.result import AsyncResult # For job status
from .celery_app import celery_app # Import the Celery app instance

app = FastAPI(
    title="Document Processor API",
    description="API for processing DOCX and PDF documents.",
    version="0.1.0"
)

# This will be replaced by serve_frontend_ui later in the file
# @app.get("/", tags=["General"])
# async def read_root():
#     return {"message": "Welcome to the Document Processor API!"}

@app.get("/ping", tags=["General"])
async def ping():
    """Simple health check endpoint."""
    return {"ping": "pong"}
import shutil
import uuid
from datetime import datetime
from typing import Dict, Any, List # Added List for ProcessRequest

UPLOAD_DIRECTORY = os.path.join(os.path.dirname(__file__), "uploaded_files")
MAX_FILE_SIZE_MB = 50  # Max file size in Megabytes
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".docx", ".pdf"}

# In-memory database for uploaded files metadata
uploaded_files_db: Dict[str, Dict[str, Any]] = {}

# In-memory database for job status and results
jobs_db: Dict[str, Dict[str, Any]] = {}

# Ensure upload directory exists (already created in a previous step, but good to have here for robustness)
os.makedirs(UPLOAD_DIRECTORY, exist_ok=True)

class ProcessRequest(BaseModel):
    operations: List[Dict[str, Any]] = Field(..., example=[{"type": "set_page_size", "size_identifier": "A4"}])
    output_filename: str = Field(None, description="Optional suggested output filename with extension.")


@app.post("/upload", status_code=201, tags=["File Operations"])
async def upload_file(file: UploadFile = File(...)): # File is now correctly imported
    """
    Uploads a document file (.docx or .pdf) for processing.
    Stores the file temporarily and returns a file_id.
    """
    original_filename = file.filename
    file_extension = os.path.splitext(original_filename)[1].lower()

    if not original_filename:
        raise HTTPException(status_code=400, detail="No filename provided.")

    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}. Allowed: {list(ALLOWED_EXTENSIONS)}")
    
    contents = await file.read() # Read file content
    file_size = len(contents) # Get size from read content

    if file_size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded.")
    
    if file_size > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File size exceeds the maximum limit of {MAX_FILE_SIZE_MB} MB.")

    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}{file_extension}"
    saved_file_path = os.path.join(UPLOAD_DIRECTORY, saved_filename)

    try:
        with open(saved_file_path, "wb") as buffer:
            buffer.write(contents) # Write the already read contents
    except Exception as e:
        print(f"Error saving file: {e}") # Basic logging
        raise HTTPException(status_code=500, detail="An unexpected error occurred while saving the file.")
    finally:
        await file.close() # Ensure the uploaded file is closed

    # Store metadata
    uploaded_files_db[file_id] = {
        "file_id": file_id,
        "original_filename": original_filename,
        "saved_path": saved_file_path,
        "upload_time": datetime.utcnow().isoformat() + "Z",
        "file_size": file_size,
        "status": "uploaded", # Initial status
        "mime_type": file.content_type # Store MIME type
    }
    
    print(f"File uploaded: ID {file_id}, Name '{original_filename}', Path '{saved_file_path}'")

    return JSONResponse(
        status_code=201, # Explicitly setting here though decorator does it, good for clarity
        content={
            "file_id": file_id,
            "file_name": original_filename,
            "file_size": file_size,
            "message": "File uploaded successfully. Ready for processing."
        }
    )

@app.post("/process/{file_id}", status_code=202, tags=["Processing"])
async def process_document_endpoint(
    file_id: str = Path(..., description="The ID of the uploaded file to process."),
    request_body: ProcessRequest = Body(...)
):
    if file_id not in uploaded_files_db:
        raise HTTPException(status_code=404, detail=f"File with id '{file_id}' not found.")

    file_meta = uploaded_files_db[file_id]

    # Check if there's an existing active job for this file_id to prevent re-processing
    active_job_exists = False
    for job_data_iter in jobs_db.values(): # Renamed job_data to job_data_iter to avoid conflict
        if job_data_iter["file_id"] == file_id and job_data_iter["status"] in ["queued", "processing"]:
            active_job_exists = True
            break
    
    if active_job_exists and file_meta["status"] not in ["uploaded", "failed"]:
         raise HTTPException(status_code=409, detail=f"File '{file_id}' has an active or queued job. Current status: '{file_meta['status']}'.")
    elif file_meta["status"] not in ["uploaded", "failed"]:
         raise HTTPException(status_code=409, detail=f"File '{file_id}' is currently '{file_meta['status']}' and cannot be processed unless it failed.")

    file_path = file_meta["saved_path"]
    original_input_filename = file_meta["original_filename"]
    file_extension = os.path.splitext(original_input_filename)[1].lower()
    
    suggested_output_filename = request_body.output_filename
    if not suggested_output_filename:
        base, ext = os.path.splitext(original_input_filename)
        suggested_output_filename = f"{base}_processed{ext}"
    
    output_ext = os.path.splitext(suggested_output_filename)[1].lower()
    if output_ext != file_extension:
        base_output_name = os.path.splitext(suggested_output_filename)[0]
        suggested_output_filename = f"{base_output_name}{file_extension}"

    task = None
    if file_extension == ".docx":
        task = process_docx_file_task.delay(
            input_file_path=file_path,
            operations=request_body.operations,
            original_filename=suggested_output_filename 
        )
    elif file_extension == ".pdf":
        task = process_pdf_file_task.delay(
            input_file_path=file_path,
            operations=request_body.operations,
            original_filename=suggested_output_filename
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type for processing found in metadata.")

    job_id = task.id

    uploaded_files_db[file_id]["status"] = "queued" 
    uploaded_files_db[file_id]["job_id"] = job_id 
    
    jobs_db[job_id] = {
        "file_id": file_id,
        "status": "queued", 
        "original_filename": suggested_output_filename,
        "celery_task_id": task.id, 
        "requested_operations": request_body.operations,
        "submission_time": datetime.utcnow().isoformat() + "Z"
    }

    print(f"Processing job created: Job ID {job_id} for File ID {file_id}")

    return {
        "job_id": job_id,
        "file_id": file_id,
        "status": "queued",
        "message": "Document processing job accepted and queued.",
        "status_check_url": f"/jobs/{job_id}/status",
        "result_download_url": f"/jobs/{job_id}/download"
    }


@app.get("/jobs/{job_id}/status", tags=["Processing"])
async def get_job_status(job_id: str = Path(..., description="The ID of the processing job.")):
    """
    Checks the status of a document processing job.
    """
    job_meta = jobs_db.get(job_id)
    if not job_meta:
        # Fallback: check Celery directly if not in our app's DB.
        # This might happen if app restarted and jobs_db is in-memory.
        celery_task_result_direct = AsyncResult(job_id, app=celery_app)
        if celery_task_result_direct.state == 'PENDING' and not celery_task_result_direct.info:
             # PENDING with no info often means task ID is unknown to Celery backend or never really started
             raise HTTPException(status_code=404, detail=f"Job with id '{job_id}' not found or never recorded.")
        # If Celery knows of it, but our jobs_db doesn't, it implies an inconsistency.
        # For now, we'll proceed to report Celery's view but flag that app state is missing.
        # This part of the logic from the prompt is a bit complex for a simple in-memory db.
        # A robust system would ensure jobs_db is persistent and reliable.
        # For this implementation, if it's not in jobs_db, it's a 404 from app's perspective.
        raise HTTPException(status_code=404, detail=f"Job with id '{job_id}' not found in application records.")

    celery_task_result = AsyncResult(job_id, app=celery_app)
    current_celery_state = celery_task_result.state
    
    job_meta["celery_task_state"] = current_celery_state # Update our record

    response_payload = {
        "job_id": job_id,
        "status": job_meta["status"], # Start with our application-level status
        "message": f"Job state from Celery: {current_celery_state}",
        "original_filename": job_meta.get("original_filename") 
    }

    if current_celery_state == "SUCCESS":
        if job_meta["status"] != "completed": # Process result only once
            task_output = celery_task_result.result
            if isinstance(task_output, dict):
                job_meta["status"] = "completed"
                job_meta["result_path"] = task_output.get("result_path")
                job_meta["temp_dir_to_cleanup"] = task_output.get("temp_dir_to_cleanup")
                job_meta["message"] = task_output.get("message", "Processing completed successfully.")
                
                file_id = job_meta.get("file_id")
                if file_id and file_id in uploaded_files_db:
                    uploaded_files_db[file_id]["status"] = "completed"
                    uploaded_files_db[file_id]["processed_file_path"] = task_output.get("result_path")
            else: # Task succeeded but returned malformed result
                job_meta["status"] = "failed" 
                job_meta["error_info"] = "Task succeeded but returned unexpected result format."
                job_meta["message"] = "Task completed but result processing within API failed."
        
        response_payload["status"] = "completed" # Reflect the final state
        response_payload["message"] = job_meta.get("message", "Processing completed successfully.")
        response_payload["result_url"] = f"/jobs/{job_id}/download"

    elif current_celery_state == "FAILURE":
        job_meta["status"] = "failed"
        job_meta["error_info"] = str(celery_task_result.info) # Celery stores exception here
        job_meta["message"] = f"Processing failed: {str(celery_task_result.info)}"
        
        file_id = job_meta.get("file_id")
        if file_id and file_id in uploaded_files_db:
            uploaded_files_db[file_id]["status"] = "failed"

        response_payload["status"] = "failed"
        response_payload["message"] = job_meta["message"]
        response_payload["error_details"] = job_meta.get("error_info")

    elif current_celery_state in ["PENDING", "SENT"]:
        job_meta["status"] = "queued" # Update our app's status
        response_payload["status"] = "queued"
        response_payload["message"] = "Job is queued and waiting for a worker."
    elif current_celery_state in ["STARTED", "RECEIVED", "RETRY"]:
        job_meta["status"] = "processing" # Update our app's status
        response_payload["status"] = "processing"
        response_payload["message"] = "Job is currently being processed."
        # Optional: Include progress if the task supports it
        # if isinstance(celery_task_result.info, dict) and 'progress' in celery_task_result.info:
        #    response_payload["progress"] = celery_task_result.info['progress']
    else: # REVOKED, or other custom states
        job_meta["status"] = "unknown" # Or map to "failed"
        response_payload["status"] = "unknown"
        response_payload["message"] = f"Job is in an unhandled Celery state: {current_celery_state}"

    # jobs_db[job_id] = job_meta # Ensure jobs_db is updated (already done by reference)
    return response_payload

# Helper function for cleanup (shutil is imported at the top)
async def cleanup_temp_dir(temp_dir_path: str):
    try:
        if temp_dir_path and os.path.exists(temp_dir_path):
            shutil.rmtree(temp_dir_path)
            print(f"Successfully cleaned up temporary directory: {temp_dir_path}")
        # else:
            # print(f"Cleanup skipped: temp_dir_path not provided or does not exist: {temp_dir_path}")
    except Exception as e:
        print(f"Error during cleanup of temporary directory {temp_dir_path}: {e}")


@app.get("/jobs/{job_id}/download", tags=["Processing"])
async def download_processed_file(job_id: str = Path(..., description="The ID of the completed processing job.")):
    """
    Downloads the processed document if the job is completed successfully.
    Cleans up the temporary processing directory for this job after initiating the download.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail=f"Job with id '{job_id}' not found.")

    job_meta = jobs_db[job_id]

    if job_meta.get("status") != "completed":
        raise HTTPException(status_code=409, detail=f"Job '{job_id}' is not completed. Current status: {job_meta.get('status')}. Download not available.")

    result_file_path = job_meta.get("result_path")
    output_filename = job_meta.get("original_filename", "processed_file") # Default filename if not set
    temp_dir_to_cleanup = job_meta.get("temp_dir_to_cleanup")

    if not result_file_path or not os.path.exists(result_file_path):
        # This indicates an inconsistency if status is "completed"
        print(f"Error: Job {job_id} marked completed but result file '{result_file_path}' not found.")
        raise HTTPException(status_code=500, detail="Processed file is missing or unavailable despite job completion.")

    # Determine media type
    media_type = None
    if output_filename.lower().endswith(".docx"):
        media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    elif output_filename.lower().endswith(".pdf"):
        media_type = "application/pdf"
    else:
        media_type = "application/octet-stream" # Fallback

    # Prepare background task for cleanup *before* returning response,
    # as FileResponse might close connection before sync cleanup code runs.
    cleanup_task = None
    if temp_dir_to_cleanup and not job_meta.get("temp_dir_to_cleanup_scheduled"): # Check if not already scheduled
        cleanup_task = BackgroundTask(cleanup_temp_dir, temp_dir_to_cleanup)
        job_meta["temp_dir_to_cleanup_scheduled"] = True # Mark as cleanup scheduled
        # To prevent re-cleanup or re-download from same temp dir if endpoint is hit again before actual cleanup.
        # A more robust system would use a proper state like "downloaded_cleanup_pending".
    elif job_meta.get("temp_dir_to_cleanup_scheduled"):
        print(f"Cleanup for job {job_id} temp directory {temp_dir_to_cleanup} already scheduled or completed.")
    else: # No temp_dir_to_cleanup specified
        print(f"Warning: No temp_dir_to_cleanup specified for job {job_id}. Cleanup will be skipped.")
        
    return FileResponse(
        path=result_file_path,
        filename=output_filename,
        media_type=media_type,
        background=cleanup_task # Execute cleanup after response is sent
    )

# It's common to include a way to run this directly for development,
# though `uvicorn web_api.main:app --reload` is standard for development.
if __name__ == "__main__":
    # This part is for direct execution like `python web_api/main.py`
    # Note: For production, use a proper ASGI server like Uvicorn or Hypercorn directly.
    # The command `uvicorn web_api.main:app --reload` should be used from the project root directory.
    uvicorn.run(app, host="0.0.0.0", port=8000)

# Static files and HTMLResponse for UI (StaticFiles, HTMLResponse are imported at the top)

# Mount static files directory
# This should be done relative to the location of main.py
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse, tags=["Frontend UI"]) # Changed root path to serve UI
async def serve_frontend_ui():
    """Serves the main HTML page for the frontend UI."""
    index_html_path = os.path.join(STATIC_DIR, "index.html")
    try:
        with open(index_html_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        print(f"Error: index.html not found at {index_html_path}") # Server-side log
        raise HTTPException(status_code=404, detail="Frontend UI (index.html) not found.")
    except Exception as e:
        print(f"Error reading index.html: {e}")
        raise HTTPException(status_code=500, detail="Could not load frontend UI.")

# The original @app.get("/", tags=["General"]) that returned a welcome message is now replaced by serve_frontend_ui.
