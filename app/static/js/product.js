document.addEventListener('DOMContentLoaded', () => {
    const addProductForm = document.getElementById('addProductForm');
    const startBtn = document.getElementById("startRapidModeBtn");
    const overlay = document.getElementById("rapidEntryOverlay");
    const fieldContainer = document.getElementById("rapidFieldContainer");
    const summaryContainer = document.getElementById("rapidSummaryContainer");
    const summaryList = document.getElementById("summaryDetailsList");
    const cancelBtn = document.getElementById("rapidCancelBtn");
    const saveBtn = document.getElementById("rapidSaveBtn");

    let isRapidMode = false;
    let currentFieldIndex = 0;
    
    // Target the actual inputs directly to prevent ID duplication issues
    const rapidInputs = Array.from(document.querySelectorAll(".rapid-field input"));

    // 1. Activate Rapid Flow Mode
    if (startBtn) {
        startBtn.addEventListener("click", function () {
            isRapidMode = true;
            currentFieldIndex = 0;
            overlay.classList.remove("d-none");
            summaryContainer.classList.add("d-none");
            fieldContainer.classList.remove("d-none");
            showField(currentFieldIndex);
        });
    }

    // 2. Render targeted field inside scaled canvas container safely
    function showField(index) {
        if (index >= rapidInputs.length) {
            showSummary();
            return;
        }

        fieldContainer.innerHTML = ""; // Clear active screen viewport

        const originalInput = rapidInputs[index];
        const originalLabel = originalInput.closest('.rapid-field').querySelector('label').textContent;

        // Build the HTML cleanly without cloning identical IDs
        const fieldWrapper = document.createElement("div");
        fieldWrapper.className = "rapid-zoomed animate-fade-in";
        
        const labelElement = document.createElement("label");
        labelElement.textContent = originalLabel;
        
        const bigInput = document.createElement("input");
        bigInput.type = originalInput.type;
        bigInput.className = "form-control";
        bigInput.value = originalInput.value;
        if (originalInput.step) bigInput.step = originalInput.step;
        if (originalInput.placeholder) bigInput.placeholder = originalInput.placeholder;

        fieldWrapper.appendChild(labelElement);
        fieldWrapper.appendChild(bigInput);
        fieldContainer.appendChild(fieldWrapper);

        // Keep focus locked in 
        bigInput.focus();
        bigInput.select();

        // Save typing straight back into your real form input instantly
        bigInput.addEventListener("input", function (e) {
            originalInput.value = e.target.value;
        });

        // Handle Enter key navigation 
        bigInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                
                if (originalInput.hasAttribute("required") && !bigInput.value.trim()) {
                    bigInput.reportValidity();
                    return;
                }

                currentFieldIndex++;
                showField(currentFieldIndex);
            }
        });
    }

    // 3. Render Large Final Confirmation Dashboard (Reads live input configurations)
    function showSummary() {
        fieldContainer.classList.add("d-none");
        summaryContainer.classList.remove("d-none");
        summaryList.innerHTML = ""; // Clear out previous view rows

        rapidInputs.forEach((input) => {
            const labelText = input.closest('.rapid-field').querySelector('label').textContent;
            const inputVal = input.value.trim() !== "" ? input.value : "N/A";
            
            const itemElement = document.createElement("p");
            itemElement.className = "mb-2 border-bottom border-secondary pb-1 d-flex justify-content-between gap-5";
            itemElement.innerHTML = `<strong>${labelText}:</strong> <span class="text-info">${inputVal}</span>`;
            summaryList.appendChild(itemElement);
        });
    }

    // 4. Cancel workflow behavior returning directly to standard layout form context
    if (cancelBtn) {
        cancelBtn.addEventListener("click", function () {
            isRapidMode = false;
            overlay.classList.add("d-none");
            if (addProductForm) addProductForm.reset(); // Wipe values clean
        });
    }

    // 5. Submit form when clicking Save in the Summary View
    if (saveBtn) {
        saveBtn.addEventListener("click", function () {
            if (addProductForm) addProductForm.requestSubmit(); 
        });
    }

    // 6. Form Submission Handling (Unified Backend Endpoint Transactions)
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
                    
                    if (isRapidMode) {
                        // Reset background form values completely for product #2
                        addProductForm.reset();
                        currentFieldIndex = 0;
                        summaryContainer.classList.add("d-none");
                        fieldContainer.classList.remove("d-none");
                        showField(currentFieldIndex); // Loops right back to Name field
                    } else {
                        window.location.href = "/shop"; 
                    }
                } else {
                    alert("Error: " + result.error);
                }
            } catch (error) {
                alert("Failed to connect to the server. Check your connection.");
            }
        });
    }
});
