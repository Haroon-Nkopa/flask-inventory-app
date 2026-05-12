document.addEventListener('DOMContentLoaded', async () => {
    const header = document.getElementById('history-header');
    const body = document.getElementById('history-body');

    try {
        const response = await fetch('/api/stock-history');
        const data = await response.json();

        if (!data.dates || data.dates.length === 0) {
            body.innerHTML = '<tr><td class="text-center">No history records found.</td></tr>';
            return;
        }

        // 1. Build Header Row (Matches your original <th> logic)
        let headerHtml = '<tr><th>Product</th>';
        data.dates.forEach(date => {
            headerHtml += `<th>${date}</th>`;
        });
        headerHtml += '</tr>';
        header.innerHTML = headerHtml;

        // 2. Build Body Rows (Matches your original .get(date, '-') logic)
        body.innerHTML = '';
        data.stock_data.forEach(product => {
            let rowHtml = `<tr><td>${product.name}</td>`;
            data.dates.forEach(date => {
                const qty = product.history[date] !== undefined ? product.history[date] : '-';
                rowHtml += `<td>${qty}</td>`;
            });
            rowHtml += '</tr>';
            body.insertAdjacentHTML('beforeend', rowHtml);
        });

    } catch (error) {
        console.error("Error:", error);
        body.innerHTML = '<tr><td colspan="100%" class="text-center text-danger">Failed to load history data.</td></tr>';
    }
});
