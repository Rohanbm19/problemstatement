// =====================================================
// TwinStock AI - Language / i18n System
// =====================================================

let translations = {};
let currentLanguage = localStorage.getItem("language") || "en";

async function loadLanguage(language) {
    try {
        const response = await fetch(`./locales/${language}.json`);
        if (!response.ok) {
            throw new Error(`Cannot load locales/${language}.json`);
        }
        translations = await response.json();
        currentLanguage = language;
        localStorage.setItem("language", language);
        document.documentElement.lang = language;
        applyTranslations();
    } catch (error) {
        console.error("Language Load Error:", error);
    }
}

function applyTranslations() {
    document.querySelectorAll("[data-i18n]").forEach(element => {
        const key = element.getAttribute("data-i18n");
        if (translations[key] !== undefined) {
            element.textContent = translations[key];
        }
    });

    document.querySelectorAll("[data-i18n-placeholder]").forEach(element => {
        const key = element.getAttribute("data-i18n-placeholder");
        if (translations[key] !== undefined) {
            element.setAttribute("placeholder", translations[key]);
        }
    });

    const languageSelect = document.getElementById("languageSelect");
    if (languageSelect) {
        languageSelect.value = currentLanguage;
    }
}

function changeLanguage(language) {
    loadLanguage(language);
}

document.addEventListener("DOMContentLoaded", () => {
    const languageSelect = document.getElementById("languageSelect");
    if (languageSelect) {
        languageSelect.addEventListener("change", function () {
            changeLanguage(this.value);
        });
    }
    loadLanguage(currentLanguage);
});