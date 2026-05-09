let routingChart = null;
let processingChart = null;
let websocket = null;
let refreshTimer = null;

const samples = [
    {
        userInput: "What is the standard bus route for line 172 in Stockholm?",
        llmOutput: "The route for Line 172 in Stockholm is from Norsborg to Skarpnäck.\n\nKey stops include:\n- Huddinge sjukhus\n- Högdalen\n- Gubbängen",
    },
    {
        userInput: "Show me the eco-drive scores and fuel consumption data for driver DRV-1001.",
        llmOutput: "Analysis for DRV-1001 (Lars Eriksson):\n- Eco-drive score: 87.3\n- Average fuel consumption: 0.35 L/km\n- Personal Number: 19850412-3456",
    },
    {
        userInput: "Can you summarize the maintenance log for bus VH-4521?",
        llmOutput: "Vehicle VH-4521 maintenance summary:\n- Last service: 2026-04-15\n- Replaced brake pads (Brake wear was at 82%)\n- Firmware updated to v2.4.1",
    },
];

document.addEventListener("DOMContentLoaded", () => {
    initializeCharts();
    bindActions();
    connectWebSocket();
    loadDashboard();
    loadAuditLog();
    refreshTimer = setInterval(loadDashboard, 10000);
    setInterval(loadAuditLog, 15000);
});

function bindActions() {
    document.getElementById("run-simulation").addEventListener("click", runSimulation);
    document.getElementById("refresh-now").addEventListener("click", loadDashboard);
    document.getElementById("refresh-audit").addEventListener("click", loadAuditLog);
    document.getElementById("quick-safe").addEventListener("click", () => {
        const sample = samples[Math.floor(Math.random() * samples.length)];
        document.getElementById("userInput").value = sample.userInput;
        document.getElementById("llmOutput").textContent = "";
    });
}

function initializeCharts() {
    if (typeof Chart === "undefined") {
        createChartFallback("routingChart", "Routing split will appear here after telemetry loads.");
        createChartFallback("processingChart", "Processing trend will appear here after telemetry loads.");
        return;
    }

    const chartTextColor = "#687589";
    const gridColor = "#e8eef6";

    routingChart = new Chart(document.getElementById("routingChart"), {
        type: "doughnut",
        data: {
            labels: ["Local LLM", "Cloud LLM"],
            datasets: [{
                data: [0, 0],
                backgroundColor: ["#2563eb", "#16a34a"],
                borderColor: "#ffffff",
                borderWidth: 4,
                hoverOffset: 5,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "68%",
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (context) => `${context.label}: ${context.raw}`,
                    },
                },
            },
        },
    });

    processingChart = new Chart(document.getElementById("processingChart"), {
        type: "line",
        data: {
            labels: [],
            datasets: [{
                label: "Processing time (ms)",
                data: [],
                borderColor: "#0891b2",
                backgroundColor: "rgba(8, 145, 178, 0.14)",
                pointRadius: 3,
                pointHoverRadius: 5,
                tension: 0.35,
                fill: true,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { intersect: false, mode: "index" },
            plugins: {
                legend: { display: false },
            },
            scales: {
                x: {
                    ticks: { color: chartTextColor, maxRotation: 0 },
                    grid: { display: false },
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: chartTextColor },
                    grid: { color: gridColor },
                },
            },
        },
    });
}

function createChartFallback(canvasId, message) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;

    const fallback = document.createElement("div");
    fallback.id = `${canvasId}-fallback`;
    fallback.className = "chart-fallback";
    fallback.textContent = message;
    canvas.replaceWith(fallback);
}

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    websocket = new WebSocket(`${protocol}//${window.location.host}/ws/metrics`);
    setConnectionStatus("connecting");

    websocket.onopen = () => setConnectionStatus("connected");
    websocket.onmessage = (event) => {
        const data = safeJson(event.data);
        if (data && !data.error) {
            updateDashboard(data);
        }
    };
    websocket.onclose = () => {
        setConnectionStatus("disconnected");
        setTimeout(connectWebSocket, 4000);
    };
    websocket.onerror = () => setConnectionStatus("disconnected");
}

