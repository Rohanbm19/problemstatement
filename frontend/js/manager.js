// =========================================================
// TwinStock AI - Manager Dashboard Module
// =========================================================

const BACKEND_URL = (window.CONFIG && window.CONFIG.getApiUrl) ? window.CONFIG.getApiUrl() : (window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "/api");

function switchRole() {
    const roleSelect = document.getElementById("roleSelect");
    if (roleSelect && roleSelect.value === "worker") {
        window.location.href = "worker.html";
    }
}

function goHome() {
    window.location.href = "index.html";
}

function openRecommendation(product) {
    localStorage.setItem("selectedProduct", product);
    window.location.href = "replenishment.html";
}

// ---------------------------------------------------------
// DASHBOARD DATA LOADER
// ---------------------------------------------------------
async function loadDashboardData() {
    try {
        console.log("Loading TwinStock AI dashboard...");
        const inventoryResponse = await fetch(`${BACKEND_URL}/inventory/`);
        if (!inventoryResponse.ok) {
            throw new Error("Unable to load inventory.");
        }

        const inventory = await inventoryResponse.json();

        // Update Summary Counts
        const totalProducts = inventory.length;
        const totalInventory = inventory.reduce((sum, item) => sum + Number(item.stock_level || 0), 0);

        document.getElementById("totalProducts").textContent = totalProducts.toLocaleString();
        document.getElementById("totalInventory").textContent = totalInventory.toLocaleString();

        // Fetch Granite Forecast for each item
        const itemsWithForecast = await Promise.all(
            inventory.map(async (item) => {
                try {
                    const itemId = item.item_id;
                    const forecastResponse = await fetch(`${BACKEND_URL}/forecast/${encodeURIComponent(itemId)}?horizon=7`, {
                        method: "POST",
                        headers: { "Content-Type": "application/json" }
                    });

                    if (!forecastResponse.ok) throw new Error(`Forecast failed for ${itemId}`);

                    const forecastData = await forecastResponse.json();
                    const forecast = Array.isArray(forecastData.forecast) ? forecastData.forecast : [];

                    const totalPredictedDemand = forecast.reduce((total, point) => total + Number(point.predicted_demand || 0), 0);
                    const predictedDailyDemand = forecast.length > 0 ? totalPredictedDemand / forecast.length : 0;
                    const currentStock = Number(item.stock_level || 0);

                    let remainingStock = currentStock;
                    let daysUntilStockout = null;

                    for (let i = 0; i < forecast.length; i++) {
                        remainingStock -= Number(forecast[i].predicted_demand || 0);
                        if (remainingStock <= 0) {
                            daysUntilStockout = i + 1;
                            break;
                        }
                    }

                    let risk = "LOW";
                    if (totalPredictedDemand <= 0) risk = "LOW";
                    else if (currentStock < totalPredictedDemand * 0.5) risk = "HIGH";
                    else if (currentStock < totalPredictedDemand) risk = "MEDIUM";
                    else if (currentStock > totalPredictedDemand * 3) risk = "OVERSTOCK";

                    const recommendedQuantity = Math.max(0, Math.ceil(totalPredictedDemand - currentStock));

                    return {
                        ...item,
                        risk,
                        currentStock,
                        forecast,
                        forecastModel: forecastData.model || "Granite Time Series (IBM TTM)",
                        totalPredictedDemand,
                        predictedDailyDemand,
                        daysUntilStockout,
                        recommendedQuantity
                    };
                } catch (error) {
                    console.error(`Forecast error for ${item.item_id}:`, error);
                    return {
                        ...item,
                        risk: "UNKNOWN",
                        currentStock: Number(item.stock_level || 0),
                        forecast: [],
                        forecastModel: "Unavailable",
                        totalPredictedDemand: 0,
                        predictedDailyDemand: 0,
                        daysUntilStockout: null,
                        recommendedQuantity: 0
                    };
                }
            })
        );

        // Update Risk Metrics
        const highRiskItems = itemsWithForecast.filter(i => i.risk === "HIGH");
        const overstockItems = itemsWithForecast.filter(i => i.risk === "OVERSTOCK");

        const highRiskEl = document.getElementById("highRisk");
        if (highRiskEl) highRiskEl.textContent = highRiskItems.length.toLocaleString();

        const overstockEl = document.getElementById("overstock");
        if (overstockEl) overstockEl.textContent = overstockItems.length.toLocaleString();

        // Sort items for suggestions
        const priorityOrder = { HIGH: 1, MEDIUM: 2, OVERSTOCK: 3, LOW: 4, UNKNOWN: 5 };
        itemsWithForecast.sort((a, b) => priorityOrder[a.risk] - priorityOrder[b.risk]);

        // Render AI Suggestions Cards
        const suggestions = itemsWithForecast.filter(i => i.risk !== "LOW" && i.risk !== "UNKNOWN").slice(0, 3);
        const suggestionCards = document.querySelectorAll(".suggestion-card");

        suggestionCards.forEach((card, index) => {
            const item = suggestions[index];
            if (!item) {
                card.style.display = "none";
                return;
            }

            card.style.display = "block";
            let riskClass = item.risk === "HIGH" ? "high" : item.risk === "MEDIUM" ? "medium" : "warning";
            let riskLabel = item.risk === "HIGH" ? "HIGH RISK" : item.risk === "MEDIUM" ? "MEDIUM RISK" : "OVERSTOCK";
            let riskDot = item.risk === "HIGH" ? "red-dot" : item.risk === "MEDIUM" ? "orange-dot" : "yellow-dot";

            let message = "";
            if (item.risk === "HIGH") {
                message = item.daysUntilStockout
                    ? `Granite predicts stockout in <strong>${item.daysUntilStockout} days</strong>.`
                    : `Granite predicts demand will exceed available inventory.`;
            } else if (item.risk === "MEDIUM") {
                message = `Granite predicts inventory pressure. 7-day demand is <strong>${item.totalPredictedDemand.toFixed(1)} units</strong>.`;
            } else {
                message = `Granite predicts demand of only <strong>${item.totalPredictedDemand.toFixed(1)} units</strong> over 7 days.`;
            }

            card.className = `suggestion-card ${riskClass}`;
            card.innerHTML = `
                <div class="suggestion-top">
                    <div class="product-info">
                        <span class="risk-dot ${riskDot}"></span>
                        <div>
                            <h3>${item.item_id}</h3>
                            <span>Product ID: ${item.item_id}</span>
                        </div>
                    </div>
                    <span class="risk-label ${riskClass}-label">${riskLabel}</span>
                </div>
                <p class="suggestion-message">${message}</p>
                <div class="suggestion-details">
                    <div><span>Current Stock</span><strong>${item.currentStock.toLocaleString()} units</strong></div>
                    <div><span>7-Day Demand</span><strong>${item.totalPredictedDemand.toFixed(1)} units</strong></div>
                    <div><span>Recommended</span><strong>${item.recommendedQuantity.toLocaleString()} units</strong></div>
                </div>
                <div style="margin-top:10px; font-size:12px; opacity:0.8;">🤖 Powered by ${item.forecastModel}</div>
                <button class="${index === 0 ? 'primary-btn' : 'secondary-btn'}" type="button">View Recommendation →</button>
            `;

            const btn = card.querySelector("button");
            if (btn) btn.addEventListener("click", () => openRecommendation(item.item_id));
        });

        // Render Inventory Table
        renderInventoryTable(itemsWithForecast);

    } catch (error) {
        console.error("Dashboard error:", error);
    }
}

