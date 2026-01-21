import json
from difflib import get_close_matches

# --- CONFIGURATION ---
INDEX_PATH = "index_global_test.json"

# LE DICTIONNAIRE INTELLIGENT (Sert à inclure les bons et exclure les rivaux)
MAPPING_RISQUES = {
    "inondation": ["inondation", "crue", "submersion", "vigicrues", "débordement"],
    "mouvement de terrain": ["mouvement de terrain", "effondrement", "argile", "cavités", "glissement"],
    "séisme": ["séisme", "sismique", "tremblement", "secousse"],
    "feu": ["feu", "incendie", "forêt", "flammes", "fumées"],
    "tempête": ["tempête", "vent", "cyclone", "rafales"],
    "radon": ["radon"],
    "industriel": ["industriel", "seveso", "usine", "toxique", "chimique"],
    "nucléaire": ["nucléaire", "radioactif", "centrale", "iode", "cnpe"],
    "barrage": ["barrage", "digue", "onde de submersion"],
    "transport": ["transport", "matières dangereuses", "tmd", "camion", "citerne"]
}


class DicrimEngineSmartV2:
    def __init__(self, db_path):
        try:
            with open(db_path, "r", encoding="utf-8") as f:
                self.db = json.load(f)
            self.villes_keys = [k for k in self.db.keys() if k != "_GLOBAL_"]
        except FileNotFoundError:
            self.db = {}

    def trouver_ville(self, user_input):
        if user_input in self.villes_keys: return user_input
        matches = get_close_matches(user_input, self.villes_keys, n=1, cutoff=0.6)
        return matches[0] if matches else None

    def construire_prompt(self, ville, topic_demande):
        contexte_local = []
        contexte_global = []

        # 1. Identifier la clé du risque (ex: "Inondation" -> "inondation")
        topic_key = None
        for key, synonyms in MAPPING_RISQUES.items():
            if key in topic_demande.lower() or topic_demande.lower() in synonyms:
                topic_key = key
                break
        if not topic_key: topic_key = topic_demande.lower()

        # 2. LOCAL : Récupération des données chiffrées
        if ville in self.db:
            for ref in self.db[ville]["references"]:
                # On vérifie si ça match via les synonymes
                is_local_match = False
                if topic_key in MAPPING_RISQUES:
                    for syn in MAPPING_RISQUES[topic_key]:
                        if syn in ref["risque"].lower():
                            is_local_match = True
                            break
                elif topic_demande.lower() in ref["risque"].lower():
                    is_local_match = True

                if is_local_match:
                    contexte_local.append(f"--- INFO LOCAL ({ref['section']}) ---\n{ref['extrait']}")

        # 3. GLOBAL : Le Filtrage Intelligent V2
        if "_GLOBAL_" in self.db:
            for ref in self.db["_GLOBAL_"]["references"]:
                # On analyse Titre + Contenu
                full_text = (ref['section_origine'] + " " + ref['extrait']).lower()

                # A. EST-CE LE BON RISQUE ?
                concerne_mon_risque = False
                if topic_key in MAPPING_RISQUES:
                    for syn in MAPPING_RISQUES[topic_key]:
                        if syn in full_text:
                            concerne_mon_risque = True
                            break

                # B. EST-CE UN RISQUE RIVAL ?
                parle_autre_risque = False
                for risque, synonymes in MAPPING_RISQUES.items():
                    if risque != topic_key:  # On ne regarde que les autres
                        for syn in synonymes:
                            # LISTE BLANCHE : Mots autorisés même s'ils sont dans d'autres risques
                            # "eau" (coupure d'eau), "vent" (aération), "fumer" (ne pas fumer)
                            if syn in full_text and syn not in ["eau", "vent", "fumer"]:
                                parle_autre_risque = True
                                break

                # C. DÉCISION
                # On garde si c'est le bon sujet OU si ce n'est pas un sujet concurrent (donc neutre)
                if concerne_mon_risque or not parle_autre_risque:
                    contexte_global.append(f"--- CONSIGNE ({ref['section_origine']}) ---\n{ref['extrait']}")

        if not contexte_local:
            return None, "ERROR_NO_DATA"

        str_local = "\n\n".join(contexte_local)
        str_global = "\n\n".join(contexte_global)

        prompt_content = f"""
RÔLE : Expert Sécurité Civile.
SUJET : {topic_demande} à {ville}.

[DONNÉES LOCALES]
{str_local}

[CONSIGNES FILTRÉES]
{str_global}

CONSIGNE : Rédige le DICRIM.
"""
        return prompt_content, "OK"


# --- EXECUTION DES 5 TESTS ---
if __name__ == "__main__":
    bot = DicrimEngineSmartV2(INDEX_PATH)

    CAS_DE_TEST = [
        ("Poitiers", "Inondation"),
        ("Civaux", "Nucléaire"),
        ("Châtellerault", "Tempête"),  # Doit trouver "Météo / Tempête"
        ("Montmorillon", "Mouvement de terrain"),
        ("Vivonne", "Feu de forêt")
    ]

    print(f"🔄 Lancement de {len(CAS_DE_TEST)} simulations...\n")

    for i, (ville, sujet) in enumerate(CAS_DE_TEST):
        print(f"👉 TEST #{i + 1} : {ville.upper()} / {sujet.upper()}")
        print("-" * 50)

        ville_reelle = bot.trouver_ville(ville)
        if ville_reelle:
            prompt, statut = bot.construire_prompt(ville_reelle, sujet)

            if statut == "OK":
                payload = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": prompt}]
                }
                # Affichage JSON pur
                print(json.dumps(payload, indent=2, ensure_ascii=False))
            else:
                print(f"⚠️  Données introuvables pour ce cas.")
        else:
            print("❌ Ville inconnue.")

        print("\n" + "=" * 80 + "\n")