"""
================================================================
 SCRIPT : EXTRACTION FAOSTAT -> AZURE DATA LAKE (ADLS)
================================================================
"""

import os
import requests
import pandas as pd
import io
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# ==========================================
# 1. PARAMÈTRES ET CONFIGURATIONS
# ==========================================
FAO_TOKEN = "eyJraWQiOiJVSFE2dmwrekFTaGRpSGpsOFFSK0d2ZW13RWIzSjZNdytYNTRURXZtNUNJPSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiIzMjI1ZDRkNC1iMDgxLTcwOTItZmZjMi02MDg0ZjViMzMyNGEiLCJpc3MiOiJodHRwczovL2NvZ25pdG8taWRwLmV1LXdlc3QtMS5hbWF6b25hd3MuY29tL2V1LXdlc3QtMV9iTkVMTk9DMnYiLCJ2ZXJzaW9uIjoyLCJjbGllbnRfaWQiOiIyY3NsdHNpZ2FvODVpdmhwNm9qcDFhaWM3byIsIm9yaWdpbl9qdGkiOiI4ZDM2Zjg5NC1mZjQ3LTRiMDEtYTVlYy0wNDQxYjRhMmUwOGMiLCJldmVudF9pZCI6ImNjN2E4ZmYzLTcyNWQtNDA2YS1iZTJjLTEwZjZiZWI0NjA0MiIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgZW1haWwiLCJhdXRoX3RpbWUiOjE3ODcxNTU2NzMsImV4cCI6MTc4NzE1OTI3MywiaWF0IjoxNzg3MTU1Njc0LCJqdGkiOiI4ZjE1MmQ1Zi1kNzhmLTQ3NGItYTcwNC1iNTk2YWI5YWFlNTYiLCJ1c2VybmFtZSI6InNhbWVyIn0.HVySPICKmlyYyhC7-1zgBwTp8or5oDlGFwDWonoU5sbMpIaQPbG064KIOfIQ9wfHq6O0wVpoHTQzehjU4gbl2Fo2fLR6ShQU_5lCDOAaGHxIavk9Htxll2X9AIkTMmnfFc444xNeIFckLPvmvD4QioCck3xpq2Q5yabvRg06k0purh49Nwol7x7MLVuf2CsuH6o5fK_eKDRB31WmDYH-iGpA2-h3osRr6hC0Ntxjb7dkcO_9iZIJ44-u1050nCyfxr6tWP2tWvf44fgaYrWYYPkRa9Kc9KF7iPT4yGPTtgdfXioqaKxZpC0Q3hUG65b8WEvdxHzJpuY38-nJdzoR-g"

# URLs d'extraction
URL_PESTICIDES = "https://faostatservices.fao.org/api/v1/en/data/RP?item=1331"
URL_FERTILIZERS = "https://faostatservices.fao.org/api/v1/en/data/RFN?item=3102,3103,3104"

# Chemin vers le fichier CSV sur votre bureau
CHEMIN_CSV_LIVESTOCK = r"C:\Users\GIGABYTE\Downloads\livestock.csv"


