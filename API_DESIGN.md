# Document Processing API Design

This document outlines the design for the core API endpoints of the document processing web application.

---

## 1. File Upload

*   **Endpoint Path:** `/upload`
*   **HTTP Method:** `POST`
*   **Description:** Uploads a document file (.docx or .pdf) for processing. The uploaded file will be stored temporarily on the server.
*   **Request:**
    *   Body: `multipart/form-data`
    *   Form field name for the file: `file` (e.g., `<input type="file" name="file">`)
*   **Response:**
    *   **201 Created:** Indicates the file was successfully uploaded and stored.
        ```json
        {
          "file_id": "unique_file_identifier_string_generated_by_server",
          "file_name": "original_uploaded_filename.docx",
          "file_size": 123456, // in bytes
          "message": "File uploaded successfully. Ready for processing."
        }
        ```
    *   **400 Bad Request:** If no file is provided in the request, the file is empty, or the file type is not .docx or .pdf.
        ```json
        {
          "detail": "Error message (e.g., 'No file part in the request.', 'Empty file uploaded.', 'Unsupported file type. Only .docx and .pdf are allowed.')"
        }
        ```
    *   **413 Payload Too Large:** If the uploaded file exceeds a server-defined size limit.
        ```json
        {
          "detail": "File size exceeds the maximum limit of XX MB."
        }
        ```
    *   **500 Internal Server Error:** For unexpected server errors during upload or storage.
        ```json
        {
          "detail": "An unexpected error occurred while saving the file."
        }
        ```
*   **Authentication/Authorization:** None for now. (Future: Could require user authentication to associate uploads with specific accounts).

---

## 2. Process Document

*   **Endpoint Path:** `/process/{file_id}`
*   **HTTP Method:** `POST`
*   **Description:** Initiates a processing job on a previously uploaded document. The client specifies a list of operations to be performed.
*   **Request:**
    *   Path Parameter: `file_id` (string) - The unique identifier of the file obtained from the `/upload` endpoint.
    *   Body: JSON object specifying the operations.
        ```json
        {
          "operations": [
            {"type": "set_page_size", "size_identifier": "A5"},
            {"type": "add_page_numbers"},
            {"type": "set_text_color", "hex_color": "0000FF"},
            {"type": "extract_keywords_for_bolding", "lang": "en", "top_n": 5},
            {"type": "bold_keywords", "use_extracted": true}
            // ... other operations as supported by the backend
          ],
          "output_filename": "processed_document.docx" // Optional: client can suggest an output filename
        }
        ```
*   **Response:**
    *   **202 Accepted:** Indicates the processing job has been successfully queued. The response includes a job ID to track status.
        ```json
        {
          "job_id": "unique_job_identifier_string",
          "file_id": "unique_file_identifier_string",
          "status": "queued",
          "message": "Document processing job accepted and queued.",
          "status_check_url": "/jobs/{job_id}/status",
          "result_download_url": "/jobs/{job_id}/download"
        }
        ```
    *   **400 Bad Request:** If the operations list is missing, empty, or contains invalid operations/parameters.
        ```json
        {
          "detail": "Error message (e.g., 'Operations list is required.', 'Invalid operation type: xyz.', 'Missing parameter for operation: set_page_size.')"
        }
        ```
    *   **404 Not Found:** If the specified `file_id` does not correspond to an existing uploaded file.
        ```json
        {
          "detail": "File with id 'unique_file_identifier_string' not found."
        }
        ```
    *   **422 Unprocessable Entity:** If the file is found but is not in a state to be processed (e.g., corrupted, or a previous processing attempt failed irreversibly).
        ```json
        {
          "detail": "The file associated with file_id cannot be processed."
        }
        ```
    *   **500 Internal Server Error:** For unexpected server errors when initiating the job.
        ```json
        {
          "detail": "An unexpected error occurred while starting the processing job."
        }
        ```
*   **Authentication/Authorization:** None for now. (Future: Could require user authentication to ensure only the uploader can process their files).

---

## 3. Job Status

*   **Endpoint Path:** `/jobs/{job_id}/status`
*   **HTTP Method:** `GET`
*   **Description:** Checks the status of a document processing job.
*   **Request:**
    *   Path Parameter: `job_id` (string) - The unique identifier of the job obtained from the `/process/{file_id}` endpoint.
