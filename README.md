# ⚖️ LexMaroc — Chatbot Juridique IA

LexMaroc est une application **Python 3.11** qui propose un assistant conversationnel spécialisé dans les **textes juridiques marocains** (version française). Le système repose sur une architecture **RAG** (Retrieval-Augmented Generation) : les réponses s’appuient sur des extraits indexés à partir de PDF officiels, puis complétés par un modèle de langage exécuté localement via **Ollama**.

Le projet vise un usage **pédagogique et informatif** : il illustre comment combiner **ChromaDB** (recherche vectorielle), **Sentence Transformers** (embeddings multilingues) et un **LLM** pour répondre de manière contextualisée, tout en rappelant les limites d’un outil automatisé face au conseil d’un professionnel du droit.

---

## Prérequis (Windows)

| Composant | Lien |
|-----------|------|
| **Python 3.11.6** | [python.org — Python 3.11.6](https://www.python.org/downloads/release/python-3116/) — cocher **« Add Python to PATH »** à l’installation. |
| **Ollama** | [ollama.com — Windows](https://ollama.com/download/windows) |
| **MongoDB Community** (optionnel, métadonnées) | [mongodb.com — Community Server](https://www.mongodb.com/try/download/community) |

Sans MongoDB, les métadonnées sont enregistrées automatiquement dans un fichier JSON sous le dossier de persistance Chroma (`articles_meta.json`).

---

## Installation (3 étapes)

```
Étape 1 : Double-clic sur setup.bat
Étape 2 : Les PDFs sont déjà dans .\data\
Étape 3 : Double-clic sur run.bat → http://localhost:8501
```

1. **`setup.bat`** crée l’environnement virtuel `.venv`, installe les dépendances, vérifie **Ollama**, télécharge le modèle **`llama3:8b-q4`** (si possible) et prépare les dossiers `data` et `chroma_db`.
2. Placez vos codes PDF dans **`.\data\`** (noms du type `code_travail.pdf`, `Code_famille.pdf`, etc. — la casse du nom de fichier est ignorée pour le typage du code).
3. **`run.bat`** active le venv et lance **Streamlit** sur le port **8501**.

Après le premier lancement, utilisez le bouton **« Indexer les documents »** ou **`ingest.bat`** pour construire l’index vectoriel.

---

## Ingestion des documents

- **Interface** : sidebar → **« Réindexer les documents »** (ou écran d’accueil si la base est vide).
- **Ligne de commande** : double-clic sur **`ingest.bat`** ou, avec le venv activé :  
  `python -m backend.ingestion.ingest`

---

## Architecture technique

| Couche | Technologie |
|--------|-------------|
| Interface | Streamlit |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2` (Sentence Transformers) |
| Base vectorielle | ChromaDB (`PersistentClient`, collection `lexmaroc_articles`) |
| LLM | Ollama (`langchain-ollama`, modèle configurable dans `.env`) |
| PDF | pdfplumber |
| Métadonnées optionnelles | PyMongo ou fichier JSON local |

---

## Peu de RAM ou machine modeste

Après installation d’Ollama, tirez un modèle plus léger puis adaptez **`.env`** :

- `ollama pull gemma2:2b` puis `LLM_MODEL=gemma2:2b`
- ou `ollama pull tinyllama` puis `LLM_MODEL=tinyllama`

Redémarrez **`run.bat`** après modification de **`.env`**.

---

## Évaluation (optionnel)

Avec le venv activé, depuis la racine du projet :

```bat
python -m evaluation.eval_runner
```

Le script lit **`evaluation/test_cases.json`** et vérifie heuristiquement la présence de mots-clés dans les réponses (nécessite Ollama et une base indexée pour des résultats pertinents).

---

## FAQ Windows

- **« Python introuvable »** : réinstallez Python en cochant **« Add Python to PATH »**, ou utilisez **`py -3.11`** après installation du launcher.
- **« Ollama déconnecté »** dans l’interface : lancez **Ollama** depuis le menu Démarrer et attendez que le service soit prêt.
- **Erreurs d’encodage** : les scripts et le code privilégient **UTF-8** (`chcp 65001` dans les `.bat`, `encoding="utf-8"` en Python).
- **Erreur liée à `torch` / DLL** : installez les **Visual C++ Redistributable** pour x64 :  
  [https://aka.ms/vs/17/release/vc_redist.x64.exe](https://aka.ms/vs/17/release/vc_redist.x64.exe)

---

## Avertissement

LexMaroc fournit des **informations à titre indicatif** et **ne remplace pas** une consultation avec un **avocat** ou un conseil juridique qualifié.