# ==========================================
# 2. EXTRACTION DEPUIS L'API & LECTURE CSV
# ==========================================
def extraire_donnees_faostat():
    headers = {"Authorization": f"Bearer {FAO_TOKEN}"}
    
    # --- A. Extraction des Pesticides (RP - item 1331) ---
    print(f"\n🌍 1/3 Interrogation API : Pesticides (RP)...")
    res_pest = requests.get(URL_PESTICIDES, headers=headers)
    df_pest = pd.DataFrame()
    if res_pest.status_code == 200:
        data_pest = res_pest.json().get("data", [])
        df_pest = pd.DataFrame(data_pest)
        if not df_pest.empty:
            df_pest["Element Code"] = df_pest["Element Code"].astype(str)
            # Filtre : Agricultural Use uniquement (element 5157)
            df_pest = df_pest[df_pest["Element Code"] == "5157"]
            df_pest = df_pest[["Area Code", "Area", "Year", "Value"]].copy()
            df_pest.rename(columns={"Value": "pesticides_t"}, inplace=True)
            df_pest["Year"] = df_pest["Year"].astype(str)
            print(f"   -> {len(df_pest)} lignes pour les Pesticides.")
    
    # --- B. Extraction des Engrais (RFN - items 3102=N, 3103=P2O5, 3104=K2O) ---
    print(f"\n🌍 2/3 Interrogation API : Engrais (RFN)...")
    res_fert = requests.get(URL_FERTILIZERS, headers=headers)
    df_fert_wide = pd.DataFrame()
    if res_fert.status_code == 200:
        data_fert = res_fert.json().get("data", [])
        df_fert = pd.DataFrame(data_fert)
        if not df_fert.empty:
            df_fert["Element Code"] = df_fert["Element Code"].astype(str)
            # Filtre : Agricultural Use uniquement (element 5157)
            df_fert = df_fert[df_fert["Element Code"] == "5157"]
            df_fert["Year"] = df_fert["Year"].astype(str)
            df_fert["Value"] = pd.to_numeric(df_fert["Value"], errors="coerce")

            # Nommage propre des engrais selon leur Item Code
            item_labels = {"3102": "nitrogen_t", "3103": "phosphate_t", "3104": "potash_t"}
            df_fert["Item Code"] = df_fert["Item Code"].astype(str)
            df_fert["Item_label"] = df_fert["Item Code"].map(item_labels)

            # PIVOT : transformer les lignes en colonnes
            df_fert_wide = df_fert.pivot_table(
                index=["Area Code", "Area", "Year"],
                columns="Item_label",
                values="Value",
                aggfunc="first"
            ).reset_index()
            df_fert_wide.columns.name = None  
            print(f"   -> {len(df_fert_wide)} lignes (pays x année) pour les Engrais.")
    
    # --- C. Fusion horizontale : Pesticides + Engrais liés par Area + Year ---
    print(f"\n🔄 Fusion horizontale Pesticides <-> Engrais sur (Area, Year)...")
    if not df_pest.empty and not df_fert_wide.empty:
        df_soil = pd.merge(
            df_pest,
            df_fert_wide,
            on=["Area Code", "Area", "Year"],
            how="outer"
        )
    elif not df_pest.empty:
        df_soil = df_pest
    elif not df_fert_wide.empty:
        df_soil = df_fert_wide
    else:
        df_soil = pd.DataFrame()
    
    if not df_soil.empty:
        df_soil["extracted_at"] = datetime.utcnow().isoformat()
        df_soil = df_soil.sort_values(by=["Area", "Year"]).reset_index(drop=True)
        print(f"[OK] Table Sol unifiee : {len(df_soil)} lignes, {len(df_soil.columns)} colonnes.")

    # --- D. Lecture du Bétail (Livestock) depuis le fichier CSV local ---
    print(f"\n📁 3/3 Récupération CSV : Bétail (Local)...")
    df_livestock = pd.DataFrame()
    try:
        # Lecture du fichier CSV
        df_livestock = pd.read_csv(CHEMIN_CSV_LIVESTOCK)
        
        # Nettoyage et préparation de base
        if not df_livestock.empty:
            if "Item Code" in df_livestock.columns:
                df_livestock["Item Code"] = df_livestock["Item Code"].astype(str)
            if "Element Code" in df_livestock.columns:
                df_livestock["Element Code"] = df_livestock["Element Code"].astype(str)
            
            # Ajout du timestamp d'extraction pour le Data Lake
            df_livestock["extracted_at"] = datetime.utcnow().isoformat()
            print(f"   -> {len(df_livestock)} lignes chargées depuis le CSV.")
    except FileNotFoundError:
        print(f"   [!] Erreur : Le fichier est introuvable au chemin {CHEMIN_CSV_LIVESTOCK}")
    except Exception as e:
        print(f"   [!] Erreur lors de la lecture du CSV : {str(e)}")

    return df_soil, df_livestock


# ==========================================
# 3. STOCKAGE DIRECT DANS AZURE BLOB STORAGE
# ==========================================
def envoyer_vers_adls(df, chemin_destination, blob_service_client, container_name):
    if df.empty:
        print(f"⚠️ Aucune donnée à envoyer pour {chemin_destination}.")
        return

    nom_fichier = f"faostat/{chemin_destination}.parquet"

    print(f"\n☁️ Envoi vers Azure : {nom_fichier}...")
    try:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=nom_fichier)
        
        buffer = io.BytesIO()
        table = pa.Table.from_pandas(df)
        pq.write_table(table, buffer)
        buffer.seek(0)
        
        blob_client.upload_blob(buffer, overwrite=True, timeout=600)
        print(f"[OK] Fichier Parquet stocké avec succès ! ({buffer.tell() / 1024:.2f} KiB)")
    except Exception as e:
        print(f"   [!] Erreur Azure : {str(e)}")

# ================================================================
# POINT D'ENTRÉE PRINCIPAL
# ================================================================
def run(blob_service_client, container_name):
    print("=" * 55)
    print("  EXTRACTION FAOSTAT -> AZURE DATA LAKE")
    print("=" * 55)
    
    # Extraction des données
    df_soil, df_livestock = extraire_donnees_faostat()
    
    # Création du DataFrame pour le dictionnaire des poids
    donnees_poids = {
        "Item Code (CPC)": ["2111", "2151", "2154", "2153", "2123", "2131", "2191", "2122", "2140", "2152"],
        "poids(kg/tete)": [400.0, 2.0, 2.8, 4.5, 35.0, 450.0, 2.2, 45.0, 80.0, 7.0]
    }
    df_poids = pd.DataFrame(donnees_poids)

    # Envoi vers ADLS
    envoyer_vers_adls(df_soil, "soil/faostat_soil", blob_service_client, container_name)
    envoyer_vers_adls(df_livestock, "livestock/faostat_livestock", blob_service_client, container_name)
    envoyer_vers_adls(df_poids, "livestock/poids_reference", blob_service_client, container_name)

if __name__ == "__main__":
    AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "votre_chaine_de_connexion_azure")
    AZURE_CONTAINER = os.getenv("AZURE_CONTAINER_NAME", "votre_nom_de_container")
    
    try:
        blob_service = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        run(blob_service, AZURE_CONTAINER)
    except Exception as e:
        print(f"Erreur fatale lors de l'initialisation de la connexion Azure : {e}")