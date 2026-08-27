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
        if (filterForm) filterForm.style.display = 'none';
        if (submitBtn) submitBtn.style.display = 'none';
    } else {
        if (filterForm) filterForm.style.display = 'block';
        if (submitBtn) submitBtn.style.display = 'block';
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
            if (summaryAlert) {
                summaryAlert.classList.replace('alert-success', 'alert-warning');
                summaryAlert.innerText = data.error || "Failed to update dashboard data matrix metrics.";
                summaryAlert.classList.remove('d-none');
            }
            return;
        }

        // Reset system context structures cleanly
        if (summaryAlert) {
            summaryAlert.classList.replace('alert-warning', 'alert-success');
            if (data.message) {
                summaryAlert.innerText = data.message;
                summaryAlert.classList.remove('d-none');
            } else {
                summaryAlert.classList.add('d-none');
            }
        }

        renderDashboardLayout(mode, data);

    } catch (e) {
        console.error("Dashboard engine components failed to compile payload context:", e);
    }
}

// Real-time panel renderer targeting unverified operator product adjustments
function renderCashlessAlerts(data) {
    const cashlessPanel = document.getElementById('cashless-alert-panel');
    const cashlessContainer = document.getElementById('cashless-transactions-list-container');
    const cashlessBadge = document.getElementById('cashless-badge-count');

    // Always clear the container first to avoid duplicate mutations
    if (cashlessContainer) cashlessContainer.innerHTML = '';

    const transactions = data.unverified_cashless_transactions || [];

    // Only show this high-priority alert panel if unverified transactions exist
    if (transactions.length > 0 && cashlessPanel && cashlessContainer) {
        cashlessPanel.classList.remove('d-none');
        if (cashlessBadge) {
            cashlessBadge.textContent = `${transactions.length} Pending Review`;
        }

        transactions.forEach(tx => {
            const cardCol = document.createElement('div');
            cardCol.className = 'col-md-6 col-lg-4';
            cardCol.innerHTML = `
                <div class="card bg-black text-white border-danger h-100 shadow-sm">
                    <div class="card-body d-flex flex-column justify-content-between p-3">
                        <div>
                            <div class="d-flex justify-content-between align-items-center mb-2">
                                <span class="badge bg-danger text-uppercase font-monospace small">${tx.type}</span>
                                <small class="text-secondary">${tx.timestamp ? new Date(tx.timestamp).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}</small>
                            </div>
                            <p class="mb-2 text-light text-start">
                                <strong class="text-warning">Staff Operator</strong> used 
                                <span class="badge bg-secondary font-monospace px-2">${tx.quantity}x</span> of 
                                <span class="text-info fw-bold">${tx.product_name}</span>.
                            </p>
                            <p class="text-muted small mb-3 text-start">Valuation: <span class="text-success fw-bold">R ${tx.total_value.toFixed(2)}</span></p>
                        </div>
                        <div class="border-top border-secondary pt-2 mt-auto d-flex align-items-center justify-content-between">
                            <span class="text-white-50 small fw-bold">Did you know?</span>
                            <button class="btn btn-sm btn-success px-3" onclick="verifyTransaction(${tx.transaction_id}, this)">
                                Yes, Approve
                            </button>
                        </div>
                    </div>
                </div>
            `;
            cashlessContainer.appendChild(cardCol);
        });
    } else if (cashlessPanel) {
        cashlessPanel.classList.add('d-none');
    }
}

