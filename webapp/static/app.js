let searchTimeout = null;
let currentQuery = "";

document.addEventListener("DOMContentLoaded", () => {
    loadDocuments();

    const searchInput = document.getElementById("search-input");
    const clearBtn = document.getElementById("clear-search-btn");

    searchInput.addEventListener("input", (e) => {
        currentQuery = e.target.value.trim();
        clearBtn.style.display = currentQuery ? "block" : "none";
        
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            loadDocuments(currentQuery);
        }, 250);
    });

    clearBtn.addEventListener("click", () => {
        searchInput.value = "";
        currentQuery = "";
        clearBtn.style.display = "none";
        loadDocuments();
    });

    // Modal Close handlers
    document.getElementById("modal-close-btn").addEventListener("click", closeModal);
    document.getElementById("modal-backdrop").addEventListener("click", (e) => {
        if (e.target.id === "modal-backdrop") closeModal();
    });

    // Auto-refresh every 5 seconds to show real-time K8s job progress
    setInterval(() => {
        loadDocuments(currentQuery, true);
    }, 5000);
});

async function loadDocuments(query = "", isBackground = false) {
    const tbody = document.getElementById("docs-tbody");
    if (!isBackground && !tbody.hasChildNodes()) {
        tbody.innerHTML = `<tr><td colspan="6" class="loading-state">Loading documents...</td></tr>`;
    }

    try {
        const url = query ? `/api/search?q=${encodeURIComponent(query)}` : `/api/docs`;
        const res = await fetch(url);
        const data = await res.json();

        document.getElementById("doc-count").textContent = data.count || 0;
        renderTable(data.results || []);
    } catch (err) {
        console.error("Failed to load documents:", err);
    }
}

function renderTable(docs) {
    const tbody = document.getElementById("docs-tbody");
    if (docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-secondary); padding: 2rem;">No documents found.</td></tr>`;
        return;
    }

    tbody.innerHTML = docs.map(doc => `
        <tr>
            <td>
                <div class="doc-title">${escapeHtml(doc.filename)}</div>
                <div class="doc-gcs">${escapeHtml(doc.gcs_uri)}</div>
            </td>
            <td>
                <div><strong>${escapeHtml(doc.institution || "Unknown")}</strong></div>
                <div style="font-size: 0.75rem; color: var(--text-secondary);">${escapeHtml(doc.doc_date || "N/A")}</div>
            </td>
            <td>${doc.page_count || 0}</td>
            <td><span class="badge badge-${doc.status}">${doc.status}</span></td>
            <td>
                <div class="snippet-box">${doc.match_snippet || '<span style="color: #64748b;">No snippet</span>'}</div>
            </td>
            <td>
                <div class="btn-group">
                    <button class="btn btn-secondary" onclick="viewDetails('${doc.id}')">View</button>
                    <button class="btn btn-primary" 
                            onclick="triggerAnalysis('${doc.id}')" 
                            ${doc.status === 'ANALYZING' ? 'disabled' : ''}>
                        ${doc.status === 'ANALYZED' ? 'Re-Analyze' : 'Analyze'}
                    </button>
                </div>
            </td>
        </tr>
    `).join("");
}

async function triggerAnalysis(docId) {
    try {
        const res = await fetch(`/api/analyze/trigger/${docId}`, { method: "POST" });
        if (!res.ok) throw new Error("Failed to trigger analysis");
        loadDocuments(currentQuery, true);
    } catch (err) {
        alert(`Error triggering analysis: ${err.message}`);
    }
}

async function viewDetails(docId) {
    try {
        const res = await fetch(`/api/docs/${docId}`);
        if (!res.ok) throw new Error("Failed to load document details");
        const doc = await res.json();

        document.getElementById("modal-title").textContent = doc.filename;
        document.getElementById("modal-doc-id").textContent = doc.id;

        const body = document.getElementById("modal-body");
        let html = `
            <div class="section-box">
                <h3>Document Metadata</h3>
                <p><strong>GCS URI:</strong> <code>${escapeHtml(doc.gcs_uri)}</code></p>
                <p><strong>Status:</strong> <span class="badge badge-${doc.status}">${doc.status}</span></p>
                <p><strong>Institution:</strong> ${escapeHtml(doc.institution || "N/A")}</p>
                <p><strong>Document Date:</strong> ${escapeHtml(doc.doc_date || "N/A")}</p>
                <p><strong>Account Numbers:</strong> ${escapeHtml(doc.account_numbers || "N/A")}</p>
                <p><strong>Raw Metadata GCS:</strong> <code>${escapeHtml(doc.raw_metadata_uri || "N/A")}</code></p>
            </div>
        `;

        if (doc.analysis) {
            let structuredFormatted = "";
            try {
                const parsed = typeof doc.analysis.structured_json === 'string' 
                    ? JSON.parse(doc.analysis.structured_json) 
                    : doc.analysis.structured_json;
                // Check if parsed itself is still a string (double-encoded)
                const finalObj = typeof parsed === 'string' ? JSON.parse(parsed) : parsed;
                structuredFormatted = JSON.stringify(finalObj, null, 2);
            } catch {
                structuredFormatted = doc.analysis.structured_json;
            }

            html += `
                <div class="section-box">
                    <h3>Deep Analysis Report (Google Antigravity SDK)</h3>
                    <p><strong>Summary:</strong> ${escapeHtml(doc.analysis.summary || "N/A")}</p>
                    <p style="margin-top: 0.5rem;"><strong>Report URI:</strong> <code>${escapeHtml(doc.analysis.report_gcs_uri || "N/A")}</code></p>
                    <div style="margin-top: 0.75rem;">
                        <strong>Structured Extraction:</strong>
                        <pre class="json-viewer">${escapeHtml(structuredFormatted)}</pre>
                    </div>
                </div>
            `;
        }

        if (doc.analysis_errors && doc.analysis_errors.length > 0) {
            const isLatestError = doc.status === 'ERROR';
            html += `
                <div class="section-box">
                    <h3 style="color: var(--status-error);">${isLatestError ? 'Analysis Error' : 'Historical Error Logs (Resolved)'}</h3>
                    ${doc.analysis_errors.map(err => `
                        <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem;">
                            <div style="font-size: 0.75rem; color: #94a3b8; margin-bottom: 0.25rem;">${escapeHtml(err.created_at || "")}</div>
                            <strong>${escapeHtml(err.error_message)}</strong>
                            ${err.traceback ? `<pre style="font-size: 0.75rem; margin-top: 0.5rem; overflow-x: auto; max-height: 150px;">${escapeHtml(err.traceback)}</pre>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        if (doc.ingest_errors && doc.ingest_errors.length > 0) {
            html += `
                <div class="section-box">
                    <h3 style="color: var(--status-error);">Ingest Errors</h3>
                    ${doc.ingest_errors.map(err => `
                        <div style="background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); padding: 0.75rem; border-radius: 6px; margin-bottom: 0.5rem;">
                            <strong>${escapeHtml(err.error_message)}</strong>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        body.innerHTML = html;
        document.getElementById("modal-backdrop").classList.remove("hidden");
    } catch (err) {
        alert(`Error opening details: ${err.message}`);
    }
}

function closeModal() {
    document.getElementById("modal-backdrop").classList.add("hidden");
}

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
