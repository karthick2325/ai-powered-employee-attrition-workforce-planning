/**
 * Workforce Intelligence — AI Attrition Prediction Controller
 */
let currentPredPage = 1;
const PRED_PAGE_SIZE = 10;
let currentSelectedEmpId = null;
let predKpiRequestId = 0;
let predChartsRequestId = 0;
let predTableRequestId = 0;

function getPredictionFilters() {
    return {
        department: document.getElementById('filterPredDept')?.value || 'All',
        job_role: document.getElementById('filterPredRole')?.value || 'All',
        job_level: document.getElementById('filterPredLevel')?.value || 'All',
        location: document.getElementById('filterPredLocation')?.value || 'All',
        risk_level: document.getElementById('filterPredRisk')?.value || 'All'
    };
}

// Populate compact chart date chips from the existing header snapshot date.
function setPredictionSnapshotContext() {
    const leafTexts = Array.from(document.querySelectorAll('body *'))
        .filter((el) => el.children.length === 0)
        .map((el) => (el.textContent || '').trim());
    const dateText = leafTexts.find((text) =>
        /^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}$/.test(text)
    );
    const snapshot = dateText || 'Snapshot date';
    document.querySelectorAll('.prediction-snapshot-date').forEach((el) => {
        el.textContent = snapshot;
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    setPredictionSnapshotContext();
    await initFilterOptions();
    await loadPredictionKPIs();
    await loadPredictionCharts();
    await loadPredictionsTable();
    setupEventHandlers();
});

async function initFilterOptions() {
    try {
        const res = await API.get('/api/analytics/filters');
        if (!res.success || !res.filters) return;
        const f = res.filters;

        const populateSelect = (id, items) => {
            const select = document.getElementById(id);
            if (!select) return;
            items.forEach(item => {
                const opt = document.createElement('option');
                opt.value = item;
                opt.textContent = item;
                select.appendChild(opt);
            });
        };

        populateSelect('filterPredDept', f.departments);
        populateSelect('filterPredRole', f.job_roles);
        populateSelect('filterPredLevel', f.job_levels);
        populateSelect('filterPredLocation', f.locations);
    } catch (err) {
        console.error('Error initializing filter options:', err);
    }
}

async function loadPredictionKPIs() {
    const reqId = ++predKpiRequestId;
    try {
        const filters = getPredictionFilters();
        const res = await API.get('/api/prediction/kpis', filters);
        if (reqId !== predKpiRequestId || !res.success) return;
        const k = res.kpis;
        document.getElementById('kpiEligibleEmployees').textContent = formatNumber(k.eligible_employees);
        document.getElementById('kpiHighRiskCount').textContent = formatNumber(k.predicted_high_risk);
        document.getElementById('kpiHighRiskPct').textContent = `${k.predicted_high_risk_pct}% of eligible`;
        document.getElementById('kpiMedRiskCount').textContent = formatNumber(k.predicted_medium_risk);
        document.getElementById('kpiMedRiskPct').textContent = `${k.predicted_medium_risk_pct}% of eligible`;
        document.getElementById('kpiLowRiskCount').textContent = formatNumber(k.predicted_low_risk);
        document.getElementById('kpiLowRiskPct').textContent = `${k.predicted_low_risk_pct}% of eligible`;
        const baseEl = document.getElementById('kpiHistoricalBaseline');
        if (baseEl) baseEl.textContent = `${k.historical_attrition_pct || 5.79}%`;
        const modelEl = document.getElementById('kpiModelUsed');
        if (modelEl) modelEl.textContent = k.model_used;
    } catch (err) {
        if (reqId === predKpiRequestId) console.error('Error loading prediction KPIs:', err);
    }
}

