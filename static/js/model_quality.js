/**
 * Workforce Intelligence — AI Model Intelligence Controller
 * Handles Supervised Attrition Models, 5-Algorithm Clustering Benchmark,
 * Diagnostics Charts (ROC, PR, Elbow, Silhouette), and Governance Audits.
 */

let rocChartInstance = null;
let prChartInstance = null;
let fiChartInstance = null;
let elbowChartInstance = null;
let silhouetteChartInstance = null;

let _currentSupervisedData = null;
let _currentModelDetails = {};
let _activeSupervisedModel = 'Random Forest';

// Render missing or invalid metrics as N/A rather than throwing on null.toFixed().
function safeMetric(value, digits = 3) {
    const number = Number(value);
    return value !== null && value !== undefined && value !== '' && Number.isFinite(number)
        ? number.toFixed(digits)
        : 'N/A';
}

function setTextIfPresent(id, value) {
    const element = document.getElementById(id);
    if (element) element.textContent = value;
}

function showTableMessage(tbody, message, colspan) {
    if (!tbody) return;
    tbody.innerHTML = `<tr><td colspan="${colspan}" class="text-center p-4">${message}</td></tr>`;
}

document.addEventListener('DOMContentLoaded', async () => {
    await loadSupervisedModelSummary();
    await loadUnsupervisedBenchmark();
    await loadKEvaluationCharts();
    setupRetrainHandler();
    setupClusterBenchmarkHandler();
});

function renderSupervisedModelMetrics(modelName) {
    if (!_currentSupervisedData) return;
    _activeSupervisedModel = modelName;

    // Sync select dropdown
    const selectElem = document.getElementById('selectSupervisedModel');
    if (selectElem && selectElem.value !== modelName) {
        selectElem.value = modelName;
    }

    const isBest = modelName === _currentSupervisedData.selected_model;
    const badge = document.getElementById('bestModelBadge');
    if (badge) {
        badge.textContent = `${modelName} (${isBest ? 'Selected Benchmark' : 'Inspecting Details'})`;
        badge.className = isBest ? 'card-badge' : 'badge badge-neutral';
    }

    // Highlight row in comparison table
    const rows = document.querySelectorAll('#modelComparisonTableBody tr');
    rows.forEach(r => {
        if (r.getAttribute('data-model-name') === modelName) {
            r.style.background = '#EBF3FE';
            r.style.fontWeight = '600';
        } else {
            r.style.background = '';
            r.style.fontWeight = '';
        }
    });

    // Lookup model details
    let m = _currentModelDetails[modelName];
    if (!m) {
        // Fallback to top-level ev if primary
        m = {
            confusion_matrix: _currentSupervisedData.confusion_matrix,
            roc_curve: _currentSupervisedData.roc_curve,
            pr_curve: _currentSupervisedData.pr_curve,
            feature_importance: _currentSupervisedData.feature_importance
        };
    }

    // 1. Confusion Matrix
    const cm = m.confusion_matrix;
    setTextIfPresent('cmTN', cm ? formatNumber(cm.true_negative) : 'N/A');
    setTextIfPresent('cmFP', cm ? formatNumber(cm.false_positive) : 'N/A');
    setTextIfPresent('cmFN', cm ? formatNumber(cm.false_negative) : 'N/A');
    setTextIfPresent('cmTP', cm ? formatNumber(cm.true_positive) : 'N/A');

    // 2. ROC Curve
    const roc = m.roc_curve;
    if (roc && document.getElementById('rocCurveChart')) {
        document.getElementById('rocAucBadge').textContent = `AUC = ${roc.auc}`;
        if (rocChartInstance) rocChartInstance.destroy();
        const ctx = document.getElementById('rocCurveChart').getContext('2d');
        rocChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: roc.fpr.map(v => v.toFixed(2)),
                datasets: [
                    {
                        label: `${modelName} ROC`,
                        data: roc.tpr,
                        borderColor: '#0D63F3',
                        backgroundColor: 'rgba(13, 99, 243, 0.08)',
                        fill: true,
                        tension: 0.2,
                        pointRadius: 0,
                        borderWidth: 2
                    },
                    {
                        label: 'Random Baseline',
                        data: roc.fpr,
                        borderColor: '#94A3B8',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0,
                        borderWidth: 1.5
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'False Positive Rate', font: { size: 10 } }, grid: { color: '#F1F5F9' } },
                    y: { title: { display: true, text: 'True Positive Rate', font: { size: 10 } }, beginAtZero: true, max: 1.0, grid: { color: '#F1F5F9' } }
                }
            }
        });
    }

    // 3. Precision-Recall Curve
    const pr = m.pr_curve;
    if (pr && document.getElementById('prCurveChart')) {
        document.getElementById('prAucBadge').textContent = `PR-AUC = ${pr.pr_auc}`;
        if (prChartInstance) prChartInstance.destroy();
        const ctx = document.getElementById('prCurveChart').getContext('2d');
        prChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: pr.recall.map(v => v.toFixed(2)),
                datasets: [{
                    label: `${modelName} PR`,
                    data: pr.precision,
                    borderColor: '#FFA726',
                    backgroundColor: 'rgba(255, 167, 38, 0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Recall', font: { size: 10 } }, grid: { color: '#F1F5F9' } },
                    y: { title: { display: true, text: 'Precision', font: { size: 10 } }, beginAtZero: true, max: 1.0, grid: { color: '#F1F5F9' } }
                }
            }
        });
    }

    // 4. Feature Importance
    const fi = m.feature_importance || [];
    const fiTitle = document.getElementById('featureImportanceTitle');
    if (fiTitle) {
        const metricName = modelName === 'Logistic Regression' ? 'Coefficient Magnitude' : 'Gini Importance';
        fiTitle.textContent = `Key Feature Attribution (${modelName} ${metricName})`;
    }
    if (fi.length > 0 && document.getElementById('featureImportanceChart')) {
        if (fiChartInstance) fiChartInstance.destroy();
        const ctx = document.getElementById('featureImportanceChart').getContext('2d');
        fiChartInstance = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: fi.slice(0, 8).map(item => item.feature),
                datasets: [{
                    label: modelName === 'Logistic Regression' ? 'Normalized Coefficient' : 'Gini Importance',
                    data: fi.slice(0, 8).map(item => item.importance),
                    backgroundColor: modelName === 'Random Forest' ? '#3B82F6' : (modelName === 'XGBoost' ? '#10B981' : '#8547F5'),
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#F1F5F9' }, title: { display: true, text: 'Relative Weight', font: { size: 10 } } },
                    y: { grid: { display: false }, ticks: { font: { size: 10.5 } } }
                }
            }
        });
    }
}

