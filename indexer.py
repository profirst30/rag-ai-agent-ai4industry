"""
Indexation JSON vers index de recherche
Version avec regroupement des textes consecutifs d'une meme section
"""
import json
import re
import requests
import unicodedata
import os


def remove_accents(text):
    """Enleve les accents"""
    if not isinstance(text, str):
        return ""
    return "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c)).lower()


def get_communes(code_dept):
    """Recupere les communes via API"""
    url = f"https://geo.api.gouv.fr/departements/{code_dept}/communes?fields=nom&format=json"
    try:
        data = requests.get(url, timeout=10).json()
        return {c['nom']: remove_accents(c['nom']) for c in data}
    except:
        return {}


def detect_risque(titre):
    """Detecte le risque dans un titre"""
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


def detect_phone(text):
    """Detecte un numero de telephone"""
    pattern = r'(?:\+33\s?|0)(?:\d[\s.\-]?){9}'
    return bool(re.search(pattern, text))


def detect_url(text):
    """Detecte une URL ou site web"""
    pattern = r'(?:https?://|www\.|[a-zA-Z0-9-]+\.(?:fr|com|gouv|org|net|eu))'
    return bool(re.search(pattern, text.lower()))


def classify_content(text, item_type):
    """Classifie le type de contenu"""
    if detect_phone(text):
        return "telephone"
    elif detect_url(text):
        return "url"
    else:
        return item_type


def is_important_short_text(text):
    """Verifie si un texte court est quand meme important"""
    if len(text) < 5:
        return False

    if detect_phone(text):
        return True

    if detect_url(text):
        return True

    patterns_importants = [
        r'\d+\s*(?:communes?|personnes?|habitants?|victimes?)',
        r'\d+[.,]\d+\s*(?:m|km|ha)',
        r'(?:19|20)\d{2}',
        r'\d+\s*(?:%|ha|km²|m²)',
    ]

    for pattern in patterns_importants:
        if re.search(pattern, text):
            return True

    return False


def merge_consecutive_refs(refs_list):
    """
    Fusionne les references consecutives d'une meme section

    Args:
        refs_list: Liste de references

    Returns:
        Liste de references fusionnees
    """
    if not refs_list:
        return []

    merged = []
    current_group = None

    for ref in refs_list:
        section = ref.get("section", "")
        path = ref.get("path", [])

        # Extraire le path de la section (sans contenu + index)
        if len(path) >= 2:
            section_path = tuple(path[:-2])  # Tuple pour comparaison
            content_idx = path[-1] if len(path) > 0 else -1
        else:
            section_path = ()
            content_idx = -1

        # Si meme section ET index consecutif, fusionner
        if current_group and current_group["section_path"] == section_path:
            # Verifier si index consecutif
            expected_idx = current_group["last_idx"] + 1
            if content_idx == expected_idx:
                # Fusionner
                current_group["textes"].append(ref["texte"])
                current_group["last_idx"] = content_idx
                continue

        # Sauvegarder le groupe precedent si existe
        if current_group:
            # Creer la ref fusionnee
            merged_ref = {
                "section": current_group["section"],
                "type": current_group["type"],
                "texte": "\n".join(current_group["textes"]),
                "path": current_group["first_path"]
            }
            if "risque" in current_group:
                merged_ref["risque"] = current_group["risque"]
            merged.append(merged_ref)

        # Demarrer nouveau groupe
        current_group = {
            "section": section,
            "section_path": section_path,
            "type": ref["type"],
            "textes": [ref["texte"]],
            "first_path": path,
            "last_idx": content_idx
        }
        if "risque" in ref:
            current_group["risque"] = ref["risque"]

    # Ajouter le dernier groupe
    if current_group:
        merged_ref = {
            "section": current_group["section"],
            "type": current_group["type"],
            "texte": "\n".join(current_group["textes"]),
            "path": current_group["first_path"]
        }
        if "risque" in current_group:
            merged_ref["risque"] = current_group["risque"]
        merged.append(merged_ref)

    return merged


