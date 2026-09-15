document.addEventListener('DOMContentLoaded', async () => {
    const list = document.getElementById('stock-list');
    const form = document.getElementById('stockTakeForm');
    const searchInput = document.getElementById('productSearchInput'); // 🔍 Search element reference

    try {
        // Fetch products from your dashboard API
        const res = await fetch('/api/stock-take-products');
        const products = await res.json();
        
        // Generates item count inputs accompanied by hidden note sub-row drawers
        list.innerHTML = products.map(p => `
            <tr data-product-id="${p.id}" data-product-name="${p.name.toLowerCase()}">
                <td class="text-capitalize text-start ps-4 fw-bold">${p.name}</td>
                <td>
                    <div class="d-flex align-items-center justify-content-center gap-2 mx-auto" style="max-width: 180px;">
                        <input type="number" name="${p.id}" class="form-control text-center quantity-input" min="0" value="0" required>
                        <button type="button" class="btn btn-sm btn-outline-secondary toggle-note-btn fw-bold" title="Add Audit Note">+</button>
                    </div>
                </td>
            </tr>
            <tr id="note-row-${p.id}" class="d-none bg-dark bg-opacity-25 border-0" data-note-for="${p.id}">
                <td colspan="2" class="p-2 border-top-0">
                    <div class="px-4 pb-2">
                        <input type="text" class="form-control form-control-sm bg-dark text-light border-secondary notes-input" placeholder="Optional audit remark for ${p.name}...">
                    </div>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        console.error("Failed to render product list rows:", e);
        list.innerHTML = '<tr><td colspan="2">Error loading products.</td></tr>';
    }

    // 🔍 REAL-TIME FILTER LOGIC
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const productRows = list.querySelectorAll('tr[data-product-id]');

            productRows.forEach(row => {
                const productName = row.getAttribute('data-product-name') || '';
                const pId = row.getAttribute('data-product-id');
                const noteRow = document.getElementById(`note-row-${pId}`);
                
                if (productName.includes(query)) {
                    row.classList.remove('d-none');
                    if (noteRow && noteRow.getAttribute('data-explicit-open') === 'true') {
                        noteRow.classList.remove('d-none');
                    }
                } else {
                    row.classList.add('d-none');
                    if (noteRow) {
                        noteRow.classList.add('d-none');
                    }
                }
            });
        });
    }

    // Dynamic click listener mapping the "+" action triggers
    list.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('toggle-note-btn')) {
            const parentRow = e.target.closest('tr[data-product-id]');
            const pId = parentRow.getAttribute('data-product-id');
            const targetNoteRow = document.getElementById(`note-row-${pId}`);

            if (targetNoteRow.classList.contains('d-none')) {
                targetNoteRow.classList.remove('d-none');
                targetNoteRow.setAttribute('data-explicit-open', 'true');
                e.target.textContent = '✕';
                e.target.classList.replace('btn-outline-secondary', 'btn-danger');
                targetNoteRow.querySelector('.notes-input').focus();
            } else {
                targetNoteRow.classList.add('d-none');
                targetNoteRow.removeAttribute('data-explicit-open');
                e.target.textContent = '+';
                e.target.classList.replace('btn-danger', 'btn-outline-secondary');
            }
        }
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const data = {};

        // Loop manual row instances
        const productRows = list.querySelectorAll('tr[data-product-id]');
        productRows.forEach(row => {
            const pId = row.getAttribute('data-product-id');
            const qty = parseInt(row.querySelector('.quantity-input').value) || 0;
            
            data[pId] = qty;

            const noteRow = document.getElementById(`note-row-${pId}`);
            if (noteRow && noteRow.getAttribute('data-explicit-open') === 'true') {
                const noteVal = noteRow.querySelector('.notes-input').value.trim();
                if (noteVal) {
                    data[`notes_${pId}`] = noteVal;
                }
            }
        });

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
            let errorMsg = result.error || "An error occurred taking stock.";
            if (result.details) {
                errorMsg += "\n\n" + result.details.join("\n");
            }
            alert(errorMsg);
        }
    });
});
