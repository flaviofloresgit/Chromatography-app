"""
Chromatography GC-MS AI Application - PerkinElmer Clarus 690 & TurboMass
Streamlit Presentation Layer (Decoupled from Core Logic).
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load local environment variables from .env if present
load_dotenv()

from core.models import SampleAnalysis
from core.spectral.library_index import NistLibraryMatcher
from core.ai.gemini_client import GeminiAnalyzer
from core.storage import get_repository
from core.storage.supabase_repo import SupabaseSampleRepository
from ui.styles import get_custom_css
from ui.components import render_header
from ui.views import (
    render_upload_view,
    render_analysis_view,
    render_chat_view,
    render_history_view
)

# 1. PAGE CONFIGURATION
st.set_page_config(
    page_title="Chromatography AI • Clarus 690 GC-MS",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. INJECT CUSTOM CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

# 3. INITIALIZE SESSION STATE
if "current_analysis" not in st.session_state:
    st.session_state["current_analysis"] = None

if "gemini_api_key" not in st.session_state:
    st.session_state["gemini_api_key"] = os.getenv("GEMINI_API_KEY", "")

if "gemini_model" not in st.session_state:
    st.session_state["gemini_model"] = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

# 4. SIDEBAR (Configuration & Instrument Details)
with st.sidebar:
    st.image(
        "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3",
        caption="Laboratorio de Cromatografía GC-MS"
    )

    st.markdown("### ⚙️ Configuración del Sistema")

    # Gemini API Key input
    with st.expander("🔑 Credenciales Gemini AI", expanded=not bool(st.session_state["gemini_api_key"])):
        input_key = st.text_input(
            "Gemini API Key",
            value=st.session_state["gemini_api_key"],
            type="password",
            help="Obtén tu API Key gratuita en https://aistudio.google.com/"
        )
        if input_key != st.session_state["gemini_api_key"]:
            st.session_state["gemini_api_key"] = input_key
            os.environ["GEMINI_API_KEY"] = input_key

        model_choice = st.selectbox(
            "Modelo Gemini",
            ["gemini-3.5-flash-lite", "gemini-3.8-flash"],
            index=0
        )
        st.session_state["gemini_model"] = model_choice

    # Supabase Configuration
    with st.expander("☁️ Supabase Cloud Storage", expanded=False):
        sb_url = st.text_input("Supabase URL", value=os.getenv("SUPABASE_URL", ""))
        sb_key = st.text_input("Supabase Key", value=os.getenv("SUPABASE_KEY", ""), type="password")
        if sb_url:
            os.environ["SUPABASE_URL"] = sb_url
        if sb_key:
            os.environ["SUPABASE_KEY"] = sb_key
        st.caption("Si no se configuran, la app usa automáticamente almacenamiento local sin errores.")

    # Status Badges in Sidebar
    st.markdown("---")
    st.markdown("### 📡 Estado de Componentes")

    matcher = NistLibraryMatcher()
    is_nist_ready = matcher.is_indexed()
    nist_count = matcher.get_index_count()

    if is_nist_ready:
        st.success(f"📚 NIST Library: {nist_count:,} espectros listos.")
    else:
        st.warning("📚 NIST Library: Sin indexar.")
        if st.button("Indexar MSP Ahora"):
            with st.spinner("Indexando 240,000+ espectros NIST..."):
                count = matcher.build_index()
                st.success(f"Indexados {count:,} espectros.")
                st.rerun()

    analyzer = GeminiAnalyzer(api_key=st.session_state["gemini_api_key"])
    if analyzer.is_configured():
        st.success(f"🤖 Gemini AI: Conectado ({st.session_state['gemini_model']}).")
    else:
        st.info("🤖 Gemini AI: Modo simulación (Ingresa tu API Key).")

    repo = get_repository()
    if isinstance(repo, SupabaseSampleRepository) and repo.is_connected():
        st.success("☁️ Supabase: Conectado a la nube.")
    else:
        st.caption("💾 Almacenamiento: Modo Local (archivos seguros en disco).")

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 0.75rem; color: #64748B; line-height: 1.4;'>"
        "<b>Equipo:</b> PerkinElmer Clarus 690 GC<br>"
        "<b>Detector:</b> Clarus SQ 8 MS (EI 70 eV)<br>"
        "<b>Software:</b> TurboMass / AMDIS<br>"
        "<b>Fase Estacionaria:</b> Elite-5MS"
        "</div>",
        unsafe_allow_html=True
    )


# 5. MAIN APPLICATION HEADER
active_badges = [
    ("PerkinElmer Clarus 690 GC-MS", "info"),
    ("TurboMass EI 70 eV", "info"),
    (f"NIST: {nist_count:,} Espectros", "success" if is_nist_ready else "warning"),
    ("Gemini AI Active" if analyzer.is_configured() else "Gemini (Modo NIST)", "success" if analyzer.is_configured() else "warning")
]

render_header(
    title="Chromatography AI • Identificación Espectral GC-MS",
    subtitle="Plataforma de análisis cromatográfico cuantitativo con deducción química por Inteligencia Artificial y biblioteca NIST.",
    badges=active_badges
)

# 6. TAB NAVIGATION
tab_upload, tab_results, tab_chat, tab_history = st.tabs([
    "📥 Cargar y Analizar Muestra",
    "📊 Resultados & Reporte",
    "💬 Chat Asistente Químico IA",
    "📚 Historial de Muestras"
])


def on_analysis_completed(analysis: SampleAnalysis, raw_bytes: bytes, filename: str):
    """Callback when sample analysis completes."""
    st.session_state["current_analysis"] = analysis
    st.session_state["chat_messages"] = []  # Reset chat for new sample
    st.success("🎉 ¡Análisis completado! Consulta los resultados en la pestaña 'Resultados & Reporte'.")


def on_load_sample(analysis: SampleAnalysis):
    """Callback when reloading a sample from history."""
    st.session_state["current_analysis"] = analysis
    st.session_state["chat_messages"] = []


with tab_upload:
    render_upload_view(on_analysis_completed)

with tab_results:
    render_analysis_view(st.session_state["current_analysis"])

with tab_chat:
    render_chat_view(st.session_state["current_analysis"])

with tab_history:
    render_history_view(on_load_sample)
