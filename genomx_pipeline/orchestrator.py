"""
================================================================
 SCRIPT 2 : ORCHESTRATEUR (AUTOMATISATION)
================================================================
 Role : Lancer TOUS les scripts d'extraction en un seul clic.
        Chaque source de donnees a son propre dossier dans /sources/.
        Il gere la connexion Azure et la distribue aux extracteurs.
================================================================
"""

import importlib
import os
import sys
# Force UTF-8 encoding for stdout/stderr to avoid emoji crash on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
import traceback
from datetime import datetime
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError

# ================================================================
#  CONFIGURATION
# ================================================================

# Identifiants Azure (Centralisés ici)
AZURE_CONNECTION_STRING = "DefaultEndpointsProtocol=https;AccountName=genomxenvdatalake;AccountKey=dckub3e4UU+PtAtJbMU2mToodcpuZzN01pCR/xU1L8JHW+60s3QmWbnajVZlK5vYOYCJMIGJOmHx+AStHAxiHw==;EndpointSuffix=core.windows.net"
CONTAINER_NAME_RAW = "raw-data"

# Liste des sources actives (correspond aux noms des dossiers dans /sources/)
SOURCES_ACTIVES = [
    "card",
    "faostat",
    "ncbi",
    "oecd",
    "owid"
]

# ================================================================
#  LOGIQUE D'ORCHESTRATION
# ================================================================

def init_azure():
    """Initialise le client Azure et s'assure que le conteneur raw-data existe."""
    print(" Connexion a Azure Data Lake...")
    blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
    container_client = blob_service_client.get_container_client(CONTAINER_NAME_RAW)
    
    try:
        container_client.create_container()
        print(f"[OK] Conteneur '{CONTAINER_NAME_RAW}' cree sur Azure.")
    except ResourceExistsError:
        print(f"[INFO] Conteneur '{CONTAINER_NAME_RAW}' deja existant.")
    
    return blob_service_client

def lancer_tous_les_extracteurs():
    """
    Parcourt la liste SOURCES_ACTIVES et lance le script extract.py de chacun d'eux.
    """

    # Ajout du dossier racine au chemin Python pour pouvoir importer 'sources.XXX.extract'
    dossier_racine = os.path.dirname(__file__)
    if dossier_racine not in sys.path:
        sys.path.insert(0, dossier_racine)

    # Initialisation Azure
    blob_service_client = init_azure()

    # Suivi des resultats
    resultats = {
        "heure_de_lancement": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "succes"  : [],
        "echecs"  : []
    }

    print("\n" + "=" * 60)
    print("   ORCHESTRATEUR GENOMX-ENV - DEBUT DU PIPELINE")
    print(f"   Heure : {resultats['heure_de_lancement']}")
    print(f"   Nombre de sources a extraire : {len(SOURCES_ACTIVES)}")
    print("=" * 60)

    for source in SOURCES_ACTIVES:
        module_path = f"sources.{source}.extract"
        print(f"\n>>> Lancement de l'extraction : {source.upper()} ...")
        print("-" * 45)

        try:
            # Importation dynamique du module d'extraction
            module = importlib.import_module(module_path)

            # Chaque extracteur doit avoir une fonction run(blob_service_client, container_name)
            module.run(blob_service_client, CONTAINER_NAME_RAW)

            resultats["succes"].append(source)
            print(f"--> [{source}] : SUCCES")

        except Exception as e:
            # En cas d'erreur, on affiche le probleme mais on continue
            print(f"--> [{source}] : ECHEC")
            print(f"    Erreur : {e}")
            print(f"    Detail :\n{traceback.format_exc()}")
            resultats["echecs"].append({"nom": source, "erreur": str(e)})

    # ================================================================
    #  RAPPORT DE FIN DE PIPELINE
    # ================================================================
    print("\n" + "=" * 60)
    print("   RAPPORT FINAL DU PIPELINE")
    print("=" * 60)
    print(f"  [OK] Succes  ({len(resultats['succes'])}) : {', '.join(resultats['succes']) or 'Aucun'}")
    print(f"  [!!] Echecs  ({len(resultats['echecs'])}) : {', '.join([e['nom'] for e in resultats['echecs']]) or 'Aucun'}")
    print("=" * 60)

    if resultats["echecs"]:
        print("\n  ATTENTION : Certaines sources ont echoue. Verifiez les logs ci-dessus.")
    else:
        print("\n  Toutes les sources ont ete extraites avec succes !")


if __name__ == "__main__":
    lancer_tous_les_extracteurs()
