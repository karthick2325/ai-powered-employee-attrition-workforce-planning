/**
 * Workforce Intelligence — Employee & Department Analytics Controller
 */
let currentEmpPage = 1;
const EMP_PAGE_SIZE = 10;

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
    try {
        const dept = document.getElementById('filterDept')?.value;
        const res = await API.get('/api/analytics/kpis', { department: dept });
        if (!res.success) return;
        const k = res.kpis;
        document.getElementById('kpiTotalEmp').textContent = formatNumber(k.total_employees);
        document.getElementById('kpiTotalDepts').textContent = k.total_departments;
        document.getElementById('kpiJobRoles').textContent = k.unique_job_roles;
        document.getElementById('kpiAvgTenure').textContent = `${k.average_tenure_months} mos`;
        document.getElementById('kpiAvgSatisfaction').textContent = `${k.average_job_satisfaction} / 5`;
        document.getElementById('kpiAvgTraining').textContent = `${k.average_training_hours} hrs`;
        document.getElementById('kpiAvgOvertime').textContent = `${k.average_overtime_hours} hrs`;
    } catch (err) {
        console.error('Error loading analytics KPIs:', err);
    }
}

async function loadDepartmentCharts() {
    try {
        const res = await API.get('/api/analytics/charts');
        if (!res.success) return;
        const c = res.charts;

        // 1. Headcount
        renderChart('chartDeptHeadcount', {
            type: 'bar',
            data: {
                labels: c.headcount.departments,
                datasets: [{
                    label: 'Headcount',
                    data: c.headcount.values,
                    backgroundColor: '#0D63F3',
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

        // 2. Attrition Rate
        renderChart('chartDeptAttrition', {
            type: 'bar',
            data: {
                labels: c.attrition_rate.departments,
                datasets: [{
                    label: 'Attrition Rate (%)',
                    data: c.attrition_rate.rates,
                    backgroundColor: '#F87171',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { callback: v => `${v}%` }, grid: { color: '#F1F5F9' } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 3. Tenure
        renderChart('chartDeptTenure', {
            type: 'bar',
            data: {
                labels: c.tenure.departments,
                datasets: [{
                    label: 'Avg. Tenure (Months)',
                    data: c.tenure.values,
                    backgroundColor: '#10B981',
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

        // 4. Satisfaction
        renderChart('chartDeptSatisfaction', {
            type: 'bar',
            data: {
                labels: c.satisfaction.departments,
                datasets: [{
                    label: 'Avg. Satisfaction',
                    data: c.satisfaction.values,
                    backgroundColor: '#FFA726',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, max: 5, grid: { color: '#F1F5F9' } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 5. Overtime
        renderChart('chartDeptOvertime', {
            type: 'bar',
            data: {
                labels: c.overtime.departments,
                datasets: [{
                    label: 'Avg. Overtime (Hours)',
                    data: c.overtime.values,
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

        // 6. Training Hours
        renderChart('chartDeptTraining', {
            type: 'bar',
            data: {
                labels: c.training.departments,
                datasets: [{
                    label: 'Training Hours',
                    data: c.training.values,
                    backgroundColor: '#00B4D8',
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
    } catch (err) {
        console.error('Error loading department charts:', err);
    }
}

async function loadEmployeesTable(page = 1) {
    currentEmpPage = page;
    const tbody = document.getElementById('employeeTableBody');
    tbody.innerHTML = `<tr><td colspan="14" class="text-center p-4"><div class="spinner"></div></td></tr>`;

    try {
        const dept = document.getElementById('filterDept')?.value;
        const role = document.getElementById('filterRole')?.value;
        const level = document.getElementById('filterLevel')?.value;
        const loc = document.getElementById('filterLocation')?.value;
        const type = document.getElementById('filterEmpType')?.value;
        const maxTenure = document.getElementById('filterTenure')?.value;
        const search = document.getElementById('employeeSearchInput')?.value;

        const res = await API.get('/api/analytics/employees', {
            department: dept,
            job_role: role,
            job_level: level,
            location: loc,
            employment_type: type,
            max_tenure: maxTenure,
            search: search,
            page: page,
            page_size: EMP_PAGE_SIZE
        });

        if (!res.success) return;

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
        loadEmployeesTable(1);
    });

    document.getElementById('resetFiltersBtn')?.addEventListener('click', () => {
        document.getElementById('filterDept').value = 'All';
        document.getElementById('filterRole').value = 'All';
        document.getElementById('filterLevel').value = 'All';
        document.getElementById('filterLocation').value = 'All';
        document.getElementById('filterEmpType').value = 'All';
        document.getElementById('filterTenure').value = document.getElementById('filterTenure').max;
        document.getElementById('tenureValDisplay').textContent = `0 - ${document.getElementById('filterTenure').max}`;
        document.getElementById('employeeSearchInput').value = '';
        loadKPIs();
        loadEmployeesTable(1);
    });

    document.getElementById('filterTenure')?.addEventListener('input', (e) => {
        document.getElementById('tenureValDisplay').textContent = `0 - ${e.target.value}`;
    });

    document.getElementById('employeeSearchInput')?.addEventListener('input', () => {
        loadEmployeesTable(1);
    });

    document.getElementById('compareDept1')?.addEventListener('change', loadDepartmentComparison);
    document.getElementById('compareDept2')?.addEventListener('change', loadDepartmentComparison);
}
