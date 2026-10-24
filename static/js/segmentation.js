/**
 * Workforce Intelligence — Segmentation & Talent Analytics Controller
 * Handles 5-algorithm unsupervised benchmark rendering, 2D PCA projection scatter,
 * dynamic archetype cards, profile table, role pressure, anomalies, and paginated employee assignments.
 */

document.addEventListener("DOMContentLoaded", function () {
    let currentK = 5;
    let segEmpPage = 1;
    let segEmpPageSize = 10;
    let segEmpSearch = "";
    let segEmpFilterSegment = -1;

    let chartPcaInstance = null;
    let chartOptInstance = null;

    init();

    function init() {
        setupEventListeners();
        loadAllData(currentK);
    }

    function setupEventListeners() {
        // K Selector Buttons
        const kBtns = document.querySelectorAll(".k-btn");
        kBtns.forEach(btn => {
            btn.addEventListener("click", function () {
                const selectedK = parseInt(this.getAttribute("data-k"), 10);
                if (selectedK !== currentK) {
                    kBtns.forEach(b => b.classList.remove("active"));
                    this.classList.add("active");
                    currentK = selectedK;
                    handleKChange(selectedK);
                }
            });
        });

        // 5-Model Benchmark Button
        const btnBenchmark = document.getElementById("btnBenchmarkFiveModels");
        if (btnBenchmark) {
            btnBenchmark.addEventListener("click", function () {
                loadBenchmarkData(true);
            });
        }

        // Role Pressure Filter
        const roleTierFilter = document.getElementById("roleTierFilter");
        if (roleTierFilter) {
            roleTierFilter.addEventListener("change", loadRolePressureData);
        }

        // Employee Cluster Assignments Table controls
        const segFilterSelect = document.getElementById("segFilterSegment");
        if (segFilterSelect) {
            segFilterSelect.addEventListener("change", function () {
                segEmpFilterSegment = parseInt(this.value, 10);
                segEmpPage = 1;
                loadSegmentEmployees();
            });
        }

        const segSearchInput = document.getElementById("segSearchEmployee");
        if (segSearchInput) {
            let debounceTimer;
            segSearchInput.addEventListener("input", function () {
                clearTimeout(debounceTimer);
                debounceTimer = setTimeout(() => {
                    segEmpSearch = this.value.trim();
                    segEmpPage = 1;
                    loadSegmentEmployees();
                }, 300);
            });
        }

        const btnPrevSegEmp = document.getElementById("btnPrevSegEmp");
        const btnNextSegEmp = document.getElementById("btnNextSegEmp");
        if (btnPrevSegEmp) {
            btnPrevSegEmp.addEventListener("click", function () {
                if (segEmpPage > 1) {
                    segEmpPage--;
                    loadSegmentEmployees();
                }
            });
        }
        if (btnNextSegEmp) {
            btnNextSegEmp.addEventListener("click", function () {
                segEmpPage++;
                loadSegmentEmployees();
            });
        }
    }

    function loadAllData(k) {
        loadOverviewKpis(k);
        loadBenchmarkData(false);
        loadPcaScatter();
        loadOptimizationCurves();
        loadSegmentProfiles(k);
        loadSegmentEmployees();
        loadRolePressureData();
        loadAnomaliesData();
    }

    function handleKChange(k) {
        loadOverviewKpis(k);
        loadSegmentProfiles(k);
        loadOptimizationCurves();
        loadPcaScatter();
        loadSegmentEmployees();
    }

    // -------------------------------------------------------------
    // 1. Executive KPIs
    // -------------------------------------------------------------
    function loadOverviewKpis(k) {
        fetch(`/api/segmentation/overview?k=${k}`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    const d = res.data;
                    document.getElementById("kpiTotalClustered").textContent = (d.total_clustered_employees || 47972).toLocaleString();
                    document.getElementById("kpiSegmentCountBadge").textContent = `K = ${d.current_k || k} Segments`;
                    document.getElementById("kpiBestModel").textContent = d.best_validated_algorithm || "K-Means";
                    document.getElementById("kpiBestModelMetric").textContent = `Silhouette: ${d.silhouette_score || '0.0602'}`;
                    document.getElementById("kpiTotalAnomalies").textContent = (d.total_anomalies_flagged || 960).toLocaleString();
                    
                    if (d.top_pressure_role) {
                        document.getElementById("kpiTopPressureRatio").textContent = d.top_pressure_role.pressure_ratio.toFixed(3);
                        document.getElementById("kpiTopPressureRole").textContent = `Top: ${d.top_pressure_role.job_role}`;
                    }
                }
            })
            .catch(err => console.error("Error loading KPIs:", err));
    }

    // -------------------------------------------------------------
    // 2. 5-Algorithm Unsupervised Benchmark (Phase 4 Deliverable)
    // -------------------------------------------------------------
    function loadBenchmarkData(forceRerun) {
        const tbody = document.getElementById("benchmarkTbody");
        if (!tbody) return;
        if (forceRerun) {
            tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-muted"><div class="spinner-border spinner-border-sm text-primary"></div> Running 5-algorithm benchmark...</td></tr>`;
        }

        fetch(`/api/segmentation/benchmark?k=${currentK}`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    const b = res.data;
                    document.getElementById("benchmarkTimestampBadge").textContent = `Evaluated: ${b.dataset_records.toLocaleString()} Active Records`;
                    
                    // Rationale banner
                    const alertEl = document.getElementById("selectionRationaleText");
                    if (alertEl) {
                        alertEl.innerHTML = `<strong>Recommended Model: ${b.selected_algorithm}</strong> &mdash; ${b.selection_rationale}`;
                    }

                    // Render Table
                    tbody.innerHTML = "";
                    b.candidates.forEach(c => {
                        const tr = document.createElement("tr");
                        const isWinner = c.name === b.selected_algorithm;
                        if (isWinner) {
                            tr.style.backgroundColor = "#F0FDF4";
                            tr.style.fontWeight = "600";
                        }

                        const statusBadge = c.is_valid
                            ? `<span class="badge-success"><i class="bi bi-check-circle"></i> Valid (${c.composite_score})</span>`
                            : `<span class="badge-danger" title="${c.rejection_reason || ''}"><i class="bi bi-x-circle"></i> Rejected</span>`;

                        tr.innerHTML = `
                            <td>
                                <strong>${c.name}</strong> ${isWinner ? '<span class="badge-success" style="font-size:10px; margin-left:4px;">Winner</span>' : ''}
                            </td>
                            <td><span style="font-size:11px; color:#64748B;">${c.family}</span></td>
                            <td class="text-center"><b>${c.clusters_found}</b></td>
                            <td class="text-center">${c.noise_count} (${c.noise_percentage}%)</td>
                            <td class="text-center">${c.coverage_percentage}%</td>
                            <td class="text-center">${c.silhouette_display}</td>
                            <td class="text-center">${c.davies_bouldin_display}</td>
                            <td class="text-center">${c.calinski_harabasz_display}</td>
                            <td class="text-center">${c.size_imbalance_ratio ? c.size_imbalance_ratio + 'x' : 'N/A'}</td>
                            <td class="text-center">${c.runtime_ms} ms</td>
                            <td class="text-center">${statusBadge}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            })
            .catch(err => {
                console.error("Error loading benchmark:", err);
                tbody.innerHTML = `<tr><td colspan="11" class="text-center py-4 text-danger">Failed to load benchmark results.</td></tr>`;
            });
    }

    // -------------------------------------------------------------
    // 3. 2D PCA Dimensionality Projection Scatter Chart
    // -------------------------------------------------------------
    function loadPcaScatter() {
        fetch(`/api/segmentation/pca`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    const pca = res.data;
                    document.getElementById("pcaVarianceBadge").textContent = `PC1: ${pca.pc1_explained_variance_pct}% | PC2: ${pca.pc2_explained_variance_pct}% | Total: ${pca.total_explained_variance_pct}%`;
                    renderPcaChart(pca.points);
                }
            })
            .catch(err => console.error("Error loading PCA:", err));
    }

    function renderPcaChart(points) {
        const ctx = document.getElementById("chartPcaScatter");
        if (!ctx) return;

        const colors = ["#0D63F3", "#22B573", "#FFA726", "#F04452", "#8547F5", "#00B4D8", "#EC4899"];

        // Group points by segment_id
        const groups = {};
        points.forEach(p => {
            const sid = p.segment_id;
            if (!groups[sid]) {
                groups[sid] = [];
            }
            groups[sid].push({ x: p.x, y: p.y, label: `${p.name} (${p.role})` });
        });

        const datasets = Object.keys(groups).sort().map(sid => {
            const idx = parseInt(sid, 10);
            return {
                label: `Segment ${idx + 1}`,
                data: groups[sid],
                backgroundColor: colors[idx % colors.length],
                borderColor: colors[idx % colors.length],
                pointRadius: 4,
                pointHoverRadius: 6
            };
        });

        if (chartPcaInstance) {
            chartPcaInstance.destroy();
        }

        chartPcaInstance = new Chart(ctx, {
            type: "scatter",
            data: { datasets: datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 10, font: { size: 11 } } },
                    tooltip: {
                        callbacks: {
                            label: function (ctx) {
                                return `${ctx.dataset.label}: ${ctx.raw.label || ''} [PC1: ${ctx.raw.x}, PC2: ${ctx.raw.y}]`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        title: { display: true, text: "Principal Component 1 (PC1)", font: { size: 11 } },
                        grid: { color: "#F1F5F9" }
                    },
                    y: {
                        title: { display: true, text: "Principal Component 2 (PC2)", font: { size: 11 } },
                        grid: { color: "#F1F5F9" }
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------
    // 4. Cluster Optimization & Separation Curves
    // -------------------------------------------------------------
    function loadOptimizationCurves() {
        fetch(`/api/segmentation/k-evaluation`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    renderOptimizationChart(res.data);
                }
            })
            .catch(err => console.error("Error loading K-eval:", err));
    }

    function renderOptimizationChart(data) {
        const ctx = document.getElementById("chartElbowSeparation");
        if (!ctx) return;

        const labels = data.map(d => `K = ${d.k}`);
        const inertias = data.map(d => d.inertia);
        const silhouettes = data.map(d => d.silhouette_score);

        if (chartOptInstance) {
            chartOptInstance.destroy();
        }

        chartOptInstance = new Chart(ctx, {
            type: "line",
            data: {
                labels: labels,
                datasets: [
                    {
                        label: "Inertia (Within-Cluster Sum of Squares)",
                        data: inertias,
                        borderColor: "#0D63F3",
                        backgroundColor: "rgba(13, 99, 243, 0.1)",
                        yAxisID: "y",
                        fill: true,
                        tension: 0.3
                    },
                    {
                        label: "Silhouette Score (Separation)",
                        data: silhouettes,
                        borderColor: "#22B573",
                        backgroundColor: "rgba(34, 181, 115, 0.1)",
                        yAxisID: "y1",
                        borderDash: [5, 5],
                        tension: 0.3
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: "top", labels: { boxWidth: 10, font: { size: 11 } } }
                },
                scales: {
                    y: {
                        type: "linear",
                        display: true,
                        position: "left",
                        title: { display: true, text: "Inertia", font: { size: 10 } },
                        grid: { color: "#F1F5F9" }
                    },
                    y1: {
                        type: "linear",
                        display: true,
                        position: "right",
                        title: { display: true, text: "Silhouette Score", font: { size: 10 } },
                        grid: { drawOnChartArea: false }
                    }
                }
            }
        });
    }

    // -------------------------------------------------------------
    // 5. Segment Archetype Cards & Comparison Table
    // -------------------------------------------------------------
    function loadSegmentProfiles(k) {
        const cardsGrid = document.getElementById("segmentCardsGrid");
        const tbody = document.getElementById("segmentProfilesTbody");

        fetch(`/api/segmentation/profiles?k=${k}`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    const profiles = res.data;
                    document.getElementById("segmentTableCountBadge").textContent = `K = ${profiles.length} Archetypes`;

                    // Render Cards
                    cardsGrid.innerHTML = "";
                    profiles.forEach(p => {
                        const card = document.createElement("div");
                        card.className = "segment-card";
                        card.innerHTML = `
                            <div class="segment-card-header">
                                <span class="badge-neutral">Segment ${p.Segment_ID + 1}</span>
                                <span style="font-size:12px; font-weight:700; color:var(--primary-blue);">${p.Pct_Workforce}% Share</span>
                            </div>
                            <h4 style="font-size:15px; font-weight:700; color:var(--navy-text); margin:8px 0 4px;">
                                ${p.Archetype_Name}
                            </h4>
                            <p style="font-size:12px; color:var(--text-muted); margin-bottom:12px;">
                                <strong>Headcount:</strong> ${p.Headcount.toLocaleString()} employees | <strong>Dominant:</strong> ${p.Dominant_Department}
                            </p>
                            <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:6px; padding:8px 10px; font-size:12px; margin-bottom:12px; display:grid; grid-template-columns:1fr 1fr; gap:6px;">
                                <div><b>Tenure:</b> ${p.Avg_Tenure_Months} mo</div>
                                <div><b>Compa:</b> ${p.Avg_Compa_Ratio}x</div>
                                <div><b>Median Salary:</b> ₹ ${p.Median_Salary_INR.toLocaleString()}</div>
                                <div><b>Satisfaction:</b> ${p.Avg_Job_Satisfaction}/5</div>
                                <div><b>Overtime:</b> ${p.Avg_Overtime_Hours} hrs/mo</div>
                                <div><b>WLB:</b> ${p.Avg_Work_Life_Balance}/5</div>
                            </div>
                            <div style="font-size:12px; color:#0F172A; background:#FEF3C7; border:1px solid #FDE68A; border-radius:6px; padding:8px 10px;">
                                <i class="bi bi-lightbulb-fill text-warning"></i>
                                <strong>Supportive Action:</strong> ${p.Actionable_Recommendation || 'Conduct regular talent check-ins.'}
                            </div>
                        `;
                        cardsGrid.appendChild(card);
                    });

                    // Render Table
                    tbody.innerHTML = "";
                    profiles.forEach(p => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td><b>${p.Segment_ID + 1}</b></td>
                            <td><b>${p.Archetype_Name}</b></td>
                            <td>${p.Headcount.toLocaleString()}</td>
                            <td>${p.Pct_Workforce}%</td>
                            <td>${p.Dominant_Department}</td>
                            <td>${p.Dominant_Role}</td>
                            <td>${p.Avg_Tenure_Months} mo</td>
                            <td>${p.Avg_Compa_Ratio}x</td>
                            <td>₹ ${p.Median_Salary_INR.toLocaleString()}</td>
                            <td>${p.Avg_Job_Satisfaction}/5</td>
                            <td><span class="badge-neutral">${p.Flight_Risk_Rate_Pct || p.Simulated_Attrition_Pct}%</span></td>
                            <td style="font-size:12px; color:#475569;">${p.Actionable_Recommendation || p.Recommended_Talent_Action || 'Regular talent check-in'}</td>
                        `;
                        tbody.appendChild(tr);
                    });

                    // Render Segment Distribution Donut Chart if element exists
                    const distCanvas = document.getElementById("chartSegmentDistribution");
                    if (distCanvas) {
                        const palette = ["#0D63F3", "#22B573", "#FFA726", "#8B5CF6", "#EC4899", "#14B8A6"];
                        if (window.segmentDistChartInstance) {
                            window.segmentDistChartInstance.destroy();
                        }
                        const ctx = distCanvas.getContext("2d");
                        window.segmentDistChartInstance = new Chart(ctx, {
                            type: 'doughnut',
                            data: {
                                labels: profiles.map(p => `${p.Archetype_Name} (${p.Pct_Workforce}%)`),
                                datasets: [{
                                    data: profiles.map(p => p.Headcount),
                                    backgroundColor: profiles.map((p, idx) => palette[idx % palette.length]),
                                    borderWidth: 2,
                                    borderColor: '#ffffff'
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                cutout: '65%',
                                plugins: {
                                    legend: {
                                        position: 'bottom',
                                        labels: { boxWidth: 12, font: { size: 11 } }
                                    },
                                    tooltip: {
                                        callbacks: {
                                            label: function (ctx) {
                                                const p = profiles[ctx.dataIndex];
                                                return ` ${p.Archetype_Name}: ${p.Headcount.toLocaleString()} (${p.Pct_Workforce}%)`;
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                }
            })
            .catch(err => console.error("Error loading segment profiles:", err));
    }

    // -------------------------------------------------------------
    // 6. Employee Cluster Assignments Table
    // -------------------------------------------------------------
    function loadSegmentEmployees() {
        const tbody = document.getElementById("segmentEmployeesTbody");
        tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">Loading employees...</td></tr>`;

        let url = `/api/segmentation/employees?page=${segEmpPage}&page_size=${segEmpPageSize}`;
        if (segEmpFilterSegment >= 0) url += `&segment_id=${segEmpFilterSegment}`;
        if (segEmpSearch) url += `&search=${encodeURIComponent(segEmpSearch)}`;

        fetch(url)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.records) {
                    tbody.innerHTML = "";
                    if (res.records.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">No employees found matching filter.</td></tr>`;
                        return;
                    }

                    res.records.forEach(emp => {
                        const tr = document.createElement("tr");
                        const nameDisplay = emp.Employee_Name && emp.Employee_Name !== emp.Employee_ID
                            ? `<b>${emp.Employee_Name}</b>`
                            : '<span class="text-muted" title="Name not recorded in source">—</span>';

                        tr.innerHTML = `
                            <td><code>${emp.Employee_ID}</code></td>
                            <td>${nameDisplay}</td>
                            <td>${emp.Department}</td>
                            <td>${emp.Job_Role}</td>
                            <td>${emp.Job_Level}</td>
                            <td><span class="badge-neutral">Segment ${emp.Segment_ID + 1}</span></td>
                            <td>${emp.Tenure_Months_At_Prediction}</td>
                            <td>₹ ${emp.Annual_Salary_INR.toLocaleString()}</td>
                            <td>${emp.Compa_Ratio}x</td>
                            <td>${emp.Job_Satisfaction_Score_1_5}/5</td>
                            <td>${emp.Overtime_Hours_Monthly} hrs</td>
                            <td>
                                <button class="btn btn-outline-primary btn-sm view-emp-btn" data-id="${emp.Employee_ID}">
                                    Inspect
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });

                    // Update pagination
                    document.getElementById("segEmpPageInfo")?.innerText || (document.getElementById("segEmployeesPageInfo").textContent = `Showing page ${res.page} of ${res.total_pages} (${res.total_records.toLocaleString()} total)`);
                    document.getElementById("btnPrevSegEmp").disabled = (res.page <= 1);
                    document.getElementById("btnNextSegEmp").disabled = (res.page >= res.total_pages);

                    // Attach inspect listener
                    document.querySelectorAll(".view-emp-btn").forEach(b => {
                        b.addEventListener("click", function () {
                            const empId = this.getAttribute("data-id");
                            if (window.showEmployeeDetail) {
                                window.showEmployeeDetail(empId);
                            }
                        });
                    });
                }
            })
            .catch(err => {
                console.error("Error loading segment employees:", err);
                tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-danger">Error loading employee list.</td></tr>`;
            });
    }

    // -------------------------------------------------------------
    // 7. Role Staffing Pressure & Anomalies
    // -------------------------------------------------------------
    function loadRolePressureData() {
        const tbody = document.getElementById("rolePressureTbody");
        const tier = document.getElementById("roleTierFilter")?.value || "All";

        fetch(`/api/segmentation/role-pressure?pressure_tier=${tier}`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    tbody.innerHTML = "";
                    res.data.slice(0, 15).forEach(r => {
                        const tr = document.createElement("tr");
                        const tierBadge = r.Pressure_Tier === "Critical Staffing Pressure"
                            ? '<span class="badge-danger">Critical</span>'
                            : (r.Pressure_Tier === "Moderate Staffing Risk" ? '<span class="badge-warning">Moderate</span>' : '<span class="badge-success">Stable</span>');

                        tr.innerHTML = `
                            <td><b>${r.Job_Role}</b></td>
                            <td>${r.Headcount}</td>
                            <td>${r.Notice_Exits}</td>
                            <td>${r.Open_Requisitions || r.Positions_Remaining || 0}</td>
                            <td><b>${r.Staffing_Pressure_Ratio}</b></td>
                            <td>${tierBadge}</td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            })
            .catch(err => console.error("Error loading role pressure:", err));
    }

    function loadAnomaliesData() {
        const tbody = document.getElementById("anomaliesTbody");
        fetch(`/api/segmentation/anomalies?page=1&page_size=15`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data && res.data.records) {
                    tbody.innerHTML = "";
                    res.data.records.forEach(a => {
                        const tr = document.createElement("tr");
                        tr.innerHTML = `
                            <td><code>${a.Employee_ID}</code></td>
                            <td>${a.Job_Role}</td>
                            <td>${a.Compa_Ratio}x</td>
                            <td>${a.Overtime_Hours_Monthly} hrs</td>
                            <td>${a.Work_Life_Balance_Score_1_5}/5</td>
                            <td><span class="badge-neutral" style="font-size:11px;">${a.Anomaly_Category || a.Anomaly_Type}</span></td>
                        `;
                        tbody.appendChild(tr);
                    });
                }
            })
            .catch(err => console.error("Error loading anomalies:", err));
    }
});