// Asynchronous background worker updating state verification on the target transaction model row
async function verifyTransaction(transactionId, buttonElement) {
    if (!confirm("Confirm this inventory usage calculation is correct?")) return;

    buttonElement.disabled = true;
    const originalText = buttonElement.innerText;
    buttonElement.innerHTML = `<span class="spinner-border spinner-border-sm" role="status"></span>`;

    try {
        const response = await fetch(`/api/cashless-transaction/${transactionId}/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();

        if (response.ok) {
            const cardItem = buttonElement.closest('.col-md-6');
            if (cardItem) cardItem.remove();
            
            const container = document.getElementById('cashless-transactions-list-container');
            const remaining = container ? container.children.length : 0;
            
            const cashlessPanel = document.getElementById('cashless-alert-panel');
            const cashlessBadge = document.getElementById('cashless-badge-count');

            if (remaining === 0 && cashlessPanel) {
                cashlessPanel.classList.add('d-none');
            } else if (cashlessBadge) {
                cashlessBadge.textContent = `${remaining} Pending Review`;
            }
        } else {
            alert(result.error || "Could not update transaction state.");
            buttonElement.disabled = false;
            buttonElement.innerText = originalText;
        }
    } catch (err) {
        console.error("Network communication error:", err);
        alert("Server error. Please verify database connection.");
        buttonElement.disabled = false;
        buttonElement.innerText = originalText;
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
    if (auditContainer) auditContainer.classList.add('d-none');
    if (trendsSection) trendsSection.classList.remove('d-none');
    if (profitCardContainer) profitCardContainer.style.display = 'none';
    if (revenueCardContainer) revenueCardContainer.className = "col-md-6"; 

    if (mode === 'live') {
        renderCashlessAlerts(data);

        if (profitCardContainer) profitCardContainer.style.display = 'block';
        if (revenueCardContainer) revenueCardContainer.className = "col-md-6";
        
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
        const cashlessPanel = document.getElementById('cashless-alert-panel');
        if (cashlessPanel) cashlessPanel.classList.add('d-none');

        if (revenueCardContainer) revenueCardContainer.className = "col-md-12";
        
        document.getElementById('actual-revenue').innerText = `R ${data.total_revenue.toFixed(2)}`;
        document.getElementById('revenue-card-subtext').innerText = "Calculated business based on stock sheet diffs";
        
        document.getElementById('table-header-title').innerText = "🗓️ Sheet Timeline Variance";
                document.getElementById('table-column-header-metric').innerText = "Calculated Sales";
        document.getElementById('chart-title-text').innerText = "📈 Stock Depletion Trends";

        renderWeeklyRevenueTable(data.chart.labels, data.chart.values, "R");
        renderTealChartInstance(data.chart.labels, data.chart.values, 'Inferred Depletion (R)');
        renderDataTables(data);

    } else if (mode === 'audited') {
        const cashlessPanel = document.getElementById('cashless-alert-panel');
        if (cashlessPanel) cashlessPanel.classList.add('d-none');

        if (revenueCardContainer) revenueCardContainer.className = "col-md-12";
        
        const count = data.audit_records ? data.audit_records.length : 0;
        document.getElementById('actual-revenue').innerText = `${count} Checks`;
        document.getElementById('revenue-card-subtext').innerText = "Total physical adjustments processed during this window";

        if (trendsSection) trendsSection.classList.add('d-none');
        if (tablesContainer) tablesContainer.innerHTML = "";
        if (auditContainer) auditContainer.classList.remove('d-none');

        renderAuditLogTable(data.audit_records);
    }
}

// 1. Renders the historical 7-day layout table cells cleanly
function renderWeeklyRevenueTable(labels, values, currencySymbol) {
    const tableBody = document.getElementById('weekly-revenues-body');
    if (!tableBody) return;

    // Clear out the "Loading timeline data..." placeholder text row completely
    tableBody.innerHTML = '';
    
    // Display items in reverse order to see the most recent days first
    for (let i = labels.length - 1; i >= 0; i--) {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td class="text-white-50">${labels[i]}</td>
            <td class="text-success fw-bold">${currencySymbol} ${values[i].toFixed(2)}</td>
        `;
        tableBody.appendChild(row);
    }
}

// 2. Renders or updates your Chart.js trend line canvas graphics safely
function renderTealChartInstance(labels, values, datasetLabel) {
    const ctx = document.getElementById('salesChart');
    if (!ctx) return;

    // Destroy existing canvas memory instances to prevent rendering glitch layouts
    if (salesChartInstance) {
        salesChartInstance.destroy();
    }

    try {
        salesChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: datasetLabel,
                    data: values,
                    borderColor: '#0dcaf0', // Beautiful Teal
                    backgroundColor: 'rgba(13, 202, 240, 0.1)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a0a0a0' } },
                    y: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { color: '#a0a0a0' } }
                }
            }
        });
    } catch (chartError) {
        console.error("Visual Chart engine initialization failed, bypassing to maintain data tables:", chartError);
    }
}

// 3. Renders Stock-Out, Fast Selling, and Top Earning tables dynamically at the bottom
function renderDataTables(data) {
    const tablesContainer = document.getElementById('tables-container');
    if (!tablesContainer) return;

    // A generic helper to construct card-wrapped clean bootstrap table blocks
    const buildTableHTML = (title, headerClass, columns, rows, emptyMsg) => {
        let rowsHTML = '';
        if (rows.length === 0) {
            rowsHTML = `<tr><td colspan="${columns.length}" class="text-muted py-3">${emptyMsg}</td></tr>`;
        } else {
            rows.forEach(row => {
                rowsHTML += `<tr>${row.map(col => `<td>${col}</td>`).join('')}</tr>`;
            });
        }

        return `
            <div class="card bg-dark border-secondary overflow-hidden mb-4 text-start">
                <div class="card-header ${headerClass} text-dark fw-bold">${title}</div>
                <div class="table-responsive">
                    <table class="table table-dark table-striped table-hover mb-0 text-center align-middle">
                        <thead>
                            <tr>${columns.map(c => `<th>${c}</th>`).join('')}</tr>
                        </thead>
                        <tbody>${rowsHTML}</tbody>
                    </table>
                </div>
            </div>
        `;
    };

    // Map Stock Out Rows
    const stockOutRows = (data.stock_out || []).map(p => [
        p.name,
        `<span class="badge bg-secondary">${p.category}</span>`,
        `<span class="text-danger">R ${p.price.toFixed(2)}</span>`
    ]);

    // Map Fast Selling Rows
    const fastSellingRows = (data.fast_selling || []).map(p => [
        p.name,
        p.category,
        `<span class="badge bg-info px-3">${p.sold_qty} units</span>`
    ]);

    // Map Top Earning Rows
    const topEarningRows = (data.top_earning || []).map(p => [
        p.name,
        p.category,
        `<span class="text-success fw-bold">R ${p.revenue.toFixed(2)}</span>`
    ]);

    // Inject all three newly compiled matrix blocks into your tables-container block wrapper
    tablesContainer.innerHTML = `
        <div class="row">
            <div class="col-12 col-xl-4">
                ${buildTableHTML("🚨 Products Currently Out of Stock", "bg-danger", ["Product Name", "Category", "Price"], stockOutRows, "No products are currently out of stock.")}
            </div>
            <div class="col-12 col-md-6 col-xl-4">
                ${buildTableHTML("🔥 Fast Selling Items (By Volume Today)", "bg-warning", ["Product Name", "Category", "Qty Sold"], fastSellingRows, "No products sold yet today.")}
            </div>
            <div class="col-12 col-md-6 col-xl-4">
                ${buildTableHTML("💰 Top Earning Products (By Revenue Today)", "bg-info", ["Product Name", "Category", "Total Revenue"], topEarningRows, "No revenue generated yet today.")}
            </div>
        </div>
    `;
}
