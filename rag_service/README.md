# RAG Service - DDRM to DICRIM

Service API RAG (Retrieval-Augmented Generation) pour convertir des documents DDRM en DICRIM.

## 📋 Prérequis

- Python 3.9+
- Accès aux APIs Otoroshi :
  - API Embedding : `http://embedding-gemma.oto.tools:8080/api/embed`
  - API Chat : `http://demo-ai4industry.oto.tools:8080/v2/chat/completions`

## 🚀 Installation

1. **Créer un environnement virtuel** (si pas déjà fait) :
```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# ou
.venv\Scripts\activate  # Windows
```

2. **Installer les dépendances** :
```bash
pip install -r requirements.txt
```

3. **Placer le fichier knowledge_base_20.json** dans le dossier `rag_service/` ou le dossier parent.

## 🏃 Lancement

```bash
cd rag_service
python main.py
```

Le service sera accessible sur `http://localhost:8000`

## 📡 API Endpoints

### GET /
Vérification que le service est actif.

### GET /health
Endpoint de santé avec informations sur la knowledge base.

### POST /rag/query
Endpoint principal RAG.

**Request Body :**
```json
{
  "question": "Quelles sont les consignes pour les inondations dans la ville le tallud?",
  "commune": "Le Tallud",  // optionnel
  "top_k": 5  // optionnel, défaut: 5
}
```

**Response :**
```json
{
  "answer": "# DICRIM Le Tallud - Risque Inondation\n\n## Avant...",
  "sources": [
    {
      "chunk_id": 123,
      "page_numbers": [45, 46],
      "heading": "Risque Inondation",
      "similarity": 0.892,
      "text_preview": "S'informer des risques..."
    }
  ],
  "metadata": {
    "commune": "Le Tallud",
    "chunks_retrieved": 5,
    "total_chunks_in_kb": 457
  }
}
```

## 🧪 Test

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quelles consignes pour inondation dans le tallud?"
  }'
```

## 📁 Structure

```
rag_service/
├── main.py           # FastAPI app + endpoints
├── embeddings.py     # Génération d'embeddings
├── retrieval.py      # Recherche vectorielle
├── generation.py     # Génération de réponses
├── requirements.txt  # Dépendances Python
└── README.md         # Ce fichier
```

## ⚙️ Configuration

| Variable | Valeur | Description |
|----------|--------|-------------|
| Port | 8000 | Port du service |
| Embedding timeout | 30s | Timeout pour l'API d'embedding |
| Chat timeout | 60s | Timeout pour l'API de chat |
| Similarity threshold | 0.3 | Seuil minimum de similarité |

## 🔍 Logs

Les logs sont écrits dans :
- La console (stdout)
- Le fichier `rag_service.log`

## ❌ Codes d'erreur

| Code | Message | Description |
|------|---------|-------------|
| 400 | Question cannot be empty | La question est vide |
| 404 | No relevant content found in DDRM | Aucun chunk pertinent trouvé |
| 503 | Embedding service unavailable | API d'embedding inaccessible |
| 503 | Chat service unavailable | API de chat inaccessible |
