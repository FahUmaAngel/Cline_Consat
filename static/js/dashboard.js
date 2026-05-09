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
    setText("decision-mix", `${workflow.approved || 0} approved / ${workflow.blocked || 0} blocked / ${workflow.rejected || 0} rejected`);
    setText("masked-count", `${stats.total_masking_items || 0} masked items`);
    setText("masked-total", stats.total_masking_items || 0);
    setText("alert-count", `${stats.total_alerts || alerts.length || 0} active alerts`);
    setText("critical-count", `${stats.critical_alerts || 0} critical`);
    setText("critical-total", stats.critical_alerts || 0);
    setText("local-percent", percentLabel(workflow.local_llm_used ?? stats.local_routing_count ?? 0, workflow.total_requests ?? stats.total_requests ?? 0));
    setText("cloud-percent", percentLabel(workflow.cloud_llm_used ?? stats.cloud_routing_count ?? 0, workflow.total_requests ?? stats.total_requests ?? 0));
    setText("last-updated", `Updated ${formatTime(data.timestamp)}`);

    updateCharts(stats, workflow);
    updateAlerts(alerts);
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

function updateAlerts(alerts) {
    const panel = document.getElementById("alerts-panel");
    if (!alerts.length) {
        panel.className = "scroll-region empty-state";
        panel.textContent = "No alerts";
        return;
    }

    panel.className = "scroll-region";
    panel.innerHTML = alerts.slice().reverse().map((alert) => {
        const severity = escapeHtml(alert.severity || "info");
        return `
            <article class="alert-item alert-${severity}">
                <strong>${severity.toUpperCase()}</strong>
                <p>${escapeHtml(alert.message || "Alert")}</p>
                <small>${formatTime(alert.timestamp)} | ${escapeHtml(alert.metric_type || "metric")}</small>
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
    panel.className = "scroll-region";
    panel.innerHTML = history.slice().reverse().map((request) => {
        const route = request.route || request.routing?.llm_used || "unknown";
        const status = request.status || "unknown";
        const sensitivity = request.sensitivity || request.routing?.sensitivity_level || "unknown";
        const duration = request.processing_time_ms || request.metrics?.processing_time_ms || "0";
        const masked = request.masked_items_count ?? request.metrics?.masked_items_count ?? 0;
        const input = request.input_preview || request.user_input || request.routing?.reason || "Workflow request";
        const forceOverridden = request.force_overridden || false;
        
        const overrideBadge = forceOverridden
            ? `<span class="decision-badge" style="background:#f59e0b;color:#fff;">⚡ OVERRIDE</span>`
            : `<span class="decision-badge decision-${escapeHtml(status)}">${escapeHtml(status).toUpperCase()}</span>`;
        
        const overrideWarning = (forceOverridden && sensitivity === "high")
            ? `<p style="color:#f59e0b;font-size:11px;margin:2px 0 0 0;">⚠️ Manually overridden — data was masked before cloud routing</p>`
            : "";
        
        return `
            <article class="history-item history-${escapeHtml(status)}">
                <div>
                    <div class="history-title">
                        <span class="route-badge route-${escapeHtml(route)}">${escapeHtml(route).toUpperCase()} LLM</span>
                        ${overrideBadge}
                        <strong>${escapeHtml(sensitivity).toUpperCase()} sensitivity</strong>
                    </div>
                    <p>${escapeHtml(input)}</p>
                    ${overrideWarning}
                </div>
                <div class="history-meta">
                    <div>${Number.parseFloat(duration).toFixed(2)}ms</div>
                    <div>${masked} masked</div>
                    <div>${formatEpoch(request.timestamp)}</div>
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
        const icons = { APPROVED: "✅", BLOCKED: "🔒", REJECTED: "❌" };
        result.textContent = `${icons[status] || ""} ${status} — ${sensitivity} sensitivity → ${route} LLM`;

        const patternNote = patterns.length ? ` (detected: ${patterns.slice(0, 3).join(", ")}${patterns.length > 3 ? ", ..." : ""})` : "";
        // Override the status line with a debug hint about what was detected.
        result.textContent = `${icons[status] || ""} ${status} - ${sensitivity} sensitivity -> ${route} LLM${patternNote}`;

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
