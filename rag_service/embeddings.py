"""
Module pour la génération d'embeddings via l'API Otoroshi.
"""

import logging
import time
import requests
from typing import List

logger = logging.getLogger(__name__)

EMBEDDING_API_URL = "http://embedding-gemma.oto.tools:8080/api/embed"
EMBEDDING_TIMEOUT = 30  # secondes


def embed_text(text: str) -> List[float]:
    """
    Génère l'embedding d'un texte via l'API d'embedding Otoroshi.
    
    Args:
        text: Le texte à convertir en vecteur d'embedding.
        
    Returns:
        Liste de floats représentant le vecteur d'embedding.
        
    Raises:
        requests.exceptions.RequestException: Si l'API est inaccessible.
    """
    start_time = time.time()
    logger.info(f"Appel API embedding pour texte de {len(text)} caractères")
    
    try:
        response = requests.post(
            EMBEDDING_API_URL,
            json={"input": text},
            timeout=EMBEDDING_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        logger.info(f"Embedding généré en {elapsed:.2f}s")
        
        data = response.json()
        
        # Gérer différents formats de réponse possibles
        if isinstance(data, list):
            # Format: [embedding_vector]
            if isinstance(data[0], float):
                return data
            # Format: [[embedding_vector]]
            return data[0]
        elif isinstance(data, dict):
            # Format OpenAI-like: {"data": [{"embedding": [...]}]}
            if "data" in data and len(data["data"]) > 0:
                return data["data"][0]["embedding"]
            # Format simple: {"embedding": [...]}
            if "embedding" in data:
                return data["embedding"]
            # Format: {"embeddings": [[...]]}
            if "embeddings" in data:
                return data["embeddings"][0] if isinstance(data["embeddings"][0], list) else data["embeddings"]
        
        # Si on arrive ici, format non reconnu
        logger.error(f"Format de réponse embedding non reconnu: {type(data)}")
        raise ValueError(f"Format de réponse embedding non reconnu: {data}")
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout lors de l'appel à l'API embedding après {EMBEDDING_TIMEOUT}s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de l'appel à l'API embedding: {e}")
        raise
