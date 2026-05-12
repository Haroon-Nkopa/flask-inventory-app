document.addEventListener('DOMContentLoaded', function() {
    loadSalesHistory();
});

async function loadSalesHistory() {
    const accordion = document.getElementById('salesAccordion');
    
    try {
        const response = await fetch(SALES_CONFIG.apiUrl);
        if (!response.ok) throw new Error("Failed to fetch sales");
        
        const data = await response.json();
        const sales = data.sales;

        if (sales.length === 0) {
            accordion.innerHTML = `
                <div class="card p-5 text-center">
                    <div class="opacity-50">
                        <h1 class="display-1">📭</h1>
                        <h4>No sales recorded yet</h4>
                        <a href="/pos" class="btn btn-primary mt-3">Go to POS Terminal</a>
                    </div>
                </div>`;
            return;
        }

        // Clear loading spinner and build accordion
        accordion.innerHTML = sales.map(sale => `
            <div class="accordion-item">
              <h2 class="accordion-header">
                <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#sale${sale.id}">
                  <div class="d-flex justify-content-between align-items-center w-100 me-3">
                    <div>
                      <span class="fw-bold text-success">#${sale.id}</span>
                      <span class="ms-3 text-secondary">${sale.timestamp}</span>
                    </div>
                    <div class="text-end">
                      <span class="me-3 status-badge">Paid</span>
                      <span class="fs-5 fw-bold text-success">R ${sale.total.toFixed(2)}</span>
                    </div>
                  </div>
                </button>
              </h2>
              <div id="sale${sale.id}" class="accordion-collapse collapse" data-bs-parent="#salesAccordion">
                <div class="accordion-body">
                  <div class="table-responsive">
                    <table class="table table-dark table-hover align-middle">
                      <thead class="text-secondary border-bottom border-secondary">
                        <tr>
                          <th>Product Item</th>
                          <th class="text-center">Qty</th>
                          <th class="text-end">Unit Price</th>
                          <th class="text-end">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        ${sale.items.map(item => `
                          <tr>
                            <td>
                              <div class="fw-bold">${item.product_name}</div>
                              <small class="text-muted">${item.category}</small>
                            </td>
                            <td class="text-center">${item.quantity}</td>
                            <td class="text-end">R ${item.unit_price.toFixed(2)}</td>
                            <td class="text-end fw-bold">R ${item.total_price.toFixed(2)}</td>
                          </tr>
                        `).join('')}
                      </tbody>
                      <tfoot>
                        <tr class="border-top border-secondary">
                          <td colspan="3" class="text-end text-secondary uppercase fw-bold pt-3">Total Amount:</td>
                          <td class="text-end text-success fs-5 fw-bold pt-3">R ${sale.total.toFixed(2)}</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                </div>
              </div>
            </div>
        `).join('');

    } catch (error) {
        accordion.innerHTML = '<p class="text-center text-danger py-5">Error loading history. Check your connection.</p>';
        console.error(error);
    }
}
