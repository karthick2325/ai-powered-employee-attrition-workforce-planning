/**
 * Workforce Intelligence — Segmentation & Talent Analytics Controller
 * Handles 5-algorithm unsupervised benchmark rendering, 2D PCA projection scatter,
 * dynamic archetype cards, profile table, role pressure, anomalies, and paginated employee assignments.
 */

document.addEventListener("DOMContentLoaded", function () {
    let currentK = 5;
    let currentProfiles = [];
    let segmentNameById = new Map();
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


    function setText(id, value) {
        const element = document.getElementById(id);
        if (element) element.textContent = value == null ? "—" : String(value);
    }

    function formatCount(value) {
        const number = Number(value);
        return value == null || !Number.isFinite(number) ? "—" : number.toLocaleString();
    }

    function setupEventListeners() {
        // K selector (2-10 segments). Backend endpoints must accept the selected k.
        const kSelect = document.getElementById("segmentationKSelect");
        if (kSelect) {
            kSelect.value = String(currentK);
            kSelect.addEventListener("change", function () {
                const selectedK = Number.parseInt(this.value, 10);
                if (Number.isInteger(selectedK) && selectedK >= 2 && selectedK <= 10 && selectedK !== currentK) {
                    currentK = selectedK;
                    segEmpPage = 1;
                    segEmpFilterSegment = -1;
                    const filter = document.getElementById("segFilterSegment");
                    if (filter) filter.value = "-1";
                    handleKChange(selectedK);
                }
            });
        }

        // Backward compatibility for existing .k-btn controls, if present.
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
        loadPcaScatter(k);
        loadSegmentProfiles(k);
        loadSegmentEmployees();
        loadRolePressureData();
        loadAnomaliesData();
    }

    function handleKChange(k) {
        loadOverviewKpis(k);
        loadSegmentProfiles(k);
        loadPcaScatter(k);
        loadSegmentEmployees();
    }

    // -------------------------------------------------------------
    // 1. Executive KPIs
    // -------------------------------------------------------------
    function loadOverviewKpis(k) {
        fetch(`/api/segmentation/overview?k=${encodeURIComponent(k)}`)
            .then(async response => {
                const body = await response.json();
                if (!response.ok || body.success === false) {
                    throw new Error(body.error || `Overview API failed (${response.status})`);
                }
                return body;
            })
            .then(res => {
                if (res.success && res.data) {
                    const d = res.data;
                    // Display only values returned by the backend; do not invent fallback metrics.
                    setText("kpiTotalClustered", formatCount(d.total_clustered_employees));
                    setText("kpiSegmentCountBadge", `K = ${d.current_k ?? k} Segments`);
                    setText("kpiBestModel", d.best_validated_algorithm || "K-Means");
                    const silhouette = d.silhouette_score == null ? null : Number(d.silhouette_score);
                    setText("kpiBestModelMetric", silhouette == null || !Number.isFinite(silhouette)
                        ? "Cluster separation: unavailable"
                        : silhouette < 0.20
                            ? `Low separation (silhouette: ${silhouette.toFixed(4)})`
                            : `Silhouette score: ${silhouette.toFixed(4)}`);
                    setText("kpiSegmentCoverage", d.clustering_coverage_pct == null
                        ? "—" : `${Number(d.clustering_coverage_pct).toFixed(1)}%`);
                    setText("kpiNoiseRate", d.unassigned_noise_pct == null
                        ? "—" : `${Number(d.unassigned_noise_pct).toFixed(1)}%`);
                    setText("kpiTotalAnomalies", formatCount(d.total_anomalies_flagged));
                    setText("kpiTopPressureRatio", d.top_pressure_role?.pressure_ratio == null
                        ? "—" : Number(d.top_pressure_role.pressure_ratio).toFixed(3));
                    setText("kpiTopPressureRole", d.top_pressure_role?.job_role
                        ? `Top: ${d.top_pressure_role.job_role}` : "No role-pressure data");
                }
            })
            .catch(err => {
                console.error("Error loading KPIs:", err);
                setText("kpiTotalClustered", "Unavailable");
                setText("kpiSegmentCoverage", "Unavailable");
                setText("kpiNoiseRate", "Unavailable");
                setText("kpiTopPressureRatio", "Unavailable");
                setText("kpiTotalAnomalies", "Unavailable");
                setText("kpiBestModelMetric", `Could not load KPI data: ${String(err.message || err)}`);
                setText("segmentationStatus", "Some segmentation KPIs could not load. Check the backend API and application log.");
            });
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
                    setText("benchmarkTimestampBadge", b.dataset_records == null
                        ? "Benchmark evaluated" : `Evaluated: ${formatCount(b.dataset_records)} Active Records`);
                    const winner = Array.isArray(b.candidates)
                        ? b.candidates.find(candidate => candidate.name === b.selected_algorithm) : null;
                    setText("kpiSegmentCoverage", winner?.coverage_percentage == null
                        ? "—" : `${Number(winner.coverage_percentage).toFixed(1)}%`);
                    setText("kpiNoiseRate", winner?.noise_percentage == null
                        ? "—" : `${Number(winner.noise_percentage).toFixed(1)}%`);

                    // Rationale banner
                    const alertEl = document.getElementById("selectionRationaleText");
                    if (alertEl) {
                        alertEl.textContent = b.selected_algorithm
                            ? `Recommended Model: ${b.selected_algorithm} — ${b.selection_rationale || "No selection rationale was returned."}`
                            : "No validated algorithm recommendation is available.";
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
    function loadPcaScatter(k = currentK) {
        fetch(`/api/segmentation/pca?k=${encodeURIComponent(k)}`)
            .then(res => res.json())
            .then(res => {
                if (res.success && res.data) {
                    const pca = res.data;
                    const badge = document.getElementById("pcaVarianceBadge");
                    if (badge) badge.textContent = pca.total_explained_variance_pct == null
                        ? "PCA variance unavailable"
                        : `PC1: ${pca.pc1_explained_variance_pct}% | PC2: ${pca.pc2_explained_variance_pct}% | Total: ${pca.total_explained_variance_pct}%`;
                    if (Array.isArray(pca.points) && pca.points.length) renderPcaChart(pca.points);
                    else showChartMessage("chartPcaScatter", "No PCA points are available for this selection.");
                } else {
                    showChartMessage("chartPcaScatter", "PCA data is unavailable for this selection.");
                }
            })
            .catch(err => {
                console.error("Error loading PCA:", err);
                showChartMessage("chartPcaScatter", "Could not load PCA data. Check the backend API.");
            });
    }

    function showChartMessage(canvasId, message) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        if (canvas._emptyMessageNode) canvas._emptyMessageNode.remove();
        canvas.style.display = "none";
        const note = document.createElement("div");
        note.className = "text-muted text-center py-5";
        note.setAttribute("role", "status");
        note.textContent = message;
        canvas.parentElement.appendChild(note);
        canvas._emptyMessageNode = note;
    }

    function clearChartMessage(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        if (canvas._emptyMessageNode) canvas._emptyMessageNode.remove();
        canvas._emptyMessageNode = null;
        canvas.style.display = "block";
    }

    function renderPcaChart(points) {
        clearChartMessage("chartPcaScatter");
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
    function loadOptimizationCurves(k = currentK) {
        fetch(`/api/segmentation/k-evaluation?selected_k=${encodeURIComponent(k)}`)
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
    // Segment naming helpers
    // Prefer backend-generated names. If names are blank/duplicated,
    // create distinct descriptive fallback names from each cluster profile.
    // These are descriptive labels, not attrition predictions.
    // -------------------------------------------------------------
    function safeNumber(value) {
        const n = Number(value);
        return Number.isFinite(n) ? n : null;
    }

    function getProfileMetric(p, keys) {
        for (const key of keys) {
            const value = safeNumber(p[key]);
            if (value !== null) return value;
        }
        return null;
    }

    function buildUniqueSegmentNames(profiles) {
        const used = new Set();
        const nameMap = new Map();

        // First preserve names that are already unique.
        const normalized = profiles.map(p => ({
            ...p,
            _baseName: String(p.Archetype_Name || "").trim()
        }));

        const counts = new Map();
        normalized.forEach(p => {
            const key = p._baseName.toLowerCase();
            if (key) counts.set(key, (counts.get(key) || 0) + 1);
        });

        normalized.forEach(p => {
            const id = Number(p.Segment_ID);
            const base = p._baseName;
            let name = base;

            if (!base || counts.get(base.toLowerCase()) > 1) {
                const tenure = getProfileMetric(p, ["Avg_Tenure_Months", "Avg_Tenure"]);
                const compa = getProfileMetric(p, ["Avg_Compa_Ratio", "Avg_Compa"]);
                const satisfaction = getProfileMetric(p, ["Avg_Job_Satisfaction", "Satisfaction"]);
                const overtime = getProfileMetric(p, ["Avg_Overtime_Hours", "Avg_Overtime"]);
                const wlb = getProfileMetric(p, ["Avg_Work_Life_Balance", "Avg_WLB"]);

                if (compa !== null && compa < 0.90) {
                    name = "Compensation Review Cohort";
                } else if (tenure !== null && tenure >= 72) {
                    name = "Experienced Core Workforce";
                } else if (overtime !== null && overtime >= 10) {
                    name = "Workload Review Cohort";
                } else if (satisfaction !== null && satisfaction < 3.2) {
                    name = "Employee Support Priority Group";
                } else if (wlb !== null && wlb < 3.0) {
                    name = "Work-Life Balance Support Group";
                } else if (tenure !== null && tenure < 40) {
                    name = "Developing Workforce";
                } else if (compa !== null && compa >= 1.10) {
                    name = "Market-Aligned Specialist Cohort";
                } else {
                    name = "Established Operational Workforce";
                }
            }

            // Guarantee uniqueness even when two clusters have similar profiles.
            if (used.has(name.toLowerCase())) {
                const tenure = getProfileMetric(p, ["Avg_Tenure_Months", "Avg_Tenure"]);
                const suffix = tenure !== null ? ` (${Math.round(tenure)} mo tenure)` : ` (Cluster ${id + 1})`;
                name = `${name}${suffix}`;
            }

            let candidate = name;
            let counter = 2;
            while (used.has(candidate.toLowerCase())) {
                candidate = `${name} ${counter++}`;
            }

            name = candidate;
            used.add(name.toLowerCase());
            nameMap.set(id, name);
        });

        return nameMap;
    }

    function getSegmentDisplayName(segmentId) {
        const id = Number(segmentId);
        return segmentNameById.get(id) || `Segment ${id + 1}`;
    }

    function populateSegmentFilter(profiles) {
        const select = document.getElementById("segFilterSegment");
        if (!select) return;

        const previous = select.value;
        select.innerHTML = '<option value="-1">All Segments</option>';

        profiles.forEach(p => {
            const option = document.createElement("option");
            option.value = String(p.Segment_ID);
            option.textContent = `Segment ${Number(p.Segment_ID) + 1} — ${getSegmentDisplayName(p.Segment_ID)}`;
            select.appendChild(option);
        });

        if ([...select.options].some(o => o.value === previous)) {
            select.value = previous;
        } else {
            select.value = "-1";
            segEmpFilterSegment = -1;
        }
    }

    // -------------------------------------------------------------
    // 5. Segment Archetype Cards & Comparison Table
    // -------------------------------------------------------------
    function loadSegmentProfiles(k) {
        const cardsGrid = document.getElementById("segmentCardsGrid");
        const tbody = document.getElementById("segmentProfilesTbody");

        fetch(`/api/segmentation/profiles?k=${encodeURIComponent(k)}`)
            .then(async response => {
                const body = await response.json();
                if (!response.ok || body.success === false) {
                    throw new Error(body.error || `Profile API failed (${response.status})`);
                }
                return body;
            })
            .then(res => {
                if (res.success && Array.isArray(res.data)) {
                    const profiles = res.data;
                    if (!profiles.length) {
                        showChartMessage("chartSegmentDistribution", "No segment profile data is available for this K value.");
                        throw new Error("No segment profiles were returned for the selected K.");
                    }
                    currentProfiles = profiles;
                    segmentNameById = buildUniqueSegmentNames(profiles);
                    populateSegmentFilter(profiles);

                    document.getElementById("segmentTableCountBadge").textContent = `K = ${profiles.length} Archetypes`;

                    const kSelect = document.getElementById("segmentationKSelect");
                    if (kSelect) kSelect.value = String(k);

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
                                ${getSegmentDisplayName(p.Segment_ID)}
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
                            <td><b>${getSegmentDisplayName(p.Segment_ID)}</b></td>
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

                    // Render an HR-focused mixed chart: gender headcount stacked columns
                    // plus average job satisfaction on a separate 1–5 axis.
                    const distCanvas = document.getElementById("chartSegmentDistribution");
                    if (distCanvas) {
                        clearChartMessage("chartSegmentDistribution");
                        if (window.segmentDistChartInstance) {
                            window.segmentDistChartInstance.destroy();
                        }

                        const genderReady = profiles.every(p => p.Gender_Counts_Available === true
                            && p.Gender_Male_Count != null
                            && p.Gender_Female_Count != null
                            && p.Gender_Other_Count != null);
                        const safeMetric = (value, decimals = 1) => {
                            const n = Number(value);
                            return value == null || value === "" || !Number.isFinite(n)
                                ? "N/A" : n.toFixed(decimals);
                        };
                        const safeCount = value => {
                            const n = Number(value);
                            return value == null || value === "" || !Number.isFinite(n)
                                ? "N/A" : Math.round(n).toLocaleString();
                        };
                        const palette = ["#0D63F3", "#22B573", "#FFA726", "#8B5CF6", "#EC4899", "#14B8A6"];
                        const chartData = {
                            labels: profiles.map(p => `Segment ${Number(p.Segment_ID) + 1}`),
                            datasets: []
                        };

                        if (genderReady) {
                            chartData.datasets.push(
                                {
                                    type: "bar", label: "Male employees", stack: "gender",
                                    data: profiles.map(p => Number(p.Gender_Male_Count)),
                                    backgroundColor: "#397FF5", borderRadius: 4, yAxisID: "yHeadcount"
                                },
                                {
                                    type: "bar", label: "Female employees", stack: "gender",
                                    data: profiles.map(p => Number(p.Gender_Female_Count)),
                                    backgroundColor: "#20B486", borderRadius: 4, yAxisID: "yHeadcount"
                                },
                                {
                                    type: "bar", label: "Other / non-disclosed", stack: "gender",
                                    data: profiles.map(p => Number(p.Gender_Other_Count)),
                                    backgroundColor: "#F5A623", borderRadius: 4, yAxisID: "yHeadcount"
                                }
                            );
                        } else {
                            chartData.datasets.push({
                                type: "bar", label: "Segment headcount", stack: "gender",
                                data: profiles.map(p => Number(p.Headcount) || 0),
                                backgroundColor: profiles.map((p, idx) => palette[idx % palette.length]),
                                borderRadius: 4, yAxisID: "yHeadcount"
                            });
                        }

                        chartData.datasets.push({
                            type: "line",
                            label: "Average job satisfaction (1–5)",
                            data: profiles.map(p => {
                                const value = Number(p.Avg_Job_Satisfaction);
                                return p.Avg_Job_Satisfaction == null || !Number.isFinite(value) ? null : value;
                            }),
                            yAxisID: "ySatisfaction",
                            borderColor: "#E34B65",
                            backgroundColor: "#E34B65",
                            pointBackgroundColor: "#E34B65",
                            pointBorderColor: "#FFFFFF",
                            pointBorderWidth: 2,
                            pointRadius: 4,
                            pointHoverRadius: 6,
                            borderWidth: 3,
                            tension: 0.25,
                            spanGaps: false
                        });

                        const ctx = distCanvas.getContext("2d");
                        window.segmentDistChartInstance = new Chart(ctx, {
                            type: "bar",
                            data: chartData,
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                interaction: { mode: "index", intersect: false },
                                scales: {
                                    x: {
                                        stacked: true,
                                        grid: { display: false },
                                        ticks: { color: "#64748B", maxRotation: 0, minRotation: 0 }
                                    },
                                    yHeadcount: {
                                        type: "linear", position: "left", stacked: true, beginAtZero: true,
                                        title: { display: true, text: "Employees" },
                                        ticks: { callback: value => Number(value).toLocaleString() },
                                        grid: { color: "#EEF2F7" }
                                    },
                                    ySatisfaction: {
                                        type: "linear", position: "right", min: 1, max: 5,
                                        title: { display: true, text: "Average satisfaction (1–5)" },
                                        grid: { drawOnChartArea: false },
                                        ticks: { stepSize: 1 }
                                    }
                                },
                                plugins: {
                                    legend: { position: "bottom", labels: { boxWidth: 12, usePointStyle: true, font: { size: 11 } } },
                                    tooltip: {
                                        callbacks: {
                                            title: items => {
                                                const p = profiles[items[0]?.dataIndex];
                                                return p ? `Segment ${Number(p.Segment_ID) + 1} — ${getSegmentDisplayName(p.Segment_ID)}` : "Segment details";
                                            },
                                            label: context => {
                                                const p = profiles[context.dataIndex];
                                                if (!p) return `${context.dataset.label}: N/A`;
                                                if (context.dataset.label === "Male employees") return `Male employees: ${safeCount(p.Gender_Male_Count)}`;
                                                if (context.dataset.label === "Female employees") return `Female employees: ${safeCount(p.Gender_Female_Count)}`;
                                                if (context.dataset.label === "Other / non-disclosed") return `Other / non-disclosed: ${safeCount(p.Gender_Other_Count)}`;
                                                if (context.dataset.label === "Segment headcount") return `Headcount: ${safeCount(p.Headcount)}`;
                                                if (context.dataset.label === "Average job satisfaction (1–5)") return `Average satisfaction: ${safeMetric(p.Avg_Job_Satisfaction, 2)} / 5`;
                                                return `${context.dataset.label}: ${safeCount(context.raw)}`;
                                            },
                                            afterBody: items => {
                                                const p = profiles[items[0]?.dataIndex];
                                                if (!p) return [];
                                                const genderLines = p.Gender_Counts_Available === true
                                                    ? [`Total gender-counted employees: ${safeCount(Number(p.Gender_Male_Count) + Number(p.Gender_Female_Count) + Number(p.Gender_Other_Count))}`]
                                                    : ["Gender counts: unavailable in source data"];
                                                return [
                                                    `Workforce share: ${safeMetric(p.Pct_Workforce, 2)}%`,
                                                    ...genderLines,
                                                    `Average tenure: ${safeMetric(p.Avg_Tenure_Months)} months`,
                                                    `Median salary: ${p.Median_Salary_INR == null ? "N/A" : "₹ " + safeCount(p.Median_Salary_INR)}`,
                                                    `Compa-ratio: ${safeMetric(p.Avg_Compa_Ratio, 3)}x`,
                                                    `Average overtime: ${safeMetric(p.Avg_Overtime_Hours)} hrs/month`,
                                                    `Average training: ${safeMetric(p.Avg_Training_Hours)} hrs/12 months`,
                                                    `Work-life balance: ${safeMetric(p.Avg_Work_Life_Balance, 2)} / 5`,
                                                    `Observed 6-month outcome rate: ${safeMetric(p.Flight_Risk_Rate_Pct ?? p.Simulated_Attrition_Pct, 2)}%`
                                                ];
                                            }
                                        }
                                    }
                                }
                            }
                        });
                    }
                } else {
                    throw new Error("The profiles API returned an unexpected response format.");
                }
            })
            .catch(err => {
                console.error("Error loading segment profiles:", err);
                if (cardsGrid) cardsGrid.innerHTML = `<div class="text-danger">Could not load segment profiles: ${String(err.message || err)}</div>`;
                if (tbody) tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-danger">Could not load profiles: ${String(err.message || err)}</td></tr>`;
                showChartMessage("chartSegmentDistribution", "Segment chart data is unavailable. Check the profiles API.");
                setText("segmentCardCountBadge", "Profiles unavailable");
                setText("segmentTableCountBadge", "Profiles unavailable");
            });
    }

    // -------------------------------------------------------------
    // 6. Employee Cluster Assignments Table
    // -------------------------------------------------------------
    function loadSegmentEmployees() {
        const tbody = document.getElementById("segmentEmployeesTbody");
        tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">Loading employees...</td></tr>`;

        let url = `/api/segmentation/employees?page=${segEmpPage}&page_size=${segEmpPageSize}&k=${encodeURIComponent(currentK)}`;
        if (segEmpFilterSegment >= 0) url += `&segment_id=${segEmpFilterSegment}`;
        if (segEmpSearch) url += `&search=${encodeURIComponent(segEmpSearch)}`;

        fetch(url)
            .then(res => res.json())
            .then(res => {
                const payload = res && res.data ? res.data : res;
                if (res.success && payload && Array.isArray(payload.records)) {
                    tbody.innerHTML = "";

                    if (payload.records.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="12" class="text-center py-4 text-muted">No employees found matching filter.</td></tr>`;
                        const pageInfo = document.getElementById("segEmployeesPageInfo");
                        if (pageInfo) pageInfo.textContent = "No matching employees";
                        return;
                    }

                    payload.records.forEach(emp => {
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
                            <td><span class="badge-neutral" title="${getSegmentDisplayName(emp.Segment_ID)}">Segment ${emp.Segment_ID + 1}: ${getSegmentDisplayName(emp.Segment_ID)}</span></td>
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
                    const pageInfo = document.getElementById("segEmployeesPageInfo");
                    if (pageInfo) {
                        pageInfo.textContent = `Showing page ${payload.page} of ${payload.total_pages} (${formatCount(payload.total_records)} total)`;
                    }
                    const previousButton = document.getElementById("btnPrevSegEmp");
                    const nextButton = document.getElementById("btnNextSegEmp");
                    if (previousButton) previousButton.disabled = (payload.page <= 1);
                    if (nextButton) nextButton.disabled = (payload.page >= payload.total_pages);

                    // Attach inspect listener
                    document.querySelectorAll(".view-emp-btn").forEach(b => {
                        b.addEventListener("click", function () {
                            const empId = this.getAttribute("data-id");
                            if (window.showEmployeeDetail) {
                                window.showEmployeeDetail(empId);
                            }
                        });
                    });
                } else {
                    throw new Error(res.error || "Employee API returned an unexpected response format.");
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