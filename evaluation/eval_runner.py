"""Évaluation simple sur test_cases.json (mots-clés dans la réponse)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def _load_cases() -> list[dict]:
    path = _ROOT / "evaluation" / "test_cases.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _check_keywords(answer: str, keywords: list[str]) -> tuple[int, int]:
    lower = answer.lower()
    hits = 0
    for kw in keywords:
        if kw.lower() in lower:
            hits += 1
    return hits, len(keywords)


def main() -> None:
    os.chdir(_ROOT)
    from backend.rag.chain import ask

    cases = _load_cases()
    print(f"Evaluation LexMaroc — {len(cases)} cas\n")
    passed = 0
    for tc in cases:
        tid = tc.get("id", "?")
        question = tc.get("question", "")
        keywords = tc.get("expected_keywords", [])
        expected_art = tc.get("expected_article", "")
        result = ask(question, chat_history=None)
        answer = result.get("answer", "") or ""
        h, n = _check_keywords(answer, keywords)
        art_ok = expected_art.lower() in answer.lower() if expected_art else True
        ok = h >= max(1, n // 2) and art_ok
        if ok:
            passed += 1
        status = "OK" if ok else "ECHEC"
        print(f"[{tid}] {status} — mots-cles {h}/{n}, article attendu: {expected_art}")
        if not ok:
            print(f"   Extrait: {answer[:220].replace(chr(10), ' ')}...")
        print()
    print(f"Resultat: {passed}/{len(cases)} cas reussis (heuristique mots-cles).")


if __name__ == "__main__":
    main()
