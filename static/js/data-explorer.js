/**
 * Data Explorer — 4-Tier Policy-Annotated Bus Data Viewer
 * Supports 3 view modes: Admin / Internal / External
 * Displays 4-tier classification badges: PUBLIC, PII, SPII, COMPANY_SECRET
 */

(function () {
    "use strict";

    // ---- State ----
    let currentTable = "drivers";
    let currentView = "admin"; // "admin" | "internal" | "external"
    let policyData = {};

    // ---- DOM refs ----
    const tableBody = document.getElementById("table-body");
    const tableHead = document.getElementById("table-head");
    const dataTable = document.getElementById("data-table");
    const viewIndicator = document.getElementById("view-indicator");
    const queryInput = document.getElementById("query-input");
    const classifyBtn = document.getElementById("classify-btn");
    const classResult = document.getElementById("class-result");
    const recordCount = document.getElementById("record-count");

    // ---- Policy badge helper ----
    function policyBadge(classification, action) {
        const cls = classification || "PUBLIC";
        let badgeClass = "badge-public";
        let icon = "fa-lock-open";
        let label = "PUBLIC";

        if (cls === "PII") {
            badgeClass = "badge-pii";
            icon = "fa-id-badge";
            label = `PII · ${action || "hash"}`;
        } else if (cls === "SPII") {
            badgeClass = "badge-spii";
            icon = "fa-user-shield";
            label = `SPII · ${action || "encrypt"}`;
        } else if (cls === "COMPANY_SECRET") {
            badgeClass = "badge-secret";
            icon = "fa-ban";
            label = "SECRET · redact";
        }

        return `<span class="badge ${badgeClass}"><i class="fa-solid ${icon}"></i> ${label}</span>`;
    }

    // ---- Cell rendering ----
    function renderCell(value) {
        if (value === null || value === undefined) return "";
        const str = String(value);

        if (currentView === "admin") return escapeHtml(str);

        if (str.startsWith("HASH:")) {
            return `<span class="cell-hashed">${escapeHtml(str)}</span>`;
        }
        if (str.startsWith("ENC:")) {
            return `<span class="cell-encrypted">${escapeHtml(str)}</span>`;
        }
        if (str.startsWith("[REDACTED:")) {
            return `<span class="cell-redacted">${escapeHtml(str)}</span>`;
        }
        return escapeHtml(str);
    }

    function escapeHtml(s) {
        const d = document.createElement("div");
        d.textContent = s;
        return d.innerHTML;
    }

    // ---- Fetch policy metadata ----
    async function loadPolicy() {
        try {
            const res = await fetch("/api/data-policy");
            const data = await res.json();
            policyData = data.all_fields || {};
        } catch (e) {
            console.error("Failed to load policy:", e);
        }
    }

    // ---- Fetch and render table ----
    async function loadTable() {
        dataTable.classList.add("loading");
        try {
            const res = await fetch(`/api/bus-data?table=${currentTable}&view=${currentView}`);
            const data = await res.json();
            const rows = data.data || [];
            recordCount.textContent = `${rows.length} records`;

            if (rows.length === 0) {
                tableHead.innerHTML = "<tr><th>No data</th></tr>";
                tableBody.innerHTML = "<tr><td>No records found</td></tr>";
                return;
            }

            // Build headers with policy badges
            const fields = Object.keys(rows[0]);
            const tablePolicies = policyData[currentTable] || {};

            let headHtml = "<tr>";
            for (const field of fields) {
                const fp = tablePolicies[field] || { classification: "PUBLIC", action: "pass" };
                headHtml += `<th><div class="th-content">
                    <span class="field-name">${escapeHtml(field)}</span>
                    ${policyBadge(fp.classification, fp.action)}
                </div></th>`;
            }
            headHtml += "</tr>";
            tableHead.innerHTML = headHtml;

            // Build body
            let bodyHtml = "";
            for (const row of rows) {
                bodyHtml += "<tr>";
                for (const field of fields) {
                    bodyHtml += `<td>${renderCell(row[field])}</td>`;
                }
                bodyHtml += "</tr>";
            }
            tableBody.innerHTML = bodyHtml;
        } catch (e) {
            console.error("Failed to load data:", e);
            tableBody.innerHTML = `<tr><td colspan="99">Error loading data: ${e.message}</td></tr>`;
        } finally {
            setTimeout(() => dataTable.classList.remove("loading"), 100);
        }
    }

    // ---- Summary cards ----
    async function loadSummaryCards() {
        try {
            const res = await fetch("/api/data-policy");
            const data = await res.json();
            const policies = data.policies || {};
            const tables = [
                { key: "bus_routes",          label: "Bus Routes" },
                { key: "bus_vehicles",         label: "Vehicles" },
                { key: "drivers",              label: "Drivers" },
                { key: "iot_sensor_readings",  label: "IoT Readings" },
                { key: "bus_stops",            label: "Bus Stops" },
                { key: "maintenance_logs",     label: "Maintenance" },
                { key: "driver_shifts",        label: "Shifts" },
                { key: "incidents",            label: "Incidents" },
            ];

            for (const t of tables) {
                const card = document.getElementById(`card-${t.key}`);
                if (!card) continue;
                const p = policies[t.key] || { public: [], pii: [], spii: [], company_secret: [] };
                const countsEl = card.querySelector(".field-counts");
                if (countsEl) {
                    countsEl.innerHTML = `
                        <span class="badge badge-public"><i class="fa-solid fa-lock-open"></i> ${(p.public || []).length} public</span>
                        <span class="badge badge-pii"><i class="fa-solid fa-id-badge"></i> ${(p.pii || []).length} PII</span>
                        <span class="badge badge-spii"><i class="fa-solid fa-user-shield"></i> ${(p.spii || []).length} SPII</span>
                        <span class="badge badge-secret"><i class="fa-solid fa-ban"></i> ${(p.company_secret || []).length} secret</span>
                    `;
                }
            }
        } catch (e) {
            console.error("Failed to load summary:", e);
        }
    }

    // ---- Table tab selection ----
    function selectTable(tableKey) {
        currentTable = tableKey;
        document.querySelectorAll(".summary-card").forEach(c => c.classList.remove("active"));
        const card = document.getElementById(`card-${tableKey}`);
        if (card) card.classList.add("active");
        loadTable();
    }

    // ---- View selector ----
    const viewConfig = {
        admin: {
            cls: "admin-view",
            html: '<i class="fa-solid fa-user-gear"></i> Admin View — All Data',
        },
        internal: {
            cls: "internal-view",
            html: '<i class="fa-solid fa-building"></i> Internal View — SPII Masked',
        },
        external: {
            cls: "external-view",
            html: '<i class="fa-solid fa-handshake"></i> External View — Policy Applied',
        },
    };

    function selectView(view) {
        currentView = view;

        // Update button states
        document.querySelectorAll(".view-btn").forEach(btn => {
            btn.classList.toggle("active", btn.dataset.view === view);
        });

        // Update indicator
        const cfg = viewConfig[view];
        viewIndicator.className = "view-indicator " + cfg.cls;
        viewIndicator.innerHTML = cfg.html;

        loadTable();
    }

    // ---- Query classifier ----
    async function classifyQuery() {
        const query = queryInput.value.trim();
        if (!query) return;

        try {
            const res = await fetch("/api/classify-query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ query }),
            });
            const data = await res.json();

            let badgeClass = "badge-public";
            if (data.classification === "PII") badgeClass = "badge-pii";
            if (data.classification === "SPII") badgeClass = "badge-spii";
            if (data.classification === "COMPANY_SECRET") badgeClass = "badge-secret";

            let html = `
                <div class="result-classification">
                    <span>Classification:</span>
                    <span class="badge ${badgeClass}">${data.classification}</span>
                </div>
                <div class="result-recommendation">${escapeHtml(data.recommendation)}</div>
            `;

            if (data.matched_keywords && data.matched_keywords.length > 0) {
                html += `<div class="result-keywords">`;
                for (const kw of data.matched_keywords) {
                    html += `<span class="keyword-tag">${escapeHtml(kw)}</span>`;
                }
                html += `</div>`;
            }

            classResult.innerHTML = html;
        } catch (e) {
            classResult.innerHTML = `<div class="result-recommendation">Error: ${e.message}</div>`;
        }
    }

    // ---- Event listeners ----
    document.querySelectorAll(".summary-card").forEach(card => {
        card.addEventListener("click", () => {
            const table = card.dataset.table;
            if (table) selectTable(table);
        });
    });

    document.querySelectorAll(".view-btn").forEach(btn => {
        btn.addEventListener("click", () => selectView(btn.dataset.view));
    });

    classifyBtn.addEventListener("click", classifyQuery);
    queryInput.addEventListener("keydown", e => {
        if (e.key === "Enter") classifyQuery();
    });

    // ---- Init ----
    async function init() {
        await loadPolicy();
        await loadSummaryCards();
        selectView("admin");
        selectTable("drivers");
    }

    init();
})();
