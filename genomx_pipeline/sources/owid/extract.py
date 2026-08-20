"""
================================================================
 SCRIPT : EXTRACTION OUR WORLD IN DATA -> AZURE DATA LAKE (PARQUET)
================================================================
"""

import pandas as pd
import numpy as np
import io
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# ================================================================
#  CONFIGURATION
# ================================================================

OWID_SOURCES = {
    "antibiotic-consumption-human": "https://ourworldindata.org/grapher/antibiotic-consumption-rate.csv?v=1&csvType=full&useColumnShortNames=true",
    "hospital-beds": "https://ourworldindata.org/grapher/hospital-beds-per-1000-people.csv?v=1&csvType=full&useColumnShortNames=true",
    "antibiotic-use-livestock": "https://ourworldindata.org/grapher/antibiotic-use-livestock-per-kg.csv?v=1&csvType=full&useColumnShortNames=true"
}

LISTE_PAYS = [
    "Afghanistan", "Albania", "Algeria", "Andorra", "Angola",
    "Antigua and Barbuda", "Armenia", "Azerbaijan", "Bahamas", "Bahrain",
    "Bangladesh", "Barbados", "Belarus", "Belize", "Benin", "Bhutan",
    "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei",
    "Burkina Faso", "Burundi", "Cabo Verde", "Cambodia", "Cameroon",
    "Central African Republic", "Chad", "China", "Comoros", "Congo",
    "Cuba", "Djibouti", "Dominica", "Dominican Republic", "Ecuador",
    "Egypt", "El Salvador", "Equatorial Guinea", "Eritrea", "Eswatini",
    "Ethiopia", "Fiji", "Gabon", "Gambia", "Georgia", "Ghana",
    "Grenada", "Guatemala", "Guinea", "Guinea-Bissau", "Guyana",
    "Haiti", "Honduras", "India", "Indonesia", "Iran", "Iraq",
    "Jamaica", "Japan", "Jordan", "Kazakhstan", "Kenya", "Kiribati",
    "Kuwait", "Kyrgyzstan", "Laos", "Lebanon", "Lesotho", "Liberia",
    "Libya", "Liechtenstein", "Madagascar", "Malawi", "Malaysia",
    "Maldives", "Mali", "Marshall Islands", "Mauritania", "Mauritius",
    "Micronesia", "Moldova", "Monaco", "Mongolia", "Morocco",
    "Mozambique", "Myanmar", "Namibia", "Nauru", "Nepal", "Nicaragua",
    "Niger", "Nigeria", "North Macedonia", "Oman", "Pakistan", "Palau",
    "Panama", "Papua New Guinea", "Paraguay", "Peru", "Philippines",
    "Qatar", "Russia", "Rwanda", "Saint Kitts and Nevis", "Saint Lucia",
    "Saint Vincent and the Grenadines", "Samoa", "San Marino",
    "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Seychelles",
    "Sierra Leone", "Singapore", "Solomon Islands", "Somalia",
    "South Africa", "South Korea", "South Sudan", "Sri Lanka", "Sudan",
    "Suriname", "Syria", "Tajikistan", "Tanzania", "Thailand",
    "Timor-Leste", "Togo", "Tonga", "Trinidad and Tobago", "Tunisia",
    "Turkmenistan", "Tuvalu", "Uganda", "Ukraine", "United Arab Emirates",
    "Uruguay", "Uzbekistan", "Vanuatu", "Venezuela", "Vietnam",
    "Yemen", "Zambia", "Zimbabwe",
]

ANNEES_SIMULATION = list(range(2016, 2024)) # 2016 à 2023 pour les humains

# ================================================================
# MAPPING REGIONAL ET VALEURS EXPERTES (BETAIL UNIQUEMENT)
# ================================================================

