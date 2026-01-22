# Pipeline de traitement PDF avec Embeddings Locaux

Ce script permet d'extraire, découper et vectoriser automatiquement des documents PDF en utilisant **Docling** pour l'extraction et **Ollama** pour les embeddings locaux.

---

## 📋 Prérequis

### 1. Python 3.8+
Vérifiez votre version :
```bash
python --version
```

### 2. Ollama (serveur local de LLM)
- **Installation** : [https://ollama.ai/download](https://ollama.ai/download)
- **Vérification** :
```bash
ollama --version
```

### 3. Modèle d'embeddings
Téléchargez le modèle utilisé par défaut :
```bash
ollama pull embeddinggemma:latest
```

> **Alternatives** : `nomic-embed-text`, `mxbai-embed-large`, etc.

---

## 🔧 Installation des dépendances Python

### Créer un environnement virtuel (recommandé)
```bash
python -m venv venv

# Activation
# Windows :
venv\Scripts\activate
# macOS/Linux :
source venv/bin/activate
```

### Installer les packages
```bash
pip install ollama sentence-transformers docling numpy
```

**Détail des bibliothèques** :
- `ollama` : client Python pour Ollama
- `sentence-transformers` : gestion des modèles d'embeddings
- `docling` : extraction structurée de PDF
- `numpy` : calculs vectoriels

---

## 📂 Structure des fichiers

```
votre_projet/
│
├── script.py              # Le script principal
├── document_86.pdf        # Votre PDF (exemple)
└── knowledge_base_86.json # Résultat généré
```

---

## 🚀 Utilisation

### 1. Placer vos PDFs
Copiez vos fichiers PDF dans le **même dossier** que le script.

### 2. Lancer le traitement
```bash
python script.py
```

### 3. Résultat
Un fichier JSON sera créé automatiquement :
- **Format** : `knowledge_base_XX.json` (XX = numéro de département détecté)
- **Contenu** : chunks de texte + embeddings + métadonnées

---

## 📊 Format de sortie

```json
{
  "metadata": {
    "total_chunks": 142,
    "dim": 768
  },
  "documents": [
    {
      "chunk_id": 0,
      "headings": ["Introduction", "Contexte"],
      "page_numbers": [1, 2],
      "text": "Contenu du chunk...",
      "embedding": [0.123, -0.456, ...]
    }
  ]
}
```

---

## ⚙️ Configuration avancée

### Modifier le modèle d'embeddings
Dans le script, changez :
```python
embed_model_id: str = "nomic-embed-text"  # Au lieu de embeddinggemma
```

### Ajuster la taille des chunks
```python
max_tokens: int = 1024  # Au lieu de 512
```

### Activer l'OCR (pour PDFs scannés)
Supprimez ces lignes :
```python
os.environ["DOCLING_DISABLE_OCR"] = "1"
os.environ["DOCLING_DISABLE_TABLES"] = "1"
```