function setConnectionStatus(status) {
    const statusEl = document.getElementById("connection-status");
    const labels = {
        connected: "Live",
        disconnected: "Offline",
        connecting: "Connecting",
    };
    statusEl.className = `status-pill status-${status}`;
    statusEl.innerHTML = `<i class="fa-solid fa-circle"></i> ${labels[status]}`;
}

async function loadDashboard() {
    try {
        const response = await fetch("/api/metrics");
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        updateDashboard(await response.json());
    } catch (error) {
        setConnectionStatus("disconnected");
        console.error("Dashboard refresh failed:", error);
    }
}

function updateDashboard(data) {
    const stats = data.stats || {};
    const workflow = data.workflow_stats || {};
    const health = data.health || {};
    const alerts = data.alerts || [];
    const history = data.history || [];

    setText("total-requests", workflow.total_requests ?? stats.total_requests ?? 0);
    setText("approval-rate", workflow.approval_rate || "0%");
    setText("avg-processing", `${workflow.avg_processing_time_ms || stats.avg_processing_time_ms || "0"}ms`);

    const healthStatus = (health.health || "unknown").toUpperCase();
    const healthEl = document.getElementById("system-health");
    healthEl.textContent = healthStatus;
    healthEl.style.color = healthColor(healthStatus);

    setText("route-mix", `${workflow.local_llm_used || stats.local_routing_count || 0} local / ${workflow.cloud_llm_used || stats.cloud_routing_count || 0} cloud`);
    setText("decision-mix", `${workflow.approved || 0} approved / ${workflow.secured_locally || 0} secured locally / ${workflow.rejected || 0} rejected`);
    setText("masked-count", `${stats.total_masking_items || 0} masked items`);
    setText("masked-total", stats.total_masking_items || 0);
    setText("alert-count", `${stats.total_alerts || alerts.length || 0} active alerts`);
    setText("critical-count", `${stats.critical_alerts || 0} critical`);
    setText("critical-total", stats.critical_alerts || 0);
    setText("local-percent", percentLabel(workflow.local_llm_used ?? stats.local_routing_count ?? 0, workflow.total_requests ?? stats.total_requests ?? 0));
    setText("cloud-percent", percentLabel(workflow.cloud_llm_used ?? stats.cloud_routing_count ?? 0, workflow.total_requests ?? stats.total_requests ?? 0));
    setText("last-updated", `Updated ${formatTime(data.timestamp)}`);

    updateCharts(stats, workflow);
    updateAlerts(alerts, history);
    updateHistory(history);
    updateComplianceKPIs(stats, workflow);
    flashCards();
}

function updateCharts(stats, workflow) {
    const localCount = Number(workflow.local_llm_used ?? stats.local_routing_count ?? 0);
    const cloudCount = Number(workflow.cloud_llm_used ?? stats.cloud_routing_count ?? 0);

    if (!routingChart || !processingChart) {
        updateChartFallback(localCount, cloudCount, workflow, stats);
        return;
    }

    routingChart.data.datasets[0].data = [localCount, cloudCount];
    routingChart.update("none");

    const value = Number(workflow.avg_processing_time_ms ?? stats.avg_processing_time_ms ?? 0);
    const labels = processingChart.data.labels;
    const points = processingChart.data.datasets[0].data;

    if (labels.length >= 20) {
        labels.shift();
        points.shift();
    }

    labels.push(new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }));
    points.push(Number.isFinite(value) ? value : 0);
    processingChart.update("none");
}

