"""
========================================================================================
 AGENT IA GENOMX-ENV - MOTEUR DE RAISONNEMENT ONE HEALTH
========================================================================================
 Rôle : 
 Cet agent autonome analyse des questions scientifiques sur la résistance aux
 antimicrobiens (AMR) en croisant les données humaines, animales et environnementales.
 Il interroge la base Azure Cosmos DB en direct via le mécanisme de "Function Calling".
========================================================================================
"""

import sys
import os
import json

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from azure.cosmos import CosmosClient
from openai import OpenAI

# ======================================================================================
# 1. INITIALISATION DES VARIABLES D'ENVIRONNEMENT ET DES CLIENTS
# ======================================================================================

# Charge les clés secrètes définies dans le fichier .env (COSMOS_URI, COSMOS_KEY, etc.)
load_dotenv()

# Connexion sécurisée au compte Azure Cosmos DB
cosmos_client = CosmosClient(
    os.getenv("COSMOS_URI"),
    credential=os.getenv("COSMOS_KEY")
)

# Sélection de la base de données principale du projet
db = cosmos_client.get_database_client("genomx_db")

# Récupération des clés API pour l'intelligence artificielle
openrouter_key = os.getenv("OPENROUTER_API_KEY")
groq_key = os.getenv("GROQ_API_KEY")
gemini_key = os.getenv("GEMINI_API_KEY")

# Configuration automatique du fournisseur IA :
# - Priorité 1 : OpenRouter (modèles gratuits très puissants)
# - Priorité 2 : Groq
# - Priorité 3 : Google Gemini
if openrouter_key:
    llm = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=openrouter_key
    )
    # Modèle auto-sélectionné (le meilleur gratuit disponible à l'instant T)
    MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
elif groq_key:
    llm = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_key
    )
    MODEL = "llama-3.3-70b-versatile"
else:
    llm = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=gemini_key
    )
    # Modèle Gemini configurable depuis le .env (par défaut gemini-3.7-flash)
    MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")


# ======================================================================================
# 2. DÉFINITION DES OUTILS (FUNCTION CALLING)
# ======================================================================================
# Ce dictionnaire JSON Schema décrit au modèle IA les fonctions Python qu'il a le droit d'appeler.
# Le modèle décide lui-même quand et comment utiliser cet outil selon la question de l'utilisateur.

tools = [{
    "type": "function",
    "function": {
        "name": "execute_cosmos_query",
        "description": (
            "Exécute une requête SQL en lecture seule sur l'un des conteneurs Cosmos DB de la base genomx_db."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "enum": ["ncbi", "card", "hospital", "Animals", "soil"],
                    "description": "Nom exact de la table/conteneur cible dans Cosmos DB."
                },
                "query": {
                    "type": "string",
                    "description": "Requête SQL Cosmos DB valide avec l'alias 'c' (ex: SELECT * FROM c WHERE c.Country = 'France')."
                }
            },
            "required": ["container_name", "query"]
        }
    }
}]


def execute_cosmos_query(container_name: str, query: str) -> str:
    """
    Exécute physiquement la requête SQL générée par l'IA sur Azure Cosmos DB.
    
    Paramètres :
        - container_name (str) : Le nom du conteneur ('ncbi', 'card', etc.)
        - query (str) : La requête SQL Cosmos DB.
        
    Retourne :
        - str : Une chaîne JSON contenant les 15 premiers résultats (pour ne pas saturer la mémoire du LLM).
    """
    try:
        # Récupération du client pour le conteneur spécifié
        container = db.get_container_client(container_name)
        
        # Exécution de la requête avec support des requêtes multi-partitions (cross-partition)
        results = list(container.query_items(query=query, enable_cross_partition_query=True))
        
        # Limitation à 15 enregistrements pour optimiser la taille du prompt et le temps de réponse
        return json.dumps(results[:15], ensure_ascii=False)
    except Exception as e:
        # En cas d'erreur de syntaxe ou de connexion, on renvoie le message d'erreur à l'IA pour qu'elle puisse s'auto-corriger
        return json.dumps({"error": str(e)}, ensure_ascii=False)


# ======================================================================================
# 3. PROMPT SYSTÈME : LE "CERVEAU" ET LES RÈGLES DE L'AGENT
# ======================================================================================
# Ce prompt définit l'expertise, le périmètre des 5 tables, les règles de syntaxe Cosmos DB
# et la chaîne de raisonnement causal One Health.

