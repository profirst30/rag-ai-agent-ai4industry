"""
Moteur de requete
"""
import json
from difflib import get_close_matches


RISQUES = {
    "inondation": ["inondation", "crue", "submersion"],
    "mouvement de terrain": ["mouvement de terrain", "effondrement"],
    "séisme": ["séisme", "sismique"],
    "feu": ["feu", "incendie", "forêt"],
    "tempête": ["tempête", "vent"],
    "radon": ["radon"],
    "industriel": ["industriel", "seveso"],
    "nucléaire": ["nucléaire", "radioactif"],
    "barrage": ["barrage"],
    "transport": ["transport", "matières"]
}


def generer_prompt(index_path, risque, ville=None):
    """
    Fonction principale : genere un prompt depuis l'index

    Args:
        index_path: Chemin vers l'index JSON
        risque: Type de risque (str)
        ville: Nom de la ville optionnel (str)

    Returns:
        Le prompt genere (str)
    """
    with open(index_path, "r", encoding="utf-8") as f:
        db = json.load(f)

    villes = [k for k in db.keys() if k != "_GLOBAL_"]

    # Trouver la ville
    ville_trouvee = None
    if ville:
        if ville in villes:
            ville_trouvee = ville
        else:
            matches = get_close_matches(ville, villes, n=1, cutoff=0.6)
            if matches:
                ville_trouvee = matches[0]
            else:
                return f"Ville introuvable : {ville}"

    # Identifier le risque
    risque_key = None
    risque_lower = risque.lower()
    for key, syns in RISQUES.items():
        if key in risque_lower or any(s in risque_lower for s in syns):
            risque_key = key
            break
    if not risque_key:
        risque_key = risque_lower

    # Donnees locales
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

    # Consignes globales
    global_consignes = []
    if "_GLOBAL_" in db:
        for ref in db["_GLOBAL_"]["refs"]:
            full = (ref['section'] + " " + ref['texte']).lower()

            bon_risque = False
            if risque_key in RISQUES:
                for syn in RISQUES[risque_key]:
                    if syn in full:
                        bon_risque = True
                        break

            autre_risque = False
            for r, syns in RISQUES.items():
                if r != risque_key:
                    for syn in syns:
                        if syn in full and syn not in ["eau", "vent"]:
                            autre_risque = True
                            break

            if bon_risque or not autre_risque:
                global_consignes.append(f"--- {ref['section']} ---\n{ref['texte']}")

    # Assemblage
    if ville_trouvee:
        if not local:
            return f"Pas de donnees pour {ville_trouvee} / {risque}"

        prompt = f"""ROLE : Expert Securite Civile.
SUJET : {risque} a {ville_trouvee}.

[DONNEES LOCALES]
{chr(10).join(local)}

[CONSIGNES]
{chr(10).join(global_consignes)}

CONSIGNE : Redige le DICRIM."""
    else:
        if not global_consignes:
            return f"Pas de consignes pour {risque}"

        prompt = f"""ROLE : Expert Securite Civile.
SUJET : {risque}.

[CONSIGNES]
{chr(10).join(global_consignes)}

CONSIGNE : Explique les consignes."""

    return prompt


# Alias pour compatibilite
query = generer_prompt