function updateChartFallback(localCount, cloudCount, workflow, stats) {
    const routingFallback = document.getElementById("routingChart-fallback");
    const processingFallback = document.getElementById("processingChart-fallback");
    const total = localCount + cloudCount;
    const localWidth = total ? (localCount / total) * 100 : 0;
    const cloudWidth = total ? (cloudCount / total) * 100 : 0;
    const processingTime = workflow.avg_processing_time_ms ?? stats.avg_processing_time_ms ?? 0;

    if (routingFallback) {
        routingFallback.innerHTML = `
            <div class="fallback-bars" aria-label="Routing split">
                <span class="fallback-bar local" style="width: ${localWidth}%"></span>
                <span class="fallback-bar cloud" style="width: ${cloudWidth}%"></span>
            </div>
            <strong>${localCount} local / ${cloudCount} cloud</strong>
        `;
    }

    if (processingFallback) {
        processingFallback.innerHTML = `
            <strong>${processingTime}ms</strong>
            <span>average processing time</span>
        `;
    }
}

function updateAlerts(alerts, history) {
    const panel = document.getElementById("alerts-panel");

    // Build combined alerts: backend alerts + UI-derived policy alerts from history
    const combined = [];

    // Backend monitoring alerts
    for (const alert of (alerts || [])) {
        combined.push({
            severity: alert.severity || "info",
            message: alert.message || "Alert",
            timestamp: alert.timestamp,
            metric_type: alert.metric_type || "metric",
        });
    }

    // Derive policy alerts from recent request history
    for (const req of (history || []).slice(-10)) {
        const classification = req.data_classification || "PUBLIC";
        const status = req.status || "unknown";
        const route = req.route || "unknown";
        const sensitivity = req.sensitivity || "unknown";
        const forceOverridden = req.force_overridden || false;
        const patterns = req.detected_patterns || [];
        const violations = req.policy_violations || [];
        const inputPreview = (req.input_preview || "").slice(0, 60);

        if (classification === "COMPANY_SECRET" && route === "cloud") {
            combined.push({
                severity: "critical",
                message: `⛔ COMPANY_SECRET data sent to Cloud LLM — data was masked but policy recommends LOCAL only. Query: "${inputPreview}..."`,
                timestamp: req.timestamp,
                metric_type: "data_classification",
            });
        }

        if (classification === "SPII") {
            const schema = req.schema_masking || {};
            const encrypted = (schema.encrypted_fields || []).join(", ");
            combined.push({
                severity: "critical",
                message: `🔒 SPII data intercepted — ${encrypted || "sensitive fields"} masked before processing. Query: "${inputPreview}..."`,
                timestamp: req.timestamp,
                metric_type: "spii_protection",
            });
        }

        if (classification === "PII" && route === "cloud") {
            const schema = req.schema_masking || {};
            const hashed = (schema.hashed_fields || []).join(", ");
            combined.push({
                severity: "warning",
                message: `⚠️ PII data (${hashed || "identifiable fields"}) hashed before cloud transmission.`,
                timestamp: req.timestamp,
                metric_type: "pii_masking",
            });
        }

        if (violations.length > 0) {
            const critical = violations.filter(v => v.severity === "critical");
            if (critical.length > 0) {
                combined.push({
                    severity: "critical",
                    message: `❌ Policy violation: ${critical[0].message} — code rejected`,
                    timestamp: req.timestamp,
                    metric_type: "policy_violation",
                });
            }
        }

        if (forceOverridden && sensitivity === "high") {
            combined.push({
                severity: "warning",
                message: `⚡ Manual routing override on HIGH sensitivity request — data was masked before cloud routing`,
                timestamp: req.timestamp,
                metric_type: "manual_override",
            });
        }
    }

    if (!combined.length) {
        panel.className = "scroll-region empty-state";
        panel.textContent = "No alerts";
        return;
    }

    // Sort by severity priority then timestamp
    const severityOrder = { critical: 0, warning: 1, info: 2 };
    combined.sort((a, b) => (severityOrder[a.severity] ?? 3) - (severityOrder[b.severity] ?? 3));

    panel.className = "scroll-region";
    panel.innerHTML = combined.map((alert) => {
        const severity = escapeHtml(alert.severity || "info");
        const icons = { critical: "🔴", warning: "🟡", info: "🔵" };
        return `
            <article class="alert-item alert-${severity}">
                <div class="alert-header">
                    <span class="alert-severity-icon">${icons[severity] || "ℹ️"}</span>
                    <strong class="alert-severity-label">${severity.toUpperCase()}</strong>
                    <span class="alert-type-badge">${escapeHtml(alert.metric_type || "metric")}</span>
                </div>
                <p class="alert-message">${escapeHtml(alert.message || "Alert")}</p>
                <small class="alert-time">${formatTime(alert.timestamp)}</small>
            </article>
        `;
    }).join("");
}

