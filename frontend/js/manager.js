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

const API_URL = "http://127.0.0.1:8000";


// ============================================================
// LANGUAGE TRANSLATIONS
// ============================================================

/* =====================================================
   TWINSTOCK AI - MANAGER
   LANGUAGE + ROLE + FORECAST
===================================================== */


/* =====================================================
   TRANSLATIONS
===================================================== */

const translations = {

    en: {

        language: "Language:",
        role: "Role:",
        logout: "Logout",

        manager_dashboard: "Manager Dashboard",

        manager_description:
            "Monitor inventory, AI predictions and replenishment recommendations.",

        system_live:
            "● System Live",

        total_products:
            "Total Products",

        total_inventory:
            "Total Inventory",

        units:
            "units",

        high_risk:
            "High Risk",

        products:
            "products",

        overstock:
            "Overstock",

        ai_suggestions:
            "🤖 AI Suggestions",

        ai_suggestions_description:
            "AI-powered inventory recommendations",

        high_risk_label:
            "HIGH RISK",

        medium_risk:
            "MEDIUM RISK",

        overstock_label:
            "OVERSTOCK",

        stockout_prediction:
            "Stockout predicted based on current demand.",

        demand_increasing:
            "Demand is increasing.",

        overstock_message:
            "Current inventory may cover expected demand.",

        current_stock:
            "Current Stock",

        predicted_demand:
            "Predicted Demand",

        recommended:
            "Recommended",

        daily_demand:
            "Daily Demand",

        status:
            "Status",

        review:
            "Review",

        view_recommendation:
            "View Recommendation →",

        view_details:
            "View Details →",

        inventory_overview:
            "📋 Inventory Overview",

        latest_activity:
            "Latest warehouse activity",

        today:
            "Today",

        ai_warehouse_assistant:
            "AI Warehouse Assistant",

        bob_greeting:
            "Hello! I'm your warehouse AI assistant. I can help you understand inventory risks, predictions and replenishment recommendations.",

        reorder_question:
            "Which products should I reorder?",

        laptop_question:
            "Why is Laptop high risk?",

        chat_placeholder:
            "Ask IBM Bob about your inventory...",

        demand_forecasting:
            "🔮 Demand Forecasting",

        forecast_description:
            "Predict future demand using TwinStock AI.",

        ai_forecast:
            "AI Forecast",

        product_item_id:
            "Product / Item ID",

        forecast_item_placeholder:
            "Example: ITM10025",

        forecast_horizon:
            "Forecast Horizon",

        next_7_days:
            "Next 7 Days",

        next_14_days:
            "Next 14 Days",

        next_30_days:
            "Next 30 Days",

        generate_forecast:
            "🔮 Generate Forecast",

        generating_forecast:
            "⏳ Generating forecast...",

        product:
            "Product",

        model:
            "Model",

        forecast_days:
            "Forecast Days",

        total_expected_demand:
            "Total Expected Demand",

        date:
            "Date"

    },


    hi: {

        language: "भाषा:",

        role: "भूमिका:",

        logout: "लॉगआउट",

        manager_dashboard:
            "मैनेजर डैशबोर्ड",

        manager_description:
            "इन्वेंटरी, AI पूर्वानुमान और पुनःपूर्ति सुझावों की निगरानी करें।",

        system_live:
            "● सिस्टम लाइव",

        total_products:
            "कुल उत्पाद",

        total_inventory:
            "कुल इन्वेंटरी",

        units:
            "इकाइयाँ",

        high_risk:
            "उच्च जोखिम",

        products:
            "उत्पाद",

        overstock:
            "अधिक स्टॉक",

        ai_suggestions:
            "🤖 AI सुझाव",

        ai_suggestions_description:
            "AI आधारित इन्वेंटरी सुझाव",

        high_risk_label:
            "उच्च जोखिम",

        medium_risk:
            "मध्यम जोखिम",

        overstock_label:
            "अधिक स्टॉक",

        stockout_prediction:
            "वर्तमान मांग के आधार पर स्टॉक समाप्त होने का अनुमान है।",

        demand_increasing:
            "मांग बढ़ रही है।",

        overstock_message:
            "वर्तमान इन्वेंटरी अपेक्षित मांग को पूरा कर सकती है।",

        current_stock:
            "वर्तमान स्टॉक",

        predicted_demand:
            "अनुमानित मांग",

        recommended:
            "अनुशंसित",

        daily_demand:
            "दैनिक मांग",

        status:
            "स्थिति",

        review:
            "समीक्षा",

        view_recommendation:
            "अनुशंसा देखें →",

        view_details:
            "विवरण देखें →",

        inventory_overview:
            "📋 इन्वेंटरी अवलोकन",

        latest_activity:
            "नवीनतम वेयरहाउस गतिविधि",

        today:
            "आज",

        ai_warehouse_assistant:
            "AI वेयरहाउस सहायक",

        bob_greeting:
            "नमस्ते! मैं आपका वेयरहाउस AI सहायक हूँ। मैं आपको इन्वेंटरी जोखिम, पूर्वानुमान और पुनःपूर्ति सुझाव समझने में मदद कर सकता हूँ।",

        reorder_question:
            "मुझे किन उत्पादों को दोबारा ऑर्डर करना चाहिए?",

        laptop_question:
            "Laptop उच्च जोखिम वाला क्यों है?",

        chat_placeholder:
            "IBM Bob से अपनी इन्वेंटरी के बारे में पूछें...",

        demand_forecasting:
            "🔮 मांग पूर्वानुमान",

        forecast_description:
            "TwinStock AI का उपयोग करके भविष्य की मांग का अनुमान लगाएँ।",

        ai_forecast:
            "AI पूर्वानुमान",

        product_item_id:
            "उत्पाद / आइटम ID",

        forecast_item_placeholder:
            "उदाहरण: ITM10025",

        forecast_horizon:
            "पूर्वानुमान अवधि",

        next_7_days:
            "अगले 7 दिन",

        next_14_days:
            "अगले 14 दिन",

        next_30_days:
            "अगले 30 दिन",

        generate_forecast:
            "🔮 पूर्वानुमान बनाएँ",

        generating_forecast:
            "⏳ पूर्वानुमान बनाया जा रहा है...",

        product:
            "उत्पाद",

        model:
            "मॉडल",

        forecast_days:
            "पूर्वानुमान दिन",

        total_expected_demand:
            "कुल अपेक्षित मांग",

        date:
            "तारीख"

    },


    kn: {

        language: "ಭಾಷೆ:",

        role: "ಪಾತ್ರ:",

        logout: "ಲಾಗ್‌ಔಟ್",

        manager_dashboard:
            "ಮ್ಯಾನೇಜರ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್",

        manager_description:
            "ದಾಸ್ತಾನು, AI ಮುನ್ಸೂಚನೆಗಳು ಮತ್ತು ಮರುಪೂರೈಕೆ ಶಿಫಾರಸುಗಳನ್ನು ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ.",

        system_live:
            "● ಸಿಸ್ಟಮ್ ಲೈವ್",

        total_products:
            "ಒಟ್ಟು ಉತ್ಪನ್ನಗಳು",

        total_inventory:
            "ಒಟ್ಟು ದಾಸ್ತಾನು",

        units:
            "ಘಟಕಗಳು",

        high_risk:
            "ಹೆಚ್ಚಿನ ಅಪಾಯ",

        products:
            "ಉತ್ಪನ್ನಗಳು",

        overstock:
            "ಹೆಚ್ಚುವರಿ ದಾಸ್ತಾನು",

        ai_suggestions:
            "🤖 AI ಸಲಹೆಗಳು",

        ai_suggestions_description:
            "AI ಆಧಾರಿತ ದಾಸ್ತಾನು ಶಿಫಾರಸುಗಳು",

        high_risk_label:
            "ಹೆಚ್ಚಿನ ಅಪಾಯ",

        medium_risk:
            "ಮಧ್ಯಮ ಅಪಾಯ",

        overstock_label:
            "ಹೆಚ್ಚುವರಿ ದಾಸ್ತಾನು",

        stockout_prediction:
            "ಪ್ರಸ್ತುತ ಬೇಡಿಕೆಯ ಆಧಾರದ ಮೇಲೆ ಸ್ಟಾಕ್ ಮುಗಿಯುವ ಸಾಧ್ಯತೆಯಿದೆ.",

        demand_increasing:
            "ಬೇಡಿಕೆ ಹೆಚ್ಚುತ್ತಿದೆ.",

        overstock_message:
            "ಪ್ರಸ್ತುತ ದಾಸ್ತಾನು ನಿರೀಕ್ಷಿತ ಬೇಡಿಕೆಯನ್ನು ಪೂರೈಸಬಹುದು.",

        current_stock:
            "ಪ್ರಸ್ತುತ ದಾಸ್ತಾನು",

        predicted_demand:
            "ಅಂದಾಜು ಬೇಡಿಕೆ",

        recommended:
            "ಶಿಫಾರಸು",

        daily_demand:
            "ದೈನಂದಿನ ಬೇಡಿಕೆ",

        status:
            "ಸ್ಥಿತಿ",

        review:
            "ಪರಿಶೀಲನೆ",

        view_recommendation:
            "ಶಿಫಾರಸು ವೀಕ್ಷಿಸಿ →",

        view_details:
            "ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಿ →",

        inventory_overview:
            "📋 ದಾಸ್ತಾನು ಅವಲೋಕನ",

        latest_activity:
            "ಇತ್ತೀಚಿನ ಗೋದಾಮಿನ ಚಟುವಟಿಕೆ",

        today:
            "ಇಂದು",

        ai_warehouse_assistant:
            "AI ಗೋದಾಮಿನ ಸಹಾಯಕ",

        bob_greeting:
            "ನಮಸ್ಕಾರ! ನಾನು ನಿಮ್ಮ ಗೋದಾಮಿನ AI ಸಹಾಯಕ. ದಾಸ್ತಾನು ಅಪಾಯಗಳು, ಮುನ್ಸೂಚನೆಗಳು ಮತ್ತು ಮರುಪೂರೈಕೆ ಶಿಫಾರಸುಗಳನ್ನು ಅರ್ಥಮಾಡಿಕೊಳ್ಳಲು ನಾನು ಸಹಾಯ ಮಾಡಬಹುದು.",

        reorder_question:
            "ಯಾವ ಉತ್ಪನ್ನಗಳನ್ನು ಮರುಆರ್ಡರ್ ಮಾಡಬೇಕು?",

        laptop_question:
            "Laptop ಹೆಚ್ಚಿನ ಅಪಾಯದಲ್ಲಿರುವುದೇಕೆ?",

        chat_placeholder:
            "ನಿಮ್ಮ ದಾಸ್ತಾನು ಕುರಿತು IBM Bob ಅನ್ನು ಕೇಳಿ...",

        demand_forecasting:
            "🔮 ಬೇಡಿಕೆ ಮುನ್ಸೂಚನೆ",

        forecast_description:
            "TwinStock AI ಬಳಸಿ ಭವಿಷ್ಯದ ಬೇಡಿಕೆಯನ್ನು ಊಹಿಸಿ.",

        ai_forecast:
            "AI ಮುನ್ಸೂಚನೆ",

        product_item_id:
            "ಉತ್ಪನ್ನ / ಐಟಂ ID",

        forecast_item_placeholder:
            "ಉದಾಹರಣೆ: ITM10025",

        forecast_horizon:
            "ಮುನ್ಸೂಚನೆ ಅವಧಿ",

        next_7_days:
            "ಮುಂದಿನ 7 ದಿನಗಳು",

        next_14_days:
            "ಮುಂದಿನ 14 ದಿನಗಳು",

        next_30_days:
            "ಮುಂದಿನ 30 ದಿನಗಳು",

        generate_forecast:
            "🔮 ಮುನ್ಸೂಚನೆ ರಚಿಸಿ",

        generating_forecast:
            "⏳ ಮುನ್ಸೂಚನೆ ರಚಿಸಲಾಗುತ್ತಿದೆ...",

        product:
            "ಉತ್ಪನ್ನ",

        model:
            "ಮಾದರಿ",

        forecast_days:
            "ಮುನ್ಸೂಚನೆ ದಿನಗಳು",

        total_expected_demand:
            "ಒಟ್ಟು ನಿರೀಕ್ಷಿತ ಬೇಡಿಕೆ",

        date:
            "ದಿನಾಂಕ"

    }

};


