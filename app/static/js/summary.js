let salesChartInstance = null;

// Execution entry point on initial page mount context
document.addEventListener('DOMContentLoaded', () => {
    loadSummaryData();
});

// Context handler triggered whenever the dropdown select item changes
function toggleViewContext() {
    const mode = document.getElementById('summaryType').value;
    const filterForm = document.getElementById('dateFiltersForm');
    const submitBtn = document.getElementById('filterSubmitBtnWrapper');
    
    // Hide date picker input panels for live telemetry stream, show for history logs
    if (mode === 'live') {
        filterForm.style.display = 'none';
        submitBtn.style.display = 'none';
    } else {
        filterForm.style.display = 'block';
        submitBtn.style.display = 'block';
    }
    loadSummaryData();
}

// Core coordinator tasked to request, fetch, and validate dynamic summary responses
async function loadSummaryData() {
    const mode = document.getElementById('summaryType').value;
    let url = `/api/summary/${mode}`;
    
    // Append URI parameters conditionally if running localized date filtering range targets
    if (mode !== 'live') {
        const start = document.getElementById('startDate').value;
        const end = document.getElementById('endDate').value;
        if (start && end) {
            url += `?start_date=${start}&end_date=${end}`;
        }
    }

    try {
        const response = await fetch(url);
        const data = await response.json();
        
        const summaryAlert = document.getElementById('summary-alert');

        if (!response.ok || data.error) {
            summaryAlert.classList.replace('alert-success', 'alert-warning');
            summaryAlert.innerText = data.error || "Failed to update dashboard data matrix metrics.";
            summaryAlert.classList.remove('d-none');
            return;
        }

        // Reset system context structures cleanly
        summaryAlert.classList.replace('alert-warning', 'alert-success');
        if (data.message) {
            summaryAlert.innerText = data.message;
            summaryAlert.classList.remove('d-none');
        } else {
            summaryAlert.classList.add('d-none');
        }

        renderDashboardLayout(mode, data);

    } catch (e) {
        console.error("Dashboard engine components failed to compile payload context:", e);
    }
}

// Master display controller routing template elements dynamically matching report selection scopes
function renderDashboardLayout(mode, data) {
    const revenueCardContainer = document.getElementById('revenue-card-container');
    const profitCardContainer = document.getElementById('profit-card-container');
    const trendsSection = document.getElementById('charts-and-trends-section');
    const auditContainer = document.getElementById('audit-log-container');
    const tablesContainer = document.getElementById('tables-container');

    // Clean structure baseline presets across transformations
    auditContainer.classList.add('d-none');
    trendsSection.classList.remove('d-none');
    profitCardContainer.style.display = 'none';
    revenueCardContainer.className = "col-md-6"; 

    if (mode === 'live') {
        profitCardContainer.style.display = 'block';
        revenueCardContainer.className = "col-md-6";
        
        document.getElementById('actual-revenue').innerText = `R ${data.total_revenue.toFixed(2)}`;
        document.getElementById('revenue-card-subtext').innerText = "Money already in the till today";
        document.getElementById('potential-profit').innerText = `R ${data.potential_profit.toFixed(2)}`;
        
        document.getElementById('table-header-title').innerText = "🗓️ Daily Revenue (Past 7 Days)";
        document.getElementById('table-column-header-metric').innerText = "Revenue";
        document.getElementById('chart-title-text').innerText = "📈 Sales Trend (Direct Turnover)";

        renderWeeklyRevenueTable(data.chart.labels, data.chart.values, "R");
        renderTealChartInstance(data.chart.labels, data.chart.values, 'Daily Sales (R)');
        renderDataTables(data);

    } else if (mode === 'daily-count') {
        revenueCardContainer.className = "col-md-12";
        
        document.getElementById('actual-revenue').innerText = `R ${data.total_revenue.toFixed(2)}`;
        document.getElementById('revenue-card-subtext').innerText = "Calculated business based on stock sheet diffs";
        
        document.getElementById('table-header-title').innerText = "🗓️ Sheet Timeline Variance";
        document.getElementById('table-column-header-metric').innerText = "Calculated Sales";
        document.getElementById('chart-title-text').innerText = "📈 Stock Depletion Trends";

        renderWeeklyRevenueTable(data.chart.labels, data.chart.values, "R");
        renderTealChartInstance(data.chart.labels, data.chart.values, 'Inferred Depletion (R)');
        renderDataTables(data);

    } else if (mode === 'audited') {
        revenueCardContainer.className = "col-md-12";
        
        const count = data.audit_records ? data.audit_records.length : 0;
        document.getElementById('actual-revenue').innerText = `${count} Checks`;
        document.getElementById('revenue-card-subtext').innerText = "Total physical adjustments processed during this window";

        trendsSection.classList.add('d-none');
        tablesContainer.innerHTML = "";
        auditContainer.classList.remove('d-none');

        renderAuditLogTable(data.audit_records);
    }
}