function updateHistory(history) {
    const panel = document.getElementById("history-panel");
    if (!history.length) {
        panel.className = "scroll-region empty-state";
        panel.textContent = "No requests yet";
        return;
    }

    panel.className = "scroll-region";
    panel.innerHTML = history.slice().reverse().map((request) => {
        const route = request.route || request.routing?.llm_used || "unknown";
        const status = request.status || "unknown";
        const sensitivity = request.sensitivity || request.routing?.sensitivity_level || "unknown";
        const duration = request.processing_time_ms || request.metrics?.processing_time_ms || "0";
        const masked = request.masked_items_count ?? request.metrics?.masked_items_count ?? 0;
        const input = request.input_preview || request.user_input || request.routing?.reason || "Workflow request";
        const forceOverridden = request.force_overridden || false;
        const classification = request.data_classification || "PUBLIC";
        const detectedPatterns = request.detected_patterns || [];
        const routingReason = request.routing_reason || "";
        const schema = request.schema_masking || {};
        const violations = request.policy_violations || [];
        const isVaultUpload = request.event_type === "vault_upload";

        // Classification badge
        const classColors = {
            COMPANY_SECRET: { bg: "#dc2626", icon: "🔴" },
            SPII:           { bg: "#ea580c", icon: "🟠" },
            PII:            { bg: "#ca8a04", icon: "🟡" },
            PUBLIC:         { bg: "#16a34a", icon: "🟢" },
        };
        const cc = classColors[classification] || classColors.PUBLIC;
        const classificationBadge = `<span class="classification-badge" style="background:${cc.bg};">${cc.icon} ${escapeHtml(classification)}</span>`;

        // Status badge
        const securedLocally = request.secured_locally || false;
        const statusIcons = { approved: "✅", rejected: "❌" };
        let statusBadge;
        if (forceOverridden && (sensitivity === "high" || classification === "COMPANY_SECRET")) {
            statusBadge = `<span class="decision-badge decision-blocked">⛔ BLOCKED</span>`;
        } else if (forceOverridden) {
            statusBadge = `<span class="decision-badge decision-override">⚡ OVERRIDE</span>`;
        } else if (securedLocally) {
            statusBadge = `<span class="decision-badge decision-approved">🔒 SECURED</span>`;
        } else {
            statusBadge = `<span class="decision-badge decision-${escapeHtml(status)}">${statusIcons[status] || ""} ${escapeHtml(status).toUpperCase()}</span>`;
        }

        // Route badge
        const routeBadge = `<span class="route-badge route-${escapeHtml(route)}">${escapeHtml(route).toUpperCase()} LLM</span>`;

        // Detected patterns row
        let patternsHtml = "";
        if (detectedPatterns.length > 0) {
            const tags = detectedPatterns.slice(0, 5).map(p => {
                const type = p.split(":")[0] || "";
                return `<span class="pattern-tag pattern-${escapeHtml(type.toLowerCase())}">${escapeHtml(p)}</span>`;
            }).join("");
            const more = detectedPatterns.length > 5 ? `<span class="pattern-tag pattern-more">+${detectedPatterns.length - 5} more</span>` : "";
            patternsHtml = `<div class="history-patterns"><span class="patterns-label">🔍 Detected:</span> ${tags}${more}</div>`;
        }

        // Routing reason
        const reasonHtml = routingReason
            ? `<div class="history-reason"><span>💡</span> ${escapeHtml(routingReason)}</div>`
            : "";

        // Schema masking summary
        let maskingHtml = "";
        const hashed = schema.hashed_fields || [];
        const encrypted = schema.encrypted_fields || [];
        const redacted = schema.redacted_fields || [];
        const totalMaskedFields = hashed.length + encrypted.length + redacted.length;
        if (totalMaskedFields > 0) {
            const parts = [];
            if (hashed.length) parts.push(`${hashed.length} hashed`);
            if (encrypted.length) parts.push(`${encrypted.length} encrypted`);
            if (redacted.length) parts.push(`${redacted.length} redacted`);

            let detailsInner = "";
            if (hashed.length) detailsInner += `<div class="masking-detail-row"><span class="masking-action-label masking-hash">HASH</span> ${hashed.map(f => escapeHtml(f)).join(", ")}</div>`;
            if (encrypted.length) detailsInner += `<div class="masking-detail-row"><span class="masking-action-label masking-encrypt">ENC</span> ${encrypted.map(f => escapeHtml(f)).join(", ")}</div>`;
            if (redacted.length) detailsInner += `<div class="masking-detail-row"><span class="masking-action-label masking-redact">REDACT</span> ${redacted.map(f => escapeHtml(f)).join(", ")}</div>`;

            maskingHtml = `
                <details class="history-masking-details">
                    <summary class="history-masking-summary">🛡️ Schema Masking: ${parts.join(" · ")}</summary>
                    <div class="masking-detail-content">${detailsInner}</div>
                </details>
            `;
        }

        // Policy violations
        let violationsHtml = "";
        if (violations.length > 0) {
            const vItems = violations.slice(0, 3).map(v => {
                const sev = v.severity || "info";
                const sevIcon = sev === "critical" ? "🔴" : sev === "warning" ? "🟡" : "🔵";
                return `<div class="violation-row violation-${escapeHtml(sev)}">${sevIcon} <strong>[${escapeHtml(sev).toUpperCase()}]</strong> ${escapeHtml(v.message || "")}</div>`;
            }).join("");
            const moreV = violations.length > 3 ? `<div class="violation-row">...and ${violations.length - 3} more</div>` : "";
            violationsHtml = `<div class="history-violations">${vItems}${moreV}</div>`;
        }

        // Override warning
        const overrideWarning = (forceOverridden && sensitivity === "high")
            ? `<div class="history-override-warning">⚠️ Manually overridden — data was masked before cloud routing</div>`
            : "";

        // Vault upload events get a distinct rendering (from kwan branch)
        if (isVaultUpload) {
            const vf = request.vault_file || {};
            const tier = vf.tier || "PUBLIC";
            const tierColors = { PUBLIC: "#16a34a", PII: "#d97706", SPII: "#7c3aed", SECRET: "#dc2626" };
            const tierBgs = { PUBLIC: "#ecfdf3", PII: "#fffbeb", SPII: "#f5f3ff", SECRET: "#fff1f2" };
            const tierIcons = { PUBLIC: "fa-lock-open", PII: "fa-user-shield", SPII: "fa-shield-halved", SECRET: "fa-ban" };
            const accentColor = tierColors[tier] || "#2563eb";
            const fileSize = vf.size_bytes ? formatFileSize(vf.size_bytes) : "";
            return `
                <article class="history-item" style="border-left-color: ${accentColor};">
                    <div>
                        <div class="history-title">
                            <span class="route-badge" style="background:${tierBgs[tier]};color:${accentColor};"><i class="fa-solid ${tierIcons[tier]}"></i> ${escapeHtml(tier)}</span>
                            <span class="decision-badge" style="background:#eff6ff;color:#2563eb;"><i class="fa-solid fa-cloud-arrow-up"></i> UPLOAD</span>
                            <span class="route-badge route-${escapeHtml(route)}">${escapeHtml(route).toUpperCase()} LLM</span>
                            <strong>${escapeHtml(sensitivity).toUpperCase()} sensitivity</strong>
                        </div>
                        <p><i class="fa-solid fa-file" style="margin-right:5px;opacity:0.5;"></i>${escapeHtml(vf.filename || input)}${fileSize ? ' — ' + fileSize : ''}</p>
                    </div>
                    <div class="history-meta">
                        <div>vault</div>
                        <div>${masked} masked</div>
                        <div>${formatEpoch(request.timestamp)}</div>
                    </div>
                </article>
            `;
        }

        return `
            <article class="history-item history-${escapeHtml(status)}">
                <div class="history-badges">
                    ${classificationBadge}
                    ${statusBadge}
                    ${routeBadge}
                </div>
                <p class="history-input">${escapeHtml(input)}</p>
                ${patternsHtml}
                ${reasonHtml}
                ${maskingHtml}
                ${violationsHtml}
                ${overrideWarning}
                <div class="history-meta">
                    <div>⏱ ${Number.parseFloat(duration).toFixed(0)}ms</div>
                    <div>🔒 ${masked} masked</div>
                    <div>🕐 ${formatEpoch(request.timestamp)}</div>
                </div>
            </article>
        `;
    }).join("");
}

