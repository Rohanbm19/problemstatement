const API_BASE = window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "/api";
const API_URL = API_BASE.replace(/\/$/, "");

function switchRole() {

    const role =
        document.getElementById("roleSelect").value;

    if (role === "worker") {

        window.location.href = "worker.html";

    }

}


async function loadDashboardData() {

    try {

        const response = await fetch(`${API_URL}/inventory/`);

        if (!response.ok) {
            throw new Error("Unable to load inventory from backend.");
        }

        const inventory = await response.json();

        const totalProducts = inventory.length;
        const totalInventory = inventory.reduce((sum, item) => sum + (item.stock_level || 0), 0);
        const highRisk = inventory.filter((item) => (item.stock_level || 0) <= (item.reorder_point || 0)).length;
        const overstock = inventory.filter((item) => (item.stock_level || 0) > ((item.reorder_point || 0) * 3)).length;

        document.getElementById("totalProducts").textContent = totalProducts.toLocaleString();
        document.getElementById("totalInventory").textContent = totalInventory.toLocaleString();
        document.getElementById("highRisk").textContent = highRisk.toLocaleString();
        document.getElementById("overstock").textContent = overstock.toLocaleString();

        const suggestionCards = document.querySelectorAll(".suggestion-card");
        const itemsWithRisk = await Promise.all(
            inventory.map(async (item) => {
                try {
                    const riskResponse = await fetch(`${API_URL}/inventory/${encodeURIComponent(item.item_id)}/stockout-risk`);
                    const riskData = await riskResponse.json();
                    return {
                        ...item,
                        risk: riskData.risk || "LOW",
                        daysUntilStockout: riskData.days_until_stockout
                    };
                } catch (error) {
                    return {
                        ...item,
                        risk: "LOW",
                        daysUntilStockout: null
                    };
                }
            })
        );

        const highRiskItems = itemsWithRisk.filter((item) => item.risk === "HIGH").sort((a, b) => (a.stock_level || 0) - (b.stock_level || 0));
        const mediumRiskItems = itemsWithRisk.filter((item) => item.risk === "MEDIUM").sort((a, b) => (a.stock_level || 0) - (b.stock_level || 0));
        const overstockItems = itemsWithRisk.filter((item) => (item.stock_level || 0) > ((item.reorder_point || 0) * 3)).sort((a, b) => (b.stock_level || 0) - (a.stock_level || 0));

        const suggestions = [
            highRiskItems[0],
            mediumRiskItems[0] || highRiskItems[1] || itemsWithRisk[0],
            overstockItems[0] || itemsWithRisk[0]
        ].filter(Boolean);

        suggestionCards.forEach((card, index) => {
            const item = suggestions[index];

            if (!item) {
                card.style.display = "none";
                return;
            }

            const riskClass = item.risk === "HIGH" ? "high" : item.risk === "MEDIUM" ? "medium" : "warning";
            const riskLabel = item.risk === "HIGH" ? "HIGH RISK" : item.risk === "MEDIUM" ? "MEDIUM RISK" : "OVERSTOCK";
            const message = item.risk === "HIGH"
                ? `Stockout predicted in <strong>${item.daysUntilStockout || "N/A"} days</strong> based on current demand.`
                : item.risk === "MEDIUM"
                    ? `Demand is increasing. Stockout predicted in <strong>${item.daysUntilStockout || "N/A"} days</strong>.`
                    : `Current inventory may cover <strong>${Math.max(0, item.stock_level || 0)} units</strong> of expected demand.`;

            card.className = `suggestion-card ${riskClass}`;
            card.innerHTML = `
                <div class="suggestion-top">
                    <div class="product-info">
                        <span class="risk-dot ${item.risk === "HIGH" ? "red-dot" : item.risk === "MEDIUM" ? "orange-dot" : "yellow-dot"}"></span>
                        <div>
                            <h3>${item.item_id}</h3>
                            <span>Product ID: ${item.item_id}</span>
                        </div>
                    </div>
                    <span class="risk-label ${item.risk === "HIGH" ? "high-label" : item.risk === "MEDIUM" ? "medium-label" : "warning-label"}">${riskLabel}</span>
                </div>
                <p class="suggestion-message">${message}</p>
                <div class="suggestion-details">
                    <div>
                        <span>Current Stock</span>
                        <strong>${(item.stock_level || 0).toLocaleString()} units</strong>
                    </div>
                    <div>
                        <span>Daily Demand</span>
                        <strong>${item.daily_demand || 0}/day</strong>
                    </div>
                    <div>
                        <span>Recommended</span>
                        <strong>${Math.max(0, (item.reorder_point || 0) - (item.stock_level || 0)).toLocaleString()} units</strong>
                    </div>
                </div>
                <button class="${index === 0 ? "primary-btn" : "secondary-btn"}" data-item-id="${item.item_id}">
                    View Recommendation →
                </button>
            `;

            const button = card.querySelector("button");
            if (button) {
                button.addEventListener("click", () => openRecommendation(item.item_id));
            }
        });

    } catch (error) {
        console.error("Dashboard load failed:", error);
        document.querySelector(".suggestions-panel")?.insertAdjacentHTML("beforeend", `<p class="error-message">Unable to reach the backend API. Start the backend and proxy server first.</p>`);
    }

}


