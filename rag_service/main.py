"""
Service API RAG pour la conversion de documents DDRM en DICRIM.
"""

import json
import logging
import sys
import time
import traceback
from pathlib import Path
from typing import Optional, List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from embeddings import embed_text
from retrieval import retrieve_chunks, format_context
from generation import generate_answer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("rag_service.log", encoding="utf-8")
    ]
)
logger = logging.getLogger(__name__)

# Initialisation FastAPI
app = FastAPI(
    title="RAG Service - DDRM to DICRIM",
    description="Service de conversion de documents DDRM en DICRIM utilisant RAG",
    version="1.0.0"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Variable globale pour la knowledge base
KNOWLEDGE_BASE: Optional[Dict[str, Any]] = None


# === Modèles Pydantic ===

class Message(BaseModel):
    """Message dans le format chat completion."""
    role: str = Field(..., description="Le rôle (user, assistant, system)")
    content: str = Field(..., description="Le contenu du message")


class ChatCompletionRequest(BaseModel):
    """Requête au format chat completion OpenAI."""
    messages: List[Message] = Field(..., description="Liste des messages de la conversation")
    model: Optional[str] = Field("rag-ddrm-dicrim", description="Modèle (ignoré, pour compatibilité)")
    temperature: Optional[float] = Field(0.7, description="Température (ignoré, pour compatibilité)")
    max_tokens: Optional[int] = Field(None, description="Max tokens (ignoré, pour compatibilité)")


class SourceInfo(BaseModel):
    """Information sur une source utilisée."""
    chunk_id: int
    page_numbers: List[int]
    heading: Optional[str]
    similarity: float
    text_preview: str


class ChatCompletionChoice(BaseModel):
    """Choice dans la réponse chat completion."""
    index: int
    message: Message
    finish_reason: str


class ChatCompletionUsage(BaseModel):
    """Usage dans la réponse chat completion."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """Réponse au format chat completion OpenAI."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str = "rag-ddrm-dicrim"
    choices: List[ChatCompletionChoice]
    usage: ChatCompletionUsage
    sources: Optional[List[SourceInfo]] = None  # Extension pour les sources RAG


# === Chargement de la Knowledge Base ===

def load_knowledge_base() -> Dict[str, Any]:
    """
    Charge la knowledge base depuis le fichier JSON.
    Appelé une seule fois au démarrage.
    """
    # Chercher le fichier dans plusieurs emplacements possibles
    possible_paths = [
        Path(__file__).parent / "knowledge_base_20.json",
        Path(__file__).parent.parent / "knowledge_base_20.json",
        Path("knowledge_base_20.json"),
    ]
    
    kb_path = None
    for path in possible_paths:
        if path.exists():
            kb_path = path
            break
    
    if kb_path is None:
        raise FileNotFoundError(
            f"knowledge_base_20.json non trouvé. Chemins testés: {possible_paths}"
        )
    
    logger.info(f"Chargement de la knowledge base depuis {kb_path}")
    start_time = time.time()
    
    with open(kb_path, "r", encoding="utf-8") as f:
        kb = json.load(f)
    
    elapsed = time.time() - start_time
    total_chunks = kb.get("metadata", {}).get("total_chunks", len(kb.get("documents", [])))
    logger.info(f"Knowledge base chargée en {elapsed:.2f}s - {total_chunks} chunks")
    
    return kb


@app.on_event("startup")
async def startup_event():
    """Événement de démarrage: charge la knowledge base."""
    global KNOWLEDGE_BASE
    try:
        KNOWLEDGE_BASE = load_knowledge_base()
        logger.info("Service RAG prêt!")
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la knowledge base: {e}")
        logger.error(traceback.format_exc())
        raise


# === Endpoints ===

@app.get("/")
async def root():
    """Endpoint racine pour vérifier que le service est actif."""
    return {
        "status": "ok",
        "service": "RAG Service - DDRM to DICRIM",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Endpoint de santé."""
    return {
        "status": "healthy",
        "knowledge_base_loaded": KNOWLEDGE_BASE is not None,
        "total_chunks": KNOWLEDGE_BASE["metadata"]["total_chunks"] if KNOWLEDGE_BASE else 0
    }


@app.post("/rag/query", response_model=ChatCompletionResponse)
async def rag_query(request: ChatCompletionRequest):
    """
    Endpoint principal RAG au format chat completion.
    
    Reçoit une requête au format OpenAI chat completion,
    recherche dans la knowledge base, et retourne une réponse
    au format chat completion avec les sources.
    """
    import uuid
    
    start_time = time.time()
    
    # Extraire la question du dernier message user
    question = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            question = msg.content
            break
    
    if not question or not question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    
    logger.info(f"Nouvelle requête RAG: '{question[:100]}...'")
    
    if KNOWLEDGE_BASE is None:
        raise HTTPException(status_code=503, detail="Knowledge base not loaded")
    
    # Étape 1: Générer l'embedding de la question
    try:
        logger.info("Étape 1: Génération de l'embedding de la question")
        query_embedding = embed_text(question)
        logger.info(f"Embedding généré: vecteur de dimension {len(query_embedding)}")
    except Exception as e:
        logger.error(f"Erreur embedding: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=503, detail="Embedding service unavailable")
    
    # Étape 2: Recherche des chunks pertinents
    try:
        logger.info("Étape 2: Recherche des chunks pertinents")
        chunks = retrieve_chunks(
            query_embedding=query_embedding,
            knowledge_base=KNOWLEDGE_BASE,
            top_k=5
        )
        logger.info(f"Chunks récupérés: {len(chunks)}")
    except Exception as e:
        logger.error(f"Erreur retrieval: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail="Error during retrieval")
    
    # Vérifier qu'on a trouvé des chunks pertinents
    if not chunks:
        raise HTTPException(status_code=404, detail="No relevant content found in DDRM")
    
    # Étape 3: Construction du contexte
    logger.info("Étape 3: Construction du contexte")
    context = format_context(chunks)
    
    # Étape 4: Génération de la réponse
    try:
        logger.info("Étape 4: Génération de la réponse")
        answer = generate_answer(
            question=question,
            context=context
        )
        logger.info(f"Réponse générée: {len(answer)} caractères")
    except Exception as e:
        logger.error(f"Erreur generation: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=503, detail="Chat service unavailable")
    
    # Construction des sources
    sources = []
    for chunk in chunks:
        # Gérer le cas où headings est une liste ou une string
        heading = chunk["headings"]
        if isinstance(heading, list):
            heading = " > ".join(heading) if heading else None
        
        sources.append(SourceInfo(
            chunk_id=chunk["chunk_id"],
            page_numbers=chunk["page_numbers"],
            heading=heading,
            similarity=round(chunk["similarity"], 4),
            text_preview=chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
        ))
    
    elapsed = time.time() - start_time
    logger.info(f"Requête RAG terminée en {elapsed:.2f}s")
    
    # Réponse au format chat completion
    return ChatCompletionResponse(
        id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
        created=int(time.time()),
        model="rag-ddrm-dicrim",
        choices=[
            ChatCompletionChoice(
                index=0,
                message=Message(role="assistant", content=answer),
                finish_reason="stop"
            )
        ],
        usage=ChatCompletionUsage(
            prompt_tokens=len(question.split()),
            completion_tokens=len(answer.split()),
            total_tokens=len(question.split()) + len(answer.split())
        ),
        sources=sources
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
