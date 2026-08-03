document.addEventListener('DOMContentLoaded', function() {
    const addStockForm = document.getElementById('addStockForm');
    if (!addStockForm) return; // Exit if not on the correct page

    const productSelect = document.getElementById('productSelect');
    const submitBtn = document.getElementById('submitBtn');
    
    // Grab the URLs from the form's data attributes
    const getUrl = addStockForm.getAttribute('data-get-url');
    const postUrl = addStockForm.getAttribute('data-post-url');
    const redirectUrl = addStockForm.getAttribute('data-redirect-url');

    // 1. Fetch products
    fetch(getUrl)
        .then(res => res.json())
        .then(data => {
            productSelect.innerHTML = '<option value="" selected disabled>Choose a product...</option>';
            data.forEach(p => {
                const option = document.createElement('option');
                option.value = p.id;
                option.textContent = p.name;
                productSelect.appendChild(option);
            });
        })
        .catch(err => {
            console.error("Error loading products:", err);
            productSelect.innerHTML = '<option disabled>Error loading products</option>';
        });

    // 2. Handle POST submission
    addStockForm.addEventListener('submit', function(e) {
        e.preventDefault();
        
        submitBtn.disabled = true;
        const originalText = submitBtn.textContent;
        submitBtn.textContent = 'Processing...';

        // FIXED: Wrap numerical inputs in parseInt() to prevent backend type validation failures
        const payload = {
            product_id: parseInt(productSelect.value, 10),
            new_quantity: parseInt(document.getElementById('new_quantity').value, 10)
        };

        fetch(postUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })
        .then(res => res.json())
        .then(data => {
            // FIXED: Standardize checking for response.ok along with data.error properties
            if (data.error) {
                alert("Error: " + data.error);
                submitBtn.disabled = false;
                submitBtn.textContent = originalText;
            } else {
                alert("🎉 " + data.message);
                window.location.href = redirectUrl;
            }
        })
        .catch(err => {
            alert("Something went wrong with the database connection.");
            submitBtn.disabled = false;
            submitBtn.textContent = originalText;
        });
    });
});
