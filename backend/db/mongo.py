"""Persistance optionnelle MongoDB avec repli JSON local."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

_MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
_JSON_PATH = Path(os.getenv("CHROMA_PERSIST_DIR", "chroma_db")) / "articles_meta.json"

_client = None
_collection = None
_use_json = False


def _init_mongo() -> bool:
    global _client, _collection, _use_json
    if _use_json and _collection is None:
        return False
    if _collection is not None:
        return True
    try:
        from pymongo import MongoClient

        _client = MongoClient(_MONGO_URI, serverSelectionTimeoutMS=3000)
        _client.admin.command("ping")
        db = _client.get_database("lexmaroc")
        _collection = db.get_collection("articles")
        _use_json = False
        return True
    except Exception:
        _client = None
        _collection = None
        _use_json = True
        return False


def _ensure_json_file() -> None:
    _JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _JSON_PATH.is_file():
        with open(_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False)


def save_articles(articles: list[dict[str, Any]]) -> None:
    """Enregistre ou met à jour les articles (MongoDB ou JSON)."""
    if not articles:
        return
    if _init_mongo() and _collection is not None:
        try:
            for doc in articles:
                aid = doc.get("article_id")
                if not aid:
                    continue
                _collection.replace_one(
                    {"article_id": aid},
                    doc,
                    upsert=True,
                )
        except Exception:
            pass
        return
    try:
        _ensure_json_file()
        with open(_JSON_PATH, encoding="utf-8") as f:
            store = json.load(f)
        for doc in articles:
            aid = doc.get("article_id")
            if aid:
                store[aid] = doc
        with open(_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(store, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_article(article_id: str) -> dict[str, Any] | None:
    """Retourne un article par identifiant."""
    if _init_mongo() and _collection is not None:
        try:
            doc = _collection.find_one({"article_id": article_id})
            if doc and "_id" in doc:
                del doc["_id"]
            return doc
        except Exception:
            pass
    try:
        _ensure_json_file()
        with open(_JSON_PATH, encoding="utf-8") as f:
            store = json.load(f)
        return store.get(article_id)
    except Exception:
        return None


def count_articles() -> int:
    """Nombre d'articles en stockage métadonnées."""
    if _init_mongo() and _collection is not None:
        try:
            return int(_collection.count_documents({}))
        except Exception:
            pass
    try:
        _ensure_json_file()
        with open(_JSON_PATH, encoding="utf-8") as f:
            store = json.load(f)
        return len(store)
    except Exception:
        return 0