def scan(node, communes_map, index_db, risque_actuel=None, dans_section_consignes=False, path=[]):
    """Parcourt recursif du JSON et indexation"""
    titre = node.get("titre", "")
    titre_lower = titre.lower()

    est_section_consignes = (
        ("consigne" in titre_lower and
         ("sécurité" in titre_lower or "individuelle" in titre_lower or "générale" in titre_lower or "commune" in titre_lower)) or
        "que faire" in titre_lower or
        "comportement" in titre_lower or
        "conduites à tenir" in titre_lower
    )

    if est_section_consignes:
        dans_section_consignes = True

    r = detect_risque(titre)
    if r:
        risque_actuel = r

    for idx, item in enumerate(node.get("contenu", [])):
        texte = item.get("valeur") if item["type"] == "texte" else item.get("valeur_brute", "")

        item_path = path + ["contenu", idx]

        if not texte:
            continue

        est_court_important = len(texte) >= 5 and len(texte) < 15 and is_important_short_text(texte)

        if len(texte) < 5 and not est_court_important:
            continue

        txt_lower = texte.lower()
        type_info = classify_content(texte, item["type"])

        # DETECTION CONSIGNES GLOBALES
        methode_1 = "avant" in txt_lower and "pendant" in txt_lower
        methode_2 = dans_section_consignes and len(texte) > 30
        methode_3 = (
            item["type"] == "tableau" and
            (("avant" in txt_lower and "après" in txt_lower) or
             ("| avant" in txt_lower) or
             ("pendant" in txt_lower and "après" in txt_lower))
        )
        mots_cles_consignes = ["s'informer", "évacuer", "se mettre à l'abri", "prévoir",
                                "alerter", "écouter la radio", "couper", "ne pas", "fermer",
                                "se confiner", "rejoindre"]
        nb_mots_cles = sum(1 for mot in mots_cles_consignes if mot in txt_lower)
        methode_4 = len(texte) > 100 and nb_mots_cles >= 2

        if methode_1 or methode_2 or methode_3 or methode_4:
            ref = {
                "section": titre,
                "type": type_info,
                "texte": texte,
                "path": item_path
            }
            if not any(r["texte"] == texte for r in index_db["_GLOBAL_"]["refs"]):
                index_db["_GLOBAL_"]["refs"].append(ref)

        # DONNEES LOCALES PAR COMMUNE
        if risque_actuel:
            texte_norm = remove_accents(texte)
            for ville_off, ville_norm in communes_map.items():
                if ville_norm in texte_norm:
                    if re.search(r"\b" + re.escape(ville_norm) + r"\b", texte_norm):
                        index_db[ville_off]["risques"].add(risque_actuel)

                        ref_local = {
                            "risque": risque_actuel,
                            "section": titre,
                            "type": type_info,
                            "texte": texte,
                            "path": item_path
                        }
                        if not any(r["texte"] == texte for r in index_db[ville_off]["refs"]):
                            index_db[ville_off]["refs"].append(ref_local)

    for idx, sous in enumerate(node.get("sous_sections", [])):
        sous_path = path + ["sous_sections", idx]
        scan(sous, communes_map, index_db, risque_actuel, dans_section_consignes, sous_path)


def build_index(json_path, code_dept, index_path):
    """Cree l'index a partir du JSON structure"""

    print(f"  Chargement JSON : {os.path.basename(json_path)}")
    with open(json_path, "r", encoding="utf-8") as f:
        ddrm_data = json.load(f)
    print(f"  OK JSON charge")

    print(f"  Recuperation des communes du departement {code_dept}...")
    communes = get_communes(code_dept)
    if not communes:
        print(f"  ATTENTION: Pas de communes pour {code_dept}")
        return
    print(f"  OK {len(communes)} communes recuperees")

    print(f"  Initialisation de l'index...")
    index_db = {ville: {"risques": set(), "refs": []} for ville in communes.keys()}
    index_db["_GLOBAL_"] = {"risques": set(), "refs": []}

    print(f"  Scan du document...")
    scan(ddrm_data, communes, index_db, path=[])

    # REGROUPEMENT des references consecutives
    print(f"  Regroupement des references consecutives...")
    for ville in index_db:
        index_db[ville]["refs"] = merge_consecutive_refs(index_db[ville]["refs"])

    nb_villes_avec_donnees = len([v for v, d in index_db.items() if v != "_GLOBAL_" and d["risques"]])
    nb_consignes_globales = len(index_db["_GLOBAL_"]["refs"])

    print(f"  Resultat: {nb_villes_avec_donnees} communes avec donnees, {nb_consignes_globales} consignes globales")

    print(f"  Export de l'index...")
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

    print(f"  OK Index cree: {index_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 4:
        build_index(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python indexer.py <json_path> <code_dept> <index_output>")