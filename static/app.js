// ======================================================================================
//  LOGIQUE CLIENT JAVASCRIPT - CHATBOT GENOMX-ENV
// ======================================================================================
// Ce script gère toute l'interactivité du navigateur :
// 1. Capture de la saisie utilisateur (Touche Entrée ou Clic sur le bouton d'envoi).
// 2. Affichage immédiat du message de l'utilisateur dans l'interface.
// 3. Affichage de l'animation de réflexion ("Thinking...") pendant le calcul de l'IA.
// 4. Appel asynchrone sécurisé de l'API backend FastAPI (/api/chat).
// 5. Conversion et affichage propre du texte Markdown retourné (avec titres, listes et gras).
// ======================================================================================

document.addEventListener("DOMContentLoaded", () => {
    // ----------------------------------------------------------------------------------
    // 1. RÉCUPÉRATION DES ÉLÉMENTS DU DOM (HTML)
    // ----------------------------------------------------------------------------------
    const chatForm = document.getElementById("chatForm");
    const userInput = document.getElementById("userInput");
    const sendBtn = document.getElementById("sendBtn");
    const chatContainer = document.getElementById("chatContainer");
    const messagesList = document.getElementById("messagesList");
    const welcomeBanner = document.getElementById("welcomeBanner");
    const thinkingIndicator = document.getElementById("thinkingIndicator");

    // ----------------------------------------------------------------------------------
    // 2. EXPANSION AUTOMATIQUE DE LA ZONE DE TEXTE (AUTO-RESIZE)
    // ----------------------------------------------------------------------------------
    // Ajuste la hauteur de la zone de saisie au fur et à mesure que l'utilisateur écrit.
    userInput.addEventListener("input", () => {
        userInput.style.height = "auto";
        userInput.style.height = (userInput.scrollHeight) + "px";
    });

    // ----------------------------------------------------------------------------------
    // 3. GESTION DU CLAVIER (TOUCHES ENTRÉE vs MAJ + ENTRÉE)
    // ----------------------------------------------------------------------------------
    // - Entrée seule : soumet le formulaire et envoie la question.
    // - Maj + Entrée : saute une ligne sans envoyer.
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event("submit"));
        }
    });

    // ----------------------------------------------------------------------------------
    // 4. GESTION DE L'ENVOI DU FORMULAIRE ET DU CYCLE DE VIE DU MESSAGE
    // ----------------------------------------------------------------------------------
    chatForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        
        const text = userInput.value.trim();
        if (!text) return;

        // Masque le message de bienvenue lors du tout premier échange
        if (welcomeBanner) {
            welcomeBanner.style.display = "none";
        }

        // Étape A : Affiche immédiatement la bulle de l'utilisateur à droite
        appendMessage("user", text);

        // Étape B : Réinitialise et désactive la zone de texte pendant le calcul pour éviter les doubles envois
        userInput.value = "";
        userInput.style.height = "auto";
        userInput.disabled = true;
        sendBtn.disabled = true;

        // Étape C : Affiche l'indicateur d'analyse en cours (Thinking)
        showThinking(true);
        scrollToBottom();

        try {
            // Étape D : Envoi de la requête POST au serveur backend FastAPI
            const response = await fetch("/api/chat", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ question: text })
            });

            // Gestion des erreurs HTTP (ex: 400, 500)
            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || "Erreur lors de la communication avec le serveur.");
            }

            const data = await response.json();

            // Étape E : Masque l'indicateur de réflexion et affiche la réponse de l'agent
            showThinking(false);
            appendMessage("assistant", data.response);

        } catch (error) {
            // En cas d'erreur de réseau ou d'API, affiche un message d'alerte convivial
            showThinking(false);
            appendMessage("assistant", `❌ **Une erreur est survenue :** ${error.message}`);
        } finally {
            // Étape F : Réactive la zone de saisie et replace le focus dessus
            userInput.disabled = false;
            sendBtn.disabled = false;
            userInput.focus();
            scrollToBottom();
        }
    });

    // ----------------------------------------------------------------------------------
    // 5. FONCTION D'AFFICHAGE D'UN MESSAGE DANS LE CHAT
    // ----------------------------------------------------------------------------------
    /**
     * Crée et insère une bulle de message dans la liste.
     * @param {string} role - 'user' pour l'utilisateur, 'assistant' pour l'IA.
     * @param {string} content - Le texte brut ou Markdown du message.
     */
    function appendMessage(role, content) {
        // Ligne englobante
        const row = document.createElement("div");
        row.className = `message-row ${role}`;

        // Avatar (icône utilisateur ou robot)
        const avatar = document.createElement("div");
        avatar.className = "message-avatar";
        avatar.innerHTML = role === "user" ? "👤" : "🤖";

        // Conteneur de la bulle de texte
        const bubble = document.createElement("div");
        bubble.className = "message-bubble";

        if (role === "assistant") {
            // Pour l'IA : conversion du Markdown en HTML propre via marked.js,
            // puis désinfection de sécurité via DOMPurify pour bloquer les failles XSS.
            const rawHtml = marked.parse(content);
            bubble.innerHTML = DOMPurify.sanitize(rawHtml);
        } else {
            // Pour l'utilisateur : simple texte sécurisé
            bubble.textContent = content;
        }

        row.appendChild(avatar);
        row.appendChild(bubble);
        messagesList.appendChild(row);
        scrollToBottom();
    }

    // ----------------------------------------------------------------------------------
    // 6. GESTION DE L'INDICATEUR DE RÉFLEXION (THINKING)
    // ----------------------------------------------------------------------------------
    /**
     * Affiche ou masque l'animation de réflexion.
     * @param {boolean} show - true pour afficher, false pour masquer.
     */
    function showThinking(show) {
        if (show) {
            thinkingIndicator.classList.add("active");
            chatContainer.appendChild(thinkingIndicator);
        } else {
            thinkingIndicator.classList.remove("active");
        }
    }

    // ----------------------------------------------------------------------------------
    // 7. DÉFILEMENT AUTOMATIQUE VERS LE BAS
    // ----------------------------------------------------------------------------------
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // ----------------------------------------------------------------------------------
    // 8. GESTION DU THÈME (CLAIR / SOMBRE)
    // ----------------------------------------------------------------------------------
    const themeToggleBtn = document.getElementById("themeToggle");
    const iconLight = document.querySelector(".icon-light");
    const iconDark = document.querySelector(".icon-dark");

    // Vérifie s'il y a un thème sauvegardé dans le navigateur
    const savedTheme = localStorage.getItem("genomx-theme") || "dark";
    
    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        localStorage.setItem("genomx-theme", theme);
        
        if (theme === "light") {
            iconLight.style.display = "none";
            iconDark.style.display = "block";
        } else {
            iconLight.style.display = "block";
            iconDark.style.display = "none";
        }
    }
    
    // Applique le thème au chargement
    applyTheme(savedTheme);

    // Bascule au clic sur le bouton
    themeToggleBtn.addEventListener("click", () => {
        const currentTheme = document.documentElement.getAttribute("data-theme");
        const newTheme = currentTheme === "light" ? "dark" : "light";
        applyTheme(newTheme);
    });
});
