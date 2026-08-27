document.addEventListener('DOMContentLoaded', function() {
    // Initial fetch of page 1 when DOM loads
    loadSalesHistory(1);
});

async function loadSalesHistory(page = 1) {
    const accordionContainer = document.getElementById('salesAccordion');
    
    // 1. Maintain visual loading state on initialization
    accordionContainer.innerHTML = `
        <div id="loadingState" class="text-center py-5">
            <div class="spinner-border text-success" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="mt-3 text-muted">Fetching transaction history...</p>
        </div>`;
    
    try {
        // Uses the dynamic API configuration route set up in your HTML file
        const url = `${SALES_CONFIG.apiUrl}?page=${page}`;
        const response = await fetch(url);
        if (!response.ok) throw new Error("Failed to fetch transaction logs");
        
        const data = await response.json();
        
        // 2. Handle empty states gracefully
        if (!data.sales || data.sales.length === 0) {
            accordionContainer.innerHTML = `
                <div class="card p-5 text-center text-secondary border-0">
                    <span class="fs-1 d-block mb-3">📭</span>
                    <h5 class="text-light">No Receipts Recorded</h5>
                    <p class="mb-0 small text-muted">Transactions completed at your POS counter will appear here.</p>
                </div>`;
            return;
        }

        // Clear loading state to ready container
        accordionContainer.innerHTML = '';

        // 3. Group Sales by Calendar Day
        // Structure: groupedByDay["26 Aug 2026"] = { sales: [...], totalRevenue: 0.00 }
        const groupedByDay = {};

        data.sales.forEach(sale => {
            // Extracts just the day segment from your backend string format (e.g., "26 Aug 2026")
            const dateParts = sale.timestamp.split(',');
            const calendarDay = dateParts[0].trim();

            if (!groupedByDay[calendarDay]) {
                groupedByDay[calendarDay] = {
                    sales: [],
                    totalRevenue: 0
                };
            }
            
            groupedByDay[calendarDay].sales.push(sale);
            groupedByDay[calendarDay].totalRevenue += sale.total;
        });

        // 4. Render Grouped Days and Accordion Panels
        // Since incoming rows are already pre-sorted descending, this maintains order
        for (const [dayString, dayData] of Object.entries(groupedByDay)) {
            
            // Create a Day Section Wrapper
            const daySection = document.createElement('div');
            daySection.className = 'day-group mb-5';

            // Visual Day Divider Component with a Daily Total indicator
            let dayHtml = `
                <div class="d-flex justify-content-between align-items-center border-bottom border-secondary border-opacity-25 pb-2 mb-3 px-1 mt-4">
                    <h5 class="text-success fw-bold mb-0 flex-grow-1">🗓️ ${dayString}</h5>
                    <div class="text-end">
                        <span class="text-secondary small me-2">Daily Revenue:</span>
                        <span class="badge bg-dark border border-success text-success fs-6 fw-bold px-3 py-1.5">
                            R ${dayData.totalRevenue.toFixed(2)}
                        </span>
                    </div>
                </div>
            `;

            // Append Accordion row blocks inside this day node
            dayData.sales.forEach((sale) => {
                const collapseId = `collapseReceipt${sale.id}`;
                const headingId = `headingReceipt${sale.id}`;
                
                const itemsRowsHtml = sale.items.map(item => `
                    <tr>
                        <td class="text-light fw-bold">${item.product_name}</td>
                        <td><span class="badge bg-secondary opacity-75">${item.category}</span></td>
                        <td class="text-center fw-bold text-info">${item.quantity}</td>
                        <td class="text-end text-muted">R ${item.unit_price.toFixed(2)}</td>
                        <td class="text-end text-success fw-bold">R ${item.total_price.toFixed(2)}</td>
                    </tr>
                `).join('');

                dayHtml += `
                    <div class="accordion-item border-0 mb-2 shadow-sm">
                        <h2 class="accordion-header" id="${headingId}">
                            <button class="accordion-button collapsed d-flex justify-content-between align-items-center pe-5" 
                                    type="button" 
                                    data-bs-toggle="collapse" 
                                    data-bs-target="#${collapseId}" 
                                    aria-expanded="false" 
                                    aria-controls="${collapseId}">
                                <div class="w-100 d-flex flex-wrap justify-content-between align-items-center gap-2 me-3">
                                    <div>
                                        <span class="fw-bold text-success me-2">#${sale.id}</span>
                                        <span class="text-secondary small">${sale.timestamp}</span>
                                    </div>
                                    <div class="text-end me-2">
                                        <span class="status-badge bg-success px-2 py-1 me-3 small">Paid</span>
                                        <strong class="text-light fs-5">R ${sale.total.toFixed(2)}</strong>
                                    </div>
                                </div>
                            </button>
                        </h2>
                        <div id="${collapseId}" class="accordion-collapse collapse" aria-labelledby="${headingId}" data-bs-parent="#salesAccordion">
                            <div class="accordion-body border-top border-dark-subtle p-0">
                                <div class="table-responsive">
                                    <table class="table table-dark table-striped table-hover align-middle px-3 mb-0">
                                        <thead>
                                            <tr class="text-secondary small border-bottom border-secondary-subtle">
                                                <th class="ps-4">Product details</th>
                                                <th>Category</th>
                                                <th class="text-center">Qty</th>
                                                <th class="text-end">Unit Cost</th>
                                                <th class="text-end pe-4">Subtotal</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            ${itemsRowsHtml}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        </div>
                    </div>`;
            });

            daySection.innerHTML = dayHtml;
            accordionContainer.appendChild(daySection);
        }

        // 5. Append pagination controls wrapper below accordion block if multi-page dataset exists
        if (data.total_pages > 1) {
            renderPagination(data.current_page, data.total_pages, accordionContainer);
        }

    } catch (error) {
        console.error("Sales UI Rendering Error:", error);
        accordionContainer.innerHTML = `
            <div class="card p-5 text-center text-danger border-0">
                <span>⚠️</span>
                <h5 class="text-danger mt-2">Failed to load sales pipeline</h5>
                <p class="text-muted small mb-0">Please check network configuration or reload your system view.</p>
            </div>`;
    }
}

function renderPagination(currentPage, totalPages, targetContainer) {
    const paginationWrapper = document.createElement('nav');
    paginationWrapper.className = 'd-flex justify-content-center mt-4';
    
    let buttonsHtml = `
        <ul class="pagination pagination-sm bg-transparent border-0 gap-1">
            <li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
                <button class="page-item btn btn-sm btn-outline-secondary px-3 text-light" onclick="loadSalesHistory(${currentPage - 1})">Previous</button>
            </li>`;

    for (let p = 1; p <= totalPages; p++) {
        buttonsHtml += `
            <li class="page-item ${p === currentPage ? 'active' : ''}">
                <button class="page-item btn btn-sm ${p === currentPage ? 'btn-success text-dark fw-bold' : 'btn-outline-secondary text-light'} px-3" onclick="loadSalesHistory(${p})">${p}</button>
            </li>`;
    }

    buttonsHtml += `
            <li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
                <button class="page-item btn btn-sm btn-outline-secondary px-3 text-light" onclick="loadSalesHistory(${currentPage + 1})">Next</button>
            </li>
        </ul>`;
        
    paginationWrapper.innerHTML = buttonsHtml;
    targetContainer.appendChild(paginationWrapper);
}