async function loadSupervisedModelSummary() {
    try {
        const res = await API.get('/api/model-quality/summary');
        if (!res.success) {
            console.error('Failed to load supervised model quality summary');
            return;
        }

        const ev = res.evaluation;
        const ds = res.dataset_summary;
        const dq = res.data_quality_checks;
        const mi = res.model_info;

        _currentSupervisedData = ev;
        _currentModelDetails = ev.model_details || {};
        _activeSupervisedModel = ev.selected_model || 'Random Forest';

        // 1. Executive KPIs
        if (document.getElementById('kpiTrainRecords')) {
            document.getElementById('kpiTrainRecords').textContent = formatNumber(ev.training_records);
        }
        if (document.getElementById('kpiTestRecords')) {
            document.getElementById('kpiTestRecords').textContent = formatNumber(ev.test_records);
        }
        if (document.getElementById('kpiPositiveClass')) {
            document.getElementById('kpiPositiveClass').textContent = formatNumber(ev.positive_class);
        }
        if (document.getElementById('kpiPositivePct')) {
            document.getElementById('kpiPositivePct').textContent = `${ev.positive_pct}% historical exit baseline`;
        }
        if (document.getElementById('kpiNegativeClass')) {
            document.getElementById('kpiNegativeClass').textContent = formatNumber(ev.negative_class);
        }
        if (document.getElementById('kpiNegativePct')) {
            document.getElementById('kpiNegativePct').textContent = `${ev.negative_pct}% of cohort`;
        }

        // Setup select dropdown
        const selectElem = document.getElementById('selectSupervisedModel');
        if (selectElem) {
            selectElem.value = _activeSupervisedModel;
            selectElem.onchange = (e) => {
                renderSupervisedModelMetrics(e.target.value);
            };
        }

        // 2. Supervised Algorithm Comparison Table
        const tbody = document.getElementById('modelComparisonTableBody');
        if (tbody) {
            tbody.innerHTML = (ev.model_comparison || []).map(m => {
                const isSelected = m.model_name === ev.selected_model;
                const trophy = isSelected ? '<i class="bi bi-trophy-fill text-warning me-1"></i> ' : '';
                const rowStyle = isSelected ? 'style="background:#EBF3FE; font-weight:600; cursor:pointer;"' : 'style="cursor:pointer;"';
                const statusBadge = isSelected 
                    ? '<span class="badge badge-valid"><i class="bi bi-check-circle-fill"></i> Selected</span>' 
                    : '<span class="badge badge-neutral">Evaluated</span>';
                const brier = safeMetric(m.brier_score, 4);

                return `
                    <tr data-model-name="${m.model_name}" ${rowStyle} title="Click to inspect ${m.model_name} metrics">
                        <td>${trophy}<strong>${m.model_name}</strong></td>
                        <td>${safeMetric(m.accuracy, 3)}</td>
                        <td>${safeMetric(m.precision, 3)}</td>
                        <td>${safeMetric(m.recall, 3)}</td>
                        <td><strong>${safeMetric(m.f1_score, 3)}</strong></td>
                        <td>${safeMetric(m.roc_auc, 3)}</td>
                        <td><strong style="color:var(--primary-blue);">${safeMetric(m.pr_auc, 3)}</strong></td>
                        <td>${brier}</td>
                        <td>${statusBadge}</td>
                    </tr>
                `;
            }).join('');

            tbody.querySelectorAll('tr').forEach(row => {
                row.addEventListener('click', () => {
                    const modelName = row.getAttribute('data-model-name');
                    if (modelName) renderSupervisedModelMetrics(modelName);
                });
            });
        }

        // Render initial active model metrics & charts
        renderSupervisedModelMetrics(_activeSupervisedModel);
        // 7. Dataset Summary Table
        const dsTbody = document.getElementById('datasetSummaryTableBody');
        if (dsTbody) {
            dsTbody.innerHTML = (ds || []).map(s => `
                <tr>
                    <td><strong>${s.sheet_name}</strong></td>
                    <td>${formatNumber(s.total_records)}</td>
                    <td>${s.total_columns}</td>
                    <td><span class="badge badge-valid"><i class="bi bi-check-circle-fill"></i> ${s.validation_status}</span></td>
                </tr>
            `).join('');
        }

        // 8. Data Quality Checks Table
        const dqTbody = document.getElementById('qualityChecksTableBody');
        if (dqTbody) {
            dqTbody.innerHTML = (dq || []).map(q => {
                const icon = q.passed 
                    ? '<i class="bi bi-check-circle-fill text-success"></i>' 
                    : '<i class="bi bi-exclamation-triangle-fill text-warning"></i>';
                return `
                    <tr>
                        <td><strong>${q.check_type}</strong></td>
                        <td>${icon} <span style="font-size:11px;">${q.result}</span></td>
                        <td style="color:var(--text-muted); font-size:10.5px;">${q.details}</td>
                    </tr>
                `;
            }).join('');
        }

        // 9. Governance & Metadata
        if (document.getElementById('infoSelectedModel')) {
            document.getElementById('infoSelectedModel').textContent = mi.selected_model;
        }
        if (document.getElementById('infoTarget')) {
            document.getElementById('infoTarget').textContent = mi.target_column;
        }
        if (document.getElementById('infoSnapshotDate')) {
            document.getElementById('infoSnapshotDate').textContent = mi.training_date;
        }
        if (document.getElementById('infoVersion')) {
            document.getElementById('infoVersion').textContent = mi.model_version;
        }

    } catch (err) {
        console.error('Error loading supervised model summary:', err);
        showTableMessage(document.getElementById('modelComparisonTableBody'),
            `Could not load model metrics. ${String(err.message || err)}. Please refresh or retry.`, 9);
        ['cmTN','cmFP','cmFN','cmTP'].forEach(id => setTextIfPresent(id, 'N/A'));
    }
}

