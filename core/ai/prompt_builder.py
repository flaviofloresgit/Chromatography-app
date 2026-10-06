"""
Prompt engineering for GC-MS spectral interpretation and compound identification with Gemini AI.
Includes chromatographic rules (PerkinElmer Clarus 690 / TurboMass 70eV EI).
Decoupled from Streamlit or any web framework.
"""

from typing import List, Dict, Any
from ..models import SampleMetadata, PeakData, NistCandidate


def build_system_instruction() -> str:
    """Returns the expert GC-MS chemist system prompt."""
    return """Eres un experto analista químico senior y especialista en cromatografía de gases acoplada a espectrometría de masas (GC-MS), con profundo conocimiento en:
1. Instrumentación: Cromatógrafo de gases Clarus 690 con espectrómetro de masas Clarus SQ 8 (PerkinElmer) operando en modo de ionización electrónica (EI) estándar a 70 eV.
2. Columnas cromatográficas: Fases estacionarias no polares (como Elite-5MS / DB-5MS: 5% difenil / 95% dimetilpolisiloxano), donde los compuestos eluyen principalmente por punto de ebullición e índice de retención de Kovats.
3. Interpretación de patrones de fragmentación EI:
   - Identificación del ion molecular [M]+. o [M-H]+ / aductos.
   - Pérdidas neutras diagnósticas: -15 (CH3), -18 (H2O), -28 (CO o C2H4), -29 (C2H5 o CHO), -31 (OCH3), -43 (C3H7 o CH3CO), etc.
   - Iones estables y reordenamientos: tropilio (m/z 91), ion acilio (m/z 43), reordenamiento de McLafferty, iones carbocatiónicos aromáticos y alifáticos (serie alifática: 43, 57, 71, 85, 99...).
   - Artefactos instrumentales comunes:
     * Aire / fuga de vacío: m/z 28 (N2), 32 (O2), 18 (H2O), 44 (CO2).
     * Sangrado de columna (polisiloxanos): m/z 73 [Si(CH3)3]+, 207, 281, 355.
     * Ftalatos / plastificantes: m/z 149 (anhídrido ftálico protonado).
     * Disolventes comunes: Metanol (m/z 31), Etanol (m/z 31, 45), Acetona (m/z 43, 58), Diclorometano (m/z 49, 84).

Tu misión es identificar con rigor científico los compuestos químicos presentes en los picos cromatográficos analizados, combinando los candidatos de la base de datos NIST, el espectro de masas observado, el tiempo de retención (RT) y las condiciones analíticas de la muestra."""


