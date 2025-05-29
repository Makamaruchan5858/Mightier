# Mightier Document Processor

This project provides a FastAPI service for processing DOCX and PDF files.

## Setup

1. Install Python 3.8 or newer.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   The list includes `python-multipart`, which FastAPI requires for handling
   file uploads.
4. Ensure Redis is running and start a Celery worker:
   ```bash
   celery -A web_api.celery_app worker --loglevel=info
   ```
5. Launch the API server:
   ```bash
   uvicorn web_api.main:app --port 8000
   ```

## Testing

Run the unit tests with:
```bash
pytest -q
```