# Répartition de LISTE_PAYS selon les grandes régions WOAH
MAPPING_REGIONS = {
    "Africa (WOAH)": [
        "Algeria", "Angola", "Benin", "Botswana", "Burkina Faso", "Burundi", 
        "Cabo Verde", "Cameroon", "Central African Republic", "Chad", "Comoros", 
        "Congo", "Côte d'Ivoire", "Democratic Republic of the Congo", "Djibouti", 
        "Egypt", "Equatorial Guinea", "Eritrea", "Eswatini", "Ethiopia", 
        "Ethiopia PDR", "Gabon", "Gambia", "Ghana", "Guinea", "Guinea-Bissau", 
        "Kenya", "Lesotho", "Liberia", "Libya", "Madagascar", "Malawi", "Mali", 
        "Mauritania", "Mauritius", "Morocco", "Mozambique", "Namibia", "Niger", 
        "Nigeria", "Rwanda", "Réunion", "Sao Tome and Principe", "Senegal", 
        "Seychelles", "Sierra Leone", "Somalia", "South Africa", "South Sudan", 
        "Sudan", "Sudan (former)", "Togo", "Tunisia", "Uganda", 
        "United Republic of Tanzania", "Zambia", "Zimbabwe"
    ],
    "Americas (WOAH)": [
        "Antigua and Barbuda", "Argentina", "Bahamas", "Barbados", "Belize", 
        "Bolivia (Plurinational State of)", "Brazil", "Canada", "Chile", "Colombia", 
        "Costa Rica", "Cuba", "Dominica", "Dominican Republic", "Ecuador", 
        "El Salvador", "French Guiana", "Grenada", "Guadeloupe", "Guatemala", 
        "Guyana", "Haiti", "Honduras", "Jamaica", "Martinique", "Mexico", 
        "Nicaragua", "Panama", "Paraguay", "Peru", "Puerto Rico", 
        "Saint Kitts and Nevis", "Saint Lucia", "Saint Vincent and the Grenadines", 
        "Suriname", "Trinidad and Tobago", "United States of America", "Uruguay", 
        "Venezuela (Bolivian Republic of)"
    ],
    "Asia (WOAH)": [
        "Afghanistan", "Armenia", "Australia", "Azerbaijan", "Bahrain", 
        "Bangladesh", "Bhutan", "Brunei Darussalam", "Cambodia", "China", 
        "China (Hong Kong SAR)", "China (Macao SAR)", "China (Taiwan Province of)", 
        "China, mainland", "Cook Islands", "Cyprus", "Democratic People's Republic of Korea", 
        "Fiji", "French Polynesia", "Georgia", "India", "Indonesia", 
        "Iran (Islamic Republic of)", "Iraq", "Israel", "Japan", "Jordan", 
        "Kazakhstan", "Kiribati", "Kuwait", "Kyrgyzstan", 
        "Lao People's Democratic Republic", "Lebanon", "Malaysia", "Maldives", 
        "Marshall Islands", "Micronesia (Federated States of)", "Mongolia", 
        "Myanmar", "Nauru", "Nepal", "New Caledonia", "New Zealand", "Niue", 
        "Oman", "Pakistan", "Palestine", "Papua New Guinea", "Philippines", 
        "Qatar", "Republic of Korea", "Samoa", "Saudi Arabia", "Singapore", 
        "Solomon Islands", "Sri Lanka", "Syrian Arab Republic", "Tajikistan", 
        "Thailand", "Timor-Leste", "Tonga", "Turkmenistan", "Tuvalu", "Türkiye", 
        "United Arab Emirates", "Uzbekistan", "Vanuatu", "Viet Nam", "Yemen"
    ],
    "Europe (WOAH)": [
        "Albania", "Andorra", "Austria", "Belarus", "Belgium", 
        "Belgium-Luxembourg", "Bosnia and Herzegovina", "Bulgaria", "Croatia", 
        "Czechia", "Czechoslovakia", "Denmark", "Estonia", "Faroe Islands", 
        "Finland", "France", "Germany", "Greece", "Hungary", "Iceland", 
        "Ireland", "Italy", "Latvia", "Liechtenstein", "Lithuania", 
        "Luxembourg", "Malta", "Montenegro", "Netherlands (Kingdom of the)", 
        "North Macedonia", "Norway", "Poland", "Portugal", "Republic of Moldova", 
        "Romania", "Russian Federation", "San Marino", "Serbia", 
        "Serbia and Montenegro", "Slovakia", "Slovenia", "Spain", "Sweden", 
        "Switzerland", "USSR", "Ukraine", 
        "United Kingdom of Great Britain and Northern Ireland", "Yugoslav SFR"
    ]
}

