/**
 * Workforce Intelligence — Common UI Utilities
 */

// Mobile sidebar toggle
document.addEventListener('DOMContentLoaded', () => {
    const toggleBtn = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('appSidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
        // Click outside closes
        document.addEventListener('click', (e) => {
            if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target) && sidebar.classList.contains('open')) {
                sidebar.classList.remove('open');
            }
        });
    }

    // Modal close listeners
    const modal = document.getElementById('employeeDetailModal');
    const closeBtn = document.getElementById('modalCloseBtn');
    if (modal && closeBtn) {
        closeBtn.addEventListener('click', () => {
            modal.classList.remove('open');
        });
        modal.addEventListener('click', (e) => {
            if (e.target === modal) modal.classList.remove('open');
        });
    }
});

// Format numbers
function formatNumber(num) {
    if (num === null || num === undefined) return '0';
    return Number(num).toLocaleString('en-IN');
}

// Format percentages
function formatPercent(val) {
    if (val === null || val === undefined) return '0%';
    return `${Number(val).toFixed(1)}%`;
}

// Chart Registry to safely track and destroy existing chart instances before re-rendering
const chartRegistry = {};

function renderChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    if (chartRegistry[canvasId]) {
        chartRegistry[canvasId].destroy();
    }

    // Default chart font styling
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.color = '#64748B';

    const ctx = canvas.getContext('2d');
    const newChart = new Chart(ctx, config);
    chartRegistry[canvasId] = newChart;
    return newChart;
}

// Open Employee Detail Modal
async function openEmployeeModal(empId) {
    const modal = document.getElementById('employeeDetailModal');
    const body = document.getElementById('modalEmployeeBody');
    const title = document.getElementById('modalEmployeeTitle');
    
    if (!modal || !body) return;
    
    modal.classList.add('open');
    body.innerHTML = `
        <div class="loading-placeholder">
            <div class="spinner"></div>
            <span>Fetching profile for ${empId}...</span>
        </div>
    `;

    try {
        const res = await API.get(`/api/prediction/employee/${empId}`);
        if (!res.success || !res.employee) {
            body.innerHTML = `<div class="p-4 text-center text-danger">Employee details could not be retrieved.</div>`;
            return;
        }

        const emp = res.employee;
        title.textContent = `${emp.employee_name} (${emp.employee_id})`;

        const riskBadge = emp.risk_level === 'High' ? 'badge-high' : (emp.risk_level === 'Medium' ? 'badge-medium' : 'badge-low');

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
                <span class="badge ${riskBadge}" style="font-size:12px; padding:6px 12px;">${emp.risk_level} Risk</span>
            </div>

            <div class="emp-probability-box">
                <div>
                    <div class="emp-prob-label">Attrition Risk Probability (Next 6 Months)</div>
                    <div style="font-size:11.5px; color:var(--text-muted);">Model Decision Support Estimate</div>
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
                    <div><span class="label">Training Hours</span><span class="val">${emp.training_hours} hrs (Last 12M)</span></div>
                </div>
                <div class="emp-detail-item">
                    <i class="bi bi-award-fill"></i>
                    <div><span class="label">Last Promotion</span><span class="val">${emp.months_since_last_promotion} months ago</span></div>
                </div>
            </div>

            <div style="margin-top:16px;">
                <h5 style="font-size:13px; font-weight:600; color:var(--navy-text); margin-bottom:10px;">Top Factors Influencing Risk</h5>
                ${(emp.top_factors || []).map(f => `
                    <div class="factor-bar-item">
                        <div class="factor-bar-header">
                            <span>${f.factor}</span>
                            <span style="font-size:11px; color:var(--text-muted);">${f.description}</span>
                        </div>
                        <div class="factor-progress-bg">
                            <div class="factor-progress-fill" style="width:${Math.min(100, f.impact * 250)}%;"></div>
                        </div>
                    </div>
                `).join('')}
            </div>

            <div style="margin-top:20px; background:#F8FAFC; border:1px solid var(--border-color); border-radius:var(--radius-md); padding:14px;">
                <h5 style="font-size:12.5px; font-weight:600; color:var(--navy-text); margin-bottom:8px; display:flex; align-items:center; gap:6px;">
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
        body.innerHTML = `<div class="p-4 text-center text-danger">Error loading employee profile: ${err.message}</div>`;
    }
}

// Global expose
window.showEmployeeDetail = openEmployeeModal;
window.openEmployeeModal = openEmployeeModal;
