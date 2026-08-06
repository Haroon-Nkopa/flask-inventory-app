/**
 * Toggles the visibility state of the inventory audit table component.
 * Executes a network data reload when the view is expanded.
 */
function toggleAuditView() {
    const container = document.getElementById('audit-discrepancy-container');
    const button = document.getElementById('toggle-audit-btn');

    if (container.classList.contains('d-none')) {
        container.classList.remove('d-none');
        button.innerText = '❌ Close Discrepancy View';
        fetchInventoryDiscrepancies();
    } else {
        container.classList.add('d-none');
        button.innerText = '🔍 Analyze Inventory Discrepancies';
    }
}

/**
 * Communicates with the backend route API to fetch discrepancy objects
 * and handles UI table population dynamically.
 */
function fetchInventoryDiscrepancies() {
    const tableBody = document.getElementById('audit-discrepancy-body');
    
    // Set initial loading state
    tableBody.innerHTML = `
        <tr>
            <td colspan="5" class="text-info py-4">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Analyzing live ledgers against physical count sheets...
            </td>
        </tr>
    `;

    fetch('/api/inventory/discrepancies', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server returned error HTTP state: ${response.status}`);
        }
        return response.json();
    })
    .then(data => {
        tableBody.innerHTML = ''; // Clear out the loading spinner row

        if (!data.discrepancies || data.discrepancies.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-success py-4 fw-bold">
                        ✅ Perfect Match! All physical counts match your live system balances.
                    </td>
                </tr>
            `;
            return;
        }

        // Render every record variance row securely
        data.discrepancies.forEach(item => {
            const row = document.createElement('tr');
            
            // Highlight negative vs positive variances dynamically
            const badgeClass = item.difference < 0 ? 'badge bg-danger' : 'badge bg-warning text-dark';
            const signPrefix = item.difference > 0 ? '+' : '';

            row.innerHTML = `
                <td><code>#${item.product_id}</code></td>
                <td class="text-start fw-semibold">${escapeHtml(item.product_name)}</td>
                <td>${item.live_quantity}</td>
                <td>${item.audited_quantity}</td>
                <td>
                    <span class="${badgeClass}">${signPrefix}${item.difference}</span>
                </td>
            `;
            tableBody.appendChild(row);
        });
    })
    .catch(error => {
        console.error('Audit Fetch Error:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-danger py-4">
                    ⚠️ Failed to run discrepancy report. Check system engine console.
                </td>
            </tr>
        `;
    });
}

/**
 * Utility tool to prevent XSS exploits when rendering raw input names to DOM
 */
function escapeHtml(string) {
    return String(string).replace(/[&<>"']/g, function (s) {
        return {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#39;'
        }[s];
    });
}