# Valeurs codées en dur (listes) pour combler les années manquantes
VALEURS_2000_2013 = {
    "Africa (WOAH)":   [20.0, 21.5, 23.0, 24.5, 26.0, 27.5, 29.0, 30.5, 32.0, 33.5, 35.0, 36.5, 38.0, 40.0],
    "Americas (WOAH)": [85.0, 86.0, 87.0, 88.0, 89.0, 91.0, 92.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0],
    "Asia (WOAH)":     [40.0, 43.0, 47.0, 51.0, 56.0, 61.0, 67.0, 72.0, 78.0, 83.0, 88.0, 92.0, 96.0, 98.0],
    "Europe (WOAH)":   [130.0, 126.0, 122.0, 118.0, 115.0, 111.0, 108.0, 105.0, 102.0, 99.0, 96.0, 94.0, 92.0, 91.0]
}

VALEURS_2022_2024 = {
    "Africa (WOAH)":   [65.0, 68.0, 71.0],
    "Americas (WOAH)": [80.0, 78.0, 76.0],
    "Asia (WOAH)":     [170.0, 175.0, 180.0],
    "Europe (WOAH)":   [45.0, 42.0, 39.0]
}

# ================================================================
# ETAPE 1 : SIMULATION DES DONNÉES MANQUANTES (HUMAINS UNIQUEMENT)
# ================================================================

def generer_antibiotiques_simules(pays_presents, metric_col_name):
    """Fonction originale intacte - pour antibiotic-consumption-human"""
    pays_a_simuler = [p for p in LISTE_PAYS if p not in pays_presents]
    np.random.seed(42)
    final_rows = []

    for country in sorted(pays_a_simuler):
        base_rate = np.random.uniform(10.0, 40.0)
        trend = np.linspace(base_rate, base_rate * 0.85, len(ANNEES_SIMULATION))
        generated_values = [round(v + np.random.normal(0, 0.5), 2) for v in trend]

        for year, val in zip(ANNEES_SIMULATION, generated_values):
            final_rows.append({
                "entity": country,
                "code": None,
                "year": year,
                metric_col_name: val
            })

    df_simulated = pd.DataFrame(final_rows)
    print(f"   -> [SIMULATION] {len(pays_a_simuler)} pays simulés de 2016 à 2023.")
    return df_simulated

# ================================================================
# TRAITEMENT SPECIFIQUE POUR LE BETAIL (LIVESTOCK)
# ================================================================

