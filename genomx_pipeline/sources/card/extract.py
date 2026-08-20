"""
================================================================
 SCRIPT : EXTRACTION BASE CARD -> AZURE DATA LAKE (ADLS)
================================================================
 Rôle : Extraire les gènes de résistance depuis le fichier JSON 
        de la base CARD et l'envoyer directement dans Azure.
================================================================
"""

import os
import json
import io
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# ==========================================
# 1. PARAMÈTRES ET CONFIGURATIONS
# ==========================================
# Emplacement de votre fichier local
CHEMIN_FICHIER_LOCAL = r"C:\Users\GIGABYTE\Desktop\card\card.json"

# ==========================================
# 2. LECTURE ET PARSING DU JSON
# ==========================================
def lire_donnees_locales():
    print(f"\n📂 Chargement et analyse du fichier {CHEMIN_FICHIER_LOCAL}...")

    if not os.path.exists(CHEMIN_FICHIER_LOCAL):
        raise FileNotFoundError(f"Le fichier n'a pas été trouvé : {CHEMIN_FICHIER_LOCAL}")

    with open(CHEMIN_FICHIER_LOCAL, "r", encoding="utf-8") as f:
        card_data = json.load(f)

    # 1. Gestion de la structure racine
    if isinstance(card_data, dict):
        entries = card_data.values()
    elif isinstance(card_data, list):
        entries = card_data
    else:
        entries = []

    records = []

    # 2. Parcours de chaque modèle de résistance
    for entry in entries:
        if not isinstance(entry, dict):
            continue

        # Récupération du nom du gène (priorité à ARO_name)
        gene_name = entry.get("ARO_name") or entry.get("CARD_short_name")
        if not gene_name:
            continue

        drug_classes = set()
        mechanisms = set()

        # Extraction et parsing du bloc ARO_category
        categories = entry.get("ARO_category")
        cat_list = []

        if isinstance(categories, dict):
            cat_list = categories.values()
        elif isinstance(categories, list):
            cat_list = categories

        for cat in cat_list:
            if not isinstance(cat, dict):
                continue

            class_type = cat.get("category_aro_class_name")
            aro_name = cat.get("category_aro_name")

            if not aro_name:
                continue

            # Filtrage selon le type de classe ARO
            if class_type == "Drug Class":
                drug_classes.add(aro_name)
            elif class_type == "Resistance Mechanism":
                mechanisms.add(aro_name)

        # Assemblage de l'enregistrement
        records.append({
            "gene_name": str(gene_name),
            "drug_class": ", ".join(sorted(drug_classes)),
            "resistance_mechanism": ", ".join(sorted(mechanisms)),
            "uploaded_at": datetime.utcnow().isoformat()
        })

    # 3. Création du DataFrame
    df = pd.DataFrame(records)
    print(f"[OK] Extraction terminée : {len(df)} gènes récupérés.")
    return df

# ==========================================
# 3. STOCKAGE DIRECT DANS AZURE BLOB STORAGE
# ==========================================
def envoyer_vers_adls(df, blob_service_client, container_name):
    nom_fichier = "card/card_donnees.parquet"

    print(f"\n☁️ Envoi du fichier vers Azure Data Lake...")
    print(f"   -> Destination : {container_name}/{nom_fichier}")

    blob_client = blob_service_client.get_blob_client(container=container_name, blob=nom_fichier)

    buffer = io.BytesIO()
    table = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    blob_client.upload_blob(buffer, overwrite=True, timeout=600)

    print(f"[OK] Fichier Parquet stocké avec succès dans ADLS !")
    print(f"     Taille sur le Cloud : {buffer.tell() / (1024*1024):.2f} MiB")

# ================================================================
# POINT D'ENTRÉE PRINCIPAL
# ================================================================
def run(blob_service_client, container_name):
    print("=" * 55)
    print("  TRANSFERT LOCAL CARD -> AZURE DATA LAKE")
    print("=" * 55)

    df_card = lire_donnees_locales()
    envoyer_vers_adls(df_card, blob_service_client, container_name)

if __name__ == "__main__":
    run()
