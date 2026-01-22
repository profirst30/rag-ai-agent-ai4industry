"""
Module pour la recherche vectorielle dans la knowledge base.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    Calcule la similarité cosinus entre deux vecteurs.
    
    Args:
        vec1: Premier vecteur.
        vec2: Deuxième vecteur.
        
    Returns:
        Score de similarité entre 0 et 1.
    """
    vec1 = np.array(vec1)
    vec2 = np.array(vec2)
    
    dot_product = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(dot_product / (norm1 * norm2))


def retrieve_chunks(
    query_embedding: List[float],
    knowledge_base: Dict[str, Any],
    top_k: int = 10,
    similarity_threshold: float = 0.5
) -> List[Dict[str, Any]]:
    """
    Recherche les chunks les plus similaires à la question.
    
    Args:
        query_embedding: Vecteur d'embedding de la question.
        knowledge_base: Base de connaissances chargée en mémoire.
        top_k: Nombre maximum de chunks à retourner.
        similarity_threshold: Seuil minimum de similarité.
        
    Returns:
        Liste des chunks les plus pertinents avec leur score de similarité.
    """
    logger.info(f"Recherche dans {len(knowledge_base['documents'])} documents")
    
    documents = knowledge_base["documents"]
    similarities = []
    
    for doc in documents:
        if "embedding" not in doc or doc["embedding"] is None:
            continue
            
        similarity = cosine_similarity(query_embedding, doc["embedding"])
        similarities.append({
            "chunk_id": doc["chunk_id"],
            "text": doc["text"],
            "headings": doc.get("headings") or doc.get("heading"),
            "page_numbers": doc.get("page_numbers", []),
            "char_count": doc.get("char_count", len(doc["text"])),
            "similarity": similarity
        })
    
    # Trier par similarité décroissante
    similarities.sort(key=lambda x: x["similarity"], reverse=True)
    
    # Filtrer par seuil et limiter à top_k
    filtered_chunks = [
        chunk for chunk in similarities 
        if chunk["similarity"] >= similarity_threshold
    ][:top_k]
    
    logger.info(f"Trouvé {len(filtered_chunks)} chunks avec similarité >= {similarity_threshold}")
    
    for i, chunk in enumerate(filtered_chunks):
        logger.debug(f"  #{i+1}: chunk_id={chunk['chunk_id']}, similarity={chunk['similarity']:.4f}")
    
    return filtered_chunks


def format_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formate les chunks récupérés en contexte pour le prompt.
    
    Args:
        chunks: Liste des chunks avec leurs métadonnées.
        
    Returns:
        Contexte formaté en string.
    """
    context_parts = []
    
    for chunk in chunks:
        page_str = ", ".join(map(str, chunk["page_numbers"])) if chunk["page_numbers"] else "N/A"
        heading = chunk["headings"] if chunk["headings"] else "Sans titre"
        
        context_part = f"""[Source: Page {page_str}, {heading}]
{chunk['text']}

---"""
        context_parts.append(context_part)
    
    return "\n\n".join(context_parts)
