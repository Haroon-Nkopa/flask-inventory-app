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
 * Communicates with the backend route API to fetch discrepancy metrics
 * and isolates timeline blocks on row click bindings.
 */
function fetchInventoryDiscrepancies() {
    const tableBody = document.getElementById('audit-discrepancy-body');
    const tableContainer = document.getElementById('audit-discrepancy-container');

    // Display basic loader state
    tableBody.innerHTML = `
        <tr>
            <td colspan="5" class="text-info py-4 text-center">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Analyzing live balances against physical count ledger tracks...
            </td>
        </tr>
    `;

    // Remove prior lookup layouts safely
    const oldTimeline = document.getElementById('audit-timeline-narrative-block');
    if (oldTimeline) oldTimeline.remove();

    const oldSummary = document.getElementById('audit-loss-summary-block');
    if (oldSummary) oldSummary.remove();

    fetch('/api/inventory/discrepancies', {
        method: 'GET',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP Error Status: ${response.status}`);
        return response.json();
    })
    .then(data => {
        // ENGINE TRACE LOG: Open your browser inspect terminal (F12) to see exactly what keys your Python app outputs
        console.log("REAL DATABASE API RAW DATA STREAM:", data);

        tableBody.innerHTML = ''; 

        // Handle structural payload parsing dynamically
        const rawRecords = data.tabular_data || data.losses || data.display || data;
        const records = Array.isArray(rawRecords) ? rawRecords : 
                        Object.keys(rawRecords || {}).map(id => ({ product_id: id, ...rawRecords[id] }));

        if (records.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-success py-4 fw-bold text-center">
                        ✅ Perfect Match! All physical counts match your live system balances.
                    </td>
                </tr>
            `;
            return;
        }

        let totalLossSum = 0;
        let missingProductsPointsHtml = '';
        let hasLosses = false;

        // 1. RENDER TABULAR RECORDS WITH CLICK EVENT TRAPS
        records.forEach(item => {
            const liveQty = Number(item.live_quantity) || 0;
            const auditedQty = Number(item.audited_quantity) || 0;
            const difference = auditedQty - liveQty; 
           
            const sellingPrice = Number(item.selling_price) || Number(item.price) || 0;
          
            if (difference < 0) {
                hasLosses = true;
                const missingCount = Math.abs(difference); 
                const productLossValue = missingCount * sellingPrice;
                
                totalLossSum += productLossValue;

                missingProductsPointsHtml += `
                    <li class="mb-1 text-light">
                        We have <strong>${missingCount} ${escapeHtml(item.product_name)}</strong> missing, that's <strong>R${productLossValue.toFixed(2)}</strong> lost
                    </li>
                `;
            }

            const row = document.createElement('tr');
            row.style.cursor = 'pointer';
            row.title = `Click to inspect ${item.product_name} timelines`;
            row.setAttribute('data-product-id', item.product_id);
            
            const badgeClass = difference < 0 ? 'badge bg-danger' : 'badge bg-warning text-dark';
            const signPrefix = difference > 0 ? '+' : '';

            row.innerHTML = `
                <td><code>#${item.product_id}</code></td>
                <td class="text-start fw-semibold">${escapeHtml(item.product_name)}</td>
                <td>${liveQty}</td>
                <td>${auditedQty}</td>
                <td>
                    <span class="${badgeClass}">${signPrefix}${difference}</span>
                </td>
            `;

            row.addEventListener('click', function() {
                document.querySelectorAll('#audit-discrepancy-body tr').forEach(r => r.classList.remove('table-info', 'text-dark'));
                this.classList.add('table-info', 'text-dark');
                
                showSpecificProductTimeline({
                    product_id: item.product_id,
                    product_name: item.product_name
                });
            });

            tableBody.appendChild(row);
        });

        // 2. APPEND THE REQUESTED LOSS SUMMARY LIST AT THE BOTTOM OF THE CONTAINER DIV
        if (hasLosses) {
            const startDateStr = data.last_audit_date || '{lasted date}';
            const endDateStr = data.today_date || '{today}';

            const summaryBlock = document.createElement('div');
            summaryBlock.id = 'audit-loss-summary-block';
            summaryBlock.className = 'card-footer bg-dark border-top border-danger p-3 mt-3 text-start';

            summaryBlock.innerHTML = `
                <h6 class="text-danger fw-bold mb-2">📉 Discrepancy Breakdown & Stock Loss Points:</h6>
                <p class="text-secondary small mb-2 fst-italic">
                    Rule: Using variance evaluation. If difference is less than 0, then we have that much lost products.
                </p>
                <ul class="mb-3 ps-3">
                    ${missingProductsPointsHtml}
                </ul>
                <div class="fw-semibold text-warning border-top border-secondary pt-2">
                    From ${startDateStr} to ${endDateStr} there is <span class="text-danger fw-bold fs-5">R${totalLossSum.toFixed(2)}</span> missing.
                </div>
            `;
            
            tableContainer.appendChild(summaryBlock);
        }

        // 3. BUILD TIMELINE ELEMENTS
        const timelineBlock = document.createElement('div');
        timelineBlock.id = 'audit-timeline-narrative-block';
        timelineBlock.className = 'card-body border-top border-secondary p-3 text-start bg-dark';

        let timelineHtml = `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <h5 class="text-info mb-0">🕒 Operational Employee Sales Audit Trails</h5>
                <div id="timeline-action-container"></div>
            </div>
            <p id="timeline-placeholder-text" class="text-secondary small mb-3">💡 Click any product row above to isolate its precise timeline narrative text.</p>
            
            <div id="merge-form-panel" class="d-none border border-warning rounded p-3 mb-3 bg-black"></div>
        `;

        records.forEach(pMeta => {
            const prodName = pMeta.product_name;
            const prodId = pMeta.product_id;
            const phrases = data.timeline_data ? (data.timeline_data[prodName] || []) : [];

            timelineHtml += `
                <div class="product-timeline-wrapper d-none" id="timeline-prod-${prodId}">
                    <strong class="text-warning small text-uppercase">📦 ${escapeHtml(prodName)}</strong>
                    <ul class="list-group list-group-flush mt-1 mb-2 ps-2">
            `;

            if (phrases.length === 0) {
                timelineHtml += `
                    <li class="list-group-item bg-dark text-muted border-0 py-1 small ps-0 fst-italic">
                        No sales transactions were logged after this product's last count stamp.
                    </li>
                `;
            } else {
                phrases.forEach(phrase => {
                    timelineHtml += `
                        <li class="list-group-item bg-dark text-light border-0 py-1 small ps-0">
                            • ${escapeHtml(phrase)}
                        </li>
                    `;
                });
            }

            timelineHtml += `</ul></div>`;
        });

        timelineBlock.innerHTML = timelineHtml;
        tableContainer.appendChild(timelineBlock);
    })
    .catch(error => {
        console.error('Audit Fetch Failure Trace:', error);
        tableBody.innerHTML = `
            <tr>
                <td colspan="5" class="text-danger py-4 text-center">
                    ⚠️ Failed to run discrepancy report. Check system engine console.
                </td>
            </tr>
        `;
    });
}



