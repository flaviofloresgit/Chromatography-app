"""
View for sample upload, chromatographic metadata entry, and triggering AI identification.
"""

import json
import os
import streamlit as st
from datetime import date
from core.models import SampleMetadata, SampleAnalysis
from core.parsers.excel_parser import parse_chromatography_excel
from core.spectral.library_index import NistLibraryMatcher
from core.quantification.calculator import calculate_relative_areas
from core.ai.gemini_client import GeminiAnalyzer
from core.storage import get_repository

DEFAULT_COLUMNS = [
    "Elite-5MS (30m x 0.25mm x 0.25µm - 5% Difenil 95% Dimetilpolisiloxano)",
    "Elite-1 / DB-1 (30m x 0.25mm x 0.25µm - 100% Dimetilpolisiloxano)",
    "Elite-624 / DB-624 (30m x 0.25mm x 1.4µm - VOCs / Solventes)",
    "Elite-WAX / HP-INNOWAX (30m x 0.25mm x 0.25µm - Polietilenglicol / Polar)",
    "DB-5MS (30m x 0.25mm x 0.25µm)",
    "HP-5MS (30m x 0.25mm x 0.25µm)",
    "Rtx-5MS (30m x 0.25mm x 0.25µm)"
]

def load_saved_columns() -> list:
    """Loads default and user-saved custom chromatographic columns."""
    filepath = os.path.join("local_storage", "columns.json")
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                saved = json.load(f)
                combined = list(DEFAULT_COLUMNS)
                for c in saved:
                    if c not in combined:
                        combined.append(c)
                return combined
        except Exception:
            pass
    return list(DEFAULT_COLUMNS)

def save_new_column(new_column: str):
    """Saves a new column specification to persistent storage."""
    if not new_column or not new_column.strip():
        return
    new_column = new_column.strip()
    os.makedirs("local_storage", exist_ok=True)
    filepath = os.path.join("local_storage", "columns.json")
    current = load_saved_columns()
    if new_column not in current:
        current.append(new_column)
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

