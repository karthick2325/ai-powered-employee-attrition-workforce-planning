/**
 * AttritionSense Technologies — Data Quality & Governance Audit
 * Uses verified API results only. Does not invent fallback KPI values.
 */

"use strict";

let domainChartInstance = null;
let categoryChartInstance = null;

document.addEventListener("DOMContentLoaded", () => {
    loadSummary();
    loadChecks();
    loadSheets();
});

const numberFormat = new Intl.NumberFormat("en-IN");

function hasNumericValue(value) {
    return value !== null && value !== undefined && value !== "" && Number.isFinite(Number(value));
}

function formatNumber(value) {
    if (!hasNumericValue(value)) return "—";
    return numberFormat.format(Number(value));
}

function formatPercent(value, digits = 1) {
    if (!hasNumericValue(value)) return "—";
    return `${Number(value).toFixed(digits)}%`;
}

function getElement(id) {
    return document.getElementById(id);
}

function setText(id, value) {
    const el = getElement(id);
    if (el) el.textContent = value === null || value === undefined || value === "" ? "—" : String(value);
}

function setKpiState(id, value, state) {
    const el = getElement(id);
    if (!el) return;
    el.textContent = value;
    el.classList.remove("text-success", "text-warning", "text-danger");
    if (state === "success") el.classList.add("text-success");
    if (state === "warning") el.classList.add("text-warning");
    if (state === "danger") el.classList.add("text-danger");
}

async function fetchJson(url) {
    const response = await fetch(url, {
        headers: { "Accept": "application/json" }
    });
    if (!response.ok) {
        let message = `Request failed (${response.status})`;
        try {
            const body = await response.json();
            if (body && body.error) message = body.error;
        } catch (_) {}
        throw new Error(message);
    }
    return response.json();
}

async function loadSummary() {
    const status = getElement("dqAuditStatus");
    try {
        const response = await fetchJson("/api/data-quality/summary");
        if (!response || response.success !== true || !response.summary) {
            throw new Error(response?.error || "The API did not return a valid audit summary.");
        }

        const s = response.summary;
        const total = s.total_records_audited ?? s.total_records_master;
        const unique = s.unique_employees;
        const completeness = s.data_completeness_pct;
        const duplicates = s.duplicate_employee_ids;
        const missing = s.missing_required_values;
        const review = s.records_requiring_review;

        setText("dqTotalAudited", formatNumber(total));
        setText("dqTotalRecords", formatNumber(s.total_records_master ?? total));
        setText("dqUniqueEmployees", formatNumber(unique));
        setText("dqUniqueBadge", hasNumericValue(unique) && hasNumericValue(total)
            ? `${Number(total) ? (Number(unique) / Number(total) * 100).toFixed(1) : "0.0"}% unique`
            : "Uniqueness not reported");

        setKpiState("dqDataCompleteness", formatPercent(completeness), hasNumericValue(completeness) ? (Number(completeness) >= 98 ? "success" : "warning") : null);
        setText("dqValidationStatus", s.validation_status || "Not classified");
        setText("dqOverallScore", formatPercent(s.overall_quality_score));
        setText("dqPassedChecks", `${formatNumber(s.passed_checks)} / ${formatNumber(s.total_checks)}`);
        setText("dqFailedChecks", formatNumber(s.failed_checks));
        setText("dqEligibleCount", formatNumber(s.eligible_outcomes_count));

        setKpiState("dqDuplicateIds", formatNumber(duplicates), hasNumericValue(duplicates) ? (Number(duplicates) === 0 ? "success" : "danger") : null);
        setText("dqDuplicateHint", hasNumericValue(duplicates)
            ? (Number(duplicates) === 0 ? "No duplicate IDs detected" : "Duplicate IDs need investigation")
            : "Duplicate-ID audit result not reported");

        setKpiState("dqMissingValues", formatNumber(missing), hasNumericValue(missing) ? (Number(missing) === 0 ? "success" : "warning") : null);
        setText("dqMissingHint", hasNumericValue(missing)
            ? (Number(missing) === 0 ? "No missing required values detected" : "Missing values need review")
            : "Missing-value audit result not reported");

        setKpiState("dqRecordsReview", formatNumber(review), hasNumericValue(review) ? (Number(review) === 0 ? "success" : "warning") : null);
        setText("dqReviewHint", hasNumericValue(review)
            ? (Number(review) === 0 ? "No records currently flagged" : "Records flagged for manual review")
            : "Review count not reported");

        setText("dqReconcileMaster", formatNumber(s.total_records_master ?? total));
        setText("dqReconcileNotice", formatNumber(s.notice_cohort_excluded ?? s.notice_period_count));
        setText("dqReconcileEligible", formatNumber(s.eligible_outcomes_count));

        if (status) {
            status.textContent = "Audit metrics loaded from the data-quality API.";
            status.classList.remove("is-error");
            status.classList.add("is-success");
        }

        renderDomainCompletenessChart(Array.isArray(s.domain_completeness) ? s.domain_completeness : []);
        renderChecksCategoryChart(Array.isArray(s.checks_by_category) ? s.checks_by_category : []);
    } catch (error) {
        console.error("Unable to load data quality summary:", error);
        if (status) {
            status.textContent = `Audit summary unavailable: ${error.message}. KPI values are not being guessed.`;
            status.classList.add("is-error");
            status.classList.remove("is-success");
        }
        showChartMessage("chartDomainCompleteness", "Completeness data is unavailable.");
        showChartMessage("chartChecksCategory", "Audit category data is unavailable.");
    }
}

