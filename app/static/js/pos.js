console.log("🔵 pos.js: Start loading...");

let cart = {};
// Global in-memory map to store loaded product stock levels for fast UI checks
let productStockMap = {};

// 1. Initial Load: Fetch products and set up IndexedDB as soon as the page is ready
document.addEventListener('DOMContentLoaded', function() {
    initOfflineDB();
    loadProducts();
});

const checkoutBtn = document.getElementById('checkoutBtn');
if (checkoutBtn) {
    checkoutBtn.addEventListener('click', checkout);
}

async function loadProducts() {
    const tableBody = document.getElementById('productTable');
    
    try {
        const response = await fetch(POS_CONFIG.productsUrl);
        if (!response.ok) throw new Error("Failed to fetch");
        
        const products = await response.json();
        
        if (products.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="text-center py-4">No products found.</td></tr>';
            return;
        }

        // Cache stock levels in our mapping database tool
        productStockMap = {};
        products.forEach(p => {
            productStockMap[p.id] = p.live_stock;
        });

        // Render rows dynamically including a beautiful live stock indicator badge
        tableBody.innerHTML = products.map(p => {
            const stockColor = p.live_stock === 0 ? 'bg-danger' : (p.live_stock <= 5 ? 'bg-warning text-dark' : 'bg-success');
            return `
            <tr class="product-row" onclick="addToCart('${p.id}', '${p.name}', ${p.price})">
                <td><strong>${p.name}</strong></td>
                <td><span class="badge bg-secondary">${p.category || 'General'}</span></td>
                <td><span id="stock-badge-${p.id}" class="badge ${stockColor}">${p.live_stock} left</span></td>
                <td>R ${parseFloat(p.price).toFixed(2)}</td>
                <td class="text-end"><button class="btn btn-sm btn-success">+</button></td>
            </tr>`;
        }).join('');

    } catch (error) {
        tableBody.innerHTML = '<tr><td colspan="5" class="text-center text-danger py-4">Error loading products. Check connection.</td></tr>';
    }
}

// 2. Search Functionality
document.getElementById('searchBar').addEventListener('keyup', function() {
    let filter = this.value.toLowerCase();
    let rows = document.querySelectorAll('#productTable tr');
    rows.forEach(row => {
        let text = row.innerText.toLowerCase();
        row.style.display = text.includes(filter) ? '' : 'none';
    });
});

// 3. Cart Logic with Guardrails
function addToCart(id, name, price) {
    const availableStock = productStockMap[id] !== undefined ? productStockMap[id] : 0;
    const currentQtyInCart = cart[id] ? cart[id].qty : 0;

    // Direct frontend validation check before adding items to the cart
    if (currentQtyInCart >= availableStock) {
        alert(`Cannot add more ${name}. Only ${availableStock} units left in stock.`);
        return;
    }

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

// 4. Checkout Logic (Updated to securely support offline transactions)
async function checkout() {
    const checkoutBtn = document.getElementById('checkoutBtn');
    const btnText = document.getElementById('btnText');
    const spinner = document.getElementById('btnSpinner');
    
    if (Object.keys(cart).length === 0) {
        alert("Cart is empty!");
        return;
    }

    const orderData = Object.keys(cart).map(id => ({
        product_id: id,
        quantity: cart[id].qty
    }));

    // If explicitly offline, intercept early and save locally
    if (!navigator.onLine) {
        saveTransactionLocally(orderData);
        return;
    }

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
            
            // Deduct the inventory values locally in-memory right away without making a full server round-trip
            Object.keys(cart).forEach(id => {
                if (productStockMap[id] !== undefined) {
                    productStockMap[id] -= cart[id].qty;
                }
            });

            cart = {};
            renderCart();
            
            // Re-fetch or re-render product records to safely display updated badge figures
            loadProducts(); 
        } else {
            alert("⚠️ " + (result.error || "Transaction failed"));
        }
    } catch (error) {
        saveTransactionLocally(orderData);
    } finally {
        checkoutBtn.disabled = false;
        if (btnText) btnText.textContent = "Complete Transaction";
        if (spinner) spinner.classList.add('d-none');
    }
}
