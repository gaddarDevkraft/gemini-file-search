const API_URL = 'http://localhost:8000';
// Hardcoded Store ID default
let currentStoreId = "fileSearchStores/storescae04512-imarheumsfib-u1zr7yaxuvz1";

const fileInput = document.getElementById('fileInput');
const dropArea = document.getElementById('dropArea');
const fileMsg = document.querySelector('.file-msg');
const uploadBtn = document.getElementById('uploadBtn');
const uploadStatus = document.getElementById('uploadStatus');

const askSection = document.getElementById('askSection');
const questionInput = document.getElementById('questionInput');
const askBtn = document.getElementById('askBtn');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const answerContent = document.getElementById('answerContent');
const citationsList = document.getElementById('citationsList');

// Enable Ask Section immediately since we have a hardcoded ID
if (currentStoreId) {
    askSection.classList.remove('disabled');
}

// File Selection
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        fileMsg.textContent = e.target.files[0].name;
        uploadBtn.disabled = false;
    }
});

// Upload Logic
uploadBtn.addEventListener('click', async () => {
    if (!fileInput.files[0]) return;

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    uploadStatus.textContent = "Uploading and indexing... this may take a moment.";
    uploadStatus.className = "status-msg";
    uploadBtn.disabled = true;

    try {
        const response = await fetch(`${API_URL}/upload-ppt`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(await response.text());

        const data = await response.json();
        currentStoreId = data.store_id;

        uploadStatus.textContent = "✓ Success! Presentation indexed.";
        uploadStatus.className = "status-msg success";

        // Show Store ID
        const storeIdDisplay = document.getElementById('storeIdDisplay');
        if (storeIdDisplay) {
            storeIdDisplay.textContent = `Store ID: ${currentStoreId}`;
            storeIdDisplay.classList.remove('hidden');
        }

        askSection.classList.remove('disabled');

    } catch (error) {
        uploadStatus.textContent = `Error: ${error.message}`;
        uploadStatus.className = "status-msg error";
        uploadBtn.disabled = false;
    }
});

// Ask Logic
askBtn.addEventListener('click', async () => {
    const question = questionInput.value.trim();
    if (!question || !currentStoreId) return;

    loading.classList.remove('hidden');
    resultsSection.classList.add('hidden');
    askBtn.disabled = true;

    try {
        const formData = new FormData();
        formData.append('question', question);
        formData.append('file_search_store_id', currentStoreId);

        const response = await fetch(`${API_URL}/ask`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) throw new Error(await response.text());

        const data = await response.json();

        // Render Answer
        answerContent.innerHTML = marked.parse(data.answer);

        // Render Citations
        citationsList.innerHTML = '';
        if (data.citations && data.citations.length > 0) {
            data.citations.forEach(citation => {
                const context = citation.retrievedContext;
                if (!context) return;

                const li = document.createElement('li');
                li.className = 'citation-card';

                const title = document.createElement('div');
                title.className = 'citation-title';
                title.textContent = context.title || "Unknown Document";

                const text = document.createElement('div');
                text.className = 'citation-text';
                // Truncate text if too long for preview
                text.textContent = context.text ? (context.text.substring(0, 150) + "...") : "No content";

                li.appendChild(title);
                li.appendChild(text);
                citationsList.appendChild(li);
            });
        } else {
            const li = document.createElement('li');
            li.textContent = "No specific citations returned.";
            citationsList.appendChild(li);
        }

        resultsSection.classList.remove('hidden');

    } catch (error) {
        alert(`Error: ${error.message}`);
    } finally {
        loading.classList.add('hidden');
        askBtn.disabled = false;
    }
});

// Enable 'Enter' to send
questionInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') askBtn.click();
});
