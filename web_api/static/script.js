// web_api/static/script.js
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('fileInput');
    const uploadProcessButton = document.getElementById('uploadProcessButton');
    const statusArea = document.getElementById('statusArea');
    const resultArea = document.getElementById('resultArea');

    let pollingIntervalId = null; // To store the interval ID for polling

    uploadProcessButton.addEventListener('click', async () => {
        if (pollingIntervalId) { // Clear previous polling if any
            clearInterval(pollingIntervalId);
            pollingIntervalId = null;
        }
        statusArea.textContent = 'Starting...';
        resultArea.innerHTML = ''; // Clear previous results

        const file = fileInput.files[0];
        if (!file) {
            statusArea.textContent = 'Please select a file first.';
            return;
        }

        // 1. Upload file
        statusArea.textContent = 'Uploading file...';
        const formData = new FormData();
        formData.append('file', file);

        let uploadResponse;
        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData,
            });
            uploadResponse = await response.json();
            if (!response.ok) {
                throw new Error(uploadResponse.detail || `HTTP error! status: ${response.status}`);
            }
            statusArea.textContent = `File uploaded. File ID: ${uploadResponse.file_id}. Processing...`;
        } catch (error) {
            statusArea.textContent = `Upload failed: ${error.message}`;
            console.error('Upload error:', error);
            return;
        }

        const fileId = uploadResponse.file_id;
        const fileName = file.name;
        const fileExtension = fileName.split('.').pop().toLowerCase();

        // 2. Start processing (fixed operations based on file type)
        let processPayload;
        if (fileExtension === 'docx') {
            processPayload = {
                operations: [
                    { "type": "set_page_size", "size_identifier": "A5" },
                    { "type": "add_page_numbers" },
                    // { "type": "correct_misspellings", "lang": "ja"}, // Keep commented out as it's a placeholder
                    { "type": "extract_keywords_for_bolding", "lang": "ja", "top_n": 20},
                    { "type": "bold_keywords", "use_extracted": true}
                ],
                output_filename: "processed_large_test_JA.docx" // Fixed output filename for test
            };
        } else if (fileExtension === 'pdf') {
            processPayload = {
                operations: [
                    { "type": "rotate_pages", "rotation_degrees": 90 },
                    { "type": "add_page_numbers", "font_size_pt": 12, "text_hex_color": "FF0000" }
                ],
                output_filename: "processed_large_test_JA.pdf" // Fixed output filename for test
            };
        } else {
            statusArea.textContent = 'Unsupported file type for fixed processing.';
            return;
        }

        let processResponseData; // Renamed to avoid conflict with 'response' variable
        try {
            const response = await fetch(`/process/${fileId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(processPayload),
            });
            processResponseData = await response.json(); // Renamed
            if (!response.ok) {
                throw new Error(processResponseData.detail || `HTTP error! status: ${response.status}`);
            }
            statusArea.textContent = `Processing job started. Job ID: ${processResponseData.job_id}. Waiting for completion...`;
        } catch (error) {
            statusArea.textContent = `Failed to start processing: ${error.message}`;
            console.error('Processing start error:', error);
            return;
        }

        const jobId = processResponseData.job_id; // Use renamed variable

        // 3. Poll for status
        pollingIntervalId = setInterval(async () => {
            try {
                const response = await fetch(`/jobs/${jobId}/status`);
                const statusData = await response.json();

                if (!response.ok) {
                    // If 404 for job, it might mean it's too early or something went wrong
                    if(response.status === 404){
                         statusArea.textContent = `Job ID ${jobId} not found yet, or an error occurred. Retrying...`;
                         // No need to clear interval here, may eventually resolve or fail permanently
                    } else {
                        throw new Error(statusData.detail || `HTTP error! status: ${response.status}`);
                    }
                } else {
                     statusArea.textContent = `Job Status: ${statusData.status}
Message: ${statusData.message || ''}`;
                }


                if (statusData.status === 'completed') {
                    clearInterval(pollingIntervalId);
                    pollingIntervalId = null;
                    statusArea.textContent = `Processing completed! Output file: ${statusData.original_filename || 'processed_file'}`;
                    const downloadLink = document.createElement('a');
                    downloadLink.href = `/jobs/${jobId}/download`;
                    downloadLink.textContent = `Download ${statusData.original_filename || 'processed_file'}`;
                    // downloadLink.setAttribute('download', statusData.original_filename || 'processed_file'); // Optional: suggest filename
                    resultArea.innerHTML = ''; // Clear previous
                    resultArea.appendChild(downloadLink);
                } else if (statusData.status === 'failed') {
                    clearInterval(pollingIntervalId);
                    pollingIntervalId = null;
                    statusArea.textContent = `Processing failed: ${statusData.message || statusData.detail || 'Unknown error'}`;
                    if(statusData.error_details) {
                        statusArea.textContent += `
Details: ${statusData.error_details}`;
                    }
                }
            } catch (error) {
                clearInterval(pollingIntervalId);
                pollingIntervalId = null;
                statusArea.textContent = `Error fetching job status: ${error.message}`;
                console.error('Status polling error:', error);
            }
        }, 3000); // Poll every 3 seconds
    });
});
