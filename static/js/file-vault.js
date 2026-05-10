/**
 * File Vault — Frontend Controller
 * ==================================
 * Google-Drive-like file manager with 4-tier policy enforcement.
 */

(function () {
    "use strict";

    /* ── State ──────────────────────────────────────────────── */
    let currentView = "admin";          // admin | internal | external
    let currentTier = null;             // null = ALL
    let isListMode  = false;
    let pendingFiles = [];              // files in upload queue
    let allFiles = [];                  // cached file list
    let openFileId = null;              // file detail modal

    /* ── DOM refs ──────────────────────────────────────────── */
    const $ = (sel) => document.querySelector(sel);
    const $$ = (sel) => [...document.querySelectorAll(sel)];

    /* ── Helpers ───────────────────────────────────────────── */
    function formatBytes(b) {
        if (b === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB"];
        const i = Math.floor(Math.log(b) / Math.log(k));
        return parseFloat((b / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
    }

    function relativeDate(iso) {
        const d = new Date(iso);
        const now = Date.now();
        const diff = now - d.getTime();
        if (diff < 60000) return "just now";
        if (diff < 3600000) return Math.floor(diff / 60000) + "m ago";
        if (diff < 86400000) return Math.floor(diff / 3600000) + "h ago";
        return d.toLocaleDateString("en-SE", { month: "short", day: "numeric" });
    }

    function fileIcon(ext) {
        const map = {
            ".pdf": ["fa-file-pdf", "ext-pdf"],
            ".txt": ["fa-file-lines", "ext-txt"],
            ".md":  ["fa-file-lines", "ext-txt"],
            ".csv": ["fa-file-csv", "ext-csv"],
            ".json": ["fa-file-code", "ext-json"],
            ".xml": ["fa-file-code", "ext-json"],
            ".html": ["fa-file-code", "ext-json"],
            ".png": ["fa-file-image", "ext-img"],
            ".jpg": ["fa-file-image", "ext-img"],
            ".jpeg": ["fa-file-image", "ext-img"],
            ".gif": ["fa-file-image", "ext-img"],
            ".svg": ["fa-file-image", "ext-img"],
            ".xlsx": ["fa-file-excel", "ext-csv"],
            ".xls": ["fa-file-excel", "ext-csv"],
            ".doc": ["fa-file-word", "ext-doc"],
            ".docx": ["fa-file-word", "ext-doc"],
            ".pem": ["fa-key", "ext-key"],
            ".key": ["fa-key", "ext-key"],
            ".env": ["fa-key", "ext-key"],
            ".zip": ["fa-file-zipper", "ext-default"],
        };
        const m = map[ext] || ["fa-file", "ext-default"];
        return m;
    }

    function tierBadge(tier) {
        const cls = {
            PUBLIC: "badge-public",
            PII:    "badge-pii",
            SPII:   "badge-spii",
            SECRET: "badge-secret",
        }[tier] || "badge-public";
        const icons = {
            PUBLIC: "fa-lock-open",
            PII:    "fa-user-shield",
            SPII:   "fa-shield-halved",
            SECRET: "fa-ban",
        };
        return `<span class="badge ${cls}"><i class="fa-solid ${icons[tier] || "fa-lock-open"}"></i> ${tier}</span>`;
    }

    function toast(msg) {
        const el = document.createElement("div");
        el.className = "vault-toast";
        el.innerHTML = `<i class="fa-solid fa-circle-check"></i> ${msg}`;
        document.body.appendChild(el);
        setTimeout(() => el.remove(), 3200);
    }

    /* ── API helpers ───────────────────────────────────────── */
    async function api(method, path, body, isForm) {
        const opts = { method };
        if (isForm) {
            opts.body = body;   // FormData
        } else if (body) {
            opts.headers = { "Content-Type": "application/json" };
            opts.body = JSON.stringify(body);
        }
        const res = await fetch(path, opts);
        if (!res.ok) throw new Error(await res.text());
        return res.json();
    }

    /* ── Load data ─────────────────────────────────────────── */
    async function loadStats() {
        try {
            const stats = await api("GET", "/api/vault/stats");
            $("#stat-total").textContent = stats.total_files;
            $("#stat-total-size").textContent = formatBytes(stats.total_size_bytes);
            for (const t of ["PUBLIC", "PII", "SPII", "SECRET"]) {
                const d = stats.by_tier[t] || { count: 0, size_bytes: 0 };
                $(`#stat-${t.toLowerCase()}`).textContent = d.count;
                $(`#stat-${t.toLowerCase()}-size`).textContent = formatBytes(d.size_bytes);
            }
        } catch (e) {
            console.error("stats error", e);
        }
    }

    async function loadFiles() {
        try {
            const params = new URLSearchParams({ view: currentView });
            if (currentTier) params.set("tier", currentTier);
            const search = $("#search-input").value.trim();
            if (search) params.set("search", search);
            const data = await api("GET", `/api/vault/files?${params}`);
            allFiles = data.files;
            $("#file-count").textContent = `${data.count} file${data.count !== 1 ? "s" : ""}`;
            renderFiles();
        } catch (e) {
            console.error("load error", e);
        }
    }

    /* ── Render files ──────────────────────────────────────── */
    function renderFiles() {
        const container = $("#file-container");
        if (allFiles.length === 0) {
            container.innerHTML = `
                <div class="empty-vault">
                    <i class="fa-solid fa-cloud-arrow-up"></i>
                    <h3>Your vault is empty</h3>
                    <p>Upload files to get started. Each file will be automatically classified into the appropriate security tier.</p>
                    <button class="primary-button trigger-upload" type="button"><i class="fa-solid fa-plus"></i> Upload your first file</button>
                </div>`;
            container.querySelector(".trigger-upload")?.addEventListener("click", openUpload);
            return;
        }

        container.innerHTML = allFiles.map(f => {
            const [icon, iconCls] = fileIcon(f.extension);
            const starred = f.starred ? "starred" : "";
            return `
                <div class="file-card" data-id="${f.file_id}">
                    <div class="card-top-row">
                        <div class="file-icon ${iconCls}"><i class="fa-solid ${icon}"></i></div>
                        <i class="fa-${f.starred ? "solid" : "regular"} fa-star star-icon ${starred}"></i>
                    </div>
                    <div class="file-name" title="${f.filename}">${f.filename}</div>
                    <div class="file-meta">
                        ${tierBadge(f.tier)}
                        <span class="file-size">${formatBytes(f.size_bytes)}</span>
                        <span class="file-date">${relativeDate(f.uploaded_at)}</span>
                    </div>
                </div>`;
        }).join("");

        // Click handlers
        container.querySelectorAll(".file-card").forEach(card => {
            card.addEventListener("click", () => openDetail(card.dataset.id));
        });
    }

    /* ── Tier filter ───────────────────────────────────────── */
    function initTierCards() {
        $$(".tier-card").forEach(card => {
            card.addEventListener("click", () => {
                $$(".tier-card").forEach(c => c.classList.remove("active"));
                card.classList.add("active");
                const tier = card.dataset.tier;
                currentTier = tier === "ALL" ? null : tier;
                const heading = tier === "ALL" ? "All Files" : `${tier} Files`;
                $("#files-heading").textContent = heading;
                loadFiles();
            });
        });
    }

    /* ── View toggle ───────────────────────────────────────── */
    function initViewToggle() {
        const labelAdmin = $("#label-admin");
        const btn1 = $("#view-toggle-1");
        const btn2 = $("#view-toggle-2");
        const indicator = $("#view-indicator");

        function setView(view) {
            currentView = view;
            [labelAdmin, btn1, btn2].forEach(b => b.classList.remove("active"));
            if (view === "admin") {
                labelAdmin.classList.add("active");
                indicator.className = "view-indicator internal";
                indicator.innerHTML = '<i class="fa-solid fa-user-tie"></i> Admin View — Full Access';
            } else if (view === "internal") {
                btn1.classList.add("active");
                indicator.className = "view-indicator internal";
                indicator.innerHTML = '<i class="fa-solid fa-server"></i> Internal View — Local LLM';
            } else {
                btn2.classList.add("active");
                indicator.className = "view-indicator external-view";
                indicator.innerHTML = '<i class="fa-solid fa-cloud"></i> External View — Cloud LLM';
            }
            loadFiles();
        }

        labelAdmin.addEventListener("click", () => setView("admin"));
        btn1.addEventListener("click", () => setView("internal"));
        btn2.addEventListener("click", () => setView("external"));
    }

    /* ── Grid / List toggle ────────────────────────────────── */
    function initViewMode() {
        const gridBtn = $("#view-grid");
        const listBtn = $("#view-list");
        const container = $("#file-container");

        gridBtn.addEventListener("click", () => {
            isListMode = false;
            gridBtn.classList.add("active");
            listBtn.classList.remove("active");
            container.classList.remove("list-mode");
        });

        listBtn.addEventListener("click", () => {
            isListMode = true;
            listBtn.classList.add("active");
            gridBtn.classList.remove("active");
            container.classList.add("list-mode");
        });
    }

    /* ── Search ────────────────────────────────────────────── */
    function initSearch() {
        let debounce;
        $("#search-input").addEventListener("input", () => {
            clearTimeout(debounce);
            debounce = setTimeout(loadFiles, 300);
        });
    }

    /* ── Upload Modal ──────────────────────────────────────── */
    function openUpload() {
        pendingFiles = [];
        renderQueue();
        $("#upload-modal").style.display = "grid";
        $("#submit-upload").disabled = true;
        
        // Reset fields
        $("#upload-tier").value = "";
        $("#upload-tags").value = "";
        $("#upload-desc").value = "";
        $("#upload-reasoning").style.display = "none";
    }

    function closeUpload() {
        $("#upload-modal").style.display = "none";
        pendingFiles = [];
    }

    function renderQueue() {
        const queue = $("#upload-queue");
        if (pendingFiles.length === 0) {
            queue.innerHTML = "";
            $("#submit-upload").disabled = true;
            return;
        }
        $("#submit-upload").disabled = false;
        queue.innerHTML = pendingFiles.map((f, i) => {
            const [icon] = fileIcon("." + f.name.split(".").pop().toLowerCase());
            return `
                <div class="queue-item">
                    <div class="q-icon"><i class="fa-solid ${icon}"></i></div>
                    <div class="q-info">
                        <div class="q-name">${f.name}</div>
                        <div class="q-size">${formatBytes(f.size)}</div>
                    </div>
                    <button class="q-remove" data-idx="${i}" type="button"><i class="fa-solid fa-xmark"></i></button>
                </div>`;
        }).join("");

        queue.querySelectorAll(".q-remove").forEach(btn => {
            btn.addEventListener("click", (e) => {
                e.stopPropagation();
                pendingFiles.splice(+btn.dataset.idx, 1);
                renderQueue();
            });
        });
    }

    function initUpload() {
        const uploadBtn = $("#upload-btn");
        const closeBtn = $("#modal-close");
        const dropZone = $("#drop-zone");
        const fileInput = $("#file-input");
        const submitBtn = $("#submit-upload");

        uploadBtn.addEventListener("click", openUpload);
        closeBtn.addEventListener("click", closeUpload);
        $("#upload-modal").addEventListener("click", (e) => {
            if (e.target.id === "upload-modal") closeUpload();
        });

        // Trigger uploads from empty state too
        document.addEventListener("click", (e) => {
            if (e.target.closest(".trigger-upload")) openUpload();
        });

        // Drop zone
        dropZone.addEventListener("click", () => fileInput.click());
        dropZone.addEventListener("dragover", (e) => { e.preventDefault(); dropZone.classList.add("drag-over"); });
        dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("drag-over");
            addFilesToQueue(e.dataTransfer.files);
        });

        fileInput.addEventListener("change", () => {
            addFilesToQueue(fileInput.files);
            fileInput.value = "";
        });

        // Submit
        submitBtn.addEventListener("click", async () => {
            if (pendingFiles.length === 0) return;
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Uploading…';

            const tier = $("#upload-tier").value;
            const tags = $("#upload-tags").value;
            const desc = $("#upload-desc").value;

            for (const f of pendingFiles) {
                const fd = new FormData();
                fd.append("file", f);
                if (tier) fd.append("tier", tier);
                if (tags) fd.append("tags", tags);
                if (desc) fd.append("description", desc);
                try {
                    await api("POST", "/api/vault/upload", fd, true);
                } catch (err) {
                    console.error("upload error", err);
                }
            }

            closeUpload();
            toast(`${pendingFiles.length} file${pendingFiles.length > 1 ? "s" : ""} uploaded`);
            pendingFiles = [];
            await loadStats();
            await loadFiles();
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload';
        });
    }

    async function addFilesToQueue(fileList) {
        for (const f of fileList) {
            if (!pendingFiles.some(p => p.name === f.name && p.size === f.size)) {
                pendingFiles.push(f);
            }
        }
        renderQueue();
        
        if (pendingFiles.length > 0) {
            await autoAnalyzeFile(pendingFiles[0]);
        }
    }

    async function autoAnalyzeFile(file) {
        const submitBtn = $("#submit-upload");
        const reasoningDiv = $("#upload-reasoning");
        
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing...';
        reasoningDiv.style.display = "block";
        reasoningDiv.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Analyzing file sensitivity...';
        reasoningDiv.style.borderLeftColor = "var(--text-secondary)";

        const fd = new FormData();
        fd.append("file", file);

        try {
            const result = await api("POST", "/api/vault/analyze", fd, true);
            if (result.tier) {
                $("#upload-tier").value = result.tier;
                $("#upload-tags").value = result.tags || "";
                $("#upload-desc").value = result.description || "";
                
                reasoningDiv.innerHTML = `<strong>Suggested Tier: ${result.tier}</strong><br>${result.reasoning}`;
                
                const colors = {
                    "PUBLIC": "#16a34a",
                    "PII": "#d97706",
                    "SPII": "#7c3aed",
                    "SECRET": "#dc2626"
                };
                reasoningDiv.style.borderLeftColor = colors[result.tier] || "#3b82f6";
            } else {
                reasoningDiv.style.display = "none";
            }
        } catch (err) {
            console.error("Analysis failed", err);
            reasoningDiv.innerHTML = "Analysis failed. You can set fields manually.";
            reasoningDiv.style.borderLeftColor = "#dc2626";
        } finally {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fa-solid fa-upload"></i> Upload';
        }
    }

    /* ── File Detail Modal ─────────────────────────────────── */
    function openDetail(fileId) {
        const f = allFiles.find(x => x.file_id === fileId);
        if (!f) return;
        openFileId = fileId;

        $("#detail-filename").innerHTML = `<i class="fa-solid fa-file"></i> ${f.filename}`;
        $("#detail-id").textContent = f.file_id;
        $("#detail-tier-badge").innerHTML = tierBadge(f.tier);
        $("#detail-size").textContent = formatBytes(f.size_bytes);
        $("#detail-type").textContent = f.mime_guess || f.extension;
        $("#detail-date").textContent = new Date(f.uploaded_at).toLocaleString();
        $("#detail-downloads").textContent = f.download_count;
        $("#detail-hash").textContent = f.sha256;
        $("#detail-tier-select").value = f.tier;

        const starBtn = $("#detail-star");
        starBtn.innerHTML = f.starred
            ? '<i class="fa-solid fa-star"></i> Unstar'
            : '<i class="fa-regular fa-star"></i> Star';

        $("#detail-modal").style.display = "grid";
    }

    function closeDetail() {
        $("#detail-modal").style.display = "none";
        openFileId = null;
    }

    function initDetail() {
        $("#detail-close").addEventListener("click", closeDetail);
        $("#detail-modal").addEventListener("click", (e) => {
            if (e.target.id === "detail-modal") closeDetail();
        });

        // Change tier
        $("#detail-tier-select").addEventListener("change", async () => {
            if (!openFileId) return;
            await api("PUT", `/api/vault/files/${openFileId}`, { tier: $("#detail-tier-select").value });
            toast("Tier updated");
            await loadStats();
            await loadFiles();
            // Re-open with fresh data
            openDetail(openFileId);
        });

        // Download
        $("#detail-download").addEventListener("click", () => {
            if (!openFileId) return;
            window.open(`/api/vault/download/${openFileId}`, "_blank");
        });

        // Star
        $("#detail-star").addEventListener("click", async () => {
            if (!openFileId) return;
            const f = allFiles.find(x => x.file_id === openFileId);
            await api("PUT", `/api/vault/files/${openFileId}`, { starred: !f.starred });
            toast(f.starred ? "Unstarred" : "Starred");
            await loadFiles();
            openDetail(openFileId);
        });

        // Delete
        $("#detail-delete").addEventListener("click", async () => {
            if (!openFileId) return;
            if (!confirm("Delete this file permanently?")) return;
            await api("DELETE", `/api/vault/files/${openFileId}`);
            closeDetail();
            toast("File deleted");
            await loadStats();
            await loadFiles();
        });
    }

    /* ── Keyboard shortcut ─────────────────────────────────── */
    document.addEventListener("keydown", (e) => {
        if (e.key === "Escape") {
            closeUpload();
            closeDetail();
        }
    });

    /* ── Init ──────────────────────────────────────────────── */
    async function init() {
        initTierCards();
        initViewToggle();
        initViewMode();
        initSearch();
        initUpload();
        initDetail();
        await loadStats();
        await loadFiles();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();
