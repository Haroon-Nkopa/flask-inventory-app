let cart = {};

// 1. Initial Load: Fetch products as soon as the page is ready
document.addEventListener('DOMContentLoaded', function() {
    loadProducts();
});

async function loadProducts() {
    const tableBody = document.getElementById('productTable');
    
    try {
        const response = await fetch(POS_CONFIG.productsUrl);
        if (!response.ok) throw new Error("Failed to fetch");
        
        const products = await response.json();
        
        if (products.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="4" class="text-center py-4">No products found.</td></tr>';
            return;
        }

        // Render rows dynamically
        tableBody.innerHTML = products.map(p => `
            <tr class="product-row" onclick="addToCart('${p.id}', '${p.name}', ${p.price})">
                <td><strong>${p.name}</strong></td>
                <td><span class="badge bg-secondary">${p.category || 'General'}</span></td>
                <td>R ${parseFloat(p.price).toFixed(2)}</td>
                <td class="text-end"><button class="btn btn-sm btn-success">+</button></td>
            </tr>
        `).join('');

    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="4" class="text-center text-danger py-4">Error loading products. Check connection.</td></tr>';
    }
}

// 2. Search Functionality (Stays the same)
document.getElementById('searchBar').addEventListener('keyup', function() {
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll('#productTable tr');
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
});

// 3. Cart Logic (Simplified for better performance)
function addToCart(id, name, price) {
    if (cart[id]) {
        cart[id].qty += 1;
    } else {
        cart[id] = { name: name, price: price, qty: 1 };
    }
    renderCart();
}

function removeFromCart(id) {
    delete cart[id];
    renderCart();
}

function renderCart() {
    const container = document.getElementById('cartItems');
    container.innerHTML = '';
    let total = 0;

    const items = Object.keys(cart);
    if (items.length === 0) {
        container.innerHTML = '<tr><td colspan="4" class="text-muted text-center py-4">Cart is empty</td></tr>';
    }

    items.forEach(id => {
        let item = cart[id];
        let rowTotal = item.price * item.qty;
        total += rowTotal;

        container.innerHTML += `
        <tr>
          <td>${item.name}</td>
          <td>${item.qty}</td>
          <td>R ${rowTotal.toFixed(2)}</td>
          <td class="text-end"><button class="btn btn-sm btn-outline-danger" onclick="removeFromCart('${id}')">×</button></td>
        </tr>`;
    });

    document.getElementById('subtotal').innerText = `R ${total.toFixed(2)}`;
    document.getElementById('grandTotal').innerText = `R ${total.toFixed(2)}`;
}

// 4. Checkout Logic (Updated to use ID selectors for reliability)
async function checkout() {
    const checkoutBtn = document.getElementById('checkoutBtn');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('btnSpinner');
    
    if (Object.keys(cart).length === 0) {
        alert("Cart is empty!");
        return;
    }

    if (!navigator.onLine) {
        alert("Cannot process transaction while offline.");
        return;
    }

    const orderData = Object.keys(cart).map(id => ({
        product_id: id,
        quantity: cart[id].qty
    }));

    // UI Loading State
    checkoutBtn.disabled = true;
    if (btnText) btnText.textContent = "Processing...";
    if (spinner) spinner.classList.remove('d-none');

    try {
        const response = await fetch(POS_CONFIG.checkoutUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ items: orderData })
        });

        const result = await response.json();

        if (response.ok) {
            alert("Transaction Successful!");
            cart = {};
            renderCart();
        } else {
            alert("⚠️ " + (result.error || "Transaction failed"));
        }
    } catch (error) {
        alert("Connection error. Please check your network.");
    } finally {
        checkoutBtn.disabled = false;
        if (btnText) btnText.textContent = "Complete Transaction";
        if (spinner) spinner.classList.add('d-none');
    }
}
