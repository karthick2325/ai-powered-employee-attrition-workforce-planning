/**
 * Workforce Intelligence — Employee & Department Analytics Controller
 */
let currentEmpPage = 1;
const EMP_PAGE_SIZE = 10;
let kpiRequestId = 0;
let chartsRequestId = 0;
let empTableRequestId = 0;

function getAnalyticsFilters() {
    return {
        department: document.getElementById('filterDept')?.value || 'All',
        job_role: document.getElementById('filterRole')?.value || 'All',
        job_level: document.getElementById('filterLevel')?.value || 'All',
        location: document.getElementById('filterLocation')?.value || 'All',
        employment_type: document.getElementById('filterEmpType')?.value || 'All',
        max_tenure: document.getElementById('filterTenure')?.value
    };
}

document.addEventListener('DOMContentLoaded', async () => {
    await initFilterOptions();
    await loadKPIs();
    await loadDepartmentCharts();
    await loadEmployeesTable();
    await loadDepartmentComparison();
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

        populateSelect('filterDept', f.departments);
        populateSelect('filterRole', f.job_roles);
        populateSelect('filterLevel', f.job_levels);
        populateSelect('filterLocation', f.locations);
        populateSelect('filterEmpType', f.employment_types);

        // Also populate comparison department selectors
        const comp1 = document.getElementById('compareDept1');
        const comp2 = document.getElementById('compareDept2');
        if (comp1 && comp2) {
            comp1.innerHTML = '';
            comp2.innerHTML = '';
            f.departments.forEach((d, idx) => {
                const opt1 = new Option(d, d, false, idx === 0);
                const opt2 = new Option(d, d, false, idx === 1);
                comp1.add(opt1);
                comp2.add(opt2);
            });
        }

        // Set tenure slider range
        if (f.tenure_range) {
            const slider = document.getElementById('filterTenure');
            const minSpan = document.getElementById('tenureMinVal');
            const maxSpan = document.getElementById('tenureMaxVal');
            slider.min = f.tenure_range.min;
            slider.max = f.tenure_range.max;
            slider.value = f.tenure_range.max;
            minSpan.textContent = f.tenure_range.min;
            maxSpan.textContent = f.tenure_range.max;
            document.getElementById('tenureValDisplay').textContent = `${f.tenure_range.min} - ${f.tenure_range.max}`;
        }
    } catch (err) {
        console.error('Error initializing filter options:', err);
    }
}

async function loadKPIs() {
    const reqId = ++kpiRequestId;
    try {
        const filters = getAnalyticsFilters();
        const res = await API.get('/api/analytics/kpis', filters);
        if (reqId !== kpiRequestId || !res.success) return;
        const k = res.kpis;
        document.getElementById('kpiTotalEmp').textContent = formatNumber(k.total_employees);
        document.getElementById('kpiTotalDepts').textContent = k.total_departments;
        document.getElementById('kpiJobRoles').textContent = k.unique_job_roles;
        document.getElementById('kpiAvgTenure').textContent = `${k.average_tenure_months} mos`;
        document.getElementById('kpiAvgSatisfaction').textContent = `${k.average_job_satisfaction} / 5`;
        document.getElementById('kpiAvgTraining').textContent = `${k.average_training_hours} hrs`;
        document.getElementById('kpiAvgOvertime').textContent = `${k.average_overtime_hours} hrs`;
    } catch (err) {
        if (reqId === kpiRequestId) console.error('Error loading analytics KPIs:', err);
    }
}