async function loadUnsupervisedBenchmark() {
    try {
        const res = await API.get('/api/segmentation/benchmark');
        if (!res.success || !res.data) {
            console.error('Failed to load unsupervised benchmark');
            return;
        }

        const data = res.data;
        const candidates = data.candidates || [];
        const tbody = document.getElementById('unsupervisedBenchmarkTbody');
        if (!tbody) return;

        if (document.getElementById('kpiUnsupervisedCoverage')) {
            const kMeans = candidates.find(c => c.id === 'kmeans');
            if (kMeans) {
                document.getElementById('kpiUnsupervisedCoverage').textContent = `${kMeans.coverage_percentage.toFixed(1)}%`;
            }
        }

        tbody.innerHTML = candidates.map(c => {
            const isSelected = c.name === data.selected_algorithm;
            const trophy = isSelected ? '<i class="bi bi-trophy-fill text-warning me-1"></i> ' : '';
            const rowStyle = isSelected ? 'style="background:#F3E8FF; font-weight:600;"' : '';
            
            let statusBadge = '<span class="badge badge-valid"><i class="bi bi-check-circle-fill"></i> Selected</span>';
            if (!isSelected) {
                if (c.is_valid) {
                    statusBadge = '<span class="badge badge-neutral">Valid Candidate</span>';
                } else {
                    statusBadge = `<span class="badge" style="background:#FEE2E2; color:#991B1B;" title="${c.rejection_reason || 'Rejected'}"><i class="bi bi-x-circle-fill"></i> Invalid</span>`;
                }
            }

            const silhouette = c.silhouette_display || (c.silhouette_score !== null ? safeMetric(c.silhouette_score, 4) : 'N/A');
            const davies = c.davies_bouldin_display || (c.davies_bouldin_index !== null ? safeMetric(c.davies_bouldin_index, 4) : 'N/A');
            const calinski = c.calinski_harabasz_display || (c.calinski_harabasz_index !== null ? safeMetric(c.calinski_harabasz_index, 1) : 'N/A');
            const runtime = c.runtime_ms !== undefined ? safeMetric(c.runtime_ms, 1) : '-';

            return `
                <tr ${rowStyle} style="cursor:pointer;" title="Click to highlight ${c.name}">
                    <td>${trophy}<strong>${c.name}</strong></td>
                    <td style="font-size:11px; color:var(--text-muted);">${c.family}</td>
                    <td class="text-center">${c.clusters_found}</td>
                    <td class="text-center">${formatNumber(c.noise_count)} (${safeMetric(c.noise_percentage, 1)}%)</td>
                    <td class="text-center"><strong>${safeMetric(c.coverage_percentage, 1)}%</strong></td>
                    <td class="text-center"><code>${silhouette}</code></td>
                    <td class="text-center"><code>${davies}</code></td>
                    <td class="text-center"><code>${calinski}</code></td>
                    <td class="text-center">${runtime}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }).join('');

        tbody.querySelectorAll('tr').forEach(row => {
            row.addEventListener('click', () => {
                tbody.querySelectorAll('tr').forEach(r => {
                    r.style.background = '';
                    r.style.fontWeight = '';
                });
                row.style.background = '#F3E8FF';
                row.style.fontWeight = '600';
            });
        });

    } catch (err) {
        console.error('Error loading unsupervised benchmark:', err);
        showTableMessage(document.getElementById('unsupervisedBenchmarkTbody'),
            `Could not load clustering benchmark. ${String(err.message || err)}. Please refresh or retry.`, 10);
    }
}

async function loadKEvaluationCharts() {
    try {
        const res = await API.get('/api/segmentation/k-evaluation');
        if (!res.success || !res.data) return;

        const evalData = res.data;
        const kValues = evalData.map(d => `K=${d.k}`);
        const inertias = evalData.map(d => Math.round(d.inertia));
        const silhouettes = evalData.map(d => d.silhouette_score);
        const davies = evalData.map(d => d.davies_bouldin);

        // 1. Elbow Method Chart (Inertia)
        if (document.getElementById('elbowCurveChart')) {
            if (elbowChartInstance) elbowChartInstance.destroy();
            const ctx = document.getElementById('elbowCurveChart').getContext('2d');
            elbowChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: kValues,
                    datasets: [{
                        label: 'Inertia (Within-Cluster Sum of Squares)',
                        data: inertias,
                        borderColor: '#0D63F3',
                        backgroundColor: 'rgba(13, 99, 243, 0.1)',
                        fill: true,
                        tension: 0.3,
                        pointBackgroundColor: '#0D63F3',
                        pointRadius: 5,
                        pointHoverRadius: 7
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10.5 } } },
                        tooltip: {
                            callbacks: {
                                label: ctx => `Inertia: ${formatNumber(ctx.raw)}`
                            }
                        }
                    },
                    scales: {
                        y: { title: { display: true, text: 'Inertia (WCSS)', font: { size: 10 } }, grid: { color: '#F1F5F9' } },
                        x: { grid: { color: '#F1F5F9' } }
                    }
                }
            });
        }

        // 2. Silhouette & Davies-Bouldin Chart
        if (document.getElementById('silhouetteCurveChart')) {
            if (silhouetteChartInstance) silhouetteChartInstance.destroy();
            const ctx = document.getElementById('silhouetteCurveChart').getContext('2d');
            silhouetteChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: kValues,
                    datasets: [
                        {
                            label: 'Silhouette Score (Higher is better)',
                            data: silhouettes,
                            borderColor: '#8547F5',
                            backgroundColor: 'transparent',
                            tension: 0.3,
                            pointBackgroundColor: '#8547F5',
                            pointRadius: 5,
                            yAxisID: 'y'
                        },
                        {
                            label: 'Davies-Bouldin Index (Lower is better)',
                            data: davies,
                            borderColor: '#FFA726',
                            borderDash: [4, 4],
                            backgroundColor: 'transparent',
                            tension: 0.3,
                            pointBackgroundColor: '#FFA726',
                            pointRadius: 5,
                            yAxisID: 'y1'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top', labels: { boxWidth: 12, font: { size: 10.5 } } }
                    },
                    scales: {
                        y: {
                            type: 'linear',
                            display: true,
                            position: 'left',
                            title: { display: true, text: 'Silhouette Score', font: { size: 10 } },
                            grid: { color: '#F1F5F9' }
                        },
                        y1: {
                            type: 'linear',
                            display: true,
                            position: 'right',
                            title: { display: true, text: 'Davies-Bouldin', font: { size: 10 } },
                            grid: { drawOnChartArea: false }
                        },
                        x: { grid: { color: '#F1F5F9' } }
                    }
                }
            });
        }

    } catch (err) {
        console.error('Error loading K-evaluation charts:', err);
    }
}

function setupRetrainHandler() {
    const btn = document.getElementById('retrainModelBtn');
    const icon = document.getElementById('retrainIcon');
    const text = document.getElementById('retrainText');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        icon.classList.add('spinner');
        text.textContent = 'Retraining 5 Models...';

        try {
            const res = await API.post('/api/model-quality/retrain');
            if (res.success) {
                alert('Models successfully retrained and evaluated on held-out test split!');
                await loadSupervisedModelSummary();
            } else {
                alert('Retraining encountered an issue: ' + (res.error || 'Unknown error'));
            }
        } catch (err) {
            alert('Error during model retraining: ' + err.message);
        } finally {
            btn.disabled = false;
            icon.classList.remove('spinner');
            text.textContent = 'Retrain Models';
        }
    });
}

function setupClusterBenchmarkHandler() {
    const btn = document.getElementById('runClusteringBenchmarkBtn');
    const icon = document.getElementById('clusterBenchIcon');
    const text = document.getElementById('clusterBenchText');
    if (!btn) return;

    btn.addEventListener('click', async () => {
        btn.disabled = true;
        icon.classList.add('spinner');
        text.textContent = 'Benchmarking 5 Algorithms...';

        try {
            // Segmentation benchmark endpoint can be called with force refresh
            const res = await API.get('/api/segmentation/benchmark?force=true');
            if (res.success) {
                alert('Unsupervised clustering benchmark completed successfully across all 5 algorithms!');
                await loadUnsupervisedBenchmark();
                await loadKEvaluationCharts();
            } else {
                alert('Benchmarking issue: ' + (res.error || 'Unknown error'));
            }
        } catch (err) {
            alert('Error during clustering benchmark: ' + err.message);
        } finally {
            btn.disabled = false;
            icon.classList.remove('spinner');
            text.textContent = 'Re-Benchmark Clusters';
        }
    });
}
