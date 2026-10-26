/** Recruitment & Training Analytics controller. Charts fail visibly, never silently blank. */
document.addEventListener("DOMContentLoaded", () => {
    const charts = { funnel: null, hiring: null, costs: null, training: null };
    let trainingData = null;
    let trainingView = "department";

    const number = value => Number.isFinite(Number(value)) ? Number(value) : null;
    const fmt = value => number(value) === null ? "N/A" : Number(value).toLocaleString("en-IN", { maximumFractionDigits: 1 });
    const safeText = value => value === null || value === undefined || String(value).trim() === "" ? "N/A" : String(value);

    function chartState(canvas, message) {
        if (!canvas) return;
        canvas.style.display = "none";
        let state = canvas.parentElement.querySelector(`[data-chart-state="${canvas.id}"]`);
        if (!state) {
            state = document.createElement("div");
            state.dataset.chartState = canvas.id;
            state.className = "text-muted text-center py-5";
            state.style.minHeight = "180px";
            state.style.display = "flex";
            state.style.alignItems = "center";
            state.style.justifyContent = "center";
            state.style.padding = "24px";
            canvas.parentElement.appendChild(state);
        }
        state.textContent = message || "No data available for this chart.";
    }

    function clearChartState(canvas) {
        if (!canvas) return;
        canvas.style.display = "block";
        const state = canvas.parentElement.querySelector(`[data-chart-state="${canvas.id}"]`);
        if (state) state.remove();
    }

    async function getJson(url) {
        const response = await fetch(url, { headers: { Accept: "application/json" } });
        if (!response.ok) throw new Error(`Request failed (${response.status})`);
        const body = await response.json();
        if (!body || body.success !== true) throw new Error(body?.error || "The server did not return valid data.");
        return body;
    }

    function setText(id, value) {
        const node = document.getElementById(id);
        if (node) node.textContent = value === null || value === undefined || value === "" ? "N/A" : value;
    }

    function markKpisUnavailable() {
        ["kpiActiveReqs", "kpiTotalReqs", "kpiPositionsRemaining", "kpiFillRate", "kpiActiveCandidates", "kpiAvgCost", "kpiTotalSpend", "kpiAvgTraining"].forEach(id => setText(id, "Unavailable"));
        setText("kpiTotalReqsSubtitle", "Could not load requisition totals.");
        setText("kpiTotalSpendSubtitle", "Could not load cost totals.");
    }

    async function loadKpis() {
        try {
            const data = (await getJson("/api/recruitment/kpis")).kpis;
            if (!data) throw new Error("KPI data is missing.");
            setText("kpiActiveReqs", fmt(data.active_requisitions));
            setText("kpiTotalReqs", fmt(data.total_requisitions));
            setText("kpiTotalReqsSubtitle", `of ${fmt(data.total_requisitions)} total requisitions`);
            setText("kpiPositionsRemaining", fmt(data.positions_remaining));
            setText("kpiFillRate", number(data.fill_rate_pct) === null ? "N/A" : `${fmt(data.fill_rate_pct)}%`);
            setText("kpiActiveCandidates", fmt(data.active_pipeline_candidates));
            setText("kpiAvgCost", safeText(data.avg_cost_per_hire));
            setText("kpiTotalSpend", safeText(data.total_recruitment_spend));
            setText("kpiTotalSpendSubtitle", `Total spend: ${safeText(data.total_recruitment_spend)}`);
            setText("kpiAvgTraining", number(data.avg_training_hours) === null ? "N/A" : `${fmt(data.avg_training_hours)} hrs`);
        } catch (error) {
            console.error("Error loading recruitment KPIs:", error);
            markKpisUnavailable();
        }
    }

    async function loadFunnel() {
        const canvas = document.getElementById("chartCandidateFunnel");
        try {
            const data = (await getJson("/api/recruitment/funnel")).funnel;
            const stages = (data?.stages || []).filter(stage => stage.stage && number(stage.count) !== null);
            if (!stages.length) return chartState(canvas, "No candidate pipeline data is available.");
            clearChartState(canvas);
            charts.funnel?.destroy();
            charts.funnel = new Chart(canvas, {
                type: "bar",
                data: {
                    labels: stages.map(stage => stage.stage),
                    datasets: [{ label: "Candidates reaching stage", data: stages.map(stage => Number(stage.count)), backgroundColor: stages.map(stage => stage.color || "#397ff5"), borderRadius: 6 }]
                },
                options: {
                    indexAxis: "y", responsive: true, maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: { callbacks: { label: context => {
                            const stage = stages[context.dataIndex];
                            return [`Candidates: ${fmt(stage.count)}`, `Share of pipeline: ${number(stage.pct) === null ? "N/A" : `${fmt(stage.pct)}%`}`];
                        } } }
                    },
                    scales: { x: { beginAtZero: true, title: { display: true, text: "Candidate count" }, grid: { color: "#F1F5F9" } }, y: { grid: { display: false } } }
                }
            });
        } catch (error) { console.error("Error loading candidate funnel:", error); chartState(canvas, "Could not load candidate funnel. Check the recruitment pipeline data or API."); }
    }

    async function loadHiring() {
        const canvas = document.getElementById("chartHiringByDepartment");
        try {
            const data = (await getJson("/api/recruitment/hiring-by-department")).hiring;
            const labels = data?.departments || [];
            if (!data?.available || !labels.length) return chartState(canvas, data?.message || "No department hiring data is available.");
            clearChartState(canvas);
            charts.hiring?.destroy();
            charts.hiring = new Chart(canvas, {
                type: "bar",
                data: {
                    labels,
                    datasets: [
                        { type: "bar", label: "Positions requested", data: data.positions_requested, backgroundColor: "#397ff5", borderRadius: 5, yAxisID: "y" },
                        { type: "bar", label: "Hires made", data: data.hires_made, backgroundColor: "#20b77a", borderRadius: 5, yAxisID: "y" },
                        { type: "bar", label: "Open positions", data: data.positions_remaining, backgroundColor: "#ffad32", borderRadius: 5, yAxisID: "y" },
                        { type: "line", label: "Fill rate (%)", data: data.fill_rate_pct, borderColor: "#e34b65", backgroundColor: "#e34b65", pointRadius: 3, pointHoverRadius: 5, tension: 0.25, yAxisID: "y1" }
                    ]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    interaction: { mode: "index", intersect: false },
                    plugins: { legend: { position: "bottom", labels: { boxWidth: 12, padding: 12, font: { size: 10 } } }, tooltip: { callbacks: { label: context => `${context.dataset.label}: ${context.dataset.yAxisID === "y1" ? `${fmt(context.raw)}%` : fmt(context.raw)}` } } },
                    scales: {
                        y: { beginAtZero: true, position: "left", title: { display: true, text: "Positions" }, grid: { color: "#F1F5F9" } },
                        y1: { beginAtZero: true, max: 100, position: "right", title: { display: true, text: "Fill rate (%)" }, grid: { drawOnChartArea: false }, ticks: { callback: value => `${value}%` } },
                        x: { grid: { display: false }, ticks: { maxRotation: 35, minRotation: 0 } }
                    }
                }
            });
        } catch (error) { console.error("Error loading department hiring performance:", error); chartState(canvas, "Could not load department hiring data. Check Job_Requisitions and the hiring API."); }
    }

    async function loadCosts() {
        const canvas = document.getElementById("chartRecruitmentCosts");
        try {
            const data = (await getJson("/api/recruitment/costs")).costs;
            const categories = data?.categories || {};
            const keys = ["recruiter", "advertising", "agency", "assessment"].filter(key => categories[key] && number(categories[key].numeric) !== null);
            if (!keys.length || keys.every(key => Number(categories[key].numeric) === 0)) return chartState(canvas, "No valid recruitment cost breakdown is available.");
            clearChartState(canvas);
            charts.costs?.destroy();
            const colors = ["#397ff5", "#00b4d8", "#8547f5", "#ffa726"];
            charts.costs = new Chart(canvas, {
                type: "doughnut",
                data: { labels: keys.map(key => categories[key].label || key), datasets: [{ data: keys.map(key => Number(categories[key].numeric)), backgroundColor: keys.map(key => colors[["recruiter", "advertising", "agency", "assessment"].indexOf(key)]), borderWidth: 2, borderColor: "#FFFFFF" }] },
                options: { responsive: true, maintainAspectRatio: false, cutout: "60%", plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, padding: 12, font: { size: 10 } } },
                    tooltip: { callbacks: { label: context => {
                        const total = context.dataset.data.reduce((sum, value) => sum + (Number(value) || 0), 0);
                        const share = total ? Number(context.raw) / total * 100 : 0;
                        return `${context.label}: ₹${fmt(context.raw)} (${share.toFixed(1)}%)`;
                    } } }
                } }
            });
        } catch (error) { console.error("Error loading recruitment costs:", error); chartState(canvas, "Could not load recruitment cost data. Check the cost workbook and API."); }
    }

    function renderTraining(view = trainingView) {
        const canvas = document.getElementById("chartTrainingComparison");
        if (!canvas || !trainingData) return;
        trainingView = view;
        const isDepartment = view === "department";
        const source = isDepartment ? trainingData.department_breakdown : trainingData.level_breakdown;
        const labels = isDepartment ? (source?.departments || []) : (source?.levels || []);
        const values = isDepartment ? (source?.average_hours || []) : (source?.average_hours || []);
        const valid = labels.map((label, index) => ({ label, value: number(values[index]) })).filter(item => item.label && item.value !== null);
        document.querySelectorAll("[data-training-view]").forEach(button => {
            const active = button.dataset.trainingView === view;
            button.classList.toggle("btn-primary", active);
            button.classList.toggle("btn-outline-primary", !active);
            button.setAttribute("aria-pressed", String(active));
        });
        setText("trainingChartDescription", isDepartment
            ? "Compare average training hours per employee across departments over the past 12 months."
            : "Compare average training hours per employee across job levels over the past 12 months.");
        if (!valid.length) return chartState(canvas, `No valid training-hour data is available ${isDepartment ? "by department" : "by job level"}.`);
        clearChartState(canvas);
        charts.training?.destroy();
        charts.training = new Chart(canvas, {
            type: "bar",
            data: { labels: valid.map(item => item.label), datasets: [{ label: "Average training hours per employee", data: valid.map(item => item.value), backgroundColor: isDepartment ? "#20b77a" : "#397ff5", borderRadius: 6 }] },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: { callbacks: { label: context => `Average: ${fmt(context.raw)} hours per employee` } } }, scales: {
                y: { beginAtZero: true, title: { display: true, text: "Average hours per employee" }, grid: { color: "#F1F5F9" } },
                x: { grid: { display: false }, ticks: { maxRotation: 35, minRotation: 0 } }
            } }
        });
    }

    async function loadTraining() {
        const canvas = document.getElementById("chartTrainingComparison");
        try {
            trainingData = (await getJson("/api/recruitment/training")).training;
            if (!trainingData) throw new Error("Training analytics data is missing.");
            renderTraining("department");
        } catch (error) { console.error("Error loading training analytics:", error); chartState(canvas, "Could not load training analytics. Check the Employees sheet and training API."); }
    }

    function escapeHtml(value) {
        return String(value ?? "N/A").replace(/[&<>"']/g, char => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char]));
    }

    async function loadRequisitions() {
        const tbody = document.getElementById("requisitionsTbody");
        if (!tbody) return;
        try {
            const data = await getJson("/api/recruitment/requisitions");
            const records = data.requisitions || [];
            setText("requisitionsTableBadge", `${fmt(data.total ?? records.length)} Requisitions`);
            if (!records.length) {
                tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">No requisition records are available.</td></tr>';
                return;
            }
            tbody.innerHTML = "";
            records.slice(0, 30).forEach(record => {
                const remaining = number(record.Positions_Remaining);
                const isFilled = remaining !== null && remaining <= 0;
                const tr = document.createElement("tr");
                tr.innerHTML = `
                    <td><code>${escapeHtml(record.Job_Requisition_ID)}</code></td>
                    <td>${escapeHtml(record.Department)}</td>
                    <td>${escapeHtml(record.Job_Role)}</td>
                    <td>${record.Requisition_Open_Date ? escapeHtml(String(record.Requisition_Open_Date).slice(0, 10)) : "N/A"}</td>
                    <td class="text-center">${fmt(record.Positions_Requested)}</td>
                    <td class="text-center">${fmt(record.Hires_Made)}</td>
                    <td class="text-center"><b>${fmt(record.Positions_Remaining)}</b></td>
                    <td class="text-center">${isFilled ? '<span class="badge-success">Filled</span>' : remaining === null ? '<span class="badge-neutral">Unknown</span>' : '<span class="badge-warning">Open</span>'}</td>`;
                tbody.appendChild(tr);
            });
        } catch (error) {
            console.error("Error loading requisitions:", error);
            tbody.innerHTML = '<tr><td colspan="8" class="text-center py-4 text-muted">Could not load requisitions. Check the requisitions API.</td></tr>';
        }
    }

    document.querySelectorAll("[data-training-view]").forEach(button => button.addEventListener("click", () => renderTraining(button.dataset.trainingView)));

    loadKpis();
    loadFunnel();
    loadHiring();
    loadCosts();
    loadTraining();
    loadRequisitions();
});
