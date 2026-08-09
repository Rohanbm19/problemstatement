let transactionType = "receive";

const API_URL = "http://127.0.0.1:8000";


/* =========================================================
   ROLE SWITCH
========================================================= */

function switchRole() {

    const role =
        document.getElementById("roleSelect").value;

    if (role === "manager") {

        window.location.href = "manager.html";

    }

}


/* =========================================================
   HOME
========================================================= */

function goHome() {

    window.location.href = "index.html";

}


/* =========================================================
   TRANSACTION TYPE
========================================================= */

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


        console.log(
            "Transaction type:",
            transactionType
        );

    });

});


/* =========================================================
   SUBMIT TRANSACTION
========================================================= */

const transactionForm =
    document.getElementById("transactionForm");


if (transactionForm) {

    transactionForm.addEventListener(
        "submit",
        async function (event) {

            event.preventDefault();


            /* =================================================
               GET FORM VALUES
            ================================================= */

            const productElement =
                document.getElementById("product");


            const quantityElement =
                document.getElementById("quantity");


            const locationElement =
                document.getElementById("location");


            const notesElement =
                document.getElementById("notes");


            /* =================================================
               CHECK ELEMENTS
            ================================================= */

            if (!productElement) {

                console.error(
                    "Product input with id='product' not found."
                );

                alert(
                    "Product input not found. Check worker.html."
                );

                return;

            }


            if (!quantityElement) {

                console.error(
                    "Quantity input not found."
                );

                return;

            }


            /* =================================================
               READ VALUES
            ================================================= */

            const product =
                productElement.value.trim();


            const quantity =
                Number(quantityElement.value);


            const location =
                locationElement
                    ? locationElement.value
                    : null;


            const notes =
                notesElement
                    ? notesElement.value.trim()
                    : null;


            /* =================================================
               VALIDATION
            ================================================= */

            if (!product) {

                alert(
                    "Please enter the Product ID."
                );

                return;

            }


            if (!quantity || quantity <= 0) {

                alert(
                    "Please enter a valid quantity."
                );

                return;

            }


            /* =================================================
               DISABLE BUTTON
            ================================================= */

            const submitButton =
                transactionForm.querySelector(
                    'button[type="submit"]'
                );


            if (submitButton) {

                submitButton.disabled = true;

                submitButton.innerText =
                    "Saving...";

            }


            /* =================================================
               SEND TO FASTAPI
            ================================================= */

            try {

                console.log(
                    "Sending transaction to backend..."
                );


                console.log({

                    item_id: product,

                    transaction_type:
                        transactionType,

                    quantity: quantity,

                    location: location,

                    notes: notes

                });


                const response =
                    await fetch(
                        `${API_URL}/transactions/`,
                        {

                            method: "POST",

                            headers: {

                                "Content-Type":
                                    "application/json"

                            },

                            body: JSON.stringify({

                                item_id:
                                    product,

                                transaction_type:
                                    transactionType,

                                quantity:
                                    quantity,

                                location:
                                    location,

                                notes:
                                    notes

                            })

                        }
                    );


                /* =================================================
                   READ RESPONSE
                ================================================= */

                const result =
                    await response.json();


                console.log(
                    "Backend response:",
                    result
                );


                /* =================================================
                   BACKEND ERROR
                ================================================= */

                if (!response.ok) {

                    alert(
                        result.detail ||
                        "Transaction failed."
                    );

                    return;

                }


                /* =================================================
                   GET UPDATED STOCK
                ================================================= */

                const newStock =
                    result.inventory.stock_level;


                /* =================================================
                   ADD TRANSACTION TO UI
                ================================================= */

                addTransactionToUI(
                    product,
                    transactionType,
                    quantity,
                    location
                );


                /* =================================================
                   SHOW SUCCESS
                ================================================= */

                const success =
                    document.getElementById(
                        "successMessage"
                    );


                if (success) {

                    success.innerHTML =
                        `✓ Transaction recorded successfully! ` +
                        `Updated stock: ${newStock}`;

                    success.style.display =
                        "block";


                    setTimeout(function () {

                        success.style.display =
                            "none";

                    }, 5000);

                }


                /* =================================================
                   SHOW UPDATED STOCK
                ================================================= */

                alert(
                    "Transaction successful!\n\n" +
                    "Product: " + product + "\n" +
                    "Transaction: " + transactionType + "\n" +
                    "Quantity: " + quantity + "\n\n" +
                    "Updated stock: " + newStock
                );


                /* =================================================
                   RESET FORM
                ================================================= */

                transactionForm.reset();


                /* =================================================
                   RESET TRANSACTION TYPE
                ================================================= */

                transactionType = "receive";


                transactionButtons.forEach(
                    function (btn) {

                        btn.classList.remove(
                            "active"
                        );

                    }
                );


                const receiveButton =
                    document.querySelector(
                        '.transaction-type[data-type="receive"]'
                    );


                if (receiveButton) {

                    receiveButton.classList.add(
                        "active"
                    );

                }

            }

            catch (error) {

                console.error(
                    "Backend connection error:",
                    error
                );


                alert(
                    "Cannot connect to backend.\n\n" +
                    "Make sure FastAPI is running at:\n" +
                    API_URL
                );

            }

            finally {

                if (submitButton) {

                    submitButton.disabled =
                        false;

                    submitButton.innerText =
                        "Submit Transaction";

                }

            }

        }
    );

}


/* =========================================================
   ADD TRANSACTION TO UI
========================================================= */

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


    if (!list) {

        return;

    }


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
                • ${location || "N/A"}
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