const DEFAULT_LANGUAGE = "en";


async function setLanguage(language) {

    try {

        const response = await fetch(
            `locales/${language}.json`
        );

        if (!response.ok) {
            throw new Error(
                `Language file not found: ${language}`
            );
        }

        const translations =
            await response.json();


        // Translate normal text
        document
            .querySelectorAll("[data-i18n]")
            .forEach(element => {

                const key =
                    element.getAttribute("data-i18n");

                if (
                    Object.prototype.hasOwnProperty.call(
                        translations,
                        key
                    )
                ) {

                    element.textContent =
                        translations[key];

                }

            });


        // Translate placeholders
        document
            .querySelectorAll(
                "[data-i18n-placeholder]"
            )
            .forEach(element => {

                const key =
                    element.getAttribute(
                        "data-i18n-placeholder"
                    );

                if (
                    Object.prototype.hasOwnProperty.call(
                        translations,
                        key
                    )
                ) {

                    element.placeholder =
                        translations[key];

                }

            });


        // Save selected language
        localStorage.setItem(
            "language",
            language
        );


        // Update HTML language
        document.documentElement.lang =
            language;


    } catch (error) {

        console.error(
            "Language loading error:",
            error
        );

    }

}


async function initializeLanguage() {

    const savedLanguage =
        localStorage.getItem("language")
        || DEFAULT_LANGUAGE;


    const languageSelect =
        document.getElementById(
            "languageSelect"
        );


    if (languageSelect) {

        languageSelect.value =
            savedLanguage;


        languageSelect.addEventListener(
            "change",
            function () {

                setLanguage(
                    this.value
                );

            }
        );

    }


    await setLanguage(
        savedLanguage
    );

}


document.addEventListener(
    "DOMContentLoaded",
    initializeLanguage
);