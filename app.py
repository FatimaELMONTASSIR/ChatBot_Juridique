"""Interface Streamlit LexMaroc — chatbot juridique RAG."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="LexMaroc — Chatbot Juridique IA",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;1,400&family=Source+Sans+Pro:wght@300;400;600&display=swap');

* { box-sizing: border-box; }

.stApp, [data-testid="stAppViewContainer"] {
    background-color: #f7f8fa !important;
    color: #1f2937 !important;
    font-family: 'Source Sans Pro', sans-serif;
}

/* Cacher header et footer Streamlit */
[data-testid="stHeader"] { display: none !important; }
footer { display: none !important; }
#MainMenu { display: none !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #ffffff !important;
    border-right: 1px solid #d1d5db !important;
}
[data-testid="stSidebar"] * { color: #1f2937 !important; }

/* Bulles de chat */
[data-testid="stChatMessage"] {
    border-radius: 12px !important;
    padding: 14px 18px !important;
    margin: 8px 0 !important;
    animation: fadeIn 0.4s ease-in;
}

/* Chat input */
[data-testid="stChatInputTextArea"] {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
}
[data-testid="stChatInputTextArea"]:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15) !important;
}

/* Boutons */
.stButton > button {
    background: #2563eb !important;
    color: #ffffff !important;
    border: 1px solid #2563eb !important;
    border-radius: 6px !important;
    font-family: 'Source Sans Pro', sans-serif !important;
    transition: all 0.2s ease !important;
}
.stButton > button:hover {
    background: #1d4ed8 !important;
    color: #ffffff !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background-color: #ffffff !important;
    border: 1px solid #d1d5db !important;
    border-radius: 8px !important;
}

/* Animation */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(6px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* Titres */
h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #1f2937 !important; }

/* Selectbox et inputs */
.stSelectbox > div, .stTextInput > div > input {
    background-color: #ffffff !important;
    color: #1f2937 !important;
    border-color: #d1d5db !important;
}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

st.markdown(
    """
<div style="text-align:center; padding: 2rem 0 1rem; border-bottom: 1px solid #d1d5db; margin-bottom: 1.5rem;">
    <h1 style="font-family:'Playfair Display',serif; color:#1f2937; font-size:2.8rem; margin:0; letter-spacing:0.05em;">
        ⚖️ LexMaroc
    </h1>
    <p style="color:#6b7280; font-style:italic; font-size:1.1rem; margin:0.3rem 0 0;">
        Assistant Juridique IA — Lois Marocaines
    </p>
</div>
""",
    unsafe_allow_html=True,
)


def check_ollama() -> bool:
    """Vérifie si Ollama est accessible."""
    try:
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        r = requests.get(f"{base_url}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def get_chroma_stats() -> dict:
    """Retourne les stats de la base vectorielle."""
    try:
        import chromadb

        persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
        client = chromadb.PersistentClient(path=str(Path(persist_dir).resolve()))
        collection = client.get_or_create_collection("lexmaroc_articles")
        count = collection.count()
        if count > 0:
            results = collection.get(include=["metadatas"], limit=min(count, 10000))
            metas = results.get("metadatas") or []
            codes = list(
                {m.get("code", "Inconnu") for m in metas if m}
            )
        else:
            codes = []
        return {"count": count, "codes": sorted(codes)}
    except Exception:
        return {"count": 0, "codes": []}


def run_ingestion():
    """Lance l'ingestion depuis l'interface."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "backend.ingestion.ingest"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(Path(__file__).resolve().parent),
        )
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


ollama_ok = check_ollama()
stats = get_chroma_stats()