async function loadDepartmentCharts() {
    const reqId = ++chartsRequestId;
    try {
        const filters = getAnalyticsFilters();
        const res = await API.get('/api/analytics/charts', filters);
        if (reqId !== chartsRequestId || !res.success) return;

        const c = res.charts || {};
        const headcount = c.headcount || {};
        const departments = headcount.departments || [];
        const values = (series, expectedLength = departments.length) => {
            const source = Array.isArray(series) ? series : [];
            return Array.from({ length: expectedLength }, (_, i) => {
                const value = source[i];
                if (value === null || value === undefined || value === '' || !Number.isFinite(Number(value))) return null;
                return Number(value);
            });
        };
        const byDepartment = (series, targetDepartments = departments) => {
            const sourceDepartments = series?.departments || [];
            const sourceValues = Array.isArray(series?.values) ? series.values : [];
            const lookup = new Map(sourceDepartments.map((dept, i) => [dept, sourceValues[i]]));
            return targetDepartments.map(dept => {
                const value = lookup.get(dept);
                return value === null || value === undefined || value === '' || !Number.isFinite(Number(value)) ? null : Number(value);
            });
        };
        const aligned = c.attrition_rate_aligned || {};
        const attritionMap = new Map((c.attrition_rate?.departments || []).map((dept, i) => [dept, c.attrition_rate?.rates?.[i]]));
        const attritionValues = departments.map((dept, i) => {
            const raw = aligned.departments?.length ? aligned.rates?.[i] : attritionMap.get(dept);
            return raw === null || raw === undefined || raw === '' || !Number.isFinite(Number(raw)) ? null : Number(raw);
        });
        const gender = c.gender_by_department || { available: false };
        const numberText = value => value === null || value === undefined || !Number.isFinite(Number(value))
            ? 'N/A' : Number(value).toLocaleString(undefined, { maximumFractionDigits: 1 });
        const scoreText = value => value === null || value === undefined || !Number.isFinite(Number(value))
            ? 'N/A' : `${Number(value).toFixed(1)} / 5`;

        const emptyStatePlugin = {
            id: 'analyticsEmptyState',
            afterDraw(chart) {
                const labels = chart.data?.labels || [];
                const hasValues = (chart.data?.datasets || []).some(ds => (ds.data || []).some(v => v !== null && v !== undefined && Number.isFinite(Number(v))));
                if (labels.length && hasValues) return;
                const { ctx, chartArea } = chart;
                if (!chartArea) return;
                ctx.save();
                ctx.fillStyle = '#64748B';
                ctx.font = '500 13px Inter, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText('No data for the selected filters', (chartArea.left + chartArea.right) / 2, (chartArea.top + chartArea.bottom) / 2);
                ctx.restore();
            }
        };
        const sharedOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { display: true, position: 'top', labels: { usePointStyle: true, boxWidth: 9, padding: 12 } },
                tooltip: {
                    enabled: true,
                    callbacks: {
                        label: context => {
                            const raw = context.parsed?.y ?? context.raw;
                            const label = context.dataset.label || '';
                            if (raw === null || raw === undefined || !Number.isFinite(Number(raw))) return `${label}: N/A`;
                            const val = Number(raw).toLocaleString(undefined, { maximumFractionDigits: 1 });
                            return `${label}: ${val}${label.includes('(%)') ? '%' : ''}`;
                        }
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#64748B', maxRotation: 30, minRotation: 0 } },
                y: { beginAtZero: true, grid: { color: '#F1F5F9' }, ticks: { color: '#64748B' } }
            }
        };
        const plugins = [emptyStatePlugin];

        // 1. Department headcount columns + attrition line. Gender is shown only in this chart's tooltip.
        renderChart('chartDeptHeadcountAttrition', {
            type: 'bar',
            data: { labels: departments, datasets: [
                { type: 'bar', label: 'Headcount (employees)', data: values(headcount.values), yAxisID: 'y', backgroundColor: '#397FF5', borderColor: '#397FF5', borderRadius: 5, maxBarThickness: 38, order: 2 },
                { type: 'line', label: 'Attrition Rate (6M, %)', data: attritionValues, yAxisID: 'y1', borderColor: '#E34B65', backgroundColor: '#E34B65', pointBackgroundColor: '#E34B65', pointBorderColor: '#FFFFFF', pointBorderWidth: 2, pointRadius: 4, pointHoverRadius: 6, borderWidth: 3, tension: 0.25, fill: false, spanGaps: false, order: 1 }
            ] },
            options: {
                ...sharedOptions, plugins: { ...sharedOptions.plugins, tooltip: { ...sharedOptions.plugins.tooltip, callbacks: {
                    ...sharedOptions.plugins.tooltip.callbacks,
                    afterBody: items => {
                        if (!items?.length) return [];
                        const idx = items[0].dataIndex;
                        if (!gender.available) return ['Gender breakdown: N/A (Gender column unavailable)'];
                        return [
                            `Male employees: ${numberText(gender.male?.[idx])}`,
                            `Female employees: ${numberText(gender.female?.[idx])}`,
                            `Non-disclosed / other: ${numberText(gender.non_disclosed?.[idx])}`,
                            ...(Number(gender.unknown?.[idx] || 0) > 0 ? [`Unknown / missing: ${numberText(gender.unknown[idx])}`] : [])
                        ];
                    }
                } } },
                scales: {
                    ...sharedOptions.scales,
                    y: { ...sharedOptions.scales.y, position: 'left', title: { display: true, text: 'Employees' }, ticks: { color: '#397FF5', callback: v => Number(v).toLocaleString() } },
                    y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Attrition rate (%)' }, ticks: { color: '#E34B65', callback: v => `${v}%` } }
                }
            }, plugins
        });

        // 2. Performance and satisfaction share the same 1–5 scale; WLB is in the tooltip.
        const performanceValues = byDepartment(c.performance);
        const satisfactionValues = byDepartment(c.satisfaction);
        const wlbValues = byDepartment(c.work_life_balance);
        renderChart('chartDeptPerformanceSatisfaction', {
            type: 'bar', data: { labels: departments, datasets: [
                { label: 'Performance Rating (out of 5)', data: performanceValues, backgroundColor: '#397FF5', borderRadius: 5, maxBarThickness: 26 },
                { label: 'Job Satisfaction (out of 5)', data: satisfactionValues, backgroundColor: '#FFA726', borderRadius: 5, maxBarThickness: 26 }
            ] },
            options: { ...sharedOptions, plugins: { ...sharedOptions.plugins, tooltip: { ...sharedOptions.plugins.tooltip, callbacks: {
                ...sharedOptions.plugins.tooltip.callbacks,
                afterBody: items => items?.length ? [`Work-life balance: ${scoreText(wlbValues[items[0].dataIndex])}`] : []
            } } }, scales: { ...sharedOptions.scales, y: { ...sharedOptions.scales.y, min: 0, max: 5, ticks: { stepSize: 1 }, title: { display: true, text: 'Average score (1–5)' } } } }, plugins
        });

        // 3. Overtime and satisfaction trend helps flag a possible workload association, not causation.
        const overtimeValues = byDepartment(c.overtime);
        renderChart('chartDeptOvertimeSatisfaction', {
            type: 'bar', data: { labels: departments, datasets: [
                { type: 'bar', label: 'Overtime (hours/month)', data: overtimeValues, yAxisID: 'y', backgroundColor: '#8547F5', borderRadius: 5, maxBarThickness: 38, order: 2 },
                { type: 'line', label: 'Job Satisfaction (out of 5)', data: satisfactionValues, yAxisID: 'y1', borderColor: '#E34B65', backgroundColor: '#E34B65', pointBackgroundColor: '#E34B65', pointBorderColor: '#FFFFFF', pointBorderWidth: 2, pointRadius: 4, borderWidth: 3, tension: 0.25, fill: false, order: 1 }
            ] },
            options: { ...sharedOptions, plugins: { ...sharedOptions.plugins, tooltip: { ...sharedOptions.plugins.tooltip, callbacks: {
                ...sharedOptions.plugins.tooltip.callbacks,
                afterBody: items => items?.length ? [
                    `Performance rating: ${scoreText(performanceValues[items[0].dataIndex])}`,
                    `Work-life balance: ${scoreText(wlbValues[items[0].dataIndex])}`,
                    `Training hours (last 12M): ${numberText(byDepartment(c.training)[items[0].dataIndex])}`
                ] : []
            } } }, scales: {
                ...sharedOptions.scales,
                y: { ...sharedOptions.scales.y, position: 'left', title: { display: true, text: 'Overtime hours / month' } },
                y1: { beginAtZero: true, min: 0, max: 5, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Satisfaction (1–5)' }, ticks: { stepSize: 1, color: '#E34B65' } }
            } }, plugins
        });

        // 4. Training and tenure, each with its own clearly labelled axis.
        const trainingValues = byDepartment(c.training);
        const tenureValues = byDepartment(c.tenure);
        renderChart('chartDeptTrainingTenure', {
            type: 'bar', data: { labels: departments, datasets: [
                { type: 'bar', label: 'Training (hours / last 12M)', data: trainingValues, yAxisID: 'y', backgroundColor: '#00A6C7', borderRadius: 5, maxBarThickness: 38, order: 2 },
                { type: 'line', label: 'Average Tenure (months)', data: tenureValues, yAxisID: 'y1', borderColor: '#10B981', backgroundColor: '#10B981', pointBackgroundColor: '#10B981', pointBorderColor: '#FFFFFF', pointBorderWidth: 2, pointRadius: 4, borderWidth: 3, tension: 0.25, fill: false, order: 1 }
            ] },
            options: { ...sharedOptions, plugins: { ...sharedOptions.plugins, tooltip: { ...sharedOptions.plugins.tooltip, callbacks: {
                ...sharedOptions.plugins.tooltip.callbacks,
                afterBody: items => items?.length ? [
                    `Performance rating: ${scoreText(performanceValues[items[0].dataIndex])}`,
                    `Job satisfaction: ${scoreText(satisfactionValues[items[0].dataIndex])}`
                ] : []
            } } }, scales: {
                ...sharedOptions.scales,
                y: { ...sharedOptions.scales.y, position: 'left', title: { display: true, text: 'Training hours / last 12 months' } },
                y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'Average tenure (months)' }, ticks: { color: '#10B981' } }
            } }, plugins
        });

    } catch (err) {
        console.error('Error loading department charts:', err);
    }
}

