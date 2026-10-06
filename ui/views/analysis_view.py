"""
Results Dashboard view displaying the interactive chromatogram, identification table,
peak mass spectra, and PDF export.
"""

import streamlit as st
import pandas as pd
from typing import Optional
from core.models import SampleAnalysis
from core.quantification.calculator import compute_sample_statistics
from core.reporting.pdf_generator import generate_analysis_pdf
from core.storage import get_repository
from ui.charts import plot_interactive_chromatogram, plot_mass_spectrum
from ui.components import render_metric_card, render_peak_details_card


def render_analysis_view(analysis: SampleAnalysis):
    """
    Renders the comprehensive chromatography analysis dashboard.
    """
    if not analysis:
        st.info("No hay ningún análisis cargado. Ve a la pestaña 'Cargar Muestra' para iniciar.")
        return

    m = analysis.metadata
    st.subheader(f"📊 Resultados de Análisis: {m.sample_name}")
    st.caption(f"Código: {m.sample_code or 'S/C'} • Columna: {m.column_type} • Fecha: {m.analysis_date}")

    # 1. METRICS ROW
    stats = compute_sample_statistics(analysis.peaks, analysis.identifications)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Área Total Integrada", f"{stats['total_area']:,.0f}", f"{stats['peak_count']} picos integrados")
    with c2:
        render_metric_card("Pureza / Identificado", f"{stats['identified_area_pct']}%", f"No asignado: {stats['unidentified_area_pct']}%")
    with c3:
        render_metric_card("Picos Mayores (>5%)", f"{stats['major_peaks_count']}", f"Medios: {stats['minor_peaks_count']} • Trazas: {stats['trace_peaks_count']}")
    with c4:
        render_metric_card("Rango de Retención", f"{stats['rt_range'][0]} - {stats['rt_range'][1]} min", f"Gas: {m.carrier_gas}")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. AI EXECUTIVE SUMMARY
    if analysis.summary_ai:
        with st.expander("🧠 Dictamen Analítico de Inteligencia Artificial (Gemini)", expanded=True):
            st.markdown(analysis.summary_ai)

    # 3. INTERACTIVE CHROMATOGRAM
    st.markdown("### 📈 Cromatograma de Iones Totales (TIC)")
    
    # Peak selector for highlighting
    peak_options = [p.peak_id for p in analysis.peaks]
    sel_col1, sel_col2 = st.columns([1, 3])
    with sel_col1:
        selected_pid = st.selectbox("Seleccionar pico para resaltar:", options=peak_options, index=0)

    fig_chrom = plot_interactive_chromatogram(
        chromatogram=analysis.chromatogram,
        peaks=analysis.peaks,
        identifications=analysis.identifications,
        selected_peak_id=selected_pid
    )
    st.plotly_chart(fig_chrom, use_container_width=True)

    # 4. EXPORT ACTIONS (PDF & Excel)
    act_col1, act_col2, act_col3 = st.columns([2, 1, 1])
    with act_col1:
        # Generate PDF Report
        try:
            pdf_bytes = generate_analysis_pdf(analysis)
            st.download_button(
                label="📄 Descargar Informe Oficial en PDF",
                data=pdf_bytes,
                file_name=f"Reporte_GCMS_{m.sample_name.replace(' ', '_')}_{m.analysis_date}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error generando PDF: {str(e)}")

    with act_col2:
        # Save to database
        if st.button("💾 Guardar en Historial", use_container_width=True):
            try:
                repo = get_repository()
                repo.save_sample_analysis(analysis)
                st.success("Guardado en historial / Supabase.")
            except Exception as e:
                st.error(f"Error al guardar: {str(e)}")

    with act_col3:
        # Export CSV
        df_export = _build_dataframe_from_analysis(analysis)
        csv_data = df_export.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Exportar Tabla CSV",
            data=csv_data,
            file_name=f"Cuantificacion_{m.sample_name.replace(' ', '_')}.csv",
            mime="text/csv",
            use_container_width=True
        )

    st.markdown("---")

    # 5. PEAK INSPECTOR & MASS SPECTRUM VIEWER
    st.markdown("### 🔬 Espectro de Masas y Razón de Identificación por Pico")
    
    target_peak = next((p for p in analysis.peaks if p.peak_id == selected_pid), None)
    target_ident = next((ident for ident in analysis.identifications if ident.peak_id == selected_pid), None)

    if target_peak:
        col_detail, col_spec = st.columns([1, 1])
        
        with col_detail:
            render_peak_details_card(target_peak, target_ident)
            
            # Show NIST Alternatives if available
            if target_ident and target_ident.alternative_candidates:
                with st.expander("📚 Candidatos alternativos considerados por NIST / IA"):
                    for alt in target_ident.alternative_candidates:
                        st.markdown(f"- **{alt.get('name', 'N/A')}** ({alt.get('formula', '')}): {alt.get('reason', '')}")

        with col_spec:
            if target_peak.spectrum:
                c_name = target_ident.compound_name if target_ident else ""
                fig_ms = plot_mass_spectrum(target_peak.spectrum, compound_name=c_name)
                st.plotly_chart(fig_ms, use_container_width=True)
            else:
                st.info("Este pico no posee datos de espectro de masas en la hoja 3.")

    st.markdown("---")

    # 6. COMPLETE QUANTIFICATION & IDENTIFICATION TABLE
    st.markdown("### 📋 Tabla de Cuantificación e Identificación Completa")
    
    df_table = _build_dataframe_from_analysis(analysis)
    
    # Search box for filtering
    search_query = st.text_input("🔍 Filtrar compuestos por nombre, fórmula o CAS:", "")
    if search_query:
        mask = (
            df_table["Compuesto"].str.contains(search_query, case=False, na=False) |
            df_table["Fórmula"].str.contains(search_query, case=False, na=False) |
            df_table["CAS"].str.contains(search_query, case=False, na=False)
        )
        df_table = df_table[mask]

    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Área %": st.column_config.ProgressColumn(
                "Área Relativa (%)",
                format="%.2f%%",
                min_value=0,
                max_value=100
            ),
            "Confianza": st.column_config.TextColumn("Confianza"),
            "Similitud NIST": st.column_config.TextColumn("NIST %"),
        }
    )


def _build_dataframe_from_analysis(analysis: SampleAnalysis) -> pd.DataFrame:
    """Creates a clean DataFrame from the analysis peaks and identifications."""
    id_map = {ident.peak_id: ident for ident in analysis.identifications}
    rows = []

    for p in sorted(analysis.peaks, key=lambda x: (x.rt if x.rt > 0 else x.peak_id)):
        ident = id_map.get(p.peak_id)
        c_name = ident.compound_name if ident else f"Pico #{p.peak_id}"
        formula = ident.formula if ident else "-"
        mw = ident.molecular_weight if ident and ident.molecular_weight > 0 else None
        cas = ident.cas_number if ident else "-"
        nist_s = f"{ident.nist_similarity:.1f}%" if ident and ident.nist_similarity > 0 else "-"
        conf = ident.confidence_level if ident else "N/A"
        family = ident.chemical_family if ident else "-"

        rows.append({
            "Pico ID": p.peak_id,
            "RT (min)": round(p.rt, 3),
            "Área": int(p.area),
            "Área %": round(p.relative_area_pct, 2),
            "Compuesto": c_name,
            "Fórmula": formula,
            "Peso Mol.": mw,
            "CAS": cas,
            "Familia": family,
            "Similitud NIST": nist_s,
            "Confianza": conf
        })

    return pd.DataFrame(rows)