with st.sidebar:
    st.markdown("### ⚙️ Statut du système")

    if ollama_ok:
        st.success("🟢 Ollama connecté")
    else:
        st.error("🔴 Ollama déconnecté")
        st.markdown(
            """
        **Pour démarrer Ollama :**
        Lancez *Ollama* depuis le menu Démarrer Windows.
        """
        )

    model = os.getenv("LLM_MODEL", "llama3:8b-q4")
    st.markdown(f"**Modèle :** `{model}`")

    st.divider()

    st.markdown(f"### 📚 Base juridique")
    st.markdown(f"**Articles indexés :** {stats['count']}")

    if stats["codes"]:
        st.markdown("**Codes disponibles :**")
        for code in stats["codes"]:
            st.markdown(f"  ✅ {code}")
    else:
        st.warning("Aucun document indexé")

    st.divider()

    if st.button("🗑️ Réinitialiser la conversation", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

    if st.button("🔄 Réindexer les documents", use_container_width=True):
        with st.spinner("Ingestion en cours..."):
            ok, output = run_ingestion()
        if ok:
            st.success("✅ Indexation terminée !")
        else:
            st.error(f"❌ Erreur : {output[:300]}")
        st.rerun()

    st.divider()
    st.markdown(
        """
    <small style="color:#6b7280;">
    LexMaroc v1.0 — Projet académique IADATA GRP5<br>
    Python 3.11.6 · LLaMA 3 8B · RAG · ChromaDB
    </small>
    """,
        unsafe_allow_html=True,
    )

if stats["count"] == 0:
    st.markdown(
        """
    <div style="background:#ffffff; border:1px solid #d1d5db; border-radius:12px; padding:2rem; text-align:center; margin:2rem 0;">
        <h2 style="color:#1f2937; font-family:'Playfair Display',serif;">📂 Base juridique vide</h2>
        <p style="color:#6b7280;">Vos PDFs sont dans <code>.\\data\\</code>. Lancez l'indexation pour démarrer.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button(
            "🔄 Indexer les documents juridiques maintenant", use_container_width=True
        ):
            with st.spinner(
                "⏳ Indexation en cours — cela peut prendre quelques minutes..."
            ):
                ok, output = run_ingestion()
            if ok:
                st.success("✅ Indexation réussie ! L'interface va se recharger.")
                st.rerun()
            else:
                st.error(f"❌ Erreur lors de l'indexation :\n{output[:500]}")
    st.stop()

if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    with st.chat_message(
        msg["role"], avatar="👤" if msg["role"] == "user" else "⚖️"
    ):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander(
                f"📚 Sources juridiques citées ({len(msg['sources'])} articles)"
            ):
                for src in msg["sources"]:
                    preview = (src.get("content") or "")[:200]
                    st.markdown(
                        f"**{src.get('code', '')}** — {src.get('article_number', '')}  \n_{preview}..._"
                    )

if prompt := st.chat_input("Posez votre question juridique en français..."):
    if not ollama_ok:
        st.error(
            "❌ Ollama n'est pas démarré. Lancez Ollama depuis le menu Démarrer Windows."
        )
        st.stop()

    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="👤"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("⚖️ LexMaroc consulte les textes de loi..."):
            try:
                from backend.rag.chain import ask

                result = ask(
                    question=prompt,
                    chat_history=[
                        (m["role"], m["content"])
                        for m in st.session_state["messages"][:-1]
                    ],
                )
                answer = result.get(
                    "answer", "Erreur lors de la génération de la réponse."
                )
                sources = result.get("sources", [])
            except Exception as e:
                answer = f"❌ Erreur : {str(e)}"
                sources = []

        st.markdown(answer)

        if sources:
            with st.expander(
                f"📚 Sources juridiques citées ({len(sources)} articles)"
            ):
                for src in sources:
                    preview = (src.get("content") or "")[:200]
                    st.markdown(
                        f"**{src.get('code', '')}** — {src.get('article_number', '')}  \n_{preview}..._"
                    )

        st.session_state["messages"].append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources,
            }
        )

st.markdown(
    """
<div style="position:fixed; bottom:0; left:0; right:0; background:#ffffff;
            border-top:1px solid #d1d5db; padding:0.5rem 1rem; text-align:center; z-index:999;">
    <small style="color:#6b7280;">
        ⚠️ LexMaroc est un outil informatif et <strong>ne remplace pas l'avis d'un avocat professionnel.</strong>
    </small>
</div>
""",
    unsafe_allow_html=True,
)
