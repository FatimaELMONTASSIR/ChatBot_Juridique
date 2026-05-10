"""Ingestion des PDF vers ChromaDB (+ métadonnées MongoDB / JSON optionnel)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from backend.db import mongo
from backend.ingestion.chunker import chunk_pdf

load_dotenv()

_COLLECTION_NAME = "lexmaroc_articles"
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _list_pdf_files(data_dir: Path) -> list[Path]:
    if not data_dir.is_dir():
        return []
    seen: dict[str, Path] = {}
    for p in data_dir.iterdir():
        if not p.is_file():
            continue
        if p.suffix.lower() != ".pdf":
            continue
        key = p.stem.lower()
        seen[key] = p
    return list(seen.values())


def main() -> None:
    root = _project_root()
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    persist = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    persist_path = Path(persist).resolve()
    persist_path.mkdir(parents=True, exist_ok=True)

    data_dir = root / "data"
    pdf_files = _list_pdf_files(data_dir)
    if not pdf_files:
        print(f"Aucun PDF trouve dans {data_dir}")
        return

    print(f"Chargement du modele d'embeddings {_MODEL_NAME}...")
    embedder = SentenceTransformer(_MODEL_NAME)

    client = chromadb.PersistentClient(path=str(persist_path))
    collection = client.get_or_create_collection(_COLLECTION_NAME)

    all_rows: list[dict] = []
    for pdf_path in sorted(pdf_files, key=lambda x: x.name.lower()):
        chunks = chunk_pdf(pdf_path)
        all_rows.extend(chunks)

    if not all_rows:
        print("Aucun extrait produit depuis les PDF.")
        return

    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    for row in tqdm(all_rows, desc="Indexation ChromaDB"):
        aid = row["article_id"]
        content = row.get("content") or ""
        if not content.strip():
            continue
        emb = embedder.encode(content, convert_to_numpy=True).tolist()
        ids.append(aid)
        embeddings.append(emb)
        documents.append(content)
        metadatas.append(
            {
                "code": str(row.get("code", "")),
                "article_number": str(row.get("article_number", "")),
                "source_file": str(row.get("source_file", "")),
            }
        )

    if not ids:
        print("Aucun document non vide a indexer.")
        return

    batch = 64
    for start in range(0, len(ids), batch):
        end = min(start + batch, len(ids))
        collection.upsert(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    try:
        mongo.save_articles(all_rows)
    except Exception:
        pass

    print(
        f"Termine : {len(pdf_files)} PDF(s) traites, "
        f"{len(ids)} article(s) indexes dans ChromaDB."
    )


if __name__ == "__main__":
    main()
