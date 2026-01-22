Documentation du Projet DICRIM
Vue d'ensemble
Système multi-agents pour génération automatique de fiches DICRIM (Documents d'Information Communal sur les Risques Majeurs) à partir de documents PDF officiels.

Architecture du projet
text
[racine]/
├── pdf/                    # Documents PDF sources
├── markdown/              # Fichiers Markdown convertis
├── json/                  # Base de connaissances JSON
├── utilitaires_pdf/       # Scripts de traitement PDF
└── src/                   # Code source principal
Prérequis
Python 3.8+

Ollama installé localement

Modèles Ollama : qwen3:1.7b, embeddinggemma:latest

Installation
Installer les dépendances Python :

bash
pip install -r requirements.txt
Installer Ollama :

bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Télécharger l'installateur pour Windows
Télécharger les modèles :

bash
ollama pull qwen3:1.7b
ollama pull embeddinggemma:latest
Utilisation
1. Préparation des données
bash
# Étape 1 : Conversion PDF vers Markdown
python utilitaires_pdf/pdf_to_md.py

# Étape 2 : Structuration en JSON
python utilitaires_pdf/md_to_json.py

# Étape 3 (optionnel) : Génération d'embeddings
python utilitaires_pdf/process_pdf_embedding.py
2. Lancement de l'application
bash
python src/main.py
Description des composants
Pipeline de traitement PDF
pdf_to_md.py : Conversion PDF → Markdown

md_to_json.py : Structuration Markdown → JSON

process_pdf_embedding.py : Génération d'embeddings vectoriels

Système multi-agents (src/)
main.py : Point d'entrée principal

core/orchestrator.py : Orchestrateur principal

agents/ : Agents spécialisés

coordinator.py : Extraction des paramètres

writer.py : Génération de fiches

validator.py : Validation des résultats

Types de risques supportés
Inondation

Séisme

Nucléaire

Transport de matières dangereuses (TMD)

Industriel

Mouvement de terrain

Radon

Feu de forêt

Format des requêtes
Exemples de requêtes acceptées :

"Quels sont les risques nucléaires à Civaux ?"

"Parle-moi des séismes"

"Y a-t-il des risques d'inondation à Bordeaux ?"

Format de sortie
Les fiches générées suivent cette structure :

Nature du risque

Situation locale

Consignes de sécurité

Variables d'environnement (optionnel)
text
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_API_KEY=ollama
OLLAMA_MODEL=qwen3:1.7b
OLLAMA_TIMEOUT=60
Tests
Le projet inclut une suite de tests intégrée :

bash
python src/main.py
Dépannage
Erreur "Aucun PDF trouvé"
Vérifier que les PDFs sont dans le dossier pdf/

S'assurer que les fichiers ont l'extension .pdf

Erreur de connexion Ollama
Vérifier que Ollama est en cours d'exécution

Tester avec : ollama list

Problèmes de mémoire
Réduire la taille des chunks dans les paramètres

Utiliser un modèle plus léger

Structure des données
Le fichier JSON généré contient :

Chunks de texte structurés

Hiérarchie des titres

Métadonnées de source