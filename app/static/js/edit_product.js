document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('productSearch');
    const datalist = document.getElementById('productListOptions');
    const formFieldsContainer = document.getElementById('formFieldsContainer');
    const editForm = document.getElementById('editProductForm');
    
    // Form Inputs References
    const idInput = document.getElementById('edit_product_id');
    const nameInput = document.getElementById('name');
    const categoryInput = document.getElementById('category');
    const priceInput = document.getElementById('price');
    const sizeInput = document.getElementById('size');
    const batchSizeInput = document.getElementById('batch_size');
    const batchPriceInput = document.getElementById('batch_price');
    const lowerBoundInput = document.getElementById('lower_bound');
    const batchNumberInput = document.getElementById('batch_number');
    const submitBtn = document.getElementById('submitUpdateBtn');

    // 1. Detect item selections inside searchable input wrapper
    searchInput.addEventListener('input', (e) => {
        const selectedValue = e.target.value;
        const options = Array.from(datalist.options);
        
        // Match chosen string against options list
        const matchedOption = options.find(opt => opt.value === selectedValue);

        if (matchedOption) {
            // Unlock fields and move values in dynamically
            formFieldsContainer.classList.remove('opacity-50', 'pointer-events-none');
            
            const inputs = formFieldsContainer.querySelectorAll('input, button');
            inputs.forEach(el => el.removeAttribute('disabled'));

            // Populate text parameters reading DOM storage
            idInput.value = matchedOption.getAttribute('data-id');
            nameInput.value = selectedValue;
            categoryInput.value = matchedOption.getAttribute('data-category') || '';
            priceInput.value = parseFloat(matchedOption.getAttribute('data-price')) || 0;
            sizeInput.value = matchedOption.getAttribute('data-size') || '';
            batchSizeInput.value = parseInt(matchedOption.getAttribute('data-batch-size')) || 1;
            batchPriceInput.value = parseFloat(matchedOption.getAttribute('data-batch-price')) || 0;
            lowerBoundInput.value = parseInt(matchedOption.getAttribute('data-lower-bound')) || 0;
            batchNumberInput.value = matchedOption.getAttribute('data-batch-number') || '';
        } else {
            // Keep locked if input doesn't match an option
            formFieldsContainer.classList.add('opacity-50', 'pointer-events-none');
            const inputs = formFieldsContainer.querySelectorAll('input, button');
            inputs.forEach(el => {
                if(el.id !== 'productSearch') el.setAttribute('disabled', 'true');
            });
        }
    });

    // 2. Submit modifications back to PUT endpoint API interface
    if (editForm) {
        editForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const productId = idInput.value;

            if (!productId) {
                alert("Please select a valid product first.");
                return;
            }

            const formData = new FormData(editForm);
            const data = Object.fromEntries(formData.entries());

            // Convert formats matching database schema definitions
            data.price = parseFloat(data.price) || 0;
            data.batch_size = parseInt(data.batch_size) || 1;
            data.batch_price = parseFloat(data.batch_price) || 0;
            data.lower_bound = parseInt(data.lower_bound) || 0;

            try {
                const response = await fetch(`/api/products/${productId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });

                const result = await response.json();
                if (response.ok) {
                    alert(result.message);
                    window.location.href = "/shop"; // Route back to inventory matrix
                } else {
                    alert("Error: " + result.error);
                }
            } catch (error) {
                alert("Failed to connect to server. Check network connection.");
            }
        });
    }
});
