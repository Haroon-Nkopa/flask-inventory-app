document.addEventListener('DOMContentLoaded', function() {
    const tableSelect = document.getElementById('stock-table-select');
    
    // Initial load with default "live" type
    loadStockHistory(tableSelect.value);

    // Watch for dropdown changes to re-fetch relevant records
    tableSelect.addEventListener('change', function() {
        loadStockHistory(this.value);
    });
});

async function loadStockHistory(reportType) {
    const headerRow = document.getElementById('history-header');
    const bodyRow = document.getElementById('history-body');
    
    // Display an intermediate loading state while shifting records
    bodyRow.innerHTML = `<tr><td colspan="100%" class="text-center py-4">Updating inventory view...</td></tr>`;
    
    try {
        // Appends select value to url structure -> e.g., /api/stock-history?type=daily
        const response = await fetch(`/api/stock-history?type=${reportType}`);
        if (!response.ok) throw new Error("Failed to fetch stock records");
        
        const data = await response.json();
        
        // Handle empty datasets gracefully
        if (!data.records || data.records.length === 0) {
            headerRow.innerHTML = '';
            bodyRow.innerHTML = `
                <tr>
                    <td colspan="100%" class="text-center text-muted py-5">
                        <span class="fs-2 d-block mb-2">📭</span>
                        No entries recorded for this view.
                    </td>
                </tr>`;
            return;
        }

        // 1. Build and Inject Headers Based on Report Type Archetype
        if (reportType === 'live') {
            headerRow.innerHTML = `
                <tr>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Size</th>
                    <th class="text-center">Live Stock Balance</th>
                    <th class="text-center">Restock Alert Threshold</th>
                </tr>`;
                
            // Render rows targeting the strict 1-to-1 live attributes
            bodyRow.innerHTML = data.records.map(record => `
                <tr>
                    <td class="fw-bold text-light">${record.product_name}</td>
                    <td><span class="badge bg-secondary">${record.category}</span></td>
                    <td>${record.size || 'N/A'}</td>
                    <td class="text-center fw-bold ${record.quantity <= record.lower_bound ? 'text-danger' : 'text-success'}">
                        ${record.quantity}
                    </td>
                    <td class="text-center text-muted">${record.lower_bound}</td>
                </tr>
            `).join('');
            
        } else {
            // Shared structure for 'daily' and 'audited' timeline arrays
            headerRow.innerHTML = `
                <tr>
                    <th>Log Date</th>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th class="text-center">Recorded Quantity</th>
                    ${reportType === 'audited' ? '<th>Audit Notes / Discrepancy</th>' : ''}
                </tr>`;
                
            bodyRow.innerHTML = data.records.map(record => `
                <tr>
                    <td class="text-secondary">${record.date}</td>
                    <td class="fw-bold text-light">${record.product_name}</td>
                    <td><span class="badge bg-secondary">${record.category}</span></td>
                    <td class="text-center fw-bold text-info">${record.quantity}</td>
                    ${reportType === 'audited' ? `<td><small class="text-muted">${record.notes || 'No notes'}</small></td>` : ''}
                </tr>
            `).join('');
        }

    } catch (error) {
        headerRow.innerHTML = '';
        bodyRow.innerHTML = `
            <tr>
                <td colspan="100%" class="text-center text-danger py-5">
                    ⚠️ Error fetching history. Please refresh or try again.
                </td>
            </tr>`;
        console.error("Stock View Error:", error);
    }
}