def render_upload_view(on_analysis_completed):
    """
    Renders the sample metadata form, file uploader and analysis workflow.
    Calls `on_analysis_completed(sample_analysis, raw_bytes, filename)` when done.
    """
    st.subheader("📋 1. Registro de Muestra y Condiciones Cromatográficas")
    st.markdown(
        "Ingresa las condiciones operativas del cromatógrafo **PerkinElmer Clarus 690** y sube el archivo Excel "
        "con las 3 hojas del análisis (*Cromatograma, Picos y Espectro de masas*)."
    )

    with st.form("sample_metadata_form"):
        col1, col2 = st.columns(2)

        with col1:
            sample_name = st.text_input("Nombre / Descripción de la Muestra *", value="Muestra Test Hidrocarburos")
            sample_code = st.text_input("Código / Lote de Muestra", value="LOT-2026-001")
            analysis_date = st.date_input("Fecha de Análisis", value=date.today()).isoformat()
            operator = st.text_input("Operador / Analista", value="Especialista Instrumental")
            notes = st.text_area("Observaciones / Notas de Muestra", value="Muestra procesada en Clarus 690 GC-MS")

        with col2:
            available_columns = load_saved_columns()
            column_options = available_columns + ["➕ Otra / Nueva columna personalizada..."]
            selected_column = st.selectbox("Columna Cromatográfica", options=column_options)
            
            custom_column_input = st.text_input(
                "Especificar nueva columna (si seleccionaste '➕ Otra'):",
                placeholder="ej. Restek Rtx-Wax (30m x 0.32mm x 0.5µm)",
                help="Escribe la fase estacionaria y dimensiones. Si la guardas, aparecerá en el menú desplegable en todos tus futuros análisis."
            )
            save_custom_col = st.checkbox("💾 Guardar esta columna en la lista para futuros análisis", value=True)

            c_gas1, c_gas2 = st.columns(2)
            with c_gas1:
                carrier_gas = st.selectbox("Gas Portador", ["Helio (He)", "Hidrógeno (H2)", "Nitrógeno (N2)"])
                inlet_temp = st.text_input("Temp. Inyector", value="250 °C")
            with c_gas2:
                flow_rate = st.text_input("Flujo Columna", value="1.0 mL/min")
                split_ratio = st.text_input("Relación Split", value="20:1")

            oven_program = st.text_input(
                "Programa de Temperatura (Horno)",
                value="40 °C (1 min) -> 10 °C/min -> 280 °C (5 min)"
            )

        st.markdown("---")
        st.subheader("📂 2. Carga de Archivo Excel del Equipo (Clarus 690 / TurboMass)")

        uploaded_file = st.file_uploader(
            "Selecciona el archivo Excel (.xlsx / .xls) extraído del software del equipo",
            type=["xlsx", "xls"],
            help="Debe contener las 3 hojas: 'Chromatogram', 'Peaks' y 'Mass spectrum'."
        )

        st.markdown("---")
        st.subheader("⚙️ 3. Parámetros de Identificación e Inteligencia Artificial")
        
        c_opt1, c_opt2 = st.columns(2)
        with c_opt1:
            scope_option = st.radio(
                "Alcance del análisis Gemini AI:",
                [
                    "Picos Mayores y Medios (Área > 0.5% - Recomendado para rapidez y optimización de cuota)",
                    "Todos los picos detectados"
                ]
            )
        with c_opt2:
            use_search = st.checkbox(
                "Habilitar búsqueda en línea de Gemini (Google Search Grounding)",
                value=False,
                help="Permite a Gemini consultar fuentes oficiales en internet (NIST WebBook, PubChem) para complementar."
            )
            auto_save = st.checkbox("Guardar automáticamente en historial / Supabase al finalizar", value=True)

        submit_btn = st.form_submit_button("🚀 Iniciar Identificación y Análisis con IA", use_container_width=True)

    # Demo quick-loader button outside the form
    st.markdown("<div style='text-align: center; margin-top: 0.5rem;'><b>¿O prefieres probar sin subir un archivo?</b></div>", unsafe_allow_html=True)
    demo_btn = st.button("🧪 Cargar Muestra de Demostración ('Sample test.xlsx')", use_container_width=True)

    # Process Form or Demo
    target_bytes = None
    target_filename = ""
    effective_column = "Elite-5MS (30m x 0.25mm x 0.25µm - 5% Difenil 95% Dimetilpolisiloxano)"

    if submit_btn:
        if not uploaded_file:
            st.error("⚠️ Por favor sube un archivo Excel de cromatografía para analizar.")
            return
        target_bytes = uploaded_file.getvalue()
        target_filename = uploaded_file.name

        # Resolver nombre final de columna
        if custom_column_input and custom_column_input.strip():
            effective_column = custom_column_input.strip()
            if save_custom_col:
                save_new_column(effective_column)
        elif "➕ Otra" in selected_column:
            effective_column = "Columna Personalizada (No especificada)"
        else:
            effective_column = selected_column

    elif demo_btn:
        sample_path = "Sample test.xlsx"
        if os.path.exists(sample_path):
            with open(sample_path, "rb") as f:
                target_bytes = f.read()
            target_filename = "Sample test.xlsx"
            sample_name = "Muestra Demo Clarus 690 (Hidrocarburos)"
            effective_column = "Elite-5MS (30m x 0.25mm x 0.25µm - 5% Difenil 95% Dimetilpolisiloxano)"
        else:
            st.error("No se encontró el archivo de prueba local 'Sample test.xlsx'.")
            return

    if target_bytes:
        _execute_analysis_workflow(
            target_bytes=target_bytes,
            filename=target_filename,
            sample_name=sample_name,
            sample_code=sample_code,
            analysis_date=analysis_date,
            column_type=effective_column,
            carrier_gas=carrier_gas,
            flow_rate=flow_rate,
            inlet_temperature=inlet_temp,
            oven_program=oven_program,
            split_ratio=split_ratio,
            operator=operator,
            notes=notes,
            scope_option=scope_option if 'scope_option' in locals() else "Picos Mayores",
            use_search=use_search if 'use_search' in locals() else False,
            auto_save=auto_save if 'auto_save' in locals() else True,
            on_analysis_completed=on_analysis_completed
        )

    # Column catalog management tool
    with st.expander("⚙️ Administrar Catálogo de Columnas del Laboratorio"):
        st.markdown("Agrega columnas cromatográficas para que estén siempre disponibles en la lista desplegable:")
        m_c1, m_c2 = st.columns([3, 1])
        with m_c1:
            direct_new_col = st.text_input(
                "Nombre y especificaciones de la columna a registrar:",
                placeholder="ej. VF-WAXms (30m x 0.25mm x 0.25µm)",
                key="direct_column_reg"
            )
        with m_c2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Registrar Columna", use_container_width=True):
                if direct_new_col and direct_new_col.strip():
                    save_new_column(direct_new_col)
                    st.success(f"¡Columna '{direct_new_col.strip()}' guardada en la lista desplegable!")
                    st.rerun()
                else:
                    st.warning("Escribe el nombre de la columna primero.")

        st.caption("Columnas registradas actualmente:")
        for idx, c in enumerate(load_saved_columns(), start=1):
            st.markdown(f"- **{idx}.** `{c}`")


