/**
 * Workforce Intelligence — Model Performance & Data Quality Controller
 */
document.addEventListener('DOMContentLoaded', async () => {
    await loadModelQualitySummary();
    setupRetrainHandler();
});

async function loadModelQualitySummary() {
    try {
        const res = await API.get('/api/model-quality/summary');
        if (!res.success) {
            console.error('Failed to load model quality summary');
            return;
        }

        const ev = res.evaluation;
        const ds = res.dataset_summary;
        const dq = res.data_quality_checks;
        const mi = res.model_info;

        // 1. Top 4 KPIs
        document.getElementById('kpiTrainRecords').textContent = formatNumber(ev.training_records);
        document.getElementById('kpiTestRecords').textContent = formatNumber(ev.test_records);
        document.getElementById('kpiPositiveClass').textContent = formatNumber(ev.positive_class);
        document.getElementById('kpiPositivePct').textContent = `${ev.positive_pct}% of population`;
        document.getElementById('kpiNegativeClass').textContent = formatNumber(ev.negative_class);
        document.getElementById('kpiNegativePct').textContent = `${ev.negative_pct}% of population`;

        // 2. Model Comparison Table
        const tbody = document.getElementById('modelComparisonTableBody');
        tbody.innerHTML = (ev.model_comparison || []).map(m => {
            const isSelected = m.model_name === ev.selected_model;
            const trophy = isSelected ? '<i class="bi bi-trophy-fill text-warning me-1"></i> ' : '';
            const rowClass = isSelected ? 'style="background:#EBF3FE; font-weight:600;"' : '';
            return `
                <tr ${rowClass}>
                    <td>${trophy}<strong>${m.model_name}</strong></td>
                    <td>${m.accuracy.toFixed(3)}</td>
                    <td>${m.precision.toFixed(3)}</td>
                    <td>${m.recall.toFixed(3)}</td>
                    <td><strong>${m.f1_score.toFixed(3)}</strong></td>
                    <td>${m.roc_auc.toFixed(3)}</td>
                    <td><strong style="color:var(--primary-blue);">${m.pr_auc.toFixed(3)}</strong></td>
                </tr>
            `;
        }).join('');

        // 3. Confusion Matrix
        const cm = ev.confusion_matrix;
        document.getElementById('cmTN').textContent = formatNumber(cm.true_negative);
        document.getElementById('cmFP').textContent = formatNumber(cm.false_positive);
        document.getElementById('cmFN').textContent = formatNumber(cm.false_negative);
        document.getElementById('cmTP').textContent = formatNumber(cm.true_positive);

        // 4. ROC Curve Chart
        const roc = ev.roc_curve;
        document.getElementById('rocAucBadge').textContent = `AUC = ${roc.auc}`;
        renderChart('rocCurveChart', {
            type: 'line',
            data: {
                labels: roc.fpr.map(v => v.toFixed(2)),
                datasets: [
                    {
                        label: 'ROC Curve',
                        data: roc.tpr,
                        borderColor: '#0D63F3',
                        backgroundColor: 'rgba(13, 99, 243, 0.08)',
                        fill: true,
                        tension: 0.2,
                        pointRadius: 0
                    },
                    {
                        label: 'Random Baseline',
                        data: roc.fpr,
                        borderColor: '#94A3B8',
                        borderDash: [5, 5],
                        fill: false,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'False Positive Rate' }, grid: { color: '#F1F5F9' } },
                    y: { title: { display: true, text: 'True Positive Rate' }, beginAtZero: true, max: 1.0, grid: { color: '#F1F5F9' } }
                }
            }
        });

        // 5. Precision-Recall Curve Chart
        const pr = ev.pr_curve;
        document.getElementById('prAucBadge').textContent = `PR-AUC = ${pr.pr_auc}`;
        renderChart('prCurveChart', {
            type: 'line',
            data: {
                labels: pr.recall.map(v => v.toFixed(2)),
                datasets: [{
                    label: 'Precision-Recall',
                    data: pr.precision,
                    borderColor: '#FFA726',
                    backgroundColor: 'rgba(255, 167, 38, 0.1)',
                    fill: true,
                    tension: 0.2,
                    pointRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { title: { display: true, text: 'Recall' }, grid: { color: '#F1F5F9' } },
                    y: { title: { display: true, text: 'Precision' }, beginAtZero: true, max: 1.0, grid: { color: '#F1F5F9' } }
                }
            }
        });

        // 6. Feature Importance Chart (Horizontal Bar)
        const fi = ev.feature_importance || [];
        renderChart('featureImportanceChart', {
            type: 'bar',
            data: {
                labels: fi.slice(0, 8).map(item => item.feature),
                datasets: [{
                    label: 'Importance Weight',
                    data: fi.slice(0, 8).map(item => item.importance),
                    backgroundColor: '#3B82F6',
                    borderRadius: 4
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { beginAtZero: true, grid: { color: '#F1F5F9' } },
                    y: { grid: { display: false } }
                }
            }
        });

        // 7. Risk Score Distribution (Probabilities Bar)
        const rsd = ev.risk_score_distribution || [];
        renderChart('riskScoreDistChart', {
            type: 'bar',
            data: {
                labels: rsd.map(r => r.range),
                datasets: [{
                    label: 'Employees',
                    data: rsd.map(r => r.count),
                    backgroundColor: '#60A5FA',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#F1F5F9' } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 8. Dataset Summary Table
        const dsTbody = document.getElementById('datasetSummaryTableBody');
        dsTbody.innerHTML = (ds || []).map(s => `
            <tr>
                <td><strong>${s.sheet_name}</strong></td>
                <td>${formatNumber(s.total_records)}</td>
                <td>${s.total_columns}</td>
                <td><span class="badge badge-valid"><i class="bi bi-check-circle-fill"></i> ${s.validation_status}</span></td>
            </tr>
        `).join('');

        // 9. Data Quality Checks Table
        const dqTbody = document.getElementById('qualityChecksTableBody');
        dqTbody.innerHTML = (dq || []).map(q => {
            const icon = q.passed ? '<i class="bi bi-check-circle-fill" style="color:var(--success-green);"></i>' : '<i class="bi bi-exclamation-triangle-fill" style="color:var(--warning-amber);"></i>';
            return `
                <tr>
                    <td><strong>${q.check_type}</strong></td>
                    <td>${icon} <span style="font-size:11px;">${q.result}</span></td>
                    <td style="color:var(--text-muted); font-size:10.5px;">${q.details}</td>
                </tr>
            `;
        }).join('');

        // 10. Model Information Card
        document.getElementById('infoSelectedModel').textContent = mi.selected_model;
        document.getElementById('infoTarget').textContent = mi.target_column;
        document.getElementById('infoHorizon').textContent = mi.prediction_horizon;
        document.getElementById('infoTrainCount').textContent = `${formatNumber(mi.training_records)} records`;
        document.getElementById('infoTestCount').textContent = `${formatNumber(mi.test_records)} records`;
        document.getElementById('infoSnapshotDate').textContent = mi.training_date;
        document.getElementById('infoVersion').textContent = mi.model_version;

    } catch (err) {
        console.error('Error loading model quality summary:', err);
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
                await loadModelQualitySummary();
            } else {
                alert('Retraining encountered an issue: ' + (res.error || 'Unknown error'));
            }
        } catch (err) {
            alert('Error during model retraining: ' + err.message);
        } finally {
            btn.disabled = false;
            icon.classList.remove('spinner');
            text.textContent = 'Retrain Model';
        }
    });
}