async function loadEmployeesTable(page = 1) {
    currentEmpPage = page;
    const reqId = ++empTableRequestId;
    const tbody = document.getElementById('employeeTableBody');
    tbody.innerHTML = `<tr><td colspan="14" class="text-center p-4"><div class="spinner"></div></td></tr>`;

    try {
        const filters = getAnalyticsFilters();
        const search = document.getElementById('employeeSearchInput')?.value;

        const res = await API.get('/api/analytics/employees', {
            ...filters,
            search: search,
            page: page,
            page_size: EMP_PAGE_SIZE
        });

        if (reqId !== empTableRequestId || !res.success) return;

        document.getElementById('employeeCountDisplay').textContent = 
            `Showing ${(res.page - 1) * res.page_size + 1} - ${Math.min(res.total_records, res.page * res.page_size)} of ${formatNumber(res.total_records)}`;

        if (res.records.length === 0) {
            tbody.innerHTML = `<tr><td colspan="14" class="text-center p-4 text-muted">No employees match the applied filter criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = res.records.map(emp => {
            const riskClass = emp.risk_level === 'High' ? 'badge-high' : (emp.risk_level === 'Medium' ? 'badge-medium' : (emp.risk_level === 'Notice' ? 'badge-high' : 'badge-low'));
            const noticeClass = emp.notice_status === 'Yes' ? 'badge-high' : 'badge-low';

            return `
                <tr>
                    <td><strong>${emp.employee_id}</strong></td>
                    <td>${emp.department}</td>
                    <td>${emp.job_role}</td>
                    <td>${emp.job_level}</td>
                    <td>${emp.location}</td>
                    <td>${emp.employment_type}</td>
                    <td>${emp.tenure_months}m</td>
                    <td>${emp.overtime_hours}</td>
                    <td>${emp.job_satisfaction}</td>
                    <td>${emp.work_life_balance}</td>
                    <td>${emp.training_hours}</td>
                    <td><span class="badge ${riskClass}">${emp.risk_level}</span></td>
                    <td><span class="badge ${noticeClass}">${emp.notice_status}</span></td>
                    <td>
                        <button class="btn btn-sm btn-outline" onclick="openEmployeeModal('${emp.employee_id}')" title="Inspect Employee">
                            <i class="bi bi-eye"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        renderPagination(res.page, res.total_pages);
    } catch (err) {
        console.error('Error loading employees table:', err);
    }
}

function renderPagination(page, totalPages) {
    document.getElementById('paginationInfo').textContent = `Page ${page} of ${formatNumber(totalPages)}`;
    const ctrl = document.getElementById('paginationControls');
    ctrl.innerHTML = '';

    const createBtn = (text, targetPage, disabled = false, active = false) => {
        const btn = document.createElement('button');
        btn.className = `page-btn ${active ? 'active' : ''}`;
        btn.disabled = disabled;
        btn.innerHTML = text;
        if (!disabled) {
            btn.onclick = () => loadEmployeesTable(targetPage);
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

async function loadDepartmentComparison() {
    const d1 = document.getElementById('compareDept1')?.value || 'Technology';
    const d2 = document.getElementById('compareDept2')?.value || 'Sales';

    document.getElementById('compareCol1Title').textContent = d1;
    document.getElementById('compareCol2Title').textContent = d2;

    try {
        const res = await API.get('/api/analytics/compare', { dept1: d1, dept2: d2 });
        if (!res.success) return;
        const c = res.comparison;

        const m1 = c.dept1.metrics;
        const m2 = c.dept2.metrics;

        document.getElementById('compHeadcount1').textContent = formatNumber(m1.headcount);
        document.getElementById('compHeadcount2').textContent = formatNumber(m2.headcount);
        document.getElementById('compAttrition1').textContent = m1.attrition_rate;
        document.getElementById('compAttrition2').textContent = m2.attrition_rate;
        document.getElementById('compTenure1').textContent = m1.avg_tenure;
        document.getElementById('compTenure2').textContent = m2.avg_tenure;
        document.getElementById('compOvertime1').textContent = m1.avg_overtime;
        document.getElementById('compOvertime2').textContent = m2.avg_overtime;
        document.getElementById('compSatisfaction1').textContent = m1.job_satisfaction;
        document.getElementById('compSatisfaction2').textContent = m2.job_satisfaction;
        document.getElementById('compTraining1').textContent = m1.training_hours;
        document.getElementById('compTraining2').textContent = m2.training_hours;
        document.getElementById('compHighRisk1').textContent = formatNumber(m1.high_risk_employees);
        document.getElementById('compHighRisk2').textContent = formatNumber(m2.high_risk_employees);
        document.getElementById('compNotice1').textContent = formatNumber(m1.employees_serving_notice);
        document.getElementById('compNotice2').textContent = formatNumber(m2.employees_serving_notice);
    } catch (err) {
        console.error('Error loading department comparison:', err);
    }
}

function setupEventHandlers() {
    document.getElementById('applyFiltersBtn')?.addEventListener('click', () => {
        loadKPIs();
        loadDepartmentCharts();
        loadEmployeesTable(1);
    });

    document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
        document.getElementById('filterDept').value = 'All';
        document.getElementById('filterRole').value = 'All';
        document.getElementById('filterLevel').value = 'All';
        document.getElementById('filterLocation').value = 'All';
        document.getElementById('filterEmpType').value = 'All';
        const slider = document.getElementById('filterTenure');
        if (slider) {
            slider.value = slider.max;
            document.getElementById('tenureValDisplay').textContent = `${slider.min || 0} - ${slider.max}`;
        }
        document.getElementById('employeeSearchInput').value = '';
        loadKPIs();
        loadDepartmentCharts();
        loadEmployeesTable(1);
    });

    document.getElementById('filterTenure')?.addEventListener('input', (e) => {
        document.getElementById('tenureValDisplay').textContent = `${document.getElementById('filterTenure')?.min || 0} - ${e.target.value}`;
    });

    document.getElementById('employeeSearchInput')?.addEventListener('input', () => {
        loadEmployeesTable(1);
    });

    document.getElementById('compareDept1')?.addEventListener('change', loadDepartmentComparison);
    document.getElementById('compareDept2')?.addEventListener('change', loadDepartmentComparison);
}
