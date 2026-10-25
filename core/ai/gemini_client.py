"""
Gemini AI Client for Compound Identification and Chemical Analysis.
Uses the modern Google GenAI SDK (google-genai).
Decoupled from Streamlit or any web framework.
"""

import os
import json
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Callable
from ..models import SampleMetadata, PeakData, IdentificationResult, NistCandidate
from .prompt_builder import (
    build_system_instruction,
    build_batch_identification_prompt,
    build_chat_system_prompt
)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def clean_json_text(text: str) -> str:
    """Extracts raw JSON string from markdown code blocks or raw text."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


class GeminiAnalyzer:
    """Manages AI-driven compound identification and chromatographic chat."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-3.5-flash-lite"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.client = None

        if GENAI_AVAILABLE and self.api_key:
            try:
                self.client = genai.Client(api_key=self.api_key)
            except Exception:
                self.client = None

    def is_configured(self) -> bool:
        """Returns True if the Gemini client is initialized with an API key."""
        return self.client is not None and bool(self.api_key)

    def identify_peaks(
        self,
        metadata: SampleMetadata,
        peaks: List[PeakData],
        candidates_by_peak: Dict[int, List[NistCandidate]],
        batch_size: int = 10,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        use_search_grounding: bool = False
    ) -> Tuple[List[IdentificationResult], str]:
        """
        Identifies compounds for a list of peaks using Gemini AI + NIST candidates.
        Processes peaks in batches with rate-limit pacing and automatic model fallbacks.
        """
        all_identifications: List[IdentificationResult] = []
        overall_summaries: List[str] = []

        total_peaks = len(peaks)
        if total_peaks == 0:
            return [], "No se encontraron picos cromatográficos para analizar."

        # If Gemini is not configured, generate heuristic/NIST-based fallback
        if not self.is_configured():
            return self._heuristic_fallback_identification(peaks, candidates_by_peak)

        # Process in batches
        num_batches = (total_peaks + batch_size - 1) // batch_size

        # Models to try in order of preference
        models_to_try = [self.model_name]
        for alt in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if alt not in models_to_try:
                models_to_try.append(alt)

        for b_idx in range(num_batches):
            start_i = b_idx * batch_size
            end_i = min(start_i + batch_size, total_peaks)
            batch_peaks = peaks[start_i:end_i]

            if progress_callback:
                progress_callback(
                    b_idx + 1, 
                    num_batches, 
                    f"Analizando picos {start_i+1} a {end_i} de {total_peaks} con IA..."
                )

            prompt = build_batch_identification_prompt(metadata, batch_peaks, candidates_by_peak)
            system_instruction = build_system_instruction()

            response_text = ""
            batch_error = None
            used_model = self.model_name

            for model_candidate in models_to_try:
                try:
                    config_params: Dict[str, Any] = {
                        "system_instruction": system_instruction,
                        "temperature": 0.2,
                    }

                    if use_search_grounding:
                        config_params["tools"] = [types.Tool(google_search=types.GoogleSearch())]
                    else:
                        config_params["response_mime_type"] = "application/json"

                    config = types.GenerateContentConfig(**config_params)

                    response = self.client.models.generate_content(
                        model=model_candidate,
                        contents=prompt,
                        config=config
                    )
                    response_text = response.text or ""
                    used_model = model_candidate
                    batch_error = None
                    break
                except Exception as ex:
                    batch_error = ex
                    err_msg = str(ex).lower()
                    # If quota exhausted (429) or temporary server overload (503), wait and try alternative model
                    if "429" in err_msg or "exhausted" in err_msg or "503" in err_msg or "unavailable" in err_msg:
                        time.sleep(2.5)
                        continue
                    else:
                        time.sleep(1.0)
                        continue

            if response_text:
                try:
                    cleaned_json = clean_json_text(response_text)
                    data = json.loads(cleaned_json)

                    idents_data = data.get("identifications", [])
                    if data.get("overall_sample_summary"):
                        overall_summaries.append(data["overall_sample_summary"])

                    ident_dict = {item.get("peak_id"): item for item in idents_data}

                    for p in batch_peaks:
                        item = ident_dict.get(p.peak_id)
                        top_cand = (candidates_by_peak.get(p.peak_id) or [None])[0]
                        nist_score = top_cand.similarity_score if top_cand else 0.0

                        if item:
                            all_identifications.append(IdentificationResult(
                                peak_id=p.peak_id,
                                rt=p.rt,
                                area=p.area,
                                relative_area_pct=p.relative_area_pct,
                                compound_name=item.get("compound_name", top_cand.name if top_cand else f"Compuesto Pico #{p.peak_id}"),
                                iupac_name=item.get("iupac_name", ""),
                                cas_number=item.get("cas_number", top_cand.cas if top_cand else ""),
                                formula=item.get("formula", top_cand.formula if top_cand else ""),
                                molecular_weight=float(item.get("molecular_weight", top_cand.mw if top_cand else 0.0)),
                                confidence_level=item.get("confidence_level", "Medium"),
                                confidence_score=float(item.get("confidence_score", nist_score)),
                                nist_similarity=nist_score,
                                identification_source=f"Gemini ({used_model}) + NIST Library",
                                chemical_family=item.get("chemical_family", ""),
                                retention_behavior_analysis=item.get("retention_behavior_analysis", ""),
                                fragmentation_rationale=item.get("fragmentation_rationale", ""),
                                key_ions=item.get("key_ions", p.spectrum.get_prominent_mz_list(5) if p.spectrum else []),
                                alternative_candidates=item.get("alternative_candidates", [])
                            ))
                        else:
                            all_identifications.append(self._single_peak_fallback(p, top_cand))
                except Exception as parse_ex:
                    for p in batch_peaks:
                        top_cand = (candidates_by_peak.get(p.peak_id) or [None])[0]
                        all_identifications.append(self._single_peak_fallback(p, top_cand, error_msg=str(parse_ex)))
            else:
                # All models failed for this batch, fallback to NIST library matches
                for p in batch_peaks:
                    top_cand = (candidates_by_peak.get(p.peak_id) or [None])[0]
                    all_identifications.append(self._single_peak_fallback(p, top_cand, error_msg=str(batch_error or "Quota limit")))

            # Pacing delay between batches to respect free-tier RPM limits
            if b_idx < num_batches - 1:
                time.sleep(1.2)

        combined_summary = "\n\n".join(overall_summaries) if overall_summaries else "Análisis espectral completado con éxito."
        return all_identifications, combined_summary

    def _single_peak_fallback(
        self,
        p: PeakData,
        top_cand: Optional[NistCandidate],
        error_msg: str = ""
    ) -> IdentificationResult:
        """Creates a reasonable identification entry from top NIST candidate."""
        name = top_cand.name if top_cand else f"Compuesto desconocido (Pico #{p.peak_id})"
        cas = top_cand.cas if top_cand else ""
        formula = top_cand.formula if top_cand else ""
        mw = top_cand.mw if top_cand else 0.0
        score = top_cand.similarity_score if top_cand else 0.0
        conf = "High" if score >= 80 else ("Medium" if score >= 50 else "Low")

        reason = (
            f"Identificado a partir del mejor candidato de similitud espectral en la biblioteca NIST ({score:.1f}%)."
            if top_cand
            else "Pico sin coincidencia directa en biblioteca NIST."
        )
        if error_msg and "429" in error_msg:
            reason += " (Asignación automática directa por biblioteca espectral NIST; cuota API en espera)."
        elif error_msg:
            reason += " (Asignación directa por biblioteca espectral NIST)."

        return IdentificationResult(
            peak_id=p.peak_id,
            rt=p.rt,
            area=p.area,
            relative_area_pct=p.relative_area_pct,
            compound_name=name,
            cas_number=cas,
            formula=formula,
            molecular_weight=mw,
            confidence_level=conf,
            confidence_score=score,
            nist_similarity=score,
            identification_source="Biblioteca NIST (Modo Heurístico)",
            chemical_family="Desconocida / Derivado",
            retention_behavior_analysis=f"Tiempo de retención {p.rt:.3f} min.",
            fragmentation_rationale=reason,
            key_ions=p.spectrum.get_prominent_mz_list(5) if p.spectrum else [],
            alternative_candidates=[]
        )

    def _heuristic_fallback_identification(
        self,
        peaks: List[PeakData],
        candidates_by_peak: Dict[int, List[NistCandidate]]
    ) -> Tuple[List[IdentificationResult], str]:
        """Provides identifications based purely on NIST matching when Gemini API Key is absent."""
        results = []
        for p in peaks:
            top_cand = (candidates_by_peak.get(p.peak_id) or [None])[0]
            results.append(self._single_peak_fallback(p, top_cand))

        summary = (
            "⚠️ MODO SIMULACIÓN / NIST LOCAL: No se detectó una API Key de Gemini configurada. "
            "Los compuestos fueron asignados usando el algoritmo de similitud espectral Stein-Scott "
            "sobre la biblioteca NIST. Para activar el análisis químico avanzado con IA, explicaciones "
            "de fragmentación y verificación en línea, configura tu GEMINI_API_KEY en el panel lateral o archivo .env."
        )
        return results, summary

    def chat_response(
        self,
        history: List[Dict[str, str]],
        user_message: str,
        metadata: SampleMetadata,
        summary_text: str,
        compounds_overview: str
    ) -> str:
        """Generates a conversational response for the chat assistant."""
        if not self.is_configured():
            return (
                "⚠️ Para utilizar el Chat Asistente de IA sobre tus muestras cromatográficas, "
                "por favor ingresa tu API Key de Gemini en la barra lateral o en el archivo `.env`."
            )

        system_prompt = build_chat_system_prompt(metadata, summary_text, compounds_overview)

        # Build clean history objects compatible with google-genai
        chat_history = []
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            content = msg.get("content", "").strip()
            if content:
                chat_history.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=content)]
                ))

        models_to_try = [self.model_name]
        for alt in ["gemini-3.5-flash-lite", "gemini-3.8-flash"]:
            if alt not in models_to_try:
                models_to_try.append(alt)

        last_err = ""
        for model_to_use in models_to_try:
            try:
                chat = self.client.chats.create(
                    model=model_to_use,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.3
                    ),
                    history=chat_history
                )
                response = chat.send_message(user_message)
                return response.text or "No se pudo generar respuesta."
            except Exception as e:
                last_err = str(e)
                time.sleep(1.5)
                continue

        return f"Error al consultar al asistente Gemini: {last_err}"
