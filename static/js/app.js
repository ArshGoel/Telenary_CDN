/**
 * Telenary CDN Developer Portal Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    const assetGridContainer = document.getElementById('assetGridContainer');
    const btnTriggerUpload = document.getElementById('btnTriggerUpload');
    const sandboxFileInput = document.getElementById('sandboxFileInput');
    const uploadProgressBox = document.getElementById('uploadProgressBox');
    const uploadProgressFill = document.getElementById('uploadProgressFill');
    const uploadProgressText = document.getElementById('uploadProgressText');
    const uploadProgressPercent = document.getElementById('uploadProgressPercent');
    const statTotalAssets = document.getElementById('statTotalAssets');

    const createKeyForm = document.getElementById('createKeyForm');
    const keyNameInput = document.getElementById('keyNameInput');
    const apiKeysListContainer = document.getElementById('apiKeysListContainer');

    // Fetch Assets on load
    fetchAssets();
    fetchApiKeys();

    function fetchAssets() {
        if (!assetGridContainer) return;

        fetch('/api/v1/resources')
            .then(res => res.json())
            .then(data => {
                renderAssets(data.resources);
                if (statTotalAssets) statTotalAssets.textContent = data.total_count || 0;
            })
            .catch(err => {
                assetGridContainer.innerHTML = `<p style="color: var(--accent-red);">Error loading assets: ${err}</p>`;
            });
    }

    function renderAssets(resources) {
        if (!assetGridContainer) return;

        if (!resources || resources.length === 0) {
            assetGridContainer.innerHTML = `
                <div style="grid-column: 1 / -1; text-align: center; padding: 40px; color: var(--text-muted);">
                    <i data-lucide="cloud-off" style="width: 48px; height: 48px; margin-bottom: 12px; color: var(--border-color);"></i>
                    <p>No media assets uploaded yet. Use the upload button or hit the <code>/api/v1/upload</code> endpoint!</p>
                </div>
            `;
            lucide.createIcons();
            return;
        }

        let html = '';
        resources.forEach(item => {
            let previewContent = '';
            if (item.resource_type === 'image') {
                previewContent = `<img src="${item.thumbnail_url}" alt="${item.filename}" loading="lazy">`;
            } else if (item.resource_type === 'video') {
                previewContent = `<i data-lucide="video" style="width: 40px; height: 40px; color: var(--accent-blue);"></i>`;
            } else if (item.resource_type === 'audio') {
                previewContent = `<i data-lucide="music" style="width: 40px; height: 40px; color: var(--accent-purple);"></i>`;
            } else {
                previewContent = `<i data-lucide="file-text" style="width: 40px; height: 40px; color: var(--accent-green);"></i>`;
            }

            html += `
                <div class="asset-card">
                    <div class="asset-preview">
                        ${previewContent}
                    </div>
                    <div class="asset-info">
                        <span class="asset-title">${item.filename}</span>
                        <span class="asset-meta">${formatBytes(item.bytes)} • ${item.format.toUpperCase() || item.resource_type}</span>
                        <div class="asset-actions">
                            <button class="btn-copy btn-copy-url" data-url="${item.secure_url}">
                                <i data-lucide="copy"></i> CDN URL
                            </button>
                            <button class="btn-copy btn-copy-transform" data-url="${item.transform_url}">
                                <i data-lucide="sliders"></i> Transform
                            </button>
                        </div>
                    </div>
                </div>
            `;
        });

        assetGridContainer.innerHTML = html;
        lucide.createIcons();

        // Attach Copy Button Handlers
        document.querySelectorAll('.btn-copy').forEach(btn => {
            btn.addEventListener('click', () => {
                const url = btn.dataset.url;
                navigator.clipboard.writeText(url).then(() => {
                    const origText = btn.innerHTML;
                    btn.innerHTML = `<i data-lucide="check" style="color: var(--accent-green);"></i> Copied!`;
                    lucide.createIcons();
                    setTimeout(() => btn.innerHTML = origText, 1500);
                });
            });
        });
    }

    // Upload Trigger
    if (btnTriggerUpload && sandboxFileInput) {
        btnTriggerUpload.addEventListener('click', () => sandboxFileInput.click());
        sandboxFileInput.addEventListener('change', (e) => handleUpload(e.target.files));
    }

    function handleUpload(files) {
        if (!files || files.length === 0) return;

        const formData = new FormData();
        for (let i = 0; i < files.length; i++) {
            formData.append('files', files[i]);
        }

        if (uploadProgressBox) uploadProgressBox.classList.remove('hidden');

        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/v1/upload', true);

        xhr.upload.onprogress = (e) => {
            if (e.lengthComputable) {
                const percent = Math.round((e.loaded / e.total) * 100);
                if (uploadProgressFill) uploadProgressFill.style.width = percent + '%';
                if (uploadProgressPercent) uploadProgressPercent.textContent = percent + '%';
            }
        };

        xhr.onload = () => {
            if (uploadProgressText) uploadProgressText.textContent = 'Upload complete! Saved to Telegram Cloud.';
            setTimeout(() => {
                if (uploadProgressBox) uploadProgressBox.classList.add('hidden');
                if (uploadProgressFill) uploadProgressFill.style.width = '0%';
                fetchAssets();
            }, 1200);
        };

        xhr.onerror = () => {
            if (uploadProgressText) uploadProgressText.textContent = 'Upload failed.';
        };

        xhr.send(formData);
    }

    // API Key Management
    function fetchApiKeys() {
        if (!apiKeysListContainer) return;
        fetch('/api/v1/keys')
            .then(res => res.json())
            .then(data => {
                if (!data.keys || data.keys.length === 0) {
                    apiKeysListContainer.innerHTML = `<p style="color: var(--text-muted); font-size: 0.85rem;">No API Keys generated yet.</p>`;
                    return;
                }

                let html = '';
                data.keys.forEach(k => {
                    html += `
                        <div class="api-box" style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="display: block; font-size: 0.9rem;">${k.name}</strong>
                                <code style="color: var(--accent-blue); font-size: 0.85rem;">${k.key}</code>
                            </div>
                            <span style="font-size: 0.75rem; color: var(--text-muted);">${new Date(k.created_at).toLocaleDateString()}</span>
                        </div>
                    `;
                });
                apiKeysListContainer.innerHTML = html;
            });
    }

    if (createKeyForm) {
        createKeyForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const name = keyNameInput.value.trim();
            if (!name) return;

            fetch('/api/v1/keys', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name })
            })
            .then(res => res.json())
            .then(() => {
                keyNameInput.value = '';
                fetchApiKeys();
            });
        });
    }

    function formatBytes(bytes, decimals = 1) {
        if (!bytes || bytes === 0) return '0 B';
        const k = 1024;
        const dm = decimals < 0 ? 0 : decimals;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
    }
});
