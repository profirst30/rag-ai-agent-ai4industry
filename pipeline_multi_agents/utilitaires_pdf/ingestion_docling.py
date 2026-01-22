import os
import re
import json
import logging
from pathlib import Path
from typing import List, Dict
import ollama
from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker

os.environ["DOCLING_DISABLE_OCR"] = "1"
os.environ["DOCLING_DISABLE_TABLES"] = "1"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_pdf_local(
    pdf_path: str,
    embed_model_id: str = "embeddinggemma:latest",
    max_tokens: int = 512
) -> List[Dict]:
    
    logger.info(f"Conversion du PDF : {pdf_path}")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    logger.info(f"Chunking hiérarchique...")
    chunker = HierarchicalChunker(max_tokens=max_tokens)
    chunks_raw = list(chunker.chunk(dl_doc=doc))

    chunks_text = [chunk.text for chunk in chunks_raw]
    chunks_metadata = []
    for i, chunk in enumerate(chunks_raw):
        chunks_metadata.append({
            "chunk_id": i,
            "headings": getattr(chunk.meta, 'headings', []),
            "page_numbers": list(set(getattr(chunk.meta, 'page_numbers', []))),
        })

    logger.info(f"Génération des vecteurs avec Ollama ({embed_model_id})...")
    
    valid_documents = []
    
    for i, text in enumerate(chunks_text):
        try:
            response = ollama.embeddings(
                model=embed_model_id,
                prompt=text,
                options={
                    "num_ctx": 4096,
                    "temperature": 0
                }
            )
            
            valid_documents.append({
                **chunks_metadata[i],
                "text": text,
                "embedding": response['embedding']
            })

        except Exception as e:
            logger.error(f"Erreur sur le chunk {i} (longueur: {len(text)} car.) : {e}")
            continue

    logger.info(f"{len(valid_documents)} / {len(chunks_text)} documents traités avec succès.")
    return valid_documents

def save_results(documents: List[Dict], output_path: str):
    output = {
        "metadata": {
            "total_chunks": len(documents),
            "dim": len(documents[0]["embedding"]) if documents else 0
        },
        "documents": documents
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"Base de connaissances sauvegardée : {output_path}")

if __name__ == "__main__":
    BASE_DIR = Path(__file__).parent.parent
    pdf_dir = BASE_DIR / "pdf"
    
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        logger.error(f"Aucun PDF trouvé dans le dossier : {pdf_dir}")
        exit()

    selected_pdf = pdf_files[0]
    dept_match = re.search(r'(\d{2})', selected_pdf.name)
    DEPARTEMENT = dept_match.group(1) if dept_match else "Inconnu"
    
    logger.info(f"Démarrage Pipeline - Fichier: {selected_pdf.name} (Dept: {DEPARTEMENT})")

    try:
        docs = process_pdf_local(str(selected_pdf))
        json_dir = BASE_DIR / "json"
        json_dir.mkdir(exist_ok=True)
        
        output_name = f"knowledge_base_{DEPARTEMENT}.json"
        save_results(docs, json_dir / output_name)
        logger.info("TRAITEMENT TERMINÉ AVEC SUCCÈS")

    except Exception as e:
        logger.error(f"Erreur critique : {e}")
        import traceback
        traceback.print_exc()