function renderInventoryTable(items) {
    const tableBody = document.getElementById("inventoryTableBody");
    if (!tableBody) return;

    if (!items || items.length === 0) {
        tableBody.innerHTML = `<tr><td colspan="6" style="text-align:center;">No inventory items found.</td></tr>`;
        return;
    }

    tableBody.innerHTML = items.map(item => {
        let badgeClass = "badge-success";
        let statusText = "In Stock";
        if (item.risk === "HIGH") { badgeClass = "badge-danger"; statusText = "High Risk"; }
        else if (item.risk === "MEDIUM") { badgeClass = "badge-warning"; statusText = "Medium Risk"; }
        else if (item.risk === "OVERSTOCK") { badgeClass = "badge-info"; statusText = "Overstocked"; }

        return `
            <tr>
                <td><strong>${item.item_id}</strong></td>
                <td>${item.currentStock.toLocaleString()}</td>
                <td>${item.totalPredictedDemand ? item.totalPredictedDemand.toFixed(1) : 0} / 7 days</td>
                <td><span class="badge ${badgeClass}">${statusText}</span></td>
                <td>${item.storage_location_id || item.location || 'Main Warehouse'}</td>
                <td>
                    <button class="action-btn" onclick="openRecommendation('${item.item_id}')">Review</button>
                </td>
            </tr>
        `;
    }).join('');
}

