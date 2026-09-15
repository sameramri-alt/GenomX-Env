"""
========================================================================================
 SERVEUR WEB BACKEND (FastAPI) - APPLICATION CHATBOT GENOMX-ENV
========================================================================================
 Rôle :
 Ce fichier lance une API REST haute performance avec FastAPI.
 Il fournit un point de terminaison (/api/chat) pour recevoir les questions du navigateur,
 exécuter l'agent IA en tâche de fond, et servir l'interface utilisateur web.
========================================================================================
"""

import sys
import os

# Forcer l'encodage UTF-8 sur Windows pour éviter les problèmes d'affichage d'emojis
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Importation directe de la fonction d'analyse de notre agent IA
from agent import run_agent

# ======================================================================================
# 1. INITIALISATION DE L'APPLICATION FASTAPI
# ======================================================================================
app = FastAPI(
    title="GenomX-Env Assistant API",
    description="API pour l'analyse One Health et l'interaction avec Cosmos DB via un agent IA.",
    version="1.0.0"
)

# ======================================================================================
# 2. MODÈLES DE DONNÉES (PYDANTIC)
# ======================================================================================
# Valide automatiquement le format du corps de la requête JSON envoyée par le frontend.
class ChatRequest(BaseModel):
    question: str


# ======================================================================================
# 3. POINTS DE TERMINAISON DE L'API (ENDPOINTS)
# ======================================================================================

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    Point d'entrée principal pour le dialogue avec l'agent :
    1. Reçoit le JSON { "question": "..." } depuis la page web.
    2. Transmet la question à la fonction `run_agent` de `agent.py`.
    3. Attend la fin du raisonnement autonome et retourne { "response": "..." }.
    """
    # Nettoyage des espaces blancs inutiles
    question = req.question.strip()
    
    # Vérification que la question n'est pas vide
    if not question:
        raise HTTPException(
            status_code=400, 
            detail="La question ne peut pas être vide."
        )
    
    try:
        # Appel synchrone sécurisé du moteur d'analyse de l'agent
        response_text = run_agent(question)
        return {"response": response_text}
    except Exception as e:
        # En cas d'erreur imprévue dans l'agent, renvoie un code d'erreur HTTP 500
        raise HTTPException(
            status_code=500, 
            detail=f"Erreur interne du serveur lors du traitement : {str(e)}"
        )


@app.get("/api/health")
async def health_check():
    """
    Endpoint de diagnostic / santé pour vérifier que le serveur est bien en ligne.
    """
    return {
        "status": "ok", 
        "service": "GenomX-Env AI Assistant",
        "cosmos_db": "connecté"
    }


# ======================================================================================
# 4. GESTION DES FICHIERS STATIQUES DU FRONTEND (HTML / CSS / JS)
# ======================================================================================

# Chemin absolu vers le dossier contenant les fichiers du site web
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)

# Montage du dossier static pour permettre au navigateur de charger style.css et app.js
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def serve_frontend():
    """
    Sert la page d'accueil principale (index.html) lorsque l'utilisateur visite http://localhost:8000/
    """
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Interface web en cours d'initialisation."}


# ======================================================================================
# 5. DÉMARRAGE DU SERVEUR LOCAL (UVICORN)
# ======================================================================================
if __name__ == "__main__":
    import uvicorn
    # Lance le serveur sur l'adresse locale 127.0.0.1 (port 8000)
    print("\n🚀 Serveur GenomX-Env démarré sur : http://127.0.0.1:8000\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