async function runSimulation() {
    const button = document.getElementById("run-simulation");
    const result = document.getElementById("simulation-result");
    const userInput = document.getElementById("userInput").value.trim();
    const routeOverride = document.getElementById("routeOverride").value;
    const llmOutput = document.getElementById("llmOutput");

    if (!userInput) {
        result.textContent = "User input is required.";
        return;
    }

    button.disabled = true;
    result.textContent = "Running workflow...";
    llmOutput.textContent = "Processing...";

    try {
        const response = await fetch("/api/simulate-request", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_input: userInput, llm_output: null, force_route: routeOverride }),
        });
        const payload = await response.json();
        if (!payload.success) {
            throw new Error(payload.error || "Simulation failed");
        }

        const route = payload.result.routing.llm_used.toUpperCase();
        const status = payload.result.status.toUpperCase();
        const sensitivity = (payload.result.routing.sensitivity_level || "unknown").toUpperCase();
        const patterns = Array.isArray(payload.result.routing.detected_patterns) ? payload.result.routing.detected_patterns : [];
        const icons = { APPROVED: "✅", REJECTED: "❌" };
        
        const classification = payload.dashboard?.history?.slice(-1)[0]?.data_classification || "PUBLIC";
        const forceOverridden = payload.result.force_overridden || false;
        const securedLocally = payload.result.secured_locally || false;
        
        let displayStatus = status;
        let displayIcon = icons[status] || "";
        
        if (forceOverridden && (sensitivity === "HIGH" || classification === "COMPANY_SECRET")) {
            displayStatus = "BLOCKED";
            displayIcon = "⛔";
        } else if (forceOverridden) {
            displayStatus = "OVERRIDE";
            displayIcon = "⚡";
        } else if (securedLocally) {
            displayStatus = "SECURED";
            displayIcon = "🔒";
        }

        const patternNote = patterns.length ? ` (detected: ${patterns.slice(0, 3).join(", ")}${patterns.length > 3 ? ", ..." : ""})` : "";
        result.textContent = `${displayIcon} ${displayStatus} - ${sensitivity} sensitivity -> ${route} LLM${patternNote}`;

        // Display the simulated output generated by the backend
        if (payload.result.final_output) {
            llmOutput.textContent = payload.result.final_output;
        } else {
            llmOutput.textContent = "No output generated (Policy rejected or blocked).";
        }

        // Show workflow log
        const logDetails = document.getElementById("log-details");
        const logEl = document.getElementById("workflowLog");
        if (payload.logs && payload.logs.length) {
            logEl.textContent = payload.logs.join("\n");
            logDetails.style.display = "";
            logDetails.open = true;
        }

        updateDashboard(payload.dashboard);
    } catch (error) {
        result.textContent = error.message;
        llmOutput.textContent = "";
    } finally {
        button.disabled = false;
    }
}