// ---------------------------------------------------------
// MANUAL FORECAST GENERATOR
// ---------------------------------------------------------
async function generateForecast() {
    const itemInput = document.getElementById("forecastItemId");
    const horizonInput = document.getElementById("forecastHorizon");
    const loading = document.getElementById("forecastLoading");
    const result = document.getElementById("forecastResult");
    const errorBox = document.getElementById("forecastError");

    if (!itemInput || !horizonInput || !loading || !result || !errorBox) return;

    const itemId = itemInput.value.trim();
    const horizon = Number(horizonInput.value) || 7;

    if (!itemId) {
        errorBox.textContent = "Please enter an Item ID.";
        errorBox.style.display = "block";
        return;
    }

    loading.style.display = "block";
    result.style.display = "none";
    errorBox.style.display = "none";

    try {
        const response = await fetch(`${BACKEND_URL}/forecast/${encodeURIComponent(itemId)}?horizon=${horizon}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" }
        });

        const data = await response.json();
        if (!response.ok) throw new Error(data.detail || "Forecast request failed.");

        const forecast = Array.isArray(data.forecast) ? data.forecast : [];

        document.getElementById("forecastProduct").textContent = data.item_id || itemId;
        document.getElementById("forecastModel").textContent = data.model || "Granite Time Series";
        document.getElementById("forecastDays").textContent = data.horizon || horizon;

        const totalDemand = forecast.reduce((sum, p) => sum + Number(p.predicted_demand || 0), 0);
        document.getElementById("forecastTotal").textContent = `${totalDemand.toFixed(1)} units`;

        const tableBody = document.getElementById("forecastTableBody");
        if (tableBody) {
            tableBody.innerHTML = forecast.map(p => `
                <tr>
                    <td>${p.date}</td>
                    <td><strong>${Number(p.predicted_demand || 0).toFixed(1)}</strong> units</td>
                </tr>
            `).join('');
        }

        result.style.display = "block";
    } catch (err) {
        console.error("Forecast error:", err);
        errorBox.textContent = err.message || "Forecast failed.";
        errorBox.style.display = "block";
    } finally {
        loading.style.display = "none";
    }
}

// ---------------------------------------------------------
// AI CHATBOT (IBM BOB)
// ---------------------------------------------------------
function handleChatKey(event) {
    if (event.key === "Enter") sendMessage();
}

function askQuestion(q) {
    const input = document.getElementById("chatInput");
    if (input) {
        input.value = q;
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById("chatInput");
    const chat = document.getElementById("chatMessages");
    if (!input || !chat) return;

    const message = input.value.trim();
    if (!message) return;

    const userMsg = document.createElement("div");
    userMsg.className = "message user-message";
    userMsg.innerHTML = `<div class="message-avatar">👤</div><div class="message-content"><span class="message-name">You</span><p>${escapeHtml(message)}</p></div>`;
    chat.appendChild(userMsg);
    input.value = "";

    setTimeout(() => {
        const response = "Based on Granite AI predictions, focus on high-risk stock items and review replenish suggestions before ordering.";
        const botMsg = document.createElement("div");
        botMsg.className = "message bot-message";
        botMsg.innerHTML = `<div class="message-avatar">🤖</div><div class="message-content"><span class="message-name">IBM Bob</span><p>${response}</p></div>`;
        chat.appendChild(botMsg);
        chat.scrollTop = chat.scrollHeight;
    }, 400);
}

function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
}

document.addEventListener("DOMContentLoaded", () => {
    loadDashboardData();
});
