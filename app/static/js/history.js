document.addEventListener('DOMContentLoaded', () => {
    const tableSelect = document.getElementById('stock-table-select');
    
    // Initial bootstrap call (hooks select value from HTML dropdown, defaults to live)
    const initialView = tableSelect ? tableSelect.value : 'live';
    fetchStockHistoryMatrix(initialView);

    if (tableSelect) {
        tableSelect.addEventListener('change', function() {
            fetchStockHistoryMatrix(this.value);
        });
    }
});

async function fetchStockHistoryMatrix(reportType) {
    const header = document.getElementById('history-header');
    const body = document.getElementById('history-body');

    // 1. Maintain a clean, responsive loading screen context across structural changes
    body.innerHTML = '<tr><td colspan="100%" class="text-center py-4"><div class="spinner-border spinner-border-sm text-success me-2" role="status"></div>Compiling inventory ledger...</td></tr>';

    try {
        const response = await fetch(`/api/stock-history?type=${reportType}`);
        const data = await response.json();

        // --- STRUCTURAL ARCHETYPE 1: Flat Live Inventory Layout ---
        if (data.report_type === 'live') {
            if (!data.records || data.records.length === 0) {
                header.innerHTML = '';
                body.innerHTML = '<tr><td colspan="100%" class="text-center text-muted py-4">📭 No live stock records found.</td></tr>';
                return;
            }

            header.innerHTML = `
                <tr>
                    <th>Product Name</th>
                    <th>Category</th>
                    <th>Size</th>
                    <th class="text-center">Live Balance</th>
                    <th class="text-center">Restock Alert Level</th>
                </tr>`;

            body.innerHTML = data.records.map(product => `
                <tr>
                    <td class="fw-bold text-light">${product.product_name}</td>
                    <td><span class="badge bg-secondary opacity-75">${product.category}</span></td>
                    <td>${product.size || 'N/A'}</td>
                    <td class="text-center fw-bold ${product.quantity <= product.lower_bound ? 'text-danger' : 'text-success'}">
                        ${product.quantity}
                    </td>
                    <td class="text-center text-muted"><small>${product.lower_bound}</small></td>
                </tr>
            `).join('');
            return;
        }

        // --- STRUCTURAL ARCHETYPE 2: Cross-Tab Matrix Grid Layout (Daily / Audited) ---
        if (!data.dates || data.dates.length === 0) {
            header.innerHTML = '';
            body.innerHTML = '<tr><td colspan="100%" class="text-center text-muted py-4">📭 No baseline log timeline sheets recorded for this category.</td></tr>';
            return;
        }

        // A. Inject dynamic calendar tracking columns into table head row
        let headerHtml = `
            <tr>
                <th>Product Details</th>
                <th>Category</th>`;
        
        data.dates.forEach(date => {
            headerHtml += `<th class="text-center text-info small" style="min-width: 120px;">${date}</th>`;
        });
        headerHtml += '</tr>';
        header.innerHTML = headerHtml;

        // B. Populate cross-tab columns cell blocks matching products against metrics
        let bodyHtml = '';
        data.stock_data.forEach(product => {
            let rowHtml = `
                <tr>
                    <td class="fw-bold text-light">${product.name}</td>
                    <td><span class="badge bg-secondary opacity-75">${product.category}</span></td>`;
            
            data.dates.forEach(date => {
                // Safely grab structural history parameters parsed by Python
                const qty = product.history[date] !== undefined ? product.history[date] : '-';
                
                // Track dynamic tooltip strings if note arrays exist
                const itemNote = (product.notes && product.notes[date]) ? product.notes[date] : '';
                
                // If it is an audited note cell block, apply hover classes and metadata attributes
                const cellClass = itemNote ? 'text-warning text-decoration-underline fw-bold' : '';
                const tooltipAttr = itemNote ? ` title="${itemNote}" data-bs-toggle="tooltip" data-bs-placement="top" style="cursor: help;"` : '';

                rowHtml += `<td class="text-center ${cellClass}" ${tooltipAttr}>${qty}</td>`;
            });
            
            rowHtml += '</tr>';
            bodyHtml += rowHtml;
        });

        body.innerHTML = bodyHtml;

        // C. Initialize Bootstrap tooltips for audit tracking logs if structural assets load safely
        if (typeof bootstrap !== 'undefined' && reportType === 'audited') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(el => new bootstrap.Tooltip(el));
        }

    } catch (error) {
        console.error("Ledger Integration Error:", error);
        header.innerHTML = '';
        body.innerHTML = '<tr><td colspan="100%" class="text-center text-danger py-4">⚠️ Critical error syncing system inventory sheets.</td></tr>';
    }
}
