"""
================================================================
 SCRIPT : TRANSFERT FICHIER LOCAL PRÊT -> AZURE DATA LAKE (ADLS)
================================================================
 Rôle : Prendre le fichier NCBI déjà filtré et téléchargé 
        sur le PC, et l'envoyer directement dans Azure.
================================================================
"""

import pandas as pd
import io
import os
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# ==========================================
# 1. PARAMÈTRES ET CONFIGURATIONS
# ==========================================
# Emplacement de votre fichier local
CHEMIN_FICHIER_LOCAL = r"C:\Users\GIGABYTE\Downloads\isolates.tsv"

# Les colonnes exactes telles qu'elles sont ecrites dans votre fichier .tsv
COLONNES_A_EXTRAIRE = [
    '#Organism group', 
    'Location', 
    'Collection date', 
    'Isolation source',
    'AMR genotypes', 
    'AST phenotypes',
    'Isolation type', 
    'Lat/Lon'   
]

# Noms propres pour la base de donnees (sans espaces)
NOUVEAUX_NOMS = {
    '#Organism group' : 'organism_group', 
    'Location'        : 'geo_loc_name', 
    'Collection date' : 'collection_date', 
    'Isolation source': 'isolation_source',
    'AMR genotypes'   : 'amr_genotypes', 
    'AST phenotypes'  : 'ast_phenotypes',
    'Isolation type'  : 'isolation_type', 
    'Lat/Lon'         : 'lat_lon'
}

# ==========================================
# 2. LECTURE DU FICHIER LOCAL
# ==========================================
def lire_donnees_locales():
    print(f"\n📂 Lecture du fichier local en cours...")
    print(f"   -> Fichier : {CHEMIN_FICHIER_LOCAL}")

    if not os.path.exists(CHEMIN_FICHIER_LOCAL):
        raise FileNotFoundError(f"Le fichier n'a pas été trouvé à ce chemin : {CHEMIN_FICHIER_LOCAL}")

    # Lecture du fichier avec sep="\t" puisque c'est un .tsv (Tab-Separated Values)
    df = pd.read_csv(CHEMIN_FICHIER_LOCAL, sep="\t", low_memory=False)

    # On garde uniquement les colonnes demandées (si elles existent dans le fichier)
    colonnes_existantes = [col for col in COLONNES_A_EXTRAIRE if col in df.columns]
    df_extrait = df[colonnes_existantes]

    # On renomme les colonnes pour qu'elles soient propres (sans espaces)
    df_extrait = df_extrait.rename(columns=NOUVEAUX_NOMS)

    # Ajout d'une colonne avec la date de transfert pour la traçabilité
    df_extrait = df_extrait.copy()
    df_extrait["uploaded_at"] = datetime.utcnow().isoformat()

    print(f"[OK] {len(df_extrait)} lignes lues avec succès (et filtrées sur {len(colonnes_existantes)} colonnes).")
    return df_extrait


# ==========================================
# 3. STOCKAGE DIRECT DANS AZURE BLOB STORAGE
# ==========================================
def envoyer_vers_adls(df, blob_service_client, container_name):
    nom_fichier = "ncbi/ncbi_donnees.parquet"

    print(f"\n☁️ Envoi du fichier vers Azure Data Lake...")
    print(f"   -> Destination : {container_name}/{nom_fichier}")

    # Connexion à ton espace Azure
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=nom_fichier)

    # Conversion DataFrame -> Parquet en mémoire
    buffer = io.BytesIO()
    table = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    # Téléversement des données dans le Cloud (avec un timeout plus long pour éviter les erreurs)
    blob_client.upload_blob(buffer, overwrite=True, timeout=600)

    print(f"[OK] Fichier Parquet stocké avec succès dans ADLS !")
    print(f"     Taille sur le Cloud : {buffer.tell() / (1024*1024):.2f} MiB")


# ================================================================
# POINT D'ENTRÉE PRINCIPAL
# ================================================================
def run(blob_service_client, container_name):
    print("=" * 55)
    print("  TRANSFERT LOCAL NCBI -> AZURE DATA LAKE")
    print("=" * 55)

    # 1. Lecture du fichier local et filtrage
    df_ncbi = lire_donnees_locales()

    # 2. Envoi vers Azure
    envoyer_vers_adls(df_ncbi, blob_service_client, container_name)

if __name__ == "__main__":
    run()