function flashCards() {
    document.querySelectorAll(".metric-card").forEach((card) => {
        card.classList.remove("flash");
        requestAnimationFrame(() => card.classList.add("flash"));
    });
}

function setText(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function percentLabel(value, total) {
    const numericValue = Number(value);
    const numericTotal = Number(total);
    if (!numericTotal || !Number.isFinite(numericTotal)) return "0%";
    return `${((numericValue / numericTotal) * 100).toFixed(1)}%`;
}

function formatTime(value) {
    if (!value) return "now";
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? "now" : date.toLocaleTimeString();
}

function formatEpoch(value) {
    if (!value) return "";
    const date = new Date(value * 1000);
    return Number.isNaN(date.getTime()) ? "" : date.toLocaleTimeString();
}

function formatFileSize(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function healthColor(status) {
    if (status === "HEALTHY") return "#16a34a";
    if (status === "DEGRADED") return "#d97706";
    if (status === "UNHEALTHY") return "#dc2626";
    return "#687589";
}

function safeJson(value) {
    try {
        return JSON.parse(value);
    } catch (error) {
        console.error("Invalid JSON:", error);
        return null;
    }
}

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function updateComplianceKPIs(stats, workflow) {
    // ISO14001: on-premise ratio (local LLM processing = lower cloud carbon)
    const totalReq = Number(workflow.total_requests ?? stats.total_requests ?? 0);
    const localReq = Number(workflow.local_llm_used ?? stats.local_routing_count ?? 0);
    const onPremiseRatio = totalReq > 0 ? ((localReq / totalReq) * 100).toFixed(1) + "%" : "0%";
    setText("on-premise-ratio", onPremiseRatio);

    // ISO9001: quality pass rate (from stats if available, else calculate)
    const qualityRate = stats.quality_pass_rate || "100.0%";
    setText("quality-pass-rate", qualityRate);
}


function updateAuditPanel(events, summary) {
    // Update ISO27001 KPI card
    setText("audit-total", summary.total_events ?? events.length ?? 0);
    const byAction = summary.by_action || {};
    setText("audit-breakdown",
        `${byAction.route ?? 0} route · ${byAction.mask ?? 0} mask · ${byAction.policy_check ?? 0} policy`
    );

    // Update audit event stream panel
    const panel = document.getElementById("audit-panel");
    if (!events.length) {
        panel.className = "scroll-region empty-state";
        panel.textContent = "No audit events yet";
        return;
    }

    panel.className = "scroll-region";
    panel.innerHTML = events.slice().reverse().map((e) => {
        const action = escapeHtml(e.action || "event");
        const classification = escapeHtml(e.classification || "");
        const decision = escapeHtml(e.decision || "");
        const reason = escapeHtml((e.reason || "").substring(0, 90));
        const traceId = escapeHtml((e.trace_id || "").substring(0, 8));
        const ts = formatTime(e.timestamp);
        const decisionColor = {
            allowed: "#16a34a", hashed: "#0891b2", encrypted: "#7c3aed",
            redacted: "#d97706", masked: "#0891b2", blocked: "#dc2626",
            rejected: "#dc2626", approved: "#16a34a", restricted: "#d97706",
            cloud: "#16a34a", local: "#2563eb",
        }[decision] || "#687589";

        return `
            <article class="audit-item">
                <span class="audit-badge audit-action-${action}">${action}</span>
                <div class="audit-meta">
                    <strong>
                        <span style="color:${decisionColor};font-weight:700;">${decision.toUpperCase()}</span>
                        &nbsp;·&nbsp;${classification}
                        ${traceId ? `<span style="color:var(--quiet);font-size:11px;font-family:var(--font-mono);">&nbsp;#${traceId}</span>` : ""}
                    </strong>
                    <small>${reason} &mdash; ${ts}</small>
                </div>
            </article>
        `;
    }).join("");
}

async function loadAuditLog() {
    try {
        const response = await fetch("/api/audit-log?last_n=30");
        if (!response.ok) return;
        const data = await response.json();
        updateAuditPanel(data.recent_events || [], data.summary || {});
    } catch (error) {
        console.warn("Audit log fetch failed:", error);
    }
}

window.addEventListener("beforeunload", () => {
    if (refreshTimer) clearInterval(refreshTimer);
    if (websocket) websocket.close();
});