/* =====================================================
   APPLY LANGUAGE
===================================================== */

function applyLanguage(language) {

    const dictionary =
        translations[language] || translations.en;


    /*
     * Normal text
     */

    document
        .querySelectorAll("[data-i18n]")
        .forEach(element => {

            const key =
                element.getAttribute("data-i18n");

            if (dictionary[key]) {

                element.textContent =
                    dictionary[key];

            }

        });


    /*
     * Placeholder text
     */

    document
        .querySelectorAll("[data-i18n-placeholder]")
        .forEach(element => {

            const key =
                element.getAttribute(
                    "data-i18n-placeholder"
                );

            if (dictionary[key]) {

                element.placeholder =
                    dictionary[key];

            }

        });


    /*
     * Save language
     */

    localStorage.setItem(
        "twinstock_language",
        language
    );


    /*
     * HTML language
     */

    document.documentElement.lang =
        language;


    /*
     * Keep select selected
     */

    const select =
        document.getElementById(
            "languageSelect"
        );

    if (select) {

        select.value = language;

    }

}


/* =====================================================
   LANGUAGE SELECT
===================================================== */

document.addEventListener(
    "DOMContentLoaded",
    function () {

        const languageSelect =
            document.getElementById(
                "languageSelect"
            );


        const savedLanguage =
            localStorage.getItem(
                "twinstock_language"
            ) || "en";


        if (languageSelect) {

            languageSelect.value =
                savedLanguage;


            languageSelect.addEventListener(
                "change",
                function () {

                    applyLanguage(
                        this.value
                    );

                }
            );

        }


        applyLanguage(
            savedLanguage
        );

    }
);


