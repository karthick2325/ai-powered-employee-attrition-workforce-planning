/**
 * Workforce Intelligence — Workforce Planning & Exit Analysis Controller
 */
let currentNoticePage = 1;
const NOTICE_PAGE_SIZE = 8;

document.addEventListener('DOMContentLoaded', async () => {
    await loadWorkforceKPIs();
    await loadWorkforceCharts();
    await loadDepartmentExitTable();
    await loadNoticeEmployeesTable();
    await loadWorkforceInsights();
    setupScenarioPlanner();
});

async function loadWorkforceKPIs() {
    try {
        const res = await API.get('/api/workforce/kpis');
        if (!res.success) return;
        const k = res.kpis;
        document.getElementById('kpiWfCurrent').textContent = formatNumber(k.current_headcount);
        document.getElementById('kpiWfNotice').textContent = formatNumber(k.employees_serving_notice);
        document.getElementById('kpiWfPredicted').textContent = formatNumber(k.expected_additional_exits);
        document.getElementById('kpiWfTarget').textContent = formatNumber(k.target_headcount);
        document.getElementById('kpiWfOpenReqs').textContent = formatNumber(k.open_requisitions);
        document.getElementById('kpiWfGap').textContent = formatNumber(k.remaining_staffing_gap);

        // Pre-populate scenario planner controls with dataset values
        document.getElementById('spCurrentSlider').value = k.current_headcount;
        document.getElementById('spCurrentInput').value = k.current_headcount;
        document.getElementById('spExitsSlider').value = k.expected_additional_exits;
        document.getElementById('spExitsInput').value = k.expected_additional_exits;
        document.getElementById('spOpenSlider').value = k.open_requisitions;
        document.getElementById('spOpenInput').value = k.open_requisitions;
        document.getElementById('spTargetSlider').value = k.target_headcount;
        document.getElementById('spTargetInput').value = k.target_headcount;

        calculateScenarioLevers();
    } catch (err) {
        console.error('Error loading workforce KPIs:', err);
    }
}

