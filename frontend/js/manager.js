function switchRole() {

    const role =
        document.getElementById("roleSelect").value;

    if (role === "worker") {

        window.location.href = "worker.html";

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