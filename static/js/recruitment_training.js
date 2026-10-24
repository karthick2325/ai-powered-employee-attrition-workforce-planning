/**
 * Workforce Intelligence — Recruitment & Training Analytics Controller
 */

document.addEventListener("DOMContentLoaded", function () {
    let funnelChart = null;
    let costsChart = null;
    let trainingChart = null;

    init();

    function init() {
        loadKpis();
        loadFunnel();
        loadCosts();
        loadTraining();
        loadRequisitions();
    }

    function loadKpis() {
        fetch("/api/recruitment/kpis")
            .then(res => res.json())
            .then(res => {
                if (res.success && res.kpis) {
                    const d = res.kpis;
                    if (document.getElementById("kpiActiveReqs")) {
                        document.getElementById("kpiActiveReqs").textContent = d.active_requisitions.toLocaleString();
                    }
                    if (document.getElementById("kpiTotalReqs")) {
                        document.getElementById("kpiTotalReqs").textContent = d.total_requisitions.toLocaleString();
                    }
                    if (document.getElementById("kpiPositionsRemaining")) {
                        document.getElementById("kpiPositionsRemaining").textContent = d.positions_remaining.toLocaleString();
                    }
                    if (document.getElementById("kpiFillRate")) {
                        document.getElementById("kpiFillRate").textContent = `${d.fill_rate_pct}%`;
                    }
                    if (document.getElementById("kpiActiveCandidates")) {
                        document.getElementById("kpiActiveCandidates").textContent = d.active_pipeline_candidates.toLocaleString();
                    }
                    if (document.getElementById("kpiAvgCost")) {
                        document.getElementById("kpiAvgCost").textContent = d.avg_cost_per_hire;
                    }
                    if (document.getElementById("kpiTotalSpend")) {
                        document.getElementById("kpiTotalSpend").textContent = d.total_recruitment_spend;
                    }
                    if (document.getElementById("kpiTotalSpendSubtitle")) {
                        document.getElementById("kpiTotalSpendSubtitle").textContent = `Total spend: ${d.total_recruitment_spend}`;
                    }
                    if (document.getElementById("kpiAvgTraining")) {
                        document.getElementById("kpiAvgTraining").textContent = `${d.avg_training_hours} hrs`;
                    }
                }
            })
            .catch(err => console.error("Error loading recruitment KPIs:", err));
    }

    function loadFunnel() {
        fetch("/api/recruitment/funnel")
            .then(res => res.json())
            .then(res => {
                if (res.success && res.funnel) {
                    renderFunnelChart(res.funnel);
                }
            })
            .catch(err => console.error("Error loading funnel:", err));
    }

    function renderFunnelChart(data) {
        const ctx = document.getElementById("chartCandidateFunnel");
        if (!ctx) return;

        const labels = data.stages.map(s => `${s.stage} (${s.count.toLocaleString()})`);
        const counts = data.stages.map(s => s.count);
        const colors = data.stages.map(s => s.color);

        if (funnelChart) funnelChart.destroy();

        funnelChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: labels,
                datasets: [{
                    label: "Candidates",
                    data: counts,
                    backgroundColor: colors,
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: "y",
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return `Candidates: ${ctx.raw.toLocaleString()}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: "#F1F5F9" },
                        title: { display: true, text: "Candidate Volume", font: { size: 11 } }
                    },
                    y: {
                        grid: { display: false }
                    }
                }
            }
        });
    }

    function loadCosts() {
        fetch("/api/recruitment/costs")
            .then(res => res.json())
            .then(res => {
                if (res.success && res.costs) {
                    renderCostsChart(res.costs);
                }
            })
            .catch(err => console.error("Error loading costs:", err));
    }

    function renderCostsChart(data) {
        const ctx = document.getElementById("chartRecruitmentCosts");
        if (!ctx) return;

        const cats = data.categories;
        const labels = [cats.recruiter.label, cats.advertising.label, cats.agency.label, cats.assessment.label];
        const amounts = [cats.recruiter.numeric, cats.advertising.numeric, cats.agency.numeric, cats.assessment.numeric];
        const colors = ["#0D63F3", "#00B4D8", "#8547F5", "#FFA726"];

        if (costsChart) costsChart.destroy();

        costsChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: labels,
                datasets: [{
                    data: amounts,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: "#FFFFFF"
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "right", labels: { boxWidth: 12, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                const val = ctx.raw;
                                return `${ctx.label}: ₹ ${val.toLocaleString()}`;
                            }
                        }
                    }
                },
                cutout: "60%"
            }
        });
    }

    function loadTraining() {
        fetch("/api/recruitment/training")
            .then(res => res.json())
            .then(res => {
                if (res.success && res.training) {
                    renderTrainingChart(res.training);
                }
            })
            .catch(err => console.error("Error loading training:", err));
    }

    function renderTrainingChart(data) {
        const ctx = document.getElementById("chartDepartmentTraining");
        if (!ctx) return;

        const depts = data.department_breakdown.departments;
        const avgHours = data.department_breakdown.average_hours;

        if (trainingChart) trainingChart.destroy();

        trainingChart = new Chart(ctx, {
            type: "bar",
            data: {
                labels: depts,
                datasets: [{
                    label: "Avg Training Hours (Past 12M)",
                    data: avgHours,
                    backgroundColor: "#22B573",
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 12, font: { size: 11 } } }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        title: { display: true, text: "Hours per Employee", font: { size: 11 } },
                        grid: { color: "#F1F5F9" }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        });

        // Job Level training chart
        const ctxLevel = document.getElementById("chartLevelTraining");
        if (ctxLevel && data.level_breakdown) {
            const levels = data.level_breakdown.levels;
            const avgLevelHours = data.level_breakdown.average_hours;
            if (window.levelTrainingChart) window.levelTrainingChart.destroy();
            window.levelTrainingChart = new Chart(ctxLevel, {
                type: "bar",
                data: {
                    labels: levels,
                    datasets: [{
                        label: "Avg Hours",
                        data: avgLevelHours,
                        backgroundColor: "#0D63F3",
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: { display: true, text: "Hours per Employee", font: { size: 11 } },
                            grid: { color: "#F1F5F9" }
                        },
                        x: { grid: { display: false } }
                    }
                }
            });
        }
    }

    function loadRequisitions() {
        const tbody = document.getElementById("requisitionsTbody");
        fetch("/api/recruitment/requisitions")
            .then(res => res.json())
            .then(res => {
                if (res.success && res.requisitions) {
                    tbody.innerHTML = "";
                    res.requisitions.slice(0, 30).forEach(r => {
                        const tr = document.createElement("tr");
                        const statusBadge = r.Positions_Remaining === 0
                            ? '<span class="badge-success">Filled</span>'
                            : '<span class="badge-warning">Open</span>';

                        tr.innerHTML = `
                            <td><code>${r.Job_Requisition_ID}</code></td>
                            <td>${r.Department}</td>
                            <td>${r.Job_Role}</td>
                            <td>${r.Requisition_Open_Date ? String(r.Requisition_Open_Date).slice(0, 10) : '-'}</td>
                            <td class="text-center">${r.Positions_Requested}</td>
                            <td class="text-center">${r.Hires_Made}</td>
                            <td class="text-center"><b>${r.Positions_Remaining}</b></td>
                            <td class="text-center">${statusBadge}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            })
            .catch(err => console.error("Error loading requisitions:", err));
    }
});