SYSTEM_PROMPT = """
Tu es un agent IA expert en analyse de données One Health (interface humain-animal-environnement) et en résistance aux antimicrobiens (AMR).
Tu as accès à la base Azure Cosmos DB `genomx_db` avec 5 tables :

1. `ncbi`: Isolats bactériens. Champs : bacterie_name, pays, collection_year, genotypes, isolation_type ('clinical', 'environment/other'), isolation_source ('human', 'chicken', 'soil', 'swine', etc.).
2. `card`: Gènes de résistance. Champs : gene_name, antibiotic, resistance_mechanism.
3. `hospital`: Données santé humaine. Champs : Country, year, antibiotic_rate, beds_per_1000_people, average_length_of_stay.
4. `Animals`: Données élevage. Champs : Country, Year, Nombre_Total_Animaux, Poids_Total, quantite_d'antibiotic/kg.
5. `soil`: Données agricoles/sols. Champs : Pays, Year, pesticides_t, nitrogen_t, phosphate_t, potash_t.

RÈGLES SQL COSMOS DB :
- Alias obligatoire 'c' : SELECT * FROM c WHERE ...
- Recherche insensible à la casse obligatoire (utiliser 'true' ou LOWER()) :
    • Pour card : CONTAINS(c.gene_name, 'fosX', true) OU CONTAINS(LOWER(c.gene_name), 'fosx')
    • Pour ncbi : (CONTAINS(c.genotypes, 'fosX', true) OR ARRAY_CONTAINS(c.genotypes, 'fosX') OR CONTAINS(LOWER(c.genotypes), 'fosx'))
    • Pour bacteries : CONTAINS(c.bacterie_name, 'Listeria', true)
- TOP obligatoire pour limiter : SELECT TOP 25 * FROM c WHERE ...
- ⚠️ INTERDICTION STRICTE du 'GROUP BY' (non supporté par Cosmos DB). Effectue les calculs et comptages toi-même en mémoire.

GESTION DU PÉRIMÈTRE DES GÈNES :
- Si la question cible un gène PRÉCIS (ex: 'gène fosX'), interroge `card` UNIQUEMENT pour ce gène précis. N'interroge pas les gènes secondaires co-présents.
- Si la question porte sur une bactérie générale sans gène précisé, extrais tous les gènes trouvés et cherche-les tous dans `card`.

GÉRER L'HÉTÉROGÉNÉITÉ DES DONNÉES (RÈGLES IMPORTANTES) :
- Noms de pays : Attention, le nom d'un pays peut s'écrire différemment selon la table (ex: "USA", "United States of America", "America"). Si une recherche sur un pays échoue, utilise ton intelligence pour tenter d'autres dénominations ou alias possibles.
- Table de contexte : Si `isolation_type` dans `ncbi` est 'environment/other', tu DOIS analyser le champ `isolation_source` pour déduire s'il faut interroger la table `Animals` (ex: 'chicken', 'swine', 'bovine') ou la table `soil` (ex: 'soil', 'water', 'plant').

RAISONNEMENT D'ANALYSE CAUSALE :
1. Interroge `ncbi` pour identifier les isolats, les années et la source (clinical vs environnement/animal/sol).
2. Selon la source trouvée, interroge la table de contexte correspondante (`hospital`, `Animals` ou `soil`).
3. Interroge `card` pour comprendre le mécanisme d'action et l'antibiotique ciblé par le gène.
4. ARRÊTE les requêtes dès que tu as ces 3 éléments et formule ta synthèse One Health.

Réponds TOUJOURS en français, de manière claire, bienveillante et structurée (avec du texte en gras, des puces et des sections bien délimitées).
"""


# ======================================================================================
# 4. BOUCLE AUTONOME D'EXÉCUTION (AGENTIC LOOP)
# ======================================================================================

def run_agent(question_utilisateur: str) -> str:
    """
    Orchestre l'exécution autonome de l'agent pour répondre à une question :
    1. Envoie la question et le prompt système au LLM.
    2. Si le LLM demande une requête SQL, l'exécute sur Cosmos DB.
    3. Renvoie les résultats à l'IA pour qu'elle continue son raisonnement.
    4. Répète jusqu'à ce que l'IA ait rédigé sa réponse finale (max 12 étapes).
    
    Paramètre :
        - question_utilisateur (str) : La question posée par l'utilisateur.
        
    Retourne :
        - str : La réponse textuelle finale rédigée par l'IA.
    """
    # Historique de la conversation pour cette requête
    messages_history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question_utilisateur}
    ]
    
    # Boucle d'autonomie (jusqu'à 12 étapes de va-et-vient entre le modèle et la base)
    for etape in range(12):
        try:
            # Appel à l'API LLM avec mise à disposition des outils
            response = llm.chat.completions.create(
                model=MODEL,
                messages=messages_history,
                tools=tools,
                tool_choice="auto"
            )
        except Exception as e:
            return f"❌ Une erreur est survenue lors de l'appel au modèle IA : {str(e)}"
        
        message = response.choices[0].message
        messages_history.append(message)
        
        # Cas 1 : L'IA a terminé son analyse et n'a plus besoin d'exécuter de requêtes SQL
        # -> On retourne directement le texte de sa réponse finale.
        if not message.tool_calls:
            return message.content or "Je n'ai pas pu trouver d'informations pertinentes."
            
        # Cas 2 : L'IA a décidé qu'elle avait besoin de données dans Cosmos DB
        # -> On exécute chaque requête SQL demandée et on lui renvoie les données.
        for tool_call in message.tool_calls:
            try:
                # Décodage des arguments générés par le LLM (ex: table et requête SQL)
                args = json.loads(tool_call.function.arguments)
                resultat = execute_cosmos_query(args['container_name'], args['query'])
            except Exception as err:
                resultat = json.dumps({"error": str(err)})
            
            # On ajoute le résultat dans l'historique sous le rôle 'tool'
            messages_history.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": resultat
            })
            
    # Message de secours si les 12 étapes ont été consommées
    return "L'analyse a nécessité trop d'étapes de recherche. Veuillez reformuler votre question de manière plus spécifique."


# Point d'entrée pour tester le script directement dans le terminal
if __name__ == "__main__":
    test_question = "Quelles sont les bactéries extraites en Tunisie ?"
    print(f"\n❓ Test : {test_question}\n")
    print(run_agent(test_question))