*   **Response:**
    *   **200 OK:** Returns the current status of the job.
        ```json
        {
          "job_id": "unique_job_identifier_string",
          "status": "queued | processing | completed | failed",
          "message": "Descriptive message about the current status (e.g., 'Processing step 2 of 5: Applying page numbers.').",
          "progress": 60, // Optional: percentage completion (0-100)
          "estimated_time_remaining": 120, // Optional: in seconds
          "result_url": "/jobs/{job_id}/download" // Included if status is 'completed'
        }
        ```
        If status is `failed`:
        ```json
        {
          "job_id": "unique_job_identifier_string",
          "status": "failed",
          "message": "Processing failed at step 'bold_keywords'.",
          "error_details": "Specific error message from the backend processing."
          // No result_url
        }
        ```
    *   **404 Not Found:** If the specified `job_id` does not exist.
        ```json
        {
          "detail": "Job with id 'unique_job_identifier_string' not found."
        }
        ```
    *   **500 Internal Server Error:** For unexpected server errors when fetching status.
        ```json
        {
          "detail": "An unexpected error occurred while checking job status."
        }
        ```
*   **Authentication/Authorization:** None for now. (Future: Could require user authentication).

---

## 4. Download Result

*   **Endpoint Path:** `/jobs/{job_id}/download`
*   **HTTP Method:** `GET`
*   **Description:** Downloads the processed document if the job is completed successfully.
*   **Request:**
    *   Path Parameter: `job_id` (string) - The unique identifier of the job.
*   **Response:**
    *   **200 OK:** The processed file is sent as a binary stream.
        *   Headers:
            *   `Content-Type`: `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (for .docx) or `application/pdf` (for .pdf).
            *   `Content-Disposition`: `attachment; filename="processed_document_name.docx"` (The filename should be the one set during processing or a generated one).
    *   **404 Not Found:** If the specified `job_id` does not exist or the processed file is not available (e.g., deleted due to retention policy).
        ```json
        {
          "detail": "Job with id 'unique_job_identifier_string' not found or result file is unavailable."
        }
        ```
    *   **409 Conflict (or 400 Bad Request):** If the job is not yet completed or has failed. The client should check `/jobs/{job_id}/status` first.
        ```json
        {
          "job_id": "unique_job_identifier_string",
          "status": "processing | failed", // Current status
          "detail": "Job is not completed or has failed. Download not available."
        }
        ```
    *   **500 Internal Server Error:** For unexpected server errors during file retrieval.
        ```json
        {
          "detail": "An unexpected error occurred while retrieving the processed file."
        }
        ```
*   **Authentication/Authorization:** None for now. (Future: Could require user authentication).

---

## 5. (Optional) List Operations

*   **Endpoint Path:** `/operations`
*   **HTTP Method:** `GET`
*   **Description:** Provides a list of available document processing operations and their configurable parameters. This helps clients construct valid requests for the `/process/{file_id}` endpoint.
*   **Request:** None
*   **Response:**
    *   **200 OK:**
        ```json
        {
          "operations": [
            {
              "type": "set_page_size",
              "description": "Sets the page size of the document (e.g., A4, Letter).",
              "doc_types_supported": ["docx", "pdf"], // or just "docx" if only for docx
              "parameters": [
                {"name": "size_identifier", "type": "string", "required": true, "description": "Standard size identifier (e.g., 'A4', 'LETTER', 'A5').", "example": "A4"}
              ]
            },
            {
              "type": "add_page_numbers",
              "description": "Adds page numbers to the document.",
              "doc_types_supported": ["docx", "pdf"],
              "parameters": [ // Example for PDF version
                {"name": "font_name", "type": "string", "required": false, "default": "Helvetica", "description": "Font for page numbers."},
                {"name": "font_size_pt", "type": "integer", "required": false, "default": 10, "description": "Font size in points."},
                {"name": "text_hex_color", "type": "string", "required": false, "default": "000000", "description": "Hex color for page numbers."}
              ]
            },
            {
              "type": "bold_keywords",
              "description": "Bolds specified keywords in the document. Can use extracted keywords.",
              "doc_types_supported": ["docx"],
              "parameters": [
                  {"name": "keywords_list", "type": "array[string]", "required": false, "description": "List of keywords to bold if not using extracted ones."},
                  {"name": "use_extracted", "type": "boolean", "required": false, "default": false, "description": "Set to true to use keywords from a previous 'extract_keywords_for_bolding' step."}
              ]
            },
            {
              "type": "extract_keywords_for_bolding",
              "description": "Extracts key terms from the document for use in other operations like 'bold_keywords'.",
              "doc_types_supported": ["docx"],
              "parameters": [
                {"name": "lang", "type": "string", "required": false, "default": "en", "description": "Language of the document (e.g., 'en', 'ja')."},
                {"name": "top_n", "type": "integer", "required": false, "default": 10, "description": "Number of top keyterms to extract."}
              ]
            }
            // ... other available operations
          ]
        }
        ```
    *   **500 Internal Server Error:** For unexpected server errors.
        ```json
        {
          "detail": "An unexpected error occurred while retrieving available operations."
        }
        ```
*   **Authentication/Authorization:** None. This is public information.

---
