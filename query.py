"""
Moteur de requête
"""
import json
from difflib import get_close_matches


# Mapping risques/synonymes
RISQUES = {
    "inondation": ["inondation", "crue", "submersion", "débordement"],
    "mouvement de terrain": ["mouvement de terrain", "effondrement", "argile", "cavités"],
    "séisme": ["séisme", "sismique", "tremblement"],
    "feu": ["feu", "incendie", "forêt", "flammes"],
    "tempête": ["tempête", "vent", "cyclone"],
    "radon": ["radon"],
    "industriel": ["industriel", "seveso", "usine"],
    "nucléaire": ["nucléaire", "radioactif", "centrale"],
    "barrage": ["barrage", "digue"],
    "transport": ["transport", "matières dangereuses"]
}


def query(index_path, risque, ville=None):
    """Génère un prompt"""

    # Chargement index
    with open(index_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    villes = [k for k in db.keys() if k != "_GLOBAL_"]

    # Trouver la ville si fournie
    ville_trouvee = None
    if ville:
        if ville in villes:
            ville_trouvee = ville
        else:
            matches = get_close_matches(ville, villes, n=1, cutoff=0.6)
            if matches:
                ville_trouvee = matches[0]
            else:
                return f"❌ Ville introuvable : {ville}"

    # Identifier le risque
    risque_key = None
    risque_lower = risque.lower()
    for key, syns in RISQUES.items():
        if key in risque_lower or any(s in risque_lower for s in syns):
            risque_key = key
            break
    if not risque_key:
        risque_key = risque_lower

    # Données locales
    local = []
    if ville_trouvee and ville_trouvee in db:
        for ref in db[ville_trouvee]["refs"]:
            match = False
            if risque_key in RISQUES:
                for syn in RISQUES[risque_key]:
                    if syn in ref["risque"].lower():
                        match = True
                        break
            elif risque_lower in ref["risque"].lower():
                match = True

            if match:
                local.append(f"--- {ref['section']} ---\n{ref['texte']}")

    # Consignes globales filtrées
    global_consignes = []
    if "_GLOBAL_" in db:
        for ref in db["_GLOBAL_"]["refs"]:
            full = (ref['section'] + " " + ref['texte']).lower()

            # Contient le bon risque ?
            bon_risque = False
            if risque_key in RISQUES:
                for syn in RISQUES[risque_key]:
                    if syn in full:
                        bon_risque = True
                        break

            # Contient un autre risque ?
            autre_risque = False
            for r, syns in RISQUES.items():
                if r != risque_key:
                    for syn in syns:
                        if syn in full and syn not in ["eau", "vent"]:
                            autre_risque = True
                            break

            # Garder si pertinent ou neutre
            if bon_risque or not autre_risque:
                global_consignes.append(f"--- {ref['section']} ---\n{ref['texte']}")

    # Assemblage prompt
    if ville_trouvee:
        if not local:
            return f"❌ Pas de données pour {ville_trouvee} / {risque}"

        prompt = f"""RÔLE : Expert Sécurité Civile.
SUJET : {risque} à {ville_trouvee}.

[DONNÉES LOCALES]
{chr(10).join(local)}

[CONSIGNES]
{chr(10).join(global_consignes)}

CONSIGNE : Rédige le DICRIM."""
    else:
        if not global_consignes:
            return f"❌ Pas de consignes pour {risque}"

        prompt = f"""RÔLE : Expert Sécurité Civile.
SUJET : {risque}.

[CONSIGNES]
{chr(10).join(global_consignes)}

CONSIGNE : Explique les consignes."""

    return prompt