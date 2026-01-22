# Agent DDRM → DICRIM avec RAG

Système RAG (Retrieval-Augmented Generation) pour transformer des documents DDRM (Dossier Départemental des Risques Majeurs) en contenus DICRIM (Document d'Information Communal sur les Risques Majeurs) adaptés localement.

## Architecture

Ce projet utilise :
- **Otoroshi** : Gateway API pour gérer les LLM
- **Otoroshi LLM Extension** : Extension pour connecter et gérer les modèles de langage
- **Service RAG Python** : Orchestrateur pour la recherche vectorielle et la génération
- **Groq** : Provider LLM (modèles rapides et performants)

```
Utilisateur → Interface HTML → Service RAG Python
                                    ↓
                        ┌───────────┼───────────┐
                        ↓           ↓           ↓
                    Embedding   Recherche   Génération
                      (Otoroshi)  (Local)   (Otoroshi)
```

## Prérequis

- Java 17+
- Python 3.10+
- Un compte Groq (gratuit) : [https://groq.com/](https://groq.com/)

## Installation

### 1. Cloner le repository

```bash
git clone https://github.com/votre-repo/rag-ai-agent-ai4industry.git
cd rag-ai-agent-ai4industry
```

### 2. Télécharger Otoroshi et son extension LLM

Téléchargez les dernières versions des fichiers .jar :

- **Otoroshi** : [https://github.com/MAIF/otoroshi/releases](https://github.com/MAIF/otoroshi/releases)
- **Otoroshi LLM Extension** : [https://github.com/cloud-apim/otoroshi-llm-extension/releases](https://github.com/cloud-apim/otoroshi-llm-extension/releases)

Placez les deux fichiers .jar dans le répertoire racine du projet.

### 3. Lancer Otoroshi avec l'extension LLM

```bash
# Démarrer Otoroshi avec l'extension
java \
  -Dotoroshi.storage=file \
  -Dotoroshi.adminPassword=admin \
  -Dotoroshi.plugins.directory=./plugins \
  -cp "otoroshi.jar:otoroshi-llm-extension.jar" \
  otoroshi.Main
```

Otoroshi démarre sur :
- Interface admin : [http://otoroshi.oto.tools:8080](http://otoroshi.oto.tools:8080)
- Login : `admin@otoroshi.io` / Mot de passe : `admin`

Documentation complète : [https://cloud-apim.github.io/otoroshi-llm-extension/docs/install](https://cloud-apim.github.io/otoroshi-llm-extension/docs/install)

### 4. Configurer le provider LLM dans Otoroshi

1. Connectez-vous à l'interface Otoroshi
2. Allez dans **Extensions** → **LLM Providers**
3. Créez un nouveau provider Groq :
   - **Name** : `groq-llama`
   - **Type** : `groq`
   - **API Key** : Votre clé API Groq (récupérée sur [https://groq.com/](https://groq.com/))
   - **Model** : `llama-3.3-70b-versatile` (ou autre modèle disponible)

4. Importez la configuration depuis `filedb/state.ndjson` si disponible dans le projet

### 5. Installer et lancer le service RAG

```bash
cd rag_service

# Installer les dépendances Python
pip install -r requirements.txt

# Lancer le service
python main.py
```

Le service démarre sur [http://localhost:8000](http://localhost:8000)

### 6. Ouvrir l'interface de démonstration

Ouvrez le fichier `chat.html` dans votre navigateur :

```bash
# Linux/Mac
open chat.html

# Windows
start chat.html

# Ou directement via le service
open http://localhost:8000
```

## Utilisation

### Interface Web

1. Ouvrez `chat.html` dans votre navigateur
2. Posez une question sur les risques majeurs (exemples fournis dans l'interface)
3. Le système récupère automatiquement les extraits pertinents de la DDRM et génère une réponse adaptée

### API REST

**Endpoint principal** : `POST /rag/query`

```bash
curl -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quelles sont les consignes pour les inondations dans la ville Le Tallud?"
  }'
```

**Réponse** :

```json
{
  "answer": "# DICRIM Le Tallud - Risque Inondation\n\n## Avant l'événement\n...",
  "sources": [
    {
      "chunk_id": 123,
      "page_numbers": [45, 46],
      "heading": "Risque Inondation - Consignes",
      "similarity": 0.892,
      "text_preview": "S'informer des risques..."
    }
  ],
  "metadata": {
    "chunks_retrieved": 5,
    "total_chunks_in_kb": 457
  }
}
```

**Health check** : `GET /health`

```bash
curl http://localhost:8000/health
```

## Structure du Projet

```
.
├── filedb/                     # Configuration Otoroshi
│   └── state.ndjson           # État exporté d'Otoroshi
├── rag_service/               # Service RAG Python
│   ├── main.py               # API FastAPI
│   ├── embeddings.py         # Client API embedding
│   ├── retrieval.py          # Recherche vectorielle
│   ├── generation.py         # Génération de réponses
│   ├── knowledge_base_20.json # Base de connaissances DDRM
│   └── requirements.txt      # Dépendances Python
├── v3_ai4industry/           # Ressources du use case
├── chat.html                 # Interface de démo
├── otoroshi.jar              # À télécharger
└── otoroshi-llm-extension.jar # À télécharger
```

## Configuration Avancée

### Modifier les URLs des services

Dans `rag_service/main.py`, ajustez les variables :

```python
EMBEDDING_API_URL = "http://embedding-gemma.oto.tools:8080/api/embed"
CHAT_API_URL = "http://demo-ai4industry.oto.tools:8080/v2/chat/completions"
```

### Changer le nombre de chunks récupérés

Par défaut, le système récupère les 5 chunks les plus pertinents. Pour modifier :

```python
# Dans la requête
{
  "question": "Ma question",
  "top_k": 10  # Récupérer 10 chunks
}
```

### Ajuster le seuil de similarité

Dans `rag_service/retrieval.py`, modifier :

```python
MIN_SIMILARITY_THRESHOLD = 0.3  # Valeur entre 0 et 1
```

## Dépannage

### Otoroshi ne démarre pas

Vérifiez que vous utilisez Java 17+ :

```bash
java -version
```

### Le service RAG ne trouve pas la knowledge base

Assurez-vous que `knowledge_base_20.json` est dans le dossier `rag_service/`

### Erreur 503 "Service unavailable"

Vérifiez que :
1. Otoroshi est démarré
2. Les routes sont bien configurées dans Otoroshi
3. La clé API Groq est valide

### Les embeddings ne fonctionnent pas

Vérifiez que la route d'embedding est accessible :

```bash
curl -X POST http://embedding-gemma.oto.tools:8080/api/embed \
  -H "Content-Type: application/json" \
  -d '{"input": "test"}'
```

## Technologies Utilisées

- **Otoroshi** ([MAIF](https://github.com/MAIF/otoroshi)) : API Gateway en Scala
- **Otoroshi LLM Extension** ([Cloud APIM](https://github.com/cloud-apim/otoroshi-llm-extension)) : Extension pour LLM
- **FastAPI** : Framework web Python
- **Groq** : Provider LLM rapide (Llama 3.3)
- **NumPy** : Calculs vectoriels pour la similarité cosinus


***

**Documentation Otoroshi LLM Extension** : [https://cloud-apim.github.io/otoroshi-llm-extension/](https://cloud-apim.github.io/otoroshi-llm-extension/)