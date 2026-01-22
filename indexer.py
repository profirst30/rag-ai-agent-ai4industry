"""
Indexation JSON vers index de recherche
"""
import json
import re
import requests
import unicodedata


def remove_accents(text):
    """Enlève les accents"""
    if not isinstance(text, str):
        return ""
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).lower()


def get_communes(code_dept):
    """Récupère les communes via API"""
    url = f"https://geo.api.gouv.fr/departements/{code_dept}/communes?fields=nom&format=json"
    try:
        data = requests.get(url, timeout=10).json()
        return {c['nom']: remove_accents(c['nom']) for c in data}
    except:
        return {}


def detect_risque(titre):
    """Détecte le risque dans un titre"""
    risques = {
        "inondation": "Inondation", "crues": "Inondation",
        "mouvement de terrain": "Mouvement de terrain",
        "séisme": "Séisme", "sismique": "Séisme",
        "feu": "Feu de forêt", "incendie": "Feu de forêt",
        "tempête": "Météo / Tempête",
        "radon": "Radon",
        "industriel": "Industriel", "seveso": "Industriel",
        "nucléaire": "Nucléaire",
        "barrage": "Barrage",
        "transport": "Transport"
    }
    titre_lower = titre.lower()
    for key, val in risques.items():
        if key in titre_lower:
            return val
    return None


def scan(node, communes_map, index_db, risque_actuel=None, dans_section_consignes=False):
    """Parcourt le JSON et indexe"""
    titre = node.get("titre", "")
    titre_lower = titre.lower()

    # Détecter si on entre dans une section de consignes générales
    est_section_consignes = (
        "consigne" in titre_lower and ("sécurité" in titre_lower or "individuelle" in titre_lower or "générale" in titre_lower) or
        "que faire" in titre_lower or
        "comportement" in titre_lower
    )

    if est_section_consignes:
        dans_section_consignes = True

    # Mise à jour risque
    r = detect_risque(titre)
    if r:
        risque_actuel = r

    # Analyse contenu
    for item in node.get("contenu", []):
        texte = item.get("valeur") if item["type"] == "texte" else item.get("valeur_brute", "")
        if not texte or len(texte) < 15:
            continue

        txt_lower = texte.lower()

        # === DÉTECTION CONSIGNES GLOBALES (3 méthodes) ===

        # Méthode 1 : Pattern classique AVANT + PENDANT dans le même texte
        methode_1 = "avant" in txt_lower and "pendant" in txt_lower

        # Méthode 2 : On est dans une section de consignes
        methode_2 = dans_section_consignes and len(texte) > 30

        # Méthode 3 : Tableaux avec colonnes AVANT/PENDANT/APRÈS
        methode_3 = (
            item["type"] == "tableau" and
            (("avant" in txt_lower and "après" in txt_lower) or
             ("| avant" in txt_lower) or
             ("pendant" in txt_lower and "après" in txt_lower))
        )

        # Méthode 4 : Long texte avec mots-clés de consignes
        mots_cles_consignes = ["s'informer", "évacuer", "se mettre à l'abri", "prévoir", "alerter",
                                "écouter la radio", "couper", "ne pas", "fermer"]
        nb_mots_cles = sum(1 for mot in mots_cles_consignes if mot in txt_lower)
        methode_4 = len(texte) > 100 and nb_mots_cles >= 2

        if methode_1 or methode_2 or methode_3 or methode_4:
            ref = {"section": titre, "type": item["type"], "texte": texte}
            if not any(r["texte"] == texte for r in index_db["_GLOBAL_"]["refs"]):
                index_db["_GLOBAL_"]["refs"].append(ref)

        # === 2. DONNÉES LOCALES (inchangé) ===
        if risque_actuel:
            texte_norm = remove_accents(texte)
            for ville_off, ville_norm in communes_map.items():
                if ville_norm in texte_norm:
                    if re.search(r"\b" + re.escape(ville_norm) + r"\b", texte_norm):
                        index_db[ville_off]["risques"].add(risque_actuel)
                        if not any(r["texte"] == texte for r in index_db[ville_off]["refs"]):
                            index_db[ville_off]["refs"].append({
                                "risque": risque_actuel,
                                "section": titre,
                                "type": item["type"],
                                "texte": texte
                            })

    # Récursion (propager le flag dans_section_consignes)
    for sous in node.get("sous_sections", []):
        scan(sous, communes_map, index_db, risque_actuel, dans_section_consignes)


def build_index(json_path, code_dept, index_path):
    """Crée l'index"""

    print(f"  📂 Chargement JSON : {os.path.basename(json_path)}")
    # Chargement
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"  ✓ JSON chargé")

    print(f"  🌍 Récupération des communes du département {code_dept}...")
    communes = get_communes(code_dept)
    if not communes:
        print(f"  ⚠ Pas de communes pour {code_dept}")
        return
    print(f"  ✓ {len(communes)} communes récupérées")

    # Init index
    print(f"  🗂️  Initialisation de l'index...")
    index_db = {ville: {"risques": set(), "refs": []} for ville in communes.keys()}
    index_db["_GLOBAL_"] = {"risques": set(), "refs": []}

    # Scan
    print(f"  🔍 Scan du document en cours...")
    scan(data, communes, index_db)

    # Comptage
    nb_villes_avec_donnees = len([v for v, d in index_db.items() if v != "_GLOBAL_" and d["risques"]])
    nb_consignes_globales = len(index_db["_GLOBAL_"]["refs"])

    print(f"  📊 Trouvé : {nb_villes_avec_donnees} communes avec données, {nb_consignes_globales} consignes globales")

    # Export
    print(f"  💾 Export de l'index...")
    final = {}
    for ville, d in index_db.items():
        if d["risques"] or ville == "_GLOBAL_":
            final[ville] = {
                "risques": sorted(list(d["risques"])),
                "refs": d["refs"]
            }

    os.makedirs(os.path.dirname(index_path), exist_ok=True)
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"  ✅ Indexé : {json_path} → {index_path}")


import os