/* ==========================================================================
   PTM Prime - Facebook Media Downloader
   Client Frontend Controller
   Powered by PTM Prime
   ========================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // Initialize Lucide Icons
    if (window.lucide) {
        lucide.createIcons();
    }

    // Elements
    const urlInput = document.getElementById("urlInput");
    const btnPaste = document.getElementById("btnPaste");
    const btnClear = document.getElementById("btnClear");
    const btnStartDownload = document.getElementById("btnStartDownload");
    const btnCancelDownload = document.getElementById("btnCancelDownload");
    const modeChips = document.querySelectorAll(".mode-chip");
    
    // Advanced Options
    const toggleAdvanced = document.getElementById("toggleAdvanced");
    const advancedContent = document.getElementById("advancedContent");
    const advancedChevron = document.getElementById("advancedChevron");
    const browserCookies = document.getElementById("browserCookies");

    // Progress Panel
    const progressPanel = document.getElementById("progressPanel");
    const progressBarFill = document.getElementById("progressBarFill");
    const progressPct = document.getElementById("progressPct");
    const progressStatusText = document.getElementById("progressStatusText");
    const statPhotos = document.getElementById("statPhotos");
    const statVideos = document.getElementById("statVideos");
    const terminalLog = document.getElementById("terminalLog");
    const btnClearLogs = document.getElementById("btnClearLogs");

    // Completion Bar
    const completionBar = document.getElementById("completionBar");
    const btnOpenCompletedFolder = document.getElementById("btnOpenCompletedFolder");
    const btnOpenFolderHeader = document.getElementById("btnOpenFolderHeader");

    // History
    const historyList = document.getElementById("historyList");
    const btnRefreshHistory = document.getElementById("btnRefreshHistory");

    // Toast
    const toast = document.getElementById("toast");

    let eventSource = null;
    let photoCount = 0;
    let videoCount = 0;

    // Toast Notification Helper
    function showToast(message, duration = 3000) {
        toast.textContent = message;
        toast.classList.add("show");
        setTimeout(() => {
            toast.classList.remove("show");
        }, duration);
    }

    // Toggle Mode Chips
    modeChips.forEach(chip => {
        chip.addEventListener("click", () => {
            modeChips.forEach(c => c.classList.remove("active"));
            chip.classList.add("active");
            const radio = chip.querySelector('input[type="radio"]');
            if (radio) radio.checked = true;
        });
    });

    // Toggle Advanced Options
    if (toggleAdvanced) {
        toggleAdvanced.addEventListener("click", () => {
            const isHidden = advancedContent.style.display === "none";
            advancedContent.style.display = isHidden ? "block" : "none";
            if (advancedChevron) {
                advancedChevron.classList.toggle("rotate", isHidden);
            }
        });
    }

    // Paste from Clipboard
    btnPaste.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                showToast("📋 Pasted link from clipboard!");
                urlInput.focus();
            }
        } catch (err) {
            showToast("⚠️ Clipboard permission denied. Please paste manually (Ctrl+V).");
        }
    });

    // Clear URL
    btnClear.addEventListener("click", () => {
        urlInput.value = "";
        urlInput.focus();
    });

    // Clear Logs
    btnClearLogs.addEventListener("click", () => {
        terminalLog.innerHTML = '<div class="log-line info">Logs cleared.</div>';
    });

    // Append Log Line
    function appendLog(message, level = "info") {
        const line = document.createElement("div");
        line.className = `log-line ${level}`;
        line.textContent = message;
        terminalLog.appendChild(line);
        terminalLog.scrollTop = terminalLog.scrollHeight;
    }

    // Open Folder in Windows Explorer
    async function triggerOpenFolder() {
        try {
            const res = await fetch("/api/open-folder", {
                method: "POST",
                headers: { "Content-Type": "application/json" }
            });
            const data = await res.json();
            if (data.success) {
                showToast("📂 Opened Downloads folder in File Explorer!");
            } else {
                showToast("⚠️ Could not open folder: " + (data.error || "Unknown"));
            }
        } catch (err) {
            showToast("⚠️ Error opening folder.");
        }
    }

    btnOpenFolderHeader.addEventListener("click", triggerOpenFolder);
    btnOpenCompletedFolder.addEventListener("click", triggerOpenFolder);

    // Open Individual Downloaded File
    async function openDownloadedMedia(relPath, action = "open") {
        if (!relPath) return;
        try {
            const res = await fetch("/api/open-file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ rel_path: relPath, action: action })
            });
            const data = await res.json();
            if (data.success) {
                if (action === "locate") {
                    showToast("📂 File highlighted in Explorer!");
                } else {
                    showToast("▶️ Opening file...");
                }
            } else {
                showToast("⚠️ Could not open file: " + (data.error || "Unknown"));
            }
        } catch (err) {
            showToast("⚠️ Error opening file.");
        }
    }

    // Refresh History
    async function loadHistory() {
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            if (data.success && data.items.length > 0) {
                historyList.innerHTML = data.items.map(item => `
                    <div class="history-item" data-relpath="${item.rel_path}" title="Click to open ${item.name}">
                        <div class="history-left">
                            <i data-lucide="${item.type === 'video' ? 'film' : 'image'}" class="history-icon ${item.type}"></i>
                            <div>
                                <div class="history-filename" title="${item.name}">${item.name}</div>
                                <div class="history-meta">${item.folder}</div>
                            </div>
                        </div>
                        <div class="history-right">
                            <span class="history-size">${item.size_formatted}</span>
                            <div class="history-actions">
                                <button type="button" class="history-btn btn-open-media" data-relpath="${item.rel_path}" title="Open with default app">
                                    <i data-lucide="external-link"></i>
                                    <span>Open</span>
                                </button>
                                <button type="button" class="history-btn history-btn-locate btn-locate-media" data-relpath="${item.rel_path}" title="Show in Windows Explorer">
                                    <i data-lucide="folder-search"></i>
                                </button>
                            </div>
                        </div>
                    </div>
                `).join("");

                // Attach click listeners to rows and buttons
                historyList.querySelectorAll(".history-item").forEach(row => {
                    row.addEventListener("click", (e) => {
                        const locateBtn = e.target.closest(".btn-locate-media");
                        const openBtn = e.target.closest(".btn-open-media");

                        if (locateBtn) {
                            e.stopPropagation();
                            openDownloadedMedia(locateBtn.dataset.relpath, "locate");
                        } else if (openBtn) {
                            e.stopPropagation();
                            openDownloadedMedia(openBtn.dataset.relpath, "open");
                        } else {
                            openDownloadedMedia(row.dataset.relpath, "open");
                        }
                    });
                });

                if (window.lucide) lucide.createIcons();
            } else {
                historyList.innerHTML = `
                    <div class="history-empty">
                        <i data-lucide="inbox"></i>
                        <p>No downloads recorded yet.</p>
                    </div>
                `;
                if (window.lucide) lucide.createIcons();
            }
        } catch (err) {
            console.error("Failed to load history:", err);
        }
    }

    btnRefreshHistory.addEventListener("click", () => {
        loadHistory();
        showToast("🔄 History refreshed!");
    });

    // Start Download Flow
    btnStartDownload.addEventListener("click", () => {
        const url = urlInput.value.trim();
        if (!url) {
            showToast("⚠️ Please enter a Facebook URL first!");
            urlInput.focus();
            return;
        }

        const selectedModeInput = document.querySelector('input[name="downloadMode"]:checked');
        const mode = selectedModeInput ? selectedModeInput.value : "auto";
        const cookiesOption = browserCookies.value;

        // Reset Counters & UI
        photoCount = 0;
        videoCount = 0;
        statPhotos.textContent = "0 Photos";
        statVideos.textContent = "0 Videos";
        progressBarFill.style.width = "5%";
        progressPct.textContent = "5%";
        progressStatusText.innerHTML = '<span class="spinner-small"></span><span>Connecting to Facebook...</span>';
        completionBar.style.display = "none";
        progressPanel.style.display = "block";
        btnStartDownload.style.display = "none";
        btnCancelDownload.style.display = "inline-flex";

        terminalLog.innerHTML = `<div class="log-line info">🚀 Initiating download job [Mode: ${mode.toUpperCase()}]</div>`;

        // Build SSE URL
        const queryParams = new URLSearchParams({
            url: url,
            mode: mode,
            browser_cookies: cookiesOption
        });

        if (eventSource) {
            eventSource.close();
        }

        eventSource = new EventSource(`/api/download/stream?${queryParams.toString()}`);

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                handleStreamEvent(data);
            } catch (err) {
                console.error("Error parsing SSE event:", err);
            }
        };

        eventSource.onerror = (err) => {
            console.error("SSE Error:", err);
            appendLog("⚠️ Connection closed or interrupted.", "warning");
            finishDownloadUI(false);
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        };
    });

    // Handle SSE Event
    function handleStreamEvent(data) {
        const type = data.type;

        if (type === "log") {
            appendLog(data.message, data.level || "info");
        } else if (type === "progress") {
            const pct = Math.min(Math.max(data.percent || 0, 0), 100);
            progressBarFill.style.width = `${pct}%`;
            progressPct.textContent = `${pct}%`;
            if (data.text) {
                progressStatusText.innerHTML = `<span class="spinner-small"></span><span>${data.text}</span>`;
            }
        } else if (type === "item_downloaded") {
            if (data.media_type === "photo") {
                photoCount++;
                statPhotos.textContent = `${photoCount} Photos`;
            } else if (data.media_type === "video") {
                videoCount++;
                statVideos.textContent = `${videoCount} Videos`;
            }
            appendLog(data.message || `Downloaded: ${data.filename}`, "success");
        } else if (type === "error") {
            appendLog(`❌ ${data.message}`, "error");
            showToast(`❌ Error: ${data.message}`);
            finishDownloadUI(false);
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        } else if (type === "finished") {
            progressBarFill.style.width = "100%";
            progressPct.textContent = "100%";
            progressStatusText.innerHTML = `<span>Completed!</span>`;
            appendLog(data.message || "Download complete!", "success");
            
            completionBar.style.display = "flex";
            const successTitle = document.getElementById("successTitle");
            const successSubtitle = document.getElementById("successSubtitle");
            
            if (data.total_count > 0) {
                successTitle.textContent = `Successfully Downloaded ${data.total_count} File(s)!`;
                successSubtitle.textContent = `Saved ${data.photos_count} photo(s) and ${data.videos_count} video(s) into your downloads folder.`;
                showToast("🎉 Downloads complete! Ready to view.");
            } else {
                successTitle.textContent = "Extraction Finished";
                successSubtitle.textContent = "No downloadable media was detected. (Check if the post is private).";
            }

            finishDownloadUI(true);
            loadHistory();
            if (eventSource) {
                eventSource.close();
                eventSource = null;
            }
        }
    }

    // Cancel Button
    btnCancelDownload.addEventListener("click", () => {
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
        appendLog("⛔ Download cancelled by user.", "warning");
        finishDownloadUI(false);
        showToast("⏹️ Download process cancelled.");
    });

    function finishDownloadUI(isSuccess) {
        btnStartDownload.style.display = "inline-flex";
        btnCancelDownload.style.display = "none";
    }

    // Initial history load
    loadHistory();
});