function openRecommendation(product) {

    localStorage.setItem(
        "selectedProduct",
        product
    );

    window.location.href =
        "replenishment.html";

}


function goHome() {

    window.location.href =
        "index.html";

}


/* =========================
   IBM BOB CHAT
========================= */

function handleChatKey(event) {

    if (event.key === "Enter") {

        sendMessage();

    }

}


function askQuestion(question) {

    document.getElementById("chatInput").value =
        question;

    sendMessage();

}


function sendMessage() {

    const input =
        document.getElementById("chatInput");

    const message =
        input.value.trim();

    if (!message) return;


    const chat =
        document.getElementById("chatMessages");


    /* USER MESSAGE */

    chat.innerHTML += `

        <div class="user-chat-message">

            ${message}

        </div>

    `;


    input.value = "";


    /* TEMPORARY MOCK BOB RESPONSE */

    setTimeout(function() {

        let response =
            "Based on the current inventory data, I recommend reviewing the high-risk products first.";


        const lower =
            message.toLowerCase();


        if (
            lower.includes("reorder") ||
            lower.includes("restock")
        ) {

            response =
                "There are currently 3 products that require attention: Laptop, Keyboard and Mouse. Laptop is the highest priority with a predicted stockout in 3 days.";

        }


        else if (
            lower.includes("laptop") &&
            lower.includes("why")
        ) {

            response =
                "Laptop is at high stockout risk because current inventory is expected to last only 3 days, while the recommended supplier requires 5 days to deliver.";

        }


        chat.innerHTML += `

            <div class="message bot-message">

                <div class="message-avatar">
                    🤖
                </div>

                <div class="message-content">

                    <span class="message-name">
                        IBM Bob
                    </span>

                    <p>
                        ${response}
                    </p>

                </div>

            </div>

        `;


        chat.scrollTop =
            chat.scrollHeight;


    }, 500);

}

document.addEventListener("DOMContentLoaded", loadDashboardData);
const BACKEND_URL = "http://127.0.0.1:8000";

/* =========================================================
   GENERATE FORECAST
========================================================= */

async function generateForecast() {

    const itemId = document
        .getElementById("forecastItemId")
        .value
        .trim();

    const horizon = Number(
        document
            .getElementById("forecastHorizon")
            .value
    );

    if (!itemId) {
        alert("Please enter an Item ID.");
        return;
    }

    const loading =
        document.getElementById("forecastLoading");

    const result =
        document.getElementById("forecastResult");

    const errorBox =
        document.getElementById("forecastError");

    loading.style.display = "block";
    result.style.display = "none";
    errorBox.style.display = "none";

    try {

        console.log(
            "Requesting forecast for:",
            itemId
        );

        const response = await fetch(
            `${BACKEND_URL}/forecast/${encodeURIComponent(itemId)}?horizon=${horizon}`,
            {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            }
        );

        const data = await response.json();

        console.log(
            "Forecast response:",
            data
        );

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Forecast request failed."
            );
        }

        /* =============================================
           SUMMARY
        ============================================= */

        document.getElementById(
            "forecastProduct"
        ).textContent = data.item_id;

        document.getElementById(
            "forecastModel"
        ).textContent = data.model;

        document.getElementById(
            "forecastDays"
        ).textContent = data.horizon;


        /* =============================================
           FORECAST DATA
        ============================================= */

        const forecast =
            data.forecast || [];

        const totalDemand =
            forecast.reduce(
                (total, point) =>
                    total +
                    Number(
                        point.predicted_demand || 0
                    ),
                0
            );


        document.getElementById(
            "forecastTotal"
        ).textContent =
            totalDemand.toFixed(2) +
            " units";


        /* =============================================
           TABLE
        ============================================= */

        const tableBody =
            document.getElementById(
                "forecastTableBody"
            );

        tableBody.innerHTML = "";


        if (forecast.length === 0) {

            tableBody.innerHTML = `
                <tr>
                    <td colspan="2">
                        No forecast data available.
                    </td>
                </tr>
            `;

        } else {

            forecast.forEach(
                function(point) {

                    const row =
                        document.createElement("tr");

                    row.innerHTML = `
                        <td>
                            ${point.date}
                        </td>

                        <td>
                            ${Number(
                                point.predicted_demand || 0
                            ).toFixed(2)}
                            units
                        </td>
                    `;

                    tableBody.appendChild(row);
                }
            );
        }


        /* =============================================
           SHOW RESULT
        ============================================= */

        result.style.display = "block";


    } catch (error) {

        console.error(
            "Forecast error:",
            error
        );

        errorBox.textContent =
            error.message;

        errorBox.style.display =
            "block";

    } finally {

        loading.style.display =
            "none";
    }
}