async function loadPredictionCharts() {
    const reqId = ++predChartsRequestId;
    try {
        const filters = getPredictionFilters();
        // 1. Risk Distribution (Doughnut)
        const distRes = await API.get('/api/prediction/risk-distribution', filters);
        if (reqId === predChartsRequestId && distRes.success && distRes.risk_distribution) {
            const d = distRes.risk_distribution;
            renderChart('predRiskDistChart', {
                type: 'doughnut',
                data: {
                    labels: d.categories.map(c => `${c.level} (${c.percentage}%)`),
                    datasets: [{
                        data: d.categories.map(c => c.count),
                        backgroundColor: d.categories.map(c => c.color),
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '70%',
                    plugins: { legend: { position: 'bottom', labels: { boxWidth: 12 } } }
                }
            });
        }

        // 2. Average Risk Probability by Department (Bar)
        const deptRes = await API.get('/api/prediction/department-risk', filters);
        if (reqId === predChartsRequestId && deptRes.success && deptRes.department_risk) {
            const dr = deptRes.department_risk;
            renderChart('predDeptRiskChart', {
                type: 'bar',
                data: {
                    labels: dr.map(item => item.department),
                    datasets: [{
                        label: 'Average Risk Probability',
                        data: dr.map(item => item.avg_probability),
                        backgroundColor: '#F87171',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: { beginAtZero: true, max: 0.6, grid: { color: '#F1F5F9' } },
                        x: { grid: { display: false } }
                    }
                }
            });
        }

        // 3. Top Feature Importance (Horizontal Bar)
        const featRes = await API.get('/api/prediction/feature-importance');
        if (featRes.success && featRes.feature_importance) {
            const fi = featRes.feature_importance;
            renderChart('predFeatureImportanceChart', {
                type: 'bar',
                data: {
                    labels: fi.map(item => item.feature),
                    datasets: [{
                        label: 'Importance Weight',
                        data: fi.map(item => item.importance),
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
        }
    } catch (err) {
        console.error('Error loading prediction charts:', err);
    }
}

async function loadPredictionsTable(page = 1) {
    currentPredPage = page;
    const reqId = ++predTableRequestId;
    const tbody = document.getElementById('predTableBody');
    tbody.innerHTML = `<tr><td colspan="12" class="text-center p-4"><div class="spinner"></div></td></tr>`;

    try {
        const filters = getPredictionFilters();
        const search = document.getElementById('filterPredSearch')?.value;

        const res = await API.get('/api/prediction/employees', {
            ...filters,
            search: search,
            page: page,
            page_size: PRED_PAGE_SIZE
        });

        if (reqId !== predTableRequestId || !res.success) return;

        document.getElementById('predTableCountDisplay').textContent = 
            `Showing ${(res.page - 1) * res.page_size + 1} - ${Math.min(res.total_records, res.page * res.page_size)} of ${formatNumber(res.total_records)}`;

        if (res.records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="12" class="text-center p-4 text-muted">No predicted employees match the criteria.</td></tr>`;
            const body = document.getElementById('selectedEmpPanelBody');
            if (body) {
                body.innerHTML = `<div class="p-4 text-center text-muted">No employee selected or matching current filter criteria.</div>`;
            }
            const badge = document.getElementById('selectedEmpRiskBadge');
            if (badge) {
                badge.textContent = 'None';
                badge.className = 'card-badge';
            }
            currentSelectedEmpId = null;
            return;
        }

        tbody.innerHTML = res.records.map((emp, index) => {
            const riskClass = emp.risk_level === 'High' ? 'badge-high' : (emp.risk_level === 'Medium' ? 'badge-medium' : 'badge-low');
            return `
                <tr style="cursor:pointer;" onclick="selectEmployee('${emp.employee_id}')">
                    <td><strong>${emp.employee_id}</strong></td>
                    <td>${emp.employee_name}</td>
                    <td>${emp.department}</td>
                    <td>${emp.job_role}</td>
                    <td>${emp.tenure_months}m</td>
                    <td>${emp.overtime_hours}</td>
                    <td>${emp.job_satisfaction}</td>
                    <td>${emp.work_life_balance}</td>
                    <td>${emp.training_hours}</td>
                    <td><strong>${emp.risk_probability.toFixed(2)}</strong></td>
                    <td><span class="badge ${riskClass}">${emp.risk_level}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline" onclick="event.stopPropagation(); openEmployeeModal('${emp.employee_id}')" title="Full Profile">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        renderPredPagination(res.page, res.total_pages);

        // Auto-select first employee if none selected yet or current not in list
        const ids = res.records.map(r => r.employee_id);
        if (!currentSelectedEmpId || !ids.includes(currentSelectedEmpId)) {
            selectEmployee(res.records[0].employee_id);
        }
    } catch (err) {
        if (reqId === predTableRequestId) console.error('Error loading predictions table:', err);
    }
}

function renderPredPagination(page, totalPages) {
    document.getElementById('predPaginationInfo').textContent = `Page ${page} of ${formatNumber(totalPages)}`;
    const ctrl = document.getElementById('predPaginationControls');
    ctrl.innerHTML = '';

    const createBtn = (text, targetPage, disabled = false, active = false) => {
        const btn = document.createElement('button');
        btn.className = `page-btn ${active ? 'active' : ''}`;
        btn.disabled = disabled;
        btn.innerHTML = text;
        if (!disabled) {
            btn.onclick = () => loadPredictionsTable(targetPage);
        }
        return btn;
    };

    ctrl.appendChild(createBtn('&laquo;', page - 1, page <= 1));

    let start = Math.max(1, page - 2);
    let end = Math.min(totalPages, page + 2);

    for (let p = start; p <= end; p++) {
        ctrl.appendChild(createBtn(p, p, false, p === page));
    }

    ctrl.appendChild(createBtn('&raquo;', page + 1, page >= totalPages));
}

async function selectEmployee(empId) {
    currentSelectedEmpId = empId;
    const body = document.getElementById('selectedEmpPanelBody');
    const badge = document.getElementById('selectedEmpRiskBadge');

    try {
        const res = await API.get(`/api/prediction/employee/${empId}`);
        if (!res.success || !res.employee) return;
        const emp = res.employee;

        badge.textContent = `${emp.risk_level} Risk`;
        badge.className = `card-badge ${emp.risk_level === 'High' ? 'badge-high' : (emp.risk_level === 'Medium' ? 'badge-medium' : 'badge-low')}`;

        body.innerHTML = `
            <div class="emp-panel-header">
                <div class="emp-profile-left">
                    <div class="emp-avatar-lg">
                        <i class="bi bi-person-fill"></i>
                    </div>
                    <div class="emp-info-lg">
                        <h4>${emp.employee_name}</h4>
                        <p>${emp.job_role} &bull; ${emp.department} &bull; ${emp.location}</p>
                    </div>
                </div>
                <button class="btn btn-sm btn-outline" onclick="openEmployeeModal('${emp.employee_id}')">
                    <i class="bi bi-person-badge"></i> View Full
                </button>
            </div>

            <div class="emp-probability-box">
                <div>
                    <div class="emp-prob-label">Attrition Risk Probability (Next 6 Months)</div>
                    <div style="font-size:11.5px; color:var(--text-muted);">Threshold decision band: ${emp.risk_level} Risk</div>
                </div>
                <div class="emp-prob-num">${emp.risk_probability_pct}%</div>
            </div>

            <div class="emp-details-grid">
                <div class="emp-detail-item">
                    <i class="bi bi-clock-history"></i>
                    <div><span class="label">Tenure</span><span class="val">${emp.tenure_months} months</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-speedometer2"></i>
                    <div><span class="label">Monthly Overtime</span><span class="val">${emp.overtime_hours} hrs/mo</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-star-fill" style="color:var(--warning-amber);"></i>
                    <div><span class="label">Job Satisfaction</span><span class="val">${emp.job_satisfaction} / 5</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-heart-pulse-fill" style="color:var(--danger-red);"></i>
                    <div><span class="label">Work-Life Balance</span><span class="val">${emp.work_life_balance} / 5</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-mortarboard-fill"></i>
                    <div><span class="label">Training Hours</span><span class="val">${emp.training_hours} hrs</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-award-fill"></i>
                    <div><span class="label">Last Promotion</span><span class="val">${emp.months_since_last_promotion} mos ago</span></div>
                </div>
            </div>

            <div style="margin-top:16px;">
                <h5 style="font-size:12.5px; font-weight:600; color:var(--navy-text); margin-bottom:8px;">Top Contributing Risk Factors</h5>
                ${(emp.top_factors || []).map(f => `
                    <div class="factor-bar-item">
                        <div class="factor-bar-header">
                            <span>${f.factor}</span>
                            <span style="font-size:11px; color:var(--text-muted);">${f.description}</span>
                        </div>
                        <div class="factor-progress-bg">
                            <div class="factor-progress-fill" style="width:${Math.min(100, f.impact * 260)}%;"></div>
                        </div>
                    </div>
                `).join('')}
            </div>

            <div style="margin-top:18px; background:#F8FAFC; border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
                <h5 style="font-size:12px; font-weight:600; color:var(--navy-text); margin-bottom:8px; display:flex; align-items:center; gap:6px;">
                    <i class="bi bi-lightbulb-fill" style="color:var(--warning-amber);"></i> Suggested Retention Actions
                </h5>
                <ul class="retention-list">
                    ${(emp.retention_actions || []).map((action, i) => `
                        <li class="retention-item">
                            <span class="retention-num">${i + 1}</span>
                            <span>${action}</span>
                        </li>
                    `).join('')}
                </ul>
            </div>
        `;
    } catch (err) {
        console.error('Error selecting employee:', err);
    }
}

function setupEventHandlers() {
    document.getElementById('applyPredFiltersBtn')?.addEventListener('click', () => {
        loadPredictionKPIs();
        loadPredictionCharts();
        loadPredictionsTable(1);
    });

    document.getElementById('resetPredFiltersBtn')?.addEventListener('click', () => {
        document.getElementById('filterPredDept').value = 'All';
        document.getElementById('filterPredRole').value = 'All';
        document.getElementById('filterPredLevel').value = 'All';
        document.getElementById('filterPredLocation').value = 'All';
        document.getElementById('filterPredRisk').value = 'All';
        document.getElementById('filterPredSearch').value = '';
        loadPredictionKPIs();
        loadPredictionCharts();
        loadPredictionsTable(1);
    });

    document.getElementById('filterPredSearch')?.addEventListener('input', () => {
        loadPredictionsTable(1);
    });
}
