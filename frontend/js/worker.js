let transactionType = "receive";


/* =========================
   ROLE SWITCH
========================= */

function switchRole() {

    const role =
        document.getElementById("roleSelect").value;

    if (role === "manager") {

        window.location.href =
            "manager.html";

    }

}


/* =========================
   HOME
========================= */

function goHome() {

    window.location.href =
        "index.html";

}


/* =========================
   TRANSACTION TYPE
========================= */

const transactionButtons =
    document.querySelectorAll(
        ".transaction-type"
    );


transactionButtons.forEach(function(button) {

    button.addEventListener(
        "click",
        function() {

            transactionButtons.forEach(
                function(btn) {

                    btn.classList.remove(
                        "active"
                    );

                }
            );


            this.classList.add("active");


            transactionType =
                this.dataset.type;

        }
    );

});


/* =========================
   SUBMIT TRANSACTION
========================= */

document
    .getElementById("transactionForm")
    .addEventListener(
        "submit",
        function(event) {

            event.preventDefault();


            const product =
                document.getElementById(
                    "product"
                ).value;


            const quantity =
                document.getElementById(
                    "quantity"
                ).value;


            const location =
                document.getElementById(
                    "location"
                ).value;


            if (!product || !quantity) {

                alert(
                    "Please select a product and enter the quantity."
                );

                return;

            }


            /* ADD TO RECENT TRANSACTIONS */

            const list =
                document.getElementById(
                    "transactionList"
                );


            let icon = "📥";

            let cssClass = "receive";

            let sign = "+";


            if (transactionType === "dispatch") {

                icon = "📤";

                cssClass = "dispatch";

                sign = "-";

            }


            if (transactionType === "damaged") {

                icon = "⚠️";

                cssClass = "damaged";

                sign = "-";

            }


            if (transactionType === "return") {

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
                        ${transactionType}
                        • Just now
                        • ${location}
                    </span>

                </div>

                <strong class="${sign === '+' ? 'positive' : 'negative'}">

                    ${sign}${quantity}

                </strong>

            `;


            list.prepend(item);


            /* SUCCESS MESSAGE */

            const success =
                document.getElementById(
                    "successMessage"
                );


            success.style.display =
                "block";


            setTimeout(
                function() {

                    success.style.display =
                        "none";

                },
                3000
            );


            /* RESET FORM */

            document
                .getElementById(
                    "transactionForm"
                )
                .reset();

        }
    );