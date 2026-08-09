let transactionType = "receive";

const API_URL = "http://127.0.0.1:8000";


// =========================
// ROLE SWITCH
// =========================

function switchRole() {

    const role =
        document.getElementById("roleSelect").value;

    if (role === "manager") {
        window.location.href = "manager.html";
    }
}


// =========================
// HOME
// =========================

function goHome() {

    window.location.href = "index.html";
}


// =========================
// TRANSACTION TYPE
// =========================

document.addEventListener("DOMContentLoaded", function () {

    const transactionButtons =
        document.querySelectorAll(".transaction-type");


    transactionButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            transactionButtons.forEach(function (btn) {

                btn.classList.remove("active");

            });


            this.classList.add("active");

            transactionType =
                this.dataset.type;

        });

    });


    // =========================
    // SUBMIT TRANSACTION
    // =========================

    const form =
        document.getElementById("transactionForm");


    if (!form) {

        console.error(
            "transactionForm not found"
        );

        return;
    }


    form.addEventListener("submit", async function (event) {

        event.preventDefault();


        const productElement =
            document.getElementById("product");


        const quantityElement =
            document.getElementById("quantity");


        const locationElement =
            document.getElementById("location");


        const notesElement =
            document.getElementById("notes");


        if (!productElement ||
            !quantityElement ||
            !locationElement) {

            alert(
                "Product, quantity or location field is missing."
            );

            return;
        }


        const product =
            productElement.value.trim();


        const quantity =
            parseInt(quantityElement.value);


        const location =
            locationElement.value;


        const notes =
            notesElement
                ? notesElement.value.trim()
                : "";


        // =========================
        // VALIDATION
        // =========================

        if (!product) {

            alert("Please enter a Product ID.");

            return;
        }


        if (!quantity || quantity <= 0) {

            alert(
                "Please enter a valid quantity."
            );

            return;
        }


        // =========================
        // SEND TO BACKEND
        // =========================

        const transactionData = {

            item_id: product,

            transaction_type:
                transactionType,

            quantity:
                quantity,

            location:
                location,

            notes:
                notes

        };


        console.log(
            "Sending transaction:",
            transactionData
        );


        try {

            const response =
                await fetch(
                    `${API_URL}/transactions/`,
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body:
                            JSON.stringify(
                                transactionData
                            )
                    }
                );


            const data =
                await response.json();


            console.log(
                "Backend response:",
                data
            );


            // =========================
            // BACKEND ERROR
            // =========================

            if (!response.ok) {

                alert(
                    data.detail ||
                    "Backend rejected the transaction."
                );

                return;
            }


            // =========================
            // SUCCESS
            // =========================

            addTransactionToUI(
                product,
                transactionType,
                quantity,
                location
            );


            const success =
                document.getElementById(
                    "successMessage"
                );


            if (success) {

                success.innerHTML =
                    `✓ Transaction recorded successfully! 
                     Current stock: 
                     ${data.inventory.stock_level}`;

                success.style.display =
                    "block";


                setTimeout(function () {

                    success.style.display =
                        "none";

                }, 4000);

            }


            // =========================
            // RESET FORM
            // =========================

            form.reset();


            // Keep receive selected
            transactionType =
                "receive";


            document
                .querySelectorAll(
                    ".transaction-type"
                )
                .forEach(function (btn) {

                    btn.classList.remove(
                        "active"
                    );

                });


            const receiveButton =
                document.querySelector(
                    '[data-type="receive"]'
                );


            if (receiveButton) {

                receiveButton.classList.add(
                    "active"
                );

            }


        } catch (error) {

            console.error(
                "Backend connection error:",
                error
            );


            alert(
                "Backend is not running or cannot be reached.\n\n" +
                "Please start FastAPI on http://127.0.0.1:8000"
            );

        }

    });

});


// =========================
// ADD TRANSACTION TO UI
// =========================

function addTransactionToUI(
    product,
    type,
    quantity,
    location
) {

    const list =
        document.getElementById(
            "transactionList"
        );


    if (!list) return;


    let icon = "📥";

    let cssClass = "receive";

    let sign = "+";


    if (type === "dispatch") {

        icon = "📤";

        cssClass = "dispatch";

        sign = "-";

    }


    if (type === "damaged") {

        icon = "⚠️";

        cssClass = "damaged";

        sign = "-";

    }


    if (type === "return") {

        icon = "↩️";

        cssClass = "receive";

        sign = "+";

    }


    const item =
        document.createElement("div");


    item.className =
        "transaction-item";


    item.innerHTML = `

        <div class="transaction-icon ${cssClass}">
            ${icon}
        </div>

        <div class="transaction-info">

            <strong>
                ${product}
            </strong>

            <span>
                ${type}
                • Just now
                • ${location}
            </span>

        </div>

        <strong class="${
            sign === "+"
                ? "positive"
                : "negative"
        }">

            ${sign}${quantity}

        </strong>

    `;


    list.prepend(item);
}