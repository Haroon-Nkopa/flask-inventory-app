// StockWise Global API Helpers
async function apiRequest(url, method = 'GET', data = null) {
    const options = {
        method,
        headers: { 'Content-Type': 'application/json' }
    };
    if (data) options.body = JSON.stringify(data);

    try {
        const response = await fetch(url, options);
        return await response.json();
    } catch (error) {
        console.error('API Error:', error);
        return { error: 'Connection failed' };
    }
}

document.addEventListener('click', function(e) {
    // 1. Look for the button with the ID 'logoutBtn'
    const btn = e.target.closest('#logoutBtn');
    
    if (btn) {
        e.preventDefault();
        
        // 2. Get the URL from the data-url attribute
        const logoutUrl = btn.getAttribute('data-url');
        
        // 3. Perform the POST request
        fetch(logoutUrl, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        })
        .then(res => res.json())
        .then(data => {
            // 4. Redirect to the login page sent by the server
            window.location.href = data.redirect; 
        })
        .catch(err => console.error("Logout error:", err));
    }
});



document.addEventListener('DOMContentLoaded', function() {
    const printBtn = document.getElementById('printSheetBtn');
    
    // This code only sets up the "listener" - it does NOT download anything yet
    if (printBtn) {
        printBtn.addEventListener('click', async function(e) {
            e.preventDefault(); // Stop any default link behavior

            // 1. Check for Internet Connection (PWA Style)
            if (!navigator.onLine) {
                alert("Cannot download stock sheet without internet access.");
                return;
            }

            const url = this.getAttribute('data-url');
            print(url)
            const btnText = document.getElementById('printBtnText');
            const spinner = document.getElementById('printBtnSpinner');

            // 2. UI Feedback: Show loading state so user knows to wait
            printBtn.disabled = true;
            if (btnText) btnText.textContent = 'Generating PDF...';
            if (spinner) spinner.classList.remove('d-none');

            try {
                // 3. Fetch the file in the background (stays on the dashboard)
                const response = await fetch(url);
                
                if (!response.ok) throw new Error('PDF generation failed');

                // Convert response to a blob (the actual file data)
                const blob = await response.blob();
                
                // 4. Trigger the download without moving from the page
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = downloadUrl;
                a.download = "stock_sheet.pdf"; 
                
                document.body.appendChild(a);
                a.click();
                
                // 5. Cleanup
                window.URL.revokeObjectURL(downloadUrl);
                a.remove();

            } catch (error) {
                console.error(error);
                alert("Something went wrong while generating the PDF.");
            } finally {
                // 6. Reset UI back to original state
                printBtn.disabled = false;
                if (btnText) btnText.textContent = '🖨️ Print Stock Sheet';
                if (spinner) spinner.classList.add('d-none');
            }
        });
    }
});