/* =====================================================
   ROLE SWITCH
===================================================== */

function switchRole() {

    const roleSelect =
        document.getElementById(
            "roleSelect"
        );


    if (!roleSelect) {
        return;
    }


    const role =
        roleSelect.value;


    if (role === "worker") {

        window.location.href =
            "worker.html";

    }


    if (role === "manager") {

        window.location.href =
            "manager.html";

    }

}


/* =====================================================
   HOME / LOGOUT
===================================================== */

function goHome() {

    window.location.href =
        "index.html";

}


/* =====================================================
   RECOMMENDATION
===================================================== */

function openRecommendation(product) {

    alert(
        "Recommendation for " +
        product +
        " will be shown here."
    );

}


/* =====================================================
   IBM BOB
===================================================== */

function askQuestion(question) {

    const input =
        document.getElementById(
            "chatInput"
        );


    if (!input) {
        return;
    }


    input.value =
        question;


    sendMessage();

}


/* =====================================================
   CHAT ENTER
===================================================== */

function handleChatKey(event) {

    if (event.key === "Enter") {

        sendMessage();

    }

}


/* =====================================================
   CHAT MESSAGE
===================================================== */

function sendMessage() {

    const input =
        document.getElementById(
            "chatInput"
        );


    const messages =
        document.getElementById(
            "chatMessages"
        );


    if (!input || !messages) {
        return;
    }


    const question =
        input.value.trim();


    if (!question) {
        return;
    }


    /*
     * User message
     */

    const userMessage =
        document.createElement("div");

    userMessage.className =
        "message user-message";


    userMessage.innerHTML = `
        <div class="message-avatar">
            👤
        </div>

        <div class="message-content">

            <span class="message-name">
                You
            </span>

            <p>
                ${escapeHtml(question)}
            </p>

        </div>
    `;


    messages.appendChild(
        userMessage
    );


    input.value = "";


    /*
     * Temporary Bob response
     */

    setTimeout(
        function () {

            const botMessage =
                document.createElement("div");

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
                        I am analyzing your inventory information.
                    </p>

                </div>
            `;


            messages.appendChild(
                botMessage
            );


            messages.scrollTop =
                messages.scrollHeight;

        },
        500
    );

}


/* =====================================================
   HTML ESCAPE
===================================================== */

function escapeHtml(text) {

    const div =
        document.createElement("div");

    div.textContent =
        text;

    return div.innerHTML;

}


/* =====================================================
   FORECAST
===================================================== */

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


    const error =
        document.getElementById(
            "forecastError"
        );


    const result =
        document.getElementById(
            "forecastResult"
        );


    if (!itemInput || !horizonInput) {
        return;
    }


    const itemId =
        itemInput.value.trim();


    const horizon =
        Number(
            horizonInput.value
        );


    if (!itemId) {

        error.textContent =
            "Please enter a Product / Item ID.";

        error.style.display =
            "block";

        result.style.display =
            "none";

        return;

    }


    error.style.display =
        "none";

    result.style.display =
        "none";

    loading.style.display =
        "block";


    try {

        /*
         * Your MAIN backend.
         *
         * Change this ONLY if your backend
         * runs on another port.
         */

        const response =
            await fetch(
                `http://127.0.0.1:8000/forecast/${encodeURIComponent(itemId)}?horizon=${horizon}`,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    }
                }
            );


        if (!response.ok) {

            let message =
                "Forecast request failed.";

            try {

                const data =
                    await response.json();

                if (data.detail) {

                    message =
                        typeof data.detail === "string"
                            ? data.detail
                            : JSON.stringify(
                                data.detail
                              );

                }

            } catch (_) {}


            throw new Error(
                message
            );

        }


        const data =
            await response.json();


        displayForecast(
            data
        );


    } catch (err) {

        console.error(
            "Forecast error:",
            err
        );


        error.textContent =
            err.message ||
            "Unable to generate forecast.";


        error.style.display =
            "block";


    } finally {

        loading.style.display =
            "none";

    }

}


