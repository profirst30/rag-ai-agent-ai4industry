"""
Extraction PDF vers JSON
"""
import json
import os
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc import DocItemLabel


def extract_pdf(pdf_path, json_path):
    """Extrait un PDF en JSON structure"""

    print(f"  Lecture du PDF : {os.path.basename(pdf_path)}")

    # Config Docling
    pipeline = PdfPipelineOptions()
    pipeline.do_ocr = False
    pipeline.do_table_structure = True
    pipeline.accelerator_options = AcceleratorOptions(num_threads=4, device=AcceleratorDevice.AUTO)

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline)}
    )

    # Conversion
    print(f"  Conversion en cours...")
    doc = converter.convert(pdf_path).document
    print(f"  PDF converti")

    # Structure arborescente
    print(f"  Construction de l'arborescence...")
    root = {"titre": "root", "niveau": 0, "contenu": [], "sous_sections": []}
    stack = [root]

    nb_titres = 0
    nb_tableaux = 0
    nb_textes = 0

    for item, _ in doc.iterate_items():

        # Titres
        if item.label in [DocItemLabel.SECTION_HEADER, DocItemLabel.TITLE]:
            text = item.text.strip()
            if not text:
                continue

            nb_titres += 1
            level = getattr(item, 'level', 1)
            section = {"titre": text, "niveau": level, "contenu": [], "sous_sections": []}

            while len(stack) > 1 and stack[-1].get("niveau", 0) >= level:
                stack.pop()

            stack[-1]["sous_sections"].append(section)
            stack.append(section)

        # Tableaux
        elif item.label == DocItemLabel.TABLE:
            table_text = ""
            if hasattr(item, "export_to_markdown"):
                table_text = item.export_to_markdown()
            elif hasattr(item, "export_to_html"):
                table_text = item.export_to_html()

            if table_text:
                nb_tableaux += 1
                stack[-1]["contenu"].append({
                    "type": "tableau",
                    "valeur_brute": table_text,
                    "contenu_structure": table_text
                })

        # Texte
        elif item.label in [DocItemLabel.TEXT, DocItemLabel.PARAGRAPH, DocItemLabel.LIST_ITEM]:
            text = item.text.strip()
            if text:
                nb_textes += 1
                stack[-1]["contenu"].append({"type": "texte", "valeur": text})

    print(f"  Extrait : {nb_titres} titres, {nb_tableaux} tableaux, {nb_textes} paragraphes")

    # Sauvegarde
    print(f"  Sauvegarde JSON...")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(root, f, ensure_ascii=False, indent=2)

    print(f"  OK : {os.path.basename(json_path)}")