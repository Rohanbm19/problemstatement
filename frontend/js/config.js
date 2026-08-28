// =========================================================
// TwinStock AI - Global Configuration & API Resolution
// =========================================================

const CONFIG = {
    // Dynamic API URL Resolution
    getApiUrl() {
        // 1. Explicit global variable override
        if (window.TWINSTOCK_API_URL) {
            return window.TWINSTOCK_API_URL.replace(/\/$/, "");
        }
        
        // 2. Saved user preference in localStorage
        const savedUrl = localStorage.getItem("TWINSTOCK_API_URL");
        if (savedUrl) {
            return savedUrl.replace(/\/$/, "");
        }

        // 3. Protocol & origin-based resolution
        // If loaded directly from filesystem (file://), default to backend on 8000
        if (window.location.protocol === "file:") {
            return "http://127.0.0.1:8000";
        }

        // If running behind reverse proxy or same-origin backend, use relative /api
        const host = window.location.hostname;
        const port = window.location.port;

        if (port === "8000" && window.location.pathname.startsWith("/api")) {
            return "http://127.0.0.1:8000";
        }

        // Standard fallback for separate dev frontend port (e.g. 5500, 3000, 8080)
        if (port && port !== "8000") {
            return "http://127.0.0.1:8000";
        }

        return "/api";
    },

    // Check backend connection health
    async checkHealth() {
        const baseUrl = this.getApiUrl();
        try {
            const response = await fetch(`${baseUrl}/health`, { method: "GET" });
            if (response.ok) {
                const data = await response.json();
                this.updateStatusUI(true, baseUrl, data);
                return true;
            }
        } catch (err) {
            console.warn(`[TwinStock AI] Backend health check failed at ${baseUrl}:`, err);
        }

        // Fallback check to root endpoint
        try {
            const rootResp = await fetch(`${baseUrl}/`, { method: "GET" });
            if (rootResp.ok) {
                this.updateStatusUI(true, baseUrl);
                return true;
            }
        } catch (e) {
            console.warn(`[TwinStock AI] Root check failed at ${baseUrl}`);
        }

        this.updateStatusUI(false, baseUrl);
        return false;
    },

    // Update status badge across topbar if present
    updateStatusUI(isOnline, url) {
        const statusBadges = document.querySelectorAll(".status-badge, [data-i18n='system_live']");
        statusBadges.forEach(badge => {
            if (isOnline) {
                badge.style.backgroundColor = "rgba(16, 185, 129, 0.15)";
                badge.style.color = "#10b981";
                badge.style.borderColor = "rgba(16, 185, 129, 0.3)";
                badge.textContent = `● System Live (${url.replace(/^https?:\/\//, '')})`;
            } else {
                badge.style.backgroundColor = "rgba(239, 68, 68, 0.15)";
                badge.style.color = "#ef4444";
                badge.style.borderColor = "rgba(239, 68, 68, 0.3)";
                badge.textContent = `● Backend Offline (${url.replace(/^https?:\/\//, '')})`;
            }
        });
    }
};

// Expose globally
window.CONFIG = CONFIG;

// Auto check backend status on DOM load
document.addEventListener("DOMContentLoaded", () => {
    CONFIG.checkHealth();
});
