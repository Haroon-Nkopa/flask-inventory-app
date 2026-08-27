let financialChartInstance = null;

// Initial execution entry point on page mount context
document.addEventListener('DOMContentLoaded', () => {
    // Fire off both telemetry data gathering workers on initial load
    fetchUnderpricedProducts();
    fetchBusinessHealthAnalysis();
});

// ====== Worker Handling Business Health Diagnostics Evaluation ======
async function fetchBusinessHealthAnalysis() {
    try {
        const response = await fetch('/api/financials/business-health');
        const data = await response.json();

        const healthSection = document.getElementById('business-health-section');
        const healthCard = document.getElementById('business-health-card');
        const healthBadge = document.getElementById('business-health-badge');
        const healthStatement = document.getElementById('business-health-statement');

        if (!response.ok || data.status !== 'success') {
            console.error("Business health data pipeline threw an exception:", data);
            return;
        }

        if (healthSection) healthSection.classList.remove('d-none');

        // Style the dashboard cards based on health evaluation outputs
        if (healthCard && healthBadge && healthStatement) {
            healthStatement.innerText = data.business_quality;
            
            // Clean out styling class traces before setting overrides
            healthCard.className = "card text-white shadow mb-3";
            healthBadge.className = "badge px-3 py-1 font-monospace";

            if (data.health_status_code === "HEALTHY") {
                healthCard.classList.add('bg-success', 'border-success');
                healthBadge.classList.add('bg-dark', 'text-success');
                healthBadge.innerText = "FINANCIALLY HEALTHY";
            } else {
                // Treats warnings cleanly without assuming artificial deficits
                healthCard.classList.add('bg-warning', 'text-dark', 'border-warning');
                healthBadge.classList.add('bg-dark', 'text-warning');
                healthBadge.innerText = "BUDGET ALERT WARNING";
            }
        }

        // Map quantitative aggregate text metrics for tracking reserves
        const s = data.summary || {};
        
        const revenueEl = document.getElementById('health-stat-revenue');
        const restockBudgetEl = document.getElementById('health-stat-restock-budget');
        const trueProfitEl = document.getElementById('health-stat-true-profit');

        if (revenueEl) revenueEl.innerText = `R ${(s.total_realised_revenue || 0).toFixed(2)}`;
        if (restockBudgetEl) restockBudgetEl.innerText = `R ${(s.total_restock_budget_to_save || 0).toFixed(2)}`;
        if (trueProfitEl) trueProfitEl.innerText = `R ${(s.total_realised_profit || 0).toFixed(2)}`;

    } catch (err) {
        console.error("Network communication exception within business health loop:", err);
    }
}

// 1. Core Worker handling initial high-urgency alerts (PRESERVED INTACT)
async function fetchUnderpricedProducts() {
    try {
        const response = await fetch('/api/financials/management-data');
        const data = await response.json();

        const spinner = document.getElementById('loading-spinner');
        const healthyAlert = document.getElementById('healthy-alert');
        const tableContainer = document.getElementById('report-table-container');
        const tableBody = document.getElementById('underpriced-table-body');
        const countBadge = document.getElementById('items-count-badge');

        if (spinner) spinner.classList.add('d-none');

        if (!response.ok || data.status !== 'success') {
            console.error("Management API validation error payload:", data);
            return;
        }

        const items = data.under_priced || [];

        if (items.length === 0) {
            if (healthyAlert) healthyAlert.classList.remove('d-none');
        } else {
            if (tableContainer) tableContainer.classList.remove('d-none');
            if (countBadge) countBadge.textContent = `${items.length} Flagged`;
            if (tableBody) {
                tableBody.innerHTML = '';
                items.forEach(item => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td class="text-start text-white fw-bold">${item.name}</td>
                        <td><span class="badge bg-secondary">${item.category}</span></td>
                        <td>R ${item.min_price_per_product.toFixed(2)}</td>
                        <td class="text-info font-monospace fw-bold">R ${item.selling_price.toFixed(2)}</td>
                        <td class="text-danger font-monospace fw-bold">R ${item.margin_loss.toFixed(2)}</td>
                    `;
                    tableBody.appendChild(row);
                });
            }
        }
    } catch (err) {
        console.error("Network crash compiling underpriced elements:", err);
    }
}

// 2. Interactive Toggle Trigger requested by user click events (PRESERVED INTACT)
async function toggleProfitMarginsView() {
    const marginContainer = document.getElementById('all-margins-container');
    const toggleBtn = document.getElementById('toggle-margins-btn');

    if (!marginContainer) return;

    if (!marginContainer.classList.contains('d-none')) {
        marginContainer.classList.add('d-none');
        if (toggleBtn) toggleBtn.innerText = "🔍 View Profit Margins for All Products";
        return;
    }

    marginContainer.classList.remove('d-none');
    if (toggleBtn) toggleBtn.innerText = "✖ Close Profit Margins Ledger";

    const tableBody = document.getElementById('margins-table-body');
    const allCountBadge = document.getElementById('all-items-count-badge');

    try {
        const response = await fetch('/api/financials/profit-margins');
        const data = await response.json();

        if (!response.ok || data.status !== 'success') {
            if (tableBody) tableBody.innerHTML = `<tr><td colspan="5" class="text-danger">Failed to download general ledger data parameters.</td></tr>`;
            return;
        }

        const margins = data.profit_margins || [];

        if (allCountBadge) allCountBadge.textContent = `${margins.length} Products`;
        if (!tableBody) return;

        tableBody.innerHTML = '';

        if (margins.length === 0) {
            tableBody.innerHTML = `<tr><td colspan="5" class="text-muted py-3">No active inventory items logged inside this shop profile.</td></tr>`;
            return;
        }

        margins.forEach(item => {
            const row = document.createElement('tr');
            
            let marginClass = 'text-success';
            let prependSymbol = '+';
            
            if (item.profit_margin < 0) {
                marginClass = 'text-danger fw-bold';
                prependSymbol = ''; 
            } else if (item.profit_margin === 0) {
                marginClass = 'text-warning';
                prependSymbol = '';
            }

            row.innerHTML = `
                <td class="text-start text-white fw-bold font-monospace">${item.name}</td>
                <td><span class="badge bg-secondary">${item.category}</span></td>
                <td>R ${item.min_price_per_product.toFixed(2)}</td>
                <td>R ${item.selling_price.toFixed(2)}</td>
                <td class="${marginClass}">R ${prependSymbol}${item.profit_margin.toFixed(2)}</td>
            `;
            tableBody.appendChild(row);
        });

    } catch (networkErr) {
        console.error("Ledger communication error pipeline exception:", networkErr);
        if (tableBody) tableBody.innerHTML = `<tr><td colspan="5" class="text-danger">⚠️ Server Connectivity Fault. Check DB connections.</td></tr>`;
    }
}
