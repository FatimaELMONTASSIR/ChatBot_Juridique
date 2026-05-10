"""Chaîne RAG : retrieval + LLM Ollama."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_ollama import OllamaLLM

try:
    from langchain.memory import ConversationBufferWindowMemory
except ImportError:
    from langchain_classic.memory import ConversationBufferWindowMemory

from backend.rag.prompt import SYSTEM_PROMPT
from backend.rag import retriever

load_dotenv()

_memory = ConversationBufferWindowMemory(k=5, return_messages=True)

_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
_model = os.getenv("LLM_MODEL", "llama3:8b-q4")
_num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT", "180"))
_NO_INFO_MSG = "Je ne trouve pas d'information sur ce sujet dans les textes juridiques disponibles."

try:
    _llm = OllamaLLM(
        base_url=_base_url.rstrip("/"),
        model=_model,
        num_ctx=_num_ctx,
        num_predict=_num_predict,
    )
except TypeError:
    _llm = OllamaLLM(
        base_url=_base_url.rstrip("/"),
        model=_model,
        model_kwargs={"num_ctx": _num_ctx, "num_predict": _num_predict},
    )


def _format_chat_history(chat_history: list | None) -> str:
    if not chat_history:
        return "(aucun message precedent)"
    lines: list[str] = []
    for item in chat_history:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            role, content = item[0], item[1]
        else:
            continue
        label = "Utilisateur" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    return "\n".join(lines) if lines else "(aucun message precedent)"


def ask(question: str, chat_history: list | None = None) -> dict:
    """
    Pose une question au RAG. Retourne answer et sources (liste de dicts).
    """
    top_k = int(os.getenv("TOP_K_RESULTS", "5"))
    articles = retriever.retrieve(question, top_k=top_k)
    if not articles:
        return {"answer": _NO_INFO_MSG, "sources": []}
    context = retriever.format_context(articles)
    hist = _format_chat_history(chat_history)
    prompt = SYSTEM_PROMPT.format(
        context=context,
        chat_history=hist,
        question=question,
    )
    try:
        answer = _llm.invoke(prompt)
        if isinstance(answer, str):
            text = answer
        else:
            text = str(answer)
        return {"answer": text, "sources": articles}
    except Exception:
        return {
            "answer": "Erreur lors de l'appel Ollama. Verifiez qu'Ollama est lance et que le modele configure dans .env est disponible.",
            "sources": articles,
        }