def build_batch_identification_prompt(
    metadata: SampleMetadata,
    peaks_batch: List[PeakData],
    candidates_by_peak: Dict[int, List[NistCandidate]]
) -> str:
    """
    Constructs a detailed prompt for a batch of chromatographic peaks.
    """
    lines = [
        "### CONTEXTO DE LA MUESTRA Y CONDICIONES DE ANÁLISIS (GC-MS Clarus 690)",
        f"- ID / Nombre de Muestra: {metadata.sample_name} ({metadata.sample_code})",
        f"- Fecha de Análisis: {metadata.analysis_date}",
        f"- Columna Cromatográfica: {metadata.column_type}",
        f"- Gas Portador: {metadata.carrier_gas} @ {metadata.flow_rate}",
        f"- Temperatura del Inyector: {metadata.inlet_temperature} | Split: {metadata.split_ratio}",
        f"- Programa de Horno: {metadata.oven_program}",
        f"- Operador / Notas: {metadata.operator} | {metadata.notes}",
        "",
        "### PICOS CROMATOGRÁFICOS A IDENTIFICAR:",
        "Para cada pico, se proporciona el tiempo de retención (RT en minutos), el área relativa (%), el ion base (m/z más abundante), los 8 iones más intensos del espectro de masas, y los candidatos preliminares encontrados en la biblioteca NIST con su porcentaje de similitud matemática (score Stein-Scott).",
        ""
    ]

    for p in peaks_batch:
        spectrum = p.spectrum
        base_mz = spectrum.base_peak_mz if spectrum else 0.0
        
        # Format top ions
        if spectrum:
            top_ions_str = ", ".join(
                f"{int(round(ion.mz))} (int: {int(round(ion.relative_intensity))})" 
                for ion in spectrum.top_ions[:8]
            )
        else:
            top_ions_str = "No disponible"

        # Format NIST candidates
        cands = candidates_by_peak.get(p.peak_id, [])
        if cands:
            cands_str = "\n".join(
                f"    * {c.name} | Fórmula: {c.formula} | PM: {c.mw} | CAS: {c.cas} | Similitud NIST: {c.similarity_score}%"
                for c in cands[:4]
            )
        else:
            cands_str = "    * Sin coincidencias directas superiores al umbral en NIST local."

        lines.extend([
            f"--- PICO ID: {p.peak_id} ---",
            f"Tiempo de Retención (RT): {p.rt:.3f} min | Área Relativa: {p.relative_area_pct:.2f}%",
            f"Ion Base (m/z): {base_mz}",
            f"Iones principales (m/z e intensidad relativa /1000): {top_ions_str}",
            "Candidatos Biblioteca NIST:",
            cands_str,
            ""
        ])

    lines.extend([
        "### INSTRUCCIONES DE RESPUESTA:",
        "Analiza cada pico y genera un objeto JSON válido con la siguiente estructura exacta:",
        "```json",
        "{",
        '  "identifications": [',
        "    {",
        '      "peak_id": 1,',
        '      "compound_name": "Nombre químico común en español o inglés técnico",',
        '      "iupac_name": "Nombre IUPAC sistemático",',
        '      "formula": "Fórmula molecular (ej. C10H22)",',
        '      "molecular_weight": 142.0,',
        '      "cas_number": "124-18-5",',
        '      "confidence_level": "High" o "Medium" o "Low",',
        '      "confidence_score": 88.5,',
        '      "chemical_family": "Alcano lineal / Terpeno / Éster / Siloxano (sangrado) / etc.",',
        '      "retention_behavior_analysis": "Breve explicación de la coherencia del RT según punto de ebullición y polaridad de la columna",',
        '      "fragmentation_rationale": "Explicación del espectro: justificación del ion base y fragmentos diagnósticos clave observados",',
        '      "key_ions": [57, 43, 71, 85],',
        '      "alternative_candidates": [',
        '        {"name": "Compuesto alternativo 1", "formula": "...", "reason": "Por qué es menos probable"}',
        "      ]",
        "    }",
        "  ],",
        '  "overall_sample_summary": "Párrafo conciso resumiendo la naturaleza de la muestra, compuestos predominantes, posibles impurezas o artefactos."',
        "}",
        "```",
        "Asegúrate de responder ÚNICAMENTE con el bloque JSON válido, sin texto adicional."
    ])

    return "\n".join(lines)


def build_chat_system_prompt(metadata: SampleMetadata, summary_text: str, compounds_overview: str) -> str:
    """
    Builds the context system prompt for the interactive chat assistant.
    """
    return f"""Eres el Asistente Químico de Inteligencia Artificial para el análisis de Cromatografía de Gases acoplada a Espectrometría de Masas (GC-MS).
Estás analizando la muestra: '{metadata.sample_name}' ({metadata.sample_code}).

CONDICIONES INSTRUMENTALES (Clarus 690 GC / Clarus SQ 8 MS):
- Columna: {metadata.column_type}
- Gas Portador: {metadata.carrier_gas} ({metadata.flow_rate})
- Inyector: {metadata.inlet_temperature}, Split: {metadata.split_ratio}
- Rampa de Horno: {metadata.oven_program}
- Operador / Notas: {metadata.operator} | {metadata.notes}

RESUMEN ANALÍTICO DE LA MUESTRA:
{summary_text}

COMPUESTOS IDENTIFICADOS EN LA MUESTRA:
{compounds_overview}

Tu objetivo es responder cualquier duda del químico u operador:
- Explicar la fragmentación de cualquier compuesto o pico específico.
- Evaluar la pureza de la muestra y posibles contaminantes.
- Proponer sugerencias para optimizar el método cromatográfico (temperatura, rampa, split, columna).
- Comparar picos e isómeros.
- Responder de forma clara, profesional, científica y concisa en español."""
