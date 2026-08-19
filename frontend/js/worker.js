// =====================================================
// TwinStock AI - Worker Dashboard Module
// =====================================================

const API_URL = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "/api";
let transactionType = "receive";

function switchRole() {
    const roleSelect = document.getElementById("roleSelect");
    if (roleSelect && roleSelect.value === "manager") {
        window.location.href = "manager.html";
    }
}

function goHome() {
    window.location.href = "index.html";
}

document.addEventListener("DOMContentLoaded", () => {
    // Setup transaction type selector buttons
    const transactionButtons = document.querySelectorAll(".transaction-type");
    transactionButtons.forEach(button => {
        button.addEventListener("click", function () {
            transactionButtons.forEach(btn => btn.classList.remove("active"));
            this.classList.add("active");
            transactionType = this.dataset.type || "receive";
        });
    });

    // Form submission
    const transactionForm = document.getElementById("transactionForm");
    if (transactionForm) {
        transactionForm.addEventListener("submit", async (event) => {
            event.preventDefault();

            const productElement = document.getElementById("product");
            const quantityElement = document.getElementById("quantity");
            const locationElement = document.getElementById("location");
            const notesElement = document.getElementById("notes");

            if (!productElement || !quantityElement) {
                alert("Form elements missing.");
                return;
            }

            const product = productElement.value.trim();
            const quantity = Number(quantityElement.value);
            const location = locationElement ? locationElement.value : null;
            const notes = notesElement ? notesElement.value.trim() : null;

            if (!product) {
                alert("Please enter the Product ID.");
                return;
            }

            if (!quantity || quantity <= 0) {
                alert("Please enter a valid quantity greater than 0.");
                return;
            }

            const submitButton = transactionForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.textContent = "Saving...";
            }

            try {
                const response = await fetch(`${API_URL}/transactions/`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        item_id: product,
                        transaction_type: transactionType,
                        quantity: quantity,
                        location: location,
                        notes: notes
                    })
                });

                const result = await response.json();

                if (!response.ok) {
                    alert(result.detail || "Transaction failed.");
                    return;
                }

                const newStock = result.inventory ? result.inventory.stock_level : "N/A";
                addTransactionToUI(product, transactionType, quantity, location);

                const success = document.getElementById("successMessage");
                if (success) {
                    success.innerHTML = `✓ Transaction recorded successfully! Updated stock: <strong>${newStock}</strong>`;
                    success.style.display = "block";
                    setTimeout(() => { success.style.display = "none"; }, 5000);
                }

                transactionForm.reset();
                transactionType = "receive";
                transactionButtons.forEach(btn => btn.classList.remove("active"));
                const receiveBtn = document.querySelector('.transaction-type[data-type="receive"]');
                if (receiveBtn) receiveBtn.classList.add("active");

            } catch (error) {
                console.error("Backend connection error:", error);
                alert(`Cannot connect to backend server at ${API_URL}`);
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.textContent = "Submit Transaction";
                }
            }
        });
    }

    loadWorkerProducts();
});

function addTransactionToUI(product, type, quantity, location) {
    const list = document.getElementById("transactionList");
    if (!list) return;

    let icon = "📥";
    let cssClass = "receive";
    let sign = "+";

    if (type === "dispatch") {
        icon = "📤";
        cssClass = "dispatch";
        sign = "-";
    } else if (type === "damaged") {
        icon = "⚠️";
        cssClass = "damaged";
        sign = "-";
    } else if (type === "return") {
        icon = "↩️";
        cssClass = "receive";
        sign = "+";
    }

    const item = document.createElement("div");
    item.className = "transaction-item";
    item.innerHTML = `
        <div class="transaction-icon ${cssClass}">${icon}</div>
        <div class="transaction-info">
            <strong>${product}</strong>
            <span>${type} • Just now • ${location || "N/A"}</span>
        </div>
        <strong class="${sign === '+' ? 'positive' : 'negative'}">${sign}${quantity}</strong>
    `;

    list.prepend(item);
}

async function loadWorkerProducts() {
    const tableBody = document.getElementById("workerProductsTable");
    if (!tableBody) return;

    try {
        const response = await fetch(`${API_URL}/inventory/`);
        if (!response.ok) return;
        const products = await response.json();

        tableBody.innerHTML = products.map(item => `
            <tr>
                <td><strong>${item.item_id}</strong></td>
                <td>${item.stock_level}</td>
                <td><span class="badge ${item.stock_level < 20 ? 'badge-danger' : 'badge-success'}">${item.stock_level < 20 ? 'Low Stock' : 'In Stock'}</span></td>
                <td>${item.location || 'Warehouse A'}</td>
            </tr>
        `).join('');
    } catch (e) {
        console.warn("Could not load worker product list:", e);
    }
}