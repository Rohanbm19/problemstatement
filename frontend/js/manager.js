/* =========================================================
   TwinStock AI - Manager Dashboard
   Granite-powered AI Suggestions
========================================================= */

const BACKEND_URL = "http://127.0.0.1:8000";


/* =========================================================
   ROLE SWITCHING
========================================================= */

function switchRole() {

    const roleSelect =
        document.getElementById("roleSelect");

    if (!roleSelect) return;

    const role =
        roleSelect.value;

    if (role === "worker") {

        window.location.href =
            "worker.html";
    }
}


/* =========================================================
   LOAD DASHBOARD
========================================================= */

async function loadDashboardData() {

    try {

        console.log(
            "Loading TwinStock AI dashboard..."
        );


        /* =====================================================
           GET INVENTORY
        ===================================================== */

        const inventoryResponse =
            await fetch(
                `${BACKEND_URL}/inventory/`
            );


        if (!inventoryResponse.ok) {

            throw new Error(
                "Unable to load inventory."
            );
        }


        const inventory =
            await inventoryResponse.json();


        console.log(
            "Inventory:",
            inventory
        );


        /* =====================================================
           SUMMARY CARDS
        ===================================================== */

        const totalProducts =
            inventory.length;


        const totalInventory =
            inventory.reduce(
                (sum, item) =>
                    sum +
                    Number(
                        item.stock_level || 0
                    ),
                0
            );


        document.getElementById(
            "totalProducts"
        ).textContent =
            totalProducts.toLocaleString();


        document.getElementById(
            "totalInventory"
        ).textContent =
            totalInventory.toLocaleString();


        /* =====================================================
           GET GRANITE FORECAST FOR EVERY PRODUCT
        ===================================================== */

        console.log(
            "Generating Granite forecasts for AI Suggestions..."
        );


        const itemsWithForecast =
            await Promise.all(

                inventory.map(
                    async function (item) {

                        try {

                            const itemId =
                                item.item_id;


                            /* =================================
                               CALL SAME FORECAST API
                               USED BY DEMAND FORECASTING
                            ================================= */

                            const forecastResponse =
                                await fetch(
                                    `${BACKEND_URL}/forecast/${encodeURIComponent(
                                        itemId
                                    )}?horizon=7`,
                                    {
                                        method: "POST",
                                        headers: {
                                            "Content-Type":
                                                "application/json"
                                        }
                                    }
                                );


                            if (!forecastResponse.ok) {

                                throw new Error(
                                    `Forecast failed for ${itemId}`
                                );
                            }


                            const forecastData =
                                await forecastResponse.json();


                            const forecast =
                                Array.isArray(
                                    forecastData.forecast
                                )
                                    ? forecastData.forecast
                                    : [];


                            /* =================================
                               TOTAL 7-DAY PREDICTED DEMAND
                            ================================= */

                            const totalPredictedDemand =
                                forecast.reduce(
                                    (
                                        total,
                                        point
                                    ) =>
                                        total +
                                        Number(
                                            point.predicted_demand ||
                                            0
                                        ),
                                    0
                                );


                            /* =================================
                               AVERAGE PREDICTED DAILY DEMAND
                            ================================= */

                            const predictedDailyDemand =
                                forecast.length > 0
                                    ? totalPredictedDemand /
                                      forecast.length
                                    : 0;


                            const currentStock =
                                Number(
                                    item.stock_level || 0
                                );


                            /* =================================
                               PREDICTED STOCKOUT
                            ================================= */

                            let remainingStock =
                                currentStock;


                            let daysUntilStockout =
                                null;


                            for (
                                let i = 0;
                                i < forecast.length;
                                i++
                            ) {

                                const demand =
                                    Number(
                                        forecast[i]
                                            .predicted_demand ||
                                        0
                                    );


                                remainingStock -=
                                    demand;


                                if (
                                    remainingStock <=
                                    0
                                ) {

                                    daysUntilStockout =
                                        i + 1;

                                    break;
                                }
                            }


                            /* =================================
                               RISK CLASSIFICATION

                               ALL BASED ON GRANITE
                            ================================= */

                            let risk =
                                "LOW";


                            if (
                                totalPredictedDemand <= 0
                            ) {

                                risk = "LOW";

                            }

                            else if (
                                currentStock <
                                totalPredictedDemand *
                                0.5
                            ) {

                                risk = "HIGH";

                            }

                            else if (
                                currentStock <
                                totalPredictedDemand
                            ) {

                                risk = "MEDIUM";

                            }

                            else if (
                                currentStock >
                                totalPredictedDemand *
                                3
                            ) {

                                risk = "OVERSTOCK";

                            }


                            /* =================================
                               RECOMMENDED REPLENISHMENT

                               Bring stock up to expected
                               7-day Granite demand.
                            ================================= */

                            const recommendedQuantity =
                                Math.max(
                                    0,
                                    Math.ceil(
                                        totalPredictedDemand -
                                        currentStock
                                    )
                                );


                            return {

                                ...item,

                                risk: risk,

                                currentStock:
                                    currentStock,

                                forecast:
                                    forecast,

                                forecastModel:
                                    forecastData.model ||
                                    "Granite Time Series (IBM TTM)",

                                totalPredictedDemand:
                                    totalPredictedDemand,

                                predictedDailyDemand:
                                    predictedDailyDemand,

                                daysUntilStockout:
                                    daysUntilStockout,

                                recommendedQuantity:
                                    recommendedQuantity

                            };


                        } catch (error) {

                            console.error(
                                `Granite forecast failed for ${item.item_id}:`,
                                error
                            );


                            return {

                                ...item,

                                risk:
                                    "UNKNOWN",

                                currentStock:
                                    Number(
                                        item.stock_level ||
                                        0
                                    ),

                                forecast: [],

                                forecastModel:
                                    "Unavailable",

                                totalPredictedDemand:
                                    0,

                                predictedDailyDemand:
                                    0,

                                daysUntilStockout:
                                    null,

                                recommendedQuantity:
                                    0

                            };
                        }

                    }
                )
            );


        console.log(
            "Granite-powered inventory:",
            itemsWithForecast
        );


        /* =====================================================
           SUMMARY RISK COUNTS
        ===================================================== */

        const highRiskItems =
            itemsWithForecast.filter(
                item =>
                    item.risk === "HIGH"
            );


        const mediumRiskItems =
            itemsWithForecast.filter(
                item =>
                    item.risk === "MEDIUM"
            );


        const overstockItems =
            itemsWithForecast.filter(
                item =>
                    item.risk === "OVERSTOCK"
            );


        document.getElementById(
            "highRisk"
        ).textContent =
            highRiskItems.length.toLocaleString();


        document.getElementById(
            "overstock"
        ).textContent =
            overstockItems.length.toLocaleString();


        /* =====================================================
           SORT PRODUCTS BY PRIORITY
        ===================================================== */

        const priorityOrder = {

            HIGH: 1,

            MEDIUM: 2,

            OVERSTOCK: 3,

            LOW: 4,

            UNKNOWN: 5

        };


        itemsWithForecast.sort(
            function (a, b) {

                return (
                    priorityOrder[a.risk] -
                    priorityOrder[b.risk]
                );
            }
        );


        /* =====================================================
           SELECT TOP 3 AI SUGGESTIONS
        ===================================================== */

        const suggestions =
            itemsWithForecast
                .filter(
                    item =>
                        item.risk !==
                        "LOW" &&
                        item.risk !==
                        "UNKNOWN"
                )
                .slice(0, 3);


        /* =====================================================
           SUGGESTION CARDS
        ===================================================== */

        const suggestionCards =
            document.querySelectorAll(
                ".suggestion-card"
            );


        suggestionCards.forEach(
            function (
                card,
                index
            ) {

                const item =
                    suggestions[index];


                /* =========================================
                   NO SUGGESTION
                ========================================= */

                if (!item) {

                    card.style.display =
                        "none";

                    return;
                }


                card.style.display =
                    "block";


                /* =========================================
                   RISK STYLE
                ========================================= */

                let riskClass;
                let riskLabel;
                let riskDot;


                if (
                    item.risk === "HIGH"
                ) {

                    riskClass =
                        "high";

                    riskLabel =
                        "HIGH RISK";

                    riskDot =
                        "red-dot";

                }

                else if (
                    item.risk === "MEDIUM"
                ) {

                    riskClass =
                        "medium";

                    riskLabel =
                        "MEDIUM RISK";

                    riskDot =
                        "orange-dot";

                }

                else {

                    riskClass =
                        "warning";

                    riskLabel =
                        "OVERSTOCK";

                    riskDot =
                        "yellow-dot";
                }


                /* =========================================
                   MESSAGE
                ========================================= */

                let message;


                if (
                    item.risk === "HIGH"
                ) {

                    if (
                        item.daysUntilStockout
                    ) {

                        message =
                            `Granite predicts stockout in ` +
                            `<strong>${item.daysUntilStockout} days</strong> ` +
                            `based on the next 7 days of expected demand.`;

                    } else {

                        message =
                            `Granite predicts demand will exceed ` +
                            `available inventory within the forecast period.`;
                    }

                }

                else if (
                    item.risk === "MEDIUM"
                ) {

                    message =
                        `Granite predicts increasing inventory pressure. ` +
                        `Expected 7-day demand is ` +
                        `<strong>${item.totalPredictedDemand.toFixed(
                            2
                        )} units</strong>.`;

                }

                else {

                    message =
                        `Granite predicts only ` +
                        `<strong>${item.totalPredictedDemand.toFixed(
                            2
                        )} units</strong> ` +
                        `of demand over the next 7 days, while current stock is much higher.`;
                }


                /* =========================================
                   CREATE CARD
                ========================================= */

                card.className =
                    `suggestion-card ${riskClass}`;


                card.innerHTML = `

                    <div class="suggestion-top">

                        <div class="product-info">

                            <span
                                class="risk-dot ${riskDot}">
                            </span>

                            <div>

                                <h3>
                                    ${item.item_id}
                                </h3>

                                <span>
                                    Product ID:
                                    ${item.item_id}
                                </span>

                            </div>

                        </div>


                        <span
                            class="risk-label ${riskClass}-label">

                            ${riskLabel}

                        </span>

                    </div>


                    <p class="suggestion-message">

                        ${message}

                    </p>


                    <div class="suggestion-details">


                        <div>

                            <span>
                                Current Stock
                            </span>

                            <strong>

                                ${item.currentStock.toLocaleString()}
                                units

                            </strong>

                        </div>


                        <div>

                            <span>
                                Granite 7-Day Demand
                            </span>

                            <strong>

                                ${item.totalPredictedDemand.toFixed(
                                    2
                                )}
                                units

                            </strong>

                        </div>


                        <div>

                            <span>
                                Recommended
                            </span>

                            <strong>

                                ${item.recommendedQuantity.toLocaleString()}
                                units

                            </strong>

                        </div>


                    </div>


                    <div
                        style="
                            margin-top:12px;
                            font-size:12px;
                            color:#64748b;
                        "
                    >

                        🤖 Powered by
                        ${item.forecastModel}

                    </div>


                    <button
                        class="${
                            index === 0
                                ? "primary-btn"
                                : "secondary-btn"
                        }"
                        type="button"
                    >

                        View Recommendation →

                    </button>

                `;


                /* =========================================
                   BUTTON
                ========================================= */

                const button =
                    card.querySelector(
                        "button"
                    );


                if (button) {

                    button.addEventListener(
                        "click",
                        function () {

                            openRecommendation(
                                item.item_id
                            );

                        }
                    );
                }

            }
        );

    }

    catch (error) {

        console.error(
            "Dashboard error:",
            error
        );


        const panel =
            document.querySelector(
                ".suggestions-panel"
            );


        if (panel) {

            panel.insertAdjacentHTML(
                "beforeend",
                `
                <p class="error-message">

                    Unable to load AI Suggestions.

                    Make sure the backend is
                    running on port 8000.

                </p>
                `
            );
        }
    }
}


