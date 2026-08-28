// =====================================================
// TwinStock AI - Replenishment Page Module
// =====================================================

const API_BASE = (window.CONFIG && window.CONFIG.getApiUrl) ? window.CONFIG.getApiUrl() : (window.location.protocol === "file:" ? "http://127.0.0.1:8000" : "/api");
const API_URL = API_BASE.replace(/\/$/, "");
const selectedProduct = localStorage.getItem("selectedProduct");

async function loadRecommendationData() {
    if (!selectedProduct) {
        document.getElementById("productName").textContent = "No product selected";
        return;
    }

    try {
        const [recommendationResponse, riskResponse] = await Promise.all([
            fetch(`${API_URL}/inventory/${encodeURIComponent(selectedProduct)}/recommendation`),
            fetch(`${API_URL}/inventory/${encodeURIComponent(selectedProduct)}/stockout-risk`)
        ]);

        if (!recommendationResponse.ok || !riskResponse.ok) {
            throw new Error("Recommendation request failed");
        }

        const recommendation = await recommendationResponse.json();
        const risk = await riskResponse.json();

        document.getElementById("productName").textContent = recommendation.item_id;
        const productIdElement = document.getElementById("productId");
        if (productIdElement) {
            productIdElement.textContent = `Product ID: ${recommendation.item_id}`;
        }

        const metrics = document.querySelectorAll(".metrics-grid .metric strong");
        if (metrics.length >= 4) {
            metrics[0].textContent = `${recommendation.current_stock || risk.stock_level || 0} units`;
            metrics[1].textContent = `${recommendation.daily_demand || 0}/day`;
            metrics[2].textContent = `${risk.days_until_stockout ?? "N/A"} days`;
            metrics[3].textContent = `${recommendation.lead_time_days || 0} days`;
        }

        const explanationTitle = document.querySelector(".risk-explanation strong");
        const explanationText = document.querySelector(".risk-explanation p");

        if (explanationTitle) {
            explanationTitle.textContent = `${risk.risk || "LOW"} stockout risk`;
        }

        if (explanationText) {
            explanationText.textContent = recommendation.reason || "The current inventory is within expected safety limits.";
        }

        const orderQuantity = document.getElementById("orderQuantity");
        if (orderQuantity) {
            orderQuantity.value = recommendation.recommended_order_quantity || 10;
        }
    } catch (error) {
        console.error("Recommendation load failed:", error);
        const explanationP = document.querySelector(".risk-explanation p");
        if (explanationP) {
            explanationP.textContent = "Unable to load the recommendation from the backend API.";
        }
    }
}

function goBack() {
    window.location.href = "manager.html";
}

function changeQuantity(amount) {
    const input = document.getElementById("orderQuantity");
    let value = parseInt(input.value) || 0;
    value += amount;
    if (value < 1) value = 1;
    input.value = value;
}

function ignoreRecommendation() {
    const message = document.getElementById("decisionMessage");
    if (message) {
        message.textContent = "Recommendation ignored. No purchase order was created.";
        message.className = "decision-message muted";
    }
}

function approveRestock() {
    const quantity = document.getElementById("orderQuantity")?.value || 0;
    const supplier = document.getElementById("supplier")?.value || "Default";
    const message = document.getElementById("decisionMessage");

    if (message) {
        message.innerHTML = `✓ Restock approved for <strong>${quantity} units</strong>.<br>Supplier: ${supplier}<br>Purchase order created successfully.`;
        message.className = "decision-message success";
    }
}

document.addEventListener("DOMContentLoaded", loadRecommendationData);