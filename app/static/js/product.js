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

    // Dynamically inject the status alert element into the overlay if it doesn't exist
    let statusAlert = document.getElementById('rapidStatusAlert');
    if (!statusAlert && overlay) {
        statusAlert = document.createElement('div');
        statusAlert.id = 'rapidStatusAlert';
        statusAlert.className = 'text-center fw-bold fs-3 my-2 d-none w-75 m-auto';
        statusAlert.style.transition = 'all 0.3s ease';
        overlay.insertBefore(statusAlert, overlay.firstChild);
    }

    // 1. Activate Rapid Flow Mode
    if (startBtn) {
        startBtn.addEventListener("click", function () {
            isRapidMode = true;
            currentFieldIndex = 0;
            if (statusAlert) statusAlert.classList.add("d-none"); // Clear old messages
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
                    if (isRapidMode) {
                        // 1. Show flashing green notification banner instead of alert
                        if (statusAlert) {
                            statusAlert.textContent = "✓ " + (result.message || "Product added successfully!");
                            statusAlert.className = "text-success fw-bold fs-2 my-3 alert alert-success py-2 px-4 d-inline-block text-center";
                            statusAlert.classList.remove('d-none');

                            // Hide the confirmation message automatically after 1.5 seconds
                            setTimeout(() => {
                                statusAlert.classList.add('d-none');
                            }, 1500);
                        }

                        // 2. Clear values out and start product #2 loop without blocking execution
                        addProductForm.reset();
                        currentFieldIndex = 0;
                        summaryContainer.classList.add("d-none");
                        fieldContainer.classList.remove("d-none");
                        showField(currentFieldIndex); // Jump directly to Name input field
                    } else {
                        // Standard fallback redirection for manual page-view clicks
                        window.location.href = "/shop"; 
                    }
                } else {
                    // Show error details directly inside the rapid overlay context instead of an alert window
                    if (isRapidMode && statusAlert) {
                        statusAlert.textContent = "❌ Error: " + (result.error || "Could not save product.");
                        statusAlert.className = "text-danger fw-bold fs-3 my-3 alert alert-danger py-2 px-4 d-inline-block text-center";
                        statusAlert.classList.remove('d-none');
                    } else {
                        alert("Error: " + result.error);
                    }
                }
            } catch (error) {
                if (isRapidMode && statusAlert) {
                    statusAlert.textContent = "❌ Connection failed. Check server status.";
                    statusAlert.className = "text-danger fw-bold fs-3 my-3 alert alert-danger py-2 px-4 d-inline-block text-center";
                    statusAlert.classList.remove('d-none');
                } else {
                    alert("Failed to connect to the server. Check your connection.");
                }
            }
        });
    }
});