/**
 * Isolates and changes display states for the target timeline and binds the action panel
 */
function showSpecificProductTimeline(item) {
    const placeholder = document.getElementById('timeline-placeholder-text');
    if (placeholder) placeholder.classList.add('d-none');

    const formPanel = document.getElementById('merge-form-panel');
    if (formPanel) formPanel.classList.add('d-none');

    document.querySelectorAll('.product-timeline-wrapper').forEach(block => {
        block.classList.add('d-none');
    });

    const targetBlock = document.getElementById(`timeline-prod-${item.product_id}`);
    if (targetBlock) {
        targetBlock.classList.remove('d-none');
        targetBlock.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    const actionContainer = document.getElementById('timeline-action-container');
    if (actionContainer) {
        actionContainer.innerHTML = `
            <button class="btn btn-sm btn-warning fw-bold shadow-sm" id="initiate-merge-btn">
                🛠️ Merge Variance for ${escapeHtml(item.product_name)}
            </button>
        `;

        document.getElementById('initiate-merge-btn').addEventListener('click', () => {
            renderMergeForm(item);
        });
    }
}

/**
 * Renders the internal interactive override framework form within the narrative panel
 */
function renderMergeForm(item) {
    const formPanel = document.getElementById('merge-form-panel');
    
    document.querySelectorAll('.product-timeline-wrapper').forEach(block => block.classList.add('d-none'));
    
    formPanel.innerHTML = `
        <h6 class="text-warning mb-2 fw-bold">🔄 Reconcile Discrepancy Flow</h6>
        <p class="text-light small mb-3">
            ⚠️ Please recount the physical stock layout of <b class="text-info">${escapeHtml(item.product_name)}</b> to discover actual final inventory assets before saving.
        </p>
        
        <form id="variance-submit-form">
            <div class="mb-3">
                <label class="form-label text-secondary small fw-bold">ACTUAL ${escapeHtml(item.product_name).toUpperCase()} NUMBER IN STOCK:</label>
                <input type="number" class="form-control bg-dark text-white border-secondary" id="merge-actual-count" required min="0" placeholder="Enter true count value">
            </div>
            
            <div class="mb-3">
                <label class="form-label text-secondary small fw-bold">REASON FOR MERGING / OVERRIDING:</label>
                <textarea class="form-control bg-dark text-white border-secondary" id="merge-reason" rows="2" required placeholder="E.g., Spillage, tracking offset, theft, unlogged transaction"></textarea>
            </div>
            
            <div class="d-flex gap-2">
                <button type="submit" class="btn btn-sm btn-success px-3 fw-bold">Confirm Database Merge Action</button>
                <button type="button" class="btn btn-sm btn-outline-secondary text-light" id="cancel-merge-btn">Cancel</button>
            </div>
        </form>
    `;

    formPanel.classList.remove('d-none');
    formPanel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        // Handle form submissions dynamically
    document.getElementById('variance-submit-form').addEventListener('submit', function(e) {
        executeVarianceMerge(e, item.product_id);
    });

    document.getElementById('cancel-merge-btn').addEventListener('click', () => {
        formPanel.classList.add('d-none');
        document.getElementById(`timeline-prod-${item.product_id}`).classList.remove('d-none');
    });
}

/**
 * Dispatches payload properties back to the system route engine API
 */
function executeVarianceMerge(event, productId) {
    event.preventDefault();

    const actualCount = document.getElementById('merge-actual-count').value;
    const mergeReason = document.getElementById('merge-reason').value;

    fetch('/api/inventory/merge-variance', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify({
            product_id: parseInt(productId, 10),
            actual_count: parseInt(actualCount, 10),
            reason: mergeReason
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(err => { throw new Error(err.message || 'Server error'); });
        }
        return response.json();
    })
    .then(data => {
        alert(`✅ Success: ${data.message}`);
        fetchInventoryDiscrepancies();
    })
    .catch(error => {
        console.error('Merge Error Trace:', error);
        alert(`❌ Failed to complete operation: ${error.message}`);
    });
}

/**
 * Utility tool to prevent XSS injection risks safely
 */
function escapeHtml(string) {
    return String(string).replace(/[&<>"']/g, s => ({
        '&': '&amp;', 
        '<': '&lt;', 
        '>': '&gt;', 
        '"': '&quot;', 
        "'": '&#39;'
    }[s]));
}


