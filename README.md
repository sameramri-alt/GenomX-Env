# GenomX-Env : Assistant IA One Health & Antimicrobiorésistance

**GenomX-Env** est un projet d'ingénierie des données et d'Intelligence Artificielle visant à explorer l'approche "One Health" (santé humaine, animale et environnementale) face à la résistance aux antimicrobiens (AMR). 

Ce projet repose sur un pipeline de données Cloud (Microsoft Azure) couplé à un Agent IA autonome capable de générer des requêtes SQL intelligentes pour croiser des millions d'enregistrements.

---

## 🏗️ Architecture du Projet (Flux de données)

Le cycle de vie de la donnée dans GenomX-Env est totalement automatisé du script local jusqu'à la base de données requêtable par l'IA :

### 1. Extraction (Local ➡️ Cloud)
Tout le travail commence localement avec le script d'orchestration.
- **Commande** : `python genomx_pipeline/orchestrator.py`
- **Action** : Le script se connecte aux sources de données (NCBI, CARD, Hôpitaux, Agriculture...), extrait les données brutes et les transfère de manière sécurisée vers **Azure Data Lake Storage (ADLS)**.
- **Destination** : Les fichiers sont stockés dans le conteneur cloud `raw-data`.

### 2. Normalisation (Trigger Automatique Cloud)
- **Déclencheur** : Dès que les données arrivent dans le conteneur `raw-data`, un *trigger* Azure détecte l'événement automatiquement.
- **Action** : Ce trigger lance de manière autonome les **Pipelines de Normalisation** dans le cloud (nettoyage, structuration, typage).

### 3. Stockage (Azure Cosmos DB)
- **Destination finale** : Une fois normalisées, les données sont injectées dans les différentes tables de la base de données NoSQL **Azure Cosmos DB** (ex: tables `ncbi`, `card`, `hospital`, `Animals`, `soil`).
- La donnée est désormais prête, indexée et requêtable.

### 4. Interface Utilisateur & Agent IA
- **Lancement** : `python app.py`
- L'utilisateur se connecte à l'interface web (FastAPI + HTML/CSS/JS) et pose une question en langage naturel (ex: *"Quelles bactéries hébergent le gène fosX en Tunisie ?"*).
- **L'Agent IA (`agent.py`)** (via OpenRouter/Groq/Gemini) analyse la question, décide de quelles tables Cosmos DB il a besoin, génère des requêtes SQL via *Function Calling*, exécute les requêtes sur Cosmos DB, et synthétise une réponse finale structurée et scientifique.

---

## 🚀 Démarrage Rapide (Local)

L'environnement de déploiement est pensé pour s'adapter aux restrictions des abonnements de type *Azure for Students* (l'orchestration et l'IA sont gérées localement pour économiser des quotas).

### Prérequis
1. Python 3.9+
2. Un compte Azure avec Cosmos DB et un Data Lake.
3. Une clé API LLM gratuite (OpenRouter, Groq ou Gemini).

### Installation
1. Clonez ce dépôt.
2. Créez un fichier `.env` à la racine contenant vos clés (voir la configuration système).
3. Installez les dépendances :
   ```bash
   pip install fastapi uvicorn azure-cosmos azure-storage-blob openai python-dotenv
   ```

### Exécution
1. **Mettre à jour les données (ETL)** : 
   ```bash
   python genomx_pipeline/orchestrator.py
   ```
2. **Lancer l'interface Web (Chatbot)** : 
   ```bash
   python app.py
   ```
   *Accédez ensuite à l'interface via votre navigateur sur `http://127.0.0.1:8000`.*
