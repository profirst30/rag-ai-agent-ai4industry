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


def get_code_dept(filename):
    """Extrait le code departement"""
    import re
    match = re.search(r'(\d{2,3})', filename)
    return match.group(1) if match else None


def process_all():
    """Traite tous les PDFs"""
    print("\n" + "=" * 70)
    print("TRAITEMENT")
    print("=" * 70)

    for d in [PDFS_DIR, JSON_DIR, INDEX_DIR]:
        os.makedirs(d, exist_ok=True)

    pdfs = [f for f in os.listdir(PDFS_DIR) if f.endswith('.pdf')] if os.path.exists(PDFS_DIR) else []
    if not pdfs:
        print("Aucun PDF")
        return

    print(f"\n{len(pdfs)} PDF(s)")

    for idx, pdf_file in enumerate(pdfs, 1):
        print(f"\n[{idx}/{len(pdfs)}] {pdf_file}")
        print("-" * 70)

        code = get_code_dept(pdf_file)
        if not code:
            print("  ERREUR: Code introuvable")
            continue

        pdf_path = os.path.join(PDFS_DIR, pdf_file)
        json_path = os.path.join(JSON_DIR, f"{code}.json")
        index_path = os.path.join(INDEX_DIR, f"{code}.json")

        # Logique automatique
        if os.path.exists(index_path):
            print("  OK Index pret")
            continue

        if os.path.exists(json_path):
            print("  OK JSON existe")
            try:
                build_index(json_path, code, index_path)
            except Exception as e:
                print(f"  ERREUR: {e}")
            continue

        # Tout faire
        try:
            extract_pdf(pdf_path, json_path)
            build_index(json_path, code, index_path)
        except Exception as e:
            print(f"  ERREUR: {e}")

    print(f"\n{'=' * 70}")
    print("TERMINE")
    print("=" * 70)


def mode_interactif():
    """Mode interactif"""
    print("\n" + "=" * 70)
    print("MODE INTERACTIF")
    print("=" * 70)

    if not os.path.exists(INDEX_DIR):
        print("Aucun index")
        return

    indexes = [f.replace('.json', '') for f in os.listdir(INDEX_DIR) if f.endswith('.json')]
    if not indexes:
        print("Aucun departement")
        return

    print(f"Departements : {', '.join(indexes)}")

    while True:
        print("\n" + "-" * 70)

        code = input("Code (q=quitter) : ").strip()
        if code.lower() == 'q':
            break

        index_path = os.path.join(INDEX_DIR, f"{code}.json")
        if not os.path.exists(index_path):
            print(f"Introuvable : {code}")
            continue

        print("\n1. GENERALE")
        print("2. LOCALE")
        choix = input("Choix : ").strip()

        ville = None
        risque = None

        if choix == '1':
            risque = input("Risque : ").strip()
        elif choix == '2':
            ville = input("Ville : ").strip()
            risque = input("Risque : ").strip()
        else:
            continue

        if not risque:
            continue

        print(f"\n{'=' * 70}")
        result = generer_prompt(index_path, risque, ville)
        print(result)
        print(f"{'=' * 70}\n")


def main():
    """Point d'entree"""
    process_all()

    if len(sys.argv) >= 3:
        code = sys.argv[1]
        index_path = os.path.join(INDEX_DIR, f"{code}.json")

        if not os.path.exists(index_path):
            print(f"Index introuvable : {code}")
            return

        if len(sys.argv) == 3:
            # Generale
            result = generer_prompt(index_path, sys.argv[2])
        else:
            # Locale
            result = generer_prompt(index_path, sys.argv[3], sys.argv[2])

        print(result)
    else:
        mode_interactif()


if __name__ == "__main__":
    main()