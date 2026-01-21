import json
import re
import requests
import os
import unicodedata

# --- CONFIGURATION ---
DDRM_JSON_PATH = "ddrm_structure_complet.json"
OUTPUT_INDEX_PATH = "index_global_test.json"  # Nouveau nom pour ne pas écraser l'autre
CODE_DEPARTEMENT = "86"

KEYWORDS_RISQUES = {
    "inondation": "Inondation", "crues": "Inondation",
    "mouvement de terrain": "Mouvement de terrain",
    "séisme": "Séisme", "sismique": "Séisme",
    "feu": "Feu de forêt", "incendie": "Feu de forêt",
    "tempête": "Météo / Tempête",
    "radon": "Radon",
    "industriel": "Industriel (Seveso)",
    "nucléaire": "Nucléaire",
    "barrage": "Rupture de barrage",
    "transport": "Transport Marchandises Dangereuses"
}


def remove_accents(input_str):
    if not isinstance(input_str, str): return ""
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()


def get_liste_communes(code_dept):
    print(f"🌍 Récupération des communes...")
    try:
        url = f"https://geo.api.gouv.fr/departements/{code_dept}/communes?fields=nom&format=json"
        data = requests.get(url).json()
        return {c['nom']: remove_accents(c['nom']) for c in data}
    except:
        return {}


def detect_risk_context(titre_section):
    titre_lower = titre_section.lower()
    for keyword, category in KEYWORDS_RISQUES.items():
        if keyword in titre_lower:
            return category
    return None


def scan_hierarchy_loose(node, communes_map, index_db, current_risk=None):
    """
    Parcours simplifié :
    - On essaie de deviner le risque courant pour les données locales.
    - Pour les consignes, on prend TOUT ce qui ressemble à un tableau de sécurité.
    """
    current_title = node.get("titre", "")

    # Mise à jour du risque (juste pour les données locales)
    detected_risk = detect_risk_context(current_title)
    if detected_risk:
        current_risk = detected_risk

    for item in node.get("contenu", []):
        texte_brut = item.get("valeur") if item["type"] == "texte" else item.get("valeur_brute", "")

        if not texte_brut or len(texte_brut) < 15: continue

        # --- 1. DETECTION "BOURRIN" DES CONSIGNES ---
        # Si ça contient "AVANT" et "PENDANT" (peu importe le titre du chapitre)
        txt_low = texte_brut.lower()
        if "avant" in txt_low and "pendant" in txt_low:
            # On stocke dans GLOBAL sans se soucier du risque précis
            # On note juste le titre de la section pour aider le LLM plus tard
            ref = {
                "section_origine": current_title,  # Le LLM lira le titre pour deviner le contexte
                "type_contenu": item["type"],
                "extrait": texte_brut
            }
            if not any(r["extrait"] == texte_brut for r in index_db["_GLOBAL_"]["preuves"]):
                index_db["_GLOBAL_"]["preuves"].append(ref)

        # --- 2. DETECTION LOCALE (VILLES) ---
        # Ça on garde le filtre strict sinon on va avoir n'importe quoi
        if current_risk:
            texte_norm = remove_accents(texte_brut)
            for ville_off, ville_norm in communes_map.items():
                if ville_norm in texte_norm:
                    if re.search(r"\b" + re.escape(ville_norm) + r"\b", texte_norm):
                        index_db[ville_off]["risques"].add(current_risk)
                        if not any(r["extrait"] == texte_brut for r in index_db[ville_off]["preuves"]):
                            index_db[ville_off]["preuves"].append({
                                "risque": current_risk,
                                "section": current_title,
                                "type_contenu": item["type"],
                                "extrait": texte_brut
                            })

    # Récursion
    for sous in node.get("sous_sections", []):
        scan_hierarchy_loose(sous, communes_map, index_db, current_risk)


if __name__ == "__main__":
    with open(DDRM_JSON_PATH, "r", encoding="utf-8") as f:
        ddrm_data = json.load(f)
    communes_map = get_liste_communes(CODE_DEPARTEMENT)

    index_db = {ville: {"risques": set(), "preuves": []} for ville in communes_map.keys()}
    index_db["_GLOBAL_"] = {"risques": set(), "preuves": []}

    print("🕵️  Indexation Mode Large (Toutes les consignes dans le panier)...")
    scan_hierarchy_loose(ddrm_data, communes_map, index_db)

    # Export
    final_export = {}
    for ville, data in index_db.items():
        if data["risques"] or ville == "_GLOBAL_":
            final_export[ville] = {
                "risques": list(data["risques"]),
                "references": data["preuves"]
            }

    with open(OUTPUT_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(final_export, f, ensure_ascii=False, indent=2)

    print(f"✅ Index 'Loose' généré : {OUTPUT_INDEX_PATH}")
    print(f"📊 {len(index_db['_GLOBAL_']['preuves'])} blocs de consignes trouvés au total.")