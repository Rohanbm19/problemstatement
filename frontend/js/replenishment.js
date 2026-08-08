/* =========================
   LOAD PRODUCT
========================= */

const selectedProduct =
    localStorage.getItem(
        "selectedProduct"
    );


if (selectedProduct) {

    document.getElementById(
        "productName"
    ).textContent =
        selectedProduct;

}


/* =========================
   BACK
========================= */

function goBack() {

    window.location.href =
        "manager.html";

}


/* =========================
   QUANTITY
========================= */

function changeQuantity(amount) {

    const input =
        document.getElementById(
            "orderQuantity"
        );


    let value =
        parseInt(input.value) || 0;


    value += amount;


    if (value < 10) {

        value = 10;

    }


    input.value = value;

}


/* =========================
   IGNORE
========================= */

function ignoreRecommendation() {

    const message =
        document.getElementById(
            "decisionMessage"
        );


    message.textContent =
        "Recommendation ignored. No purchase order was created.";


    message.style.color =
        "#667085";

}


/* =========================
   APPROVE
========================= */

function approveRestock() {

    const quantity =
        document.getElementById(
            "orderQuantity"
        ).value;


    const supplier =
        document.getElementById(
            "supplier"
        ).value;


    const message =
        document.getElementById(
            "decisionMessage"
        );


    message.innerHTML = `
        ✓ Restock approved for
        <strong>${quantity} units</strong>.
        <br>
        Supplier: ${supplier}
        <br>
        Purchase order ready to be created.
    `;


    message.style.color =
        "#027a48";

}