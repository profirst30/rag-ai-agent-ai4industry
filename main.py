#!/usr/bin/env python3
"""
Script principal
"""
import os
import sys
from extract import extract_pdf
from indexer import build_index
from query import generer_prompt

PDFS_DIR = "data/pdfs"
JSON_DIR = "data/json"
INDEX_DIR = "data/index"

# === PARAMÈTRES HARDCODÉS ===
RISQUE_PAR_DEFAUT = "inondation"  # Modifiez selon vos besoins
VILLE_PAR_DEFAUT = None  # Laissez None pour mode général
CODE_DEPT_PAR_DEFAUT = "86"  # Code du département à traiter


def get_code_dept(filename):
    """Extrait le code departement"""
    import re
    match = re.search(r'(\d{2,3})', filename)
    return match.group(1) if match else None


def process_all():
    """Traite tous les PDFs"""
    print("\n" + "=" * 70)
    print("TRAITEMENT DES PDFs")
    print("=" * 70)

    for d in [PDFS_DIR, JSON_DIR, INDEX_DIR]:
        os.makedirs(d, exist_ok=True)

    pdfs = [f for f in os.listdir(PDFS_DIR) if f.endswith('.pdf')] if os.path.exists(PDFS_DIR) else []

    if not pdfs:
        print("Aucun PDF trouvé")
        return

    print(f"\n{len(pdfs)} PDF(s) trouvé(s)")

    for idx, pdf_file in enumerate(pdfs, 1):
        print(f"\n[{idx}/{len(pdfs)}] {pdf_file}")
        print("-" * 70)

        code = get_code_dept(pdf_file)
        if not code:
            print("  ERREUR: Code département introuvable")
            continue

        pdf_path = os.path.join(PDFS_DIR, pdf_file)
        json_path = os.path.join(JSON_DIR, f"{code}.json")
        index_path = os.path.join(INDEX_DIR, f"{code}.json")

        # Logique automatique
        if os.path.exists(index_path):
            print("  ✅ Index déjà prêt")
            continue

        if os.path.exists(json_path):
            print("  ✅ JSON existe déjà")
            try:
                build_index(json_path, code, index_path)
                print("  ✅ Index créé")
            except Exception as e:
                print(f"  ❌ ERREUR: {e}")
            continue

        # Tout faire
        try:
            print("  🔄 Extraction PDF...")
            extract_pdf(pdf_path, json_path)
            print("  🔄 Création index...")
            build_index(json_path, code, index_path)
            print("  ✅ Terminé")
        except Exception as e:
            print(f"  ❌ ERREUR: {e}")

    print(f"\n{'=' * 70}")
    print("TRAITEMENT TERMINÉ")
    print("=" * 70)


def generer_contexte_automatique():
    """
    Génère automatiquement le contexte RAG avec les paramètres hardcodés
    """
    print("\n" + "=" * 70)
    print("GÉNÉRATION DU CONTEXTE RAG")
    print("=" * 70)

    # Vérifier que l'index existe
    index_path = os.path.join(INDEX_DIR, f"{CODE_DEPT_PAR_DEFAUT}.json")

    if not os.path.exists(index_path):
        print(f"❌ ERREUR: Index introuvable pour le département {CODE_DEPT_PAR_DEFAUT}")
        print(f"   Chemin attendu: {index_path}")
        return None

    # Afficher les paramètres
    print(f"\n📍 Département: {CODE_DEPT_PAR_DEFAUT}")
    print(f"⚠️  Risque: {RISQUE_PAR_DEFAUT}")
    print(f"🏘️  Ville: {VILLE_PAR_DEFAUT if VILLE_PAR_DEFAUT else 'Mode général'}")
    print("-" * 70)

    # Générer le prompt
    try:
        result = generer_prompt(index_path, RISQUE_PAR_DEFAUT, VILLE_PAR_DEFAUT)
        print("\n✅ CONTEXTE GÉNÉRÉ:")
        print("=" * 70)
        print(result)
        print("=" * 70)
        return result
    except Exception as e:
        print(f"❌ ERREUR lors de la génération: {e}")
        return None


def main():
    """Point d'entrée"""
    # Étape 1: Traiter tous les PDFs
    process_all()

    # Étape 2: Générer le contexte automatiquement
    generer_contexte_automatique()


if __name__ == "__main__":
    main()