/* =====================================================
   DISPLAY FORECAST
===================================================== */

function displayForecast(data) {

    const result =
        document.getElementById(
            "forecastResult"
        );


    const product =
        document.getElementById(
            "forecastProduct"
        );


    const model =
        document.getElementById(
            "forecastModel"
        );


    const days =
        document.getElementById(
            "forecastDays"
        );


    const total =
        document.getElementById(
            "forecastTotal"
        );


    const tableBody =
        document.getElementById(
            "forecastTableBody"
        );


    if (!result ||
        !product ||
        !model ||
        !days ||
        !total ||
        !tableBody) {

        return;

    }


    /*
     * Expected backend response:
     *
     * {
     *   item_id: "ITM10025",
     *   model: "Baseline (Moving Average)",
     *   horizon: 7,
     *   forecast: [
     *      {
     *        date: "2026-08-10",
     *        predicted_demand: 12
     *      }
     *   ]
     * }
     */


    const forecast =
        Array.isArray(data.forecast)
            ? data.forecast
            : [];


    const totalDemand =
        forecast.reduce(
            function (sum, row) {

                return sum +
                    Number(
                        row.predicted_demand || 0
                    );

            },
            0
        );


    product.textContent =
        data.item_id || "-";


    model.textContent =
        data.model || "-";


    days.textContent =
        data.horizon ||
        forecast.length ||
        "-";


    total.textContent =
        Math.round(
            totalDemand
        );


    tableBody.innerHTML =
        "";


    forecast.forEach(
        function (row) {

            const tr =
                document.createElement("tr");


            const date =
                document.createElement("td");

            date.textContent =
                row.date || "-";


            const demand =
                document.createElement("td");

            demand.textContent =
                row.predicted_demand ?? 0;


            tr.appendChild(
                date
            );


            tr.appendChild(
                demand
            );


            tableBody.appendChild(
                tr
            );

        }
    );


    result.style.display =
        "block";

}