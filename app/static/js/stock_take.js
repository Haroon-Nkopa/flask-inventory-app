document.addEventListener('DOMContentLoaded', async () => {
    const list = document.getElementById('stock-list');
    const form = document.getElementById('stockTakeForm');

    try {
        // Fetch products from your dashboard API
        const res = await fetch('/api/stock-take-products');
        const products = await res.json();
        
        list.innerHTML = products.map(p => `
            <tr>
                <td>${p.name}</td>
                <td>
                    <input type="number" name="${p.id}" class="form-control text-center" min="0" value="0">
                </td>
            </tr>
        `).join('');
    } catch (e) {
        list.innerHTML = '<tr><td colspan="2">Error loading products.</td></tr>';
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());

        const response = await fetch('/api/take-stock', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (response.ok) {
            alert(result.message);
            window.location.href = "/shop";
        } else {
            // Display main error + any specific problematic products
            let errorMsg = result.error;
            if (result.details) {
                errorMsg += "\n\n" + result.details.join("\n");
            }
            alert(errorMsg);
        }
    });
});