def traiter_livestock_par_pays(df_api, metric_col_name):
    """Filtre les régions, ajoute les listes de valeurs fixes, et assigne aux pays."""
    lignes_finales = []
    
    # 1. On parcourt nos 4 régions principales
    for region, pays_de_la_region in MAPPING_REGIONS.items():
        
        # A. Récupérer les années de l'API (ex: 2014-2021) pour cette région
        df_region = df_api[df_api['entity'] == region]
        
        # B. Injecter dans notre tableau final les données par PAYS
        for pays in pays_de_la_region:
            
            # --- Ajout des années 2000 à 2013 (depuis la liste en dur) ---
            annees_anciennes = list(range(2000, 2014))
            valeurs_anciennes = VALEURS_2000_2013[region]
            for annee, val in zip(annees_anciennes, valeurs_anciennes):
                lignes_finales.append({"nom de pays": pays, "annee": annee, "quantite d'antibiotic/kg": val})
                
            # --- Ajout des données réelles de l'API (2014 à 2021) ---
            if not df_region.empty:
                for _, row in df_region.iterrows():
                    lignes_finales.append({"nom de pays": pays, "annee": int(row['year']), "quantite d'antibiotic/kg": row[metric_col_name]})
            
            # --- Ajout des années 2022 à 2024 (depuis la liste en dur) ---
            annees_nouvelles = [2022, 2023, 2024]
            valeurs_nouvelles = VALEURS_2022_2024[region]
            for annee, val in zip(annees_nouvelles, valeurs_nouvelles):
                lignes_finales.append({"nom de pays": pays, "annee": annee, "quantite d'antibiotic/kg": val})

    # 2. Conversion en DataFrame
    df_final = pd.DataFrame(lignes_finales)
    print(f"   -> [BETAIL] Éclatement géographique réussi : {len(df_final)} lignes créées (2000-2024) pour {len(LISTE_PAYS)} pays.")
    return df_final


# ================================================================
# ETAPE 2 : EXTRACTION
# ================================================================

def extraire_donnees_csv(url, sous_dossier):
    headers = {'User-Agent': 'Mozilla/5.0'}
    print(f"   -> Telechargement depuis : {url.split('?')[0]}...")
    
    df = pd.read_csv(url, storage_options=headers)
    df["extracted_at"] = datetime.utcnow().isoformat()
    
    colonnes_de_base = ["entity", "code", "year", "extracted_at"]
    metric_col_name = [c for c in df.columns if c not in colonnes_de_base][0]
    
    if sous_dossier == "antibiotic-consumption-human":
        # Comportement original intact
        pays_presents = set(df["entity"].dropna().unique())
        df_simulated = generer_antibiotiques_simules(pays_presents, metric_col_name)
        df_simulated["extracted_at"] = datetime.utcnow().isoformat()
        df = pd.concat([df, df_simulated], ignore_index=True)
        df = df.sort_values(by=["entity", "year"]).reset_index(drop=True)
        
    elif sous_dossier == "antibiotic-use-livestock":
        # NOUVEAU COMPORTEMENT STRICT (Pays, Année, Quantité)
        df = traiter_livestock_par_pays(df, metric_col_name)
        # Note : On ne remet pas "extracted_at" car on a forcé les 3 colonnes strictes.

    print(f"   -> [OK] {len(df)} lignes totales traitées.")
    return df

# ================================================================
# ETAPE 3 : ENVOI ADLS
# ================================================================

def envoyer_vers_adls(blob_service_client, container_name, df, sous_dossier):
    chemin_blob = f"our-world-in-data/{sous_dossier}/owid_{sous_dossier}.parquet"
    print(f"   -> Conversion en Parquet et envoi vers : {container_name}/{chemin_blob}")

    buffer = io.BytesIO()
    table  = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    if blob_service_client:
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=chemin_blob)
        blob_client.upload_blob(buffer, overwrite=True, timeout=600)
        print(f"   -> [OK] Stocke avec succes ! Taille : {buffer.tell() / 1024:.2f} KiB\n")
    else:
        print(f"   -> [MODE TEST] Fichier généré. Taille : {buffer.tell() / 1024:.2f} KiB\n")
        
    return chemin_blob

def run(blob_service_client, container_name):
    print("=" * 65)
    print("  EXTRACTION OUR WORLD IN DATA -> AZURE DATA LAKE (PARQUET)")
    print("=" * 65)

    fichiers_generes = []
    for sous_dossier, url in OWID_SOURCES.items():
        print(f"\n Traitement du dossier : {sous_dossier.upper()}")
        df = extraire_donnees_csv(url, sous_dossier)
        chemin = envoyer_vers_adls(blob_service_client, container_name, df, sous_dossier)
        fichiers_generes.append(chemin)

    print("=" * 65)
    print("  [OK] PIPELINE TERMINE.")
    print("=" * 65)

if __name__ == "__main__":
    run(None, None)