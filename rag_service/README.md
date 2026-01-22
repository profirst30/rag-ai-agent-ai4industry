# RAG Service - DDRM to DICRIM

Service API RAG (Retrieval-Augmented Generation) pour convertir des documents DDRM en DICRIM.
L'API expose un endpoint au format **OpenAI Chat Completion** pour une intégration facile avec les interfaces de chat.

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
Endpoint principal RAG au **format OpenAI Chat Completion**.

**Request Body :**
```json
{
  "messages": [
    {"role": "user", "content": "Quelles sont les consignes en cas d'inondation?"}
  ]
}
```

**Response (format Chat Completion) :**
```json
{
  "id": "chatcmpl-abc123def456",
  "object": "chat.completion",
  "created": 1737550517,
  "model": "rag-ddrm-dicrim",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "# DICRIM - Risque Inondation\n\n## Avant l'événement..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 8,
    "completion_tokens": 596,
    "total_tokens": 604
  },
  "sources": [
    {
      "chunk_id": 122,
      "page_numbers": [],
      "heading": "OÙ S'INFORMER SUR LE RISQUE INONDATION ?",
      "similarity": 0.6752,
      "text_preview": "https://www.georisques.gouv.fr/consulter-les-dossiers-thematiques/inondations..."
    }
  ]
}
```

## 🧪 Test

### Avec curl
```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Quelles sont les consignes en cas d inondation?"}
    ]
  }'
```

### Avec Python
```python
import requests

response = requests.post(
    "http://localhost:8000/rag/query",
    json={
        "messages": [
            {"role": "user", "content": "Quels sont les risques naturels?"}
        ]
    }
)
data = response.json()
print(data["choices"][0]["message"]["content"])
```

### Via le navigateur (Swagger UI)
Ouvrez `http://localhost:8000/docs` pour une interface interactive.

### Avec l'interface HTML
Ouvrez le fichier `chat.html` à la racine du projet dans un navigateur.

## 📁 Structure

```
rag_service/
├── main.py                  # FastAPI app + endpoints
├── embeddings.py            # Génération d'embeddings via API Otoroshi
├── retrieval.py             # Recherche vectorielle (similarité cosinus)
├── generation.py            # Génération de réponses via API Chat
├── knowledge_base_20.json   # Base de connaissances avec embeddings
├── requirements.txt         # Dépendances Python
└── README.md                # Ce fichier
```

## ⚙️ Configuration

| Variable | Valeur | Description |
|----------|--------|-------------|
| Port | 8000 | Port du service |
| Embedding timeout | 30s | Timeout pour l'API d'embedding |
| Chat timeout | 60s | Timeout pour l'API de chat |
| Similarity threshold | 0.5 | Seuil minimum de similarité |
| Top K | 5 | Nombre de chunks récupérés |

## � Flux de traitement

1. **Réception** de la question (format chat completion)
2. **Embedding** de la question via l'API Gemma
3. **Recherche vectorielle** des 5 chunks les plus similaires
4. **Construction du contexte** avec les chunks récupérés
5. **Génération** de la réponse via l'API Chat
6. **Retour** au format chat completion avec les sources

## �🔍 Logs

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

## 🔗 Intégration

L'API est compatible avec les interfaces de chat qui supportent le format OpenAI.
Le champ `sources` est une extension pour fournir les références des documents utilisés.
