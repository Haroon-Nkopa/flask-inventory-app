document.addEventListener('DOMContentLoaded', () => {
    const addProductForm = document.getElementById('addProductForm');
    
    if (addProductForm) {
        addProductForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData.entries());

            // Data conversion
            data.price = parseFloat(data.price) || 0;
            data.batch_size = parseInt(data.batch_size) || 1;
            data.batch_price = parseFloat(data.batch_price) || 0;
            data.lower_bound = parseInt(data.lower_bound) || 0;

            try {
                const response = await fetch('/api/products', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (response.ok) {
                    alert(result.message);
                    // Redirect back to the shop using the URL path
                    window.location.href = "/shop"; 
                } else {
                    alert("Error: " + result.error);
                }
            } catch (error) {
                alert("Failed to connect to the server. Check your connection.");
            }
        });
    }
});
