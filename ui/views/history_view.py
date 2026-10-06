"""
History View for browsing, reloading, and exporting past chromatographic analyses.
"""

import streamlit as st
import pandas as pd
from core.storage import get_repository
from core.reporting.pdf_generator import generate_analysis_pdf


def render_history_view(on_load_sample):
    """
    Renders the past samples list with options to reload, download PDF, or delete.
    `on_load_sample(sample_analysis)` is called when user clicks to view a sample.
    """
    st.subheader("📚 Historial de Muestras Analizadas")
    st.markdown("Consulta y recarga resultados de análisis anteriores almacenados en Supabase / Base de datos.")

    repo = get_repository()
    samples = repo.list_samples()

    if not samples:
        st.info("No hay muestras guardadas en el historial todavía. Carga y analiza una muestra para registrarla.")
        return

    st.caption(f"Total de análisis registrados: **{len(samples)}**")

    # Display as an interactive cards/table list
    for s in samples:
        sid = s["sample_id"]
        sname = s.get("sample_name", "Sin nombre")
        scode = s.get("sample_code", "S/C")
        sdate = s.get("analysis_date", "")
        pcount = s.get("peak_count", 0)
        tot_area = s.get("total_area", 0.0)
        created = s.get("created_at", "")[:16].replace("T", " ")

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([3, 2, 2, 1.5, 1.2])

            with col1:
                st.markdown(f"**{sname}**")
                st.caption(f"ID: `{sid[:8]}...` • Código: `{scode}`")

            with col2:
                st.markdown(f"📅 **Fecha:** {sdate}")
                st.caption(f"Registro: {created}")

            with col3:
                st.markdown(f"📊 **{pcount} picos**")
                st.caption(f"Área: {tot_area:,.0f}")

            with col4:
                if st.button("📂 Cargar", key=f"load_{sid}", use_container_width=True):
                    with st.spinner("Recuperando análisis completo..."):
                        full_analysis = repo.get_sample_analysis(sid)
                        if full_analysis:
                            on_load_sample(full_analysis)
                            st.success(f"Muestra '{sname}' cargada en el visor.")
                            st.rerun()
                        else:
                            st.error("No se pudo cargar la muestra seleccionada.")

            with col5:
                with st.popover("🗑️", help="Eliminar muestra de Supabase e historial"):
                    st.markdown(f"**¿Eliminar '{sname}'?**")
                    st.caption("Esta acción eliminará el archivo Excel y todos los picos y registros de las tablas de Supabase.")
                    if st.button("Sí, eliminar", key=f"confirm_del_{sid}", type="primary", use_container_width=True):
                        with st.spinner("Eliminando datos y archivos de Supabase..."):
                            ok = repo.delete_sample(sid)
                            if ok:
                                curr = st.session_state.get("current_analysis")
                                if curr and curr.sample_id == sid:
                                    st.session_state["current_analysis"] = None
                                    st.session_state["chat_messages"] = []
                                st.success("Muestra y archivo eliminados de Supabase correctamente.")
                                st.rerun()
                            else:
                                st.error("No se pudo eliminar la muestra.")

            st.markdown("<hr style='margin: 0.4rem 0; border: none; border-top: 1px solid #E2E8F0;'>", unsafe_allow_html=True)
