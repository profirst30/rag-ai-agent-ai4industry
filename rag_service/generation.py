"""
Module pour la génération de réponses via l'API de chat completion Otoroshi.
"""

import logging
import time
import requests

logger = logging.getLogger(__name__)

CHAT_API_URL = "http://demo-ai4industry.oto.tools:8080/v2/chat/completions"
CHAT_TIMEOUT = 60  # secondes


def generate_answer(question: str, context: str) -> str:
    """
    Génère une réponse en utilisant l'API de chat completion.
    
    Args:
        question: La question de l'utilisateur.
        context: Le contexte extrait des chunks pertinents.
        
    Returns:
        La réponse générée par le modèle.
        
    Raises:
        requests.exceptions.RequestException: Si l'API est inaccessible.
    """
    start_time = time.time()
    logger.info(f"Appel API chat completion pour question de {len(question)} caractères")
    logger.info(f"Contexte de {len(context)} caractères")
    
    # Construction du prompt
    user_content = f"""EXTRAITS DE DDRM:
{context}

---

QUESTION: {question}"""

    payload = {
        "messages": [
            {
                "role": "user",
                "content": user_content
            }
        ]
    }
    
    try:
        response = requests.post(
            CHAT_API_URL,
            json=payload,
            timeout=CHAT_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        elapsed = time.time() - start_time
        logger.info(f"Réponse générée en {elapsed:.2f}s")
        
        data = response.json()
        
        # Extraire la réponse selon le format OpenAI
        if "choices" in data and len(data["choices"]) > 0:
            choice = data["choices"][0]
            if "message" in choice:
                return choice["message"]["content"]
            elif "text" in choice:
                return choice["text"]
        
        # Format alternatif
        if "response" in data:
            return data["response"]
        if "content" in data:
            return data["content"]
        if "text" in data:
            return data["text"]
            
        logger.error(f"Format de réponse chat non reconnu: {data}")
        raise ValueError(f"Format de réponse chat non reconnu")
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout lors de l'appel à l'API chat après {CHAT_TIMEOUT}s")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Erreur lors de l'appel à l'API chat: {e}")
        raise