/* =========================================================
   OPEN RECOMMENDATION
========================================================= */

function openRecommendation(
    product
) {

    localStorage.setItem(
        "selectedProduct",
        product
    );


    window.location.href =
        "replenishment.html";
}


/* =========================================================
   LOGOUT
========================================================= */

function goHome() {

    window.location.href =
        "index.html";
}


/* =========================================================
   IBM BOB
========================================================= */

function handleChatKey(
    event
) {

    if (
        event.key === "Enter"
    ) {

        sendMessage();
    }
}


function askQuestion(
    question
) {

    const input =
        document.getElementById(
            "chatInput"
        );


    if (!input) return;


    input.value =
        question;


    sendMessage();
}


function sendMessage() {

    const input =
        document.getElementById(
            "chatInput"
        );


    const chat =
        document.getElementById(
            "chatMessages"
        );


    if (
        !input ||
        !chat
    ) {

        return;
    }


    const message =
        input.value.trim();


    if (!message) return;


    /* USER */

    const userMessage =
        document.createElement(
            "div"
        );


    userMessage.className =
        "user-chat-message";


    userMessage.textContent =
        message;


    chat.appendChild(
        userMessage
    );


    input.value = "";


    /* BOT */

    setTimeout(
        function () {

            const response =
                "Based on the Granite demand forecast, review the highest-risk products first and replenish products where predicted demand exceeds available stock.";


            const botMessage =
                document.createElement(
                    "div"
                );


            botMessage.className =
                "message bot-message";


            botMessage.innerHTML = `

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

            `;


            chat.appendChild(
                botMessage
            );


            chat.scrollTop =
                chat.scrollHeight;

        },
        500
    );
}


