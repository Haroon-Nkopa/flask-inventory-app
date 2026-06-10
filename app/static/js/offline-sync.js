console.log("🟢 offline-sync.js: Start loading...");

let localDB;  //making lacalDb variable globally abauilable. 
let isSyncing = false; // Global lock to prevent double-syncing

// Initialize IndexedDB Database
function initOfflineDB() {
    const dbRequest = indexedDB.open('StockWiseOfflineDB', 1);

    dbRequest.onupgradeneeded = (e) => {
        localDB = e.target.result;
        if (!localDB.objectStoreNames.contains('pending_transactions')) {
            localDB.createObjectStore('pending_transactions', { keyPath: 'id', autoIncrement: true });
        }
    };

    dbRequest.onsuccess = (e) => { 
        localDB = e.target.result; 
        // Try syncing any pending transactions right away on page load
        syncOfflineTransactions();
    };

    dbRequest.onerror = (e) => {
        console.error("IndexedDB error:", e.target.error);
    };
}


function saveTransactionLocally(orderData) {
    if (!localDB) {
        alert("Local database not ready. Cannot save offline transaction.");
        return;
    }
    const transaction = localDB.transaction(['pending_transactions'], 'readwrite');
    const store = transaction.objectStore('pending_transactions');
    store.add({ items: orderData, timestamp: new Date().toISOString() });
    
    alert("⚠️ Network issue or offline. Transaction saved locally! It will sync once you are back online.");
    cart = {};
    renderCart();
}


async function syncOfflineTransactions() {
    // 1. Guard against concurrent sync processes or lack of connection
    if (!navigator.onLine || !localDB || isSyncing) return;
    isSyncing = true;

    console.log("🔄 Background sync checked. Inspecting local queue...");

    try {
        // 2. Fetch all pending entries using a short-lived read-only transaction
        const getRecords = () => {
            return new Promise((resolve, reject) => {
                const tx = localDB.transaction(['pending_transactions'], 'readonly');
                const store = tx.objectStore('pending_transactions');
                const request = store.getAll();
                request.onsuccess = () => resolve(request.result);
                request.onerror = () => reject(request.error);
            });
        };

        const pendingSales = await getRecords();
        if (!pendingSales || pendingSales.length === 0) {
            console.log("✅ No pending offline sales found.");
            isSyncing = false;
            return;
        }

        console.log(`📦 Found ${pendingSales.length} offline transactions. Starting atomic sync...`);
        const targetUrl = (typeof POS_CONFIG !== 'undefined') ? POS_CONFIG.checkoutUrl : '/api/pos/checkout';
        // 3. Process each record using an isolated, independent transaction block
        for (const sale of pendingSales) {
            try {
                const response = await fetch(targetUrl, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ 
                        items: sale.items,
                        timestamp: sale.timestamp 
                    })
                });

                const result = await response.json();

                if (response.ok) {
                    // Open a dedicated, short-lived write transaction ONLY after server confirmation
                    await new Promise((resolve, reject) => {
                        const deleteTx = localDB.transaction(['pending_transactions'], 'readwrite');
                        const deleteStore = deleteTx.objectStore('pending_transactions');
                        const deleteReq = deleteStore.delete(sale.id);
                        
                        deleteReq.onsuccess = () => resolve();
                        deleteReq.onerror = () => reject(deleteReq.error);
                    });
                    console.log(`✨ Transaction ID ${sale.id} successfully saved to server and cleared locally.`);
                } else {
                    console.error(`❌ Server rejected sale ID ${sale.id}:`, result.error);
                    
                    // Session expired during offline interval
                    if (response.status === 401 || (result.error && result.error.includes("shop"))) {
                        alert("⚠️ Background sync halted due to session expiration. Please refresh and log in again.");
                        break; 
                    }
                }
            } catch (err) {
                console.error("🛑 Sync batch paused. Server network connection lost mid-process:", err);
                break; // Stop iterating if the network drops out again
            }
        }
    } catch (criticalError) {
        console.error("Critical error inside storage sync controller:", criticalError);
    } finally {
        isSyncing = false; // Release the execution lock
    }
}


// Listeners to execute automatic transaction sync
window.addEventListener('online', syncOfflineTransactions);


document.addEventListener('visibilitychange', () => {
    if (!document.hidden) {
        syncOfflineTransactions();
    }
});


setInterval(syncOfflineTransactions, 3000);