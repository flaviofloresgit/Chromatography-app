"""
Interactive AI Chat View for conversing with Gemini about the chromatographic sample.
"""

import os
import streamlit as st
from typing import Optional
from core.models import SampleAnalysis
from core.ai.gemini_client import GeminiAnalyzer
from core.storage import get_repository


def render_chat_view(analysis: Optional[SampleAnalysis]):
    """
    Renders the conversational chemical assistant for the active sample.
    """
    st.subheader("💬 Asistente Químico de Inteligencia Artificial (Gemini)")
    
    if not analysis:
        st.warning("⚠️ No hay ninguna muestra activa cargada. Por favor carga una muestra en 'Cargar Muestra' para que la IA tenga el contexto completo de los compuestos y condiciones.")
        return

    m = analysis.metadata
    st.caption(f"Contexto activo: **{m.sample_name}** ({m.column_type}) • {len(analysis.peaks)} picos integrados")

    gemini_key = st.session_state.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    gemini_model = st.session_state.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    analyzer = GeminiAnalyzer(api_key=gemini_key, model_name=gemini_model)

    if not analyzer.is_configured():
        st.info("💡 Para chatear con el Asistente Químico sobre esta muestra, ingresa tu API Key de Gemini en la barra lateral.")

    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    # Quick prompt buttons
    st.markdown("##### ⚡ Preguntas sugeridas para esta muestra:")
    q_col1, q_col2 = st.columns(2)
    selected_quick_prompt = None
    with q_col1:
        if st.button("🔍 ¿Cuáles son las impurezas o contaminantes principales?", use_container_width=True):
            selected_quick_prompt = "¿Cuáles son las impurezas o compuestos minoritarios que podrían considerarse contaminantes en esta muestra?"
        if st.button("🧪 ¿Hay indicios de sangrado de columna (siloxanos)?", use_container_width=True):
            selected_quick_prompt = "¿Detectas algún pico en este análisis que corresponda a sangrado de columna (iones m/z 73, 207, 281, 355)?"
    with q_col2:
        if st.button("🌡️ ¿Cómo puedo optimizar la rampa de horno para estos picos?", use_container_width=True):
            selected_quick_prompt = "Considerando las temperaturas y tiempos de elución de los picos en esta columna, ¿qué ajustes sugieres al programa de horno para mejorar la resolución?"
        if st.button("📊 Explicar la fragmentación de los 3 picos más abundantes", use_container_width=True):
            selected_quick_prompt = "Explica detalladamente la fragmentación por impacto electrónico (EI 70 eV) de los 3 compuestos más abundantes por área en este análisis."

    # Build compounds overview text for the prompt
    compounds_overview = "\n".join([
        f"- Pico #{ident.peak_id} (RT={ident.rt:.2f} min, Área={ident.relative_area_pct:.1f}%): "
        f"{ident.compound_name} ({ident.formula}, PM={ident.molecular_weight:.1f}, CAS={ident.cas_number}) "
        f"[Iones clave: {ident.key_ions}]"
        for ident in analysis.identifications[:20]
    ])

    # Display chat messages
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state["chat_messages"]:
            role = msg["role"]
            avatar = "🧑‍🔬" if role == "user" else "🤖"
            with st.chat_message(role, avatar=avatar):
                st.markdown(msg["content"])

    # Chat Input
    user_input = st.chat_input("Escribe tu pregunta sobre la muestra, picos o condiciones...")
    prompt_to_send = selected_quick_prompt or user_input

    if prompt_to_send:
        # Add user message
        st.session_state["chat_messages"].append({"role": "user", "content": prompt_to_send})
        with chat_container:
            with st.chat_message("user", avatar="🧑‍🔬"):
                st.markdown(prompt_to_send)

        # Generate Assistant response
        with chat_container:
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Razonando sobre los espectros y datos cromatográficos..."):
                    history = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["chat_messages"][:-1]
                    ]
                    reply = analyzer.chat_response(
                        history=history,
                        user_message=prompt_to_send,
                        metadata=m,
                        summary_text=analysis.summary_ai,
                        compounds_overview=compounds_overview
                    )
                    st.markdown(reply)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": reply})

        # Save to repository
        try:
            repo = get_repository()
            repo.save_chat_message(analysis.sample_id, "user", prompt_to_send)
            repo.save_chat_message(analysis.sample_id, "assistant", reply)
        except Exception:
            pass

        if selected_quick_prompt:
            st.rerun()
