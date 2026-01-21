import json
import time
import os
import traceback

# Imports Docling
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import DocItemLabel

def build_hierarchy(doc):
    """
    Transforme le document plat de Docling en une structure JSON arborescente.
    """
    root = {
        "titre": "Racine du document",
        "niveau": 0,
        "contenu": [],
        "sous_sections": []
    }

    stack = [root]

    for item, _ in doc.iterate_items():

        # --- CAS 1 : TITRES ---
        if item.label in [DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE]:
            text_content = item.text.strip()
            if not text_content:
                continue

            level = getattr(item, 'level', 1)

            new_section = {
                "titre": text_content,
                "niveau": level,
                "contenu": [],
                "sous_sections": []
            }

            while len(stack) > 1 and stack[-1].get("niveau", 0) >= level:
                stack.pop()

            stack[-1]["sous_sections"].append(new_section)
            stack.append(new_section)

        # --- CAS 2 : TABLEAUX ---
        elif item.label == DocItemLabel.TABLE:
            # On utilise l'export Markdown pour garder la structure du tableau
            structured_rep = ""
            if hasattr(item, "export_to_markdown"):
                structured_rep = item.export_to_markdown()
            elif hasattr(item, "export_to_html"):
                structured_rep = item.export_to_html()

            if not structured_rep:
                continue

            table_data = {
                "type": "tableau",
                "valeur_brute": structured_rep,
                "contenu_structure": structured_rep
            }
            stack[-1]["contenu"].append(table_data)

        # --- CAS 3 : TEXTE ---
        elif item.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH, DocItemLabel.LIST_ITEM]:
            text_content = item.text.strip()
            if text_content:
                content_data = {
                    "type": "texte",
                    "valeur": text_content
                }
                stack[-1]["contenu"].append(content_data)

    return root

def process_ddrm(pdf_path, output_json_path):
    print(f"🚀 Démarrage de l'extraction pour : {pdf_path}")
    print("-" * 50)

    global_start = time.time()

    # 1. Configuration Docling
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # OCR OFF (Rapidité)
    pipeline_options.do_table_structure = True  # Structure Tableaux ON

    pipeline_options.accelerator_options = AcceleratorOptions(
        num_threads=4,
        device=AcceleratorDevice.AUTO
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    # 2. Conversion
    print("⏳ [1/3] Analyse du PDF (Docling)...")
    t0 = time.time()
    doc_result = converter.convert(pdf_path)
    t1 = time.time()
    print(f"   ⏱️  Terminé en : {t1 - t0:.2f} s")

    # 3. Structuration
    print("🏗️ [2/3] Construction de la hiérarchie JSON...")
    hierarchy = build_hierarchy(doc_result.document)
    t2 = time.time()

    # 4. Sauvegarde
    print(f"💾 [3/3] Sauvegarde vers {output_json_path}...")
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(hierarchy, f, ensure_ascii=False, indent=2)

    t3 = time.time()
    print("-" * 50)
    print(f"✅ SUCCÈS - Temps total : {t3 - global_start:.2f} s")
    print("-" * 50)

# --- POINT D'ENTRÉE ---
if __name__ == "__main__":
    # FICHIERS CIBLES (A modifier selon tes besoins)
    PDF_FILE = "DDRM_Vienne_2024.pdf"
    JSON_OUTPUT = "ddrm_structure_complet.json"

    if os.path.exists(PDF_FILE):
        try:
            process_ddrm(PDF_FILE, JSON_OUTPUT)
        except Exception:
            traceback.print_exc()
    else:
        print(f"❌ Erreur : Le fichier '{PDF_FILE}' est introuvable.")