async function loadWorkforceCharts() {
    try {
        // 1. Headcount Analysis by Department (Grouped Bar)
        const hcRes = await API.get('/api/workforce/headcount-analysis');
        if (hcRes.success && hcRes.data) {
            const d = hcRes.data;
            renderChart('wfHeadcountChart', {
                type: 'bar',
                data: {
                    labels: d.departments,
                    datasets: [
                        { label: 'Current Headcount', data: d.current_headcount, backgroundColor: '#3B82F6', borderRadius: 4 },
                        { label: 'Target Headcount', data: d.target_headcount, backgroundColor: '#22B573', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top', labels: { boxWidth: 12 } } },
                    scales: { y: { beginAtZero: true, grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                }
            });
        }

        // 2. Expected Exits Donut
        const exitsRes = await API.get('/api/workforce/expected-exits-breakdown');
        if (exitsRes.success && exitsRes.data) {
            const d = exitsRes.data;
            renderChart('wfExpectedExitsDonut', {
                type: 'doughnut',
                data: {
                    labels: d.categories.map(c => `${c.label} (${c.pct}%)`),
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

        // 3. Monthly Expected Exits (Stacked Bar)
        const mRes = await API.get('/api/workforce/monthly-exits');
        if (mRes.success && mRes.data) {
            const d = mRes.data;
            renderChart('wfMonthlyExitsChart', {
                type: 'bar',
                data: {
                    labels: d.months,
                    datasets: [
                        { label: 'Notice Period Exits', data: d.notice_exits, backgroundColor: '#F87171', borderRadius: 4 },
                        { label: 'Predicted Exits', data: d.predicted_exits, backgroundColor: '#FFA726', borderRadius: 4 }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { position: 'top', labels: { boxWidth: 12 } } },
                    scales: {
                        x: { stacked: true, grid: { display: false } },
                        y: { stacked: true, beginAtZero: true, grid: { color: '#F1F5F9' } }
                    }
                }
            });
        }

        // 4. Open Job Requisitions by Department
        const reqRes = await API.get('/api/workforce/open-requisitions');
        if (reqRes.success && reqRes.data) {
            const d = reqRes.data;
            renderChart('wfOpenReqsChart', {
                type: 'bar',
                data: {
                    labels: d.departments,
                    datasets: [{
                        label: 'Open Requisitions',
                        data: d.open_positions,
                        backgroundColor: '#3B82F6',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                }
            });
        }

        // 5. Notice Period Distribution (Days Remaining)
        const distRes = await API.get('/api/workforce/notice-distribution');
        if (distRes.success && distRes.data) {
            const d = distRes.data;
            renderChart('wfNoticeDistChart', {
                type: 'bar',
                data: {
                    labels: d.labels,
                    datasets: [{
                        label: 'Employees',
                        data: d.values,
                        backgroundColor: '#8547F5',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: { y: { beginAtZero: true, grid: { color: '#F1F5F9' } }, x: { grid: { display: false } } }
                }
            });
        }
    } catch (err) {
        console.error('Error loading workforce charts:', err);
    }
}

async function loadDepartmentExitTable() {
    try {
        const res = await API.get('/api/workforce/department-table');
        if (!res.success || !res.data) return;
        const d = res.data;

        const tbody = document.getElementById('wfDeptTableBody');
        let html = d.rows.map(r => `
            <tr>
                <td><strong>${r.department}</strong></td>
                <td>${formatNumber(r.current_headcount)}</td>
                <td style="color:var(--danger-red);">${formatNumber(r.serving_notice)}</td>
                <td style="color:var(--warning-amber);">${formatNumber(r.predicted_exits)}</td>
                <td><strong>${formatNumber(r.total_expected_exits)}</strong></td>
                <td>${formatNumber(r.target_headcount)}</td>
                <td style="color:var(--primary-blue);">${formatNumber(r.open_positions)}</td>
                <td style="color:var(--danger-red); font-weight:700;">${formatNumber(r.remaining_gap)}</td>
            </tr>
        `).join('');

        const t = d.totals;
        html += `
            <tr style="background:#F8FAFD; font-weight:700; border-top:2px solid var(--border-color);">
                <td>Total</td>
                <td>${formatNumber(t.current_headcount)}</td>
                <td style="color:var(--danger-red);">${formatNumber(t.serving_notice)}</td>
                <td style="color:var(--warning-amber);">${formatNumber(t.predicted_exits)}</td>
                <td>${formatNumber(t.total_expected_exits)}</td>
                <td>${formatNumber(t.target_headcount)}</td>
                <td style="color:var(--primary-blue);">${formatNumber(t.open_positions)}</td>
                <td style="color:var(--danger-red); font-weight:800;">${formatNumber(t.remaining_gap)}</td>
            </tr>
        `;

        tbody.innerHTML = html;
    } catch (err) {
        console.error('Error loading department exit table:', err);
    }
}

async function loadNoticeEmployeesTable(page = 1) {
    currentNoticePage = page;
    const tbody = document.getElementById('noticeTableBody');
    tbody.innerHTML = `<tr><td colspan="7" class="text-center p-3"><div class="spinner"></div></td></tr>`;

    try {
        const search = document.getElementById('noticeSearchInput')?.value;
        const res = await API.get('/api/workforce/notice-employees', {
            search: search,
            page: page,
            page_size: NOTICE_PAGE_SIZE
        });

        if (!res.success) return;

        if (res.records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="text-center p-3 text-muted">No notice records match the query.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.records.map(emp => `
            <tr>
                <td><strong>${emp.employee_id}</strong></td>
                <td>${emp.employee_name}</td>
                <td>${emp.department}</td>
                <td>${emp.notice_start_date}</td>
                <td>${emp.expected_last_working_day}</td>
                <td><strong>${emp.days_remaining}</strong></td>
                <td><span class="badge badge-active">${emp.notice_status}</span></td>
            </tr>
        `).join('');

        document.getElementById('noticePaginationInfo').textContent = `Page ${res.page} of ${res.total_pages}`;
        const ctrl = document.getElementById('noticePaginationControls');
        ctrl.innerHTML = '';

        const createBtn = (text, targetPage, disabled = false, active = false) => {
            const btn = document.createElement('button');
            btn.className = `page-btn ${active ? 'active' : ''}`;
            btn.disabled = disabled;
            btn.innerHTML = text;
            if (!disabled) {
                btn.onclick = () => loadNoticeEmployeesTable(targetPage);
            }
            return btn;
        };

        ctrl.appendChild(createBtn('&laquo;', res.page - 1, res.page <= 1));
        for (let p = Math.max(1, res.page - 1); p <= Math.min(res.total_pages, res.page + 1); p++) {
            ctrl.appendChild(createBtn(p, p, false, p === res.page));
        }
        ctrl.appendChild(createBtn('&raquo;', res.page + 1, res.page >= res.total_pages));
    } catch (err) {
        console.error('Error loading notice employees table:', err);
    }
}

async function loadWorkforceInsights() {
    try {
        const res = await API.get('/api/workforce/insights');
        if (!res.success || !res.insights) return;
        const list = document.getElementById('wfInsightsList');
        list.innerHTML = res.insights.map(item => `
            <div class="insight-item">
                <div class="insight-icon kpi-icon-${item.color}">
                    <i class="bi ${item.icon}"></i>
                </div>
                <div>${item.text}</div>
            </div>
        `).join('');
    } catch (err) {
        console.error('Error loading workforce insights:', err);
    }
}

function setupScenarioPlanner() {
    const bindDualInput = (sliderId, inputId) => {
        const slider = document.getElementById(sliderId);
        const input = document.getElementById(inputId);
        if (!slider || !input) return;

        slider.addEventListener('input', () => {
            input.value = slider.value;
            calculateScenarioLevers();
        });

        input.addEventListener('input', () => {
            slider.value = input.value;
            calculateScenarioLevers();
        });
    };

    bindDualInput('spCurrentSlider', 'spCurrentInput');
    bindDualInput('spExitsSlider', 'spExitsInput');
    bindDualInput('spOpenSlider', 'spOpenInput');
    bindDualInput('spTargetSlider', 'spTargetInput');

    document.getElementById('noticeSearchInput')?.addEventListener('input', () => {
        loadNoticeEmployeesTable(1);
    });
}

function calculateScenarioLevers() {
    const current = Number(document.getElementById('spCurrentInput')?.value || 50000);
    const exits = Number(document.getElementById('spExitsInput')?.value || 3412);
    const open = Number(document.getElementById('spOpenInput')?.value || 1200);
    const target = Number(document.getElementById('spTargetInput')?.value || 55000);

    // Known notice is fixed 2,028 from workbook
    const knownNotice = 2028;

    // Formula: Projected = Current - Notice - Predicted + Open
    const projected = current - knownNotice - exits + open;
    const gap = Math.max(0, target - projected);

    document.getElementById('spProjectedStaff').textContent = formatNumber(projected);
    document.getElementById('spNewGap').textContent = formatNumber(gap);
}
