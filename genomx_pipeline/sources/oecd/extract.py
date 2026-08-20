import pandas as pd
import numpy as np
import requests
import io
import pyarrow as pa
import pyarrow.parquet as pq
from azure.storage.blob import BlobServiceClient
from datetime import datetime

# ================================================================
#  CONFIGURATION
# ================================================================

# URL de l'API OCDE
OECD_URL = "https://sdmx.oecd.org/public/rest/data/OECD.ELS.HD,DSD_HEALTH_PROC@DF_HOSP_AV_LENGTH,1.2/AUS+AUT+BEL+CAN+CHL+COL+CRI+CZE+DNK+EST+FIN+FRA+DEU+GRC+HUN+ISL+IRL+ISR+ITA+KOR+LVA+LTU+LUX+MEX+NLD+NZL+NOR+POL+PRT+SVK+SVN+ESP+SWE+CHE+TUR+GBR+USA+ARG+BGR+HRV+CYP+MLT+MNE+ROU+SRB.....DICDA000............?startPeriod=1970&endPeriod=2025&dimensionAtObservation=AllDimensions&format=csvfile"

# Liste des pays non-OCDE pour lesquels on génère des valeurs estimées
NON_OECD_COUNTRIES = [
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

# Années ciblées pour la simulation
YEARS = [str(y) for y in range(2000, 2025)]


# ================================================================
# ETAPE 1 : EXTRAIRE ET FORMATER LES DONNEES OCDE (réelles)
# ================================================================

def extraire_donnees_oecd(url):
    """
    Interroge l'API OCDE, pivote le tableau et remplace les codes ISO
    par les noms complets des pays.
    """
    print(f"   -> Interrogation de l'API OCDE...")

    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()

    # 1. Lecture du flux CSV brut
    df_brut = pd.read_csv(io.StringIO(response.text))

    # 2. Pivotement : création du tableau croisé (pays x années)
    df_pivot = df_brut.pivot_table(
        index='REF_AREA',
        columns='TIME_PERIOD',
        values='OBS_VALUE'
    ).reset_index()

    # 3. Conversion Codes ISO Alpha-3 -> Noms de pays
    iso_mapping = {
        "ARG": "Argentina", "AUS": "Australia", "AUT": "Austria", "BEL": "Belgium",
        "BGR": "Bulgaria", "CAN": "Canada", "CHE": "Switzerland", "CHL": "Chile",
        "COL": "Colombia", "CRI": "Costa Rica", "CYP": "Cyprus", "CZE": "Czechia",
        "DEU": "Germany", "DNK": "Denmark", "ESP": "Spain", "EST": "Estonia",
        "FIN": "Finland", "FRA": "France", "GBR": "United Kingdom", "GRC": "Greece",
        "HRV": "Croatia", "HUN": "Hungary", "IRL": "Ireland", "ISL": "Iceland",
        "ISR": "Israel", "ITA": "Italy", "KOR": "South Korea", "LTU": "Lithuania",
        "LUX": "Luxembourg", "LVA": "Latvia", "MEX": "Mexico", "MLT": "Malta",
        "MNE": "Montenegro", "NLD": "Netherlands", "NOR": "Norway", "NZL": "New Zealand",
        "POL": "Poland", "PRT": "Portugal", "ROU": "Romania", "SRB": "Serbia",
        "SVK": "Slovakia", "SVN": "Slovenia", "SWE": "Sweden", "TUR": "Turkey",
        "USA": "United States"
    }

    df_pivot['REF_AREA'] = df_pivot['REF_AREA'].map(iso_mapping).fillna(df_pivot['REF_AREA'])
    df_pivot.rename(columns={'REF_AREA': 'Country'}, inplace=True)

    # 4. Forcer les noms de colonnes en string (sécurité Parquet)
    df_pivot.columns = df_pivot.columns.astype(str)

    # 5. Garder uniquement les colonnes des années 2000-2024 + Country
    colonnes_annees = [c for c in df_pivot.columns if c in YEARS]
    df_pivot = df_pivot[["Country"] + colonnes_annees].copy()

    # 6. Métadonnées de traçabilité
    df_pivot["data_type"] = "real"
    df_pivot["extracted_at"] = datetime.utcnow().isoformat()

    print(f"   -> [OK] {len(df_pivot)} pays OCDE extraits (données réelles).")
    return df_pivot


# ================================================================
# ETAPE 2 : GÉNÉRER LES DONNÉES ESTIMÉES (pays non-OCDE)
# ================================================================

def generer_donnees_simulees(pays_deja_presents):
    """
    Pour chaque pays manquant, génère une série temporelle estimée
    2000-2024 à partir d'une valeur de base aléatoire avec tendance
    à la baisse et bruit gaussien.
    """
    print(f"\n   -> Génération des données estimées pour les pays non-OCDE...")

    # Pays à simuler = NON_OECD_COUNTRIES - ceux déjà dans les données OCDE
    pays_a_simuler = [p for p in NON_OECD_COUNTRIES if p not in pays_deja_presents]

    np.random.seed(42)
    final_rows = []

    for country in sorted(pays_a_simuler):
        # Durée de base aléatoire entre 4.8 et 10.5 jours
        base_stay = np.random.uniform(4.8, 10.5)
        # Tendance linéaire décroissante : de base_stay à 78% de base_stay
        trend = np.linspace(base_stay, base_stay * 0.78, len(YEARS))
        # Valeurs avec bruit gaussien léger
        generated_values = [
            round(v + np.random.normal(0, 0.1), 1)
            for v in trend
        ]
        row = {"Country": country, "data_type": "simulated"}
        for year, val in zip(YEARS, generated_values):
            row[year] = val
        final_rows.append(row)

    df_simulated = pd.DataFrame(final_rows)
    df_simulated["extracted_at"] = datetime.utcnow().isoformat()
    df_simulated.columns = df_simulated.columns.astype(str)

    print(f"   -> [OK] {len(df_simulated)} pays simulés générés.")
    return df_simulated


# ================================================================
# ETAPE 3 : ENVOYER LE FICHIER FINAL VERS AZURE raw-data
# ================================================================

def envoyer_vers_adls(blob_service_client, container_name, df):
    """
    Convertit le DataFrame complet (réel + simulé) en Parquet
    et l'envoie dans Azure Blob Storage sous raw-data/oecd/...
    """
    chemin_blob = "oecd/hospital-length-of-stay/oecd_alos_global.parquet"

    print(f"\n   -> Envoi vers : {container_name}/{chemin_blob}")

    buffer = io.BytesIO()
    table = pa.Table.from_pandas(df)
    pq.write_table(table, buffer)
    buffer.seek(0)

    blob_client = blob_service_client.get_blob_client(
        container=container_name,
        blob=chemin_blob
    )
    blob_client.upload_blob(buffer, overwrite=True, timeout=600)

    print(f"   -> [OK] Stocké avec succès ! Taille : {buffer.tell() / 1024:.2f} KiB\n")
    return chemin_blob


# ================================================================
# POINT D'ENTRÉE PRINCIPAL
# ================================================================

def run(blob_service_client, container_name):
    print("=" * 65)
    print("  EXTRACTION OCDE + SIMULATION MONDIALE -> AZURE DATA LAKE")
    print("=" * 65)

    # 1. Extraction des données réelles OCDE
    print("\n Etape 1 : Donnees reelles (API OCDE)...")
    df_oecd = extraire_donnees_oecd(OECD_URL)

    # 2. Génération des données simulées pour les pays manquants
    print("\n Etape 2 : Donnees estimees (pays non-OCDE)...")
    pays_deja_presents = set(df_oecd["Country"].tolist())
    df_simulated = generer_donnees_simulees(pays_deja_presents)

    # 3. Fusion des deux tables (réel + simulé)
    print("\n Etape 3 : Fusion globale...")
    df_global = pd.concat([df_oecd, df_simulated], ignore_index=True)
    df_global = df_global.sort_values(by="Country").reset_index(drop=True)
    print(f"   -> [OK] Table finale : {len(df_global)} pays, {len(df_global.columns)} colonnes.")
    print(f"         -> {df_oecd['data_type'].value_counts().get('real', 0)} pays réels (OCDE)")
    print(f"         -> {len(df_simulated)} pays simulés (non-OCDE)")

    # 4. Sauvegarde sur Azure raw-data
    print("\n Etape 4 : Envoi vers Azure...")
    chemin = envoyer_vers_adls(blob_service_client, container_name, df_global)

    print("=" * 65)
    print(f"  [OK] PIPELINE TERMINE. Fichier : {chemin}")
    print("=" * 65)


if __name__ == "__main__":
    run(None, None)