// Helper: Safely updates chronological timeline tables using fallback logic matrices
function renderWeeklyRevenueTable(labels, values, currencySymbol) {
    const weeklyBody = document.getElementById('weekly-revenues-body');
    if (!weeklyBody) return;

    if (!labels || labels.length === 0) {
        weeklyBody.innerHTML = `<tr><td colspan="2" class="text-muted">No historical timeline logs found.</td></tr>`;
        return;
    }

    // Maps array indexes backward to guarantee newest data surfaces at the top
    let html = '';
    for (let i = labels.length - 1; i >= 0; i--) {
        html += `
            <tr>
                <td class="text-capitalize">${labels[i]}</td>
                <td class="fw-bold text-success">${currencySymbol} ${parseFloat(values[i]).toFixed(2)}</td>
            </tr>`;
    }
    weeklyBody.innerHTML = html;
}

// Helper: Draws physical asset adjustment records on dedicated table rows
function renderAuditLogTable(records) {
    const auditBody = document.getElementById('audit-logs-body');
    if (!auditBody) return;

    if (!records || records.length === 0) {
        auditBody.innerHTML = `<tr><td colspan="5" class="text-center text-muted">No audit logs found for this window.</td></tr>`;
        return;
    }

    auditBody.innerHTML = records.map(r => `
        <tr>
            <td><small class="text-info">${r.date}</small> <span class="text-secondary d-block small">${r.timestamp}</span></td>
            <td><strong class="text-white">${r.product_name}</strong></td>
            <td><span class="badge bg-secondary">${r.counted_qty} units</span></td>
            <td><span class="text-warning">${r.logged_by}</span></td>
            <td><p class="text-muted small mb-0 text-wrap" style="max-width:250px;">${r.notes || '—'}</p></td>
        </tr>
    `).join('');
}

// Helper: Re-creates the original Stock-out, Fast Selling, and Top Earning list blocks
function renderDataTables(data) {
    const container = document.getElementById('tables-container');
    if (!container) return;
    
    let html = '';

    // Stock Out Table Component
    if (data.stock_out && data.stock_out.length > 0) {
        html += `
        <div class="alert alert-warning mt-4 text-start">
            <h5 class="mb-3 text-center">⚠️ Stock Out Products (${data.stock_out.length})</h5>
            <table class="table table-dark table-striped table-bordered mb-0">
                <thead><tr><th>Product</th><th>Category</th><th>Price (R)</th></tr></thead>
                <tbody>${data.stock_out.map(p => `<tr><td>${p.name}</td><td>${p.category || '-'}</td><td>${p.price.toFixed(2)}</td></tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    // Fast Selling Table Component
    if (data.fast_selling && data.fast_selling.length > 0) {
        html += `
        <div class="mt-5 text-start">
            <h4 class="text-warning mb-3">🔥 Fast Selling Products</h4>
            <table class="table table-dark table-striped table-bordered mb-0">
                <thead><tr><th>Product</th><th>Category</th><th>Units Sold</th></tr></thead>
                <tbody>${data.fast_selling.map(p => `<tr><td>${p.name}</td><td>${p.category || '-'}</td><td><strong>${p.sold_qty}</strong></td></tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    // Top Earning Table Component
    if (data.top_earning && data.top_earning.length > 0) {
        html += `
        <div class="mt-5 text-start">
            <h4 class="text-info mb-3">💎 Top Earning Products</h4>
            <table class="table table-dark table-striped table-bordered mb-0">
                <thead><tr><th>Product</th><th>Category</th><th>Gross Revenue</th></tr></thead>
                <tbody>${data.top_earning.map(p => `<tr><td>${p.name}</td><td>${p.category || '-'}</td><td class="text-success fw-bold">R ${p.revenue.toFixed(2)}</td></tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    container.innerHTML = html;
}

// Helper: Redraws the ChartJS timeline utilizing your exact canvas teal style settings
function renderTealChartInstance(labels, values, datasetLabel) {
    const canvasElement = document.getElementById('salesChart');
    if (!canvasElement) return;
    
    const ctx = canvasElement.getContext('2d');
    
    // Destroy the older canvas instance cleanly to avoid interface overlap visual bugs
        // Destroy the older canvas instance cleanly to avoid interface overlap visual bugs
    if (salesChartInstance) {
        salesChartInstance.destroy();
    }
    
    salesChartInstance = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: datasetLabel,
                data: values,
                borderColor: '#0dcaf0',
                backgroundColor: 'rgba(13, 202, 240, 0.2)',
                tension: 0.4,
                fill: true,
                pointRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { labels: { color: '#fff' } } },
            scales: {
                x: { ticks: { color: '#ccc' }, grid: { color: '#333' } },
                y: { ticks: { color: '#ccc' }, grid: { color: '#333' }, beginAtZero: true }
            }
        }
    });
}
