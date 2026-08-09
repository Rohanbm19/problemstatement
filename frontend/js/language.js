// =====================================================
// TwinStock AI - Language System
// =====================================================

let translations = {};

let currentLanguage =
    localStorage.getItem("language") || "en";


// =====================================================
// LOAD LANGUAGE FILE
// =====================================================

async function loadLanguage(language) {

    console.log("Loading language:", language);

    try {

        const response = await fetch(
            "./locales/" + language + ".json"
        );

        console.log(
            "Language file response:",
            response.status,
            language
        );

        if (!response.ok) {

            throw new Error(
                "Cannot load ./locales/" +
                language +
                ".json"
            );

        }

        translations = await response.json();

        console.log(
            "Translations loaded:",
            translations
        );

        currentLanguage = language;

        localStorage.setItem(
            "language",
            language
        );

        applyTranslations();

    }

    catch (error) {

        console.error(
            "LANGUAGE ERROR:",
            error
        );

    }

}


// =====================================================
// APPLY TRANSLATIONS
// =====================================================

function applyTranslations() {

    console.log(
        "Applying language:",
        currentLanguage
    );


    // -----------------------------------------------
    // TEXT
    // -----------------------------------------------

    document
        .querySelectorAll("[data-i18n]")
        .forEach(function (element) {

            const key =
                element.getAttribute("data-i18n");

            if (
                translations[key] !== undefined
            ) {

                element.textContent =
                    translations[key];

            }
            else {

                console.warn(
                    "Missing translation key:",
                    key
                );

            }

        });


    // -----------------------------------------------
    // PLACEHOLDERS
    // -----------------------------------------------

    document
        .querySelectorAll("[data-i18n-placeholder]")
        .forEach(function (element) {

            const key =
                element.getAttribute(
                    "data-i18n-placeholder"
                );

            if (
                translations[key] !== undefined
            ) {

                element.setAttribute(
                    "placeholder",
                    translations[key]
                );

            }

        });


    // -----------------------------------------------
    // LANGUAGE SELECT
    // -----------------------------------------------

    const languageSelect =
        document.getElementById(
            "languageSelect"
        );

    if (languageSelect) {

        languageSelect.value =
            currentLanguage;

    }

}


// =====================================================
// CHANGE LANGUAGE
// =====================================================

function changeLanguage(language) {

    console.log(
        "Changing language to:",
        language
    );

    loadLanguage(language);

}


// =====================================================
// START LANGUAGE SYSTEM
// =====================================================

document.addEventListener(
    "DOMContentLoaded",
    function () {

        console.log(
            "Language system started"
        );


        const languageSelect =
            document.getElementById(
                "languageSelect"
            );


        if (!languageSelect) {

            console.error(
                "languageSelect NOT FOUND"
            );

        }
        else {

            languageSelect.addEventListener(
                "change",
                function () {

                    changeLanguage(
                        this.value
                    );

                }
            );

        }


        // Load saved/default language
        loadLanguage(
            currentLanguage
        );

    }
);