function showChartMessage(canvasId, message) {
    const canvas = getElement(canvasId);
    if (!canvas) return;
    const container = canvas.closest(".chart-container");
    if (!container) return;
    canvas.style.display = "none";
    let note = container.querySelector(`[data-chart-message="${canvasId}"]`);
    if (!note) {
        note = document.createElement("div");
        note.dataset.chartMessage = canvasId;
        note.className = "dq-chart-empty";
        container.appendChild(note);
    }
    note.textContent = message;
}

function clearChartMessage(canvasId) {
    const canvas = getElement(canvasId);
    if (!canvas) return;
    canvas.style.display = "";
    const container = canvas.closest(".chart-container");
    const note = container?.querySelector(`[data-chart-message="${canvasId}"]`);
    if (note) note.remove();
}

function renderDomainCompletenessChart(domains) {
    const canvas = getElement("chartDomainCompleteness");
    if (!canvas || typeof Chart === "undefined") return;
    if (domainChartInstance) domainChartInstance.destroy();

    const valid = domains.filter(d => d && d.domain != null && Number.isFinite(Number(d.completeness_pct)));
    if (!valid.length) {
        showChartMessage("chartDomainCompleteness", "No verified completeness-by-domain data was returned.");
        return;
    }

    clearChartMessage("chartDomainCompleteness");
    domainChartInstance = new Chart(canvas.getContext("2d"), {
        type: "bar",
        data: {
            labels: valid.map(d => String(d.domain)),
            datasets: [{
                label: "Completeness (%)",
                data: valid.map(d => Number(d.completeness_pct)),
                backgroundColor: "#0D63F3",
                borderRadius: 5,
                maxBarThickness: 30
            }]
        },
        options: {
            indexAxis: "y",
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: context => `Completeness: ${context.raw}%` } }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: value => `${value}%`, font: { size: 10 } },
                    grid: { color: "#F1F5F9" }
                },
                y: {
                    ticks: { font: { size: 11, weight: "bold" } },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderChecksCategoryChart(categoryData) {
    const canvas = getElement("chartChecksCategory");
    if (!canvas || typeof Chart === "undefined") return;
    if (categoryChartInstance) categoryChartInstance.destroy();

    const valid = categoryData.filter(item =>
        item && item.category != null && Number.isFinite(Number(item.count)) && Number(item.count) >= 0
    );
    if (!valid.length || valid.every(item => Number(item.count) === 0)) {
        showChartMessage("chartChecksCategory", "No verified audit-category counts were returned.");
        return;
    }

    clearChartMessage("chartChecksCategory");
    categoryChartInstance = new Chart(canvas.getContext("2d"), {
        type: "doughnut",
        data: {
            labels: valid.map(item => String(item.category)),
            datasets: [{
                data: valid.map(item => Number(item.count)),
                backgroundColor: ["#0D63F3", "#10B981", "#8547F5", "#FFA726", "#06B6D4", "#F04452"],
                borderWidth: 2,
                borderColor: "#FFFFFF"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: "right",
                    labels: { boxWidth: 12, padding: 12, font: { size: 11 } }
                },
                tooltip: {
                    callbacks: {
                        label: context => ` ${context.label}: ${context.raw} checks`
                    }
                }
            },
            cutout: "60%"
        }
    });
}

async function loadChecks() {
    const tbody = getElement("checksTbody");
    if (!tbody) return;
    try {
        const response = await fetchJson("/api/data-quality/checks");
        if (response.success !== true || !Array.isArray(response.checks)) {
            throw new Error(response.error || "Invalid audit-check response.");
        }
        tbody.replaceChildren();
        if (!response.checks.length) {
            appendEmptyRow(tbody, 8, "No audit checks were returned.");
            return;
        }

        response.checks.forEach(check => {
            const row = document.createElement("tr");
            addCell(row, check.check_id ?? "—", "code");
            addCell(row, check.category ?? "—");
            addCell(row, check.check_type ?? "—", "strong");
            addStatusCell(row, check.status);
            addCell(row, check.severity ?? "—");
            addCell(row, check.result ?? "—", "strong");
            addCell(row, check.details ?? "—");
            addCell(row, check.remediation ?? "—");
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error("Unable to load data quality checks:", error);
        appendEmptyRow(tbody, 8, `Could not load audit checks: ${error.message}`);
    }
}

async function loadSheets() {
    const tbody = getElement("sheetsTbody");
    if (!tbody) return;
    try {
        const response = await fetchJson("/api/data-quality/sheets");
        if (response.success !== true || !Array.isArray(response.sheets)) {
            throw new Error(response.error || "Invalid worksheet-inventory response.");
        }
        tbody.replaceChildren();
        setText("sheetCountBadge", `${response.sheets.length} worksheets loaded`);
        if (!response.sheets.length) {
            appendEmptyRow(tbody, 5, "No worksheet inventory was returned.");
            return;
        }

        response.sheets.forEach(sheet => {
            const row = document.createElement("tr");
            addCell(row, sheet.sheet_name ?? "—", "strong");
            addCell(row, sheet.description ?? "—");
            addCell(row, formatNumber(sheet.total_records));
            addCell(row, formatNumber(sheet.total_columns));
            const statusCell = document.createElement("td");
            statusCell.className = "text-center";
            const badge = document.createElement("span");
            const isValid = sheet.integrity_status === "Valid" || sheet.integrity_status === "PASS";
            badge.className = isValid ? "badge-success" : "badge-neutral";
            badge.textContent = sheet.integrity_status || "Not reported";
            statusCell.appendChild(badge);
            row.appendChild(statusCell);
            tbody.appendChild(row);
        });
    } catch (error) {
        console.error("Unable to load worksheet inventory:", error);
        appendEmptyRow(tbody, 5, `Could not load worksheet inventory: ${error.message}`);
    }
}

function addCell(row, value, style = "") {
    const cell = document.createElement("td");
    if (style === "code") {
        const code = document.createElement("code");
        code.textContent = String(value);
        cell.appendChild(code);
    } else if (style === "strong") {
        const strong = document.createElement("strong");
        strong.textContent = String(value);
        cell.appendChild(strong);
    } else {
        cell.textContent = String(value);
    }
    row.appendChild(cell);
    return cell;
}

function addStatusCell(row, status) {
    const cell = document.createElement("td");
    cell.className = "text-center";
    const normalized = String(status || "").toUpperCase();
    const config = {
        PASS: ["badge-success", "bi-check-circle", "PASS"],
        INFO: ["badge-neutral", "bi-info-circle", "INFO"],
        WARNING: ["badge-warning", "bi-exclamation-triangle", "WARNING"],
        FAIL: ["badge-danger", "bi-x-circle", "FAIL"]
    };
    const item = config[normalized] || ["badge-neutral", "bi-question-circle", normalized || "NOT REPORTED"];
    const badge = document.createElement("span");
    badge.className = item[0];
    const icon = document.createElement("i");
    icon.className = `bi ${item[1]}`;
    badge.append(icon, document.createTextNode(` ${item[2]}`));
    cell.appendChild(badge);
    row.appendChild(cell);
}

function appendEmptyRow(tbody, colspan, message) {
    tbody.replaceChildren();
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = colspan;
    cell.className = "text-center py-4 text-muted";
    cell.textContent = message;
    row.appendChild(cell);
    tbody.appendChild(row);
}
