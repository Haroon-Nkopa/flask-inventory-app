document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch('/api/summary');
        const data = await response.json();

        if (data.error) {
            document.getElementById('summary-alert').classList.replace('alert-success', 'alert-warning');
            document.getElementById('summary-alert').innerText = data.error;
            document.getElementById('summary-alert').classList.remove('d-none');
            return;
        }

        // Fill Stats
        document.getElementById('summary-alert').innerText = data.message;
        document.getElementById('summary-alert').classList.remove('d-none');
        document.getElementById('actual-revenue').innerText = `R ${data.total_revenue.toFixed(2)}`;
        document.getElementById('potential-profit').innerText = `R ${data.potential_profit.toFixed(2)}`;

        // Load Tables (Stock Out, Fast Selling, Top Earning)
        renderTables(data);

        // Render Chart (Your exact teal styling)
        const ctx = document.getElementById('salesChart').getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.chart.labels,
                datasets: [{
                    label: 'Daily Sales (R)',
                    data: data.chart.values,
                    borderColor: '#0dcaf0',
                    backgroundColor: 'rgba(13, 202, 240, 0.2)',
                    tension: 0.4,
                    fill: true,
                    pointRadius: 5
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { labels: { color: '#fff' } } },
                scales: {
                    x: { ticks: { color: '#ccc' }, grid: { color: '#333' } },
                    y: { ticks: { color: '#ccc' }, grid: { color: '#333' } }
                }
            }
        });
    } catch (e) {
        console.error("Summary failed to load:", e);
    }
});

function renderTables(data) {
    const container = document.getElementById('tables-container');
    let html = '';

    // Stock Out Table
    if (data.stock_out && data.stock_out.length > 0) {
        html += `
        <div class="alert alert-warning mt-4 text-start">
            <h5 class="mb-3 text-center">⚠️ Stock Out Products (${data.stock_out.length})</h5>
            <table class="table table-dark table-striped table-bordered">
                <thead><tr><th>Product</th><th>Category</th><th>Price (R)</th></tr></thead>
                <tbody>${data.stock_out.map(p => `<tr><td>${p.name}</td><td>${p.category || '-'}</td><td>${p.price.toFixed(2)}</td></tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    // Fast Selling Table
    if (data.fast_selling && data.fast_selling.length > 0) {
        html += `
        <div class="mt-5">
            <h4 class="text-warning mb-3">🔥 Fast Selling Products</h4>
            <table class="table table-dark table-striped table-bordered">
                <thead><tr><th>Product</th><th>Category</th><th>Units Sold</th></tr></thead>
                <tbody>${data.fast_selling.map(p => `<tr><td>${p.name}</td><td>${p.category || '-'}</td><td><strong>${p.sold_qty}</strong></td></tr>`).join('')}</tbody>
            </table>
        </div>`;
    }

    container.innerHTML = html;
}