/* =========================================================
   MANUAL GRANITE FORECAST
========================================================= */

async function generateForecast() {

    const itemInput =
        document.getElementById(
            "forecastItemId"
        );


    const horizonInput =
        document.getElementById(
            "forecastHorizon"
        );


    const loading =
        document.getElementById(
            "forecastLoading"
        );


    const result =
        document.getElementById(
            "forecastResult"
        );


    const errorBox =
        document.getElementById(
            "forecastError"
        );


    if (
        !itemInput ||
        !horizonInput ||
        !loading ||
        !result ||
        !errorBox
    ) {

        console.error(
            "Forecast elements missing."
        );

        return;
    }


    const itemId =
        itemInput.value.trim();


    const horizon =
        Number(
            horizonInput.value
        );


    if (!itemId) {

        errorBox.textContent =
            "Please enter an Item ID.";

        errorBox.style.display =
            "block";

        return;
    }


    loading.style.display =
        "block";


    result.style.display =
        "none";


    errorBox.style.display =
        "none";


    try {

        const response =
            await fetch(
                `${BACKEND_URL}/forecast/${encodeURIComponent(
                    itemId
                )}?horizon=${horizon}`,
                {
                    method: "POST",
                    headers: {
                        "Content-Type":
                            "application/json"
                    }
                }
            );


        const data =
            await response.json();


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Forecast request failed."
            );
        }


        const forecast =
            Array.isArray(
                data.forecast
            )
                ? data.forecast
                : [];


        if (
            forecast.length === 0
        ) {

            throw new Error(
                "No forecast data returned."
            );
        }


        /* SUMMARY */

        document.getElementById(
            "forecastProduct"
        ).textContent =
            data.item_id ||
            itemId;


        document.getElementById(
            "forecastModel"
        ).textContent =
            data.model ||
            "Granite Time Series (IBM TTM)";


        document.getElementById(
            "forecastDays"
        ).textContent =
            data.horizon ||
            forecast.length;


        /* TOTAL */

        const totalDemand =
            forecast.reduce(
                (
                    total,
                    point
                ) =>
                    total +
                    Number(
                        point.predicted_demand ||
                        0
                    ),
                0
            );


        document.getElementById(
            "forecastTotal"
        ).textContent =
            `${totalDemand.toFixed(
                2
            )} units`;


        /* TABLE */

        const tableBody =
            document.getElementById(
                "forecastTableBody"
            );


        tableBody.innerHTML =
            "";


        forecast.forEach(
            function (
                point
            ) {

                const row =
                    document.createElement(
                        "tr"
                    );


                row.innerHTML = `

                    <td>
                        ${point.date}
                    </td>

                    <td>
                        ${Number(
                            point.predicted_demand ||
                            0
                        ).toFixed(
                            2
                        )}
                        units
                    </td>

                `;


                tableBody.appendChild(
                    row
                );
            }
        );


        result.style.display =
            "block";


    }

    catch (error) {

        console.error(
            "Forecast error:",
            error
        );


        errorBox.textContent =
            error.message;


        errorBox.style.display =
            "block";


    }

    finally {

        loading.style.display =
            "none";
    }
}


/* =========================================================
   START DASHBOARD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "TwinStock AI Manager loaded."
        );


        loadDashboardData();
    }
);