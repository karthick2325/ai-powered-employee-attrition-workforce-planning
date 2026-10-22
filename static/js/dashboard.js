/**
 * Workforce Intelligence — Dashboard Overview Controller
 */
document.addEventListener('DOMContentLoaded', async () => {
    try {
        const data = await API.get('/api/dashboard/overview');
        if (!data.success) {
            console.error('Failed to load dashboard overview data');
            return;
        }

        // 1. Populate Top 6 KPIs
        const k = data.kpis;
        document.getElementById('kpiTotalEmployees').textContent = formatNumber(k.total_employees);
        document.getElementById('kpiHistoricalAttrition').textContent = formatNumber(k.historical_attrition);
        document.getElementById('kpiHistoricalAttritionPct').textContent = `${k.historical_attrition_pct}% of ${formatNumber(k.total_eligible_outcomes)}`;
        document.getElementById('kpiServingNotice').textContent = formatNumber(k.serving_notice);
        document.getElementById('kpiPredictedHighRisk').textContent = formatNumber(k.predicted_high_risk);
        document.getElementById('kpiPredictedHighRiskPct').textContent = `${k.predicted_high_risk_pct}% of active`;
        document.getElementById('kpiOpenRequisitions').textContent = formatNumber(k.open_requisitions);
        document.getElementById('kpiStaffingGap').textContent = formatNumber(k.staffing_gap);

        // Badges
        document.getElementById('headcountTotalBadge').textContent = `Total: ${formatNumber(k.total_employees)}`;
        document.getElementById('attritionCohortBadge').textContent = `From ${formatNumber(k.total_eligible_outcomes)} records`;

        // 2. Department-wise Headcount Chart
        const hc = data.headcount_by_department;
        renderChart('headcountChart', {
            type: 'bar',
            data: {
                labels: hc.departments,
                datasets: [{
                    label: 'Employees',
                    data: hc.values,
                    backgroundColor: '#3B82F6',
                    borderRadius: 6
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

        // 3. Attrition Outcome Distribution (Doughnut)
        const aDist = data.attrition_outcome_distribution;
        renderChart('attritionOutcomeChart', {
            type: 'doughnut',
            data: {
                labels: [
                    `Stayed (${aDist.stayed_pct}%)`,
                    `Attrition (${aDist.attrition_pct}%)`
                ],
                datasets: [{
                    data: [aDist.stayed_count, aDist.attrition_count],
                    backgroundColor: ['#22B573', '#F04452'],
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12 } }
                }
            }
        });

        // 4. Department-wise Attrition Rate (Bar)
        const ar = data.attrition_rate_by_department;
        renderChart('deptAttritionRateChart', {
            type: 'bar',
            data: {
                labels: ar.departments,
                datasets: [{
                    label: 'Attrition Rate (%)',
                    data: ar.rates,
                    backgroundColor: '#F87171',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: (ctx) => ` Attrition: ${ctx.parsed.y}%`
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { callback: (val) => `${val}%` },
                        grid: { color: '#F1F5F9' }
                    },
                    x: { grid: { display: false } }
                }
            }
        });

        // 5. Employee Risk Distribution (Doughnut)
        const rDist = data.risk_distribution;
        renderChart('employeeRiskChart', {
            type: 'doughnut',
            data: {
                labels: rDist.categories.map(c => `${c.level} (${c.percentage}%)`),
                datasets: [{
                    data: rDist.categories.map(c => c.count),
                    backgroundColor: rDist.categories.map(c => c.color),
                    borderWidth: 2,
                    borderColor: '#ffffff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12 } }
                }
            }
        });

        // 6. Notice Period — Expected Exits by Month (Bar)
        const ne = data.notice_monthly_exits;
        renderChart('noticeExitsChart', {
            type: 'bar',
            data: {
                labels: ne.months,
                datasets: [{
                    label: 'Confirmed Notice Exits',
                    data: ne.notice_exits,
                    backgroundColor: '#38BDF8',
                    borderRadius: 6
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

        // 7. Workforce Planning — Current vs Target Headcount (Grouped Bar)
        const wf = data.workforce_target_comparison;
        renderChart('wfTargetComparisonChart', {
            type: 'bar',
            data: {
                labels: wf.departments,
                datasets: [
                    {
                        label: 'Current Headcount',
                        data: wf.current_headcount,
                        backgroundColor: '#3B82F6',
                        borderRadius: 4
                    },
                    {
                        label: 'Target Headcount',
                        data: wf.target_headcount,
                        backgroundColor: '#22B573',
                        borderRadius: 4
                    },
                    {
                        label: 'Gap After Open Requisitions',
                        data: wf.gap_after_open,
                        backgroundColor: '#FFA726',
                        borderRadius: 4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'top', labels: { boxWidth: 12, font: { size: 11 } } }
                },
                scales: {
                    y: { beginAtZero: true, grid: { color: '#F1F5F9' } },
                    x: { grid: { display: false } }
                }
            }
        });

        // 8. Recruitment Pipeline Candidate Funnel
        const rf = data.recruitment_funnel;
        renderChart('recruitmentFunnelChart', {
            type: 'bar',
            data: {
                labels: rf.stages.map(s => s.stage),
                datasets: [{
                    label: 'Candidates',
                    data: rf.stages.map(s => s.count),
                    backgroundColor: rf.stages.map(s => s.color),
                    borderRadius: 6
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

        // 9. Recruitment Costs Summary
        const rc = data.recruitment_costs;
        document.getElementById('totalRecruitmentCost').textContent = rc.total_cost_formatted;
        document.getElementById('avgCostPerRequisition').textContent = rc.avg_cost_formatted;
        document.getElementById('costRecruiter').textContent = rc.categories.recruiter.formatted;
        document.getElementById('costAdvertising').textContent = rc.categories.advertising.formatted;
        document.getElementById('costAgency').textContent = rc.categories.agency.formatted;
        document.getElementById('costAssessment').textContent = rc.categories.assessment.formatted;

        // 10. Quick Insights List
        const insightsList = document.getElementById('quickInsightsList');
        if (data.quick_insights && data.quick_insights.length > 0) {
            insightsList.innerHTML = data.quick_insights.map(item => `
                <div class="insight-item">
                    <div class="insight-icon kpi-icon-${item.color}">
                        <i class="bi ${item.icon}"></i>
                    </div>
                    <div>${item.text}</div>
                </div>
            `).join('');
        }
    } catch (err) {
        console.error('Error initializing dashboard overview:', err);
    }
});
