"""Récupération sémantique hybride depuis ChromaDB (filtrage + reranking)."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
_embedder: SentenceTransformer | None = None

LEGAL_CODE_ALIASES = {
    "Code des Obligations et des Contrats": [
        "code des obligations et des contrats",
        "coc",
        "obligations",
        "contrats",
        "dahir des obligations et des contrats",
    ],
    "Code du Travail": [
        "code du travail",
        "travail",
        "emploi",
        "licenciement",
        "preavis",
        "salaire",
    ],
    "Code Pénal": [
        "code penal",
        "pénal",
        "penal",
        "infraction",
        "crime",
        "delit",
    ],
    "Code de Commerce": [
        "code de commerce",
        "commerce",
        "societe",
        "sarl",
        "faillite",
        "commercant",
    ],
    "Code de la Famille": [
        "code de la famille",
        "famille",
        "mariage",
        "divorce",
        "pension",
        "garde",
    ],
    "Code de Procédure Civile": [
        "code de procedure civile",
        "procédure civile",
        "procedure civile",
        "tribunal civil",
        "instance civile",
    ],
}

LEGAL_KEYWORDS = {
    "contrat",
    "obligation",
    "responsabilite",
    "responsabilité",
    "licenciement",
    "preavis",
    "préavis",
    "procedure",
    "procédure",
    "infraction",
    "peine",
    "mariage",
    "divorce",
    "travail",
    "societe",
    "société",
    "faillite",
    "bail",
    "locataire",
    "delit",
    "délit",
    "crime",
}
MIN_SEMANTIC_SCORE = 0.45
MIN_KEYWORD_RATIO = 0.10


def _normalize_text(text: str) -> str:
    clean = unicodedata.normalize("NFKD", text or "")
    clean = "".join(ch for ch in clean if not unicodedata.combining(ch))
    clean = clean.lower()
    return re.sub(r"\s+", " ", clean).strip()


def _detect_requested_code(query: str) -> str | None:
    q = _normalize_text(query)
    for code_name, aliases in LEGAL_CODE_ALIASES.items():
        for alias in aliases:
            if alias in q:
                return code_name
    return None


def _query_terms(query: str) -> set[str]:
    q = _normalize_text(query)
    terms: set[str] = set()
    for kw in LEGAL_KEYWORDS:
        if _normalize_text(kw) in q:
            terms.add(_normalize_text(kw))
    return terms


def _score_candidate(
    query_terms: set[str],
    requested_code: str | None,
    candidate_code: str,
    content: str,
    distance: float | None,
) -> float:
    semantic_score = 1.0 / (1.0 + (distance or 0.0))
    content_norm = _normalize_text(content)

    if query_terms:
        hits = sum(1 for t in query_terms if t in content_norm)
        keyword_score = hits / len(query_terms)
    else:
        keyword_score = 0.0

    if requested_code and candidate_code == requested_code:
        code_score = 1.0
    elif requested_code and candidate_code != requested_code:
        code_score = -1.0
    else:
        code_score = 0.0

    # Pondération hybride :
    # - similarité vectorielle
    # - bonus mots-clés métier
    # - bonus/malus fort sur le code demandé pour éviter le hors-sujet
    return (0.62 * semantic_score) + (0.23 * keyword_score) + (0.15 * code_score)


def _is_directly_relevant(
    query_terms: set[str],
    requested_code: str | None,
    candidate_code: str,
    content: str,
    distance: float | None,
) -> bool:
    semantic_score = 1.0 / (1.0 + (distance or 0.0))
    content_norm = _normalize_text(content)
    if requested_code and candidate_code == requested_code:
        return True
    if requested_code and candidate_code != requested_code:
        return False
    if query_terms:
        hits = sum(1 for t in query_terms if t in content_norm)
        ratio = hits / len(query_terms)
        return ratio >= MIN_KEYWORD_RATIO or semantic_score >= MIN_SEMANTIC_SCORE
    return semantic_score >= MIN_SEMANTIC_SCORE


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer(_MODEL_NAME)
    return _embedder


def _get_collection():
    persist = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    path = Path(persist)
    client = chromadb.PersistentClient(path=str(path.resolve()))
    return client.get_or_create_collection("lexmaroc_articles")


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """
    Retourne les articles les plus pertinents pour la requête.
    Chaque élément : code, article_number, content, source_file.
    """
    try:
        collection = _get_collection()
        if collection.count() == 0:
            return []
        emb = _get_embedder().encode(query, convert_to_numpy=True).tolist()
        requested_code = _detect_requested_code(query)
        query_terms = _query_terms(query)

        max_n = max(8, top_k * 4)
        max_n = min(max_n, max(1, collection.count()))

        # Recherche filtrée prioritaire si un code juridique a été détecté.
        filtered_rows: list[dict] = []
        if requested_code:
            filtered = collection.query(
                query_embeddings=[emb],
                n_results=max_n,
                where={"code": requested_code},
                include=["documents", "metadatas", "distances"],
            )
            f_metas = filtered.get("metadatas") or [[]]
            f_docs = filtered.get("documents") or [[]]
            f_dist = filtered.get("distances") or [[]]
            if f_metas and f_metas[0]:
                for i, meta in enumerate(f_metas[0]):
                    if not meta:
                        continue
                    filtered_rows.append(
                        {
                            "code": meta.get("code", ""),
                            "article_number": meta.get("article_number", ""),
                            "content": f_docs[0][i] if f_docs and f_docs[0] and i < len(f_docs[0]) else "",
                            "source_file": meta.get("source_file", ""),
                            "_distance": f_dist[0][i] if f_dist and f_dist[0] and i < len(f_dist[0]) else None,
                        }
                    )

        # Si on a déjà assez de résultats filtrés, on ne garde que ceux-là.
        if requested_code and len(filtered_rows) >= top_k:
            rows = filtered_rows
        else:
            # Fallback global (utile si le code détecté n'a pas assez de chunks).
            res = collection.query(
                query_embeddings=[emb],
                n_results=max_n,
                include=["documents", "metadatas", "distances"],
            )
            metas = res.get("metadatas") or [[]]
            docs = res.get("documents") or [[]]
            dists = res.get("distances") or [[]]
            if not metas or not metas[0]:
                return []
            rows = filtered_rows[:]
            for i, meta in enumerate(metas[0]):
                if not meta:
                    continue
                rows.append(
                    {
                        "code": meta.get("code", ""),
                        "article_number": meta.get("article_number", ""),
                        "content": docs[0][i] if docs and docs[0] and i < len(docs[0]) else "",
                        "source_file": meta.get("source_file", ""),
                        "_distance": dists[0][i] if dists and dists[0] and i < len(dists[0]) else None,
                    }
                )

        # Déduplication
        dedup: dict[str, dict] = {}
        for row in rows:
            key = f"{row.get('code','')}|{row.get('article_number','')}|{row.get('source_file','')}|{(row.get('content') or '')[:160]}"
            if key not in dedup:
                dedup[key] = row

        reranked: list[tuple[float, dict]] = []
        for row in dedup.values():
            if not _is_directly_relevant(
                query_terms=query_terms,
                requested_code=requested_code,
                candidate_code=row.get("code", ""),
                content=row.get("content", ""),
                distance=row.get("_distance"),
            ):
                continue
            score = _score_candidate(
                query_terms=query_terms,
                requested_code=requested_code,
                candidate_code=row.get("code", ""),
                content=row.get("content", ""),
                distance=row.get("_distance"),
            )
            reranked.append((score, row))

        reranked.sort(key=lambda x: x[0], reverse=True)
        if not reranked:
            return []
        out: list[dict] = []
        for _, row in reranked[:top_k]:
            out.append(
                {
                    "code": row.get("code", ""),
                    "article_number": row.get("article_number", ""),
                    "content": row.get("content", ""),
                    "source_file": row.get("source_file", ""),
                }
            )
        return out
    except Exception:
        return []


def format_context(articles: list[dict]) -> str:
    """Formate les articles pour le prompt système."""
    if not articles:
        return "(Aucun article pertinent trouvé dans la base indexée. La base peut être vide — indexez les PDF depuis l'interface.)"
    max_chars = int(os.getenv("MAX_CONTEXT_CHARS_PER_ARTICLE", "900"))
    blocks = []
    for a in articles:
        code = a.get("code", "")
        num = a.get("article_number", "")
        src = a.get("source_file", "")
        body = (a.get("content") or "").strip()
        if len(body) > max_chars:
            body = body[:max_chars].rstrip() + " ..."
        blocks.append(
            f"[{code}] Article {num} (source: {src})\n{body}"
        )
    return "\n\n---\n\n".join(blocks)