def _execute_analysis_workflow(
    target_bytes: bytes,
    filename: str,
    sample_name: str,
    sample_code: str,
    analysis_date: str,
    column_type: str,
    carrier_gas: str,
    flow_rate: str,
    inlet_temperature: str,
    oven_program: str,
    split_ratio: str,
    operator: str,
    notes: str,
    scope_option: str,
    use_search: bool,
    auto_save: bool,
    on_analysis_completed
):
    """Executes parsing, NIST spectral matching, and Gemini identification."""
    progress_bar = st.progress(0, text="Iniciando procesamiento cromatográfico...")

    metadata = SampleMetadata(
        sample_name=sample_name,
        sample_code=sample_code,
        analysis_date=analysis_date,
        column_type=column_type,
        carrier_gas=carrier_gas,
        flow_rate=flow_rate,
        inlet_temperature=inlet_temperature,
        oven_program=oven_program,
        split_ratio=split_ratio,
        operator=operator,
        notes=notes,
        original_file_name=filename
    )

    # 1. Parse Excel
    progress_bar.progress(15, text="Leyendo tablas de cromatograma, picos y espectros de masas...")
    try:
        chromatogram, peaks, total_area = parse_chromatography_excel(target_bytes)
        calculate_relative_areas(peaks)
    except Exception as e:
        progress_bar.empty()
        st.error(f"❌ Error al procesar el archivo Excel: {str(e)}")
        return

    st.success(f"✅ Excel procesado: {len(chromatogram):,} puntos de señal TIC y {len(peaks)} picos integrados.")

    # 2. Filter peaks if user selected major/medium only
    if "Picos Mayores" in scope_option:
        peaks_to_identify = [p for p in peaks if p.relative_area_pct >= 0.5]
        # Always include at least top 10 if few
        if len(peaks_to_identify) < 10 and len(peaks) > len(peaks_to_identify):
            sorted_by_area = sorted(peaks, key=lambda x: x.area, reverse=True)
            peaks_to_identify = sorted_by_area[:15]
    else:
        peaks_to_identify = peaks

    # 3. NIST Spectral Matching
    progress_bar.progress(35, text="Consultando biblioteca espectral NIST (Similitud Stein-Scott)...")
    matcher = NistLibraryMatcher()

    # If index not present, auto-build fast index
    if not matcher.is_indexed() and os.path.exists(matcher.msp_path):
        st.info("ℹ️ Indexando base de datos NIST (.MSP) para búsquedas de alta velocidad (un solo proceso inicial)...")
        matcher.build_index()

    candidates_by_peak = {}
    for p in peaks_to_identify:
        if p.spectrum:
            candidates_by_peak[p.peak_id] = matcher.search_candidates(p.spectrum, top_k=4)

    progress_bar.progress(55, text=f"Búsqueda NIST completada para {len(peaks_to_identify)} picos.")

    # 4. Gemini AI Compound Identification
    progress_bar.progress(65, text="Enviando espectros y condiciones a Gemini AI para deducción química...")
    gemini_key = st.session_state.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
    gemini_model = st.session_state.get("gemini_model", os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
    
    analyzer = GeminiAnalyzer(api_key=gemini_key, model_name=gemini_model)

    def ai_progress(curr, total, msg):
        pct = int(65 + (curr / total) * 25)
        progress_bar.progress(pct, text=msg)

    identifications, summary_ai = analyzer.identify_peaks(
        metadata=metadata,
        peaks=peaks_to_identify,
        candidates_by_peak=candidates_by_peak,
        batch_size=8,
        progress_callback=ai_progress,
        use_search_grounding=use_search
    )

    # 5. Build full analysis state
    progress_bar.progress(92, text="Consolidando reporte y cuantificación de áreas relativas...")
    import uuid
    sample_id = str(uuid.uuid4())
    
    analysis = SampleAnalysis(
        sample_id=sample_id,
        metadata=metadata,
        chromatogram=chromatogram,
        peaks=peaks,
        identifications=identifications,
        total_area=total_area,
        summary_ai=summary_ai
    )

    # 6. Auto-save if enabled
    if auto_save:
        try:
            repo = get_repository()
            repo.save_sample_analysis(analysis, raw_file_bytes=target_bytes, raw_filename=filename)
        except Exception as e:
            st.warning(f"Aviso de guardado: {str(e)}")

    progress_bar.progress(100, text="¡Análisis cromatográfico completado con éxito!")
    progress_bar.empty()

    # Pass result to parent view
    on_analysis_completed(analysis, target_bytes, filename)
