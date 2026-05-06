/**
 * Data Explorer — Policy-Annotated Bus Data Viewer
 * Fetches Stockholm bus data and shows per-column policy badges.
 */

(function () {
    "use strict";

    // ---- State ----
    let currentTable = "drivers";
    let currentView = "internal"; // "internal" | "external"
    let policyData = {};          // field-level policy metadata

    // ---- DOM refs ----
    const tableBody = document.getElementById("table-body");
    const tableHead = document.getElementById("table-head");
    const dataTable = document.getElementById("data-table");
    const viewToggle = document.getElementById("view-toggle");
    const viewIndicator = document.getElementById("view-indicator");
    const labelInternal = document.getElementById("label-internal");
    const labelExternal = document.getElementById("label-external");
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
            icon = "fa-user-shield";
            label = `PII · ${action || "hash"}`;
        } else if (cls === "COMPANY_SECRET") {
            badgeClass = "badge-secret";
            icon = "fa-ban";
            label = "SECRET · redact";
        }

        return `<span class="badge ${badgeClass}"><i class="fa-solid ${icon}"></i> ${label}</span>`;
    }

    // ---- Cell rendering ----
    function renderCell(value, field) {
        if (currentView === "internal") return escapeHtml(String(value));

        const str = String(value);
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
                    bodyHtml += `<td>${renderCell(row[field], field)}</td>`;
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
                { key: "bus_routes", icon: "fa-route", label: "Bus Routes" },
                { key: "bus_vehicles", icon: "fa-bus", label: "Vehicles" },
                { key: "drivers", icon: "fa-id-card", label: "Drivers" },
                { key: "iot_sensor_readings", icon: "fa-satellite-dish", label: "IoT Readings" },
            ];

            for (const t of tables) {
                const card = document.getElementById(`card-${t.key}`);
                if (!card) continue;
                const p = policies[t.key] || { public: [], pii: [], company_secret: [] };
                const countsEl = card.querySelector(".field-counts");
                if (countsEl) {
                    countsEl.innerHTML = `
                        <span class="badge badge-public"><i class="fa-solid fa-lock-open"></i> ${p.public.length} public</span>
                        <span class="badge badge-pii"><i class="fa-solid fa-user-shield"></i> ${p.pii.length} PII</span>
                        <span class="badge badge-secret"><i class="fa-solid fa-ban"></i> ${p.company_secret.length} secret</span>
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

    // ---- Toggle view ----
    function toggleView() {
        currentView = currentView === "internal" ? "external" : "internal";
        viewToggle.classList.toggle("external", currentView === "external");
        labelInternal.classList.toggle("active", currentView === "internal");
        labelExternal.classList.toggle("active", currentView === "external");

        viewIndicator.className = "view-indicator " + (currentView === "internal" ? "internal" : "external-view");
        viewIndicator.innerHTML = currentView === "internal"
            ? '<i class="fa-solid fa-building"></i> Internal View — Full Data'
            : '<i class="fa-solid fa-handshake"></i> External Partner View — Policy Applied';
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

    viewToggle.addEventListener("click", toggleView);

    classifyBtn.addEventListener("click", classifyQuery);
    queryInput.addEventListener("keydown", e => {
        if (e.key === "Enter") classifyQuery();
    });

    // ---- Init ----
    async function init() {
        await loadPolicy();
        await loadSummaryCards();
        selectTable("drivers"); // Start with drivers — most interesting for PII demo
    }

    init();
})();
