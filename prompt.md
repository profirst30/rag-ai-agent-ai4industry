Tu es un développeur Python expert. Tu dois créer un service API RAG (Retrieval-Augmented Generation) pour convertir des documents DDRM en DICRIM.

## CONTEXTE

Je dispose de :
1. Une API d'embedding Otoroshi : http://embedding-gemma.oto.tools:8080/api/embed
2. Une API de chat completion Otoroshi : http://demo-ai4industry.oto.tools:8080/v2/chat/completions
3. Un fichier JSON local "knowledge_base_20.json" contenant :
   - metadata.total_chunks : nombre total de chunks
   - metadata.dim : dimension des vecteurs d'embedding
   - documents : liste d'objets avec :
     * chunk_id (int)
     * text (str) : le contenu textuel
     * heading (str ou null) : titre de section
     * page_numbers (list[int]) : numéros de pages
     * char_count (int)
     * embedding (list[float]) : vecteur d'embedding pré-calculé

## OBJECTIF

Créer un service FastAPI qui :
1. Reçoit une question de l'utilisateur (+ optionnellement le nom de commune)
2. Génère l'embedding de la question via l'API d'embedding
3. Cherche les 5 chunks les plus similaires dans le JSON local (similarité cosinus)
4. Construit un contexte avec ces chunks
5. Envoie question + contexte à l'API de chat completion
6. Retourne la réponse + les sources utilisées

## FLUX DE DONNÉES

INPUT (POST /rag/query) :
{
  "question": "Quelles sont les consignes pour les inondations dans la ville le tallud?",
}

ÉTAPE 1 - Embedding de la question :
- Appeler POST http://embedding-gemma.oto.tools:8080/api/embed
- Body: {"input": "Quelles sont les consignes..."}
- Récupérer le vecteur d'embedding de la réponse

ÉTAPE 2 - Recherche vectorielle locale :
- Charger knowledge_base_20.json en mémoire au démarrage
- Pour chaque document, calculer similarité cosinus entre :
  * embedding de la question
  * document["embedding"]
- Trier par similarité décroissante
- Garder les top_k (défaut 5)
- Filtrer ceux avec similarité < 0.3

ÉTAPE 3 - Construction du contexte :
- Pour chaque chunk récupéré, formater :
  "[Source: Page {page_numbers}, {heading}]
  {text}
  
  ---"
- Concaténer tous les chunks

ÉTAPE 4 - Génération de réponse :
- Appeler POST http://demo-ai4industry.oto.tools:8080/v2/chat/completions
- Body:
{
  "messages": [
    {
      "role": "user",
      "content": "EXTRAITS DE DDRM:\n{contexte}\n\n---\n\nQUESTION: {question}"
    }
  ],
}

OUTPUT (réponse JSON) :
{
  "answer": "# DICRIM Le Tallud - Risque Inondation\n\n## Avant...",
  "sources": [
    {
      "chunk_id": 123,
      "page_numbers": [45, 46],
      "heading": "Risque Inondation",
      "similarity": 0.892,
      "text_preview": "S'informer des risques..."  // 200 premiers chars
    }
  ],
  "metadata": {
    "commune": "Le Tallud",
    "chunks_retrieved": 5,
    "total_chunks_in_kb": 457
  }
}

## CONTRAINTES TECHNIQUES

1. Framework : FastAPI + Uvicorn
2. Dépendances : fastapi, uvicorn, requests, numpy, pydantic
3. Port : 8000
4. Endpoints requis :
   - POST /rag/query : endpoint principal

5. Fonction de similarité cosinus :
   cosine_similarity(vec1, vec2) = dot(vec1, vec2) / (norm(vec1) * norm(vec2))
   Utiliser numpy pour le calcul

6. Gestion d'erreurs :
   - Si API embedding inaccessible : HTTP 503 "Embedding service unavailable"
   - Si API chat inaccessible : HTTP 503 "Chat service unavailable"
   - Si aucun chunk pertinent trouvé : HTTP 404 "No relevant content found in DDRM"
   - Si question vide : HTTP 400 "Question cannot be empty"

7. Logging :
   - Logger chaque appel d'API externe
   - Logger les temps de réponse
   - Logger les erreurs avec traceback

8. Performance :
   - Charger knowledge_base_20.json UNE SEULE FOIS au démarrage (global variable)
   - Ne pas recharger à chaque requête
   - Timeouts : 30s pour embedding, 60s pour chat

## STRUCTURE DE FICHIERS ATTENDUE

rag_service/
├── main.py                     # FastAPI app + endpoints
├── embeddings.py               # Fonction embed_text()
├── retrieval.py                # Fonction retrieve_chunks()
├── generation.py               # Fonction generate_answer()
├── knowledge_base_20.json      # À placer ici
├── requirements.txt
└── README.md

## EXEMPLE D'UTILISATION

```bash
# Lancer le service
python main.py

# Tester
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quelles consignes pour inondation dans le tallud?"
  }'
