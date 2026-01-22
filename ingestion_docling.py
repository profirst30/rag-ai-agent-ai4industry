import os
import re
import json
import logging
import numpy as np
import ollama


logger = logging.getLogger(__name__)

from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass 
# Désactivation temporaire pour la vitesse (à réactiver si besoin de précision)
os.environ["DOCLING_DISABLE_OCR"] = "1"
os.environ["DOCLING_DISABLE_TABLES"] = "1"

from sentence_transformers import SentenceTransformer
from docling.document_converter import DocumentConverter
from docling.chunking import HierarchicalChunker
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def embed_batch(model, batch):
    """Fonction helper pour l'embedding en parallèle"""
    return model.encode(batch, show_progress_bar=False)

def process_pdf_local(
    pdf_path: str,
    embed_model_id: str = "embeddinggemma:latest",
    max_tokens: int = 512
) -> List[Dict]:
    """Pipeline complet avec extraction Docling et embeddings via Ollama"""
    
    # 1. Conversion du PDF (Docling)
    logger.info(f"Conversion du PDF : {pdf_path}")
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc = result.document

    # 2. Chunking hiérarchique
    logger.info(f"Chunking hiérarchique...")
    chunker = HierarchicalChunker(max_tokens=max_tokens)
    chunks_raw = list(chunker.chunk(dl_doc=doc))

    # 3. Extraction texte et métadonnées
    chunks_text = [chunk.text for chunk in chunks_raw]
    chunks_metadata = []
    for i, chunk in enumerate(chunks_raw):
        chunks_metadata.append({
            "chunk_id": i,
            "headings": getattr(chunk.meta, 'headings', []),
            "page_numbers": list(set(getattr(chunk.meta, 'page_numbers', []))),
        })

    # 4. Création des embeddings via Ollama
    logger.info(f"Génération des vecteurs avec Ollama ({embed_model_id})...")
    
    valid_documents = []
    
    for i, text in enumerate(chunks_text):
        try:
            # Appel à l'API locale d'Ollama avec sécurité sur le contexte
            response = ollama.embeddings(
                model=embed_model_id,
                prompt=text,
                options={
                    "num_ctx": 4096, # On augmente la fenêtre de contexte (ex: 4k ou 8k)
                    "temperature": 0  # Recommandé pour les embeddings
                }
            )
            
            # 5. Assemblage immédiat du document valide
            valid_documents.append({
                **chunks_metadata[i],
                "text": text,
                "embedding": response['embedding']
            })

        except Exception as e:
            logger.error(f"❌ Erreur sur le chunk {i} (longueur: {len(text)} car.) : {e}")
            # On ignore ce chunk problématique et on continue
            continue

    logger.info(f"✅ {len(valid_documents)} / {len(chunks_text)} documents traités avec succès.")
    return valid_documents

def save_results(documents: List[Dict], output_path: str):
    """Sauvegarde final au format JSON pour les agents"""
    output = {
        "metadata": {
            "total_chunks": len(documents),
            "dim": len(documents[0]["embedding"]) if documents else 0
        },
        "documents": documents
    }
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"✓ Base de connaissances sauvegardée : {output_path}")

if __name__ == "__main__":
    # --- CONFIGURATION LOCALE AUTOMATIQUE ---
    BASE_DIR = Path(__file__).parent
    pdf_files = list(BASE_DIR.glob("*.pdf"))

    if not pdf_files:
        logger.error("Aucun PDF trouvé dans le dossier !")
        exit()

    selected_pdf = pdf_files[0]
    # Extraction du département (ex: 79 ou 86)
    dept_match = re.search(r'(\d{2})', selected_pdf.name)
    DEPARTEMENT = dept_match.group(1) if dept_match else "Inconnu"
    
    logger.info(f"Démarrage Pipeline - Fichier: {selected_pdf.name} (Dept: {DEPARTEMENT})")

    try:
        # Lancement du traitement
        docs = process_pdf_local(str(selected_pdf))
        
        # Sauvegarde
        output_name = f"knowledge_base_{DEPARTEMENT}.json"
        save_results(docs, BASE_DIR / output_name)
        
        logger.info("=== TRAITEMENT TERMINÉ AVEC SUCCÈS ===")

    except Exception as e:
        logger.error(f"Erreur critique : {e}")
        import traceback
        traceback.print_exc()